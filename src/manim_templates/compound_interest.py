"""
compound_interest.py - Compound interest and the discovery of e for 数学史記

Visualizes Jakob Bernoulli's 1683 investigation of compound interest:
how (1+1/n)^n converges to e as n increases.

Modes:
    bar_chart - Bar chart comparing compound interest with n=1,2,4,12,365.
                Fixed params: principal=1, rate=100%, period=1 year.
                Shows (1+1/n)^n values next to e≈2.718 reference line.
    limit     - Animated graph of (1+1/n)^n as n increases,
                converging to e≈2.718. Sample points:
                n=1,2,3,4,5,6,8,10,15,20,30,50,75,100.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 011 (Bernoulli), math pillar 1
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    DashedLine,
    Dot,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class CompoundInterest(Scene):
    """Compound interest / discovery of e. Mode-branching scene.

    Modes:
        bar_chart (default) - (1+1/n)^n for n in {1,2,4,12,365}
        limit               - (1+1/n)^n converging to e as a line graph
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "bar_chart")

        if mode == "limit":
            self.build_limit()
        else:
            self.build_bar_chart()

    # -------------------------------------------------------------------
    # Mode: bar_chart
    # -------------------------------------------------------------------
    def build_bar_chart(self):
        """Bar chart: (1+1/n)^n for n = 1, 2, 4, 12, 365."""
        duration = self._duration
        highlight_color = self._highlight_color

        # Title
        title = Text("(1+1/n)^n", font=FONT, font_size=24, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)

        # Data
        ns = [1, 2, 4, 12, 365]
        labels_text = ["1", "2", "4", "12", "365"]
        values = [(1 + 1 / n) ** n for n in ns]

        # Bar dimensions (bar_base_y ensures labels stay above y=-2.0)
        bar_width = 0.8
        max_height = 2.5
        bar_base_y = -1.5
        x_start = -3.0
        x_gap = 1.5

        # e reference line
        e_y = bar_base_y + (math.e / max(values)) * max_height
        e_line = DashedLine(
            start=[x_start - 0.5, e_y, 0],
            end=[x_start + x_gap * (len(ns) - 1) + 1.0, e_y, 0],
            color=ACCENT_PINK,
            dash_length=0.1,
        )
        e_label = MathTex("e \\approx 2.718", font_size=22, color=ACCENT_PINK)
        e_label.next_to(e_line, RIGHT, buff=0.2)

        self.play(FadeIn(title), run_time=0.5)

        # Animate bars
        anim_time = max(0.5, (duration - 4.0) / len(ns))
        bars = VGroup()
        for i, (_n, label_t, val) in enumerate(zip(ns, labels_text, values, strict=False)):
            h = (val / max(values)) * max_height
            x = x_start + i * x_gap

            bar = Rectangle(
                width=bar_width,
                height=h,
                fill_color=ACCENT_CYAN if i < len(ns) - 1 else highlight_color,
                fill_opacity=0.8,
                stroke_color=TEXT_WHITE,
                stroke_width=1,
            )
            bar.move_to([x, bar_base_y + h / 2, 0])

            n_label = MathTex(f"n={label_t}", font_size=20, color=TEXT_WHITE)
            n_label.next_to(bar, DOWN, buff=0.15)

            val_label = Text(f"{val:.3f}", font=FONT, font_size=18, color=TEXT_WHITE)
            val_label.next_to(bar, UP, buff=0.1)

            group = VGroup(bar, n_label, val_label)
            bars.add(group)
            self.play(FadeIn(group), run_time=0.6)
            self.wait(anim_time - 0.6)

        # Show e reference
        self.play(FadeIn(e_line), FadeIn(e_label), run_time=0.8)
        self.wait(1.5)

    # -------------------------------------------------------------------
    # Mode: limit
    # -------------------------------------------------------------------
    def build_limit(self):
        """Animated graph of (1+1/n)^n converging to e as n increases."""
        duration = self._duration
        highlight_color = self._highlight_color

        # Title
        formula = MathTex(
            r"\lim_{n \to \infty}",
            r"\left(1 + \frac{1}{n}\right)^n",
            r"= e",
            font_size=32,
        )
        formula[0].set_color(TEXT_DIM)
        formula[1].set_color(ACCENT_CYAN)
        formula[2].set_color(highlight_color)
        formula.to_edge(UP, buff=0.3)

        self.play(FadeIn(formula), run_time=0.8)

        # Axes
        axes = Axes(
            x_range=[0, 120, 20],
            y_range=[1.5, 3.0, 0.5],
            x_length=10,
            y_length=4,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1},
        )
        axes.shift(DOWN * 0.3)

        x_label = Text("n", font=FONT, font_size=20, color=TEXT_DIM)
        x_label.next_to(axes.x_axis, RIGHT, buff=0.15)
        y_label = MathTex(r"(1+\tfrac{1}{n})^n", font_size=20, color=TEXT_DIM)
        y_label.next_to(axes.y_axis, UP, buff=0.15)

        self.play(FadeIn(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.6)

        # e reference line
        e_point = axes.c2p(0, math.e)
        e_end = axes.c2p(120, math.e)
        e_line = DashedLine(e_point, e_end, color=ACCENT_PINK, dash_length=0.08)
        e_text = MathTex("e", font_size=22, color=ACCENT_PINK)
        e_text.next_to(e_line, LEFT, buff=0.15)
        self.play(FadeIn(e_line), FadeIn(e_text), run_time=0.5)

        # Plot points progressively
        sample_ns = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50, 75, 100]
        dots = VGroup()
        prev_dot = None

        anim_per = max(0.3, (duration - 5.0) / len(sample_ns))
        for n in sample_ns:
            val = (1 + 1 / n) ** n
            pos = axes.c2p(n, val)
            dot = Dot(pos, radius=0.06, color=ACCENT_CYAN)

            if prev_dot is not None:
                line_seg = Line(
                    prev_dot.get_center(),
                    dot.get_center(),
                    color=ACCENT_CYAN,
                    stroke_width=1.5,
                    stroke_opacity=0.5,
                )
                self.play(FadeIn(line_seg), FadeIn(dot), run_time=0.3)
            else:
                self.play(FadeIn(dot), run_time=0.3)

            dots.add(dot)
            prev_dot = dot
            self.wait(anim_per - 0.3)

        # Final value label
        final_label = MathTex(r"\approx 2.718...", font_size=24, color=highlight_color)
        final_label.next_to(dots[-1], UP, buff=0.2)
        self.play(FadeIn(final_label), run_time=0.6)
        self.wait(1.0)


# ---------------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# ---------------------------------------------------------------------------
# no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "bar_chart": {"people": [], "years": []},
    "limit": {"people": [], "years": []},
}


SCENES = {
    "bar_chart": CompoundInterest,
    "limit": CompoundInterest,
}
