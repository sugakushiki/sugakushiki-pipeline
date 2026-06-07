"""
probabilistic_method.py - Probabilistic method concept visualization

Shows the core idea of the probabilistic method:
  1. Generate random objects (dots in a grid)
  2. Randomly assign properties — some satisfy the condition
  3. Observe probability > 0
  4. Conclude: such an object must exist

Duration-aware: reads target duration from _manim_params.json.

Used by: math_03
"""

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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate a multiplier for wait() calls to fill the target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))
# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}




class ProbabilisticMethod(Scene):
    """Visualize the core concept of the probabilistic method."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 27)
        self.build()

    def build(self):
        dur = self._duration
        # Animation time estimate: ~9s total play() calls
        # Default waits: 1.0 + 0.5 + 1.5 + 1.0 + 1.0 + 1.0 + 3.0 = 9.0s
        ws = _calc_wait_scale(dur, anim_time=9.0, default_wait_total=9.0)

        # --- Phase 1: Title ---
        title = Text("確率的手法", font=FONT, font_size=36, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.6)
        self.play(FadeIn(title))
        self.wait(1.0 * ws)

        # --- Phase 2: Generate random objects (dot grid) ---
        random.seed(42)
        n_rows, n_cols = 4, 8
        dots = VGroup()
        dot_list = []
        for r in range(n_rows):
            for c in range(n_cols):
                x = (c - (n_cols - 1) / 2) * 0.7
                y = (r - (n_rows - 1) / 2) * 0.7 + 0.3
                dot = Dot(point=[x, y, 0], radius=0.15, color=TEXT_DIM)
                dots.add(dot)
                dot_list.append(dot)

        self.play(FadeIn(dots), run_time=1.0)
        self.wait(0.5 * ws)

        # --- Phase 3: Randomly assign — some satisfy, some don't ---
        satisfy_count = 0
        anims = []
        for dot in dot_list:
            if random.random() < 0.6:
                anims.append(dot.animate.set_color(ACCENT_CYAN))
                satisfy_count += 1
            else:
                anims.append(dot.animate.set_color(ACCENT_PINK).set_opacity(0.35))

        self.play(*anims, run_time=1.5)
        self.wait(1.5 * ws)

        # Show probability count
        total = len(dot_list)
        pct = satisfy_count / total * 100
        prob_label = Text(
            f"条件を満たす割合: {pct:.0f}%",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        prob_label.shift(DOWN * 1.5)
        self.play(FadeIn(prob_label))
        self.wait(1.0 * ws)

        # --- Phase 4: Transition to formula ---
        self.play(
            FadeOut(dots),
            FadeOut(prob_label),
            run_time=1.0,
        )

        # Key formula: P > 0
        formula = MathTex(r"P > 0", font_size=56, color=ACCENT_CYAN)
        formula.shift(UP * 0.8)
        self.play(FadeIn(formula, scale=1.2))
        self.wait(1.0 * ws)

        # Arrow
        arrow = MathTex(r"\Downarrow", font_size=48, color=TEXT_WHITE)
        arrow.next_to(formula, DOWN, buff=0.4)
        self.play(FadeIn(arrow))

        # Conclusion
        conclusion = Text(
            "そのような対象は必ず存在する",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        conclusion.next_to(arrow, DOWN, buff=0.4)
        self.play(FadeIn(conclusion))
        self.wait(1.0 * ws)

        # Box highlight
        box = SurroundingRectangle(
            conclusion,
            color=ACCENT_GOLD,
            buff=0.2,
            stroke_width=2,
        )
        self.play(Create(box))
        self.wait(3.0 * ws)
