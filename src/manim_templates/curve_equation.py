"""
curve_equation.py - Curve and equation correspondence for 数学史記

Visualizes Descartes' central insight from La Géométrie (1637):
a curve is an equation. Each point on a curve corresponds to a solution
of an algebraic equation, and vice versa. This unification of geometry
and algebra is the foundation of analytic geometry.

Modes:
    parabola - Plot y=x² on axes with equation overlay. Point tracing left to right.
               Fixed params: x∈[-2,2], y∈[0,4], equation y=x²
    circle   - Plot unit circle x²+y²=1 on axes with equation overlay.
               Fixed params: center origin, radius r=1
    ellipse  - Plot ellipse (x/2)²+y²=1 with equation overlay.
               Fixed params: a=2, b=1
    compare  - Two-column layout: left=Greek straightedge/compass (circle drawn),
               right=Descartes' algebraic approach (y=x² with equation).
               Shows the unification of two traditions.

Duration-aware: reads target duration from _manim_params.json.
Y range: -0.8 to +3.0 (axes), title at +3.0, subtitle clearance preserved.

Used by: Episode 012 (Descartes), math pillar 1
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    Circle,
    DashedLine,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    ParametricFunction,
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
)

config.background_color = BG_COLOR


class CurveEquation(Scene):
    """Curve↔equation correspondence — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "parabola")
        self._duration = params.get("duration", 25)

        if mode == "circle":
            self._build_circle()
        elif mode == "ellipse":
            self._build_ellipse()
        elif mode == "compare":
            self._build_compare()
        else:
            self._build_parabola()

    # ------------------------------------------------------------------
    def _make_axes(self, x_range, y_range, x_length, y_length, shift=DOWN * 0.2):
        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.5},
        )
        axes.shift(shift)
        return axes

    # ------------------------------------------------------------------
    def _build_parabola(self):
        duration = self._duration

        # Title and equation at top
        title = Text("曲線は方程式である", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"y = x^2", font_size=48, color=ACCENT_CYAN)
        eq.move_to([0, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.6)

        # Axes
        axes = self._make_axes(
            x_range=[-2.5, 2.5, 1],
            y_range=[-0.3, 3.2, 1],
            x_length=6.5,
            y_length=3.3,
            shift=DOWN * 0.6,
        )
        self.play(FadeIn(axes), run_time=0.5)

        # Parabola curve
        curve = axes.plot(lambda x: x * x, x_range=[-1.85, 1.85], color=ACCENT_GOLD, stroke_width=3)
        self.play(FadeIn(curve), run_time=0.8)

        # Trace sample points left-to-right with labeled coordinates
        sample_xs = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        header_anim = 0.6 + 0.6 + 0.5 + 0.8
        per_point_budget = max(0.5, (duration - header_anim - 1.5) / len(sample_xs))
        dot_group = VGroup()
        for xv in sample_xs:
            yv = xv * xv
            pos = axes.c2p(xv, yv)
            dot = Dot(pos, radius=0.08, color=ACCENT_PINK)
            coord_label = MathTex(
                f"({xv:g}, {yv:g})",
                font_size=22,
                color=TEXT_WHITE,
            )
            coord_label.next_to(dot, UP, buff=0.15)
            self.play(FadeIn(dot), FadeIn(coord_label), run_time=min(0.4, per_point_budget * 0.5))
            wait_t = max(0.05, per_point_budget - 0.4)
            self.wait(wait_t)
            if dot_group:
                self.play(FadeOut(coord_label), run_time=0.15)
            dot_group.add(dot)
        self.wait(1.2)

    # ------------------------------------------------------------------
    def _build_circle(self):
        duration = self._duration

        title = Text("曲線は方程式である", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"x^2 + y^2 = 1", font_size=48, color=ACCENT_CYAN)
        eq.move_to([0, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.6)

        axes = self._make_axes(
            x_range=[-1.6, 1.6, 0.5],
            y_range=[-1.6, 1.6, 0.5],
            x_length=4.5,
            y_length=4.5,
            shift=DOWN * 0.5,
        )
        self.play(FadeIn(axes), run_time=0.5)

        # Circle as parametric
        circle_curve = ParametricFunction(
            lambda t: axes.c2p(math.cos(t), math.sin(t)),
            t_range=[0, 2 * math.pi],
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        self.play(FadeIn(circle_curve), run_time=0.8)

        # Trace angular points
        angles_deg = [0, 45, 90, 135, 180, 225, 270, 315]
        header_anim = 0.6 + 0.6 + 0.5 + 0.8
        per_point_budget = max(0.4, (duration - header_anim - 1.5) / len(angles_deg))
        dots = VGroup()
        for deg in angles_deg:
            rad = math.radians(deg)
            xv, yv = math.cos(rad), math.sin(rad)
            pos = axes.c2p(xv, yv)
            dot = Dot(pos, radius=0.07, color=ACCENT_PINK)
            lbl = MathTex(
                f"({xv:.2f}, {yv:.2f})",
                font_size=20,
                color=TEXT_WHITE,
            )
            lbl.next_to(dot, UP * 0.8 + RIGHT * 0.5, buff=0.1)
            self.play(FadeIn(dot), FadeIn(lbl), run_time=min(0.35, per_point_budget * 0.5))
            self.wait(max(0.05, per_point_budget - 0.35))
            self.play(FadeOut(lbl), run_time=0.1)
            dots.add(dot)
        self.wait(1.0)

    # ------------------------------------------------------------------
    def _build_ellipse(self):
        duration = self._duration

        title = Text("曲線は方程式である", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"\left(\frac{x}{2}\right)^2 + y^2 = 1", font_size=44, color=ACCENT_CYAN)
        eq.move_to([0, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.6)

        axes = self._make_axes(
            x_range=[-2.6, 2.6, 1],
            y_range=[-1.6, 1.6, 0.5],
            x_length=6.5,
            y_length=3.5,
            shift=DOWN * 0.5,
        )
        self.play(FadeIn(axes), run_time=0.5)

        ellipse_curve = ParametricFunction(
            lambda t: axes.c2p(2 * math.cos(t), math.sin(t)),
            t_range=[0, 2 * math.pi],
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        self.play(FadeIn(ellipse_curve), run_time=0.8)

        # Highlight axes lengths
        a_line = Line(axes.c2p(0, 0), axes.c2p(2, 0), color=ACCENT_PINK, stroke_width=4)
        a_lbl = MathTex("a=2", font_size=28, color=ACCENT_PINK)
        a_lbl.next_to(a_line, DOWN, buff=0.15)
        b_line = Line(axes.c2p(0, 0), axes.c2p(0, 1), color=ACCENT_CYAN, stroke_width=4)
        b_lbl = MathTex("b=1", font_size=28, color=ACCENT_CYAN)
        b_lbl.next_to(b_line, LEFT, buff=0.15)
        self.play(FadeIn(a_line), FadeIn(a_lbl), run_time=0.6)
        self.play(FadeIn(b_line), FadeIn(b_lbl), run_time=0.6)

        header_anim = 0.6 + 0.6 + 0.5 + 0.8 + 1.2
        self.wait(max(1.0, duration - header_anim))

    # ------------------------------------------------------------------
    def _build_compare(self):
        duration = self._duration

        title = Text(
            "ギリシャの作図と、デカルトの代数",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Vertical divider
        divider = DashedLine(
            start=[0, 2.2, 0],
            end=[0, -2.0, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        self.play(FadeIn(divider), run_time=0.4)

        # ---- Left: Greek approach ----
        left_label = Text("ギリシャ", font=FONT, font_size=24, color=TEXT_DIM)
        left_label.move_to([-3.3, 2.3, 0])

        tools_label = Text("コンパスと定規", font=FONT, font_size=20, color=TEXT_DIM)
        tools_label.move_to([-3.3, 1.7, 0])

        left_axes_shift = [-3.3, -0.6, 0]
        greek_circle = Circle(radius=1.1, color=ACCENT_CYAN, stroke_width=3)
        greek_circle.move_to(left_axes_shift)
        center_dot = Dot(left_axes_shift, radius=0.05, color=TEXT_WHITE)
        radius_line = Line(
            left_axes_shift,
            [left_axes_shift[0] + 1.1, left_axes_shift[1], 0],
            color=ACCENT_PINK,
            stroke_width=3,
        )

        self.play(FadeIn(left_label), FadeIn(tools_label), run_time=0.5)
        self.play(FadeIn(center_dot), FadeIn(radius_line), run_time=0.6)
        self.play(FadeIn(greek_circle), run_time=0.9)

        # ---- Right: Descartes approach ----
        right_label = Text("デカルト", font=FONT, font_size=24, color=TEXT_DIM)
        right_label.move_to([3.3, 2.3, 0])

        eq_label = MathTex(r"y = x^2", font_size=32, color=ACCENT_CYAN)
        eq_label.move_to([3.3, 1.7, 0])

        right_axes = Axes(
            x_range=[-1.6, 1.6, 1],
            y_range=[-0.3, 2.5, 1],
            x_length=2.8,
            y_length=2.4,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.2},
        )
        right_axes.move_to([3.3, -0.6, 0])

        para = right_axes.plot(
            lambda x: x * x,
            x_range=[-1.4, 1.4],
            color=ACCENT_GOLD,
            stroke_width=3,
        )

        self.play(FadeIn(right_label), FadeIn(eq_label), run_time=0.5)
        self.play(FadeIn(right_axes), run_time=0.5)
        self.play(FadeIn(para), run_time=0.9)

        # Bottom caption
        caption = Text(
            "2000年の幾何学が、方程式になった",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        caption.move_to([0, -1.9, 0])
        self.play(FadeIn(caption), run_time=0.8)

        anim_time = 0.6 + 0.4 + 0.5 + 0.6 + 0.9 + 0.5 + 0.5 + 0.9 + 0.8
        self.wait(max(1.0, duration - anim_time))


# ---------------------------------------------------------------------------
# B-10 / B-24: factual claims displayed in each mode.
# "2000年の幾何学" caption refers to elapsed years from Greek geometry,
# not a year — intentionally omitted from "years".
LINT_FACTUAL_CLAIMS = {
    "parabola": {"people": [], "years": []},
    "circle": {"people": [], "years": []},
    "ellipse": {"people": [], "years": []},
    "compare": {"people": [["デカルト", "Descartes"]], "years": []},
}


SCENES = {
    "parabola": CurveEquation,
    "circle": CurveEquation,
    "ellipse": CurveEquation,
    "compare": CurveEquation,
}
