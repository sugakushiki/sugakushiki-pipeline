"""
pascals_wager_table.py - Pascal's Wager (decision-theoretic table) for 数学史記

Pascal's Wager appears in 'Pensées de M. Pascal sur la religion et sur
quelques autres sujets' (Port-Royal edition, Paris 1670, posthumous),
fragment Lafuma 418 / Brunschvicg 233. The argument is not a proof of
God's existence; it is a decision-theoretic case for the rationality of
faith, framed in the language of expectation. Pascal places the choice
to believe or not believe against the two possibilities of God's
existence or non-existence and observes that the believer's expected
utility is dominated by +∞ (eternal beatitude) when God exists, whereas
all other cells of the matrix remain finite. The mainstream Hájek/SEP
reading assigns finite values f1, f2, f3 to the other three cells; some
later writers (Hacking, Martin) instead assign -∞ to the non-believer /
God-exists cell to reflect 'eternal damnation', but this is a secondary
interpretation. This template adopts the mainstream finite reading.

Stanford Encyclopedia of Philosophy (Alan Hájek) distinguishes three
formulations: (i) the dominance argument, (ii) the expectations
argument, and (iii) the dominating-expectations argument. This template
visualises the expectations argument.

Modes:
    expectation_matrix
        Draw a 2×2 decision matrix:
                    God exists     God does not exist
            Believe |    +∞      |    -c (finite loss)
            Not     |    -d      |    +e (finite gain)
        with row and column headers and color-coded cells. The +∞ cell is
        highlighted in ACCENT_GOLD to show why it dominates the
        comparison; all other cells are finite.
        Fixed params: 2×2 matrix layout, cell width 3.0, cell height 0.95.

    infinity_comparison
        Algebraic comparison of two expected utilities:
            E[believe]      = p · (+∞) + (1−p) · (−c)  =  +∞   (for any p > 0)
            E[not believe]  = p · (−d) + (1−p) · (+e)  =  finite
        Where c, d, e are finite positive numbers. Show two stacked
        equations with the +∞ term highlighted, and a concluding line
        E[believe] > E[not believe] (+∞ > finite). Below, annotate
        'これは「神の存在証明」ではなく、信仰の決定の合理性の議論である'.
        Fixed params: symbolic expectations with p > 0.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.3, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 029 (Pascal), 遺産6 - パスカルの賭けと『パンセ』.
"""

from manim import (
    Create,
    FadeIn,
    MathTex,
    Rectangle,
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


class PascalsWagerTable(Scene):
    """Pascal's Wager decision-theoretic visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "expectation_matrix")
        self._duration = float(params.get("duration", 25))

        if mode == "infinity_comparison":
            self._build_infinity_comparison()
        else:
            self._build_expectation_matrix()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_expectation_matrix(self):
        duration = self._duration
        title = self._title("パスカルの賭け ── 期待値の行列")
        self.play(FadeIn(title), run_time=0.6)

        # Matrix layout: 2 cols × 2 rows, cell w=3.0 h=0.95
        cell_w = 3.0
        cell_h = 0.95
        # Top-left of matrix data area (rows: 0=Believe row, 1=Not row)
        # Place matrix centered horizontally with the row headers to its left.
        x_left_col = 0.0
        x_right_col = x_left_col + cell_w
        y_top_row = 0.95
        y_bot_row = y_top_row - cell_h

        # Column headers
        col1_lbl = Text("神が存在する", font=FONT, font_size=22, color=ACCENT_CYAN)
        col1_lbl.move_to([x_left_col, y_top_row + cell_h / 2.0 + 0.45, 0])
        col2_lbl = Text("神が存在しない", font=FONT, font_size=22, color=ACCENT_CYAN)
        col2_lbl.move_to([x_right_col, y_top_row + cell_h / 2.0 + 0.45, 0])

        # Row headers
        row1_lbl = Text("信じる", font=FONT, font_size=22, color=ACCENT_PINK)
        row1_lbl.move_to([x_left_col - cell_w / 2.0 - 0.90, y_top_row, 0])
        row2_lbl = Text("信じない", font=FONT, font_size=22, color=ACCENT_PINK)
        row2_lbl.move_to([x_left_col - cell_w / 2.0 - 0.90, y_bot_row, 0])

        # Cell rectangles
        def cell_rect(cx, cy, color, fill_op=0.2):
            r = Rectangle(
                width=cell_w * 0.92,
                height=cell_h * 0.85,
                color=color,
                fill_color=color,
                fill_opacity=fill_op,
                stroke_width=2.0,
            )
            r.move_to([cx, cy, 0])
            return r

        cell11 = cell_rect(x_left_col, y_top_row, ACCENT_GOLD, fill_op=0.30)
        cell12 = cell_rect(x_right_col, y_top_row, TEXT_DIM, fill_op=0.10)
        cell21 = cell_rect(x_left_col, y_bot_row, TEXT_DIM, fill_op=0.10)
        cell22 = cell_rect(x_right_col, y_bot_row, TEXT_DIM, fill_op=0.10)

        # Cell contents (Hájek/SEP mainstream: finite cells f1/f2/f3, only
        # the believer/God-exists cell is +∞ in the expectations argument).
        cell11_txt = MathTex(r"+\infty", font_size=36, color=ACCENT_GOLD)
        cell11_txt.move_to([x_left_col, y_top_row, 0])
        cell12_txt = MathTex(r"-c", font_size=28, color=TEXT_WHITE)
        cell12_txt.move_to([x_right_col, y_top_row, 0])
        cell21_txt = MathTex(r"-d", font_size=28, color=TEXT_WHITE)
        cell21_txt.move_to([x_left_col, y_bot_row, 0])
        cell22_txt = MathTex(r"+e", font_size=28, color=TEXT_WHITE)
        cell22_txt.move_to([x_right_col, y_bot_row, 0])

        # Build header & matrix in two stages
        self.play(
            FadeIn(col1_lbl), FadeIn(col2_lbl), FadeIn(row1_lbl), FadeIn(row2_lbl), run_time=0.7
        )
        self.play(
            Create(cell11),
            Create(cell12),
            Create(cell21),
            Create(cell22),
            run_time=1.0,
        )
        self.play(
            FadeIn(cell11_txt),
            FadeIn(cell12_txt),
            FadeIn(cell21_txt),
            FadeIn(cell22_txt),
            run_time=0.8,
        )

        # Lower legend (Text for Japanese, MathTex disallowed)
        legend = Text(
            "c, d, e > 0 (有限の値)",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        legend.move_to([0.5, -1.30, 0])
        self.play(FadeIn(legend), run_time=0.5)

        msg = Text(
            "+∞ のセルが他の値を支配する ── これが賭けの核心",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.7 + 1.0 + 0.8 + 0.5 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_infinity_comparison(self):
        duration = self._duration
        title = self._title("期待値の比較 ── ∞ と有限")
        self.play(FadeIn(title), run_time=0.6)

        # Believer's expected utility (use ASCII Believe/NotBelieve labels in
        # MathTex; Japanese row legend appears as separate Text below.)
        eq_believe = MathTex(
            r"E[\mathrm{Believe}] = p \cdot (+\infty) + (1-p) \cdot (-c) = +\infty",
            font_size=26,
            color=ACCENT_GOLD,
        )
        eq_believe.move_to([0, 1.50, 0])
        self.play(FadeIn(eq_believe), run_time=0.8)

        # Non-believer's expected utility (Hájek/SEP mainstream: all
        # non-believer cells are finite, so the expectation is finite)
        eq_not = MathTex(
            r"E[\mathrm{NotBelieve}] = p \cdot (-d) + (1-p) \cdot (+e) = \mathrm{finite}",
            font_size=26,
            color=ACCENT_CYAN,
        )
        eq_not.move_to([0, 0.55, 0])
        self.play(FadeIn(eq_not), run_time=0.8)

        # Condition reminder (Text for Japanese)
        cond = Text(
            "p > 0 (神が存在する確率が 0 より大きい)",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        cond.move_to([0, -0.20, 0])
        self.play(FadeIn(cond), run_time=0.5)

        # Conclusion (MathTex with ASCII Believe/NotBelieve)
        conclusion = MathTex(
            r"\therefore\;E[\mathrm{Believe}] > E[\mathrm{NotBelieve}]\quad(+\infty > \mathrm{finite})",
            font_size=28,
            color=ACCENT_PINK,
        )
        conclusion.move_to([0, -1.05, 0])
        self.play(FadeIn(conclusion), run_time=0.8)

        # Legend mapping Believe/NotBelieve to Japanese (Text)
        legend = Text(
            "Believe = 信じる、NotBelieve = 信じない",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        legend.move_to([0, -1.55, 0])
        self.play(FadeIn(legend), run_time=0.4)

        # Disclaimer
        disclaimer = Text(
            "これは「神の存在証明」ではなく、信仰の決定の合理性の議論",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        disclaimer.move_to([0, -1.92, 0])
        self.play(FadeIn(disclaimer), run_time=0.6)

        anim_total = 0.6 + 0.8 + 0.8 + 0.5 + 0.8 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "expectation_matrix": {"people": [], "years": []},
    "infinity_comparison": {"people": [], "years": []},
}

SCENES = {
    "expectation_matrix": PascalsWagerTable,
    "infinity_comparison": PascalsWagerTable,
}
