"""
euclid_proof_jewels.py - Two jewels of Euclid's deductive method (数学史記)

Episode 052 (Euclid). Two intuition-level showcases of what the deductive method
produces: the infinitude of primes (Book IX.20) shown CONSTRUCTIVELY -- not as a
proof by contradiction, but as "give me any finite list of primes and I will
build one you missed" -- and the Euclidean algorithm (Book VII) for the greatest
common divisor, shown as repeatedly cutting the largest possible square from a
rectangle.

Modes:
    primes (default)
        Book IX.20. From any finite list p_1..p_n, form N = p_1*...*p_n + 1.
        N leaves remainder 1 under every p_i, so no p_i divides it; hence N is
        itself a new prime OR is divisible by a prime not in the list -- either
        way a prime outside the list is CONSTRUCTED. No "assume finitely many"
        contradiction framing. Concrete example: 2*3*5 + 1 = 31 (a new prime).
        Fixed params: symbolic p_1..p_n; N = product + 1; 5 reveal steps.
    gcd
        Book VII: the Euclidean algorithm as square tiling. Rectangle 8 x 6 ->
        cut one 6x6 square, leaving 2x6 -> cut three 2x2 squares -> done. The side
        of the final repeating square (2) is the greatest common divisor.
        Fixed params: unit u=0.42; rectangle 8u x 6u centred at (0,0.2); one 6x6
        square (cyan) + three 2x2 squares (gold); gcd square side = 2.

All Text uses FONT (BIZ UDMincho). MathTex holds only ASCII (numbers / symbols),
no Japanese. Y range: about -1.75 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    Create,
    FadeIn,
    Indicate,
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


class EuclidProofJewels(Scene):
    """Two jewels of Euclid's deductive method -- primes and the algorithm."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "primes")
        duration = float(params.get("duration", 28))
        if mode == "gcd":
            self._build_gcd(duration)
        else:
            self._build_primes(duration)

    # ---------------------------------------------------------------------- primes
    def _build_primes(self, duration):
        title = Text(
            "素数は尽きない ── 抜けた素数を、作ってみせる",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        sub = Text(
            "『原論』第九巻・命題20（背理法ではなく、構成的に）",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        sub.move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        s1 = Text("どんな有限の素数のリストでも", font=FONT, font_size=24, color=TEXT_WHITE)
        m1 = MathTex(r"p_1,\; p_2,\; \ldots,\; p_n", font_size=34, color=ACCENT_CYAN)
        g1 = VGroup(s1, m1).arrange(DOWN, buff=0.2).move_to([0, 1.5, 0])

        s2 = Text("全部を掛けて 1 を足す", font=FONT, font_size=24, color=TEXT_WHITE)
        m2 = MathTex(
            r"N = p_1 \times p_2 \times \cdots \times p_n + 1",
            font_size=32,
            color=ACCENT_CYAN,
        )
        g2 = VGroup(s2, m2).arrange(DOWN, buff=0.2).move_to([0, 0.25, 0])

        s3 = Text(
            "N はどの素数で割っても 1 余る ── どれでも割り切れない",
            font=FONT,
            font_size=23,
            color=TEXT_WHITE,
        )
        s3.move_to([0, -0.8, 0])

        s4 = Text(
            "だから N 自身が新しい素数か、リストにない素数で割り切れる",
            font=FONT,
            font_size=23,
            color=TEXT_WHITE,
        )
        s4.move_to([0, -1.35, 0])

        ex = MathTex(r"2 \times 3 \times 5 + 1 = 31", font_size=30, color=ACCENT_PINK)
        ex_lab = Text("（新しい素数）", font=FONT, font_size=18, color=ACCENT_PINK)
        gex = VGroup(ex, ex_lab).arrange(RIGHT, buff=0.2).move_to([0, -1.9, 0])

        blocks = [g1, g2, s3, s4, gex]
        used = 0.6 + 0.5
        coda = 3.0
        emphasize = 1.0
        body = max(3.0, duration - used - emphasize - coda)
        per = body / max(1, len(blocks))
        for i, blk in enumerate(blocks):
            self.play(FadeIn(blk), run_time=min(per, 1.1))
            if i < len(blocks) - 1:
                self.wait(max(0.3, per - 1.1))
        self.play(Indicate(gex, color=ACCENT_PINK, scale_factor=1.08), run_time=emphasize)
        self.wait(coda)

    # ------------------------------------------------------------------------- gcd
    def _build_gcd(self, duration):
        title = Text(
            "ユークリッドの互除法 ── 最大公約数を、正方形で",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        sub = Text(
            "大きい方から、最大の正方形を切り取り続ける",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        sub.move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        u = 0.42
        w, h = 8, 6
        # bottom-left corner so the rectangle is centred at (0, 0.5)
        cy = 0.5
        bl = np.array([-w * u / 2.0, cy - h * u / 2.0, 0.0])

        def cell(x0, y0, cw, ch, color, opacity):
            r = Rectangle(width=cw * u, height=ch * u, stroke_width=2.5, color=color)
            r.move_to(bl + np.array([(x0 + cw / 2.0) * u, (y0 + ch / 2.0) * u, 0.0]))
            r.set_fill(color, opacity=opacity)
            return r

        outline = Rectangle(width=w * u, height=h * u, color=TEXT_WHITE, stroke_width=3)
        outline.move_to([0, cy, 0])
        dim_w = MathTex(r"8", font_size=28, color=TEXT_WHITE).next_to(outline, DOWN, buff=0.15)
        dim_h = MathTex(r"6", font_size=28, color=TEXT_WHITE).next_to(outline, LEFT, buff=0.15)

        sq_big = cell(0, 0, 6, 6, ACCENT_CYAN, 0.12)  # 6x6 from the left
        big_lab = MathTex(r"6 \times 6", font_size=24, color=ACCENT_CYAN).move_to(sq_big)

        # remaining 2-wide strip: three 2x2 squares stacked
        sq_s = VGroup(
            cell(6, 0, 2, 2, ACCENT_GOLD, 0.18),
            cell(6, 2, 2, 2, ACCENT_GOLD, 0.18),
            cell(6, 4, 2, 2, ACCENT_GOLD, 0.18),
        )

        gcd_lab = MathTex(r"\gcd(8,6) = 2", font_size=32, color=ACCENT_PINK).move_to([0, -1.5, 0])
        gcd_note = Text(
            "最後にくり返す正方形の一辺が、最大公約数",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        ).move_to([0, -1.9, 0])

        used = 0.6 + 0.5
        coda = 3.0
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(Create(outline), FadeIn(dim_w), FadeIn(dim_h), run_time=per)
        self.play(Create(sq_big), FadeIn(big_lab), run_time=per)
        self.play(Create(sq_s[0]), run_time=per * 0.8)
        self.play(Create(sq_s[1]), Create(sq_s[2]), run_time=per * 0.9)
        self.play(FadeIn(gcd_lab), FadeIn(gcd_note), run_time=per)
        self.play(Indicate(sq_s, color=ACCENT_PINK, scale_factor=1.05), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "primes": {"people": [], "years": []},
    "gcd": {"people": [], "years": []},
}

SCENES = {
    "primes": EuclidProofJewels,
    "gcd": EuclidProofJewels,
}
