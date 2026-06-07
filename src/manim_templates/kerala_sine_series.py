"""
kerala_sine_series.py - Kerala school's sine/cosine Taylor series for 数学史記

Visualizes Mādhava's sine and cosine power series (Taylor expansions),
preserved by the Kerala school through Tantrasaṅgraha (1501) and
Yuktibhāṣā (c.1550). These series predate Newton (1669) by ~270 years.

Modes:
    sine_series   - sin(x) = x - x³/3! + x⁵/5! - x⁷/7! + ...
                    Partial sums plotted in sequence, converging to sin(x).
                    Fixed params: degrees 1, 3, 5, 7, 9 shown.
    cosine_series - cos(x) = 1 - x²/2! + x⁴/4! - x⁶/6! + ...
                    Partial sums plotted similarly.
                    Fixed params: degrees 0, 2, 4, 6, 8 shown.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 015 (Mādhava), math pillar 4.
"""

import math

from manim import (
    DOWN,
    LEFT,
    UP,
    Axes,
    FadeIn,
    FadeOut,
    MathTex,
    Scene,
    Text,
    config,
)
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    ACCENT_PINK,
    BG_COLOR,
    FONT,
    TEXT_DIM,
    load_params,
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------
def sine_partial_sum(x: float, n_terms: int) -> float:
    """Partial sum of sin Taylor series: Σ_{k=0..n-1} (-1)^k x^(2k+1) / (2k+1)!"""
    s = 0.0
    for k in range(n_terms):
        sign = (-1) ** k
        power = 2 * k + 1
        s += sign * (x**power) / math.factorial(power)
    return s


def cosine_partial_sum(x: float, n_terms: int) -> float:
    """Partial sum of cos Taylor series: Σ_{k=0..n-1} (-1)^k x^(2k) / (2k)!"""
    s = 0.0
    for k in range(n_terms):
        sign = (-1) ** k
        power = 2 * k
        s += sign * (x**power) / math.factorial(power)
    return s


class KeralaSineSeries(Scene):
    """Kerala school's sine/cosine series. Mode-branching scene.

    Modes:
        sine_series (default) - sin(x) Taylor partial sums
        cosine_series         - cos(x) Taylor partial sums
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "sine_series")

        if mode == "cosine_series":
            self.build_cosine_series()
        else:
            self.build_sine_series()

    # -------------------------------------------------------------------
    # Mode: sine_series
    # -------------------------------------------------------------------
    def build_sine_series(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("マーダヴァの正弦級数", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)

        formula = MathTex(
            r"\sin x",
            r"=",
            r"x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!} + \cdots",
            font_size=30,
        )
        formula[0].set_color(ACCENT_PINK)
        formula.next_to(title, DOWN, buff=0.3)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(formula), run_time=1.0)
        self.wait(0.5)

        axes = Axes(
            x_range=[-math.pi - 0.3, math.pi + 0.3, math.pi / 2],
            y_range=[-1.3, 1.3, 0.5],
            x_length=9.5,
            y_length=3.3,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.3)

        true_sin = axes.plot(
            math.sin,
            x_range=[-math.pi, math.pi, 0.01],
            color=ACCENT_PINK,
            stroke_width=4.0,
            stroke_opacity=0.5,
        )

        self.play(FadeIn(axes), run_time=0.7)
        self.play(FadeIn(true_sin), run_time=0.7)
        self.wait(0.3)

        # Partial sums: 1, 2, 3, 4, 5 terms → degrees 1, 3, 5, 7, 9
        n_terms_list = [1, 2, 3, 4, 5]
        degrees = [2 * n - 1 for n in n_terms_list]
        colors = [ACCENT_CYAN, ACCENT_GOLD, "#7b68ee", "#20b2aa", highlight]

        anim_overhead = 0.5 + 1.0 + 0.5 + 0.7 + 0.7 + 0.3 + 1.0
        per_step = max(0.5, (duration - anim_overhead) / max(len(n_terms_list), 1))

        current_graph = None
        degree_label = None

        for i, (n_terms, deg, color) in enumerate(zip(n_terms_list, degrees, colors, strict=False)):
            # Plot partial sum, clipped to a reasonable y range
            def make_fn(nt):
                def fn(x):
                    v = sine_partial_sum(x, nt)
                    # Clip to avoid runaway at edges for low-degree approximations
                    if v > 2.5:
                        return 2.5
                    if v < -2.5:
                        return -2.5
                    return v

                return fn

            new_graph = axes.plot(
                make_fn(n_terms),
                x_range=[-math.pi, math.pi, 0.01],
                color=color,
                stroke_width=3.5,
            )

            new_label = MathTex(
                r"\text{degree } " + str(deg),
                font_size=28,
                color=color,
            )
            new_label.to_corner(DOWN + LEFT, buff=0.5)
            new_label.shift(UP * 0.3)

            if current_graph is None:
                self.play(FadeIn(new_graph), FadeIn(new_label), run_time=0.6)
            else:
                self.play(
                    FadeOut(current_graph),
                    FadeOut(degree_label),
                    FadeIn(new_graph),
                    FadeIn(new_label),
                    run_time=0.6,
                )
            current_graph = new_graph
            degree_label = new_label
            self.wait(per_step * 0.5)

        self.wait(max(0.5, per_step * 0.5))

    # -------------------------------------------------------------------
    # Mode: cosine_series
    # -------------------------------------------------------------------
    def build_cosine_series(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("マーダヴァの余弦級数", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)

        formula = MathTex(
            r"\cos x",
            r"=",
            r"1 - \frac{x^2}{2!} + \frac{x^4}{4!} - \frac{x^6}{6!} + \cdots",
            font_size=30,
        )
        formula[0].set_color(ACCENT_CYAN)
        formula.next_to(title, DOWN, buff=0.3)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(formula), run_time=1.0)
        self.wait(0.5)

        axes = Axes(
            x_range=[-math.pi - 0.3, math.pi + 0.3, math.pi / 2],
            y_range=[-1.3, 1.3, 0.5],
            x_length=9.5,
            y_length=3.3,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.3)

        true_cos = axes.plot(
            math.cos,
            x_range=[-math.pi, math.pi, 0.01],
            color=ACCENT_CYAN,
            stroke_width=4.0,
            stroke_opacity=0.5,
        )

        self.play(FadeIn(axes), run_time=0.7)
        self.play(FadeIn(true_cos), run_time=0.7)
        self.wait(0.3)

        # Partial sums: 1, 2, 3, 4, 5 terms → degrees 0, 2, 4, 6, 8
        n_terms_list = [1, 2, 3, 4, 5]
        degrees = [2 * (n - 1) for n in n_terms_list]
        colors = [ACCENT_PINK, ACCENT_GOLD, "#7b68ee", "#20b2aa", highlight]

        anim_overhead = 0.5 + 1.0 + 0.5 + 0.7 + 0.7 + 0.3 + 1.0
        per_step = max(0.5, (duration - anim_overhead) / max(len(n_terms_list), 1))

        current_graph = None
        degree_label = None

        for i, (n_terms, deg, color) in enumerate(zip(n_terms_list, degrees, colors, strict=False)):

            def make_fn(nt):
                def fn(x):
                    v = cosine_partial_sum(x, nt)
                    if v > 2.5:
                        return 2.5
                    if v < -2.5:
                        return -2.5
                    return v

                return fn

            new_graph = axes.plot(
                make_fn(n_terms),
                x_range=[-math.pi, math.pi, 0.01],
                color=color,
                stroke_width=3.5,
            )

            new_label = MathTex(
                r"\text{degree } " + str(deg),
                font_size=28,
                color=color,
            )
            new_label.to_corner(DOWN + LEFT, buff=0.5)
            new_label.shift(UP * 0.3)

            if current_graph is None:
                self.play(FadeIn(new_graph), FadeIn(new_label), run_time=0.6)
            else:
                self.play(
                    FadeOut(current_graph),
                    FadeOut(degree_label),
                    FadeIn(new_graph),
                    FadeIn(new_label),
                    run_time=0.6,
                )
            current_graph = new_graph
            degree_label = new_label
            self.wait(per_step * 0.5)

        self.wait(max(0.5, per_step * 0.5))


# Factual-claim metadata (read by qa_manim_consistency.py). Both modes title
# the curves "マーダヴァの正弦/余弦級数".
LINT_FACTUAL_CLAIMS = {
    "sine_series": {"people": [["マーダヴァ", "Madhava"]], "years": []},
    "cosine_series": {"people": [["マーダヴァ", "Madhava"]], "years": []},
}

# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "sine_series": {
        "class": "KeralaSineSeries",
        "params": {"mode": "sine_series"},
        "description": "sin(x) Taylor partial sums converging to true sin curve (degrees 1,3,5,7,9)",
    },
    "cosine_series": {
        "class": "KeralaSineSeries",
        "params": {"mode": "cosine_series"},
        "description": "cos(x) Taylor partial sums converging to true cos curve (degrees 0,2,4,6,8)",
    },
}
