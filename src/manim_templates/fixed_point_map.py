"""
fixed_point_map.py - Banach's fixed point theorem

A map that SHRINKS all distances, applied over and over, drives every
starting point to one and the same point - the only point that does not
move. In Banach's dissertation this single statement, set in a complete
metric space, hands over existence AND uniqueness of solutions of
differential equations (Picard's successive approximations, abstracted).

Deliberately different from the digit-table picture used elsewhere in the
channel for numerical iteration: here the pictures are (1) a map lying on
the land, (2) CURVES folding onto the one solution curve in function space,
(3) whole trajectories collapsing to one point.

ALL Picard iterates shown in mode 'picard' are exact: for y' = y, y(0)=1
the n-th Picard iterate is the Taylor partial sum
    y_n(x) = 1 + x + x^2/2! + ... + x^n/n!,
so the drawn curves y_0..y_4 and the limit e^x are mathematically real.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    map_metaphor - The intuition. A country outline, a shrunken rotated
              copy lying on it (the map), a second application of the same
              shrinking, and the single point they all agree on.
              Fixed params: 3 nested outlines (scale 0.45 per step,
              rotation 15 deg), 1 gold fixed point.
    picard  - THE key mode. Axes with the iterates y_0..y_4 of y'=y,
              y(0)=1 appearing one by one and folding onto the dashed
              gold solution e^x. Only y_0, y_1, y_2 carry labels - the
              later iterates are already indistinguishable from the
              solution, which is the point.
              Fixed params: 5 iterate curves on [0, 1.6], 1 dashed limit
              curve, 3 labels + 1 limit label.
    collapse - Uniqueness. Five starting points scattered in a region,
              each trajectory (4 hops of the same contraction: scale 0.45,
              rotation 40 deg) spiraling into the SAME gold point, with the
              contraction inequality on top.
              Fixed params: 5 trajectories x 4 hops, 1 gold fixed point,
              formula d(F(x),F(y)) <= q d(x,y), q < 1.

No person names and no years appear on screen in any mode - the narration
carries Banach, Picard and the dates.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Axes,
    DashedVMobject,
    Dot,
    Ellipse,
    FadeIn,
    Indicate,
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
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR

# Japanese glyphs hang ~0.17 below their centre; subtitle band starts at -2.0.
_BOTTOM_Y = -1.72

_MODES = ("map_metaphor", "picard", "collapse")
_DEFAULT_MODE = "picard"
assert _DEFAULT_MODE in _MODES

# Irregular country-ish outline for mode 'map_metaphor': fixed radii around
# the unit circle (deterministic; no randomness at import time).
_BLOB_RADII = (
    1.00,
    1.12,
    1.05,
    0.88,
    0.97,
    1.10,
    1.18,
    1.04,
    0.90,
    0.82,
    0.93,
    1.08,
    1.15,
    1.02,
    0.87,
    0.94,
)


def _contract(p, center, q, theta):
    """One application of the contraction: rotate by theta about center,
    then scale distances by q (< 1)."""
    rot = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta), np.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return center + q * (rot @ (p - center))


class FixedPointMap(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly instead of silently drawing
        # the default picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"fixed_point_map: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "map_metaphor":
            self._map_metaphor(duration)
        elif mode == "collapse":
            self._collapse(duration)
        else:
            self._picard(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    def _note(self, s, color=TEXT_WHITE, y=_BOTTOM_Y, font_size=29):
        t = Text(s, font=FONT, font_size=font_size, color=color)
        t.move_to(UP * y)
        return self._fit(t, 12.4)

    def _reveal(self, *mobjects, run_time):
        """FadeIn crisply, hold the remainder (fade + rest == run_time exactly,
        so the scene cannot overrun - an earlier episode)."""
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _pulse(self, m, run_time, color, extras=()):
        """FadeIn (m plus extras), then Indicate m, as SEPARATE plays. Never
        combine FadeIn and Indicate in one AnimationGroup: Indicate records the
        mobject's state at begin() as the restore target, and inside a shared
        group that state is the transparent pre-FadeIn one - the object ends
        invisible (found on the first an earlier episode render: both fixed-point dots
        vanished). fade + indicate + wait == run_time exactly."""
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.6, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    # -- mode: map_metaphor ------------------------------------------------------
    def _map_metaphor(self, duration):
        title = self._title("地図の上の、動かない一点")

        # Scale 1.8 / centre y=0.65 keeps the outline's lowest vertex (radius
        # 1.15 at 270 deg) at y = 0.65 - 1.8*1.15 = -1.42, clear of the note.
        center_of_land = np.array([-1.1, 0.65, 0.0])
        angles = np.linspace(0.0, 2.0 * np.pi, len(_BLOB_RADII), endpoint=False)
        base_pts = [
            center_of_land + 1.8 * r * np.array([np.cos(a), np.sin(a), 0.0])
            for r, a in zip(_BLOB_RADII, angles, strict=True)
        ]

        # The fixed point of the contraction (inside the land).
        fp = np.array([-0.35, 0.15, 0.0])
        Q, THETA = 0.45, np.deg2rad(15.0)

        gen_styles = (
            (ACCENT_CYAN, 3.4, "土地"),
            (ACCENT_GOLD, 3.0, "その地図"),
            (TEXT_DIM, 2.4, "地図の地図"),
        )
        outlines, labels = [], []
        pts = base_pts
        for color, sw, _label in gen_styles:
            poly = Polygon(*pts, color=color, stroke_width=sw)
            outlines.append(poly)
            pts = [_contract(p, fp, Q, THETA) for p in pts]
        # Labels sit clear of the outlines, stacked on the right.
        label_x = 4.55
        for (color, _sw, label_s), y in zip(gen_styles, (2.15, 1.35, 0.55), strict=True):
            t = Text(label_s, font=FONT, font_size=26, color=color)
            t.move_to(np.array([label_x, y, 0.0]))
            labels.append(t)

        fp_dot = Dot(fp, radius=0.11, color=ACCENT_PINK)
        fp_label = Text("動かない一点", font=FONT, font_size=27, color=ACCENT_PINK)
        fp_label.move_to(np.array([label_x, -0.6, 0.0]))
        fp_line = Line(
            fp + np.array([0.18, -0.06, 0.0]),
            np.array([label_x - 1.55, -0.6, 0.0]),
            color=TEXT_DIM,
            stroke_width=1.6,
        )

        note = self._note("地図と土地が、ぴったり重なる場所がただ一つある", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.1, 1.0, 0.9, 1.2, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(outlines[0], labels[0], run_time=rt[0])
        self._reveal(outlines[1], labels[1], run_time=rt[1])
        self._reveal(outlines[2], labels[2], run_time=rt[2])
        self._pulse(fp_dot, run_time=rt[3], color=ACCENT_PINK, extras=(fp_line, fp_label))
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: picard (THE key mode) ---------------------------------------------
    def _picard(self, duration):
        title = self._title("繰り返すたびに、解へ折りたたまれる")

        problem = MathTex(r"y' = y,\quad y(0) = 1", color=TEXT_WHITE)
        problem.scale(0.9)
        problem.move_to(np.array([-4.7, 2.35, 0.0]))

        axes = Axes(
            x_range=[0.0, 1.7, 1.0],
            y_range=[0.0, 5.5, 1.0],
            x_length=7.0,
            y_length=3.5,
            axis_config={
                "include_ticks": False,
                "include_tip": False,
                "stroke_width": 2.0,
                "color": TEXT_DIM,
            },
        )
        axes.move_to(np.array([-1.2, 0.45, 0.0]))

        def partial_sum(n):
            def y_n(x):
                return sum(x**k / float(math.factorial(k)) for k in range(n + 1))

            return y_n

        limit_graph = DashedVMobject(
            axes.plot(lambda x: np.exp(x), x_range=[0.0, 1.6], color=ACCENT_GOLD, stroke_width=4.0),
            num_dashes=42,
        )
        limit_label = MathTex(r"y = e^x", color=ACCENT_GOLD).scale(0.9)
        limit_label.move_to(axes.c2p(1.6, np.exp(1.6)) + np.array([0.85, 0.1, 0.0]))

        iter_specs = (
            (0, TEXT_DIM, 2.6),
            (1, TEXT_DIM, 3.0),
            (2, ACCENT_CYAN, 3.2),
            (3, ACCENT_CYAN, 3.4),
            (4, ACCENT_CYAN, 3.6),
        )
        graphs, labels = [], []
        for n, color, sw in iter_specs:
            g = axes.plot(partial_sum(n), x_range=[0.0, 1.6], color=color, stroke_width=sw)
            graphs.append(g)
            if n <= 2:
                lab = MathTex(f"y_{n}", color=color).scale(0.8)
                lab.move_to(axes.c2p(1.6, partial_sum(n)(1.6)) + np.array([0.5, 0.0, 0.0]))
                labels.append(lab)
            else:
                labels.append(None)

        note = self._note("四回目には、もう解と見分けがつかない", color=ACCENT_PINK)

        CODA = 2.8
        rt = pace(duration, [1.0, 1.0, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(problem, axes, run_time=rt[0])
        self._reveal(limit_graph, limit_label, run_time=rt[1])
        for i, (g, lab) in enumerate(zip(graphs, labels, strict=True)):
            targets = [g] if lab is None else [g, lab]
            self._reveal(*targets, run_time=rt[2 + i])
        self._reveal(note, run_time=rt[7])
        self.wait(CODA)

    # -- mode: collapse ----------------------------------------------------------
    def _collapse(self, duration):
        title = self._title("どこから始めても、同じ一点へ")

        formula = MathTex(
            r"d\!\left(F(x),\,F(y)\right) \;\le\; q \cdot d(x,y),\qquad q<1",
            color=ACCENT_CYAN,
        )
        formula.scale(0.9)
        formula.move_to(np.array([0.0, 2.32, 0.0]))
        self._fit(formula, 10.5)

        region = Ellipse(width=10.2, height=3.0, color=TEXT_DIM, stroke_width=2.0)
        region.move_to(np.array([0.0, 0.15, 0.0]))

        fp = np.array([0.25, -0.05, 0.0])
        Q, THETA = 0.45, np.deg2rad(40.0)
        starts = (
            np.array([-4.35, 0.75, 0.0]),
            np.array([-2.6, -1.05, 0.0]),
            np.array([0.4, 1.35, 0.0]),
            np.array([3.1, 0.95, 0.0]),
            np.array([4.3, -0.6, 0.0]),
        )
        trajectories = []
        for s in starts:
            pts = [s]
            for _ in range(4):
                pts.append(_contract(pts[-1], fp, Q, THETA))
            links = VGroup(
                *[
                    Line(a, b, color=TEXT_DIM, stroke_width=2.0)
                    for a, b in zip(pts[:-1], pts[1:], strict=True)
                ]
            )
            dots = VGroup(
                Dot(pts[0], radius=0.085, color=ACCENT_CYAN),
                *[Dot(p, radius=0.055, color=ACCENT_CYAN) for p in pts[1:]],
            )
            trajectories.append(VGroup(links, dots))

        fp_dot = Dot(fp, radius=0.12, color=ACCENT_GOLD)

        note = self._note("縮める写像の行き先は、ただ一点 ── 存在して、ただ一つ", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 0.9, 1.3, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(formula, run_time=rt[0])
        self._reveal(region, run_time=rt[1])
        self.play(
            AnimationGroup(
                *[FadeIn(t) for t in trajectories],
                lag_ratio=0.15,
                run_time=rt[2],
            )
        )
        self._pulse(fp_dot, run_time=rt[3], color=ACCENT_GOLD)
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "map_metaphor": ["地図", "点"],
    "picard": ["曲線", "縦軸", "横軸", "数式", "破線"],
    "collapse": ["点", "数式"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "map_metaphor": {"people": [], "years": []},
    "picard": {"people": [], "years": []},
    "collapse": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, FixedPointMap)
