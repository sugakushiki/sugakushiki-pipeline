"""
bijection_diagram.py - One-to-one correspondence visualizations for 数学史記

Visualizes Cantor's definition of "same cardinality" via explicit bijections.

Modes:
    natural_even    - N = {1,2,3,...} <-> 2N = {2,4,6,...} via n ↔ 2n.
                      Two columns of 6 elements each, connecting arrows.
                      Demonstrates that a proper subset of N has the same
                      cardinality as N itself (paradox-of-infinity).
                      Fixed params: 6 visible rows (n=1..6, 2n=2..12)
                      + ellipsis. 1-based for consistency with episode
                      narration.
    rational_zigzag - Positive rationals p/q arranged on a 2D grid,
                      animated zigzag path (Cantor's enumeration) visits
                      (1,1) (1,2) (2,1) (3,1) (2,2) (1,3) (1,4) (2,3)
                      (3,2) (4,1) ... showing countability of Q.
                      Fixed params: 5x5 grid, 10-step path.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 016 (Cantor), math pillars 1 and 2.
"""

from manim import (
    LEFT,
    RIGHT,
    UP,
    Arrow,
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


class BijectionDiagram(Scene):
    """One-to-one correspondence visualizations. Mode-branching scene.

    Modes:
        natural_even (default) - N <-> 2N via n ↔ 2n
        rational_zigzag        - Q+ countability via diagonal enumeration
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "natural_even")

        if mode == "rational_zigzag":
            self.build_rational_zigzag()
        else:
            self.build_natural_even()

    # -------------------------------------------------------------------
    # Mode: natural_even
    # -------------------------------------------------------------------
    def build_natural_even(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("自然数と偶数 ── 同じ大きさ", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)

        left_header = Text("自然数 N", font=FONT, font_size=24, color=ACCENT_CYAN)
        right_header = Text("偶数 2N", font=FONT, font_size=24, color=ACCENT_PINK)
        left_header.move_to([-3.2, 2.45, 0])
        right_header.move_to([3.2, 2.45, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(left_header), FadeIn(right_header), run_time=0.5)

        # 6 rows: 1-6 <-> 2, 4, 6, 8, 10, 12
        row_y_start = 1.8
        row_spacing = 0.45

        left_items = []
        right_items = []
        arrows = []

        for idx in range(6):
            n = idx + 1  # 1-based naturals
            y = row_y_start - idx * row_spacing
            n_label = MathTex(str(n), font_size=32, color=TEXT_WHITE)
            m_label = MathTex(str(2 * n), font_size=32, color=TEXT_WHITE)
            n_label.move_to([-3.2, y, 0])
            m_label.move_to([3.2, y, 0])
            left_items.append(n_label)
            right_items.append(m_label)

            arrow = Arrow(
                start=n_label.get_right() + RIGHT * 0.15,
                end=m_label.get_left() + LEFT * 0.15,
                color=highlight,
                buff=0.05,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.06,
            )
            arrows.append(arrow)

        ellipsis_y = row_y_start - 6 * row_spacing
        left_dots = MathTex(r"\vdots", font_size=32, color=TEXT_DIM)
        right_dots = MathTex(r"\vdots", font_size=32, color=TEXT_DIM)
        left_dots.move_to([-3.2, ellipsis_y, 0])
        right_dots.move_to([3.2, ellipsis_y, 0])

        for item in left_items + right_items:
            self.play(FadeIn(item), run_time=0.12)
        self.play(FadeIn(left_dots), FadeIn(right_dots), run_time=0.3)

        for arrow in arrows:
            self.play(FadeIn(arrow), run_time=0.18)

        rule_label = MathTex(
            r"n \longleftrightarrow 2n",
            font_size=38,
            color=highlight,
        )
        rule_label.move_to([0, ellipsis_y - 0.9, 0])
        self.play(FadeIn(rule_label), run_time=0.6)

        anim_overhead = 0.5 + 0.5 + 0.12 * 12 + 0.3 + 0.18 * 6 + 0.6
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: rational_zigzag
    # -------------------------------------------------------------------
    def build_rational_zigzag(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("有理数も数え上げられる", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        # 5x5 grid of positive rationals p/q.
        # Fits within y = [-1.1, 1.9] so 5th row stays above subtitle zone (-2.0).
        grid_size = 5
        cell_spacing = 0.75
        origin_x = -cell_spacing * (grid_size - 1) / 2
        origin_y = 1.9

        fractions = {}
        for p in range(1, grid_size + 1):
            for q in range(1, grid_size + 1):
                x = origin_x + (q - 1) * cell_spacing
                y = origin_y - (p - 1) * cell_spacing
                frac = MathTex(
                    rf"\frac{{{p}}}{{{q}}}",
                    font_size=28,
                    color=TEXT_WHITE,
                )
                frac.move_to([x, y, 0])
                fractions[(p, q)] = frac
                self.play(FadeIn(frac), run_time=0.04)

        # Cantor's zigzag path (standard enumeration visiting all p/q).
        # Visit order: upward-right diagonals.
        path = [
            (1, 1),
            (2, 1),
            (1, 2),
            (1, 3),
            (2, 2),
            (3, 1),
            (4, 1),
            (3, 2),
            (2, 3),
            (1, 4),
            (1, 5),
            (2, 4),
            (3, 3),
            (4, 2),
            (5, 1),
        ]

        for step, (p, q) in enumerate(path, start=1):
            frac = fractions.get((p, q))
            if frac is None:
                continue
            # Highlight current fraction
            self.play(frac.animate.set_color(highlight), run_time=0.12)

            # Draw segment from previous to current
            if step >= 2:
                prev_p, prev_q = path[step - 2]
                prev_frac = fractions[(prev_p, prev_q)]
                seg = Line(
                    start=prev_frac.get_center(),
                    end=frac.get_center(),
                    color=highlight,
                    stroke_width=2.5,
                )
                self.play(FadeIn(seg), run_time=0.08)

        number_label = MathTex(
            r"1,\; 2,\; 3,\; 4,\; 5,\; 6,\; \ldots",
            font_size=32,
            color=ACCENT_CYAN,
        )
        number_label.move_to([0, -2.0, 0])
        self.play(FadeIn(number_label), run_time=0.5)

        anim_overhead = 0.5 + 0.04 * 25 + 0.12 * len(path) + 0.08 * (len(path) - 1) + 0.5
        self.wait(max(1.0, duration - anim_overhead))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "natural_even": {"people": [], "years": []},
    "rational_zigzag": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "natural_even": {
        "class": "BijectionDiagram",
        "params": {"mode": "natural_even"},
        "description": "Natural numbers N and evens 2N bijection n <-> 2n",
    },
    "rational_zigzag": {
        "class": "BijectionDiagram",
        "params": {"mode": "rational_zigzag"},
        "description": "Rational numbers Q+ countability via Cantor's zigzag enumeration",
    },
}
