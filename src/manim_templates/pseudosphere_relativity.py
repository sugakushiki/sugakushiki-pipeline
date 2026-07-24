"""
pseudosphere_relativity.py - The imaginary geometry becomes the language of the cosmos

Episode 045 (Nikolai Lobachevsky). Intuition-level visuals for how hyperbolic
geometry was vindicated after Lobachevsky's death: realised on a real surface
(the pseudosphere) and generalised into the geometry of curved spacetime.
No proofs -- wonder and intuition only.

Modes:
    pseudosphere (default)
        A stylised pseudosphere (a trumpet/funnel of constant negative curvature),
        with a small geodesic triangle on it whose angle sum is < 180 degrees:
        Lobachevsky's geometry lives on a real surface. Caption: Beltrami, 1868 --
        the first proof that the geometry is consistent.
        Fixed params: rim at (0,1.7) width ~2.6; profile tapering to (0,-1.3);
        three cross-section rings; one on-surface triangle.
        On screen: name Beltrami (ベルトラミ), year 1868.
    spacetime
        A flat Euclidean grid (left) vs a grid warped around a mass (right):
        Riemann generalised geometry to any curvature, and Einstein's general
        relativity made gravity the curving of spacetime. A three-step timeline
        1854 Riemann / 1868 Beltrami / 1915 Einstein.
        Fixed params: two 2.6-wide grids centred at x=-3.4 and x=+3.4; one mass dot;
        warp k=0.38, sigma=0.72.
        On screen: names Riemann/Beltrami/Einstein/Euclid, years 1854/1868/1915.

All Text uses FONT (BIZ UDMincho). No MathTex, no Japanese-in-LaTeX risk.
Y range: about -1.9 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    ArcBetweenPoints,
    Create,
    Dot,
    Ellipse,
    FadeIn,
    Line,
    Scene,
    Text,
    VGroup,
    VMobject,
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


def _half_width(u):
    """Funnel half-width: wide at the top rim (u=0), narrow at the tip (u=1)."""
    return 1.3 * (1.0 - u) ** 1.6 + 0.06


def _profile_y(u):
    return 1.7 - 3.0 * u


def _warp(point, center, k=0.38, sigma=0.72):
    """Pull a point toward `center` with a Gaussian falloff (a 2-D gravity well)."""
    p = np.array(point, dtype=float)
    c = np.array(center, dtype=float)
    diff = c - p
    dist2 = float(diff[0] ** 2 + diff[1] ** 2)
    pull = k * np.exp(-dist2 / (2.0 * sigma * sigma))
    return p + diff * pull


class PseudosphereRelativity(Scene):
    """From the pseudosphere to curved spacetime -- two intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "pseudosphere")
        duration = float(params.get("duration", 26))
        if mode == "spacetime":
            self._build_spacetime(duration)
        else:
            self._build_pseudosphere(duration)

    # --------------------------------------------------------------- pseudosphere
    def _build_pseudosphere(self, duration):
        title = Text(
            "擬球 ── 曲がった面の上では、本当になる", font=FONT, font_size=27, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        us = np.linspace(0.0, 1.0, 44)
        right_pts = [np.array([_half_width(u), _profile_y(u), 0.0]) for u in us]
        left_pts = [np.array([-_half_width(u), _profile_y(u), 0.0]) for u in us]
        right = VMobject().set_points_smoothly(right_pts)
        right.set_stroke(ACCENT_CYAN, 2.5)
        left = VMobject().set_points_smoothly(left_pts)
        left.set_stroke(ACCENT_CYAN, 2.5)

        rim = Ellipse(
            width=2.0 * _half_width(0.0), height=0.42, color=ACCENT_CYAN, stroke_width=2.5
        )
        rim.move_to([0, _profile_y(0.0), 0])
        rim.set_fill(ACCENT_CYAN, opacity=0.06)
        rings = VGroup()
        for u in (0.33, 0.63):
            hw = _half_width(u)
            ring = Ellipse(
                width=2.0 * hw, height=0.30 * (hw / 1.3) + 0.05, color=EDGE_COLOR, stroke_width=1.4
            )
            ring.move_to([0, _profile_y(u), 0])
            rings.add(ring)

        surf_label = Text("曲率が一定の、負に曲がった面", font=FONT, font_size=18, color=TEXT_DIM)
        surf_label.move_to([3.5, 1.55, 0])

        tri_pts = [
            np.array([-0.55, 0.95, 0.0]),
            np.array([0.6, 0.7, 0.0]),
            np.array([-0.05, -0.25, 0.0]),
        ]
        centroid = (tri_pts[0] + tri_pts[1] + tri_pts[2]) / 3.0
        tri = VGroup(
            self._bow(tri_pts[0], tri_pts[1], centroid),
            self._bow(tri_pts[1], tri_pts[2], centroid),
            self._bow(tri_pts[2], tri_pts[0], centroid),
        )
        tri_label = Text("内角の和 ＜ 180°", font=FONT, font_size=22, color=TEXT_WHITE)
        tri_label.move_to([0, -1.6, 0])

        cap = Text(
            "ベルトラミ 1868 ── この面の上に、幾何がそのまま現れる",
            font=FONT,
            font_size=19,
            color=ACCENT_GOLD,
        )
        cap.move_to([0, -1.88, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(Create(left), Create(right), run_time=per * 1.2)
        self.play(FadeIn(rim), run_time=per * 0.7)
        self.play(Create(rings), run_time=per * 0.8)
        self.play(FadeIn(surf_label), run_time=per * 0.7)
        self.play(Create(tri), FadeIn(tri_label), run_time=per * 1.2)
        self.play(FadeIn(cap), run_time=per)
        self.wait(coda)

    def _bow(self, a, b, center, mag=0.45, color=ACCENT_GOLD, width=3.5):
        a = np.array(a, float)
        b = np.array(b, float)
        c = np.array(center, float)
        d = b - a
        mid = (a + b) / 2.0
        left_normal = np.array([-d[1], d[0], 0.0])
        # bow inward, toward the triangle centroid (angle sum < 180, negative curvature)
        sign = -1.0 if float(np.dot(left_normal, c - mid)) > 0 else 1.0
        arc = ArcBetweenPoints(a, b, angle=sign * mag)
        arc.set_stroke(color, width)
        return arc

    # ------------------------------------------------------------------ spacetime
    def _build_spacetime(self, duration):
        title = Text(
            "曲率 ── リーマンからアインシュタインへ", font=FONT, font_size=27, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        flat = self._grid(center=[-3.4, 1.0, 0], warp_center=None)
        flat.set_stroke(EDGE_COLOR, 1.6)
        flat_label = Text("平らな空間（ユークリッド）", font=FONT, font_size=19, color=ACCENT_CYAN)
        flat_label.move_to([-3.4, 2.35, 0])

        mass_c = [3.4, 1.0, 0]
        curved = self._grid(center=mass_c, warp_center=mass_c)
        curved.set_stroke(ACCENT_CYAN, 1.6)
        mass = Dot(mass_c, color=ACCENT_PINK, radius=0.12)
        curved_label = Text("曲がった時空（重力）", font=FONT, font_size=19, color=ACCENT_GOLD)
        curved_label.move_to([3.4, 2.35, 0])

        mid = Text(
            "質量が\n時空を曲げる", font=FONT, font_size=18, color=TEXT_WHITE, line_spacing=0.7
        )
        mid.move_to([0, 1.35, 0])
        arrow = Text("→", font=FONT, font_size=30, color=TEXT_DIM)
        arrow.move_to([0, 0.5, 0])

        steps = VGroup(
            Text("1854 リーマン", font=FONT, font_size=17, color=TEXT_WHITE),
            Text("1868 ベルトラミ", font=FONT, font_size=17, color=TEXT_WHITE),
            Text("1915 アインシュタイン", font=FONT, font_size=17, color=ACCENT_GOLD),
        )
        for s, x in zip(steps, (-4.1, -0.7, 3.2), strict=True):
            s.move_to([x, -1.45, 0])
        base_line = Line([-5.3, -1.7, 0], [5.3, -1.7, 0], color=EDGE_COLOR, stroke_width=1.4)
        note = Text(
            "想像上の幾何が、宇宙の言葉になった", font=FONT, font_size=20, color=ACCENT_GOLD
        )
        note.move_to([0, -1.95, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(Create(flat), FadeIn(flat_label), run_time=per)
        self.play(Create(curved), FadeIn(mass), FadeIn(curved_label), run_time=per * 1.2)
        self.play(FadeIn(mid), FadeIn(arrow), run_time=per * 0.7)
        self.play(FadeIn(base_line), FadeIn(steps[0]), run_time=per)
        self.play(FadeIn(steps[1]), FadeIn(steps[2]), run_time=per)
        self.play(FadeIn(note), run_time=per)
        self.wait(coda)

    def _grid(self, center, warp_center, n=4, half=1.25):
        """A small square grid; if warp_center is given, warp toward it."""
        cx, cy = center[0], center[1]
        lines = VGroup()
        coords = np.linspace(-half, half, n + 1)
        for gy in coords:
            pts = []
            for gx in np.linspace(-half, half, 30):
                p = [cx + gx, cy + gy, 0.0]
                pts.append(_warp(p, warp_center) if warp_center else np.array(p, float))
            lines.add(VMobject().set_points_smoothly(pts))
        for gx in coords:
            pts = []
            for gy in np.linspace(-half, half, 30):
                p = [cx + gx, cy + gy, 0.0]
                pts.append(_warp(p, warp_center) if warp_center else np.array(p, float))
            lines.add(VMobject().set_points_smoothly(pts))
        return lines


LINT_FACTUAL_CLAIMS = {
    "pseudosphere": {"people": [["ベルトラミ", "Beltrami"]], "years": ["1868"]},
    "spacetime": {
        "people": [
            ["リーマン", "Riemann"],
            ["ベルトラミ", "Beltrami"],
            ["アインシュタイン", "Einstein"],
            ["ユークリッド", "Euclid"],
        ],
        "years": ["1854", "1868", "1915"],
    },
}

SCENES = {
    "pseudosphere": PseudosphereRelativity,
    "spacetime": PseudosphereRelativity,
}
