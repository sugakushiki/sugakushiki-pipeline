"""lint_image_borders.py - 生成画像に焼き込まれた白縁を検出する。

Gemini Flash は油絵スタイル画像にキャンバス/額縁状の白い縁を稀に描き込む。
ken_burns は 15% ズームで cover scale するが、その余白幅を超える白縁は
クロップしきれず、最終動画で「両サイド/上下が白帯」として出る。本 lint は各画像の四辺に一様な near-white strip が
あるか実測し、閾値超を WARN する。`--trim` で content bounding box に自動クロップ。

Usage:
    python scripts/lint_image_borders.py examples/moriarty/images
    python scripts/lint_image_borders.py examples/moriarty/images --trim
"""

import argparse
import glob
import os
import sys

_WHITE = 235.0  # この平均輝度超を near-white とみなす (0-255)
_MIN_BORDER_PX = 12  # 1-2px の極薄縁は ken_burns ズームで消えるので無視
_TRIM_TH = 232.0  # --trim 時に content 境界とみなす輝度閾値


def _line_mean(px, w, h, axis: str, idx: int) -> float:
    if axis == "col":
        ys = range(0, h, 6)
        return sum(sum(px[idx, y]) for y in ys) / 3 / max(1, len(ys))
    xs = range(0, w, 6)
    return sum(sum(px[x, idx]) for x in xs) / 3 / max(1, len(xs))


def _border_width(px, w, h, axis: str, frm: str) -> int:
    """端から数えて連続して near-white な列/行の本数を返す。"""
    n = w if axis == "col" else h
    rng = range(n) if frm == "start" else range(n - 1, -1, -1)
    width = 0
    for idx in rng:
        if _line_mean(px, w, h, axis, idx) > _WHITE:
            width += 1
        else:
            break
    return width


def run(images_dir: str) -> list:
    """白縁のある画像の WARN dict リストを返す。PIL 不在/読込失敗はスキップ。"""
    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        print(f"  [SKIP] PIL を import できません: {e}")
        return []
    warns = []
    for p in sorted(glob.glob(os.path.join(images_dir, "*.png"))):
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        px = im.load()
        borders = {
            "left": _border_width(px, w, h, "col", "start"),
            "right": _border_width(px, w, h, "col", "end"),
            "top": _border_width(px, w, h, "row", "start"),
            "bottom": _border_width(px, w, h, "row", "end"),
        }
        bad = {k: v for k, v in borders.items() if v >= _MIN_BORDER_PX}
        if bad:
            warns.append({"image": os.path.basename(p), "borders": bad, "size": (w, h)})
    return warns


def run_video(video_dir: str, frac: float = 0.3, min_pct: float = 0.04) -> list:
    """visuals/*.mp4 の 1 フレームを抽出し外周の白帯を % で実測。

    source 画像の白縁は ken_burns の COVER 拡大でむしろ広がる。source lint (run) だけでは「納品物に白帯が出ない」を
    保証できないため、レンダ後の動画フレームを直接測る。band を幅/高さに対する比で返す。
    WARN dict: {video, bands_pct{edge:比}, max_pct}。PIL/ffmpeg 不在や読込失敗はスキップ。
    """
    import subprocess
    import tempfile

    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        print(f"  [SKIP] PIL を import できません: {e}")
        return []
    warns = []
    for mp4 in sorted(glob.glob(os.path.join(video_dir, "*.mp4"))):
        try:
            out = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "csv=p=0",
                    mp4,
                ],
                text=True,
            ).strip()
            dur = float(out)
        except Exception:
            dur = 1.0
        t = max(0.1, dur * frac)
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            subprocess.run(
                ["ffmpeg", "-nostdin", "-y", "-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", tmp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            im = Image.open(tmp).convert("RGB")
        except Exception:
            continue
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        w, h = im.size
        px = im.load()
        bands = {
            "left": _border_width(px, w, h, "col", "start") / max(1, w),
            "right": _border_width(px, w, h, "col", "end") / max(1, w),
            "top": _border_width(px, w, h, "row", "start") / max(1, h),
            "bottom": _border_width(px, w, h, "row", "end") / max(1, h),
        }
        bad = {k: v for k, v in bands.items() if v >= min_pct}
        if bad:
            warns.append(
                {
                    "video": os.path.basename(mp4),
                    "bands_pct": bad,
                    "max_pct": max(bad.values()),
                }
            )
    return warns


def trim_image(path: str) -> tuple:
    """白縁を content bounding box にクロップして上書き。(orig_size, new_size) を返す。"""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    L = 0
    while L < w // 3 and _line_mean(px, w, h, "col", L) > _TRIM_TH:
        L += 1
    R = w - 1
    while R > 2 * w // 3 and _line_mean(px, w, h, "col", R) > _TRIM_TH:
        R -= 1
    T = 0
    while T < h // 3 and _line_mean(px, w, h, "row", T) > _TRIM_TH:
        T += 1
    B = h - 1
    while B > 2 * h // 3 and _line_mean(px, w, h, "row", B) > _TRIM_TH:
        B -= 1
    if (L, T, R, B) == (0, 0, w - 1, h - 1):
        return (w, h), (w, h)
    cropped = im.crop((L, T, R + 1, B + 1))
    cropped.save(path)
    return (w, h), cropped.size


def main():
    parser = argparse.ArgumentParser(description="生成画像の白縁検出")
    parser.add_argument("images_dir", help="episodes/XXX/images または visuals ディレクトリ")
    parser.add_argument(
        "--trim", action="store_true", help="検出した画像を content box に自動クロップ"
    )
    parser.add_argument(
        "--video",
        action="store_true",
        help="images でなく visuals/*.mp4 のレンダ後フレームを白帯検査",
    )
    parser.add_argument(
        "--strict", action="store_true", help="WARN があれば exit 1 (既定は exit 0)"
    )
    args = parser.parse_args()

    print("=" * 60)
    title = (
        "Video Border Lint (post-render)"
        if args.video
        else "Image Border Lint (white-border bake detection)"
    )
    print(f"  {title}")
    print("=" * 60)
    if not os.path.isdir(args.images_dir):
        print(f"  [ERROR] not a directory: {args.images_dir}")
        sys.exit(2)

    if args.video:
        vwarns = run_video(args.images_dir)
        if not vwarns:
            print("\n  RESULT: PASS (レンダ動画に白帯は検出されませんでした)")
            sys.exit(0)
        print(f"\n  [WARN] {len(vwarns)} 本のレンダ動画に白帯:")
        for v in vwarns:
            bd = ", ".join(f"{k}={p * 100:.0f}%" for k, p in v["bands_pct"].items())
            print(f"    - {v['video']}: {bd}")
        print("\n  対処: source 画像を `--trim` でクロップし visuals を再描画")
        print(f"\n  RESULT: {'FAIL' if args.strict else 'WARN'} ({len(vwarns)} 本)")
        sys.exit(1 if args.strict else 0)

    warns = run(args.images_dir)
    if not warns:
        print("\n  RESULT: PASS (白縁は検出されませんでした)")
        sys.exit(0)

    print(f"\n  [WARN] {len(warns)} 枚に白縁を検出:")
    for w in warns:
        bd = ", ".join(f"{k}={v}px" for k, v in w["borders"].items())
        print(f"    - {w['image']} ({w['size'][0]}x{w['size'][1]}): {bd}")
        if args.trim:
            (ow, oh), (nw, nh) = trim_image(os.path.join(args.images_dir, w["image"]))
            print(f"        -> trimmed {ow}x{oh} -> {nw}x{nh}")
    if not args.trim:
        print("\n  対処: `--trim` で自動クロップ、または visual を再描画")
    print(f"\n  RESULT: {'FAIL' if args.strict else 'WARN'} ({len(warns)} 枚)")
    sys.exit(1 if args.strict else 0)


if __name__ == "__main__":
    main()
