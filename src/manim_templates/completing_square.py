"""
completing_square.py - Geometric completing the square for 数学史記

Al-Khwarizmi's geometric proof of x² + 10x = 39.
Builds up rectangles visually to show how completing the square works
without any symbolic algebra — only geometry.

Modes:
    buildup    - Step-by-step geometric construction.
                 Fixed params: equation x²+10x=39, split 10x into 4×2.5x,
                 corner squares 4×(2.5²)=25, total=64, side=8, x=3
    proof      - Show completed figure with area calculation overlay.
                 Fixed params: same equation, final square side=8
    six_types  - Display al-Khwarizmi's 6 standard forms of equations.
                 Fixed params: 6 forms (squares=roots, squares=number, etc.)

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 008 (Al-Khwarizmi)
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Brace,
    FadeIn,
    FadeOut,
    MathTex,
    Rectangle,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


# Layout constants
UNIT = 0.55  # scale factor for buildup mode


class CompletingSquare(Scene):
    """Geometric completing the square — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "buildup")
        self._duration = params.get("duration", 30)

        if mode == "proof":
            self._build_proof()
        elif mode == "six_types":
            self._build_six_types()
        else:
            self._build_buildup()

    # ------------------------------------------------------------------
    # Mode: buildup
    # ------------------------------------------------------------------
    def _build_buildup(self):
        duration = self._duration

        title = Text(
            "x² + 10x = 39  ── 幾何学的平方完成",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        n_steps = 6
        anim_time = 0.8 + n_steps * 1.5
        default_waits = n_steps * 1.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        x_val = 3
        half_coeff = 2.5
        x_size = x_val * UNIT
        h_size = half_coeff * UNIT

        fig_center = LEFT * 1.0 + UP * 1.0

        # Step 1: Central x² square
        x_sq = Square(
            side_length=x_size,
            color=ACCENT_CYAN,
            fill_opacity=0.35,
            stroke_width=2,
        )
        x_sq.move_to(fig_center)
        x_sq_label = MathTex(r"x^2", font_size=28, color=ACCENT_CYAN)
        x_sq_label.move_to(fig_center)

        step1_text = Text(
            "① 中央に x×x の正方形",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        step1_text.move_to(DOWN * 1.8)

        self.play(FadeIn(x_sq), FadeIn(x_sq_label), FadeIn(step1_text), run_time=1.0)
        self.wait(1.5 * ws)

        # Step 2: Four rectangles
        rects = VGroup()
        rect_labels = VGroup()
        for direction, w, h in [
            (RIGHT, h_size, x_size),
            (LEFT, h_size, x_size),
            (UP, x_size, h_size),
            (DOWN, x_size, h_size),
        ]:
            r = Rectangle(width=w, height=h, color=ACCENT_GOLD, fill_opacity=0.3, stroke_width=2)
            r.next_to(x_sq, direction, buff=0)
            rl = MathTex(r"2.5x", font_size=20, color=ACCENT_GOLD)
            rl.move_to(r)
            rects.add(r)
            rect_labels.add(rl)

        step2_text = Text(
            "② 10x を4等分し長方形を四辺に配置",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        step2_text.move_to(DOWN * 1.8)

        self.play(FadeOut(step1_text), run_time=0.3)
        self.play(FadeIn(rects), FadeIn(rect_labels), FadeIn(step2_text), run_time=1.2)
        self.wait(1.5 * ws)

        # Step 3: Four corner squares
        corners = VGroup()
        corner_labels = VGroup()
        for d1, d2 in [(UP, RIGHT), (UP, LEFT), (DOWN, RIGHT), (DOWN, LEFT)]:
            corner_pos = x_sq.get_corner(d1 + d2)
            c_sq = Square(
                side_length=h_size,
                color=ACCENT_PINK,
                fill_opacity=0.3,
                stroke_width=2,
            )
            c_sq.move_to(corner_pos + (d1 + d2) * h_size / 2)
            corners.add(c_sq)
            cl = MathTex(r"6.25", font_size=16, color=ACCENT_PINK)
            cl.move_to(c_sq)
            corner_labels.add(cl)

        step3_text = Text(
            "③ 角に 2.5×2.5 の正方形を追加",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        step3_text.move_to(DOWN * 1.8)

        self.play(FadeOut(step2_text), run_time=0.3)
        self.play(FadeIn(corners), FadeIn(corner_labels), FadeIn(step3_text), run_time=1.0)
        self.wait(1.5 * ws)

        # Step 4: Brace (right side only)
        full_group = VGroup(x_sq, rects, corners)
        brace_r = Brace(full_group, RIGHT, color=TEXT_DIM)
        brace_r_label = MathTex(r"x + 5", font_size=24, color=TEXT_WHITE)
        brace_r_label.next_to(brace_r, RIGHT, buff=0.15)

        step4_text = Text(
            "④ 全体の面積 = 39 + 25 = 64",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        step4_text.move_to(DOWN * 1.8)

        self.play(FadeOut(step3_text), run_time=0.3)
        self.play(
            FadeIn(brace_r),
            FadeIn(brace_r_label),
            FadeIn(step4_text),
            run_time=1.0,
        )
        self.wait(1.5 * ws)

        # Step 5: Solve
        step5_text = VGroup(
            MathTex(r"(x+5)^2 = 64", font_size=32, color=ACCENT_GOLD),
            MathTex(r"x + 5 = 8", font_size=32, color=ACCENT_CYAN),
            MathTex(r"x = 3", font_size=36, color=ACCENT_PINK),
        )
        step5_text.arrange(DOWN, buff=0.3)
        step5_text.move_to(RIGHT * 4.5 + UP * 0.5)

        self.play(FadeOut(step4_text), run_time=0.3)
        for eq in step5_text:
            self.play(FadeIn(eq), run_time=0.8)
            self.wait(0.8 * ws)

        # Step 6: Final highlight
        answer_box = Rectangle(
            width=2.0,
            height=0.7,
            color=ACCENT_PINK,
            stroke_width=3,
            fill_opacity=0.15,
        )
        answer_box.move_to(step5_text[2])
        self.play(FadeIn(answer_box), run_time=0.5)
        self.wait(1.5 * ws)

    # ------------------------------------------------------------------
    # Mode: proof
    # ------------------------------------------------------------------
    def _build_proof(self):
        duration = self._duration

        title = Text(
            "平方完成 ── 完成図",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 3.5
        default_waits = duration - anim_time
        ws = _calc_wait_scale(duration, anim_time, max(default_waits, 1.0))

        u = 0.38
        x_size = 3 * u
        h5_size = 5 * u
        side = 8 * u

        fig_cx, fig_cy = -2.5, 0.3

        big_sq = Square(
            side_length=side,
            color=TEXT_DIM,
            stroke_width=2,
            fill_opacity=0.05,
        )
        big_sq.move_to([fig_cx, fig_cy, 0])

        inner_bl = big_sq.get_corner(DOWN + LEFT)
        x_sq = Rectangle(
            width=x_size,
            height=x_size,
            color=ACCENT_CYAN,
            fill_opacity=0.35,
            stroke_width=2,
        )
        x_sq.move_to(inner_bl + RIGHT * x_size / 2 + UP * x_size / 2)
        x_label = MathTex(r"x^2", font_size=24, color=ACCENT_CYAN)
        x_label.move_to(x_sq)

        r_right = Rectangle(
            width=h5_size,
            height=x_size,
            color=ACCENT_GOLD,
            fill_opacity=0.25,
            stroke_width=2,
        )
        r_right.next_to(x_sq, RIGHT, buff=0)
        r_right_label = MathTex(r"5x", font_size=20, color=ACCENT_GOLD)
        r_right_label.move_to(r_right)

        r_top = Rectangle(
            width=x_size,
            height=h5_size,
            color=ACCENT_GOLD,
            fill_opacity=0.25,
            stroke_width=2,
        )
        r_top.next_to(x_sq, UP, buff=0)
        r_top_label = MathTex(r"5x", font_size=20, color=ACCENT_GOLD)
        r_top_label.move_to(r_top)

        c_sq = Square(
            side_length=h5_size,
            color=ACCENT_PINK,
            fill_opacity=0.25,
            stroke_width=2,
        )
        c_sq.next_to(r_right, UP, buff=0)
        c_label = MathTex(r"25", font_size=22, color=ACCENT_PINK)
        c_label.move_to(c_sq)

        brace_r = Brace(big_sq, RIGHT, color=TEXT_DIM)
        br_label = MathTex(r"x+5", font_size=20, color=TEXT_WHITE)
        br_label.next_to(brace_r, RIGHT, buff=0.1)

        brace_b = Brace(big_sq, DOWN, color=TEXT_DIM)
        bb_label = MathTex(r"x+5", font_size=20, color=TEXT_WHITE)
        bb_label.next_to(brace_b, DOWN, buff=0.1)

        figure = VGroup(big_sq, x_sq, r_right, r_top, c_sq)
        fig_labels = VGroup(x_label, r_right_label, r_top_label, c_label)
        braces = VGroup(brace_r, br_label, brace_b, bb_label)

        self.play(FadeIn(figure), FadeIn(fig_labels), FadeIn(braces), run_time=1.5)
        self.wait(1.0 * ws)

        eqs = VGroup(
            MathTex(r"x^2 + 10x = 39", font_size=32, color=TEXT_WHITE),
            MathTex(r"x^2 + 10x + 25 = 64", font_size=32, color=ACCENT_GOLD),
            MathTex(r"(x+5)^2 = 64", font_size=32, color=ACCENT_GOLD),
            MathTex(r"x = 3", font_size=36, color=ACCENT_PINK),
        )
        eqs.arrange(DOWN, buff=0.35)
        eqs.move_to([2.5, 0.3, 0])

        for eq in eqs:
            self.play(FadeIn(eq), run_time=0.5)
            self.wait(0.5 * ws)

        self.wait(max(duration - 5.0, 1.0))

    # ------------------------------------------------------------------
    # Mode: six_types
    # ------------------------------------------------------------------
    def _build_six_types(self):
        duration = self._duration

        title = Text(
            "6つの標準形",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.8)

        subtitle = Text(
            "負の数がないため、場合分けが必要だった",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(subtitle), run_time=0.5)

        forms = [
            (r"ax^2 = bx", "正方形 = 根"),
            (r"ax^2 = c", "正方形 = 数"),
            (r"bx = c", "根 = 数"),
            (r"ax^2 + bx = c", "正方形 + 根 = 数"),
            (r"ax^2 + c = bx", "正方形 + 数 = 根"),
            (r"bx + c = ax^2", "根 + 数 = 正方形"),
        ]

        n_forms = len(forms)
        anim_time = 1.3 + n_forms * 0.7 + 0.6
        default_waits = n_forms * 0.8 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        rows = VGroup()
        start_y = 2.0
        row_gap = 0.7

        for i, (latex, label) in enumerate(forms):
            y_pos = start_y - i * row_gap

            num = Text(f"{i + 1}.", font=FONT, font_size=22, color=TEXT_DIM)
            num.move_to(LEFT * 4.5 + UP * y_pos)

            formula = MathTex(latex, font_size=30, color=ACCENT_CYAN)
            formula.move_to(LEFT * 1.5 + UP * y_pos)

            desc = Text(label, font=FONT, font_size=22, color=TEXT_WHITE)
            desc.move_to(RIGHT * 2.5 + UP * y_pos)

            row = VGroup(num, formula, desc)
            rows.add(row)

            self.play(FadeIn(row), run_time=0.5)
            self.wait(0.8 * ws)

        highlight_box = Rectangle(
            width=9.0,
            height=0.55,
            color=ACCENT_PINK,
            stroke_width=2,
            fill_opacity=0.1,
        )
        highlight_box.move_to(rows[3])

        note = Text(
            "x² + 10x = 39 は第4の形に該当する",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        note.move_to(DOWN * 1.9)

        self.play(FadeIn(highlight_box), FadeIn(note), run_time=0.6)
        self.wait(max(duration - anim_time - n_forms * 0.8, 1.0))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "buildup": {"people": [], "years": []},
    "proof": {"people": [], "years": []},
    "six_types": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
SCENES = {
    "buildup": CompletingSquare,
    "proof": CompletingSquare,
    "six_types": CompletingSquare,
}
