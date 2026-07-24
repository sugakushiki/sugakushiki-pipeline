"""
polygon_squeeze.py - Archimedes' method of exhaustion for pi approximation

Visualizes inscribed and circumscribed regular polygons squeezing a circle
to approximate pi. The core visual of Episode 005 (Archimedes).

Modes:
    buildup   - Animate polygon progression n=6,12,24,48,96 with running
                upper/lower bounds converging toward pi
    compare   - Show inscribed vs circumscribed side by side for a given n
    final     - Static display of the 96-gon result with bounds

Duration-aware: reads target duration from _manim_params.json and adapts
wait times and number of steps shown.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    WHITE,
    Circle,
    Create,
    FadeIn,
    MathTex,
    RegularPolygon,
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
# Math helpers
# ---------------------------------------------------------------------------


def inscribed_perimeter(n):
    """Perimeter of regular n-gon inscribed in unit circle (diameter=2)."""
    return 2 * n * math.sin(math.pi / n)


def circumscribed_perimeter(n):
    """Perimeter of regular n-gon circumscribed around unit circle (diameter=2)."""
    return 2 * n * math.tan(math.pi / n)


def pi_lower(n):
    """Lower bound for pi from inscribed n-gon (perimeter / diameter)."""
    return inscribed_perimeter(n) / 2


def pi_upper(n):
    """Upper bound for pi from circumscribed n-gon (perimeter / diameter)."""
    return circumscribed_perimeter(n) / 2


# Archimedes' progression: 6 -> 12 -> 24 -> 48 -> 96
ARCHIMEDES_STEPS = [6, 12, 24, 48, 96]


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


class PolygonSqueezeBuildup(Scene):
    """Animate the progression from hexagon to 96-gon."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 30)

        # ── Layout ──
        # Circle + polygons on the left, bounds display on the right
        circle_center = LEFT * 2.2
        circle_radius = 2.0

        # Unit circle
        circle = Circle(radius=circle_radius, color=WHITE, stroke_width=2)
        circle.move_to(circle_center)

        # Title
        title = Text("取り尽くし法", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to(UP * 3.0 + LEFT * 2.2)

        self.play(FadeIn(title), Create(circle), run_time=1.0)

        # ── Bounds display (right side) ──
        bounds_x = 2.8

        header_lower = Text("下界", font=FONT, font_size=22, color=ACCENT_CYAN)
        header_lower.move_to(RIGHT * bounds_x + UP * 2.5)

        header_upper = Text("上界", font=FONT, font_size=22, color=ACCENT_PINK)
        header_upper.move_to(RIGHT * bounds_x + UP * 1.0)

        pi_label = MathTex(r"\pi = 3.14159\ldots", font_size=28, color=ACCENT_GOLD)
        pi_label.move_to(RIGHT * bounds_x + DOWN * 1.0)

        self.play(FadeIn(header_lower), FadeIn(header_upper), FadeIn(pi_label), run_time=0.8)

        # ── Time allocation ──
        intro_time = 2.0
        remaining = max(duration - intro_time - 3.0, 10.0)
        time_per_step = remaining / len(ARCHIMEDES_STEPS)
        wait_time = max(time_per_step - 2.5, 0.5)

        # ── Polygon progression ──
        prev_inscribed = None
        prev_circumscribed = None
        prev_lower_tex = None
        prev_upper_tex = None
        prev_n_label = None

        for _i, n in enumerate(ARCHIMEDES_STEPS):
            # Inscribed polygon (cyan)
            inscribed = RegularPolygon(n=n, color=ACCENT_CYAN, stroke_width=2.5)
            inscribed.scale(circle_radius)
            inscribed.move_to(circle_center)

            # Circumscribed polygon (pink)
            # Scale: circumscribed radius = r / cos(pi/n)
            circum_scale = circle_radius / math.cos(math.pi / n)
            circumscribed = RegularPolygon(n=n, color=ACCENT_PINK, stroke_width=2.5)
            circumscribed.scale(circum_scale)
            circumscribed.move_to(circle_center)

            # N-gon label
            n_label = Text(f"{n}", font=FONT, font_size=32, color=TEXT_WHITE)
            n_label.move_to(circle_center + DOWN * 1.8)
            n_suffix = Text("-gon", font=FONT, font_size=22, color=TEXT_DIM)
            n_suffix.next_to(n_label, RIGHT, buff=0.1)
            n_group = VGroup(n_label, n_suffix)

            # Bounds values
            lower = pi_lower(n)
            upper = pi_upper(n)
            lower_str = f"{lower:.4f}"
            upper_str = f"{upper:.4f}"

            lower_tex = MathTex(lower_str, font_size=30, color=ACCENT_CYAN)
            lower_tex.move_to(RIGHT * bounds_x + UP * 2.0)

            upper_tex = MathTex(upper_str, font_size=30, color=ACCENT_PINK)
            upper_tex.move_to(RIGHT * bounds_x + UP * 0.5)

            # Animate
            if prev_inscribed is None:
                self.play(
                    Create(inscribed),
                    Create(circumscribed),
                    FadeIn(n_group),
                    FadeIn(lower_tex),
                    FadeIn(upper_tex),
                    run_time=1.5,
                )
            else:
                self.play(
                    ReplacementTransform(prev_inscribed, inscribed),
                    ReplacementTransform(prev_circumscribed, circumscribed),
                    ReplacementTransform(prev_n_label, n_group),
                    ReplacementTransform(prev_lower_tex, lower_tex),
                    ReplacementTransform(prev_upper_tex, upper_tex),
                    run_time=1.2,
                )

            self.wait(wait_time)

            prev_inscribed = inscribed
            prev_circumscribed = circumscribed
            prev_lower_tex = lower_tex
            prev_upper_tex = upper_tex
            prev_n_label = n_group

        # ── Final highlight: Archimedes' result ──
        result_lower = MathTex(r"3\tfrac{10}{71}", font_size=34, color=ACCENT_CYAN)
        result_upper = MathTex(r"3\tfrac{1}{7}", font_size=34, color=ACCENT_PINK)
        lt_pi = MathTex(r"< \pi <", font_size=34, color=ACCENT_GOLD)

        result_group = VGroup(result_lower, lt_pi, result_upper)
        result_group.arrange(RIGHT, buff=0.25)
        result_group.move_to(RIGHT * bounds_x + DOWN * 1.5)

        self.play(FadeIn(result_group), run_time=1.0)
        # Hold final state long enough to cover any audio duration.
        # visual_generator truncates to audio length; without FadeOut the
        # last frame stays on the polygon/bounds rather than going black.
        self.wait(20.0)


class PolygonSqueezeCompare(Scene):
    """Show inscribed vs circumscribed side by side for a single n."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        n = params.get("n", 12)
        duration = params.get("duration", 15)

        # Two circles side by side
        left_center = LEFT * 3.0
        right_center = RIGHT * 3.0
        radius = 1.8

        # Left: inscribed
        circle_l = Circle(radius=radius, color=WHITE, stroke_width=2)
        circle_l.move_to(left_center)
        inscribed = RegularPolygon(n=n, color=ACCENT_CYAN, stroke_width=2.5)
        inscribed.scale(radius)
        inscribed.move_to(left_center)

        label_l = Text("内接", font=FONT, font_size=22, color=ACCENT_CYAN)
        label_l.move_to(left_center + DOWN * 1.6)

        lower = pi_lower(n)
        val_l = MathTex(f"{lower:.4f}", font_size=28, color=ACCENT_CYAN)
        val_l.next_to(label_l, DOWN, buff=0.15)

        # Right: circumscribed
        circle_r = Circle(radius=radius, color=WHITE, stroke_width=2)
        circle_r.move_to(right_center)
        circum_scale = radius / math.cos(math.pi / n)
        circumscribed = RegularPolygon(n=n, color=ACCENT_PINK, stroke_width=2.5)
        circumscribed.scale(circum_scale)
        circumscribed.move_to(right_center)

        label_r = Text("外接", font=FONT, font_size=22, color=ACCENT_PINK)
        label_r.move_to(right_center + DOWN * 1.6)

        upper = pi_upper(n)
        val_r = MathTex(f"{upper:.4f}", font_size=28, color=ACCENT_PINK)
        val_r.next_to(label_r, DOWN, buff=0.15)

        # Center: pi
        pi_tex = MathTex(r"\pi", font_size=42, color=ACCENT_GOLD)
        pi_tex.move_to(UP * 3.0)

        n_tex = Text(f"{n}-gon", font=FONT, font_size=26, color=TEXT_WHITE)
        n_tex.move_to(UP * 2.3)

        self.play(
            FadeIn(pi_tex),
            FadeIn(n_tex),
            Create(circle_l),
            Create(inscribed),
            FadeIn(label_l),
            FadeIn(val_l),
            Create(circle_r),
            Create(circumscribed),
            FadeIn(label_r),
            FadeIn(val_r),
            run_time=2.0,
        )

        wait = max(duration - 4.0, 3.0)
        self.wait(wait)

        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class PolygonSqueezeFinal(Scene):
    """Static display of the 96-gon result."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 12)

        # Circle with 96-gon (visually near-circle)
        center = LEFT * 2.0
        radius = 2.0

        circle = Circle(radius=radius, color=WHITE, stroke_width=2)
        circle.move_to(center)

        poly = RegularPolygon(n=96, color=ACCENT_CYAN, stroke_width=2)
        poly.scale(radius)
        poly.move_to(center)

        label_96 = Text("96-gon", font=FONT, font_size=24, color=TEXT_DIM)
        label_96.move_to(center + DOWN * 1.8)

        # Result
        result_lower = MathTex(r"3\tfrac{10}{71}", font_size=36, color=ACCENT_CYAN)
        lt_pi = MathTex(r"< \pi <", font_size=36, color=ACCENT_GOLD)
        result_upper = MathTex(r"3\tfrac{1}{7}", font_size=36, color=ACCENT_PINK)

        result_group = VGroup(result_lower, lt_pi, result_upper)
        result_group.arrange(RIGHT, buff=0.3)
        result_group.move_to(RIGHT * 3.0 + UP * 1.0)

        # Decimal
        decimal = MathTex(r"3.1408 < \pi < 3.1429", font_size=28, color=TEXT_DIM)
        decimal.move_to(RIGHT * 3.0 + DOWN * 0.3)

        self.play(
            Create(circle),
            Create(poly),
            FadeIn(label_96),
            run_time=1.5,
        )
        self.play(FadeIn(result_group), run_time=1.0)
        self.play(FadeIn(decimal), run_time=0.8)

        wait = max(duration - 5.0, 3.0)
        self.wait(wait)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "buildup": {"people": [], "years": []},
    "compare": {"people": [], "years": []},
    "final": {"people": [], "years": []},
}


# End FadeOut removed: leaves the last frame visible for FFmpeg
# to pad when audio exceeds animation length. Scene transitions
# are handled at video_assembler time, not inside Manim.


# =========================================================
# Entry point for pipeline (mode dispatch)
# =========================================================
SCENES = {
    "buildup": PolygonSqueezeBuildup,
    "compare": PolygonSqueezeCompare,
    "final": PolygonSqueezeFinal,
}
