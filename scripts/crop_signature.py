"""crop_signature.py - 生成画像の下端に焼き込まれた AI の偽署名をクロップで落とす。

ある回で毎回同じ手順を手書きの Python で繰り返していた (ある回は 13 枚中 4 枚)。
手順を 1 コマンドにして、原画の退避と 16:9 への戻しを取りこぼさないようにする:

  1. images/_orig/<scene>_vN_raw.png に原画を退避 (N は既存の退避数 + 1)
  2. 下端 frac (既定 10%) を切り落とす
  3. 中央で 16:9 に切り直し、1920x1080 にリサイズして上書き

署名が上隅にあるときは --top。クロップ後は images ステップを再実行せず、そのまま
`--steps visuals,assemble,credits,bgm` (visual cache が source 画像の変更を検出して
当該 scene だけ再レンダする)。

Usage:
  python scripts/crop_signature.py examples/moriarty closing_01 person_02 [--frac 0.10] [--top]
"""

import argparse
import os
import shutil
import sys

from PIL import Image

OUT_W, OUT_H = 1920, 1080


def crop_signature(episode_dir: str, scene_id: str, frac: float = 0.10, top: bool = False) -> str:
    """1 枚をクロップして上書きし、退避先のパスを返す。frac は 0 < frac < 0.5。"""
    if not 0.0 < frac < 0.5:
        raise ValueError(f"frac must be in (0, 0.5): {frac}")
    images = os.path.join(episode_dir, "images")
    src = os.path.join(images, f"{scene_id}.png")
    if not os.path.exists(src):
        raise FileNotFoundError(src)
    orig_dir = os.path.join(images, "_orig")
    os.makedirs(orig_dir, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(orig_dir, f"{scene_id}_v{n}_raw.png")):
        n += 1
    backup = os.path.join(orig_dir, f"{scene_id}_v{n}_raw.png")
    shutil.copy2(src, backup)

    im = Image.open(src).convert("RGB")
    w, h = im.size
    cut = int(round(h * frac))
    im = im.crop((0, cut, w, h)) if top else im.crop((0, 0, w, h - cut))
    w2, h2 = im.size
    tw = int(h2 * 16 / 9)
    if tw <= w2:
        x0 = (w2 - tw) // 2
        im = im.crop((x0, 0, x0 + tw, h2))
    else:
        th = int(w2 * 9 / 16)
        y0 = 0 if top else (h2 - th)  # 署名側と反対の端を残す
        im = im.crop((0, y0, w2, y0 + th))
    im = im.resize((OUT_W, OUT_H), Image.LANCZOS)
    im.save(src)
    return backup


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("episode_dir")
    ap.add_argument("scene_ids", nargs="+")
    ap.add_argument("--frac", type=float, default=0.10, help="切り落とす割合 (既定 0.10)")
    ap.add_argument("--top", action="store_true", help="上端を切る (既定は下端)")
    a = ap.parse_args()
    rc = 0
    for sid in a.scene_ids:
        try:
            backup = crop_signature(a.episode_dir, sid, a.frac, a.top)
            print(
                f"  [OK] {sid}.png: {'top' if a.top else 'bottom'} {a.frac:.0%} cropped -> 1920x1080 (orig: {backup})"
            )
        except Exception as e:  # noqa: BLE001 - 1 枚の失敗で残りを止めない (fail loud on exit code)
            print(f"  [FAIL] {sid}: {e}")
            rc = 1
    if rc == 0:
        print(
            "  次: python src/pipeline.py <config> --skip-script --skip-qa-script-only --steps visuals,assemble,credits,bgm"
        )
    return rc


if __name__ == "__main__":
    sys.exit(main())
