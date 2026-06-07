"""
imitation_game.py - Turing test (imitation game) visualization for 数学史記

Visualizes the original imitation game setup and the machine substitution.

Modes:
    original - Three-participant setup: Interrogator C, Man A, Woman B
               communicating via text only
    machine  - Variation: Man A replaced by a machine, same interrogator C

Params:
    mode: "original" or "machine" (default: "original")
    duration: target duration in seconds

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    UP,
    Arrow,
    DashedLine,
    FadeIn,
    RoundedRectangle,
    Scene,
    Text,
    Transform,
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
    load_params,
)

config.background_color = BG_COLOR

PERSON_A_COLOR = ACCENT_CYAN
PERSON_B_COLOR = ACCENT_PINK
JUDGE_COLOR = ACCENT_GOLD
MACHINE_COLOR = "#7b61ff"  # purple for machine


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _make_person_box(label, sublabel, color, pos, is_machine=False):
    """Create a labeled box representing a participant."""
    if is_machine:
        box = RoundedRectangle(
            width=2.4,
            height=1.6,
            corner_radius=0.2,
            stroke_color=color,
            stroke_width=3,
            fill_color=color,
            fill_opacity=0.1,
        ).move_to(pos)
    else:
        box = RoundedRectangle(
            width=2.4,
            height=1.6,
            corner_radius=0.2,
            stroke_color=color,
            stroke_width=2,
        ).move_to(pos)
    name = Text(label, font=FONT, font_size=28, color=color)
    name.move_to([pos[0], pos[1] + 0.2, 0])
    role = Text(sublabel, font=FONT, font_size=18, color=TEXT_DIM)
    role.move_to([pos[0], pos[1] - 0.3, 0])
    return VGroup(box, name, role)


class ImitationGame(Scene):
    """Turing's imitation game (Turing test) visualization."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "original")
        self._duration = params.get("duration", 30)

        if mode == "machine":
            self._build_machine()
        else:
            self._build_original()

    # ------------------------------------------------------------------
    # Mode: original — man/woman/interrogator
    # ------------------------------------------------------------------
    def _build_original(self):
        duration = self._duration

        title = Text(
            "模倣ゲーム (1950)",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)
        subtitle = Text(
            "元の構成: 男 / 女 / 審問者",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).next_to(title, DOWN, buff=0.15)

        anim_time = 5.0
        default_wait_total = 8.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)
        self.wait(0.6 * ws)

        # Three participants
        # Interrogator C at bottom center
        # A (man) top left, B (woman) top right
        # Wall/screen separating them

        person_a = _make_person_box("A", "男性", PERSON_A_COLOR, [-3, 1.0, 0])
        person_b = _make_person_box("B", "女性", PERSON_B_COLOR, [3, 1.0, 0])
        judge_c = _make_person_box("C", "審問者", JUDGE_COLOR, [0, -1.8, 0])

        # Wall
        wall = DashedLine(
            start=[-5.5, -0.3, 0],
            end=[5.5, -0.3, 0],
            color=TEXT_DIM,
            dash_length=0.15,
        )
        wall_label = Text(
            "テキストのみで対話",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        ).next_to(wall, DOWN, buff=0.05)

        self.play(
            FadeIn(person_a),
            FadeIn(person_b),
            FadeIn(judge_c),
            run_time=0.8,
        )
        self.play(FadeIn(wall), FadeIn(wall_label), run_time=0.5)
        self.wait(0.8 * ws)

        # Arrows: C sends questions to both
        arrow_ca = Arrow(
            start=[-0.8, -1.0, 0],
            end=[-2.2, 0.2, 0],
            color=JUDGE_COLOR,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_cb = Arrow(
            start=[0.8, -1.0, 0],
            end=[2.2, 0.2, 0],
            color=JUDGE_COLOR,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(FadeIn(arrow_ca), FadeIn(arrow_cb), run_time=0.5)
        self.wait(0.6 * ws)

        # Role labels
        role_a = Text(
            "欺く",
            font=FONT,
            font_size=18,
            color=PERSON_A_COLOR,
        ).next_to(person_a, DOWN, buff=0.15)
        role_b = Text(
            "助ける",
            font=FONT,
            font_size=18,
            color=PERSON_B_COLOR,
        ).next_to(person_b, DOWN, buff=0.15)
        role_c = Text(
            "どちらが男性か当てる",
            font=FONT,
            font_size=18,
            color=JUDGE_COLOR,
        ).next_to(judge_c, DOWN, buff=0.15)

        self.play(
            FadeIn(role_a),
            FadeIn(role_b),
            FadeIn(role_c),
            run_time=0.5,
        )
        self.wait(max(duration - 5.5, 2.0))

    # ------------------------------------------------------------------
    # Mode: machine — A replaced by machine
    # ------------------------------------------------------------------
    def _build_machine(self):
        duration = self._duration

        title = Text(
            "チューリングテスト",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)
        subtitle = Text(
            "A を機械に置き換える",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).next_to(title, DOWN, buff=0.15)

        anim_time = 6.0
        default_wait_total = 10.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)
        self.wait(0.6 * ws)

        # First show original A (man), then transform to machine
        person_a = _make_person_box("A", "男性", PERSON_A_COLOR, [-3, 1.0, 0])
        person_b = _make_person_box("B", "女性", PERSON_B_COLOR, [3, 1.0, 0])
        judge_c = _make_person_box("C", "審問者", JUDGE_COLOR, [0, -1.8, 0])

        wall = DashedLine(
            start=[-5.5, -0.3, 0],
            end=[5.5, -0.3, 0],
            color=TEXT_DIM,
            dash_length=0.15,
        )

        arrow_ca = Arrow(
            start=[-0.8, -1.0, 0],
            end=[-2.2, 0.2, 0],
            color=JUDGE_COLOR,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_cb = Arrow(
            start=[0.8, -1.0, 0],
            end=[2.2, 0.2, 0],
            color=JUDGE_COLOR,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )

        self.play(
            FadeIn(person_a),
            FadeIn(person_b),
            FadeIn(judge_c),
            FadeIn(wall),
            FadeIn(arrow_ca),
            FadeIn(arrow_cb),
            run_time=0.8,
        )
        self.wait(1.0 * ws)

        # Transform A into machine
        machine_a = _make_person_box(
            "A",
            "機械",
            MACHINE_COLOR,
            [-3, 1.0, 0],
            is_machine=True,
        )
        self.play(
            Transform(person_a, machine_a),
            run_time=1.0,
        )
        self.wait(1.0 * ws)

        # New role labels
        role_b = Text(
            "人間",
            font=FONT,
            font_size=18,
            color=PERSON_B_COLOR,
        ).next_to(person_b, DOWN, buff=0.15)
        role_c = Text(
            "区別できるか?",
            font=FONT,
            font_size=18,
            color=JUDGE_COLOR,
        ).next_to(judge_c, DOWN, buff=0.15)
        self.play(FadeIn(role_b), FadeIn(role_c), run_time=0.5)
        self.wait(0.8 * ws)

        # Key question
        question = Text(
            "区別できなければ、機械は「考えている」と言えるか",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        ).move_to([0, -2.0, 0])
        self.play(FadeIn(question), run_time=0.5)
        self.wait(max(duration - 7.0, 2.0))


# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "original": {"people": [], "years": ["1950"]},
    "machine": {"people": [], "years": []},
}


SCENES = {
    "original": ImitationGame,
    "machine": ImitationGame,
}
