"""
diagonal_argument.py - Cantor's diagonal argument visualization for 数学史記

Visualizes Cantor's 1891 proof that the reals in [0,1) cannot be
enumerated by the naturals. The most celebrated argument in set theory.

Modes:
    setup    - Suppose all reals in [0,1) are enumerated as r_1, r_2, ...
               Display 6 sample reals with 6 visible decimal digits each.
               Fixed params: 6 rows, 6 digits per row.
    diagonal - Highlight the diagonal digits d_{nn} in GOLD.
               Fixed params: same 6 rows, diagonal cells = (1,1)..(6,6).
    flip     - Construct a new real s by flipping each diagonal digit
               via rule s_n = (d_{nn} + 1) mod 10 (digits chosen so no
               overflow). Show s differs from every r_n at position n,
               so s is not in the list — contradiction.
               Fixed params: flipped s = 0.267248 for fixed digits.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 016 (Cantor), math pillar 3 (the core scene).
"""

from manim import (
    DOWN,
    UP,
    Arrow,
    FadeIn,
    MathTex,
    Scene,
    SurroundingRectangle,
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


# Fixed digit table. Each row: r_i = 0.d_{i1} d_{i2} ... d_{i6}
# Diagonal (d_11, d_22, ..., d_66) = (1, 5, 6, 1, 3, 7).
# Flipped (d_ii + 1): s = (2, 6, 7, 2, 4, 8). No 9->0 overflow needed.
DIGITS = [
    [1, 4, 9, 2, 6, 5],
    [3, 5, 8, 9, 7, 9],
    [7, 1, 6, 3, 5, 2],
    [4, 2, 8, 1, 5, 7],
    [9, 5, 2, 1, 3, 8],
    [6, 2, 4, 8, 1, 7],
]
N_ROWS = len(DIGITS)
N_DIGITS = len(DIGITS[0])
FLIPPED = [(DIGITS[i][i] + 1) % 10 for i in range(N_ROWS)]  # [2,6,7,2,4,8]


class DiagonalArgument(Scene):
    """Cantor's diagonal argument. Mode-branching scene.

    Modes:
        setup (default) - enumerate 6 reals with visible digits
        diagonal        - highlight diagonal digits
        flip            - construct s not in the list
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "setup")

        if mode == "diagonal":
            self.build_diagonal(highlight_only=True)
        elif mode == "flip":
            self.build_diagonal(highlight_only=False)
        else:
            self.build_setup()

    # -------------------------------------------------------------------
    # Layout constants
    # -------------------------------------------------------------------
    ROW_Y_START = 2.0
    ROW_SPACING = 0.5
    LABEL_X = -4.8
    PREFIX_X = -3.8  # "= 0."
    FIRST_DIGIT_X = -2.8
    DIGIT_SPACING = 0.55

    def _row_y(self, i):
        return self.ROW_Y_START - i * self.ROW_SPACING

    def _digit_x(self, j):
        return self.FIRST_DIGIT_X + j * self.DIGIT_SPACING

    # -------------------------------------------------------------------
    # Mode: setup
    # -------------------------------------------------------------------
    def build_setup(self):
        duration = self._duration

        title = Text("実数を数え上げられると仮定すると", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        digit_mobs = self._build_rows()

        for row in digit_mobs:
            for mob in row:
                self.play(FadeIn(mob), run_time=0.04)

        anim_overhead = 0.5 + 0.04 * sum(len(r) for r in digit_mobs)
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: diagonal / flip
    # -------------------------------------------------------------------
    def build_diagonal(self, highlight_only: bool):
        duration = self._duration
        highlight = self._highlight_color

        title = Text(
            "対角線論法 ── 列挙に含まれない実数を作る", font=FONT, font_size=26, color=TEXT_DIM
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        digit_mobs = self._build_rows(animate=True, per_item=0.02)

        # Highlight diagonal digits d_{ii}
        diag_cells = [digit_mobs[i][2 + i] for i in range(N_ROWS)]
        # digit_mobs[i] structure: [label, "= 0.", d_1, d_2, ..., d_6]
        # index 0: label (r_i), 1: "= 0.", 2+j: j-th digit (0-indexed)
        self.play(
            *[cell.animate.set_color(highlight) for cell in diag_cells],
            run_time=0.8,
        )

        # Surrounding box around each diagonal cell for emphasis
        boxes = [
            SurroundingRectangle(cell, color=highlight, buff=0.05, stroke_width=2.5)
            for cell in diag_cells
        ]
        for box in boxes:
            self.play(FadeIn(box), run_time=0.1)

        if highlight_only:
            anim_overhead = 0.5 + 0.02 * sum(len(r) for r in digit_mobs) + 0.8 + 0.1 * len(boxes)
            self.wait(max(1.0, duration - anim_overhead))
            return

        # Flip mode: construct s = 0.s_1 s_2 ... s_6
        # Each s_i = (d_{ii} + 1) mod 10, listed as FLIPPED.
        s_y = -1.5

        s_label = MathTex(r"s", font_size=34, color=ACCENT_PINK)
        s_label.move_to([self.LABEL_X, s_y, 0])
        s_prefix = MathTex(r"= \; 0.", font_size=32, color=TEXT_WHITE)
        s_prefix.move_to([self.PREFIX_X, s_y, 0])

        self.play(FadeIn(s_label), FadeIn(s_prefix), run_time=0.4)

        s_digits = []
        for i, d in enumerate(FLIPPED):
            x = self._digit_x(i)
            digit = MathTex(str(d), font_size=36, color=ACCENT_PINK)
            digit.move_to([x, s_y, 0])
            s_digits.append(digit)
            # Draw arrow from diagonal cell to s_i
            arrow = Arrow(
                start=diag_cells[i].get_bottom() + DOWN * 0.05,
                end=digit.get_top() + UP * 0.05,
                color=highlight,
                buff=0.05,
                stroke_width=2,
                max_tip_length_to_length_ratio=0.12,
            )
            self.play(FadeIn(arrow), FadeIn(digit), run_time=0.25)

        conclusion = Text(
            "s はどの列とも必ず一桁違う ── 矛盾", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        conclusion.move_to([0, -2.0, 0])
        self.play(FadeIn(conclusion), run_time=0.6)

        anim_overhead = (
            0.5
            + 0.02 * sum(len(r) for r in digit_mobs)
            + 0.8
            + 0.1 * len(boxes)
            + 0.4
            + 0.25 * N_ROWS
            + 0.6
        )
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _build_rows(self, animate=False, per_item=0.04):
        """Create the 6 rows of labeled reals with fixed digits.

        Each returned row is a list of mobjects:
            [label, "= 0.", digit_1, digit_2, ..., digit_6]

        If animate is True, caller animates them. This method just
        creates and positions them without animating.
        """
        rows = []
        for i in range(N_ROWS):
            y = self._row_y(i)
            label = MathTex(rf"r_{{{i + 1}}}", font_size=32, color=ACCENT_CYAN)
            label.move_to([self.LABEL_X, y, 0])
            prefix = MathTex(r"= \; 0.", font_size=30, color=TEXT_WHITE)
            prefix.move_to([self.PREFIX_X, y, 0])
            row = [label, prefix]
            for j, d in enumerate(DIGITS[i]):
                x = self._digit_x(j)
                digit = MathTex(str(d), font_size=34, color=TEXT_WHITE)
                digit.move_to([x, y, 0])
                row.append(digit)
            # Trailing ellipsis
            ellipsis = MathTex(r"\ldots", font_size=30, color=TEXT_DIM)
            ellipsis.move_to([self._digit_x(N_DIGITS) + 0.1, y, 0])
            row.append(ellipsis)
            rows.append(row)

            if not animate:
                for mob in row:
                    self.add(mob)

        if animate:
            for row in rows:
                for mob in row:
                    self.play(FadeIn(mob), run_time=per_item)

        return rows


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "setup": {"people": [], "years": []},
    "diagonal": {"people": [], "years": []},
    "flip": {"people": [], "years": []},
}


SCENES = {
    "setup": {
        "class": "DiagonalArgument",
        "params": {"mode": "setup"},
        "description": "Enumerate 6 sample reals in [0,1) with fixed digits",
    },
    "diagonal": {
        "class": "DiagonalArgument",
        "params": {"mode": "diagonal"},
        "description": "Highlight diagonal digits d_{11}..d_{66} in gold",
    },
    "flip": {
        "class": "DiagonalArgument",
        "params": {"mode": "flip"},
        "description": "Flip each diagonal digit to construct s not in the list",
    },
}
