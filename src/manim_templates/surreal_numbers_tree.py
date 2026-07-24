"""
surreal_numbers_tree.py - 超現実数: 無から数を創り、無限の先へ (数学史記)

ジョン・ホートン・コンウェイ回。囲碁の終盤の分析から、コンウェイは
実数をまるごと含み、さらに無限大 (ω) と無限小 (ε) までを一つの体系に呑み込む
「超現実数」を創造した (命名はクヌース、著書 On Numbers and Games 1976)。
<最も単純なものの奥に最も豊かな構造がある> という軸の、数の創造の顔。

Modes:
    construction - 空集合 {|}=0 から始め、日を追うごとに二分木状に数が枝分かれ
                   して生まれる (0 -> -1,1 -> -2,-1/2,1/2,2 -> ...)。数直線が
                   次第に埋まっていく。
                   Fixed: day0 {0}, day1 {-1,1}, day2 {-2,-1/2,1/2,2}.
    beyond       - この構築を続けると、あらゆる実数 (π,e のような超越数も含む)
                   が埋まり、さらにその外に無限大 ω、0 のすぐ隣に無限小 ε が
                   同じ体系の中に現れる。
                   Fixed: reals filled (incl. transcendentals pi,e); omega > all
                   finite; 0 < epsilon < any positive real.

画面に人名・年号は出さない (narration が担う)。記号 (0,-1,1,1/2,ω,ε,π,e) は
数学的な値であり年号ではない。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 050 (John Horton Conway), surreal numbers.
"""

from manim import (
    DashedLine,
    Dot,
    FadeIn,
    Line,
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
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class SurrealNumbersTree(Scene):
    """超現実数 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "construction")
        self._duration = params.get("duration", 26)

        if mode == "beyond":
            self._build_beyond()
        else:
            self._build_construction()

    # ------------------------------------------------------------------
    # Mode: construction  ── 二分木で数が生まれる
    # ------------------------------------------------------------------
    def _node(self, tex, x, y, color):
        m = MathTex(tex, font_size=34, color=color)
        m.move_to([x, y, 0])
        return m

    def _build_construction(self):
        duration = self._duration

        title = Text("無から数を創る ── 超現実数", font=FONT, font_size=33, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])

        seed = MathTex(r"\{\ \mid\ \} = 0", font_size=32, color=TEXT_DIM)
        seed.move_to([0, 2.3, 0])

        # tree levels
        root = self._node(r"0", 0, 1.5, ACCENT_GOLD)
        l1 = [self._node(r"-1", -2.2, 0.4, ACCENT_CYAN), self._node(r"1", 2.2, 0.4, ACCENT_CYAN)]
        l2 = [
            self._node(r"-2", -3.4, -0.75, TEXT_WHITE),
            self._node(r"-\tfrac{1}{2}", -1.1, -0.75, TEXT_WHITE),
            self._node(r"\tfrac{1}{2}", 1.1, -0.75, TEXT_WHITE),
            self._node(r"2", 3.4, -0.75, TEXT_WHITE),
        ]

        edges = VGroup(
            Line(root.get_bottom(), l1[0].get_top(), stroke_width=2, color=EDGE_COLOR),
            Line(root.get_bottom(), l1[1].get_top(), stroke_width=2, color=EDGE_COLOR),
            Line(l1[0].get_bottom(), l2[0].get_top(), stroke_width=2, color=EDGE_COLOR),
            Line(l1[0].get_bottom(), l2[1].get_top(), stroke_width=2, color=EDGE_COLOR),
            Line(l1[1].get_bottom(), l2[2].get_top(), stroke_width=2, color=EDGE_COLOR),
            Line(l1[1].get_bottom(), l2[3].get_top(), stroke_width=2, color=EDGE_COLOR),
        )

        cap = Text(
            "空集合から始め、日を追うごとに数が枝分かれして生まれる",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        cap.move_to([0, -1.35, 0])
        punch = Text(
            "この木は、やがてすべての実数を埋めつくす", font=FONT, font_size=25, color=ACCENT_PINK
        )
        punch.move_to([0, -1.8, 0])

        anim_time = 0.7 + 0.5 + 0.5 + 0.7 + 0.4 + 0.7 + 0.4 + 0.6 + 0.6
        ws = _calc_wait_scale(duration, anim_time, 4.8)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(seed), run_time=0.5)
        self.play(FadeIn(root), run_time=0.5)
        self.wait(0.6 * ws)
        self.play(FadeIn(VGroup(edges[0], edges[1])), run_time=0.4)
        self.play(FadeIn(VGroup(*l1)), run_time=0.7)
        self.wait(0.6 * ws)
        self.play(FadeIn(VGroup(edges[2], edges[3], edges[4], edges[5])), run_time=0.4)
        self.play(FadeIn(VGroup(*l2)), run_time=0.7)
        self.wait(0.7 * ws)
        self.play(FadeIn(cap), run_time=0.6)
        self.wait(0.6 * ws)
        self.play(FadeIn(punch), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.5 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: beyond  ── 実数を埋めつくし、無限大 ω と無限小 ε の先へ
    # ------------------------------------------------------------------
    def _build_beyond(self):
        duration = self._duration

        title = Text("実数を呑み込み、その先へ", font=FONT, font_size=33, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])

        # number line for the reals
        axis = Line([-4.6, 1.1, 0], [3.2, 1.1, 0], stroke_width=2.5, color=TEXT_WHITE)
        zero_tick = Line([-0.7, 0.95, 0], [-0.7, 1.25, 0], stroke_width=2, color=TEXT_DIM)
        zero_lab = MathTex(r"0", font_size=26, color=TEXT_DIM)
        zero_lab.move_to([-0.7, 0.65, 0])
        # dense reals
        dots = VGroup(
            *[Dot([-4.4 + i * 0.28, 1.1, 0], radius=0.03, color=ACCENT_CYAN) for i in range(28)]
        )
        # pi and e example labels (transcendentals)
        pi_lab = MathTex(r"\pi", font_size=28, color=ACCENT_CYAN)
        pi_lab.move_to([1.85, 1.5, 0])
        e_lab = MathTex(r"e", font_size=28, color=ACCENT_CYAN)
        e_lab.move_to([0.75, 1.5, 0])
        # epsilon marked just above 0 : infinitesimally close to zero
        eps = MathTex(r"\varepsilon", font_size=26, color=ACCENT_PINK)
        eps.move_to([-0.28, 1.55, 0])
        reals_cap = Text(
            "すべての実数（π や e のような超越数さえも）が埋まる",
            font=FONT,
            font_size=23,
            color=TEXT_DIM,
        )
        reals_cap.move_to([0, 0.15, 0])

        # omega : beyond all finite, to the far right
        brk = DashedLine([3.3, 1.1, 0], [4.5, 1.1, 0], stroke_width=2, color=EDGE_COLOR)
        omega = MathTex(r"\omega", font_size=46, color=ACCENT_GOLD)
        omega.move_to([5.0, 1.1, 0])

        # three centered, vertically-separated lines (no horizontal overlap)
        omega_cap = Text(
            "ω ── あらゆる有限の数より大きい「無限大」",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        omega_cap.move_to([0, -0.7, 0])
        eps_cap = Text(
            "ε ── 0 より大きいのに、どんな正の実数より小さい「無限小」",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        eps_cap.move_to([0, -1.3, 0])

        punch = Text(
            "実数も、無限大も、無限小も、一つの数の体系に",
            font=FONT,
            font_size=25,
            color=TEXT_WHITE,
        )
        punch.move_to([0, -1.9, 0])

        anim_time = 0.7 + 0.8 + 0.5 + 0.6 + 0.6 + 0.7 + 0.6 + 0.7 + 0.6 + 0.6
        ws = _calc_wait_scale(duration, anim_time, 4.6)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(axis), FadeIn(dots), run_time=0.8)
        self.play(FadeIn(VGroup(zero_tick, zero_lab)), run_time=0.5)
        self.play(FadeIn(VGroup(e_lab, pi_lab)), run_time=0.6)
        self.play(FadeIn(reals_cap), run_time=0.6)
        self.wait(0.7 * ws)
        self.play(FadeIn(VGroup(brk, omega)), FadeIn(omega_cap), run_time=0.7)
        self.wait(0.6 * ws)
        self.play(FadeIn(eps), FadeIn(eps_cap), run_time=0.7)
        self.wait(0.6 * ws)
        self.play(FadeIn(punch), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 1.9 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years. Symbols (0,-1,1,1/2,omega,epsilon,
# pi,e) are mathematical values, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "construction": {"people": [], "years": []},
    "beyond": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "construction": SurrealNumbersTree,
    "beyond": SurrealNumbersTree,
}
