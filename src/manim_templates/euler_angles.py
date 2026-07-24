"""
euler_angles.py - Euler angles for rigid body orientation (数学史記)

Visualizes Euler's 1775 result (Formulae generales pro translatione
quacunque corporum rigidorum, E478): any orientation of a rigid body
in 3D space can be described by three angles α, β, γ. The convention
shown here is the z-x-z (proper Euler) rotation sequence.

A slender rectangular body serves as the rigid object; three sequential
rotations demonstrate how arbitrary orientations are achieved.

Modes:
    rotate_z   - First rotation: α around the world z-axis.
                 Fixed params: α = 60°, other angles held at 0°.
    rotate_x   - Second rotation: β around the x-axis
                 (α pre-applied). Fixed params: α = 60°, β = 45°.
    rotate_z2  - Third rotation: γ around the z-axis
                 (α and β pre-applied).
                 Fixed params: α = 60°, β = 45°, γ = 30°.
    combined   - Full sequence α → β → γ animated continuously.
                 Fixed params: α = 60°, β = 45°, γ = 30°.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 019 (Euler applied), math pillar 2a (rigid body).
"""

from manim import (
    DEGREES,
    DOWN,
    ORIGIN,
    OUT,
    RIGHT,
    UP,
    MathTex,
    Prism,
    Rotate,
    Text,
    ThreeDAxes,
    ThreeDScene,
    config,
)
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    ACCENT_PINK,
    BG_COLOR,
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class EulerAngles(ThreeDScene):
    """Euler angles z-x-z rotation of a rigid body. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 25)
        params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "rotate_z")

        # --- Camera setup: 3/4 overhead view ---
        self.set_camera_orientation(
            phi=68 * DEGREES,
            theta=-50 * DEGREES,
            zoom=0.95,
        )

        # --- 3D axes ---
        axes = ThreeDAxes(
            x_range=[-2.5, 2.5, 1],
            y_range=[-2.5, 2.5, 1],
            z_range=[-2.0, 2.0, 1],
            x_length=5,
            y_length=5,
            z_length=4,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_ticks": False,
                "include_tip": True,
            },
        )
        x_label = MathTex("x", font_size=32, color=ACCENT_PINK)
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.12)
        y_label = MathTex("y", font_size=32, color=ACCENT_PINK)
        y_label.next_to(axes.y_axis.get_end(), UP, buff=0.12)
        z_label = MathTex("z", font_size=32, color=ACCENT_PINK)
        z_label.next_to(axes.z_axis.get_end(), OUT, buff=0.12)

        # --- Rigid body: slender cuboid along the x-axis ---
        body = Prism(dimensions=[2.4, 0.6, 0.4])
        body.set_fill(ACCENT_CYAN, opacity=0.55)
        body.set_stroke(TEXT_WHITE, width=1.5)

        self.add(axes, x_label, y_label, z_label, body)

        # --- 2D overlays (fixed-in-frame) ---
        title_str, sub_str = {
            "rotate_z": ("オイラー角：第1回転 α", "z 軸まわりに α だけ回す"),
            "rotate_x": ("オイラー角：第2回転 β", "α 適用後、x 軸まわりに β"),
            "rotate_z2": ("オイラー角：第3回転 γ", "α,β 適用後、z 軸まわりに γ"),
            "combined": ("3つの角度で任意の姿勢", "α → β → γ の順に合成"),
        }.get(mode, ("", ""))

        title = Text(title_str, font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        subtitle = Text(sub_str, font=FONT, font_size=20, color=TEXT_DIM)
        subtitle.next_to(title, DOWN, buff=0.15)

        # Angle readout at lower-right (fixed-in-frame)
        angle_readout = MathTex(
            r"\alpha = 0^\circ, \ \beta = 0^\circ, \ \gamma = 0^\circ",
            font_size=26,
            color=ACCENT_GOLD,
        )
        angle_readout.move_to([3.5, -1.75, 0])

        self.add_fixed_in_frame_mobjects(title, subtitle, angle_readout)

        # --- Rotation parameters ---
        ALPHA = 60 * DEGREES
        BETA = 45 * DEGREES
        GAMMA = 30 * DEGREES

        def make_readout(a_deg, b_deg, g_deg):
            m = MathTex(
                rf"\alpha = {a_deg}^\circ, \ \beta = {b_deg}^\circ, \ \gamma = {g_deg}^\circ",
                font_size=26,
                color=ACCENT_GOLD,
            )
            m.move_to([3.5, -1.75, 0])
            return m

        # --- Pre-apply earlier rotations (static) for later-stage modes ---
        if mode == "rotate_x":
            body.rotate(ALPHA, axis=OUT, about_point=ORIGIN)
            self.remove(angle_readout)
            angle_readout = make_readout(60, 0, 0)
            self.add_fixed_in_frame_mobjects(angle_readout)
        elif mode == "rotate_z2":
            body.rotate(ALPHA, axis=OUT, about_point=ORIGIN)
            body.rotate(BETA, axis=RIGHT, about_point=ORIGIN)
            self.remove(angle_readout)
            angle_readout = make_readout(60, 45, 0)
            self.add_fixed_in_frame_mobjects(angle_readout)

        self.wait(0.6)

        # --- Animate the featured rotation(s) ---
        if mode == "rotate_z":
            self.play(
                Rotate(body, angle=ALPHA, axis=OUT, about_point=ORIGIN),
                run_time=3.0,
            )
            new_readout = make_readout(60, 0, 0)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(new_readout)
        elif mode == "rotate_x":
            self.play(
                Rotate(body, angle=BETA, axis=RIGHT, about_point=ORIGIN),
                run_time=3.0,
            )
            new_readout = make_readout(60, 45, 0)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(new_readout)
        elif mode == "rotate_z2":
            self.play(
                Rotate(body, angle=GAMMA, axis=OUT, about_point=ORIGIN),
                run_time=3.0,
            )
            new_readout = make_readout(60, 45, 30)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(new_readout)
        else:  # combined
            self.play(
                Rotate(body, angle=ALPHA, axis=OUT, about_point=ORIGIN),
                run_time=1.5,
            )
            mid1 = make_readout(60, 0, 0)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(mid1)
            angle_readout = mid1
            self.wait(0.3)

            self.play(
                Rotate(body, angle=BETA, axis=RIGHT, about_point=ORIGIN),
                run_time=1.5,
            )
            mid2 = make_readout(60, 45, 0)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(mid2)
            angle_readout = mid2
            self.wait(0.3)

            self.play(
                Rotate(body, angle=GAMMA, axis=OUT, about_point=ORIGIN),
                run_time=1.5,
            )
            final = make_readout(60, 45, 30)
            self.remove(angle_readout)
            self.add_fixed_in_frame_mobjects(final)

        # Hold the final pose
        used = {
            "rotate_z": 3.0 + 0.6,
            "rotate_x": 3.0 + 0.6,
            "rotate_z2": 3.0 + 0.6,
            "combined": 1.5 * 3 + 0.3 * 2 + 0.6,
        }.get(mode, 5.0)
        self.wait(max(1.0, duration - used))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "rotate_z": {"people": [], "years": []},
    "rotate_x": {"people": [], "years": []},
    "rotate_z2": {"people": [], "years": []},
    "combined": {"people": [], "years": []},
}


SCENES = {
    "rotate_z": {
        "class": "EulerAngles",
        "params": {"mode": "rotate_z"},
        "description": "First Euler rotation α around z-axis (slender body)",
    },
    "rotate_x": {
        "class": "EulerAngles",
        "params": {"mode": "rotate_x"},
        "description": "Second rotation β around x-axis (α pre-applied)",
    },
    "rotate_z2": {
        "class": "EulerAngles",
        "params": {"mode": "rotate_z2"},
        "description": "Third rotation γ around z-axis (α,β pre-applied)",
    },
    "combined": {
        "class": "EulerAngles",
        "params": {"mode": "combined"},
        "description": "Full α → β → γ sequence animated continuously",
    },
}
