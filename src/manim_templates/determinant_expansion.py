"""
determinant_expansion.py — 行列式の段階的展開 for 数学史記

関孝和『解伏題之法』(1683) の行列式を、2×2基礎、3×3交式斜乗
（サラス則相当）、ライプニッツ(1693)との時系列比較で視覚化。
1ファイル1クラス + mode分岐。

Modes:
    two_by_two       - 2×2 determinant ad-bc.
                       Fixed params: matrix [[2,1],[1,3]], det = 2·3-1·1 = 5.
                       Main diagonal = ACCENT_GOLD, anti-diagonal = ACCENT_PINK.
    seki_method      - Seki's 交式斜乗 for 3×3 (Sarrus rule).
                       Fixed params: matrix [[1,2,3],[4,5,6],[7,8,10]], det = -3.
                       Positive terms (ACCENT_CYAN): aei+bfg+cdh = 50+84+96 = 230.
                       Negative terms (ACCENT_PINK): ceg+afh+bdi = 105+48+80 = 233.
                       Final: 230 - 233 = -3.
    history_parallel - Timeline 1680-1695 comparing 関『解伏題之法』(1683, Edo)
                       vs Leibniz letter to l'Hôpital (1693, Hanover).
                       Fixed params: 10-year gap, no communication.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 009 (関孝和)
"""

from manim import (
    DOWN,
    LEFT,
    UP,
    DashedLine,
    Dot,
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


class DeterminantExpansion(Scene):
    """Determinant expansion — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "two_by_two")
        self._duration = params.get("duration", 18)

        if mode == "seki_method":
            self._build_seki_method()
        elif mode == "history_parallel":
            self._build_history_parallel()
        else:
            self._build_two_by_two()

    # ------------------------------------------------------------------
    # Mode A: two_by_two
    # ------------------------------------------------------------------
    def _build_two_by_two(self):
        duration = self._duration

        title = Text(
            "行列式 ── 2×2 から始めよう",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 5 * 0.8 + 0.6
        default_waits = 5 * 1.0 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Symbolic matrix on the left
        sym_matrix = MathTex(
            r"\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc",
            font_size=42,
            color=TEXT_WHITE,
        )
        sym_matrix.move_to([-3.0, 1.2, 0])

        self.play(FadeIn(sym_matrix), run_time=0.8)
        self.wait(0.6 * ws)

        # Numeric example on the right: [[2,1],[1,3]]
        num_matrix = MathTex(
            r"\begin{pmatrix} 2 & 1 \\ 1 & 3 \end{pmatrix}",
            font_size=48,
            color=TEXT_WHITE,
        )
        num_matrix.move_to([3.0, 1.2, 0])
        self.play(FadeIn(num_matrix), run_time=0.8)
        self.wait(0.4 * ws)

        # Main diagonal (a·d)
        main_diag_label = MathTex(
            r"2 \cdot 3 = 6",
            font_size=36,
            color=ACCENT_GOLD,
        )
        main_diag_label.move_to([3.0, -0.1, 0])
        main_arrow = Text("主対角", font=FONT, font_size=20, color=ACCENT_GOLD)
        main_arrow.next_to(main_diag_label, LEFT, buff=0.3)
        self.play(FadeIn(main_arrow), FadeIn(main_diag_label), run_time=0.8)
        self.wait(0.8 * ws)

        # Anti-diagonal (b·c)
        anti_diag_label = MathTex(
            r"1 \cdot 1 = 1",
            font_size=36,
            color=ACCENT_PINK,
        )
        anti_diag_label.move_to([3.0, -0.9, 0])
        anti_arrow = Text("副対角", font=FONT, font_size=20, color=ACCENT_PINK)
        anti_arrow.next_to(anti_diag_label, LEFT, buff=0.3)
        self.play(FadeIn(anti_arrow), FadeIn(anti_diag_label), run_time=0.8)
        self.wait(0.8 * ws)

        # Result
        result_eq = MathTex(
            r"\det = 6 - 1 = 5",
            font_size=40,
            color=ACCENT_CYAN,
        )
        result_eq.move_to([0, -1.7, 0])
        box = Rectangle(
            width=3.5,
            height=0.85,
            color=ACCENT_CYAN,
            stroke_width=2,
            fill_opacity=0.1,
        )
        box.move_to(result_eq)
        self.play(FadeIn(box), FadeIn(result_eq), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode B: seki_method (3x3 Sarrus)
    # ------------------------------------------------------------------
    def _build_seki_method(self):
        duration = self._duration

        title = Text(
            "交式斜乗（関の展開法）",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 6 * 0.7 + 1.2 + 0.8
        default_waits = 6 * 0.7 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # 3x3 matrix (numeric): [[1,2,3],[4,5,6],[7,8,10]]
        matrix_tex = MathTex(
            r"\begin{pmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 10 \end{pmatrix}",
            font_size=42,
            color=TEXT_WHITE,
        )
        matrix_tex.move_to([-3.5, 0.6, 0])
        self.play(FadeIn(matrix_tex), run_time=0.8)
        self.wait(0.4 * ws)

        # Note: Seki built concrete examples (not general formula)
        note = Text(
            "関は具体例を一つずつ組み立てた",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        note.move_to([-3.5, -1.3, 0])
        self.play(FadeIn(note), run_time=0.5)
        self.wait(0.3 * ws)

        # Positive 3 terms (diagonal): 1·5·10=50, 2·6·7=84, 3·4·8=96
        pos_label = Text("正方向（+）", font=FONT, font_size=22, color=ACCENT_CYAN)
        pos_label.move_to([3.0, 1.9, 0])

        pos_terms = VGroup(
            MathTex(r"1 \cdot 5 \cdot 10 = 50", font_size=26, color=ACCENT_CYAN),
            MathTex(r"2 \cdot 6 \cdot 7 = 84", font_size=26, color=ACCENT_CYAN),
            MathTex(r"3 \cdot 4 \cdot 8 = 96", font_size=26, color=ACCENT_CYAN),
        )
        pos_terms.arrange(DOWN, buff=0.15)
        pos_terms.move_to([3.0, 1.15, 0])

        # Negative 3 terms: 3·5·7=105, 1·6·8=48, 2·4·10=80
        neg_label = Text("斜方向（−）", font=FONT, font_size=22, color=ACCENT_PINK)
        neg_label.move_to([3.0, 0.1, 0])

        neg_terms = VGroup(
            MathTex(r"3 \cdot 5 \cdot 7 = 105", font_size=26, color=ACCENT_PINK),
            MathTex(r"1 \cdot 6 \cdot 8 = 48", font_size=26, color=ACCENT_PINK),
            MathTex(r"2 \cdot 4 \cdot 10 = 80", font_size=26, color=ACCENT_PINK),
        )
        neg_terms.arrange(DOWN, buff=0.15)
        neg_terms.move_to([3.0, -0.65, 0])

        self.play(FadeIn(pos_label), run_time=0.5)
        for t in pos_terms:
            self.play(FadeIn(t), run_time=0.5)
            self.wait(0.2 * ws)

        self.play(FadeIn(neg_label), run_time=0.5)
        for t in neg_terms:
            self.play(FadeIn(t), run_time=0.5)
            self.wait(0.2 * ws)

        # Final result: (50+84+96) - (105+48+80) = 230 - 233 = -3
        result_eq = MathTex(
            r"\det = 230 - 233 = -3",
            font_size=36,
            color=ACCENT_GOLD,
        )
        result_eq.move_to([-0.3, -1.9, 0])
        box = Rectangle(
            width=5.5,
            height=0.7,
            color=ACCENT_GOLD,
            stroke_width=2,
            fill_opacity=0.1,
        )
        box.move_to(result_eq)
        self.play(FadeIn(box), FadeIn(result_eq), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode C: history_parallel
    # ------------------------------------------------------------------
    def _build_history_parallel(self):
        duration = self._duration

        title = Text(
            "同じ発見、違う場所、10年の差",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 1.2 + 1.2 + 0.8 + 0.8
        default_waits = 5 * 0.8 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Timeline axis 1680 - 1695 across x = -5.5 to 5.5
        axis_y = 0.2
        axis = Line(
            start=[-5.5, axis_y, 0],
            end=[5.5, axis_y, 0],
            color=TEXT_DIM,
            stroke_width=3,
        )

        # Year ticks
        years = [1680, 1685, 1690, 1695]
        tick_labels = VGroup()
        for y in years:
            # Map 1680 -> -5.5, 1695 -> +5.5 (15 year span, 11 units wide)
            x = -5.5 + (y - 1680) * (11.0 / 15.0)
            tick = Line(
                start=[x, axis_y - 0.1, 0],
                end=[x, axis_y + 0.1, 0],
                color=TEXT_DIM,
                stroke_width=2,
            )
            label = Text(str(y), font=FONT, font_size=18, color=TEXT_DIM)
            label.next_to(tick, DOWN, buff=0.15)
            tick_labels.add(tick, label)

        self.play(FadeIn(axis), FadeIn(tick_labels), run_time=1.0)
        self.wait(0.4 * ws)

        # Seki marker at 1683
        seki_x = -5.5 + (1683 - 1680) * (11.0 / 15.0)  # = -5.5 + 2.2 = -3.3
        seki_dot = Dot([seki_x, axis_y, 0], color=ACCENT_GOLD, radius=0.15)
        seki_name = Text("関孝和", font=FONT, font_size=22, color=ACCENT_GOLD)
        seki_book = Text("『解伏題之法』", font=FONT, font_size=20, color=TEXT_WHITE)
        seki_place = Text("（江戸）", font=FONT, font_size=18, color=TEXT_DIM)
        seki_year = Text("1683", font=FONT, font_size=20, color=ACCENT_GOLD)
        seki_info = VGroup(seki_name, seki_book, seki_place)
        seki_info.arrange(DOWN, buff=0.1)
        seki_info.move_to([seki_x, 1.55, 0])
        seki_year.move_to([seki_x, 0.7, 0])

        seki_stem = Line(
            start=[seki_x, axis_y + 0.15, 0],
            end=[seki_x, 0.5, 0],
            color=ACCENT_GOLD,
            stroke_width=2,
        )

        self.play(
            FadeIn(seki_dot),
            FadeIn(seki_stem),
            FadeIn(seki_year),
            FadeIn(seki_info),
            run_time=1.2,
        )
        self.wait(0.6 * ws)

        # Leibniz marker at 1693
        leib_x = -5.5 + (1693 - 1680) * (11.0 / 15.0)  # = -5.5 + 9.53 = 4.03
        leib_dot = Dot([leib_x, axis_y, 0], color=ACCENT_CYAN, radius=0.15)
        leib_name = Text("ライプニッツ", font=FONT, font_size=22, color=ACCENT_CYAN)
        leib_book = Text("ロピタル宛書簡", font=FONT, font_size=20, color=TEXT_WHITE)
        leib_place = Text("（ハノーファー）", font=FONT, font_size=18, color=TEXT_DIM)
        leib_year = Text("1693", font=FONT, font_size=20, color=ACCENT_CYAN)
        leib_info = VGroup(leib_name, leib_book, leib_place)
        leib_info.arrange(DOWN, buff=0.1)
        leib_info.move_to([leib_x, 1.55, 0])
        leib_year.move_to([leib_x, 0.7, 0])

        leib_stem = Line(
            start=[leib_x, axis_y + 0.15, 0],
            end=[leib_x, 0.5, 0],
            color=ACCENT_CYAN,
            stroke_width=2,
        )

        self.play(
            FadeIn(leib_dot),
            FadeIn(leib_stem),
            FadeIn(leib_year),
            FadeIn(leib_info),
            run_time=1.2,
        )
        self.wait(0.6 * ws)

        # Dashed line between the two (no-communication line)
        connector = DashedLine(
            start=[seki_x + 0.2, axis_y - 0.8, 0],
            end=[leib_x - 0.2, axis_y - 0.8, 0],
            color=TEXT_DIM,
            stroke_width=2,
            dash_length=0.15,
        )
        no_contact = Text(
            "交流なし",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        no_contact.move_to([(seki_x + leib_x) / 2, axis_y - 1.1, 0])

        self.play(FadeIn(connector), FadeIn(no_contact), run_time=0.8)
        self.wait(0.4 * ws)

        # Bottom caption
        caption = Text(
            "独立に同じ数学へ到達",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        )
        caption.move_to([0, -1.85, 0])
        self.play(FadeIn(caption), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))


# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
# B-10: factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "two_by_two": {"people": [], "years": []},
    "seki_method": {"people": [], "years": []},
    "history_parallel": {
        "people": [
            ["関孝和", "関"],
            ["ライプニッツ", "Leibniz"],
        ],
        "years": ["1683", "1693"],
    },
}


SCENES = {
    "two_by_two": DeterminantExpansion,
    "seki_method": DeterminantExpansion,
    "history_parallel": DeterminantExpansion,
}
