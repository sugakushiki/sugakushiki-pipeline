"""image_watermark_trim.py — Trim AI-generator watermarks (ChatGPT/Sora ✦).

ChatGPT and OpenAI Sora image generators stamp a 4-pointed sparkle watermark
in the bottom-right corner of every output. For documentary use we need
clean frames at 16:9 / 1920x1080.

Usage (CLI):
    python image_watermark_trim.py input.png output.png
    python image_watermark_trim.py input.png output.png --bottom 0.13
    python image_watermark_trim.py *.png --in-place --bottom 0.10

Usage (Python):
    from image_watermark_trim import trim_watermark
    trim_watermark("in.png", "out.png", bottom_crop_pct=0.10)

Discovery: a past session — manually generated 4 portraits via
ChatGPT all had the BR sparkle. Documented in internal notes
"""

import argparse
import os
import sys

from PIL import Image

TARGET_W = 1920
TARGET_H = 1080
TARGET_RATIO = TARGET_W / TARGET_H  # 1.778


def detect_watermark_corner(
    img: Image.Image, brightness_threshold: int = 200, min_pixels: int = 50
) -> str | None:
    """Heuristic: detect a bright watermark in any corner.

    Returns "BR", "TR", "BL", "TL", or None if no obvious watermark found.
    Works on dark/colorful backgrounds; may have false positives on bright
    natural images (e.g. sky in TR corner). Use as a hint, not a strict gate.
    """
    import numpy as np

    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    cw = max(40, int(w * 0.04))
    ch = max(40, int(h * 0.04))
    corners = {
        "TL": arr[:ch, :cw],
        "TR": arr[:ch, w - cw :],
        "BL": arr[h - ch :, :cw],
        "BR": arr[h - ch :, w - cw :],
    }
    best = None
    best_count = 0
    for name, c in corners.items():
        gray = c.mean(axis=2)
        bright_count = int((gray > brightness_threshold).sum())
        if bright_count >= min_pixels and bright_count > best_count:
            best = name
            best_count = bright_count
    return best


def trim_watermark(
    input_path: str,
    output_path: str,
    bottom_crop_pct: float = 0.10,
    target_w: int = TARGET_W,
    target_h: int = TARGET_H,
) -> None:
    """Trim BR watermark by cropping bottom strip, then center-crop to 16:9
    and resize to target resolution (default 1920×1080).

    Args:
        input_path: source image (any format Pillow reads)
        output_path: destination .png
        bottom_crop_pct: fraction of height to crop from bottom (0.10 = 10%).
            Increase to 0.13 if the AI added an additional fake signature
            (e.g. "T. Euler" 風) above the sparkle.
    """
    img = Image.open(input_path).convert("RGB")
    w, h = img.size

    # 1. Crop bottom strip to remove watermark
    new_h = h - int(h * bottom_crop_pct)
    img = img.crop((0, 0, w, new_h))

    # 2. Center-crop to 16:9
    cur_ratio = w / new_h
    if cur_ratio > TARGET_RATIO:
        new_w = int(new_h * TARGET_RATIO)
        margin = (w - new_w) // 2
        img = img.crop((margin, 0, margin + new_w, new_h))
    elif cur_ratio < TARGET_RATIO:
        new_h2 = int(w / TARGET_RATIO)
        img = img.crop((0, 0, w, new_h2))

    # 3. Resize to target resolution with LANCZOS
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    img.save(output_path, "PNG")


def main():
    parser = argparse.ArgumentParser(
        description="Trim AI-generator watermarks (ChatGPT/Sora ✦) and normalize to 1920×1080.",
    )
    parser.add_argument("inputs", nargs="+", help="Input image path(s)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (single input only). Defaults to input_clean.png.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file. Mutually exclusive with --output.",
    )
    parser.add_argument(
        "--bottom",
        type=float,
        default=0.10,
        help="Bottom crop fraction (default 0.10 = 10%%). Increase to 0.13 for ChatGPT signatures.",
    )
    parser.add_argument(
        "--detect", action="store_true", help="Only run watermark corner detection and report."
    )
    args = parser.parse_args()

    if args.detect:
        for path in args.inputs:
            img = Image.open(path)
            corner = detect_watermark_corner(img)
            print(f"{path}: watermark={corner or 'none detected'}")
        return

    if args.output and args.in_place:
        print("ERROR: --output and --in-place are mutually exclusive")
        sys.exit(2)

    if args.output and len(args.inputs) > 1:
        print("ERROR: --output requires exactly one input")
        sys.exit(2)

    for path in args.inputs:
        if args.in_place:
            out = path
        elif args.output:
            out = args.output
        else:
            base, ext = os.path.splitext(path)
            out = base + "_clean.png"
        trim_watermark(path, out, bottom_crop_pct=args.bottom)
        print(f"  {path} -> {out}")


if __name__ == "__main__":
    main()
