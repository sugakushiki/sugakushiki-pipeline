"""
numeral_systems.py - Roman vs Hindu-Arabic numeral comparison for 数学史記

Visualizes the contrast between Roman numerals and Hindu-Arabic positional
notation, and explains the role of zero.

Modes:
    comparison  - Side-by-side comparison of Roman vs Hindu-Arabic for
                  several numbers.
                  Fixed params: numbers = [39, 207, 1492, 10000]
    place_value - Animated breakdown of positional notation (e.g. 3906).
                  Fixed params: number = 3906 (thousands, hundreds, tens, ones)
    zero_power  - Illustrate how zero enables compact representation.
                  Fixed params: compare 207 with/without zero placeholder

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 008 (Al-Khwarizmi)
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
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


def _to_roman(n):
    """Convert integer to Roman numeral string."""
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    result = ""
    for value, numeral in vals:
        while n >= value:
            result += numeral
            n -= value
    return result


class NumeralSystems(Scene):
    """Numeral system visualization — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "comparison")
        self._duration = params.get("duration", 25)

        if mode == "place_value":
            self._build_place_value()
        elif mode == "zero_power":
            self._build_zero_power()
        else:
            self._build_comparison()

    # ------------------------------------------------------------------
    # Mode: comparison
    # ------------------------------------------------------------------
    def _build_comparison(self):
        duration = self._duration

        title = Text(
            "ローマ数字 vs Hindu-Arabic数字",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        numbers = [39, 207, 1492, 10000]
        n_rows = len(numbers)
        anim_time = 0.8 + n_rows * 1.2 + 1.0
        default_waits = n_rows * 1.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        header_roman = Text("ローマ数字", font=FONT, font_size=24, color=TEXT_DIM)
        header_roman.move_to(LEFT * 3.0 + UP * 2.5)

        header_arabic = Text("Hindu-Arabic", font=FONT, font_size=24, color=TEXT_DIM)
        header_arabic.move_to(RIGHT * 3.0 + UP * 2.5)

        sep_line = Line(
            UP * 2.3 + LEFT * 0.3,
            DOWN * 1.5 + LEFT * 0.3,
            color=TEXT_DIM,
            stroke_width=1,
            stroke_opacity=0.5,
        )

        self.play(FadeIn(header_roman), FadeIn(header_arabic), FadeIn(sep_line), run_time=0.5)

        row_y_start = 1.7
        row_gap = 0.95

        for i, num in enumerate(numbers):
            y_pos = row_y_start - i * row_gap

            roman_str = _to_roman(num)
            if num == 10000:
                roman_str = "MMMMMMMMMM"

            roman_text = Text(roman_str, font=FONT, font_size=22, color=ACCENT_PINK)
            roman_text.move_to(LEFT * 3.0 + UP * y_pos)
            if roman_text.width > 4.0:
                roman_text.scale(4.0 / roman_text.width)

            arabic_text = Text(str(num), font=FONT, font_size=28, color=ACCENT_CYAN)
            arabic_text.move_to(RIGHT * 3.0 + UP * y_pos)

            roman_len = len(roman_str)
            arabic_len = len(str(num))
            count_text = Text(
                f"{roman_len}字 → {arabic_len}字",
                font=FONT,
                font_size=16,
                color=TEXT_DIM,
            )
            count_text.move_to(RIGHT * 5.5 + UP * y_pos)

            row = VGroup(roman_text, arabic_text, count_text)
            self.play(FadeIn(row), run_time=0.8)
            self.wait(1.0 * ws)

        conclusion = Text(
            "位取り記数法は桁数の増加を抑える",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        conclusion.move_to(DOWN * 1.7)
        self.play(FadeIn(conclusion), run_time=0.6)
        self.wait(max(duration - anim_time - n_rows * 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode: place_value
    # ------------------------------------------------------------------
    def _build_place_value(self):
        duration = self._duration

        title = Text(
            "位取り記数法の仕組み",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 5.0
        default_waits = 8.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        digits = ["3", "9", "0", "6"]
        place_names = ["千の位", "百の位", "十の位", "一の位"]
        place_values = ["3000", "900", "0", "6"]
        place_powers = [r"10^3", r"10^2", r"10^1", r"10^0"]

        full_num = Text("3906", font=FONT, font_size=52, color=ACCENT_CYAN)
        full_num.move_to(UP * 2.2)
        self.play(FadeIn(full_num), run_time=0.8)
        self.wait(0.8 * ws)

        digit_groups = VGroup()
        box_width = 1.6
        start_x = -2.4
        digit_y = 0.8

        for i, (d, pname, pval, ppow) in enumerate(
            zip(digits, place_names, place_values, place_powers, strict=False)
        ):
            x = start_x + i * box_width

            box = Rectangle(
                width=1.3,
                height=1.3,
                color=ACCENT_CYAN if d != "0" else ACCENT_PINK,
                stroke_width=2,
                fill_opacity=0.15,
            )
            box.move_to([x, digit_y, 0])

            digit_text = Text(
                d,
                font=FONT,
                font_size=40,
                color=ACCENT_CYAN if d != "0" else ACCENT_PINK,
            )
            digit_text.move_to(box)

            place_label = Text(pname, font=FONT, font_size=16, color=TEXT_DIM)
            place_label.next_to(box, UP, buff=0.1)

            power_label = MathTex(ppow, font_size=22, color=TEXT_DIM)
            power_label.next_to(box, DOWN, buff=0.15)

            value_label = Text(pval, font=FONT, font_size=22, color=ACCENT_GOLD)
            value_label.next_to(power_label, DOWN, buff=0.15)

            group = VGroup(box, digit_text, place_label, power_label, value_label)
            digit_groups.add(group)

        for g in digit_groups:
            self.play(FadeIn(g), run_time=0.7)
            self.wait(0.6 * ws)

        sum_eq = MathTex(
            r"3 \times 10^3 + 9 \times 10^2 + 0 \times 10^1 + 6 \times 10^0 = 3906",
            font_size=26,
            color=TEXT_WHITE,
        )
        sum_eq.move_to(DOWN * 1.5)
        self.play(FadeIn(sum_eq), run_time=0.8)
        self.wait(max(duration - 7.0, 1.0))

    # ------------------------------------------------------------------
    # Mode: zero_power
    # ------------------------------------------------------------------
    def _build_zero_power(self):
        duration = self._duration

        title = Text(
            "ゼロの力 ── 位の空白を埋める",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 4.0
        default_waits = 6.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        problem_label = Text(
            "ゼロがなかったら？",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        problem_label.move_to(UP * 2.3)
        self.play(FadeIn(problem_label), run_time=0.5)

        ambig = Text("2  7", font=FONT, font_size=48, color=ACCENT_PINK)
        ambig.move_to(UP * 1.3)

        question = Text("27？ 207？ 2007？", font=FONT, font_size=28, color=TEXT_DIM)
        question.move_to(UP * 0.5)

        self.play(FadeIn(ambig), run_time=0.6)
        self.wait(0.8 * ws)
        self.play(FadeIn(question), run_time=0.5)
        self.wait(1.0 * ws)

        solution_label = Text(
            "ゼロがあれば明確になる",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        solution_label.move_to(DOWN * 0.3)

        nums = VGroup()
        examples = [("27", "二十七"), ("207", "二百七"), ("2007", "二千七")]
        for i, (n, desc) in enumerate(examples):
            x = -3.0 + i * 3.0
            num_text = Text(n, font=FONT, font_size=36, color=ACCENT_CYAN)
            num_text.move_to([x, -1.0, 0])
            desc_text = Text(desc, font=FONT, font_size=18, color=TEXT_DIM)
            desc_text.next_to(num_text, DOWN, buff=0.15)
            nums.add(VGroup(num_text, desc_text))

        self.play(FadeIn(solution_label), run_time=0.5)
        self.wait(0.5 * ws)

        for g in nums:
            self.play(FadeIn(g), run_time=0.5)

        self.wait(0.8 * ws)

        zero_note = Text(
            "0 は「この桁には何もない」という情報を伝える",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        zero_note.move_to(DOWN * 1.8)
        self.play(FadeIn(zero_note), run_time=0.6)
        self.wait(max(duration - 6.0, 1.0))
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "comparison": {"people": [], "years": []},
    "place_value": {"people": [], "years": []},
    "zero_power": {"people": [], "years": []},
}



# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
SCENES = {
    "comparison": NumeralSystems,
    "place_value": NumeralSystems,
    "zero_power": NumeralSystems,
}
