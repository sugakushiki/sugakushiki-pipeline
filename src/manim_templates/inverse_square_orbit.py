"""
inverse_square_orbit.py - Newton's derivation of Kepler's laws for 数学史記

In the Principia (1687) Newton showed that one assumption - a force pulling the
planet toward the Sun that falls off as the inverse square of distance - forces
the orbit to obey Kepler's empirical laws.

Propositions involved (Book I, Section 3):
    Prop. 1          (2nd law): a force directed at a fixed centre makes the
                     radius vector sweep equal areas in equal times. (True for
                     ANY central force, not only the inverse square.)
    Prop. 11         (direct problem): if the orbit IS an ellipse, the force
                     toward a focus is inverse-square (ellipse -> inverse square).
    Prop. 13 Cor. 1  (inverse problem): conversely, an inverse-square central
                     force yields a conic orbit - an ellipse for a bound orbit
                     (inverse square -> ellipse). The `inverse_square_ellipse`
                     mode illustrates this physical direction. (Johann Bernoulli
                     later criticised this corollary as incompletely proved.)

The planet moves with the physically correct Kepler speed (slow at aphelion,
fast at perihelion), obtained by solving Kepler's equation M = E - e sin E for
the eccentric anomaly E at uniform time (mean anomaly M).

Modes:
    central_force        - Planet orbits; a force arrow always points at the Sun
                           and lengthens near perihelion (inverse-square hint).
                           Full-scene motion (ValueTracker), ~2 orbits.
    equal_areas          - Same orbit; two shaded wedges swept in EQUAL TIME
                           (equal mean-anomaly span dM=0.55) are therefore EQUAL
                           in area: perihelion (short fat) vs aphelion (long
                           thin). Label A_1 = A_2. Planet keeps orbiting.
    inverse_square_ellipse - Force law F = G M m / r^2 and the resulting ellipse
                           with the Sun at one focus (Prop. 13 Cor. 1: inverse
                           square -> conic); a planet slowly orbits.

Fixed geometry (scene units): a=2.4, e=0.6, b=1.92, c=ae=1.44, centre=[0,0.15].
Sun at the right focus [1.44, 0.15]. Orbit fits y in -1.77 .. +2.07.

Duration-aware: reads target duration from _manim_params.json; orbital motion
fills the scene with a fixed ~2.5s coda (no long static tail).
Y range: title at +2.9, all content within -1.85 .. +2.1.

Used by: Episode 037 (Newton), math pillar 4 (Principia / gravitation).
"""

import math

import numpy as np
from manim import (
    Arrow,
    Dot,
    Ellipse,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    Scene,
    Text,
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

# Orbit geometry
A = 2.4
E_ECC = 0.6
B = A * math.sqrt(1.0 - E_ECC * E_ECC)  # 1.92
C = A * E_ECC  # 1.44
CENTER = np.array([0.0, 0.15, 0.0])
SUN = CENTER + np.array([C, 0.0, 0.0])  # right focus

# Precomputed table to invert Kepler's equation M = E - e sin E
_EG = np.linspace(0.0, 2.0 * math.pi, 4000)
_MG = _EG - E_ECC * np.sin(_EG)


def _E_of_M(M):
    """Eccentric anomaly E for mean anomaly M (radians), via interpolation."""
    M = M % (2.0 * math.pi)
    return float(np.interp(M, _MG, _EG))


def _point(E):
    return CENTER + np.array([A * math.cos(E), B * math.sin(E), 0.0])


def _planet_at(frac):
    """Planet position at time fraction `frac` of one period (Kepler speed)."""
    return _point(_E_of_M(2.0 * math.pi * frac))


def _wedge(m0, m1, color, n=40):
    """Polygon from the Sun over the arc between mean anomalies m0..m1.

    Built from the (signed) eccentric anomaly so the arc stays smooth across
    M = 0. Equal mean-anomaly spans => equal swept time => equal area.
    """
    e0 = _signed_E(m0)
    e1 = _signed_E(m1)
    pts = [SUN]
    for i in range(n + 1):
        e = e0 + (e1 - e0) * i / n
        pts.append(_point(e))
    poly = Polygon(*pts, color=color, stroke_width=1.5)
    poly.set_fill(color, opacity=0.45)
    return poly


def _signed_E(M):
    """Eccentric anomaly that varies continuously through M=0 (can be negative)."""
    if M < 0:
        return -_E_of_M(-M)
    return _E_of_M(M)


class InverseSquareOrbit(Scene):
    """Newton: Prop. 1 (equal areas), Prop. 11 (ellipse -> inverse square),
    Prop. 13 Cor. 1 (inverse square -> conic/ellipse)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        mode = params.get("mode", "central_force")

        if mode == "equal_areas":
            self._build_equal_areas()
        elif mode == "inverse_square_ellipse":
            self._build_inverse_square_ellipse()
        else:
            self._build_central_force()

    # ------------------------------------------------------------------
    def _ellipse_mobjects(self):
        ellipse = Ellipse(width=2 * A, height=2 * B, color=ACCENT_CYAN, stroke_width=3)
        ellipse.move_to(CENTER)
        sun_dot = Dot(SUN, color=ACCENT_GOLD, radius=0.16)
        sun_label = Text("太陽", font=FONT, font_size=22, color=ACCENT_GOLD)
        sun_label.next_to(sun_dot, np.array([0.6, -1, 0]), buff=0.1)
        return ellipse, sun_dot, sun_label

    # ------------------------------------------------------------------
    # Mode: central_force
    # ------------------------------------------------------------------
    def _build_central_force(self):
        duration = self._duration

        title = Text(
            "中心へ向かう力 ── 太陽が引く",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        ellipse, sun_dot, sun_label = self._ellipse_mobjects()

        frac = self._tracker_intro(title, ellipse, sun_dot, sun_label)

        def make_planet():
            return Dot(_planet_at(frac.get_value() % 1.0), color=ACCENT_PINK, radius=0.12)

        def make_radius():
            p = _planet_at(frac.get_value() % 1.0)
            return Line(SUN, p, color=EDGE_COLOR, stroke_width=2)

        def make_force():
            p = _planet_at(frac.get_value() % 1.0)
            rvec = SUN - p
            r = float(np.linalg.norm(rvec))
            unit = rvec / r
            length = min(max(0.95 / (r * r), 0.30), min(1.25, r * 0.85))
            return Arrow(
                p,
                p + unit * length,
                color=ACCENT_GOLD,
                buff=0.0,
                stroke_width=5,
                max_tip_length_to_length_ratio=0.35,
            )

        planet = always_redraw(make_planet)
        radius = always_redraw(make_radius)
        force = always_redraw(make_force)
        force_lbl = Text("力", font=FONT, font_size=22, color=ACCENT_GOLD)
        force_lbl.add_updater(
            lambda m: m.move_to(
                _planet_at(frac.get_value() % 1.0)
                + (SUN - _planet_at(frac.get_value() % 1.0))
                / float(np.linalg.norm(SUN - _planet_at(frac.get_value() % 1.0)))
                * 0.55
                + np.array([0.0, 0.28, 0.0])
            )
        )

        self.add(radius, force, planet, force_lbl)
        self._orbit_motion(frac, duration, n_orbits=2.0)

    # ------------------------------------------------------------------
    # Mode: equal_areas
    # ------------------------------------------------------------------
    def _build_equal_areas(self):
        duration = self._duration

        title = Text(
            "面積速度一定 ── 同じ時間に同じ面積",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        ellipse, sun_dot, sun_label = self._ellipse_mobjects()

        dM = 0.55
        peri = _wedge(-dM, dM, ACCENT_PINK)  # near perihelion (E around 0)
        aph = _wedge(math.pi - dM, math.pi + dM, ACCENT_CYAN)  # near aphelion

        fast = Text("速い", font=FONT, font_size=22, color=ACCENT_PINK)
        fast.move_to(_point(0) + np.array([0.55, -0.1, 0]))
        slow = Text("遅い", font=FONT, font_size=22, color=ACCENT_CYAN)
        slow.move_to(_point(math.pi) + np.array([-0.55, 0.05, 0]))

        eq = MathTex(r"A_1 = A_2", font_size=40, color=ACCENT_GOLD)
        eq.move_to([0, 2.2, 0])

        frac = self._tracker_intro(title, ellipse, sun_dot, sun_label)
        self.play(FadeIn(peri), FadeIn(aph), FadeIn(fast), FadeIn(slow), FadeIn(eq), run_time=1.0)

        planet = always_redraw(
            lambda: Dot(_planet_at(frac.get_value() % 1.0), color=ACCENT_PINK, radius=0.12)
        )
        radius = always_redraw(
            lambda: Line(SUN, _planet_at(frac.get_value() % 1.0), color=EDGE_COLOR, stroke_width=2)
        )
        self.add(radius, planet)
        self._orbit_motion(frac, duration, n_orbits=1.5, extra_used=1.0)

    # ------------------------------------------------------------------
    # Mode: inverse_square_ellipse
    # ------------------------------------------------------------------
    def _build_inverse_square_ellipse(self):
        duration = self._duration

        title = Text(
            "逆二乗の力が描く楕円",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        law = MathTex(r"F = G\,\dfrac{M\,m}{r^2}", font_size=40, color=ACCENT_CYAN)
        law.move_to([0, 2.15, 0])

        ellipse, sun_dot, sun_label = self._ellipse_mobjects()
        empty = Dot(CENTER + np.array([-C, 0, 0]), color=TEXT_DIM, radius=0.08)
        empty_lbl = Text("焦点", font=FONT, font_size=20, color=TEXT_DIM)
        empty_lbl.next_to(empty, np.array([0, -1, 0]), buff=0.1)

        caption = Text(
            "太陽が焦点 ── 軌道は楕円になる",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        caption.move_to([0, -1.55, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(law), run_time=0.7)
        self.play(FadeIn(ellipse), FadeIn(sun_dot), FadeIn(sun_label), run_time=1.0)
        self.play(FadeIn(empty), FadeIn(empty_lbl), FadeIn(caption), run_time=0.8)
        used = 0.6 + 0.7 + 1.0 + 0.8

        frac = self._make_tracker()
        planet = always_redraw(
            lambda: Dot(_planet_at(frac.get_value() % 1.0), color=ACCENT_PINK, radius=0.12)
        )
        radius = always_redraw(
            lambda: Line(SUN, _planet_at(frac.get_value() % 1.0), color=EDGE_COLOR, stroke_width=2)
        )
        self.add(radius, planet)
        self._orbit_motion(frac, duration, n_orbits=1.5, extra_used=used - (0.6 + 1.0))

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _make_tracker(self):
        from manim import ValueTracker

        return ValueTracker(0.0)

    def _tracker_intro(self, title, ellipse, sun_dot, sun_label):
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(ellipse), run_time=0.9)
        self.play(FadeIn(sun_dot), FadeIn(sun_label), run_time=0.7)
        return self._make_tracker()

    def _orbit_motion(self, frac, duration, n_orbits=2.0, extra_used=0.0):
        # Intro overhead already played: title(0.6)+ellipse(0.9)+sun(0.7) = 2.2
        used = 2.2 + extra_used
        coda = 2.5
        motion = max(3.0, duration - used - coda)
        self.play(frac.animate.set_value(n_orbits), run_time=motion, rate_func=lambda a: a)
        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No person names or year text are shown on screen in any mode.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "central_force": {"people": [], "years": []},
    "equal_areas": {"people": [], "years": []},
    "inverse_square_ellipse": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "central_force": {
        "class": "InverseSquareOrbit",
        "params": {"mode": "central_force"},
        "description": "Orbiting planet with a force arrow always pointing at the Sun (central force)",
    },
    "equal_areas": {
        "class": "InverseSquareOrbit",
        "params": {"mode": "equal_areas"},
        "description": "Prop. 1 / 2nd law: equal areas swept in equal times, A1=A2 (perihelion vs aphelion)",
    },
    "inverse_square_ellipse": {
        "class": "InverseSquareOrbit",
        "params": {"mode": "inverse_square_ellipse"},
        "description": "Prop. 13 Cor. 1: inverse-square force F=GMm/r^2 yields a conic (ellipse), Sun at a focus",
    },
}
