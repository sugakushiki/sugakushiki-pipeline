"""
leibniz_calculus.py - Leibniz's calculus notation for 数学史記

Visualizes how Leibniz introduced the symbolic notation that became
the standard for differential and integral calculus:

    - tangent_problem: Tangent slope at P(1,1) on y = x² via the
      difference quotient Δy/Δx, with Δx shrinking toward 0.
    - differential_notation: From Δy/Δx to dy/dx, the symbolic leap
      Leibniz made in his Paris manuscripts (1675).
    - area_integral: Area under y = x² on [0,1] approximated as a
      sum of infinitesimal rectangles ∫₀¹ y dx = 1/3.
    - fundamental_theorem: Differentiation and integration as
      mutually inverse operations: d/dx (∫₀ˣ t² dt) = x².

Fixed parameters (verified by hand):
    Curve:        y = x² on [0, 2]
    Tangent at:   P(1, 1), slope dy/dx = 2x|_{x=1} = 2
    Area:         ∫₀¹ x² dx = 1/3
    FT identity:  d/dx (∫₀ˣ t² dt) = x²

Duration-aware: reads target duration from _manim_params.json.
Y range: -1.6 to +3.0, axes shifted DOWN, title at +3.0,
subtitle clearance preserved.

Used by: Episode 023 (Leibniz), math pillar 1 — calculus & notation.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Axes,
    Dot,
    FadeIn,
    FadeOut,
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
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class LeibnizCalculus(Scene):
    """Leibniz's calculus notation — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "tangent_problem")
        self._duration = params.get("duration", 35)

        if mode == "differential_notation":
            self._build_differential_notation()
        elif mode == "area_integral":
            self._build_area_integral()
        elif mode == "fundamental_theorem":
            self._build_fundamental_theorem()
        else:
            self._build_tangent_problem()

    # ------------------------------------------------------------------
    def _make_axes(self, shift=DOWN * 0.5, x_max=2.2, y_max=2.6):
        axes = Axes(
            x_range=[-0.3, x_max, 1],
            y_range=[-0.3, y_max, 1],
            x_length=6.4,
            y_length=3.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.5},
        )
        axes.shift(shift)
        return axes

    def _draw_parabola(self, axes, x_min=-0.2, x_max=1.6, color=ACCENT_GOLD):
        return axes.plot(
            lambda x: x * x,
            x_range=[x_min, x_max],
            color=color,
            stroke_width=3,
        )

    # ------------------------------------------------------------------
    def _build_tangent_problem(self):
        duration = self._duration

        title = Text(
            "接線の傾き ── 差分 Δy/Δx を縮めていく",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"y = x^2", font_size=30, color=ACCENT_CYAN)
        eq.move_to([-4.8, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.5)

        axes = self._make_axes()
        parabola = self._draw_parabola(axes)
        self.play(FadeIn(axes), FadeIn(parabola), run_time=0.7)

        # Anchor point P(1, 1)
        p_pos = axes.c2p(1, 1)
        p_dot = Dot(p_pos, radius=0.09, color=ACCENT_PINK)
        p_label = MathTex(r"P(1, 1)", font_size=24, color=ACCENT_PINK)
        p_label.next_to(p_dot, LEFT, buff=0.15)
        self.play(FadeIn(p_dot), FadeIn(p_label), run_time=0.5)

        # Secant lines for shrinking Δx
        delta_values = [0.5, 0.3, 0.15, 0.05]
        header_anim = 0.6 + 0.5 + 0.7 + 0.5
        per_step = max(0.8, (duration - header_anim - 3.0) / len(delta_values))

        prev_secant = None
        prev_q = None
        prev_label = None

        for d in delta_values:
            x_q = 1 + d
            y_q = x_q * x_q
            slope = (y_q - 1) / d  # = 2 + d

            q_pos = axes.c2p(x_q, y_q)
            q_dot = Dot(q_pos, radius=0.07, color=ACCENT_CYAN)

            secant = Line(p_pos, q_pos, color=ACCENT_CYAN, stroke_width=2)

            slope_label = MathTex(
                rf"\frac{{\Delta y}}{{\Delta x}} = {slope:.2f}",
                font_size=24,
                color=ACCENT_CYAN,
            )
            slope_label.move_to([-4.8, 1.6 - 0.0, 0])

            if prev_secant is not None:
                self.play(
                    FadeOut(prev_secant),
                    FadeOut(prev_q),
                    FadeOut(prev_label),
                    run_time=0.2,
                )

            self.play(
                FadeIn(secant),
                FadeIn(q_dot),
                FadeIn(slope_label),
                run_time=min(0.55, per_step * 0.45),
            )
            self.wait(max(0.2, per_step - 0.55))

            prev_secant = secant
            prev_q = q_dot
            prev_label = slope_label

        # Final tangent at slope 2
        tan_start = axes.c2p(0.2, 2 * 0.2 - 1)
        tan_end = axes.c2p(1.8, 2 * 1.8 - 1)
        tangent_line = Line(tan_start, tan_end, color=ACCENT_GOLD, stroke_width=3)
        tan_label = MathTex(
            r"\Delta x \to 0 \;\Rightarrow\; \frac{dy}{dx} = 2",
            font_size=28,
            color=ACCENT_GOLD,
        )
        tan_label.move_to([0, 2.55, 0])

        self.play(
            FadeIn(tangent_line),
            FadeIn(tan_label),
            run_time=0.7,
        )
        self.wait(1.5)

    # ------------------------------------------------------------------
    def _build_differential_notation(self):
        duration = self._duration

        title = Text(
            "差分から微分へ ── ライプニッツの dy, dx",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        steps = [
            (r"\frac{\Delta y}{\Delta x} = \frac{(x+\Delta x)^2 - x^2}{\Delta x}", "差分商"),
            (r"= \frac{2x\,\Delta x + (\Delta x)^2}{\Delta x} = 2x + \Delta x", "展開"),
            (r"\Delta x \to 0 \;\Rightarrow\; \frac{dy}{dx} = 2x", "極限"),
            (r"dy = 2x \, dx", "微分形式"),
            (r"d(uv) = u\,dv + v\,du", "積の法則 (1684 Nova Methodus)"),
        ]

        y_start = 2.2
        y_step = 0.78
        per_line = max(0.8, (duration - 1.5) / len(steps))

        for i, (expr, tag) in enumerate(steps):
            y = y_start - i * y_step
            color = ACCENT_PINK if i >= 3 else TEXT_WHITE
            fs = 32 if i >= 3 else 28
            eq = MathTex(expr, font_size=fs, color=color)
            eq.move_to([-1.0, y, 0])

            tag_label = Text(tag, font=FONT, font_size=20, color=TEXT_DIM)
            tag_label.next_to(eq, RIGHT, buff=0.5)

            self.play(FadeIn(eq), FadeIn(tag_label), run_time=0.6)
            self.wait(max(0.15, per_line - 0.6))

        self.wait(1.0)

    # ------------------------------------------------------------------
    def _build_area_integral(self):
        duration = self._duration

        title = Text(
            "曲線の下の面積 ── 無限小長方形の和 ∫ y dx",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(r"y = x^2", font_size=30, color=ACCENT_CYAN)
        eq.move_to([-4.8, 2.3, 0])
        self.play(FadeIn(eq), run_time=0.5)

        axes = self._make_axes(shift=DOWN * 0.5, x_max=1.4, y_max=1.4)
        parabola = self._draw_parabola(axes, x_min=0, x_max=1.0)
        self.play(FadeIn(axes), FadeIn(parabola), run_time=0.7)

        # Three stages: coarse, medium, fine rectangles + final integral symbol
        n_values = [4, 8, 16]
        header_anim = 0.6 + 0.5 + 0.7
        per_step = max(1.0, (duration - header_anim - 3.0) / (len(n_values) + 1))

        prev_rects = None

        for n in n_values:
            rects = VGroup()
            dx = 1.0 / n
            for k in range(n):
                x_left = k * dx
                x_right = (k + 1) * dx
                # right-rule: height = (x_right)^2
                h = x_right * x_right
                bl = axes.c2p(x_left, 0)
                tr = axes.c2p(x_right, h)
                w = tr[0] - bl[0]
                hh = tr[1] - bl[1]
                rect = Rectangle(
                    width=w,
                    height=hh,
                    stroke_width=1.2,
                    stroke_color=ACCENT_CYAN,
                    fill_color=ACCENT_CYAN,
                    fill_opacity=0.35,
                )
                rect.move_to([(bl[0] + tr[0]) / 2, (bl[1] + tr[1]) / 2, 0])
                rects.add(rect)

            # right-rule sum: sum_{k=1}^{n} (k/n)^2 * (1/n) = (n+1)(2n+1)/(6n²)
            approx = (n + 1) * (2 * n + 1) / (6 * n * n)

            n_label = MathTex(
                rf"n={n}: \;\sum y\,\Delta x \approx {approx:.3f}",
                font_size=24,
                color=ACCENT_CYAN,
            )
            n_label.move_to([-4.8, 1.5, 0])

            if prev_rects is not None:
                self.play(FadeOut(prev_rects), run_time=0.25)
                # clear any previous n_label
                # (we'll overlap; FadeIn after FadeOut keeps it clean)

            self.play(FadeIn(rects), FadeIn(n_label), run_time=min(0.6, per_step * 0.5))
            self.wait(max(0.2, per_step - 0.6))

            prev_rects = rects
            # ensure n_label is replaced each step: remove from previous
            self.remove(n_label)
            # actually keep last one visible; use VGroup to manage
            # (For simplicity, leave; final label below will overlay)

        # Final exact integral
        final = MathTex(
            r"\int_{0}^{1} x^2 \, dx = \frac{1}{3}",
            font_size=34,
            color=ACCENT_GOLD,
        )
        final.move_to([-4.0, 2.55, 0])
        self.play(FadeIn(final), run_time=0.8)
        self.wait(1.5)

    # ------------------------------------------------------------------
    def _build_fundamental_theorem(self):
        duration = self._duration

        title = Text(
            "微分と積分は逆操作 ── 基本定理",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Layout: f(x)  ↔  F(x) = ∫f
        # left box: f(x) = x²
        # right box: F(x) = ∫₀ˣ t² dt = x³/3
        # arrows: d/dx (down) and ∫ (up)

        f_box = MathTex(r"f(x) = x^2", font_size=34, color=ACCENT_CYAN)
        f_box.move_to([-3.5, 1.2, 0])
        self.play(FadeIn(f_box), run_time=0.5)

        F_box = MathTex(
            r"F(x) = \int_{0}^{x} t^2 \, dt = \frac{x^3}{3}",
            font_size=32,
            color=ACCENT_PINK,
        )
        F_box.move_to([3.0, 1.2, 0])
        self.play(FadeIn(F_box), run_time=0.6)

        # Integration arrow: f → F
        int_arrow = Arrow(
            [-1.6, 1.5, 0],
            [1.0, 1.5, 0],
            color=ACCENT_GOLD,
            stroke_width=4,
            buff=0.1,
        )
        int_label = MathTex(r"\int \cdots dx", font_size=26, color=ACCENT_GOLD)
        int_label.next_to(int_arrow, UP, buff=0.15)
        self.play(FadeIn(int_arrow), FadeIn(int_label), run_time=0.7)

        # Differentiation arrow: F → f
        diff_arrow = Arrow(
            [1.0, 0.9, 0],
            [-1.6, 0.9, 0],
            color=ACCENT_GOLD,
            stroke_width=4,
            buff=0.1,
        )
        diff_label = MathTex(r"\frac{d}{dx}", font_size=26, color=ACCENT_GOLD)
        diff_label.next_to(diff_arrow, DOWN, buff=0.15)
        self.play(FadeIn(diff_arrow), FadeIn(diff_label), run_time=0.7)

        # Identity statement
        identity = MathTex(
            r"\frac{d}{dx}\left(\int_{0}^{x} t^2 \, dt\right) = x^2",
            font_size=32,
            color=TEXT_WHITE,
        )
        identity.move_to([0, -0.4, 0])
        self.play(FadeIn(identity), run_time=0.7)

        # Closing line: a structural insight Leibniz's notation makes explicit
        note = Text(
            "記号 dx と ∫ が、この双方向を一目で示す",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.4, 0])
        self.play(FadeIn(note), run_time=0.7)

        anim_total = 0.6 + 0.5 + 0.6 + 0.7 + 0.7 + 0.7 + 0.7
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "tangent_problem": {"people": [], "years": []},
    "differential_notation": {"people": [], "years": ["1684"]},
    "area_integral": {"people": [], "years": []},
    "fundamental_theorem": {"people": [], "years": []},
}

SCENES = {
    "tangent_problem": LeibnizCalculus,
    "differential_notation": LeibnizCalculus,
    "area_integral": LeibnizCalculus,
    "fundamental_theorem": LeibnizCalculus,
}
