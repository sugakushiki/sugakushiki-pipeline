"""
check_font_coverage.py - scene_definition.json内の文字がフォントで表示可能か検証する

Usage:
    python check_font_coverage.py examples/moriarty/scene_definition.json

フォントファイルのパスはスクリプト内のFONT_PATHを環境に合わせて変更すること。
fonttools が必要: pip install fonttools
"""

import json
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:
    print("ERROR: fonttools が必要です。 pip install fonttools")
    sys.exit(1)

# --- 環境に合わせて変更 ---
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\BIZUDMincho-Regular.ttf",
    r"C:\Windows\Fonts\BIZUDMincho_Regular.ttf",
    str(Path(__file__).resolve().parent.parent / "_font.ttc"),
]


def find_font():
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def get_supported_chars(font_path):
    """フォントのcmapから対応文字のセットを取得"""
    font = TTFont(font_path, fontNumber=0)
    chars = set()
    for table in font["cmap"].tables:
        if table.isUnicode():
            chars.update(table.cmap.keys())
    font.close()
    return chars


def extract_texts(scene_def):
    """scene_definition.jsonからナレーションとtext_overlayのテキストを抽出"""
    texts = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            scene_id = scene.get("scene_id", "?")
            # narration
            for line in scene.get("narration", []):
                texts.append((scene_id, "narration", line))
            # text_overlay
            visual = scene.get("visual", {})
            if visual.get("type") == "text_overlay":
                content = visual.get("content", {})
                if "main" in content:
                    texts.append((scene_id, "overlay-main", content["main"]))
                if "sub" in content:
                    texts.append((scene_id, "overlay-sub", content["sub"]))
    return texts


def check_coverage(texts, supported_codepoints):
    """各テキスト中の文字がフォントに含まれるか検証"""
    issues = []
    for scene_id, source, text in texts:
        for ch in text:
            if ch in "|\n\r\t ":  # 制御文字・区切りはスキップ
                continue
            cp = ord(ch)
            if cp < 128:  # ASCII は常にOK
                continue
            if cp not in supported_codepoints:
                issues.append(
                    {
                        "scene_id": scene_id,
                        "source": source,
                        "char": ch,
                        "codepoint": f"U+{cp:04X}",
                        "context": text,
                    }
                )
    return issues


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <scene_definition.json>")
        sys.exit(1)

    scene_path = sys.argv[1]
    with open(scene_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    font_path = find_font()
    if not font_path:
        print("ERROR: フォントが見つかりません。FONT_CANDIDATES を確認してください。")
        print(f"  検索パス: {FONT_CANDIDATES}")
        sys.exit(1)

    print(f"Font: {font_path}")
    supported = get_supported_chars(font_path)
    print(f"Supported characters: {len(supported)}")

    texts = extract_texts(scene_def)
    print(f"Text entries: {len(texts)}")

    issues = check_coverage(texts, supported)

    if not issues:
        print("\n[OK] All characters are supported by the font.")
    else:
        # deduplicate by character
        seen = set()
        unique_issues = []
        for issue in issues:
            if issue["char"] not in seen:
                seen.add(issue["char"])
                unique_issues.append(issue)

        print(f"\n[NG] {len(unique_issues)} unsupported character(s) found:\n")
        for issue in unique_issues:
            print(
                f"  {issue['codepoint']}  '{issue['char']}'  [{issue['scene_id']}:{issue['source']}]"
            )
            # Show all scenes where this char appears
            affected = [i for i in issues if i["char"] == issue["char"]]
            if len(affected) > 1:
                scenes = sorted(set(f"{i['scene_id']}:{i['source']}" for i in affected))
                print(f"         (appears in {len(affected)} places: {', '.join(scenes)})")


if __name__ == "__main__":
    main()
