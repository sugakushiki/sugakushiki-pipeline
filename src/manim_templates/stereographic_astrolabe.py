"""
stereographic_astrolabe.py - The astrolabe and stereographic projection

Visualizes the mathematics behind the plane astrolabe, whose construction
Hypatia of Alexandria taught to her student Synesius of Cyrene (she guided its
making but did NOT invent it). The astrolabe is based on the stereographic
projection of the celestial sphere onto a plane, projected from the south
celestial pole onto the plane of the equator; this projection maps circles on
the sphere to circles on the plane and preserves angles (it is conformal).

Modes:
    projection - 2D cross-section: the celestial sphere, the south pole S as the
                 projection point, the equatorial plane as a horizontal line,
                 and a latitude circle on the sphere projected through S onto a
                 circle on the plane. Property note: 円 -> 円, angle-preserving.
                 Fixed params: sphere radius 1.55 centred [-1.6, 0.65];
                 plane at y=0.65; south pole at [-1.6, -0.90].
    astrolabe  - The resulting flat disk (tympanum): the limb, the equator and
                 the two tropic circles (concentric), an off-centre horizon
                 circle, the north celestial pole at the centre, a few star
                 points and a rule, with a colour-coded legend.
                 Fixed params: disk centre [-1.3, 0.55], limb radius 1.90.

No people or years are drawn on screen (narration carries the names and dates).
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 032 (Hypatia), astronomy / stereographic-projection pillar.
"""

import math

import numpy as np
from manim import (
    Circle,
    DashedLine,
    Dot,
    Ellipse,
    FadeIn,
    Line,
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


class StereographicAstrolabe(Scene):
    """The plane astrolabe and the stereographic projection behind it."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 12)
        mode = params.get("mode", "projection")

        if mode == "astrolabe":
            self._build_astrolabe()
        else:
            self._build_projection()

    # ------------------------------------------------------------------
    # Mode: projection
    # ------------------------------------------------------------------
    def _build_projection(self):
        duration = self._duration

        title = Text(
            "アストロラーベの原理 ── 平射図法",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        R = 1.55
        sc = np.array([-1.6, 0.65, 0.0])
        plane_y = sc[1]
        south = np.array([sc[0], sc[1] - R, 0.0])

        sphere = Circle(radius=R, color=ACCENT_CYAN, stroke_width=2.5)
        sphere.move_to(sc)

        plane = Line([-3.5, plane_y, 0], [4.9, plane_y, 0], color=EDGE_COLOR, stroke_width=2)
        plane_lbl = Text("投影面", font=FONT, font_size=20, color=TEXT_DIM)
        plane_lbl.move_to([4.0, plane_y - 0.32, 0])

        north_dot = Dot(sc + np.array([0, R, 0]), color=TEXT_DIM, radius=0.06)
        south_dot = Dot(south, color=ACCENT_GOLD, radius=0.10)
        south_lbl = Text("天の南極（投影の点）", font=FONT, font_size=18, color=ACCENT_GOLD)
        south_lbl.move_to([-1.6, south[1] - 0.33, 0])

        # A latitude circle on the sphere (a horizontal chord in cross-section).
        lat_y = 1.25
        dx = math.sqrt(max(R * R - (lat_y - sc[1]) ** 2, 0.0))
        e_right = np.array([sc[0] + dx, lat_y, 0.0])
        e_left = np.array([sc[0] - dx, lat_y, 0.0])
        lat_circle = Ellipse(width=2 * dx, height=0.30, color=ACCENT_GOLD, stroke_width=2.5)
        lat_circle.move_to([sc[0], lat_y, 0])

        # Project the two endpoints through the south pole onto the plane.
        def _project(p):
            d = p - south
            t = (plane_y - south[1]) / d[1]
            return south + t * d

        p_right = _project(e_right)
        p_left = _project(e_left)
        img_w = abs(p_right[0] - p_left[0])
        img_circle = Ellipse(width=img_w, height=0.26, color=ACCENT_GOLD, stroke_width=3)
        img_circle.move_to([sc[0], plane_y, 0])

        ray_r = DashedLine(south, e_right, color=ACCENT_PINK, stroke_width=1.6)
        ray_l = DashedLine(south, e_left, color=ACCENT_PINK, stroke_width=1.6)

        d_er = Dot(e_right, color=ACCENT_GOLD, radius=0.05)
        d_el = Dot(e_left, color=ACCENT_GOLD, radius=0.05)
        d_pr = Dot(p_right, color=ACCENT_GOLD, radius=0.05)
        d_pl = Dot(p_left, color=ACCENT_GOLD, radius=0.05)

        prop = Text(
            "球面上の円 → 平面上の円（角度を保つ）",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        prop.move_to([0.0, -1.55, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(sphere), FadeIn(plane), FadeIn(plane_lbl), run_time=0.9)
        self.play(FadeIn(north_dot), FadeIn(south_dot), FadeIn(south_lbl), run_time=0.7)
        self.play(FadeIn(lat_circle), FadeIn(d_er), FadeIn(d_el), run_time=0.7)
        self.play(FadeIn(ray_r), FadeIn(ray_l), run_time=0.7)
        self.play(FadeIn(img_circle), FadeIn(d_pr), FadeIn(d_pl), run_time=0.7)
        self.play(FadeIn(prop), run_time=0.7)

        anim_overhead = 0.7 + 0.9 + 0.7 + 0.7 + 0.7 + 0.7 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: astrolabe
    # ------------------------------------------------------------------
    def _build_astrolabe(self):
        duration = self._duration

        title = Text(
            "平面アストロラーベ ── 天球を写した円盤",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        o = np.array([-1.3, 0.55, 0.0])

        limb = Circle(radius=1.90, color=ACCENT_GOLD, stroke_width=3)
        limb.move_to(o)
        capricorn = Circle(radius=1.74, color=TEXT_DIM, stroke_width=1.6)
        capricorn.move_to(o)
        equator = Circle(radius=1.12, color=ACCENT_CYAN, stroke_width=2.5)
        equator.move_to(o)
        cancer = Circle(radius=0.58, color=TEXT_DIM, stroke_width=1.6)
        cancer.move_to(o)

        pole_dot = Dot(o, color=ACCENT_GOLD, radius=0.07)

        # Off-centre horizon circle (projection of the local horizon).
        horizon = Circle(radius=0.92, color=ACCENT_PINK, stroke_width=2.5)
        horizon.move_to(o + np.array([0.0, 0.62, 0.0]))

        # A rule (alidade) and a few star pointers (a hint of the rete).
        rule = Line(
            o + np.array([-1.55, -0.95, 0]),
            o + np.array([1.55, 0.95, 0]),
            color=TEXT_WHITE,
            stroke_width=1.8,
        )
        stars = VGroup()
        for ang, rad in [(40, 1.45), (135, 0.95), (210, 1.55), (300, 0.7), (95, 1.3)]:
            p = o + np.array(
                [rad * math.cos(math.radians(ang)), rad * math.sin(math.radians(ang)), 0.0]
            )
            stars.add(Dot(p, color=ACCENT_GOLD, radius=0.045))

        # Colour-coded legend on the right.
        legend = VGroup()
        items = [
            ("天の北極", ACCENT_GOLD),
            ("赤道", ACCENT_CYAN),
            ("回帰線", TEXT_DIM),
            ("地平線", ACCENT_PINK),
        ]
        lx = 2.7
        ly0 = 1.5
        for i, (txt, col) in enumerate(items):
            y = ly0 - i * 0.62
            swatch = Dot([lx, y, 0], color=col, radius=0.08)
            lbl = Text(txt, font=FONT, font_size=22, color=col)
            lbl.next_to(swatch, np.array([1, 0, 0]), buff=0.22)
            legend.add(swatch, lbl)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(limb), FadeIn(pole_dot), run_time=0.7)
        self.play(FadeIn(capricorn), FadeIn(equator), FadeIn(cancer), run_time=0.9)
        self.play(FadeIn(horizon), FadeIn(rule), FadeIn(stars), run_time=0.8)
        self.play(FadeIn(legend), run_time=0.8)

        anim_overhead = 0.7 + 0.7 + 0.9 + 0.8 + 0.8
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "projection": {"people": [], "years": []},
    "astrolabe": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "projection": {
        "class": "StereographicAstrolabe",
        "params": {"mode": "projection"},
        "description": "Stereographic projection from the south pole: a circle on the sphere maps to a circle on the plane",
    },
    "astrolabe": {
        "class": "StereographicAstrolabe",
        "params": {"mode": "astrolabe"},
        "description": "The plane astrolabe tympanum: limb, equator, tropics, off-centre horizon, celestial pole",
    },
}
