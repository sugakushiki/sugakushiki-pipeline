"""
solvable_vs_unsolvable: 群の組成列（composition series）を視覚化し、可解群と非可解群の違いを示す。

モード:
- s3_chain: S₃の組成列 S₃ ⊃ A₃ ⊃ {e} を段階的に表示。各商群が巡回群であることを示す
- s5_chain: S₅の組成列 S₅ ⊃ A₅ で行き詰まるアニメーション。A₅が単純群で分解不可能なことを示す
- comparison: S₃（可解）とS₅（非可解）を左右に並べて対比する
"""

import numpy as np
from manim import *

BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
FONT = "BIZ UDMincho"
GREEN_OK = "#2ecc71"
RED_NG = "#e74c3c"

# Subtitle safe zone: y > -2.0 (Manim scene uses 240px bottom margin)
SUBTITLE_Y_LIMIT = -2.0


def get_duration(mode):
    defaults = {"s3_chain": 30, "s5_chain": 30, "comparison": 35}
    return defaults.get(mode, 30)


def make_group_box(
    label_tex, order_str, center, width=2.2, height=0.75, box_color=WHITE, label_color=WHITE
):
    box = RoundedRectangle(
        corner_radius=0.1,
        width=width,
        height=height,
        color=box_color,
        stroke_width=2.0,
        fill_color=box_color,
        fill_opacity=0.08,
    )
    box.move_to(center)
    label = MathTex(label_tex, font_size=36, color=label_color)
    label.move_to(center)
    order = MathTex(order_str, font_size=24, color=box_color).set_opacity(0.6)
    order.next_to(box, RIGHT, buff=0.18)
    return VGroup(box, label, order)


def make_quotient_arrow(start_center, end_center, quotient_tex, status="ok"):
    arrow = Arrow(
        start=start_center + DOWN * 0.38,
        end=end_center + UP * 0.38,
        buff=0.05,
        stroke_width=2.5,
        color=WHITE,
        max_tip_length_to_length_ratio=0.15,
    )
    q_label = MathTex(r"\div\;" + quotient_tex, font_size=26, color=WHITE).set_opacity(0.8)
    q_label.next_to(arrow, RIGHT, buff=0.18)
    if status == "ok":
        icon = MathTex(r"\checkmark", font_size=28, color=GREEN_OK)
    else:
        icon = MathTex(r"\times", font_size=28, color=RED_NG)
    icon.next_to(q_label, RIGHT, buff=0.12)
    return VGroup(arrow, q_label, icon)


class SolvableVsUnsolvableS3Chain(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("s3_chain")

        # Layout: shifted up to keep all above y=-2.0
        y_top, y_mid, y_bot = 2.2, 0.6, -1.0

        box_s3 = make_group_box(
            r"S_3", r"(6)", center=np.array([0, y_top, 0]), box_color=CYAN, label_color=CYAN
        )
        box_a3 = make_group_box(
            r"A_3", r"(3)", center=np.array([0, y_mid, 0]), box_color=GOLD, label_color=GOLD
        )
        box_e = make_group_box(
            r"\{e\}",
            r"(1)",
            center=np.array([0, y_bot, 0]),
            box_color=GREEN_OK,
            label_color=GREEN_OK,
        )

        arr1 = make_quotient_arrow(
            np.array([0, y_top, 0]), np.array([0, y_mid, 0]), r"\mathbb{Z}_2", "ok"
        )
        arr2 = make_quotient_arrow(
            np.array([0, y_mid, 0]), np.array([0, y_bot, 0]), r"\mathbb{Z}_3", "ok"
        )

        self.play(FadeIn(box_s3), run_time=0.6)
        self.wait(0.8)
        self.play(FadeIn(arr1), run_time=0.6)
        self.play(FadeIn(box_a3), run_time=0.6)
        self.wait(0.8)
        self.play(FadeIn(arr2), run_time=0.6)
        self.play(FadeIn(box_e), run_time=0.6)
        self.wait(0.5)

        # Result at y=-1.8 (above subtitle limit)
        result = MathTex(r"\checkmark", font_size=52, color=GREEN_OK)
        result.move_to(np.array([0, -1.8, 0]))
        self.play(FadeIn(result), run_time=0.5)

        elapsed = 0.6 + 0.8 + 0.6 + 0.6 + 0.8 + 0.6 + 0.6 + 0.5 + 0.5
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class SolvableVsUnsolvableS5Chain(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("s5_chain")

        # Layout: shifted up
        y_top, y_mid, y_blocked = 2.2, 0.6, -1.0

        box_s5 = make_group_box(
            r"S_5", r"(120)", center=np.array([0, y_top, 0]), box_color=CYAN, label_color=CYAN
        )
        box_a5 = make_group_box(
            r"A_5", r"(60)", center=np.array([0, y_mid, 0]), box_color=GOLD, label_color=GOLD
        )
        arr1 = make_quotient_arrow(
            np.array([0, y_top, 0]), np.array([0, y_mid, 0]), r"\mathbb{Z}_2", "ok"
        )

        self.play(FadeIn(box_s5), run_time=0.6)
        self.wait(0.5)
        self.play(FadeIn(arr1), run_time=0.6)
        self.play(FadeIn(box_a5), run_time=0.6)
        self.wait(0.8)

        # Blocked
        dashed_arrow = DashedLine(
            start=np.array([0, y_mid - 0.38, 0]),
            end=np.array([0, y_blocked + 0.2, 0]),
            color=RED_NG,
            stroke_width=2.5,
            dash_length=0.1,
        )
        self.play(FadeIn(dashed_arrow), run_time=0.5)

        cross = VGroup(
            Line(
                np.array([0, y_blocked, 0]) + UL * 0.25,
                np.array([0, y_blocked, 0]) + DR * 0.25,
                color=RED_NG,
                stroke_width=5,
            ),
            Line(
                np.array([0, y_blocked, 0]) + UR * 0.25,
                np.array([0, y_blocked, 0]) + DL * 0.25,
                color=RED_NG,
                stroke_width=5,
            ),
        )
        self.play(FadeIn(cross), run_time=0.5)

        # Result at y=-1.8
        result = MathTex(r"\times", font_size=52, color=RED_NG)
        result.move_to(np.array([0, -1.8, 0]))
        self.play(FadeIn(result), run_time=0.5)

        elapsed = 0.6 + 0.5 + 0.6 + 0.6 + 0.8 + 0.5 + 0.5 + 0.5
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class SolvableVsUnsolvableComparison(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("comparison")

        x_left, x_right = -3.5, 3.5
        # Shifted up: top=2.2, mid=0.8, bot=-0.6
        y_positions = [2.2, 0.8, -0.6]

        # Divider — only extends to y=-2.0
        divider = DashedLine(
            UP * 3.2, DOWN * 1.8, color=WHITE, stroke_opacity=0.2, dash_length=0.15
        )
        self.play(FadeIn(divider), run_time=0.3)

        # Left: S₃
        h_l = MathTex(r"S_3", font_size=44, color=GREEN_OK).move_to(np.array([x_left, 3.2, 0]))
        b_s3 = make_group_box(
            r"S_3",
            r"(6)",
            np.array([x_left, y_positions[0], 0]),
            width=1.8,
            height=0.6,
            box_color=CYAN,
            label_color=CYAN,
        )
        b_a3 = make_group_box(
            r"A_3",
            r"(3)",
            np.array([x_left, y_positions[1], 0]),
            width=1.8,
            height=0.6,
            box_color=GOLD,
            label_color=GOLD,
        )
        b_e = make_group_box(
            r"\{e\}",
            r"(1)",
            np.array([x_left, y_positions[2], 0]),
            width=1.8,
            height=0.6,
            box_color=GREEN_OK,
            label_color=GREEN_OK,
        )
        a_l1 = make_quotient_arrow(
            np.array([x_left, y_positions[0], 0]),
            np.array([x_left, y_positions[1], 0]),
            r"\mathbb{Z}_2",
            "ok",
        )
        a_l2 = make_quotient_arrow(
            np.array([x_left, y_positions[1], 0]),
            np.array([x_left, y_positions[2], 0]),
            r"\mathbb{Z}_3",
            "ok",
        )
        result_l = MathTex(r"\checkmark", font_size=48, color=GREEN_OK).move_to(
            np.array([x_left, -1.5, 0])
        )

        self.play(FadeIn(h_l), FadeIn(b_s3), run_time=0.5)
        self.play(FadeIn(a_l1), FadeIn(b_a3), run_time=0.5)
        self.play(FadeIn(a_l2), FadeIn(b_e), run_time=0.5)
        self.play(FadeIn(result_l), run_time=0.4)
        self.wait(0.3)

        # Right: S₅
        h_r = MathTex(r"S_5", font_size=44, color=RED_NG).move_to(np.array([x_right, 3.2, 0]))
        b_s5 = make_group_box(
            r"S_5",
            r"(120)",
            np.array([x_right, y_positions[0], 0]),
            width=1.8,
            height=0.6,
            box_color=CYAN,
            label_color=CYAN,
        )
        b_a5 = make_group_box(
            r"A_5",
            r"(60)",
            np.array([x_right, y_positions[1], 0]),
            width=1.8,
            height=0.6,
            box_color=GOLD,
            label_color=GOLD,
        )
        a_r1 = make_quotient_arrow(
            np.array([x_right, y_positions[0], 0]),
            np.array([x_right, y_positions[1], 0]),
            r"\mathbb{Z}_2",
            "ok",
        )

        blocked_x = VGroup(
            Line(
                np.array([x_right, y_positions[2], 0]) + UL * 0.25,
                np.array([x_right, y_positions[2], 0]) + DR * 0.25,
                color=RED_NG,
                stroke_width=5,
            ),
            Line(
                np.array([x_right, y_positions[2], 0]) + UR * 0.25,
                np.array([x_right, y_positions[2], 0]) + DL * 0.25,
                color=RED_NG,
                stroke_width=5,
            ),
        )
        result_r = MathTex(r"\times", font_size=48, color=RED_NG).move_to(
            np.array([x_right, -1.5, 0])
        )

        self.play(FadeIn(h_r), FadeIn(b_s5), run_time=0.5)
        self.play(FadeIn(a_r1), FadeIn(b_a5), run_time=0.5)
        self.play(FadeIn(blocked_x), run_time=0.5)
        self.play(FadeIn(result_r), run_time=0.4)
        self.wait(0.5)

        elapsed = 0.3 + 0.5 * 3 + 0.4 + 0.3 + 0.5 * 3 + 0.4 + 0.5
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "s3_chain": {"people": [], "years": []},
    "s5_chain": {"people": [], "years": []},
    "comparison": {"people": [], "years": []},
}

# End FadeOut removed: leaves the last frame visible for FFmpeg
# to pad when audio exceeds animation length. Scene transitions
# are handled at video_assembler time, not inside Manim.


SCENES = {
    "s3_chain": SolvableVsUnsolvableS3Chain,
    "s5_chain": SolvableVsUnsolvableS5Chain,
    "comparison": SolvableVsUnsolvableComparison,
}
