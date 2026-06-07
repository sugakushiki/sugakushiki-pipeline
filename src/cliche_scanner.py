"""cliche_scanner.py — source_prompt 内の時代物 cliche 検出

Detects unverified period-stereotype phrases in `source_prompt` fields of
scene_definition.json's visual blocks. Two-layer design:

  Layer 1 (always on, deterministic):
      Dictionary-based grep against ``cliche_dictionary.json`` (~30 entries
      across 6 categories: period_accessory / smoking / atmosphere / pose /
      anachronism / academic_stereotype). WARN-level — generation continues.

  Layer 2 (opt-in, LLM-based):
      Claude Sonnet review per source_prompt for "unverified atmospheric
      stereotypes". Triggered with --cliche-llm-review (default off).
      Cost: 0 (Max subscription via Claude Code CLI).

Per-scene opt-out:
    Scene's visual block may declare ``"cliche_acks": ["smoking pipe", ...]``
    to acknowledge cliches that are intentionally and verifiably correct
    for that scene (e.g. Vienna Circle smoking IS verified, opt-out lets the
    scanner stay silent).

Why it's needed (B-20 background):
    A past prompt edit used "intellectuals smoking pipes and gesturing animatedly"
    as source_prompt → Gemini Flash produced a Vienna Circle scene with
    pipes that had no historical basis. The error was caught only at
    Vision QA (B-18) post-image. This scanner moves the check earlier:
    pre-image, pre-API-call.

Design twins:
    B-17 (pre_script_fact_check.py) — pre-script fact verification.
    B-20 (cliche_scanner.py)        — pre-image stereotype verification.
    Both shift errors left of the expensive image/script generation step.

Usage (standalone):
    python -m cliche_scanner episodes/021_godel/scene_definition.json
    python -m cliche_scanner --llm-review episodes/021_godel/scene_definition.json

Usage (from image_generator):
    from cliche_scanner import scan_tasks
    findings = scan_tasks(tasks, llm_review=False)
    for f in findings:
        print(f.format())
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Windows cp932 console: reconfigure stdout/stderr to UTF-8 so em-dash and
# similar Unicode in rationale text don't crash the CLI. Pattern from
# Day 6 R-1 follow-up (qa_report_reminder.py).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DICT_PATH = Path(__file__).parent / "cliche_dictionary.json"


# ─────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    scene_id: str
    term: str
    category: str
    rationale: str
    source_prompt_excerpt: str
    layer: str = "dictionary"  # or "llm"

    def format(self) -> str:
        return (
            f"  [cliche/{self.layer}] {self.scene_id} ({self.category}): "
            f"'{self.term}' — {self.rationale}\n"
            f"    excerpt: {self.source_prompt_excerpt}"
        )


@dataclass
class ScanReport:
    findings: list[Finding] = field(default_factory=list)
    scenes_scanned: int = 0
    scenes_with_findings: int = 0
    layer1_hits: int = 0
    layer2_hits: int = 0


# ─────────────────────────────────────────────────────────────────────
# Layer 1: dictionary-based scanner
# ─────────────────────────────────────────────────────────────────────


def load_dictionary(path: Path = DICT_PATH) -> list[dict]:
    """Load cliche entries (excluding meta block)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", [])


def _excerpt(prompt: str, term: str, ctx: int = 30) -> str:
    """Return a prompt fragment around the matched term for the report."""
    idx = prompt.lower().find(term.lower())
    if idx < 0:
        return prompt[:80] + ("..." if len(prompt) > 80 else "")
    start = max(0, idx - ctx)
    end = min(len(prompt), idx + len(term) + ctx)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(prompt) else ""
    return f"{prefix}{prompt[start:end]}{suffix}"


def _term_to_regex(term: str) -> re.Pattern[str]:
    """Compile a case-insensitive whole-phrase regex for a dictionary term.

    Uses \\b boundaries on the alphanumeric edges of the term so that
    'smoking pipe' (singular) does NOT match inside 'smoking pipes' (plural).
    Each individual entry must therefore appear as its own dictionary line.
    Hyphens and punctuation inside the term are preserved literally.
    """
    return re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)


def scan_prompt_dictionary(
    scene_id: str,
    prompt: str,
    cliche_acks: list[str],
    entries: list[dict],
) -> list[Finding]:
    """Scan a single source_prompt against the cliche dictionary.

    cliche_acks is a list of term strings that the scene explicitly
    acknowledges as historically verified. Matched terms in this list are
    NOT reported (opt-out per scene).

    Uses word-boundary regex (see _term_to_regex) so that singular vs plural
    forms are distinguished — both 'smoking pipe' and 'smoking pipes' need
    their own dictionary entries to be reported separately.
    """
    if not prompt:
        return []
    findings: list[Finding] = []
    acks_lower = {a.lower().strip() for a in cliche_acks}
    for entry in entries:
        term = entry["term"]
        term_lower = term.lower()
        if term_lower in acks_lower:
            continue
        if not _term_to_regex(term).search(prompt):
            continue
        findings.append(
            Finding(
                scene_id=scene_id,
                term=term,
                category=entry["category"],
                rationale=entry["rationale"],
                source_prompt_excerpt=_excerpt(prompt, term),
                layer="dictionary",
            )
        )
    return findings


# ─────────────────────────────────────────────────────────────────────
# Layer 2: LLM-based scanner (opt-in)
# ─────────────────────────────────────────────────────────────────────


LLM_REVIEW_PROMPT_TEMPLATE = """\
You are a historical-accuracy reviewer for visual prompts used in a math-
history documentary. Examine the following source_prompt for *unverified*
period stereotypes — i.e. atmospheric or stylistic cliches that were added
without specific historical basis for the depicted person, era, or event.

Examples of stereotypes to flag:
  - Generic 'Victorian smoking' added to a scene without a tobacco-related
    record for the subject.
  - 'Powdered wig' for a 19th-century scientist (out of period).
  - 'Candle-lit' for a daytime venue.

Do NOT flag accurately depicted period detail (e.g. a verified portrait
description). Do NOT flag the rest of the prompt — focus only on stereotypes.

Output format (one entry per line, or empty if no issues):
  TERM | RATIONALE

scene_id: {scene_id}
source_prompt: {prompt}
"""


# Sentinel module-level flag that scan_tasks() checks once per run to print
# a one-line "Layer 2 is stub" warning instead of silently returning empty
# results when --cliche-llm-review is enabled.
LAYER2_IS_STUB = True


def scan_prompt_llm(scene_id: str, prompt: str, cliche_acks: list[str]) -> list[Finding]:
    """LLM review via Claude Sonnet. Returns findings (empty list on no issues
    or call failure). Defensive: never raises into the pipeline.

    Implementation note: dispatches via Claude Code CLI (os.system + temp file)
    pattern documented in CLAUDE.md / claude_backend.py. Subprocess.run is
    forbidden on Windows for Claude CLI calls.

    For now this is a stub-friendly seam: returns [] unless a Claude backend
    is actually available. Wire to claude_backend.invoke_for_text() at the
    image_generator integration point. The LAYER2_IS_STUB module flag tells
    scan_tasks() to surface this status to users who set --cliche-llm-review.
    """
    return []


# ─────────────────────────────────────────────────────────────────────
# Top-level scanner
# ─────────────────────────────────────────────────────────────────────


def scan_tasks(
    tasks: list[dict],
    llm_review: bool = False,
    dict_path: Path = DICT_PATH,
) -> ScanReport:
    """Scan image-generation tasks (as produced by image_generator
    .extract_image_tasks). Returns a ScanReport with all findings.

    tasks: list of dicts with at least 'scene_id', 'prompt' (source_prompt),
    and optional 'cliche_acks' (list of acknowledged terms).
    """
    entries = load_dictionary(dict_path)
    report = ScanReport()
    report.scenes_scanned = len(tasks)

    # Issue 1 (s96 fix): warn explicitly when --cliche-llm-review is enabled
    # but Layer 2 is still a stub. Otherwise users see "0 llm hits" and can't
    # tell if it means "no issues" or "stub didn't run".
    if llm_review and LAYER2_IS_STUB:
        print(
            "  [cliche_scanner] WARNING: Layer 2 LLM review is currently a "
            "stub (returns 0 findings). Wire to claude_backend.invoke_for_text "
            "to activate. Layer 1 dictionary scan is unaffected."
        )

    for t in tasks:
        scene_id = t.get("scene_id", "<unknown>")
        prompt = t.get("prompt", "") or ""
        acks = t.get("cliche_acks", []) or []

        # Layer 1
        l1 = scan_prompt_dictionary(scene_id, prompt, acks, entries)
        report.layer1_hits += len(l1)
        report.findings.extend(l1)

        # Layer 2
        if llm_review:
            l2 = scan_prompt_llm(scene_id, prompt, acks)
            report.layer2_hits += len(l2)
            report.findings.extend(l2)

        if l1 or (llm_review and report.layer2_hits):
            report.scenes_with_findings += 1

    return report


def scan_scene_definition(
    scene_def_path: str | Path,
    llm_review: bool = False,
    dict_path: Path = DICT_PATH,
) -> ScanReport:
    """Standalone entry: load scene_definition.json and scan all ken_burns
    visual blocks. Used by `python -m cliche_scanner ...`.
    """
    with open(scene_def_path, encoding="utf-8") as f:
        sd = json.load(f)

    tasks = []
    for section in sd.get("sections", []):
        for scene in section.get("scenes", []):
            v = scene.get("visual", {})
            if v.get("type") != "ken_burns":
                continue
            tasks.append(
                {
                    "scene_id": scene.get("scene_id", "<unknown>"),
                    "prompt": v.get("source_prompt", ""),
                    "cliche_acks": v.get("cliche_acks", []),
                }
            )
    return scan_tasks(tasks, llm_review=llm_review, dict_path=dict_path)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


def _print_report(report: ScanReport) -> None:
    print(
        f"[cliche_scanner] {report.scenes_with_findings}/{report.scenes_scanned} "
        f"scenes flagged "
        f"({report.layer1_hits} dict, {report.layer2_hits} llm)"
    )
    for f in report.findings:
        print(f.format())


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="cliche_scanner",
        description="Detect unverified period-stereotype phrases in scene_definition source_prompts.",
    )
    p.add_argument("scene_definition", type=str, help="Path to scene_definition.json")
    p.add_argument(
        "--llm-review",
        action="store_true",
        help="Run Layer 2 LLM-based review (Claude Sonnet, opt-in).",
    )
    p.add_argument(
        "--dictionary", type=Path, default=DICT_PATH, help="Override path to cliche_dictionary.json"
    )
    args = p.parse_args(argv)

    if not os.path.exists(args.scene_definition):
        print(f"[ERROR] not found: {args.scene_definition}", file=sys.stderr)
        return 1

    report = scan_scene_definition(
        args.scene_definition,
        llm_review=args.llm_review,
        dict_path=args.dictionary,
    )
    _print_report(report)
    # Always exit 0 — WARN-level only by design.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
