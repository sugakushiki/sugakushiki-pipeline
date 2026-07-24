"""
hilbert_problems_1900.py - Hilbert's 23 problems as an event for 数学史記

Visualizes the 1900 Paris ICM moment: a central "1900" node from which 23
numbered problem-nodes radiate and then ignite, conveying that Hilbert
charted the agenda of 20th-century mathematics. Individual problems are not
detailed; the focus is the act and its sweep.

Modes:
    radiate - Central 1900 node, 23 numbered nodes in a ring, then a golden
              sweep lights them as the century's program.
              Fixed params: 23 nodes, ring radius 1.6, center (0, 0.5).

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 038 (Hilbert), the 1900 Paris event beat.
"""

import numpy as np
from manim import (
    Circle,
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
    BG_COLOR,
    EDGE_COLOR,
    FONT,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

N_PROBLEMS = 23
CENTER = np.array([0.0, 0.5, 0])
RING_R = 1.6


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class HilbertProblems1900(Scene):
    """The 1900 problems as an event. Single mode branch."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        _mode = params.get("mode", "radiate")
        self.build_radiate()

    def build_radiate(self):
        dur = self._duration

        title = Text("1900年 パリ ── 23の問題", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(np.array([0, 3.0, 0]))

        center_circle = Circle(
            radius=0.5,
            color=ACCENT_GOLD,
            stroke_width=3,
            fill_color=ACCENT_GOLD,
            fill_opacity=0.2,
        )
        center_circle.move_to(CENTER)
        center_label = MathTex("1900", font_size=26, color=TEXT_WHITE)
        center_label.move_to(CENTER)

        nodes = VGroup()
        node_nums = VGroup()
        spokes = VGroup()
        for i in range(N_PROBLEMS):
            ang = np.pi / 2 - i * (2 * np.pi / N_PROBLEMS)
            pos = CENTER + RING_R * np.array([np.cos(ang), np.sin(ang), 0])
            node = Circle(
                radius=0.2,
                color=ACCENT_CYAN,
                stroke_width=2,
                fill_color="#22223a",
                fill_opacity=0.85,
            )
            node.move_to(pos)
            nodes.add(node)
            num = MathTex(str(i + 1), font_size=16, color=TEXT_WHITE)
            num.move_to(pos)
            node_nums.add(num)
            spoke = Line(CENTER, pos, color=EDGE_COLOR, stroke_width=1)
            spokes.add(spoke)

        caption = Text("20世紀の数学への、設計図", font=FONT, font_size=22, color=TEXT_WHITE)
        caption.move_to(np.array([0, -1.7, 0]))

        # --- timing: pace the batch reveals across the duration; fixed coda ---
        batch = 6
        n_batches = (N_PROBLEMS + batch - 1) // batch
        coda = 2.5
        fixed = 0.6 + 0.8 + 0.5 + n_batches * 0.7 + 1.5 + 0.6
        pause = max(0.4, (dur - fixed - coda) / n_batches)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(center_circle), FadeIn(center_label), run_time=0.8)
        self.wait(0.5)

        for start in range(0, N_PROBLEMS, batch):
            self.play(
                FadeIn(spokes[start : start + batch]),
                FadeIn(nodes[start : start + batch]),
                FadeIn(node_nums[start : start + batch]),
                run_time=0.7,
            )
            self.wait(pause)

        # golden sweep: the problems ignite the century
        self.play(
            *[n.animate.set_fill(ACCENT_GOLD, opacity=0.35).set_stroke(ACCENT_GOLD) for n in nodes],
            run_time=1.5,
        )
        self.play(FadeIn(caption), run_time=0.6)
        self.wait(coda)


# Factual-claim metadata (read by qa_manim_consistency.py). Only the year
# "1900" is shown on screen (node indices 1-23 are problem numbers, not
# years/people).
LINT_FACTUAL_CLAIMS = {
    "radiate": {"people": [], "years": ["1900"]},
}


SCENES = {
    "radiate": {
        "class": "HilbertProblems1900",
        "params": {"mode": "radiate"},
        "description": "1900 node radiates 23 numbered problems that ignite the century",
    },
}
