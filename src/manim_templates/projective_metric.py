"""
projective_metric.py - non-Euclidean geometry living inside projective geometry

Klein's 1871 papers put Euclidean and non-Euclidean geometry into one projective
frame: fix an "absolute" conic, measure distance from the cross-ratio against it
(Cayley's projective metric), and the three classical geometries appear as three
choices of that conic. The disc model itself is Beltrami's (1868); Klein rebuilt
it projectively and supplied the names parabolic / elliptic / hyperbolic.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    absolute_conic  - The disc is the world, a chord is a "line", and through one
                      interior point MANY chords miss a given chord. The rim is
                      infinitely far away. Fixed: circle radius 2.3, 1 horizontal
                      base chord (rim angles 205/335 deg), 3 non-meeting chords
                      through the interior point at -28/0/+28 deg. Those angles
                      are checked against the crossing wedge (42.7..137.3 deg for
                      this configuration), so all three visibly miss the chord.
    cross_ratio     - A pencil of 4 rays from one viewpoint cuts two transversals.
                      Lengths and segment ratios differ between the two, but the
                      cross-ratio prints the SAME value on both. Fixed: 4 points,
                      2 transversals meeting at a vertex on the right; both
                      cross-ratios are computed from the line parameters at build
                      time, so the two readouts must agree.
    three_geometries- The absolute conic taken 3 ways, side by side: real -> 双曲
                      (chords that miss), imaginary -> 楕円 (any two lines meet
                      twice), degenerate -> 放物 = Euclid (parallels never meet).
                      Fixed: 3 panels, radius 1.15.

No on-screen person names or years (every label is geometric vocabulary), so
LINT_FACTUAL_CLAIMS is empty for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    ArcBetweenPoints,
    Circle,
    Create,
    DashedVMobject,
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


def _pt(x, y):
    return np.array([x, y, 0.0])


def _chord(center, r, p, d):
    """Both endpoints of the chord through p with direction d (d need not be unit)."""
    d = np.array(d, dtype=float)
    d = d / np.linalg.norm(d)
    u = np.array(p, dtype=float) - np.array(center, dtype=float)
    b = float(np.dot(u, d))
    c = float(np.dot(u, u)) - r * r
    s = math.sqrt(max(b * b - c, 1e-9))
    return np.array(p) + d * (-b + s), np.array(p) + d * (-b - s)


def _cross_ratio(a, b, c, d):
    """Cross-ratio (a,b;c,d) from signed 1-D parameters along a line."""
    return ((c - a) / (c - b)) / ((d - a) / (d - b))


class ProjectiveMetric(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "absolute_conic")
        duration = params.get("duration", 26)
        if mode == "cross_ratio":
            self._cross_ratio_mode(duration)
        elif mode == "three_geometries":
            self._three_geometries(duration)
        else:
            self._absolute_conic(duration)

    # -- mode: absolute_conic -------------------------------------------------
    def _absolute_conic(self, duration):
        title = Text("円板の中の、もう一つの幾何", font=FONT, font_size=29, color=ACCENT_GOLD)
        title.move_to(UP * 3.05)

        c = _pt(-2.6, 0.35)
        r = 2.3
        rim = Circle(radius=r, color=TEXT_DIM, stroke_width=4).move_to(c)

        a1 = c + _pt(r * math.cos(math.radians(205)), r * math.sin(math.radians(205)))
        a2 = c + _pt(r * math.cos(math.radians(335)), r * math.sin(math.radians(335)))
        base = Line(a1, a2, color=TEXT_WHITE, stroke_width=4)

        p = c + UP * 0.95
        dot_p = Dot(p, color=ACCENT_GOLD, radius=0.09)

        # A line through p misses the base chord exactly when its direction lies
        # OUTSIDE the wedge spanned by (a1-p) and (a2-p). With the chord at 205 deg
        # / 335 deg and p at the centre + 0.95 that wedge is 42.7..137.3 deg, so the
        # near-horizontal fan below is safe with ~15 deg of margin on both sides.
        # (Do NOT use the bisector (a1-p)+(a2-p): it points INTO the wedge, i.e.
        # straight down here, and that chord really does cut the base chord.)
        parallels = VGroup()
        for deg in (-28.0, 0.0, 28.0):
            d = _pt(math.cos(math.radians(deg)), math.sin(math.radians(deg)))
            e1, e2 = _chord(c, r, p, d)
            parallels.add(Line(e1, e2, color=ACCENT_CYAN, stroke_width=3.5))

        notes_x = 3.7
        n1 = Text("円板の内側だけが、世界", font=FONT, font_size=22, color=TEXT_WHITE)
        n1.move_to(RIGHT * notes_x + UP * 1.75)
        n2 = Text("弦が、この世界の直線", font=FONT, font_size=22, color=TEXT_WHITE)
        n2.move_to(RIGHT * notes_x + UP * 0.65)
        n3 = Text("交わらない直線が、何本も", font=FONT, font_size=22, color=ACCENT_CYAN)
        n3.move_to(RIGHT * notes_x + DOWN * 0.45)
        n4 = Text("円周は、無限の彼方", font=FONT, font_size=22, color=ACCENT_PINK)
        n4.move_to(RIGHT * notes_x + DOWN * 1.55)

        rt = pace(duration, [1.0, 1.0, 0.7, 1.0, 1.0, 1.0, 1.1], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)
        self.play(Create(rim), FadeIn(n1), run_time=rt[0])
        self.play(Create(base), FadeIn(n2), run_time=rt[1])
        self.play(FadeIn(dot_p), run_time=rt[2])
        for i in range(3):
            extra = [FadeIn(n3)] if i == 0 else []
            self.play(Create(parallels[i]), *extra, run_time=rt[3 + i])
        self.play(FadeIn(n4), rim.animate.set_color(ACCENT_PINK), run_time=rt[6])
        self.wait(3.0)

    # -- mode: cross_ratio ----------------------------------------------------
    def _cross_ratio_mode(self, duration):
        title = Text("透視で残るもの、失われるもの", font=FONT, font_size=29, color=ACCENT_GOLD)
        title.move_to(UP * 3.15)

        vertex = _pt(4.6, 0.2)
        d1 = _pt(-10.4, 1.9)
        d2 = _pt(-10.4, -1.9)
        eye = _pt(-2.0, 2.55)

        line1 = Line(vertex, vertex + d1 * 0.75, color=ACCENT_GOLD, stroke_width=4)
        line2 = Line(vertex, vertex + d2 * 0.85, color=ACCENT_CYAN, stroke_width=4)

        us = [0.18, 0.30, 0.44, 0.60]
        pts1 = [vertex + d1 * u for u in us]

        # ray from the eye through each point, intersected with the second line
        ws = []
        pts2 = []
        for a in pts1:
            ray = a - eye
            # eye + s*ray = vertex + w*d2  ->  solve the 2x2 system
            m = np.array([[ray[0], -d2[0]], [ray[1], -d2[1]]])
            rhs = np.array([vertex[0] - eye[0], vertex[1] - eye[1]])
            s, w = np.linalg.solve(m, rhs)
            ws.append(float(w))
            pts2.append(eye + ray * float(s))

        cr1 = _cross_ratio(*us)
        cr2 = _cross_ratio(*ws)

        eye_dot = Dot(eye, color=TEXT_WHITE, radius=0.1)
        eye_lab = Text("視点", font=FONT, font_size=21, color=TEXT_WHITE)
        eye_lab.next_to(eye_dot, LEFT, buff=0.18)

        names = ["A", "B", "C", "D"]
        dots1 = VGroup()
        labs1 = VGroup()
        for a, nm in zip(pts1, names, strict=True):
            dots1.add(Dot(a, color=ACCENT_GOLD, radius=0.08))
            lb = MathTex(nm, font_size=26, color=ACCENT_GOLD)
            lb.move_to(a + UP * 0.32)
            labs1.add(lb)

        rays = VGroup()
        dots2 = VGroup()
        labs2 = VGroup()
        for bpt, nm in zip(pts2, names, strict=True):
            rays.add(Line(eye, bpt, color=EDGE_COLOR, stroke_width=2))
            dots2.add(Dot(bpt, color=ACCENT_CYAN, radius=0.08))
            lb = MathTex(nm + "'", font_size=26, color=ACCENT_CYAN)
            lb.move_to(bpt + DOWN * 0.32)
            labs2.add(lb)

        read1 = MathTex(rf"(A,B;C,D) = {cr1:.3f}", font_size=30, color=ACCENT_GOLD)
        read1.move_to(_pt(-5.1, 1.95))
        read2 = MathTex(rf"(A',B';C',D') = {cr2:.3f}", font_size=30, color=ACCENT_CYAN)
        read2.move_to(_pt(-5.1, 1.3))

        caption = Text(
            "長さも比も変わるのに、複比だけが残る",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        caption.move_to(DOWN * 1.8)

        rt = pace(duration, [1.0, 1.0, 1.1, 1.0, 1.2], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)
        self.play(Create(line1), FadeIn(dots1), FadeIn(labs1), run_time=rt[0])
        self.play(FadeIn(eye_dot), FadeIn(eye_lab), Create(rays), run_time=rt[1])
        self.play(Create(line2), FadeIn(dots2), FadeIn(labs2), run_time=rt[2])
        self.play(FadeIn(read1), run_time=rt[3])
        self.play(FadeIn(read2), FadeIn(caption), run_time=rt[4])
        self.wait(3.0)

    # -- mode: three_geometries -----------------------------------------------
    def _three_geometries(self, duration):
        title = Text("絶対二次曲線の、三つの取り方", font=FONT, font_size=29, color=ACCENT_GOLD)
        title.move_to(UP * 3.1)
        note = Text(
            "取り方を変えると、三つの幾何が現れる",
            font=FONT,
            font_size=21,
            color=TEXT_DIM,
        )
        note.move_to(UP * 2.5)

        rr = 1.15
        cy = 0.5
        centers = [_pt(-4.6, cy), _pt(0.0, cy), _pt(4.6, cy)]

        # ---- panel A: real conic -> hyperbolic ------------------------------
        ca = centers[0]
        rim_a = Circle(radius=rr, color=ACCENT_CYAN, stroke_width=3.5).move_to(ca)
        b1 = ca + _pt(rr * math.cos(math.radians(210)), rr * math.sin(math.radians(210)))
        b2 = ca + _pt(rr * math.cos(math.radians(330)), rr * math.sin(math.radians(330)))
        base_a = Line(b1, b2, color=TEXT_WHITE, stroke_width=3)
        pa = ca + UP * 0.48
        # same wedge rule as absolute_conic: here the crossing band is 46.7..133.3
        # deg, so +/-26 deg keeps both chords clear of the base chord on screen.
        misses = VGroup()
        for deg in (-26.0, 26.0):
            d = _pt(math.cos(math.radians(deg)), math.sin(math.radians(deg)))
            e1, e2 = _chord(ca, rr, pa, d)
            misses.add(Line(e1, e2, color=ACCENT_GOLD, stroke_width=3))
        panel_a = VGroup(rim_a, base_a, misses, Dot(pa, color=ACCENT_GOLD, radius=0.06))

        # ---- panel B: imaginary conic -> elliptic ---------------------------
        cb = centers[1]
        rim_b = DashedVMobject(
            Circle(radius=rr, color=TEXT_DIM, stroke_width=3).move_to(cb),
            num_dashes=26,
        )
        arc1 = ArcBetweenPoints(
            cb + _pt(-rr, 0), cb + _pt(rr, 0), angle=1.5, color=ACCENT_GOLD, stroke_width=3
        )
        arc2 = ArcBetweenPoints(
            cb + _pt(-rr, 0), cb + _pt(rr, 0), angle=-1.5, color=ACCENT_CYAN, stroke_width=3
        )
        meets = VGroup(
            Dot(cb + _pt(-rr, 0), color=ACCENT_PINK, radius=0.07),
            Dot(cb + _pt(rr, 0), color=ACCENT_PINK, radius=0.07),
        )
        panel_b = VGroup(rim_b, arc1, arc2, meets)

        # ---- panel C: degenerate conic -> parabolic (Euclid) ----------------
        cc = centers[2]
        far = DashedVMobject(
            Line(cc + _pt(-rr - 0.15, rr), cc + _pt(rr + 0.15, rr), color=TEXT_DIM, stroke_width=3),
            num_dashes=14,
        )
        par1 = Line(cc + _pt(-rr, 0.05), cc + _pt(rr, 0.05), color=ACCENT_GOLD, stroke_width=3)
        par2 = Line(cc + _pt(-rr, -0.65), cc + _pt(rr, -0.65), color=ACCENT_CYAN, stroke_width=3)
        panel_c = VGroup(far, par1, par2)

        caps = ["双曲幾何", "楕円幾何", "放物幾何"]
        subs = ["実の二次曲線", "虚の二次曲線", "退化 ─ ユークリッド"]
        colors = [ACCENT_CYAN, ACCENT_GOLD, TEXT_WHITE]
        cap_g = VGroup()
        sub_g = VGroup()
        for ctr, cap, sub, col in zip(centers, caps, subs, colors, strict=True):
            t = Text(cap, font=FONT, font_size=24, color=col)
            t.move_to(_pt(ctr[0], -1.15))
            s = Text(sub, font=FONT, font_size=19, color=TEXT_DIM)
            s.move_to(_pt(ctr[0], -1.68))
            cap_g.add(t)
            sub_g.add(s)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.1], intro=1.2, coda=3.0)
        self.play(FadeIn(title), FadeIn(note), run_time=1.2)
        for i, panel in enumerate((panel_a, panel_b, panel_c)):
            self.play(Create(panel), FadeIn(cap_g[i]), FadeIn(sub_g[i]), run_time=rt[i])
        self.play(
            cap_g[0].animate.set_color(ACCENT_CYAN),
            cap_g[1].animate.set_color(ACCENT_GOLD),
            cap_g[2].animate.set_color(ACCENT_PINK),
            run_time=rt[3],
        )
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). Every on-screen label
# is geometric vocabulary or a computed number - no person names, no years.
LINT_FACTUAL_CLAIMS = {
    "absolute_conic": {"people": [], "years": []},
    "cross_ratio": {"people": [], "years": []},
    "three_geometries": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "absolute_conic": ProjectiveMetric,
    "cross_ratio": ProjectiveMetric,
    "three_geometries": ProjectiveMetric,
}
