"""
rigid_body_integrable.py - The three integrable tops (Sofya Kovalevskaya)

Episode 047 (Sofya Kovalevskaya). Intuition-level visuals for the rotation of a
rigid body (a spinning top) about a fixed point under gravity, and the three
cases in which the motion is fully integrable ("solvable"): Euler, Lagrange, and
Kovalevskaya. No proofs -- the top is drawn as a recognizable spinning-top
silhouette (a body tapering to a point at the pivot, with a flywheel disk and a
stem) and the defining conditions (moment-of-inertia relations, where the center
of mass sits) are shown as static labels built up by staged reveals (no
time-filler motion). The Kovalevskaya case (I1=I2=2*I3, center of mass off the
symmetry axis in the equatorial plane) is the payoff.

Modes:
    top (default)
        A single tilted spinning top on its pivot (left): tip = fixed point,
        symmetry axis, flywheel disk, center of mass. Poses the question (right,
        spaced text): the motion can be written as equations, but only special
        tops can actually be "solved".
        Fixed params: pivot (tip) at cx=-3.2, y=-1.0; axis tilt 20 deg, length
        2.35; flywheel disk / center of mass at axis fraction 0.40.
        On screen: no proper nouns.
    euler
        The Euler case: the fixed point coincides with the center of mass, so
        gravity exerts no torque -- a free rotation of a symmetric body about its
        own centre. Moments of inertia unrestricted.
        Fixed params: torque tau = 0; body centre = fixed point; tilt 20 deg.
        On screen: name Euler (オイラー).
    lagrange
        The Lagrange case: a symmetric top on its pivot, two equal moments
        (I1=I2, not I3), center of mass on the symmetry axis -> regular
        precession.
        Fixed params: I1=I2 != I3; center of mass on axis (disk centre);
        tip on the pivot; tilt 20 deg.
        On screen: name Lagrange (ラグランジュ).
    kovalevskaya
        The Kovalevskaya case (payoff): I1=I2=2*I3 (two moments each TWICE the
        third) and the center of mass lies OFF the symmetry axis, in the
        equatorial plane (the flywheel-disk plane). The third -- and, for
        arbitrary initial conditions, the last general -- integrable case.
        Fixed params: I1=I2=2*I3; center of mass off-axis 0.45 along the
        equatorial (disk) direction; tip on the pivot; tilt 20 deg.
        On screen: name Kovalevskaya (コワレフスカヤ).

All Text uses FONT (BIZ UDMincho). MathTex holds LaTeX only (no Japanese).
Y range: about -1.75 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    Arrow,
    Create,
    DashedLine,
    Dot,
    Ellipse,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Polygon,
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

_L = 2.35  # symmetry-axis length (pivot tip -> stem top)
_PIVOT_Y = -1.0  # pivot (tip) height
_DISK_F = 0.40  # axis fraction of the flywheel disk / center of mass


def _geom(cx, tilt_deg):
    """Geometry for a top pivoted (tip) at (cx, _PIVOT_Y), tilted tilt_deg."""
    tr = np.radians(tilt_deg)
    p = np.array([cx, _PIVOT_Y, 0.0])
    axdir = np.array([np.sin(tr), np.cos(tr), 0.0])
    perp = np.array([np.cos(tr), -np.sin(tr), 0.0])  # equatorial direction
    axtop = p + _L * axdir
    disk_c = p + _DISK_F * _L * axdir  # flywheel / on-axis CoM
    return dict(p=p, tr=tr, axdir=axdir, perp=perp, axtop=axtop, disk_c=disk_c)


def _top_silhouette(g, color):
    """A recognizable spinning-top silhouette along the tilted axis."""
    p, axdir, perp, tr = g["p"], g["axdir"], g["perp"], g["tr"]

    def pt(f, s):
        return p + f * _L * axdir + s * perp

    outline = Polygon(
        pt(0.0, 0.0),
        pt(0.40, 0.62),
        pt(0.58, 0.28),
        pt(0.70, 0.0),
        pt(0.58, -0.28),
        pt(0.40, -0.62),
        color=color,
        stroke_width=3,
    )
    outline.set_fill(color, opacity=0.13)
    disk = Ellipse(width=1.24, height=0.26, color=color, stroke_width=2)
    disk.rotate(-tr)
    disk.move_to(g["disk_c"])
    stem = Line(pt(0.70, 0.0), pt(0.96, 0.0), color=color, stroke_width=3)
    return VGroup(outline, disk, stem)


class RigidBodyIntegrable(Scene):
    """The three integrable tops -- four intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "top")
        duration = float(params.get("duration", 28))
        if mode == "euler":
            self._build_euler(duration)
        elif mode == "lagrange":
            self._build_case(duration, "lagrange")
        elif mode == "kovalevskaya":
            self._build_case(duration, "kovalevskaya")
        else:
            self._build_top(duration)

    # helper: staged reveals scaled to span the scene ("information appearing"),
    # then a short constant coda. No time-filler motion.
    def _finish(self, plays, duration, used, coda=2.2):
        base = sum(rt for _, rt in plays)
        body = max(base, duration - used - coda)
        scale = min(body / base, 4.5) if base > 0 else 1.0
        for mobs, rt in plays:
            self.play(*mobs, run_time=rt * scale)
        leftover = duration - used - base * scale - coda
        if leftover > 0.4:
            self.wait(min(leftover, coda))
        self.wait(coda)

    # ---------------------------------------------------------------------- top
    def _build_top(self, duration):
        title = Text("回る独楽 ── いつ「解ける」のか", font=FONT, font_size=27, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        g = _geom(-3.2, 20.0)
        vertical = DashedLine(
            g["p"], g["p"] + np.array([0, _L, 0]), color=EDGE_COLOR, stroke_width=1.5
        )
        top = _top_silhouette(g, ACCENT_GOLD)
        axis = Line(g["p"], g["axtop"], color=ACCENT_CYAN, stroke_width=3)
        pivot = Dot(g["p"], color=TEXT_WHITE, radius=0.09)
        com = Dot(g["disk_c"], color=ACCENT_PINK, radius=0.10)

        l_pivot = Text("支点", font=FONT, font_size=19, color=TEXT_WHITE).move_to([-4.15, -1.0, 0])
        l_axis = Text("対称軸", font=FONT, font_size=19, color=ACCENT_CYAN).move_to([-1.5, 1.2, 0])
        l_com = Text("重心", font=FONT, font_size=19, color=ACCENT_PINK).move_to([-1.55, -0.12, 0])

        t1 = Text("運動の方程式は、書ける。", font=FONT, font_size=23, color=TEXT_WHITE)
        t1.move_to([2.95, 1.35, 0])
        t2 = Text("でも《解ける》形にできるのは", font=FONT, font_size=21, color=TEXT_DIM)
        t2.move_to([2.95, 0.45, 0])
        t3 = Text("ごく特別な独楽だけ。", font=FONT, font_size=23, color=ACCENT_GOLD)
        t3.move_to([2.95, -0.25, 0])
        caption = Text(
            "固定点のまわりで、重力を受けて回る剛体", font=FONT, font_size=19, color=TEXT_DIM
        )
        caption.move_to([0, -1.72, 0])

        plays = [
            ([FadeIn(vertical), FadeIn(pivot), FadeIn(l_pivot)], 0.9),
            ([Create(top), Create(axis), FadeIn(l_axis)], 1.3),
            ([FadeIn(com), FadeIn(l_com)], 1.0),
            ([FadeIn(t1)], 1.0),
            ([FadeIn(t2), FadeIn(t3)], 1.2),
            ([FadeIn(caption)], 0.8),
        ]
        self._finish(plays, duration, used=0.7)

    # -------------------------------------------------------------------- euler
    def _build_euler(self, duration):
        title = Text(
            "オイラーの場合 ── 重力が効かない、自由な回転",
            font=FONT,
            font_size=25,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        cx = -3.2
        center = np.array([cx, 0.2, 0.0])
        tr = np.radians(20.0)
        axdir = np.array([np.sin(tr), np.cos(tr), 0.0])
        # a symmetric body spinning freely about its own centre (ellipsoid)
        body = Ellipse(width=1.7, height=1.0, color=ACCENT_GOLD, stroke_width=3)
        body.set_fill(ACCENT_GOLD, opacity=0.13)
        body.rotate(-tr)
        body.move_to(center)
        equator = Ellipse(width=1.7, height=0.42, color=ACCENT_GOLD, stroke_width=2)
        equator.rotate(-tr)
        equator.move_to(center)
        axis = Line(center - 1.35 * axdir, center + 1.35 * axdir, color=ACCENT_CYAN, stroke_width=3)
        fixed = Dot(center, color=TEXT_WHITE, radius=0.10)
        l_fixed = Text("支点＝重心", font=FONT, font_size=18, color=TEXT_WHITE)
        l_fixed.move_to([cx - 0.05, -1.2, 0])

        cond = MathTex(r"\tau = 0", font_size=48, color=ACCENT_CYAN).move_to([2.9, 1.65, 0])
        l_cond = Text("重力のトルクが、ゼロ", font=FONT, font_size=20, color=TEXT_WHITE)
        l_cond.move_to([2.9, 0.95, 0])
        line1 = Text("支点が重心に一致するので", font=FONT, font_size=19, color=TEXT_WHITE)
        line1.move_to([2.9, 0.25, 0])
        line2 = Text("重力の効果が消える", font=FONT, font_size=19, color=TEXT_WHITE)
        line2.move_to([2.9, -0.3, 0])
        line3 = Text("慣性モーメントは、自由でよい", font=FONT, font_size=18, color=TEXT_DIM)
        line3.move_to([2.9, -0.85, 0])
        bottom = Text("解ける第一の場合 ── 自由な回転", font=FONT, font_size=20, color=ACCENT_GOLD)
        bottom.move_to([0, -1.68, 0])

        plays = [
            ([Create(body), Create(equator), Create(axis)], 1.2),
            ([FadeIn(fixed), FadeIn(l_fixed)], 0.9),
            ([FadeIn(cond), FadeIn(l_cond)], 1.1),
            ([FadeIn(line1)], 0.9),
            ([FadeIn(line2)], 0.9),
            ([FadeIn(line3)], 0.9),
            ([FadeIn(bottom)], 0.9),
        ]
        self._finish(plays, duration, used=0.7)

    # --------------------------------------------------- lagrange / kovalevskaya
    def _build_case(self, duration, kind):
        if kind == "lagrange":
            title = Text(
                "ラグランジュの場合 ── 軸対称の独楽", font=FONT, font_size=26, color=ACCENT_GOLD
            )
            cond = MathTex(r"I_1 = I_2 \neq I_3", font_size=40, color=ACCENT_CYAN)
            l1 = "二つの慣性モーメントが等しい"
            l2 = "重心が、対称軸の上にある"
            l3 = "→ 規則的な歳差運動"
            l3_col = ACCENT_GOLD
            bottom_txt = "解ける第二の場合 ── 対称の独楽"
            bottom_col = ACCENT_GOLD
            com_col = ACCENT_PINK
        else:
            title = Text(
                "コワレフスカヤの場合 ── 第三の《解ける》独楽",
                font=FONT,
                font_size=24,
                color=ACCENT_PINK,
            )
            cond = MathTex(r"I_1 = I_2 = 2\,I_3", font_size=40, color=ACCENT_GOLD)
            l1 = "二つが、三つ目のちょうど2倍"
            l2 = "重心が対称軸を外れ、赤道面の中に"
            l3 = "→ 誰も見つけられなかった場合"
            l3_col = ACCENT_PINK
            bottom_txt = "任意の初期条件で解ける、最後の一般の場合"
            bottom_col = ACCENT_GOLD
            com_col = ACCENT_PINK
        title.move_to([0, 3.05, 0])
        cond.move_to([2.9, 1.7, 0])
        self.play(FadeIn(title), run_time=0.7)

        g = _geom(-3.2, 20.0)
        vertical = DashedLine(
            g["p"], g["p"] + np.array([0, _L, 0]), color=EDGE_COLOR, stroke_width=1.5
        )
        top = _top_silhouette(g, ACCENT_GOLD)
        axis = Line(g["p"], g["axtop"], color=ACCENT_CYAN, stroke_width=3)
        pivot = Dot(g["p"], color=TEXT_WHITE, radius=0.09)

        if kind == "lagrange":
            com_pt = g["disk_c"]
        else:
            com_pt = g["disk_c"] + 0.45 * g["perp"]
        com = Dot(com_pt, color=com_col, radius=0.10)
        grav = Arrow(
            com_pt,
            com_pt + np.array([0, -0.55, 0]),
            color=TEXT_DIM,
            stroke_width=3,
            buff=0.02,
            max_tip_length_to_length_ratio=0.4,
        )
        l_com = Text("重心", font=FONT, font_size=18, color=com_col)

        extras = []
        if kind == "kovalevskaya":
            # equatorial plane = the flywheel-disk plane (through disk_c, along perp)
            e0 = g["disk_c"] - 1.0 * g["perp"]
            e1 = g["disk_c"] + 1.15 * g["perp"]
            equator = DashedLine(e0, e1, color=ACCENT_PINK, stroke_width=2)
            l_eq = Text("赤道面", font=FONT, font_size=16, color=ACCENT_PINK)
            l_eq.move_to(e1 + np.array([0.5, 0.02, 0]))
            l_com.move_to(com_pt + np.array([0.5, 0.24, 0]))
            extras = [([Create(equator), FadeIn(l_eq)], 1.0)]
        else:
            l_com.move_to(com_pt + np.array([1.05, 0.12, 0]))

        t1 = Text(l1, font=FONT, font_size=20, color=TEXT_WHITE).move_to([2.9, 0.85, 0])
        t2 = Text(l2, font=FONT, font_size=19, color=TEXT_WHITE).move_to([2.9, 0.28, 0])
        t3 = Text(l3, font=FONT, font_size=19, color=l3_col).move_to([2.9, -0.4, 0])
        bottom = Text(bottom_txt, font=FONT, font_size=19, color=bottom_col)
        bottom.move_to([0, -1.68, 0])

        plays = [
            ([FadeIn(vertical), FadeIn(pivot)], 0.8),
            ([Create(top), Create(axis)], 1.3),
            ([FadeIn(com), FadeIn(l_com), FadeIn(grav)], 1.0),
        ]
        plays += extras
        plays += [
            ([FadeIn(cond)], 1.0),
            ([FadeIn(t1)], 0.9),
            ([FadeIn(t2)], 0.9),
            ([FadeIn(t3), Indicate(cond, color=l3_col, scale_factor=1.1)], 1.1),
            ([FadeIn(bottom)], 0.9),
        ]
        self._finish(plays, duration, used=0.7)


LINT_FACTUAL_CLAIMS = {
    "top": {"people": [], "years": []},
    "euler": {"people": [["オイラー", "Euler"]], "years": []},
    "lagrange": {"people": [["ラグランジュ", "Lagrange"]], "years": []},
    "kovalevskaya": {"people": [["コワレフスカヤ", "Kovalevskaya"]], "years": []},
}

SCENES = {
    "top": RigidBodyIntegrable,
    "euler": RigidBodyIntegrable,
    "lagrange": RigidBodyIntegrable,
    "kovalevskaya": RigidBodyIntegrable,
}
