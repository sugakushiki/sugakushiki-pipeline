"""
wave_decomposition.py - Wave decomposition visualization for 数学史記

Shows a composite waveform being decomposed into individual sine wave
components. The reverse perspective of fourier_square_wave: instead of
building up, we break down.

Modes:
    decompose   - Start with a composite wave, then separate into components
    compose     - Start with individual components, combine into composite
    spectrum    - Show frequency spectrum (amplitude vs frequency bar chart)

Duration-aware: reads target duration from _manim_params.json.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Axes,
    Create,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Rectangle,
    ReplacementTransform,
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


# ---------------------------------------------------------------------------
# Wave definitions
# ---------------------------------------------------------------------------

# Default components: a few harmonics that make an interesting shape
DEFAULT_COMPONENTS = [
    {"amplitude": 1.0, "frequency": 1, "phase": 0},
    {"amplitude": 0.5, "frequency": 3, "phase": 0},
    {"amplitude": 0.3, "frequency": 5, "phase": 0},
]

COMPONENT_COLORS = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK, "#7b68ee", "#20b2aa"]


def composite_wave(x, components):
    """Sum of sine components."""
    result = 0.0
    for c in components:
        result += c["amplitude"] * math.sin(c["frequency"] * x + c.get("phase", 0))
    return result


def single_component(x, comp):
    """Single sine component."""
    return comp["amplitude"] * math.sin(comp["frequency"] * x + comp.get("phase", 0))


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))
# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}




# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class WaveDecomposition(Scene):
    """Visualize wave decomposition / composition."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "decompose")
        self._duration = params.get("duration", 25)
        self._components = params.get("components", DEFAULT_COMPONENTS)

        if mode == "compose":
            self.build_compose()
        elif mode == "spectrum":
            self.build_spectrum()
        else:
            self.build_decompose()

    # -------------------------------------------------------------------
    # Mode: decompose (main visual)
    # -------------------------------------------------------------------
    def build_decompose(self):
        """Start with composite, then separate into individual components."""
        dur = self._duration
        components = self._components
        n_comp = len(components)

        anim_time = 3.0 + n_comp * 2.5
        default_wait_total = 2.0 + n_comp * 1.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # --- Full composite wave (top) ---
        axes_top = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2.0, 2.0, 1],
            x_length=10,
            y_length=2.3,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes_top.shift(UP * 2.0)

        composite_graph = axes_top.plot(
            lambda x: composite_wave(x, components),
            x_range=[-3.8, 3.8, 0.02],
            color=TEXT_WHITE,
            stroke_width=4.0,
        )

        title = Text("この波形は何でできている？", font=FONT, font_size=26, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.5)

        self.play(FadeIn(title), FadeIn(axes_top), Create(composite_graph), run_time=2.0)
        self.wait(1.0 * ws)

        # --- Decompose into individual components (stacked below) ---
        decompose_title = Text("分解すると...", font=FONT, font_size=22, color=ACCENT_GOLD)
        decompose_title.move_to(ORIGIN + UP * 0.5)
        self.play(FadeIn(decompose_title), run_time=0.5)
        self.wait(0.5 * ws)

        # Calculate vertical positions for component axes
        # Each component gets a small axes below
        comp_height = 1.1
        start_y = -0.1
        component_visuals = []

        for i, comp in enumerate(components):
            color = COMPONENT_COLORS[i % len(COMPONENT_COLORS)]
            freq = comp["frequency"]
            amp = comp["amplitude"]

            # Small axes for this component
            axes_comp = Axes(
                x_range=[-4, 4, 2],
                y_range=[-1.2, 1.2, 1],
                x_length=8,
                y_length=comp_height,
                axis_config={
                    "color": TEXT_DIM,
                    "stroke_width": 0.5,
                    "include_ticks": False,
                    "include_tip": False,
                },
            )
            y_pos = start_y - i * (comp_height + 0.15)
            axes_comp.move_to([0, y_pos, 0])

            comp_graph = axes_comp.plot(
                lambda x, c=comp: single_component(x, c),
                x_range=[-3.8, 3.8, 0.02],
                color=color,
                stroke_width=3.0,
            )

            # Label: amplitude × sin(freq × x)
            if freq == 1:
                freq_str = "x"
            else:
                freq_str = f"{freq}x"

            if amp == 1.0:
                label_str = rf"\sin({freq_str})"
            else:
                label_str = rf"{amp}\sin({freq_str})"

            label = MathTex(label_str, font_size=20, color=color)
            label.next_to(axes_comp, RIGHT, buff=0.2)

            self.play(
                FadeIn(axes_comp),
                Create(comp_graph),
                FadeIn(label),
                run_time=1.5,
            )
            self.wait(0.5 * ws)

            component_visuals.append((axes_comp, comp_graph, label))

        self.wait(1.5 * ws)

    # -------------------------------------------------------------------
    # Mode: compose
    # -------------------------------------------------------------------
    def build_compose(self):
        """Start with individual components, combine into composite."""
        dur = self._duration
        components = self._components
        n_comp = len(components)

        anim_time = n_comp * 2.0 + 4.0
        default_wait_total = n_comp * 0.8 + 3.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2.0, 2.0, 1],
            x_length=10,
            y_length=5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.shift(UP * 0.2)

        title = Text("波を足し合わせる", font=FONT, font_size=26, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.5)
        self.play(FadeIn(axes), FadeIn(title), run_time=1.0)

        # Add components one by one
        current_sum_func = lambda x: 0.0
        current_graph = None
        sum_label = None

        for i, comp in enumerate(components):
            color = COMPONENT_COLORS[i % len(COMPONENT_COLORS)]
            freq = comp["frequency"]
            amp = comp["amplitude"]

            # Show individual component briefly
            comp_graph = axes.plot(
                lambda x, c=comp: single_component(x, c),
                x_range=[-3.8, 3.8, 0.02],
                color=color,
                stroke_width=1.5,
                stroke_opacity=0.6,
            )

            self.play(Create(comp_graph), run_time=0.8)

            # Update cumulative sum
            prev_func = current_sum_func
            current_sum_func = lambda x, pf=prev_func, c=comp: pf(x) + single_component(x, c)

            new_graph = axes.plot(
                current_sum_func,
                x_range=[-3.8, 3.8, 0.02],
                color=ACCENT_CYAN,
                stroke_width=4.0,
            )

            # Day 14 fix: separate MathTex (number) from Text (Japanese)
            # MathTex cannot render Japanese chars without \usepackage{CJK}.
            number_label = MathTex(
                f"{i + 1}",
                font_size=22,
                color=ACCENT_GOLD,
            )
            text_label = Text(
                "つの波の合成",
                font=FONT,
                font_size=22,
                color=ACCENT_GOLD,
            )
            text_label.next_to(number_label, RIGHT, buff=0.08)
            new_label = VGroup(number_label, text_label)
            new_label.to_corner(UP + RIGHT, buff=0.5)

            if current_graph is None:
                self.play(
                    ReplacementTransform(comp_graph, new_graph),
                    FadeIn(new_label),
                    run_time=1.0,
                )
            else:
                self.play(
                    FadeOut(comp_graph),
                    ReplacementTransform(current_graph, new_graph),
                    ReplacementTransform(sum_label, new_label),
                    run_time=1.0,
                )

            current_graph = new_graph
            sum_label = new_label
            self.wait(0.8 * ws)

        # Final note
        note = Text(
            "単純な波の足し算で、複雑な波形が生まれる",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note))
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: spectrum
    # -------------------------------------------------------------------
    def build_spectrum(self):
        """Show frequency spectrum as bar chart."""
        dur = self._duration
        components = self._components

        anim_time = 4.0
        default_wait_total = 4.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Title
        title = Text("周波数スペクトル", font=FONT, font_size=26, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.5)

        # Top: waveform
        axes_wave = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=2.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes_wave.shift(UP * 1.5)

        wave_graph = axes_wave.plot(
            lambda x: composite_wave(x, components),
            x_range=[-3.8, 3.8, 0.02],
            color=ACCENT_CYAN,
            stroke_width=4.0,
        )

        self.play(FadeIn(title), FadeIn(axes_wave), Create(wave_graph), run_time=1.5)
        self.wait(1.0 * ws)

        # Bottom: bar chart of amplitudes
        # Find max frequency for axis range
        max_freq = max(c["frequency"] for c in components)
        bar_width = 0.6

        bars = VGroup()
        labels = VGroup()

        for i, comp in enumerate(components):
            color = COMPONENT_COLORS[i % len(COMPONENT_COLORS)]
            freq = comp["frequency"]
            amp = comp["amplitude"]

            # Bar
            bar_height = amp * 2.5  # scale for visibility
            bar = Rectangle(
                width=bar_width,
                height=bar_height,
                fill_color=color,
                fill_opacity=0.8,
                stroke_color=color,
                stroke_width=1.5,
            )
            x_pos = -3 + freq * (6.0 / (max_freq + 1))
            bar.move_to([x_pos, -2.0 + bar_height / 2, 0])
            bars.add(bar)

            # Frequency label below
            freq_label = MathTex(str(freq), font_size=18, color=TEXT_DIM)
            freq_label.next_to(bar, DOWN, buff=0.15)
            labels.add(freq_label)

        # Axis line
        freq_axis = Line(
            [-4, -2.0, 0],
            [4, -2.0, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        freq_axis_label = Text("周波数", font=FONT, font_size=18, color=TEXT_DIM)
        freq_axis_label.next_to(freq_axis, RIGHT, buff=0.2)

        amp_label = Text("振幅", font=FONT, font_size=18, color=TEXT_DIM)
        amp_label.next_to(bars, LEFT, buff=0.3)

        self.play(
            FadeIn(freq_axis),
            FadeIn(freq_axis_label),
            FadeIn(amp_label),
            run_time=0.5,
        )

        # Animate bars appearing one by one
        for bar, label in zip(bars, labels, strict=False):
            self.play(FadeIn(bar, shift=UP * 0.3), FadeIn(label), run_time=0.5)

        self.wait(1.0 * ws)

        note = Text(
            "どの周波数がどれだけ含まれているか ── これがフーリエ変換の本質",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note))
        self.wait(2.0 * ws)
