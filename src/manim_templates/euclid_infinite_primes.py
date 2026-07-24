"""
euclid_infinite_primes.py - Euclid's proof that primes are infinite (数学史記)

Hardy cites this in 'A Mathematician's Apology' as a model of mathematical
beauty (unexpectedness, inevitability, economy). Proof by contradiction,
revealed step by step.

Modes:
    proof - Assume finitely many primes p_1..p_n; form N = p_1*...*p_n + 1;
            N leaves remainder 1 when divided by any p_i, so a new prime must
            exist -> contradiction. Primes are infinite.
            Fixed params: symbolic p_1..p_n, N = p_1...p_n + 1, 4 reveal steps.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 035 (Hardy), pillar 1 (Euclid's primes as a beautiful proof).
"""

from manim import (
    DOWN,
    FadeIn,
    Indicate,
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


class EuclidInfinitePrimes(Scene):
    """Euclid's infinitude-of-primes proof, revealed step by step."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 28)
        _mode = params.get("mode", "proof")
        self.build_proof()

    def build_proof(self):
        duration = self._duration

        title = Text("素数は無限に存在する", font=FONT, font_size=34, color=ACCENT_GOLD)
        title.move_to([0, 3.1, 0])
        subtitle = Text("ユークリッドの証明 ── 背理法", font=FONT, font_size=24, color=TEXT_DIM)
        subtitle.move_to([0, 2.45, 0])

        s1 = Text("もし素数が有限個だと仮定する", font=FONT, font_size=26, color=TEXT_WHITE)
        m1 = MathTex(r"p_1,\; p_2,\; \ldots,\; p_n", font_size=34, color=ACCENT_CYAN)
        g1 = VGroup(s1, m1).arrange(DOWN, buff=0.2)
        g1.move_to([0, 1.45, 0])

        s2 = Text("すべて掛けて 1 を足す", font=FONT, font_size=26, color=TEXT_WHITE)
        m2 = MathTex(
            r"N = p_1 \times p_2 \times \cdots \times p_n + 1",
            font_size=32,
            color=ACCENT_CYAN,
        )
        g2 = VGroup(s2, m2).arrange(DOWN, buff=0.2)
        g2.move_to([0, 0.15, 0])

        s3 = Text("N はどの素数で割っても 1 余る", font=FONT, font_size=26, color=TEXT_WHITE)
        s3.move_to([0, -1.05, 0])

        s4 = Text("→ 新たな素数が必要。仮定に矛盾", font=FONT, font_size=26, color=ACCENT_PINK)
        s4.move_to([0, -1.75, 0])

        blocks = [g1, g2, s3, s4]

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(subtitle), run_time=0.5)

        fade = 0.7
        coda = 5.0
        emphasize = 1.0
        intro = 0.6 + 0.5
        n = len(blocks)
        gaps = max(1, n - 1)
        slack = max(0.0, duration - intro - n * fade - emphasize - coda)
        step_wait = slack / gaps
        for idx, blk in enumerate(blocks):
            self.play(FadeIn(blk), run_time=fade)
            if idx < n - 1:
                self.wait(max(0.4, step_wait))
        self.play(Indicate(s4, color=ACCENT_PINK), run_time=emphasize)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "proof": {"people": [["ユークリッド", "Euclid"]], "years": []},
}


SCENES = {
    "proof": {
        "class": "EuclidInfinitePrimes",
        "params": {"mode": "proof"},
        "description": "Euclid's proof that primes are infinite, by contradiction, revealed step by step",
    },
}
