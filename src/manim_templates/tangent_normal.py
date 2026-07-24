"""
tangent_normal.py - Descartes' method of normals for 数学史記

Visualizes the method of normals from La Géométrie Book II (1637):
to find the tangent to a curve at a point P, Descartes sought a circle
centered on the x-axis that touches the curve at P with a double-root
(tangency) condition. The line from the circle's center to P is the
normal; the tangent is perpendicular to it.

This is a pre-calculus solution to the tangent problem, half a century
before Newton and Leibniz.

Fixed parameters (verified with sympy):
    Curve:         y = x² (parabola)
    Point P:       (1, 1)
    Circle center: (c, 0) on x-axis
    Tangency cond: g'(1) = 0 where g(x) = (x-c)² + x⁴
                   → 2(1-c) + 4 = 0 → c = 3
    Radius:        r² = (1-3)² + 1⁴ = 5, so r = √5
    Normal slope:  (1-0)/(1-3) = -1/2
    Tangent slope: 2 (perpendicular to normal)
    Tangent:       y = 2x - 1
    Modern check:  dy/dx = 2x, at x=1 gives 2. ✓ Matches.

Modes:
    circle_sweep - Sweep c from 0 to 5, visualize how circles intersect
                   the parabola, highlight c=3 as the tangency point.
    derivation   - Step-through of the algebraic derivation of c=3.
    to_tangent   - Show normal → perpendicular tangent → y=2x-1, and
                   its agreement with modern differentiation dy/dx=2x.

Duration-aware: reads target duration from _manim_params.json.
Y range: -0.6 to +3.0, title at +3.0, subtitle clearance preserved.

Used by: Episode 012 (Descartes), math pillar 3
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    Circle,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Scene,
    Text,
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


class TangentNormal(Scene):
    """Descartes' method of normals — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "circle_sweep")
        self._duration = params.get("duration", 35)

        if mode == "derivation":
            self._build_derivation()
        elif mode == "to_tangent":
            self._build_to_tangent()
        else:
            self._build_circle_sweep()

    # ------------------------------------------------------------------
    def _make_axes(self, shift=DOWN * 0.3):
        axes = Axes(
            x_range=[-1.5, 4.0, 1],
            y_range=[-0.4, 2.8, 1],
            x_length=6.5,
            y_length=3.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.5},
        )
        axes.shift(shift)
        return axes

    def _draw_parabola(self, axes):
        return axes.plot(
            lambda x: x * x,
            x_range=[-1.2, 2.2],
            color=ACCENT_GOLD,
            stroke_width=3,
        )

    # ------------------------------------------------------------------
    def _build_circle_sweep(self):
        duration = self._duration

        title = Text("法線法 ── 接触する円を探す", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"y = x^2", font_size=32, color=ACCENT_CYAN)
        eq.move_to([-4.8, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.5)

        axes = self._make_axes(shift=DOWN * 0.5)
        self.play(FadeIn(axes), run_time=0.5)

        parabola = self._draw_parabola(axes)
        self.play(FadeIn(parabola), run_time=0.7)

        # Point P(1, 1)
        p_pos = axes.c2p(1, 1)
        p_dot = Dot(p_pos, radius=0.1, color=ACCENT_PINK)
        p_label = MathTex(r"P(1, 1)", font_size=26, color=ACCENT_PINK)
        p_label.next_to(p_dot, UP + LEFT * 0.3, buff=0.1)
        self.play(FadeIn(p_dot), FadeIn(p_label), run_time=0.6)

        # Sweep circles c = 0.5, 1.5, 2.5, then c=3.0 (tangent)
        c_values = [0.5, 1.5, 2.5, 3.0]
        header_anim = 0.6 + 0.5 + 0.5 + 0.7 + 0.6
        per_c_budget = max(1.0, (duration - header_anim - 3.0) / len(c_values))

        # Compute screen scale from axes
        ux = (axes.c2p(1, 0) - axes.c2p(0, 0))[0]

        prev_circle = None
        prev_center_dot = None
        prev_c_label = None

        for c in c_values:
            # radius so that circle passes through P(1,1): r = sqrt((1-c)^2 + 1)
            r = math.sqrt((1 - c) ** 2 + 1)
            center_world = axes.c2p(c, 0)
            screen_r = abs(ux) * r

            is_tangent = abs(c - 3.0) < 1e-6
            circle_color = ACCENT_GOLD if is_tangent else ACCENT_CYAN
            stroke_w = 4 if is_tangent else 2
            circ = Circle(radius=screen_r, color=circle_color, stroke_width=stroke_w)
            circ.move_to(center_world)

            center_dot = Dot(center_world, radius=0.06, color=circle_color)
            c_label = MathTex(f"c={c:g}", font_size=22, color=circle_color)
            # Place label above the dot to avoid overlapping x-axis
            c_label.next_to(center_dot, UP, buff=0.15)

            if prev_circle is not None:
                self.play(
                    FadeOut(prev_circle),
                    FadeOut(prev_center_dot),
                    FadeOut(prev_c_label),
                    run_time=0.25,
                )

            self.play(
                FadeIn(circ),
                FadeIn(center_dot),
                FadeIn(c_label),
                run_time=min(0.5, per_c_budget * 0.4),
            )
            self.wait(max(0.2, per_c_budget - 0.5))

            # For tangent case (c=3), do NOT set prev so it stays visible
            if is_tangent:
                break
            prev_circle = circ
            prev_center_dot = center_dot
            prev_c_label = c_label

        # Announce tangency (c=3 circle remains on screen)
        # x-axis is at screen y≈-1.85, so place note well above it
        tangency_note = Text(
            "c=3 のとき、円は P で曲線に接する",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        tangency_note.move_to([0, 2.5, 0])
        self.play(FadeIn(tangency_note), run_time=0.6)

        self.wait(2.0)

    # ------------------------------------------------------------------
    def _build_derivation(self):
        duration = self._duration

        title = Text("重根条件から c を決める", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        lines = [
            (r"(x - c)^2 + y^2 = r^2", "円"),
            (r"y = x^2 \;\Rightarrow\; (x - c)^2 + x^4 = r^2", "代入"),
            (r"g(x) = (x - c)^2 + x^4 - r^2", "整理"),
            (r"g'(x) = 2(x - c) + 4x^3", "微分"),
            (r"g'(1) = 0 \;\Rightarrow\; 2(1 - c) + 4 = 0", "重根条件"),
            (r"c = 3, \quad r = \sqrt{5}", "解"),
        ]

        y_start = 2.2
        y_step = 0.75
        anim_budget_per_line = max(0.8, (duration - 2.0) / len(lines))

        for i, (expr, tag) in enumerate(lines):
            y = y_start - i * y_step
            color = ACCENT_PINK if i == len(lines) - 1 else TEXT_WHITE
            fs = 34 if i == len(lines) - 1 else 30
            eq = MathTex(expr, font_size=fs, color=color)
            eq.move_to([-0.8, y, 0])

            tag_label = Text(tag, font=FONT, font_size=20, color=TEXT_DIM)
            tag_label.next_to(eq, RIGHT, buff=0.6)

            self.play(FadeIn(eq), FadeIn(tag_label), run_time=0.6)
            self.wait(max(0.1, anim_budget_per_line - 0.6))

        self.wait(1.0)

    # ------------------------------------------------------------------
    def _build_to_tangent(self):
        duration = self._duration

        title = Text("法線から接線へ", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        axes = self._make_axes(shift=DOWN * 0.5)
        self.play(FadeIn(axes), run_time=0.5)

        parabola = self._draw_parabola(axes)
        self.play(FadeIn(parabola), run_time=0.6)

        # Point P(1,1)
        p_pos = axes.c2p(1, 1)
        p_dot = Dot(p_pos, radius=0.1, color=ACCENT_PINK)
        p_label = MathTex(r"P(1, 1)", font_size=24, color=ACCENT_PINK)
        p_label.next_to(p_dot, UP + LEFT * 0.3, buff=0.1)
        self.play(FadeIn(p_dot), FadeIn(p_label), run_time=0.5)

        # Circle center (3, 0)
        center_pos = axes.c2p(3, 0)
        ux = (axes.c2p(1, 0) - axes.c2p(0, 0))[0]
        screen_r = abs(ux) * math.sqrt(5)
        circ = Circle(radius=screen_r, color=ACCENT_CYAN, stroke_width=2)
        circ.move_to(center_pos)

        center_dot = Dot(center_pos, radius=0.07, color=ACCENT_CYAN)
        center_label = MathTex(r"(3, 0)", font_size=22, color=ACCENT_CYAN)
        center_label.next_to(center_dot, DOWN, buff=0.1)
        self.play(FadeIn(circ), FadeIn(center_dot), FadeIn(center_label), run_time=0.7)

        # Normal line: from (3,0) through P(1,1), extend a bit
        # Parametrize: point = (3,0) + t * ((1,1) - (3,0)) = (3,0) + t*(-2,1)
        normal_start = axes.c2p(3 - 0.6 * (-2), 0 - 0.6 * 1)  # extend behind center
        normal_end = axes.c2p(1 + 0.5 * (-2), 1 + 0.5 * 1)  # extend past P
        normal_line = Line(normal_start, normal_end, color=ACCENT_PINK, stroke_width=3)
        normal_label = Text("法線", font=FONT, font_size=22, color=ACCENT_PINK)
        normal_label.move_to(axes.c2p(2.5, -0.15))
        self.play(FadeIn(normal_line), FadeIn(normal_label), run_time=0.6)

        # Tangent line: y = 2x - 1, plot over x range around P
        tan_start = axes.c2p(0.2, 2 * 0.2 - 1)
        tan_end = axes.c2p(1.8, 2 * 1.8 - 1)
        tangent_line = Line(tan_start, tan_end, color=ACCENT_GOLD, stroke_width=3)
        tangent_label = Text("接線", font=FONT, font_size=22, color=ACCENT_GOLD)
        tangent_label.move_to(axes.c2p(1.9, 2.4))
        self.play(FadeIn(tangent_line), FadeIn(tangent_label), run_time=0.6)

        # Result equations (top right)
        tangent_eq = MathTex(r"y = 2x - 1", font_size=32, color=ACCENT_GOLD)
        tangent_eq.move_to([-4.3, 2.3, 0])
        self.play(FadeIn(tangent_eq), run_time=0.5)

        modern_eq = MathTex(
            r"\frac{dy}{dx} = 2x,\quad x=1 \Rightarrow 2",
            font_size=28,
            color=ACCENT_CYAN,
        )
        modern_eq.move_to([-4.3, 1.65, 0])
        self.play(FadeIn(modern_eq), run_time=0.5)

        check = Text("現代の微分と一致", font=FONT, font_size=20, color=TEXT_DIM)
        check.move_to([-4.3, 1.15, 0])
        self.play(FadeIn(check), run_time=0.5)

        anim_time = 0.6 + 0.5 + 0.6 + 0.5 + 0.7 + 0.6 + 0.6 + 0.5 + 0.5 + 0.5
        self.wait(max(1.0, duration - anim_time))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "circle_sweep": {"people": [], "years": []},
    "derivation": {"people": [], "years": []},
    "to_tangent": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
SCENES = {
    "circle_sweep": TangentNormal,
    "derivation": TangentNormal,
    "to_tangent": TangentNormal,
}
