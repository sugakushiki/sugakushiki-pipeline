"""
erdos_network_grow.py - Network growth / ripple animation

Shows how Erdős's collaboration network expands outward in waves,
demonstrating the "6 degrees of separation" concept visually.

Used by: math_04 (ripple mode)
"""

import math as pymath
import random

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
# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template; "default" is the lint's fallback key when no mode is given.
LINT_FACTUAL_CLAIMS = {"default": {"people": [["Erdős", "エルデシュ"]], "years": []}}




class ErdosNetworkGrow(Scene):
    """Animate network growing outward from Erdős in concentric waves."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        random.seed(42)
        center = ORIGIN

        # Pre-generate all node positions
        rings = [
            {"n": 1, "r": 0.0, "color": highlight_color, "size": 0.2},  # Erdős
            {"n": 6, "r": 1.5, "color": ACCENT_CYAN, "size": 0.10},
            {"n": 14, "r": 2.8, "color": ACCENT_PINK, "size": 0.07},
            {"n": 24, "r": 4.0, "color": "#88cc44", "size": 0.05},
            {"n": 36, "r": 5.2, "color": TEXT_DIM, "size": 0.04},
        ]

        all_ring_positions = []
        all_ring_nodes = []
        all_ring_edges = []

        prev_positions = [center.tolist() if hasattr(center, "tolist") else [0, 0, 0]]

        for ring_idx, ring in enumerate(rings):
            n = ring["n"]
            r = ring["r"]
            color = ring["color"]
            size = ring["size"]

            if ring_idx == 0:
                # Center node
                positions = [[0, 0, 0]]
                dot = Dot(point=ORIGIN, radius=size, color=color)
                label = Text("Erdős", font_size=18, color=TEXT_WHITE)
                label.next_to(dot, DOWN, buff=0.1)
                nodes = VGroup(VGroup(dot, label))
                edges = VGroup()
            else:
                # Jitter the ring positions slightly for organic feel
                positions = []
                nodes = VGroup()
                edges = VGroup()
                for i in range(n):
                    angle = 2 * pymath.pi * i / n + random.uniform(-0.15, 0.15)
                    jitter_r = r + random.uniform(-0.2, 0.2)
                    x = jitter_r * pymath.cos(angle)
                    y = jitter_r * pymath.sin(angle)
                    pos = [x, y, 0]
                    positions.append(pos)

                    dot = Dot(point=pos, radius=size, color=color)
                    nodes.add(dot)

                    # Connect to nearest node in previous ring
                    nearest_prev = min(
                        prev_positions,
                        key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2,
                    )
                    edge = Line(
                        nearest_prev,
                        pos,
                        color=color,
                        stroke_width=max(0.5, 2 - ring_idx * 0.4),
                        stroke_opacity=max(0.15, 0.6 - ring_idx * 0.1),
                    )
                    edges.add(edge)

            all_ring_positions.append(positions)
            all_ring_nodes.append(nodes)
            all_ring_edges.append(edges)
            prev_positions = positions

        # Animate ring by ring (ripple effect)
        # Ring 0: Erdős
        self.play(FadeIn(all_ring_nodes[0]), run_time=0.5)
        self.wait(0.5)

        # Ripple circle effect + nodes
        for ring_idx in range(1, len(rings)):
            ring = rings[ring_idx]

            # Expanding circle
            ripple = Circle(
                radius=ring["r"], color=ring["color"], stroke_width=1.5, stroke_opacity=0.5
            )
            self.play(
                Create(ripple),
                FadeIn(all_ring_edges[ring_idx]),
                FadeIn(all_ring_nodes[ring_idx]),
                run_time=0.8,
            )
            self.play(ripple.animate.set_stroke(opacity=0.1), run_time=0.3)
            self.wait(0.3)

        self.wait(1.0)

        # Number counter
        counter = Text("268,000+ 研究者", font=FONT, font_size=28, color=ACCENT_GOLD)
        counter.to_edge(DOWN, buff=0.5)
        self.play(FadeIn(counter))
        self.wait(2.0)
