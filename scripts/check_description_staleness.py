"""check_description_staleness.py - description.intro staleness check (数学史記).

`scene_definition.json` の `description.intro` は script_generator が LLM で
episode_config の導入系フィールド (theme / hook / modern_connection /
description.intro_guidance) から生成する。生成後にこれらを編集しても intro は
自動同期されず、credits_generator が古い intro をそのまま description.txt
(公開 YouTube 概要欄) に焼き込む。

このスクリプトは `_description_meta.json` (script_generator が刻印) を使って、
**config の導入系フィールドが変化 AND intro テキストが刻印時から不変** の両成立
= stale を検出する (intro を手で直していれば text hash が変わり抑止 = FP 回避)。
pipeline.verify_outputs にも同一ロジックが配線されている (本 CLI は単独確認用)。

Advisory (exit 0)。--strict -> WARN で exit 1。

--accept: 現在の config + intro で `_description_meta.json` を再刻印する。config を
編集し intro は「意図して据え置く」と判断したとき (= 手で直さず現状を正とする) に、
WARN を明示的に解消する。刻印無しの出荷済み ep に初回 sidecar を付けるのにも使える。

Usage:
    python scripts/check_description_staleness.py examples/moriarty [--strict]
    python scripts/check_description_staleness.py examples/moriarty --accept
    python scripts/check_description_staleness.py examples/moriarty/scene_definition.json
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

import description_meta as dm  # noqa: E402


def _resolve(path: str):
    """Return (episode_dir, scene_def_path, config_path) from an episode dir or
    a scene_definition.json path."""
    if os.path.isdir(path):
        episode_dir = path
    else:
        episode_dir = os.path.dirname(os.path.abspath(path))
    return (
        episode_dir,
        os.path.join(episode_dir, "scene_definition.json"),
        os.path.join(episode_dir, "episode_config.json"),
    )


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="description.intro staleness check")
    ap.add_argument("path", help="episode dir or scene_definition.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 if stale")
    ap.add_argument(
        "--accept",
        action="store_true",
        help="現 config + intro で _description_meta.json を再刻印し WARN を解消する "
        "(config を編集したが intro は据え置くと判断したとき / 出荷済み ep への初回刻印)",
    )
    args = ap.parse_args()

    episode_dir, scene_path, config_path = _resolve(args.path)
    if not os.path.exists(scene_path):
        print(f"[desc-stale] scene_definition.json not found: {scene_path}")
        return 0
    if not os.path.exists(config_path):
        print(f"[desc-stale] episode_config.json not found: {config_path}")
        return 0

    config = _load(config_path)
    scene_def = _load(scene_path)

    if args.accept:
        path = dm.write_meta(episode_dir, config, scene_def)
        if path:
            print(
                f"[desc-stale] re-stamped: {os.path.basename(path)} (現 config + intro を正とした)"
            )
        else:
            print("[desc-stale] description.intro が空のため刻印しませんでした")
        return 0

    stale = dm.check_staleness(episode_dir, config, scene_def)
    if not stale:
        meta_exists = os.path.exists(os.path.join(episode_dir, dm.META_FILENAME))
        if meta_exists:
            print("[desc-stale] OK: description.intro は config と同期 (or intro を手編集済)")
        else:
            print(
                "[desc-stale] OK: _description_meta.json 無し (出荷済み ep / 未 script gen) "
                "-> no-op。--accept で刻印を付けられます"
            )
        return 0

    print(f"[desc-stale] WARN: {stale}")
    print(
        "    -> scene_def.description.intro を config に合わせて更新 "
        "(credits step で description.txt に反映)、"
        "または意図して据え置くなら --accept で再刻印してください。"
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
