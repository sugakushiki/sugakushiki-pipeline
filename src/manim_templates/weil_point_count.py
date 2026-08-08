"""
weil_point_count.py - Counting solutions mod p, and the band the count lives in

The Weil conjectures start from something anyone can do by hand: take a curve,
reduce it modulo a prime p, and count the solutions. The count N_p never strays
far from p + 1, and the size of the deviation a_p = p + 1 - N_p is controlled by
the SHAPE of the curve: for a curve of genus g the deviation always fits inside
2g*sqrt(p). For an elliptic curve (one hole) that is the band 2*sqrt(p); a curve
with two holes needs a band twice as wide. The number of holes - a topological
quantity - governs an arithmetic count. Grothendieck and Michael Artin built
etale cohomology so that "counting holes" would make sense in this setting.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    count  - Do the counting once, in full, for p = 7 on the curve
             y^2 = x^3 - x + 1. The 7x7 lattice of (x, y) pairs is drawn, the
             solutions light up in batches, and the point at infinity is added.
             Fixed params: 11 lattice solutions + 1 point at infinity = 12, so
             N_7 = 12. Side tally: N_5 = 8, N_11 = 10, N_13 = 19.
    band   - The deviation a_p = p + 1 - N_p plotted against p for the same
             curve, with the envelope +/- 2*sqrt(p) drawn over it. Every point
             sits inside the band.
             Fixed params: 13 primes 5..47; a_p = -2, -4, 2, -5, 4, -2, 1, -7,
             -3, 2, -9, -8, 9. Widest |a_p| = 9 at p = 47 against 2*sqrt(47)
             = 13.71.
    genus  - Why the width is what it is. The deviations are rescaled by
             sqrt(p) so the band becomes two straight lines at +/-2. The same 13
             primes are then counted on y^2 = x^5 + 2x^3 + 2x^2 - 3x - 1, a
             curve with TWO holes: three of its deviations break out of the
             +/-2 band, and the band has to be widened to +/-4 to hold them.
             Only the two UNAMBIGUOUS breaches are haloed (p = 17 and p = 29);
             p = 19 clears the line by 0.06 in these units, so its dot sits on
             the line and circling it would confuse rather than convince.
             Fixed params: genus-2 deviations = -4, -3, -2, -5, -13, 9, -5,
             -14, 7, -10, -12, -2, -1; the three that break +/-2*sqrt(p) are
             p = 17 (-3.15), p = 19 (+2.06) and p = 29 (-2.60) in units of
             sqrt(p); all 13 fit inside 4*sqrt(p).

Every number on screen is recomputed at import time by brute force over F_p and
checked against the values above with assertions, so the screen cannot drift
away from the narration - if the curve or the arithmetic is ever edited, the
render fails loudly instead of showing quietly wrong counts.

The genus-2 curve was chosen so that its discriminant is divisible by none of
the 13 primes drawn (every fibre shown is a smooth curve) and so that the band
is broken visibly rather than by a hair - y^2 = x^5 - x + 1 also breaks it, but
only by 0.24 and 0.11 in these units, which is invisible on screen. The elliptic
curve has discriminant -16*23, so p = 23 is a prime of bad reduction for it; its
point still lies well inside the band and is drawn with the rest.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR

_PRIMES = [5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

_E = (1, 0, -1, 1)  # x^3 - x + 1, one hole
_H = (1, 0, 2, 2, -3, -1)  # x^5 + 2x^3 + 2x^2 - 3x - 1, two holes


def _affine_points(coeffs, p):
    """Solutions (x, y) of y^2 = f(x) over F_p; coeffs highest degree first."""
    pts = []
    for x in range(p):
        v = 0
        for c in coeffs:
            v = (v * x + c) % p
        for y in range(p):
            if (y * y - v) % p == 0:
                pts.append((x, y))
    return pts


def _total(coeffs, p):
    """Projective count: the affine solutions plus the single point at infinity."""
    return len(_affine_points(coeffs, p)) + 1


_E_N = {p: _total(_E, p) for p in _PRIMES}
_E_A = {p: p + 1 - _E_N[p] for p in _PRIMES}
_H_D = {p: p + 1 - _total(_H, p) for p in _PRIMES}
_BREACH = tuple(p for p in _PRIMES if abs(_H_D[p]) > 2 * math.sqrt(p))
# Only breaches that READ as breaches get the halo. p = 19 clears the band by 0.06 in
# units of sqrt(p) -- about 4 px at this scale -- so its dot straddles the +2 line and a
# viewer cannot tell which side it is on. Highlighting it undercuts the very claim the
# scene is making, so the halo is reserved for the two unambiguous ones (the p = 19 dot
# is still drawn with the rest of the data, just not circled).
_VISIBLE_MARGIN = 2.25
_VISIBLE_BREACH = tuple(p for p in _BREACH if abs(_H_D[p]) / math.sqrt(p) >= _VISIBLE_MARGIN)

# Fail loudly rather than render quietly wrong numbers (fail fast, no silent failures).
assert [_E_N[p] for p in (5, 7, 11, 13)] == [8, 12, 10, 19]
assert [_E_A[p] for p in _PRIMES] == [-2, -4, 2, -5, 4, -2, 1, -7, -3, 2, -9, -8, 9]
assert [_H_D[p] for p in _PRIMES] == [-4, -3, -2, -5, -13, 9, -5, -14, 7, -10, -12, -2, -1]
assert all(abs(_E_A[p]) <= 2 * math.sqrt(p) for p in _PRIMES)
assert _BREACH == (17, 19, 29)
assert _VISIBLE_BREACH == (17, 29)
assert all(abs(_H_D[p]) <= 4 * math.sqrt(p) for p in _PRIMES)


class WeilPointCount(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "count")
        duration = params.get("duration", 28)
        if mode == "band":
            self._band(duration)
        elif mode == "genus":
            self._genus(duration)
        else:
            self._count(duration)

    # -- shared axes for the two scatter modes --------------------------------
    def _scatter_axes(self, y_max, y_step):
        axes = Axes(
            x_range=[0, 50, 10],
            y_range=[-y_max, y_max, y_step],
            x_length=8.5,
            y_length=3.85,
            tips=False,
            axis_config={"stroke_width": 2, "color": EDGE_COLOR, "include_ticks": True},
            # No x numbers: the horizontal axis runs through the middle of the data,
            # so its labels collide with the dots (p = 19 landed on top of "20").
            # The scale is carried by the band labels instead.
            y_axis_config={"font_size": 20},
        )
        axes.move_to(RIGHT * 0.75 + UP * 0.32)
        return axes

    # -- mode: count ----------------------------------------------------------
    def _count(self, duration):
        p = 7
        pts = _affine_points(_E, p)  # 11 solutions

        title = Text(
            "素数で割った余りの世界で、解を数える", font=FONT, font_size=30, color=ACCENT_GOLD
        )
        title.move_to(UP * 3.08)

        eq = MathTex(r"y^2 = x^3 - x + 1", font_size=34, color=TEXT_WHITE)
        eq.move_to(LEFT * 3.45 + UP * 2.28)
        modp = MathTex(r"\bmod \; 7", font_size=28, color=ACCENT_PINK)
        modp.next_to(eq, DOWN, buff=0.18)

        cell = 0.42
        cx, cy = -3.45, 0.18
        half = (p - 1) / 2

        def at(i, j):
            return RIGHT * (cx + (i - half) * cell) + UP * (cy + (j - half) * cell)

        lattice = VGroup()
        for i in range(p):
            for j in range(p):
                lattice.add(Dot(at(i, j), radius=0.038, color=EDGE_COLOR))

        x_ticks = VGroup()
        for i in range(p):
            t = Text(str(i), font=FONT, font_size=17, color=TEXT_DIM)
            t.move_to(at(i, 0) + DOWN * 0.34)
            x_ticks.add(t)
        y_ticks = VGroup()
        for j in range(p):
            t = Text(str(j), font=FONT, font_size=17, color=TEXT_DIM)
            t.move_to(at(0, j) + LEFT * 0.36)
            y_ticks.add(t)
        x_lab = MathTex("x", font_size=24, color=TEXT_DIM)
        x_lab.move_to(at(p - 1, 0) + DOWN * 0.34 + RIGHT * 0.45)
        y_lab = MathTex("y", font_size=24, color=TEXT_DIM)
        y_lab.move_to(at(0, p - 1) + LEFT * 0.36 + UP * 0.42)

        solutions = [Dot(at(i, j), radius=0.105, color=ACCENT_CYAN) for i, j in pts]

        col_x = 3.35
        head = Text("格子の上の解", font=FONT, font_size=22, color=TEXT_DIM)
        head.move_to(RIGHT * col_x + UP * 2.30)
        counter = MathTex("0", font_size=46, color=ACCENT_CYAN)
        counter.move_to(RIGHT * col_x + UP * 1.72)

        inf_note = Text("無限遠点をあわせて", font=FONT, font_size=21, color=TEXT_DIM)
        inf_note.move_to(RIGHT * col_x + UP * 1.08)
        total = MathTex(r"N_7 = 12", font_size=40, color=ACCENT_GOLD)
        total.move_to(RIGHT * col_x + UP * 0.52)

        others_head = Text("ほかの素数でも", font=FONT, font_size=21, color=TEXT_DIM)
        others_head.move_to(RIGHT * col_x + DOWN * 0.22)
        others = VGroup()
        for k, (q, n) in enumerate([(5, 8), (11, 10), (13, 19)]):
            row = MathTex(rf"N_{{{q}}} = {n}", font_size=30, color=TEXT_WHITE)
            row.move_to(RIGHT * col_x + DOWN * (0.70 + 0.42 * k))
            others.add(row)

        batches = [solutions[0:3], solutions[3:6], solutions[6:9], solutions[9:]]
        running = [3, 6, 9, 11]

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 0.9, 1.0, 1.1], intro=2.0, coda=3.0)
        self.play(FadeIn(title), FadeIn(eq), FadeIn(modp), run_time=1.0)
        self.play(
            FadeIn(lattice),
            FadeIn(x_ticks),
            FadeIn(y_ticks),
            FadeIn(x_lab),
            FadeIn(y_lab),
            FadeIn(head),
            FadeIn(counter),
            run_time=1.0,
        )
        for k, batch in enumerate(batches):
            self.play(
                AnimationGroup(*[FadeIn(d, run_time=0.45) for d in batch], lag_ratio=0.25),
                run_time=rt[k],
            )
            # Swap the tally instantly instead of animating it: fading a new number in
            # over the old one leaves BOTH on screen for the whole play, which reads as
            # a smear of overlapping digits in mid-scene frames.
            nxt = MathTex(str(running[k]), font_size=46, color=ACCENT_CYAN)
            nxt.move_to(RIGHT * col_x + UP * 1.72)
            self.remove(counter)
            self.add(nxt)
            counter = nxt
        self.play(FadeIn(inf_note), run_time=rt[4] * 0.4)
        self.play(FadeIn(total), run_time=rt[4] * 0.6)
        self.play(FadeIn(others_head), run_time=rt[5] * 0.3)
        for row in others:
            self.play(FadeIn(row), run_time=rt[5] * 0.7 / 3 + rt[6] / 3)
        self.wait(3.0)

    # -- mode: band -----------------------------------------------------------
    def _band(self, duration):
        title = Text("ずれは、いつも同じ幅の中にいる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        defn = MathTex(r"a_p = p + 1 - N_p", font_size=30, color=TEXT_WHITE)
        defn.move_to(LEFT * 4.55 + UP * 2.42)

        axes = self._scatter_axes(15, 5)
        upper = axes.plot(
            lambda t: 2 * math.sqrt(t), x_range=[0.4, 50, 0.4], color=ACCENT_GOLD, stroke_width=3
        )
        lower = axes.plot(
            lambda t: -2 * math.sqrt(t), x_range=[0.4, 50, 0.4], color=ACCENT_GOLD, stroke_width=3
        )
        area = axes.get_area(
            upper, x_range=[0.4, 50], bounded_graph=lower, color=ACCENT_GOLD, opacity=0.11
        )

        band_lab = MathTex(r"+2\sqrt{p}", font_size=28, color=ACCENT_GOLD)
        band_lab.move_to(axes.c2p(44, 13.4) + UP * 0.34)
        band_lab2 = MathTex(r"-2\sqrt{p}", font_size=28, color=ACCENT_GOLD)
        band_lab2.move_to(axes.c2p(44, -13.4) + DOWN * 0.34)

        p_lab = MathTex("p", font_size=26, color=TEXT_DIM)
        p_lab.move_to(axes.c2p(50, 0) + RIGHT * 0.36 + DOWN * 0.3)

        dots = VGroup(
            *[Dot(axes.c2p(q, _E_A[q]), radius=0.085, color=ACCENT_CYAN) for q in _PRIMES]
        )

        note = Text(
            "解の個数のふらつきは、この帯を出ない", font=FONT, font_size=23, color=TEXT_WHITE
        )
        note.move_to(DOWN * 1.92)

        rt = pace(duration, [1.0, 1.1, 1.0, 1.0, 1.0], intro=1.9, coda=3.0)
        self.play(FadeIn(title), FadeIn(defn), run_time=1.0)
        self.play(Create(axes), FadeIn(p_lab), run_time=0.9)
        self.play(Create(upper), Create(lower), run_time=rt[0])
        self.play(FadeIn(area), FadeIn(band_lab), FadeIn(band_lab2), run_time=rt[1])
        self.play(
            AnimationGroup(*[FadeIn(d, run_time=0.5) for d in dots], lag_ratio=0.3),
            run_time=rt[2] + rt[3],
        )
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(3.0)

    # -- mode: genus ----------------------------------------------------------
    def _genus(self, duration):
        title = Text("帯の幅は、穴の数で決まる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        scale_note = MathTex(r"a_p / \sqrt{p}", font_size=30, color=TEXT_DIM)
        scale_note.move_to(LEFT * 5.15 + UP * 2.45)

        axes = self._scatter_axes(4.8, 2)
        p_lab = MathTex("p", font_size=26, color=TEXT_DIM)
        p_lab.move_to(axes.c2p(50, 0) + RIGHT * 0.36 + DOWN * 0.3)

        def hline(v, color, dashed=False):
            a, b = axes.c2p(0, v), axes.c2p(50, v)
            if dashed:
                return DashedLine(a, b, color=color, stroke_width=3, dash_length=0.14)
            return Line(a, b, color=color, stroke_width=3)

        band2 = VGroup(hline(2, ACCENT_GOLD), hline(-2, ACCENT_GOLD))
        band2_lab = Text("穴が1つなら 2まで", font=FONT, font_size=21, color=ACCENT_GOLD)
        band2_lab.move_to(axes.c2p(12, 2) + UP * 0.42)

        g1 = VGroup(
            *[
                Dot(axes.c2p(q, _E_A[q] / math.sqrt(q)), radius=0.085, color=ACCENT_CYAN)
                for q in _PRIMES
            ]
        )

        # BOTH curves are named, each in the colour of its own dots. Only the genus-2
        # equation used to be on screen, so the cyan points had no identity at all --
        # and the narration says "この方程式が表す図形の穴が1つ" while the only
        # equation displayed was the TWO-hole one, pointing the viewer at the wrong
        # curve. A figure that compares two things has to name both of them.
        eq1 = MathTex(r"y^2 = x^3 - x + 1", font_size=26, color=ACCENT_CYAN)
        eq1_note = Text("穴が1つ", font=FONT, font_size=21, color=ACCENT_CYAN)
        row1 = VGroup(eq1, eq1_note).arrange(RIGHT, buff=0.3)
        eq2 = MathTex(r"y^2 = x^5 + 2x^3 + 2x^2 - 3x - 1", font_size=26, color=ACCENT_PINK)
        eq2_note = Text("穴が2つ", font=FONT, font_size=21, color=ACCENT_PINK)
        row2 = VGroup(eq2, eq2_note).arrange(RIGHT, buff=0.3)
        VGroup(row1, row2).arrange(RIGHT, buff=0.9).move_to(DOWN * 1.78)

        g2 = VGroup(
            *[
                Dot(axes.c2p(q, _H_D[q] / math.sqrt(q)), radius=0.085, color=ACCENT_PINK)
                for q in _PRIMES
            ]
        )
        out = VGroup(
            *[
                Dot(
                    axes.c2p(q, _H_D[q] / math.sqrt(q)), radius=0.16, color=ACCENT_PINK
                ).set_opacity(0.4)
                for q in _VISIBLE_BREACH
            ]
        )

        band4 = VGroup(hline(4, ACCENT_PINK, dashed=True), hline(-4, ACCENT_PINK, dashed=True))
        band4_lab = Text("穴が2つなら 4まで", font=FONT, font_size=21, color=ACCENT_PINK)
        band4_lab.move_to(axes.c2p(12, 4) + UP * 0.40)

        rt = pace(duration, [1.0, 1.0, 0.9, 1.1, 1.0, 1.0], intro=1.9, coda=3.0)
        self.play(FadeIn(title), FadeIn(scale_note), run_time=1.0)
        self.play(Create(axes), FadeIn(p_lab), run_time=0.9)
        self.play(Create(band2), FadeIn(band2_lab), FadeIn(row1), run_time=rt[0])
        self.play(
            AnimationGroup(*[FadeIn(d, run_time=0.4) for d in g1], lag_ratio=0.22), run_time=rt[1]
        )
        self.play(FadeIn(row2), run_time=rt[2])
        self.play(
            AnimationGroup(*[FadeIn(d, run_time=0.4) for d in g2], lag_ratio=0.22), run_time=rt[3]
        )
        self.play(FadeIn(out), run_time=rt[4])
        self.play(Create(band4), FadeIn(band4_lab), run_time=rt[5])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; every number shown is one of the counts documented in the
# module docstring and asserted at import time.
LINT_FACTUAL_CLAIMS = {
    "count": {"people": [], "years": []},
    "band": {"people": [], "years": []},
    "genus": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "count": WeilPointCount,
    "band": WeilPointCount,
    "genus": WeilPointCount,
}
