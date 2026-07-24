"""
infinitesimal_ghost.py - Berkeley's "ghost of departed quantities" (1734)

The secant-to-tangent derivation of a derivative exposes the paradox Berkeley
attacked in The Analyst (1734): to find the slope of y = x^2 we form the
difference quotient ((x+dx)^2 - x^2)/dx, DIVIDE by dx (so dx must be nonzero),
simplify to 2x + dx, and THEN set dx = 0 to get 2x. The increment dx is treated
as nonzero (to divide) and then as zero (to discard) - "the ghost of departed
quantities." Motivation visual for Episode 041 (Cauchy), block 2 (the crisis
Cauchy's limit later resolves).

Modes:
    ghost (default)
        Parabola y = x^2 on the left with a fixed point P(1,1) and a sliding
        point Q(1+dx, (1+dx)^2); the secant PQ flattens into the tangent as
        dx -> 0 (slope 2+dx -> 2). On the right the algebra reveals:
        ((x+dx)^2 - x^2)/dx = (2x dx + dx^2)/dx = 2x + dx ; dx -> 0 => 2x, with
        the contradiction marked: "divide: dx != 0" vs "discard: dx = 0".
        Fixed params: f(x)=x^2, x0=1, dx slides 1.0 -> 0.1.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -1.85 to +3.05, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: the sliding secant fills the body (no static tail).
"""

from manim import (
    LEFT,
    UP,
    Axes,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Scene,
    Text,
    ValueTracker,
    always_redraw,
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

_X0 = 1.0


def _f(x):
    return x * x


class InfinitesimalGhost(Scene):
    """Berkeley's ghost of departed quantities - single mode (ghost)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = float(params.get("duration", 30))
        self._build_ghost(duration)

    def _build_ghost(self, duration):
        title = Text("消えゆく量の亡霊", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        subtitle = Text(
            "── 割るときは0でない、消すときは0", font=FONT, font_size=21, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)

        # --- axes + parabola (left) ---
        axes = Axes(
            x_range=[0, 2.4, 1],
            y_range=[0, 4.4, 1],
            x_length=4.8,
            y_length=3.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([-3.0, -0.05, 0])
        curve = axes.plot(_f, x_range=[0, 2.1], color=ACCENT_GOLD, stroke_width=3.5)
        eq = MathTex(r"y = x^{2}", font_size=26, color=ACCENT_GOLD)
        eq.next_to(axes.c2p(2.1, _f(2.1)), UP, buff=0.05)
        self.play(FadeIn(axes), run_time=0.4)
        self.play(Create(curve), FadeIn(eq), run_time=1.0)

        # --- fixed point P ---
        p_pt = axes.c2p(_X0, _f(_X0))
        p_dot = Dot(p_pt, color=ACCENT_PINK, radius=0.08)
        p_lab = MathTex(r"P", font_size=26, color=ACCENT_PINK).next_to(p_dot, LEFT, buff=0.12)
        self.play(FadeIn(p_dot), FadeIn(p_lab), run_time=0.4)

        # --- sliding point Q + secant (always_redraw) ---
        dx = ValueTracker(1.0)

        def q_screen():
            x = _X0 + dx.get_value()
            return axes.c2p(x, _f(x))

        def secant():
            d = dx.get_value()
            qx = _X0 + d
            slope = (_f(qx) - _f(_X0)) / d
            xl, xr = _X0 - 0.4, qx + 0.4
            pl = axes.c2p(xl, _f(_X0) + slope * (xl - _X0))
            pr = axes.c2p(xr, _f(_X0) + slope * (xr - _X0))
            return Line(pl, pr, color=ACCENT_CYAN, stroke_width=3)

        q_dot = always_redraw(lambda: Dot(q_screen(), color=ACCENT_CYAN, radius=0.08))
        q_lab = always_redraw(
            lambda: MathTex(r"Q", font_size=26, color=ACCENT_CYAN).next_to(q_screen(), UP, buff=0.1)
        )
        secant_line = always_redraw(secant)
        self.add(secant_line, q_dot, q_lab)
        self.wait(0.3)

        # --- algebra panel (right), revealed step by step ---
        col = 3.5
        a1 = MathTex(
            r"\frac{(x+\Delta x)^{2} - x^{2}}{\Delta x}", font_size=30, color=TEXT_WHITE
        ).move_to([col, 1.95, 0])
        a2 = MathTex(
            r"= \frac{2x\,\Delta x + (\Delta x)^{2}}{\Delta x}", font_size=30, color=TEXT_WHITE
        ).move_to([col, 0.95, 0])
        a3 = MathTex(r"= 2x + \Delta x", font_size=32, color=ACCENT_CYAN).move_to([col, 0.05, 0])
        div_note = Text("Δx で割る（Δx≠0）", font=FONT, font_size=20, color=ACCENT_PINK).move_to(
            [col + 0.15, -0.55, 0]
        )
        self.play(FadeIn(a1), run_time=0.6)
        self.play(FadeIn(a2), run_time=0.6)
        self.play(FadeIn(a3), FadeIn(div_note), run_time=0.7)

        # --- slide dx -> 0 (secant flattens to tangent); reveal the discard step ---
        a4 = MathTex(r"\Delta x \to 0 \;\Rightarrow\; 2x", font_size=32, color=ACCENT_GOLD).move_to(
            [col, -1.05, 0]
        )
        kill_note = Text("Δx を消す（Δx=0）", font=FONT, font_size=20, color=ACCENT_PINK).move_to(
            [col + 0.15, -1.6, 0]
        )

        used = 0.7 + 0.4 + 1.0 + 0.4 + 0.3 + 0.6 + 0.6 + 0.7
        coda = 2.2
        motion = max(3.0, duration - used - coda)
        self.play(
            dx.animate.set_value(0.1),
            FadeIn(a4),
            run_time=motion * 0.7,
            rate_func=linear,
        )
        self.play(FadeIn(kill_note), run_time=motion * 0.3)

        self.wait(coda)


# ---------------------------------------------------------------------------
# Factual-claim metadata (read by qa_manim_consistency.py).
# Renders only math symbols (x, dx, P, Q, y=x^2) and generic Japanese labels;
# no person names or years appear on screen.
# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "ghost": {"people": [], "years": []},
}

SCENES = {
    "ghost": InfinitesimalGhost,
}
