"""
quaternion_rotation.py - 3D rotation, non-commutativity and quaternions (数学史記)

Hamilton's quaternions describe rotations in 3D space. Three facts are shown:
    1. 3D rotations do NOT commute (order matters) - the heart of why
       Hamilton had to abandon the commutative law ab=ba.
    2. Euler angles suffer "gimbal lock": at a quarter-turn pitch two of the
       rotation axes line up and a degree of freedom is lost.
    3. A unit quaternion turns an object smoothly about a single axis,
       avoiding gimbal lock - the modern tool for 3D rotation.

A 3D scene with a slab body (gold-tipped at its +x end so its orientation
is readable) is rotated; 2D titles/labels are fixed in frame.

Modes:
    noncommutative - Two identical bodies. Left turns about x then z; right
                     turns about z then x (both quarter turns). The final
                     orientations differ. Fixed params: two 90-deg turns.
    gimbal_lock    - One body with three axis arrows (yaw=z, pitch=y,
                     roll=x). A 90-deg pitch lines the roll axis up with the
                     yaw axis; the two coincide and freedom is lost.
                     Fixed params: pitch = 90 deg.
    smooth         - One body turning a full 360 deg about a single fixed
                     tilted axis (1,1,1), continuously and smoothly.
                     Fixed params: 360 deg about axis (1,1,1).

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 033 (Hamilton), quaternion pillar (3D core).
"""

import numpy as np
from manim import (
    DEGREES,
    DOWN,
    ORIGIN,
    OUT,
    RIGHT,
    UP,
    Group,
    Line,
    Prism,
    Rotate,
    Text,
    ThreeDScene,
    config,
    linear,
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


def _make_body(color=ACCENT_CYAN, center=(0.0, 0.0, 0.0)):
    """A slender slab with a gold cube marker at its +x end, so the
    orientation stays readable. Returns a Group placed at `center`."""
    slab = Prism(dimensions=[1.7, 1.05, 0.35])
    slab.set_fill(color, opacity=0.5)
    slab.set_stroke(TEXT_WHITE, width=1.2)
    tip = Prism(dimensions=[0.32, 0.32, 0.32])
    tip.set_fill(ACCENT_GOLD, opacity=0.95)
    tip.set_stroke(TEXT_WHITE, width=1.0)
    tip.move_to([0.85, 0.0, 0.0])
    body = Group(slab, tip)
    body.shift(np.array(center))
    return body


class QuaternionRotation(ThreeDScene):
    """3D rotation / non-commutativity / quaternions. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 26)
        mode = params.get("mode", "noncommutative")

        self.set_camera_orientation(phi=66 * DEGREES, theta=-50 * DEGREES, zoom=0.95)

        if mode == "gimbal_lock":
            self.build_gimbal_lock()
        elif mode == "smooth":
            self.build_smooth()
        else:
            self.build_noncommutative()

    # ------------------------------------------------------------------
    # Mode: noncommutative
    # ------------------------------------------------------------------
    def build_noncommutative(self):
        duration = self._duration

        title = Text("三次元の回転は順序で変わる", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        left_label = Text("順序①  x軸 → z軸", font=FONT, font_size=22, color=ACCENT_CYAN)
        left_label.move_to([-3.3, 2.55, 0])
        right_label = Text("順序②  z軸 → x軸", font=FONT, font_size=22, color=ACCENT_GOLD)
        right_label.move_to([3.3, 2.55, 0])
        self.add_fixed_in_frame_mobjects(title, left_label, right_label)

        left = _make_body(color=ACCENT_CYAN, center=(-2.3, 0.0, 0.0))
        right = _make_body(color=ACCENT_CYAN, center=(2.3, 0.0, 0.0))
        lc = np.array([-2.3, 0.0, 0.0])
        rc = np.array([2.3, 0.0, 0.0])
        self.add(left, right)
        self.wait(0.6)

        # First turns: left about x, right about z
        self.play(
            Rotate(left, angle=90 * DEGREES, axis=RIGHT, about_point=lc),
            Rotate(right, angle=90 * DEGREES, axis=OUT, about_point=rc),
            run_time=2.2,
        )
        self.wait(0.4)
        # Second turns: left about z, right about x
        self.play(
            Rotate(left, angle=90 * DEGREES, axis=OUT, about_point=lc),
            Rotate(right, angle=90 * DEGREES, axis=RIGHT, about_point=rc),
            run_time=2.2,
        )

        note = Text("同じ二回の回転でも、向きが違う", font=FONT, font_size=24, color=ACCENT_PINK)
        note.move_to([0, -1.75, 0])
        self.add_fixed_in_frame_mobjects(note)

        used = 0.6 + 2.2 + 0.4 + 2.2
        self.wait(0.8)
        # Fill the remaining narration time by slowly turning BOTH final
        # orientations together, then settle and hold the final frame (余韻).
        remaining = duration - used - 0.8
        end_hold = 1.2
        if remaining > end_hold + 1.5:
            spin = remaining - end_hold
            turns = max(1, round(spin / 14.0))
            self.play(
                Rotate(left, angle=360 * DEGREES * turns, axis=UP, about_point=lc),
                Rotate(right, angle=360 * DEGREES * turns, axis=UP, about_point=rc),
                run_time=spin,
                rate_func=linear,
            )
            self.wait(end_hold)  # 余韻: hold the settled final comparison
        else:
            self.wait(max(0.5, remaining))

    # ------------------------------------------------------------------
    # Mode: gimbal_lock
    # ------------------------------------------------------------------
    def build_gimbal_lock(self):
        duration = self._duration

        title = Text("オイラー角のジンバルロック", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        body = _make_body(color=ACCENT_CYAN, center=(0.0, 0.0, 0.0))

        # Light Line axes (not Arrow3D: 3D cones are very slow to render over a
        # long continuous spin at 1080p and caused a render timeout -> placeholder).
        yaw = Line(ORIGIN, [0, 0, 1.9], color=ACCENT_PINK, stroke_width=6)  # z (yaw)
        pitch = Line(ORIGIN, [0, 1.9, 0], color=TEXT_DIM, stroke_width=6)  # y (pitch)
        roll = Line(ORIGIN, [1.9, 0, 0], color=ACCENT_GOLD, stroke_width=6)  # x (roll)
        self.add(body, yaw, pitch, roll)
        self.wait(0.6)

        # A 90-deg pitch about y carries the roll axis (+x) onto the yaw axis (+z)
        rolling = Group(body, roll)
        self.play(
            Rotate(rolling, angle=-90 * DEGREES, axis=UP, about_point=ORIGIN),
            run_time=2.6,
        )

        note1 = Text("ロール軸がヨー軸と重なった", font=FONT, font_size=24, color=ACCENT_PINK)
        note1.move_to([0, -1.45, 0])
        note2 = Text(
            "回転の自由がひとつ失われる ── ジンバルロック",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note2.move_to([0, -1.92, 0])
        self.add_fixed_in_frame_mobjects(note1, note2)

        used = 0.6 + 2.6
        self.wait(1.0)
        # Demonstrate the consequence of the lock: the only rotational freedom left
        # is a single spin about the merged (vertical) axis. Slowly turn the body
        # about it, then settle and hold the final frame (余韻).
        remaining = duration - used - 1.0
        end_hold = 1.2
        if remaining > end_hold + 1.5:
            spin = remaining - end_hold
            turns = max(1, round(spin / 14.0))
            self.play(
                Rotate(
                    Group(body, roll), angle=360 * DEGREES * turns, axis=OUT, about_point=ORIGIN
                ),
                run_time=spin,
                rate_func=linear,
            )
            self.wait(end_hold)  # 余韻: hold the settled locked state
        else:
            self.wait(max(0.5, remaining))

    # ------------------------------------------------------------------
    # Mode: smooth
    # ------------------------------------------------------------------
    def build_smooth(self):
        duration = self._duration

        title = Text("四元数による滑らかな回転", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        sub = Text("ひとつの軸まわりに連続して回る", font=FONT, font_size=22, color=TEXT_DIM)
        sub.next_to(title, DOWN, buff=0.15)
        self.add_fixed_in_frame_mobjects(title, sub)

        body = _make_body(color=ACCENT_CYAN, center=(0.0, 0.0, 0.0))
        axis_vec = np.array([1.0, 1.0, 1.0])
        axis_vec = axis_vec / np.linalg.norm(axis_vec)
        axis_arrow = Line(-1.9 * axis_vec, 1.9 * axis_vec, color=ACCENT_PINK, stroke_width=6)
        self.add(axis_arrow, body)
        self.wait(0.4)

        spin_time = max(4.0, duration - 1.4)
        self.play(
            Rotate(body, angle=360 * DEGREES, axis=axis_vec, about_point=ORIGIN),
            run_time=spin_time,
        )
        self.wait(max(0.6, duration - 0.4 - spin_time))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# No people/years displayed on screen (3D shapes + concept labels only).
LINT_FACTUAL_CLAIMS = {
    "noncommutative": {"people": [], "years": []},
    "gimbal_lock": {"people": [], "years": []},
    "smooth": {"people": [], "years": []},
}


SCENES = {
    "noncommutative": {
        "class": "QuaternionRotation",
        "params": {"mode": "noncommutative"},
        "description": "Two bodies: x-then-z vs z-then-x give different final orientations (non-commutative)",
    },
    "gimbal_lock": {
        "class": "QuaternionRotation",
        "params": {"mode": "gimbal_lock"},
        "description": "Euler-angle gimbal lock: a 90-deg pitch makes roll and yaw axes coincide",
    },
    "smooth": {
        "class": "QuaternionRotation",
        "params": {"mode": "smooth"},
        "description": "A unit quaternion turns a body smoothly 360 deg about a single tilted axis",
    },
}
