"""qa_manim_consistency.py - Lint check that warns when narration is missing
factual claims (people / years) hardcoded in Manim templates.

Implements (case 丙-3): each Manim template can declare a module-level
LINT_FACTUAL_CLAIMS dict mapping mode -> {"people": [...], "years": [...]}.
Templates without this metadata are silently skipped (gradual rollout).

Format expected in each template:

    LINT_FACTUAL_CLAIMS = {
        "<mode_key>": {
            "people": [
                ["Bernoulli", "ベルヌーイ", "ヤコブ"],  # OR-list of aliases
                ["Seki", "関孝和", "関"],
            ],
            "years": ["1705", "1708", "1712", "1713"],
        },
        ...
    }

Each `people` entry is a list of aliases — narration only needs to mention
ONE alias to satisfy the check (handles Latin/kana/given-name variants).
A bare string is also accepted as a single-alias entry.

The lint reads metadata via ast.literal_eval rather than importing the
template, so Manim itself is never loaded (cheap, no side effects).
"""

import ast
import os
import sys

# Windows cp932 console: reconfigure stdout/stderr to UTF-8 so that non-ASCII
# names in WARN output (e.g. "Erdős", "Gödel") do not crash a standalone run.
# (In-pipeline this is already a no-op — pipeline_log.py reconfigures first.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _extract_claims_via_ast(template_name, manim_dir):
    """Read LINT_FACTUAL_CLAIMS dict from a template via AST parse.

    Returns: dict (parsed metadata) or None on missing/error.
    """
    path = os.path.join(manim_dir, f"{template_name}.py")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "LINT_FACTUAL_CLAIMS":
                try:
                    return ast.literal_eval(node.value)
                except Exception:
                    return None
    return None


def _get_claims_for_scene(template_name, mode, manim_dir):
    """Return claims dict for the given (template, mode), or None to skip."""
    claims_all = _extract_claims_via_ast(template_name, manim_dir)
    if not claims_all or not isinstance(claims_all, dict):
        return None
    if mode is None:
        # No mode specified: try "default" key, else first entry
        return claims_all.get("default") or next(iter(claims_all.values()), None)
    return claims_all.get(mode) or claims_all.get("default")


def _scene_narration_text(scene):
    """Concatenate narration + narration_speech into one searchable string."""
    parts = list(scene.get("narration", []))
    speech = scene.get("narration_speech")
    if speech:
        parts.extend(s for s in speech if s)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# backstop: data-driven reused templates must carry their data param.
# ---------------------------------------------------------------------------
# Reused, data-driven templates fall back to a built-in self-test default when
# their required data param is absent -- and that default is ANOTHER episode's
# data. timeline_recap with empty params {} silently renders Laplace's life
# events (誕生1749 / 大不等性 / 娘を亡くす) under the current episode's title.
# It recurred in ある回 (Germain) / ある回 (Fibonacci) / ある回 (Cauchy) / ある回
# (Daniel Bernoulli). The template's own guard only fires on PARTIAL params; a
# fully-empty {} is indistinguishable from the standalone self-test, so it
# cannot raise there. This pipeline-scope check asserts the data param so an
# empty-params reuse never reaches the assembled video (fail fast, no silent
# failures; see internal notes).
_REQUIRED_TEMPLATE_PARAMS = {
    "timeline_recap": "milestones",
}


def check_reused_template_params(scene_def):
    """Return violations for data-driven reused templates missing their param.

    A violation is a dict {scene_id, template, param} for each manim scene whose
    template is in _REQUIRED_TEMPLATE_PARAMS but whose visual.params lacks a
    non-empty value for the required key. The pipeline runs this as a fail-fast
    preflight before the (expensive) visuals render, so a template's self-test
    default never silently ships another episode's data.

    Args:
        scene_def: scene_definition.json dict

    Returns:
        list of dicts {"scene_id", "template", "param"} (empty if all OK).
    """
    violations = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "manim":
                continue
            template = visual.get("template")
            req = _REQUIRED_TEMPLATE_PARAMS.get(template)
            if not req:
                continue
            params = visual.get("params") or {}
            if not params.get(req):  # missing, None, empty list/str/dict
                violations.append(
                    {
                        "scene_id": scene.get("scene_id", "?"),
                        "template": template,
                        "param": req,
                    }
                )
    return violations


def lint_manim_factual_claims(scene_def, manim_dir):
    """warn when narration is missing factual claims (people / years)
    hardcoded in Manim templates' LINT_FACTUAL_CLAIMS metadata.

    Templates without LINT_FACTUAL_CLAIMS now emit a WARN (no silent skip):
    an un-annotated template's on-screen people/years cannot be cross-checked,
    so the gap is surfaced rather than hidden. Templates that genuinely show no
    person/year declare empty entries ({"people": [], "years": []}).

    Episode-scope check (γ): a claim is satisfied if it appears anywhere in
    the episode's narration, not only in the same scene. This suppresses
    "year already mentioned in a previous scene" false positives (e.g. astronomy-related episodes
    math_01 establishes 1796, math_02 keeps the visual without restating).

    Args:
        scene_def: scene_definition.json dict
        manim_dir: path to src/manim_templates

    Returns:
        int: number of warnings emitted (non-blocking, no exceptions)
    """
    # Pre-pass: gather narration text from the entire episode for γ scope
    episode_text_parts = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            episode_text_parts.append(_scene_narration_text(scene))
    episode_text = " ".join(episode_text_parts)

    warn_count = 0
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "manim":
                continue
            template = visual.get("template")
            if not template:
                continue
            mode = visual.get("params", {}).get("mode")
            sid = scene.get("scene_id", "?")
            tag = f"{template}/{mode}" if mode else template
            _claims_all = _extract_claims_via_ast(template, manim_dir)

            # multi-mode template selected without an explicit mode. The
            # render then falls back to the template's DEFAULT mode, which may
            # not match the narration. ある回 failure mode: math_06
            # 'mandelbrot_julia' had no mode -> defaulted to 'iteration' and
            # never drew the Mandelbrot set the narration describes (the
            # showpiece scene showed a single diverging orbit instead). math_02
            # /03/04 had the same silent-mismatch. LINT_FACTUAL_CLAIMS is keyed
            # by mode, so >1 key == multi-mode. Warn so the operator sets
            # visual.params.mode explicitly (no silent default mismatch).
            if mode is None and isinstance(_claims_all, dict) and len(_claims_all) > 1:
                _modes = ", ".join(sorted(_claims_all.keys()))
                print(
                    f"  [LINT] {sid} ({template}): multi-mode template but no "
                    f"explicit visual.params.mode -> renders DEFAULT mode "
                    f"(may mismatch narration). Modes: {_modes}"
                )
                warn_count += 1

            # No-silent-failures: a manim scene whose template carries no
            # LINT_FACTUAL_CLAIMS metadata cannot have its on-screen people /
            # years cross-checked against narration. Warn instead of skipping
            # silently — a template selected by name can render an unrelated
            # person/year (the exact failure mode this lint exists to catch).
            # Missing template files are left to visual_generator.
            if _claims_all is None:
                if os.path.exists(os.path.join(manim_dir, f"{template}.py")):
                    print(
                        f"  [LINT] {sid} ({tag}): template has no "
                        f"LINT_FACTUAL_CLAIMS metadata; on-screen claims not "
                        f"verified against narration"
                    )
                    warn_count += 1
                continue

            claims = _get_claims_for_scene(template, mode, manim_dir)
            if not claims:
                continue

            for entry in claims.get("people", []):
                aliases = entry if isinstance(entry, list) else [entry]
                if not any(alias in episode_text for alias in aliases):
                    label = "/".join(aliases)
                    print(
                        f"  [LINT] {sid} ({tag}): person '{label}' "
                        f"shown in template but absent from "
                        f"episode narration"
                    )
                    warn_count += 1

            for year in claims.get("years", []):
                if str(year) not in episode_text:
                    print(
                        f"  [LINT] {sid} ({tag}): year '{year}' "
                        f"shown in template but absent from "
                        f"episode narration"
                    )
                    warn_count += 1

    return warn_count


# ---------------------------------------------------------------------------
# CLI for standalone dry-run / debugging
# ---------------------------------------------------------------------------
def _main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Lint Manim factual-claim consistency")
    parser.add_argument("scene_definition", help="path to scene_definition.json")
    parser.add_argument(
        "--manim-templates",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "manim_templates"),
        help="directory containing Manim templates",
    )
    args = parser.parse_args()

    with open(args.scene_definition, encoding="utf-8") as f:
        scene_def = json.load(f)

    n = lint_manim_factual_claims(scene_def, args.manim_templates)
    print(f"\nTotal warnings: {n}")


if __name__ == "__main__":
    _main()
