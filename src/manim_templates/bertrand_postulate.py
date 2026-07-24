"""Bertrand's Postulate visualization for 数学史記.

Shows that for any n >= 1, there exists a prime p with n < p <= 2n.

Duration-aware (P2-8): reads target duration from _manim_params.json
and adapts the number of examples and wait times to fill the audio.

Reads params from _manim_params.json in the same directory.
"""

import json
from pathlib import Path

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Dot,
    FadeIn,
    FadeOut,
    MathTex,
    NumberLine,
    Rectangle,
    Scene,
    Text,
    VGroup,
    Write,
    config,
)

# === Style constants (from STYLE_GUIDE.md) ===
BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
FONT = "BIZ UDMincho"

config.background_color = BG_COLOR


def load_params() -> dict:
    """Load parameters from _manim_params.json."""
    params_path = Path(__file__).parent / "_manim_params.json"
    if params_path.exists():
        with open(params_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}


class BertrandPostulate(Scene):
    """Visualize Bertrand's postulate: for n>=1, exists prime in (n, 2n]."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 25)  # target seconds from audio

        # ── Choose examples based on available duration ──
        # Intro animation: ~4s.  Each example animation: ~3s avg.
        all_examples = [2, 5, 10, 25]
        if duration >= 40:
            examples = all_examples  # 4 examples
        elif duration >= 28:
            examples = all_examples[:3]  # 3 examples
        else:
            examples = all_examples[:2]  # 2 examples
        examples = params.get("examples", examples)

        # ── Calculate wait scale ──
        # Non-wait animation time estimate:
        #   intro plays: ~4s, per example plays: ~2.8s avg, cleanup: ~0.5s
        n_examples = len(examples)
        anim_time = 4.0 + n_examples * 2.8 + 0.5
        wait_budget = max(duration - anim_time, n_examples + 2.0)

        # Distribute across wait points:
        #   intro: 2 points, per example: 1 point, final: 1 point
        n_wait_points = 2 + n_examples + 1
        base_wait = max(0.3, min(wait_budget / n_wait_points, 4.0))

        # ── Intro ──
        title = Text(
            "ベルトランの仮説",
            font=FONT,
            font_size=36,
            color=GOLD,
        ).to_edge(UP, buff=0.5)
        self.play(FadeIn(title))

        formula = MathTex(
            r"\forall \, n \geq 1, \quad \exists \, p \text{ prime}: \quad n < p \leq 2n",
            font_size=32,
            color=CYAN,
        ).next_to(title, DOWN, buff=0.4)
        self.play(Write(formula))
        self.wait(base_wait * 0.6)

        explanation = Text(
            "任意の自然数 n に対し、n と 2n の間に素数が存在する",
            font=FONT,
            font_size=22,
            color="#aaaaaa",
        ).next_to(formula, DOWN, buff=0.3)
        self.play(FadeIn(explanation))
        self.wait(base_wait * 1.2)

        self.play(FadeOut(explanation))

        # ── Examples ──
        for i, n in enumerate(examples):
            self._show_example(n, formula, hold_time=base_wait, is_last=(i == len(examples) - 1))

        # Final hold
        self.wait(base_wait * 0.8)

    def _show_example(self, n: int, formula, hold_time: float = 1.5, is_last: bool = False):
        """Show one example of Bertrand's postulate for a given n."""
        two_n = 2 * n

        # Choose number line range with padding
        x_min = max(0, n - 2)
        x_max = two_n + 2

        # Determine tick step to avoid overlap
        total_range = x_max - x_min
        if total_range <= 15:
            tick_step = 1
        elif total_range <= 30:
            tick_step = 2
        else:
            tick_step = 5

        # Scale to fit screen width
        unit_size = min(0.6, 10.0 / total_range)

        number_line = NumberLine(
            x_range=[x_min, x_max, tick_step],
            length=total_range * unit_size,
            include_numbers=True,
            font_size=20,
            color="#666666",
            decimal_number_config={"num_decimal_places": 0},
        ).shift(DOWN * 0.3)

        n_label = Text(f"n = {n}", font=FONT, font_size=28, color=GOLD)
        n_label.next_to(number_line, UP, buff=1.2).align_to(number_line, LEFT).shift(RIGHT * 0.5)

        n_pos = number_line.n2p(n)
        two_n_pos = number_line.n2p(two_n)
        range_width = two_n_pos[0] - n_pos[0]

        range_rect = (
            Rectangle(
                width=range_width,
                height=0.5,
                fill_color=CYAN,
                fill_opacity=0.15,
                stroke_color=CYAN,
                stroke_opacity=0.5,
                stroke_width=1,
            )
            .move_to((n_pos + two_n_pos) / 2)
            .align_to(number_line, DOWN)
            .shift(UP * 0.05)
        )

        n_marker = Dot(n_pos, color=GOLD, radius=0.10)
        two_n_marker = Dot(two_n_pos, color=GOLD, radius=0.10)
        n_var = MathTex("n", font_size=22, color=GOLD).next_to(n_marker, UP, buff=0.35)
        two_n_var = MathTex("2n", font_size=22, color=GOLD).next_to(two_n_marker, UP, buff=0.35)

        primes_in_range = [p for p in range(n + 1, two_n + 1) if is_prime(p)]

        prime_dots = VGroup()
        for p in primes_in_range:
            p_pos = number_line.n2p(p)
            dot = Dot(p_pos, color=PINK, radius=0.12)
            prime_dots.add(dot)

        # ── Animate ──
        self.play(FadeIn(number_line), FadeIn(n_label), run_time=0.5)
        self.play(
            FadeIn(range_rect),
            FadeIn(n_marker),
            FadeIn(two_n_marker),
            FadeIn(n_var),
            FadeIn(two_n_var),
            run_time=0.5,
        )

        if len(primes_in_range) <= 4:
            for dot in prime_dots:
                self.play(FadeIn(dot, scale=1.5), run_time=0.3)
        else:
            self.play(FadeIn(prime_dots, scale=1.5), run_time=0.5)

        count_text = Text(
            f"{len(primes_in_range)} 個の素数",
            font=FONT,
            font_size=22,
            color=PINK,
        ).next_to(number_line, DOWN, buff=0.6)
        self.play(FadeIn(count_text), run_time=0.3)

        # Hold for viewing (duration-aware)
        self.wait(hold_time)

        all_elements = VGroup(
            number_line,
            n_label,
            range_rect,
            n_marker,
            two_n_marker,
            n_var,
            two_n_var,
            prime_dots,
            count_text,
        )
        self.play(FadeOut(all_elements), run_time=0.4)
        self.wait(0.5)
