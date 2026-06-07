"""
euler_product.py - Euler's 1737 Euler product for 数学史記

Visualizes ζ(s) = Σ 1/n^s = Π_p (1 − p^(−s))^(−1) and its consequence
── Euler's analytic proof of the infinitude of primes (1737).

Modes:
    expansion  - The identity Σ 1/n^s = Π_p (1-p^-s)^-1 with the
                 product written out over primes p = 2,3,5,7,11.
                 Fixed params: first 5 primes.
    unfold     - Unfold each factor as a geometric series
                 (1-1/p^s)^-1 = 1 + 1/p^s + 1/p^(2s) + ... and
                 show how unique factorization gives 1/n^s for
                 every n. Highlight the example 1/6^s = (1/2^s)(1/3^s).
                 Fixed params: expand p=2, p=3 factors; highlight n=6.
    divergence - s=1 case: the harmonic series Σ 1/n diverges, so
                 Π (1-1/p)^-1 diverges, so primes must be infinite.
                 Fixed params: illustrate harmonic divergence.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 018 (Euler analysis), math pillar 2.
"""

from manim import (
    RIGHT,
    FadeIn,
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


class EulerProduct(Scene):
    """Euler product ζ(s) = Π_p (1-p^-s)^-1. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "expansion")

        if mode == "unfold":
            self.build_unfold()
        elif mode == "divergence":
            self.build_divergence()
        else:
            self.build_expansion()

    # -------------------------------------------------------------------
    # Mode: expansion
    # -------------------------------------------------------------------
    def build_expansion(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:        y = +3.15
        # identity:     y = +1.85  ζ(s) = Σ 1/n^s = Π_p (1-1/p^s)^-1
        # expansion:    y = +0.25  = (1-1/2^s)^-1 · (1-1/3^s)^-1 · ... · ···
        # prime_note:   y = -0.80  "p は全ての素数を走る"
        # conclusion:   y = -1.65

        title = Text(
            "オイラー積 ── 無限級数と素数を結ぶ恒等式", font=FONT, font_size=24, color=TEXT_DIM
        )
        title.move_to([0, 3.15, 0])

        # Combined fundamental identity on one line
        identity = MathTex(
            r"\zeta(s)",
            r"=",
            r"\sum_{n=1}^{\infty} \frac{1}{n^s}",
            r"=",
            r"\prod_{p \ \text{prime}}",
            r"\left(1 - \frac{1}{p^s}\right)^{-1}",
            font_size=28,
        )
        identity[0].set_color(ACCENT_CYAN)
        identity[2].set_color(ACCENT_PINK)
        identity[5].set_color(highlight)
        identity.move_to([0, 1.85, 0])

        expansion = MathTex(
            r"=",
            r"\left(1 - \tfrac{1}{2^s}\right)^{-1}",
            r"\left(1 - \tfrac{1}{3^s}\right)^{-1}",
            r"\left(1 - \tfrac{1}{5^s}\right)^{-1}",
            r"\left(1 - \tfrac{1}{7^s}\right)^{-1}",
            r"\left(1 - \tfrac{1}{11^s}\right)^{-1}",
            r"\cdots",
            font_size=24,
        )
        expansion.set_color(ACCENT_GOLD)
        expansion[0].set_color(TEXT_WHITE)
        expansion[6].set_color(TEXT_DIM)
        expansion.move_to([0, 0.25, 0])

        prime_note = Text(
            "p は全ての素数 (2, 3, 5, 7, 11, ...) を走る", font=FONT, font_size=22, color=TEXT_DIM
        )
        prime_note.move_to([0, -0.90, 0])

        conclusion = Text(
            "解析と数論が一つの式で結ばれた", font=FONT, font_size=26, color=ACCENT_GOLD
        )
        conclusion.move_to([0, -1.65, 0])

        # Animation
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(identity), run_time=1.0)
        self.wait(0.7)
        self.play(FadeIn(expansion), run_time=1.0)
        self.wait(0.7)
        self.play(FadeIn(prime_note), run_time=0.5)
        self.wait(0.4)
        self.play(FadeIn(conclusion), run_time=0.7)

        anim_overhead = 0.5 + 1.0 + 0.7 + 1.0 + 0.7 + 0.5 + 0.4 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: unfold
    # -------------------------------------------------------------------
    def build_unfold(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:        y = +3.15
        # geom_series:  y = +2.25   (1-x)^-1 = 1 + x + x^2 + ...
        # factor_p2:    y = +1.20   (1-1/2^s)^-1 = 1 + 1/2^s + 1/4^s + ...
        # factor_p3:    y = +0.30   (1-1/3^s)^-1 = 1 + 1/3^s + 1/9^s + ...
        # example:      y = -0.80   1/6^s = (1/2^s) · (1/3^s)
        # conclusion:   y = -1.70

        title = Text(
            "素因数分解の一意性で Π が Σ に変わる", font=FONT, font_size=24, color=TEXT_DIM
        )
        title.move_to([0, 3.15, 0])

        geom_series = MathTex(
            r"\frac{1}{1-x}",
            r"=",
            r"1 + x + x^2 + x^3 + \cdots",
            font_size=28,
        )
        geom_series[0].set_color(ACCENT_GOLD)
        geom_series.move_to([0, 2.25, 0])

        # p=2 factor expansion
        factor_p2 = MathTex(
            r"\left(1 - \frac{1}{2^s}\right)^{-1}",
            r"=",
            r"1 + \frac{1}{2^s} + \frac{1}{4^s} + \frac{1}{8^s} + \cdots",
            font_size=26,
        )
        factor_p2[0].set_color(ACCENT_CYAN)
        factor_p2[2].set_color(ACCENT_PINK)
        factor_p2.move_to([0, 1.15, 0])

        # p=3 factor expansion
        factor_p3 = MathTex(
            r"\left(1 - \frac{1}{3^s}\right)^{-1}",
            r"=",
            r"1 + \frac{1}{3^s} + \frac{1}{9^s} + \frac{1}{27^s} + \cdots",
            font_size=26,
        )
        factor_p3[0].set_color(ACCENT_CYAN)
        factor_p3[2].set_color(ACCENT_GOLD)
        factor_p3.move_to([0, 0.25, 0])

        # Example showing how 1/6^s emerges
        example = MathTex(
            r"\frac{1}{2^s}",
            r"\cdot",
            r"\frac{1}{3^s}",
            r"=",
            r"\frac{1}{6^s}",
            font_size=32,
        )
        example[0].set_color(ACCENT_PINK)
        example[2].set_color(ACCENT_GOLD)
        example[4].set_color(highlight)
        example.move_to([0, -0.80, 0])

        conclusion = Text(
            "全ての自然数 n が、素因数分解で過不足なく現れる",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        conclusion.move_to([0, -1.70, 0])

        # Animation
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(geom_series), run_time=0.8)
        self.wait(0.5)
        self.play(FadeIn(factor_p2), run_time=0.8)
        self.wait(0.4)
        self.play(FadeIn(factor_p3), run_time=0.8)
        self.wait(0.5)
        self.play(FadeIn(example), run_time=0.9)
        box = SurroundingRectangle(example[4], color=highlight, buff=0.08)
        self.play(FadeIn(box), run_time=0.4)
        self.wait(0.5)
        self.play(FadeIn(conclusion), run_time=0.7)

        anim_overhead = 0.5 + 0.8 + 0.5 + 0.8 + 0.4 + 0.8 + 0.5 + 0.9 + 0.4 + 0.5 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: divergence
    # -------------------------------------------------------------------
    def build_divergence(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan (simplified 4-step flow)
        # title:           y = +3.15
        # substituted:     y = +2.15   Σ 1/n = Π (1-1/p)^-1
        # step1:           y = +0.95   左辺: 1 + 1/2 + 1/3 + ... → ∞
        # step2:           y = -0.20   右辺も発散するしかない
        # step3:           y = -1.05   素数が有限なら右辺は有限 → 矛盾
        # conclusion:      y = -1.80   ∴ 素数は無限にある

        title = Text(
            "s = 1 を代入すると ── 素数が無限にある解析的証明",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        title.move_to([0, 3.15, 0])

        substituted = MathTex(
            r"\sum_{n=1}^{\infty} \frac{1}{n}",
            r"=",
            r"\prod_{p \ \text{prime}}",
            r"\left(1 - \frac{1}{p}\right)^{-1}",
            font_size=30,
        )
        substituted[0].set_color(ACCENT_PINK)
        substituted[3].set_color(ACCENT_CYAN)
        substituted.move_to([0, 2.15, 0])

        # Step 1: harmonic series diverges
        step1_label = Text("左辺（調和級数）:", font=FONT, font_size=22, color=ACCENT_PINK)
        step1_expr = MathTex(
            r"1 + \tfrac{1}{2} + \tfrac{1}{3} + \tfrac{1}{4} + \cdots",
            r"\ \to \ ",
            r"\infty",
            font_size=26,
        )
        step1_expr[2].set_color(highlight)
        step1_group = VGroup(step1_label, step1_expr).arrange(RIGHT, buff=0.3)
        step1_group.move_to([0, 0.95, 0])

        # Step 2: therefore product diverges
        step2 = Text(
            "→ したがって右辺の無限積も発散するしかない", font=FONT, font_size=24, color=TEXT_WHITE
        )
        step2.move_to([0, -0.20, 0])

        # Step 3: if primes finite, contradiction
        step3 = Text(
            "もし素数が有限なら積は有限値 ── これは矛盾", font=FONT, font_size=24, color=ACCENT_CYAN
        )
        step3.move_to([0, -0.95, 0])

        # Conclusion (safe zone: bottom >= -2.0)
        conclusion = Text(
            "したがって、素数は無限にある", font=FONT, font_size=26, color=ACCENT_GOLD
        )
        conclusion.move_to([0, -1.65, 0])

        # Animation
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(substituted), run_time=0.9)
        self.wait(0.6)
        self.play(FadeIn(step1_group), run_time=0.9)
        self.wait(0.6)
        self.play(FadeIn(step2), run_time=0.7)
        self.wait(0.5)
        self.play(FadeIn(step3), run_time=0.7)
        self.wait(0.5)
        self.play(FadeIn(conclusion), run_time=0.8)
        box = SurroundingRectangle(conclusion, color=ACCENT_GOLD, buff=0.12)
        self.play(FadeIn(box), run_time=0.4)

        anim_overhead = 0.5 + 0.9 + 0.6 + 0.9 + 0.6 + 0.7 + 0.5 + 0.7 + 0.5 + 0.8 + 0.4
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "expansion": {"people": [["オイラー", "Euler"]], "years": []},
    "unfold": {"people": [], "years": []},
    "divergence": {"people": [], "years": []},
}


SCENES = {
    "expansion": {
        "class": "EulerProduct",
        "params": {"mode": "expansion"},
        "description": "ζ(s) = Σ 1/n^s = Π_p (1-1/p^s)^-1 identity with 5 prime factors",
    },
    "unfold": {
        "class": "EulerProduct",
        "params": {"mode": "unfold"},
        "description": "Geometric expansion of each factor; 1/6^s = (1/2^s)(1/3^s) example",
    },
    "divergence": {
        "class": "EulerProduct",
        "params": {"mode": "divergence"},
        "description": "s=1 case: harmonic divergence → infinitely many primes (Euler 1737)",
    },
}
