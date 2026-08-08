"""check_route_places.py - ナレーションの地名 vs route_map の表示地名 (advisory, 数学史記).

ある回の指摘「ナレーションはピレネーなのに地図に表示されていなくて分かりづらい」から。
既存の route_map 検査はすべてレイアウト (衝突・見切れ・所属・凡例色) で、**語られた土地が
描かれているか**は誰も見ていなかった。

判定は Claude (advisory)。地名が文字列として在るかと、その人がそこに居たかは別問題で、
辞書照合では団体名 (ロンドン数学会)・反実仮想・他人の移動を切り分けられない (実測 真1/偽4)。
設計と較正は `src/route_place_check.py` の docstring を参照。

Advisory (exit 0)。--strict -> WARN で exit 1。結果は地図+ナレーションの hash に cache され
(`_route_place_cache.json`)、内容が変わるまで Claude を呼ばない。--force で再実行。

**必ず human が判断する (鵜呑み禁止)**。correction は出さない設計 -- 「語られたが地図に無い」の
正解は「地図に足す」とは限らない (ナレーションから外す / そもそも地図の対象外)。

Usage:
    python scripts/check_route_places.py examples/moriarty
    python scripts/check_route_places.py examples/moriarty --strict
    python scripts/check_route_places.py examples/moriarty --force
    python scripts/check_route_places.py examples/moriarty/scene_definition.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import route_place_check as rpc  # noqa: E402


def _resolve(path: str):
    """Return (episode_dir, scene_def_path, config_path)."""
    episode_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    return (
        episode_dir,
        os.path.join(episode_dir, "scene_definition.json"),
        os.path.join(episode_dir, "episode_config.json"),
    )


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="ナレーション地名 vs route_map 地名 (advisory)")
    ap.add_argument("path", help="episode dir or scene_definition.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 if WARN")
    ap.add_argument("--force", action="store_true", help="cache を無視して Claude で再レビューする")
    args = ap.parse_args()

    episode_dir, scene_path, config_path = _resolve(args.path)
    if not os.path.exists(scene_path):
        print(f"[route-place] scene_definition.json not found: {scene_path}")
        return 0

    scene_def = _load(scene_path)
    subject = ""
    if os.path.exists(config_path):
        cfg = _load(config_path)
        subject = cfg.get("mathematician_ja") or cfg.get("mathematician", "")

    if args.force:
        cache_path = os.path.join(episode_dir, "_route_place_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print("[route-place] cache 削除 (--force) -> 再レビュー")

    report = rpc.run_route_place_check(scene_def, episode_dir, subject)
    print(rpc.format_report(report))

    has_warn = report.get("status") == "WARN" and bool(report.get("issues"))
    if has_warn:
        print(
            "    -> 地名欠落は advisory。地図に点を足すか、ナレーションから地名を外すか、"
            "そもそも地図の対象外か、を人間が決めてください (鵜呑み禁止)。"
        )
    return 1 if (args.strict and has_warn) else 0


if __name__ == "__main__":
    sys.exit(main())
