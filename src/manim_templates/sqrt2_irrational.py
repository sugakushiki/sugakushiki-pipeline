"""
sqrt2_irrational.py - Proof that the square root of 2 is irrational (数学史記)

Hardy's second example of a beautiful theorem in 'A Mathematician's Apology'.
Proof by contradiction via a parity argument, revealed step by step.

Modes:
    proof - Assume sqrt(2) = p/q in lowest terms; squaring gives p^2 = 2 q^2,
            so p is even (p = 2k); substituting gives q^2 = 2 k^2, so q is even;
            p and q share factor 2, contradicting "lowest terms".
            Fixed params: sqrt(2)=p/q, p^2=2q^2, p=2k, q^2=2k^2, 4 reveal steps.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 035 (Hardy), pillar 2 (irrationality of sqrt(2) as a beautiful proof).
"""

from manim import (
    DOWN,
    RIGHT,
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


class Sqrt2Irrational(Scene):
    """Irrationality of sqrt(2) by contradiction (parity), revealed step by step."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 28)
        _mode = params.get("mode", "proof")
        self.build_proof()

    def build_proof(self):
        duration = self._duration

        title_math = MathTex(r"\sqrt{2}", font_size=40, color=ACCENT_GOLD)
        title_text = Text("は無理数である", font=FONT, font_size=34, color=ACCENT_GOLD)
        title = VGroup(title_math, title_text).arrange(RIGHT, buff=0.15)
        title.move_to([0, 3.05, 0])
        subtitle = Text("背理法 ── 既約分数と仮定する", font=FONT, font_size=24, color=TEXT_DIM)
        subtitle.move_to([0, 2.4, 0])

        s1 = Text("既約分数で表せると仮定", font=FONT, font_size=25, color=TEXT_WHITE)
        m1 = MathTex(r"\sqrt{2} = \frac{p}{q}", font_size=34, color=ACCENT_CYAN)
        g1 = VGroup(s1, m1).arrange(DOWN, buff=0.18)
        g1.move_to([0, 1.5, 0])

        m2 = MathTex(r"p^2 = 2q^2", font_size=34, color=ACCENT_CYAN)
        s2 = Text("→ p は偶数, p = 2k", font=FONT, font_size=25, color=TEXT_WHITE)
        g2 = VGroup(m2, s2).arrange(DOWN, buff=0.18)
        g2.move_to([0, 0.35, 0])

        m3 = MathTex(r"q^2 = 2k^2", font_size=34, color=ACCENT_CYAN)
        s3 = Text("→ q も偶数", font=FONT, font_size=25, color=TEXT_WHITE)
        g3 = VGroup(m3, s3).arrange(DOWN, buff=0.18)
        g3.move_to([0, -0.8, 0])

        s4 = Text("p も q も偶数 → 既約に矛盾", font=FONT, font_size=26, color=ACCENT_PINK)
        s4.move_to([0, -1.7, 0])

        blocks = [g1, g2, g3, s4]

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
    "proof": {"people": [], "years": []},
}


SCENES = {
    "proof": {
        "class": "Sqrt2Irrational",
        "params": {"mode": "proof"},
        "description": "Proof that sqrt(2) is irrational, by contradiction (parity), revealed step by step",
    },
}
