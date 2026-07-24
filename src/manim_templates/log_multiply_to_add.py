"""
log_multiply_to_add.py - 掛け算を足し算に変える: 対数の核心と現代の姿 (数学史記)

ジョン・ネイピア回 の数学的主軸。七桁の掛け算に潰されていた時代に、
ネイピアは <掛け算を足し算に変える> 対数を着想した。等比の段と等差の段を
並べれば、掛けるという難しい操作が、足すという易しい操作に化ける ── その
一つの発想を可視化し、さらにそれが計算尺として、そして世界を測る目盛として
生き続けていることを見せる。

Modes:
    gp_ap  - 等比数列 1,2,4,8,16,32,64,128 (上段) と等差数列 0..7 (下段) を
             対応させ、4x8 を「下段の 2 と 3 を足して 5、その位置の 32」として
             示す。掛け算が表引き+足し算に降格する。
             Fixed params: geo=2^i (i=0..7), ari=i; 4x8: idx 2+3=5 -> 32.
    slide  - 二本の対数目盛 (1..10 を対数間隔で刻んだ物差し) を上下に置き、
             下をずらして長さを足すと数が掛かる (計算尺の原理) を示す。
             例: 上の目盛の 2 に下の 1 を合わせると、下の 4 の上に上の 8。
             Fixed params: log10 scale 1..10; 2x4=8 alignment.
    world  - 一本の目盛の上に、音 (デシベル)・地震・酸 (pH)・星の明るさ (等級)
             を並べ、量を《比》で測る対数の尺度であることを示す (エンドカード)。
             Fixed params: dB x10->+10, quake x10->+1, pH x10->1, star x100->5.

画面に人名・年号は出さない (narration が担う)。数字 (2,4,8,32,10,100 等) は
数学的な値で年号ではない。Duration-aware: reads target duration.

Used by: Episode 051 (John Napier), math pillar (multiplication becomes addition).
"""

import math

from manim import (
    RIGHT,
    DashedLine,
    FadeIn,
    Indicate,
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
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class LogMultiplyToAdd(Scene):
    """掛け算を足し算に変える対数 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "gp_ap")
        self._duration = params.get("duration", 26)

        if mode == "slide":
            self._build_slide()
        elif mode == "world":
            self._build_world()
        else:
            self._build_gp_ap()

    # ------------------------------------------------------------------
    # Mode: gp_ap  ── 等比の段と等差の段を並べると、掛け算が足し算になる
    # ------------------------------------------------------------------
    def _build_gp_ap(self):
        duration = self._duration

        title = Text(
            "掛け算を、足し算に変える",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        geo = [1, 2, 4, 8, 16, 32, 64, 128]
        ari = [0, 1, 2, 3, 4, 5, 6, 7]

        top_lbl = Text("かけ算で増える（等比）", font=FONT, font_size=22, color=TEXT_DIM)
        top_lbl.move_to([0, 2.35, 0])

        top = VGroup(*[MathTex(str(v), font_size=30, color=TEXT_WHITE) for v in geo])
        top.arrange(RIGHT, buff=0.5)
        top.move_to([0, 1.7, 0])

        bot = VGroup()
        for i, v in enumerate(ari):
            m = MathTex(str(v), font_size=30, color=TEXT_DIM)
            m.move_to([top[i].get_x(), 0.9, 0])
            bot.add(m)

        bot_lbl = Text("たし算で増える（等差）", font=FONT, font_size=22, color=TEXT_DIM)
        bot_lbl.move_to([0, 0.3, 0])

        # worked example: 4 x 8
        ex1 = MathTex(r"4 \times 8", font_size=40, color=ACCENT_CYAN)
        ex1.move_to([-3.4, -0.75, 0])
        ex2 = MathTex(r"\Rightarrow\ 2 + 3 = 5", font_size=40, color=TEXT_WHITE)
        ex2.move_to([0.1, -0.75, 0])
        ex3 = MathTex(r"\Rightarrow\ 32", font_size=40, color=ACCENT_PINK)
        ex3.move_to([3.5, -0.75, 0])

        note = Text(
            "難しい掛け算が、表引きと足し算になる",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.3, 0])

        formula = MathTex(
            r"\log(a \times b) = \log a + \log b",
            font_size=34,
            color=ACCENT_CYAN,
        )
        formula.move_to([0, -1.85, 0])

        anim_time = 0.7 + 0.5 + 1.0 + 1.0 + 0.5 + 0.7 + 0.6 + 0.7 + 0.7 + 0.6
        default_waits = 4.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(top_lbl), run_time=0.5)
        self.play(FadeIn(top), run_time=1.0)
        self.play(FadeIn(bot), FadeIn(bot_lbl), run_time=1.0)
        self.wait(0.8 * ws)
        # highlight 4, 8 (top idx 2,3) and their positions 2,3 (bot idx 2,3)
        self.play(
            top[2].animate.set_color(ACCENT_CYAN),
            top[3].animate.set_color(ACCENT_CYAN),
            bot[2].animate.set_color(ACCENT_CYAN),
            bot[3].animate.set_color(ACCENT_CYAN),
            run_time=0.7,
        )
        self.play(FadeIn(ex1), run_time=0.5)
        self.play(FadeIn(ex2), run_time=0.6)
        self.wait(0.7 * ws)
        # highlight result 32 (top idx 5) and position 5 (bot idx 5)
        self.play(
            top[5].animate.set_color(ACCENT_PINK),
            bot[5].animate.set_color(ACCENT_PINK),
            run_time=0.6,
        )
        self.play(FadeIn(ex3), run_time=0.6)
        self.wait(0.8 * ws)
        self.play(FadeIn(note), run_time=0.7)
        self.play(FadeIn(formula), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.3 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: slide  ── 長さ(=対数)を足すと数が掛かる (計算尺の原理)
    # ------------------------------------------------------------------
    def _log_scale(self, y, x0, span, color, radius_hi=None):
        """Build a logarithmic scale (ruler) group: axis + ticks + labels 1..10."""
        axis = Line([x0, y, 0], [x0 + span, y, 0], color=color, stroke_width=3)
        group = VGroup(axis)
        marks = {}
        for v in range(1, 11):
            xx = x0 + span * math.log10(v)
            tick = Line([xx, y - 0.12, 0], [xx, y + 0.12, 0], color=color, stroke_width=2)
            lab = MathTex(str(v), font_size=24, color=color)
            lab.move_to([xx, y + 0.34, 0])
            group.add(tick, lab)
            marks[v] = (tick, lab)
        group._marks = marks
        return group

    def _build_slide(self):
        duration = self._duration

        title = Text(
            "長さを足すと、数が掛かる ── 計算尺のしくみ",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        span = 8.2
        x0 = -4.6
        y_top = 1.3
        y_bot = 0.0

        top = self._log_scale(y_top, x0, span, ACCENT_CYAN)
        # bottom scale starts aligned (1 under top's 1), then slides right by log10(2)
        bot = self._log_scale(y_bot, x0, span, ACCENT_GOLD)

        shift_x = span * math.log10(2)

        note1 = Text(
            "上の目盛の「2」に、下の目盛の「1」を合わせる",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note1.move_to([0, -0.7, 0])

        connect = DashedLine(
            [x0 + shift_x + span * math.log10(4), y_bot - 0.12, 0],
            [x0 + span * math.log10(8), y_top - 0.12, 0],
            color=ACCENT_PINK,
            stroke_width=3,
        )

        result = MathTex(r"2 \times 4 = 8", font_size=34, color=ACCENT_PINK)
        result.move_to([0, -1.25, 0])

        punch = Text(
            "長さ（＝対数）を足すことが、掛け算になる",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        punch.move_to([0, -1.85, 0])

        anim_time = 0.7 + 0.9 + 0.9 + 0.6 + 1.0 + 0.6 + 0.6 + 0.6 + 0.7
        default_waits = 3.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(top), run_time=0.9)
        self.play(FadeIn(bot), run_time=0.9)
        self.wait(0.6 * ws)
        self.play(FadeIn(note1), run_time=0.6)
        # slide bottom scale so its "1" sits under top's "2"
        self.play(bot.animate.shift(RIGHT * shift_x), run_time=1.0)
        self.wait(0.5 * ws)
        # highlight the alignment producing 2 x 4 = 8
        self.play(
            top._marks[2][1].animate.set_color(ACCENT_PINK),
            bot._marks[4][1].animate.set_color(ACCENT_PINK),
            top._marks[8][1].animate.set_color(ACCENT_PINK),
            run_time=0.6,
        )
        self.play(FadeIn(connect), run_time=0.6)
        self.play(FadeIn(result), run_time=0.6)
        self.wait(0.7 * ws)
        self.play(FadeIn(punch), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 1.8 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: world  ── 対数は世界を測る目盛 (量を《比》で測る)
    # ------------------------------------------------------------------
    def _build_world(self):
        duration = self._duration

        title = Text(
            "対数は、世界を測る目盛",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        # a power-of-ten axis
        axis = Line([-5.0, 2.05, 0], [5.0, 2.05, 0], color=EDGE_COLOR, stroke_width=3)
        ticks = VGroup(axis)
        for k in range(0, 7):
            xx = -5.0 + k * (10.0 / 6.0)
            tick = Line([xx, 1.92, 0], [xx, 2.18, 0], color=EDGE_COLOR, stroke_width=2)
            lab = MathTex(rf"10^{{{k}}}", font_size=24, color=TEXT_DIM)
            lab.move_to([xx, 2.5, 0])
            ticks.add(tick, lab)

        sub = Text(
            "量が十倍になるたびに、一目盛ずつ",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        sub.move_to([0, 1.4, 0])

        # four perceptual scales, revealed one by one
        rows = [
            ("音の大きさ（デシベル）", r"\times 10 \;\to\; +10"),
            ("地震の揺れ（マグニチュード）", r"\times 10 \;\to\; +1"),
            ("酸・アルカリ（pH）", r"\times 10 \;\to\; 1"),
            ("星の明るさ（等級）", r"\times 100 \;\to\; 5"),
        ]
        ys = [0.5, -0.1, -0.7, -1.3]
        items = []
        for (jp, mx), yy in zip(rows, ys, strict=True):
            name = Text(jp, font=FONT, font_size=26, color=ACCENT_CYAN)
            name.move_to([-1.7, yy, 0])
            ratio = MathTex(mx, font_size=30, color=TEXT_WHITE)
            ratio.next_to(name, RIGHT, buff=0.5)
            items.append(VGroup(name, ratio))

        punch = Text(
            "桁ちがいの世界が、たし算の目盛に畳み込まれる",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        punch.move_to([0, -1.85, 0])

        anim_time = 0.7 + 0.9 + 0.6 + 4 * 0.7 + 0.7
        default_waits = 4.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(ticks), run_time=0.9)
        self.play(FadeIn(sub), run_time=0.6)
        self.wait(0.6 * ws)
        for it in items:
            self.play(FadeIn(it), run_time=0.7)
            self.wait(0.5 * ws)
        self.play(FadeIn(punch), run_time=0.7)
        self.play(Indicate(punch, color=ACCENT_GOLD, scale_factor=1.1), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - (0.6 + 4 * 0.5) * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years in any mode. On-screen numbers
# (1,2,4,8,32,10,100, powers of ten) are mathematical values, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "gp_ap": {"people": [], "years": []},
    "slide": {"people": [], "years": []},
    "world": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "gp_ap": LogMultiplyToAdd,
    "slide": LogMultiplyToAdd,
    "world": LogMultiplyToAdd,
}
