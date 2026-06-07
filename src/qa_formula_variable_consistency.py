"""qa_formula_variable_consistency.py - Lint for cross-scene formula variable
mismatches in an episode.

Originally created after ある回 round-6 (math_16 vs math_17):

    math_16 (sea_island_survey double_difference)  uses: h, H, s_1, s_2, d, L
    math_17 (formula_display, same physical formulas) uses: a, h, b_1, b_2, d, s

The letter `h` had different roles between the two adjacent scenes (pole
height in math_16, island height in math_17). This silently slipped through
the manual review until a viewer pointed it out. This lint scans:

  1. all formula_display scenes -> extract variables from each formula
  2. all Manim templates referenced by other scenes -> extract MathTex
     literals (heuristic: regex over the .py file; doesn't distinguish modes)

Then it pairs ADJACENT formula-bearing scenes inside the same section and
flags pairs whose variable sets are disjoint enough to be suspicious
(Jaccard < threshold). Output is a WARN report; the lint never blocks the
pipeline. Per-pair acks can be added later if false positives appear.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Regex helpers ───────────────────────────────────────────────────────────────
# Variables: single letter (not preceded by backslash = LaTeX command) +
# optional subscript like _1, _{12}, _{ij}.
_VAR_PATTERN = re.compile(
    r"(?<!\\)([a-zA-Z])"           # leading letter not part of a LaTeX command
    r"(?:_\{?([0-9a-zA-Z]+)\}?)?"  # optional subscript
)


def extract_variables(latex: str) -> set[str]:
    """Return the set of variable names (with subscript) used in a LaTeX string.

    Strips LaTeX commands (`\\frac`, `\\cdot`, `\\text{...}`, etc.) and
    structural punctuation so what remains is roughly the "math content".
    """
    if not latex:
        return set()
    # Drop \-prefixed commands (\\frac, \\cdot, \\text, \\pi …) — they may
    # contain letters that we MUST NOT treat as variables.
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", latex)
    # Strip braces, equals, arithmetic operators, parens.
    s = re.sub(r"[{}=+\-*/()\[\]]", " ", s)
    out: set[str] = set()
    for letter, sub in _VAR_PATTERN.findall(s):
        out.add(f"{letter}_{sub}" if sub else letter)
    return out


# Scene scanners ──────────────────────────────────────────────────────────────


def _formulas_of_formula_display(params: dict) -> list[tuple[str, str]]:
    """Return [(latex, label), ...] for a formula_display visual block."""
    formulas = params.get("formulas") or []
    if not isinstance(formulas, list):
        formulas = [formulas]
    single = params.get("formula")
    if single and not formulas:
        formulas = [single]
    out: list[tuple[str, str]] = []
    for f in formulas:
        if isinstance(f, dict):
            out.append((f.get("latex", ""), f.get("label", "")))
        elif f:
            out.append((str(f), ""))
    return out


def _mathtex_literals_in_template(template_path: str) -> list[str]:
    """Heuristic: scan a Manim template .py for MathTex(r"...") literals.

    Doesn't distinguish modes (a single template can host several modes
    each with different MathTex calls). Treated as a soft lower bound on
    the set of variable letters the template ever displays.
    """
    if not os.path.exists(template_path):
        return []
    with open(template_path, encoding="utf-8") as f:
        src = f.read()
    return [
        m.group(3)
        for m in re.finditer(
            r"MathTex\s*\(\s*(r?)([\"\'])(.*?)\2",
            src,
            re.DOTALL,
        )
    ]


def collect_scene_variables(
    scene_def: dict, manim_dir: str
) -> list[dict]:
    """Walk every (section, scene) and return a list of dicts:

        {
          "section_id":   "math",
          "scene_id":     "math_17",
          "template":     "formula_display",
          "source":       "scene_def_params" | "manim_template",
          "items":        [(latex, label), ...],   # for formula_display
          "variables":    {"h", "s_1", ...},
        }

    A scene contributes to the list ONLY if it has any formula content.
    """
    out: list[dict] = []
    for sect in scene_def.get("sections", []):
        sect_id = sect.get("section_id") or sect.get("section_title") or "?"
        for sc in sect.get("scenes", []):
            v = sc.get("visual", {}) or {}
            template = v.get("template")
            params = v.get("params", {}) or {}
            scene_id = sc["scene_id"]
            if not template:
                continue
            if template == "formula_display":
                items = _formulas_of_formula_display(params)
                if not items:
                    continue
                vars_set: set[str] = set()
                for latex, _label in items:
                    vars_set |= extract_variables(latex)
                out.append(
                    {
                        "section_id": sect_id,
                        "scene_id": scene_id,
                        "template": template,
                        "source": "scene_def_params",
                        "items": items,
                        "variables": vars_set,
                    }
                )
            else:
                # Manim template -> heuristic scan of the .py file
                tmpl_path = os.path.join(manim_dir, f"{template}.py")
                literals = _mathtex_literals_in_template(tmpl_path)
                if not literals:
                    continue
                vars_set = set()
                items_for_report: list[tuple[str, str]] = []
                for lit in literals:
                    v_in_lit = extract_variables(lit)
                    if not v_in_lit:
                        continue
                    vars_set |= v_in_lit
                    items_for_report.append((lit, "(MathTex literal)"))
                if not vars_set:
                    continue
                out.append(
                    {
                        "section_id": sect_id,
                        "scene_id": scene_id,
                        "template": template,
                        "source": "manim_template",
                        "items": items_for_report,
                        "variables": vars_set,
                    }
                )
    return out


# Consistency analysis ───────────────────────────────────────────────────────


def adjacent_pair_warnings(scenes: list[dict], jaccard_floor: float = 0.4) -> list[str]:
    """Flag adjacent (consecutive in same section) formula-bearing scenes
    whose variable sets overlap LESS than `jaccard_floor`, BUT ONLY when at
    least one side is formula_display.

    Rationale: cross-topic transitions inside an episode are common
    (circle -> Pythagorean -> sea island) and naturally use disjoint
    variable conventions. The high-value signal is when a formula_display
    "summary card" scene appears adjacent to a Manim scene that already
    showed the same physical formulas: the summary MUST reuse the Manim
    scene's variables. All other pairs are
    skipped to avoid topic-boundary false positives.
    """
    warns: list[str] = []
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        if a["section_id"] != b["section_id"]:
            continue
        # Only flag pairs where AT LEAST ONE side is a formula_display
        # (= static formula card that should mirror the surrounding Manim).
        if a["template"] != "formula_display" and b["template"] != "formula_display":
            continue
        sa, sb = a["variables"], b["variables"]
        if not sa or not sb:
            continue
        common = sa & sb
        union = sa | sb
        jaccard = len(common) / len(union) if union else 1.0
        if jaccard < jaccard_floor:
            warns.append(
                f"WARN [{a['section_id']}] {a['scene_id']} ({a['template']}) "
                f"vs {b['scene_id']} ({b['template']}): "
                f"variable sets {sorted(sa)} vs {sorted(sb)} "
                f"share only {len(common)}/{len(union)} "
                f"(jaccard={jaccard:.2f}). "
                f"formula_display scenes should reuse the adjacent Manim "
                f"scene's variables."
            )
    return warns


def collide_warnings(scenes: list[dict]) -> list[str]:
    """Flag the specific pattern that triggered this lint: the same single
    letter appearing as a variable in two scenes that semantically pair up
    (e.g. an adjacent (Manim, formula_display) pair). `h` meaning pole height
    in one and island height in the other is exactly the case to catch.

    Heuristic: within an adjacent pair (same section), if the intersection
    of single-letter variables (no subscript) is non-empty but ONE side has
    that letter combined with the OTHER side's distinctive letters, flag.
    For now a simple report: "shared bare letter -> manual review".
    """
    warns: list[str] = []
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        if a["section_id"] != b["section_id"]:
            continue
        # Only bare single letters (no subscript) -- they are the most ambiguous.
        bare_a = {v for v in a["variables"] if "_" not in v}
        bare_b = {v for v in b["variables"] if "_" not in v}
        shared = bare_a & bare_b
        # Different subscripts on the same letter is a stronger signal too.
        # But to keep noise low, only flag if BOTH the shared bare letter
        # AND a disjoint variable on each side exist.
        if not shared:
            continue
        only_a = bare_a - bare_b
        only_b = bare_b - bare_a
        if only_a and only_b:
            warns.append(
                f"WARN [{a['section_id']}] {a['scene_id']} & {b['scene_id']} "
                f"share bare letters {sorted(shared)} but each ALSO defines "
                f"distinct letters ({a['scene_id']}-only={sorted(only_a)}, "
                f"{b['scene_id']}-only={sorted(only_b)}). "
                f"Check the shared letters mean the SAME quantity in both."
            )
    return warns


# CLI ─────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Lint: cross-scene formula variable consistency."
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument(
        "--manim-dir",
        default=os.path.join(os.path.dirname(__file__), "manim_templates"),
        help="Directory containing Manim template .py files",
    )
    parser.add_argument(
        "--jaccard-floor",
        type=float,
        default=0.4,
        help="Adjacency Jaccard floor (below this, warn). Default 0.4",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print the per-scene variable summary in addition to warnings.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.scene_json):
        print(f"ERROR: scene_def not found: {args.scene_json}", file=sys.stderr)
        sys.exit(2)

    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)

    scenes = collect_scene_variables(scene_def, args.manim_dir)

    if args.report:
        print("=" * 72)
        print(f"Formula-bearing scenes: {len(scenes)}")
        print("=" * 72)
        for s in scenes:
            print(
                f"  [{s['section_id']}] {s['scene_id']} ({s['template']}, "
                f"src={s['source']}) -> {sorted(s['variables'])}"
            )

    warnings = adjacent_pair_warnings(scenes, args.jaccard_floor)
    warnings += collide_warnings(scenes)

    if warnings:
        print("=" * 72)
        print(f"FORMULA VARIABLE LINT: {len(warnings)} WARN(s)")
        print("=" * 72)
        for w in warnings:
            print(w)
        # Non-blocking by design.
        sys.exit(0)
    else:
        print("[OK] qa_formula_variable_consistency: no warnings.")


if __name__ == "__main__":
    main()
