"""
visual_generator.py - Generate visual MP4 segments for each scene

Usage:
    python visual_generator.py scene_definition.json timing.json --output-dir episodes/001_erdos
    python visual_generator.py scene_definition.json timing.json --output-dir episodes/001_erdos --skip-manim

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
import json
import os
import subprocess
import sys
import time

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

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

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
        frame = img.resize((width, height), Image.LANCZOS, box=(cx, cy, cx + crop_w, cy + crop_h))
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()


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
        """Wrap text to fit within max_width."""
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
        return lines

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
        y_main_start = y
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

    Day 20 ある回 で pascals_triangle.binomial_highlight + probability_link
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

    # Alias mapping: generic names → closest match in available templates
    # Only generic aliases that make sense regardless of episode
    TEMPLATE_ALIASES = {
        "graph_coloring": "random_graph_coloring",
        "coloring": "random_graph_coloring",
        "world_map": "route_map",
        "travel_map": "route_map",
    }

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

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,
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

    except subprocess.TimeoutExpired:
        print("\n    [WARN] Manim render timed out (240s)")
        _record_manim_fallback(output_path, scene_id, "timeout_240s")
        fallback_visual = _manim_to_text_overlay_fallback(visual, scene_id)
        generate_text_overlay(fallback_visual, output_path, duration)
    finally:
        # Clean up params file
        if os.path.exists(params_path):
            os.remove(params_path)


def _find_manim_output(media_dir: str, class_name: str) -> str:
    """Find Manim's output MP4 file in the media directory tree."""
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            if f.endswith(".mp4") and class_name in f:
                return os.path.join(root, f)
    # Fallback: any MP4
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            if f.endswith(".mp4"):
                return os.path.join(root, f)
    return None


def _adjust_duration(
    input_path: str, output_path: str, target_duration: float, width: int, height: int, fps: int
):
    """Adjust video duration to match target: trim if longer, pad with freeze-frame if shorter."""
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
    result = subprocess.run(
        probe_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
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
        subprocess.run(cmd, capture_output=True)

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
        subprocess.run(cmd, capture_output=True)

    else:
        # Pad: freeze last frame for remaining time
        pad_duration = target_duration - actual_duration
        # Extract last frame
        last_frame = input_path + "_lastframe.png"
        subprocess.run(
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
            capture_output=True,
        )

        if os.path.exists(last_frame):
            # Create freeze segment
            freeze_path = input_path + "_freeze.mp4"
            subprocess.run(
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
                capture_output=True,
            )

            # Concatenate original + freeze
            concat_list = input_path + "_concat.txt"
            with open(concat_list, "w") as f:
                f.write(f"file '{os.path.abspath(input_path)}'\n")
                f.write(f"file '{os.path.abspath(freeze_path)}'\n")

            # Scale original first
            scaled = input_path + "_scaled.mp4"
            subprocess.run(
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
                capture_output=True,
            )

            with open(concat_list, "w") as f:
                f.write(f"file '{os.path.abspath(scaled)}'\n")
                f.write(f"file '{os.path.abspath(freeze_path)}'\n")

            subprocess.run(
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
                capture_output=True,
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

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

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

    for _ in range(total_frames):
        proc.stdin.write(frame_bytes)

    proc.stdin.close()
    proc.wait()


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


# ===========================================================================
# Route map (matplotlib + Natural Earth)
# ===========================================================================

# Natural Earth GeoJSON for world map polygons
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)

# Color mapping for route categories
_ROUTE_CATEGORY_COLORS = {
    "origin": "#e2b714",  # ACCENT_GOLD — 生誕地・出発点
    "education": "#7bc8f6",  # ライトブルー — 留学・進学
    "career": "#4cc9f0",  # ACCENT_CYAN — 職務・研究赴任
    "wandering": "#f72585",  # ACCENT_PINK — 放浪・旅
    "exile": "#c792ea",  # ライトパープル — 亡命・追放
    "final": "#aaaabb",  # TEXT_DIM — 最期の地
}

# Default map bounds (Europe + North America east coast + Middle East)
_DEFAULT_BOUNDS = {"lon": [-85, 45], "lat": [20, 65]}


def _get_geojson_cache_dir() -> str:
    """Return cache directory for Natural Earth data, next to this script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _download_natural_earth() -> str:
    """Download Natural Earth GeoJSON if not cached. Returns path to file."""
    cache_dir = _get_geojson_cache_dir()
    cache_file = os.path.join(cache_dir, "ne_110m_countries.geojson")

    if os.path.exists(cache_file):
        return cache_file

    os.makedirs(cache_dir, exist_ok=True)
    print("\n    [DL] Downloading Natural Earth data...")
    import urllib.request

    urllib.request.urlretrieve(_GEOJSON_URL, cache_file)
    print(f"    [DL] Saved: {cache_file}")
    return cache_file


def _load_geojson_polygons(cache_file: str) -> list:
    """Load GeoJSON and return list of polygon coordinate arrays."""
    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)

    polygons = []
    for feature in data["features"]:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                polygons.append(ring)
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                for ring in polygon:
                    polygons.append(ring)
    return polygons


def _check_route_map_collisions(
    fig, title_artist, route_label_artists, legend, city_label_artists=None
) -> list[dict]:
    """Detect title/route_label/legend/city_label bbox overlaps after layout (B-11).

    Calls fig.canvas.draw() to materialize layout, gets pixel-space bboxes via
    get_window_extent(renderer), and checks pairwise overlap. Returns a list of
    collision reports; empty list means clean.

    Each report: {
        "type": "title_vs_route_label" | "title_vs_legend" | "route_label_vs_legend"
                 | "route_label_vs_route_label" | "city_label_vs_route_label"
                 | "city_label_vs_city_label",
        "summary": "<human readable>",
        "overlap_px": (dx, dy),
        "suggestion": "<concrete fix proposal>",
    }

    B-11 E: city_label vs route_label and city_label vs city_label
    were previously unchecked — a displaced route label could land on a city name
    (or two clustered city names overlap) and slip past preflight. Now covered.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def _bbox(artist):
        if artist is None:
            return None
        try:
            return artist.get_window_extent(renderer=renderer)
        except Exception:
            return None

    def _overlap(a, b):
        """Return (dx, dy) overlap in pixels, or None if disjoint."""
        if a is None or b is None:
            return None
        dx = min(a.x1, b.x1) - max(a.x0, b.x0)
        dy = min(a.y1, b.y1) - max(a.y0, b.y0)
        if dx > 0 and dy > 0:
            return (dx, dy)
        return None

    title_bbox = _bbox(title_artist)
    legend_bbox = _bbox(legend)
    route_bboxes = [(a, _bbox(a)) for a in route_label_artists]

    reports = []

    if title_bbox is not None:
        for artist, bbox in route_bboxes:
            ov = _overlap(title_bbox, bbox)
            if ov is None:
                continue
            label_text = artist.get_text() if artist is not None else "?"
            reports.append(
                {
                    "type": "title_vs_route_label",
                    "summary": f"title overlaps route_label '{label_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Expand bounds.lat[1] upward, shorten title, "
                    "or move the route segment to a lower latitude.",
                }
            )

    if title_bbox is not None and legend_bbox is not None:
        ov = _overlap(title_bbox, legend_bbox)
        if ov is not None:
            reports.append(
                {
                    "type": "title_vs_legend",
                    "summary": f"title overlaps legend ({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Set legend_loc to 'lower right' / 'lower left', "
                    "or shorten the title.",
                }
            )

    if legend_bbox is not None:
        for artist, bbox in route_bboxes:
            ov = _overlap(legend_bbox, bbox)
            if ov is None:
                continue
            label_text = artist.get_text() if artist is not None else "?"
            reports.append(
                {
                    "type": "route_label_vs_legend",
                    "summary": f"legend overlaps route_label '{label_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Move legend to opposite corner via legend_loc / "
                    "legend_bbox_to_anchor.",
                }
            )

    # B-11 D: route_label vs route_label (pairwise) — closes preflight gap
    # where two adjacent route labels cluster around a shared pivot city.
    for i in range(len(route_bboxes)):
        for j in range(i + 1, len(route_bboxes)):
            artist_i, bbox_i = route_bboxes[i]
            artist_j, bbox_j = route_bboxes[j]
            ov = _overlap(bbox_i, bbox_j)
            if ov is None:
                continue
            text_i = artist_i.get_text() if artist_i is not None else "?"
            text_j = artist_j.get_text() if artist_j is not None else "?"
            reports.append(
                {
                    "type": "route_label_vs_route_label",
                    "summary": f"route_label '{text_i}' overlaps '{text_j}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Shorten one of the labels, drop one route, "
                    "or set both year and label of one route to empty string.",
                }
            )

    # B-11 E: city_label vs route_label / city_label vs city_label.
    # A displaced route label can land on a city name, or two clustered city
    # names can overlap — both previously slipped past preflight.
    # Require a meaningful 2D overlap (>=4px each way). bbox edges that merely
    # touch (e.g. a city name 1px under a route label) are not a real collision
    #. Real collisions overlap by
    # most of the label height.
    _min_ov = 4
    city_bboxes = [(a, _bbox(a)) for a in (city_label_artists or [])]
    for c_artist, c_bbox in city_bboxes:
        c_text = c_artist.get_text() if c_artist is not None else "?"
        for r_artist, r_bbox in route_bboxes:
            ov = _overlap(c_bbox, r_bbox)
            if ov is None or ov[0] < _min_ov or ov[1] < _min_ov:
                continue
            r_text = r_artist.get_text() if r_artist is not None else "?"
            reports.append(
                {
                    "type": "city_label_vs_route_label",
                    "summary": f"city '{c_text}' overlaps route_label '{r_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Move the route label via that route step's "
                    "'label_offset' [dlon, dlat], or move the city label via "
                    "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}.",
                }
            )
    for i in range(len(city_bboxes)):
        for j in range(i + 1, len(city_bboxes)):
            a_artist, a_bbox = city_bboxes[i]
            b_artist, b_bbox = city_bboxes[j]
            ov = _overlap(a_bbox, b_bbox)
            if ov is None or ov[0] < _min_ov or ov[1] < _min_ov:
                continue
            a_text = a_artist.get_text() if a_artist is not None else "?"
            b_text = b_artist.get_text() if b_artist is not None else "?"
            reports.append(
                {
                    "type": "city_label_vs_city_label",
                    "summary": f"city '{a_text}' overlaps city '{b_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Separate clustered city labels via "
                    "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}.",
                }
            )

    return reports


def generate_route_map(
    visual: dict,
    output_path: str,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    preflight_only: bool = False,
) -> list[dict]:
    """Generate route map visualization as MP4 (or run preflight only).

    When preflight_only=True, the figure is built and collision-checked but not
    saved (no PNG, no Ken Burns). Returns the collision reports list. Use this
    from B-11 preflight to detect title/label/legend overlaps before running
    expensive downstream steps.

    Returns:
        list of collision report dicts (empty if no collision detected). For
        the normal path (preflight_only=False), the return value is informational
        only (the function's primary effect is writing output_path).
    """
    """Generate route map visualization as MP4.

    Renders a world map with cities and travel routes using matplotlib,
    saves as temp PNG, then applies Ken Burns effect for video output.

    Visual spec:
        {
            "type": "route_map",
            "title": "エルデシュの旅路（1913–1996）",
            "cities": {
                "ブダペスト": [19.04, 47.50],
                "マンチェスター": [-2.24, 53.48],
                ...
            },
            "route": [
                {"from": "ブダペスト", "to": "マンチェスター",
                 "year": "1934", "label": "ハンガリーを離れる",
                 "category": "exile"}
            ],
            "bounds": {"lon": [-85, 45], "lat": [20, 65]},  // optional, auto-calculated from cities
            "effect": "zoom_in"  // optional, default zoom_in
        }
    """
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    # Extract params from visual spec
    title = visual.get("title", "")
    cities = visual.get("cities", {})
    route = visual.get("route", [])
    bounds = visual.get("bounds", None)
    effect = visual.get("effect", "zoom_in")

    # Style constants (hex for matplotlib)
    bg_hex = "#1a1a2e"
    land_color = "#2a2a4e"
    land_edge = "#3a3a5e"
    line_color = "#50507a"
    gold_hex = "#e2b714"
    white_hex = "#ffffff"

    # Auto-calculate bounds from city coordinates if not specified
    if bounds is None and cities:
        lons = [coord[0] for coord in cities.values()]
        lats = [coord[1] for coord in cities.values()]
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        # Add padding (20% of range, minimum 5 degrees)
        lon_pad = max((lon_max - lon_min) * 0.20, 5)
        lat_pad = max((lat_max - lat_min) * 0.20, 4)
        bounds = {
            "lon": [lon_min - lon_pad, lon_max + lon_pad],
            "lat": [lat_min - lat_pad, lat_max + lat_pad],
        }
    elif bounds is None:
        bounds = _DEFAULT_BOUNDS

    # Style constants (hex for matplotlib)
    bg_hex = "#1a1a2e"
    land_color = "#2a2a4e"
    land_edge = "#3a3a5e"
    line_color = "#50507a"
    gold_hex = "#e2b714"
    white_hex = "#ffffff"

    # Load map data
    try:
        cache_file = _download_natural_earth()
        polygons = _load_geojson_polygons(cache_file)
    except Exception as e:
        print(f"\n    [WARN] Failed to load map data: {e}")
        print("    Falling back to text_overlay.")
        fallback = {
            "type": "text_overlay",
            "style": "definition",
            "content": {"main": title or "Route Map", "sub": ""},
        }
        generate_text_overlay(fallback, output_path, duration)
        return

    # Find font for Japanese text
    font_path = find_font()
    font_props = {}
    if font_path:
        from matplotlib.font_manager import FontProperties

        font_props = {"fontproperties": FontProperties(fname=font_path)}

    # Create figure (16:9, high DPI)
    fig, ax = plt.subplots(1, 1, figsize=(16, 9), facecolor=bg_hex)
    ax.set_facecolor(bg_hex)

    # Set map bounds — do NOT use aspect="equal" (wastes space on 16:9)
    lon_range = bounds.get("lon", _DEFAULT_BOUNDS["lon"])
    lat_range = bounds.get("lat", _DEFAULT_BOUNDS["lat"])
    ax.set_xlim(lon_range)
    ax.set_ylim(lat_range)

    # Draw country polygons
    for ring in polygons:
        coords = np.array(ring)
        ax.fill(
            coords[:, 0],
            coords[:, 1],
            facecolor=land_color,
            edgecolor=land_edge,
            linewidth=0.5,
            zorder=1,
        )

    # Grid lines (subtle)
    for lat in range(int(lat_range[0]), int(lat_range[1]) + 1, 10):
        ax.axhline(lat, color=line_color, linewidth=0.3, alpha=0.3, zorder=0)
    for lon in range(int(lon_range[0]), int(lon_range[1]) + 1, 10):
        ax.axvline(lon, color=line_color, linewidth=0.3, alpha=0.3, zorder=0)

    # Scale factor for label offsets based on map extent
    lon_span = lon_range[1] - lon_range[0]
    lat_span = lat_range[1] - lat_range[0]

    # Draw route arrows
    legend_categories = set()
    route_labels = []

    for i_step, step in enumerate(route):
        from_city = step.get("from", "")
        to_city = step.get("to", "")
        category = step.get("category", "wandering")
        color = _ROUTE_CATEGORY_COLORS.get(category, "#4cc9f0")
        legend_categories.add(category)

        if from_city not in cities or to_city not in cities:
            continue

        sx, sy = cities[from_city]
        ex, ey = cities[to_city]

        # Bezier curve — alternate direction to spread overlapping routes
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        dist = np.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        curve_height = dist * 0.12
        direction = 1 if i_step % 2 == 0 else -1
        cx, cy = mx, my + curve_height * direction

        t = np.linspace(0, 1, 50)
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t**2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t**2 * ey

        ax.plot(bx, by, color=color, linewidth=3, alpha=0.8, zorder=3)
        ax.annotate(
            "",
            xy=(ex, ey),
            xytext=(bx[-3], by[-3]),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=3, mutation_scale=15),
            zorder=3,
        )

        # Place label ON the curve at varying t values (B-11 B fix).
        # Store curve params so placement loop can compute (Bx,By) at any t,
        # preserving visual correspondence between label and its own arc.
        year = step.get("year", "")
        label = step.get("label", "")
        if year or label:
            label_text = f"{year} {label}" if year and label else (year or label)
            route_labels.append(
                {
                    "sx": sx,
                    "sy": sy,
                    "cx": cx,
                    "cy": cy,
                    "ex": ex,
                    "ey": ey,
                    "direction": direction,
                    "curve_height": curve_height,
                    "text": label_text,
                    "color": color,
                    "label_offset": step.get("label_offset"),
                }
            )

    # Determine approximate legend bbox in data coords so that city labels
    # can avoid placing themselves under the legend.
    legend_loc = visual.get("legend_loc", "upper right")
    legend_bbox = tuple(visual.get("legend_bbox_to_anchor", [0.92, 0.98]))
    # Rough estimate based on 6 possible items × 18pt fontsize
    _legend_n = len(legend_categories) if legend_categories else 1
    _leg_w_ax = 0.18
    _leg_h_ax = 0.05 + 0.055 * _legend_n
    if "right" in legend_loc:
        _leg_x0_ax = legend_bbox[0] - _leg_w_ax
    else:
        _leg_x0_ax = legend_bbox[0]
    if "upper" in legend_loc:
        _leg_y1_ax = legend_bbox[1]
        _leg_y0_ax = _leg_y1_ax - _leg_h_ax
    else:
        _leg_y0_ax = legend_bbox[1]
        _leg_y1_ax = _leg_y0_ax + _leg_h_ax
    legend_rect_data = (
        lon_range[0] + _leg_x0_ax * lon_span,
        lat_range[0] + _leg_y0_ax * lat_span,
        lon_range[0] + (_leg_x0_ax + _leg_w_ax) * lon_span,
        lat_range[0] + _leg_y1_ax * lat_span,
    )

    def _in_legend(x, y):
        x0, y0, x1, y1 = legend_rect_data
        return x0 <= x <= x1 and y0 <= y <= y1

    # Draw city dots and labels FIRST (so we can track positions for route label collision)
    city_list = list(cities.items())
    placed_labels = []  # track (x, y) of placed label centers for collision avoidance
    placed_label_bboxes = []  # track (x0, y0, x1, y1) for tighter collision
    city_label_artists = []  # B-11 E: track city-label artists for collision check
    # Per-city label position override (Day 21 ある回 で追加 — auto-placement だと
    # 日本語長名 (ゲッティンゲン等) が canvas 端で clipping。scene_def の
    # visual.city_offsets = {city_name: [x_off_pts, y_off_pts, ha]} で固定 placement。
    # ha は "left" | "right" | "center"、省略時 "left"。auto candidates を skip。
    city_offsets_override = visual.get("city_offsets", {}) or {}

    def _estimate_label_w_deg(text: str, fontsize_pt: float, pts_per_lon_local: float) -> float:
        """Estimate rendered text width in longitude degrees.

        Japanese chars are ~1em (full-width); ASCII chars ~0.55em.
        """
        width_pts = 0.0
        for ch in text:
            width_pts += fontsize_pt * (0.55 if ch.isascii() else 1.05)
        return width_pts / pts_per_lon_local

    def _label_bbox(cx, cy, w, h, ha):
        """Return (x0, y0, x1, y1) in data coords for a label anchored at
        (cx, cy) with width w and height h. ha selects horizontal anchor.
        """
        if ha == "left":
            x0, x1 = cx, cx + w
        elif ha == "right":
            x0, x1 = cx - w, cx
        else:
            x0, x1 = cx - w / 2, cx + w / 2
        return (x0, cy - h / 2, x1, cy + h / 2)

    def _bboxes_overlap(a, b):
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

    for idx, (city_name, (lon, lat)) in enumerate(city_list):
        ax.plot(
            lon,
            lat,
            "o",
            color=gold_hex,
            markersize=14,
            zorder=5,
            markeredgecolor=bg_hex,
            markeredgewidth=2,
        )

        # Smart label offset with collision avoidance.
        # Tries near + far offsets × 4 corners + center, to handle clustered cities.
        candidates = [
            (12, -18, "left"),  # below-right
            (12, 14, "left"),  # above-right
            (-12, -18, "right"),  # below-left
            (-12, 14, "right"),  # above-left
            (0, 22, "center"),  # above-center
            (0, -24, "center"),  # below-center
            # Extra far offsets for dense clusters
            (12, -38, "left"),  # far below-right
            (12, 34, "left"),  # far above-right
            (-12, -38, "right"),  # far below-left
            (-12, 34, "right"),  # far above-left
            (0, 42, "center"),  # far above-center
            (0, -44, "center"),  # far below-center
        ]

        # Prefer placement away from map center
        map_cx = (lon_range[0] + lon_range[1]) / 2
        map_cy = (lat_range[0] + lat_range[1]) / 2
        preferred_x = 1 if lon >= map_cx else -1
        preferred_y = -1 if lat >= map_cy else 1

        # Sort candidates by preference
        def _score_candidate(c):
            xo, yo, _ = c
            return -(xo * preferred_x + yo * preferred_y * 0.5)

        candidates.sort(key=_score_candidate)

        # Convert offset points to data coordinates for collision check
        pts_per_lon = fig.get_size_inches()[0] * fig.dpi / lon_span
        pts_per_lat = fig.get_size_inches()[1] * fig.dpi / lat_span

        # Per-label width estimate (Japanese full-width vs ASCII narrower)
        label_w_deg = _estimate_label_w_deg(city_name, 18, pts_per_lon)
        label_h_deg = 22 / pts_per_lat  # ~22pt vertical extent incl. padding

        # Day 21 ある回: per-city manual override (skip auto-placement)
        if city_name in city_offsets_override:
            ov = city_offsets_override[city_name]
            ov_x, ov_y = float(ov[0]), float(ov[1])
            ov_ha = ov[2] if len(ov) >= 3 else "left"
            label_lon_final = lon + ov_x / pts_per_lon
            label_lat_final = lat + ov_y / pts_per_lat
            placed_labels.append((label_lon_final, label_lat_final))
            placed_label_bboxes.append(
                _label_bbox(label_lon_final, label_lat_final, label_w_deg, label_h_deg, ov_ha)
            )
            _city_artist = ax.annotate(
                city_name,
                xy=(lon, lat),
                xytext=(ov_x, ov_y),
                textcoords="offset points",
                fontsize=18,
                fontweight="bold",
                color=white_hex,
                ha=ov_ha,
                zorder=6,
                **font_props,
            )
            city_label_artists.append(_city_artist)
            continue  # skip auto-candidate loop below

        best = candidates[0]
        best_min_dist = -1
        best_bbox = None
        for xo, yo, ha_c in candidates:
            label_lon = lon + xo / pts_per_lon
            label_lat = lat + yo / pts_per_lat
            bbox = _label_bbox(label_lon, label_lat, label_w_deg, label_h_deg, ha_c)

            # Bounds check — label bbox must fit inside the map frame
            if bbox[0] < lon_range[0] or bbox[2] > lon_range[1]:
                continue
            if bbox[1] < lat_range[0] or bbox[3] > lat_range[1]:
                continue
            # Skip candidates that overlap the legend rectangle
            if _in_legend(label_lon, label_lat):
                continue
            # Hard reject: overlap with any already-placed label's bbox
            if any(_bboxes_overlap(bbox, pb) for pb in placed_label_bboxes):
                continue
            # Check distance to all previously placed label centers
            min_d = float("inf")
            for pl_lon, pl_lat in placed_labels:
                d = ((label_lon - pl_lon) ** 2 + (label_lat - pl_lat) ** 2) ** 0.5
                min_d = min(min_d, d)
            # Also check distance to other city dots
            for other_name, (other_lon, other_lat) in city_list:
                if other_name == city_name:
                    continue
                d = ((label_lon - other_lon) ** 2 + (label_lat - other_lat) ** 2) ** 0.5
                min_d = min(min_d, d)
            if min_d > best_min_dist:
                best_min_dist = min_d
                best = (xo, yo, ha_c)
                best_bbox = bbox

        x_off, y_off, ha = best
        label_lon_final = lon + x_off / pts_per_lon
        label_lat_final = lat + y_off / pts_per_lat
        placed_labels.append((label_lon_final, label_lat_final))
        if best_bbox is not None:
            placed_label_bboxes.append(best_bbox)
        else:
            # No candidate passed all constraints — still record bbox for
            # the fallback placement to limit future collisions.
            placed_label_bboxes.append(
                _label_bbox(label_lon_final, label_lat_final, label_w_deg, label_h_deg, ha)
            )

        _city_artist = ax.annotate(
            city_name,
            xy=(lon, lat),
            xytext=(x_off, y_off),
            textcoords="offset points",
            fontsize=18,
            fontweight="bold",
            color=white_hex,
            ha=ha,
            zorder=6,
            **font_props,
        )
        city_label_artists.append(_city_artist)

    # Draw route labels with collision avoidance against city labels and other route labels
    # Estimate label size in data coordinates
    pts_per_lon = fig.get_size_inches()[0] * fig.dpi / lon_span
    pts_per_lat = fig.get_size_inches()[1] * fig.dpi / lat_span
    label_h_data = 20 / pts_per_lat  # approx label height in data coords
    placed_route_labels = []
    placed_route_label_bboxes = []  # B-11 C: bbox-aware overlap check for route labels
    route_label_artists = []  # B-11: track artists for collision check
    # B-11 auto-fix Stage 1: route_label upper exclusion zone (default 5%, raise to 18% to avoid title)
    _route_label_top_padding = visual.get("_route_label_top_padding", 0.05)

    def _bezier_point(sx, sy, cx, cy, ex, ey, t):
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t**2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t**2 * ey
        return bx, by

    def _try_candidate(test_x, test_y, rl_w_data, rl_h_data, lat_range, lat_span, _route_label_top_padding, placed_label_bboxes, placed_route_label_bboxes, placed_labels, city_list, placed_route_labels):
        """Return (bbox, min_dist) if candidate position is acceptable, else (None, -1)."""
        if (
            test_y < lat_range[0] + lat_span * 0.05
            or test_y > lat_range[1] - lat_span * _route_label_top_padding
        ):
            return None, -1
        cand_bbox = (
            test_x - rl_w_data / 2,
            test_y - rl_h_data / 2,
            test_x + rl_w_data / 2,
            test_y + rl_h_data / 2,
        )
        if any(_bboxes_overlap(cand_bbox, pb) for pb in placed_label_bboxes):
            return None, -1
        if any(_bboxes_overlap(cand_bbox, pb) for pb in placed_route_label_bboxes):
            return None, -1
        if _in_legend(test_x, test_y):
            return None, -1
        min_d = float("inf")
        for pl_lon, pl_lat in placed_labels:
            d = ((test_x - pl_lon) ** 2 + (test_y - pl_lat) ** 2) ** 0.5
            min_d = min(min_d, d)
        for _, (clon, clat) in city_list:
            d = ((test_x - clon) ** 2 + (test_y - clat) ** 2) ** 0.5
            min_d = min(min_d, d)
        for rl_x, rl_y in placed_route_labels:
            d = ((test_x - rl_x) ** 2 + (test_y - rl_y) ** 2) ** 0.5
            min_d = min(min_d, d)
        return cand_bbox, min_d

    leader_lines = []  # B-11 A: (start_x, start_y, end_x, end_y, color) for displaced labels

    for rl in route_labels:
        lt = rl["text"]
        lc = rl["color"]
        sx_r, sy_r = rl["sx"], rl["sy"]
        cx_r, cy_r = rl["cx"], rl["cy"]
        ex_r, ey_r = rl["ex"], rl["ey"]
        direction = rl["direction"]

        # B-11 hybrid: estimate route label bbox for overlap detection.
        # Add 20% safety margin to width to account for boxstyle round padding
        # and font rendering variance (avoids false-pass on borderline overlaps).
        rl_w_data = _estimate_label_w_deg(lt, 16, pts_per_lon) * 1.20
        rl_h_data = label_h_data * 1.8  # boxstyle round padding + safety margin

        # Curve midpoint (anchor for leader line if label gets displaced)
        anchor_x, anchor_y = _bezier_point(sx_r, sy_r, cx_r, cy_r, ex_r, ey_r, 0.5)

        best_pos = None
        best_min_dist = -1
        best_bbox_route = None
        used_displacement = False

        # Manual override: scene_def label_offset (data coords, [x, y]) — skip auto placement
        manual_offset = rl.get("label_offset")
        if manual_offset is not None and isinstance(manual_offset, (list, tuple)) and len(manual_offset) == 2:
            best_pos = (anchor_x + manual_offset[0], anchor_y + manual_offset[1])
            best_bbox_route = (
                best_pos[0] - rl_w_data / 2,
                best_pos[1] - rl_h_data / 2,
                best_pos[0] + rl_w_data / 2,
                best_pos[1] + rl_h_data / 2,
            )
            best_min_dist = 999  # bypass collision-based selection below
            displacement = (manual_offset[0] ** 2 + manual_offset[1] ** 2) ** 0.5
            used_displacement = displacement > label_h_data * 1.5

        # Phase B: try along-curve placements first (preserves visual correspondence)
        t_candidates = [0.5, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75]
        perp_offsets = [
            lat_span * 0.04 * direction,
            lat_span * 0.04 * (-direction),
            lat_span * 0.08 * direction,
            lat_span * 0.08 * (-direction),
        ]
        for t_val in t_candidates:
            bx_t, by_t = _bezier_point(sx_r, sy_r, cx_r, cy_r, ex_r, ey_r, t_val)
            for perp_off in perp_offsets:
                test_x = bx_t
                test_y = by_t + perp_off
                cand_bbox, min_d = _try_candidate(
                    test_x, test_y, rl_w_data, rl_h_data, lat_range, lat_span,
                    _route_label_top_padding, placed_label_bboxes, placed_route_label_bboxes,
                    placed_labels, city_list, placed_route_labels,
                )
                if cand_bbox is None:
                    continue
                if min_d > best_min_dist:
                    best_min_dist = min_d
                    best_pos = (test_x, test_y)
                    best_bbox_route = cand_bbox

        # Phase C (displacement fallback): if Phase B found nothing acceptable,
        # widen search to displaced positions with bigger offsets, and mark for leader line.
        if best_min_dist < 0:
            v_offsets = [
                0,
                label_h_data * 2,
                -label_h_data * 2,
                label_h_data * 4,
                -label_h_data * 4,
                label_h_data * 6,
                -label_h_data * 6,
                label_h_data * 8,
                -label_h_data * 8,
            ]
            h_offsets = [0, rl_w_data * 0.4, -rl_w_data * 0.4]
            for dx in h_offsets:
                for dy in v_offsets:
                    test_x = anchor_x + dx
                    test_y = anchor_y + dy
                    cand_bbox, min_d = _try_candidate(
                        test_x, test_y, rl_w_data, rl_h_data, lat_range, lat_span,
                        _route_label_top_padding, placed_label_bboxes, placed_route_label_bboxes,
                        placed_labels, city_list, placed_route_labels,
                    )
                    if cand_bbox is None:
                        continue
                    if min_d > best_min_dist:
                        best_min_dist = min_d
                        best_pos = (test_x, test_y)
                        best_bbox_route = cand_bbox
                        used_displacement = True

        # Final fallback: forced position below top exclusion zone
        if best_min_dist < 0 or best_pos is None:
            forced_y = lat_range[1] - lat_span * (_route_label_top_padding + 0.02)
            best_pos = (anchor_x, forced_y)
            best_bbox_route = (
                best_pos[0] - rl_w_data / 2,
                forced_y - rl_h_data / 2,
                best_pos[0] + rl_w_data / 2,
                forced_y + rl_h_data / 2,
            )
            used_displacement = True

        # B-11 A: if label is displaced from its curve, queue a leader line
        # (will be drawn AFTER all labels placed so it appears below them).
        displacement = ((best_pos[0] - anchor_x) ** 2 + (best_pos[1] - anchor_y) ** 2) ** 0.5
        if used_displacement and displacement > label_h_data * 1.5:
            leader_lines.append((anchor_x, anchor_y, best_pos[0], best_pos[1], lc))

        placed_route_labels.append(best_pos)
        if best_bbox_route is not None:
            placed_route_label_bboxes.append(best_bbox_route)
        _route_label_artist = ax.text(
            best_pos[0],
            best_pos[1],
            lt,
            fontsize=16,
            color=lc,
            ha="center",
            va="center",
            alpha=0.95,
            zorder=6,
            fontweight="bold",
            **font_props,
            bbox=dict(
                boxstyle="round,pad=0.4", facecolor=bg_hex, alpha=0.8, edgecolor=lc, linewidth=0.5
            ),
        )
        route_label_artists.append(_route_label_artist)

    # B-11 A: draw queued leader lines (curve anchor → displaced label).
    # zorder=5 so they sit below route labels (6) but above arrows (3).
    for ax_x, ay, lx_end, ly_end, lc_line in leader_lines:
        ax.plot(
            [ax_x, lx_end],
            [ay, ly_end],
            color=lc_line,
            linewidth=0.7,
            alpha=0.55,
            linestyle="--",
            zorder=5,
        )

    # Title (inside plot area, top center)
    title_artist = None  # B-11: track for collision check
    title_fontsize = visual.get("_title_fontsize", 28)  # auto-fix Stage 3 may override
    if title:
        title_y = lat_range[1] - lat_span * 0.06
        title_artist = ax.text(
            (lon_range[0] + lon_range[1]) / 2,
            title_y,
            title,
            fontsize=title_fontsize,
            color=gold_hex,
            ha="center",
            va="top",
            fontweight="bold",
            zorder=7,
            **font_props,
        )

    # Legend — use custom labels from visual spec if provided,
    # otherwise fall back to default person-journey labels.
    _DEFAULT_LEGEND_LABELS = {
        "origin": "生誕",
        "education": "留学",
        "career": "研究",
        "wandering": "遍歴",
        "exile": "亡命",
        "final": "最期の地",
    }
    _LEGEND_LABELS = visual.get("legend_labels", _DEFAULT_LEGEND_LABELS)
    legend_items = []
    seen_labels = set()
    for cat in ["origin", "education", "career", "wandering", "exile", "final"]:
        if cat in legend_categories:
            lbl = _LEGEND_LABELS.get(cat, cat)
            if lbl not in seen_labels:
                legend_items.append(mpatches.Patch(color=_ROUTE_CATEGORY_COLORS[cat], label=lbl))
                seen_labels.add(lbl)

    legend_artist = None  # B-11: track for collision check
    if legend_items:
        legend_prop = FontProperties(fname=font_path, size=18) if font_path else {"size": 18}
        legend_artist = ax.legend(
            handles=legend_items,
            loc=legend_loc,
            bbox_to_anchor=legend_bbox,
            fontsize=18,
            facecolor=bg_hex,
            edgecolor=line_color,
            labelcolor=white_hex,
            prop=legend_prop,
            borderpad=0.8,
            handlelength=1.5,
        )
        legend_artist.get_frame().set_alpha(0.85)

    # Hide axes
    ax.spines[:].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Reserve bottom 220/1080 (≈20.4%) for subtitle overlay.
    # Axis content is constrained to the top ~79.6% of the figure, ensuring
    # city markers/labels never collide with subtitles rendered on top.
    # NOTE: bbox_inches="tight" would crop the reserved margin away,
    # so we use the full figsize instead.
    SUBTITLE_SAFE_FRAC = 220 / 1080  # ≈ 0.2037
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=SUBTITLE_SAFE_FRAC)

    # B-11 Layer 3: collision check (runs whether or not preflight ran).
    # Reports printed as WARN here; preflight is responsible for STOP/auto-fix.
    collision_reports = _check_route_map_collisions(
        fig, title_artist, route_label_artists, legend_artist, city_label_artists
    )
    for rep in collision_reports:
        print(f"    [WARN] route_map collision: {rep['summary']}")
        print(f"           suggest: {rep['suggestion']}")

    if preflight_only:
        plt.close(fig)
        return collision_reports

    # Save as temp PNG then apply Ken Burns
    temp_png = output_path.replace(".mp4", "_map.png")
    fig.savefig(temp_png, dpi=200, facecolor=bg_hex)
    plt.close()

    try:
        generate_ken_burns(
            temp_png, output_path, duration, effect=effect, width=width, height=height, fps=fps
        )
    finally:
        if os.path.exists(temp_png):
            os.remove(temp_png)
    return collision_reports


def _apply_route_map_auto_fix_stage(visual: dict, stage: int) -> tuple[dict, str]:
    """B-11 auto-fix: mutate visual for the given stage. Returns (new_visual, description)."""
    import copy

    new_visual = copy.deepcopy(visual)
    if stage == 1:
        # Stage 1 (label avoidance): widen route_label top exclusion zone so labels
        # avoid the band where the title sits.
        new_visual["_route_label_top_padding"] = 0.18
        return new_visual, "route_label top exclusion 5%->18% (labels avoid title band)"
    if stage == 2:
        # Stage 2 (bounds expansion): grow bounds.lat[1] upward by 20% of current span.
        cities = new_visual.get("cities", {})
        bounds = new_visual.get("bounds")
        if not bounds and cities:
            lats = [coord[1] for coord in cities.values()]
            lat_min, lat_max = min(lats), max(lats)
            pad = max((lat_max - lat_min) * 0.20, 4)
            bounds = {"lat": [lat_min - pad, lat_max + pad]}
            new_visual["bounds"] = bounds
        if bounds and "lat" in bounds:
            lat_min, lat_max = bounds["lat"]
            span = lat_max - lat_min
            new_visual["bounds"]["lat"] = [lat_min, lat_max + span * 0.20]
            return new_visual, (
                f"bounds.lat[1] expanded {lat_max:.1f}->{lat_max + span * 0.20:.1f} (+20% of span)"
            )
        return new_visual, "bounds expansion skipped (no lat info)"
    if stage == 3:
        # Stage 3 (fontsize reduction): shrink title fontsize 28 -> 22.
        new_visual["_title_fontsize"] = 22
        return new_visual, "title fontsize 28->22"
    if stage == 4:
        # Stage 4 (legend relocation): cycle legend_loc through corners to avoid
        # route_label / city overlap. Each invocation rotates one position:
        # upper right -> lower right -> lower left -> upper left.
        rotation = ["upper right", "lower right", "lower left", "upper left"]
        anchors = {
            "upper right": [0.92, 0.98],
            "lower right": [0.92, 0.30],
            "lower left": [0.08, 0.30],
            "upper left": [0.08, 0.98],
        }
        cur_loc = new_visual.get("legend_loc", "upper right")
        try:
            next_loc = rotation[(rotation.index(cur_loc) + 1) % 4]
        except ValueError:
            next_loc = "lower right"  # unknown current → start from lower right
        new_visual["legend_loc"] = next_loc
        new_visual["legend_bbox_to_anchor"] = anchors[next_loc]
        return new_visual, f"legend_loc {cur_loc!r}->{next_loc!r}"
    return new_visual, f"unknown stage {stage}"


def route_map_preflight(scene_def_path: str, allow: bool = False, auto_fix: bool = False) -> dict:
    """B-11 Layer 2: pre-render collision check for all route_map visuals.

    Loads scene_definition.json, iterates scenes whose visual.type == "route_map",
    calls generate_route_map(..., preflight_only=True) on each, and collects
    collision reports.

    With auto_fix=True, attempts a 3-stage repair sequence per affected scene:
      Stage 1: widen route_label top exclusion zone to avoid title band
      Stage 2: expand bounds.lat[1] upward by 10% of span
      Stage 3: reduce title fontsize 28 -> 22
    Each stage is followed by a re-check; the first stage that resolves all
    collisions for the scene is accepted, persisted to scene_definition.json,
    and logged under the top-level `_route_map_auto_fix_log` block.

    Args:
        scene_def_path: path to scene_definition.json
        allow: if True, return reports without raising (caller decides STOP)
        auto_fix: if True, mutate scene_def visual params and persist on success

    Returns:
        dict {scene_id: [collision_report, ...]} for unresolved collisions only.
        Empty dict means all clean (or all auto-fixed).
    """
    if not os.path.exists(scene_def_path):
        print(f"[route-map preflight] scene_definition.json not found: {scene_def_path}")
        return {}

    with open(scene_def_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    # scene_definition.json structure: sd["sections"][i]["scenes"][j]
    # Collect (section_idx, scene_idx, scene) for every route_map scene.
    route_scenes: list = []
    for sec_idx, section in enumerate(scene_def.get("sections", [])):
        for sc_idx, sc in enumerate(section.get("scenes", [])):
            v = sc.get("visual")
            if isinstance(v, dict) and v.get("type") == "route_map":
                route_scenes.append((sec_idx, sc_idx, sc))
    if not route_scenes:
        return {}

    print(f"\n[route-map preflight] checking {len(route_scenes)} route_map scene(s)...")

    unresolved: dict = {}
    fix_log: list[dict] = []

    for sec_idx, sc_idx, scene in route_scenes:
        scene_id = scene.get("scene_id") or scene.get("id") or f"scene_{sec_idx}_{sc_idx}"
        visual = scene["visual"]
        try:
            reports = generate_route_map(visual, "", 0.0, preflight_only=True)
        except Exception as e:
            print(f"  {scene_id}: preflight render failed: {type(e).__name__}: {e}")
            continue

        if not reports:
            print(f"  {scene_id}: clean")
            continue

        print(f"  {scene_id}: {len(reports)} collision(s) detected")
        for rep in reports:
            print(f"    - {rep['summary']}")
            print(f"      suggest: {rep['suggestion']}")

        if not auto_fix:
            unresolved[scene_id] = reports
            continue

        # auto-fix: try stages cumulatively (each builds on previous mutations).
        # stage 1 -> 1+2 -> 1+2+3 -> 1+2+3+4 (legend rotation, may iterate up to 4 times).
        fixed_visual = visual
        accepted_stages: list[str] = []
        for stage in (1, 2, 3, 4, 4, 4):
            candidate, descr = _apply_route_map_auto_fix_stage(fixed_visual, stage)
            try:
                stage_reports = generate_route_map(candidate, "", 0.0, preflight_only=True)
            except Exception as e:
                print(f"    stage {stage} render failed: {type(e).__name__}: {e}")
                stage_reports = reports
            # Always update fixed_visual cumulatively, so the next stage builds on top.
            fixed_visual = candidate
            accepted_stages.append(f"stage{stage}: {descr}")
            if not stage_reports:
                print(f"    stage {stage} ({descr}): RESOLVED")
                break
            print(f"    stage {stage} ({descr}): still {len(stage_reports)} collision(s)")
        else:
            # All 3 stages applied but still collision -> revert (don't accept partial fixes)
            accepted_stages = []
            fixed_visual = visual

        # Re-check final result
        if accepted_stages:
            scene_def["sections"][sec_idx]["scenes"][sc_idx]["visual"] = fixed_visual
            fix_log.append(
                {
                    "scene_id": scene_id,
                    "stages_applied": accepted_stages,
                    "original_reports": [r["summary"] for r in reports],
                }
            )
        else:
            print(f"    auto-fix exhausted all 3 stages for {scene_id}")
            unresolved[scene_id] = reports

    # Persist auto-fix changes (if any)
    if fix_log:
        existing_log = scene_def.get("_route_map_auto_fix_log", [])
        existing_log.extend(fix_log)
        scene_def["_route_map_auto_fix_log"] = existing_log
        with open(scene_def_path, "w", encoding="utf-8") as f:
            json.dump(scene_def, f, ensure_ascii=False, indent=2)
        print(f"[route-map preflight] {len(fix_log)} scene(s) auto-fixed and persisted")

    if unresolved and not allow:
        print(f"\n[route-map preflight] FAIL: {len(unresolved)} scene(s) still have collisions.")
        print("  Re-run with --auto-fix-route-collisions or --allow-route-collision,")
        print("  or edit scene_definition.json manually following the suggestions above.")

    return unresolved


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
    """Process a single scene and generate its visual MP4 segment."""
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
            prompt = visual.get("source_prompt", "no prompt")
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
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("ERROR: FFmpeg not found in PATH")
        sys.exit(1)

    # Check Pillow
    try:
        from PIL import Image
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

            output_file = os.path.join(visuals_dir, f"{scene_id}.mp4")
            if os.path.exists(output_file):
                size_kb = os.path.getsize(output_file) / 1024
                print(f"[OK] ({elapsed:.1f}s, {size_kb:.0f}KB)")
            else:
                print("[NG] output missing")
                stats["stub"] = stats.get("stub", 0) + 1

    # Summary
    print(f"\n{'=' * 50}")
    print("Visual generation complete")
    print(f"  Total scenes:  {sum(stats.values())}")
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

    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[PARTIAL REBUILD] Visual rebuilt: {scene_id} ({elapsed:.1f}s, {size_kb:.0f}KB)")
        return True
    else:
        print(f"[PARTIAL REBUILD] ERROR: Visual output not created: {output_path}")
        return False


if __name__ == "__main__":
    main()
