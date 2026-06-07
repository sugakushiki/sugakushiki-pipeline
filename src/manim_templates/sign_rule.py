"""
sign_rule.py - Descartes' rule of signs for 数学史記

Visualizes Descartes' rule of signs from La Géométrie Book III (1637):
the number of positive real roots of a polynomial f(x) is at most the
number of sign changes in its coefficient sequence, and the difference
is always even. Negative roots are found by applying the same rule to f(-x).

Modes:
    simple         - f(x) = x³ - 2x² - x + 2. Coefficients [+1, -2, -1, +2],
                     sign changes at positions 1→2 and 3→4, total 2.
                     Actual positive roots: x=1 and x=2.
                     Difference = 0 (even). Verified.
    negative_roots - Same polynomial, f(-x) = -x³ - 2x² + x + 2.
                     Coefficients [-1, -2, +1, +2], sign change at position 2→3, total 1.
                     Actual negative root: x=-1. Difference = 0 (even). Verified.
    compare        - Three polynomials side by side:
                     (A) x² - 3x + 2 → 2 sign changes → roots 1, 2
                     (B) x³ - 2x² - x + 2 → 2 sign changes → roots 1, 2 (positive), -1
                     (C) x⁴ - 1 → 1 sign change → 1 positive root (x=1)

Duration-aware: reads target duration from _manim_params.json.
Y range: -2.0 to +3.0, title at +3.0, subtitle clearance preserved.

Used by: Episode 012 (Descartes), math pillar 2
"""

from manim import (
    RIGHT,
    UP,
    Arrow,
    CurvedArrow,
    Dot,
    FadeIn,
    MathTex,
    NumberLine,
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


class SignRule(Scene):
    """Descartes' rule of signs — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "simple")
        self._duration = params.get("duration", 30)

        if mode == "negative_roots":
            self._build_negative_roots()
        elif mode == "compare":
            self._build_compare()
        else:
            self._build_simple()

    # ------------------------------------------------------------------
    def _build_simple(self):
        duration = self._duration

        title = Text("デカルトの符号法則", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        sub_parts = VGroup(
            Text("正根の個数", font=FONT, font_size=22, color=TEXT_DIM),
            MathTex(r"\leq", font_size=22, color=TEXT_DIM),
            Text("係数の符号変化の回数", font=FONT, font_size=22, color=TEXT_DIM),
        )
        sub_parts.arrange(RIGHT, buff=0.15)
        sub_parts.move_to([0, 2.35, 0])
        self.play(FadeIn(sub_parts), run_time=0.6)

        # Polynomial with parts indexed for color coding
        # f(x) = x^3 - 2x^2 - x + 2
        poly = MathTex(
            r"f(x) = ",  # 0
            r"+x^3",  # 1 (+)
            r"-2x^2",  # 2 (-)
            r"-x",  # 3 (-)
            r"+2",  # 4 (+)
            font_size=44,
        )
        poly.move_to([0, 1.2, 0])
        # Color sign parts
        poly[0].set_color(TEXT_WHITE)
        poly[1].set_color(ACCENT_GOLD)  # +
        poly[2].set_color(ACCENT_PINK)  # -
        poly[3].set_color(ACCENT_PINK)  # -
        poly[4].set_color(ACCENT_GOLD)  # +

        self.play(FadeIn(poly), run_time=0.8)

        # Coefficient signs row below
        sign_labels = VGroup()
        sign_positions = []
        sign_chars = ["+", "-", "-", "+"]
        sign_colors = [ACCENT_GOLD, ACCENT_PINK, ACCENT_PINK, ACCENT_GOLD]
        for i, (ch, col) in enumerate(zip(sign_chars, sign_colors, strict=False)):
            x = -2.4 + i * 1.6
            y = 0.2
            lbl = MathTex(ch, font_size=52, color=col)
            lbl.move_to([x, y, 0])
            sign_labels.add(lbl)
            sign_positions.append([x, y, 0])
        self.play(FadeIn(sign_labels), run_time=0.6)

        # Highlight sign changes with curved arrows
        # Change 1: index 0 (+) -> index 1 (-)
        # Change 2: index 2 (-) -> index 3 (+)
        change_arrows = VGroup()
        change_pairs = [(0, 1), (2, 3)]
        for a, b in change_pairs:
            start = [sign_positions[a][0] + 0.35, sign_positions[a][1] + 0.45, 0]
            end = [sign_positions[b][0] - 0.35, sign_positions[b][1] + 0.45, 0]
            arrow = CurvedArrow(
                start,
                end,
                color=ACCENT_CYAN,
                tip_length=0.2,
                stroke_width=3,
                angle=-1.0,
            )
            change_arrows.add(arrow)
        self.play(FadeIn(change_arrows), run_time=0.7)

        count_label = Text(
            "符号変化 2回 → 正根は2個以下",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        count_label.move_to([0, -0.6, 0])
        self.play(FadeIn(count_label), run_time=0.6)

        # Number line with actual roots
        nline = NumberLine(
            x_range=[-2, 3, 1],
            length=6,
            include_numbers=True,
            numbers_to_include=[-2, -1, 0, 1, 2, 3],
            font_size=22,
            color=TEXT_DIM,
        )
        nline.move_to([0, -1.3, 0])
        self.play(FadeIn(nline), run_time=0.5)

        root_1 = Dot(nline.n2p(1), radius=0.11, color=ACCENT_PINK)
        root_2 = Dot(nline.n2p(2), radius=0.11, color=ACCENT_PINK)

        self.play(FadeIn(root_1), FadeIn(root_2), run_time=0.6)

        roots_label = Text(
            "実根 x=1, x=2（正根2個）",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        roots_label.move_to([0, -1.9, 0])

        self.play(FadeIn(roots_label), run_time=0.5)

        anim_time = 0.6 + 0.6 + 0.8 + 0.6 + 0.7 + 0.6 + 0.5 + 0.6 + 0.5
        self.wait(max(1.0, duration - anim_time))

    # ------------------------------------------------------------------
    def _build_negative_roots(self):
        duration = self._duration

        title = Text("負根は f(-x) で調べる", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Original polynomial
        poly = MathTex(
            r"f(x) = x^3 - 2x^2 - x + 2",
            font_size=38,
            color=TEXT_WHITE,
        )
        poly.move_to([0, 2.25, 0])
        self.play(FadeIn(poly), run_time=0.6)

        arrow = Arrow(
            start=[0, 1.85, 0],
            end=[0, 1.35, 0],
            color=TEXT_DIM,
            buff=0.05,
            stroke_width=3,
        )
        sub_label = Text("x → -x を代入", font=FONT, font_size=20, color=TEXT_DIM)
        sub_label.next_to(arrow, RIGHT, buff=0.25)
        self.play(FadeIn(arrow), FadeIn(sub_label), run_time=0.5)

        # f(-x) with sign-colored parts
        poly_neg = MathTex(
            r"f(-x) = ",  # 0
            r"-x^3",  # 1 (-)
            r"-2x^2",  # 2 (-)
            r"+x",  # 3 (+)
            r"+2",  # 4 (+)
            font_size=40,
        )
        poly_neg.move_to([0, 0.9, 0])
        poly_neg[0].set_color(TEXT_WHITE)
        poly_neg[1].set_color(ACCENT_PINK)
        poly_neg[2].set_color(ACCENT_PINK)
        poly_neg[3].set_color(ACCENT_GOLD)
        poly_neg[4].set_color(ACCENT_GOLD)
        self.play(FadeIn(poly_neg), run_time=0.7)

        # Sign sequence row
        sign_chars = ["-", "-", "+", "+"]
        sign_colors = [ACCENT_PINK, ACCENT_PINK, ACCENT_GOLD, ACCENT_GOLD]
        sign_positions = []
        sign_group = VGroup()
        for i, (ch, col) in enumerate(zip(sign_chars, sign_colors, strict=False)):
            x = -2.4 + i * 1.6
            y = 0.0
            lbl = MathTex(ch, font_size=52, color=col)
            lbl.move_to([x, y, 0])
            sign_group.add(lbl)
            sign_positions.append([x, y, 0])
        self.play(FadeIn(sign_group), run_time=0.5)

        # One sign change: index 1 -> 2
        start = [sign_positions[1][0] + 0.35, sign_positions[1][1] + 0.45, 0]
        end = [sign_positions[2][0] - 0.35, sign_positions[2][1] + 0.45, 0]
        change_arrow = CurvedArrow(
            start,
            end,
            color=ACCENT_CYAN,
            tip_length=0.2,
            stroke_width=3,
            angle=-1.0,
        )
        self.play(FadeIn(change_arrow), run_time=0.6)

        conclusion = Text(
            "符号変化 1回 → 負根は1個（x=-1）",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        conclusion.move_to([0, -1.0, 0])
        self.play(FadeIn(conclusion), run_time=0.6)

        # Number line with the negative root
        nline = NumberLine(
            x_range=[-2, 3, 1],
            length=6,
            include_numbers=True,
            numbers_to_include=[-2, -1, 0, 1, 2, 3],
            font_size=22,
            color=TEXT_DIM,
        )
        nline.move_to([0, -1.8, 0])
        self.play(FadeIn(nline), run_time=0.5)

        root_neg1 = Dot(nline.n2p(-1), radius=0.12, color=ACCENT_PINK)
        self.play(FadeIn(root_neg1), run_time=0.5)

        anim_time = 0.6 + 0.6 + 0.5 + 0.7 + 0.5 + 0.6 + 0.6 + 0.5 + 0.5
        self.wait(max(1.0, duration - anim_time))

    # ------------------------------------------------------------------
    def _build_compare(self):
        duration = self._duration

        title = Text("符号法則の3つの例", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        rows = [
            {
                "poly": r"f(x) = x^2 - 3x + 2",
                "signs": ["+", "-", "+"],
                "changes": 2,
                "roots": "正根: x=1, x=2",
            },
            {
                "poly": r"f(x) = x^3 - 2x^2 - x + 2",
                "signs": ["+", "-", "-", "+"],
                "changes": 2,
                "roots": "正根: x=1, x=2",
            },
            {
                "poly": r"f(x) = x^4 - 1",
                "signs": ["+", "-"],
                "changes": 1,
                "roots": "正根: x=1",
            },
        ]

        y_positions = [1.6, 0.1, -1.4]
        for row, y in zip(rows, y_positions, strict=False):
            # Polynomial
            p = MathTex(row["poly"], font_size=30, color=TEXT_WHITE)
            p.move_to([-3.4, y, 0])

            # Changes count
            c = Text(
                f"符号変化 {row['changes']}回",
                font=FONT,
                font_size=20,
                color=ACCENT_CYAN,
            )
            c.move_to([1.4, y, 0])

            # Roots
            r = Text(
                row["roots"],
                font=FONT,
                font_size=20,
                color=ACCENT_PINK,
            )
            r.move_to([4.3, y, 0])

            self.play(FadeIn(p), run_time=0.45)
            self.play(FadeIn(c), FadeIn(r), run_time=0.55)

        # Bottom note
        note = Text(
            "正根の個数 ≤ 符号変化の回数（差は偶数）",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.move_to([0, -2.2, 0])
        # keep above -2.0 clearance: shift up
        note.move_to([0, -2.0, 0])
        note.shift(UP * 0.05)
        self.play(FadeIn(note), run_time=0.6)

        anim_time = 0.6 + 3 * (0.45 + 0.55) + 0.6
        self.wait(max(1.0, duration - anim_time))


# Factual-claim metadata (read by qa_manim_consistency.py). All modes share the
# title "デカルトの符号法則".
LINT_FACTUAL_CLAIMS = {
    "simple": {"people": [["デカルト", "Descartes"]], "years": []},
    "negative_roots": {"people": [["デカルト", "Descartes"]], "years": []},
    "compare": {"people": [["デカルト", "Descartes"]], "years": []},
}

# ---------------------------------------------------------------------------
SCENES = {
    "simple": SignRule,
    "negative_roots": SignRule,
    "compare": SignRule,
}
