"""
erdos_wander.py - Abstract visualization of Erdős's wandering lifestyle

Dots appear representing cities/colleagues, with a traveling dot
moving between them. Conveys the feeling of constant movement.

Used by: person_08
"""

import random

from manim import *
from style import ACCENT_CYAN, ACCENT_GOLD, BG_COLOR, TEXT_DIM, load_params
# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}




class ErdosWander(Scene):
    """Abstract representation of Erdős traveling between mathematicians."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        style = params.get("style", "abstract_dots")

        random.seed(42)  # reproducible layout

        # Create scattered dots representing mathematicians/cities
        n_nodes = 18
        nodes = VGroup()
        positions = []
        for _ in range(n_nodes):
            x = random.uniform(-5.5, 5.5)
            y = random.uniform(-2.5, 2.5)
            positions.append([x, y, 0])
            dot = Dot(point=[x, y, 0], radius=0.08, color=TEXT_DIM)
            nodes.add(dot)

        # Fade in nodes gradually
        self.play(
            LaggedStart(*[FadeIn(n, scale=0.5) for n in nodes], lag_ratio=0.05),
            run_time=1.5,
        )

        # Traveling dot (Erdős)
        erdos_dot = Dot(point=positions[0], radius=0.15, color=ACCENT_GOLD)
        erdos_glow = Dot(point=positions[0], radius=0.25, color=ACCENT_GOLD, fill_opacity=0.3)
        traveler = VGroup(erdos_glow, erdos_dot)
        self.play(FadeIn(traveler))

        # Visit sequence: random walk through nodes
        visit_order = list(range(n_nodes))
        random.shuffle(visit_order)

        edges = VGroup()
        for i, target_idx in enumerate(visit_order[:12]):
            target = positions[target_idx]

            # Draw faint trail
            current_pos = erdos_dot.get_center()
            trail = Line(
                start=current_pos,
                end=target,
                color=ACCENT_CYAN,
                stroke_width=1,
                stroke_opacity=0.4,
            )
            edges.add(trail)

            # Move traveler
            self.play(
                traveler.animate.move_to(target),
                Create(trail),
                run_time=0.4,
            )

            # Briefly brighten visited node
            nodes[target_idx].set_color(ACCENT_CYAN)
            self.wait(0.15)

        self.wait(1.5)

        # Final: show all connections as a network
        self.play(
            edges.animate.set_stroke(opacity=0.6),
            run_time=0.8,
        )
        self.wait(1.5)
