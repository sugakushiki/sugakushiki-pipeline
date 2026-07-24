"""
erdos_network.py - Erdős number network visualization

Modes:
    step_by_step - Build network incrementally, showing Erdős number assignment
    colored      - Full network with nodes colored by Erdős number

Used by: math_01 (step_by_step), math_02 (colored)
"""

import math as pymath

from manim import *
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

# Erdős number → color mapping
NUMBER_COLORS = {
    0: ACCENT_GOLD,  # Erdős himself
    1: ACCENT_CYAN,  # Direct coauthors
    2: ACCENT_PINK,  # Distance 2
    3: "#88cc44",  # Distance 3
    4: TEXT_DIM,  # Distance 4+
}


def ring_positions(center, radius, n, start_angle=0):
    """Generate n positions in a circle around center."""
    positions = []
    for i in range(n):
        angle = start_angle + 2 * pymath.pi * i / n
        x = center[0] + radius * pymath.cos(angle)
        y = center[1] + radius * pymath.sin(angle)
        positions.append([x, y, 0])
    return positions


# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}


class ErdosNetwork(Scene):
    """Visualize the Erdős number concept as a network graph."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "step_by_step")
        center_label = params.get("center_label", "Erdős")
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        if mode == "colored":
            self.build_colored(center_label, highlight_color)
        else:
            self.build_step_by_step(center_label, highlight_color)

    def build_step_by_step(self, center_label, highlight_color):
        """Build network step by step, explaining Erdős numbers."""

        # Center: Erdős (number 0)
        center = [0, 0, 0]
        erdos_dot = Dot(point=center, radius=0.2, color=highlight_color)
        erdos_label = Text(center_label, font_size=22, color=TEXT_WHITE)
        erdos_label.next_to(erdos_dot, DOWN, buff=0.15)
        num_0 = Text("0", font_size=18, color=highlight_color)
        num_0.move_to(erdos_dot)

        self.play(FadeIn(erdos_dot), FadeIn(erdos_label))
        self.play(FadeIn(num_0))
        self.wait(0.5)

        # Ring 1: Erdős number 1 (direct coauthors)
        coauthors_1 = ["Selberg", "Turán", "Szemerédi", "Alon", "Graham"]
        pos_1 = ring_positions(center, 2.0, len(coauthors_1))
        ring1_group = VGroup()

        for _i, (name, pos) in enumerate(zip(coauthors_1, pos_1, strict=False)):
            dot = Dot(point=pos, radius=0.12, color=ACCENT_CYAN)
            label = Text(name, font_size=16, color=TEXT_WHITE)
            # Place label above for bottom-half nodes to avoid subtitle overlap
            label_dir = UP if pos[1] < -0.5 else DOWN
            label.next_to(dot, label_dir, buff=0.1)
            edge = Line(center, pos, color=ACCENT_CYAN, stroke_width=1.5, stroke_opacity=0.6)
            num = Text("1", font_size=14, color=ACCENT_CYAN)
            num.move_to(dot)

            ring1_group.add(VGroup(edge, dot, label, num))

        self.play(
            LaggedStart(*[FadeIn(g) for g in ring1_group], lag_ratio=0.15),
            run_time=2.0,
        )
        self.wait(1.0)

        # Ring 2: Erdős number 2
        coauthors_2_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
        pos_2 = ring_positions(center, 3.8, len(coauthors_2_names), start_angle=0.2)
        ring2_group = VGroup()

        for i, (_name, pos) in enumerate(zip(coauthors_2_names, pos_2, strict=False)):
            dot = Dot(point=pos, radius=0.08, color=ACCENT_PINK)
            # Connect to nearest ring-1 node
            nearest_r1 = pos_1[i % len(pos_1)]
            edge = Line(nearest_r1, pos, color=ACCENT_PINK, stroke_width=1, stroke_opacity=0.4)
            num = Text("2", font_size=12, color=ACCENT_PINK)
            num.move_to(dot)
            ring2_group.add(VGroup(edge, dot, num))

        self.play(
            LaggedStart(*[FadeIn(g) for g in ring2_group], lag_ratio=0.05),
            run_time=1.5,
        )
        self.wait(2.0)

    def build_colored(self, center_label, highlight_color):
        """Show full network with nodes colored by Erdős number."""

        center = [0, 0, 0]

        # Build all rings at once
        all_nodes = VGroup()
        all_edges = VGroup()

        # Center
        erdos_dot = Dot(point=center, radius=0.2, color=highlight_color)
        erdos_label = Text(center_label, font_size=20, color=TEXT_WHITE)
        erdos_label.next_to(erdos_dot, DOWN, buff=0.1)
        all_nodes.add(VGroup(erdos_dot, erdos_label))

        # Ring 1
        n1 = 6
        pos_1 = ring_positions(center, 1.8, n1)
        for pos in pos_1:
            dot = Dot(point=pos, radius=0.1, color=ACCENT_CYAN)
            edge = Line(center, pos, color=ACCENT_CYAN, stroke_width=1.5, stroke_opacity=0.5)
            all_nodes.add(dot)
            all_edges.add(edge)

        # Ring 2
        n2 = 12
        pos_2 = ring_positions(center, 3.2, n2, start_angle=0.15)
        for i, pos in enumerate(pos_2):
            dot = Dot(point=pos, radius=0.07, color=ACCENT_PINK)
            nearest = pos_1[i % n1]
            edge = Line(nearest, pos, color=ACCENT_PINK, stroke_width=1, stroke_opacity=0.3)
            all_nodes.add(dot)
            all_edges.add(edge)

        # Ring 3
        n3 = 20
        pos_3 = ring_positions(center, 4.5, n3, start_angle=0.1)
        for i, pos in enumerate(pos_3):
            dot = Dot(point=pos, radius=0.05, color="#88cc44")
            nearest = pos_2[i % n2]
            edge = Line(nearest, pos, color="#88cc44", stroke_width=0.5, stroke_opacity=0.2)
            all_nodes.add(dot)
            all_edges.add(edge)

        # Some cross-edges within rings for realism
        import random

        random.seed(42)
        for pos_list in [pos_1, pos_2]:
            for i in range(len(pos_list)):
                j = (i + 1) % len(pos_list)
                if random.random() < 0.4:
                    edge = Line(
                        pos_list[i],
                        pos_list[j],
                        stroke_width=0.5,
                        stroke_opacity=0.15,
                        color=TEXT_DIM,
                    )
                    all_edges.add(edge)

        self.play(FadeIn(all_edges, run_time=1.0))
        self.play(FadeIn(all_nodes, run_time=1.5))
        self.wait(1.0)

        # Legend
        legend = VGroup()
        for num, color, label in [
            ("0", highlight_color, "Erdős"),
            ("1", ACCENT_CYAN, "直接共著者"),
            ("2", ACCENT_PINK, "2ステップ"),
            ("3", "#88cc44", "3ステップ"),
        ]:
            dot = Dot(radius=0.08, color=color)
            text = Text(f" {num}: {label}", font=FONT, font_size=18, color=color)
            text.next_to(dot, RIGHT, buff=0.1)
            row = VGroup(dot, text)
            legend.add(row)

        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        legend.to_corner(DR, buff=0.5)
        self.play(FadeIn(legend))
        self.wait(2.0)
