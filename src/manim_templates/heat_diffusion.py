"""
heat_diffusion.py - 1D heat diffusion visualization for 数学史記

Visualizes how temperature distribution in a bar evolves over time,
smoothing out toward equilibrium. The core motivation behind Fourier's work.

Modes:
    diffusion   - Animate temperature distribution smoothing over time
                  (initial condition → gradual equilibrium)
    equation    - Show the heat equation with visual explanation
    comparison  - Side-by-side: initial sharp profile vs. smooth equilibrium

Duration-aware: reads target duration from _manim_params.json.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    BLUE,
    DOWN,
    LEFT,
    ORIGIN,
    RED,
    RIGHT,
    UP,
    YELLOW,
    Axes,
    Create,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
    ReplacementTransform,
    Scene,
    Text,
    VGroup,
    color_gradient,
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
# Math helpers
# ---------------------------------------------------------------------------


def heat_solution(x, t, n_terms=20, k=1.0):
    """Fourier series solution to 1D heat equation.

    Initial condition: step function (hot on left half, cold on right half).
    u(x, 0) = 1 for 0 < x < 0.5, 0 for 0.5 < x < 1
    Boundary: u(0,t) = u(1,t) = 0 (Dirichlet)

    Solution: u(x,t) = sum_{n=1}^{inf} b_n * sin(n*pi*x) * exp(-k*(n*pi)^2*t)
    where b_n = 2 * integral_0^1 f(x)*sin(n*pi*x) dx

    For step function f(x) = 1 on (0, 0.5):
        b_n = (2/(n*pi)) * (1 - cos(n*pi/2))
    """
    result = 0.0
    for n in range(1, n_terms + 1):
        b_n = (2.0 / (n * math.pi)) * (1.0 - math.cos(n * math.pi * 0.5))
        decay = math.exp(-k * (n * math.pi) ** 2 * t)
        result += b_n * math.sin(n * math.pi * x) * decay
    return result


def initial_condition(x):
    """Step function: hot on left half."""
    if 0 < x < 0.5:
        return 1.0
    elif x == 0.5:
        return 0.5
    else:
        return 0.0


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _temp_to_color(temp, min_t=0.0, max_t=1.0):
    """Map temperature value to color (blue=cold, red=hot)."""
    t = max(0.0, min(1.0, (temp - min_t) / (max_t - min_t + 1e-9)))
    # Interpolate: BLUE (cold) → YELLOW (warm) → RED (hot)
    if t < 0.5:
        return color_gradient([BLUE, YELLOW], 101)[int(t * 2 * 100)]
    else:
        return color_gradient([YELLOW, RED], 101)[int((t - 0.5) * 2 * 100)]


# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class HeatDiffusion(Scene):
    """Visualize 1D heat diffusion over time."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "diffusion")
        self._duration = params.get("duration", 25)

        if mode == "equation":
            self.build_equation()
        elif mode == "comparison":
            self.build_comparison()
        else:
            self.build_diffusion()

    # -------------------------------------------------------------------
    # Mode: diffusion (main visual)
    # -------------------------------------------------------------------
    def build_diffusion(self):
        """Animate temperature profile evolving over time."""
        dur = self._duration

        # Decide number of time snapshots based on duration
        if dur >= 35:
            n_snapshots = 7
        elif dur >= 25:
            n_snapshots = 5
        else:
            n_snapshots = 4

        anim_time = n_snapshots * 1.5 + 3.0
        default_wait_total = n_snapshots * 0.8 + 2.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # --- Title ---
        title = Text("熱伝導 ── 温度分布の時間変化", font=FONT, font_size=26, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.4)

        # --- Axes ---
        axes = Axes(
            x_range=[0, 1, 0.25],
            y_range=[-0.1, 1.2, 0.5],
            x_length=9,
            y_length=4.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(UP * 0.1)

        # Axis labels — placed at axis ends to avoid color bar overlap
        x_label = Text("位置", font=FONT, font_size=20, color=TEXT_WHITE, weight="BOLD")
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.2)
        y_label = Text("温度", font=FONT, font_size=20, color=TEXT_WHITE, weight="BOLD")
        y_label.next_to(axes.y_axis.get_top(), UP, buff=0.2)

        self.play(FadeIn(title), FadeIn(axes), FadeIn(x_label), FadeIn(y_label), run_time=1.0)

        # --- Color bar (physical intuition) ---
        n_segments = 40
        bar_group = VGroup()
        bar_width = 9.0  # match axes x_length
        seg_width = bar_width / n_segments

        for i in range(n_segments):
            x_val = (i + 0.5) / n_segments
            temp = initial_condition(x_val)
            color = _temp_to_color(temp)
            rect = Rectangle(
                width=seg_width,
                height=0.35,
                fill_color=color,
                fill_opacity=0.8,
                stroke_width=0,
            )
            rect.move_to(axes.c2p(x_val, -0.05) + DOWN * 0.7)
            # Adjust x position to align with axes
            rect.set_x(axes.c2p(x_val, 0)[0])
            bar_group.add(rect)

        self.play(FadeIn(bar_group), run_time=0.5)

        # --- Initial condition graph ---
        initial_graph = axes.plot(
            lambda x: initial_condition(x),
            x_range=[0.001, 0.999, 0.001],
            color=ACCENT_PINK,
            stroke_width=4.0,
        )

        t_label = MathTex("t = 0", font_size=36, color=ACCENT_GOLD)
        t_label.to_corner(UP + RIGHT, buff=0.5)
        t_label_bg = Rectangle(
            width=t_label.width + 0.4,
            height=t_label.height + 0.25,
            fill_color=BG_COLOR,
            fill_opacity=0.8,
            stroke_color=ACCENT_GOLD,
            stroke_width=1.5,
        )
        t_label_bg.move_to(t_label)
        t_label_group = VGroup(t_label_bg, t_label)

        self.play(Create(initial_graph), FadeIn(t_label_group), run_time=1.5)
        self.wait(1.0 * ws)

        # --- Time evolution snapshots ---
        # Logarithmic time steps for visual interest (fast change early, slow later)
        time_values = [0.001, 0.005, 0.015, 0.04, 0.1, 0.25, 0.5][:n_snapshots]

        current_graph = initial_graph
        current_label = t_label_group
        k_diffusivity = 0.5

        for t_val in time_values:
            new_graph = axes.plot(
                lambda x, tv=t_val: heat_solution(x, tv, n_terms=30, k=k_diffusivity),
                x_range=[0.001, 0.999, 0.005],
                color=ACCENT_CYAN,
                stroke_width=4.0,
            )

            # Format time label
            if t_val < 0.01:
                t_str = f"t = {t_val:.3f}"
            elif t_val < 0.1:
                t_str = f"t = {t_val:.2f}"
            else:
                t_str = f"t = {t_val:.1f}"

            new_label = MathTex(t_str, font_size=36, color=ACCENT_GOLD)
            new_label.to_corner(UP + RIGHT, buff=0.5)
            new_label_bg = Rectangle(
                width=new_label.width + 0.4,
                height=new_label.height + 0.25,
                fill_color=BG_COLOR,
                fill_opacity=0.8,
                stroke_color=ACCENT_GOLD,
                stroke_width=1.5,
            )
            new_label_bg.move_to(new_label)
            new_label_group = VGroup(new_label_bg, new_label)

            # Update color bar
            new_bar = VGroup()
            for i in range(n_segments):
                x_val = (i + 0.5) / n_segments
                temp = heat_solution(x_val, t_val, n_terms=30, k=k_diffusivity)
                color = _temp_to_color(temp)
                rect = Rectangle(
                    width=seg_width,
                    height=0.35,
                    fill_color=color,
                    fill_opacity=0.8,
                    stroke_width=0,
                )
                rect.set_x(axes.c2p(x_val, 0)[0])
                rect.set_y(bar_group[0].get_y())
                new_bar.add(rect)

            self.play(
                ReplacementTransform(current_graph, new_graph),
                ReplacementTransform(current_label, new_label_group),
                ReplacementTransform(bar_group, new_bar),
                run_time=1.5,
            )

            current_graph = new_graph
            current_label = new_label_group
            bar_group = new_bar
            self.wait(0.8 * ws)

        # Final hold (narration explains the convergence to equilibrium)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: equation
    # -------------------------------------------------------------------
    def build_equation(self):
        """Show the heat equation with visual explanation."""
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Heat equation
        eq = MathTex(
            r"\frac{\partial u}{\partial t}",
            r"=",
            r"k",
            r"\frac{\partial^2 u}{\partial x^2}",
            font_size=48,
        )
        eq[0].set_color(ACCENT_PINK)  # du/dt
        eq[2].set_color(ACCENT_GOLD)  # k
        eq[3].set_color(ACCENT_CYAN)  # d²u/dx²

        eq.shift(UP * 1.0)
        self.play(FadeIn(eq), run_time=1.5)
        self.wait(1.5 * ws)

        # Annotations
        ann1 = Text("温度の時間変化", font=FONT, font_size=20, color=ACCENT_PINK)
        ann1.next_to(eq[0], DOWN, buff=0.8)
        arr1 = Line(
            ann1.get_top(),
            eq[0].get_bottom() + DOWN * 0.1,
            color=ACCENT_PINK,
            stroke_width=1.5,
        )

        ann2 = Text("熱拡散率", font=FONT, font_size=20, color=ACCENT_GOLD)
        ann2.next_to(eq[2], DOWN, buff=1.5)
        arr2 = Line(
            ann2.get_top(),
            eq[2].get_bottom() + DOWN * 0.1,
            color=ACCENT_GOLD,
            stroke_width=1.5,
        )

        ann3 = Text("空間的な温度の曲がり", font=FONT, font_size=20, color=ACCENT_CYAN)
        ann3.next_to(eq[3], DOWN, buff=0.8)
        arr3 = Line(
            ann3.get_top(),
            eq[3].get_bottom() + DOWN * 0.1,
            color=ACCENT_CYAN,
            stroke_width=1.5,
        )

        self.play(FadeIn(ann1), FadeIn(arr1), run_time=1.0)
        self.wait(1.0 * ws)
        self.play(FadeIn(ann2), FadeIn(arr2), run_time=1.0)
        self.wait(0.5 * ws)
        self.play(FadeIn(ann3), FadeIn(arr3), run_time=1.0)
        self.wait(1.0 * ws)

        # Summary
        summary = Text(
            "温度が「曲がって」いる場所ほど、速く変化する",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        summary.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(summary))
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: comparison
    # -------------------------------------------------------------------
    def build_comparison(self):
        """Side-by-side: initial sharp profile vs smooth equilibrium."""
        dur = self._duration
        anim_time = 5.0
        default_wait_total = 4.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Left: t=0
        axes_left = Axes(
            x_range=[0, 1, 0.5],
            y_range=[-0.1, 1.2, 0.5],
            x_length=4.5,
            y_length=3.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes_left.shift(LEFT * 3 + DOWN * 0.3)

        # Right: t=large
        axes_right = Axes(
            x_range=[0, 1, 0.5],
            y_range=[-0.1, 1.2, 0.5],
            x_length=4.5,
            y_length=3.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes_right.shift(RIGHT * 3 + DOWN * 0.3)

        label_left = Text("初期状態", font=FONT, font_size=22, color=ACCENT_PINK)
        label_left.next_to(axes_left, UP, buff=0.3)

        label_right = Text("時間経過後", font=FONT, font_size=22, color=ACCENT_CYAN)
        label_right.next_to(axes_right, UP, buff=0.3)

        graph_left = axes_left.plot(
            lambda x: initial_condition(x),
            x_range=[0.001, 0.999, 0.001],
            color=ACCENT_PINK,
            stroke_width=4.0,
        )

        graph_right = axes_right.plot(
            lambda x: heat_solution(x, 0.1, n_terms=30, k=0.5),
            x_range=[0.001, 0.999, 0.005],
            color=ACCENT_CYAN,
            stroke_width=4.0,
        )

        arrow = MathTex(r"\Longrightarrow", font_size=48, color=ACCENT_GOLD)
        arrow.move_to(ORIGIN + DOWN * 0.3)

        title = Text("熱伝導方程式の効果", font=FONT, font_size=26, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.4)

        self.play(FadeIn(title), run_time=0.5)
        self.play(
            FadeIn(axes_left),
            FadeIn(label_left),
            Create(graph_left),
            run_time=1.5,
        )
        self.wait(1.0 * ws)

        self.play(FadeIn(arrow), run_time=0.5)
        self.play(
            FadeIn(axes_right),
            FadeIn(label_right),
            Create(graph_right),
            run_time=1.5,
        )
        self.wait(1.0 * ws)

        # Bottom text
        note = Text(
            "鋭い変化が滑らかになる ── これを解くためにフーリエ級数が生まれた",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note))
        self.wait(2.0 * ws)
