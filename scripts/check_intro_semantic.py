"""check_intro_semantic.py - (F): narration -> description.intro 意味一致 (数学史記).

`scene_definition.json` の `description.intro` は本編を短くまとめた公開 概要欄 導入文。
生成後に narration を編集しても intro は自動同期されず、**本編が保持している数学的
前提条件・限定詞を intro が落として記述が不正確になる** drift が起こりうる (ある回
ゲーデルで本編『無矛盾な形式体系』の『無矛盾な』が intro から欠落した型)。

このスクリプトは intro + narration を Claude (advisory) に渡し、**本編にある限定詞を
intro が落として不正確化している箇所だけ**を高確信で報告する。既存 6-gram 表層検査
(qa_checker) が言い換えで取りこぼす意味 drift を埋める。credits step + pipeline
verify_outputs にも同一チェックが配線されている (本 CLI は単独確認用)。

Advisory (exit 0)。--strict -> WARN で exit 1。結果は intro+narration の hash に
cache され (`_intro_semantic_cache.json`)、内容が変わるまで Claude を呼ばない。
--force で cache を捨てて再レビュー。

**必ず human が本編と照合して最終判断する (鵜呑み禁止)**。correction は出さない設計。

Usage:
    python scripts/check_intro_semantic.py examples/moriarty
    python scripts/check_intro_semantic.py examples/moriarty --strict
    python scripts/check_intro_semantic.py examples/moriarty --force
    python scripts/check_intro_semantic.py examples/moriarty/scene_definition.json
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

import intro_semantic_check as isc  # noqa: E402


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
    ap = argparse.ArgumentParser(
        description="narration -> description.intro 意味一致レビュー (F, advisory)"
    )
    ap.add_argument("path", help="episode dir or scene_definition.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 if WARN")
    ap.add_argument("--force", action="store_true", help="cache を無視して Claude で再レビューする")
    args = ap.parse_args()

    episode_dir, scene_path, config_path = _resolve(args.path)
    if not os.path.exists(scene_path):
        print(f"[intro-semantic] scene_definition.json not found: {scene_path}")
        return 0

    scene_def = _load(scene_path)
    subject = ""
    if os.path.exists(config_path):
        cfg = _load(config_path)
        subject = cfg.get("mathematician_ja") or cfg.get("mathematician", "")

    if args.force:
        cache_path = os.path.join(episode_dir, "_intro_semantic_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print("[intro-semantic] cache 削除 (--force) -> 再レビュー")

    report = isc.run_intro_semantic_check(scene_def, episode_dir, subject)
    print(isc.format_report(report))

    has_warn = report.get("status") == "WARN" and bool(report.get("issues"))
    if has_warn:
        print(
            "    -> 限定詞欠落は advisory。人間が本編と照合し、必要なら "
            "scene_definition.json の description.intro に限定詞を補ってください (鵜呑み禁止)。"
        )
    return 1 if (args.strict and has_warn) else 0


if __name__ == "__main__":
    sys.exit(main())
