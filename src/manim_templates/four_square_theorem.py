"""
four_square_theorem.py - Lagrange's four-square theorem (数学史記)

Episode 055 (Joseph-Louis Lagrange). Every natural number is the sum of at most
four squares. Lagrange gave the first complete proof (1770); Bachet conjectured
it, Euler supplied the key identity. This template shows the statement only --
no names, no years on screen.

Modes:
    sums (default)
        Two worked examples built from real square tiles:
        7 = 2^2 + 1^2 + 1^2 + 1^2  and  31 = 5^2 + 2^2 + 1^2 + 1^2.
        Note: some numbers (7, 15, 23, ...) cannot be done in three squares, but
        four always suffice.
        Fixed params: 7 = one 2x2 block + three unit cells; 31 = one 5x5 block +
        one 2x2 block + two unit cells. cell = 0.26.
    grid
        Small integers 1..8, each written as a sum of at most four squares, to
        drive home that four is never exceeded.
        Fixed params: 1=1^2, 2=1^2+1^2, 3=1^2+1^2+1^2, 4=2^2, 5=2^2+1^2,
        6=2^2+1^2+1^2, 7=2^2+1^2+1^2+1^2, 8=2^2+2^2.

All Japanese labels use Text(font=FONT). MathTex holds only ASCII/LaTeX. Y range:
about -1.75 to +3.05. No trailing FadeOut.
"""

from manim import (
    FadeIn,
    MathTex,
    Scene,
    Square,
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
    pace,
)

config.background_color = BG_COLOR


def _grid(rows, cols, color, cell=0.26, center=(0.0, 0.0)):
    """A rows x cols block of unit squares, centered at `center`."""
    g = VGroup()
    for i in range(rows):
        for j in range(cols):
            sq = Square(side_length=cell * 0.9, color=color, stroke_width=1.6, fill_opacity=0.55)
            sq.move_to([j * cell, -i * cell, 0])
            g.add(sq)
    g.move_to([center[0], center[1], 0])
    return g


class FourSquareTheorem(Scene):
    """Every natural number is a sum of at most four squares (tiles + examples)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "sums")
        duration = float(params.get("duration", 24))
        if mode == "grid":
            self._build_grid(duration)
        else:
            self._build_sums(duration)

    def _titles(self, title, subtitle):
        t = Text(title, font=FONT, font_size=27, color=ACCENT_GOLD).move_to([0, 3.0, 0])
        s = Text(subtitle, font=FONT, font_size=18, color=TEXT_DIM).move_to([0, 2.45, 0])
        self.play(FadeIn(t), run_time=0.6)
        self.play(FadeIn(s), run_time=0.5)

    # ---------------------------------------------------------------- sums
    def _build_sums(self, duration):
        self._titles("あらゆる数は、四つの平方の和", "どんな自然数も、たかだか四つの平方数で書ける")

        cell = 0.26
        # 7 = 2^2 + 1^2 + 1^2 + 1^2
        t7_big = _grid(2, 2, ACCENT_GOLD, cell, center=(-4.25, 0.62))
        t7_u1 = _grid(1, 1, ACCENT_CYAN, cell, center=(-3.45, 0.75))
        t7_u2 = _grid(1, 1, ACCENT_CYAN, cell, center=(-3.45, 0.49))
        t7_u3 = _grid(1, 1, ACCENT_CYAN, cell, center=(-3.19, 0.62))
        tiles7 = VGroup(t7_big, t7_u1, t7_u2, t7_u3)
        eq7 = MathTex(r"7 = 2^2 + 1^2 + 1^2 + 1^2", font_size=26, color=TEXT_WHITE).move_to(
            [-3.5, -0.5, 0]
        )

        # 31 = 5^2 + 2^2 + 1^2 + 1^2
        t31_big = _grid(5, 5, ACCENT_GOLD, cell, center=(1.75, 0.55))
        t31_2 = _grid(2, 2, ACCENT_CYAN, cell, center=(3.05, 0.85))
        t31_u1 = _grid(1, 1, ACCENT_PINK, cell, center=(2.92, 0.3))
        t31_u2 = _grid(1, 1, ACCENT_PINK, cell, center=(3.18, 0.3))
        tiles31 = VGroup(t31_big, t31_2, t31_u1, t31_u2)
        eq31 = MathTex(r"31 = 5^2 + 2^2 + 1^2 + 1^2", font_size=26, color=TEXT_WHITE).move_to(
            [2.25, -0.5, 0]
        )

        note = Text(
            "三つでは足りない数があるのに、四つなら、必ず足りる",
            font=FONT,
            font_size=19,
            color=ACCENT_PINK,
        ).move_to([0, -1.45, 0])

        coda = 3.0
        rt = pace(duration, [1.0, 0.7, 1.0, 0.7, 0.9], intro=1.1, coda=coda)
        self.play(FadeIn(tiles7), run_time=rt[0])
        self.play(FadeIn(eq7), run_time=rt[1])
        self.play(FadeIn(tiles31), run_time=rt[2])
        self.play(FadeIn(eq31), run_time=rt[3])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(coda)

    # ---------------------------------------------------------------- grid
    def _build_grid(self, duration):
        self._titles(
            "四つを超えることは、決してない", "小さな数から確かめる ── どれも四つ以下の平方で"
        )

        rows = [
            r"1 = 1^2",
            r"2 = 1^2 + 1^2",
            r"3 = 1^2 + 1^2 + 1^2",
            r"4 = 2^2",
            r"5 = 2^2 + 1^2",
            r"6 = 2^2 + 1^2 + 1^2",
            r"7 = 2^2 + 1^2 + 1^2 + 1^2",
            r"8 = 2^2 + 2^2",
        ]
        ys = [1.35, 0.6, -0.15, -0.9]
        eqs = []
        for k, s in enumerate(rows):
            col = k // 4
            row = k % 4
            x = -2.6 if col == 0 else 2.4
            color = ACCENT_GOLD if s.count("+") == 3 else TEXT_WHITE
            eqs.append(MathTex(s, font_size=26, color=color).move_to([x, ys[row], 0]))
        note = Text("四つで、いつも足りる", font=FONT, font_size=20, color=ACCENT_GOLD).move_to(
            [0, -1.6, 0]
        )

        coda = 3.0
        rt = pace(duration, [0.6] * len(eqs) + [0.9], intro=1.1, coda=coda)
        for i, eq in enumerate(eqs):
            self.play(FadeIn(eq), run_time=rt[i])
        self.play(FadeIn(note), run_time=rt[-1])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "sums": {"people": [], "years": []},
    "grid": {"people": [], "years": []},
}

SCENES = {
    "sums": FourSquareTheorem,
    "grid": FourSquareTheorem,
}
