"""
entropy_calculation.py - Information entropy visualization for 数学史記

Visualizes Shannon's information entropy concept with intuitive examples.

Modes:
    coin_flip  - Fair coin: 50/50 probability → H = 1 bit
                 Fixed params: 2 outcomes (H/T), p=0.5 each, result = 1 bit
    weather    - Biased distribution (80% sun / 20% rain) → lower entropy
                 Fixed params: 2 outcomes, p=[0.8, 0.2], result ≈ 0.72 bit
    formula    - General formula H = -Σ p_i log₂ p_i with highlights
                 Fixed params: 7-part MathTex, annotations for H, p_i, log₂

Duration-aware: reads target duration from _manim_params.json.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    BarChart,
    FadeIn,
    Indicate,
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
    FONT,
    TEXT_DIM,
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


class EntropyCalculation(Scene):
    """Visualize information entropy with intuitive examples."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "coin_flip")
        self._duration = params.get("duration", 25)

        if mode == "weather":
            self.build_weather()
        elif mode == "formula":
            self.build_formula()
        else:
            self.build_coin_flip()

    # -------------------------------------------------------------------
    # Mode: coin_flip
    # -------------------------------------------------------------------
    def build_coin_flip(self):
        """Fair coin: 50/50 → H = 1 bit."""
        dur = self._duration
        anim_time = 5.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Title
        title = Text(
            "公正なコインのエントロピー",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Bar chart for probabilities
        chart = BarChart(
            values=[0.5, 0.5],
            bar_names=["H", "T"],
            y_range=[0, 1, 0.25],
            y_length=3.0,
            x_length=4.0,
            bar_colors=[ACCENT_CYAN, ACCENT_PINK],
            bar_width=0.8,
        )
        chart.shift(LEFT * 2.5 + DOWN * 0.3)

        # Labels
        prob_label_h = Text("50%", font=FONT, font_size=22, color=ACCENT_CYAN)
        prob_label_h.next_to(chart.bars[0], UP, buff=0.15)
        prob_label_t = Text("50%", font=FONT, font_size=22, color=ACCENT_PINK)
        prob_label_t.next_to(chart.bars[1], UP, buff=0.15)

        self.play(FadeIn(chart), run_time=1.0)
        self.play(FadeIn(prob_label_h), FadeIn(prob_label_t), run_time=0.5)
        self.wait(1.0 * ws)

        # Entropy result
        entropy_box = VGroup()
        eq = MathTex(
            r"H = -\sum p_i \log_2 p_i",
            font_size=36,
            color=TEXT_DIM,
        )
        eq.shift(RIGHT * 2.5 + UP * 0.5)

        calc = MathTex(
            r"= -2 \times 0.5 \times \log_2 0.5",
            font_size=32,
            color=TEXT_WHITE,
        )
        calc.next_to(eq, DOWN, buff=0.4)

        result = MathTex(
            r"= 1 \text{ bit}",
            font_size=44,
            color=ACCENT_GOLD,
        )
        result.next_to(calc, DOWN, buff=0.4)

        self.play(FadeIn(eq), run_time=0.8)
        self.wait(0.5 * ws)
        self.play(FadeIn(calc), run_time=0.8)
        self.wait(0.5 * ws)
        self.play(FadeIn(result), run_time=0.8)
        self.wait(1.0 * ws)

        # Explanation
        note = Text(
            "結果が完全に予測不能 = 最大エントロピー",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: weather
    # -------------------------------------------------------------------
    def build_weather(self):
        """Biased distribution: 80% sun / 20% rain → lower entropy."""
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Title
        title = Text(
            "偏った分布のエントロピー",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Bar chart
        chart = BarChart(
            values=[0.8, 0.2],
            bar_names=["Sun", "Rain"],
            y_range=[0, 1, 0.25],
            y_length=3.0,
            x_length=4.0,
            bar_colors=[ACCENT_GOLD, ACCENT_CYAN],
            bar_width=0.8,
        )
        chart.shift(LEFT * 2.5 + DOWN * 0.3)

        prob_label_s = Text("80%", font=FONT, font_size=22, color=ACCENT_GOLD)
        prob_label_s.next_to(chart.bars[0], UP, buff=0.15)
        prob_label_r = Text("20%", font=FONT, font_size=22, color=ACCENT_CYAN)
        prob_label_r.next_to(chart.bars[1], UP, buff=0.15)

        self.play(FadeIn(chart), run_time=1.0)
        self.play(FadeIn(prob_label_s), FadeIn(prob_label_r), run_time=0.5)
        self.wait(1.0 * ws)

        # Calculation
        calc_line1 = MathTex(
            r"H = -(0.8 \log_2 0.8 + 0.2 \log_2 0.2)",
            font_size=30,
            color=TEXT_WHITE,
        )
        calc_line1.shift(RIGHT * 2.5 + UP * 0.8)

        # Compute actual value
        h_val = -(0.8 * math.log2(0.8) + 0.2 * math.log2(0.2))
        result = MathTex(
            rf"= {h_val:.2f} \text{{ bit}}",
            font_size=40,
            color=ACCENT_GOLD,
        )
        result.next_to(calc_line1, DOWN, buff=0.5)

        self.play(FadeIn(calc_line1), run_time=0.8)
        self.wait(0.5 * ws)
        self.play(FadeIn(result), run_time=0.8)
        self.wait(1.0 * ws)

        # Comparison with fair coin
        sep = Line(LEFT * 1.5, RIGHT * 1.5, color=ACCENT_GOLD, stroke_width=1.5)
        sep.next_to(result, DOWN, buff=0.5)

        compare = Text(
            "公正なコイン: 1.00 bit",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        compare.next_to(sep, DOWN, buff=0.3)

        note = Text(
            "予測しやすい = エントロピーが低い",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.next_to(compare, DOWN, buff=0.4)

        self.play(FadeIn(sep), FadeIn(compare), run_time=0.5)
        self.wait(0.5 * ws)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: formula
    # -------------------------------------------------------------------
    def build_formula(self):
        """General entropy formula with part highlights."""
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Title
        title = Text(
            "シャノンの情報エントロピー",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Main formula
        formula = MathTex(
            r"H",
            r"=",
            r"-",
            r"\sum_{i}",
            r"p_i",
            r"\log_2",
            r"p_i",
            font_size=56,
            color=TEXT_WHITE,
        )
        formula.shift(UP * 0.5)
        self.play(FadeIn(formula), run_time=1.5)
        self.wait(1.0 * ws)

        # Annotations for each part
        ann_h = Text("エントロピー（不確実性）", font=FONT, font_size=20, color=ACCENT_GOLD)
        ann_h.next_to(formula[0], DOWN, buff=1.2)
        arr_h = Line(
            ann_h.get_top(),
            formula[0].get_bottom() + DOWN * 0.1,
            color=ACCENT_GOLD,
            stroke_width=1.5,
        )

        self.play(
            Indicate(formula[0], color=ACCENT_GOLD, scale_factor=1.3),
            FadeIn(ann_h),
            FadeIn(arr_h),
            run_time=1.0,
        )
        self.wait(0.8 * ws)

        ann_p = Text("各事象の確率", font=FONT, font_size=20, color=ACCENT_CYAN)
        ann_p.next_to(formula[4], DOWN, buff=1.2)
        arr_p = Line(
            ann_p.get_top(),
            formula[4].get_bottom() + DOWN * 0.1,
            color=ACCENT_CYAN,
            stroke_width=1.5,
        )

        self.play(
            Indicate(formula[4], color=ACCENT_CYAN, scale_factor=1.3),
            FadeIn(ann_p),
            FadeIn(arr_p),
            run_time=1.0,
        )
        self.wait(0.8 * ws)

        ann_log = Text("情報量（驚きの度合い）", font=FONT, font_size=20, color=ACCENT_PINK)
        ann_log.next_to(formula[5], DOWN, buff=1.8)
        arr_log = Line(
            ann_log.get_top(),
            formula[5].get_bottom() + DOWN * 0.1,
            color=ACCENT_PINK,
            stroke_width=1.5,
        )

        self.play(
            Indicate(formula[5], color=ACCENT_PINK, scale_factor=1.3),
            Indicate(formula[6], color=ACCENT_PINK, scale_factor=1.3),
            FadeIn(ann_log),
            FadeIn(arr_log),
            run_time=1.0,
        )
        self.wait(1.0 * ws)

        # Bottom note
        note = Text(
            "珍しい事象ほど大きな情報量を持つ",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "coin_flip": {"people": [], "years": []},
    "weather": {"people": [], "years": []},
    "formula": {"people": [], "years": []},
}



# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
SCENES = {
    "coin_flip": EntropyCalculation,
    "weather": EntropyCalculation,
    "formula": EntropyCalculation,
}
