"""
binary_arithmetic.py - Leibniz's binary arithmetic for 数学史記

Visualizes Leibniz's 1679-1703 work on binary arithmetic and its
parallel with the Chinese I Ching hexagrams brought to him by
Joachim Bouvet in 1701:

    - binary_table: Decimal 0-15 with binary representation
      (columns: 10進 | 2進 | 各桁の重み).
    - counting_up: Counting 0 → 7 in binary, animating carry
      propagation across three bit positions.
    - stepped_reckoner: Abstracted gear diagram of Leibniz's
      Staffelwalze (1670-1694) showing four geared columns and
      a carry arrow between adjacent columns.
    - leibniz_to_iching: Side-by-side correspondence between
      3-bit binary patterns (000-111) and the eight trigrams
      (八卦) of Fu Xi, with 陽 as solid line and 陰 as broken
      line.

Fixed parameters (verified by hand):
    Decimal range:    0-15 (binary 0000-1111)
    Trigram pairs:    000=坤, 001=震, 010=坎, 011=兌,
                      100=艮, 101=離, 110=巽, 111=乾
    Reckoner columns: 4 (units, tens, hundreds, thousands)

Duration-aware: reads target duration from _manim_params.json.
Y range: -1.6 to +3.0, content centered with subtitle clearance preserved.

Used by: Episode 023 (Leibniz), math pillar 2 — binary & universal computation.
"""

import math

from manim import (
    RIGHT,
    Arrow,
    Circle,
    Dot,
    FadeIn,
    FadeOut,
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


def _to_binary(n, width=4):
    return format(n, f"0{width}b")


def _yang_line(center, width=0.9, stroke_width=6, color=ACCENT_GOLD):
    """Solid line representing 陽 (1)."""
    return Line(
        [center[0] - width / 2, center[1], 0],
        [center[0] + width / 2, center[1], 0],
        color=color,
        stroke_width=stroke_width,
    )


def _yin_line(center, width=0.9, stroke_width=6, color=ACCENT_CYAN):
    """Broken line (two short segments) representing 陰 (0)."""
    half = width * 0.4
    gap = width * 0.1
    left = Line(
        [center[0] - half - gap, center[1], 0],
        [center[0] - gap, center[1], 0],
        color=color,
        stroke_width=stroke_width,
    )
    right = Line(
        [center[0] + gap, center[1], 0],
        [center[0] + half + gap, center[1], 0],
        color=color,
        stroke_width=stroke_width,
    )
    return VGroup(left, right)


class BinaryArithmetic(Scene):
    """Leibniz's binary arithmetic — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "binary_table")
        self._duration = params.get("duration", 35)

        if mode == "counting_up":
            self._build_counting_up()
        elif mode == "stepped_reckoner":
            self._build_stepped_reckoner()
        elif mode == "leibniz_to_iching":
            self._build_leibniz_to_iching()
        else:
            self._build_binary_table()

    # ------------------------------------------------------------------
    def _build_binary_table(self):
        duration = self._duration

        title = Text(
            "十進と二進 ── 0と1だけで数を表す",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Header
        header_y = 2.2
        header_dec = Text("十進", font=FONT, font_size=22, color=TEXT_DIM)
        header_bin = Text("二進", font=FONT, font_size=22, color=TEXT_DIM)
        header_dec.move_to([-2.2, header_y, 0])
        header_bin.move_to([1.2, header_y, 0])
        self.play(FadeIn(header_dec), FadeIn(header_bin), run_time=0.5)

        # Show 0..15 in two columns (8 rows each)
        rows_y_start = 1.7
        row_step = 0.42
        col_x_left = [-3.4, -1.0]   # decimal, binary
        col_x_right = [1.4, 3.4]    # decimal, binary

        anim_budget = (duration - 1.5 - 0.5) / 16
        per_pair = max(0.18, anim_budget * 2)

        for k in range(8):
            n_left = k
            n_right = k + 8
            y = rows_y_start - k * row_step

            d_left = MathTex(str(n_left), font_size=26, color=TEXT_WHITE)
            b_left = MathTex(
                _to_binary(n_left), font_size=26, color=ACCENT_CYAN
            )
            d_right = MathTex(str(n_right), font_size=26, color=TEXT_WHITE)
            b_right = MathTex(
                _to_binary(n_right), font_size=26, color=ACCENT_CYAN
            )

            d_left.move_to([col_x_left[0], y, 0])
            b_left.move_to([col_x_left[1], y, 0])
            d_right.move_to([col_x_right[0], y, 0])
            b_right.move_to([col_x_right[1], y, 0])

            self.play(
                FadeIn(d_left),
                FadeIn(b_left),
                FadeIn(d_right),
                FadeIn(b_right),
                run_time=min(0.45, per_pair),
            )

        # Bit weight note at bottom (Japanese label as Text, formula as MathTex)
        weight_label = Text(
            "各桁の重み:",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        weight_label.move_to([-2.5, -1.8, 0])
        weight_formula = MathTex(
            r"2^3 = 8,\; 2^2 = 4,\; 2^1 = 2,\; 2^0 = 1",
            font_size=24,
            color=ACCENT_PINK,
        )
        weight_formula.next_to(weight_label, RIGHT, buff=0.3)
        self.play(FadeIn(weight_label), FadeIn(weight_formula), run_time=0.7)

        anim_total = 0.6 + 0.5 + per_pair * 8 + 0.7
        self.wait(max(1.0, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_counting_up(self):
        duration = self._duration

        title = Text(
            "二進で数え上げる ── 桁上がり",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Show counter 0 .. 7 (3-bit)
        # Layout: decimal on left, binary digits as 3 boxes on right
        budget = (duration - 1.5) / 8
        per_step = max(0.7, budget)

        prev_dec = None
        prev_bits = None

        for n in range(8):
            bin_str = _to_binary(n, width=3)
            dec_label = MathTex(f"{n}", font_size=60, color=ACCENT_GOLD)
            dec_label.move_to([-3.5, 0.7, 0])

            arrow = MathTex(r"\;\to\;", font_size=40, color=TEXT_DIM)
            arrow.move_to([-1.7, 0.7, 0])

            bits = VGroup()
            for i, ch in enumerate(bin_str):
                bit_color = ACCENT_PINK if ch == "1" else TEXT_DIM
                bit = MathTex(ch, font_size=60, color=bit_color)
                bit.move_to([-0.4 + i * 1.1, 0.7, 0])
                bits.add(bit)

            if prev_dec is not None:
                self.play(
                    FadeOut(prev_dec),
                    FadeOut(prev_bits),
                    run_time=0.2,
                )

            self.play(
                FadeIn(dec_label),
                FadeIn(arrow),
                FadeIn(bits),
                run_time=min(0.5, per_step * 0.45),
            )
            self.wait(max(0.2, per_step - 0.55))

            # Keep arrow visible across steps by re-adding
            prev_dec = VGroup(dec_label, arrow)
            prev_bits = bits

        # Footnote
        note = Text(
            "1 が一番上の桁まで上がると桁が増える",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.4, 0])
        self.play(FadeIn(note), run_time=0.7)
        self.wait(1.5)

    # ------------------------------------------------------------------
    def _build_stepped_reckoner(self):
        duration = self._duration

        title = Text(
            "ステップ・レコナー ── 桁ごとに歯車を回す",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        subtitle = Text(
            "Staffelwalze (1670-1694)",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        subtitle.move_to([0, 2.45, 0])
        self.play(FadeIn(subtitle), run_time=0.4)

        # Four gear columns
        col_x = [-3.6, -1.2, 1.2, 3.6]
        col_labels_text = ["1の位", "10の位", "100の位", "1000の位"]
        col_digits = ["3", "7", "0", "0"]

        gears = []
        labels = []
        digit_labels = []
        for x, label, digit in zip(
            col_x, col_labels_text, col_digits, strict=True
        ):
            # Gear: large circle with small dot teeth
            big = Circle(radius=0.7, color=ACCENT_CYAN, stroke_width=3)
            big.move_to([x, 0.6, 0])
            teeth = VGroup()
            for t in range(8):
                ang = 2 * math.pi * t / 8
                dot = Dot(
                    [x + 0.78 * math.cos(ang), 0.6 + 0.78 * math.sin(ang), 0],
                    radius=0.05,
                    color=ACCENT_CYAN,
                )
                teeth.add(dot)
            digit_label = MathTex(digit, font_size=38, color=ACCENT_GOLD)
            digit_label.move_to([x, 0.6, 0])

            col_label = Text(label, font=FONT, font_size=20, color=TEXT_DIM)
            col_label.move_to([x, -0.55, 0])

            gears.append(VGroup(big, teeth))
            labels.append(col_label)
            digit_labels.append(digit_label)

        # Animate column by column
        per_col = max(0.5, (duration - 1.5 - 1.5) / 4)
        for gear, label, digit in zip(gears, labels, digit_labels, strict=True):
            self.play(
                FadeIn(gear),
                FadeIn(label),
                FadeIn(digit),
                run_time=min(0.6, per_col * 0.6),
            )
            self.wait(max(0.15, per_col - 0.6))

        # Carry arrows between columns
        carry_arrows = VGroup()
        for i in range(3):
            x1 = col_x[i] + 0.78
            x2 = col_x[i + 1] - 0.78
            ar = Arrow(
                [x1, 0.6, 0], [x2, 0.6, 0],
                color=ACCENT_PINK, stroke_width=3, buff=0.05,
            )
            carry_arrows.add(ar)
        carry_label = Text(
            "桁上がり",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        carry_label.move_to([0, 1.7, 0])
        self.play(FadeIn(carry_arrows), FadeIn(carry_label), run_time=0.7)

        # Bottom note
        note = Text(
            "0と1だけで動く加減乗除の機械、未完のまま終わる",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.4, 0])
        self.play(FadeIn(note), run_time=0.7)
        self.wait(1.0)

    # ------------------------------------------------------------------
    def _build_leibniz_to_iching(self):
        duration = self._duration

        title = Text(
            "二進と易経 ── 0/1 と 陰/陽 の対応",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Eight trigrams: each is 3 bits, top bit at top
        # Layout: 2 rows × 4 columns
        positions_row1 = [-4.5, -1.5, 1.5, 4.5]   # 0..3
        positions_row2 = [-4.5, -1.5, 1.5, 4.5]   # 4..7
        row1_y = 1.4
        row2_y = -0.6

        # Trigram names (one Han character each)
        names = ["坤", "震", "坎", "兌", "艮", "離", "巽", "乾"]

        budget = (duration - 1.5) / 8
        per_trigram = max(0.4, budget)

        all_groups = []
        for n in range(8):
            bin_str = _to_binary(n, width=3)
            if n < 4:
                x = positions_row1[n]
                y_center = row1_y
            else:
                x = positions_row2[n - 4]
                y_center = row2_y

            # Three lines stacked vertically (top bit at top)
            line_group = VGroup()
            line_spacing = 0.28
            for i, ch in enumerate(bin_str):
                ly = y_center + line_spacing - i * line_spacing
                if ch == "1":
                    seg = _yang_line([x, ly, 0])
                else:
                    seg = _yin_line([x, ly, 0])
                line_group.add(seg)

            # Binary label below
            bin_label = MathTex(bin_str, font_size=22, color=ACCENT_CYAN)
            bin_label.move_to([x, y_center - 0.7, 0])

            # Name below binary
            name_label = Text(names[n], font=FONT, font_size=22, color=ACCENT_PINK)
            name_label.move_to([x, y_center - 1.05, 0])

            all_groups.append(VGroup(line_group, bin_label, name_label))

        # Animate in
        for group in all_groups:
            self.play(FadeIn(group), run_time=min(0.5, per_trigram * 0.7))

        # Bottom note
        note = Text(
            "陽 = 1、陰 = 0 ── 1701年、北京から届いた図",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.95, 0])
        self.play(FadeIn(note), run_time=0.7)
        self.wait(1.5)


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "binary_table": {"people": [], "years": []},
    "counting_up": {"people": [], "years": []},
    "stepped_reckoner": {"people": [], "years": ["1670", "1694"]},
    "leibniz_to_iching": {"people": [], "years": ["1701"]},
}

SCENES = {
    "binary_table": BinaryArithmetic,
    "counting_up": BinaryArithmetic,
    "stepped_reckoner": BinaryArithmetic,
    "leibniz_to_iching": BinaryArithmetic,
}
