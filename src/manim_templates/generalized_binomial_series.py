"""
generalized_binomial_series.py - Newton's generalized binomial theorem for 数学史記

Newton (around 1664-65) extended the binomial expansion from whole-number
exponents, where it terminates, to fractional and negative exponents, where it
becomes an INFINITE series. He then used such series to compute the area under a
curve (quadrature), which is the seed of the integral. In De Analysi he applied
the series for the circle y = sqrt(1 - x^2) and computed pi to many digits.

Modes:
    expansion  - Stack the terminating expansions (1+x)^2 and (1+x)^3 (Pascal
                 coefficients), then generalize the exponent to 1/2 and reveal
                 the non-terminating series term by term:
                 (1+x)^{1/2} = 1 + (1/2)x - (1/8)x^2 + (1/16)x^3
                                 - (5/128)x^4 + ...
                 Fixed coefficients (verified): 1, 1/2, -1/8, 1/16, -5/128.
                 Reveals are spread across the duration (no single tail wait).
    quadrature - Quarter circle y = sqrt(1 - x^2) on Axes (x,y in [0,1.1]); a
                 gold area fills under the curve as a cyan dot sweeps x: 0 -> 1
                 (ValueTracker, full-scene motion). Series for the area shown:
                 int_0^x sqrt(1-t^2) dt = x - (1/6)x^3 - (1/40)x^5 - ...
                 Reaching x = 1 marks the area pi/4.
                 Fixed area-series coefficients (verified): 1, -1/6, -1/40, -1/112.

Duration-aware: reads target duration from _manim_params.json; motion/reveals
fill the scene with a fixed 2.5s coda (no long static tail).
Y range: title at +2.9, all content within -1.9 .. +2.0.

Used by: Episode 037 (Newton), math pillar 1 (infinite series / quadrature).
"""

import numpy as np
from manim import (
    Axes,
    Dot,
    FadeIn,
    Indicate,
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


class GeneralizedBinomialSeries(Scene):
    """Newton's generalized binomial theorem and series quadrature."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 24)
        mode = params.get("mode", "expansion")

        if mode == "quadrature":
            self._build_quadrature()
        elif mode == "pascal":
            self._build_pascal()
        else:
            self._build_expansion()

    # ------------------------------------------------------------------
    # Mode: pascal (integer binomial coefficients via Pascal's triangle)
    # ------------------------------------------------------------------
    def _build_pascal(self):
        duration = self._duration

        title = Text(
            "整数の二項展開とパスカルの三角形",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        rows_data = [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]
        dx, dy, y_top = 0.62, 0.46, 1.95
        row_groups = []
        for i, row in enumerate(rows_data):
            g = VGroup()
            for j, val in enumerate(row):
                t = MathTex(str(val), font_size=34, color=TEXT_WHITE)
                t.move_to([(j - i / 2.0) * dx, y_top - i * dy, 0])
                g.add(t)
            row_groups.append(g)

        expansion = MathTex(r"(1+x)^3 = 1 + 3x + 3x^2 + x^3", font_size=36, color=ACCENT_CYAN)
        expansion.move_to([0, -0.85, 0])
        note = Text(
            "指数が整数なら、項は有限で終わる",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.6, 0])

        self.play(FadeIn(title), run_time=0.7)
        used = 0.7
        coda = 2.5
        reveal_budget = max(2.0, duration - used - coda - 2.2)
        per = reveal_budget / len(row_groups)
        show = min(0.6, per * 0.6)
        for g in row_groups:
            self.play(FadeIn(g), run_time=show)
            rest = max(0.0, per - show)
            if rest > 0:
                self.wait(rest)

        self.play(row_groups[3].animate.set_color(ACCENT_GOLD), run_time=0.6)
        self.play(FadeIn(expansion), run_time=0.7)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: expansion
    # ------------------------------------------------------------------
    def _build_expansion(self):
        duration = self._duration

        title = Text(
            "一般化二項定理 ── 無限へ続く展開",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        row2 = MathTex(
            r"(1+x)^2 = 1 + 2x + x^2",
            font_size=38,
            color=TEXT_WHITE,
        )
        row2.move_to([0, 1.75, 0])

        row3 = MathTex(
            r"(1+x)^3 = 1 + 3x + 3x^2 + x^3",
            font_size=38,
            color=TEXT_WHITE,
        )
        row3.move_to([0, 1.0, 0])

        bridge = Text(
            "指数を分数にすると、項は終わらない",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        bridge.move_to([0, 0.2, 0])

        # Infinite series, built as separate terms for one-by-one reveal.
        term_strs = [
            r"(1+x)^{\frac{1}{2}} =",
            r"1",
            r"+\tfrac{1}{2}x",
            r"-\tfrac{1}{8}x^2",
            r"+\tfrac{1}{16}x^3",
            r"-\tfrac{5}{128}x^4",
            r"+\cdots",
        ]
        terms = VGroup(*[MathTex(s, font_size=36, color=ACCENT_CYAN) for s in term_strs])
        terms.arrange(buff=0.16)
        terms.move_to([0, -0.85, 0])
        terms[0].set_color(ACCENT_GOLD)
        terms[-1].set_color(ACCENT_GOLD)

        # Intro: finite rows + bridge
        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(row2), run_time=0.7)
        self.play(FadeIn(row3), run_time=0.7)
        self.play(FadeIn(bridge), run_time=0.7)
        used = 0.7 * 4

        # Spread the infinite-series term reveals across the rest of the scene.
        coda = 2.5
        reveal_budget = max(2.0, duration - used - coda)
        per = reveal_budget / len(terms)
        show = min(0.6, per * 0.5)
        for i, t in enumerate(terms):
            self.play(FadeIn(t), run_time=show)
            if 0 < i < len(terms) - 1:
                self.play(
                    Indicate(t, scale_factor=1.15, color=ACCENT_PINK), run_time=min(0.5, per * 0.3)
                )
                rest = max(0.0, per - show - min(0.5, per * 0.3))
            else:
                rest = max(0.0, per - show)
            if rest > 0:
                self.wait(rest)

        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: quadrature
    # ------------------------------------------------------------------
    def _build_quadrature(self):
        duration = self._duration

        title = Text(
            "無限級数で円の面積を求める",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        axes = Axes(
            x_range=[0, 1.1, 0.25],
            y_range=[0, 1.1, 0.25],
            x_length=3.6,
            y_length=3.6,
            axis_config={
                "include_numbers": False,
                "include_tip": True,
                "stroke_width": 2,
                "color": EDGE_COLOR,
            },
        )
        axes.move_to([-3.0, -0.05, 0])

        graph = axes.plot(
            lambda x: float(np.sqrt(max(0.0, 1.0 - x * x))),
            x_range=[0, 1.0, 0.01],
            color=ACCENT_CYAN,
            stroke_width=3,
        )
        curve_lbl = MathTex(r"y=\sqrt{1-x^2}", font_size=30, color=ACCENT_CYAN)
        curve_lbl.next_to(axes.c2p(0.62, 0.86), np.array([1, 1, 0]), buff=0.1)

        t = ValueTracker(0.0)
        area = always_redraw(
            lambda: axes.get_area(
                graph,
                x_range=(0.0, max(0.001, t.get_value())),
                color=ACCENT_GOLD,
                opacity=0.45,
            )
        )
        dot = always_redraw(
            lambda: Dot(
                axes.c2p(t.get_value(), float(np.sqrt(max(0.0, 1.0 - t.get_value() ** 2)))),
                color=ACCENT_PINK,
                radius=0.09,
            )
        )

        series = MathTex(
            r"\int_0^x \!\sqrt{1-t^2}\,dt",
            r"= x - \tfrac{1}{6}x^3 - \tfrac{1}{40}x^5 - \cdots",
            font_size=32,
            color=TEXT_WHITE,
        )
        series.arrange(np.array([0, -1, 0]), buff=0.25)
        series.move_to([2.7, 0.9, 0])
        series[0].set_color(ACCENT_CYAN)

        note = Text(
            "x = 1 で 四分円の面積",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        note.move_to([2.7, -0.4, 0])
        quarter = MathTex(r"=\dfrac{\pi}{4}", font_size=40, color=ACCENT_GOLD)
        quarter.next_to(note, np.array([0, -1, 0]), buff=0.25)

        # Intro
        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(axes), FadeIn(graph), FadeIn(curve_lbl), run_time=1.0)
        self.play(FadeIn(series), run_time=0.8)
        self.add(area, dot)
        used = 0.7 + 1.0 + 0.8

        # Full-scene sweep: the dot traverses the curve while the area fills.
        coda = 2.5
        motion = max(2.5, duration - used - coda - 1.0)
        self.play(t.animate.set_value(1.0), run_time=motion, rate_func=lambda a: a)
        self.play(FadeIn(note), FadeIn(quarter), run_time=1.0)
        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No people or year text is shown on screen in either mode.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "expansion": {"people": [], "years": []},
    "quadrature": {"people": [], "years": []},
    "pascal": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "expansion": {
        "class": "GeneralizedBinomialSeries",
        "params": {"mode": "expansion"},
        "description": "Binomial expansion from whole-number exponents to the infinite (1+x)^{1/2} series",
    },
    "quadrature": {
        "class": "GeneralizedBinomialSeries",
        "params": {"mode": "quadrature"},
        "description": "Series quadrature of the circle y=sqrt(1-x^2); area fills as the dot sweeps to x=1 (pi/4)",
    },
    "pascal": {
        "class": "GeneralizedBinomialSeries",
        "params": {"mode": "pascal"},
        "description": "Pascal's triangle building up the integer binomial coefficients; row 3 -> (1+x)^3 (finite)",
    },
}
