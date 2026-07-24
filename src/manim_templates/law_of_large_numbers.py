"""
law_of_large_numbers.py - Law of Large Numbers visualization for 数学史記

Visualizes Jakob Bernoulli's "Theorema Aureum" (Golden Theorem):
as the number of trials increases, the observed proportion converges
to the true probability.

Modes:
    coin_flip   - Simulated coin flips with running proportion graph.
                  Fixed params: p=0.5 (fair coin), N up to 1000, seed=42.
    convergence - Multiple sample paths showing convergence to p=0.5,
                  with 5 paths up to N=1000.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 011 (Bernoulli), math pillar 3
"""

import random

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

# Fixed seed for reproducibility across renders
# seed=111 chosen for clean monotone convergence in coin_flip mode:
# N=10:0.700 → 100:0.520 → 500:0.508 → 1000:0.505
SEED = 111


class LawOfLargeNumbers(Scene):
    """Law of Large Numbers. Mode-branching scene.

    Modes:
        coin_flip (default) - single path, p=0.5, N up to 500
        convergence         - 5 sample paths converging, N up to 1000
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "coin_flip")

        if mode == "convergence":
            self.build_convergence()
        else:
            self.build_coin_flip()

    # -------------------------------------------------------------------
    # Mode: coin_flip
    # -------------------------------------------------------------------
    def build_coin_flip(self):
        """Simulated coin flips with running proportion displayed as a graph.

        Fixed parameters: fair coin (p=0.5), up to N=1000 flips.
        Shows the proportion of heads converging to 0.5.
        """
        duration = self._duration
        highlight_color = self._highlight_color

        rng = random.Random(SEED)

        # Title
        title_parts = VGroup(
            Text("Theorema Aureum", font=FONT, font_size=24, color=TEXT_DIM),
        )
        title_parts.to_edge(UP, buff=0.3)
        self.play(FadeIn(title_parts), run_time=0.5)

        # Axes (y bottom must stay above -2.0 for subtitle clearance)
        axes = Axes(
            x_range=[0, 1000, 200],
            y_range=[0.0, 1.0, 0.25],
            x_length=10,
            y_length=3.2,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1},
        )
        axes.shift(DOWN * 0.2)

        x_label = Text("N", font=FONT, font_size=18, color=TEXT_DIM)
        x_label.next_to(axes.x_axis, RIGHT, buff=0.15)
        self.play(FadeIn(axes), FadeIn(x_label), run_time=0.5)

        # p=0.5 reference line
        p_left = axes.c2p(0, 0.5)
        p_right = axes.c2p(1000, 0.5)
        p_line = DashedLine(p_left, p_right, color=ACCENT_PINK, dash_length=0.08)
        p_label = MathTex(r"p = \tfrac{1}{2}", font_size=30, color=ACCENT_PINK)
        p_label.next_to(p_line, LEFT, buff=0.15)
        self.play(FadeIn(p_line), FadeIn(p_label), run_time=0.4)

        # Simulate and animate
        # Sample at these N values for smooth animation
        sample_points = (
            list(range(1, 11))
            + list(range(15, 51, 5))
            + list(range(60, 101, 10))
            + list(range(125, 501, 25))
            + list(range(550, 1001, 50))
        )

        heads = 0
        flips = 0
        prev_pos = None
        lines = VGroup()

        total_points = len(sample_points)
        anim_per = max(0.1, (duration - 4.0) / total_points)

        for target_n in sample_points:
            while flips < target_n:
                flips += 1
                if rng.random() < 0.5:
                    heads += 1

            proportion = heads / flips
            pos = axes.c2p(flips, proportion)

            dot = Dot(pos, radius=0.04, color=ACCENT_CYAN)

            if prev_pos is not None:
                seg = Line(
                    prev_pos,
                    pos,
                    color=ACCENT_CYAN,
                    stroke_width=1.5,
                    stroke_opacity=0.6,
                )
                self.add(seg)
                lines.add(seg)

            self.add(dot)
            prev_pos = pos

            if anim_per >= 0.15:
                self.wait(anim_per)
            else:
                self.wait(0.05)

        # Final proportion label (keep above y=-2.0)
        final_p = heads / flips
        final_label = Text(
            f"N=1000: {final_p:.3f}",
            font=FONT,
            font_size=22,
            color=highlight_color,
        )
        final_label.next_to(axes.x_axis, RIGHT, buff=0.3).shift(UP * 0.3)
        self.play(FadeIn(final_label), run_time=0.5)
        self.wait(1.5)

    # -------------------------------------------------------------------
    # Mode: convergence
    # -------------------------------------------------------------------
    def build_convergence(self):
        """Multiple sample paths converging to p=0.5 with narrowing band."""
        duration = self._duration
        highlight_color = self._highlight_color

        # Title
        formula = MathTex(
            r"P\!\left(\left|\frac{S_n}{n} - p\right| < \varepsilon\right)",
            r"\to 1",
            font_size=28,
        )
        formula[0].set_color(ACCENT_CYAN)
        formula[1].set_color(highlight_color)
        formula.to_edge(UP, buff=0.3)
        self.play(FadeIn(formula), run_time=0.6)

        # Axes (y bottom must stay above -2.0 for subtitle clearance)
        axes = Axes(
            x_range=[0, 1000, 200],
            y_range=[0.0, 1.0, 0.25],
            x_length=10,
            y_length=3.2,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1},
        )
        axes.shift(DOWN * 0.2)

        x_label = Text("N", font=FONT, font_size=18, color=TEXT_DIM)
        x_label.next_to(axes.x_axis, RIGHT, buff=0.15)
        self.play(FadeIn(axes), FadeIn(x_label), run_time=0.4)

        # p=0.5 reference
        p_left = axes.c2p(0, 0.5)
        p_right = axes.c2p(1000, 0.5)
        p_line = DashedLine(p_left, p_right, color=ACCENT_PINK, dash_length=0.08)
        self.play(FadeIn(p_line), run_time=0.3)

        # Draw multiple paths
        path_colors = [ACCENT_CYAN, ACCENT_GOLD, "#7bed9f", "#70a1ff", ACCENT_PINK]
        n_paths = 5
        sample_ns = list(range(1, 20)) + list(range(20, 101, 5)) + list(range(120, 1001, 20))

        wait_total = max(1.0, duration - 5.0)

        for path_idx in range(n_paths):
            rng = random.Random(SEED + path_idx * 7)
            color = path_colors[path_idx % len(path_colors)]

            heads = 0
            flips = 0
            prev_pos = None

            for target_n in sample_ns:
                while flips < target_n:
                    flips += 1
                    if rng.random() < 0.5:
                        heads += 1

                proportion = heads / flips
                pos = axes.c2p(flips, proportion)

                if prev_pos is not None:
                    seg = Line(
                        prev_pos,
                        pos,
                        color=color,
                        stroke_width=1.2,
                        stroke_opacity=0.5,
                    )
                    self.add(seg)

                prev_pos = pos

            self.wait(wait_total / n_paths)

        # Convergence label
        conv_label = MathTex(r"\to p", font_size=28, color=highlight_color)
        conv_label.move_to(axes.c2p(900, 0.58))
        self.play(FadeIn(conv_label), run_time=0.5)
        self.wait(1.5)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "coin_flip": {"people": [], "years": []},
    "convergence": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# ---------------------------------------------------------------------------
SCENES = {
    "coin_flip": LawOfLargeNumbers,
    "convergence": LawOfLargeNumbers,
}
