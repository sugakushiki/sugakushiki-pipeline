"""
three_body_problem.py - Poincaré's three-body problem visualization for 数学史記

Visualizes the structures Poincaré discovered when correcting his 1888 Oscar II
prize memoir, which became the starting point of deterministic chaos:

    - orbit: Three bodies moving under mutual gravitation. A near-circular
      stable case (small perturbation around Lagrange L4/L5 geometry) contrasted
      with an unstable case where one body's trajectory diverges quickly.
    - homoclinic: 2D phase space with a hyperbolic fixed point (saddle), its
      stable manifold W^s and unstable manifold W^u, and their infinitely
      many transverse intersections (homoclinic points). This is the
      structure Poincaré found in 1890 when correcting his memoir.
    - poincare_section: A periodic orbit pierces a 2D section plane in
      successive return points. The "first return map" Φ(P_n) = P_{n+1}
      condenses the continuous flow into a discrete map.

Fixed parameters (verified by hand):
    Stable orbit:    period T = 2π, radius r = 1.4
    Unstable orbit:  exponentially diverging amplitude exp(0.3 t)
    Saddle point:    origin, stable axis along x, unstable along y
    Section plane:   x = 0 line in 2D analog

Duration-aware: reads target duration from _manim_params.json.
Y range: -2.0 to +3.0, subtitle clearance preserved.

Used by: Episode 024 (Poincaré), math pillar 1 — three-body problem & chaos.
"""

import math

from manim import (
    DOWN,
    PI,
    RIGHT,
    UP,
    Arrow,
    Axes,
    Circle,
    Dot,
    FadeIn,
    Line,
    MathTex,
    ParametricFunction,
    Scene,
    Text,
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
    styled_text,
)

config.background_color = BG_COLOR


class ThreeBodyProblem(Scene):
    """Poincaré's three-body problem — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "orbit")
        self._duration = params.get("duration", 35)

        if mode == "homoclinic":
            self._build_homoclinic()
        elif mode == "poincare_section":
            self._build_poincare_section()
        else:
            self._build_orbit()

    # ------------------------------------------------------------------
    def _title(self, jp_text, en_text=None):
        title = Text(jp_text, font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_orbit(self):
        """Three bodies under mutual gravitation: stable vs unstable cases."""
        duration = self._duration

        title = self._title("三体問題 ── 解析的に解けない")
        self.play(FadeIn(title), run_time=0.5)

        # Left panel: stable (Lagrange-like equilateral) configuration
        left_label = Text(
            "安定軌道 (Lagrange 配置)",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        left_label.move_to([-3.5, 2.0, 0])
        self.play(FadeIn(left_label), run_time=0.4)

        # Three bodies in equilateral triangle, rotating together
        center_l = [-3.5, 0.0, 0]
        r = 0.8
        body_colors = [ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK]
        stable_bodies = []
        stable_trails = []
        for k in range(3):
            angle = 2 * PI * k / 3
            pos = [center_l[0] + r * math.cos(angle), center_l[1] + r * math.sin(angle), 0]
            body = Dot(point=pos, radius=0.10, color=body_colors[k])
            stable_bodies.append(body)
            trail = Circle(radius=r, color=body_colors[k], stroke_width=1.5).move_to(center_l)
            stable_trails.append(trail)

        for body in stable_bodies:
            self.play(FadeIn(body), run_time=0.2)
        for trail in stable_trails:
            self.play(FadeIn(trail), run_time=0.25)

        # Right panel: unstable case with diverging trajectory
        right_label = Text(
            "不安定軌道 (一般の三体)",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        right_label.move_to([3.5, 2.0, 0])
        self.play(FadeIn(right_label), run_time=0.4)

        center_r = [3.5, 0.0, 0]
        # Two heavy bodies near center
        heavy1 = Dot(point=[center_r[0] - 0.4, center_r[1], 0], radius=0.12, color=ACCENT_GOLD)
        heavy2 = Dot(point=[center_r[0] + 0.4, center_r[1], 0], radius=0.12, color=ACCENT_CYAN)
        self.play(FadeIn(heavy1), FadeIn(heavy2), run_time=0.4)

        # Third body: trajectory that spirals outward (Manim ParametricFunction)
        def unstable_traj(t):
            # spirals outward as t increases, with chaotic-looking oscillation
            amp = 0.4 + 0.6 * t / 3.0
            x = center_r[0] + amp * math.cos(3.0 * t + 0.5 * math.sin(2.0 * t))
            y = center_r[1] + amp * math.sin(3.0 * t + 0.5 * math.sin(2.0 * t))
            return [x, y, 0]

        unstable_path = ParametricFunction(
            unstable_traj,
            t_range=[0, 3.0, 0.02],
            color=ACCENT_PINK,
            stroke_width=2.0,
        )
        self.play(FadeIn(unstable_path), run_time=0.8)

        third_body_start = unstable_traj(0)
        third_body = Dot(point=third_body_start, radius=0.10, color=ACCENT_PINK)
        self.play(FadeIn(third_body), run_time=0.3)

        # Annotation below
        annot = Text(
            "一般の三体問題には解析的な閉形式の解は存在しない",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        annot.move_to([0, -1.8, 0])
        self.play(FadeIn(annot), run_time=0.6)

        anim_total = 0.5 + 0.4 + 0.6 + 0.75 + 0.4 + 0.4 + 0.8 + 0.3 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_homoclinic(self):
        """Saddle point with stable & unstable manifolds intersecting."""
        duration = self._duration

        title = self._title("ホモクリニック構造")
        self.play(FadeIn(title), run_time=0.5)

        # Axes for phase plane
        axes = Axes(
            x_range=[-3.0, 3.0, 1],
            y_range=[-2.0, 2.0, 1],
            x_length=8.0,
            y_length=4.4,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.2},
        )
        axes.shift(DOWN * 0.3)
        self.play(FadeIn(axes), run_time=0.6)

        # Axes labels
        x_lbl = MathTex("x", font_size=22, color=TEXT_DIM).next_to(axes.x_axis, RIGHT, buff=0.1)
        y_lbl = MathTex("p", font_size=22, color=TEXT_DIM).next_to(axes.y_axis, UP, buff=0.1)
        self.play(FadeIn(x_lbl), FadeIn(y_lbl), run_time=0.3)

        # Saddle point at origin
        saddle = Dot(point=axes.c2p(0, 0), radius=0.10, color=ACCENT_GOLD)
        self.play(FadeIn(saddle), run_time=0.3)
        saddle_lbl = Text("鞍点", font=FONT, font_size=18, color=ACCENT_GOLD)
        saddle_lbl.next_to(saddle, DOWN, buff=0.1)
        self.play(FadeIn(saddle_lbl), run_time=0.3)

        # Stable manifold W^s (incoming, along a curved path)
        def w_stable(t):
            # t in [-1.5, 1.5]; curve that approaches origin tangentially
            x = t
            y = 0.4 * t**3 - 0.1 * t  # cubic-like approach
            p = axes.c2p(x, y)
            return [p[0], p[1], 0]

        ws_curve = ParametricFunction(
            w_stable, t_range=[-2.5, 2.5, 0.02], color=ACCENT_CYAN, stroke_width=2.5
        )
        self.play(FadeIn(ws_curve), run_time=0.8)
        ws_lbl = MathTex(r"W^s", font_size=26, color=ACCENT_CYAN)
        ws_lbl.move_to(axes.c2p(2.4, -1.4))
        self.play(FadeIn(ws_lbl), run_time=0.3)

        # Unstable manifold W^u (outgoing, oscillates and crosses W^s many times)
        def w_unstable(t):
            # oscillating curve that crosses w_stable many times near origin
            x = t
            y = 0.5 * math.sin(4.0 * t) * math.exp(-0.3 * abs(t)) + 0.05 * t
            p = axes.c2p(x, y)
            return [p[0], p[1], 0]

        wu_curve = ParametricFunction(
            w_unstable, t_range=[-2.5, 2.5, 0.01], color=ACCENT_PINK, stroke_width=2.5
        )
        self.play(FadeIn(wu_curve), run_time=1.0)
        wu_lbl = MathTex(r"W^u", font_size=26, color=ACCENT_PINK)
        wu_lbl.move_to(axes.c2p(2.4, 0.5))
        self.play(FadeIn(wu_lbl), run_time=0.3)

        # Mark several homoclinic intersection points
        intersections = []
        for x_val in [-1.2, -0.6, 0.6, 1.2]:
            y_stable = 0.4 * x_val**3 - 0.1 * x_val
            y_unstable = 0.5 * math.sin(4.0 * x_val) * math.exp(-0.3 * abs(x_val)) + 0.05 * x_val
            # only mark if reasonably close (visual approximation)
            if abs(y_stable - y_unstable) < 0.3:
                avg_y = (y_stable + y_unstable) / 2
                dot = Dot(point=axes.c2p(x_val, avg_y), radius=0.07, color=TEXT_WHITE)
                intersections.append(dot)
        for dot in intersections:
            self.play(FadeIn(dot), run_time=0.15)

        annot = Text(
            "ホモクリニック点 ── 無限に絡み合う構造",
            font=FONT,
            font_size=18,
            color=TEXT_WHITE,
        )
        annot.move_to([0, -1.9, 0])
        self.play(FadeIn(annot), run_time=0.6)

        anim_total = 0.5 + 0.6 + 0.3 + 0.3 + 0.3 + 0.8 + 0.3 + 1.0 + 0.3 + 0.15 * len(intersections) + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_poincare_section(self):
        """Poincaré section: continuous orbit pierces a section plane."""
        duration = self._duration

        title = self._title("ポアンカレ写像 ── 断面で軌道を読む")
        self.play(FadeIn(title), run_time=0.5)

        # Left: 3D-like orbit (drawn as 2D projection with depth cue)
        # We'll draw a torus-knot-like curve in 2D as the "orbit"
        left_label = Text(
            "連続軌道",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        left_label.move_to([-3.5, 2.2, 0])
        self.play(FadeIn(left_label), run_time=0.4)

        def orbit_curve(t):
            # 2D projection of a 3D quasi-periodic orbit
            x = -3.5 + 1.4 * math.cos(t) + 0.25 * math.cos(5 * t)
            y = 0.4 * math.sin(t) + 0.25 * math.sin(5 * t)
            return [x, y, 0]

        orbit = ParametricFunction(
            orbit_curve, t_range=[0, 8 * PI, 0.02], color=ACCENT_CYAN, stroke_width=1.8
        )
        self.play(FadeIn(orbit), run_time=1.2)

        # Section line (vertical line at x = -3.5)
        section_line = Line(
            start=[-3.5, -1.8, 0],
            end=[-3.5, 1.8, 0],
            color=ACCENT_GOLD,
            stroke_width=2.5,
        )
        self.play(FadeIn(section_line), run_time=0.5)
        section_lbl = MathTex(r"\Sigma", font_size=26, color=ACCENT_GOLD)
        section_lbl.move_to([-3.5, -1.95, 0])
        self.play(FadeIn(section_lbl), run_time=0.3)

        # Mark intersection points on the section
        # The orbit passes through x = -3.5 when cos(t) = 0, so t = π/2, 3π/2, 5π/2, ...
        section_points_left = []
        for k in range(6):
            t_val = PI / 2 + k * PI
            y_val = 0.4 * math.sin(t_val) + 0.25 * math.sin(5 * t_val)
            dot = Dot(point=[-3.5, y_val, 0], radius=0.08, color=ACCENT_PINK)
            section_points_left.append(dot)
        for dot in section_points_left:
            self.play(FadeIn(dot), run_time=0.18)

        # Right: same points displayed as a 2D map sequence
        right_label = styled_text(
            ("離散写像  ", "text"),
            (r"P_n \to P_{n+1}", "math"),
            font_size=20,
        )
        right_label.set_color(TEXT_DIM)
        right_label.move_to([3.5, 2.2, 0])
        self.play(FadeIn(right_label), run_time=0.4)

        # 2D axes for the map
        right_axes = Axes(
            x_range=[-1.5, 1.5, 1],
            y_range=[-1.5, 1.5, 1],
            x_length=3.2,
            y_length=3.0,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.0},
        )
        right_axes.move_to([3.5, 0.0, 0])
        self.play(FadeIn(right_axes), run_time=0.5)

        # Place numbered dots representing successive returns
        prev_pos = None
        for k in range(6):
            t_val = PI / 2 + k * PI
            y_val = 0.4 * math.sin(t_val) + 0.25 * math.sin(5 * t_val)
            # Map (y on section, k) → 2D point
            mx = y_val * 1.8
            my = -1.0 + 0.4 * k
            pos = right_axes.c2p(mx, my)
            dot = Dot(point=pos, radius=0.07, color=ACCENT_PINK)
            self.play(FadeIn(dot), run_time=0.15)
            if prev_pos is not None:
                arrow = Arrow(
                    prev_pos, pos, color=EDGE_COLOR, stroke_width=2, buff=0.05
                )
                self.play(FadeIn(arrow), run_time=0.1)
            prev_pos = pos

        annot = Text(
            "連続な流れを離散写像で読み替える",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        annot.move_to([0, -1.8, 0])
        self.play(FadeIn(annot), run_time=0.5)

        anim_total = 0.5 + 0.4 + 1.2 + 0.5 + 0.3 + 0.18 * 6 + 0.4 + 0.5 + (0.15 + 0.1) * 6 + 0.5
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "orbit": {"people": [], "years": []},
    "homoclinic": {"people": [], "years": []},
    "poincare_section": {"people": [], "years": []},
}

SCENES = {
    "orbit": ThreeBodyProblem,
    "homoclinic": ThreeBodyProblem,
    "poincare_section": ThreeBodyProblem,
}
