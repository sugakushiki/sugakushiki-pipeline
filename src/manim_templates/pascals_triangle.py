"""
pascals_triangle.py - Pascal's triangle and binomial coefficients for 数学史記

Pascal's Traité du triangle arithmétique (text printed Paris 1654, formally
published posthumously by Desprez 1665) tabulated the binomial coefficients
C(n, k) = n! / (k! (n-k)!) in a triangular array and used the recursive
identity
    C(n, k) = C(n-1, k-1) + C(n-1, k)
to derive properties of combinations. The treatise contains one of the
earliest explicit uses of mathematical induction in the Western tradition.

Modes:
    rows_build
        Build rows 0 through 6 of the triangle one at a time. Each cell is
        labeled with C(n, k) (numerical value). For rows 2 and above, draw
        two short arrows from the two parent cells into the new cell to
        illustrate Pascal's identity C(n,k) = C(n-1,k-1) + C(n-1,k).
        Fixed params: rows 0..6, row height 0.5, cell horizontal spacing
        0.7, top row at y = 2.10.

    binomial_highlight
        Show all rows 0..6, then highlight row n = 4 (values 1, 4, 6, 4, 1)
        in ACCENT_GOLD. Below the triangle, display the binomial expansion
        (x + y)^4 = x^4 + 4 x^3 y + 6 x^2 y^2 + 4 x y^3 + y^4 with each
        coefficient colored to match its triangle cell.
        Fixed params: highlighted row n = 4.

    probability_link
        Show rows 0..6 dimmed, then re-emphasize row n = 4 and add a
        probability label: C(4,k) / 2^4 = {1/16, 4/16, 6/16, 4/16, 1/16}.
        Display histogram-like vertical bars whose heights are proportional
        to C(4,k). This connects the triangle to the binomial probability
        distribution for n = 4 fair coin flips.
        Fixed params: n = 4 for probability row.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.3, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 029 (Pascal), 遺産4 - パスカルの三角形.
"""

from math import comb

from manim import (
    Arrow,
    FadeIn,
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

# Triangle layout constants
ROW_TOP_Y = 2.10
ROW_DY = 0.50
CELL_DX = 0.70
N_ROWS = 7  # rows 0..6


def _cell_position(n, k):
    """Return (x, y) center of cell at row n, position k (0 <= k <= n)."""
    x = (k - n / 2.0) * CELL_DX
    y = ROW_TOP_Y - n * ROW_DY
    return [x, y, 0]


class PascalsTriangle(Scene):
    """Pascal's triangle visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "rows_build")
        self._duration = float(params.get("duration", 25))

        if mode == "binomial_highlight":
            self._build_binomial_highlight()
        elif mode == "probability_link":
            self._build_probability_link()
        else:
            self._build_rows_build()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _cell(self, value, n, k, color=ACCENT_CYAN, font_size=22):
        # Text(font=FONT) is rendered via cairo (no LaTeX subprocess), making
        # 28 cells × FadeIn complete in seconds instead of timing out at 240s.
        # ある回 fix: math_11/12 (binomial_highlight, probability_link)
        # previously hit 240s timeout with MathTex(str(value)) × 28 cells.
        cell = Text(str(value), font=FONT, font_size=font_size, color=color)
        cell.move_to(_cell_position(n, k))
        return cell

    def _full_triangle(self, color=ACCENT_CYAN, max_rows=None):
        """Build triangle rows 0..max_rows-1. Default max_rows = N_ROWS (=7).

        For binomial_highlight and probability_link, pass max_rows=5 so that
        the target row n=4 sits at the bottom and the lower half of the
        screen is free for the expansion formula / histogram bars
        (avoiding overlap with rows 5, 6).
        """
        if max_rows is None:
            max_rows = N_ROWS
        cells = {}
        for n in range(max_rows):
            for k in range(n + 1):
                cells[(n, k)] = self._cell(comb(n, k), n, k, color=color)
        return cells

    # ------------------------------------------------------------------
    def _build_rows_build(self):
        duration = self._duration
        title = self._title("パスカルの三角形 ── 行を一つずつ組み立てる")
        self.play(FadeIn(title), run_time=0.6)

        identity = MathTex(
            r"C(n,k) = C(n{-}1,k{-}1) + C(n{-}1,k)",
            font_size=22,
            color=ACCENT_PINK,
        )
        identity.move_to([0, 2.65, 0])
        self.play(FadeIn(identity), run_time=0.5)

        cells = {}
        for n in range(N_ROWS):
            new_cells = [self._cell(comb(n, k), n, k) for k in range(n + 1)]
            arrows = []
            if n >= 2 and n <= 4:
                # Draw two short arrows showing parents → new cell at k=1
                # (for visual clarity, only annotate the second cell)
                k_target = 1
                if k_target <= n:
                    target_pos = _cell_position(n, k_target)
                    parent_left = _cell_position(n - 1, k_target - 1)
                    parent_right = _cell_position(n - 1, k_target)
                    a1 = Arrow(
                        start=[parent_left[0], parent_left[1] - 0.12, 0],
                        end=[target_pos[0] - 0.08, target_pos[1] + 0.12, 0],
                        color=ACCENT_PINK,
                        buff=0.04,
                        stroke_width=2.0,
                        max_tip_length_to_length_ratio=0.18,
                    )
                    a2 = Arrow(
                        start=[parent_right[0], parent_right[1] - 0.12, 0],
                        end=[target_pos[0] + 0.08, target_pos[1] + 0.12, 0],
                        color=ACCENT_PINK,
                        buff=0.04,
                        stroke_width=2.0,
                        max_tip_length_to_length_ratio=0.18,
                    )
                    arrows = [a1, a2]
            if arrows:
                self.play(
                    *[FadeIn(c) for c in new_cells], *[FadeIn(a) for a in arrows], run_time=0.55
                )
            else:
                self.play(*[FadeIn(c) for c in new_cells], run_time=0.45)
            for k, c in enumerate(new_cells):
                cells[(n, k)] = c

        # Brief afterword
        msg = Text("各セルは上の二つの和", font=FONT, font_size=20, color=ACCENT_PINK)
        msg.move_to([0, -1.85, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.5 + 0.45 * 7 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_binomial_highlight(self):
        duration = self._duration
        title = self._title("二項係数と二項定理")
        self.play(FadeIn(title), run_time=0.6)

        # Render only rows 0..4 (target_row=4 sits at bottom) so that the
        # expansion formula + coefficient labels below have free space and
        # don't overlap with rows 5, 6.
        cells = self._full_triangle(color=TEXT_DIM, max_rows=5)
        # Use VGroup for one-shot FadeIn instead of 28 individual FadeIns
        # (reduces Manim animation overhead). ある回 fix.
        self.play(FadeIn(VGroup(*cells.values())), run_time=0.9)

        # Highlight row n = 4: cells (4,0)..(4,4) values 1, 4, 6, 4, 1.
        # Use .animate.set_color() instead of .copy() + FadeIn + shift
        # (Text(font=FONT).copy() is broken with shift on this Manim version:
        # ValueError: operands could not be broadcast together (60,3) (0,)).
        target_row = 4
        self.play(
            *[cells[(target_row, k)].animate.set_color(ACCENT_GOLD) for k in range(target_row + 1)],
            run_time=0.5,
        )

        # Below triangle, show binomial expansion
        expansion = MathTex(
            r"(x+y)^4 = x^4 + 4 x^3 y + 6 x^2 y^2 + 4 x y^3 + y^4",
            font_size=26,
            color=TEXT_WHITE,
        )
        expansion.move_to([0, -1.20, 0])
        self.play(FadeIn(expansion), run_time=0.7)

        # Coefficient labels colored gold
        coeffs_label = MathTex(
            r"C(4,0){=}1,\;C(4,1){=}4,\;C(4,2){=}6,\;C(4,3){=}4,\;C(4,4){=}1",
            font_size=22,
            color=ACCENT_GOLD,
        )
        coeffs_label.move_to([0, -1.85, 0])
        self.play(FadeIn(coeffs_label), run_time=0.6)

        anim_total = 0.6 + 0.9 + 0.5 + 0.7 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_probability_link(self):
        duration = self._duration
        title = self._title("コインを 4 回投げると ── 二項分布として")
        self.play(FadeIn(title), run_time=0.6)

        # Render only rows 0..4 (target_row=4 at bottom) so the histogram
        # bars below have free space.
        cells = self._full_triangle(color=TEXT_DIM, max_rows=5)
        # Use VGroup for one-shot FadeIn.
        self.play(FadeIn(VGroup(*cells.values())), run_time=0.8)

        # Highlight target row with .animate.set_color() (avoids
        # Text(font=FONT).copy()+shift broadcast error on this Manim version).
        target_row = 4
        self.play(
            *[cells[(target_row, k)].animate.set_color(ACCENT_GOLD) for k in range(target_row + 1)],
            run_time=0.5,
        )

        # Histogram of C(4,k)/16 below triangle
        bar_base_y = -1.20
        bar_unit = 0.10  # height per unit (max value 6 → 0.60)
        bar_width = 0.45
        bar_spacing = 0.85

        bars = VGroup()
        prob_labels = VGroup()
        for k in range(target_row + 1):
            value = comb(target_row, k)
            bar_h = value * bar_unit
            bar = Rectangle(
                width=bar_width,
                height=bar_h,
                color=ACCENT_CYAN,
                fill_color=ACCENT_CYAN,
                fill_opacity=0.65,
                stroke_width=1.4,
            )
            bar_x = (k - target_row / 2.0) * bar_spacing
            bar.move_to([bar_x, bar_base_y + bar_h / 2.0, 0])
            bars.add(bar)
            lbl = MathTex(rf"\tfrac{{{value}}}{{16}}", font_size=18, color=ACCENT_GOLD)
            lbl.move_to([bar_x, bar_base_y + bar_h + 0.20, 0])
            prob_labels.add(lbl)

        self.play(*[FadeIn(b) for b in bars], *[FadeIn(lab) for lab in prob_labels], run_time=0.9)

        msg = Text(
            "k 回表が出る確率 = C(4,k) / 2^4",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.8 + 0.5 + 0.9 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "rows_build": {"people": [], "years": []},
    "binomial_highlight": {"people": [], "years": []},
    "probability_link": {"people": [], "years": []},
}

SCENES = {
    "rows_build": PascalsTriangle,
    "binomial_highlight": PascalsTriangle,
    "probability_link": PascalsTriangle,
}
