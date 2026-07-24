"""
newtons_method.py - Newton's iterative root finding for 数学史記

To solve an equation, Newton started from a guess and improved it step by step.
Geometrically: draw the tangent at the current point; where it crosses the
x-axis is the next, better guess. The method converges quadratically.

IMPORTANT (staged attribution, verified): the modern iteration that uses the
derivative explicitly,  x_{n+1} = x_n - f(x_n)/f'(x_n), is NOT due to Newton
alone. Newton (in De Analysi) gave a polynomial-only prototype; Raphson (1690)
streamlined the iteration; Simpson (1740) first cast it in the modern
derivative form. The name "Newton's method" is therefore a partial misnomer,
and this template shows the three-stage attribution in the `attribution` mode.

Modes:
    iteration   - Parabola f(x) = x^2 - 2 on Axes; from x0 = 2 the tangent
                  iteration converges to sqrt(2) ~= 1.41421356.
                  Verified values: x0=2, x1=3/2=1.5, x2=17/12~=1.41667,
                  x3=577/408~=1.414216. Tangents + verticals drawn step by step
                  (steps spread across the duration); target sqrt(2) marked.
    attribution - Modern formula x_{n+1}=x_n - f(x_n)/f'(x_n) on top, then the
                  three-stage attribution revealed one by one:
                  Newton (polynomial prototype) -> Raphson (streamlined) ->
                  Simpson (general, derivative form).

Duration-aware: reads target duration from _manim_params.json; steps/reveals
fill the scene with a fixed ~2.5s coda (no long static tail).
Y range: title at +2.9, all content within -1.9 .. +2.3.

Used by: Episode 037 (Newton), math pillar 3 (iterative root finding).
"""

import numpy as np
from manim import (
    Axes,
    DashedLine,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

ROOT = np.sqrt(2.0)  # 1.41421356...


def _f(x):
    return x * x - 2.0


def _next(x):
    return x - (x * x - 2.0) / (2.0 * x)


class NewtonsMethod(Scene):
    """Newton's iterative root finding and its staged attribution."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 26)
        mode = params.get("mode", "iteration")

        if mode == "attribution":
            self._build_attribution()
        else:
            self._build_iteration()

    # ------------------------------------------------------------------
    # Mode: iteration
    # ------------------------------------------------------------------
    def _build_iteration(self):
        duration = self._duration

        title = Text(
            "ニュートン法 ── 接線で答えに近づく",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        recur = MathTex(
            r"x_{n+1} = x_n - \frac{x_n^{2}-2}{2x_n}",
            font_size=30,
            color=ACCENT_CYAN,
        )
        recur.move_to([0, 2.2, 0])

        axes = Axes(
            x_range=[1.1, 2.15, 0.25],
            y_range=[-0.6, 2.4, 0.5],
            x_length=7.2,
            y_length=3.5,
            axis_config={
                "include_numbers": False,
                "include_tip": True,
                "stroke_width": 2,
                "color": EDGE_COLOR,
            },
        )
        axes.move_to([0, -0.25, 0])

        graph = axes.plot(_f, x_range=[1.19, 2.1, 0.01], color=ACCENT_CYAN, stroke_width=3)
        # f(x)=x^2-2 label and the value list both sit in the empty upper-left
        # region (the curve is low on the left), stacked, clear of the iteration
        # tangents/dots in the centre-right and of the recurrence at the top.
        graph_lbl = MathTex(r"f(x)=x^2-2", font_size=26, color=ACCENT_CYAN)
        graph_lbl.move_to([-2.5, 1.5, 0])

        # Target root sqrt(2). Keep the label at y=-1.72 (>= -2.0) so it never
        # enters the subtitle band around y=-2.2 (the old next_to(...,-0.55) put
        # it at ~-2.2 and collided with the burned-in subtitles).
        root_line = DashedLine(
            axes.c2p(ROOT, -0.1), axes.c2p(ROOT, 0.55), color=ACCENT_GOLD, stroke_width=2
        )
        root_lbl = MathTex(r"\sqrt{2}", font_size=30, color=ACCENT_GOLD)
        root_lbl.move_to([axes.c2p(ROOT, 0.0)[0], -1.72, 0])

        # Iteration values
        xs = [2.0]
        for _ in range(3):
            xs.append(_next(xs[-1]))
        # xs = [2.0, 1.5, 1.41666..., 1.414215...]

        value_strs = [
            r"x_0 = 2",
            r"x_1 = \tfrac{3}{2} = 1.5",
            r"x_2 = \tfrac{17}{12} \approx 1.41667",
            r"x_3 = \tfrac{577}{408} \approx 1.414216",
        ]
        values = VGroup(*[MathTex(s, font_size=22, color=TEXT_WHITE) for s in value_strs])
        values.arrange(np.array([0, -1, 0]), aligned_edge=np.array([-1, 0, 0]), buff=0.2)
        values.move_to([-2.5, 0.35, 0])
        values[0].set_color(ACCENT_PINK)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(recur), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(graph), FadeIn(graph_lbl), run_time=1.0)
        self.play(FadeIn(root_line), FadeIn(root_lbl), run_time=0.6)
        used = 0.6 + 0.6 + 1.0 + 0.6

        # First point x0
        p0 = Dot(axes.c2p(xs[0], _f(xs[0])), color=ACCENT_PINK, radius=0.08)
        x0mark = Dot(axes.c2p(xs[0], 0.0), color=ACCENT_PINK, radius=0.06)
        self.play(FadeIn(p0), FadeIn(x0mark), FadeIn(values[0]), run_time=0.7)
        used += 0.7

        coda = 2.5
        n_steps = 3
        step_budget = max(1.2, (duration - used - coda) / n_steps)

        for k in range(n_steps):
            xk, xk1 = xs[k], xs[k + 1]
            pk = axes.c2p(xk, _f(xk))
            x_int = axes.c2p(xk1, 0.0)
            tangent = Line(pk, x_int, color=ACCENT_GOLD, stroke_width=2.5)
            vline = DashedLine(
                axes.c2p(xk1, 0.0), axes.c2p(xk1, _f(xk1)), color=ACCENT_PINK, stroke_width=2
            )
            p_next = Dot(axes.c2p(xk1, _f(xk1)), color=ACCENT_PINK, radius=0.08)
            x_dot = Dot(axes.c2p(xk1, 0.0), color=ACCENT_CYAN, radius=0.06)

            self.play(FadeIn(tangent), run_time=0.6)
            self.play(FadeIn(x_dot), FadeIn(values[k + 1]), run_time=0.5)
            self.play(FadeIn(vline), FadeIn(p_next), run_time=0.5)
            if k == n_steps - 1:
                self.play(
                    Indicate(values[k + 1], color=ACCENT_GOLD, scale_factor=1.2), run_time=0.6
                )
                spent = 0.6 + 0.5 + 0.5 + 0.6
            else:
                spent = 0.6 + 0.5 + 0.5
            rest = max(0.0, step_budget - spent)
            if rest > 0:
                self.wait(rest)

        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: attribution
    # ------------------------------------------------------------------
    def _build_attribution(self):
        duration = self._duration

        title = Text(
            "『ニュートン法』ができるまで",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.9, 0])

        formula = MathTex(
            r"x_{n+1} = x_n - \frac{f(x_n)}{f'(x_n)}",
            font_size=44,
            color=ACCENT_CYAN,
        )
        formula.move_to([0, 1.85, 0])

        rows = [
            ("ニュートン", "多項式の根を近づける原型", ACCENT_PINK),
            ("ラフソン", "反復をすっきり整理 (1690)", TEXT_WHITE),
            ("シンプソン", "導関数を使い一般の式へ (1740)", ACCENT_GOLD),
        ]
        cards = VGroup()
        y0 = 0.65
        for i, (name, desc, color) in enumerate(rows):
            name_t = Text(name, font=FONT, font_size=30, color=color)
            arrow = Text("──", font=FONT, font_size=26, color=TEXT_DIM)
            desc_t = Text(desc, font=FONT, font_size=24, color=TEXT_WHITE)
            line = VGroup(name_t, arrow, desc_t).arrange(buff=0.25)
            line.move_to([0, y0 - i * 0.85, 0])
            cards.add(line)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(formula), run_time=0.8)
        used = 0.7 + 0.8

        coda = 2.5
        per = max(1.2, (duration - used - coda) / len(cards))
        for line in cards:
            self.play(FadeIn(line), run_time=0.7)
            rest = max(0.0, per - 0.7)
            if rest > 0:
                self.wait(rest)

        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# iteration shows only math; attribution shows the three names + years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "iteration": {"people": [], "years": []},
    "attribution": {
        "people": [
            ["ニュートン", "Newton"],
            ["ラフソン", "Raphson"],
            ["シンプソン", "Simpson"],
        ],
        "years": ["1690", "1740"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "iteration": {
        "class": "NewtonsMethod",
        "params": {"mode": "iteration"},
        "description": "Tangent iteration on f(x)=x^2-2 converging to sqrt(2): 2 -> 1.5 -> 17/12 -> 577/408",
    },
    "attribution": {
        "class": "NewtonsMethod",
        "params": {"mode": "attribution"},
        "description": "Staged attribution of the modern formula: Newton (prototype) -> Raphson -> Simpson",
    },
}
