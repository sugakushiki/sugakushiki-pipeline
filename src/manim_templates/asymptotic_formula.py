"""
asymptotic_formula.py - Hardy-Ramanujan asymptotic formula for 数学史記

Displays the Hardy-Ramanujan asymptotic formula for p(n) and optionally
compares the approximation with actual values.

Modes:
    formula    - Display the formula with highlight animation
    comparison - Show formula vs actual p(n) values side by side

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 004 (Ramanujan), math_03
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    FadeIn,
    MathTex,
    Scene,
    SurroundingRectangle,
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


def hardy_ramanujan_approx(n):
    """Compute the leading term of the Hardy-Ramanujan asymptotic formula."""
    if n <= 0:
        return 0
    return (1.0 / (4.0 * n * math.sqrt(3))) * math.exp(math.pi * math.sqrt(2.0 * n / 3.0))


# Exact p(n) values for reference
EXACT_PN = {
    1: 1,
    2: 2,
    3: 3,
    4: 5,
    5: 7,
    6: 11,
    7: 15,
    8: 22,
    9: 30,
    10: 42,
    20: 627,
    50: 204226,
    100: 190569292,
    200: 3972999029388,
}


class AsymptoticFormula(Scene):
    """Display the Hardy-Ramanujan asymptotic formula."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 20)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        # Title line
        title = Text("Hardy-Ramanujan (1918)", font=FONT, font_size=32, color=TEXT_DIM)
        title.to_edge(UP, buff=0.5)

        # The formula
        formula = MathTex(
            r"p(n)",
            r"\sim",
            r"\frac{1}{4n\sqrt{3}}",
            r"\, e^{\,\pi\sqrt{2n/3}}",
            font_size=48,
        )
        formula[0].set_color(ACCENT_CYAN)
        formula[2].set_color(TEXT_WHITE)
        formula[3].set_color(highlight_color)
        formula.move_to([0, 0.8, 0])

        # Explanation
        note1 = Text(
            "n が大きいほど近似精度が上がる",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        note1.move_to([0, -0.5, 0])

        # Highlight box around exponential part
        box = SurroundingRectangle(formula[3], color=highlight_color, buff=0.1)

        wait_unit = max(0.5, (duration - 5) / 4)

        self.play(FadeIn(title), run_time=0.6)
        self.wait(wait_unit * 0.5)

        self.play(FadeIn(formula), run_time=1.2)
        self.wait(wait_unit)

        self.play(FadeIn(box), run_time=0.5)
        self.wait(wait_unit)

        self.play(FadeIn(note1), run_time=0.6)
        self.wait(wait_unit * 1.5)


class AsymptoticComparison(Scene):
    """Compare Hardy-Ramanujan approximation with actual p(n) values."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 25)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        title = Text("Hardy-Ramanujan (1918)", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)

        # Formula (compact)
        formula = MathTex(
            r"p(n) \sim \frac{1}{4n\sqrt{3}} \, e^{\,\pi\sqrt{2n/3}}",
            font_size=36,
            color=highlight_color,
        )
        formula.next_to(title, DOWN, buff=0.4)

        self.play(FadeIn(title), FadeIn(formula), run_time=1.0)

        # Comparison data
        test_values = [10, 50, 100, 200]
        entries = VGroup()

        for n in test_values:
            approx = hardy_ramanujan_approx(n)
            exact = EXACT_PN.get(n, 0)

            if exact < 1_000_000:
                exact_str = f"{exact:,}"
            else:
                exact_exp = len(str(exact)) - 1
                exact_str = f"\\approx {str(exact)[:4]}\\times 10^{{{exact_exp}}}"

            if approx < 1_000_000:
                approx_str = f"{approx:,.0f}"
            else:
                approx_exp = int(math.log10(approx))
                approx_lead = approx / (10**approx_exp)
                approx_str = f"\\approx {approx_lead:.2f}\\times 10^{{{approx_exp}}}"

            # Error percentage
            if exact > 0:
                error_pct = abs(approx - exact) / exact * 100
                error_str = f"{error_pct:.1f}\\%"
            else:
                error_str = "-"

            row = VGroup(
                MathTex(f"n={n}", font_size=26, color=ACCENT_CYAN),
                MathTex(f"p({n}) = {exact_str}", font_size=22, color=TEXT_WHITE),
                MathTex(f"\\text{{approx}} = {approx_str}", font_size=22, color=highlight_color),
                MathTex(f"\\text{{error}} \\approx {error_str}", font_size=22, color=ACCENT_PINK),
            )
            row.arrange(RIGHT, buff=0.3)
            entries.add(row)

        entries.arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        entries.next_to(formula, DOWN, buff=0.6)

        wait_per = max(0.3, (duration - 5) / len(test_values))

        for entry in entries:
            self.play(FadeIn(entry), run_time=0.8)
            self.wait(wait_per)

        self.wait(1.0)


# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "formula": {
        "people": [
            ["Hardy", "ハーディ"],
            ["Ramanujan", "ラマヌジャン"],
        ],
        "years": ["1918"],
    },
    "comparison": {
        "people": [
            ["Hardy", "ハーディ"],
            ["Ramanujan", "ラマヌジャン"],
        ],
        "years": ["1918"],
    },
}


SCENES = {
    "formula": AsymptoticFormula,
    "comparison": AsymptoticComparison,
}
