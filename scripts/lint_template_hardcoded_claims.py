#!/usr/bin/env python3
"""lint_template_hardcoded_claims.py - find reusable Manim templates that
hardcode episode-specific person/year data.

Background (timeline_recap / Laplace class): a template named generically but
holding ONE episode's data (Laplace's chronology + title "ラプラスの歩んだ時間")
silently rendered Laplace's timeline when reused for ある回 (Germain). The
lint (qa_manim_consistency.py) only cross-checks claims that a template *declares*
in LINT_FACTUAL_CLAIMS; undeclared, non-parameterized on-screen data is invisible
to it. This audit surfaces that blind spot.

What it flags (advisory, WARN/INFO; never blocks a build):
  * SHARED template (used by >= 2 distinct episode subjects) that hardcodes a
    person name or year on screen:
      - reads data from params  -> INFO  (param-driven; verify every episode
        supplies the data params, else the hardcoded fallback renders)
      - does NOT read from params -> WARN
  * FOREIGN-name leak: a template hardcodes a subject name that is NOT a subject
    of any episode using it (e.g. a Germain template that prints "ラプラス").

Hardcoded names/years already declared in LINT_FACTUAL_CLAIMS are ignored here
. Years come from string literals (\\d{3,4}年 / N世紀);
names are matched against the distinctive katakana parts of every episode's
subject so generic katakana (ルート, シグマ ...) is not flagged.

Usage:
    python scripts/lint_template_hardcoded_claims.py
    python scripts/lint_template_hardcoded_claims.py --strict   # exit 1 on WARN
"""

import argparse
import ast
import glob
import json
import os
import re
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

YEAR_RE = re.compile(r"(?:紀元前)?\d{3,4}年|\d{1,2}世紀")
# split a subject display name into distinctive katakana parts (>= 3 chars)
_NAME_SPLIT = re.compile(r"[・＝=\s　]+")
_KATA_PART = re.compile(r"^[゠-ヿー]{3,}$")


def _subject_surname(subject: str):
    """Distinctive katakana SURNAME (last katakana part) of a subject, or None.

    Last-part-only avoids generic given-name false positives: "ポール" (Paul) and
    "アラン" (Alan) collide with common words (測量ポール, etc.), whereas surnames
    (ラプラス / ジェルマン / アーベル) are distinctive. Kanji-named subjects
    (関孝和 等) have no katakana part and are simply not name-matched (years still
    are). For "ヨハン・ベルヌーイ" -> ベルヌーイ; "ピエール=シモン・ラプラス" -> ラプラス.
    """
    parts = [p for p in _NAME_SPLIT.split(subject) if _KATA_PART.match(p)]
    return parts[-1] if parts else None


def build_usage(episodes_dir: str):
    """Return (template -> set(subjects), surname -> subject, all_subjects)."""
    template_to_subjects = defaultdict(set)
    name_part_to_subject = {}
    all_subjects = set()
    for cfg_path in glob.glob(os.path.join(episodes_dir, "*", "episode_config.json")):
        ep_dir = os.path.dirname(cfg_path)
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        subject = (
            cfg.get("mathematician_ja") or cfg.get("mathematician") or os.path.basename(ep_dir)
        )
        all_subjects.add(subject)
        surname = _subject_surname(subject)
        if surname:
            name_part_to_subject.setdefault(surname, subject)
        sd_path = os.path.join(ep_dir, "scene_definition.json")
        if not os.path.exists(sd_path):
            continue
        try:
            with open(sd_path, encoding="utf-8") as f:
                sd = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for sec in sd.get("sections", []):
            for sc in sec.get("scenes", []):
                v = sc.get("visual", {})
                if v.get("type") == "manim" and v.get("template"):
                    template_to_subjects[v["template"]].add(subject)
    return template_to_subjects, name_part_to_subject, all_subjects


def _declared_claims(tree):
    """Flattened declared (years, people-aliases) from LINT_FACTUAL_CLAIMS."""
    years, people = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "LINT_FACTUAL_CLAIMS" for t in node.targets
        ):
            try:
                claims = ast.literal_eval(node.value)
            except Exception:
                return years, people
            for c in (claims or {}).values():
                years.update(str(y) for y in c.get("years", []))
                for entry in c.get("people", []):
                    aliases = entry if isinstance(entry, list) else [entry]
                    people.update(aliases)
    return years, people


def analyze_template(path: str, name_part_to_subject: dict):
    """Return findings dict for one template file."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    string_consts = [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    years = set()
    for s in string_consts:
        years.update(YEAR_RE.findall(s))
    name_hits = {}  # name_part -> owner subject
    for s in string_consts:
        for part, subj in name_part_to_subject.items():
            if part in s:
                name_hits[part] = subj
    declared_years, declared_people = _declared_claims(tree)
    reads_params = "load_params" in src and ("params.get(" in src or "params[" in src)
    return {
        "years": years - declared_years,
        "name_hits": {p: s for p, s in name_hits.items() if p not in declared_people},
        "reads_params": reads_params,
    }


def run(episodes_dir: str, manim_dir: str):
    template_to_subjects, name_part_to_subject, _ = build_usage(episodes_dir)
    findings = []
    for path in sorted(glob.glob(os.path.join(manim_dir, "*.py"))):
        tname = os.path.splitext(os.path.basename(path))[0]
        if tname in ("style", "__init__"):
            continue
        a = analyze_template(path, name_part_to_subject)
        if a is None:
            continue
        subjects_using = template_to_subjects.get(tname, set())
        # scope = REUSED templates (the timeline_recap class). A single-use
        # template showing its own subject's data is not a reuse hazard.
        if len(subjects_using) < 2:
            continue
        years = a["years"]
        names = a["name_hits"]
        foreign = {p: s for p, s in names.items() if s not in subjects_using}
        if not (years or names):
            continue
        # WARN = the actionable timeline_recap-old class: a reused template that is
        # NOT parameterized and carries ep-specific data (biographical years, or a
        # FOREIGN person's name). INFO = param-driven (residual: verify each episode
        # supplies its data params) OR only using-subject names hardcoded (likely
        # intentional shared history, e.g. equation_history shows ガロア & アーベル).
        if not a["reads_params"] and (years or foreign):
            sev = "WARN"
            reason = "reused template is NOT parameterized but hardcodes ep-specific data"
        else:
            sev = "INFO"
            reason = (
                "param-driven; verify each episode supplies its data params"
                if a["reads_params"]
                else "hardcodes only using-subject names (verify it is intentional shared content)"
            )
        findings.append(
            {
                "template": tname,
                "severity": sev,
                "reason": reason,
                "subjects_using": sorted(subjects_using),
                "hardcoded_names": names,
                "foreign_names": foreign,
                "hardcoded_years": sorted(years),
                "reads_params": a["reads_params"],
            }
        )
    return findings


def main():
    ap = argparse.ArgumentParser
    ap.add_argument("--episodes-dir", default=os.path.join(_ROOT, "episodes"))
    ap.add_argument("--manim-templates", default=os.path.join(_SRC, "manim_templates"))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any WARN")
    args = ap.parse_args()

    print("=" * 64)
    print
    print("=" * 64)
    findings = run(args.episodes_dir, args.manim_templates)
    warns = [f for f in findings if f["severity"] == "WARN"]
    if not findings:
        print("\n  PASS: no reusable template hardcodes person/year data.")
        sys.exit(0)
    for f in findings:
        print(f"\n  [{f['severity']}] {f['template']}: {f['reason']}")
        print(f"        used by: {', '.join(f['subjects_using']) or '(none)'}")
        if f["hardcoded_years"]:
            print(f"        hardcoded years: {', '.join(f['hardcoded_years'])}")
        if f["hardcoded_names"]:
            print(f"        hardcoded names: {', '.join(f['hardcoded_names'])}")
        if f["foreign_names"]:
            print(
                f"        FOREIGN names (not a user of this template): "
                f"{', '.join(f['foreign_names'])}"
            )
        print(
            f"        param-driven: {f['reads_params']} "
            f"({'verify each episode supplies params' if f['reads_params'] else 'NOT parameterized -> move data to visual.params'})"
        )
    print(f"\n  {len(warns)} WARN / {len(findings) - len(warns)} INFO")
    sys.exit(1 if (args.strict and warns) else 0)


if __name__ == "__main__":
    main()
