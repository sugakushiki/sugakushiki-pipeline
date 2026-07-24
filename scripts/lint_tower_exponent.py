#!/usr/bin/env python3
"""lint_tower_exponent.py - flag ambiguous power-tower prose in narration.

Background: a Fermat number
F_k = 2^(2^k) + 1 was narrated/subtitled as "2の2のk乗" -- a power tower
rendered with only ONE 乗 and no parentheses. A listener parses that as 2^(2k),
not 2^(2^k). The source data (episode_config verified_facts) was correct; the
ambiguity was introduced when the formula was turned into Japanese prose, and it
slipped through because the formula was never shown on screen as a Manim formula
(only the prime list + constructibility condition were).

This audit scans narration / narration_speech for the tower signature
"A の B の C 乗" (three short tokens, two の, a single 乗) which represents a
double exponent A^(B^C) but is written as if it had one exponent. The robust
fixes are (1) parenthesize -> "2の(2のk乗)乗", (2) spell the spoken form with an
explicit second 乗 -> "2の、2のk乗、じょう", AND (3) show the formula visually.

What it does NOT flag (verified against every existing episode):
  * fractions / roots / factorials -- "3ぶんのxの3乗" (= x^3/3), "8分の1のxの2乗",
    "二の三乗根" (cube root): excluded when 分/ぶん/階乗/かいじょう/根/ルート/√
    appears just before the match.
  * genitive の -- "コサインのbのn乗" (= cos(b^n)): the base token must start a
    word (not be the tail of a katakana word like コサイン), enforced by a
    look-behind, so ン-の-... is skipped.
  * single exponents -- "xのn乗", "aのpマイナス1乗", "2のアレフゼロ乗": only ONE の.
  * the correct explicit double-乗 form "2の2のk乗乗": a trailing 乗/じょう is
    excluded by a look-ahead.

Advisory only (WARN); never blocks a build. Wired into smoke_test.py section 12.

Usage:
    python scripts/lint_tower_exponent.py
    python scripts/lint_tower_exponent.py --strict   # exit 1 on any finding
"""

import argparse
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# single token usable as an exponent base/level: digit, latin letter, or katakana
# (variable names spoken as katakana: ケー=k, エヌ=n, エム=m, アレフ ...).
_TOK = r"[0-9A-Za-zァ-ヶー]"
# A の B の C 乗  -> A^(B^C) written with one 乗 (the ambiguity we hunt).
#  - base must START a token (look-behind: not preceded by latin/katakana/ー),
#    so "...コサインのbのn乗" (genitive の) is NOT matched on ン.
#  - not followed by another 乗/じょう (the correct explicit double-乗 form).
_TOWER_RE = re.compile(
    r"(?<![0-9A-Za-zァ-ヶー])"
    r"(" + _TOK + r")"
    r"の(" + _TOK + r"{1,3})"
    r"の(" + _TOK + r"{1,3})乗"
    r"(?!乗|じょう|ジョウ)"
)
# fraction / root / factorial markers: their presence just before a hit means the
# leading "Nの" belongs to a fraction or root, not an outer exponent.
_EXCLUDE = ("分", "ぶん", "階乗", "かいじょう", "根", "ルート", "√")
_CTX_BEFORE = 6


def find_tower_candidates(text):
    """Return list of flagged substrings in one narration string (may be empty)."""
    hits = []
    for m in _TOWER_RE.finditer(text):
        ctx = text[max(0, m.start() - _CTX_BEFORE) : m.end()]
        if any(tok in ctx for tok in _EXCLUDE):
            continue
        hits.append(m.group(0))
    return hits


def run(episodes_dir):
    """Scan every episode's scene_definition.json narration fields.

    Returns a list of findings dicts:
        {episode, scene_id, field, index, snippet}
    """
    findings = []
    for sd_path in sorted(glob.glob(os.path.join(episodes_dir, "*", "scene_definition.json"))):
        episode = os.path.basename(os.path.dirname(sd_path))
        try:
            with open(sd_path, encoding="utf-8") as f:
                sd = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for sec in sd.get("sections", []):
            for sc in sec.get("scenes", []):
                scene_id = sc.get("scene_id", "?")
                for field in ("narration", "narration_speech"):
                    for i, line in enumerate(sc.get(field, []) or []):
                        if not isinstance(line, str):
                            continue
                        for snip in find_tower_candidates(line):
                            findings.append(
                                {
                                    "episode": episode,
                                    "scene_id": scene_id,
                                    "field": field,
                                    "index": i,
                                    "snippet": snip,
                                }
                            )
    return findings


def main():
    ap = argparse.ArgumentParser(description="ambiguous power-tower prose audit")
    ap.add_argument("--episodes-dir", default=os.path.join(_ROOT, "episodes"))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any finding")
    args = ap.parse_args()

    print("=" * 64)
    print("  power-tower prose audit (A no B no C jou = A^(B^C), one jou)")
    print("=" * 64)
    findings = run(args.episodes_dir)
    if not findings:
        print("\n  PASS: no ambiguous power-tower prose found.")
        sys.exit(0)
    for f in findings:
        print(
            f"\n  [WARN] {f['episode']} {f['scene_id']} "
            f'{f["field"]}[{f["index"]}]: "{f["snippet"]}"'
        )
        print(
            "        -> parenthesize (e.g. 2の(2のk乗)乗), spell the spoken "
            "form with an explicit second 乗, AND show the formula on screen."
        )
    print(f"\n  {len(findings)} finding(s).")
    sys.exit(1 if args.strict else 0)


if __name__ == "__main__":
    main()
