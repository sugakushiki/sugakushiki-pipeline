"""
continued_fraction.py - Ramanujan's continued fractions for 数学史記

Visualizes continued fraction expansion, showing the nested structure
that "defeated" Hardy.

Modes:
    expand   - Build a continued fraction level by level
    collapse - Show a full continued fraction, then simplify to a value

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 004 (Ramanujan), math_07
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    FadeIn,
    FadeOut,
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


class ContinuedFractionExpand(Scene):
    """Build a continued fraction level by level."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 25)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        title = Text("Ramanujan's Continued Fractions", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.6)

        # Build levels of a continued fraction for e^(-2pi/5)
        # This is the famous Rogers-Ramanujan CF from the letter to Hardy
        levels = [
            r"\cfrac{e^{-2\pi/5}}{1+\cdots}",
            r"\cfrac{e^{-2\pi/5}}{1+\cfrac{e^{-2\pi}}{1+\cdots}}",
            r"\cfrac{e^{-2\pi/5}}{1+\cfrac{e^{-2\pi}}{1+\cfrac{e^{-4\pi}}{1+\cdots}}}",
        ]

        wait_per = max(0.8, (duration - 6) / (len(levels) + 2))

        prev_cf = None
        for _i, latex in enumerate(levels):
            cf = MathTex(latex, font_size=36, color=highlight_color)
            cf.move_to([0, 0, 0])

            if prev_cf is None:
                self.play(FadeIn(cf), run_time=1.0)
            else:
                self.play(FadeOut(prev_cf), run_time=0.3)
                self.play(FadeIn(cf), run_time=0.8)
            self.wait(wait_per)
            prev_cf = cf

        # Show the beautiful closed form alongside the CF
        # Shrink and move CF to the left, add = and result to the right
        cf_small = MathTex(
            r"\cfrac{e^{-2\pi/5}}{1+\cfrac{e^{-2\pi}}{1+\cfrac{e^{-4\pi}}{1+\cdots}}}",
            font_size=30,
            color=highlight_color,
        )
        equals = MathTex(r"=", font_size=36, color=TEXT_WHITE)
        result = MathTex(
            r"\sqrt{\frac{5+\sqrt{5}}{2}} - \frac{\sqrt{5}+1}{2}",
            font_size=30,
            color=ACCENT_CYAN,
        )
        equation_row = VGroup(cf_small, equals, result)
        equation_row.arrange(RIGHT, buff=0.4)
        equation_row.move_to([0, 0.3, 0])

        self.play(FadeOut(prev_cf), run_time=0.3)
        self.play(FadeIn(equation_row), run_time=1.0)
        self.wait(wait_per * 1.5)

        # Hardy's quote reference
        quote_note = Text(
            "Hardy: 'I had never seen anything in the least like them before'",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        quote_note.next_to(equation_row, DOWN, buff=0.8)
        self.play(FadeIn(quote_note), run_time=0.6)
        self.wait(wait_per)


class ContinuedFractionCollapse(Scene):
    """Show continued fraction = closed form side-by-side on one screen."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 20)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        title = Text("Ramanujan's Continued Fractions", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.6)

        wait_unit = max(0.5, (duration - 5) / 4)

        # --- Horizontal layout: CF = closed form ---
        # 2-level nesting keeps height manageable
        cf_part = MathTex(
            r"\cfrac{e^{-2\pi/5}}{1+\cfrac{e^{-2\pi}}{1+\cfrac{e^{-4\pi}}{1+\cdots}}}",
            font_size=30,
            color=highlight_color,
        )
        equals = MathTex(r"=", font_size=36, color=TEXT_WHITE)
        result = MathTex(
            r"\sqrt{\frac{5+\sqrt{5}}{2}} - \frac{\sqrt{5}+1}{2}",
            font_size=30,
            color=ACCENT_CYAN,
        )

        # Arrange left-to-right
        equation_row = VGroup(cf_part, equals, result)
        equation_row.arrange(RIGHT, buff=0.4)
        equation_row.move_to([0, 0.3, 0])

        # Animate: CF first, then = and result
        self.play(FadeIn(cf_part), run_time=1.0)
        self.wait(wait_unit)

        self.play(FadeIn(equals), FadeIn(result), run_time=1.0)
        self.wait(wait_unit)

        # Highlight box around the whole equation
        box = SurroundingRectangle(equation_row, color=ACCENT_PINK, buff=0.2)
        letter_note = Text(
            "1913 Hardy's letter",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        letter_note.next_to(box, DOWN, buff=0.3)

        self.play(FadeIn(box), FadeIn(letter_note), run_time=0.8)
        self.wait(wait_unit * 2)


# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "expand": {"people": [["Ramanujan", "ラマヌジャン"]], "years": []},
    "collapse": {
        "people": [
            ["Ramanujan", "ラマヌジャン"],
            ["Hardy", "ハーディ"],
        ],
        "years": ["1913"],
    },
}


SCENES = {
    "expand": ContinuedFractionExpand,
    "collapse": ContinuedFractionCollapse,
}
