"""
madhava_pi_series.py - Mādhava's pi series visualization for 数学史記

Visualizes Mādhava's (c.1400) discovery of the arctan series and the
π/4 series, plus his end-correction terms that accelerate convergence.

Modes:
    arctan_derivation - arctan(x) = x - x³/3 + x⁵/5 - ... ; set x=1 to
                        obtain π/4 = 1 - 1/3 + 1/5 - 1/7 + ...
                        Fixed params: series shown to 7th power.
    partial_sums      - Table of partial sums of π/4 = 1 - 1/3 + 1/5 - ...
                        to demonstrate slow convergence.
                        Fixed params: n = 1, 10, 50, 100, 1000.
    with_correction   - Side-by-side: plain partial sums vs Mādhava-
                        corrected sums with correction term n / (4n² + 1).
                        Fixed params: n = 10, 20, 50.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 015 (Mādhava), math pillars 2 and 3.
"""

import math

from manim import (
    DOWN,
    UP,
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
def pi_partial_sum(n_terms: int) -> float:
    """π approximation from n_terms of Mādhava's π/4 series.

    π/4 = Σ_{k=0}^{n-1} (-1)^k / (2k+1). Returns 4 × Σ.
    """
    s = 0.0
    for k in range(n_terms):
        s += (-1) ** k / (2 * k + 1)
    return 4.0 * s


def pi_with_correction(n_terms: int) -> float:
    """π approximation with Mādhava's end-correction term n/(4n²+1).

    π/4 ≈ Σ_{k=0..n-1} (-1)^k/(2k+1) + (-1)^n · n/(4n² + 1).

    This is the correction term recorded in Jyeṣṭhadeva's Yuktibhāṣā
    as being due to Mādhava.
    """
    s = 0.0
    for k in range(n_terms):
        s += (-1) ** k / (2 * k + 1)
    correction = (-1) ** n_terms * n_terms / (4 * n_terms**2 + 1)
    return 4.0 * (s + correction)


class MadhavaPiSeries(Scene):
    """Mādhava's π series. Mode-branching scene.

    Modes:
        arctan_derivation (default) - arctan series → π/4 series
        partial_sums                 - slow-converging partial sums
        with_correction              - correction term accelerates convergence
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "arctan_derivation")

        if mode == "partial_sums":
            self.build_partial_sums()
        elif mode == "with_correction":
            self.build_with_correction()
        else:
            self.build_arctan_derivation()

    # -------------------------------------------------------------------
    # Mode: arctan_derivation
    # -------------------------------------------------------------------
    def build_arctan_derivation(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("マーダヴァの逆正接級数", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.5)

        arctan_formula = MathTex(
            r"\arctan x",
            r"=",
            r"x - \frac{x^3}{3} + \frac{x^5}{5} - \frac{x^7}{7} + \cdots",
            font_size=36,
        )
        arctan_formula[0].set_color(ACCENT_CYAN)
        arctan_formula.next_to(title, DOWN, buff=0.5)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(arctan_formula), run_time=1.0)
        self.wait(0.8)

        substitute_note = MathTex(r"x = 1", font_size=32, color=highlight)
        substitute_note.next_to(arctan_formula, DOWN, buff=0.5)

        self.play(FadeIn(substitute_note), run_time=0.5)
        self.wait(0.6)

        mid_formula = MathTex(
            r"\arctan 1",
            r"=",
            r"\frac{\pi}{4}",
            font_size=32,
        )
        mid_formula[2].set_color(ACCENT_PINK)
        mid_formula.next_to(substitute_note, DOWN, buff=0.4)

        self.play(FadeIn(mid_formula), run_time=0.6)
        self.wait(0.5)

        pi_series = MathTex(
            r"\frac{\pi}{4}",
            r"=",
            r"1 - \frac{1}{3} + \frac{1}{5} - \frac{1}{7} + \cdots",
            font_size=40,
        )
        pi_series[0].set_color(ACCENT_PINK)
        pi_series.next_to(mid_formula, DOWN, buff=0.5)

        self.play(FadeIn(pi_series), run_time=0.8)

        box = SurroundingRectangle(pi_series, color=highlight, buff=0.2)
        self.play(FadeIn(box), run_time=0.4)

        anim_overhead = 0.5 + 1.0 + 0.8 + 0.5 + 0.6 + 0.6 + 0.5 + 0.8 + 0.4
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: partial_sums
    # -------------------------------------------------------------------
    def build_partial_sums(self):
        duration = self._duration
        highlight = self._highlight_color

        title = MathTex(
            r"\frac{\pi}{4} = 1 - \frac{1}{3} + \frac{1}{5} - \frac{1}{7} + \cdots",
            font_size=32,
        )
        title.to_edge(UP, buff=0.5)

        pi_label = MathTex(
            r"\pi \approx 3.14159\,26535\,89793",
            font_size=26,
            color=ACCENT_PINK,
        )
        pi_label.next_to(title, DOWN, buff=0.3)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(pi_label), run_time=0.5)
        self.wait(0.4)

        # Column x-coordinates
        col_xs = [-4.0, -0.5, 3.8]

        header = VGroup(
            Text("項数 n", font=FONT, font_size=22, color=TEXT_DIM),
            Text("部分和による近似", font=FONT, font_size=22, color=TEXT_DIM),
            Text("有効桁数", font=FONT, font_size=22, color=TEXT_DIM),
        )
        header_y = 1.4
        for i, cell in enumerate(header):
            cell.move_to([col_xs[i], header_y, 0])

        self.play(FadeIn(header), run_time=0.5)

        n_values = [1, 10, 50, 100, 1000]
        pi_ref = math.pi
        pi_ref_str = f"{pi_ref:.10f}"  # "3.1415926536"

        rows = []
        for n in n_values:
            approx = pi_partial_sum(n)
            approx_str = f"{approx:.10f}"
            # Count matching significant digits (including the leading "3").
            # The decimal point is skipped so it doesn't inflate the count.
            sig_digits = 0
            for a, b in zip(approx_str, pi_ref_str, strict=False):
                if a == ".":
                    continue
                if a == b:
                    sig_digits += 1
                else:
                    break

            row = VGroup(
                MathTex(f"{n}", font_size=26, color=ACCENT_CYAN),
                MathTex(f"{approx:.7f}", font_size=26, color=TEXT_WHITE),
                MathTex(f"{sig_digits}", font_size=26, color=highlight),
            )
            rows.append((row, n))

        row_spacing = 0.55
        start_y = header_y - 0.6
        rendered = VGroup()
        for idx, (row, _n) in enumerate(rows):
            y = start_y - idx * row_spacing
            for j, cell in enumerate(row):
                cell.move_to([col_xs[j], y, 0])
            rendered.add(row)

        anim_overhead = 0.6 + 0.5 + 0.4 + 0.5 + 1.0
        wait_per = max(0.3, (duration - anim_overhead) / max(len(rows), 1))

        for row in rendered:
            self.play(FadeIn(row), run_time=0.4)
            self.wait(wait_per * 0.4)

        note = Text("1000項でも3桁の精度にとどまる", font=FONT, font_size=22, color=ACCENT_PINK)
        last_y = start_y - (len(rows) - 1) * row_spacing
        note.move_to([0, last_y - 0.7, 0])

        self.play(FadeIn(note), run_time=0.5)
        self.wait(max(1.0, wait_per * 0.8))

    # -------------------------------------------------------------------
    # Mode: with_correction
    # -------------------------------------------------------------------
    def build_with_correction(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("マーダヴァの補正項", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.5)

        correction_formula = MathTex(
            r"\frac{\pi}{4}",
            r"\approx",
            r"\sum_{k=0}^{n-1} \frac{(-1)^k}{2k+1}",
            r"+",
            r"(-1)^n \cdot \frac{n}{4n^2 + 1}",
            font_size=30,
        )
        correction_formula[4].set_color(highlight)
        correction_formula.next_to(title, DOWN, buff=0.35)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(correction_formula), run_time=1.0)
        self.wait(0.6)

        col_xs = [-4.5, -1.2, 3.4]
        header_y = 0.9

        header = VGroup(
            Text("項数 n", font=FONT, font_size=22, color=TEXT_DIM),
            Text("部分和のみ", font=FONT, font_size=22, color=TEXT_DIM),
            Text("補正項を加えた", font=FONT, font_size=22, color=ACCENT_GOLD),
        )
        for i, cell in enumerate(header):
            cell.move_to([col_xs[i], header_y, 0])

        self.play(FadeIn(header), run_time=0.5)

        n_values = [10, 20, 50]
        rows = VGroup()
        row_spacing = 0.55

        for i, n in enumerate(n_values):
            plain = pi_partial_sum(n)
            corrected = pi_with_correction(n)
            y = header_y - 0.6 - i * row_spacing

            cells = VGroup(
                MathTex(f"{n}", font_size=26, color=ACCENT_CYAN),
                MathTex(f"{plain:.9f}", font_size=22, color=TEXT_WHITE),
                MathTex(f"{corrected:.9f}", font_size=22, color=highlight),
            )
            for j, cell in enumerate(cells):
                cell.move_to([col_xs[j], y, 0])
            rows.add(cells)

        anim_overhead = 0.5 + 1.0 + 0.6 + 0.5 + 0.6 + 1.0
        wait_per = max(0.4, (duration - anim_overhead) / max(len(n_values), 1))

        for row in rows:
            self.play(FadeIn(row), run_time=0.5)
            self.wait(wait_per * 0.3)

        pi_ref_text = MathTex(
            r"\pi \approx 3.141592653",
            font_size=26,
            color=ACCENT_PINK,
        )
        last_y = header_y - 0.6 - (len(n_values) - 1) * row_spacing
        pi_ref_text.move_to([0, last_y - 0.8, 0])

        self.play(FadeIn(pi_ref_text), run_time=0.6)
        self.wait(max(1.0, wait_per * 0.6))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# factual claims displayed in each mode.
# Numerical constants like 3.141592653 are math literals, not factual claims.
LINT_FACTUAL_CLAIMS = {
    "arctan_derivation": {
        "people": [["マーダヴァ", "Madhava"]],
        "years": [],
    },
    "partial_sums": {
        "people": [["マーダヴァ", "Madhava"]],
        "years": [],
    },
    "with_correction": {
        "people": [["マーダヴァ", "Madhava"]],
        "years": [],
    },
}


SCENES = {
    "arctan_derivation": {
        "class": "MadhavaPiSeries",
        "params": {"mode": "arctan_derivation"},
        "description": "arctan series -> pi/4 = 1 - 1/3 + 1/5 - ... derivation",
    },
    "partial_sums": {
        "class": "MadhavaPiSeries",
        "params": {"mode": "partial_sums"},
        "description": "pi/4 series partial sums n=1..1000, slow convergence",
    },
    "with_correction": {
        "class": "MadhavaPiSeries",
        "params": {"mode": "with_correction"},
        "description": "Madhava's end-correction term dramatically improves precision",
    },
}
