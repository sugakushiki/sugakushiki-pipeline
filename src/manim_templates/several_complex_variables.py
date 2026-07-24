"""
several_complex_variables.py - Why several complex variables is a different world

Episode 044 (Kiyoshi Oka). Intuition-level visuals for the leap from one complex
variable to several, the geometry Oka mapped, and his signature method. No proofs,
no rigorous definitions -- wonder and intuition only.

Modes:
    puncture (default)
        One complex variable: a domain in the plane from which you can drill an
        isolated hole and place a singularity (a pole, like 1/z) there.
        Fixed params: one domain disk, one dashed hole, one pole (star) marker.
    hartogs
        Two variables, drawn faithfully in the (|z_1|, |z_2|) quadrant (a
        Reinhardt picture, not a fake schematic). A Hartogs figure (top strip +
        left column, cyan) is where a holomorphic function is given; the remaining
        bottom-right notch (gold) fills itself in -- no isolated hole is possible
        (Hartogs, 1906).
        Fixed params: unit bidisc square; figure r=0.4 (left column), e=0.55
        (top strip); gold notch = the forced extension.
    pseudoconvex
        Two domains: one with a complex "dent" (non-pseudoconvex) where a function
        leaks out, one without (pseudoconvex) where it stays. Statement shown:
        "pseudoconvex => domain of holomorphy" (Oka's Levi-problem theorem), no
        name on screen.
        Fixed params: left dented blob + one leak arrow, right convex blob.
    ascent
        Oka's "passage to a higher space" (joukuu ikou): a tangled low-dimensional
        problem, lifted to a higher dimension where it is clear, then brought back.
        Fixed params: one tangled curve (low), one smooth curve (high), two arrows.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.85 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Axes,
    Circle,
    Create,
    DashedVMobject,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Polygon,
    Scene,
    Square,
    Text,
    VGroup,
    VMobject,
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
)

config.background_color = BG_COLOR


def _star(center, color, r=0.16, width=3):
    """A small 4-spoke burst marking a singularity."""
    center = np.array(center, dtype=float)
    group = VGroup()
    for ang in (0.0, math.pi / 2, math.pi / 4, 3 * math.pi / 4):
        d = np.array([math.cos(ang), math.sin(ang), 0.0]) * r
        group.add(Line(center - d, center + d, color=color, stroke_width=width))
    return group


def _region(axes, u0, u1, v0, v1, color, opacity, stroke=1.5):
    """A faithful rectangle in (|z_1|, |z_2|) coordinates via axes.c2p."""
    pts = [axes.c2p(u0, v0), axes.c2p(u1, v0), axes.c2p(u1, v1), axes.c2p(u0, v1)]
    return Polygon(*pts, color=color, fill_color=color, fill_opacity=opacity, stroke_width=stroke)


class SeveralComplexVariables(Scene):
    """The world of several complex variables - four intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "puncture")
        duration = float(params.get("duration", 26))
        if mode == "hartogs":
            self._build_hartogs(duration)
        elif mode == "pseudoconvex":
            self._build_pseudoconvex(duration)
        elif mode == "ascent":
            self._build_ascent(duration)
        else:
            self._build_puncture(duration)

    # --------------------------------------------------------------- puncture
    def _build_puncture(self, duration):
        title = Text("一変数：穴を開けられる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        center = np.array([-0.3, 0.5, 0.0])
        domain = Circle(radius=2.0, color=ACCENT_CYAN, stroke_width=2.5).move_to(center)
        domain.set_fill(ACCENT_CYAN, opacity=0.07)
        ax_h = Line(center + LEFT * 2.0, center + RIGHT * 2.0, color=EDGE_COLOR, stroke_width=1.2)
        ax_v = Line(center + DOWN * 2.0, center + UP * 2.0, color=EDGE_COLOR, stroke_width=1.2)
        plane_label = Text("複素平面（一変数）", font=FONT, font_size=22, color=TEXT_DIM)
        plane_label.move_to([-3.0, 2.0, 0])

        self.play(FadeIn(ax_h), FadeIn(ax_v), Create(domain), run_time=1.2)
        self.play(FadeIn(plane_label), run_time=0.5)

        hole_c = np.array([0.5, 1.0, 0.0])
        hole = Circle(radius=0.14, stroke_width=0).move_to(hole_c)
        hole.set_fill(BG_COLOR, opacity=1.0)
        rim = DashedVMobject(
            Circle(radius=0.14, color=ACCENT_PINK, stroke_width=2).move_to(hole_c),
            num_dashes=14,
        )
        star = _star(hole_c, ACCENT_PINK, r=0.16)
        anchor = np.array([2.5, 1.0, 0.0])
        connector = Line(hole_c + RIGHT * 0.22, anchor, color=TEXT_DIM, stroke_width=1.2)
        pole_label = Text("特異点（極）", font=FONT, font_size=22, color=ACCENT_PINK)
        pole_label.next_to(anchor, RIGHT, buff=0.12)
        note = Text("一変数なら、穴を開けて極を置ける", font=FONT, font_size=22, color=TEXT_WHITE)
        note.move_to([0, -1.55, 0])

        used = 0.7 + 1.2 + 0.5
        coda = 2.5
        body = max(2.4, duration - used - coda)
        per = body / 4.0
        self.play(FadeIn(hole), FadeIn(rim), run_time=per)
        self.play(FadeIn(star), run_time=per)
        self.play(Create(connector), FadeIn(pole_label), run_time=per)
        self.play(FadeIn(note), run_time=per)
        self.wait(coda)

    # ---------------------------------------------------------------- hartogs
    def _build_hartogs(self, duration):
        title = Text("二変数：穴がひとりでに埋まる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[0, 1.05, 0.5],
            y_range=[0, 1.05, 0.5],
            x_length=4.4,
            y_length=3.2,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6, "include_ticks": False},
        )
        axes.move_to([-1.5, 0.6, 0])
        xl = MathTex(r"|z_1|", font_size=26, color=TEXT_DIM).next_to(axes.x_axis, RIGHT, buff=0.12)
        yl = MathTex(r"|z_2|", font_size=26, color=TEXT_DIM).next_to(axes.y_axis, UP, buff=0.12)
        self.play(FadeIn(axes), FadeIn(xl), FadeIn(yl), run_time=0.8)

        r, e = 0.4, 0.55
        square = _region(axes, 0, 1, 0, 1, EDGE_COLOR, 0.0, stroke=2.0)
        strip = _region(axes, 0, 1, e, 1, ACCENT_CYAN, 0.32)
        col = _region(axes, 0, r, 0, 1, ACCENT_CYAN, 0.32)
        notch = _region(axes, r, 1, 0, e, ACCENT_GOLD, 0.0, stroke=1.2)
        notch.set_stroke(ACCENT_GOLD, 1.2)

        leg1 = self._legend_row(ACCENT_CYAN, "関数がある範囲", [1.4, 1.3, 0])
        leg2 = self._legend_row(ACCENT_GOLD, "ひとりでに埋まる", [1.4, 0.55, 0])
        note = Text("孤立した穴は作れない", font=FONT, font_size=24, color=TEXT_WHITE)
        note.move_to([-1.1, -1.5, 0])
        foot = Text("絶対値でみた、二変数の忠実な姿", font=FONT, font_size=17, color=TEXT_DIM)
        foot.move_to([-1.1, -1.82, 0])

        used = 0.7 + 0.8
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 7.0
        self.play(FadeIn(square), run_time=per)
        self.play(FadeIn(strip), run_time=per)
        self.play(FadeIn(col), run_time=per)
        self.add(notch)
        self.play(notch.animate.set_fill(ACCENT_GOLD, opacity=0.5), run_time=per)
        self.play(Indicate(notch, color=ACCENT_GOLD, scale_factor=1.05), run_time=per)
        self.play(FadeIn(leg1), FadeIn(leg2), run_time=per)
        self.play(FadeIn(note), FadeIn(foot), run_time=per)
        self.wait(coda)

    def _legend_row(self, color, label, pos):
        sq = Square(side_length=0.24, color=color, stroke_width=1)
        sq.set_fill(color, opacity=0.5)
        sq.move_to(pos)
        tx = Text(label, font=FONT, font_size=20, color=TEXT_WHITE).next_to(sq, RIGHT, buff=0.16)
        return VGroup(sq, tx)

    # ----------------------------------------------------------- pseudoconvex
    def _build_pseudoconvex(self, duration):
        title = Text("関数が棲める形、漏れる形", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        cl = np.array([-3.4, 0.7, 0.0])
        rel = [
            [-1.1, -1.1],
            [1.1, -1.1],
            [1.1, -0.25],
            [0.05, 0.0],
            [1.1, 0.25],
            [1.1, 1.1],
            [-1.1, 1.1],
        ]
        left_pts = [cl + np.array([x, y, 0.0]) for x, y in rel]
        left_blob = Polygon(*left_pts, color=ACCENT_CYAN, stroke_width=2.5)
        left_blob.set_fill(ACCENT_CYAN, opacity=0.10)
        left_top = Text("へこみがある（非擬凸）", font=FONT, font_size=20, color=ACCENT_PINK)
        left_top.move_to([-3.4, 2.05, 0])
        leak = Arrow(
            cl + np.array([0.05, 0.0, 0]),
            cl + np.array([2.0, 0.0, 0]),
            color=ACCENT_PINK,
            buff=0.05,
            stroke_width=4,
        )
        leak_label = Text("漏れる", font=FONT, font_size=20, color=ACCENT_PINK)
        leak_label.next_to(cl + np.array([2.0, 0.0, 0]), UP, buff=0.1)

        cr = np.array([3.4, 0.7, 0.0])
        right_blob = Circle(radius=1.15, color=ACCENT_CYAN, stroke_width=2.5).move_to(cr)
        right_blob.set_fill(ACCENT_CYAN, opacity=0.10)
        right_top = Text("へこみがない（擬凸）", font=FONT, font_size=20, color=ACCENT_CYAN)
        right_top.move_to([3.4, 2.05, 0])
        stay = Text("棲める", font=FONT, font_size=24, color=ACCENT_GOLD).move_to(cr)

        line1 = Text(
            "へこみがなければ、関数はそこに棲む", font=FONT, font_size=22, color=TEXT_WHITE
        )
        line1.move_to([0, -1.35, 0])
        line2 = Text("「擬凸ならば正則領域」", font=FONT, font_size=24, color=ACCENT_GOLD)
        line2.move_to([0, -1.78, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(Create(left_blob), run_time=per)
        self.play(FadeIn(left_top), run_time=per * 0.6)
        self.play(Create(leak), FadeIn(leak_label), run_time=per)
        self.play(Create(right_blob), FadeIn(right_top), run_time=per)
        self.play(FadeIn(stay), run_time=per * 0.6)
        self.play(FadeIn(line1), run_time=per)
        self.play(FadeIn(line2), run_time=per)
        self.wait(coda)

    # ------------------------------------------------------------------ ascent
    def _build_ascent(self, duration):
        title = Text("上空移行 ── 高い次元へ持ち上げる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        ts = np.linspace(0, 2 * math.pi, 220)
        tangle_pts = [
            np.array([1.6 * math.sin(2 * t), -0.9 + 0.42 * math.sin(3 * t), 0.0]) for t in ts
        ]
        tangle = VMobject().set_points_smoothly(tangle_pts)
        tangle.set_stroke(ACCENT_PINK, width=3)
        low_label = Text(
            "低い次元：問題が絡まって見える", font=FONT, font_size=20, color=ACCENT_PINK
        )
        low_label.move_to([0, -1.7, 0])

        xs = np.linspace(-1.6, 1.6, 80)
        smooth_pts = [
            np.array([x, 1.6 + 0.3 * math.sin(math.pi * (x + 1.6) / 3.2), 0.0]) for x in xs
        ]
        smooth = VMobject().set_points_smoothly(smooth_pts)
        smooth.set_stroke(ACCENT_CYAN, width=3)
        high_label = Text(
            "高い次元：見通しよくほどける", font=FONT, font_size=20, color=ACCENT_CYAN
        )
        high_label.move_to([0, 2.4, 0])

        up_arrow = Arrow([3.4, -0.7, 0], [3.4, 1.3, 0], color=ACCENT_GOLD, buff=0.1, stroke_width=4)
        up_label = Text("持ち上げる", font=FONT, font_size=20, color=ACCENT_GOLD)
        up_label.next_to([3.4, 0.3, 0], RIGHT, buff=0.12)
        down_arrow = Arrow(
            [-3.4, 1.3, 0], [-3.4, -0.7, 0], color=ACCENT_CYAN, buff=0.1, stroke_width=4
        )
        down_label = Text("解いて戻す", font=FONT, font_size=20, color=ACCENT_CYAN)
        down_label.next_to([-3.4, 0.3, 0], LEFT, buff=0.12)
        mid = Text("立つ場所を変えると、見えてくる", font=FONT, font_size=22, color=ACCENT_GOLD)
        mid.move_to([0, 0.35, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 5.0
        self.play(Create(tangle), FadeIn(low_label), run_time=per)
        self.play(Create(up_arrow), FadeIn(up_label), run_time=per)
        self.play(Create(smooth), FadeIn(high_label), run_time=per)
        self.play(FadeIn(mid), run_time=per)
        self.play(Create(down_arrow), FadeIn(down_label), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "puncture": {"people": [], "years": []},
    "hartogs": {"people": [], "years": []},
    "pseudoconvex": {"people": [], "years": []},
    "ascent": {"people": [], "years": []},
}

SCENES = {
    "puncture": SeveralComplexVariables,
    "hartogs": SeveralComplexVariables,
    "pseudoconvex": SeveralComplexVariables,
    "ascent": SeveralComplexVariables,
}
