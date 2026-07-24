"""
series_convergence.py - Ramanujan's 1/pi series convergence for 数学史記

Visualizes how Ramanujan's 1/pi series converges rapidly, gaining
approximately 8 digits of pi per term.

Modes:
    pi_series     - Show the formula and animate terms being added with
                    digit count increasing
    partial_sums  - Show partial sums converging to pi numerically

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 004 (Ramanujan), math_05
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    FadeIn,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def ramanujan_1pi_term(k):
    """Compute the k-th term of Ramanujan's 1/pi series.

    1/pi = (2*sqrt(2)/99^2) * sum_{k=0}^inf (4k)! / (k!)^4 * (26390k + 1103) / 396^{4k}
    """
    from math import factorial

    numerator = factorial(4 * k) * (26390 * k + 1103)
    denominator = (factorial(k) ** 4) * (396 ** (4 * k))
    return numerator / denominator


def partial_sum_pi(n_terms):
    """Compute pi approximation using n_terms of Ramanujan's series."""
    from math import sqrt

    coeff = 2 * sqrt(2) / (99**2)
    s = sum(ramanujan_1pi_term(k) for k in range(n_terms))
    return 1.0 / (coeff * s)


class PiSeries(Scene):
    """Show Ramanujan's 1/pi formula with digit count animation."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 25)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        # Formula display (simplified representation)
        formula_label = Text("Ramanujan (1914)", font=FONT, font_size=28, color=TEXT_DIM)
        formula_label.to_edge(UP, buff=0.4)

        formula = MathTex(
            r"\frac{1}{\pi}",
            r"=",
            r"\frac{2\sqrt{2}}{99^2}",
            r"\sum_{k=0}^{\infty}",
            r"\frac{(4k)!}{(k!)^4}",
            r"\cdot",
            r"\frac{26390k+1103}{396^{4k}}",
            font_size=32,
        )
        formula[0].set_color(ACCENT_CYAN)
        formula[2].set_color(TEXT_WHITE)
        formula[4].set_color(highlight_color)
        formula[6].set_color(ACCENT_PINK)
        formula.next_to(formula_label, DOWN, buff=0.5)

        self.play(FadeIn(formula_label), run_time=0.5)
        self.play(FadeIn(formula), run_time=1.2)
        self.wait(1.0)

        # Animate terms being added (4 terms to fit above subtitle area)
        n_terms_list = [1, 2, 3, 4]
        # Reserve time: 1.0 intro + 0.6*4 fade + wait_per*4 + 0.6 note_fade + 1.5 final
        anim_overhead = 1.0 + 0.6 * len(n_terms_list) + 0.6 + 1.5
        wait_per = max(0.5, (duration - anim_overhead) / (len(n_terms_list) + 1))

        term_display = VGroup()

        for _idx, n in enumerate(n_terms_list):
            # Simplified: show terms count and digit accuracy
            term_word = " term " if n == 1 else " terms "
            row = VGroup(
                MathTex(f"{n}", font_size=28, color=ACCENT_CYAN),
                Text(term_word, font=FONT, font_size=22, color=TEXT_DIM),
                MathTex(r"\rightarrow", font_size=24, color=TEXT_DIM),
                Text(f" {n * 8} digits", font=FONT, font_size=28, color=highlight_color),
            )
            row.arrange(RIGHT, buff=0.2)
            term_display.add(row)

        term_display.arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        term_display.next_to(formula, DOWN, buff=0.5)

        for row in term_display:
            self.play(FadeIn(row), run_time=0.6)
            self.wait(wait_per)

        # Emphasis note
        note = VGroup(
            MathTex(r"+1", font_size=28, color=ACCENT_CYAN),
            Text(" term ", font=FONT, font_size=26, color=ACCENT_PINK),
            MathTex(r"\rightarrow", font_size=28, color=ACCENT_PINK),
            Text(" +8 digits", font=FONT, font_size=26, color=ACCENT_PINK),
        )
        note.arrange(RIGHT, buff=0.15)
        note.next_to(term_display, DOWN, buff=0.4)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(min(1.5, wait_per))


class PartialSums(Scene):
    """Show partial sums converging to pi numerically."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 20)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        title = Text("Ramanujan (1914)", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)

        pi_label = MathTex(r"\pi = 3.14159265358979...", font_size=32, color=ACCENT_PINK)
        pi_label.next_to(title, DOWN, buff=0.4)

        self.play(FadeIn(title), FadeIn(pi_label), run_time=0.8)

        # Partial sums
        entries = VGroup()
        for n in range(1, 6):
            approx = partial_sum_pi(n)
            approx_str = f"{approx:.16f}"
            entry = VGroup(
                MathTex(f"S_{{{n}}}", font_size=26, color=ACCENT_CYAN),
                MathTex("=", font_size=26, color=TEXT_DIM),
                Text(approx_str, font=FONT, font_size=22, color=highlight_color),
            )
            entry.arrange(RIGHT, buff=0.2)
            entries.add(entry)

        entries.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        entries.next_to(pi_label, DOWN, buff=0.6)

        wait_per = max(0.5, (duration - 5) / 5)
        for entry in entries:
            self.play(FadeIn(entry), run_time=0.6)
            self.wait(wait_per)

        self.wait(1.0)


# ---------------------------------------------------------------------------
# Factual-claim metadata (read by qa_manim_consistency.py)
# ---------------------------------------------------------------------------
# Both scenes render the on-screen label "Ramanujan (1914)". This template is
# Ramanujan-1/pi-specific despite its generic-sounding name, so declare the
# claim: the consistency lint then WARNs if it is selected for a scene whose
# narration is not about Ramanujan / 1914 (guards the name-based misuse that put
# a Ramanujan formula into a Cauchy/Abel convergence scene).
LINT_FACTUAL_CLAIMS = {
    "pi_series": {"people": [["Ramanujan", "ラマヌジャン"]], "years": ["1914"]},
    "partial_sums": {"people": [["Ramanujan", "ラマヌジャン"]], "years": ["1914"]},
}

# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
SCENES = {
    "pi_series": PiSeries,
    "partial_sums": PartialSums,
}
