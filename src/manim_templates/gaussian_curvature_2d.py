"""
gaussian_curvature_2d.py — Theorema Egregium 2D visualization for 数学史記

2D alternative for Pillar 4: Gaussian curvature explained with
flat diagrams, color-coded surfaces, and map projection distortion.

Modes:
    curvature_types  - Show positive (sphere cross-section), zero (flat/cylinder),
                       negative (saddle cross-section) with color coding.
    map_distortion   - Grid on circle (globe) vs grid on rectangle (map).
                       Grid cells near poles stretch to show distortion.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 010 (Gauss) — Pillar 4 benchmark
"""

import math

from manim import (
    UP,
    Arc,
    Circle,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
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
    FONT,
    TEXT_DIM,
    load_params,
)

config.background_color = BG_COLOR


def _calc_wait_scale(duration, anim_time, default_wait_total):
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class GaussianCurvature2D(Scene):
    """Gaussian curvature in 2D — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "curvature_types")
        self._duration = params.get("duration", 18)

        if mode == "map_distortion":
            self._build_map_distortion()
        else:
            self._build_curvature_types()

    def _build_curvature_types(self):
        duration = self._duration

        title = Text(
            "曲率 ── 曲面の本質",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 3 * 1.5 + 0.8
        default_waits = 3 * 0.8 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Three columns: positive, zero, negative
        col_x = [-3.8, 0, 3.8]
        labels = ["K > 0", "K = 0", "K < 0"]
        names = ["球面", "平面・円筒", "鞍面"]
        colors = [ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK]

        for i, (x, label, name, color) in enumerate(
            zip(col_x, labels, names, colors, strict=False)
        ):
            # Label
            k_label = MathTex(label, font_size=32, color=color)
            k_label.move_to([x, 1.8, 0])

            name_label = Text(name, font=FONT, font_size=20, color=TEXT_DIM)
            name_label.move_to([x, 1.3, 0])

            # Shape
            if i == 0:  # Positive: circle (sphere cross-section)
                shape = Circle(
                    radius=0.9, color=color, stroke_width=3, fill_color=color, fill_opacity=0.15
                )
                # Add curved arrows to suggest bulging
                arc1 = Arc(radius=0.9, start_angle=0.3, angle=0.8, color=color, stroke_width=2)
                arc2 = Arc(radius=0.9, start_angle=2.5, angle=0.8, color=color, stroke_width=2)
                shape = VGroup(shape, arc1, arc2)
            elif i == 1:  # Zero: rectangle (flat sheet)
                shape = Rectangle(
                    width=1.8,
                    height=1.2,
                    color=color,
                    stroke_width=3,
                    fill_color=color,
                    fill_opacity=0.1,
                )
                # Add arrow showing it can bend
                bend_text = Text("曲げてもK=0", font=FONT, font_size=14, color=TEXT_DIM)
                bend_text.move_to([x, -0.9, 0])
                shape = VGroup(shape, bend_text)
            else:  # Negative: saddle shape (like a Pringles chip)
                import numpy as np
                from manim import Arrow, ParametricFunction

                # Main curve: upward bend (like sitting in a saddle front-to-back)
                curve_up = ParametricFunction(
                    lambda t: np.array([t, 0.5 * t**2, 0]),
                    t_range=[-1.0, 1.0],
                    color=color,
                    stroke_width=3,
                )
                # Shift cross curve to horizontal representation
                curve_down_h = ParametricFunction(
                    lambda t: np.array([t, -0.5 * t**2, 0]),
                    t_range=[-1.0, 1.0],
                    color=color,
                    stroke_width=3,
                    stroke_opacity=0.6,
                )
                # Small arrows showing opposite curvature directions
                arr_up = Arrow(
                    start=[0, 0.3, 0],
                    end=[0, 0.7, 0],
                    color=color,
                    stroke_width=2,
                    max_tip_length_to_length_ratio=0.3,
                    buff=0,
                )
                arr_down = Arrow(
                    start=[0.5, 0, 0],
                    end=[0.5, -0.4, 0],
                    color=color,
                    stroke_width=2,
                    max_tip_length_to_length_ratio=0.3,
                    buff=0,
                )
                saddle_note = Text("上に凸、横に凹", font=FONT, font_size=14, color=TEXT_DIM)
                saddle_note.move_to([x, -0.9, 0])
                shape = VGroup(curve_up, curve_down_h, arr_up, arr_down, saddle_note)

            shape.move_to([x, 0.1, 0])

            self.play(FadeIn(k_label), FadeIn(name_label), FadeIn(shape), run_time=1.5)
            self.wait(0.5 * ws)

        # Bottom note
        note = Text(
            "曲率は曲面の内在的な量 ── 曲げても変わらない",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.9, 0])
        self.play(FadeIn(note), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    def _build_map_distortion(self):
        duration = self._duration

        title = Text(
            "完全な世界地図は作れない",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 1.0 + 1.0 + 1.5 + 0.8
        default_waits = 0.5 + 0.5 + 0.8 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Left: circle (globe) with uniform grid
        globe = Circle(radius=1.5, color=ACCENT_GOLD, stroke_width=2)
        globe.move_to([-3, 0, 0])

        # Grid lines on circle
        globe_grid = VGroup()
        for lat in [-0.8, -0.4, 0, 0.4, 0.8]:
            half_w = math.sqrt(max(1.5**2 - lat**2, 0))
            if half_w > 0.1:
                line = Line(
                    [-3 - half_w, lat, 0],
                    [-3 + half_w, lat, 0],
                    color=ACCENT_GOLD,
                    stroke_width=1,
                    stroke_opacity=0.5,
                )
                globe_grid.add(line)
        for lon_x in [-0.8, -0.4, 0, 0.4, 0.8]:
            half_h = math.sqrt(max(1.5**2 - lon_x**2, 0))
            if half_h > 0.1:
                line = Line(
                    [-3 + lon_x, -half_h, 0],
                    [-3 + lon_x, half_h, 0],
                    color=ACCENT_GOLD,
                    stroke_width=1,
                    stroke_opacity=0.5,
                )
                globe_grid.add(line)

        globe_label = Text("K > 0", font=FONT, font_size=22, color=ACCENT_GOLD)
        globe_label.move_to([-3, -2.0, 0])

        self.play(FadeIn(globe), FadeIn(globe_grid), FadeIn(globe_label), run_time=1.0)
        self.wait(0.3 * ws)

        # Arrow
        arrow = Text("-->", font=FONT, font_size=36, color=TEXT_DIM)
        arrow.move_to([0, 0, 0])
        self.play(FadeIn(arrow), run_time=0.5)

        # Right: rectangle (map) with distorted grid
        map_rect = Rectangle(width=3.0, height=2.0, color=ACCENT_PINK, stroke_width=2)
        map_rect.move_to([3.2, 0, 0])

        # Distorted grid: cells stretch near top and bottom (poles)
        map_grid = VGroup()
        # Horizontal lines (latitudes) - evenly spaced
        for y_frac in [-0.8, -0.4, 0, 0.4, 0.8]:
            y = y_frac
            line = Line(
                [3.2 - 1.5, y, 0],
                [3.2 + 1.5, y, 0],
                color=ACCENT_PINK,
                stroke_width=1,
                stroke_opacity=0.5,
            )
            map_grid.add(line)
        # Vertical lines (longitudes) - stretched at poles
        for x_frac in [-0.8, -0.4, 0, 0.4, 0.8]:
            # Longitudes converge at poles on globe but are parallel on map
            line = Line(
                [3.2 + x_frac, -1.0, 0],
                [3.2 + x_frac, 1.0, 0],
                color=ACCENT_PINK,
                stroke_width=1,
                stroke_opacity=0.5,
            )
            map_grid.add(line)

        # Highlight distortion at poles
        pole_top = Rectangle(
            width=3.0,
            height=0.3,
            color=ACCENT_PINK,
            stroke_width=0,
            fill_opacity=0.2,
        )
        pole_top.move_to([3.2, 0.85, 0])
        pole_bot = Rectangle(
            width=3.0,
            height=0.3,
            color=ACCENT_PINK,
            stroke_width=0,
            fill_opacity=0.2,
        )
        pole_bot.move_to([3.2, -0.85, 0])

        map_label = Text("K = 0 (歪みあり)", font=FONT, font_size=22, color=ACCENT_PINK)
        map_label.move_to([3.2, -2.0, 0])

        self.play(
            FadeIn(map_rect),
            FadeIn(map_grid),
            FadeIn(pole_top),
            FadeIn(pole_bot),
            FadeIn(map_label),
            run_time=1.5,
        )
        self.wait(0.5 * ws)

        # Bottom conclusion
        note = Text(
            "球面(K>0)を平面(K=0)に展開すると必ず歪む",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -2.0, 0])

        # Move labels up to make room
        self.play(
            globe_label.animate.move_to([-3, -1.7, 0]),
            map_label.animate.move_to([3.2, -1.7, 0]),
            run_time=0.3,
        )
        note.move_to([0, -2.2, 0])
        self.play(FadeIn(note), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "curvature_types": {"people": [], "years": []},
    "map_distortion": {"people": [], "years": []},
}


SCENES = {
    "curvature_types": GaussianCurvature2D,
    "map_distortion": GaussianCurvature2D,
}
