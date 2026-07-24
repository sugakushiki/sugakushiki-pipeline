"""
axiom_substitution.py - Hilbert's axiomatic method for 数学史記

Visualizes Hilbert's insight from Grundlagen der Geometrie (1899): the
objects of geometry ("points, lines, planes") may be renamed to anything
("tables, chairs, beer mugs"), and the axioms still hold, because only the
relations between objects -- not what the objects "are" -- define the
mathematics. This is the seed of formalism.

Modes:
    substitute - A fixed incidence figure (3 points, the 3 lines joining
                 them, and the plane they span) with a constant axiom
                 caption. The category names cycle through three vocabularies
                 while the figure and the axiom never change:
                 点/直線/平面 -> 机/椅子/ビアジョッキ -> a/b/c (abstract).
                 Fixed params: 3 points (triangle), 3 lines, 1 plane,
                 name-swaps x3.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 038 (Hilbert), the axiomatics beat.
"""

import numpy as np
from manim import (
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Polygon,
    Scene,
    Text,
    VGroup,
    config,
)
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    ACCENT_PINK,
    BG_COLOR,
    FONT,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class AxiomSubstitution(Scene):
    """Hilbert's axiomatic substitution. Single mode branch."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        _mode = params.get("mode", "substitute")
        self.build_substitute()

    def build_substitute(self):
        dur = self._duration

        # --- Title + constant axiom caption ---
        title = Text(
            "公理主義 ── 名前ではなく関係",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        axiom = Text(
            "公理: 2点を通る直線は、ただ一つ",
            font=FONT,
            font_size=24,
            color=ACCENT_CYAN,
        )
        axiom.move_to(np.array([0, 2.1, 0]))

        # --- Fixed incidence figure (3 points, 3 lines, 1 plane) ---
        pa = np.array([-2.2, 1.0, 0])
        pb = np.array([2.2, 1.0, 0])
        pc = np.array([0.0, -0.6, 0])

        plane = Polygon(
            pa,
            pb,
            pc,
            color=ACCENT_PINK,
            stroke_width=1.5,
            fill_color=ACCENT_PINK,
            fill_opacity=0.12,
        )
        lines = VGroup(
            Line(pa, pb, color=ACCENT_CYAN, stroke_width=3),
            Line(pb, pc, color=ACCENT_CYAN, stroke_width=3),
            Line(pc, pa, color=ACCENT_CYAN, stroke_width=3),
        )
        dots = VGroup(
            Dot(pa, radius=0.11, color=ACCENT_GOLD),
            Dot(pb, radius=0.11, color=ACCENT_GOLD),
            Dot(pc, radius=0.11, color=ACCENT_GOLD),
        )

        # --- Legend markers (fixed); only the names below them swap ---
        cols_x = [-3.4, 0.0, 3.4]
        marker_y = -1.05
        name_y = -1.55
        dot_marker = Dot(np.array([cols_x[0], marker_y, 0]), radius=0.11, color=ACCENT_GOLD)
        line_marker = Line(
            np.array([cols_x[1] - 0.35, marker_y, 0]),
            np.array([cols_x[1] + 0.35, marker_y, 0]),
            color=ACCENT_CYAN,
            stroke_width=3,
        )
        tri_marker = Polygon(
            np.array([cols_x[2] - 0.3, marker_y - 0.18, 0]),
            np.array([cols_x[2] + 0.3, marker_y - 0.18, 0]),
            np.array([cols_x[2], marker_y + 0.22, 0]),
            color=ACCENT_PINK,
            stroke_width=1.5,
            fill_color=ACCENT_PINK,
            fill_opacity=0.18,
        )
        markers = VGroup(dot_marker, line_marker, tri_marker)

        def make_names(triple, math=False):
            g = VGroup()
            for x, label in zip(cols_x, triple, strict=False):
                if math:
                    t = MathTex(label, font_size=30, color=TEXT_WHITE)
                else:
                    t = Text(label, font=FONT, font_size=24, color=TEXT_WHITE)
                t.move_to(np.array([x, name_y, 0]))
                g.add(t)
            return g

        names1 = make_names(["点", "直線", "平面"])
        names2 = make_names(["机", "椅子", "ビアジョッキ"])
        names3 = make_names(["a", "b", "c"], math=True)

        # --- timing: spread inter-step gaps to fill duration; fixed coda ---
        total_anim = 0.6 + 3 * 0.3 + 0.6 + 0.6 + 0.6 + 0.7 + 0.7
        coda = 2.5
        gap = max(0.5, (dur - total_anim - coda) / 3)

        # --- animate ---
        self.play(FadeIn(title), run_time=0.6)
        for d in dots:
            self.play(FadeIn(d), run_time=0.3)
        self.play(FadeIn(lines), FadeIn(plane), run_time=0.6)
        self.play(FadeIn(axiom), run_time=0.6)
        self.wait(gap)

        self.play(FadeIn(markers), FadeIn(names1), run_time=0.6)
        self.wait(gap)
        self.play(FadeOut(names1), FadeIn(names2), run_time=0.7)
        self.wait(gap)
        self.play(FadeOut(names2), FadeIn(names3), run_time=0.7)
        self.wait(coda)


# Factual-claim metadata (read by qa_manim_consistency.py). No on-screen
# person/year claims; declared empty (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "substitute": {"people": [], "years": []},
}


SCENES = {
    "substitute": {
        "class": "AxiomSubstitution",
        "params": {"mode": "substitute"},
        "description": "Rename points/lines/planes to tables/chairs/beer mugs; axiom invariant",
    },
}
