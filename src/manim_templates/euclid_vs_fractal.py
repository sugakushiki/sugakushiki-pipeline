"""
euclid_vs_fractal.py - Smooth Euclidean shapes vs rough fractal nature

Episode 042 (Mandelbrot), block 1 -- the thesis image. For roughly two
thousand years geometry drew smooth, ideal forms (line, circle, cone); but
nature is rough: "Clouds are not spheres, mountains are not cones, coastlines
are not circles." The left column shows three smooth Euclidean shapes; the
right column shows their rough, jagged natural counterparts, revealed in pairs.

Modes:
    contrast (default, single mode)
        Three rows separated from a center divider. Row 1: a straight Line vs a
        jagged coastline polyline. Row 2: a smooth Circle vs a Koch-snowflake
        outline. Row 3: a smooth triangle (cone / mountain) vs a rough,
        midpoint-displaced ridge.
        Fixed params: 3 pairs; Koch snowflake depth 3; coastline/ridge midpoint
        displacement depth 5; deterministic (fixed seeds). No person names or
        years appear on screen (only generic Japanese labels + MathTex symbols).

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.65 to +3.05, subtitle clearance preserved. No trailing FadeOut.
"""

import math
import random

import numpy as np
from manim import (
    DOWN,
    Circle,
    Create,
    DashedLine,
    FadeIn,
    Indicate,
    Line,
    Polygon,
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
    FONT,
    TEXT_DIM,
    load_params,
)

config.background_color = BG_COLOR


# --------------------------------------------------------------------------
# Deterministic rough-curve helpers
# --------------------------------------------------------------------------
def _koch(p0, p1, depth):
    """Koch curve points between p0 and p1 (peak rotated outward by 60 deg)."""
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    if depth == 0:
        return [p0]
    a = p0 + (p1 - p0) / 3.0
    b = p0 + 2.0 * (p1 - p0) / 3.0
    d = b - a
    ang = math.pi / 3.0  # +60 deg -> outward bump for CCW winding
    rot = np.array(
        [
            d[0] * math.cos(ang) - d[1] * math.sin(ang),
            d[0] * math.sin(ang) + d[1] * math.cos(ang),
            0.0,
        ]
    )
    peak = a + rot
    pts = []
    pts += _koch(p0, a, depth - 1)
    pts += _koch(a, peak, depth - 1)
    pts += _koch(peak, b, depth - 1)
    pts += _koch(b, p1, depth - 1)
    return pts


def _koch_snowflake(center, radius, depth):
    cx, cy = center[0], center[1]
    verts = []
    for k in range(3):
        ang = math.pi / 2 + k * 2 * math.pi / 3
        verts.append(np.array([cx + radius * math.cos(ang), cy + radius * math.sin(ang), 0.0]))
    pts = []
    for i in range(3):
        pts += _koch(verts[i], verts[(i + 1) % 3], depth)
    pts.append(pts[0])
    return pts


def _midpoint_disp(p0, p1, depth, rough, seed):
    """Midpoint-displacement fractal polyline from p0 to p1 (deterministic)."""
    rng = random.Random(seed)
    pts = [np.array(p0, dtype=float), np.array(p1, dtype=float)]
    amp = rough
    for _ in range(depth):
        new = [pts[0]]
        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]
            mid = (a + b) / 2.0
            d = b - a
            perp = np.array([-d[1], d[0], 0.0])
            n = np.linalg.norm(perp)
            if n > 1e-9:
                perp = perp / n
            mid = mid + perp * rng.uniform(-amp, amp)
            new.append(mid)
            new.append(b)
        pts = new
        amp *= 0.5
    return pts


def _polyline(points, color, width=3.0):
    m = VMobject()
    m.set_points_as_corners([np.array(p, dtype=float) for p in points])
    m.set_stroke(color=color, width=width)
    return m


class EuclidVsFractal(Scene):
    """Smooth Euclidean shapes vs rough fractal nature - single mode."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = float(params.get("duration", 22))
        self._build_contrast(duration)

    def _build_contrast(self, duration):
        title = Text("なめらかな図形と、粗い自然", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        # column headers + divider
        head_l = Text("ユークリッド：なめらか", font=FONT, font_size=22, color=ACCENT_CYAN)
        head_l.move_to([-3.3, 2.45, 0])
        head_r = Text("自然：粗い（ギザギザ）", font=FONT, font_size=22, color=ACCENT_PINK)
        head_r.move_to([3.3, 2.45, 0])
        divider = DashedLine([0, 2.15, 0], [0, -1.55, 0], color=TEXT_DIM, stroke_width=1.8)
        self.play(FadeIn(head_l), FadeIn(head_r), Create(divider), run_time=0.7)

        rows_y = [1.55, 0.2, -1.15]
        lx, rx = -3.3, 3.3

        # --- Row 1: straight line vs jagged coastline ---
        line_smooth = Line(
            [lx - 0.85, rows_y[0], 0], [lx + 0.85, rows_y[0], 0], color=ACCENT_CYAN, stroke_width=4
        )
        coast = _midpoint_disp(
            [rx - 0.95, rows_y[0], 0], [rx + 0.95, rows_y[0], 0], depth=5, rough=0.42, seed=7
        )
        coast_m = _polyline(coast, ACCENT_PINK, 2.6)
        lab1l = Text("直線", font=FONT, font_size=18, color=TEXT_DIM)
        lab1l.next_to(line_smooth, DOWN, buff=0.12)
        lab1r = Text("海岸線", font=FONT, font_size=18, color=TEXT_DIM)
        lab1r.next_to(coast_m, DOWN, buff=0.12)

        # --- Row 2: circle vs Koch snowflake ---
        circ = Circle(radius=0.5, color=ACCENT_CYAN, stroke_width=4)
        circ.move_to([lx, rows_y[1], 0])
        snow_pts = _koch_snowflake([rx, rows_y[1]], 0.55, depth=3)
        snow_m = _polyline(snow_pts, ACCENT_PINK, 2.2)
        lab2l = Text("円", font=FONT, font_size=18, color=TEXT_DIM)
        lab2l.next_to(circ, DOWN, buff=0.12)
        lab2r = Text("コッホ曲線", font=FONT, font_size=18, color=TEXT_DIM)
        lab2r.next_to(snow_m, DOWN, buff=0.10)

        # --- Row 3: smooth triangle (cone/mountain) vs rough ridge ---
        tri = Polygon(
            [lx, rows_y[2] + 0.5, 0],
            [lx - 0.6, rows_y[2] - 0.35, 0],
            [lx + 0.6, rows_y[2] - 0.35, 0],
            color=ACCENT_CYAN,
            stroke_width=4,
        )
        ridge_pts = _midpoint_disp(
            [rx - 0.95, rows_y[2] - 0.35, 0],
            [rx + 0.95, rows_y[2] - 0.35, 0],
            depth=5,
            rough=0.55,
            seed=23,
        )
        ridge_m = _polyline(ridge_pts, ACCENT_PINK, 2.4)
        lab3l = Text("円錐・山", font=FONT, font_size=18, color=TEXT_DIM)
        lab3l.next_to(tri, DOWN, buff=0.10)
        lab3r = Text("山稜", font=FONT, font_size=18, color=TEXT_DIM)
        lab3r.next_to(ridge_m, DOWN, buff=0.10)

        pairs = [
            (VGroup(line_smooth, lab1l), VGroup(coast_m, lab1r)),
            (VGroup(circ, lab2l), VGroup(snow_m, lab2r)),
            (VGroup(tri, lab3l), VGroup(ridge_m, lab3r)),
        ]

        used = 0.7 + 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / (len(pairs) * 2 + 1)

        for left, right in pairs:
            self.play(FadeIn(left), run_time=per)
            self.play(FadeIn(right), run_time=per)

        # closing emphasis: the rough (right) column is the rule, not the exception
        self.play(
            Indicate(VGroup(*[r for _, r in pairs]), color=ACCENT_PINK, scale_factor=1.08),
            run_time=per,
        )
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "contrast": {"people": [], "years": []},
}

SCENES = {
    "contrast": EuclidVsFractal,
}
