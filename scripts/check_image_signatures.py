"""check_image_signatures.py - AI が描き込む画家風署名のコーナー検査

生成画像の下隅には高頻度で筆記体の偽署名が入る (ある回: 13 枚中 6 枚 / ある回: 10
箇所 / ある回: 7 枚 / ある回: 12 箇所 + 再生成 3 枚にも新署名)。post_build_verify
check 11 はコーナーシートを作って**人間の目**に委ねるが、ある回では暗部の署名 1
件をシート目視で見落とし、部分再ビルドがもう 1 周増えた。ここでは同じコーナー群を
1 枚のシートに束ね、**Claude vision に 1 回だけ**「署名らしき筆記体があるタイル」を
挙げさせて advisory WARN にする (人間の目の置き換えではなく前処理 — [ACTION] の
シート目視は残る)。

判定の較正メモ:
  - 署名 = 隅にある筆記体・モノグラム・透かし風の孤立した書き込み
  - 署名ではない = 封蝋・リボン・草木・石畳・机の木目・黒板の板書・楽譜など
    絵の内容そのもの (プロンプトで明示的に除外を指示)
  - image_generator の ある回 anti-signature 節が生成側で頻度を下げるが、モデルは
    指示を無視することがある (実測: 節なしで 3/3 に署名) ので出口検査は残す

advisory: 検出しても build は止めない (真偽の最終判断はクロップ実行前に人間が行う)。
Claude CLI が使えない環境では graceful degrade (空リストを返し [SKIP] を出す)。

Usage:
    python scripts/check_image_signatures.py examples/moriarty
    python scripts/check_image_signatures.py examples/moriarty/images
"""

import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 下隅の帯。署名の実測位置は全て下端 8% 以内 だが、余裕を
# 持って 16% を切り出す。左右は 45% ずつ (中央 10% はほぼ被写体で署名実績なし)。
_STRIP_H = 0.16
_STRIP_W = 0.45
_TILE_W = 620
_LABEL_H = 18


def _scene_ids_next_to(images_dir: str) -> set:
    """images/ の親にある scene_definition.json の scene_id 集合 (無ければ空 = 全 png を対象)。"""
    sd_path = os.path.join(os.path.dirname(os.path.abspath(images_dir)), "scene_definition.json")
    try:
        with open(sd_path, encoding="utf-8") as f:
            sd = json.load(f)
    except Exception:
        return set()
    stems = set()
    for sec in sd.get("sections", []) or []:
        for sc in sec.get("scenes", []) or []:
            if sc.get("scene_id"):
                stems.add(sc["scene_id"])
            # visual.source で別名の png を出荷する回がある (010_gauss: gemini_map.png)。
            v = sc.get("visual") or {}
            for key in ("source", "image", "source_image", "background"):
                val = v.get(key)
                if isinstance(val, str) and val:
                    stems.add(os.path.splitext(os.path.basename(val))[0])
    return stems


def build_corner_sheet(images_dir: str, out_path: str) -> list[str]:
    """images_dir の各 png の下隅 2 枚を 1 シートに束ねる。返り値はラベル一覧。"""
    from PIL import Image, ImageDraw, ImageEnhance

    names = sorted(
        f
        for f in os.listdir(images_dir)
        if f.lower().endswith(".png") and os.path.isfile(os.path.join(images_dir, f))
    )
    # ある回: 作業ファイル (crop_bottomleft.png) がシートに混ざった。scene_definition が
    # 隣にあれば scene_id の png だけを見る (post_build_verify.split_scene_images と同じ規則)。
    scene_ids = _scene_ids_next_to(images_dir)
    if scene_ids:
        names = [n for n in names if os.path.splitext(n)[0] in scene_ids]
    tiles = []
    labels = []
    for name in names:
        try:
            im = Image.open(os.path.join(images_dir, name)).convert("RGB")
        except OSError:
            continue
        w, h = im.size
        strip_h = max(1, int(h * _STRIP_H))
        strip_w = max(1, int(w * _STRIP_W))
        for corner, box in (
            ("BL", (0, h - strip_h, strip_w, h)),
            ("BR", (w - strip_w, h - strip_h, w, h)),
        ):
            crop = im.crop(box)
            scale = _TILE_W / crop.width
            crop = crop.resize((_TILE_W, max(1, int(crop.height * scale))))
            # 暗部の署名 はそのままでは見えないので持ち上げる
            crop = ImageEnhance.Brightness(crop).enhance(1.5)
            label = f"{os.path.splitext(name)[0]}__{corner}"
            labels.append(label)
            tiles.append((label, crop))
    if not tiles:
        return []

    cols = 2
    tile_h = max(t.height for _, t in tiles) + _LABEL_H
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (_TILE_W + 8) + 8, rows * (tile_h + 8) + 8), (12, 12, 18))
    draw = ImageDraw.Draw(sheet)
    for i, (label, tile) in enumerate(tiles):
        x = 8 + (i % cols) * (_TILE_W + 8)
        y = 8 + (i // cols) * (tile_h + 8)
        draw.text((x + 2, y + 2), label, fill=(255, 220, 80))
        sheet.paste(tile, (x, y + _LABEL_H))
    sheet.save(out_path)
    return labels


def _call_claude(prompt: str) -> str | None:
    """実装は claude_backend.call_claude_text。"""
    _src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    from claude_backend import call_claude_text

    return call_claude_text(prompt, context="check_image_signatures", prefix="sig_check")


def analyze_sheet(sheet_path: str, labels: list[str]) -> list[str] | None:
    """署名疑いのラベル一覧を返す。Claude 不可なら None (skip の合図)。"""
    prompt = (
        f"画像ファイル {os.path.abspath(sheet_path)} を Read ツールで開いてください。\n"
        "これは AI 生成画像の下隅だけを並べたシートで、各タイルの左上に黄色い LABEL が"
        "書いてあります。\n\n"
        "タスク: **画家の署名・モノグラム・透かしのような、隅に置かれた孤立した筆記体/"
        "文字風の書き込み**が写っているタイルの LABEL だけを列挙してください。\n"
        "署名ではないもの (絵の内容そのもの): 封蝋・リボン・草木・石畳・木目・家具・"
        "黒板/紙/テーブル面/大理石面の板書・落書き・数式・服の皺・大理石の艶や光の反射・"
        "石目/大理石の縞。これらは挙げない (較正 2026-08-18: 大理石ハイライトと"
        "大理石上の鉛筆数式の誤検出が各 1 件あった -- 署名は隅に孤立した筆記体のみ)。\n"
        "淡い/暗い署名も対象 (シートは明度を持ち上げてある)。\n\n"
        '出力は JSON 配列のみ: ["label1", "label2"]。無ければ []。説明文は書かない。'
    )
    resp = _call_claude(prompt)
    if resp is None:
        return None
    m = re.search(r"\[.*?\]", resp, re.S)
    if not m:
        return None
    try:
        found = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    valid = set(labels)
    return [x for x in found if isinstance(x, str) and x in valid]


def run(images_dir: str) -> list[str] | None:
    """署名疑いのラベルを返す (None = Claude 不可で未実施)。"""
    qa_dir = os.path.join(os.path.dirname(os.path.abspath(images_dir)), "_qa_frames")
    os.makedirs(qa_dir, exist_ok=True)
    sheet = os.path.join(qa_dir, "_sig_check_sheet.png")
    labels = build_corner_sheet(images_dir, sheet)
    if not labels:
        return []
    return analyze_sheet(sheet, labels)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="episode dir か images dir")
    args = ap.parse_args()
    images_dir = args.path
    if os.path.isdir(os.path.join(images_dir, "images")):
        images_dir = os.path.join(images_dir, "images")
    found = run(images_dir)
    if found is None:
        print("[SKIP] Claude CLI が使えないため署名 vision チェックを実施できませんでした")
        return 0
    if found:
        print(f"[WARN] 署名らしき書き込み {len(found)} 件 (advisory -- クロップ前に人間が確認):")
        for label in found:
            print(f"  - {label}")
        print("  対処: 該当画像の下端をクロップ (縦横比維持) するか、再生成する")
    else:
        print("[OK] 署名らしき書き込みは検出されませんでした")
    return 0


if __name__ == "__main__":
    sys.exit(main())
