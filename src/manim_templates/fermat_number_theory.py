"""
fermat_number_theory.py - Fermat's number theory visualization for 数学史記

Visualizes Fermat's two foundational results in number theory:
1. Fermat's Little Theorem: a^(p-1) ≡ 1 (mod p)
2. Two-square sum theorem (Christmas theorem): primes ≡ 1 (mod 4) = x² + y²

Modes:
    mod_table   - Table showing a^(p-1) mod p for p=7, a=1..6.
                  All results are 1, demonstrating the little theorem.
                  Fixed params: p=7.
    two_squares - Classification of odd primes by remainder mod 4.
                  Primes ≡ 1 (mod 4): expressible as sum of two squares.
                  Primes ≡ 3 (mod 4): never expressible.
                  Fixed params: primes up to 41, 5 concrete decompositions.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 014 (Fermat), math pillar 1
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    FadeIn,
    Line,
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


class FermatNumberTheory(Scene):
    """Fermat's number theory. Mode-branching scene.

    Modes:
        mod_table (default) - a^(p-1) mod p table for p=7
        two_squares         - prime classification by mod 4, two-square sums
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "mod_table")

        if mode == "two_squares":
            self.build_two_squares()
        else:
            self.build_mod_table()

    # -------------------------------------------------------------------
    # Mode: mod_table
    # -------------------------------------------------------------------
    def build_mod_table(self):
        """Table of a^(p-1) mod p for p=7, demonstrating all results = 1.

        Fixed parameters: p=7, a=1,2,3,4,5,6.
        a^6 mod 7: 1^6=1, 2^6=64≡1, 3^6=729≡1, 4^6=4096≡1,
                   5^6=15625≡1, 6^6=46656≡1.
        """
        duration = self._duration
        highlight = self._highlight_color

        p = 7
        a_values = [1, 2, 3, 4, 5, 6]

        # Title
        title = Text("Fermat's Little Theorem", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)

        # Theorem statement
        theorem = MathTex(r"a^{p-1}", r"\equiv", r"1", r"\pmod{p}", font_size=36)
        theorem[0].set_color(ACCENT_CYAN)
        theorem[2].set_color(ACCENT_GOLD)
        theorem.next_to(title, DOWN, buff=0.4)

        # p = 7 label
        p_label_parts = VGroup(
            Text("p = 7", font=FONT, font_size=24, color=ACCENT_PINK),
        )
        p_label_parts.next_to(theorem, DOWN, buff=0.3)

        self.play(FadeIn(title), run_time=0.4)
        self.play(FadeIn(theorem), run_time=0.5)
        self.play(FadeIn(p_label_parts), run_time=0.3)

        # Build table
        # Y 範囲計算: header_y=1.4, cell_h=0.4 → 6行で最下段 y=-1.0（-2.0の字幕クリアランス内）
        cell_w = 1.6
        cell_h = 0.4
        header_y = 1.4
        start_x = -3.5

        # Header row
        headers = ["a", "a^6", "a^6 \\bmod 7"]
        header_texts = []
        for i, h in enumerate(headers):
            x = start_x + i * cell_w + cell_w / 2
            t = MathTex(h, font_size=22, color=ACCENT_GOLD)
            t.move_to([x, header_y, 0])
            header_texts.append(t)

        header_line = Line(
            [start_x, header_y - cell_h / 2, 0],
            [start_x + len(headers) * cell_w, header_y - cell_h / 2, 0],
            color=TEXT_DIM,
            stroke_width=1,
        )

        header_group = VGroup(*header_texts, header_line)
        self.play(FadeIn(header_group), run_time=0.4)

        # Data rows - reveal one by one
        a_pow = [pow(a, p - 1) for a in a_values]
        a_mod = [pow(a, p - 1, p) for a in a_values]

        row_groups = []
        for idx, a in enumerate(a_values):
            y = header_y - cell_h * (idx + 1)
            row = VGroup()

            # a value
            t_a = MathTex(str(a), font_size=22, color=ACCENT_CYAN)
            t_a.move_to([start_x + cell_w / 2, y, 0])
            row.add(t_a)

            # a^6 value
            t_pow = MathTex(str(a_pow[idx]), font_size=22, color=TEXT_WHITE)
            t_pow.move_to([start_x + cell_w + cell_w / 2, y, 0])
            row.add(t_pow)

            # result (always 1)
            t_mod = MathTex(str(a_mod[idx]), font_size=22, color=ACCENT_GOLD)
            t_mod.move_to([start_x + 2 * cell_w + cell_w / 2, y, 0])
            row.add(t_mod)

            row_groups.append(row)

        # Stagger row reveals
        time_per_row = min(0.6, (duration * 0.3) / len(a_values))
        for rg in row_groups:
            self.play(FadeIn(rg), run_time=time_per_row)

        # Highlight: all results are 1
        result_rects = VGroup()
        for idx in range(len(a_values)):
            y = header_y - cell_h * (idx + 1)
            rect = SurroundingRectangle(
                row_groups[idx][2], color=ACCENT_GOLD, buff=0.08, stroke_width=2
            )
            result_rects.add(rect)

        self.play(FadeIn(result_rects), run_time=0.5)

        # Conclusion text (最下段のRow 6 (a=6) は y=-1.0、conclusion は -1.7 で衝突回避)
        conclusion = VGroup(
            Text("すべて余り", font=FONT, font_size=22, color=TEXT_WHITE),
            MathTex("1", font_size=28, color=ACCENT_GOLD),
        )
        conclusion.arrange(RIGHT, buff=0.15)
        conclusion.move_to([2.5, -1.7, 0])
        self.play(FadeIn(conclusion), run_time=0.5)

        # Hold
        self.wait(max(1, duration * 0.15))

    # -------------------------------------------------------------------
    # Mode: two_squares
    # -------------------------------------------------------------------
    def build_two_squares(self):
        """Classify odd primes by mod 4, show two-square decompositions.

        Primes ≡ 1 (mod 4): 5, 13, 17, 29, 37, 41 → can be written as x²+y²
        Primes ≡ 3 (mod 4): 3, 7, 11, 19, 23, 31, 43 → cannot
        Concrete examples: 5=1²+2², 13=2²+3², 17=1²+4², 29=2²+5², 37=1²+6²
        """
        duration = self._duration
        highlight = self._highlight_color

        # Title
        title = Text("Christmas Theorem (1640)", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)

        # Theorem statement
        theorem = MathTex(r"p \equiv 1 \pmod{4}", r"\iff", r"p = x^2 + y^2", font_size=32)
        theorem[0].set_color(ACCENT_CYAN)
        theorem[2].set_color(ACCENT_GOLD)
        theorem.next_to(title, DOWN, buff=0.4)

        self.play(FadeIn(title), run_time=0.4)
        self.play(FadeIn(theorem), run_time=0.5)

        # Two columns: mod 4 ≡ 1 (left) vs mod 4 ≡ 3 (right)
        col_left_x = -3.0
        col_right_x = 1.5
        col_top_y = 0.8

        # Left header
        left_header = MathTex(r"p \equiv 1 \pmod{4}", font_size=22, color=ACCENT_GOLD)
        left_header.move_to([col_left_x + 1.2, col_top_y, 0])

        # Right header
        right_header = MathTex(r"p \equiv 3 \pmod{4}", font_size=22, color=ACCENT_PINK)
        right_header.move_to([col_right_x + 1.2, col_top_y, 0])

        self.play(FadeIn(left_header), FadeIn(right_header), run_time=0.4)

        # Left column: primes ≡ 1 (mod 4) with decomposition
        left_data = [
            (5, "1^2 + 2^2"),
            (13, "2^2 + 3^2"),
            (17, "1^2 + 4^2"),
            (29, "2^2 + 5^2"),
            (37, "1^2 + 6^2"),
        ]

        left_groups = []
        for i, (p, decomp) in enumerate(left_data):
            y = col_top_y - 0.55 * (i + 1)
            prime_t = MathTex(str(p), font_size=22, color=ACCENT_CYAN)
            prime_t.move_to([col_left_x + 0.3, y, 0])
            eq_t = MathTex(f"= {decomp}", font_size=22, color=ACCENT_GOLD)
            eq_t.next_to(prime_t, RIGHT, buff=0.15)
            group = VGroup(prime_t, eq_t)
            left_groups.append(group)

        # Right column: primes ≡ 3 (mod 4) with X mark
        right_primes = [3, 7, 11, 19, 23]
        right_groups = []
        for i, p in enumerate(right_primes):
            y = col_top_y - 0.55 * (i + 1)
            prime_t = MathTex(str(p), font_size=22, color=ACCENT_CYAN)
            prime_t.move_to([col_right_x + 0.3, y, 0])
            x_mark = Text("---", font=FONT, font_size=18, color=TEXT_DIM)
            x_mark.next_to(prime_t, RIGHT, buff=0.3)
            group = VGroup(prime_t, x_mark)
            right_groups.append(group)

        # Reveal rows in parallel
        time_per_row = min(0.5, (duration * 0.3) / max(len(left_data), len(right_primes)))
        for i in range(max(len(left_groups), len(right_groups))):
            anims = []
            if i < len(left_groups):
                anims.append(FadeIn(left_groups[i]))
            if i < len(right_groups):
                anims.append(FadeIn(right_groups[i]))
            self.play(*anims, run_time=time_per_row)

        # Highlight left column
        left_all = VGroup(*left_groups)
        left_rect = SurroundingRectangle(left_all, color=ACCENT_GOLD, buff=0.15, stroke_width=2)

        right_all = VGroup(*right_groups)
        right_rect = SurroundingRectangle(right_all, color=ACCENT_PINK, buff=0.15, stroke_width=2)

        self.play(FadeIn(left_rect), FadeIn(right_rect), run_time=0.4)

        # Hold
        self.wait(max(1, duration * 0.15))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "mod_table": {"people": [["Fermat", "フェルマー"]], "years": []},
    "two_squares": {"people": [], "years": ["1640"]},
}


SCENES = {
    "mod_table": {
        "class": "FermatNumberTheory",
        "params": {"mode": "mod_table"},
        "description": "a^(p-1) mod p table for p=7, all results = 1",
    },
    "two_squares": {
        "class": "FermatNumberTheory",
        "params": {"mode": "two_squares"},
        "description": "Prime classification by mod 4, two-square decompositions",
    },
}
