"""
ideal_factorization.py - Unique factorization breaks, and ideals restore it (数学史記)

Episode 053 (Richard Dedekind). Dedekind's second jewel, shown at intuition level.
In ordinary integers every number factors into primes in just one way (6 = 2*3).
But in the world of algebraic integers Z[sqrt(-5)] this backbone snaps: 6 factors
two different ways, 6 = 2*3 = (1+sqrt(-5))(1-sqrt(-5)), and 2, 3, 1 +/- sqrt(-5)
are all irreducible. Dedekind restored the uniqueness not at the level of NUMBERS
but at the level of SETS -- ideals -- where the decomposition into prime ideals is
again unique. The unifying idea (shared with the Dedekind cut): capture an object
as a SET that has its essential property.

Modes:
    crisis (default)
        6 = 2*3 in the ordinary integers (unique), then in Z[sqrt(-5)] the second
        factorization 6 = (1+sqrt(-5))(1-sqrt(-5)); check (1+s)(1-s)=1-(-5)=6; note
        2,3,1 +/- sqrt(-5) are irreducible; uniqueness of prime factorization fails.
        Fixed params: single number 6; two factorizations; no people/years.
    restore
        The two number-factorizations of 6 both flow into ONE prime-ideal
        decomposition (unique). Numbers factor two ways, but the ideal factors one
        way. Ties back to the cut: an object captured as a SET.
        Fixed params: two source boxes -> one target box; no explicit exponents.

All Text uses FONT (BIZ UDMincho). MathTex holds only ASCII (numbers / symbols),
no Japanese. Y range: about -1.85 to +3.05. No trailing FadeOut.
"""

from manim import (
    Arrow,
    Create,
    FadeIn,
    FadeOut,
    Indicate,
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
    pace,
)

config.background_color = BG_COLOR


class IdealFactorization(Scene):
    """Unique factorization breaks in Z[sqrt(-5)]; ideals restore it."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "crisis")
        duration = float(params.get("duration", 26))
        if mode == "restore":
            self._build_restore(duration)
        else:
            self._build_crisis(duration)

    # ------------------------------------------------------------------- crisis
    def _build_crisis(self, duration):
        title = Text(
            "素因数分解の一意性が、壊れる世界",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "整数を √-5 の世界まで広げると、算術の背骨が折れる",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        m1 = MathTex(r"6 = 2 \times 3", font_size=40, color=ACCENT_CYAN).move_to([0, 1.4, 0])
        note1 = Text(
            "ふつうの整数では、素因数分解はただ一通り",
            font=FONT,
            font_size=21,
            color=TEXT_WHITE,
        ).move_to([0, 0.82, 0])

        world = Text(
            "── ところが、√-5 を含む世界（代数的整数）では ──",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        ).move_to([0, 0.82, 0])
        m2 = MathTex(
            r"6 = (1+\sqrt{-5})(1-\sqrt{-5})",
            font_size=38,
            color=ACCENT_GOLD,
        ).move_to([0, 0.1, 0])
        check = MathTex(
            r"(1+\sqrt{-5})(1-\sqrt{-5}) = 1-(-5) = 6",
            font_size=28,
            color=TEXT_DIM,
        ).move_to([0, -0.6, 0])
        irr = Text(
            "2・3・1±√-5 は、どれもこれ以上分解できない（既約）",
            font=FONT,
            font_size=21,
            color=TEXT_WHITE,
        ).move_to([0, -1.2, 0])
        msg = Text(
            "なのに分解が二通り ── 素因数分解の一意性が壊れる",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        ).move_to([0, -1.82, 0])

        # pace(): denominator = sum of weights, so the pink conclusion + coda are NOT
        # truncated (a hand-typed /6.0 undercounted the weights -> overrun -> mp4 clipped).
        coda = 4.5
        rt = pace(
            duration, [1.0, 1.0, 0.4, 0.7, 1.0, 0.9, 1.0, 1.0, 0.7], intro=0.6 + 0.5, coda=coda
        )
        self.play(FadeIn(m1), run_time=rt[0])
        self.play(FadeIn(note1), run_time=rt[1])
        self.wait(rt[2])
        self.play(FadeOut(note1), FadeIn(world), run_time=rt[3])
        self.play(FadeIn(m2), run_time=rt[4])
        self.play(FadeIn(check), run_time=rt[5])
        self.play(FadeIn(irr), run_time=rt[6])
        self.play(FadeIn(msg), run_time=rt[7])
        self.play(Indicate(msg, color=ACCENT_PINK, scale_factor=1.04), run_time=rt[8])
        self.wait(coda)

    # ------------------------------------------------------------------ restore
    def _build_restore(self, duration):
        title = Text(
            "イデアル ── 集合で、一意性を取り戻す",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "数の分解は二通りでも、集合（イデアル）の分解は一通り",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        f1 = MathTex(r"6 = 2 \times 3", font_size=30, color=ACCENT_CYAN).move_to([-3.4, 1.4, 0])
        box1 = SurroundingRectangle(f1, color=ACCENT_CYAN, buff=0.22, corner_radius=0.12)
        f2 = MathTex(r"6 = (1+\sqrt{-5})(1-\sqrt{-5})", font_size=26, color=ACCENT_GOLD).move_to(
            [2.3, 1.4, 0]
        )
        box2 = SurroundingRectangle(f2, color=ACCENT_GOLD, buff=0.22, corner_radius=0.12)

        two = Text(
            "数の世界では、分解は二通り",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        ).move_to([0, 0.5, 0])

        center = Text(
            "イデアル（倍数の集合）で見れば、素イデアルの積は、ただ一通り",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        ).move_to([0, -0.75, 0])
        cbox = SurroundingRectangle(center, color=ACCENT_PINK, buff=0.22, corner_radius=0.12)

        arr1 = Arrow(
            box1.get_bottom(),
            [-1.6, cbox.get_top()[1], 0],
            buff=0.12,
            color=TEXT_DIM,
            stroke_width=4,
        )
        arr2 = Arrow(
            box2.get_bottom(),
            [1.6, cbox.get_top()[1], 0],
            buff=0.12,
            color=TEXT_DIM,
            stroke_width=4,
        )

        msg = Text(
            "切断も、イデアルも ── 対象を《集合》として捉える",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        ).move_to([0, -1.82, 0])

        # pace(): denominator = sum of weights, preserving the coda hold.
        coda = 4.5
        rt = pace(duration, [1.0, 0.8, 1.0, 1.0, 1.0, 0.8], intro=0.6 + 0.5, coda=coda)
        self.play(Create(box1), FadeIn(f1), Create(box2), FadeIn(f2), run_time=rt[0])
        self.play(FadeIn(two), run_time=rt[1])
        self.play(Create(arr1), Create(arr2), run_time=rt[2])
        self.play(Create(cbox), FadeIn(center), run_time=rt[3])
        self.play(FadeIn(msg), run_time=rt[4])
        self.play(Indicate(msg, color=ACCENT_GOLD, scale_factor=1.04), run_time=rt[5])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "crisis": {"people": [], "years": []},
    "restore": {"people": [], "years": []},
}

SCENES = {
    "crisis": IdealFactorization,
    "restore": IdealFactorization,
}
