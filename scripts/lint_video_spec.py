#!/usr/bin/env python
"""lint that all tracked docs mention the canonical video duration.

Reads the canonical duration from `docs/02_pipeline/VIDEO_SPEC.md` (the
SSOT) and ensures that every tracked doc contains AT LEAST ONE mention of
the canonical value. Different content types (regular / shorts / samples)
may legitimately mention other ranges, so additional mentions are OK.

This is the structural safeguard against the past sanitize-miss class of
bug (CLAUDE.md / README.md / architecture.md updated
10〜15 → 10〜19, but STYLE_GUIDE.md L232 was missed).

Detection logic:
1. Extract canonical "(low, high)" from the SSOT's marker line:
       **通常回の尺: 10〜19 分**
2. For each tracked doc, check that "(low, high)" appears at least once
   in the duration form (e.g. "10〜19 分" / "10-19分").
3. (Optional) Warn if any doc still contains values listed in the
   DEPRECATED set (previously canonical, now stale).

Usage:
    python scripts/lint_video_spec.py            # exit 0 on PASS, 1 on FAIL
    python scripts/lint_video_spec.py --verbose
"""

import argparse
import os
import re
import sys

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SSOT_PATH = os.path.join(REPO_ROOT, "docs", "02_pipeline", "VIDEO_SPEC.md")

# Tracked docs that intentionally mention the regular-episode duration.
# Add new docs here when they reference the duration.
TRACKED_DOCS = [
    "CLAUDE.md",
    "README.md",
    "docs/architecture.md",
    "docs/03_quality/STYLE_GUIDE.md",
]

# Values that used to be canonical. Lint emits FAIL if any tracked doc
# still mentions them (sanitize miss). Update when canonical changes.
DEPRECATED_DURATIONS: list[tuple[int, int]] = [
    (10, 15),  # before 2026-03 R-1 follow-up update; sanitize-miss risk
]

# SSOT canonical marker — first regex match is treated as authoritative.
SSOT_CANONICAL_RE = re.compile(r"\*\*通常回の尺:\s*(\d+)\s*[〜～~\-]\s*(\d+)\s*分\*\*")
DURATION_RE = re.compile(r"(\d+)\s*[〜～~\-]\s*(\d+)\s*分")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def find_canonical() -> tuple[int, int] | None:
    if not os.path.exists(SSOT_PATH):
        return None
    m = SSOT_CANONICAL_RE.search(read_text(SSOT_PATH))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def find_all_durations(text: str) -> list[tuple[int, int]]:
    return [(int(m.group(1)), int(m.group(2))) for m in DURATION_RE.finditer(text)]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    canonical = find_canonical()
    if canonical is None:
        print(
            f"[FAIL] SSOT canonical marker not found in {SSOT_PATH}\n"
            f"       expected line like: **通常回の尺: 10〜19 分**"
        )
        return 1
    print(f"[INFO] SSOT canonical: {canonical[0]}〜{canonical[1]} 分 (from {os.path.relpath(SSOT_PATH, REPO_ROOT)})")

    failures: list[str] = []
    for rel in TRACKED_DOCS:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            failures.append(f"{rel}: tracked doc does not exist")
            continue
        durs = find_all_durations(read_text(path))
        has_canonical = canonical in durs
        deprecated_hits = [d for d in durs if d in DEPRECATED_DURATIONS]
        if not has_canonical:
            failures.append(
                f"{rel}: canonical {canonical[0]}〜{canonical[1]} 分 not found "
                f"(found ranges: {durs or 'none'})"
            )
        elif deprecated_hits:
            failures.append(
                f"{rel}: contains DEPRECATED duration(s) {deprecated_hits} "
                f"(sanitize miss — replace with {canonical[0]}〜{canonical[1]} 分)"
            )
        elif args.verbose:
            print(f"  [OK] {rel}: canonical found ({len(durs)} total duration mention(s))")

    if failures:
        print(f"\n[FAIL] {len(failures)} issue(s):")
        for line in failures:
            print(f"  - {line}")
        return 1

    print(f"[PASS] all {len(TRACKED_DOCS)} tracked docs mention canonical {canonical[0]}〜{canonical[1]} 分.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
