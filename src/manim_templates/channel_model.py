"""
channel_model.py - Shannon's communication channel model for 数学史記

Visualizes the communication channel model and channel capacity theorem.

Modes:
    diagram  - 5-block diagram: source → encoder → channel → decoder → destination
               with noise source arrow from above
               Fixed params: 5 blocks (情報源/符号器/通信路/復号器/受信先) + noise source
    noise    - Binary sequence with noise flipping bits, then error correction
               Fixed params: 8-bit sequence "10110010", flip indices [2,5]
    capacity - C = W log₂(1 + S/N) graph with axes
               Fixed params: x_range S/N=[0,30], y_range C/W=[0,5.5]

Duration-aware: reads target duration from _manim_params.json.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Axes,
    FadeIn,
    Indicate,
    MathTex,
    Rectangle,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _make_block(label_text, width=1.8, height=0.9, color=ACCENT_CYAN):
    """Create a labeled rectangle block."""
    rect = Rectangle(
        width=width,
        height=height,
        color=color,
        stroke_width=2,
        fill_color=BG_COLOR,
        fill_opacity=0.8,
    )
    label = Text(label_text, font=FONT, font_size=18, color=color)
    label.move_to(rect)
    return VGroup(rect, label)


class ChannelModel(Scene):
    """Visualize Shannon's communication channel model."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "diagram")
        self._duration = params.get("duration", 25)

        if mode == "noise":
            self.build_noise()
        elif mode == "capacity":
            self.build_capacity()
        else:
            self.build_diagram()

    # -------------------------------------------------------------------
    # Mode: diagram
    # -------------------------------------------------------------------
    def build_diagram(self):
        """5-block communication model with noise source."""
        dur = self._duration
        anim_time = 7.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Title
        title = Text(
            "シャノンの通信モデル",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # 5 blocks
        source = _make_block("情報源", color=ACCENT_GOLD)
        encoder = _make_block("符号器", color=ACCENT_CYAN)
        channel = _make_block("通信路", width=2.0, color=TEXT_WHITE)
        decoder = _make_block("復号器", color=ACCENT_CYAN)
        dest = _make_block("受信先", color=ACCENT_GOLD)

        blocks = VGroup(source, encoder, channel, decoder, dest)
        blocks.arrange(RIGHT, buff=0.6)
        blocks.shift(DOWN * 0.3)

        # Arrows between blocks
        arrows = VGroup()
        block_list = [source, encoder, channel, decoder, dest]
        for i in range(len(block_list) - 1):
            a = Arrow(
                block_list[i].get_right(),
                block_list[i + 1].get_left(),
                buff=0.1,
                color=TEXT_DIM,
                stroke_width=2,
            )
            arrows.add(a)

        # Noise source
        noise_block = _make_block("ノイズ源", width=1.6, height=0.7, color=ACCENT_PINK)
        noise_block.next_to(channel, UP, buff=1.0)
        noise_arrow = Arrow(
            noise_block.get_bottom(),
            channel.get_top(),
            buff=0.1,
            color=ACCENT_PINK,
            stroke_width=2,
        )

        # Animate: blocks appear left to right
        self.play(FadeIn(source), run_time=0.6)
        self.play(FadeIn(arrows[0]), FadeIn(encoder), run_time=0.6)
        self.play(FadeIn(arrows[1]), FadeIn(channel), run_time=0.6)
        self.play(FadeIn(arrows[2]), FadeIn(decoder), run_time=0.6)
        self.play(FadeIn(arrows[3]), FadeIn(dest), run_time=0.6)
        self.wait(0.5 * ws)

        # Noise appears
        self.play(FadeIn(noise_block), FadeIn(noise_arrow), run_time=0.8)
        self.wait(1.0 * ws)

        # Labels below
        signal_label = Text(
            "信号",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        signal_label.next_to(arrows[1], DOWN, buff=0.15)
        received_label = Text(
            "受信信号",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        received_label.next_to(arrows[2], DOWN, buff=0.15)

        self.play(FadeIn(signal_label), FadeIn(received_label), run_time=0.5)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: noise
    # -------------------------------------------------------------------
    def build_noise(self):
        """Binary sequence with noise flipping, then correction."""
        dur = self._duration
        anim_time = 7.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "ノイズと誤り訂正",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Original binary sequence
        original_bits = "1 0 1 1 0 0 1 0"
        bits_list = original_bits.split()

        label_orig = Text("送信:", font=FONT, font_size=22, color=ACCENT_GOLD)
        label_orig.shift(UP * 1.5 + LEFT * 5.0)

        orig_texts = VGroup()
        for i, b in enumerate(bits_list):
            t = Text(b, font=FONT, font_size=36, color=ACCENT_CYAN)
            t.shift(UP * 1.5 + LEFT * (3.0 - i * 0.9))
            orig_texts.add(t)

        self.play(FadeIn(label_orig), run_time=0.3)
        self.play(FadeIn(orig_texts), run_time=0.8)
        self.wait(0.8 * ws)

        # Noisy version (some bits flipped)
        noisy_bits = list(bits_list)
        flip_indices = [2, 5]  # positions to flip
        for idx in flip_indices:
            noisy_bits[idx] = "0" if noisy_bits[idx] == "1" else "1"

        label_noisy = Text("受信:", font=FONT, font_size=22, color=ACCENT_PINK)
        label_noisy.shift(DOWN * 0.0 + LEFT * 5.0)

        noisy_texts = VGroup()
        for i, b in enumerate(noisy_bits):
            color = ACCENT_PINK if i in flip_indices else ACCENT_CYAN
            t = Text(b, font=FONT, font_size=36, color=color)
            t.shift(DOWN * 0.0 + LEFT * (3.0 - i * 0.9))
            noisy_texts.add(t)

        self.play(FadeIn(label_noisy), FadeIn(noisy_texts), run_time=0.8)
        self.wait(0.5 * ws)

        # Highlight flipped bits
        for idx in flip_indices:
            self.play(
                Indicate(noisy_texts[idx], color=ACCENT_PINK, scale_factor=1.4),
                run_time=0.5,
            )
        self.wait(0.5 * ws)

        # Corrected version
        label_corrected = Text("復号:", font=FONT, font_size=22, color=ACCENT_GOLD)
        label_corrected.shift(DOWN * 1.5 + LEFT * 5.0)

        corrected_texts = VGroup()
        for i, b in enumerate(bits_list):
            t = Text(b, font=FONT, font_size=36, color=ACCENT_GOLD)
            t.shift(DOWN * 1.5 + LEFT * (3.0 - i * 0.9))
            corrected_texts.add(t)

        self.play(FadeIn(label_corrected), FadeIn(corrected_texts), run_time=0.8)
        self.wait(1.0 * ws)

        # Bottom note
        note = Text(
            "シャノン限界以下の速度なら、誤りなく通信できる",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: capacity
    # -------------------------------------------------------------------
    def build_capacity(self):
        """C = W log₂(1 + S/N) graph."""
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "通信路容量",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Formula
        formula = MathTex(
            r"C = W \log_2 \left(1 + \frac{S}{N}\right)",
            font_size=44,
            color=ACCENT_GOLD,
        )
        formula.shift(UP * 2.2)
        self.play(FadeIn(formula), run_time=1.0)
        self.wait(0.5 * ws)

        # Graph: C/W vs S/N
        axes = Axes(
            x_range=[0, 30, 5],
            y_range=[0, 5.5, 1],
            x_length=8,
            y_length=3.5,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": True,
                "include_tip": False,
            },
        )
        axes.shift(DOWN * 0.8)

        x_label = MathTex(r"S/N", font_size=24, color=TEXT_WHITE)
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.2)
        y_label = MathTex(r"C/W", font_size=24, color=TEXT_WHITE)
        y_label.next_to(axes.y_axis.get_top(), UP, buff=0.2)

        graph = axes.plot(
            lambda x: math.log2(1 + x),
            x_range=[0.01, 30, 0.1],
            color=ACCENT_CYAN,
            stroke_width=3,
        )

        self.play(FadeIn(axes), FadeIn(x_label), FadeIn(y_label), run_time=1.0)
        self.play(FadeIn(graph), run_time=1.5)
        self.wait(1.0 * ws)

        # Annotations
        ann_w = Text("W: 帯域幅", font=FONT, font_size=20, color=TEXT_DIM)
        ann_sn = Text("S/N: 信号対雑音比", font=FONT, font_size=20, color=TEXT_DIM)
        ann_group = VGroup(ann_w, ann_sn).arrange(RIGHT, buff=1.5)
        ann_group.to_edge(DOWN, buff=0.9)

        self.play(FadeIn(ann_group), run_time=0.5)
        self.wait(2.0 * ws)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "diagram": {"people": [], "years": []},
    "noise": {"people": [], "years": []},
    "capacity": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
SCENES = {
    "diagram": ChannelModel,
    "noise": ChannelModel,
    "capacity": ChannelModel,
}
