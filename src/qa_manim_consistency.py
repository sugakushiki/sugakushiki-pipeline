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
import json
import os
import re
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
# It recurred in an earlier episode (Germain) / an earlier episode (Fibonacci) / an earlier episode (Cauchy) / an earlier episode
# (Daniel Bernoulli). The template's own guard only fires on PARTIAL params; a
# fully-empty {} is indistinguishable from the standalone self-test, so it
# cannot raise there. This pipeline-scope check asserts the data param so an
# empty-params reuse never reaches the assembled video (fail fast, no silent
# failures; see internal notes).
_REQUIRED_TEMPLATE_PARAMS = {
    "timeline_recap": "milestones",
}

# the sibling failure of -- the data param IS populated, but the
# scene is too SHORT to draw it. An earlier episode got a 9-milestone timeline in a
# 2.2s scene (the script generator wrote a 17-character narration for it), so the
# render stopped after the first milestone and the episode ended on a near-blank
# frame. (stale-visual) cannot see this: the mp4 length matches the audio
# exactly. Budget = max(_MIN_SCENE_SEC, _SEC_PER_ITEM * item_count).
#
# Calibrated on all 17 shipped episodes that use timeline_recap: the tightest is
# An earlier episode (9 milestones / 16.5s = 1.83 s/item), so 1.2 s/item keeps a 1.5x margin and
# yields ZERO false positives, while an earlier episode's broken 0.24 s/item is caught by ~5x.
_TEMPLATE_ITEM_BUDGET = {
    "timeline_recap": "milestones",
}
_SEC_PER_ITEM = 1.2
_MIN_SCENE_SEC = 6.0


def check_template_duration_budget(scene_def, timing):
    """Return advisory violations where a data-driven scene is too short to draw.

    Args:
        scene_def: scene_definition.json dict
        timing: timing.json dict (or its "scenes" mapping); {} disables the check.

    Returns:
        list of dicts {"scene_id", "template", "items", "duration", "required"}.
        Empty when every such scene has enough time (or timing is unavailable).
    """
    scenes_timing = timing.get("scenes", timing) if isinstance(timing, dict) else {}
    if not scenes_timing:
        return []
    violations = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "manim":
                continue
            key = _TEMPLATE_ITEM_BUDGET.get(visual.get("template"))
            if not key:
                continue
            items = (visual.get("params") or {}).get(key) or []
            if not items:
                continue  # owns the empty case
            sid = scene.get("scene_id", "?")
            duration = (scenes_timing.get(sid) or {}).get("duration")
            if not isinstance(duration, (int, float)) or duration <= 0:
                continue
            required = max(_MIN_SCENE_SEC, _SEC_PER_ITEM * len(items))
            if duration < required:
                violations.append(
                    {
                        "scene_id": sid,
                        "template": visual.get("template"),
                        "items": len(items),
                        "duration": round(float(duration), 2),
                        "required": round(required, 1),
                    }
                )
    return violations


def check_timeline_legend_coherence(scene_def):
    """Return advisory violations where a timeline colour is on screen but unnamed.

    The legend is the key that decodes the picture, and until now nothing checked
    that it decodes anything. The template itself now drops legend entries for
    unused colours and suppresses a legend too small to distinguish anything, but
    it cannot invent the LABEL for a colour that IS used and has no entry -- that
    is an editorial decision, so it is reported here.

    The rule is what makes colour meaningful: colour only carries information when
    it splits a track. A timeline where every `work` dot is gold and every `life`
    dot is white needs no legend at all, because POSITION already says which is
    which (the note under the title states it). But when one track uses two or more
    colours, the colour is making a distinction that nothing on screen explains.

    Calibrated against all 19 episodes using the template: it flags an earlier episode, an earlier episode,
    an earlier episode, an earlier episode and an earlier episode
    under a legend that names only gold, and an earlier episode splits its life track white/pink
    (転機) with no legend at all -- and passes the 6 coherent ones plus every single-colour-per-track timeline.

    Returns:
        list of dicts {"scene_id", "track", "unnamed"}; empty when coherent.
    """
    violations = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "manim" or visual.get("template") != "timeline_recap":
                continue
            params = visual.get("params") or {}
            milestones = [m for m in (params.get("milestones") or []) if len(m) >= 4]
            if not milestones:
                continue  # owns the empty case
            named = {str(c[0]) for c in (params.get("legend") or []) if len(c) >= 2}
            by_track = {}
            for m in milestones:
                by_track.setdefault(str(m[2]), set()).add(str(m[3]))
            for track, colours in sorted(by_track.items()):
                if len(colours) < 2:
                    continue  # position alone explains a single-colour track
                unnamed = sorted(colours - named)
                if unnamed:
                    violations.append(
                        {
                            "scene_id": scene.get("scene_id", "?"),
                            "track": track,
                            "unnamed": unnamed,
                        }
                    )
    return violations


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


_YEAR_RE = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)")

# Config fields whose text counts as "this episode's verified record": everything
# here has been through the pre-script fact check.
_VERIFIED_CONFIG_FIELDS = (
    "theme",
    "hook",
    "key_topics",
    "key_episodes",
    "verified_facts",
    "modern_connection",
)


def _years_in(text):
    return set(_YEAR_RE.findall(text or ""))


def _verified_claim_text(config):
    """The config text that states CLAIMS, excluding citation metadata.

    verified_facts entries are {"fact": ..., "source": ...}, and the source strings
    are dense with unrelated years (journal volumes, publication dates, "Biometrika 6
    (1908)"). Counting those as backing produced coincidental matches: an earlier episode's route
    map showed 1895 for the Oxford matriculation and the check stayed silent only
    because an editorial note elsewhere happened to contain "1895年" while discussing
    Pearson's type IV paper. Only claim text counts.
    """
    out = []
    for field in _VERIFIED_CONFIG_FIELDS:
        value = config.get(field)
        if field == "verified_facts" and isinstance(value, dict):
            for v in value.values():
                if isinstance(v, dict):
                    out.append(v.get("fact", ""))
                elif isinstance(v, str):
                    out.append(v)
        else:
            out.append(value)
    return out


def check_onscreen_years_traceable(scene_def, config):
    """Warn about on-screen years that appear nowhere else in the episode.

    lint_manim_factual_claims() reads LINT_FACTUAL_CLAIMS out of the TEMPLATE, so it
    can only police years a template hardcodes. Data-driven visuals put their years in
    the SCENE instead -- route_map's route[].year and timeline_recap's
    milestones[][0] -- and nothing checked those. An earlier episode's route map therefore showed
    "1890 カレッジへ", a year the LLM had inferred and that was simply wrong (Gosset
    entered Winchester in 1889); it was on screen, in no narration, and in no
    verified_fact.

    A year is "traceable" when it occurs in the narration OR in the config's claim
    text. Everything else is reported so the author either sources it or removes it.
    Advisory: legitimately-unspoken years exist (calibrated on the 59 shipped episodes
    -> 8 of them carry one, i.e. roughly one advisory line per seven episodes).

    KNOWN LIMIT -- this compares bare year strings, so an unrelated mention of the same
    year silently vouches for a claim it has nothing to do with. An earlier episode's map showed
    1895 for the Oxford matriculation and stayed unflagged because a note elsewhere
    discussed Pearson's 1895 paper. Missing a real problem is the safe direction for an
    advisory check (it never invents an alarm), but do not read silence as proof: the
    years a visual asserts still belong in verified_facts.

    Args:
        scene_def: scene_definition.json dict
        config: episode_config.json dict (may be None -> narration only)

    Returns:
        list of dicts {"scene_id", "kind", "years"} (empty if all traceable).
    """
    narration = " ".join(
        n
        for section in scene_def.get("sections", [])
        for scene in section.get("scenes", [])
        for n in scene.get("narration", [])
    )
    known = _years_in(narration)
    if config:
        known |= _years_in(json.dumps(_verified_claim_text(config), ensure_ascii=False))

    findings = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual") or {}
            onscreen = set()
            kind = None
            if visual.get("type") == "route_map":
                kind = "route_map"
                for step in visual.get("route") or []:
                    onscreen |= _years_in(str(step.get("year", "")))
            elif visual.get("template") == "timeline_recap":
                kind = "timeline_recap"
                for m in (visual.get("params") or {}).get("milestones") or []:
                    if isinstance(m, (list, tuple)) and m:
                        onscreen |= _years_in(str(m[0]))
            if not onscreen:
                continue
            missing = sorted(onscreen - known)
            if missing:
                findings.append(
                    {"scene_id": scene.get("scene_id", "?"), "kind": kind, "years": missing}
                )
    return findings


# ---------------------------------------------------------------------------
# misreading: the narration points at something the assigned mode does not draw.
# ---------------------------------------------------------------------------
# The user watching ある回 wrote: "矢印の説明で矢印が画面上になく理解が難しい".
# math_02 said "二つの状態と、そのあいだの四本の矢印があります" while its mode
# (converge) draws a line chart -- the arrows live in a DIFFERENT mode of the same
# template. Manim Vision QA later found the same shape in math_04 ("縦横10のますに
# 書き写します" over a plain stream of letters), so this is a class, not a one-off.
#
# Nothing deterministic could see it: the params were valid, the mode existed, the
# coordinates were legal. What was missing is that only the TEMPLATE knows what each
# mode puts on screen. So templates may declare it, and this checks the narration
# against the declaration:
#
#     LINT_VISUAL_ELEMENTS = {"two_state": ["矢印", "状態"], "converge": ["軸", "線"]}
#
# Deliberately narrow. Only words that PROMISE A PICTURE are looked for, and only
# templates that opt in are checked (absent key -> skipped, so the other 170
# templates are unaffected). advisory.
_VISUAL_NOUNS = (
    "矢印",
    "等高線",
    "折れ線",
    "棒グラフ",
    "縦軸",
    "横軸",
    "年表",
    "ます目",
    "格子",
    "座標",
)


def _extract_visual_elements(template_name, manim_dir):
    """Read the optional LINT_VISUAL_ELEMENTS dict from a template via AST."""
    path = os.path.join(manim_dir, f"{template_name}.py")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "LINT_VISUAL_ELEMENTS":
                try:
                    return ast.literal_eval(node.value)
                except Exception:
                    return None
    return None


def check_narration_names_absent_visual(scene_def, manim_dir):
    """Narration naming a visual element the assigned mode does not draw.

    Returns a list of {scene_id, template, mode, words}. Templates without
    LINT_VISUAL_ELEMENTS are skipped entirely (opt-in).
    """
    findings = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual") or {}
            if visual.get("type") != "manim":
                continue
            template = visual.get("template")
            if not template:
                continue
            declared_all = _extract_visual_elements(template, manim_dir)
            if not isinstance(declared_all, dict):
                continue
            mode = (visual.get("params") or {}).get("mode")
            declared = declared_all.get(mode)
            if declared is None:
                declared = declared_all.get("default")
            if declared is None:
                continue
            drawn = "".join(declared)
            text = " ".join(scene.get("narration") or [])
            missing = [w for w in _VISUAL_NOUNS if w in text and w not in drawn]
            if missing:
                findings.append(
                    {
                        "scene_id": scene.get("scene_id", "?"),
                        "template": template,
                        "mode": mode or "(default)",
                        "words": missing,
                    }
                )
    return findings


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
            # not match the narration. An earlier episode failure mode: math_06
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
