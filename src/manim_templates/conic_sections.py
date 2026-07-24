"""
conic_sections.py - Apollonius's conic sections for 数学史記

Visualizes the conic sections that Apollonius of Perga (c. 262-190 BC)
systematized and named in his Conica (8 books), and on which Hypatia of
Alexandria wrote a (now lost) commentary. One double cone, cut by a plane at
different angles, yields the circle, ellipse, parabola and hyperbola.

Modes:
    cone_cut    - Four shaded double cones in a row (translucent nappes with a
                  curved elliptical base, front-solid / back-dashed rims, dashed
                  axis), each cut at a different angle with the resulting
                  cross-section drawn ON the cone surface (horizontal sections
                  wrap the cone: near edge solid, far edge dashed): horizontal
                  cut -> circle (円), oblique cut -> ellipse (楕円) anchored on
                  the two slant edges, cut parallel to the slant edge ->
                  parabola (放物線) opening toward the base, cut parallel to the
                  axis through both nappes -> hyperbola (双曲線).
                  Fixed params: apex y=0.50, nappe half-height H=1.25,
                  half-width W=0.82, rim semi-minor 0.16, four cones at
                  x = -5.05, -1.7, 1.65, 5.0.
    four_curves - The four curves drawn larger with foci / directrix / asymptote
                  detail, each with its Japanese name and the Greek origin of the
                  latter three: ellipse = 不足 (ellipsis), parabola = 一致
                  (parabole), hyperbola = 超過 (hyperbole).

No people or years are drawn on screen (narration carries Apollonius and dates).
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 032 (Hypatia), conic-sections / Greek-geometry pillar.
"""

import math

import numpy as np
from manim import (
    Circle,
    DashedLine,
    DashedVMobject,
    Dot,
    Ellipse,
    FadeIn,
    Line,
    ParametricFunction,
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

# Shared double-cone geometry (scene units)
APEX_Y = 0.50
NAPPE_H = 1.25
NAPPE_W = 0.82
RIM_RY = 0.16  # perspective semi-minor axis of a horizontal circle on the cone
FORESHORTEN = RIM_RY / NAPPE_W  # vertical squash of a horizontal circle
CONE_FILL = "#3a4a66"  # neutral slate so coloured sections pop


def _ellipse_arc(cx, cy, rx, ry, a0, a1, color, stroke):
    return ParametricFunction(
        lambda a: np.array([cx + rx * math.cos(a), cy + ry * math.sin(a), 0.0]),
        t_range=[a0, a1, 0.05],
        color=color,
        stroke_width=stroke,
    )


def _disk(cx, cy, hw, color, fill_op, stroke):
    """A horizontal circle on the cone, drawn in perspective: near (front, lower)
    arc solid, far (back, upper) arc dashed, optional translucent fill."""
    ry = hw * FORESHORTEN
    g = VGroup()
    if fill_op > 0:
        e = Ellipse(width=2 * hw, height=2 * ry)
        e.move_to([cx, cy, 0])
        e.set_fill(color, opacity=fill_op)
        e.set_stroke(width=0)
        g.add(e)
    back = DashedVMobject(_ellipse_arc(cx, cy, hw, ry, 0, math.pi, color, stroke), num_dashes=16)
    front = _ellipse_arc(cx, cy, hw, ry, math.pi, 2 * math.pi, color, stroke)
    g.add(back, front)
    return g


def _shaded_cone(cx):
    """A shaded double cone: curved elliptical base, slant edges, perspective
    rims (front solid / back dashed), dashed axis, apex dot."""
    g = VGroup()
    apex = np.array([cx, APEX_Y, 0.0])
    for s in (1, -1):
        ry_rim = APEX_Y + s * NAPPE_H
        # solid silhouette = apex + the near (bottom) arc of the rim ellipse
        arc = [
            np.array([cx + NAPPE_W * math.cos(a), ry_rim + RIM_RY * math.sin(a), 0.0])
            for a in np.linspace(math.pi, 2 * math.pi, 24)
        ]
        body = Polygon(apex, *arc, stroke_width=0)
        body.set_fill(CONE_FILL, opacity=0.5)
        g.add(body)
        g.add(Line(apex, [cx - NAPPE_W, ry_rim, 0], color=EDGE_COLOR, stroke_width=2))
        g.add(Line(apex, [cx + NAPPE_W, ry_rim, 0], color=EDGE_COLOR, stroke_width=2))
        g.add(_disk(cx, ry_rim, NAPPE_W, EDGE_COLOR, 0, 2))
    g.add(
        DashedLine(
            [cx, APEX_Y + NAPPE_H + 0.22, 0],
            [cx, APEX_Y - NAPPE_H - 0.22, 0],
            color=TEXT_DIM,
            stroke_width=1.1,
            dash_length=0.08,
        )
    )
    g.add(Dot(apex, color=TEXT_DIM, radius=0.03))
    return g


def _half_width_at(dy):
    return NAPPE_W * min(abs(dy) / NAPPE_H, 1.0)


def _parabolic_face(cx, vx, vy, k, phi, t0, t1, opening, color, fill_op):
    """A translucent planar cut face whose curved boundary is a parabola/branch
    (vertex near the apex) and whose straight 'mouth' is the edge where the plane
    exits through the cone's base (rim). opening=+1 opens up, -1 opens down."""
    cphi, sphi = math.cos(phi), math.sin(phi)

    def _p(t):
        lx, ly = t, opening * k * t * t
        return np.array([vx + lx * cphi - ly * sphi, vy + lx * sphi + ly * cphi, 0.0])

    pts = [_p(t) for t in np.linspace(t0, t1, 30)]
    fill = Polygon(*pts, stroke_width=0)
    fill.set_fill(color, opacity=fill_op)
    arc = ParametricFunction(_p, t_range=[t0, t1, 0.03], color=color, stroke_width=4)
    mouth = DashedVMobject(Line(pts[0], pts[-1], color=color, stroke_width=2.5), num_dashes=12)
    return VGroup(fill, mouth, arc)


class ConicSections(Scene):
    """Apollonius's conic sections: one cone, four curves."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 12)
        mode = params.get("mode", "cone_cut")

        if mode == "four_curves":
            self._build_four_curves()
        else:
            self._build_cone_cut()

    # ------------------------------------------------------------------
    # Mode: cone_cut
    # ------------------------------------------------------------------
    def _build_cone_cut(self):
        duration = self._duration

        title = Text(
            "一つの円錐 ── 切る角度で四つの曲線",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])

        centres = [-5.05, -1.7, 1.65, 5.0]
        names = ["円", "楕円", "放物線", "双曲線"]
        colors = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK, TEXT_WHITE]

        cones = VGroup()
        sections = VGroup()
        labels = VGroup()
        for cx, name, col in zip(centres, names, colors, strict=False):
            cones.add(_shaded_cone(cx))
            sections.add(self._section(cx, name, col))
            lbl = Text(name, font=FONT, font_size=28, color=col)
            lbl.move_to([cx, APEX_Y - NAPPE_H - 0.58, 0])
            labels.add(lbl)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(cones), run_time=1.2)
        self.play(FadeIn(sections), run_time=1.0)
        self.play(FadeIn(labels), run_time=0.8)

        anim_overhead = 0.7 + 1.2 + 1.0 + 0.8
        self.wait(max(1.0, duration - anim_overhead))

    def _edge_point(self, cx, y, side):
        """Point at height y on the left (-1) or right (+1) slant edge."""
        return np.array([cx + side * NAPPE_W * (y - APEX_Y) / NAPPE_H, y, 0.0])

    def _section(self, cx, name, col):
        if name == "円":
            # horizontal cut -> circle, wraps the cone (front solid / back dashed)
            yy = APEX_Y + 0.72
            hw = _half_width_at(0.72)
            return _disk(cx, yy, hw, col, 0.26, 4)
        if name == "楕円":
            # oblique cut -> ellipse anchored on the two slant edges
            p1 = self._edge_point(cx, 0.98, -1)
            p2 = self._edge_point(cx, 1.52, +1)
            centre = (p1 + p2) / 2
            d = p2 - p1
            a = math.hypot(d[0], d[1]) / 2
            ang = math.atan2(d[1], d[0])
            e = Ellipse(width=2 * a, height=0.40, color=col, stroke_width=4)
            e.set_fill(col, opacity=0.24)
            e.rotate(ang)
            e.move_to(centre)
            return e
        if name == "放物線":
            # cut parallel to a slant edge -> a tilted planar face; the parabola
            # arms reach the top rim (base), where the mouth (base edge) sits.
            return _parabolic_face(
                cx, cx - 0.05, APEX_Y + 0.32, 2.3, -0.08, -0.62, 0.62, +1, col, 0.22
            )
        # 双曲線: cut parallel to the axis -> two planar faces, one per nappe,
        # each reaching its rim; vertices face each other across the apex
        upper = _parabolic_face(cx, cx, APEX_Y + 0.40, 1.9, 0.0, -0.65, 0.65, +1, col, 0.18)
        lower = _parabolic_face(cx, cx, APEX_Y - 0.40, 1.9, 0.0, -0.65, 0.65, -1, col, 0.18)
        return VGroup(upper, lower)

    # ------------------------------------------------------------------
    # Mode: four_curves
    # ------------------------------------------------------------------
    def _build_four_curves(self):
        duration = self._duration

        title = Text(
            "アポロニウスが名づけた四つの曲線",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])

        cols = [-5.1, -1.7, 1.7, 5.1]
        cy = 1.05
        names = ["円", "楕円", "放物線", "双曲線"]
        roots = ["", "不足（ellipsis）", "一致（parabole）", "超過（hyperbole）"]
        name_colors = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK, TEXT_WHITE]

        glyphs = VGroup()

        c0 = cols[0]
        circ = Circle(radius=0.78, color=ACCENT_CYAN, stroke_width=4)
        circ.set_fill(ACCENT_CYAN, opacity=0.10)
        circ.move_to([c0, cy, 0])
        r_line = Line([c0, cy, 0], [c0 + 0.78, cy, 0], color=ACCENT_CYAN, stroke_width=2)
        glyphs.add(circ, Dot([c0, cy, 0], color=ACCENT_CYAN, radius=0.05), r_line)

        c1 = cols[1]
        a_e, b_e = 0.95, 0.62
        ce_e = math.sqrt(a_e * a_e - b_e * b_e)
        ell = Ellipse(width=2 * a_e, height=2 * b_e, color=ACCENT_GOLD, stroke_width=4)
        ell.set_fill(ACCENT_GOLD, opacity=0.10)
        ell.move_to([c1, cy, 0])
        f1 = Dot([c1 - ce_e, cy, 0], color=ACCENT_GOLD, radius=0.05)
        f2 = Dot([c1 + ce_e, cy, 0], color=ACCENT_GOLD, radius=0.05)
        glyphs.add(ell, f1, f2)

        c2 = cols[2]
        a_p = 0.95
        par = ParametricFunction(
            lambda t: np.array([c2 + t, cy - 0.5 + a_p * t * t, 0.0]),
            t_range=[-0.92, 0.92, 0.03],
            color=ACCENT_PINK,
            stroke_width=4,
        )
        focus = Dot([c2, cy - 0.5 + 1.0 / (4 * a_p), 0], color=ACCENT_PINK, radius=0.05)
        directrix = Line(
            [c2 - 0.95, cy - 0.5 - 1.0 / (4 * a_p), 0],
            [c2 + 0.95, cy - 0.5 - 1.0 / (4 * a_p), 0],
            color=TEXT_DIM,
            stroke_width=1.6,
        )
        glyphs.add(par, focus, directrix)

        c3 = cols[3]
        # up/down opening hyperbola (vertical), matching the cone_cut section
        a_v, b_v, half_h = 0.40, 0.42, 1.38
        hyp = VGroup(
            ParametricFunction(
                lambda t: np.array([c3 + b_v * math.sinh(t), cy + a_v * math.cosh(t), 0.0]),
                t_range=[-half_h, half_h, 0.04],
                color=TEXT_WHITE,
                stroke_width=4,
            ),
            ParametricFunction(
                lambda t: np.array([c3 + b_v * math.sinh(t), cy - a_v * math.cosh(t), 0.0]),
                t_range=[-half_h, half_h, 0.04],
                color=TEXT_WHITE,
                stroke_width=4,
            ),
        )
        x_end = b_v * math.sinh(half_h)
        sl = a_v / b_v
        asym = VGroup(
            DashedLine(
                [c3 - x_end, cy - sl * x_end, 0],
                [c3 + x_end, cy + sl * x_end, 0],
                color=TEXT_DIM,
                stroke_width=1.3,
            ),
            DashedLine(
                [c3 - x_end, cy + sl * x_end, 0],
                [c3 + x_end, cy - sl * x_end, 0],
                color=TEXT_DIM,
                stroke_width=1.3,
            ),
        )
        glyphs.add(asym, hyp)

        name_lbls = VGroup()
        root_lbls = VGroup()
        for cx, name, root, col in zip(cols, names, roots, name_colors, strict=False):
            nl = Text(name, font=FONT, font_size=28, color=col)
            nl.move_to([cx, -0.45, 0])
            name_lbls.add(nl)
            if root:
                rl = Text(root, font=FONT, font_size=19, color=TEXT_DIM)
                rl.move_to([cx, -0.98, 0])
                root_lbls.add(rl)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(glyphs), run_time=1.2)
        self.play(FadeIn(name_lbls), run_time=0.7)
        self.play(FadeIn(root_lbls), run_time=0.8)

        anim_overhead = 0.7 + 1.2 + 0.7 + 0.8
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "cone_cut": {"people": [], "years": []},
    "four_curves": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "cone_cut": {
        "class": "ConicSections",
        "params": {"mode": "cone_cut"},
        "description": "Four shaded double cones cut at four angles, each with its cross-section drawn on the cone (circle, ellipse, parabola, hyperbola)",
    },
    "four_curves": {
        "class": "ConicSections",
        "params": {"mode": "four_curves"},
        "description": "The four conic curves with foci/directrix/asymptotes and Greek etymology (deficiency/equality/excess)",
    },
}
