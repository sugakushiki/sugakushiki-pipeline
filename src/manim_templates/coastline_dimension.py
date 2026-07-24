"""
coastline_dimension.py - "How long is the coast?" and the fractional dimension

Episode 042 (Mandelbrot), block 3 (pillar 1). Measuring a rough coastline with
a ruler of length epsilon gives a total length that keeps growing as epsilon
shrinks -- not from measurement error, but because the coastline is rough. The
answer is not a length but a fractional dimension between 1 and 2. Lewis Fry
Richardson found this empirically; Mandelbrot reinterpreted it as a fractal
dimension (credited in the narration, not on screen).

Modes:
    ruler (default)
        A fixed jagged coastline. It is "walked" with rulers of length
        epsilon = 1.0, 0.5, 0.25; each shorter ruler hugs more inlets, so the
        measured length L = N * epsilon increases. A readout lists the three
        (epsilon, L) pairs.
        Fixed params: coastline = midpoint displacement depth 7 (seed 11);
        epsilon in {1.0, 0.5, 0.25}; measured lengths rise monotonically.
    loglog
        log L plotted against log(1/epsilon) for five rulers; the points fall on
        a line of slope ~0.25, and since slope = D - 1, the dimension is
        D ~ 1.25.
        Fixed params: 5 rulers; slope 0.25; D = 1 + slope ~ 1.25.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.65 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math
import random

import numpy as np
from manim import (
    RIGHT,
    UP,
    Axes,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def _midpoint_disp(p0, p1, depth, rough, seed, decay=0.5):
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
        amp *= decay
    return pts


def _walk(points, eps, cap=4000):
    """Lay chords of Euclidean length eps along the polyline; return anchors.

    Divider-walking: from the current anchor, advance along the polyline to the
    first point at Euclidean distance eps, place a vertex there, repeat.
    """
    anchors = [np.array(points[0], dtype=float)]
    anchor = anchors[0]
    i = 0
    n = len(points)
    while i < n - 1 and len(anchors) < cap:
        j = i
        found = None
        found_j = i
        while j < n - 1:
            seg_a = np.array(points[j], dtype=float)
            seg_b = np.array(points[j + 1], dtype=float)
            d = seg_b - seg_a
            f = seg_a - anchor  # point = seg_a + t d; |point - anchor|^2 = |f + t d|^2
            A = d.dot(d)
            if A < 1e-12:
                j += 1
                continue
            B = 2 * d.dot(f)
            C = f.dot(f) - eps * eps
            disc = B * B - 4 * A * C
            if disc >= 0:
                t = (-B + math.sqrt(disc)) / (2 * A)
                if 0 <= t <= 1:
                    found = seg_a + t * d
                    found_j = j
                    break
            j += 1
        if found is None:
            break
        anchors.append(found)
        anchor = found
        i = found_j
    return anchors


def _polyline(points, color, width=2.5):
    m = VMobject()
    m.set_points_as_corners([np.array(p, dtype=float) for p in points])
    m.set_stroke(color=color, width=width)
    return m


class CoastlineDimension(Scene):
    """Coastline ruler measurement and log-log dimension - two modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "ruler")
        duration = float(params.get("duration", 26))
        if mode == "loglog":
            self._build_loglog(duration)
        else:
            self._build_ruler(duration)

    # ------------------------------------------------------------------ ruler
    def _build_ruler(self, duration):
        title = Text("海岸線の長さは？", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        coast = _midpoint_disp(
            [-5.2, 1.3, 0], [5.2, 1.3, 0], depth=7, rough=0.85, seed=11, decay=0.7
        )
        coast_m = _polyline(coast, TEXT_DIM, 2.2)
        self.play(Create(coast_m), run_time=1.4)

        epsilons = [1.0, 0.5, 0.25]
        colors = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK]
        readout = VGroup()
        readout_y0 = -0.45

        used = 0.7 + 1.4
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / (len(epsilons) + 1)

        prev_chords = None
        for k, eps in enumerate(epsilons):
            anchors = _walk(coast, eps)
            N = len(anchors) - 1
            L = N * eps
            chords = _polyline(anchors, colors[k], 3.0)
            dots = VGroup(*[Dot(a, color=colors[k], radius=0.045) for a in anchors])
            if prev_chords is not None:
                self.play(FadeIn(chords), FadeIn(dots), run_time=per * 0.8)
            else:
                self.play(Create(chords), FadeIn(dots), run_time=per)
            row = Text(
                f"ものさし {eps:>4} ── {N}本 ── 長さ {L:.1f}",
                font=FONT,
                font_size=22,
                color=colors[k],
            )
            row.move_to([0, readout_y0 - k * 0.38, 0])
            self.play(FadeIn(row), run_time=per * 0.4)
            readout.add(row)
            if prev_chords is not None:
                self.remove(prev_chords)
            prev_chords = chords
            # keep dots/chords of last iteration visible only briefly to avoid clutter
            if k < len(epsilons) - 1:
                self.remove(dots)

        note = Text(
            "ものさしを縮めるほど、長さは増えていく",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        )
        note.move_to([0, readout_y0 - len(epsilons) * 0.38 - 0.08, 0])
        self.play(FadeIn(note), run_time=per * 0.6)
        self.wait(coda)

    # ----------------------------------------------------------------- loglog
    def _build_loglog(self, duration):
        title = Text("長さではなく、次元", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[0, 1.3, 0.3],
            y_range=[0.3, 1.05, 0.2],
            x_length=6.6,
            y_length=3.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0.2, 0.1, 0])
        x_lab = MathTex(r"\log(1/\varepsilon)", font_size=26, color=TEXT_DIM)
        x_lab.next_to(axes.x_axis, RIGHT, buff=0.15)
        y_lab = MathTex(r"\log L", font_size=26, color=TEXT_DIM)
        y_lab.next_to(axes.y_axis, UP, buff=0.12)
        self.play(FadeIn(axes), FadeIn(x_lab), FadeIn(y_lab), run_time=0.8)

        slope = 0.25
        intercept = 0.5
        xs = [0.0, 0.301, 0.602, 0.903, 1.204]
        jit = [0.0, 0.015, -0.012, 0.018, -0.01]
        pts = [(x, slope * x + intercept + j) for x, j in zip(xs, jit, strict=True)]

        used = 0.7 + 0.8
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / (len(pts) + 3)

        dots = VGroup()
        for x, y in pts:
            d = Dot(axes.c2p(x, y), color=ACCENT_CYAN, radius=0.07)
            self.play(FadeIn(d), run_time=per * 0.6)
            dots.add(d)

        fit = Line(
            axes.c2p(0.0, intercept),
            axes.c2p(1.25, slope * 1.25 + intercept),
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        self.play(Create(fit), run_time=per)

        rel = MathTex(r"\log L = (D-1)\,\log(1/\varepsilon) + c", font_size=26, color=TEXT_WHITE)
        rel.move_to([0, -1.15, 0])
        slope_eq = MathTex(r"\text{slope} = D - 1 \approx 0.25", font_size=26, color=ACCENT_PINK)
        slope_eq.move_to([-3.1, 1.9, 0])
        dim_eq = MathTex(r"D \approx 1.25", font_size=34, color=ACCENT_GOLD)
        dim_eq.move_to([2.7, 1.9, 0])
        self.play(FadeIn(rel), run_time=per)
        self.play(FadeIn(slope_eq), FadeIn(dim_eq), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "ruler": {"people": [], "years": []},
    "loglog": {"people": [], "years": []},
}

SCENES = {
    "ruler": CoastlineDimension,
    "loglog": CoastlineDimension,
}
