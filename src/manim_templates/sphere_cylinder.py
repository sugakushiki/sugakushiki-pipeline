"""
sphere_cylinder.py - Archimedes' sphere and cylinder volume relationship

Visualizes that the volume of a sphere is 2/3 that of its circumscribed
cylinder. Archimedes considered this his greatest achievement and requested
it be engraved on his tombstone.

Modes:
    reveal     - Show cylinder, then sphere appearing inside, then the 2:3
                 ratio with formula
    cross_section - 2D cross-section view showing the relationship
    tombstone  - Stylized sphere-in-cylinder diagram echoing the tombstone

Duration-aware: reads target duration from _manim_params.json.

Reads params from _manim_params.json in the same directory.
"""

from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Circle,
    Create,
    DashedLine,
    Ellipse,
    FadeIn,
    GrowFromCenter,
    Indicate,
    Line,
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
    load_params,
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_cylinder_2d(center, radius, height, color=ACCENT_PINK):
    """Create a 2D representation of a cylinder (front view with ellipses)."""
    cx, cy = center[0], center[1]
    half_h = height / 2

    # Side lines
    left_line = Line(
        start=[cx - radius, cy + half_h, 0],
        end=[cx - radius, cy - half_h, 0],
        color=color,
        stroke_width=2,
    )
    right_line = Line(
        start=[cx + radius, cy + half_h, 0],
        end=[cx + radius, cy - half_h, 0],
        color=color,
        stroke_width=2,
    )

    # Top ellipse (full)
    top_ellipse = Ellipse(width=radius * 2, height=radius * 0.5, color=color, stroke_width=2)
    top_ellipse.move_to([cx, cy + half_h, 0])

    # Bottom ellipse (dashed back, solid front)
    bottom_ellipse = Ellipse(width=radius * 2, height=radius * 0.5, color=color, stroke_width=2)
    bottom_ellipse.move_to([cx, cy - half_h, 0])

    return VGroup(left_line, right_line, top_ellipse, bottom_ellipse)


def create_sphere_2d(center, radius, color=ACCENT_CYAN):
    """Create a 2D representation of a sphere (circle + equator ellipse)."""
    cx, cy = center[0], center[1]

    outline = Circle(radius=radius, color=color, stroke_width=2.5)
    outline.move_to(center)

    # Equator ellipse for 3D effect
    equator = Ellipse(
        width=radius * 2, height=radius * 0.4, color=color, stroke_width=1.5, stroke_opacity=0.5
    )
    equator.move_to(center)

    return VGroup(outline, equator)


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


class SphereCylinderReveal(Scene):
    """Show cylinder, then sphere inside, then the volume ratio."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 25)

        center = LEFT * 1.5
        radius = 1.8
        height = radius * 2  # cylinder height = sphere diameter

        # ── Phase 1: Cylinder ──
        cylinder = create_cylinder_2d(center, radius, height, color=ACCENT_PINK)
        cyl_label = Text("外接円柱", font=FONT, font_size=22, color=ACCENT_PINK)
        cyl_label.move_to(center + DOWN * 1.8)

        self.play(Create(cylinder), FadeIn(cyl_label), run_time=1.5)
        self.wait(1.0)

        # ── Phase 2: Sphere inside ──
        sphere = create_sphere_2d(center, radius, color=ACCENT_CYAN)
        sph_label = Text("球", font=FONT, font_size=22, color=ACCENT_CYAN)
        sph_label.move_to(center + UP * 0.0)

        self.play(GrowFromCenter(sphere), FadeIn(sph_label), run_time=1.5)
        self.wait(1.0)

        # ── Phase 3: Radius annotation ──
        r_line = DashedLine(
            start=[center[0], center[1], 0],
            end=[center[0] + radius, center[1], 0],
            color=ACCENT_GOLD,
            stroke_width=2,
            dash_length=0.1,
        )
        r_label = MathTex("r", font_size=26, color=ACCENT_GOLD)
        r_label.next_to(r_line, UP, buff=0.1)

        self.play(Create(r_line), FadeIn(r_label), run_time=0.8)
        self.wait(0.5)

        # ── Phase 4: Volume formulas ──
        formulas_x = 3.2

        v_sphere_label = MathTex(r"V_{\text{sphere}}", font_size=28, color=ACCENT_CYAN)
        v_sphere_label.move_to(RIGHT * formulas_x + UP * 2.5)

        v_sphere = MathTex(r"= \frac{4}{3}\pi r^3", font_size=28, color=ACCENT_CYAN)
        v_sphere.next_to(v_sphere_label, RIGHT, buff=0.15)

        v_cyl_label = MathTex(r"V_{\text{cyl}}", font_size=28, color=ACCENT_PINK)
        v_cyl_label.move_to(RIGHT * formulas_x + UP * 1.5)

        v_cyl = MathTex(r"= 2\pi r^3", font_size=28, color=ACCENT_PINK)
        v_cyl.next_to(v_cyl_label, RIGHT, buff=0.15)

        self.play(
            FadeIn(v_sphere_label),
            FadeIn(v_sphere),
            run_time=1.0,
        )
        self.play(
            FadeIn(v_cyl_label),
            FadeIn(v_cyl),
            run_time=1.0,
        )
        self.wait(0.8)

        # ── Phase 5: The ratio ──
        ratio = MathTex(
            r"\frac{V_{\text{sphere}}}{V_{\text{cyl}}} = \frac{2}{3}",
            font_size=36,
            color=ACCENT_GOLD,
        )
        ratio.move_to(RIGHT * 3.5 + DOWN * 0.3)

        self.play(FadeIn(ratio), run_time=1.0)
        self.play(Indicate(ratio, color=ACCENT_GOLD, scale_factor=1.15), run_time=0.8)

        # ── Phase 6: Tombstone note ──
        note = Text("-- 墓碑に刻むよう遺言した --", font=FONT, font_size=18, color=TEXT_DIM)
        note.move_to(RIGHT * 3.5 + DOWN * 1.5)

        self.play(FadeIn(note), run_time=0.8)

        wait = max(duration - 11.0, 2.0)
        self.wait(wait)

        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class SphereCylinderCrossSection(Scene):
    """2D cross-section view emphasizing the geometric relationship."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 18)

        center = ORIGIN
        radius = 2.0
        half_h = radius  # height = 2r, so half = r

        # Rectangle (cylinder cross section)
        rect = Rectangle(
            width=radius * 2,
            height=radius * 2,
            color=ACCENT_PINK,
            stroke_width=2.5,
        )
        rect.move_to(center)

        # Circle (sphere cross section)
        circle = Circle(radius=radius, color=ACCENT_CYAN, stroke_width=2.5)
        circle.move_to(center)

        # Radius line
        r_line = DashedLine(
            start=center,
            end=[center[0] + radius, center[1], 0],
            color=ACCENT_GOLD,
            stroke_width=2,
            dash_length=0.1,
        )
        r_label = MathTex("r", font_size=28, color=ACCENT_GOLD)
        r_label.next_to(r_line, UP, buff=0.1)

        # Height annotation
        h_line = DashedLine(
            start=[center[0] + radius + 0.5, center[1] + half_h, 0],
            end=[center[0] + radius + 0.5, center[1] - half_h, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
            dash_length=0.1,
        )
        h_label = MathTex("2r", font_size=24, color=TEXT_DIM)
        h_label.next_to(h_line, RIGHT, buff=0.1)

        # Labels
        rect_label = Text("円柱断面", font=FONT, font_size=20, color=ACCENT_PINK)
        rect_label.move_to(UP * 3.0 + LEFT * 3.0)

        circle_label = Text("球断面", font=FONT, font_size=20, color=ACCENT_CYAN)
        circle_label.move_to(UP * 3.0 + RIGHT * 3.0)

        self.play(
            Create(rect),
            FadeIn(rect_label),
            run_time=1.2,
        )
        self.play(
            Create(circle),
            FadeIn(circle_label),
            run_time=1.2,
        )
        self.play(
            Create(r_line),
            FadeIn(r_label),
            Create(h_line),
            FadeIn(h_label),
            run_time=1.0,
        )

        # Area ratio text
        area_text = MathTex(
            r"\frac{\text{circle area}}{\text{square area}} = "
            r"\frac{\pi r^2}{(2r)^2} = \frac{\pi}{4}",
            font_size=26,
            color=ACCENT_GOLD,
        )
        area_text.move_to(DOWN * 1.8)

        self.play(FadeIn(area_text), run_time=1.0)

        wait = max(duration - 6.0, 2.0)
        self.wait(wait)

        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class SphereCylinderTombstone(Scene):
    """Stylized diagram of sphere inscribed in cylinder, evoking the tombstone."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 15)

        center = ORIGIN
        radius = 2.0

        # Cylinder outline
        cylinder = create_cylinder_2d(center, radius, radius * 2, color=TEXT_DIM)
        cylinder.set_stroke(opacity=0.6)

        # Sphere
        sphere = create_sphere_2d(center, radius, color=ACCENT_GOLD)
        sphere.set_stroke(width=3)

        # The ratio, prominent
        ratio = MathTex(r"\frac{2}{3}", font_size=72, color=ACCENT_GOLD)
        ratio.move_to(DOWN * 1.8)

        self.play(
            Create(cylinder),
            run_time=1.5,
        )
        self.play(
            GrowFromCenter(sphere),
            run_time=1.5,
        )
        self.play(
            FadeIn(ratio),
            run_time=1.0,
        )

        wait = max(duration - 5.0, 2.0)
        self.wait(wait)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "reveal": {"people": [], "years": []},
    "cross_section": {"people": [], "years": []},
    "tombstone": {"people": [], "years": []},
}


        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


# =========================================================
# Entry point for pipeline (mode dispatch)
# =========================================================
SCENES = {
    "reveal": SphereCylinderReveal,
    "cross_section": SphereCylinderCrossSection,
    "tombstone": SphereCylinderTombstone,
}
