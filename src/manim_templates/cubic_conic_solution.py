"""
cubic_conic_solution.py - 数を図形で解く: ハイヤームの三次方程式 (数学史記)

オマル・ハイヤーム回 の数学的主軸。三次方程式には当時<解の公式>が
無かったが、ハイヤームは円錐曲線 (放物線と円) を交わらせ、その交点の横座標
(線分の長さ) として正の根を得た。数 (代数) で届かないものに図形 (幾何) で
手を伸ばした、という軸を可視化する。

Modes:
    wall      - 二次方程式には解の公式があるのに、三次方程式には (当時) 公式が
                無かった、という壁を左右対比で示す。二次 x = (-b±√(b^2-4ac))/2a、
                三次 x^3+ax=b は <?>。
                Fixed params: quadratic formula shown; cubic marked unsolved.
    construct - ハイヤームの幾何解。放物線 x^2=a y と円 x^2+y^2=(b/a^2)x を
                交わらせ、原点以外の交点の横座標 (原点からの線分の長さ) が
                x^3+a^2 x=b の正の根になる。具体値 a=2, b=9.375, 根=1.5。
                Fixed params: parabola x^2=a y, circle through origin, root=1.5.
    classify  - 負の数・負の係数を認めないため方程式が多くの型に分かれる。
                x^3+ax=b, x^3+b=ax, x^3=ax+b は別の方程式。分類すると全25型、
                うち14型が真の三次。25を 3+9+7 のように分解して見せない。
                Fixed params: 25 types total, 14 true cubics.

画面に人名・年号は出さない (narration が担う)。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 048 (Omar Khayyam), math pillar (cubic via conics).
"""

import numpy as np
from manim import (
    DOWN,
    RIGHT,
    Circle,
    DashedLine,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    ParametricFunction,
    RoundedRectangle,
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


class CubicConicSolution(Scene):
    """ハイヤームの三次方程式 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "construct")
        self._duration = params.get("duration", 26)

        if mode == "wall":
            self._build_wall()
        elif mode == "classify":
            self._build_classify()
        else:
            self._build_construct()

    # ------------------------------------------------------------------
    # Mode: wall  ── 二次は解けるが三次には公式が無い
    # ------------------------------------------------------------------
    def _build_wall(self):
        duration = self._duration

        title = Text(
            "二次には公式がある。では、三次は？",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        divider = DashedLine([0, 1.7, 0], [0, -1.1, 0], color=EDGE_COLOR, stroke_width=2)

        # Left: quadratic (solved)
        q_head = Text("二次方程式", font=FONT, font_size=28, color=ACCENT_CYAN)
        q_head.move_to([-3.35, 1.95, 0])
        q_eq = MathTex(r"a x^2 + b x + c = 0", font_size=34, color=TEXT_WHITE)
        q_eq.move_to([-3.35, 1.05, 0])
        q_form = MathTex(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", font_size=34, color=ACCENT_CYAN)
        q_form.move_to([-3.35, 0.0, 0])
        q_ok = Text("解の公式が、ある", font=FONT, font_size=24, color=ACCENT_GOLD)
        q_ok.move_to([-3.35, -0.85, 0])

        # Right: cubic (unsolved in his era)
        c_head = Text("三次方程式", font=FONT, font_size=28, color=ACCENT_PINK)
        c_head.move_to([3.35, 1.95, 0])
        c_eq = MathTex(r"x^3 + a x = b", font_size=34, color=TEXT_WHITE)
        c_eq.move_to([3.35, 1.05, 0])
        c_q = Text("？", font=FONT, font_size=88, color=ACCENT_PINK)
        c_q.move_to([3.35, -0.05, 0])
        c_no = Text("当時、解の公式は無い", font=FONT, font_size=24, color=TEXT_DIM)
        c_no.move_to([3.35, -0.85, 0])

        bottom = Text(
            "数の計算だけでは、三次に手が届かない",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        bottom.move_to([0, -1.6, 0])

        anim_time = 0.7 + 0.8 + 0.7 + 0.5 + 0.5 + 0.8 + 0.7 + 0.6 + 0.7
        default_waits = 5.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(q_head), FadeIn(q_eq), run_time=0.8)
        self.play(FadeIn(q_form), run_time=0.7)
        self.play(FadeIn(q_ok), run_time=0.5)
        self.wait(1.4 * ws)
        self.play(FadeIn(divider), run_time=0.5)
        self.play(FadeIn(c_head), FadeIn(c_eq), run_time=0.8)
        self.play(FadeIn(c_q), run_time=0.7)
        self.play(FadeIn(c_no), run_time=0.6)
        self.wait(1.4 * ws)
        self.play(FadeIn(bottom), run_time=0.7)
        self.play(Indicate(c_q, color=ACCENT_PINK, scale_factor=1.25), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.8 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: construct  ── 放物線 x^2=ay と円の交点が根
    # ------------------------------------------------------------------
    def _build_construct(self):
        duration = self._duration

        # Concrete instance: x^3 + a^2 x = b,  a=2, b=9.375, positive root = 1.5
        a = 2.0
        b = 9.375
        root = 1.5  # x-coordinate of the non-origin intersection
        # circle x^2+y^2=(b/a^2)x -> center (b/2a^2, 0), radius b/2a^2 (through origin)
        circ_cx = b / (2 * a * a)  # = 1.171875
        circ_r = b / (2 * a * a)

        # screen mapping: (mx,my) -> [ox + s*mx, oy + s*my, 0]
        s = 1.2
        ox, oy = -1.4, 0.1

        def P(mx, my):
            return np.array([ox + s * mx, oy + s * my, 0.0])

        title = Text(
            "放物線と円を交わらせて、三次方程式を解く",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])

        eq = MathTex(r"x^3 + a^2 x = b", font_size=34, color=TEXT_WHITE)
        eq.move_to([3.9, 2.35, 0])

        # axes
        x_axis = Line(P(-1.2, 0), P(2.7, 0), color=EDGE_COLOR, stroke_width=2)
        y_axis = Line(P(0, -1.05), P(0, 1.75), color=EDGE_COLOR, stroke_width=2)
        origin_dot = Dot(P(0, 0), radius=0.05, color=TEXT_DIM)

        # parabola y = x^2 / a
        parab = ParametricFunction(
            lambda t: P(t, t * t / a),
            t_range=[-1.05, 1.78, 0.02],
            color=ACCENT_CYAN,
            stroke_width=4,
        )
        parab_lbl = Text("放物線", font=FONT, font_size=22, color=ACCENT_CYAN)
        parab_lbl.move_to(P(-0.95, 1.35) + np.array([-0.15, 0, 0]))
        parab_eq = MathTex(r"x^2 = a\,y", font_size=26, color=ACCENT_CYAN)
        parab_eq.next_to(parab_lbl, DOWN, buff=0.12)

        # circle x^2 + y^2 = (b/a^2) x  -> center (circ_cx,0), radius circ_r
        circle = Circle(radius=s * circ_r, color=ACCENT_GOLD, stroke_width=4)
        circle.move_to(P(circ_cx, 0))
        circle.set_fill(ACCENT_GOLD, opacity=0.06)
        circ_lbl = Text("円", font=FONT, font_size=24, color=ACCENT_GOLD)
        circ_lbl.move_to(P(circ_cx + 1.05, 0.55))

        # intersection (root, root^2/a)
        iy = root * root / a
        inter_dot = Dot(P(root, iy), radius=0.075, color=ACCENT_PINK)
        inter_lbl = Text("交点", font=FONT, font_size=22, color=ACCENT_PINK)
        inter_lbl.move_to(P(root + 0.05, iy) + np.array([0.35, 0.2, 0]))

        # drop line to x-axis + root marker + segment
        drop = DashedLine(P(root, iy), P(root, 0), color=ACCENT_PINK, stroke_width=2.5)
        root_dot = Dot(P(root, 0), radius=0.065, color=ACCENT_PINK)
        root_seg = Line(P(0, 0), P(root, 0), color=ACCENT_PINK, stroke_width=6)
        root_lbl = Text("この長さが、正の根", font=FONT, font_size=22, color=ACCENT_PINK)
        root_lbl.move_to(P(root / 2, 0) + np.array([0, -0.55, 0]))

        anim_time = 0.7 + 0.6 + 0.7 + 0.9 + 0.9 + 0.7 + 0.9 + 0.6
        default_waits = 5.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(x_axis), FadeIn(y_axis), FadeIn(origin_dot), run_time=0.6)
        self.play(FadeIn(eq), run_time=0.7)
        self.wait(0.8 * ws)
        self.play(FadeIn(parab), FadeIn(parab_lbl), FadeIn(parab_eq), run_time=0.9)
        self.wait(0.9 * ws)
        self.play(FadeIn(circle), FadeIn(circ_lbl), run_time=0.9)
        self.wait(0.9 * ws)
        self.play(FadeIn(inter_dot), FadeIn(inter_lbl), run_time=0.7)
        self.wait(0.7 * ws)
        self.play(FadeIn(drop), FadeIn(root_dot), FadeIn(root_seg), FadeIn(root_lbl), run_time=0.9)
        self.play(Indicate(root_seg, color=ACCENT_PINK, scale_factor=1.15), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 3.3 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: classify  ── 負の数を認めないので型が増える (全25型 / 真の三次14型)
    # ------------------------------------------------------------------
    def _build_classify(self):
        duration = self._duration

        title = Text(
            "なぜ、三次方程式は何種類にも分かれるのか",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])

        subtitle = Text(
            "当時は「負の数」を認めない ── 符号で移項できない",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        subtitle.move_to([0, 2.35, 0])

        forms = [r"x^3 + a x = b", r"x^3 + b = a x", r"x^3 = a x + b"]
        xs = [-3.7, 0.0, 3.7]
        cards = VGroup()
        eqs = VGroup()
        for form, x in zip(forms, xs, strict=False):
            card = RoundedRectangle(
                width=3.0, height=1.0, corner_radius=0.12, color=EDGE_COLOR, stroke_width=2
            )
            card.move_to([x, 1.15, 0])
            card.set_fill(ACCENT_CYAN, opacity=0.05)
            m = MathTex(form, font_size=32, color=ACCENT_CYAN)
            m.move_to([x, 1.15, 0])
            cards.add(card)
            eqs.add(m)

        note = Text(
            "これらは、すべて別の三次方程式",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        note.move_to([0, 0.05, 0])

        # summary stat line (do NOT decompose 25 as 3+9+7)
        stat = VGroup(
            Text("分類すると、全部で ", font=FONT, font_size=26, color=TEXT_WHITE),
            Text("25型", font=FONT, font_size=34, color=ACCENT_GOLD),
        ).arrange(RIGHT, buff=0.12)
        stat.move_to([0, -0.95, 0])

        stat2 = VGroup(
            Text("うち ", font=FONT, font_size=26, color=TEXT_WHITE),
            Text("14型", font=FONT, font_size=34, color=ACCENT_PINK),
            Text(" が、数では解けない真の三次", font=FONT, font_size=26, color=TEXT_WHITE),
        ).arrange(RIGHT, buff=0.1)
        stat2.move_to([0, -1.65, 0])

        anim_time = 0.7 + 0.7 + 3 * 0.6 + 0.6 + 0.7 + 0.7
        default_waits = 4.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(subtitle), run_time=0.7)
        self.wait(0.7 * ws)
        for card, m in zip(cards, eqs, strict=False):
            self.play(FadeIn(card), FadeIn(m), run_time=0.6)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(1.0 * ws)
        self.play(FadeIn(stat), run_time=0.7)
        self.play(FadeIn(stat2), run_time=0.7)
        self.play(Indicate(stat2[1], color=ACCENT_PINK, scale_factor=1.2), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 1.7 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years in any mode (numbers 25/14 are counts,
# not years; a/b are symbolic coefficients).
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "wall": {"people": [], "years": []},
    "construct": {"people": [], "years": []},
    "classify": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "wall": CubicConicSolution,
    "construct": CubicConicSolution,
    "classify": CubicConicSolution,
}
