"""
infinite_descent.py - Infinite descent proof visualization for 数学史記

Visualizes Fermat's method of infinite descent, the only complete proof
Fermat left behind: x⁴ + y⁴ = z² has no positive integer solutions.

Modes:
    staircase   - Intuitive visualization of the descent principle.
                  If a solution exists → a smaller solution exists →
                  even smaller → ... → contradiction (positive integers
                  cannot decrease forever).
                  Fixed params: 4 descent steps shown.
    pythagorean - Skeleton of the x⁴+y⁴=z² proof.
                  Shows how Pythagorean triple theory produces
                  a smaller z' < z at each step, leading to contradiction.
                  Fixed params: schematic (no specific numbers).

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 014 (Fermat), math pillar 2
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    Arrow,
    FadeIn,
    Line,
    MathTex,
    Scene,
    SurroundingRectangle,
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


class InfiniteDescent(Scene):
    """Infinite descent visualization. Mode-branching scene.

    Modes:
        staircase (default) - intuitive descending staircase diagram
        pythagorean         - x⁴+y⁴=z² proof skeleton
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "staircase")

        if mode == "pythagorean":
            self.build_pythagorean()
        else:
            self.build_staircase()

    # -------------------------------------------------------------------
    # Mode: staircase
    # -------------------------------------------------------------------
    def build_staircase(self):
        """Descending staircase showing the logic of infinite descent.

        Step 1: Assume a solution (x, y, z) exists
        Step 2: From it, derive a smaller solution (x', y', z') with z' < z
        Step 3: From that, derive an even smaller one...
        Step 4: But positive integers can't decrease forever → contradiction!
        """
        duration = self._duration
        highlight = self._highlight_color

        # Title
        title = Text("Proof by Infinite Descent", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        # Equation
        equation = MathTex(r"x^4 + y^4 = z^2", font_size=32, color=ACCENT_CYAN)
        equation.next_to(title, DOWN, buff=0.35)
        self.play(FadeIn(equation), run_time=0.4)

        # Staircase steps
        steps_data = [
            (r"(x_1, y_1, z_1)", "z_1"),
            (r"(x_2, y_2, z_2)", "z_2 < z_1"),
            (r"(x_3, y_3, z_3)", "z_3 < z_2"),
            (r"\cdots", r"\cdots"),
        ]

        step_x_start = -4.0
        step_y_start = 1.8
        step_dx = 1.8
        step_dy = -0.75

        step_groups = []
        arrows = []

        for i, (sol_tex, cond_tex) in enumerate(steps_data):
            x = step_x_start + i * step_dx
            y = step_y_start + i * step_dy

            # Solution box
            sol = MathTex(sol_tex, font_size=22, color=ACCENT_CYAN)
            sol.move_to([x, y, 0])

            # Condition label
            cond = MathTex(cond_tex, font_size=18, color=TEXT_DIM)
            cond.next_to(sol, DOWN, buff=0.12)

            # Step platform (horizontal line)
            platform = Line(
                [x - 0.8, y - 0.35, 0], [x + 0.8, y - 0.35, 0], color=TEXT_DIM, stroke_width=1.5
            )

            group = VGroup(sol, cond, platform)
            step_groups.append(group)

            # Arrow to next step
            if i < len(steps_data) - 1:
                arr = Arrow(
                    [x + 0.5, y - 0.1, 0],
                    [x + step_dx - 0.5, y + step_dy + 0.1, 0],
                    color=ACCENT_GOLD,
                    buff=0.05,
                    stroke_width=2,
                    max_tip_length_to_length_ratio=0.15,
                )
                arrows.append(arr)

        # Animate steps
        time_per_step = min(0.8, (duration * 0.35) / len(steps_data))
        for i, sg in enumerate(step_groups):
            self.play(FadeIn(sg), run_time=time_per_step)
            if i < len(arrows):
                self.play(FadeIn(arrows[i]), run_time=time_per_step * 0.5)

        # Contradiction box
        contra_y = step_y_start + len(steps_data) * step_dy - 0.15
        contradiction = VGroup(
            Text("正の整数は", font=FONT, font_size=20, color=TEXT_WHITE),
            Text("無限に小さくなれない", font=FONT, font_size=20, color=ACCENT_PINK),
        )
        contradiction.arrange(RIGHT, buff=0.1)
        contradiction.move_to([0, contra_y, 0])

        contra_rect = SurroundingRectangle(
            contradiction, color=ACCENT_PINK, buff=0.15, stroke_width=2
        )

        self.play(FadeIn(contradiction), FadeIn(contra_rect), run_time=0.6)

        # Final conclusion
        conclusion = VGroup(
            Text("矛盾", font=FONT, font_size=24, color=ACCENT_PINK),
            Text("  =  解は存在しない", font=FONT, font_size=22, color=ACCENT_GOLD),
        )
        conclusion.arrange(RIGHT, buff=0.1)
        conclusion.move_to([0, contra_y - 0.55, 0])
        self.play(FadeIn(conclusion), run_time=0.5)

        self.wait(max(1, duration * 0.15))

    # -------------------------------------------------------------------
    # Mode: pythagorean
    # -------------------------------------------------------------------
    def build_pythagorean(self):
        """Skeleton of the x⁴+y⁴=z² proof using Pythagorean triples.

        Shows the key insight: (x², y², z) forms a Pythagorean triple,
        which through parametrization yields a new equation of the same
        form with a strictly smaller z.
        """
        duration = self._duration
        highlight = self._highlight_color

        # Title
        title = Text("Proof Skeleton", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        # Step 1: Start equation
        step1_label = Text("Step 1:", font=FONT, font_size=20, color=ACCENT_GOLD)
        step1_label.move_to([-5.0, 2.5, 0])
        step1_eq = MathTex(r"x^4 + y^4 = z^2", font_size=28, color=ACCENT_CYAN)
        step1_eq.next_to(step1_label, RIGHT, buff=0.3)
        step1_note = Text("(仮に解が存在すると仮定)", font=FONT, font_size=16, color=TEXT_DIM)
        step1_note.next_to(step1_eq, RIGHT, buff=0.2)

        self.play(FadeIn(step1_label), FadeIn(step1_eq), FadeIn(step1_note), run_time=0.5)

        # Step 2: Recognize Pythagorean triple
        step2_label = Text("Step 2:", font=FONT, font_size=20, color=ACCENT_GOLD)
        step2_label.move_to([-5.0, 1.5, 0])
        step2_eq = MathTex(r"(x^2)^2 + (y^2)^2 = z^2", font_size=28, color=TEXT_WHITE)
        step2_eq.next_to(step2_label, RIGHT, buff=0.3)
        step2_note = Text("= Pythagorean triple", font=FONT, font_size=16, color=TEXT_DIM)
        step2_note.next_to(step2_eq, RIGHT, buff=0.2)

        self.play(FadeIn(step2_label), FadeIn(step2_eq), FadeIn(step2_note), run_time=0.5)

        # Step 3: Parametrize
        step3_label = Text("Step 3:", font=FONT, font_size=20, color=ACCENT_GOLD)
        step3_label.move_to([-5.0, 0.5, 0])
        step3_eq = MathTex(
            r"x^2 = 2pq, \quad y^2 = p^2 - q^2, \quad z = p^2 + q^2", font_size=24, color=TEXT_WHITE
        )
        step3_eq.next_to(step3_label, RIGHT, buff=0.3)

        self.play(FadeIn(step3_label), FadeIn(step3_eq), run_time=0.5)

        # Step 4: Derive new equation
        step4_label = Text("Step 4:", font=FONT, font_size=20, color=ACCENT_GOLD)
        step4_label.move_to([-5.0, -0.5, 0])
        step4_eq = MathTex(r"A^4 + B^4 = P^2", font_size=28, color=ACCENT_CYAN)
        step4_eq.next_to(step4_label, RIGHT, buff=0.3)

        step4_note_parts = VGroup(
            Text("ただし", font=FONT, font_size=16, color=TEXT_DIM),
            MathTex(r"P < z", font_size=22, color=ACCENT_PINK),
        )
        step4_note_parts.arrange(RIGHT, buff=0.1)
        step4_note_parts.next_to(step4_eq, RIGHT, buff=0.2)

        self.play(FadeIn(step4_label), FadeIn(step4_eq), FadeIn(step4_note_parts), run_time=0.5)

        # Arrow showing descent
        descent_arrow = Arrow(
            step4_eq.get_bottom() + DOWN * 0.1,
            step4_eq.get_bottom() + DOWN * 0.8,
            color=ACCENT_PINK,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.2,
        )
        descent_label = Text("Descent!", font=FONT, font_size=18, color=ACCENT_PINK)
        descent_label.next_to(descent_arrow, RIGHT, buff=0.15)

        self.play(FadeIn(descent_arrow), FadeIn(descent_label), run_time=0.4)

        # Conclusion
        conclusion = VGroup(
            MathTex(r"z > P > P' > P'' > \cdots", font_size=24, color=ACCENT_GOLD),
        )
        conclusion.move_to([0, -1.5, 0])

        contra = Text(
            "正の整数列は無限に減少できない = 矛盾", font=FONT, font_size=20, color=ACCENT_PINK
        )
        contra.next_to(conclusion, DOWN, buff=0.25)

        self.play(FadeIn(conclusion), run_time=0.5)
        self.play(FadeIn(contra), run_time=0.5)

        self.wait(max(1, duration * 0.15))
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "staircase": {"people": [], "years": []},
    "pythagorean": {"people": [], "years": []},
}



# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "staircase": {
        "class": "InfiniteDescent",
        "params": {"mode": "staircase"},
        "description": "Descending staircase showing infinite descent logic",
    },
    "pythagorean": {
        "class": "InfiniteDescent",
        "params": {"mode": "pythagorean"},
        "description": "x^4+y^4=z^2 proof skeleton via Pythagorean triples",
    },
}
