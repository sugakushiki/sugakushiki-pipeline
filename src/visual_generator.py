"""
visual_generator.py - Generate visual MP4 segments for each scene

Usage:
    python visual_generator.py scene_definition.json timing.json --output-dir examples/moriarty
    python visual_generator.py scene_definition.json timing.json --output-dir examples/moriarty --skip-manim

Input:  scene_definition.json + timing.json
Output: {output_dir}/visuals/{scene_id}.mp4 for each scene

Visual types:
    ken_burns     - Static image with pan/zoom effect (Pillow+FFmpeg pipe)
    text_overlay  - Rendered text on dark background
    manim         - Manim animation (requires Manim installation)
    blender       - Blender 3D animation (requires Blender installation)
    route_map     - World map with travel routes (matplotlib+Natural Earth→Ken Burns)

Fallback behavior:
    - Unknown/aliased manim templates → resolved via TEMPLATE_ALIASES or
      gracefully degraded to text_overlay (no more purple stub screens)
    - Missing manim_templates dir / render failure → text_overlay fallback
    - --skip-manim → text_overlay fallback (not stub)
    - Unknown visual type → text_overlay fallback
    - ken_burns with no image → stub (image is genuinely required)

Requires: FFmpeg in PATH. Manim required unless --skip-manim.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

# route_map (描画・幾何・レイアウト検査・auto-fix・preflight) は route_map_render.py
# に分割してある。ここで名前を再輸出しているのは、pipeline / smoke test /
# check_*.py が `from visual_generator import route_map_preflight` の形で呼んでいる
# ため。route_map_render は generate_ken_burns / generate_text_overlay / find_font を
# 関数の中で遅延 import するので循環にはならない。
#
# **モンキーパッチはこちらではなく route_map_render 側に当てること** — preflight を
# 掃引する手順 (internal notes) で内部関数を差し替えるとき、
# ここの名前を書き換えても内部の呼び出しは向こうの名前空間で解決される。
from route_map_render import (  # noqa: F401  (re-export)
    _ROUTE_BG_HEX,
    _ROUTE_CATEGORY_COLORS,
    _ROUTE_COLOR_MIN_DIST,
    _apply_route_map_auto_fix_stage,
    _auto_bounds_pad,
    _check_label_ownership,
    _check_line_through_label,
    _check_route_map_collisions,
    _color_distance,
    _download_natural_earth,
    _get_geojson_cache_dir,
    _hex_to_rgb,
    _load_geojson_polygons,
    _ownership_ratio_of,
    _ownership_ratios,
    _ownership_veto,
    _rect_curve_distance,
    _rect_point_distance,
    _segment_length_inside_rect,
    check_route_palette_separation,
    generate_route_map,
    ken_burns_safe_rect,
    route_label_attachment,
    route_map_preflight,
)

# ---------------------------------------------------------------------------
# Video settings
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
PIXEL_FORMAT = "rgb24"

# ---------------------------------------------------------------------------
# Style settings (from STYLE_GUIDE.md)
# ---------------------------------------------------------------------------
BG_COLOR = (0x1A, 0x1A, 0x2E)  # #1a1a2e
ACCENT_GOLD = (0xE2, 0xB7, 0x14)  # #e2b714
ACCENT_CYAN = (0x4C, 0xC9, 0xF0)  # #4cc9f0
ACCENT_PINK = (0xF7, 0x25, 0x85)  # #f72585
TEXT_WHITE = (0xFF, 0xFF, 0xFF)
TEXT_DIM = (0xAA, 0xAA, 0xBB)

FONT_NAME = "BIZ UDMincho"
# Windows font path (will be searched)
FONT_SEARCH_PATHS = [
    "_font.ttc",  # local copy
    "C:/Windows/Fonts/BIZ-UDMinchoM.ttc",
    "C:/Windows/Fonts/BIZUDMincho-Regular.ttf",
    "/usr/share/fonts/truetype/bizud-mincho/BIZUDMincho-Regular.ttf",  # Linux
]


def find_font():
    """Find BIZ UDMincho font file."""
    for path in FONT_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    return None


# ===========================================================================
# FFmpeg subprocess timeouts
# ===========================================================================
#
# ken_burns / stub encodes stream raw 1080p frames into ffmpeg over a stdin
# pipe. If ffmpeg stops draining that pipe, the pipe
# buffer fills and proc.stdin.write() blocks forever; there is no return code to
# check because the process never exits. Manim render already had a 240s bound
# (_MANIM_TIMEOUT_S); ffmpeg had none. These guards bound every ffmpeg/ffprobe
# call so a stuck encode fails fast (explicit error -> recorded fallback marker
# -> placeholder) instead of hanging the whole build.
#
# Timeouts are tiered by workload and overridable via env vars. Defaults are
# generous: per-scene ffmpeg ops act on one <=30s clip, so 300s never
# false-positives on real work while still catching a true hang.
#
# Windows note: ffmpeg/ffprobe reading a pipe/file are leaf processes (no child
# processes), so proc.kill() / run()'s TerminateProcess reaps them without a
# process-tree walk. (Manim, which shells out to its own ffmpeg child, is the
# one place a tree-kill would matter -- left as-is, out of this change's scope.)


def _ffmpeg_timeout_s(env_var: str, default: int) -> int:
    """Read a positive-int timeout override from the environment, else default."""
    raw = os.environ.get(env_var)
    if raw:
        try:
            val = int(raw.strip())
            if val > 0:
                return val
        except ValueError:
            pass
    return default


_FFPROBE_TIMEOUT_S = _ffmpeg_timeout_s("SUGAKUSHIKI_FFPROBE_TIMEOUT_S", 60)
_FFMPEG_TIMEOUT_S = _ffmpeg_timeout_s("SUGAKUSHIKI_FFMPEG_TIMEOUT_S", 300)


class _FFmpegError(RuntimeError):
    """An ffmpeg/ffprobe subprocess failed (non-zero exit)."""


class _FFmpegTimeout(_FFmpegError):
    """An ffmpeg/ffprobe subprocess exceeded its timeout and was killed."""


def _run_ffmpeg_bounded(cmd, timeout=None, label="ffmpeg", **kwargs):
    """subprocess.run(cmd) with a wall-clock timeout, raising _FFmpegTimeout.

    For non-streaming ffmpeg/ffprobe calls (no stdin pipe). The process is a
    leaf, so run()'s kill-on-timeout reaps it cleanly on Windows.
    """
    if timeout is None:
        timeout = _FFMPEG_TIMEOUT_S
    kwargs.setdefault("capture_output", True)
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise _FFmpegTimeout(f"{label}: ffmpeg timed out after {timeout}s") from exc


def _pipe_frames_to_ffmpeg(cmd, frames, timeout_s, label):
    """Stream raw RGB frames to an ffmpeg Popen via stdin under a watchdog timeout.

    Raw 1080p frames are ~6 MB each, so they must be streamed rather than
    buffered -- which rules out subprocess.run(timeout=). A Timer kills ffmpeg
    if it overruns; the kill breaks the pipe and unblocks any write() stuck on a
    full buffer. On a clean exit (rc 0) we return; otherwise we
    distinguish a timeout (_FFmpegTimeout) from a genuine ffmpeg error
    (_FFmpegError) -- the latter was previously swallowed because proc.wait()'s
    return code was ignored.
    """
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    state = {"timed_out": False}

    def _watchdog():
        state["timed_out"] = True
        try:
            proc.kill()
        except Exception:
            pass

    timer = threading.Timer(timeout_s, _watchdog)
    timer.daemon = True
    timer.start()
    try:
        for frame in frames:
            proc.stdin.write(frame)
    except (BrokenPipeError, OSError):
        # ffmpeg exited early (its own error, or killed by the watchdog) and the
        # pipe broke mid-write. Classified via returncode / timed_out below.
        pass
    finally:
        try:
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        proc.wait()
        timer.cancel()

    # rc == 0 only if ffmpeg exited on its own (a watchdog kill yields non-zero),
    # so a late-firing timer after success can never be misread as a timeout.
    if proc.returncode == 0:
        return
    if state["timed_out"]:
        raise _FFmpegTimeout(f"{label}: ffmpeg killed after {timeout_s}s timeout")
    raise _FFmpegError(f"{label}: ffmpeg exited with code {proc.returncode}")


# ===========================================================================
# Ken Burns effect (Pillow + FFmpeg pipe, confirmed Weekend 2)
# ===========================================================================


def generate_ken_burns(
    image_path: str,
    output_path: str,
    duration: float,
    effect: str = "zoom_in",
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate Ken Burns effect video from a still image.

    Uses Pillow for frame generation piped to FFmpeg as raw video.
    This approach avoids the jitter problem of FFmpeg's zoompan filter.
    """
    from PIL import Image

    img = Image.open(image_path).convert("RGB")

    # Scale image to cover the output dimensions with room for zoom
    zoom_range = 0.15  # 15% zoom range
    max_zoom = 1.0 + zoom_range
    scale_factor = max(
        (width * max_zoom) / img.width,
        (height * max_zoom) / img.height,
    )
    new_w = int(img.width * scale_factor)
    new_h = int(img.height * scale_factor)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    total_frames = int(duration * fps)
    if total_frames < 1:
        total_frames = 1

    # FFmpeg process: receive raw RGB frames via pipe
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        PIXEL_FORMAT,
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]

    def _frames():
        for frame_idx in range(total_frames):
            t = frame_idx / max(total_frames - 1, 1)  # 0.0 → 1.0

            # Calculate zoom level based on effect
            if effect == "zoom_in":
                zoom = 1.0 + zoom_range * t
            elif effect == "zoom_out":
                zoom = max_zoom - zoom_range * t
            elif effect == "pan_left":
                zoom = 1.0 + zoom_range * 0.5  # slight zoom, pan left
            elif effect == "pan_right":
                zoom = 1.0 + zoom_range * 0.5  # slight zoom, pan right
            else:
                zoom = 1.0 + zoom_range * t  # default: zoom_in

            # Use float coordinates for sub-pixel precision (eliminates jitter)
            crop_w = width * max_zoom / zoom
            crop_h = height * max_zoom / zoom

            # Center crop with optional pan (float precision)
            if effect == "pan_left":
                cx = (new_w - crop_w) * (1.0 - t * 0.5)
            elif effect == "pan_right":
                cx = (new_w - crop_w) * (0.5 + t * 0.5)
            else:
                cx = (new_w - crop_w) / 2.0
            cy = (new_h - crop_h) / 2.0

            # Clamp (float)
            cx = max(0.0, min(cx, new_w - crop_w))
            cy = max(0.0, min(cy, new_h - crop_h))

            # Use resize with float box for sub-pixel interpolation
            frame = img.resize(
                (width, height), Image.LANCZOS, box=(cx, cy, cx + crop_w, cy + crop_h)
            )
            yield frame.tobytes()

    # Bounded by a watchdog: a stuck ffmpeg pipe fails fast instead of hanging.
    _pipe_frames_to_ffmpeg(
        cmd, _frames(), _FFMPEG_TIMEOUT_S, f"ken_burns[{os.path.basename(output_path)}]"
    )


# ===========================================================================
# Text overlay (Pillow rendering)
# ===========================================================================


def _draw_vignette(img, strength=0.4):
    """Apply radial vignette darkening to edges of a PIL Image (in-place).

    Creates a subtle depth effect by darkening corners/edges,
    drawing the viewer's eye to the center text.
    """
    from PIL import Image, ImageDraw

    w, h = img.size
    # Create a black overlay
    overlay = Image.new("L", (w, h), 0)
    draw_ov = ImageDraw.Draw(overlay)
    # Draw concentric white ellipses (center = bright, edges = dark)
    cx, cy = w // 2, h // 2
    max_r = max(w, h)
    steps = 40
    for i in range(steps):
        frac = i / steps
        # Brightness: 255 at center, 0 at edge
        brightness = int(255 * (1.0 - frac * strength))
        rx = int(max_r * (1.0 - frac * 0.8))
        ry = int(max_r * 0.6 * (1.0 - frac * 0.8))
        draw_ov.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=brightness)
    # Composite: darken original where overlay is dark
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    # overlay is the mask: 255=show original, 0=show black
    result = Image.composite(img, dark, overlay)
    img.paste(result)


def _hex_alpha(rgb_tuple, alpha):
    """Blend an RGB tuple toward the background color by alpha.

    PIL doesn't support RGBA drawing on RGB images, so we manually blend.
    alpha=1.0 → full color, alpha=0.0 → background color.
    """
    bg = BG_COLOR
    return tuple(int(c * alpha + b * (1 - alpha)) for c, b in zip(rgb_tuple, bg, strict=False))


def _rgb_to_hex(rgb_tuple) -> str:
    """(R, G, B) ints → '#rrggbb' for matplotlib color spec."""
    return "#{:02x}{:02x}{:02x}".format(*rgb_tuple)


# 禁則処理 (kinsoku): 行頭・行末で使ってはいけない約物。
_KINSOKU_HEAD = "、。，．・：；？！）］｝」』】〕〉》”’"  # これで行を始めない
_KINSOKU_TAIL = "（［｛「『【〔〈《“‘"  # これで行を終えない


def _apply_kinsoku(lines: list[str]) -> list[str]:
    """禁則処理: 折り返し後、行が、。」』 等で始まらない・「『（ 等で終わらないよう整える。
    ある回: quote overlay が『…寿命を』/『、いわば二倍にした』と折り返し、読点が行頭に
    孤立して不自然だった (行頭禁則違反)。行頭約物は直前行末尾へ追い込み、行末の開き括弧は
    次行先頭へ追い出す。lines を破壊的に整えて返す。"""
    # 行頭禁則: 行頭の約物を直前行の末尾へ追い込む (追い込み)。
    i = 1
    while i < len(lines):
        while lines[i] and lines[i][0] in _KINSOKU_HEAD:
            lines[i - 1] += lines[i][0]
            lines[i] = lines[i][1:]
        if not lines[i]:
            del lines[i]
            continue
        i += 1
    # 行末禁則: 行末の開き括弧を次行の先頭へ追い出す (追い出し)。
    i = 0
    while i < len(lines) - 1:
        while lines[i] and lines[i][-1] in _KINSOKU_TAIL:
            lines[i + 1] = lines[i][-1] + lines[i + 1]
            lines[i] = lines[i][:-1]
        if not lines[i]:
            del lines[i]
            i = max(0, i - 1)
            continue
        i += 1
    return lines


def generate_text_overlay(
    visual: dict,
    output_path: str,
    duration: float,
    font_path: str = None,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate text overlay video with style-specific design.

    Renders styled text card on dark background with vignette,
    then applies subtle Ken Burns effect.

    Styles:
        definition  - Gold title + accent line + white explanation
        fact        - Left accent bar + white text
        quote       - 「」quotation marks + attribution line
        title_card  - Large centered gold text + decorative lines

    TeX support: main/sub が `$...$` で囲まれているか `\\` を含む場合、
    matplotlib mathtext で画像レンダリングされる（BIZ UDMincho が豆腐化
    する ℵ・ℕ・ℝ・添字などに対応）。折り返しはせず単一画像として配置。
    """
    from PIL import Image, ImageDraw, ImageFont

    from math_render import render_mathtext_png, uses_tex

    content = visual.get("content", {})
    _scene_id = os.path.splitext(os.path.basename(output_path))[0]
    main_text = content.get("main", "")
    sub_text = content.get("sub", "")
    style = visual.get("style", "fact")

    # Substitute math symbols that Japanese fonts may not support
    # (適用は非TeXパートのみ。TeXは mathtext で描くので置換不要)
    _SYMBOL_SUBS = {
        "≤": "≦",
        "≥": "≧",
        "→": "→",
        "∀": "∀",
        "∃": "∃",
    }
    if not uses_tex(main_text):
        for old, new in _SYMBOL_SUBS.items():
            main_text = main_text.replace(old, new)
    if not uses_tex(sub_text):
        for old, new in _SYMBOL_SUBS.items():
            sub_text = sub_text.replace(old, new)

    # Create base image (larger than output for Ken Burns room)
    margin_factor = 1.15
    img_w = int(width * margin_factor)
    img_h = int(height * margin_factor)
    img = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Vignette background (radial gradient darkening at edges) ---
    _draw_vignette(img, strength=0.4)

    # Load font
    if font_path is None:
        font_path = find_font()

    def load_font(size):
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    max_text_width = int(img_w * 0.70)

    def wrap_text(text, font, max_width):
        """Wrap text to fit within max_width, then apply 禁則処理 (_apply_kinsoku) so a
        line never starts with、。」』 nor ends with an opening bracket 「『（."""
        if not text:
            return []
        lines = []
        for paragraph in text.split("\n"):
            current_line = ""
            for char in paragraph:
                test = current_line + char
                bbox = font.getbbox(test)
                if bbox[2] - bbox[0] > max_width and current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    current_line = test
            if current_line:
                lines.append(current_line)
        return _apply_kinsoku(lines)

    def text_block_height(lines, line_h):
        return len(lines) * line_h if lines else 0

    # --- TeX-aware block helpers ---------------------------------------
    # prep_block: text → either wrapped lines (dict with 'lines') or a
    # pre-rendered mathtext image (dict with 'image'). Uniform 'height'
    # and 'widths' keys let layout code ignore the distinction.
    # render_block: draws a prepared block and returns the post-block y.
    def prep_block(text, font, font_size, color_rgb, wrap_width):
        if uses_tex(text):
            im = render_mathtext_png(text, fontsize=font_size, color_hex=_rgb_to_hex(color_rgb))
            return {"is_tex": True, "image": im, "height": im.height, "widths": [im.width]}
        lines = wrap_text(text, font, wrap_width)
        # misreading: orphan-line guard. A block wrapping to a final line of ONE character
        # (intro_04 "…まとめ上げた" -> "…まとめ上げ" + lone "た") reads as a jarring stray
        # line. Deterministic warn at render (exact font metrics); fix by adding a manual
        # \n at a natural break or shortening. Not auto-fixed (rebalance would fight 禁則).
        if len(lines) > 1 and len(lines[-1].strip()) == 1:
            print(
                f"[OVERLAY-ORPHAN] {_scene_id}: 折り返し最終行が1文字 "
                f"'{lines[-1].strip()}' ({text[:24]!r})。手動 \\n で均等分割 or 短縮を推奨",
                file=sys.stderr,
            )
        line_h = int(font_size * 1.5)
        widths = [font.getbbox(ln)[2] - font.getbbox(ln)[0] for ln in lines]
        return {
            "is_tex": False,
            "lines": lines,
            "line_h": line_h,
            "height": len(lines) * line_h,
            "widths": widths,
        }

    def render_block(block, font, color_rgb, x_fn, y_top):
        y = y_top
        if block["is_tex"]:
            tim = block["image"]
            x = int(x_fn(tim.width))
            img.paste(tim, (x, int(y)), tim)
            return y + tim.height
        for ln, w in zip(block["lines"], block["widths"], strict=False):
            x = int(x_fn(w))
            draw.text((x, int(y)), ln, font=font, fill=color_rgb)
            y += block["line_h"]
        return y

    # ─── Style: definition ────────────────────────────────────────────
    if style == "definition":
        main_font = load_font(60)
        sub_font = load_font(34)
        main_block = prep_block(main_text, main_font, 60, ACCENT_GOLD, max_text_width)
        sub_block = prep_block(sub_text, sub_font, 34, TEXT_WHITE, max_text_width)

        sep_gap = 40
        total_h = main_block["height"] + sep_gap + 4 + sub_block["height"]
        y = (img_h - total_h) // 2

        center_x = lambda w: (img_w - w) // 2
        y = render_block(main_block, main_font, ACCENT_GOLD, center_x, y)

        # Horizontal accent line
        y += sep_gap // 2
        line_w = min(max_text_width, 500)
        lx = (img_w - line_w) // 2
        draw.line([(lx, y), (lx + line_w, y)], fill=ACCENT_GOLD, width=2)
        y += 4 + sep_gap // 2

        y = render_block(sub_block, sub_font, TEXT_WHITE, center_x, y)

    # ─── Style: quote ─────────────────────────────────────────────────
    elif style == "quote":
        main_font = load_font(48)
        sub_font = load_font(28)
        main_block = prep_block(main_text, main_font, 48, TEXT_WHITE, int(max_text_width * 0.85))
        sub_block = prep_block(sub_text, sub_font, 28, TEXT_DIM, max_text_width)

        # Legacy line heights used for closing-quote positioning below.
        main_line_h = int(48 * 1.6)
        total_h = main_block["height"] + 50 + sub_block["height"]
        y = (img_h - total_h) // 2

        # Opening quotation mark
        quote_font = load_font(96)
        draw.text(
            ((img_w - max_text_width) // 2 - 20, y - 60),
            "「",
            font=quote_font,
            fill=_hex_alpha(ACCENT_GOLD, 0.3),
        )

        # Main text (white, slightly indented)
        text_left = (img_w - int(max_text_width * 0.85)) // 2
        y = render_block(main_block, main_font, TEXT_WHITE, lambda _w: text_left, y)

        # Closing quotation mark: horizontally just after the last
        # visible element, vertically overlapping its top area.
        if main_block["is_tex"]:
            last_w = main_block["image"].width
            close_y = y - main_block["image"].height // 2 - 30
        else:
            last_w = main_block["widths"][-1] if main_block["widths"] else 0
            close_y = y - main_line_h - 10
        draw.text(
            (text_left + last_w + 10, close_y),
            "」",
            font=quote_font,
            fill=_hex_alpha(ACCENT_GOLD, 0.3),
        )

        # Attribution (dim, right-aligned)
        y += 50
        right_margin = (img_w - max_text_width) // 2
        y = render_block(sub_block, sub_font, TEXT_DIM, lambda w: img_w - w - right_margin, y)

    # ─── Style: title_card ────────────────────────────────────────────
    elif style == "title_card":
        main_font = load_font(72)
        sub_font = load_font(36)
        main_block = prep_block(main_text, main_font, 72, ACCENT_GOLD, max_text_width)
        sub_block = prep_block(sub_text, sub_font, 36, TEXT_DIM, max_text_width)

        total_h = main_block["height"] + 60 + sub_block["height"]
        y = (img_h - total_h) // 2

        # Decorative line above
        deco_w = 120
        dx = (img_w - deco_w) // 2
        draw.line([(dx, y - 30), (dx + deco_w, y - 30)], fill=ACCENT_GOLD, width=3)

        center_x = lambda w: (img_w - w) // 2
        y = render_block(main_block, main_font, ACCENT_GOLD, center_x, y)

        # Decorative line below main
        y += 10
        draw.line([(dx, y), (dx + deco_w, y)], fill=ACCENT_GOLD, width=3)
        y += 50

        y = render_block(sub_block, sub_font, TEXT_DIM, center_x, y)

    # ─── Style: fact (default) ────────────────────────────────────────
    else:
        main_font = load_font(50)
        sub_font = load_font(30)
        main_block = prep_block(main_text, main_font, 50, TEXT_WHITE, int(max_text_width * 0.9))
        sub_block = prep_block(sub_text, sub_font, 30, TEXT_DIM, int(max_text_width * 0.9))

        gap = 30 if sub_block["height"] > 0 else 0
        total_h = main_block["height"] + gap + sub_block["height"]
        y = (img_h - total_h) // 2

        # Left accent bar
        bar_x = (img_w - max_text_width) // 2
        bar_top = y - 10
        bar_bottom = y + total_h + 10
        draw.line([(bar_x, bar_top), (bar_x, bar_bottom)], fill=ACCENT_CYAN, width=4)

        text_left = bar_x + 30
        left_x = lambda _w: text_left
        y = render_block(main_block, main_font, TEXT_WHITE, left_x, y)

        if sub_block["height"] > 0:
            y += 30
            y = render_block(sub_block, sub_font, TEXT_DIM, left_x, y)

    # Save temp image for Ken Burns
    temp_img = os.path.join(
        os.path.dirname(output_path),
        f"_temp_{os.path.basename(output_path).replace('.mp4', '.png')}",
    )
    img.save(temp_img)

    try:
        generate_ken_burns(
            temp_img, output_path, duration, effect="zoom_in", width=width, height=height, fps=fps
        )
    finally:
        if os.path.exists(temp_img):
            os.remove(temp_img)


# ===========================================================================
# Manim rendering
# ===========================================================================

# Files to exclude from template discovery
_MANIM_EXCLUDE = {"style.py", "__init__.py", "_manim_params.json"}

# Alias mapping: generic template names → closest match in available templates.
# Only generic aliases that make sense regardless of episode. Module-level so
# both generate_manim() and the visual-cache staleness key resolve the
# same way (single source of truth).
TEMPLATE_ALIASES = {
    "graph_coloring": "random_graph_coloring",
    "coloring": "random_graph_coloring",
    "world_map": "route_map",
    "travel_map": "route_map",
}


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase: 'erdos_network' → 'ErdosNetwork'."""
    return "".join(word.capitalize() for word in name.split("_"))


def discover_manim_templates(manim_templates_dir: str) -> dict[str, tuple[str, str]]:
    """Auto-discover Manim templates from directory.

    Scans .py files in manim_templates_dir, finds Scene subclasses via ast,
    and builds a template_name → (filename, ClassName) mapping.

    Convention: template name = filename without .py extension.
    Class discovery: parses each file for classes inheriting from Scene.
    Falls back to PascalCase conversion if ast parsing fails.

    Returns:
        {"bertrand_postulate": ("bertrand_postulate.py", "BertrandPostulate"), ...}
    """
    import ast as _ast

    templates = {}
    if not manim_templates_dir or not os.path.isdir(manim_templates_dir):
        return templates

    for fname in sorted(os.listdir(manim_templates_dir)):
        if not fname.endswith(".py") or fname in _MANIM_EXCLUDE or fname.startswith("_"):
            continue

        template_name = fname[:-3]  # remove .py
        filepath = os.path.join(manim_templates_dir, fname)

        # Try to find Scene subclass via ast
        class_name = None
        try:
            with open(filepath, encoding="utf-8") as f:
                tree = _ast.parse(f.read())
            for node in _ast.walk(tree):
                if isinstance(node, _ast.ClassDef):
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, _ast.Name):
                            base_names.append(base.id)
                        elif isinstance(base, _ast.Attribute):
                            base_names.append(base.attr)
                    if "Scene" in base_names:
                        class_name = node.name
                        break  # use first Scene subclass
        except Exception:
            pass

        # Fallback: snake_case → PascalCase
        if not class_name:
            class_name = _snake_to_pascal(template_name)

        templates[template_name] = (fname, class_name)

    return templates


def _record_manim_fallback(output_path: str, scene_id: str, reason: str) -> None:
    """Append scene_id to _fallback_scenes.json sidecar.

    Manim render fallback (timeout / error / lookup fail) が「[OK]」報告 +
    placeholder mp4 で silent fail する問題への layered detect。pipeline
    verify_outputs が本 sidecar を読んで WARN 出力。

    an earlier episodeで pascals_triangle.binomial_highlight + probability_link
    が 240s timeout → fallback placeholder「Math 11 [pascals_triangle]」で
    silent fail、user 動画視聴で初発覚した failure mode の構造防御。
    """
    import datetime as _dt

    sidecar = os.path.join(os.path.dirname(output_path), "_fallback_scenes.json")
    record: list = []
    if os.path.exists(sidecar):
        try:
            with open(sidecar, encoding="utf-8") as f:
                record = json.load(f)
            if not isinstance(record, list):
                record = []
        except Exception:
            record = []
    record.append(
        {
            "scene_id": scene_id,
            "reason": reason,
            "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    try:
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # sidecar write failure is non-fatal


def _clear_manim_fallback(output_path: str, scene_id: str) -> None:
    """Drop this scene's fallback records after a successful render.

    `_record_manim_fallback` only ever appends, so a scene that fell back once
    stayed on the list for the life of the episode and every later build warned
    about a placeholder that had long since been replaced. An earlier episode carried 19
    entries from an aborted 2026-07-26 run for good; the warning was true of
    that run and false of the episode, which is the worst way for a check to be
    wrong -- it trains the reader to ignore it.

    With this, the sidecar means exactly one thing: the scenes whose MOST RECENT
    render attempt did not produce a real render. A scene that was not re-run
    keeps its entry (its mp4 really is still the placeholder).
    """
    sidecar = os.path.join(os.path.dirname(output_path), "_fallback_scenes.json")
    if not os.path.exists(sidecar):
        return
    try:
        with open(sidecar, encoding="utf-8") as f:
            record = json.load(f)
        if not isinstance(record, list):
            return
        kept = [r for r in record if r.get("scene_id") != scene_id]
        if len(kept) == len(record):
            return
        if kept:
            with open(sidecar, "w", encoding="utf-8") as f:
                json.dump(kept, f, ensure_ascii=False, indent=2)
        else:
            os.remove(sidecar)
    except Exception:
        pass  # sidecar bookkeeping must never break a good render


def _manim_to_text_overlay_fallback(visual: dict, scene_id: str) -> dict:
    """Convert a manim visual spec to a text_overlay visual for graceful fallback.

    Extracts meaningful text from manim params to display instead of a stub.
    """
    params = visual.get("params", {})
    template = visual.get("template", "")

    # Try to extract displayable text from params
    main_text = ""
    sub_text = ""

    # Common param patterns across templates
    if "title" in params:
        main_text = params["title"]
    elif "label" in params:
        main_text = params["label"]
    elif "equation" in params:
        main_text = params["equation"]
    elif "formula" in params:
        main_text = params["formula"]

    if "description" in params:
        sub_text = params["description"]
    elif "subtitle" in params:
        sub_text = params["subtitle"]

    # If no text found, use scene_id as fallback
    if not main_text:
        # Convert scene_id to readable text: "math_02" → "Math 02"
        main_text = scene_id.replace("_", " ").title()
        sub_text = f"[{template}]" if template else ""

    return {
        "type": "text_overlay",
        "style": "definition",
        "content": {
            "main": main_text,
            "sub": sub_text,
        },
    }


# 強化 (b): Manim render timeout を定数化し near-timeout を予兆警告。
# 過去 math_07 gimbal_lock が 240s timeout -> text_overlay placeholder で
# silent ship した near-miss。timeout 失敗自体は pipeline の placeholder
# バナーで事後検出済だが、閾値超 (既定 70%) の「危険水域」レンダリングは成功
# しても警告し、僅かな負荷増で placeholder 化する前に template 簡素化を促す。
_MANIM_TIMEOUT_S = 240
_MANIM_NEAR_TIMEOUT_FRAC = 0.7


def generate_manim(
    scene_id: str,
    visual: dict,
    output_path: str,
    duration: float,
    manim_templates_dir: str = None,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate Manim animation MP4.

    Writes params to _manim_params.json, calls `manim render`, then
    adjusts output duration to match timing.json.
    """
    template = visual.get("template", "")
    params = visual.get("params", {})

    if not manim_templates_dir or not os.path.isdir(manim_templates_dir):
        print("\n    [WARN] manim_templates dir not found, falling back to text_overlay.")
        _record_manim_fallback(output_path, scene_id, "templates_dir_missing")
        fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    # Map template name → file and class (auto-discovered from directory)
    TEMPLATE_MAP = discover_manim_templates(manim_templates_dir)

    # Resolve alias if needed
    resolved = template
    if template not in TEMPLATE_MAP and template in TEMPLATE_ALIASES:
        resolved = TEMPLATE_ALIASES[template]
        print(f"\n    [ALIAS] Template alias: '{template}' -> '{resolved}'")

    if resolved not in TEMPLATE_MAP:
        # Fallback: generate text_overlay instead of stub (much better than black screen)
        print(f"\n    [WARN] Unknown template '{template}', falling back to text_overlay.")
        _record_manim_fallback(output_path, scene_id, f"unknown_template:{template}")
        fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    template_file, class_name = TEMPLATE_MAP[resolved]
    template_path = os.path.join(manim_templates_dir, template_file)

    if not os.path.exists(template_path):
        print(
            f"\n    [WARN] Template file not found: {template_path}, falling back to text_overlay."
        )
        _record_manim_fallback(output_path, scene_id, f"template_file_missing:{template_file}")
        fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    # Write params JSON for template to read
    # Use absolute path so it works regardless of cwd
    abs_templates_dir = os.path.abspath(manim_templates_dir)
    params_path = os.path.join(abs_templates_dir, "_manim_params.json")
    # Inject duration so templates can adapt animation timing to audio length
    params_with_duration = {**params, "duration": duration}
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(params_with_duration, f, ensure_ascii=False, indent=2)

    # Create temp media directory (absolute path for manim)
    media_dir = os.path.abspath(os.path.join(os.path.dirname(output_path), "_manim_media"))
    os.makedirs(media_dir, exist_ok=True)

    # Call manim render
    # Use filename only (not full path) since cwd is the templates directory
    cmd = [
        sys.executable,
        "-m",
        "manim",
        "render",
        "-qh",  # high quality (1080p) to match video resolution
        "--media_dir",
        media_dir,
        "--fps",
        str(fps),
        template_file,  # just filename, cwd handles the rest
        class_name,
    ]

    _render_t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_MANIM_TIMEOUT_S,
            cwd=abs_templates_dir,  # so `from style import ...` works
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            # Show enough error to diagnose
            stderr_lines = result.stderr.strip().split("\n")
            # Show last 5 lines (most useful part of traceback)
            err_summary = "\n      ".join(stderr_lines[-5:])
            print(f"\n    [WARN] Manim render failed:\n      {err_summary}")
            _record_manim_fallback(output_path, scene_id, f"render_failed_rc{result.returncode}")
            fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
            generate_text_overlay(fallback_visual, output_path, duration)
            return

        # Find output MP4 (Manim puts it in media_dir/videos/...)
        manim_output = _find_manim_output(media_dir, class_name)
        if not manim_output:
            print(f"\n    [WARN] Manim output not found in {media_dir}")
            _record_manim_fallback(output_path, scene_id, "output_not_found")
            fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
            generate_text_overlay(fallback_visual, output_path, duration)
            return

        # Adjust duration: pad or trim to match timing.json
        _adjust_duration(manim_output, output_path, duration, width, height, fps)

        # This scene rendered for real, so it is no longer a placeholder.
        _clear_manim_fallback(output_path, scene_id)

        # 強化 (b): 成功したが timeout 近傍 (>=70%) なら予兆警告。
        # この scene は次回 (FPS/解像度/尺の僅かな変動や環境負荷) で timeout
        # -> placeholder 化しうる。template 簡素化 (重い 3D primitive の削減等)
        # の余地を placeholder 化する前に可視化する。
        _render_elapsed = time.time() - _render_t0
        if _render_elapsed >= _MANIM_NEAR_TIMEOUT_FRAC * _MANIM_TIMEOUT_S:
            _pct = _render_elapsed / _MANIM_TIMEOUT_S * 100
            print(
                f"\n    [WARN] {scene_id}: Manim render {_render_elapsed:.0f}s "
                f"(timeout {_MANIM_TIMEOUT_S}s の {_pct:.0f}%) -> timeout 近傍。"
                f"僅かな負荷増で placeholder 化リスク。template 簡素化 "
                f"(重い 3D primitive / 長時間 Rotate の削減等) を推奨"
            )

    except subprocess.TimeoutExpired:
        print(f"\n    [WARN] Manim render timed out ({_MANIM_TIMEOUT_S}s)")
        _record_manim_fallback(output_path, scene_id, f"timeout_{_MANIM_TIMEOUT_S}s")
        fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
    finally:
        # Clean up params file
        if os.path.exists(params_path):
            os.remove(params_path)


def _find_manim_output(media_dir: str, class_name: str) -> str:
    """Find Manim's output MP4 file in the media directory tree."""
    for root, _dirs, files in os.walk(media_dir):
        for f in files:
            if f.endswith(".mp4") and class_name in f:
                return os.path.join(root, f)
    # Fallback: any MP4
    for root, _dirs, files in os.walk(media_dir):
        for f in files:
            if f.endswith(".mp4"):
                return os.path.join(root, f)
    return None


# [DEAD-AIR guard] When a rendered visual is shorter than its audio slot, _adjust_duration
# freeze-pads the last frame. A small pad (coda slack) is normal; a large one means the
# template could not fill the narration (e.g. reveal scale cap hit) -> excessive static tail.
# Advisory WARN only when the freeze-pad is BOTH long AND a big fraction of the scene, so it
# does NOT fire on an earlier episode (~12s/23%) / math_06 (~10s/19%) that shipped as accepted
# "held complete diagram during narration"; it fires only on worse under-fill.
_DEADAIR_PAD_MIN_S = 8.0
_DEADAIR_PAD_MIN_FRAC = 0.33
# Scenes that tripped the DEAD-AIR guard this run (for the ③ advisory roll-up).
_DEADAIR_HITS: list[str] = []


def _adjust_duration(
    input_path: str, output_path: str, target_duration: float, width: int, height: int, fps: int
):
    """Adjust video duration to match target: trim if longer, pad with freeze-frame if shorter.

    Wraps _adjust_duration_impl so an ffmpeg timeout during these (post-render,
    short-clip) fixups degrades to copying the un-adjusted render rather than
    hanging -- the render itself is already bounded by _MANIM_TIMEOUT_S.
    """
    import shutil

    try:
        _adjust_duration_impl(input_path, output_path, target_duration, width, height, fps)
    except _FFmpegTimeout as exc:
        print(f"    [WARN] {exc} -> keeping un-adjusted render")
        if os.path.abspath(input_path) != os.path.abspath(output_path):
            shutil.copy2(input_path, output_path)


def _adjust_duration_impl(
    input_path: str, output_path: str, target_duration: float, width: int, height: int, fps: int
):
    import shutil

    # Get input duration
    probe_cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        input_path,
    ]
    result = _run_ffmpeg_bounded(
        probe_cmd,
        timeout=_FFPROBE_TIMEOUT_S,
        label="adjust_duration probe",
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        probe_data = json.loads(result.stdout)
        actual_duration = float(probe_data["format"]["duration"])
    except (json.JSONDecodeError, KeyError):
        # Can't probe, just copy
        shutil.copy2(input_path, output_path)
        return

    tolerance = 0.5  # seconds

    if abs(actual_duration - target_duration) < tolerance:
        # Close enough, just scale to correct resolution
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            output_path,
        ]
        _run_ffmpeg_bounded(cmd, label="adjust_duration scale")

    elif actual_duration > target_duration:
        # Trim
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-t",
            str(target_duration),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            output_path,
        ]
        _run_ffmpeg_bounded(cmd, label="adjust_duration trim")

    else:
        # Pad: freeze last frame for remaining time
        pad_duration = target_duration - actual_duration
        _pad_frac = pad_duration / target_duration if target_duration > 0 else 0.0
        if pad_duration > _DEADAIR_PAD_MIN_S and _pad_frac > _DEADAIR_PAD_MIN_FRAC:
            _scene = os.path.splitext(os.path.basename(output_path))[0]
            _DEADAIR_HITS.append(_scene)
            print(
                f"  [WARN][DEAD-AIR] {_scene}: freeze-pad {pad_duration:.1f}s "
                f"({_pad_frac * 100:.0f}% of {target_duration:.1f}s) -- rendered visual is "
                f"shorter than its audio; likely excessive static tail. Narration may exceed "
                f"the template fill capacity (reveal scale cap) -- tighten narration or template."
            )
        # Extract last frame
        last_frame = input_path + "_lastframe.png"
        _run_ffmpeg_bounded(
            [
                "ffmpeg",
                "-y",
                "-sseof",
                "-0.1",
                "-i",
                input_path,
                "-frames:v",
                "1",
                last_frame,
            ],
            label="adjust_duration pad-extract",
        )

        if os.path.exists(last_frame):
            # Create freeze segment
            freeze_path = input_path + "_freeze.mp4"
            _run_ffmpeg_bounded(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    last_frame,
                    "-t",
                    str(pad_duration),
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    str(fps),
                    freeze_path,
                ],
                label="adjust_duration pad-freeze",
            )

            # Concatenate original + freeze
            concat_list = input_path + "_concat.txt"
            with open(concat_list, "w") as f:
                f.write(f"file '{os.path.abspath(input_path)}'\n")
                f.write(f"file '{os.path.abspath(freeze_path)}'\n")

            # Scale original first
            scaled = input_path + "_scaled.mp4"
            _run_ffmpeg_bounded(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path,
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-an",
                    scaled,
                ],
                label="adjust_duration pad-scale",
            )

            with open(concat_list, "w") as f:
                f.write(f"file '{os.path.abspath(scaled)}'\n")
                f.write(f"file '{os.path.abspath(freeze_path)}'\n")

            _run_ffmpeg_bounded(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list,
                    "-c",
                    "copy",
                    output_path,
                ],
                label="adjust_duration pad-concat",
            )

            # Cleanup temp files
            for tmp in [last_frame, freeze_path, concat_list, scaled]:
                if os.path.exists(tmp):
                    os.remove(tmp)
        else:
            # Fallback: just copy with scale
            shutil.copy2(input_path, output_path)


def _generate_stub_video(
    scene_id: str,
    label: str,
    duration: float,
    output_path: str,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate a placeholder video with colored background and label text.

    Used as fallback when Manim templates are not available.
    """
    from PIL import Image, ImageDraw, ImageFont

    total_frames = max(int(duration * fps), 1)

    # Distinct color for manim stubs
    bg = (0x2E, 0x1A, 0x3E)  # purple-ish dark

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        PIXEL_FORMAT,
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]

    # Create a single frame (static placeholder)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Draw label text
    font_path = find_font()
    try:
        font_large = ImageFont.truetype(font_path, 48) if font_path else ImageFont.load_default()
        font_small = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default()
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Scene ID
    text1 = "[MANIM STUB]"
    text2 = f"{scene_id}"
    text3 = f"template: {label}"
    text4 = f"duration: {duration:.1f}s"

    for i, (text, font, color) in enumerate(
        [
            (text1, font_large, ACCENT_PINK),
            (text2, font_large, ACCENT_GOLD),
            (text3, font_small, TEXT_DIM),
            (text4, font_small, TEXT_DIM),
        ]
    ):
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = height // 2 - 100 + i * 60
        draw.text((x, y), text, font=font, fill=color)

    frame_bytes = img.tobytes()

    # Bounded by the same watchdog as ken_burns: the stub shares the frame-pipe
    # deadlock risk and is itself a fallback, so it must not be able to hang.
    _pipe_frames_to_ffmpeg(
        cmd,
        (frame_bytes for _ in range(total_frames)),
        _FFMPEG_TIMEOUT_S,
        f"stub[{scene_id}]",
    )


def _generate_black_placeholder(
    output_path: str,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Last-resort placeholder via ffmpeg's lavfi color source.

    Unlike ken_burns/stub this feeds no stdin pipe, so it cannot hit the
    pipe-drain deadlock; it is the fallback used by process_scene when a
    frame-pipe encode times out or errors, guaranteeing the scene still has a
    valid (if blank) segment so assembly does not fail on a missing file.
    """
    dur = max(duration, 0.1)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=#1a1a2e:s={width}x{height}:d={dur:.3f}:r={fps}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]
    try:
        _run_ffmpeg_bounded(cmd, label=f"black_placeholder[{os.path.basename(output_path)}]")
    except _FFmpegError as exc:
        # Even the pipe-free fallback failed -- nothing more to degrade to.
        # Leave no/partial output; the caller's "output missing" check reports it.
        print(f"    [ERROR] {exc}")


# ===========================================================================
# Pillow chart (stub for Phase 1)
# ===========================================================================


def generate_pillow_chart(
    scene_id: str,
    visual: dict,
    output_path: str,
    duration: float,
    images_dir: str = None,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate chart visualization MP4.

    If visual.source exists, use that image with Ken Burns.
    Otherwise, generate chart from visual.data (Phase 2+).
    """
    source = visual.get("source")
    if source and images_dir:
        img_path = os.path.join(images_dir, source)
        if os.path.exists(img_path):
            generate_ken_burns(
                img_path,
                output_path,
                duration,
                effect="zoom_in",
                width=width,
                height=height,
                fps=fps,
            )
            return

    # Stub: placeholder
    _generate_stub_video(
        scene_id,
        f"chart:{visual.get('chart_type', '?')}",
        duration,
        output_path,
        width,
        height,
        fps,
    )


# route_map の描画・レイアウト検査・preflight はここにあったが、約 2,300 行あって
# ken_burns / text_overlay / manim と同居していたので route_map_render.py へ分割した
#。名前はこのモジュールの先頭で再輸出しているので呼び出し側は不変。


# ===========================================================================
# Blender 3D rendering
# ===========================================================================


def generate_blender(
    scene_id: str,
    visual: dict,
    output_path: str,
    duration: float,
    blender_templates_dir: str = None,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
):
    """Generate Blender 3D animation MP4.

    Discovers template from blender_templates_dir, passes params via JSON,
    calls Blender in headless mode. Falls back to text_overlay on failure.
    """
    from blender_renderer import discover_blender_templates, find_blender, render_blender_template

    template = visual.get("template", "")
    params = visual.get("params", {})

    if not blender_templates_dir or not os.path.isdir(blender_templates_dir):
        print("\n    [WARN] blender_templates dir not found, falling back to text_overlay.")
        fallback_visual = _blender_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    # Discover available templates
    template_map = discover_blender_templates(blender_templates_dir)

    if template not in template_map:
        print(
            f"\n    [WARN] Blender template '{template}' not found, falling back to text_overlay."
        )
        fallback_visual = _blender_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    template_file = template_map[template]
    template_path = os.path.join(blender_templates_dir, template_file)

    # Check Blender is available
    blender_exe = find_blender()
    if blender_exe is None:
        print("\n    [WARN] Blender not installed, falling back to text_overlay.")
        fallback_visual = _blender_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    success = render_blender_template(
        template_path=template_path,
        params=params,
        output_path=output_path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        blender_exe=blender_exe,
        timeout=600,
    )

    if not success:
        print("    [WARN] Blender render failed, falling back to text_overlay.")
        fallback_visual = _blender_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
        return

    # Duration adjustment (same as Manim)
    _adjust_duration(output_path, output_path, duration, width, height, fps)


def _blender_to_text_overlay_fallback(visual: dict, scene_id: str) -> dict:
    """Extract text from Blender visual params for text_overlay fallback."""
    params = visual.get("params", {})
    template = visual.get("template", "")

    main_text = params.get("title") or params.get("label") or params.get("description") or ""
    sub_text = params.get("subtitle", "")

    if not main_text:
        main_text = scene_id.replace("_", " ").title()
        sub_text = f"[blender: {template}]" if template else "[blender]"

    return {
        "type": "text_overlay",
        "style": "definition",
        "content": {"main": main_text, "sub": sub_text},
    }


# ===========================================================================
# Main dispatcher
# ===========================================================================


def process_scene(
    scene: dict,
    scene_duration: float,
    visuals_dir: str,
    images_dir: str,
    manim_templates_dir: str = None,
    skip_manim: bool = False,
    blender_templates_dir: str = None,
):
    """Process a single scene and generate its visual MP4 segment.

    Thin guard around _dispatch_scene_visual: a frame-pipe encode that times out
    or errors (ken_burns / stub, reached by every visual type that ends in Ken
    Burns -- text_overlay, route_map, pillow_chart too) is caught here and
    degraded to a recorded fallback marker + a pipe-free black placeholder,
    mirroring the Manim/Blender fallback path. The build keeps going, the failure
    is surfaced (not silent), and a stuck ffmpeg can no longer hang the whole
    pipeline.
    """
    scene_id = scene["scene_id"]
    visual = scene["visual"]
    vtype = visual["type"]
    output_path = os.path.join(visuals_dir, f"{scene_id}.mp4")

    try:
        _dispatch_scene_visual(
            scene,
            scene_duration,
            visuals_dir,
            images_dir,
            manim_templates_dir=manim_templates_dir,
            skip_manim=skip_manim,
            blender_templates_dir=blender_templates_dir,
        )
    except _FFmpegError as exc:
        reason = "ffmpeg_timeout" if isinstance(exc, _FFmpegTimeout) else "ffmpeg_error"
        print(f"\n    [ERROR] {scene_id} ({vtype}): {exc}")
        print(f"    [ERROR] -> fallback marker + black placeholder ({reason})")
        _record_manim_fallback(output_path, scene_id, f"{reason}:{vtype}")
        _generate_black_placeholder(output_path, scene_duration)


def _dispatch_scene_visual(
    scene: dict,
    scene_duration: float,
    visuals_dir: str,
    images_dir: str,
    manim_templates_dir: str = None,
    skip_manim: bool = False,
    blender_templates_dir: str = None,
):
    """Dispatch a scene to its per-type visual generator.

    No error handling here: process_scene wraps this and degrades ffmpeg-pipe
    failures (_FFmpegError / _FFmpegTimeout) to a placeholder.
    """
    scene_id = scene["scene_id"]
    visual = scene["visual"]
    vtype = visual["type"]
    output_path = os.path.join(visuals_dir, f"{scene_id}.mp4")

    if vtype == "ken_burns":
        source = visual.get("source")
        effect = visual.get("effect", "zoom_in")

        img_path = None
        if source:
            img_path = os.path.join(images_dir, source)
            if not os.path.exists(img_path):
                print(f"    [WARN] Image not found: {img_path}")
                img_path = None  # fall through to fallback

        # Fallback: try images/{scene_id}.png (image_generator auto-naming)
        if img_path is None:
            fallback = os.path.join(images_dir, f"{scene_id}.png")
            if os.path.exists(fallback):
                img_path = fallback
                print(f"    [ALIAS] Using fallback image: {scene_id}.png")

        if img_path is None:
            print("    [WARN] No source image found, stub created.")
            _generate_stub_video(scene_id, "needs_image_gen", scene_duration, output_path)
            return

        generate_ken_burns(img_path, output_path, scene_duration, effect=effect)

    elif vtype == "text_overlay":
        generate_text_overlay(visual, output_path, scene_duration)

    elif vtype == "manim":
        if skip_manim:
            # Use text_overlay fallback instead of purple stub
            fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
            generate_text_overlay(fallback_visual, output_path, scene_duration)
        else:
            generate_manim(
                scene_id,
                visual,
                output_path,
                scene_duration,
                manim_templates_dir=manim_templates_dir,
            )

    elif vtype == "pillow_chart":
        generate_pillow_chart(scene_id, visual, output_path, scene_duration, images_dir=images_dir)

    elif vtype == "route_map":
        generate_route_map(visual, output_path, scene_duration)

    elif vtype == "blender":
        generate_blender(
            scene_id,
            visual,
            output_path,
            scene_duration,
            blender_templates_dir=blender_templates_dir,
        )

    else:
        print(f"    [WARN] Unknown visual type: {vtype}, falling back to text_overlay.")
        fallback_visual = {
            "type": "text_overlay",
            "style": "fact",
            "content": {
                "main": scene_id.replace("_", " ").title(),
                "sub": f"[{vtype}]",
            },
        }
        generate_text_overlay(fallback_visual, output_path, scene_duration)


# ===========================================================================
# Phase 2: incremental visual rebuild (per-scene mp4 cache)
#
# Mirrors the audio per-sentence cache (audio_generator.py). A scene's mp4 is
# reused instead of re-rendered when nothing that affects its output changed.
# Key = CONTENT hash (never mtime): the visual block + scene duration + the
# render backend's external inputs (manim template .py + style.py, or the
# source image). The stale-visual preflight (pipeline.py, before assemble)
# is the backstop: any reused mp4 whose duration drifts from timing.json is
# caught there. Default-on; --force-regen-visuals bypasses; --scenes restricts.
# ===========================================================================

VISUAL_CACHE_FILE = "_visual_cache.json"


def _load_visual_cache(visuals_dir: str) -> dict:
    """Load the per-scene visual cache; return {} on a cold/corrupt cache."""
    path = os.path.join(visuals_dir, VISUAL_CACHE_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_visual_cache(visuals_dir: str, cache: dict) -> None:
    """Persist the visual cache (best-effort; never fails the build)."""
    path = os.path.join(visuals_dir, VISUAL_CACHE_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError as e:
        print(f"    [WARN] visual cache 保存失敗 (続行): {e}")


def _file_hash(path: str) -> str:
    """sha256[:16] of a file's bytes, or 'none' if unreadable."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "none"


def _file_fingerprint(path: str) -> str:
    """'{len}:{sha256[:16]}' of a file's bytes, or '' if unreadable.

    Used for the source-image key input and for detecting out-of-band mp4
    swaps/truncation (mirrors audio_generator._wav_fingerprint).
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        return f"{len(data)}:{hashlib.sha256(data).hexdigest()[:16]}"
    except OSError:
        return ""


def _resolve_manim_template_path(visual: dict, manim_templates_dir: str | None) -> str | None:
    """Resolve a manim scene's template .py path (alias-aware), or None.

    Mirrors the resolution in generate_manim() so the cache key hashes the same
    file that actually renders. None when unresolved (scene degrades to a
    text_overlay fallback → no template file involved).
    """
    if not manim_templates_dir or not os.path.isdir(manim_templates_dir):
        return None
    template = visual.get("template", "")
    tmap = discover_manim_templates(manim_templates_dir)
    resolved = template if template in tmap else TEMPLATE_ALIASES.get(template, template)
    if resolved not in tmap:
        return None
    template_file, _ = tmap[resolved]
    path = os.path.join(manim_templates_dir, template_file)
    return path if os.path.exists(path) else None


def _resolve_source_image(scene: dict, images_dir: str) -> str | None:
    """Resolve the source-image path for image-backed scenes, or None.

    Mirrors the ken_burns/pillow_chart source resolution in
    _dispatch_scene_visual (visual.source, else images/{scene_id}.png).
    """
    visual = scene.get("visual", {})
    if visual.get("type") not in ("ken_burns", "pillow_chart"):
        return None
    source = visual.get("source")
    if source:
        p = os.path.join(images_dir, source)
        if os.path.exists(p):
            return p
    fallback = os.path.join(images_dir, f"{scene.get('scene_id', '')}.png")
    return fallback if os.path.exists(fallback) else None


def _local_import_names(py_path: str) -> set:
    """Top-level module names imported by a .py file (for local-dep resolution)."""
    import ast as _ast

    try:
        with open(py_path, encoding="utf-8") as f:
            tree = _ast.parse(f.read())
    except (OSError, SyntaxError):
        return set()
    names = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom) and node.module and (node.level or 0) == 0:
            names.add(node.module.split(".")[0])
        elif isinstance(node, _ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
    return names


def _manim_render_deps(template_path: str, manim_templates_dir: str) -> list:
    """Local .py files a manim template's render depends on (for the cache key).

    Transitive closure within manim_templates_dir: the template itself + any
    sibling module it imports (e.g. hamiltonian_cycle imports polyhedron_euler)
    + the shared style.py. Editing any of them must invalidate dependent scenes,
    so all are hashed into the staleness key. Returns sorted absolute paths.
    """
    seen: set = set()
    stack = [template_path]
    while stack:
        p = stack.pop()
        if p in seen or not os.path.exists(p):
            continue
        seen.add(p)
        for name in _local_import_names(p):
            sib = os.path.join(manim_templates_dir, name + ".py")
            if os.path.exists(sib) and sib not in seen:
                stack.append(sib)
    style = os.path.join(manim_templates_dir, "style.py")
    if os.path.exists(style):
        seen.add(style)
    return sorted(seen)


def _visual_staleness_key(
    scene: dict,
    duration: float,
    manim_templates_dir: str | None,
    images_dir: str,
    skip_manim: bool = False,
) -> str:
    """Content hash (sha256[:16]) of everything that changes a scene's mp4.

    Inputs: the visual block (type/params/source/style/…), the scene duration
    (audio-cascade trigger), and the render backend's external files — for
    manim the template's local-dependency closure (template .py + imported
    sibling modules + shared style.py) (+ skip_manim, which swaps the real
    render for a text_overlay fallback); for image types the source-image
    fingerprint. A key mismatch => re-render.

    NOT tracked (use --force-regen-visuals after changing these): the renderer
    code in visual_generator.py itself, fonts, and non-.py assets.
    """
    visual = scene.get("visual", {})
    parts = [
        json.dumps(visual, sort_keys=True, ensure_ascii=False),
        f"dur={round(float(duration), 3)}",
    ]
    vtype = visual.get("type")
    if vtype == "manim":
        parts.append(f"skip_manim={bool(skip_manim)}")
        tpath = _resolve_manim_template_path(visual, manim_templates_dir)
        if tpath:
            # Hash the template's full local-dependency closure so editing a
            # shared module (e.g. polyhedron_euler, style) invalidates dependents.
            for dep in _manim_render_deps(tpath, manim_templates_dir):
                parts.append(f"dep:{os.path.basename(dep)}={_file_hash(dep)}")
        else:
            parts.append("tmpl=none")
    elif vtype in ("ken_burns", "pillow_chart"):
        img = _resolve_source_image(scene, images_dir)
        parts.append("img=" + (_file_fingerprint(img) if img else "none"))
    payload = "\x00".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _visual_cache_entry_matches(cache: dict | None, scene_id: str, key: str, mp4_path: str) -> bool:
    """True iff the cached entry, the on-disk mp4, and the current key agree.

    Requires cache present, entry exists, stored key == key, mp4 exists, and
    (for new-format entries) the mp4 fingerprint matches — so an out-of-band
    mp4 swap/truncation is a miss (mirrors _cache_entry_matches).
    """
    if cache is None:
        return False
    entry = cache.get(scene_id)
    if not entry:
        return False
    stored_key = entry.get("key") if isinstance(entry, dict) else entry
    if stored_key != key:
        return False
    if not os.path.exists(mp4_path):
        return False
    stored_fp = entry.get("mp4") if isinstance(entry, dict) else None
    if stored_fp is not None:
        return _file_fingerprint(mp4_path) == stored_fp
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate visual segments from scene_definition.json + timing.json"
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument("timing_json", help="Path to timing.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument(
        "--images-dir",
        default=None,
        help="Directory containing source images (default: {output_dir}/images)",
    )
    parser.add_argument(
        "--manim-templates", default=None, help="Directory containing Manim templates"
    )
    parser.add_argument(
        "--skip-manim", action="store_true", help="Generate stubs instead of Manim rendering"
    )
    parser.add_argument(
        "--blender-templates", default=None, help="Directory containing Blender templates"
    )
    parser.add_argument(
        "--scenes",
        default=None,
        help="comma-separated scene_ids to (re-)render; other scenes keep "
        "their existing mp4 untouched. Omit to consider all scenes.",
    )
    parser.add_argument(
        "--force-regen-visuals",
        action="store_true",
        help="ignore the per-scene visual cache and re-render every "
        "in-scope scene (the cache is still refreshed afterwards).",
    )
    args = parser.parse_args()

    # Load data
    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)
    with open(args.timing_json, encoding="utf-8") as f:
        timing = json.load(f)

    # Setup directories
    visuals_dir = os.path.join(args.output_dir, "visuals")
    images_dir = args.images_dir or os.path.join(args.output_dir, "images")
    os.makedirs(visuals_dir, exist_ok=True)

    # Check FFmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("ERROR: FFmpeg not found in PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: FFmpeg did not respond to -version within 30s")
        sys.exit(1)

    # Check Pillow
    try:
        from PIL import Image  # noqa: F401  (import presence-check only)
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow")
        sys.exit(1)

    # Font check
    font = find_font()
    if font:
        print(f"Font: {font}")
    else:
        print("[WARN] BIZ UDMincho not found. Text overlays will use default font.")

    # Manim templates directory
    if args.manim_templates:
        manim_dir = args.manim_templates
    else:
        # Default: src/manim_templates/ relative to this script
        manim_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manim_templates")
    if os.path.isdir(manim_dir):
        print(f"Manim templates: {manim_dir}")
    else:
        print(f"[WARN] Manim templates dir not found: {manim_dir}")
        print("   Manim scenes will use stubs unless --skip-manim is specified.")
        manim_dir = None

    # Blender templates directory
    if args.blender_templates:
        blender_dir = args.blender_templates
    else:
        blender_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_templates")
    if os.path.isdir(blender_dir):
        print(f"Blender templates: {blender_dir}")
    else:
        blender_dir = None  # No warning: Blender templates are optional

    # Process all scenes
    stats = {
        "ken_burns": 0,
        "text_overlay": 0,
        "manim": 0,
        "blender": 0,
        "route_map": 0,
        "pillow_chart": 0,
        "stub": 0,
    }
    total_duration = 0.0

    # Phase 2: incremental rebuild (default-on). Reuse an unchanged scene's
    # mp4 instead of re-rendering. --scenes limits which scenes are considered;
    # --force-regen-visuals bypasses the cache. The whole cache dict is loaded,
    # mutated only for in-scope re-rendered scenes, and saved back — so reused
    # and out-of-scope (--scenes) scenes keep their prior entries.
    visual_cache = _load_visual_cache(visuals_dir)
    scene_filter = None
    if args.scenes:
        scene_filter = {s.strip() for s in args.scenes.split(",") if s.strip()}
        print(f"--scenes: {sorted(scene_filter)} のみ対象 (他は既存 mp4 を保持)")
    if args.force_regen_visuals:
        print
    reused = 0
    rendered = 0
    kept = 0  # out-of-scope (--scenes) scenes left untouched

    for section in scene_def["sections"]:
        section_id = section["section_id"]
        print(f"\n=== Section: {section_id} ===")

        for scene in section["scenes"]:
            scene_id = scene["scene_id"]
            vtype = scene["visual"]["type"]

            # Get duration from timing.json
            scene_timing = timing["scenes"].get(scene_id, {})
            duration = scene_timing.get("duration", 5.0)  # fallback 5s
            total_duration += duration

            output_file = os.path.join(visuals_dir, f"{scene_id}.mp4")

            # --scenes: out-of-scope scenes keep their existing mp4 (and cache
            # entry) untouched, but are still counted so assemble sees them.
            if scene_filter is not None and scene_id not in scene_filter:
                stats[vtype] = stats.get(vtype, 0) + 1
                kept += 1
                miss = "" if os.path.exists(output_file) else " (mp4 無し!)"
                print(f"  {scene_id} ({vtype}, {duration:.1f}s)... [KEEP]{miss}")
                continue

            # cache reuse decision (content key + on-disk mp4 fingerprint).
            key = _visual_staleness_key(
                scene, duration, manim_dir, images_dir, skip_manim=args.skip_manim
            )
            if not args.force_regen_visuals and _visual_cache_entry_matches(
                visual_cache, scene_id, key, output_file
            ):
                stats[vtype] = stats.get(vtype, 0) + 1
                reused += 1
                size_kb = os.path.getsize(output_file) / 1024
                print(f"  {scene_id} ({vtype}, {duration:.1f}s)... [REUSE] ({size_kb:.0f}KB)")
                continue

            print(f"  {scene_id} ({vtype}, {duration:.1f}s)...", end=" ", flush=True)
            start_time = time.time()

            process_scene(
                scene,
                duration,
                visuals_dir,
                images_dir,
                manim_templates_dir=manim_dir,
                skip_manim=args.skip_manim,
                blender_templates_dir=blender_dir,
            )

            elapsed = time.time() - start_time
            stats[vtype] = stats.get(vtype, 0) + 1

            if os.path.exists(output_file):
                size_kb = os.path.getsize(output_file) / 1024
                print(f"[OK] ({elapsed:.1f}s, {size_kb:.0f}KB)")
                rendered += 1
                # Record the render we just produced (content key + fingerprint).
                visual_cache[scene_id] = {"key": key, "mp4": _file_fingerprint(output_file)}
            else:
                print("[NG] output missing")
                stats["stub"] = stats.get("stub", 0) + 1
                # Drop any stale entry so a later run re-renders rather than
                # trusting a vanished mp4.
                visual_cache.pop(scene_id, None)

    # Persist the cache (best-effort). Reused / out-of-scope entries are kept.
    _save_visual_cache(visuals_dir, visual_cache)

    # Summary
    print(f"\n{'=' * 50}")
    print("Visual generation complete")
    print(f"  Total scenes:  {sum(stats.values())}")
    reuse_line = f"  Rendered: {rendered}  Reused (cache): {reused}"
    if scene_filter is not None:
        reuse_line += f"  Kept (--scenes): {kept}"
    print(reuse_line)
    print(f"  Total duration: {total_duration:.1f}s ({total_duration / 60:.1f} min)")
    for vtype, count in stats.items():
        if count > 0:
            print(f"  {vtype:15s}: {count}")
    print(f"  Output dir:    {visuals_dir}")

    if args.skip_manim:
        print("\n  Note: Manim scenes are stubs (--skip-manim). Run without flag for full render.")


# ===========================================================================
# Partial rebuild: single-scene visual regeneration
# ===========================================================================


def rebuild_single_scene_visual(
    scene_json_path: str,
    timing_json_path: str,
    scene_id: str,
    output_dir: str,
    manim_templates_dir: str = None,
) -> bool:
    """Rebuild visual for a single scene.

    This function is called by pipeline.py's --rebuild-scene mode.
    It does NOT modify the existing full-build code path.

    Steps:
      1. Load scene_definition.json, find the target scene
      2. Load timing.json, get the target scene's duration
      3. Delete existing visuals/{scene_id}.mp4
      4. Call process_scene() for the target scene only
      5. Update the visual cache for this scene (keeps a later full build
         from reusing a stale mp4)

    Returns True on success.
    """
    # Load data
    with open(scene_json_path, encoding="utf-8") as f:
        scene_def = json.load(f)
    with open(timing_json_path, encoding="utf-8") as f:
        timing = json.load(f)

    # Find target scene
    target_scene = None
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            if scene["scene_id"] == scene_id:
                target_scene = scene
                break
        if target_scene:
            break

    if target_scene is None:
        print(f"[PARTIAL REBUILD] ERROR: Scene '{scene_id}' not found in scene_definition.json")
        return False

    # Get duration from timing.json
    scene_timing = timing.get("scenes", {}).get(scene_id, {})
    duration = scene_timing.get("duration", 5.0)

    # Setup directories
    visuals_dir = os.path.join(output_dir, "visuals")
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(visuals_dir, exist_ok=True)

    # Resolve manim templates directory
    if manim_templates_dir is None:
        manim_templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "manim_templates"
        )
    if not os.path.isdir(manim_templates_dir):
        manim_templates_dir = None

    # Resolve blender templates directory
    blender_templates_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "blender_templates"
    )
    if not os.path.isdir(blender_templates_dir):
        blender_templates_dir = None

    # Delete existing visual for this scene
    output_path = os.path.join(visuals_dir, f"{scene_id}.mp4")
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"[PARTIAL REBUILD] Deleted existing: {output_path}")

    # Generate visual
    vtype = target_scene["visual"]["type"]
    print(f"[PARTIAL REBUILD] Generating visual: {scene_id} ({vtype}, {duration:.1f}s)...")

    start_time = time.time()
    process_scene(
        target_scene,
        duration,
        visuals_dir,
        images_dir,
        manim_templates_dir=manim_templates_dir,
        skip_manim=False,
        blender_templates_dir=blender_templates_dir,
    )
    elapsed = time.time() - start_time

    # keep the visual cache consistent so a later full build cannot reuse
    # a stale mp4 (or, on failure, skip re-rendering this scene). Load-update-save
    # the whole cache, mirroring audio_generator.rebuild_single_scene_audio.
    visual_cache = _load_visual_cache(visuals_dir)
    if os.path.exists(output_path):
        key = _visual_staleness_key(
            target_scene, duration, manim_templates_dir, images_dir, skip_manim=False
        )
        visual_cache[scene_id] = {"key": key, "mp4": _file_fingerprint(output_path)}
    else:
        visual_cache.pop(scene_id, None)
    _save_visual_cache(visuals_dir, visual_cache)

    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[PARTIAL REBUILD] Visual rebuilt: {scene_id} ({elapsed:.1f}s, {size_kb:.0f}KB)")
        return True
    else:
        print(f"[PARTIAL REBUILD] ERROR: Visual output not created: {output_path}")
        return False


if __name__ == "__main__":
    main()
    # ③ advisory roll-up: surface DEAD-AIR guard hits to the pipeline summary via
    # the X3 stderr channel (no-op unless run under the pipeline with hits).
    if _DEADAIR_HITS:
        try:
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("dead-air", len(_DEADAIR_HITS))
        except Exception:
            pass
