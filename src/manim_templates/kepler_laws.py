"""
kepler_laws.py - Kepler's three laws of planetary motion for 数学史記

Visualizes the three laws Kepler derived from Tycho Brahe's observations of
Mars:
    1st law (Astronomia Nova, 1609): a planet moves on an ellipse with the
        Sun at one focus. Defining property r1 + r2 = 2a (constant).
    2nd law (Astronomia Nova, 1609): the line from the Sun to the planet
        sweeps equal areas in equal times (faster near perihelion, slower
        near aphelion).
    3rd law (Harmonices Mundi, 1619): the square of the orbital period is
        proportional to the cube of the semi-major axis, T^2 / a^3 = const.

Modes:
    ellipse_focus - Ellipse (a=3.0, b=1.8) centered at [0, 0.1, 0]; Sun (gold)
                    at the right focus, empty focus (dim) at the left, planet
                    (pink) on the curve with the two focal radii drawn.
                    MathTex r_1 + r_2 = 2a at top.
                    Fixed params: a=3.0, b=1.8, c=sqrt(a^2-b^2)=2.40.
    equal_areas   - Same ellipse and Sun; two shaded wedges of EQUAL area,
                    one long-arc/short-radius near perihelion, one short-arc/
                    long-radius near aphelion. Areas numerically equalised by
                    bisection. Labels A_1 = A_2.
                    Fixed params: perihelion half-span 0.62 rad about t=0.
    harmonic_law  - MathTex T^2 / a^3 = const at top; table of four planets
                    (Earth, Mars, Jupiter, Saturn) with a (AU), T (yr) and
                    T^2/a^3 ~= 1.000 for each.
                    Fixed params: Earth a=1.000 T=1.000; Mars a=1.524 T=1.881;
                    Jupiter a=5.203 T=11.862; Saturn a=9.537 T=29.447.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 031 (Kepler), planetary-motion pillar.
"""

import math

import numpy as np
from manim import (
    Brace,
    Dot,
    Ellipse,
    FadeIn,
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

# Shared ellipse geometry (scene units)
A = 3.0
B = 1.8
C = math.sqrt(A * A - B * B)  # 2.4
CENTER = np.array([0.0, 0.1, 0.0])
SUN = CENTER + np.array([C, 0.0, 0.0])  # right focus
EMPTY_FOCUS = CENTER + np.array([-C, 0.0, 0.0])  # left focus


def _ellipse_point(t, a=A, b=B, center=CENTER):
    return center + np.array([a * math.cos(t), b * math.sin(t), 0.0])


def _wedge_area(t0, t1, n=24, a=A, b=B, center=CENTER, sun=SUN):
    """Shoelace area of the polygon (sun + arc points from t0 to t1)."""
    pts = [sun]
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        pts.append(_ellipse_point(t, a, b, center))
    area = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i][0], pts[i][1]
        x1, y1 = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
        area += x0 * y1 - x1 * y0
    return abs(area) / 2.0


def _wedge_polygon(t0, t1, color, n=24, a=A, b=B, center=CENTER, sun=SUN):
    pts = [sun]
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        pts.append(_ellipse_point(t, a, b, center))
    poly = Polygon(*pts, color=color, stroke_width=1.5)
    poly.set_fill(color, opacity=0.45)
    return poly


class KeplerLaws(Scene):
    """Kepler's first, second and third laws of planetary motion."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 16)
        mode = params.get("mode", "ellipse_focus")

        if mode == "equal_areas":
            self._build_equal_areas()
        elif mode == "harmonic_law":
            self._build_harmonic_law()
        else:
            self._build_ellipse_focus()

    # ------------------------------------------------------------------
    # Mode: ellipse_focus (1st law)
    # ------------------------------------------------------------------
    def _build_ellipse_focus(self):
        duration = self._duration

        title = Text(
            "ケプラーの第一法則 ── 楕円軌道 (1609)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.8, 0])

        formula = MathTex(r"r_1 + r_2 = 2a", font_size=40, color=ACCENT_GOLD)
        formula.move_to([0, 2.05, 0])

        ellipse = Ellipse(width=2 * A, height=2 * B, color=ACCENT_CYAN, stroke_width=3)
        ellipse.move_to(CENTER)

        # Major axis (長軸): the longest diameter, length 2a. Braced + labelled
        # so 2a is clearly the major-axis length, NOT the circumference.
        left_vertex = CENTER + np.array([-A, 0, 0])
        right_vertex = CENTER + np.array([A, 0, 0])
        major = Line(left_vertex, right_vertex, color=EDGE_COLOR, stroke_width=1.5)
        v_left = Dot(left_vertex, color=ACCENT_GOLD, radius=0.05)
        v_right = Dot(right_vertex, color=ACCENT_GOLD, radius=0.05)
        major_brace = Brace(major, direction=np.array([0, -1, 0]), color=ACCENT_GOLD, buff=0.1)
        major_lbl = Text("長軸（長い方の直径）＝ 2a", font=FONT, font_size=20, color=ACCENT_GOLD)
        major_lbl.next_to(major_brace, np.array([0, -1, 0]), buff=0.06)

        sun_dot = Dot(SUN, color=ACCENT_GOLD, radius=0.13)
        sun_label = Text("太陽", font=FONT, font_size=22, color=ACCENT_GOLD)
        sun_label.next_to(sun_dot, np.array([0, 1, 0]), buff=0.1)

        empty_dot = Dot(EMPTY_FOCUS, color=TEXT_DIM, radius=0.08)
        empty_label = Text("焦点", font=FONT, font_size=20, color=TEXT_DIM)
        empty_label.next_to(empty_dot, np.array([0, 1, 0]), buff=0.1)

        planet_t = 0.95
        planet_pos = _ellipse_point(planet_t)
        planet_dot = Dot(planet_pos, color=ACCENT_PINK, radius=0.11)
        planet_label = Text("惑星", font=FONT, font_size=22, color=ACCENT_PINK)
        planet_label.next_to(planet_dot, np.array([0.4, 1, 0]), buff=0.12)

        r1 = Line(SUN, planet_pos, color=ACCENT_PINK, stroke_width=2.5)
        r2 = Line(EMPTY_FOCUS, planet_pos, color=ACCENT_CYAN, stroke_width=2.5)
        r1_lbl = MathTex(r"r_1", font_size=30, color=ACCENT_PINK)
        r1_lbl.move_to((SUN + planet_pos) / 2 + np.array([0.25, -0.05, 0]))
        r2_lbl = MathTex(r"r_2", font_size=30, color=ACCENT_CYAN)
        r2_lbl.move_to((EMPTY_FOCUS + planet_pos) / 2 + np.array([-0.1, 0.3, 0]))

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(ellipse), FadeIn(major), FadeIn(v_left), FadeIn(v_right), run_time=1.0)
        self.play(
            FadeIn(sun_dot), FadeIn(sun_label), FadeIn(empty_dot), FadeIn(empty_label), run_time=0.8
        )
        self.play(FadeIn(planet_dot), FadeIn(planet_label), run_time=0.6)
        self.play(FadeIn(r1), FadeIn(r2), FadeIn(r1_lbl), FadeIn(r2_lbl), run_time=0.8)
        self.play(FadeIn(formula), run_time=0.7)
        self.play(FadeIn(major_brace), FadeIn(major_lbl), run_time=0.7)

        anim_overhead = 0.7 + 1.0 + 0.8 + 0.6 + 0.8 + 0.7 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: equal_areas (2nd law)
    # ------------------------------------------------------------------
    def _build_equal_areas(self):
        duration = self._duration

        title = Text(
            "ケプラーの第二法則 ── 面積速度一定 (1609)",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.8, 0])

        # Less-eccentric ellipse for the 2nd law (e~0.59) so both swept areas
        # are visibly comparable; ellipse_focus keeps the dramatic e=0.8 spread.
        a_e, b_e = 2.3, 1.85
        c_e = math.sqrt(a_e * a_e - b_e * b_e)
        center_e = CENTER
        sun_e = center_e + np.array([c_e, 0.0, 0.0])

        ellipse = Ellipse(width=2 * a_e, height=2 * b_e, color=ACCENT_CYAN, stroke_width=3)
        ellipse.move_to(center_e)

        sun_dot = Dot(sun_e, color=ACCENT_GOLD, radius=0.13)
        sun_label = Text("太陽", font=FONT, font_size=20, color=ACCENT_GOLD)
        sun_label.next_to(sun_dot, np.array([0.3, -1, 0]), buff=0.12)

        ekw = {"a": a_e, "b": b_e, "center": center_e, "sun": sun_e}

        # Perihelion wedge: arc about t = 0 (near the Sun / right focus)
        peri_half = 0.62
        peri = _wedge_polygon(-peri_half, peri_half, ACCENT_PINK, **ekw)
        area_target = _wedge_area(-peri_half, peri_half, **ekw)

        # Aphelion wedge: arc about t = pi, span found by bisection to match area
        lo, hi = 0.05, 1.5
        for _ in range(40):
            mid = (lo + hi) / 2
            ar = _wedge_area(math.pi - mid, math.pi + mid, **ekw)
            if ar < area_target:
                lo = mid
            else:
                hi = mid
        aph_half = (lo + hi) / 2
        aph = _wedge_polygon(math.pi - aph_half, math.pi + aph_half, ACCENT_CYAN, **ekw)

        peri_dot = Dot(_ellipse_point(0, a_e, b_e, center_e), color=ACCENT_PINK, radius=0.09)
        aph_dot = Dot(_ellipse_point(math.pi, a_e, b_e, center_e), color=ACCENT_CYAN, radius=0.09)

        fast_lbl = Text("速い", font=FONT, font_size=22, color=ACCENT_PINK)
        fast_lbl.move_to(_ellipse_point(0, a_e, b_e, center_e) + np.array([0.5, -0.05, 0]))
        slow_lbl = Text("遅い", font=FONT, font_size=22, color=ACCENT_CYAN)
        slow_lbl.move_to(_ellipse_point(math.pi, a_e, b_e, center_e) + np.array([-0.5, 0.0, 0]))

        eq = MathTex(r"A_1 = A_2", font_size=38, color=ACCENT_GOLD)
        eq.move_to([0, 2.05, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(ellipse), FadeIn(sun_dot), FadeIn(sun_label), run_time=0.9)
        self.play(FadeIn(peri), FadeIn(peri_dot), FadeIn(fast_lbl), run_time=0.8)
        self.play(FadeIn(aph), FadeIn(aph_dot), FadeIn(slow_lbl), run_time=0.8)
        self.play(FadeIn(eq), run_time=0.7)

        anim_overhead = 0.7 + 0.9 + 0.8 + 0.8 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: harmonic_law (3rd law)
    # ------------------------------------------------------------------
    def _build_harmonic_law(self):
        duration = self._duration

        title = Text(
            "ケプラーの第三法則 ── 調和の法則 (1619)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.8, 0])

        formula = MathTex(r"\frac{T^2}{a^3} = \text{const}", font_size=44, color=ACCENT_GOLD)
        formula.move_to([0, 1.95, 0])

        # Planet data: name, a (AU), T (yr)
        rows = [
            ("惑星", "a (天文単位)", "T (年)", "T^2 / a^3"),
            ("地球", "1.000", "1.000", "1.000"),
            ("火星", "1.524", "1.881", "1.000"),
            ("木星", "5.203", "11.862", "1.000"),
            ("土星", "9.537", "29.447", "1.001"),
        ]

        col_x = [-4.2, -1.4, 1.2, 3.8]
        row_y0 = 1.05
        row_dy = 0.62

        table = VGroup()
        for r, row in enumerate(rows):
            y = row_y0 - r * row_dy
            is_head = r == 0
            color = ACCENT_CYAN if is_head else TEXT_WHITE
            fsz = 22 if is_head else 24
            for c, cell in enumerate(row):
                if is_head:
                    if c == 3:
                        obj = MathTex(r"T^2 / a^3", font_size=26, color=color)
                    else:
                        obj = Text(cell, font=FONT, font_size=fsz, color=color)
                elif c == 0:
                    obj = Text(cell, font=FONT, font_size=fsz, color=ACCENT_PINK)
                else:
                    obj = MathTex(cell, font_size=30, color=color)
                obj.move_to([col_x[c], y, 0])
                table.add(obj)

        head_rule = Line(
            [-5.2, row_y0 - 0.32, 0],
            [5.0, row_y0 - 0.32, 0],
            color=EDGE_COLOR,
            stroke_width=1.5,
        )

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(formula), run_time=0.7)
        self.play(FadeIn(table[:4]), FadeIn(head_rule), run_time=0.7)
        self.play(FadeIn(table[4:]), run_time=1.0)

        anim_overhead = 0.7 + 0.7 + 0.7 + 1.0
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "ellipse_focus": {
        "people": [["ケプラー", "Kepler"]],
        "years": ["1609"],
    },
    "equal_areas": {
        "people": [["ケプラー", "Kepler"]],
        "years": ["1609"],
    },
    "harmonic_law": {
        "people": [["ケプラー", "Kepler"]],
        "years": ["1619"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "ellipse_focus": {
        "class": "KeplerLaws",
        "params": {"mode": "ellipse_focus"},
        "description": "Kepler's 1st law: ellipse with the Sun at one focus, r1+r2=2a (1609)",
    },
    "equal_areas": {
        "class": "KeplerLaws",
        "params": {"mode": "equal_areas"},
        "description": "Kepler's 2nd law: equal areas in equal times, A1=A2 near perihelion vs aphelion (1609)",
    },
    "harmonic_law": {
        "class": "KeplerLaws",
        "params": {"mode": "harmonic_law"},
        "description": "Kepler's 3rd law: T^2/a^3 = const, table of Earth/Mars/Jupiter/Saturn (1619)",
    },
}
