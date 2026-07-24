"""
intermediate_value.py - The Intermediate Value Theorem (Cauchy 1821 / Bolzano 1817)

A continuous curve that starts below a target height and ends above it must
cross that height somewhere in between. Cauchy proved this in Cours d'analyse
(1821); Bolzano proved it independently and earlier (1817), in an obscure
pamphlet that went largely unnoticed at the time. This template is the
"what does rigorization actually do" demo for Episode 041 (Cauchy), block 4:
it turns an obvious-looking picture into a statement that follows from the
definition of continuity alone.

Modes:
    crossing (default)
        Axes with a continuous curve y = f(x) on [a, b], a horizontal target
        line at height gamma with f(a) < gamma < f(b). A dot travels along the
        curve from a (below the line) to b (above), and the moment it meets the
        line we mark the crossing point c with f(c) = gamma and drop a vertical
        guide to the x-axis.
        Fixed params: x in [0.3, 3.7], f(x) = 0.6 + 0.55 x + 0.18 sin(1.6 x)
        (strictly increasing, so it crosses gamma exactly once), gamma = 1.5,
        crossing c ~ 1.39 solved by bisection at render time.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -1.9 to +3.05, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: the traveling dot fills the body so there is no static tail.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
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

# Fixed mathematical setup (declared once so docstring and code agree)
_A, _B = 0.3, 3.7
_GAMMA = 1.5


def _f(x):
    return 0.6 + 0.55 * x + 0.18 * math.sin(1.6 * x)


def _solve_crossing(target, lo, hi, iters=60):
    """Bisection for the unique c in [lo, hi] with _f(c) = target."""
    flo = _f(lo) - target
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fmid = _f(mid) - target
        if flo * fmid <= 0:
            hi = mid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)


class IntermediateValue(Scene):
    """Intermediate value theorem - single mode (crossing)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = float(params.get("duration", 30))
        self._build_crossing(duration)

    def _build_crossing(self, duration):
        # --- titles ---
        title = Text("中間値の定理", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        subtitle = Text(
            "── 連続なら、途中の値は飛び越せない", font=FONT, font_size=22, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)

        # --- axes + curve ---
        axes = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 3, 1],
            x_length=7.2,
            y_length=3.8,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0, 0.25, 0])
        curve = axes.plot(_f, x_range=[_A, _B], color=ACCENT_GOLD, stroke_width=3.5)
        self.play(FadeIn(axes), run_time=0.5)
        self.play(Create(curve), run_time=1.3)

        # --- endpoints: A below the line, B above ---
        a_pt = axes.c2p(_A, _f(_A))
        b_pt = axes.c2p(_B, _f(_B))
        a_dot = Dot(a_pt, color=ACCENT_PINK, radius=0.08)
        b_dot = Dot(b_pt, color=ACCENT_CYAN, radius=0.08)
        a_lab = MathTex(r"f(a)", font_size=26, color=ACCENT_PINK)
        a_lab.next_to(a_dot, LEFT + UP * 0.4, buff=0.1)
        b_lab = MathTex(r"f(b)", font_size=26, color=ACCENT_CYAN)
        b_lab.next_to(b_dot, UP, buff=0.12)
        self.play(FadeIn(a_dot), FadeIn(a_lab), run_time=0.4)
        self.play(FadeIn(b_dot), FadeIn(b_lab), run_time=0.4)

        below = Text("下から", font=FONT, font_size=20, color=ACCENT_PINK)
        below.next_to(a_dot, DOWN, buff=0.18)
        above = Text("上へ", font=FONT, font_size=20, color=ACCENT_CYAN)
        above.next_to(b_dot, RIGHT, buff=0.12)
        self.play(FadeIn(below), FadeIn(above), run_time=0.4)

        # --- target line gamma ---
        line_l = axes.c2p(_A, _GAMMA)
        line_r = axes.c2p(_B, _GAMMA)
        gamma_line = DashedLine(line_l, line_r, color=TEXT_WHITE, stroke_width=2.5)
        gamma_lab = MathTex(r"\gamma", font_size=30, color=TEXT_WHITE)
        gamma_lab.next_to(gamma_line, LEFT, buff=0.15)
        target_note = Text("目標の高さ", font=FONT, font_size=20, color=TEXT_DIM)
        target_note.next_to(gamma_lab, UP, buff=0.12)
        self.play(FadeIn(gamma_line), FadeIn(gamma_lab), FadeIn(target_note), run_time=0.6)

        # --- traveling dot fills the body (no static tail) ---
        c_val = _solve_crossing(_GAMMA, _A, _B)
        tracker = ValueTracker(_A)
        mover = always_redraw(
            lambda: Dot(
                axes.c2p(tracker.get_value(), _f(tracker.get_value())),
                color=ACCENT_GOLD,
                radius=0.10,
            )
        )
        self.add(mover)

        used = 0.7 + 0.5 + 1.3 + 0.4 + 0.4 + 0.4 + 0.6
        coda = 2.5
        motion = max(3.0, duration - used - coda)
        m1 = motion * 0.58
        m2 = motion * 0.42

        # a -> c : approach the line
        self.play(tracker.animate.set_value(c_val), run_time=m1, rate_func=linear)

        # crossing reveal
        c_pt = axes.c2p(c_val, _GAMMA)
        c_dot = Dot(c_pt, color=ACCENT_PINK, radius=0.10)
        drop = DashedLine(c_pt, axes.c2p(c_val, 0), color=ACCENT_PINK, stroke_width=2.2)
        c_axis = MathTex(r"c", font_size=28, color=ACCENT_PINK)
        c_axis.next_to(axes.c2p(c_val, 0), DOWN, buff=0.14)
        fc_eq = MathTex(r"f(c) = \gamma", font_size=30, color=ACCENT_PINK)
        fc_eq.move_to([-4.4, 2.1, 0])
        must = Text("必ず、ここを通る", font=FONT, font_size=22, color=ACCENT_GOLD)
        must.move_to([-4.4, 1.5, 0])
        self.play(FadeIn(c_dot), Create(drop), FadeIn(c_axis), FadeIn(fc_eq), run_time=0.7)
        self.play(FadeIn(must), run_time=0.4)

        # c -> b : continue past the line
        self.play(tracker.animate.set_value(_B), run_time=m2, rate_func=linear)

        self.wait(coda)


# ---------------------------------------------------------------------------
# Factual-claim metadata (read by qa_manim_consistency.py).
# The scene renders only mathematical symbols (gamma, f, a, b, c) and generic
# Japanese labels; no person names or years appear on screen.
# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "crossing": {"people": [], "years": []},
}

SCENES = {
    "crossing": IntermediateValue,
}
