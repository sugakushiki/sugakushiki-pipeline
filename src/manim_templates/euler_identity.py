"""
euler_identity.py - Euler's formula and identity for 数学史記

Visualizes Euler's 1748 Introductio derivation:
    e^{ix} = cos x + i sin x,
with the special case x = π giving Euler's celebrated identity
    e^{iπ} + 1 = 0
── the climax of Episode 018.

Modes:
    series      - Three Taylor expansions stacked:
                    e^x   = 1 + x + x²/2! + x³/3! + ...
                    cos x = 1 − x²/2! + x⁴/4! − ...
                    sin x = x − x³/3! + x⁵/5! − ...
                  Fixed params: each shown to at least the 4th/5th term.
    substitute  - Substitute x → ix into e^x, separate real and
                  imaginary parts using i² = −1, and derive
                    e^{ix} = cos x + i sin x.
                  Fixed params: expand to (ix)⁴ / x^4 order.
    unit_circle - Complex plane with unit circle. e^{ix} is a
                  rotating point at angle x; animate x from 0 → π
                  so the point travels from (1,0) to (−1,0).
                  Fixed params: circle radius 1.3, angle 0 → π.
                  Climax: display e^{iπ}+1=0 with five colour-coded
                  fundamental constants.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 018 (Euler analysis), math pillar 3 (climax).
"""

import math

from manim import (
    RIGHT,
    Circle,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Scene,
    SurroundingRectangle,
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


class EulerIdentity(Scene):
    """Euler's formula/identity e^{iπ}+1=0. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "series")

        if mode == "substitute":
            self.build_substitute()
        elif mode == "unit_circle":
            self.build_unit_circle()
        else:
            self.build_series()

    # -------------------------------------------------------------------
    # Mode: series
    # -------------------------------------------------------------------
    def build_series(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:     y = +3.15
        # e^x:       y = +2.15
        # cos x:     y = +0.95
        # sin x:     y = -0.25
        # note:      y = -1.30
        # conclusion:y = -1.80

        title = Text("3つの基本関数のテイラー展開", font=FONT, font_size=26, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        exp_series = MathTex(
            r"e^{x}",
            r"=",
            r"1 + x + \frac{x^2}{2!} + \frac{x^3}{3!} + \frac{x^4}{4!} + \cdots",
            font_size=30,
        )
        exp_series[0].set_color(ACCENT_GOLD)
        exp_series.move_to([0, 2.15, 0])

        cos_series = MathTex(
            r"\cos x",
            r"=",
            r"1 - \frac{x^2}{2!} + \frac{x^4}{4!} - \frac{x^6}{6!} + \cdots",
            font_size=30,
        )
        cos_series[0].set_color(ACCENT_CYAN)
        cos_series.move_to([0, 0.95, 0])

        sin_series = MathTex(
            r"\sin x",
            r"=",
            r"x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!} + \cdots",
            font_size=30,
        )
        sin_series[0].set_color(ACCENT_PINK)
        sin_series.move_to([0, -0.25, 0])

        note = Text("── 偶数項と奇数項のリズムに注目", font=FONT, font_size=22, color=TEXT_DIM)
        note.move_to([0, -1.20, 0])

        # Conclusion (safe zone: bottom >= -2.0)
        conclusion = Text(
            "この3つは、虚数単位 i でつながっている", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        conclusion.move_to([0, -1.75, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(exp_series), run_time=0.9)
        self.wait(0.5)
        self.play(FadeIn(cos_series), run_time=0.9)
        self.wait(0.5)
        self.play(FadeIn(sin_series), run_time=0.9)
        self.wait(0.6)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(0.4)
        self.play(FadeIn(conclusion), run_time=0.7)

        anim_overhead = 0.5 + 0.9 + 0.5 + 0.9 + 0.5 + 0.9 + 0.6 + 0.5 + 0.4 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: substitute
    # -------------------------------------------------------------------
    def build_substitute(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:       y = +3.15
        # line1:       y = +2.15  e^{ix} = 1 + ix + (ix)²/2! + ...
        # line2:       y = +1.00  simplify using i² = -1
        # line3:       y = -0.20  group real and imaginary
        # line4:       y = -1.10  e^{ix} = cos x + i sin x
        # conclusion:  y = -1.85

        title = Text("x に ix を代入すると…", font=FONT, font_size=26, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        line1 = MathTex(
            r"e^{ix}",
            r"=",
            r"1 + ix + \frac{(ix)^2}{2!} + \frac{(ix)^3}{3!} + \frac{(ix)^4}{4!} + \cdots",
            font_size=26,
        )
        line1[0].set_color(ACCENT_GOLD)
        line1.move_to([0, 2.20, 0])

        line2 = MathTex(
            r"=",
            r"1 + ix - \frac{x^2}{2!} - i\,\frac{x^3}{3!} + \frac{x^4}{4!} + \cdots",
            font_size=26,
        )
        line2.move_to([0, 1.05, 0])

        line3_left_label = Text("実部：", font=FONT, font_size=22, color=ACCENT_CYAN)
        line3_left_expr = MathTex(
            r"1 - \frac{x^2}{2!} + \frac{x^4}{4!} - \cdots",
            r"=",
            r"\cos x",
            font_size=26,
        )
        line3_left_expr[2].set_color(ACCENT_CYAN)
        line3_left = VGroup(line3_left_label, line3_left_expr).arrange(RIGHT, buff=0.25)
        line3_left.move_to([0, -0.15, 0])

        line3_right_label = Text("虚部：", font=FONT, font_size=22, color=ACCENT_PINK)
        line3_right_expr = MathTex(
            r"x - \frac{x^3}{3!} + \frac{x^5}{5!} - \cdots",
            r"=",
            r"\sin x",
            font_size=26,
        )
        line3_right_expr[2].set_color(ACCENT_PINK)
        line3_right = VGroup(line3_right_label, line3_right_expr).arrange(RIGHT, buff=0.25)
        line3_right.move_to([0, -0.95, 0])

        # Conclusion (safe zone: bottom >= -2.0)
        conclusion = MathTex(
            r"e^{ix}",
            r"=",
            r"\cos x",
            r"+",
            r"i \sin x",
            font_size=32,
        )
        conclusion[0].set_color(ACCENT_GOLD)
        conclusion[2].set_color(ACCENT_CYAN)
        conclusion[4].set_color(ACCENT_PINK)
        conclusion.move_to([0, -1.65, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(line1), run_time=0.9)
        self.wait(0.5)
        self.play(FadeIn(line2), run_time=0.9)
        self.wait(0.5)
        self.play(FadeIn(line3_left), run_time=0.8)
        self.wait(0.4)
        self.play(FadeIn(line3_right), run_time=0.8)
        self.wait(0.5)
        self.play(FadeIn(conclusion), run_time=0.9)
        box = SurroundingRectangle(conclusion, color=highlight, buff=0.10)
        self.play(FadeIn(box), run_time=0.4)

        anim_overhead = 0.5 + 0.9 + 0.5 + 0.9 + 0.5 + 0.8 + 0.4 + 0.8 + 0.5 + 0.9 + 0.4
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: unit_circle
    # -------------------------------------------------------------------
    def build_unit_circle(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:         y = +3.15
        # plane center:  (cx=-2.5, cy=0.55), radius = 1.3
        # right side:    formula labels at x≈+2.5
        # conclusion:    y = -1.55 (climax)
        #
        # Note: uses only geometric primitives (Line, Dot, Circle) as
        # always_redraw targets. MathTex in always_redraw is prohibitively
        # slow (each frame re-runs LaTeX), so no live value readouts.

        title_text = Text("複素平面の単位円と", font=FONT, font_size=26, color=TEXT_DIM)
        title_math = MathTex(r"e^{ix}", font_size=32, color=ACCENT_GOLD)
        title = VGroup(title_text, title_math).arrange(RIGHT, buff=0.3)
        title.move_to([0, 3.15, 0])
        self.play(FadeIn(title), run_time=0.5)

        # Complex plane centered at (-2.5, 1.05). Positioned to leave room
        # for the climax formula below (measured box bottom safely above -2.0).
        cx, cy = -2.5, 1.05
        radius = 1.3

        # Axes
        axis_len = 1.9
        re_axis = Line(
            start=[cx - axis_len, cy, 0],
            end=[cx + axis_len, cy, 0],
            color=EDGE_COLOR,
            stroke_width=2,
        )
        im_axis = Line(
            start=[cx, cy - axis_len, 0],
            end=[cx, cy + axis_len, 0],
            color=EDGE_COLOR,
            stroke_width=2,
        )
        re_label = MathTex(r"\text{Re}", font_size=22, color=TEXT_DIM)
        re_label.move_to([cx + axis_len + 0.25, cy, 0])
        im_label = MathTex(r"\text{Im}", font_size=22, color=TEXT_DIM)
        im_label.move_to([cx, cy + axis_len + 0.25, 0])

        unit_circle = Circle(
            radius=radius,
            color=ACCENT_CYAN,
            stroke_width=3,
        )
        unit_circle.move_to([cx, cy, 0])

        # Markers for 1 and -1
        one_dot = Dot([cx + radius, cy, 0], color=TEXT_DIM, radius=0.05)
        neg_one_dot = Dot([cx - radius, cy, 0], color=ACCENT_GOLD, radius=0.07)
        one_label = MathTex(r"1", font_size=22, color=TEXT_DIM)
        one_label.move_to([cx + radius + 0.20, cy - 0.22, 0])
        neg_one_label = MathTex(r"-1", font_size=24, color=ACCENT_GOLD)
        neg_one_label.move_to([cx - radius - 0.30, cy - 0.22, 0])

        self.play(
            FadeIn(re_axis),
            FadeIn(im_axis),
            FadeIn(re_label),
            FadeIn(im_label),
            run_time=0.6,
        )
        self.play(FadeIn(unit_circle), run_time=0.7)
        self.play(
            FadeIn(one_dot),
            FadeIn(one_label),
            FadeIn(neg_one_dot),
            FadeIn(neg_one_label),
            run_time=0.5,
        )

        # Right-side static formula panel
        formula_eix = MathTex(
            r"e^{ix}",
            r"=",
            r"\cos x",
            r"+",
            r"i \sin x",
            font_size=30,
        )
        formula_eix[0].set_color(ACCENT_GOLD)
        formula_eix[2].set_color(ACCENT_CYAN)
        formula_eix[4].set_color(ACCENT_PINK)
        formula_eix.move_to([2.5, 2.10, 0])

        angle_note = MathTex(
            r"x:",
            r"0",
            r"\to",
            r"\pi",
            font_size=28,
        )
        angle_note[1].set_color(TEXT_DIM)
        angle_note[3].set_color(ACCENT_CYAN)
        angle_note.move_to([2.5, 1.20, 0])

        self.play(FadeIn(formula_eix), run_time=0.7)
        self.play(FadeIn(angle_note), run_time=0.5)

        # ValueTracker for angle x (0 to pi) -- only for geometric primitives
        angle_tracker = ValueTracker(0.0)

        # Rotating dot e^{ix} (geometric primitives only; no MathTex)
        moving_dot = always_redraw(
            lambda: Dot(
                [
                    cx + radius * math.cos(angle_tracker.get_value()),
                    cy + radius * math.sin(angle_tracker.get_value()),
                    0,
                ],
                color=ACCENT_PINK,
                radius=0.09,
            )
        )
        radius_line = always_redraw(
            lambda: Line(
                start=[cx, cy, 0],
                end=[
                    cx + radius * math.cos(angle_tracker.get_value()),
                    cy + radius * math.sin(angle_tracker.get_value()),
                    0,
                ],
                color=ACCENT_PINK,
                stroke_width=2,
            )
        )

        self.play(
            FadeIn(moving_dot),
            FadeIn(radius_line),
            run_time=0.5,
        )
        self.wait(0.3)

        # Animate angle 0 -> pi
        rotation_time = 3.5
        self.play(angle_tracker.animate.set_value(math.pi), run_time=rotation_time)
        self.wait(0.5)

        # Highlight: moving_dot is now at (-1, 0)
        self.play(Indicate(neg_one_dot, color=ACCENT_GOLD, scale_factor=1.7), run_time=0.8)
        self.wait(0.3)

        # Climax: display Euler's identity (large, centered below)
        # Split to color-code the five fundamental constants
        identity = MathTex(
            r"e",  # 0 - e (natural log base)
            r"^{",  # 1 - superscript delimiter
            r"i",  # 2 - i (imaginary unit)
            r"\pi",  # 3 - π (circle constant)
            r"}",  # 4 - superscript delimiter
            r"+",  # 5
            r"1",  # 6 - multiplicative identity
            r"=",  # 7
            r"0",  # 8 - additive identity
            font_size=32,
        )
        identity[0].set_color(ACCENT_GOLD)  # e
        identity[2].set_color(ACCENT_PINK)  # i
        identity[3].set_color(ACCENT_CYAN)  # π
        identity[6].set_color(TEXT_WHITE)  # 1
        identity[8].set_color(highlight)  # 0 (gold)
        identity.move_to([0, -1.10, 0])

        self.play(FadeIn(identity), run_time=1.0)
        box = SurroundingRectangle(identity, color=highlight, buff=0.10)
        self.play(FadeIn(box), run_time=0.5)

        anim_overhead_guess = (
            0.5
            + 0.6
            + 0.7
            + 0.5
            + 0.7
            + 0.5
            + 0.5
            + 0.3
            + rotation_time
            + 0.5
            + 0.8
            + 0.3
            + 1.0
            + 0.5
        )
        self.wait(max(1.0, duration - anim_overhead_guess))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "series": {"people": [], "years": []},
    "substitute": {"people": [], "years": []},
    "unit_circle": {"people": [], "years": []},
}


SCENES = {
    "series": {
        "class": "EulerIdentity",
        "params": {"mode": "series"},
        "description": "Taylor series of e^x, cos x, sin x stacked",
    },
    "substitute": {
        "class": "EulerIdentity",
        "params": {"mode": "substitute"},
        "description": "x → ix substitution derives e^{ix} = cos x + i sin x",
    },
    "unit_circle": {
        "class": "EulerIdentity",
        "params": {"mode": "unit_circle"},
        "description": "Unit circle animation: e^{ix} rotates 0 → π, reveals e^{iπ}+1=0",
    },
}
