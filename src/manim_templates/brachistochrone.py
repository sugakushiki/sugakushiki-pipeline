"""
brachistochrone.py - Brachistochrone problem and the birth of calculus of variations

Visualizes Johann Bernoulli's 1696 challenge: find the curve of fastest
descent under gravity between two points. Answer: cycloid.

Modes:
    challenge   - Present the setup: points A (top) and B (bottom-right)
                  with 3 candidate curves (straight line, circular arc,
                  cycloid). Title poses "どれが最速か？".
                  Fixed params: A=(-3, 1.5), B=(2, -1.7), r=1.6, theta in [0, pi].
    race        - 3 balls start simultaneously from A, each constrained
                  to one of the 3 curves. Cycloid ball finishes first,
                  then arc, then straight line.
                  Fixed params: run_times roughly proportional to physics
                  (cycloid 2.5s, arc 3.1s, line 3.7s).
    cycloid_gen - A circle rolls along a horizontal line; a marked point
                  on the rim traces out the cycloid.
                  Fixed params: r=0.9, rolling over 2 full revolutions
                  (theta from 0 to 4*pi), center moves left-to-right.
    optics      - Johann's solution via Fermat's principle: stratified
                  medium with progressively smaller refractive index,
                  light ray refracts at each layer following Snell's law;
                  cycloid emerges in the infinitesimal limit.
                  Fixed params: 5 layers, incident angle increases per
                  layer, dashed cycloid overlay shows limit curve.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 017 (Johann Bernoulli), math pillar 2 (最速降下線)
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Circle,
    Create,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    MoveAlongPath,
    ParametricFunction,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# Geometry constants (shared across modes)
# ---------------------------------------------------------------------------
# Anchor points A (start, upper-left) and B (end, lower-right)
POINT_A = [-3.0, 1.5, 0]
POINT_B = [2.03, -1.7, 0]  # Chosen so cycloid with r=1.6 over [0,pi] lands here

# Cycloid parameter: theta in [0, pi], r chosen so endpoint matches B.
CYCLOID_R = 1.6


def cycloid_xy(theta):
    """Cycloid starting at POINT_A, going down-right.

    Standard form: x = r(theta - sin theta), y = r(cos theta - 1)
    Shifted so theta=0 → POINT_A, theta=pi → POINT_B.
    """
    x = POINT_A[0] + CYCLOID_R * (theta - math.sin(theta))
    y = POINT_A[1] + CYCLOID_R * (math.cos(theta) - 1)
    return [x, y, 0]


def arc_xy(t):
    """Circular arc from A to B, bulging downward.

    t in [0, 1]. Uses a smooth quadratic bezier-like curve
    that passes through both endpoints and dips below the straight line.
    """
    # Simple parabolic arc: lerp plus a downward bulge
    ax, ay = POINT_A[0], POINT_A[1]
    bx, by = POINT_B[0], POINT_B[1]
    # Linear component
    x = ax + (bx - ax) * t
    y = ay + (by - ay) * t
    # Downward bulge (sin-shaped) to imitate a circular arc
    bulge = 0.6 * math.sin(math.pi * t)
    y -= bulge
    return [x, y, 0]


def line_xy(t):
    """Straight line from A to B. t in [0, 1]."""
    ax, ay = POINT_A[0], POINT_A[1]
    bx, by = POINT_B[0], POINT_B[1]
    return [ax + (bx - ax) * t, ay + (by - ay) * t, 0]


class Brachistochrone(Scene):
    """Brachistochrone problem visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "challenge")

        if mode == "race":
            self.build_race()
        elif mode == "cycloid_gen":
            self.build_cycloid_gen()
        elif mode == "optics":
            self.build_optics()
        else:
            self.build_challenge()

    # -------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------
    def _make_cycloid_curve(self, color=ACCENT_GOLD, stroke_width=4):
        return ParametricFunction(
            lambda t: cycloid_xy(t),
            t_range=[0, math.pi, 0.02],
            color=color,
            stroke_width=stroke_width,
        )

    def _make_arc_curve(self, color=ACCENT_CYAN, stroke_width=4):
        return ParametricFunction(
            lambda t: arc_xy(t),
            t_range=[0, 1, 0.01],
            color=color,
            stroke_width=stroke_width,
        )

    def _make_line_curve(self, color=TEXT_DIM, stroke_width=4):
        return Line(POINT_A, POINT_B, color=color, stroke_width=stroke_width)

    def _make_endpoints(self):
        dot_a = Dot(POINT_A, radius=0.1, color=TEXT_WHITE)
        dot_b = Dot(POINT_B, radius=0.1, color=TEXT_WHITE)
        label_a = Text("A", font=FONT, font_size=24, color=TEXT_WHITE)
        label_a.next_to(dot_a, UP, buff=0.15)
        label_b = Text("B", font=FONT, font_size=24, color=TEXT_WHITE)
        label_b.next_to(dot_b, RIGHT, buff=0.15)
        return VGroup(dot_a, dot_b, label_a, label_b)

    # -------------------------------------------------------------------
    # Mode: challenge
    # -------------------------------------------------------------------
    def build_challenge(self):
        duration = self._duration

        title = Text(
            "最速降下線問題  1696",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)

        subtitle = Text(
            "点Aから点Bへ、重力下で最速の曲線は？",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.2)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(subtitle), run_time=0.5)

        endpoints = self._make_endpoints()
        self.play(FadeIn(endpoints), run_time=0.5)

        # Draw the 3 candidate curves progressively
        line_curve = self._make_line_curve()
        arc_curve = self._make_arc_curve()
        cyc_curve = self._make_cycloid_curve()

        line_label = Text("直線", font=FONT, font_size=22, color=TEXT_DIM)
        line_label.move_to([-0.6, 0.3, 0])

        arc_label = Text("円弧", font=FONT, font_size=22, color=ACCENT_CYAN)
        arc_label.move_to([-0.6, -0.65, 0])

        cyc_label = Text("サイクロイド", font=FONT, font_size=22, color=ACCENT_GOLD)
        cyc_label.move_to([1.0, -1.85, 0])

        self.play(Create(line_curve), FadeIn(line_label), run_time=1.0)
        self.play(Create(arc_curve), FadeIn(arc_label), run_time=1.0)
        self.play(Create(cyc_curve), FadeIn(cyc_label), run_time=1.2)

        question = Text(
            "どれが最速か？",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        )
        # Left-align under point A (POINT_A.x = -3.0), y clear of subtitle
        question.move_to([-3.0 + question.width / 2, -1.7, 0])
        self.play(FadeIn(question), run_time=0.6)

        anim_time = 6.4
        self.wait(max(0.5, duration - anim_time))

    # -------------------------------------------------------------------
    # Mode: race
    # -------------------------------------------------------------------
    def build_race(self):
        duration = self._duration

        title = Text(
            "3つの曲線、同時スタート",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)

        self.play(FadeIn(title), run_time=0.5)

        endpoints = self._make_endpoints()
        line_curve = self._make_line_curve(color=TEXT_DIM, stroke_width=3)
        arc_curve = self._make_arc_curve(color=ACCENT_CYAN, stroke_width=3)
        cyc_curve = self._make_cycloid_curve(color=ACCENT_GOLD, stroke_width=3)

        self.play(
            FadeIn(endpoints),
            Create(line_curve),
            Create(arc_curve),
            Create(cyc_curve),
            run_time=1.0,
        )

        # Three balls at A
        ball_line = Dot(POINT_A, radius=0.14, color=TEXT_WHITE)
        ball_arc = Dot(POINT_A, radius=0.14, color=ACCENT_CYAN)
        ball_cyc = Dot(POINT_A, radius=0.14, color=ACCENT_GOLD)
        balls = VGroup(ball_line, ball_arc, ball_cyc)
        self.play(FadeIn(balls), run_time=0.4)

        # Legend labels
        legend_line = Text("直線", font=FONT, font_size=18, color=TEXT_WHITE)
        legend_arc = Text("円弧", font=FONT, font_size=18, color=ACCENT_CYAN)
        legend_cyc = Text("サイクロイド", font=FONT, font_size=18, color=ACCENT_GOLD)
        legend = VGroup(legend_cyc, legend_arc, legend_line).arrange(
            DOWN, buff=0.15, aligned_edge=LEFT
        )
        legend.move_to([3.5, 1.8, 0])
        self.play(FadeIn(legend), run_time=0.4)

        # Paths for MoveAlongPath
        line_path = self._make_line_curve()
        arc_path = self._make_arc_curve()
        cyc_path = self._make_cycloid_curve()

        # Run times reflect physics: cycloid fastest, arc middle, line slowest.
        t_cyc = 2.5
        t_arc = 3.1
        t_line = 3.7

        # Start all simultaneously, but each with own run_time.
        # MoveAlongPath doesn't support different run_times in one play call
        # for the same animation; play each with its own run_time but start
        # together by using self.play with a single call that has matching
        # internal timing. We'll use the fact that MoveAlongPath accepts
        # run_time per animation.
        self.play(
            MoveAlongPath(ball_cyc, cyc_path, run_time=t_cyc),
            MoveAlongPath(ball_arc, arc_path, run_time=t_arc),
            MoveAlongPath(ball_line, line_path, run_time=t_line),
        )

        # Winner indication
        winner = Text(
            "サイクロイドが最速",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        # Left-align under point A (POINT_A.x = -3.0), y clear of subtitle
        winner.move_to([-3.0 + winner.width / 2, -1.7, 0])
        self.play(FadeIn(winner), Indicate(ball_cyc, color=ACCENT_GOLD), run_time=0.8)

        anim_time = 0.5 + 1.0 + 0.4 + 0.4 + t_line + 0.8
        self.wait(max(0.5, duration - anim_time))

    # -------------------------------------------------------------------
    # Mode: cycloid_gen
    # -------------------------------------------------------------------
    def build_cycloid_gen(self):
        duration = self._duration

        title = Text(
            "サイクロイド ── 転がる円が描く曲線",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        # Rolling circle geometry
        r = 0.9
        ground_y = -1.7
        # Circle starts at x=-5.5, rolls to x=+4.0  (distance ≈ 9.5, about 1.7 revolutions)
        x_start = -5.5
        theta_max = 9.5 / r  # ≈ 10.6 rad, roughly 1.7 full turns

        ground = Line(
            [x_start - 0.5, ground_y, 0],
            [x_start + 9.6, ground_y, 0],
            color=TEXT_DIM,
            stroke_width=1,
        )
        self.play(FadeIn(ground), run_time=0.3)

        # Initial circle (center at (x_start, ground_y + r))
        center_y = ground_y + r
        circle = Circle(radius=r, color=ACCENT_CYAN, stroke_width=2)
        circle.move_to([x_start, center_y, 0])

        # Mark on the rim: start at bottom of circle (contact point)
        mark = Dot([x_start, ground_y, 0], radius=0.1, color=ACCENT_PINK)

        # Radius line from center to mark
        radius_line = Line(
            circle.get_center(),
            mark.get_center(),
            color=ACCENT_PINK,
            stroke_width=2,
        )

        self.play(FadeIn(circle), FadeIn(mark), FadeIn(radius_line), run_time=0.6)

        # Build the traced path as a ParametricFunction
        def rolling_mark(theta):
            cx = x_start + r * theta
            x = cx - r * math.sin(theta)
            y = center_y - r * math.cos(theta)
            return [x, y, 0]

        # Animate: step through theta values, updating circle/mark/trace
        num_steps = 60
        anim_total = min(max(duration - 3.0, 4.0), 12.0)
        step_time = anim_total / num_steps

        # Build trace incrementally
        trace_points = [rolling_mark(0)]
        trace_obj = VGroup()

        for i in range(1, num_steps + 1):
            theta = theta_max * i / num_steps
            new_center = [x_start + r * theta, center_y, 0]
            new_mark_pos = rolling_mark(theta)

            # Move circle, mark, and radius line
            new_circle = Circle(radius=r, color=ACCENT_CYAN, stroke_width=2).move_to(new_center)
            new_mark = Dot(new_mark_pos, radius=0.1, color=ACCENT_PINK)
            new_radius = Line(new_center, new_mark_pos, color=ACCENT_PINK, stroke_width=2)

            # Trace segment
            prev = trace_points[-1]
            seg = Line(prev, new_mark_pos, color=ACCENT_GOLD, stroke_width=3)
            trace_obj.add(seg)
            trace_points.append(new_mark_pos)

            self.remove(circle, mark, radius_line)
            self.add(seg, new_circle, new_mark, new_radius)
            circle = new_circle
            mark = new_mark
            radius_line = new_radius
            self.wait(step_time)

        # Equation label
        equation = MathTex(
            r"x = r(\theta - \sin\theta),\quad y = r(1 - \cos\theta)",
            font_size=24,
            color=TEXT_WHITE,
        )
        equation.to_edge(DOWN, buff=2.3)
        self.play(FadeIn(equation), run_time=0.6)

        anim_time = 0.5 + 0.3 + 0.6 + anim_total + 0.6
        self.wait(max(0.3, duration - anim_time))

    # -------------------------------------------------------------------
    # Mode: optics
    # -------------------------------------------------------------------
    def build_optics(self):
        duration = self._duration

        title = Text(
            "光の屈折から導く ── ヨハンの解法",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)

        subtitle = Text(
            "フェルマーの最小時間原理を応用",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.15)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.8)

        # Stratified medium: 5 horizontal layers between y=1.5 (top) and y=-1.8 (bottom)
        n_layers = 5
        top_y = 1.3
        bottom_y = -1.8
        layer_height = (top_y - bottom_y) / n_layers

        x_left = -4.5
        x_right = 4.5

        layers = VGroup()
        n_labels = VGroup()
        for i in range(n_layers):
            y_top = top_y - i * layer_height
            y_bot = top_y - (i + 1) * layer_height
            # Shaded layer with increasing darkness (simulating changing index)
            opacity = 0.08 + 0.05 * i
            rect = Rectangle(
                width=(x_right - x_left),
                height=layer_height,
                fill_color=ACCENT_CYAN,
                fill_opacity=opacity,
                stroke_color=TEXT_DIM,
                stroke_width=0.5,
            )
            rect.move_to([(x_left + x_right) / 2, (y_top + y_bot) / 2, 0])
            layers.add(rect)
            # Refractive index label
            n_val = 1.0 + 0.4 * i
            label = MathTex(f"n_{{{i + 1}}} = {n_val:.1f}", font_size=16, color=TEXT_DIM)
            label.move_to([x_left - 0.6, (y_top + y_bot) / 2, 0])
            n_labels.add(label)

        self.play(FadeIn(layers), FadeIn(n_labels), run_time=0.8)

        # Light ray: piecewise linear path, angle grows with each layer
        # Start at x=-3, y=1.3 ; bend progressively toward horizontal at bottom
        start_x = -3.0
        start_y = top_y
        angles_from_vertical = [18, 30, 45, 62, 80]  # degrees, grows per layer

        pts = [[start_x, start_y, 0]]
        cur_x, cur_y = start_x, start_y
        for i, ang_deg in enumerate(angles_from_vertical):
            ang_rad = math.radians(ang_deg)
            dx = layer_height * math.tan(ang_rad)
            dy = -layer_height
            cur_x += dx
            cur_y += dy
            pts.append([cur_x, cur_y, 0])

        ray_segments = VGroup()
        for i in range(len(pts) - 1):
            seg = Line(pts[i], pts[i + 1], color=ACCENT_PINK, stroke_width=3)
            ray_segments.add(seg)

        # Animate segment by segment
        for seg in ray_segments:
            self.play(Create(seg), run_time=0.5)

        # Dashed cycloid overlay showing the limit
        cyc_limit = ParametricFunction(
            lambda t: [
                start_x + 1.6 * (t - math.sin(t)),
                start_y + 1.6 * (math.cos(t) - 1),
                0,
            ],
            t_range=[0, math.pi, 0.02],
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        # Don't render the curve directly; use DashedLine segments for effect.
        # Simpler: just draw the cycloid with standard stroke.

        cyc_label = Text(
            "層を無限小に → サイクロイド",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        cyc_label.to_edge(DOWN, buff=2.3)

        self.play(FadeIn(cyc_limit), FadeIn(cyc_label), run_time=1.0)

        anim_time = 0.8 + 0.8 + len(angles_from_vertical) * 0.5 + 1.0
        self.wait(max(0.5, duration - anim_time))


# ---------------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "challenge": {"people": [], "years": ["1696"]},
    "race": {"people": [], "years": []},
    "cycloid_gen": {"people": [], "years": []},
    "optics": {"people": [], "years": []},
}


SCENES = {
    "challenge": Brachistochrone,
    "race": Brachistochrone,
    "cycloid_gen": Brachistochrone,
    "optics": Brachistochrone,
}
