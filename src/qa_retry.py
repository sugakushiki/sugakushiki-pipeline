"""
qa_retry.py - QA-based script retry with comparison gate

After qa_checker finds issues in v1, this module:
1. Calls script_generator with QA feedback injected
2. Runs qa_checker on v2
3. Compares v1 vs v2 (issues, char count, diff rate)
4. Accepts v2 or rejects it (keeping v1)

Usage (called from pipeline.py):
    result = run_qa_retry(scene_json, config_json, qa_report_path, src_dir, args)
"""

import difflib
import json
import os
import shutil
import subprocess
import sys
import time

# ─── Diff calculation ────────────────────────────────────────────────────────


def extract_all_narrations(scene_def: dict) -> dict[str, str]:
    """Extract narration text per scene_id.

    Returns: {"intro_01": "文1\n文2\n...", "person_01": "...", ...}
    """
    narrations = {}

    # sections[].scenes[].narration[]
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            narr = scene.get("narration", [])
            if isinstance(narr, list):
                narrations[sid] = "\n".join(narr)
            elif isinstance(narr, str):
                narrations[sid] = narr

    # Fallback: flat scenes[]
    if not narrations:
        for scene in scene_def.get("scenes", []):
            sid = scene.get("scene_id", "")
            narr = scene.get("narration", [])
            if isinstance(narr, list):
                narrations[sid] = "\n".join(narr)
            elif isinstance(narr, str):
                narrations[sid] = narr

    return narrations


def calculate_diff_rate(v1: dict, v2: dict) -> float:
    """Calculate overall narration change rate between v1 and v2.

    Uses SequenceMatcher to compute similarity ratio.
    Returns: 0.0 (identical) to 1.0 (completely different)
    """
    v1_narr = extract_all_narrations(v1)
    v2_narr = extract_all_narrations(v2)

    v1_text = "\n\n".join(f"[{k}]\n{v}" for k, v in sorted(v1_narr.items()))
    v2_text = "\n\n".join(f"[{k}]\n{v}" for k, v in sorted(v2_narr.items()))

    if not v1_text and not v2_text:
        return 0.0
    if not v1_text or not v2_text:
        return 1.0

    ratio = difflib.SequenceMatcher(None, v1_text, v2_text).ratio()
    return 1.0 - ratio  # Convert similarity to diff rate


def format_scene_diffs(v1: dict, v2: dict) -> list[dict]:
    """Compare narration scene-by-scene.

    Returns list of diffs: [{"scene_id": ..., "diff_rate": ..., "v1": ..., "v2": ...}, ...]
    """
    v1_narr = extract_all_narrations(v1)
    v2_narr = extract_all_narrations(v2)

    all_ids = sorted(set(list(v1_narr.keys()) + list(v2_narr.keys())))
    diffs = []

    for sid in all_ids:
        t1 = v1_narr.get(sid, "")
        t2 = v2_narr.get(sid, "")

        if t1 == t2:
            continue

        if t1 and t2:
            ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
            diff_rate = 1.0 - ratio
        elif t1:
            diff_rate = 1.0  # Removed
        else:
            diff_rate = 1.0  # Added

        diffs.append(
            {
                "scene_id": sid,
                "diff_rate": round(diff_rate, 3),
                "v1_chars": len(t1),
                "v2_chars": len(t2),
                "v1_text": t1[:200],  # Truncate for display
                "v2_text": t2[:200],
            }
        )

    return diffs


def count_narration_chars(scene_def: dict) -> int:
    """Count total narration chars."""
    total = 0
    for text in extract_all_narrations(scene_def).values():
        total += len(text.replace("|", ""))
    return total


# ─── Comparison gate ─────────────────────────────────────────────────────────


def count_issues(qa_report: dict) -> dict:
    """Count issues by severity from QA report."""
    counts = {"critical": 0, "warning": 0, "info": 0}
    for agent_result in qa_report.get("agents", {}).values():
        for issue in agent_result.get("issues", []):
            sev = issue.get("severity", "info")
            counts[sev] = counts.get(sev, 0) + 1
    return counts


def compare_gate(
    v1_sd: dict,
    v2_sd: dict,
    v1_report: dict,
    v2_report: dict,
    max_diff_rate: float = 0.20,
    char_min: int = 2600,
    char_max: int = 3200,
) -> dict:
    """Run comparison gate between v1 and v2.

    Returns:
        {
            "accepted": True/False,
            "reasons": ["..."],
            "v1_issues": {...},
            "v2_issues": {...},
            "diff_rate": float,
            "v2_chars": int,
            "scene_diffs": [...]
        }
    """
    v1_issues = count_issues(v1_report)
    v2_issues = count_issues(v2_report)
    diff_rate = calculate_diff_rate(v1_sd, v2_sd)
    v2_chars = count_narration_chars(v2_sd)
    scene_diffs = format_scene_diffs(v1_sd, v2_sd)

    reasons = []
    accepted = True

    # Check 1: v2 must not have more critical+warning issues
    v1_serious = v1_issues["critical"] + v1_issues["warning"]
    v2_serious = v2_issues["critical"] + v2_issues["warning"]

    if v2_serious > v1_serious:
        reasons.append(f"Issues increased: v1={v1_serious} → v2={v2_serious} (critical+warning)")
        accepted = False
    else:
        reasons.append(f"Issues OK: v1={v1_serious} → v2={v2_serious} (critical+warning)")

    # Check 2: char count within range
    if v2_chars < char_min or v2_chars > char_max:
        reasons.append(f"Char count out of range: {v2_chars} (target: {char_min}-{char_max})")
        accepted = False
    else:
        reasons.append(f"Char count OK: {v2_chars}")

    # Check 3: diff rate within limit
    if diff_rate > max_diff_rate:
        reasons.append(f"Diff rate too high: {diff_rate:.1%} (max: {max_diff_rate:.0%})")
        accepted = False
    else:
        reasons.append(f"Diff rate OK: {diff_rate:.1%}")

    return {
        "accepted": accepted,
        "reasons": reasons,
        "v1_issues": v1_issues,
        "v2_issues": v2_issues,
        "diff_rate": round(diff_rate, 4),
        "v2_chars": v2_chars,
        "scene_diffs": scene_diffs,
    }


# ─── Console output ─────────────────────────────────────────────────────────


def print_comparison(gate_result: dict):
    """Print comparison gate results to console."""
    print(f"\n{'─' * 50}")
    print("  Comparison Gate: v1 vs v2")
    print(f"{'─' * 50}")

    for reason in gate_result["reasons"]:
        icon = "✅" if "OK" in reason else "❌"
        print(f"  {icon} {reason}")

    print(f"\n  Changed scenes ({len(gate_result['scene_diffs'])}):")
    for d in gate_result["scene_diffs"]:
        print(
            f"    {d['scene_id']}: {d['diff_rate']:.0%} changed "
            f"({d['v1_chars']}→{d['v2_chars']} chars)"
        )

    if gate_result["accepted"]:
        print("\n  🟢 v2 ACCEPTED")
    else:
        print("\n  🔴 v2 REJECTED — v1 retained")

    print(f"{'─' * 50}")


# ─── Main orchestration ─────────────────────────────────────────────────────


def run_qa_retry(
    scene_json: str,
    config_json: str,
    qa_report_path: str,
    src_dir: str,
    model: str = "claude",
    quick: bool = True,
    use_gemini_fact: bool = False,
    max_diff_rate: float = 0.20,
    debug: bool = False,
) -> dict:
    """Run QA retry cycle: re-generate with feedback → re-QA → compare.

    Args:
        scene_json: Path to scene_definition.json (v1)
        config_json: Path to episode_config.json
        qa_report_path: Path to v1's QA report
        src_dir: Path to src/ directory
        model: Model for script_generator
        quick: Use quick QA mode
        max_diff_rate: Maximum allowed diff rate (0.0-1.0)
        debug: Debug mode

    Returns:
        {
            "action": "accepted" | "rejected",
            "v1_path": str,
            "v2_path": str | None,
            "gate_result": dict,
            "v2_report_path": str | None,
        }
    """
    episode_dir = os.path.dirname(scene_json)

    print(f"\n{'=' * 60}")
    print("  QA Retry: Re-generating script with QA feedback")
    print(f"{'=' * 60}")

    # ── Step 1: Backup v1 ──
    v1_backup = os.path.join(episode_dir, "scene_definition_v1.json")
    shutil.copy2(scene_json, v1_backup)
    print(f"  v1 backup: {v1_backup}")

    with open(scene_json, encoding="utf-8") as f:
        v1_sd = json.load(f)
    with open(qa_report_path, encoding="utf-8") as f:
        v1_report = json.load(f)

    # ── Step 2: Re-generate with QA feedback ──
    print("\n  Re-generating script with QA feedback...")

    regen_cmd = [
        sys.executable,
        os.path.join(src_dir, "script_generator.py"),
        config_json,
        "--output",
        scene_json,
        "--model",
        model,
        "--qa-feedback",
        qa_report_path,
        "--manim-templates",
        os.path.join(src_dir, "manim_templates"),
    ]
    if debug:
        regen_cmd.append("--debug")

    regen_start = time.time()
    result = subprocess.run(regen_cmd)
    regen_elapsed = time.time() - regen_start

    if result.returncode != 0:
        print(
            f"\n  ❌ Script re-generation failed (exit {result.returncode}, {regen_elapsed:.0f}s)"
        )
        # Restore v1
        shutil.copy2(v1_backup, scene_json)
        print("  v1 restored.")
        return {
            "action": "rejected",
            "v1_path": v1_backup,
            "v2_path": None,
            "gate_result": None,
            "v2_report_path": None,
        }

    print(f"  Re-generation complete ({regen_elapsed:.0f}s)")

    with open(scene_json, encoding="utf-8") as f:
        v2_sd = json.load(f)

    # ── Step 3: Run QA on v2 ──
    print("\n  Running QA on v2...")

    v2_report_path = os.path.join(episode_dir, "qa_report_script_v2.json")

    qa_cmd = [
        sys.executable,
        os.path.join(src_dir, "qa_checker.py"),
        scene_json,
        "--gate",
        "script",
        "--output",
        v2_report_path,
    ]
    if quick:
        qa_cmd.append("--quick")
    if use_gemini_fact:
        qa_cmd.append("--use-gemini-fact")

    qa_start = time.time()
    subprocess.run(qa_cmd)
    qa_elapsed = time.time() - qa_start

    print(f"  QA v2 complete ({qa_elapsed:.0f}s)")

    # Load v2 report (may not exist if QA errored)
    if os.path.exists(v2_report_path):
        with open(v2_report_path, encoding="utf-8") as f:
            v2_report = json.load(f)
    else:
        print("  ⚠️ v2 QA report not found, treating as rejected")
        shutil.copy2(v1_backup, scene_json)
        return {
            "action": "rejected",
            "v1_path": v1_backup,
            "v2_path": None,
            "gate_result": None,
            "v2_report_path": None,
        }

    # ── Step 4: Comparison gate ──
    gate_result = compare_gate(
        v1_sd,
        v2_sd,
        v1_report,
        v2_report,
        max_diff_rate=max_diff_rate,
    )

    print_comparison(gate_result)

    # ── Step 5: Accept or reject ──
    if gate_result["accepted"]:
        # v2 is now scene_definition.json (already written by script_generator)
        # Save diff report
        diff_report_path = os.path.join(episode_dir, "qa_diff_report.json")
        with open(diff_report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "action": "accepted",
                    "gate_result": gate_result,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print("  v2 accepted as scene_definition.json")
        print(f"  v1 backup: {v1_backup}")
        print(f"  Diff report: {diff_report_path}")

        return {
            "action": "accepted",
            "v1_path": v1_backup,
            "v2_path": scene_json,
            "gate_result": gate_result,
            "v2_report_path": v2_report_path,
        }
    else:
        # Restore v1
        shutil.copy2(v1_backup, scene_json)

        # Save v2 as rejected for reference
        v2_rejected_path = os.path.join(episode_dir, "scene_definition_v2_rejected.json")
        with open(v2_rejected_path, "w", encoding="utf-8") as f:
            json.dump(v2_sd, f, ensure_ascii=False, indent=2)

        # Save diff report
        diff_report_path = os.path.join(episode_dir, "qa_diff_report.json")
        with open(diff_report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "action": "rejected",
                    "gate_result": gate_result,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "v2_rejected_path": v2_rejected_path,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print("  v1 restored as scene_definition.json")
        print(f"  v2 saved for reference: {v2_rejected_path}")
        print(f"  Diff report: {diff_report_path}")
        print("\n  手動修正する場合:")
        print(f"    v1ベース: {scene_json} を直接編集")
        print(f"    v2ベース: {v2_rejected_path} を編集 → scene_definition.json にコピー")

        return {
            "action": "rejected",
            "v1_path": v1_backup,
            "v2_path": v2_rejected_path,
            "gate_result": gate_result,
            "v2_report_path": v2_report_path,
        }
