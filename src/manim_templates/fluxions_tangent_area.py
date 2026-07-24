"""
fluxions_tangent_area.py - Newton's fluxions: differentiation and integration
as inverse operations, for 数学史記

The heart of Newton's "method of fluxions" (his calculus) is that two operations
are inverse to each other:
    - the slope of the tangent to a curve = the rate of change (differentiation)
    - the area under a curve = its accumulation (integration)
Finding the slope and finding the area undo one another.

Modes:
    tangent_area - One curve y = 0.25 x^2 + 0.3 on Axes. First a dot sweeps the
                   curve showing the moving TANGENT (slope = rate of change =
                   differentiation); then it sweeps again with the AREA filling
                   underneath (integration). Full-scene motion (ValueTracker).
                   Fixed curve: f(x)=0.25x^2+0.3, f'(x)=0.5x, x in [-2.2, 2.2].
    notation     - The same idea symbolically: differentiation (left) and
                   integration (right) shown as inverse, with Newton's dot
                   (fluxion) notation x-dot and Leibniz's dy/dx and integral
                   sign. Reveals spread across the duration.

Duration-aware: reads target duration from _manim_params.json; motion/reveals
fill the scene with a fixed ~2.5s coda (no long static tail).
Y range: title at +2.9, all content within -1.85 .. +2.0.

Used by: Episode 037 (Newton), math pillar 2 (calculus / fluxions).
"""

from manim import (
    Arrow,
    Axes,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
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

X0, X1 = -2.2, 2.2


def _f(x):
    return 0.25 * x * x + 0.3


def _df(x):
    return 0.5 * x


class FluxionsTangentArea(Scene):
    """Differentiation (tangent) and integration (area) as inverse operations."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 28)
        mode = params.get("mode", "tangent_area")

        if mode == "notation":
            self._build_notation()
        else:
            self._build_tangent_area()

    # ------------------------------------------------------------------
    # Mode: tangent_area
    # ------------------------------------------------------------------
    def _build_tangent_area(self):
        duration = self._duration

        title = Text(
            "流率法 ── 接線と面積は逆向きの操作",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        axes = Axes(
            x_range=[X0 - 0.2, X1 + 0.2, 1.0],
            y_range=[0, 2.0, 0.5],
            x_length=7.0,
            y_length=2.7,
            axis_config={
                "include_numbers": False,
                "include_tip": True,
                "stroke_width": 2,
                "color": EDGE_COLOR,
            },
        )
        axes.move_to([0, -0.45, 0])

        graph = axes.plot(_f, x_range=[X0, X1, 0.01], color=ACCENT_CYAN, stroke_width=3)

        xt = ValueTracker(X0)

        def make_dot():
            x = xt.get_value()
            return Dot(axes.c2p(x, _f(x)), color=ACCENT_PINK, radius=0.1)

        def make_tangent():
            x = xt.get_value()
            m = _df(x)
            h = 0.55
            p_left = axes.c2p(x - h, _f(x) - m * h)
            p_right = axes.c2p(x + h, _f(x) + m * h)
            return Line(p_left, p_right, color=ACCENT_GOLD, stroke_width=3)

        dot = always_redraw(make_dot)
        tangent = always_redraw(make_tangent)

        diff_lbl = Text(
            "接線の傾き ＝ 変化の速さ（微分）",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        diff_lbl.move_to([0, 1.95, 0])

        # Intro
        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(axes), FadeIn(graph), run_time=1.0)
        self.play(FadeIn(diff_lbl), run_time=0.6)
        self.add(tangent, dot)
        used = 0.7 + 1.0 + 0.6

        coda = 2.5
        reset_t = 0.5
        sweep = max(3.0, (duration - used - coda - reset_t) / 2.0)

        # Phase A: tangent sweep (differentiation)
        self.play(xt.animate.set_value(X1), run_time=sweep, rate_func=lambda a: a)

        # Switch to area (integration)
        self.remove(tangent)
        area_lbl = Text(
            "曲線の下の面積（積分）",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        area_lbl.move_to([0, 1.95, 0])
        area = always_redraw(
            lambda: axes.get_area(
                graph,
                x_range=(X0, max(X0 + 0.001, xt.get_value())),
                color=ACCENT_PINK,
                opacity=0.4,
            )
        )
        self.play(xt.animate.set_value(X0), run_time=reset_t, rate_func=lambda a: a)
        self.add(area)
        self.play(FadeIn(area_lbl), run_time=0.01)
        self.remove(diff_lbl)

        # Phase B: area sweep (integration)
        self.play(xt.animate.set_value(X1), run_time=sweep, rate_func=lambda a: a)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: notation
    # ------------------------------------------------------------------
    def _build_notation(self):
        duration = self._duration

        title = Text(
            "微分と積分は逆向きの操作",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        # Left column: differentiation
        d_head = Text("微分 ── 接線の傾き", font=FONT, font_size=26, color=ACCENT_PINK)
        d_head.move_to([-3.4, 1.4, 0])
        d_newton_lbl = Text("ニュートンの点記法", font=FONT, font_size=20, color=TEXT_DIM)
        d_newton_lbl.move_to([-3.4, 0.55, 0])
        d_newton = MathTex(r"\dot{x}", font_size=46, color=ACCENT_CYAN)
        d_newton.move_to([-3.4, 0.0, 0])
        d_leibniz_lbl = Text("ライプニッツの記法", font=FONT, font_size=20, color=TEXT_DIM)
        d_leibniz_lbl.move_to([-3.4, -0.7, 0])
        d_leibniz = MathTex(r"\frac{dy}{dx}", font_size=46, color=ACCENT_CYAN)
        d_leibniz.move_to([-3.4, -1.35, 0])

        # Right column: integration
        i_head = Text("積分 ── 曲線の下の面積", font=FONT, font_size=26, color=ACCENT_GOLD)
        i_head.move_to([3.4, 1.4, 0])
        i_leibniz_lbl = Text("ライプニッツの記法", font=FONT, font_size=20, color=TEXT_DIM)
        i_leibniz_lbl.move_to([3.4, 0.05, 0])
        i_leibniz = MathTex(r"\int y\,dx", font_size=46, color=ACCENT_GOLD)
        i_leibniz.move_to([3.4, -0.7, 0])

        # Middle: inverse-operation double arrow
        arrow_r = Arrow([-1.0, 0.25, 0], [1.0, 0.25, 0], color=TEXT_WHITE, buff=0.1, stroke_width=4)
        arrow_l = Arrow(
            [1.0, -0.25, 0], [-1.0, -0.25, 0], color=TEXT_WHITE, buff=0.1, stroke_width=4
        )
        inv_lbl = Text("逆の操作", font=FONT, font_size=22, color=ACCENT_PINK)
        inv_lbl.move_to([0, 0.85, 0])

        groups = [
            VGroup(d_head),
            VGroup(i_head),
            VGroup(arrow_r, arrow_l, inv_lbl),
            VGroup(d_newton_lbl, d_newton),
            VGroup(d_leibniz_lbl, d_leibniz),
            VGroup(i_leibniz_lbl, i_leibniz),
        ]

        self.play(FadeIn(title), run_time=0.7)
        used = 0.7

        coda = 2.5
        per = max(1.0, (duration - used - coda) / len(groups))
        for i, g in enumerate(groups):
            self.play(FadeIn(g), run_time=0.6)
            if i == 2:
                self.play(Indicate(inv_lbl, color=ACCENT_GOLD, scale_factor=1.2), run_time=0.5)
                rest = max(0.0, per - 0.6 - 0.5)
            else:
                rest = max(0.0, per - 0.6)
            if rest > 0:
                self.wait(rest)

        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "tangent_area": {"people": [], "years": []},
    "notation": {
        "people": [
            ["ニュートン", "Newton"],
            ["ライプニッツ", "Leibniz"],
        ],
        "years": [],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "tangent_area": {
        "class": "FluxionsTangentArea",
        "params": {"mode": "tangent_area"},
        "description": "A dot sweeps a curve: first the moving tangent (differentiation), then the filling area (integration)",
    },
    "notation": {
        "class": "FluxionsTangentArea",
        "params": {"mode": "notation"},
        "description": "Differentiation vs integration as inverse operations; Newton's x-dot and Leibniz's dy/dx and integral",
    },
}
