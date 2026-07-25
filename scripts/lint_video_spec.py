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
import glob
import os
import re
import sys

# Windows cp932 console: the FAIL path prints a message containing characters the
# console codepage cannot encode, so the lint CRASHED instead of reporting -- and
# only on the deprecated-duration path, i.e. exactly the regression this lint
# exists to catch. It went unnoticed because that path had never been taken.
# Same guard used by the other report-printing scripts in this repo.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SSOT_PATH = os.path.join(REPO_ROOT, "docs", "02_pipeline", "VIDEO_SPEC.md")

# Tracked docs that intentionally mention the regular-episode duration.
# Add new docs here when they reference the duration.
# A tracked doc that is absent is SKIPPED, not failed: this script ships in a repo
# that carries a subset of the source tree, so some entries legitimately do not
# exist there.
TRACKED_DOCS = [
    "CLAUDE.md",
    "README.md",
    "docs/architecture.md",
    "docs/03_quality/STYLE_GUIDE.md",
    "docs/01_concept/CONTENT_PLAN.md",
]

# Docs that mention a "N〜M分" range which is NOT the regular-episode duration.
# Each needs a reason: the point of listing them is that an unlisted doc gets
# reported, so a new file mentioning a duration cannot pass unnoticed.
ACKNOWLEDGED_DOCS: dict[str, str] = {
    "docs/01_concept/ROADMAP.md": "Phase 1 の完了基準 (当時の記録であって現在の仕様ではない)",
    "docs/03_quality/pitfalls.md": "再ビルド所要時間と、過去バグの記録に残る旧尺",
    "docs/03_quality/QA_PIPELINE.md": "Gate ごとの所要時間の見積り",
}

# Values that used to be canonical. Lint emits FAIL if any tracked doc
# still mentions them (sanitize miss). Update when canonical changes.
DEPRECATED_DURATIONS: list[tuple[int, int]] = [
    (10, 15),  # before 2026-03 R-1 follow-up update; sanitize-miss risk
    (8, 12),  # the original figure; outlived the update in CONCEPT.md / QA_PIPELINE.md
]

# Where to look for docs that mention a duration at all. The tracked list above is
# opt-in, and opt-in is exactly how the stale figures survived: CONCEPT.md and
# QA_PIPELINE.md each carried "8〜12分" for months because nobody added them to it.
# A doc found here that is neither tracked nor acknowledged is reported so it gets
# classified -- silence is no longer the default for an unknown file.
# Repo-root *.md is deliberately NOT swept. Root-level docs are few and are listed
# in TRACKED_DOCS by name; the internal status / history journals cannot be named
# here at all, because this file ships to a repo where references to them are
# rewritten to abstract placeholders -- naming them left the published lint tracking
# a file whose name was that placeholder, which of course does not exist. Sweeping
# docs/ and the rules dir covers everything that can grow a new duration mention.
DISCOVERY_GLOBS = ["docs/**/*.md", ".claude/rules/*.md"]

# ...but only over NORMATIVE docs. Session notes and planning files are full of
# unrelated time estimates ("30〜60 分" for a build step), and sweeping them in
# buried the real finding under 11 lines of noise on the first run -- the same
# too-broad failure this lint is meant to prevent in the docs themselves.
DISCOVERY_EXCLUDE_PREFIXES = (
    "docs/internal/",
    "docs/archive/",
    "docs/05_planning/",
    "docs/06_episodes/",
)

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


def discover_untriaged() -> list[str]:
    """Docs mentioning a duration range that are neither tracked nor acknowledged."""
    seen: set[str] = set()
    out: list[str] = []
    ssot_rel = os.path.relpath(SSOT_PATH, REPO_ROOT).replace(os.sep, "/")
    for pattern in DISCOVERY_GLOBS:
        for path in glob.glob(os.path.join(REPO_ROOT, pattern), recursive=True):
            rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
            if rel in seen or rel == ssot_rel:
                continue
            seen.add(rel)
            if rel.startswith(DISCOVERY_EXCLUDE_PREFIXES):
                continue
            if rel in TRACKED_DOCS or rel in ACKNOWLEDGED_DOCS:
                continue
            try:
                durs = find_all_durations(read_text(path))
            except OSError:
                continue
            if durs:
                out.append(f"{rel}: mentions {durs} but is neither tracked nor acknowledged")
    return sorted(out)


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
    print(
        f"[INFO] SSOT canonical: {canonical[0]}〜{canonical[1]} 分 (from {os.path.relpath(SSOT_PATH, REPO_ROOT)})"
    )

    failures: list[str] = []
    skipped: list[str] = []
    for rel in TRACKED_DOCS:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            skipped.append(rel)
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
                f"(sanitize miss -- replace with {canonical[0]}〜{canonical[1]} 分)"
            )
        elif args.verbose:
            print(f"  [OK] {rel}: canonical found ({len(durs)} total duration mention(s))")

    untriaged = discover_untriaged()
    for line in untriaged:
        failures.append(line)

    if failures:
        print(f"\n[FAIL] {len(failures)} issue(s):")
        for line in failures:
            print(f"  - {line}")
        if untriaged:
            print(
                "\n  A doc mentioning a duration must be classified: add it to\n"
                "  TRACKED_DOCS (it states the episode duration and must match canonical)\n"
                "  or to ACKNOWLEDGED_DOCS with a reason (the range means something else)."
            )
        return 1

    if skipped:
        print(f"[INFO] {len(skipped)} tracked doc(s) absent from this checkout: {skipped}")
    print(
        f"[PASS] {len(TRACKED_DOCS) - len(skipped)} tracked docs mention canonical "
        f"{canonical[0]}〜{canonical[1]} 分; "
        f"{len(ACKNOWLEDGED_DOCS)} doc(s) acknowledged as unrelated; no untriaged doc."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
