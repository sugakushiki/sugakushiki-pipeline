#!/usr/bin/env python3
"""
qa_image_checker.py - Gate 2: Image Quality Check

Evaluates generated images against their source_prompt and narration using
Claude Sonnet Vision via Claude Code CLI (Max subscription, no additional cost).
Also checks cross-scene consistency of the main subject.

Role distinction:
    This module (qa_image_checker.py) is Gate 2 standalone, using Claude Sonnet
    Vision for higher-accuracy evaluation including cross-scene consistency.
    In contrast, image_generator.py's evaluate_image_quality() is an inline
    check (also Claude Sonnet via CLI) for basic quality gating during generation.
    Both use the same model via Claude Code CLI but serve different purposes.

Usage:
    python src/qa_image_checker.py examples/moriarty/scene_definition.json
    python src/qa_image_checker.py examples/moriarty/scene_definition.json --output qa_report_images.json
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime


def _call_claude_cli(prompt: str, debug: bool = False) -> str | None:
    """Call Claude Code CLI with a text prompt (which may reference image file paths).

    Uses the same file-based I/O pattern as claude_backend.py.
    Claude Code reads image files directly via its Read tool.
    Runs under Max subscription — no API key or additional cost.

    Returns response text, or None on failure.
    """
    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, "_tmp_gate2_prompt.txt")
    output_path = os.path.join(tmp_dir, "_tmp_gate2_output.txt")
    error_path = os.path.join(tmp_dir, "_tmp_gate2_error.txt")

    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(prompt)

        for p in [output_path, error_path]:
            if os.path.exists(p):
                os.remove(p)

        cmd = (
            f'type "{prompt_path}" | claude -p --output-format text '
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


def evaluate_single_scene(scene: dict, image_path: str) -> dict:
    """Evaluate a single image against its scene definition."""
    visual = scene.get("visual", {})
    source_prompt = visual.get("source_prompt", "")
    narration = " ".join(scene.get("narration", []))
    scene_id = scene.get("scene_id", "unknown")

    abs_path = os.path.abspath(image_path)

    prompt = f"""以下の画像ファイルを読んで評価してください。
画像ファイル: {abs_path}

【シーンID】{scene_id}
【ナレーション】{narration}
【生成プロンプト（source_prompt）】{source_prompt}

以下の観点で評価し、JSONのみ（```なし）で回答してください。

1. 時代・場所の適切性 [warning]
   ナレーションとプロンプトが示す時代・場所と画像が合っているか。

2. 人物描写の適切性 [warning]
   プロンプトが指定する人物の特徴（年齢、服装、民族等）と画像の人物が合っているか。

3. 雰囲気・構図 [info]
   oil painting style, academic realism が実現されているか。

4. ナレーションとの整合性

   4-1. 主要人物の有無 [critical: 完全欠落 / warning: 一部欠落]
        source_prompt または narration が固有名・続柄・年齢で言及する主要人物
        （例: 父Rudolf、母Marianne、兄Rudolf、6歳の少年など）が画像に描かれているか。
        判定例:
        - source_prompt が「young boy of about six」を指定しているのに画像に該当年齢層の
          少年が見当たらず女性のみが描かれている → critical
        - narration が「父・母・兄の3人家族」と言うのに画像に1人しかいない → critical
        - 一人だけ欠落（4人家族 narration vs 3人画像） → warning

   4-2. 人物の性別 [critical: 逆転 / warning: 部分逆転]
        source_prompt または narration が示す性別（boy=男性、woman=女性、
        父=男性、母=女性、兄=男性等）と画像の人物の性別の整合性。
        判定例:
        - source_prompt が boy/man なのに画像が明らかに girl/woman → critical
        - 毛布や帽子で部分的に隠れていても髪型・顔立ち・体格・服装から女性的（または
          男性的）に見える場合は critical（Vision の「判別困難」を理由に severity を
          下げないこと。明らかに source_prompt の性別と異なる印象なら critical を維持）
        - narration が示す主要人物の性別と画像が逆転 → critical
        - 補助人物の性別不整合 → warning
        この観点は 4-1 主要人物の有無 と密接で、性別逆転は通常人物欠落と同時に発生する
        （指定人物が存在せず別性別の人物が描かれる）。

   重要 [aspect 優先順位]: 4-1 主要人物の有無 / 4-2 人物の性別 に該当する不整合は
   必ず aspect "主要人物の有無" / "人物の性別" として報告し、aspect "人物描写" (item 2)
   には書かないこと。"人物描写" (item 2) は source_prompt の指定（年齢層の細部、服装の
   スタイル、民族特徴など）と画像の整合性のうち、4-1/4-2 に該当しないもの（例:
   服装の色合い、髪型のスタイル等）に限定する。

   4-3. 人物の人数 [warning]
        narration「3人家族」 vs 画像「2人」のような数の不整合。
        narration が複数人を言及するのに画像が1人だけの場合等。

   4-4. 活動・小道具 [warning]
        narration が言及しない強い視覚要素（例: 全員パイプ喫煙、全員ワイングラス）が
        あり、史実的根拠が弱そうなステレオタイプの場合。

   4-5. 細部 [info]
        服装の色、家具の形状、その他細部の不整合。

JSONフォーマット:
{{
  "overall": "pass" | "warning" | "critical",
  "issues": [
    {{
      "severity": "critical" | "warning" | "info",
      "aspect": "時代・場所" | "人物描写" | "雰囲気・構図" | "主要人物の有無" | "人物の性別" | "人物の人数" | "活動・小道具" | "細部",
      "message": "問題の説明（日本語、1〜2文）",
      "suggestion": "改善の提案（日本語、1文）"
    }}
  ],
  "positive": "良い点（日本語、1文）"
}}

critical は明らかに・確実に間違っている場合のみ。FP（誤検出）を避けるため、判断が
難しい場合は warning または info に下げること。例:
- ナレーションが「父・母・兄の3人家族」と言うのに画像に女性2人しかいない → critical
- 現代の人物なのに古代ローマの服装 → critical
- narration が示唆しない服装のディテール（色違い等） → info

issuesがない場合は [] とすること。"""

    try:
        text = _call_claude_cli(prompt)
        if text is None:
            return {
                "scene_id": scene_id,
                "status": "error",
                "error": "Claude Code CLI returned no output",
            }
        result = _extract_json(text)
        if result is None:
            return {
                "scene_id": scene_id,
                "status": "parse_error",
                "error": f"JSON parse failed: {text[:100]}",
            }
        return {"scene_id": scene_id, "status": "ok", "result": result}
    except Exception as e:
        return {"scene_id": scene_id, "status": "error", "error": str(e)}


def evaluate_consistency(scenes_with_images: list[dict]) -> dict:
    """Check cross-scene consistency of the main subject across person/intro scenes.

    ある回 強化: visual.is_subject=false のシーン (脇役・別人物、例 テオン/シネシオス) は
    除外する。従来は intro+person 全シーンを「主人公」前提で比較したため、脇役を別人物
    として「不統一」と誤検出していた。無印は is_subject=true 扱い (後方互換)。主題者シーンが2枚未満なら
    比較対象なしとして skip する。
    """
    # intro + person セクションかつ主題者シーンのみ対象 (脇役は is_subject=false で除外)
    target = [
        s
        for s in scenes_with_images
        if s["scene"].get("section_id") in ("intro", "person")
        and s["image_path"] is not None
        and s["scene"].get("visual", {}).get("is_subject", True)
    ][:8]  # 最大8枚

    if len(target) < 2:
        return {"status": "skip", "reason": "対象シーンが2枚未満"}

    # Build image file list for the prompt
    image_lines = []
    scene_ids = []
    for i, s in enumerate(target):
        scene_id = s["scene"]["scene_id"]
        abs_path = os.path.abspath(s["image_path"])
        image_lines.append(f"[画像{i + 1}: {scene_id}] {abs_path}")
        scene_ids.append(scene_id)

    images_text = "\n".join(image_lines)

    prompt = f"""以下の{len(target)}枚の画像ファイルを読んで、人物描写の一貫性を評価してください。

画像ファイル一覧:
{images_text}

これらは同一の数学者を主人公とするドキュメンタリー動画の各シーンです。
シーンID: {", ".join(scene_ids)}

主人公（数学者）の人物描写の一貫性を評価してください:
- 外見的特徴（体型、髪、顔）が一貫しているか
- 民族・国籍の印象が一貫しているか
- 「同一人物」として認識できるか

JSONのみ（```なし）で回答:
{{
  "consistent": true | false,
  "overall_assessment": "一貫性の総合評価（日本語、1〜2文）",
  "issues": [
    {{
      "severity": "warning" | "info",
      "scenes": ["scene_id1", "scene_id2"],
      "message": "不一致の説明（日本語）",
      "suggestion": "改善案（日本語）"
    }}
  ]
}}"""

    try:
        text = _call_claude_cli(prompt)
        if text is None:
            return {"status": "error", "error": "Claude Code CLI returned no output"}
        result = _extract_json(text)
        if result is None:
            return {"status": "parse_error", "error": f"JSON parse failed: {text[:100]}"}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Gate 2: Image Quality Check")
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument("--output", default=None, help="Output path for QA report JSON")
    parser.add_argument("--images-dir", default=None, help="Override images directory")
    args = parser.parse_args()

    scene_json_path = os.path.abspath(args.scene_json)
    episode_dir = os.path.dirname(scene_json_path)
    images_dir = args.images_dir or os.path.join(episode_dir, "images")
    output_path = args.output or os.path.join(episode_dir, "qa_report_images.json")

    # Load scene definition
    with open(scene_json_path, encoding="utf-8") as f:
        scene_def = json.load(f)
    episode_id = scene_def.get("episode_id", "unknown")

    # Verify Claude Code CLI is available
    if os.system("claude --version >nul 2>&1") != 0:
        print("ERROR: Claude Code CLI not found.")
        print("  Install Claude Code and authenticate with Max subscription.")
        print("  See: https://code.claude.com/docs/en/getting-started")
        sys.exit(1)

    # Collect ken_burns scenes
    all_scenes = []
    for section in scene_def.get("sections", []):
        section_id = section.get("section_id")
        for scene in section.get("scenes", []):
            scene = dict(scene)
            scene["section_id"] = section_id
            all_scenes.append(scene)

    ken_burns_scenes = [s for s in all_scenes if s.get("visual", {}).get("type") == "ken_burns"]

    print(f"\n{'=' * 60}")
    print("  Gate 2: Image Quality Check")
    print(f"{'=' * 60}")
    print(f"  Episode:      {episode_id}")
    print(f"  ken_burns:    {len(ken_burns_scenes)} scenes")
    print(f"  Images dir:   {images_dir}")
    print()

    start_time = time.time()

    # 画像の存在確認
    scenes_with_images = []
    missing_images = []

    for scene in ken_burns_scenes:
        scene_id = scene["scene_id"]
        image_path = os.path.join(images_dir, f"{scene_id}.png")
        if os.path.exists(image_path):
            scenes_with_images.append({"scene": scene, "image_path": image_path})
        else:
            missing_images.append(scene_id)

    print(f"  Found: {len(scenes_with_images)} images, Missing: {len(missing_images)}")
    print()

    # ── 個別シーン評価 ──────────────────────────────────────────
    all_issues = []
    scene_results = {}

    for i, item in enumerate(scenes_with_images):
        scene = item["scene"]
        scene_id = scene["scene_id"]
        print(f"  [{i + 1}/{len(scenes_with_images)}] {scene_id}...", end=" ", flush=True)
        t0 = time.time()

        eval_result = evaluate_single_scene(scene, item["image_path"])
        elapsed = time.time() - t0

        if eval_result["status"] == "ok":
            result = eval_result["result"]
            overall = result.get("overall", "pass")
            n_issues = len(result.get("issues", []))
            icon = "[OK]" if overall == "pass" else "[WARN]" if overall == "warning" else "[FAIL]"
            print(f"{icon} ({elapsed:.0f}s, {n_issues} issues)")
            scene_results[scene_id] = result
            for issue in result.get("issues", []):
                all_issues.append(
                    {
                        "scene_id": scene_id,
                        "severity": issue.get("severity"),
                        "aspect": issue.get("aspect"),
                        "message": issue.get("message"),
                        "suggestion": issue.get("suggestion"),
                    }
                )
        else:
            print(f"💥 {eval_result.get('error', '')[:60]}")
            scene_results[scene_id] = {"error": eval_result.get("error")}

    # 画像不在のissue
    for scene_id in missing_images:
        all_issues.append(
            {
                "scene_id": scene_id,
                "severity": "info",
                "aspect": "画像不在",
                "message": f"images/{scene_id}.png が存在しない（フォールバック画像使用中）",
                "suggestion": "image_generatorを再実行して画像を生成してください",
            }
        )

    # ── 一貫性チェック ──────────────────────────────────────────
    print("\n  Consistency check...", end=" ", flush=True)
    t0 = time.time()
    consistency = evaluate_consistency(scenes_with_images)
    elapsed = time.time() - t0

    if consistency["status"] == "ok":
        result = consistency["result"]
        is_ok = result.get("consistent", True)
        cons_issues = result.get("issues", [])
        print(f"{'[OK]' if is_ok else '[WARN]'} ({elapsed:.0f}s, {len(cons_issues)} issues)")
        for issue in cons_issues:
            all_issues.append(
                {
                    "scene_id": ",".join(issue.get("scenes", [])),
                    "severity": issue.get("severity", "warning"),
                    "aspect": "人物一貫性",
                    "message": issue.get("message"),
                    "suggestion": issue.get("suggestion"),
                }
            )
    elif consistency["status"] == "skip":
        print(f"⏭️  {consistency.get('reason')}")
    else:
        print(f"💥 {consistency.get('error', '')[:60]}")

    # ── 集計 ──────────────────────────────────────────────────
    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")
    info_count = sum(1 for i in all_issues if i.get("severity") == "info")

    # Silent-fail detection: if every scene errored out (e.g., Claude CLI returned no
    # output across the board), the issues_count would naively report 0 issues = PASS.
    # That would mask the actual silent failure.
    # Treat "all scenes errored" as ERROR status instead of PASS.
    scenes_errored = sum(1 for r in scene_results.values() if isinstance(r, dict) and "error" in r)
    total_scenes = len(scenes_with_images)
    silent_fail_all = total_scenes > 0 and scenes_errored == total_scenes

    if silent_fail_all:
        status = "ERROR"
    elif critical_count > 0:
        status = "FAIL"
    elif warning_count > 0:
        status = "WARN"
    else:
        status = "PASS"

    total_elapsed = time.time() - start_time

    # ── レポート保存 ──────────────────────────────────────────
    report = {
        "episode_id": episode_id,
        "gate": "images",
        "status": status,
        "issues_summary": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        "scenes_checked": len(scenes_with_images),
        "scenes_missing": len(missing_images),
        "issues": all_issues,
        "scene_details": scene_results,
        "consistency": consistency,
        "elapsed_seconds": round(total_elapsed),
        "time": datetime.now().isoformat(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ── サマリー表示 ──────────────────────────────────────────
    status_icon = (
        "[PASS]"
        if status == "PASS"
        else "[WARN]"
        if status == "WARN"
        else "[ERROR]"
        if status == "ERROR"
        else "[FAIL]"
    )
    if status == "ERROR":
        print(
            f"\n[ERROR] All {total_scenes} scenes failed Vision QA — Claude CLI likely broken. "
            "Check qa_report_images.json scene_details for individual errors."
        )
    print(f"\n{'=' * 60}")
    print(f"  QA Report: {episode_id} / images")
    print(f"  Status: {status_icon}")
    print(f"  Issues: {critical_count} critical, {warning_count} warning, {info_count} info")
    print(f"  Time: {total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")
    print(f"{'=' * 60}")

    for issue in all_issues:
        sev = issue.get("severity", "info")
        icon = "[C]" if sev == "critical" else "[W]" if sev == "warning" else "[I]"
        scene_id = issue.get("scene_id", "")
        print(f"  {icon} [{scene_id}] {issue.get('message', '')}")
        if issue.get("suggestion"):
            print(f"     → {issue.get('suggestion')}")

    print(f"\n  Report saved: {output_path}")
    print(f"{'=' * 60}\n")

    # FAIL (critical issues) or ERROR (silent CLI failure) → exit 1 to alert pipeline.
    sys.exit(1 if status in ("FAIL", "ERROR") else 0)


if __name__ == "__main__":
    main()
