"""
taxicab_number.py - Hardy-Ramanujan number 1729 visualization for 数学史記

Shows 1729 = 1³ + 12³ = 9³ + 10³ with cubic block representation.

Modes:
    static    - Display 1729 = 1³+12³ = 9³+10³ with equation
    animation - Build up cubes visually, then reveal second decomposition

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 004 (Ramanujan), hook_02
"""

from manim import (
    DOWN,
    ORIGIN,
    UP,
    FadeIn,
    FadeOut,
    MathTex,
    Scene,
    Square,
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


def make_cube_stack(n, color, cell_size=0.08, max_display=12):
    """Create a visual representation of n³ as a stack of small squares.

    For large n, shows a symbolic square with label instead of individual cells.
    """
    if n <= max_display:
        # Show n×n grid (simplified 2D representation of cube)
        grid = VGroup()
        for row in range(min(n, 8)):
            for col in range(min(n, 8)):
                sq = Square(
                    side_length=cell_size,
                    color=color,
                    fill_opacity=0.6,
                    stroke_width=0.5,
                    stroke_color=color,
                )
                sq.move_to([col * cell_size * 1.1, row * cell_size * 1.1, 0])
                grid.add(sq)
        grid.move_to(ORIGIN)
        return grid
    else:
        # Symbolic block
        block = Square(
            side_length=n * cell_size * 0.8,
            color=color,
            fill_opacity=0.3,
            stroke_width=2,
            stroke_color=color,
        )
        label = MathTex(f"{n}^3", font_size=24, color=color)
        label.move_to(block.get_center())
        return VGroup(block, label)


class TaxicabStatic(Scene):
    """Display 1729 decomposition statically."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 15)

        # Title
        title = MathTex("1729", font_size=72, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.6)

        # Two decompositions - chain vertically: eq1 → val1 → eq2 → val2
        eq1 = MathTex(r"= 1^3 + 12^3", font_size=48, color=ACCENT_CYAN)
        eq2 = MathTex(r"= 9^3 + 10^3", font_size=48, color=ACCENT_PINK)
        eq1.next_to(title, DOWN, buff=0.6)

        # Values
        val1 = MathTex(r"= 1 + 1728", font_size=36, color=TEXT_DIM)
        val2 = MathTex(r"= 729 + 1000", font_size=36, color=TEXT_DIM)
        val1.next_to(eq1, DOWN, buff=0.2)
        eq2.next_to(val1, DOWN, buff=0.5)
        val2.next_to(eq2, DOWN, buff=0.2)

        # Bottom note
        note = Text(
            "2 通りの立方数の和で表せる最小の正の整数",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        note.next_to(val2, DOWN, buff=0.6)
        self.play(FadeIn(title, scale=1.2), run_time=1.0)
        wait_unit = max(0.5, (duration - 6) / 4)
        self.wait(wait_unit)

        self.play(FadeIn(eq1), run_time=0.8)
        self.play(FadeIn(val1), run_time=0.5)
        self.wait(wait_unit)

        self.play(FadeIn(eq2), run_time=0.8)
        self.play(FadeIn(val2), run_time=0.5)
        self.wait(wait_unit)

        self.play(FadeIn(note), run_time=0.8)
        self.wait(wait_unit)


class TaxicabAnimation(Scene):
    """Animate the two decompositions of 1729 with cube blocks."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 25)

        # Title
        title = MathTex("1729", font_size=72, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.6)
        self.play(FadeIn(title, scale=1.2), run_time=1.0)

        wait_unit = max(0.3, (duration - 10) / 6)

        # First decomposition: 1³ + 12³
        eq1 = MathTex(r"= 1^3 + 12^3", font_size=48, color=ACCENT_CYAN)
        eq1.move_to([0, 1.5, 0])

        cube_1 = make_cube_stack(1, ACCENT_CYAN, cell_size=0.15)
        cube_12 = make_cube_stack(12, ACCENT_CYAN, cell_size=0.06)
        cube_1.move_to([-2.5, -0.5, 0])
        cube_12.move_to([1.5, -0.5, 0])

        label_1 = MathTex("1^3 = 1", font_size=28, color=ACCENT_CYAN)
        label_12 = MathTex("12^3 = 1728", font_size=28, color=ACCENT_CYAN)
        label_1.next_to(cube_1, DOWN, buff=0.3)
        label_12.next_to(cube_12, DOWN, buff=0.3)

        plus = MathTex("+", font_size=42, color=TEXT_WHITE)
        plus.move_to([-0.5, -0.5, 0])

        self.play(FadeIn(eq1), run_time=0.8)
        self.play(FadeIn(cube_1), FadeIn(label_1), run_time=0.6)
        self.play(FadeIn(plus), run_time=0.3)
        self.play(FadeIn(cube_12), FadeIn(label_12), run_time=0.6)
        self.wait(wait_unit * 1.5)

        # Transition
        group1 = VGroup(eq1, cube_1, cube_12, label_1, label_12, plus)
        self.play(FadeOut(group1), run_time=0.6)

        # Second decomposition: 9³ + 10³
        eq2 = MathTex(r"= 9^3 + 10^3", font_size=48, color=ACCENT_PINK)
        eq2.move_to([0, 1.5, 0])

        cube_9 = make_cube_stack(9, ACCENT_PINK, cell_size=0.06)
        cube_10 = make_cube_stack(10, ACCENT_PINK, cell_size=0.06)
        cube_9.move_to([-2.5, -0.5, 0])
        cube_10.move_to([1.5, -0.5, 0])

        label_9 = MathTex("9^3 = 729", font_size=28, color=ACCENT_PINK)
        label_10 = MathTex("10^3 = 1000", font_size=28, color=ACCENT_PINK)
        label_9.next_to(cube_9, DOWN, buff=0.3)
        label_10.next_to(cube_10, DOWN, buff=0.3)

        plus2 = MathTex("+", font_size=42, color=TEXT_WHITE)
        plus2.move_to([-0.5, -0.5, 0])

        self.play(FadeIn(eq2), run_time=0.8)
        self.play(FadeIn(cube_9), FadeIn(label_9), run_time=0.6)
        self.play(FadeIn(plus2), run_time=0.3)
        self.play(FadeIn(cube_10), FadeIn(label_10), run_time=0.6)
        self.wait(wait_unit * 1.5)

        # Final: show both equations together
        group2 = VGroup(eq2, cube_9, cube_10, label_9, label_10, plus2)
        self.play(FadeOut(group2), run_time=0.5)

        both = VGroup(
            MathTex(r"1729 = 1^3 + 12^3", font_size=42, color=ACCENT_CYAN),
            MathTex(r"1729 = 9^3 + 10^3", font_size=42, color=ACCENT_PINK),
        )
        both.arrange(DOWN, buff=0.5)
        both.move_to([0, 0.5, 0])

        note = Text(
            "2 通りの立方数の和で表せる最小の正の整数",
            font=FONT,
            font_size=24,
            color=TEXT_DIM,
        )
        note.next_to(both, DOWN, buff=0.6)

        self.play(FadeIn(both), run_time=0.8)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(wait_unit * 2)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "static": {"people": [], "years": []},
    "animation": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
SCENES = {
    "static": TaxicabStatic,
    "animation": TaxicabAnimation,
}
