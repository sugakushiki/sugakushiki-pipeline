"""
basel_problem.py - Euler's 1735 solution to the Basel problem for 数学史記

Visualizes Euler's derivation of Σ 1/n² = π²/6, posed by Pietro Mengoli
(1650), made public by Jakob Bernoulli (1689), and solved by Euler
at age 28 in late 1734 / early 1735.

Modes:
    partial_sums - Numerical partial sums of Σ_{n=1}^{N} 1/n² for
                   N = 10, 100, 1000, 10000, converging toward
                   π²/6 ≈ 1.644934066848...
                   Fixed params: 4 rows (N, S_N, |π²/6 − S_N|).
    sine_product - Sketch of Euler's 1734 argument:
                   sin x = x · Π_{n=1}^∞ (1 − x²/(n²π²))
                   Compare the x³ coefficient with the Taylor expansion
                   sin x = x − x³/3! + x⁵/5! − ...
                   to conclude Σ 1/n² = π²/6.
                   Fixed params: show first 3 factors, Taylor to x⁵.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 018 (Euler analysis), math pillar 1.
"""

import math

from manim import (
    FadeIn,
    MathTex,
    Scene,
    SurroundingRectangle,
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


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------
def basel_partial_sum(n_terms: int) -> float:
    """Compute Σ_{n=1}^{n_terms} 1/n²."""
    s = 0.0
    for n in range(1, n_terms + 1):
        s += 1.0 / (n * n)
    return s


class BaselProblem(Scene):
    """Euler's 1735 Basel problem solution. Mode-branching scene.

    Modes:
        partial_sums (default) - numerical convergence table
        sine_product           - sin x infinite product coefficient match
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "partial_sums")

        if mode == "sine_product":
            self.build_sine_product()
        else:
            self.build_partial_sums()

    # -------------------------------------------------------------------
    # Mode: partial_sums
    # -------------------------------------------------------------------
    def build_partial_sums(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan (y range [-2.0, +3.3], subtitle clearance y >= -2.0)
        # title:      y = +3.15 (top edge)
        # problem:    y = +2.25 (Σ has ∞ on top + n=1 on bottom, needs buffer)
        # header:     y = +1.15
        # rows:       y = +0.6, +0.1, -0.4, -0.9  (spacing 0.5)
        # conclusion: y = -1.55  (center; height ~0.45 so bottom ~ -1.78)

        title = Text("バーゼル問題", font=FONT, font_size=26, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        problem = MathTex(
            r"\sum_{n=1}^{\infty}",
            r"\frac{1}{n^2}",
            r"= \ ?",
            font_size=32,
        )
        problem[1].set_color(ACCENT_CYAN)
        problem[2].set_color(ACCENT_PINK)
        problem.move_to([0, 2.25, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(problem), run_time=0.8)
        self.wait(0.4)

        # Table header
        col_xs = [-4.2, -0.5, 3.5]
        header_y = 1.15

        header = VGroup(
            MathTex(r"N", font_size=22, color=TEXT_DIM),
            MathTex(r"S_N", font_size=22, color=TEXT_DIM),
            MathTex(r"\left|\tfrac{\pi^2}{6} - S_N\right|", font_size=22, color=TEXT_DIM),
        )
        for i, cell in enumerate(header):
            cell.move_to([col_xs[i], header_y, 0])

        self.play(FadeIn(header), run_time=0.4)

        n_values = [10, 100, 1000, 10000]
        target = math.pi * math.pi / 6.0

        rows = VGroup()
        row_spacing = 0.5
        start_y = header_y - 0.55

        for i, n in enumerate(n_values):
            s_n = basel_partial_sum(n)
            err = target - s_n
            y = start_y - i * row_spacing

            cells = VGroup(
                MathTex(f"{n}", font_size=24, color=ACCENT_CYAN),
                MathTex(f"{s_n:.7f}", font_size=24, color=TEXT_WHITE),
                MathTex(f"{err:.7f}", font_size=24, color=ACCENT_PINK),
            )
            for j, cell in enumerate(cells):
                cell.move_to([col_xs[j], y, 0])
            rows.add(cells)

        # Fade in rows sequentially
        anim_overhead = 0.5 + 0.8 + 0.4 + 0.4 + 1.2
        wait_per = max(0.3, (duration - anim_overhead) / max(len(n_values), 1))

        for row in rows:
            self.play(FadeIn(row), run_time=0.4)
            self.wait(wait_per * 0.35)

        # Final conclusion (safe zone: center y = -1.55, bottom ~ -1.78)
        conclusion = MathTex(
            r"\sum_{n=1}^{\infty} \frac{1}{n^2}",
            r"=",
            r"\frac{\pi^2}{6}",
            r"\approx 1.6449340668",
            font_size=28,
        )
        conclusion[0].set_color(ACCENT_CYAN)
        conclusion[2].set_color(highlight)
        conclusion.move_to([0, -1.55, 0])

        self.play(FadeIn(conclusion), run_time=0.8)
        box = SurroundingRectangle(conclusion[2], color=highlight, buff=0.08)
        self.play(FadeIn(box), run_time=0.4)
        self.wait(max(1.0, wait_per * 0.7))

    # -------------------------------------------------------------------
    # Mode: sine_product
    # -------------------------------------------------------------------
    def build_sine_product(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan (two-column coefficient comparison)
        # title:            y = +3.15
        # infinite_product: y = +2.25  (contains Σ and ∏, tall)
        # taylor:           y = +1.15
        # left column label:  y = +0.15  x = -3.4
        # right column label: y = +0.15  x = +3.0
        # left  coeff expr:   y = -0.65  x = -3.4
        # right coeff expr:   y = -0.65  x = +3.0
        # equals sign:        y = -0.65  x =  0.0  (smaller, matched to coeffs)
        # conclusion:  y = -1.60 (center; height ~0.5 → bottom ~ -1.85)

        title = Text(
            "sin x の二つの表現から Σ 1/n² を導く", font=FONT, font_size=22, color=TEXT_DIM
        )
        title.move_to([0, 3.15, 0])

        # Top: infinite product (fundamental identity)
        infinite_product = MathTex(
            r"\sin x",
            r"=",
            r"x \prod_{n=1}^{\infty}",
            r"\left(1 - \frac{x^2}{n^2 \pi^2}\right)",
            font_size=28,
        )
        infinite_product[0].set_color(ACCENT_CYAN)
        infinite_product.move_to([0, 2.25, 0])

        # Mid: Taylor expansion
        taylor = MathTex(
            r"\sin x",
            r"=",
            r"x - \frac{x^3}{3!} + \frac{x^5}{5!} - \cdots",
            font_size=28,
        )
        taylor[0].set_color(ACCENT_CYAN)
        taylor.move_to([0, 1.15, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(infinite_product), run_time=0.8)
        self.wait(0.3)
        self.play(FadeIn(taylor), run_time=0.7)
        self.wait(0.4)

        # Left column: coefficient from product side
        left_label = Text("無限積側 x³ の係数", font=FONT, font_size=20, color=ACCENT_CYAN)
        left_label.move_to([-3.4, 0.15, 0])
        left_expr = MathTex(
            r"-\frac{1}{\pi^2}\sum_{n=1}^{\infty}\frac{1}{n^2}",
            font_size=28,
        )
        left_expr.set_color(ACCENT_PINK)
        left_expr.move_to([-3.4, -0.70, 0])

        # Right column: coefficient from Taylor side
        right_label = Text("テイラー側 x³ の係数", font=FONT, font_size=20, color=ACCENT_CYAN)
        right_label.move_to([3.0, 0.15, 0])
        right_expr = MathTex(r"-\frac{1}{6}", font_size=32)
        right_expr.set_color(ACCENT_PINK)
        right_expr.move_to([3.0, -0.70, 0])

        # Equals sign between columns (size matched to coeffs)
        equals_sign = MathTex(r"=", font_size=32, color=TEXT_WHITE)
        equals_sign.move_to([-0.1, -0.70, 0])

        self.play(FadeIn(left_label), FadeIn(right_label), run_time=0.6)
        self.play(FadeIn(left_expr), run_time=0.6)
        self.wait(0.3)
        self.play(FadeIn(right_expr), run_time=0.5)
        self.wait(0.3)
        self.play(FadeIn(equals_sign), run_time=0.4)
        self.wait(0.5)

        # Conclusion (safe zone: bottom >= -2.0, verified via pixel check).
        # Σ has subscript n=1 descender + ∞ ascender so effective height is ~0.7.
        # At y=-1.45 with buff 0.06, box bottom ≈ -1.81, safely clear of -2.0.
        conclusion = MathTex(
            r"\sum_{n=1}^{\infty}\frac{1}{n^2}",
            r"=",
            r"\frac{\pi^2}{6}",
            font_size=26,
        )
        conclusion[0].set_color(ACCENT_CYAN)
        conclusion[2].set_color(highlight)
        conclusion.move_to([0, -1.45, 0])

        self.play(FadeIn(conclusion), run_time=0.8)
        box = SurroundingRectangle(conclusion, color=highlight, buff=0.06)
        self.play(FadeIn(box), run_time=0.4)

        anim_overhead = (
            0.5 + 0.8 + 0.3 + 0.7 + 0.4 + 0.6 + 0.6 + 0.3 + 0.5 + 0.3 + 0.4 + 0.5 + 0.8 + 0.4
        )
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "partial_sums": {"people": [], "years": []},
    "sine_product": {"people": [], "years": []},
}


SCENES = {
    "partial_sums": {
        "class": "BaselProblem",
        "params": {"mode": "partial_sums"},
        "description": "Σ 1/n² partial sums N=10..10000 converging to π²/6",
    },
    "sine_product": {
        "class": "BaselProblem",
        "params": {"mode": "sine_product"},
        "description": "Euler's 1734 sketch: sin x product + Taylor coefficient match → π²/6",
    },
}
