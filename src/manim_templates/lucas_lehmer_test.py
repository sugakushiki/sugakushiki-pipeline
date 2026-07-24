"""
lucas_lehmer_test.py - 割らずに素数を見抜く: リュカの素数判定 (数学史記)

エドゥアール・リュカ回 の数学的主軸。素朴な試し割りでは天文学的な
回数がかかる素数判定を、リュカは数列の性質だけで、因数を一つも見つけずに
成し遂げた。<計算を賢くする (アルゴリズム的思考)> という軸を可視化する。

Modes:
    wall        - 2^127-1 は39桁の巨大数。素朴な試し割りは平方根まで約10^19通り
                  (素数に絞っても約10^17通り)で手計算では不可能、という壁を示す。
                  Fixed params: N=2^127-1, sqrt(N)~10^19, primes-only ~10^17.
    divisibility- 彼の名を冠するリュカ数 2,1,3,4,7,11,18,29,47,76,123 を示し、
                  ある素数 (例: 3) で割り切れる項が規則正しく並ぶことを見せる
                  (3 で割れるのは 3,18,123 = index 2,6,10)。黄金比・螺旋には
                  立ち入らない。
                  Fixed params: Lucas numbers L0..L10, multiples of 3 at idx 2,6,10.
    test        - リュカ・レーマー・テスト s0=4, s_{k+1}=s_k^2-2 (mod 2^p-1) を
                  p-2回。p=5/M=31 は 4->14->8->0 で素数、p=11/M=2047 は 0 に
                  落ちず合成数だが因数 23・89 は現れない。2^127-1 は125回。
                  Fixed params: p=5 chain 4,14,8,0 (prime); p=11 ends 1736
                  (composite, factors 23*89 hidden); M127 needs 125 steps.

画面に人名・年号は出さない (narration が担う)。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 049 (Edouard Lucas), math pillar (primality without factoring).
"""

from manim import (
    RIGHT,
    DashedLine,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class LucasLehmerTest(Scene):
    """リュカの素数判定 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "test")
        self._duration = params.get("duration", 26)

        if mode == "wall":
            self._build_wall()
        elif mode == "divisibility":
            self._build_divisibility()
        else:
            self._build_test()

    # ------------------------------------------------------------------
    # Mode: wall  ── 39桁の数を素朴に確かめる手間の天文学的な大きさ
    # ------------------------------------------------------------------
    def _build_wall(self):
        duration = self._duration

        title = Text(
            "この39桁の数が素数か、どう確かめる？",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        n_expr = MathTex(
            r"N = 2^{127} - 1 \approx 1.7 \times 10^{38}",
            font_size=38,
            color=TEXT_WHITE,
        )
        n_expr.move_to([0, 2.05, 0])

        digits = Text("39桁の巨大な数", font=FONT, font_size=24, color=TEXT_DIM)
        digits.move_to([0, 1.35, 0])

        method = Text(
            "素朴な方法：小さい数から順に割ってみる（試し割り）",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        method.move_to([0, 0.5, 0])

        sqrtg = VGroup(
            MathTex(r"\sqrt{N} \approx 10^{19}", font_size=42, color=ACCENT_CYAN),
            Text("通り試す必要がある", font=FONT, font_size=26, color=TEXT_WHITE),
        ).arrange(RIGHT, buff=0.28)
        sqrtg.move_to([0, -0.4, 0])

        primes = Text(
            "賢く素数に絞っても、10の17乗のおよそ3倍",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        primes.move_to([0, -1.2, 0])

        punch = Text(
            "一秒に一回でも、約90億年 ── 地球の歴史の約2倍",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        )
        punch.move_to([0, -1.95, 0])

        anim_time = 0.7 + 0.8 + 0.5 + 0.7 + 0.8 + 0.6 + 0.7 + 0.6
        default_waits = 5.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(n_expr), run_time=0.8)
        self.play(FadeIn(digits), run_time=0.5)
        self.wait(1.0 * ws)
        self.play(FadeIn(method), run_time=0.7)
        self.wait(0.8 * ws)
        self.play(FadeIn(sqrtg), run_time=0.8)
        self.play(FadeIn(primes), run_time=0.6)
        self.wait(1.0 * ws)
        self.play(FadeIn(punch), run_time=0.7)
        self.play(Indicate(punch, color=ACCENT_PINK, scale_factor=1.15), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.8 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: divisibility  ── リュカ数の割れ方に規則がある
    # ------------------------------------------------------------------
    def _build_divisibility(self):
        duration = self._duration

        title = Text(
            "リュカ数 ── 割れ方に、規則がある",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        rule = Text(
            "前の二つを足して、次を作る（フィボナッチの兄弟）",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        rule.move_to([0, 2.35, 0])

        lucas = [2, 1, 3, 4, 7, 11, 18, 29, 47, 76, 123]
        mult3_idx = [2, 6, 10]  # terms divisible by 3
        nums = VGroup(*[MathTex(str(v), font_size=32, color=TEXT_WHITE) for v in lucas])
        nums.arrange(RIGHT, buff=0.4)
        nums.move_to([0, 1.25, 0])

        pattern = Text(
            "「3」で割り切れる項が、規則正しく並ぶ",
            font=FONT,
            font_size=28,
            color=ACCENT_PINK,
        )
        pattern.move_to([0, 0.2, 0])

        insight = Text(
            "どの項が初めて割れるかが決まると、割れ方が読める",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        insight.move_to([0, -0.75, 0])

        punch = Text(
            "数を割ってみなくても、素数の手がかりになる",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        punch.move_to([0, -1.7, 0])

        anim_time = 0.7 + 0.6 + 1.1 + 0.7 + 0.7 + 0.6 + 0.7
        default_waits = 5.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(rule), run_time=0.6)
        self.play(FadeIn(nums), run_time=1.1)
        self.wait(0.9 * ws)
        self.play(
            *[nums[i].animate.set_color(ACCENT_PINK) for i in mult3_idx],
            run_time=0.7,
        )
        self.play(FadeIn(pattern), run_time=0.7)
        self.wait(1.0 * ws)
        self.play(FadeIn(insight), run_time=0.6)
        self.wait(0.9 * ws)
        self.play(FadeIn(punch), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 2.8 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: test  ── リュカ・レーマー・テスト (素数 vs 合成数)
    # ------------------------------------------------------------------
    def _build_test(self):
        duration = self._duration

        title = Text(
            "二乗して2を引く、をくり返す",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])

        recur = MathTex(
            r"s_0 = 4,\quad s_{k+1} = s_k^{2} - 2 \pmod{2^p - 1}",
            font_size=32,
            color=TEXT_WHITE,
        )
        recur.move_to([0, 2.3, 0])

        divider = DashedLine([0, 1.75, 0], [0, -1.25, 0], color=EDGE_COLOR, stroke_width=2)

        # Left: p=5 -> prime
        l_head = MathTex(r"p=5:\ \ 2^5 - 1 = 31", font_size=30, color=ACCENT_CYAN)
        l_head.move_to([-3.5, 1.35, 0])
        l_chain = MathTex(r"4 \to 14 \to 8 \to 0", font_size=34, color=TEXT_WHITE)
        l_chain.move_to([-3.5, 0.5, 0])
        l_verd = Text("0 に着地 → 31 は素数", font=FONT, font_size=25, color=ACCENT_GOLD)
        l_verd.move_to([-3.5, -0.35, 0])

        # Right: p=11 -> composite
        r_head = MathTex(r"p=11:\ \ 2^{11} - 1 = 2047", font_size=30, color=ACCENT_PINK)
        r_head.move_to([3.5, 1.35, 0])
        r_chain = MathTex(r"4 \to 14 \to 194 \to \cdots \to 1736", font_size=28, color=TEXT_WHITE)
        r_chain.move_to([3.5, 0.5, 0])
        r_verd = Text("0 に落ちない → 合成数", font=FONT, font_size=25, color=TEXT_WHITE)
        r_verd.move_to([3.5, -0.35, 0])
        r_note = Text("でも、因数 23・89 は現れない", font=FONT, font_size=25, color=ACCENT_PINK)
        r_note.move_to([3.5, -1.05, 0])

        bottom = VGroup(
            MathTex(r"2^{127} - 1", font_size=32, color=ACCENT_CYAN),
            Text(" なら、たった ", font=FONT, font_size=26, color=TEXT_WHITE),
            Text("125回", font=FONT, font_size=34, color=ACCENT_GOLD),
            Text(" でわかる", font=FONT, font_size=26, color=TEXT_WHITE),
        ).arrange(RIGHT, buff=0.12)
        bottom.move_to([0, -1.95, 0])

        anim_time = 0.7 + 0.8 + 0.5 + 0.7 + 0.6 + 0.5 + 0.7 + 0.6 + 0.6 + 0.7 + 0.6
        default_waits = 4.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(recur), run_time=0.8)
        self.play(FadeIn(divider), run_time=0.5)
        self.wait(0.6 * ws)
        self.play(FadeIn(l_head), run_time=0.7)
        self.play(FadeIn(l_chain), run_time=0.6)
        self.play(FadeIn(l_verd), run_time=0.5)
        self.wait(0.9 * ws)
        self.play(FadeIn(r_head), run_time=0.7)
        self.play(FadeIn(r_chain), run_time=0.6)
        self.play(FadeIn(r_verd), run_time=0.6)
        self.play(FadeIn(r_note), run_time=0.7)
        self.play(Indicate(r_note, color=ACCENT_PINK, scale_factor=1.12), run_time=0.6)
        self.wait(0.9 * ws)
        self.play(FadeIn(bottom), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 2.4 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years in any mode. On-screen numbers
# (127, 31, 2047, 23, 89, 125, Lucas numbers) are mathematical values,
# not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "wall": {"people": [], "years": []},
    "divisibility": {"people": [], "years": []},
    "test": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "wall": LucasLehmerTest,
    "divisibility": LucasLehmerTest,
    "test": LucasLehmerTest,
}
