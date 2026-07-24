"""
lagrange_points.py - The three-body problem and the equilateral Lagrange points (数学史記)

Episode 055 (Joseph-Louis Lagrange). The man who tried to erase figures from
mathematics is best remembered for a figure in space: the equilateral triangle of
the Lagrange points. Honest attribution is by COLOR only (no names on screen):
the collinear points L1/L2/L3 were found first by Euler; Lagrange added the two
triangular points L4/L5.

Modes:
    three_body (default)
        Sun + Earth on a circular orbit + a third body at L4, forming an
        equilateral triangle that rotates rigidly (the triangle is preserved).
        Continuous motion across the whole scene via a ValueTracker.
        Fixed params: Sun at (-0.2, 0.15), orbit radius 1.7, L4 = 60 deg ahead of
        Earth; ~1.4 turns.
    five_points
        A schematic (not to scale) of all five points: collinear L1/L2/L3 in cyan
        (Euler's, by color), triangular L4/L5 in pink (Lagrange's). Staged reveal.
        Fixed params: Sun and Earth on a horizontal line; L4/L5 above/below.
    trojans
        Jupiter's orbit with two rotating swarms of Trojan asteroids at L4/L5, plus
        a note that space telescopes sit at the Sun-Earth Lagrange points.
        Continuous motion. Fixed params: orbit radius 1.75, 9 dots per swarm.

All Japanese labels use Text(font=FONT). MathTex holds only ASCII/LaTeX (L_1..L_5).
Y range: about -1.9 to +3.05. No trailing FadeOut. Deterministic (fixed offsets).
"""

import numpy as np
from manim import (
    DOWN,
    PI,
    UR,
    Circle,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    config,
    linear,
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

_SWARM_OFFS = [
    (0.0, 0.0),
    (0.15, 0.09),
    (-0.13, 0.07),
    (0.08, -0.14),
    (-0.1, -0.12),
    (0.2, -0.03),
    (-0.19, 0.04),
    (0.05, 0.19),
    (-0.04, -0.2),
]


class LagrangePoints(Scene):
    """Three-body equilateral points L4/L5, all five points, and Jupiter's Trojans."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "three_body")
        duration = float(params.get("duration", 26))
        if mode == "five_points":
            self._build_five_points(duration)
        elif mode == "trojans":
            self._build_trojans(duration)
        else:
            self._build_three_body(duration)

    def _titles(self, title, subtitle):
        t = Text(title, font=FONT, font_size=27, color=ACCENT_GOLD).move_to([0, 3.0, 0])
        s = Text(subtitle, font=FONT, font_size=18, color=TEXT_DIM).move_to([0, 2.45, 0])
        self.play(FadeIn(t), run_time=0.6)
        self.play(FadeIn(s), run_time=0.5)

    # ------------------------------------------------------------ three_body
    def _build_three_body(self, duration):
        self._titles("三体問題 ── 宇宙に浮かぶ正三角形", "三つ目の天体が、正三角形の頂点で釣り合う")

        s_pt = np.array([-0.2, 0.15, 0.0])
        radius = 1.7
        th0 = -40.0 * PI / 180.0
        tracker = ValueTracker(0.0)

        def epos(ang):
            return s_pt + radius * np.array([np.cos(ang), np.sin(ang), 0.0])

        def eang():
            return th0 + tracker.get_value()

        sun = Dot(s_pt, radius=0.16, color=ACCENT_GOLD)
        orbit = Circle(radius=radius, color=EDGE_COLOR, stroke_width=1.6).move_to(s_pt)
        orbit.set_stroke(opacity=0.5)
        earth = Dot(epos(eang()), radius=0.09, color=ACCENT_CYAN)
        l4 = Dot(epos(eang() + PI / 3), radius=0.08, color=ACCENT_PINK)
        edge_se = Line(s_pt, earth.get_center(), color=TEXT_DIM, stroke_width=2)
        edge_sl = Line(s_pt, l4.get_center(), color=TEXT_DIM, stroke_width=2)
        edge_el = Line(earth.get_center(), l4.get_center(), color=ACCENT_GOLD, stroke_width=2.6)

        earth.add_updater(lambda m: m.move_to(epos(eang())))
        l4.add_updater(lambda m: m.move_to(epos(eang() + PI / 3)))
        edge_se.add_updater(lambda m: m.put_start_and_end_on(s_pt, earth.get_center()))
        edge_sl.add_updater(lambda m: m.put_start_and_end_on(s_pt, l4.get_center()))
        edge_el.add_updater(lambda m: m.put_start_and_end_on(earth.get_center(), l4.get_center()))

        sun_lab = Text("太陽", font=FONT, font_size=16, color=ACCENT_GOLD).next_to(
            sun, DOWN, buff=0.08
        )
        earth_lab = Text("地球", font=FONT, font_size=15, color=ACCENT_CYAN)
        earth_lab.add_updater(lambda m: m.next_to(earth, UR, buff=0.12))
        l4_lab = MathTex(r"L_4", font_size=24, color=ACCENT_PINK)
        l4_lab.add_updater(lambda m: m.next_to(l4, UR, buff=0.12))
        note = Text(
            "正三角形を保ったまま、回り続ける", font=FONT, font_size=18, color=TEXT_DIM
        ).move_to([0, -1.8, 0])

        coda = 2.5
        self.play(FadeIn(sun), Create(orbit), FadeIn(sun_lab), run_time=0.9)
        self.play(
            FadeIn(earth),
            FadeIn(l4),
            Create(edge_se),
            Create(edge_sl),
            Create(edge_el),
            FadeIn(earth_lab),
            FadeIn(l4_lab),
            run_time=1.0,
        )
        self.play(FadeIn(note), run_time=0.6)
        motion = max(3.0, duration - (0.6 + 0.5 + 0.9 + 1.0 + 0.6) - coda)
        self.play(tracker.animate.set_value(2 * PI * 1.4), run_time=motion, rate_func=linear)
        self.wait(coda)

    # ------------------------------------------------------------ five_points
    def _build_five_points(self, duration):
        self._titles("五つの釣り合い点 ── L1 から L5", "直線上の三点と、三角形の二点")

        s_pt = np.array([-2.6, 0.15, 0.0])
        e_pt = np.array([1.9, 0.15, 0.0])
        axis = Line([-4.9, 0.15, 0], [3.1, 0.15, 0], color=EDGE_COLOR, stroke_width=1.6)
        axis.set_stroke(opacity=0.5)
        sun = Dot(s_pt, radius=0.17, color=ACCENT_GOLD)
        earth = Dot(e_pt, radius=0.1, color=TEXT_WHITE)
        sun_lab = Text("太陽", font=FONT, font_size=15, color=ACCENT_GOLD).move_to([-2.6, -0.22, 0])
        earth_lab = Text("地球", font=FONT, font_size=15, color=TEXT_WHITE).move_to([1.9, -0.22, 0])

        col_pts = {"L_1": [1.05, 0.15, 0], "L_2": [2.65, 0.15, 0], "L_3": [-4.15, 0.15, 0]}
        col_dots = VGroup()
        col_labs = VGroup()
        for name, p in col_pts.items():
            col_dots.add(Dot(p, radius=0.075, color=ACCENT_CYAN))
            col_labs.add(MathTex(name, font_size=22, color=ACCENT_CYAN).move_to([p[0], 0.5, 0]))

        l4_pt = [-0.35, 1.7, 0]
        l5_pt = [-0.35, -1.4, 0]
        l4_dot = Dot(l4_pt, radius=0.09, color=ACCENT_PINK)
        l5_dot = Dot(l5_pt, radius=0.09, color=ACCENT_PINK)
        l4_lab = MathTex(r"L_4", font_size=24, color=ACCENT_PINK).move_to([0.05, 1.7, 0])
        l5_lab = MathTex(r"L_5", font_size=24, color=ACCENT_PINK).move_to([0.05, -1.4, 0])
        tri4 = VGroup(
            DashedLine(s_pt, l4_pt, color=ACCENT_PINK, stroke_width=1.6),
            DashedLine(e_pt, l4_pt, color=ACCENT_PINK, stroke_width=1.6),
        )
        tri5 = VGroup(
            DashedLine(s_pt, l5_pt, color=ACCENT_PINK, stroke_width=1.6),
            DashedLine(e_pt, l5_pt, color=ACCENT_PINK, stroke_width=1.6),
        )

        leg1 = Text("● 直線上の三点", font=FONT, font_size=16, color=ACCENT_CYAN).move_to(
            [4.4, 0.9, 0]
        )
        leg2 = Text("● 三角形の二点", font=FONT, font_size=16, color=ACCENT_PINK).move_to(
            [4.4, 0.35, 0]
        )
        note = Text(
            "模式図（距離は誇張しています）", font=FONT, font_size=15, color=TEXT_DIM
        ).move_to([0, -1.9, 0])

        coda = 2.5
        rt = pace(duration, [1.0, 0.6, 0.6, 0.6, 0.5, 1.0, 1.0, 0.8], intro=1.1, coda=coda)
        self.play(
            Create(axis),
            FadeIn(sun),
            FadeIn(earth),
            FadeIn(sun_lab),
            FadeIn(earth_lab),
            run_time=rt[0],
        )
        self.play(FadeIn(col_dots[0]), FadeIn(col_labs[0]), run_time=rt[1])
        self.play(FadeIn(col_dots[1]), FadeIn(col_labs[1]), run_time=rt[2])
        self.play(FadeIn(col_dots[2]), FadeIn(col_labs[2]), run_time=rt[3])
        self.play(FadeIn(leg1), run_time=rt[4])
        self.play(Create(tri4), FadeIn(l4_dot), FadeIn(l4_lab), run_time=rt[5])
        self.play(Create(tri5), FadeIn(l5_dot), FadeIn(l5_lab), run_time=rt[6])
        self.play(FadeIn(leg2), FadeIn(note), run_time=rt[7])
        self.wait(coda)

    # --------------------------------------------------------------- trojans
    def _build_trojans(self, duration):
        self._titles("いまも漂う、宇宙の正三角形", "木星の軌道の L4・L5 に、無数のトロヤ群")

        s_pt = np.array([0.0, 0.1, 0.0])
        radius = 1.75
        jth0 = 25.0 * PI / 180.0
        tracker = ValueTracker(0.0)

        def opos(ang, r=radius):
            return s_pt + r * np.array([np.cos(ang), np.sin(ang), 0.0])

        def jang():
            return jth0 + tracker.get_value()

        sun = Dot(s_pt, radius=0.17, color=ACCENT_GOLD)
        orbit = Circle(radius=radius, color=EDGE_COLOR, stroke_width=1.6).move_to(s_pt)
        orbit.set_stroke(opacity=0.5)
        jup = Dot(opos(jang()), radius=0.13, color=TEXT_WHITE)

        def swarm():
            g = VGroup()
            for dx, dy in _SWARM_OFFS:
                g.add(Dot([dx, dy, 0], radius=0.045, color=ACCENT_PINK))
            return g

        sw4 = swarm().move_to(opos(jang() + PI / 3))
        sw5 = swarm().move_to(opos(jang() - PI / 3))

        jup.add_updater(lambda m: m.move_to(opos(jang())))
        sw4.add_updater(lambda m: m.move_to(opos(jang() + PI / 3)))
        sw5.add_updater(lambda m: m.move_to(opos(jang() - PI / 3)))

        sun_lab = Text("太陽", font=FONT, font_size=15, color=ACCENT_GOLD).next_to(
            sun, DOWN, buff=0.08
        )
        jup_lab = Text("木星", font=FONT, font_size=15, color=TEXT_WHITE)
        jup_lab.add_updater(lambda m: m.next_to(jup, UR, buff=0.12))
        l4_lab = MathTex(r"L_4", font_size=22, color=ACCENT_PINK)
        l4_lab.add_updater(lambda m: m.next_to(sw4, UR, buff=0.12))
        l5_lab = MathTex(r"L_5", font_size=22, color=ACCENT_PINK)
        l5_lab.add_updater(lambda m: m.next_to(sw5, UR, buff=0.12))
        note = Text(
            "太陽と地球のラグランジュ点には、宇宙望遠鏡が停泊しています",
            font=FONT,
            font_size=17,
            color=TEXT_DIM,
        ).move_to([0, -1.85, 0])

        coda = 2.5
        self.play(FadeIn(sun), Create(orbit), FadeIn(sun_lab), run_time=0.9)
        self.play(
            FadeIn(jup),
            FadeIn(sw4),
            FadeIn(sw5),
            FadeIn(jup_lab),
            FadeIn(l4_lab),
            FadeIn(l5_lab),
            run_time=1.0,
        )
        self.play(FadeIn(note), run_time=0.6)
        motion = max(3.0, duration - (0.6 + 0.5 + 0.9 + 1.0 + 0.6) - coda)
        self.play(tracker.animate.set_value(2 * PI * 1.3), run_time=motion, rate_func=linear)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "three_body": {"people": [], "years": []},
    "five_points": {"people": [], "years": []},
    "trojans": {"people": [], "years": []},
}

SCENES = {
    "three_body": LagrangePoints,
    "five_points": LagrangePoints,
    "trojans": LagrangePoints,
}
