"""check_route_legend.py - route_map 凡例ラベル整合レビュー (advisory, 数学史記).

route_map の `legend_labels` はカテゴリごとに 1 つのラベルを与えるが、そのラベルが
**そのカテゴリの全経路について真か**は誰も検査していなかった (ある回で再発)。

このスクリプトは「カテゴリの凡例ラベル」と「そのカテゴリに属する経路ラベル群」を
Claude (advisory) に渡し、**ラベルが当てはまらない経路がある**箇所だけを高確信で
報告する。経路ラベルは短い日本語自由文なので文字列一致では判定できない。

Advisory (exit 0)。--strict -> WARN で exit 1。結果は凡例+経路ラベルの hash に cache
され (`_route_legend_cache.json`)、内容が変わるまで Claude を呼ばない。--force で再実行。

**必ず human が史実と照合して最終判断する (鵜呑み禁止)**。correction は出さない設計。

Usage:
    python scripts/check_route_legend.py examples/moriarty
    python scripts/check_route_legend.py examples/moriarty --strict
    python scripts/check_route_legend.py examples/moriarty --force
    python scripts/check_route_legend.py examples/moriarty/scene_definition.json
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

import route_legend_check as rlc  # noqa: E402


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
    ap = argparse.ArgumentParser(description="route_map 凡例ラベル整合レビュー (advisory)")
    ap.add_argument("path", help="episode dir or scene_definition.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 if WARN")
    ap.add_argument("--force", action="store_true", help="cache を無視して Claude で再レビューする")
    args = ap.parse_args()

    episode_dir, scene_path, config_path = _resolve(args.path)
    if not os.path.exists(scene_path):
        print(f"[route-legend] scene_definition.json not found: {scene_path}")
        return 0

    scene_def = _load(scene_path)
    subject = ""
    if os.path.exists(config_path):
        cfg = _load(config_path)
        subject = cfg.get("mathematician_ja") or cfg.get("mathematician", "")

    if args.force:
        cache_path = os.path.join(episode_dir, "_route_legend_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print("[route-legend] cache 削除 (--force) -> 再レビュー")

    report = rlc.run_route_legend_check(scene_def, episode_dir, subject)
    print(rlc.format_report(report))

    has_warn = report.get("status") == "WARN" and bool(report.get("issues"))
    if has_warn:
        print(
            "    -> 凡例不整合は advisory。人間が史実を確認し、必要なら "
            "scene_definition.json の legend_labels か route[].category を"
            "直してください (鵜呑み禁止)。"
        )
    return 1 if (args.strict and has_warn) else 0


if __name__ == "__main__":
    sys.exit(main())
