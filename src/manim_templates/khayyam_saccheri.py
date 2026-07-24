"""
khayyam_saccheri.py - 空間の分かれ道: ハイヤームと平行線公準 (数学史記)

オマル・ハイヤーム回 の幾何ビート。ハイヤームは『ユークリッド原論の
諸公準の難点についての註解』で、二辺が底辺に垂直な四角形 (のちのサッケーリ・
ハイヤームの四角形) の上辺の二つの角が直角か・鋭角か・鈍角かを初めて体系的に
検討した。だが彼は平行線公準を<証明しよう>として鋭角・鈍角の場合を矛盾として
退け、直角 (ユークリッド) だけを正しいとした ── 分かれ道を最初に描きながら、
二つの扉を自ら閉じた<意図せぬ先駆>。退けた二つが無矛盾な双曲/楕円幾何に
対応すると分かるのは、ずっと後のこと。

Modes:
    quadrilateral - サッケーリ・ハイヤームの四角形。底辺 AB の両端から等しい二辺を
                    垂直に立て、上端 D, C を結ぶ。底辺の両端は直角、上辺の二つの角
                    (頂角) は? という問いを立てる。
                    Fixed params: base AB, equal verticals AD=BC, summit angles at D,C.
    fork          - 三つの場合の分岐。鋭角→双曲幾何 (負に曲がる)、直角→ユークリッド
                    幾何 (平ら)、鈍角→楕円幾何 (正に曲がる)。中央の直角を
                    ハイヤームが選び、両端を退けた。
                    Fixed params: 3 panels (acute/right/obtuse -> hyperbolic/euclid/elliptic).

画面に人名・年号は出さない (narration が担う)。幾何名は固有名詞ではない。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 048 (Omar Khayyam), geometry beat (parallel postulate fork).
"""

import numpy as np
from manim import (
    FadeIn,
    Indicate,
    Line,
    MathTex,
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


def _rt_mark(corner, xdir, ydir, d=0.16, color=TEXT_DIM):
    """Small right-angle square mark at a corner (open L of two short lines)."""
    corner = np.array(corner, dtype=float)
    px = np.array([xdir * d, 0, 0])
    py = np.array([0, ydir * d, 0])
    return VGroup(
        Line(corner + px, corner + px + py, color=color, stroke_width=2),
        Line(corner + py, corner + py + px, color=color, stroke_width=2),
    )


def _bowed_top(d_pt, c_pt, bow, color, stroke=4):
    """Top edge D->C as a curved segment; bow>0 arches up, bow<0 sags down,
    bow=0 straight. Explicit control so the summit-angle sense is deterministic."""
    d_pt = np.array(d_pt, dtype=float)
    c_pt = np.array(c_pt, dtype=float)
    from manim import ParametricFunction

    return ParametricFunction(
        lambda t: (1 - t) * d_pt + t * c_pt + np.array([0.0, bow * np.sin(np.pi * t), 0.0]),
        t_range=[0.0, 1.0, 0.02],
        color=color,
        stroke_width=stroke,
    )


class KhayyamSaccheri(Scene):
    """ハイヤームと平行線公準 ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "quadrilateral")
        self._duration = params.get("duration", 24)

        if mode == "fork":
            self._build_fork()
        else:
            self._build_quadrilateral()

    # ------------------------------------------------------------------
    # Mode: quadrilateral
    # ------------------------------------------------------------------
    def _build_quadrilateral(self):
        duration = self._duration

        title = Text(
            "サッケーリ・ハイヤームの四角形",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])

        note = Text(
            "底辺の両端は直角。では、上の二つの角は ── ?",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note.move_to([0, 2.35, 0])

        a_pt = np.array([-2.0, -1.1, 0.0])
        b_pt = np.array([2.0, -1.1, 0.0])
        d_pt = np.array([-2.0, 1.1, 0.0])
        c_pt = np.array([2.0, 1.1, 0.0])

        base = Line(a_pt, b_pt, color=TEXT_WHITE, stroke_width=4)
        left = Line(a_pt, d_pt, color=ACCENT_CYAN, stroke_width=4)
        right = Line(b_pt, c_pt, color=ACCENT_CYAN, stroke_width=4)
        top = Line(d_pt, c_pt, color=ACCENT_GOLD, stroke_width=4)

        # right-angle marks at base corners
        rt_a = _rt_mark(a_pt, +1, +1)
        rt_b = _rt_mark(b_pt, -1, +1)

        # equal-length ticks on the two verticals
        def _tick(p0, p1):
            mid = (np.array(p0) + np.array(p1)) / 2
            return Line(
                mid + np.array([-0.12, 0, 0]),
                mid + np.array([0.12, 0, 0]),
                color=ACCENT_CYAN,
                stroke_width=3,
            )

        tick_l = _tick(a_pt, d_pt)
        tick_r = _tick(b_pt, c_pt)

        # summit angle question marks at D, C
        qd = Text("？", font=FONT, font_size=40, color=ACCENT_PINK)
        qd.move_to(d_pt + np.array([0.42, -0.42, 0]))
        qc = Text("？", font=FONT, font_size=40, color=ACCENT_PINK)
        qc.move_to(c_pt + np.array([-0.42, -0.42, 0]))

        # vertex labels
        la = Text("A", font=FONT, font_size=24, color=TEXT_DIM).move_to(
            a_pt + np.array([-0.32, -0.28, 0])
        )
        lb = Text("B", font=FONT, font_size=24, color=TEXT_DIM).move_to(
            b_pt + np.array([0.32, -0.28, 0])
        )
        ld = Text("D", font=FONT, font_size=24, color=TEXT_DIM).move_to(
            d_pt + np.array([-0.32, 0.28, 0])
        )
        lc = Text("C", font=FONT, font_size=24, color=TEXT_DIM).move_to(
            c_pt + np.array([0.32, 0.28, 0])
        )

        equal_note = Text("左右の辺は、同じ長さ", font=FONT, font_size=20, color=ACCENT_CYAN)
        equal_note.move_to([0, -1.7, 0])

        anim_time = 0.7 + 0.7 + 0.6 + 0.8 + 0.5 + 0.6 + 0.6 + 0.7
        default_waits = 4.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(base), FadeIn(la), FadeIn(lb), run_time=0.7)
        self.play(FadeIn(left), FadeIn(right), FadeIn(tick_l), FadeIn(tick_r), run_time=0.8)
        self.play(FadeIn(rt_a), FadeIn(rt_b), FadeIn(equal_note), run_time=0.6)
        self.wait(1.0 * ws)
        self.play(FadeIn(top), FadeIn(ld), FadeIn(lc), run_time=0.6)
        self.play(FadeIn(note), run_time=0.7)
        self.play(FadeIn(qd), FadeIn(qc), run_time=0.6)
        self.play(
            Indicate(qd, color=ACCENT_PINK, scale_factor=1.3),
            Indicate(qc, color=ACCENT_PINK, scale_factor=1.3),
            run_time=0.6,
        )
        self.wait(max(1.0, duration - anim_time - 1.0 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: fork
    # ------------------------------------------------------------------
    def _build_fork(self):
        duration = self._duration

        title = Text(
            "三つの分かれ道 ── 上の角は、直角か・鋭角か・鈍角か",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.15, 0])

        # panels: (cx, bow, case, angle_tex, geo_name, descriptor, color)
        # bow<0 sags down -> acute summit; bow>0 arches up -> obtuse summit
        panels = [
            (-4.3, -0.30, "鋭角", r"<90^\circ", "双曲幾何", "負に曲がる面", ACCENT_CYAN),
            (0.0, 0.0, "直角", r"=90^\circ", "ユークリッド幾何", "平らな面", ACCENT_GOLD),
            (4.3, 0.30, "鈍角", r">90^\circ", "楕円幾何", "正に曲がる面", ACCENT_PINK),
        ]

        py0, py1 = -0.15, 1.0
        hw = 1.0

        # gold backdrop behind the chosen (middle) panel
        backdrop = RoundedRectangle(
            width=3.0, height=3.5, corner_radius=0.15, color=ACCENT_GOLD, stroke_width=1.5
        )
        backdrop.move_to([0, 0.55, 0])
        backdrop.set_fill(ACCENT_GOLD, opacity=0.05)
        backdrop.set_stroke(opacity=0.5)

        chosen_tag = Text("ハイヤームが選んだ", font=FONT, font_size=18, color=ACCENT_GOLD)
        chosen_tag.move_to([0, 2.45, 0])

        groups = []
        for cx, bow, case, ang, geo, desc, col in panels:
            a_pt = np.array([cx - hw, py0, 0.0])
            b_pt = np.array([cx + hw, py0, 0.0])
            d_pt = np.array([cx - hw, py1, 0.0])
            c_pt = np.array([cx + hw, py1, 0.0])

            base = Line(a_pt, b_pt, color=TEXT_WHITE, stroke_width=3)
            left = Line(a_pt, d_pt, color=EDGE_COLOR, stroke_width=3)
            right = Line(b_pt, c_pt, color=EDGE_COLOR, stroke_width=3)
            top = _bowed_top(d_pt, c_pt, bow, col, stroke=4)
            rt_a = _rt_mark(a_pt, +1, +1, d=0.13)
            rt_b = _rt_mark(b_pt, -1, +1, d=0.13)

            case_lbl = Text(case, font=FONT, font_size=24, color=col)
            case_lbl.move_to([cx, 2.05, 0])
            ang_lbl = MathTex(ang, font_size=30, color=col)
            ang_lbl.move_to([cx, 1.62, 0])

            geo_lbl = Text(geo, font=FONT, font_size=22, color=col)
            geo_lbl.move_to([cx, -0.62, 0])
            desc_lbl = Text(desc, font=FONT, font_size=18, color=TEXT_DIM)
            desc_lbl.move_to([cx, -1.05, 0])

            fig = VGroup(base, left, right, top, rt_a, rt_b)
            grp = VGroup(case_lbl, ang_lbl, fig, geo_lbl, desc_lbl)
            groups.append(grp)

        banner = Text(
            "ハイヤームは鋭角・鈍角を「矛盾」として退けたが ── 後に、その二つも無矛盾な幾何だと分かる",
            font=FONT,
            font_size=19,
            color=TEXT_WHITE,
        )
        banner.move_to([0, -1.7, 0])

        anim_time = 0.7 + 0.6 + 3 * 0.7 + 0.6 + 0.7
        default_waits = 4.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(backdrop), FadeIn(chosen_tag), run_time=0.6)
        # reveal side panels first, then the chosen middle one
        for idx in (0, 2, 1):
            self.play(FadeIn(groups[idx]), run_time=0.7)
            self.wait(0.7 * ws)
        self.play(FadeIn(banner), run_time=0.6)
        self.play(Indicate(groups[1][2], color=ACCENT_GOLD, scale_factor=1.08), run_time=0.7)
        self.wait(max(1.0, duration - anim_time - 2.1 * ws - 0.7))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years; geometry names are not proper nouns.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "quadrilateral": {"people": [], "years": []},
    "fork": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "quadrilateral": KhayyamSaccheri,
    "fork": KhayyamSaccheri,
}
