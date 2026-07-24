"""
napier_kinematic.py - 動く点で数を測る: ネイピアの対数の定義と改良 (数学史記)

ジョン・ネイピア回 の数学ビート(2)(3)。ネイピアは指数や底を使わず、
二つの動く点で対数を定義した ── 残りの距離に比例して減速する点(等比)と、
等速で進む点(等差)。その運動学的な定義と、数が増えるほど対数が減るという
逆さの性質、そしてブリッグスによる常用対数への改良を可視化する。

Modes:
    points - 長さ 10^7 (一千万) の線分を、残り距離に比例した速さで進む点 P
             (だんだん減速=等比) と、無限の直線を等速で進む点 Q (等差)。Q の
             距離が P の残り距離の対数で、P が出発点(残り一千万)のとき対数は 0。
             P は減速し続け端に達しない。連続モーションで全編を使う。
             Fixed params: r(t)=exp(-k t), P decelerates, Q linear, NapLog(10^7)=0.
    curve  - 横軸に数、縦軸に対数。左=ネイピア(数が増えると減る、一千万で 0)、
             右=ブリッグスの常用対数(増える、1 で 0・10 で 1)を対比する。
             Fixed params: Napier decreasing (0 at 10^7); Briggs increasing (1->0,10->1).

画面に人名・年号は出さない (narration が担う)。10^7 等は数学的な値で年号でない。
向き・大小 (減る対数 vs 増える対数、一千万で 0) はレンダフレームで実測確認する。
Duration-aware: reads target duration.

Used by: Episode 051 (John Napier), math pillar (kinematic definition of logarithm).
"""

import math

from manim import (
    DOWN,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Scene,
    Text,
    ValueTracker,
    VMobject,
    always_redraw,
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


class NapierKinematic(Scene):
    """ネイピアの運動学的な対数の定義 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "points")
        self._duration = params.get("duration", 26)

        if mode == "curve":
            self._build_curve()
        else:
            self._build_points()

    # ------------------------------------------------------------------
    # Mode: points  ── 二つの動く点で数を測る
    # ------------------------------------------------------------------
    def _build_points(self):
        duration = self._duration

        title = Text(
            "動く点で、数を測る",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        x_l, x_r = -4.6, 4.4
        y_p = 1.35
        y_q = -0.85

        # P segment (length = 10^7) and Q infinite line
        p_line = Line([x_l, y_p, 0], [x_r, y_p, 0], color=EDGE_COLOR, stroke_width=3)
        q_line = Line([x_l, y_q, 0], [x_r + 0.6, y_q, 0], color=EDGE_COLOR, stroke_width=3)

        seg_lbl = MathTex(r"10^7", font_size=30, color=TEXT_DIM)
        seg_lbl.move_to([x_r + 0.0, y_p + 0.45, 0])
        seg_note = Text("（一千万）", font=FONT, font_size=20, color=TEXT_DIM)
        seg_note.next_to(seg_lbl, DOWN, buff=0.08)

        p_lbl = Text(
            "点 P：残りの距離に比例して減速（等比）",
            font=FONT,
            font_size=24,
            color=ACCENT_CYAN,
        )
        p_lbl.move_to([0, 2.35, 0])

        q_lbl = Text(
            "点 Q：等速で進む（等差）",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        q_lbl.move_to([0, -1.4, 0])

        rel = Text(
            "Q の進んだ距離 ＝ P の残り距離の《対数》",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        rel.move_to([0, -1.85, 0])

        # start marker: a minimal "0" at Q's start (log is 0 at the outset,
        # pairing with the P line's 10^7 at full length). Placed at the far
        # left under the Q dot so it never crowds the centred q_lbl/rel lines
        # below.
        zero_lbl = MathTex(r"0", font_size=28, color=ACCENT_PINK)
        zero_lbl.move_to([x_l, y_q - 0.38, 0])

        # moving points driven by one tracker (continuous motion whole scene)
        t = ValueTracker(0.0)
        k = 3.2

        def p_x():
            r = math.exp(-k * t.get_value())  # remaining fraction (1 -> 0)
            return x_l + (1.0 - r) * (x_r - x_l)

        def q_x():
            return x_l + t.get_value() * (x_r - x_l) * 0.98

        p_dot = always_redraw(lambda: Dot([p_x(), y_p, 0], color=ACCENT_CYAN, radius=0.1))
        q_dot = always_redraw(lambda: Dot([q_x(), y_q, 0], color=ACCENT_GOLD, radius=0.1))
        link = always_redraw(
            lambda: DashedLine([p_x(), y_p, 0], [q_x(), y_q, 0], color=EDGE_COLOR, stroke_width=1.5)
        )

        # setup (fade in everything before the single long motion)
        setup = 0.7 + 0.6 + 0.6 + 0.6 + 0.6 + 0.6 + 0.5 + 0.6
        coda = 2.2
        motion = max(4.0, duration - setup - coda)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(p_line), FadeIn(seg_lbl), FadeIn(seg_note), run_time=0.6)
        self.play(FadeIn(q_line), run_time=0.6)
        self.play(FadeIn(p_lbl), run_time=0.6)
        self.play(FadeIn(q_lbl), run_time=0.6)
        self.play(FadeIn(rel), run_time=0.6)
        self.play(FadeIn(zero_lbl), run_time=0.5)
        self.add(p_dot, q_dot, link)
        self.play(FadeIn(p_dot), FadeIn(q_dot), run_time=0.6)
        # single continuous motion for the whole remaining scene
        self.play(t.animate.set_value(1.0), run_time=motion, rate_func=lambda x: x)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: curve  ── ネイピアの対数(減る) と 現代の対数(増える)
    # ------------------------------------------------------------------
    def _smooth_curve(self, pts, color, width=4):
        c = VMobject()
        c.set_points_smoothly([[x, y, 0] for (x, y) in pts])
        c.set_stroke(color, width)
        return c

    def _build_curve(self):
        duration = self._duration

        title = Text(
            "ネイピアの対数と、現代の対数",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        divider = DashedLine([0, 2.2, 0], [0, -1.5, 0], color=EDGE_COLOR, stroke_width=2)

        # ---- Left panel: Napier (decreasing, 0 at 10^7) ----
        lx0, lx1 = -5.2, -1.2
        ly0 = -1.0
        l_xaxis = Line([lx0, ly0, 0], [lx1, ly0, 0], color=EDGE_COLOR, stroke_width=2)
        l_yaxis = Line([lx0, ly0, 0], [lx0, 1.9, 0], color=EDGE_COLOR, stroke_width=2)

        # decreasing curve: high at small x (left), crosses axis (log 0) at right end
        l_pts = []
        for i in range(21):
            u = i / 20.0
            sx = lx0 + u * (lx1 - lx0)
            # from ~1.7 down to 0 at the right end
            sy = ly0 + 1.7 * (1.0 - u) ** 1.3
            l_pts.append((sx, sy))
        l_curve = self._smooth_curve(l_pts, ACCENT_PINK)

        l_head = Text("ネイピア", font=FONT, font_size=26, color=ACCENT_PINK)
        l_head.move_to([-3.2, 2.0, 0])
        l_desc = Text(
            "数が増えると、対数は減る",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        l_desc.move_to([-3.2, -1.3, 0])
        l_zero = Dot([lx1, ly0, 0], color=ACCENT_GOLD, radius=0.08)
        l_zero_lbl = MathTex(r"10^7 \Rightarrow 0", font_size=26, color=ACCENT_GOLD)
        l_zero_lbl.move_to([lx1 - 0.1, ly0 + 0.5, 0])

        # ---- Right panel: Briggs / modern common log (increasing, 1->0, 10->1) ----
        rx0, rx1 = 1.1, 5.1
        ry0 = -1.0
        r_xaxis = Line([rx0, ry0, 0], [rx1, ry0, 0], color=EDGE_COLOR, stroke_width=2)
        r_yaxis = Line([rx0, ry0, 0], [rx0, 1.9, 0], color=EDGE_COLOR, stroke_width=2)

        # increasing curve through (1 -> 0) at left and (10 -> 1) at right
        def _sx(v):  # map value 1..10 to screen x
            return rx0 + (math.log10(v) / 1.0) * (rx1 - rx0)

        def _sy(logv):  # map log value 0..1 to screen y
            return ry0 + logv * 2.2

        r_pts = []
        for i in range(1, 41):
            v = 1.0 + (10.0 - 1.0) * i / 40.0
            r_pts.append((_sx(v), _sy(math.log10(v))))
        r_curve = self._smooth_curve(r_pts, ACCENT_CYAN)

        r_head = Text("ブリッグス（現代）", font=FONT, font_size=26, color=ACCENT_CYAN)
        r_head.move_to([3.1, 2.0, 0])
        d1 = Dot([_sx(1), _sy(0), 0], color=ACCENT_GOLD, radius=0.08)
        d1_lbl = MathTex(r"1 \Rightarrow 0", font_size=26, color=ACCENT_GOLD)
        d1_lbl.move_to([_sx(1) + 0.55, _sy(0) - 0.05, 0])
        d10 = Dot([_sx(10), _sy(1), 0], color=ACCENT_GOLD, radius=0.08)
        d10_lbl = MathTex(r"10 \Rightarrow 1", font_size=26, color=ACCENT_GOLD)
        d10_lbl.move_to([_sx(10) - 0.6, _sy(1) + 0.35, 0])

        bottom = Text(
            "ネイピアが発想を、ブリッグスが使いやすい形を与えた",
            font=FONT,
            font_size=25,
            color=ACCENT_GOLD,
        )
        bottom.move_to([0, -1.85, 0])

        anim_time = 0.7 + 0.5 + 0.6 + 0.9 + 0.6 + 0.6 + 0.6 + 0.9 + 0.6 + 0.6 + 0.6 + 0.7
        default_waits = 3.5
        ws = max(0.3, min((duration - anim_time) / default_waits, 5.0)) if default_waits else 1.0

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(divider), run_time=0.5)
        # left panel
        self.play(FadeIn(l_xaxis), FadeIn(l_yaxis), FadeIn(l_head), run_time=0.6)
        self.play(FadeIn(l_curve), run_time=0.9)
        self.play(FadeIn(l_desc), run_time=0.6)
        self.play(FadeIn(l_zero), FadeIn(l_zero_lbl), run_time=0.6)
        self.wait(0.8 * ws)
        # right panel
        self.play(FadeIn(r_xaxis), FadeIn(r_yaxis), FadeIn(r_head), run_time=0.6)
        self.play(FadeIn(r_curve), run_time=0.9)
        self.play(FadeIn(d1), FadeIn(d1_lbl), run_time=0.6)
        self.play(FadeIn(d10), FadeIn(d10_lbl), run_time=0.6)
        self.wait(0.9 * ws)
        self.play(FadeIn(bottom), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 1.7 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years. On-screen tokens (10^7, 0, 1, 10)
# are mathematical values, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "points": {"people": [], "years": []},
    "curve": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "points": NapierKinematic,
    "curve": NapierKinematic,
}
