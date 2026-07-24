#!/usr/bin/env python3
"""manim_text_collision_qa.py - deterministic text-collision preflight for Manim scenes.

Why: manim_vision_qa (Sonnet vision, post-render) caught SOME crowding but
MISSED the gp_ap / curve label proximity -- it returned "Warns 0" and the user found
those by eye. The static smoke_test Y-clearance lint only sees literal move_to y-coords
and only the subtitle band, so computed positions (y_q - 0.45, ys=[...], next_to) and
text-vs-text crowding slip through. This is the missing DETERMINISTIC net:

  run each Manim mode's construct() with a no-render mock -> capture every Text/MathTex
  bounding box at its final position -> flag pairs that overlap HORIZONTALLY (so they
  share a column, not merely different labels on one row) AND overlap / near-touch
  VERTICALLY (stacked labels crammed together).

Every ある回 crowding case was an actual bbox overlap (gap < 0): math_02/07/closing_01
(caught late by vision) and gp_ap/curve (missed by vision). Flagging gap < Y_GAP_MAX
catches them all while never firing on side-by-side labels (no x-overlap) or a single
multi-line Text (one bbox). Advisory; complements (does not replace) manim_vision_qa.

Usage:
    python scripts/manim_text_collision_qa.py episodes/XXX/scene_definition.json
    python scripts/manim_text_collision_qa.py --template log_multiply_to_add --mode gp_ap
"""

import argparse
import json
import os
import sys

# Flag a pair when their columns overlap by more than this (scene units) -- avoids
# treating two labels that merely brush at the edge as a collision.
X_OVERLAP_MIN = 0.12
# Flag when the vertical gap between the two bboxes is below this. <=0 is a real
# overlap; a small positive buffer catches near-touching stacks. Calibrated so shipped
# templates stay clean (0 FP) while ある回's ~0.05-overlap gp_ap/curve fire.
Y_GAP_MAX = 0.03

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "manim_templates"
)


def _capture_text_bboxes(template: str, params: dict, duration: float = 20.0) -> list[dict]:
    """Run the template's Scene.construct() with a no-render mock and return every
    Text/MathTex bounding box: {label, xl, xr, yb, yt}. The mock overrides play/wait so
    no frame is rendered (fast); move_to/arrange/next_to still position mobjects, so the
    final layout is captured. always_redraw dots/lines are not Text -> ignored."""
    if _TEMPLATES_DIR not in sys.path:
        sys.path.insert(0, _TEMPLATES_DIR)
    from manim import MathTex, Text, tempconfig

    # Templates read their params (mode + data-driven keys like milestones) from
    # _manim_params.json in the cwd -- pass the scene's REAL params so data-driven
    # templates (timeline_recap) capture the actual layout, not the self-test default.
    params_path = os.path.join(os.getcwd(), "_manim_params.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump({**params, "duration": duration}, f, ensure_ascii=False)

    mod = __import__(template)
    scenes = mod.SCENES
    # Resolve the Scene: use params.mode if it is a real SCENES key; else fall back to
    # the first key -- data-driven templates (timeline_recap) omit `mode` and key SCENES
    # under a self-test name.
    mode = params.get("mode") or ""
    key = mode if mode in scenes else next(iter(scenes))
    raw = scenes[key]
    if isinstance(raw, type):
        scene_cls = raw
    else:
        cls_name = raw["class"] if isinstance(raw, dict) else raw
        scene_cls = getattr(mod, cls_name)

    class _Capture(scene_cls):
        def play(self, *anims, **kw):
            for a in anims:
                m = getattr(a, "mobject", None)
                if m is not None:
                    try:
                        self.add(m)
                    except Exception:
                        pass

        def wait(self, *a, **k):
            return None

    boxes: list[dict] = []
    with tempconfig({"quality": "low_quality", "dry_run": True}):
        scene = _Capture()
        scene.construct()

        def walk(m):
            if isinstance(m, (Text, MathTex)):
                try:
                    label = m.text if isinstance(m, Text) else m.get_tex_string()
                except Exception:
                    label = "?"
                # A whitespace-only / empty mobject has no meaningful bbox.
                if not str(label).strip():
                    return
                boxes.append(
                    {
                        "label": str(label)[:24],
                        "xl": float(m.get_left()[0]),
                        "xr": float(m.get_right()[0]),
                        "yb": float(m.get_bottom()[1]),
                        "yt": float(m.get_top()[1]),
                    }
                )
            for sm in getattr(m, "submobjects", []):
                walk(sm)

        for m in scene.mobjects:
            walk(m)
    return boxes


def find_collisions(
    boxes: list[dict], x_overlap_min: float = X_OVERLAP_MIN, y_gap_max: float = Y_GAP_MAX
) -> list[dict]:
    """Return colliding pairs: text bboxes that share a column (x-overlap > x_overlap_min)
    and overlap / near-touch vertically (gap < y_gap_max). gap = max(bottoms) - min(tops):
    positive = separated, negative = overlapping."""
    hits = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            xov = min(a["xr"], b["xr"]) - max(a["xl"], b["xl"])
            if xov <= x_overlap_min:
                continue
            gap = max(a["yb"], b["yb"]) - min(a["yt"], b["yt"])
            if gap < y_gap_max:
                hits.append(
                    {
                        "a": a["label"],
                        "b": b["label"],
                        "x_overlap": round(xov, 3),
                        "y_gap": round(gap, 3),
                    }
                )
    return hits


def _iter_manim_scenes(scene_def: dict):
    """Yield (scene_id, template, params) for each visual.type == 'manim' scene."""
    for sec in scene_def.get("sections", []):
        for s in sec.get("scenes", []):
            v = s.get("visual", {})
            if v.get("type") == "manim" and v.get("template"):
                yield s.get("scene_id", "?"), v["template"], (v.get("params") or {})


def check_scene_definition(scene_json: str) -> int:
    with open(scene_json, encoding="utf-8") as f:
        sd = json.load(f)
    targets = list(_iter_manim_scenes(sd))
    print("=" * 60)
    print("  Manim text-collision QA (deterministic bbox preflight)")
    print("=" * 60)
    total_hits = 0
    checked = 0
    errored = 0
    for scene_id, template, params in targets:
        mode = params.get("mode", "") or "-"
        try:
            boxes = _capture_text_bboxes(template, params)
        except Exception as e:  # noqa: BLE001 - never fail the build on a capture error
            errored += 1
            print(f"  [SKIP] {scene_id} ({template}:{mode}) capture error: {repr(e)[:80]}")
            continue
        checked += 1
        hits = find_collisions(boxes)
        if hits:
            total_hits += len(hits)
            print(f"  [WARN] {scene_id} ({template}:{mode}) {len(hits)} collision(s):")
            for h in hits:
                print(
                    f"      '{h['a']}' x '{h['b']}'  y_gap={h['y_gap']} x_overlap={h['x_overlap']}"
                )
        else:
            print(f"  [OK]   {scene_id} ({template}:{mode})")
    print("-" * 60)
    print(f"  Checked {checked}, collisions {total_hits}, capture-errors {errored}")
    print("  NOTE: advisory. Complements manim_vision_qa; raise labels to clear.")
    try:  # tidy the transient params file the mock capture wrote to the cwd
        os.remove(os.path.join(os.getcwd(), "_manim_params.json"))
    except OSError:
        pass
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Deterministic Manim text-collision preflight")
    p.add_argument("scene_json", nargs="?", help="Path to scene_definition.json")
    p.add_argument("--template", help="Single template module name (e.g. log_multiply_to_add)")
    p.add_argument("--mode", help="Single mode key (with --template)")
    args = p.parse_args()

    if args.template and args.mode:
        boxes = _capture_text_bboxes(args.template, {"mode": args.mode})
        hits = find_collisions(boxes)
        print(f"{args.template}:{args.mode}  texts={len(boxes)}  collisions={len(hits)}")
        for h in hits:
            print(f"  '{h['a']}' x '{h['b']}'  y_gap={h['y_gap']} x_overlap={h['x_overlap']}")
        return 0
    if args.scene_json:
        return check_scene_definition(args.scene_json)
    p.error("give scene_definition.json, or --template NAME --mode MODE")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
