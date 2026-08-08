"""Thumbnail Vision QA for 数学史記.

Validates generated thumbnail PNG files using Claude Sonnet Vision to detect:
- Image type (portrait / group_scene / landscape / abstract)
- Whether the subject is identifiable at 1-second glance (CTR proxy)
- Concerns (e.g. "multiple figures, hard to identify subject")

## 背景

ある回で `thumbnail.source_image = person_02.png` (メルセンヌ・サークル
集会、複数人物 + 楽器類) を選定して完成 → 視聴者識別性 ✗ で user 指摘で発覚。
修正は `intro_01.png` (パスカル単独 portrait) に変更 + thumbnail rebuild。

従来 pipeline の thumbnail check は smoke_test `check_thumbnail_source_image`
の「scene_def に basename が存在するか」 lint のみ。**「該当 image が portrait か /
集会か / 風景か」「視聴者識別性」自動判定なし** が構造的 gap。

本 script はこの failure mode の自動検出を提供する。

## 使い方

```bash
python src/qa_thumbnail_vision.py examples/moriarty/episode_config.json
```

WARN exit code 1、PASS exit code 0。pipeline.py thumbnail step 末尾に統合。

## 判定基準

- **PASS (OK)**: type == "portrait" AND identifiable == true
- **WARN**: type in {"group_scene", "landscape", "abstract"} OR identifiable == false

WARN は hard failure ではなく、user に視覚 review を促す。
"""

import argparse
import json
import os
import re
import sys
import tempfile


def _call_claude_cli(prompt: str, debug: bool = False) -> str | None:
    """Call Claude Code CLI with a text prompt (image file paths referenced inside).

    Uses the same file-based I/O pattern as qa_image_checker._call_claude_cli.
    Claude Code reads image files directly via its Read tool.
    Runs under Max subscription — no API key or additional cost.
    """
    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, "_tmp_qa_thumb_prompt.txt")
    output_path = os.path.join(tmp_dir, "_tmp_qa_thumb_output.txt")
    error_path = os.path.join(tmp_dir, "_tmp_qa_thumb_error.txt")

    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(prompt)

        for p in [output_path, error_path]:
            if os.path.exists(p):
                os.remove(p)

        # --allowedTools Read,Bash required for Claude CLI v2.1.63+
        cmd = (
            f'type "{prompt_path}" | claude -p --allowedTools Read,Bash --output-format text '
            f'> "{output_path}" 2> "{error_path}"'
        )

        if debug:
            print(f"    [DEBUG] Prompt: {len(prompt)} chars")
            print(f"    [DEBUG] Command: {cmd[:120]}...")

        exit_code = os.system(cmd)

        if exit_code != 0:
            if debug and os.path.exists(error_path):
                with open(error_path, encoding="utf-8", errors="replace") as f:
                    print(f"    [DEBUG] stderr: {f.read().strip()[:200]}")
            return None

        if not os.path.exists(output_path):
            return None

        with open(output_path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()

    except Exception as e:
        if debug:
            print(f"    [DEBUG] _call_claude_cli error: {e}")
        return None
    finally:
        for p in [prompt_path, output_path, error_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from response text (handles ```json blocks)."""
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def evaluate_thumbnail(thumbnail_path: str, subject: str, debug: bool = False) -> dict:
    """Evaluate a thumbnail PNG for portrait suitability.

    Returns dict with keys: type, identifiable, concern.
    On Claude CLI failure: type="unknown", identifiable=None, concern=error msg.
    """
    abs_path = os.path.abspath(thumbnail_path)
    prompt = f"""この YouTube サムネイル画像 (`{abs_path}`) を Read tool で view してから、以下を JSON で判定してください。

判定項目:
- `type`: 画像の類型を 1 つ選択
  - `"portrait"`: 1 人の人物単独の肖像 (顔が明確、上半身中心)
  - `"group_scene"`: 複数人物の集会・会議・群像 (主役識別困難)
  - `"landscape"`: 風景・建物・物体 (人物なし or 極小)
  - `"abstract"`: 抽象画・数式・グラフ・記号のみ
- `identifiable`: 視聴者が 1 秒で「{subject}」(数学史 YouTube 動画の主題者) と識別できるか (true/false)
- `concern`: 視聴者識別性・CTR への懸念事項を 60 字以内で 1 行 (なければ `"なし"`)

判定基準:
- `portrait` + `identifiable: true` が理想 (CTR 高い)
- `group_scene` / `landscape` / `abstract` は CTR 低い傾向、視聴者が主題者を 1 秒で識別できない可能性

回答は ```json コードブロックで JSON のみ出力 (説明文不要):

```json
{{
  "type": "portrait",
  "identifiable": true,
  "concern": "なし"
}}
```
"""
    response = _call_claude_cli(prompt, debug=debug)
    if response is None:
        return {"type": "unknown", "identifiable": None, "concern": "Claude CLI failed"}
    parsed = _extract_json(response)
    if parsed is None:
        return {
            "type": "unknown",
            "identifiable": None,
            "concern": f"JSON parse failed: {response[:80]}",
        }
    # Normalize
    parsed.setdefault("type", "unknown")
    parsed.setdefault("identifiable", None)
    parsed.setdefault("concern", "")
    return parsed


def main():
    parser = argparse.ArgumentParser(description="Thumbnail Vision QA")
    parser.add_argument("episode_config", help="Path to episode_config.json")
    parser.add_argument(
        "--thumbnails-dir",
        default=None,
        help="Override thumbnails directory (default: <episode_dir>/thumbnails)",
    )
    parser.add_argument("--debug", action="store_true", help="Verbose Claude CLI debug output")
    args = parser.parse_args()

    with open(args.episode_config, encoding="utf-8") as f:
        config = json.load(f)

    subject = (
        config.get("mathematician_ja")
        or config.get("mathematician")
        or config.get("subject_en")
        or "主題者"
    )

    ep_dir = os.path.dirname(os.path.abspath(args.episode_config))
    thumbnails_dir = args.thumbnails_dir or os.path.join(ep_dir, "thumbnails")

    if not os.path.isdir(thumbnails_dir):
        print(f"[QA-THUMB] thumbnails directory not found: {thumbnails_dir}")
        return 0

    thumbnail_files = sorted(f for f in os.listdir(thumbnails_dir) if f.endswith(".png"))
    if not thumbnail_files:
        print("[QA-THUMB] no thumbnail PNGs found")
        return 0

    print(f"\n[QA-THUMB] Vision QA on {len(thumbnail_files)} thumbnail(s) for subject: {subject}")
    warnings = 0
    results = []
    for tf in thumbnail_files:
        tpath = os.path.join(thumbnails_dir, tf)
        result = evaluate_thumbnail(tpath, subject, debug=args.debug)
        type_ = result.get("type", "unknown")
        identifiable = result.get("identifiable")
        concern = result.get("concern", "")

        # Status determination
        status = "OK"
        if type_ in ("group_scene", "landscape", "abstract"):
            status = "WARN"
            warnings += 1
        elif identifiable is False:
            status = "WARN"
            warnings += 1
        elif type_ == "unknown":
            status = "WARN"  # CLI/JSON failure → safe-side warn
            warnings += 1

        results.append({"file": tf, "status": status, **result})
        identifiable_str = "yes" if identifiable is True else "no" if identifiable is False else "?"
        print(
            f"  [{status}] {tf}: type={type_}, identifiable={identifiable_str}, concern={concern}"
        )

    if warnings > 0:
        print(
            f"\n[QA-THUMB] {warnings} thumbnail warning(s) -- review thumbnails "
            "for portrait suitability (CTR proxy). To suppress: change "
            "`thumbnail.source_image` in episode_config to a single-person portrait scene."
        )
        return 1
    else:
        print("\n[QA-THUMB] All thumbnails PASS portrait suitability check")
        return 0


if __name__ == "__main__":
    sys.exit(main())
