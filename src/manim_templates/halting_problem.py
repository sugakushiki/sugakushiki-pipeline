"""
halting_problem.py - Halting problem proof visualization for 数学史記

Visualizes the undecidability of the halting problem using
a diagonal argument and self-referential paradox.

Modes:
    diagonal - Table of programs x inputs, diagonal flip -> contradiction
    paradox  - Self-referential paradox: program D that contradicts
               any hypothetical halting decider H

Params:
    mode: "diagonal" or "paradox" (default: "diagonal")
    duration: target duration in seconds

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    FadeIn,
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

HALT_COLOR = ACCENT_CYAN  # "stops" = cyan
LOOP_COLOR = ACCENT_PINK  # "loops" = pink
DIAG_COLOR = ACCENT_GOLD  # diagonal highlight


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class HaltingProblem(Scene):
    """Halting problem proof visualization."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "diagonal")
        self._duration = params.get("duration", 30)

        if mode == "paradox":
            self._build_paradox()
        else:
            self._build_diagonal()

    # ------------------------------------------------------------------
    # Mode: diagonal — table + diagonal flip
    # ------------------------------------------------------------------
    def _build_diagonal(self):
        duration = self._duration

        title = Text(
            "停止問題の非決定性",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)
        subtitle = Text(
            "対角線論法による証明",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).next_to(title, DOWN, buff=0.15)

        anim_time = 8.0
        default_wait_total = 10.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)
        self.wait(0.8 * ws)

        # Build grid: 4 programs x 4 inputs
        n = 4
        cell_w, cell_h = 1.1, 0.55
        grid_x0, grid_y0 = -1.5, 1.2

        # Column headers (inputs)
        col_headers = VGroup()
        for j in range(n):
            h = Text(
                f"P{j + 1}",
                font=FONT,
                font_size=18,
                color=TEXT_DIM,
            ).move_to([grid_x0 + (j + 1) * cell_w, grid_y0 + cell_h * 0.7, 0])
            col_headers.add(h)
        input_label = Text(
            "入力 ->",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        ).move_to([grid_x0 - 0.2, grid_y0 + cell_h * 0.7, 0])

        # Row headers (programs)
        row_headers = VGroup()
        for i in range(n):
            h = Text(
                f"P{i + 1}",
                font=FONT,
                font_size=18,
                color=TEXT_DIM,
            ).move_to([grid_x0, grid_y0 - i * cell_h, 0])
            row_headers.add(h)

        self.play(
            FadeIn(col_headers),
            FadeIn(row_headers),
            FadeIn(input_label),
            run_time=0.6,
        )

        # Halting table (H = halts, L = loops)
        # Diagonal: P1(P1)=H, P2(P2)=L, P3(P3)=H, P4(P4)=L
        table_data = [
            ["H", "L", "H", "H"],
            ["L", "L", "H", "L"],
            ["H", "H", "H", "L"],
            ["H", "L", "L", "L"],
        ]

        cells = {}
        cell_texts = {}
        cell_rects = {}
        for i in range(n):
            for j in range(n):
                val = table_data[i][j]
                x = grid_x0 + (j + 1) * cell_w
                y = grid_y0 - i * cell_h
                rect = Rectangle(
                    width=cell_w * 0.9,
                    height=cell_h * 0.85,
                    stroke_color=TEXT_DIM,
                    stroke_width=1,
                ).move_to([x, y, 0])
                col = HALT_COLOR if val == "H" else LOOP_COLOR
                txt = Text(val, font=FONT, font_size=20, color=col)
                txt.move_to(rect.get_center())
                cells[(i, j)] = VGroup(rect, txt)
                cell_texts[(i, j)] = txt
                cell_rects[(i, j)] = rect

        all_cells = VGroup(*[cells[(i, j)] for i in range(n) for j in range(n)])
        self.play(FadeIn(all_cells), run_time=0.8)
        self.wait(1.0 * ws)

        # Highlight diagonal
        for i in range(n):
            rect = cell_rects[(i, i)]
            self.play(
                rect.animate.set_stroke(color=DIAG_COLOR, width=3),
                run_time=0.3,
            )
        self.wait(0.8 * ws)

        # Show diagonal values and flip
        diag_label = Text(
            "対角線:",
            font=FONT,
            font_size=20,
            color=DIAG_COLOR,
        ).move_to([grid_x0 - 1.2, -1.2, 0])
        diag_vals = Text(
            "H  L  H  L",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).next_to(diag_label, RIGHT, buff=0.3)
        self.play(FadeIn(diag_label), FadeIn(diag_vals), run_time=0.5)
        self.wait(0.6 * ws)

        flip_label = Text(
            "反転:",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        ).move_to([grid_x0 - 1.2, -1.6, 0])
        flip_vals = Text(
            "L  H  L  H",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        ).next_to(flip_label, RIGHT, buff=0.3)
        self.play(FadeIn(flip_label), FadeIn(flip_vals), run_time=0.5)
        self.wait(0.6 * ws)

        # D label
        d_label = Text(
            "= プログラム D",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        ).next_to(flip_vals, RIGHT, buff=0.3)
        self.play(FadeIn(d_label), run_time=0.4)
        self.wait(0.5 * ws)

        # Contradiction
        contradiction = Text(
            "D はどの行とも一致しない -> 矛盾",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        ).move_to([0, -1.95, 0])
        self.play(FadeIn(contradiction), run_time=0.5)
        self.wait(max(duration - 9.0, 1.5))

    # ------------------------------------------------------------------
    # Mode: paradox — self-referential contradiction
    # ------------------------------------------------------------------
    def _build_paradox(self):
        duration = self._duration

        title = Text(
            "停止問題の矛盾",
            font=FONT,
            font_size=34,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)

        anim_time = 6.0
        default_wait_total = 8.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        self.play(FadeIn(title), run_time=0.5)
        self.wait(0.8 * ws)

        # Step 1: Assume H exists
        step1 = Text(
            "仮定: 停止判定器 H が存在する",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        ).move_to([0, 2.5, 0])
        h_box = Rectangle(
            width=4.5,
            height=0.8,
            stroke_color=HALT_COLOR,
            stroke_width=2,
        ).move_to([0, 1.7, 0])
        h_label = Text(
            "H(P, x) = 停止 or 非停止",
            font=FONT,
            font_size=20,
            color=HALT_COLOR,
        ).move_to(h_box.get_center())

        self.play(FadeIn(step1), run_time=0.5)
        self.play(FadeIn(h_box), FadeIn(h_label), run_time=0.5)
        self.wait(1.0 * ws)

        # Step 2: Construct D
        step2 = Text(
            "D を構成する:",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        ).move_to([-3.5, 0.8, 0])
        d_box = Rectangle(
            width=6.5,
            height=0.9,
            stroke_color=ACCENT_PINK,
            stroke_width=2,
        ).move_to([0, 0.1, 0])
        d_def = Text(
            "D(P): H(P,P)=停止 なら無限ループ, 否なら停止",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        ).move_to(d_box.get_center())
        self.play(FadeIn(step2), FadeIn(d_box), FadeIn(d_def), run_time=0.6)
        self.wait(1.0 * ws)

        # Step 3: D(D) — paradox
        step3 = Text(
            "D に D 自身を入力すると?",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        ).move_to([0, -0.7, 0])
        self.play(FadeIn(step3), run_time=0.5)
        self.wait(0.8 * ws)

        # Case 1
        case1 = Text(
            "H(D,D) = 停止 -> D は無限ループ -> 矛盾",
            font=FONT,
            font_size=20,
            color=LOOP_COLOR,
        ).move_to([0, -1.3, 0])
        self.play(FadeIn(case1), run_time=0.5)
        self.wait(0.5 * ws)

        # Case 2
        case2 = Text(
            "H(D,D) = 非停止 -> D は停止 -> 矛盾",
            font=FONT,
            font_size=20,
            color=HALT_COLOR,
        ).move_to([0, -1.7, 0])
        self.play(FadeIn(case2), run_time=0.5)
        self.wait(0.6 * ws)

        # Conclusion
        conclusion = Text(
            "H は存在しない",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        ).move_to([0, -2.0, 0])
        self.play(FadeIn(conclusion), run_time=0.5)
        self.wait(max(duration - 7.0, 1.5))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "diagonal": {"people": [], "years": []},
    "paradox": {"people": [], "years": []},
}


SCENES = {
    "diagonal": HaltingProblem,
    "paradox": HaltingProblem,
}
