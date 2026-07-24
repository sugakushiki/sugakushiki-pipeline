"""
zero_arithmetic_rules.py - Brahmagupta's arithmetic rules for zero and negatives

Visualizes the arithmetic of zero and negative numbers as first codified by
Brahmagupta in the Brāhmasphuṭasiddhānta (628 CE), chapter 18 (Kuṭṭakādhyāya).

Modes:
    zero_rules
        Show the four core rules for zero: a + 0 = a, a - 0 = a, a * 0 = 0,
        and 0 - a = -a. Fixed example: a = 5.
        Each rule appears as a row centered at successive y values.
    negative_arithmetic
        Number-line view of the "fortunes (財産) and debts (借金)" analogy.
        Fixed examples on a number line from -5 to +5:
            5 + (-3) = 2   (財産5から借金3で残り2)
            (-2) * (-3) = 6   (借金の借金は財産)
        Sign-rule grid shown on the right:
            (+)*(+) = +, (+)*(-) = -, (-)*(+) = -, (-)*(-) = +
    division_by_zero
        Brahmagupta's treatment of a / 0. He wrote 0/0 = 0 (incorrect by
        modern standards) but left a/0 (a != 0) without committing.
        Three rows: 0/0 = 0 (誤), 5/0 = ? (Brahmagupta は答えを避けた),
        現代 = 未定義. Includes year 628 as a single label.

Fixed parameters (verified by hand):
    Number line: x in [-5, 5], unit = 1.0
    Sign-rule grid: 2x2 cells, cell size 1.0 x 0.6
    All Text uses FONT (BIZ UDMincho). MathTex contains ASCII only.
    Y range: -2.0 to +3.0, subtitle clearance preserved.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 025 (Brahmagupta), math pillar — zero and negative numbers.
"""

from manim import (
    FadeIn,
    Line,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class ZeroArithmeticRules(Scene):
    """Brahmagupta's zero and negative-number arithmetic — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "zero_rules")
        self._duration = params.get("duration", 35)

        if mode == "negative_arithmetic":
            self._build_negative_arithmetic()
        elif mode == "division_by_zero":
            self._build_division_by_zero()
        else:
            self._build_zero_rules()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_zero_rules(self):
        """Four core rules for zero arithmetic, codified in BSS 628 CE."""
        duration = self._duration

        title = self._title("ゼロを数として扱う ── 加減乗の規則")
        self.play(FadeIn(title), run_time=0.5)

        rules = [
            (r"a + 0 = a", 1.7),
            (r"a - 0 = a", 0.7),
            (r"a \times 0 = 0", -0.3),
            (r"0 - a = -a", -1.3),
        ]
        for tex_str, y in rules:
            formula = MathTex(tex_str, font_size=42, color=ACCENT_CYAN)
            formula.move_to([-2.5, y, 0])
            self.play(FadeIn(formula), run_time=0.4)

        # Right side: concrete example with a = 5
        a_label = Text("例: a = 5", font=FONT, font_size=24, color=TEXT_DIM)
        a_label.move_to([3.2, 1.7, 0])
        self.play(FadeIn(a_label), run_time=0.3)

        examples = [
            (r"5 + 0 = 5", 0.7),
            (r"5 \times 0 = 0", -0.3),
            (r"0 - 5 = -5", -1.3),
        ]
        for tex_str, y in examples:
            ex = MathTex(tex_str, font_size=32, color=TEXT_WHITE)
            ex.move_to([3.2, y, 0])
            self.play(FadeIn(ex), run_time=0.35)

        note = Text(
            "ゼロを数として加減乗の対象に据えた",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -2.0, 0])
        self.play(FadeIn(note), run_time=0.5)

        anim_total = 0.5 + 0.4 * 4 + 0.3 + 0.35 * 3 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_negative_arithmetic(self):
        """Number-line view of negative numbers via fortunes/debts analogy."""
        duration = self._duration

        title = self._title("負の数 ── 財産と借金で数を拡張する")
        self.play(FadeIn(title), run_time=0.5)

        # Number line from -5 to +5
        line_y = 0.6
        x_left = -4.5
        x_right = 4.5
        axis = Line([x_left, line_y, 0], [x_right, line_y, 0], color=TEXT_WHITE, stroke_width=2)
        self.play(FadeIn(axis), run_time=0.5)

        # Ticks and labels
        for n in range(-5, 6):
            x = x_left + (n + 5) * (x_right - x_left) / 10.0
            tick = Line(
                [x, line_y - 0.1, 0], [x, line_y + 0.1, 0], color=TEXT_WHITE, stroke_width=1.5
            )
            self.play(FadeIn(tick), run_time=0.05)
            lbl_color = ACCENT_GOLD if n == 0 else (ACCENT_PINK if n < 0 else ACCENT_CYAN)
            lbl = MathTex(str(n), font_size=24, color=lbl_color)
            lbl.move_to([x, line_y - 0.35, 0])
            self.play(FadeIn(lbl), run_time=0.05)

        # Labels for two halves
        left_caption = Text("借金 (負)", font=FONT, font_size=20, color=ACCENT_PINK)
        left_caption.move_to([-3.0, line_y + 0.55, 0])
        self.play(FadeIn(left_caption), run_time=0.3)

        right_caption = Text("財産 (正)", font=FONT, font_size=20, color=ACCENT_CYAN)
        right_caption.move_to([3.0, line_y + 0.55, 0])
        self.play(FadeIn(right_caption), run_time=0.3)

        # Sign-rule grid on the lower portion
        grid_label = Text("符号則", font=FONT, font_size=22, color=ACCENT_GOLD)
        grid_label.move_to([-4.0, -0.6, 0])
        self.play(FadeIn(grid_label), run_time=0.3)

        cells = [
            (r"(+)\times(+) = +", -0.6, -1.4),
            (r"(+)\times(-) = -", -0.6, 1.4),
            (r"(-)\times(+) = -", -1.4, -1.4),
            (r"(-)\times(-) = +", -1.4, 1.4),
        ]
        for tex_str, y, x in cells:
            ex = MathTex(tex_str, font_size=28, color=TEXT_WHITE)
            ex.move_to([x, y, 0])
            self.play(FadeIn(ex), run_time=0.35)

        note = Text(
            "借金の借金は財産になる",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -2.0, 0])
        self.play(FadeIn(note), run_time=0.5)

        anim_total = 0.5 + 0.5 + 0.05 * 22 + 0.3 + 0.3 + 0.3 + 0.35 * 4 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_division_by_zero(self):
        """Brahmagupta's treatment of division by zero — 0/0 = 0 (incorrect)."""
        duration = self._duration

        title = self._title("ゼロで割る ── 達成できなかった一段")
        self.play(FadeIn(title), run_time=0.5)

        # Year stamp on the left
        year_label = Text("西暦628年", font=FONT, font_size=22, color=TEXT_DIM)
        year_label.move_to([-5.2, 2.3, 0])
        self.play(FadeIn(year_label), run_time=0.3)

        # Three rows: 0/0, a/0, modern
        row_y = [1.5, 0.3, -0.9]

        # Row 1: 0/0 = 0 (Brahmagupta, incorrect)
        r1 = MathTex(r"\frac{0}{0} = 0", font_size=44, color=ACCENT_CYAN)
        r1.move_to([-3.0, row_y[0], 0])
        self.play(FadeIn(r1), run_time=0.5)
        r1_note = Text(
            "ブラフマグプタの定義 (現代では誤り)", font=FONT, font_size=20, color=TEXT_DIM
        )
        r1_note.move_to([2.0, row_y[0], 0])
        self.play(FadeIn(r1_note), run_time=0.4)

        # Row 2: a/0 = ?
        r2 = MathTex(r"\frac{a}{0} = \,?", font_size=44, color=ACCENT_PINK)
        r2.move_to([-3.0, row_y[1], 0])
        self.play(FadeIn(r2), run_time=0.5)
        r2_note = Text("ここは答えを書かなかった", font=FONT, font_size=20, color=TEXT_DIM)
        r2_note.move_to([2.0, row_y[1], 0])
        self.play(FadeIn(r2_note), run_time=0.4)

        # Row 3: 現代 = 未定義
        r3 = MathTex(r"\frac{a}{0} : \text{undefined}", font_size=40, color=ACCENT_GOLD)
        r3.move_to([-3.0, row_y[2], 0])
        self.play(FadeIn(r3), run_time=0.5)
        r3_note = Text("現代の数学では 未定義", font=FONT, font_size=20, color=TEXT_DIM)
        r3_note.move_to([2.0, row_y[2], 0])
        self.play(FadeIn(r3_note), run_time=0.4)

        # Bottom caption
        note = Text(
            "ゼロを数とした人が、最後の一段で立ち止まった",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -2.0, 0])
        self.play(FadeIn(note), run_time=0.5)

        anim_total = 0.5 + 0.3 + (0.5 + 0.4) * 3 + 0.5
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "zero_rules": {"people": [], "years": []},
    "negative_arithmetic": {"people": [], "years": []},
    "division_by_zero": {"people": [], "years": ["628"]},
}

SCENES = {
    "zero_rules": ZeroArithmeticRules,
    "negative_arithmetic": ZeroArithmeticRules,
    "division_by_zero": ZeroArithmeticRules,
}
