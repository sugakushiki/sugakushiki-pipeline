"""
symmetry_conservation.py - Noether's first theorem visualization for 数学史記

Visualizes the correspondence between continuous symmetries and conservation laws.

Modes:
    spatial    - Translational symmetry → momentum conservation
                 Fixed params: ball at two positions, same physics, arrow = momentum
    temporal   - Time symmetry → energy conservation
                 Fixed params: clock at two times, same law, arrow = energy
    rotational - Rotational symmetry → angular momentum conservation
                 Fixed params: rotating system at two angles, arrow = angular momentum
    theorem    - Summary: 3 symmetries ↔ 3 conservation laws connected by arrows
                 Fixed params: left column (3 symmetries), right column (3 laws), 3 arrows

Duration-aware: reads target duration from _manim_params.json.
"""

import math

from manim import (
    DEGREES,
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Dot,
    FadeIn,
    GrowArrow,
    Line,
    MathTex,
    RoundedRectangle,
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


def _make_box(label_text, width=2.8, height=0.7, color=ACCENT_CYAN, font_size=24):
    """Create a labeled rounded rectangle (auto-expands to fit text)."""
    label = Text(label_text, font=FONT, font_size=font_size, color=color)
    auto_width = max(width, label.width + 0.6)
    rect = RoundedRectangle(
        width=auto_width,
        height=height,
        corner_radius=0.15,
        color=color,
        stroke_width=2,
        fill_color=BG_COLOR,
        fill_opacity=0.8,
    )
    label.move_to(rect.get_center())
    return VGroup(rect, label)


class SymmetryConservation(Scene):
    """Visualize Noether's first theorem: symmetry ↔ conservation law."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "theorem")
        self._duration = params.get("duration", 25)

        if mode == "spatial":
            self.build_spatial()
        elif mode == "temporal":
            self.build_temporal()
        elif mode == "rotational":
            self.build_rotational()
        else:
            self.build_theorem()

    # -------------------------------------------------------------------
    # Mode: spatial — translational symmetry → momentum conservation
    # -------------------------------------------------------------------
    def build_spatial(self):
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "空間の並進対称性",
            font=FONT,
            font_size=30,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Ground line
        ground = Line(LEFT * 5, RIGHT * 5, color=TEXT_DIM, stroke_width=1)
        ground.shift(DOWN * 0.5)
        self.play(FadeIn(ground), run_time=0.3)

        # Ball at position A
        ball_a = Circle(radius=0.3, color=ACCENT_CYAN, fill_opacity=0.6)
        ball_a.shift(LEFT * 2.5 + UP * 0.0)
        label_a = Text("A", font=FONT, font_size=20, color=TEXT_WHITE)
        label_a.next_to(ball_a, DOWN, buff=0.3)

        # Ball at position B (shifted)
        ball_b = Circle(radius=0.3, color=ACCENT_CYAN, fill_opacity=0.6)
        ball_b.shift(RIGHT * 1.5 + UP * 0.0)
        label_b = Text("B", font=FONT, font_size=20, color=TEXT_WHITE)
        label_b.next_to(ball_b, DOWN, buff=0.3)

        # Shift arrow between positions
        shift_arrow = Arrow(
            ball_a.get_right() + RIGHT * 0.1,
            ball_b.get_left() + LEFT * 0.1,
            color=ACCENT_GOLD,
            stroke_width=3,
            buff=0.1,
        )
        shift_label = Text(
            "空間シフト",
            font=FONT,
            font_size=18,
            color=ACCENT_GOLD,
        )
        shift_label.next_to(shift_arrow, UP, buff=0.15)

        self.play(FadeIn(ball_a), FadeIn(label_a), run_time=0.5)
        self.wait(0.5 * ws)
        self.play(GrowArrow(shift_arrow), FadeIn(shift_label), run_time=0.8)
        self.play(FadeIn(ball_b), FadeIn(label_b), run_time=0.5)
        self.wait(0.5 * ws)

        # "Same physics" annotation
        same = Text(
            "物理法則は同じ",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        same.shift(UP * 1.5)
        self.play(FadeIn(same), run_time=0.5)
        self.wait(0.8 * ws)

        # Result
        result_box = _make_box("運動量が保存される", color=ACCENT_PINK, font_size=26)
        result_box.shift(DOWN * 1.8)
        self.play(FadeIn(result_box), run_time=0.8)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: temporal — time symmetry → energy conservation
    # -------------------------------------------------------------------
    def build_temporal(self):
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "時間の対称性",
            font=FONT,
            font_size=30,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Two clocks (circles with hands) representing different times
        clock_a = Circle(radius=0.8, color=ACCENT_CYAN, stroke_width=2)
        clock_a.shift(LEFT * 2.5 + UP * 0.3)
        hand_a = Line(ORIGIN, UP * 0.6, color=TEXT_WHITE, stroke_width=3)
        hand_a.shift(clock_a.get_center())
        label_ta = Text("t", font=FONT, font_size=20, color=TEXT_WHITE)
        label_ta.next_to(clock_a, DOWN, buff=0.3)

        clock_b = Circle(radius=0.8, color=ACCENT_CYAN, stroke_width=2)
        clock_b.shift(RIGHT * 1.5 + UP * 0.3)
        # Hand at a different angle
        hand_b = Line(ORIGIN, RIGHT * 0.42 + UP * 0.42, color=TEXT_WHITE, stroke_width=3)
        hand_b.shift(clock_b.get_center())
        label_tb = Text("t + T", font=FONT, font_size=20, color=TEXT_WHITE)
        label_tb.next_to(clock_b, DOWN, buff=0.3)

        shift_arrow = Arrow(
            clock_a.get_right() + RIGHT * 0.1,
            clock_b.get_left() + LEFT * 0.1,
            color=ACCENT_GOLD,
            stroke_width=3,
            buff=0.1,
        )
        shift_label = Text(
            "時間シフト",
            font=FONT,
            font_size=18,
            color=ACCENT_GOLD,
        )
        shift_label.next_to(shift_arrow, UP, buff=0.15)

        self.play(
            FadeIn(clock_a),
            FadeIn(hand_a),
            FadeIn(label_ta),
            run_time=0.5,
        )
        self.wait(0.5 * ws)
        self.play(GrowArrow(shift_arrow), FadeIn(shift_label), run_time=0.8)
        self.play(
            FadeIn(clock_b),
            FadeIn(hand_b),
            FadeIn(label_tb),
            run_time=0.5,
        )
        self.wait(0.5 * ws)

        same = Text(
            "物理法則は同じ",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        same.shift(UP * 2.2)
        self.play(FadeIn(same), run_time=0.5)
        self.wait(0.8 * ws)

        result_box = _make_box("エネルギーが保存される", color=ACCENT_PINK, font_size=26)
        result_box.shift(DOWN * 1.8)
        self.play(FadeIn(result_box), run_time=0.8)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: rotational — rotational symmetry → angular momentum
    # -------------------------------------------------------------------
    def build_rotational(self):
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "回転対称性",
            font=FONT,
            font_size=30,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Central system
        center = Dot(ORIGIN, color=TEXT_WHITE, radius=0.08)
        orbit = Circle(radius=1.5, color=TEXT_DIM, stroke_width=1)

        # Object A on orbit
        angle_a = 30 * DEGREES
        pos_a = 1.5 * (math.cos(angle_a) * RIGHT + math.sin(angle_a) * UP)
        dot_a = Dot(pos_a, color=ACCENT_CYAN, radius=0.15)
        label_a = MathTex(r"\theta", font_size=22, color=TEXT_WHITE)
        label_a.next_to(dot_a, UP + RIGHT, buff=0.15)

        # Object B on orbit (rotated)
        angle_b = 120 * DEGREES
        pos_b = 1.5 * (math.cos(angle_b) * RIGHT + math.sin(angle_b) * UP)
        dot_b = Dot(pos_b, color=ACCENT_CYAN, radius=0.15)
        label_b = MathTex(r"\theta + \alpha", font_size=22, color=TEXT_WHITE)
        label_b.next_to(dot_b, UP + LEFT, buff=0.15)

        # Curved arrow indicating rotation
        arc_arrow = Arrow(
            pos_a,
            pos_b,
            color=ACCENT_GOLD,
            stroke_width=3,
            path_arc=90 * DEGREES,
        )

        self.play(FadeIn(center), FadeIn(orbit), run_time=0.5)
        self.play(FadeIn(dot_a), FadeIn(label_a), run_time=0.5)
        self.wait(0.3 * ws)
        self.play(GrowArrow(arc_arrow), run_time=0.8)
        self.play(FadeIn(dot_b), FadeIn(label_b), run_time=0.5)
        self.wait(0.5 * ws)

        same = Text(
            "物理法則は同じ",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        same.shift(UP * 2.8)
        self.play(FadeIn(same), run_time=0.5)
        self.wait(0.8 * ws)

        result_box = _make_box("角運動量が保存される", color=ACCENT_PINK, font_size=26)
        result_box.shift(DOWN * 2.0)
        self.play(FadeIn(result_box), run_time=0.8)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: theorem — summary of all 3 correspondences
    # -------------------------------------------------------------------
    def build_theorem(self):
        dur = self._duration
        anim_time = 8.0
        default_wait_total = 7.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "ネーターの定理",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        subtitle = Text(
            "連続対称性と保存則の一対一対応",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(subtitle), run_time=0.5)
        self.wait(0.5 * ws)

        # Left column: symmetries
        sym_labels = ["空間の並進対称性", "時間の対称性", "回転対称性"]
        # Right column: conservation laws
        law_labels = ["運動量保存", "エネルギー保存", "角運動量保存"]

        left_boxes = VGroup()
        right_boxes = VGroup()
        arrows = VGroup()

        y_positions = [1.0, -0.2, -1.4]

        for _i, (sym, law, y) in enumerate(zip(sym_labels, law_labels, y_positions, strict=False)):
            # Symmetry box (left)
            s_box = _make_box(sym, width=3.2, height=0.65, color=ACCENT_CYAN, font_size=22)
            s_box.move_to(LEFT * 3.0 + UP * y)
            left_boxes.add(s_box)

            # Law box (right)
            l_box = _make_box(law, width=3.0, height=0.65, color=ACCENT_PINK, font_size=22)
            l_box.move_to(RIGHT * 3.0 + UP * y)
            right_boxes.add(l_box)

            # Connecting arrow
            arr = Arrow(
                s_box.get_right() + RIGHT * 0.05,
                l_box.get_left() + LEFT * 0.05,
                color=ACCENT_GOLD,
                stroke_width=3,
                buff=0.05,
            )
            arrows.add(arr)

        # Animate row by row
        for i in range(3):
            self.play(FadeIn(left_boxes[i]), run_time=0.5)
            self.play(GrowArrow(arrows[i]), run_time=0.4)
            self.play(FadeIn(right_boxes[i]), run_time=0.5)
            self.wait(0.5 * ws)

        self.wait(1.0 * ws)

        # Bottom note
        note = Text(
            "保存則は仮定ではなく、対称性の帰結である",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to(DOWN * 2.0)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(2.0 * ws)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "spatial": {"people": [], "years": []},
    "temporal": {"people": [], "years": []},
    "rotational": {"people": [], "years": []},
    "theorem": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
SCENES = {
    "spatial": SymmetryConservation,
    "temporal": SymmetryConservation,
    "rotational": SymmetryConservation,
    "theorem": SymmetryConservation,
}
