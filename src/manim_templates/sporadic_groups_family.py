"""
sporadic_groups_family.py - リーチ格子の対称性とコンウェイ群・ムーンシャイン (数学史記)

ジョン・ホートン・コンウェイ回。不遇の講師だったコンウェイが、ある
土曜のおよそ12時間で掘り当てた24次元リーチ格子の対称性 = コンウェイ群 (散在型
単純群) と、のちに彼が名づけた「モンストラス・ムーンシャイン」の偶然を描く。
<最も単純な規則の奥に最も深い構造がある> という軸の、群論側の顔。

24次元は絵にできないので、低次元の球の詰め込み (接触数) から巨大な対称性の
位数へと直観をつなぐ抽象化で見せる。

Modes:
    leech      - 2次元 (6個接する) の球詰めから、24次元リーチ格子 (一つの球が
                 196560個に接する) へ。その完全な対称性 = 位数およそ8.3×10^18 の
                 群 Co0、その中に三つの新しい散在型単純群 Co1・Co2・Co3。
                 Fixed: 2D kissing 6, Leech kissing 196560, |Co0|~8.3e18, Co1/2/3.
    moonshine  - モンスター群の最小の非自明表現の次元 196883 に 1 を足すと、
                 モジュラー j 関数の最初の非自明係数 196884 に一致する「偶然」。
                 Fixed: 196883 = dimension, 196884 = coefficient, 196884 = 196883 + 1.

画面に人名・年号は出さない (narration が担う)。Co1/Co2/Co3 は群の名前、
196560/196883/196884/8.3e18 は数学的な値であり年号ではない。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 050 (John Horton Conway), Conway groups + monstrous moonshine.
"""

import numpy as np
from manim import (
    RIGHT,
    Circle,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class SporadicGroupsFamily(Scene):
    """リーチ格子の対称性とムーンシャイン ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "leech")
        self._duration = params.get("duration", 26)

        if mode == "moonshine":
            self._build_moonshine()
        else:
            self._build_leech()

    # ------------------------------------------------------------------
    # Mode: leech  ── 球の詰め込み → 24次元の対称性 → コンウェイ群
    # ------------------------------------------------------------------
    def _kissing_2d(self, r=0.30, center=(-4.0, 1.05)):
        """Central circle touched by 6 (hexagonal kissing = 6)."""
        cx, cy = center
        group = VGroup()
        core = Circle(
            radius=r,
            stroke_width=2.0,
            stroke_color=ACCENT_GOLD,
            fill_opacity=0.35,
            fill_color=ACCENT_GOLD,
        )
        core.move_to([cx, cy, 0])
        group.add(core)
        for k in range(6):
            ang = k * np.pi / 3.0
            c = Circle(
                radius=r,
                stroke_width=2.0,
                stroke_color=ACCENT_CYAN,
                fill_opacity=0.18,
                fill_color=ACCENT_CYAN,
            )
            c.move_to([cx + 2 * r * np.cos(ang), cy + 2 * r * np.sin(ang), 0])
            group.add(c)
        return group

    def _build_leech(self):
        duration = self._duration

        title = Text("24次元の格子の、完全な対称性", font=FONT, font_size=33, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])

        packing = self._kissing_2d()
        pack_cap = Text("2次元では、6個が接する", font=FONT, font_size=22, color=TEXT_WHITE)
        pack_cap.move_to([-4.0, -0.7, 0])

        # right stack
        r1 = Text("3次元では12個 ── 次元を上げていくと", font=FONT, font_size=24, color=TEXT_DIM)
        r1.move_to([1.6, 2.15, 0])
        r2 = VGroup(
            Text("24次元「リーチ格子」では、一つの球が", font=FONT, font_size=24, color=TEXT_WHITE),
            MathTex(r"196560", font_size=34, color=ACCENT_CYAN),
            Text("個に接する", font=FONT, font_size=24, color=TEXT_WHITE),
        ).arrange(RIGHT, buff=0.18)
        r2.move_to([1.6, 1.25, 0])

        r3lab = Text("その完全な対称性を数えると", font=FONT, font_size=24, color=TEXT_WHITE)
        r3lab.move_to([1.6, 0.35, 0])
        order = MathTex(
            r"|\mathrm{Co}_0| \approx 8.3 \times 10^{18}", font_size=40, color=ACCENT_GOLD
        )
        order.move_to([1.6, -0.5, 0])

        r4 = Text("その中に、三つの新しい散在型単純群", font=FONT, font_size=24, color=TEXT_WHITE)
        r4.move_to([1.6, -1.2, 0])
        groups = MathTex(
            r"\mathrm{Co}_1,\ \ \mathrm{Co}_2,\ \ \mathrm{Co}_3", font_size=40, color=ACCENT_PINK
        )
        groups.move_to([1.6, -1.75, 0])

        anim_time = 0.7 + 0.8 + 0.5 + 0.6 + 0.7 + 0.5 + 0.7 + 0.6 + 0.7 + 0.6
        ws = _calc_wait_scale(duration, anim_time, 5.0)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(packing), run_time=0.8)
        self.play(FadeIn(pack_cap), run_time=0.5)
        self.wait(0.7 * ws)
        self.play(FadeIn(r1), run_time=0.6)
        self.play(FadeIn(r2), run_time=0.7)
        self.wait(0.7 * ws)
        self.play(FadeIn(r3lab), run_time=0.5)
        self.play(FadeIn(order), run_time=0.7)
        self.wait(0.8 * ws)
        self.play(FadeIn(r4), run_time=0.6)
        self.play(FadeIn(groups), run_time=0.7)
        self.play(Indicate(groups, color=ACCENT_PINK, scale_factor=1.12), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.9 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: moonshine  ── 196884 = 196883 + 1
    # ------------------------------------------------------------------
    def _build_moonshine(self):
        duration = self._duration

        title = Text("途方もない偶然 ── ムーンシャイン", font=FONT, font_size=33, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])

        # left fact: monster minimal representation dimension
        lft_lab = Text(
            "巨大な「モンスター群」の\n最小の表現の次元",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
            line_spacing=0.8,
        )
        lft_lab.move_to([-3.4, 1.55, 0])
        lft_num = MathTex(r"196883", font_size=44, color=ACCENT_CYAN)
        lft_num.move_to([-3.4, 0.35, 0])

        # right fact: j-function first coefficient
        rgt_lab = Text(
            "モジュラー関数 j の\n最初の係数",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
            line_spacing=0.8,
        )
        rgt_lab.move_to([3.4, 1.55, 0])
        rgt_num = MathTex(r"196884", font_size=44, color=ACCENT_CYAN)
        rgt_num.move_to([3.4, 0.35, 0])

        eq = MathTex(r"196884 = 196883 + 1", font_size=52, color=ACCENT_GOLD)
        eq.move_to([0, -1.05, 0])

        caption = Text(
            "たった1違い ── この偶然の奥に、深い橋が隠れていた",
            font=FONT,
            font_size=25,
            color=ACCENT_PINK,
        )
        caption.move_to([0, -1.75, 0])

        anim_time = 0.7 + 0.6 + 0.6 + 0.6 + 0.6 + 0.8 + 0.6 + 0.7
        ws = _calc_wait_scale(duration, anim_time, 4.8)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(lft_lab), run_time=0.6)
        self.play(FadeIn(lft_num), run_time=0.6)
        self.wait(0.7 * ws)
        self.play(FadeIn(rgt_lab), run_time=0.6)
        self.play(FadeIn(rgt_num), run_time=0.6)
        self.wait(0.7 * ws)
        self.play(FadeIn(eq), run_time=0.8)
        self.play(Indicate(eq, color=ACCENT_GOLD, scale_factor=1.1), run_time=0.6)
        self.wait(0.7 * ws)
        self.play(FadeIn(caption), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 2.1 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years. Co1/Co2/Co3 are group names;
# 196560/196883/196884/8.3e18 are mathematical values, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "leech": {"people": [], "years": []},
    "moonshine": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "leech": SporadicGroupsFamily,
    "moonshine": SporadicGroupsFamily,
}
