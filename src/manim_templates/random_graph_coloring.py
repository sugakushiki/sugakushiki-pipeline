"""
random_graph_coloring.py - Probabilistic method visualization

Duration-aware (P2-8): reads target duration from _manim_params.json
and scales wait times to match audio length.

Phases:
    intro          - Show the question: "does a graph with property X exist?"
    demonstration  - Generate random graphs, check if condition holds
    result         - Show that probability > 0 implies existence

Used by: math_05 (intro), math_06 (demonstration), math_08 (result)
"""

import math as pymath
import random

from manim import *
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    BG_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)


def generate_random_graph(n_nodes, edge_prob, seed=None):
    """Generate random graph positions and edges."""
    if seed is not None:
        random.seed(seed)

    # Circular layout
    positions = []
    for i in range(n_nodes):
        angle = 2 * pymath.pi * i / n_nodes
        x = 2.5 * pymath.cos(angle)
        y = 2.5 * pymath.sin(angle)
        positions.append([x, y, 0])

    edges = []
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if random.random() < edge_prob:
                edges.append((i, j))

    return positions, edges


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate a multiplier for wait() calls to fill the target duration.

    Args:
        duration: target duration in seconds (from audio)
        anim_time: estimated total animation (non-wait) time
        default_wait_total: sum of all default wait() values in the phase

    Returns:
        scale factor (1.0 = use defaults, >1 = stretch, <1 = compress)
    """
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template; "default" is the lint's fallback key when no mode is given.
LINT_FACTUAL_CLAIMS = {"default": {"people": [["エルデシュ", "Erdős"]], "years": []}}


class RandomGraphColoring(Scene):
    """Visualize the probabilistic method in combinatorics."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        phase = params.get("phase", "intro")
        self._duration = params.get("duration", 25)

        if phase == "demonstration":
            self.build_demonstration()
        elif phase == "result":
            self.build_result()
        else:
            self.build_intro()

    def build_intro(self):
        """Pose the question: can we prove existence without construction?"""
        dur = self._duration
        # Animation time: ~5s (5 FadeIn plays at ~1s each)
        # Default waits: 1.0 + 1.0 + 0.5 + 2.0 = 4.5s
        ws = _calc_wait_scale(dur, anim_time=5.0, default_wait_total=4.5)

        q1 = Text("あるグラフは存在するか？", font=FONT, font_size=36, color=TEXT_WHITE)
        q1.shift(UP * 2.8)
        self.play(FadeIn(q1))
        self.wait(1.0 * ws)

        # Show a "?" graph
        positions, edges = generate_random_graph(8, 0.3, seed=10)
        nodes = VGroup(*[Dot(point=p, radius=0.1, color=TEXT_DIM) for p in positions])
        edge_lines = VGroup(
            *[
                Line(positions[i], positions[j], color=TEXT_DIM, stroke_width=1, stroke_opacity=0.4)
                for i, j in edges
            ]
        )
        graph_group = VGroup(edge_lines, nodes)
        graph_group.scale(0.5)
        graph_group.move_to(ORIGIN).shift(UP * 0.5)

        question_mark = Text("?", font_size=60, color=ACCENT_GOLD)
        question_mark.move_to(graph_group.get_center())

        self.play(FadeIn(graph_group))
        self.play(FadeIn(question_mark, scale=1.5))
        self.wait(1.0 * ws)

        # Two approaches
        approach1 = Text("従来: 具体的に構成する", font=FONT, font_size=22, color=TEXT_DIM)
        approach2 = Text("エルデシュ: 確率で示す", font=FONT, font_size=22, color=ACCENT_CYAN)
        approach1.shift(DOWN * 1.2)
        approach2.next_to(approach1, DOWN, buff=0.25)

        self.play(FadeIn(approach1))
        self.wait(0.5 * ws)
        self.play(FadeIn(approach2))
        self.wait(2.0 * ws)

    def build_demonstration(self):
        """Show random graph generation and property checking."""
        dur = self._duration
        # Animation time: ~1s(title) + 5 trials × ~1.2s = ~7s
        # Default waits: 5×0.3 + 1.5 = 3.0s
        ws = _calc_wait_scale(dur, anim_time=7.0, default_wait_total=3.0)

        # Decide number of trials based on duration
        if dur >= 35:
            n_trials = 7
        elif dur >= 25:
            n_trials = 5
        else:
            n_trials = 3

        title = Text("ランダムにグラフを生成", font=FONT, font_size=30, color=ACCENT_CYAN)
        title.to_edge(UP, buff=0.5)
        self.play(FadeIn(title))

        results_text = VGroup()

        for trial in range(n_trials):
            positions, edges = generate_random_graph(7, 0.4, seed=trial * 7 + 1)

            nodes = VGroup(*[Dot(point=p, radius=0.1, color=TEXT_WHITE) for p in positions])
            edge_lines = VGroup(
                *[
                    Line(
                        positions[i],
                        positions[j],
                        color=ACCENT_CYAN,
                        stroke_width=1.5,
                        stroke_opacity=0.5,
                    )
                    for i, j in edges
                ]
            )
            graph_group = VGroup(edge_lines, nodes)
            graph_group.scale(0.6)
            graph_group.move_to(ORIGIN).shift(DOWN * 0.3)

            self.play(FadeIn(graph_group), run_time=0.4)

            # Check for triangles
            has_triangle = False
            triangle_edges_highlight = VGroup()
            adj = set(edges)
            for i, j in edges:
                adj.add((j, i))

            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    for k in range(j + 1, len(positions)):
                        if (
                            ((i, j) in adj or (j, i) in adj)
                            and ((j, k) in adj or (k, j) in adj)
                            and ((i, k) in adj or (k, i) in adj)
                        ):
                            has_triangle = True
                            for a, b in [(i, j), (j, k), (i, k)]:
                                pa = [x * 0.6 for x in positions[a]]
                                pb = [x * 0.6 for x in positions[b]]
                                pa[1] -= 0.3
                                pb[1] -= 0.3
                                hl = Line(
                                    pa,
                                    pb,
                                    color=ACCENT_GOLD,
                                    stroke_width=3,
                                )
                                triangle_edges_highlight.add(hl)
                            break
                    if has_triangle:
                        break
                if has_triangle:
                    break

            if has_triangle:
                self.play(FadeIn(triangle_edges_highlight), run_time=0.3)
                result = Text(f"試行 {trial + 1}: ✓", font_size=20, color=ACCENT_GOLD)
            else:
                result = Text(f"試行 {trial + 1}: ✗", font_size=20, color=TEXT_DIM)

            result.to_edge(RIGHT, buff=1.0)
            result.shift(UP * (1.5 - trial * 0.5))
            results_text.add(result)
            self.play(FadeIn(result), run_time=0.2)

            self.wait(0.3 * ws)
            self.play(FadeOut(graph_group), FadeOut(triangle_edges_highlight), run_time=0.3)

        self.wait(1.5 * ws)

    def build_result(self):
        """Show the key insight: P > 0 ⟹ existence."""
        dur = self._duration
        # Animation time: ~5s (5 FadeIn/Create plays)
        # Default waits: 1.0 + 1.0 + 0.5 + 2.0 = 4.5s
        ws = _calc_wait_scale(dur, anim_time=5.0, default_wait_total=4.5)

        prob_text = MathTex(r"P(\text{condition}) > 0", font_size=48)
        prob_text.set_color(ACCENT_CYAN)
        prob_text.shift(UP * 1.5)

        self.play(FadeIn(prob_text))
        self.wait(1.0 * ws)

        arrow = MathTex(r"\Downarrow", font_size=48, color=TEXT_WHITE)
        arrow.next_to(prob_text, DOWN, buff=0.4)
        self.play(FadeIn(arrow))

        conclusion = Text(
            "そのようなグラフは必ず存在する", font=FONT, font_size=32, color=ACCENT_GOLD
        )
        conclusion.next_to(arrow, DOWN, buff=0.4)
        self.play(FadeIn(conclusion))
        self.wait(1.0 * ws)

        box = SurroundingRectangle(conclusion, color=ACCENT_GOLD, buff=0.2, stroke_width=2)
        self.play(Create(box))
        self.wait(0.5 * ws)

        note = Text(
            "具体的に構成しなくても、存在が証明できる",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.next_to(box, DOWN, buff=0.4)
        self.play(FadeIn(note))
        self.wait(2.0 * ws)
