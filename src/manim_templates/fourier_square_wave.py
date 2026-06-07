"""
fourier_square_wave.py - Fourier series square wave approximation for 数学史記

Visualizes how sin waves sum to approximate a square wave.
The core visual of Episode 002 (Fourier).

Modes:
    buildup   - Add harmonics one by one (1st, 3rd, 5th, ...) showing
                the sum converging toward a square wave
    gibbs     - Focus on Gibbs phenomenon: show overshoot at discontinuity
    single    - Show a specific number of terms (static or quick build)

Duration-aware: reads target duration from _manim_params.json and adapts
the number of harmonics and wait times.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    RIGHT,
    UP,
    Axes,
    Create,
    FadeIn,
    FadeOut,
    MathTex,
    ReplacementTransform,
    Scene,
    Text,
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
    styled_text,
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


def square_wave_partial_sum(x, n_terms):
    """Compute partial Fourier sum of square wave with n_terms odd harmonics.

    f(x) = (4/pi) * sum_{k=1,3,5,...}^{2*n_terms-1} sin(kx)/k

    Args:
        x: input value (radians)
        n_terms: number of odd harmonics to include

    Returns:
        float value of the partial sum
    """
    result = 0.0
    for i in range(n_terms):
        k = 2 * i + 1  # odd harmonics: 1, 3, 5, 7, ...
        result += math.sin(k * x) / k
    return result * (4.0 / math.pi)


def single_harmonic(x, k):
    """Single harmonic component: (4/pi) * sin(kx)/k"""
    return (4.0 / math.pi) * math.sin(k * x) / k


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))
# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template; "default" is the lint's fallback key when no mode is given.
LINT_FACTUAL_CLAIMS = {
    "default": {"people": [["フーリエ", "Fourier"], ["ギブス", "Gibbs"]], "years": []}
}




# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class FourierSquareWave(Scene):
    """Visualize Fourier series approximation of a square wave."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "buildup")
        self._duration = params.get("duration", 30)
        self._max_terms = params.get("max_terms", None)  # override auto

        if mode == "gibbs":
            self.build_gibbs()
        elif mode == "single":
            self.build_single(params.get("n_terms", 5))
        else:
            self.build_buildup()

    # -------------------------------------------------------------------
    # Mode: buildup (main visual)
    # -------------------------------------------------------------------
    def build_buildup(self):
        """Progressively add harmonics, showing convergence to square wave."""
        dur = self._duration

        # Decide how many harmonics based on duration
        if self._max_terms:
            max_terms = self._max_terms
        elif dur >= 40:
            max_terms = 8
        elif dur >= 25:
            max_terms = 6
        elif dur >= 15:
            max_terms = 4
        else:
            max_terms = 3

        # Timing estimation
        # Each harmonic addition: ~1.5s animation
        # Plus waits between steps
        anim_time = max_terms * 1.5 + 3.0  # axes + title + final
        default_wait_total = max_terms * 1.0 + 2.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # --- Axes ---
        axes = Axes(
            x_range=[-3.5, 3.5, 1],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.3)

        # Target square wave (dashed, for reference)
        square_wave_graph = axes.plot(
            lambda x: 1.0 if math.sin(x) > 0 else (-1.0 if math.sin(x) < 0 else 0.0),
            x_range=[-3.4, 3.4, 0.001],
            color=TEXT_DIM,
            stroke_width=2.5,
            stroke_opacity=0.4,
        )

        # Title
        title = Text("フーリエ級数による矩形波の近似", font=FONT, font_size=28, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.4)

        self.play(FadeIn(axes), FadeIn(title), run_time=1.0)
        self.play(Create(square_wave_graph), run_time=1.0)
        self.wait(0.5 * ws)

        # --- Build up harmonics one by one ---
        current_graph = None
        term_label = None
        formula_parts = []

        colors = [
            ACCENT_CYAN,
            ACCENT_GOLD,
            ACCENT_PINK,
            "#7b68ee",
            "#20b2aa",
            "#ff6347",
            "#9370db",
            "#3cb371",
        ]

        for i in range(max_terms):
            n_terms = i + 1
            k = 2 * i + 1  # harmonic number: 1, 3, 5, 7, ...
            color = colors[i % len(colors)]

            # Plot the partial sum with n_terms
            new_graph = axes.plot(
                lambda x, nt=n_terms: square_wave_partial_sum(x, nt),
                x_range=[-3.4, 3.4, 0.01],
                color=ACCENT_CYAN,
                stroke_width=4.0,
            )

            # Individual harmonic (thin, colored)
            harmonic_graph = axes.plot(
                lambda x, kk=k: single_harmonic(x, kk),
                x_range=[-3.4, 3.4, 0.01],
                color=color,
                stroke_width=2.0,
                stroke_opacity=0.5,
            )

            # Label showing current term
            if k == 1:
                formula_str = r"\sin(x)"
            else:
                formula_str = r"+ \frac{\sin(" + str(k) + r"x)}{" + str(k) + r"}"

            # Label showing which odd harmonics are included
            harmonics_so_far = ", ".join(str(2 * j + 1) for j in range(n_terms))
            new_label = MathTex(
                r"k=" + harmonics_so_far,
                font_size=24,
                color=ACCENT_GOLD,
            )
            new_label.to_corner(UP + RIGHT, buff=0.5)

            if current_graph is None:
                # First harmonic
                self.play(Create(new_graph), FadeIn(harmonic_graph), run_time=1.5)
                self.play(FadeIn(new_label), run_time=0.3)
                self.play(FadeOut(harmonic_graph), run_time=0.3)
            else:
                # Transform sum graph, briefly show new harmonic
                self.play(FadeIn(harmonic_graph), run_time=0.5)
                self.play(
                    ReplacementTransform(current_graph, new_graph),
                    ReplacementTransform(term_label, new_label),
                    run_time=1.0,
                )
                self.play(FadeOut(harmonic_graph), run_time=0.3)

            current_graph = new_graph
            term_label = new_label
            self.wait(1.0 * ws)

        # Final hold
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: gibbs
    # -------------------------------------------------------------------
    def build_gibbs(self):
        """Focus on Gibbs phenomenon at discontinuity."""
        dur = self._duration
        anim_time = 8.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Zoomed-in axes near discontinuity
        axes = Axes(
            x_range=[-0.5, 1.5, 0.5],
            y_range=[-0.3, 1.4, 0.5],
            x_length=10,
            y_length=5.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.3)

        title = Text("ギブス現象", font=FONT, font_size=28, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.4)

        # Target square wave step
        step_graph = axes.plot(
            lambda x: 1.0 if x > 0 else (0.0 if x == 0 else -0.0),
            x_range=[-0.4, 1.4, 0.001],
            color=TEXT_DIM,
            stroke_width=2.5,
            stroke_opacity=0.4,
        )

        self.play(FadeIn(axes), FadeIn(title), FadeIn(step_graph), run_time=1.0)
        self.wait(1.0 * ws)

        # Show increasing terms: overshoot never disappears
        term_counts = [3, 10, 30, 100]
        current_graph = None
        label = None

        for n in term_counts:
            new_graph = axes.plot(
                lambda x, nt=n: square_wave_partial_sum(x, nt),
                x_range=[-0.4, 1.4, 0.001],
                color=ACCENT_CYAN,
                stroke_width=4.0,
            )
            new_label = Text(f"{n}項", font=FONT, font_size=24, color=ACCENT_GOLD)
            new_label.to_corner(UP + RIGHT, buff=0.5)

            if current_graph is None:
                self.play(Create(new_graph), FadeIn(new_label), run_time=1.5)
            else:
                self.play(
                    ReplacementTransform(current_graph, new_graph),
                    ReplacementTransform(label, new_label),
                    run_time=1.5,
                )
            current_graph = new_graph
            label = new_label
            self.wait(1.0 * ws)

        # Annotation: overshoot ≈ 9%
        overshoot_text = styled_text(
            ("不連続点での行き過ぎは ", "text"),
            (r"\approx 9\%", "math"),
            (" で一定", "text"),
            font_size=22,
        )
        overshoot_text.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(overshoot_text))
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: single
    # -------------------------------------------------------------------
    def build_single(self, n_terms):
        """Show a specific number of terms (quick or static display)."""
        dur = self._duration
        anim_time = 3.0
        default_wait_total = dur - anim_time
        ws = 1.0  # simple hold

        axes = Axes(
            x_range=[-3.5, 3.5, 1],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.3)

        square_wave_graph = axes.plot(
            lambda x: 1.0 if math.sin(x) > 0 else (-1.0 if math.sin(x) < 0 else 0.0),
            x_range=[-3.4, 3.4, 0.001],
            color=TEXT_DIM,
            stroke_width=2.5,
            stroke_opacity=0.4,
        )

        approx_graph = axes.plot(
            lambda x, nt=n_terms: square_wave_partial_sum(x, nt),
            x_range=[-3.4, 3.4, 0.01],
            color=ACCENT_CYAN,
            stroke_width=4.0,
        )

        label = Text(f"{n_terms}項", font=FONT, font_size=28, color=ACCENT_GOLD)
        label.to_corner(UP + RIGHT, buff=0.5)

        self.play(
            FadeIn(axes),
            FadeIn(square_wave_graph),
            Create(approx_graph),
            FadeIn(label),
            run_time=2.0,
        )
        self.wait(max(dur - 3.0, 1.0))
