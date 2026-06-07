"""
weierstrass_function.py - Weierstrass's everywhere-continuous nowhere-differentiable function

On 18 July 1872, Weierstrass presented to the Königliche Akademie der
Wissenschaften (Royal Prussian Academy) in Berlin the function
    f(x) = sum_{n=0}^infty  a^n cos(b^n pi x),
where 0 < a < 1, b is a positive odd integer, and ab > 1 + (3/2) pi. The
series converges uniformly (since a < 1) so f is continuous everywhere, yet
the term-by-term derivative has amplitude (ab)^n which diverges, and f turns
out to have no finite derivative at any point.

Visualization parameters used: a = 0.5, b = 13 (so ab = 6.5 > 1 + 3pi/2 ~= 5.71,
satisfying the original Weierstrass condition; minimum b = 7 also satisfies it
if a is close enough to 1 (specifically a > (1 + 3*pi/2)/7 ~= 0.816), but
b = 13 gives clearer visual fractal structure at low partial-sum orders). Hardy (1916) later proved the function is still nowhere
differentiable for any ab >= 1, but this template stays with the original
condition.

Modes:
    intuition
        Smooth functions sin(x) and 0.6*x have tangent lines at every point.
        We show sin(x) on a small axes, then animate tangent line touching at
        x = 0.6, 1.2, 1.8, 2.4 to illustrate the 19th-century intuition that
        continuous functions are (almost) differentiable.
        Fixed params: x_range [0, 3.1], tangent positions [0.6, 1.2, 1.8, 2.4].

    partial_sum_build
        Plot partial sums f_N(x) = sum_{n=0}^{N} a^n cos(b^n pi x) for
        N = 1, 2, 3, 4, with a = 0.5 and b = 13. Each successive partial sum
        is overlaid in a fading earlier-pass color (TEXT_DIM), with the newest
        N highlighted in ACCENT_CYAN. Vertical bar at right shows the value of
        N currently being drawn.
        Fixed params: a = 0.5, b = 13, x_range [-1, 1], plot points 600 per
        partial sum.

    zoom_in
        Plot f_4(x) (4 terms of the series with a = 0.5, b = 13) on three
        successive zoom levels: x in [-1, 1], then [-0.15, 0.15], then
        [-0.02, 0.02]. Each zoom reveals similarly jagged structure, conveying
        self-affinity. A small ratio label shows the magnification: 1x, ~7x,
        ~50x.
        Fixed params: a = 0.5, b = 13, N = 4, zoom factors approximately 1,
        7, 50.

    no_tangent
        Pick a point x0 = 0.0 on f_4(x). Try to draw a tangent: compute the
        secant slope (f(x0+h)-f(x0))/h for h = 0.10, 0.05, 0.02, 0.01 and
        draw the four secants. The secant slopes oscillate wildly instead of
        converging to a single value, illustrating that no finite derivative
        exists. Show the four slope values numerically.
        Fixed params: a = 0.5, b = 13, N = 4, x0 = 0.0, h-values = [0.10,
        0.05, 0.02, 0.01].

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 028 (Weierstrass), pillar B - the Weierstrass function.
"""

import math

from manim import (
    Arrow,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

# Original Weierstrass paper parameters (1872). a = 0.5, b = 13 satisfies
# 0 < a < 1, b odd positive integer, ab = 6.5 > 1 + 3*pi/2 ~= 5.71.
WF_A = 0.5
WF_B = 13


def _weierstrass_partial(x, N, a=WF_A, b=WF_B):
    """Partial sum sum_{n=0}^{N} a^n cos(b^n pi x)."""
    s = 0.0
    for n in range(N + 1):
        s += (a ** n) * math.cos((b ** n) * math.pi * x)
    return s


class WeierstrassFunction(Scene):
    """Weierstrass's everywhere-continuous nowhere-differentiable function."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "partial_sum_build")
        self._duration = float(params.get("duration", 30))

        if mode == "intuition":
            self._build_intuition()
        elif mode == "zoom_in":
            self._build_zoom_in()
        elif mode == "no_tangent":
            self._build_no_tangent()
        else:
            self._build_partial_sum_build()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_intuition(self):
        duration = self._duration
        title = self._title("『連続なら接線が引ける』── 19世紀の素朴な直観")
        self.play(FadeIn(title), run_time=0.6)

        axes = Axes(
            x_range=[0, 3.2, 1],
            y_range=[-1.2, 1.2, 1],
            x_length=8.0,
            y_length=2.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0, 0.5, 0])
        curve = axes.plot(lambda x: math.sin(x), x_range=[0, 3.1], color=ACCENT_CYAN, stroke_width=3.0)
        self.play(Create(axes), Create(curve), run_time=0.9)

        # Animate four tangent lines at x = 0.6, 1.2, 1.8, 2.4
        for x0 in (0.6, 1.2, 1.8, 2.4):
            y0 = math.sin(x0)
            slope = math.cos(x0)
            # Draw short tangent of length ~1.0 in x-units
            dx = 0.5
            p1 = axes.c2p(x0 - dx, y0 - slope * dx)
            p2 = axes.c2p(x0 + dx, y0 + slope * dx)
            tangent = Line(p1, p2, color=ACCENT_GOLD, stroke_width=3.0)
            dot = Dot(axes.c2p(x0, y0), color=ACCENT_PINK, radius=0.07)
            self.play(FadeIn(tangent), FadeIn(dot), run_time=0.45)

        msg = Text(
            "── けれども、本当にいつもそうだろうか？",
            font=FONT, font_size=22, color=ACCENT_PINK,
        )
        msg.move_to([0, -1.85, 0])
        self.play(FadeIn(msg), run_time=0.7)

        anim_total = 0.6 + 0.9 + 0.45 * 4 + 0.7
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_partial_sum_build(self):
        duration = self._duration
        title = self._title("ヴァイエルシュトラス関数の部分和を重ねる")
        self.play(FadeIn(title), run_time=0.6)

        # Compact formula header (title at y=3.0, formula y=2.50, params y=2.10)
        # so the curve area (top y <= 1.3) does NOT overlap any text.
        formula = MathTex(
            r"f_N(x) = \sum_{n=0}^{N} a^n \cos(b^n \pi x)",
            font_size=22, color=ACCENT_GOLD,
        )
        formula.move_to([0, 2.50, 0])
        params_lbl = MathTex(
            r"a = \tfrac{1}{2},\; b = 13",
            font_size=20, color=ACCENT_PINK,
        )
        params_lbl.move_to([0, 2.05, 0])
        self.play(FadeIn(formula), FadeIn(params_lbl), run_time=0.6)

        # Axes centered lower so curve top stays well below the formula.
        # y_length 2.6 + center y=-0.30 → top y = 1.00 (clear of 2.05 params).
        axes = Axes(
            x_range=[-1.0, 1.0, 0.5],
            y_range=[-1.8, 1.8, 1],
            x_length=8.0,
            y_length=2.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0, -0.30, 0])
        self.play(Create(axes), run_time=0.6)

        # Plot partial sums N = 1, 2, 3, 4
        prev_curves = VGroup()
        for N in (1, 2, 3, 4):
            curve = axes.plot(
                lambda x, N=N: _weierstrass_partial(x, N),
                x_range=[-1.0, 1.0, 1.0 / 600],
                color=ACCENT_CYAN, stroke_width=2.4,
            )
            # Counter showing current N — placed at lower-right margin.
            n_label = MathTex(f"N = {N}", font_size=26, color=ACCENT_GOLD)
            n_label.move_to([4.6, -1.85, 0])

            # Fade previous (last drawn) curves to dim, then draw new
            if len(prev_curves) > 0:
                self.play(prev_curves.animate.set_color(TEXT_DIM).set_stroke(opacity=0.35), run_time=0.3)
            if N == 1:
                self.play(Create(curve), FadeIn(n_label), run_time=0.9)
                cur_n_label = n_label
            else:
                self.play(Create(curve), n_label.animate.move_to([4.6, -1.85, 0]), run_time=0.9)
                self.remove(cur_n_label)
                self.add(n_label)
                cur_n_label = n_label
            prev_curves.add(curve)

        anim_total = 0.6 + 0.6 + 0.6 + (0.3 + 0.9) * 4
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_zoom_in(self):
        duration = self._duration
        title = self._title("拡大しても、振動は消えない")
        self.play(FadeIn(title), run_time=0.6)

        # Three small axes side by side
        zoom_levels = [
            (1.0, "1倍"),
            (0.15, "約 7倍"),
            (0.02, "約 50倍"),
        ]
        x_centers = [-4.0, 0.0, 4.0]
        N = 4
        groups = VGroup()

        for (half_range, label_text), cx in zip(zoom_levels, x_centers):
            axes = Axes(
                x_range=[-half_range, half_range, half_range],
                y_range=[-1.8, 1.8, 1],
                x_length=3.2,
                y_length=2.4,
                tips=False,
                axis_config={"color": TEXT_DIM, "stroke_width": 1.4},
            )
            axes.move_to([cx, 0.40, 0])
            curve = axes.plot(
                lambda x: _weierstrass_partial(x, N),
                x_range=[-half_range, half_range, half_range / 200],
                color=ACCENT_CYAN, stroke_width=2.0,
            )
            zoom_lbl = Text(
                label_text, font=FONT, font_size=22, color=ACCENT_GOLD,
            )
            zoom_lbl.move_to([cx, -1.20, 0])
            groups.add(VGroup(axes, curve, zoom_lbl))

        for grp in groups:
            self.play(Create(grp[0]), Create(grp[1]), FadeIn(grp[2]), run_time=0.9)

        msg = Text(
            "── どの倍率にも、同じような細かい揺れが現れる",
            font=FONT, font_size=20, color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.9 * 3 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_no_tangent(self):
        duration = self._duration
        title = self._title("接線は引けない ── 差分商が振動する")
        self.play(FadeIn(title), run_time=0.6)

        axes = Axes(
            x_range=[-0.3, 0.3, 0.1],
            y_range=[-1.0, 2.0, 1],
            x_length=6.5,
            y_length=2.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([-1.6, 0.5, 0])
        N = 4
        curve = axes.plot(
            lambda x: _weierstrass_partial(x, N),
            x_range=[-0.30, 0.30, 0.30 / 400],
            color=ACCENT_CYAN, stroke_width=2.2,
        )
        self.play(Create(axes), Create(curve), run_time=0.8)

        x0 = 0.0
        y0 = _weierstrass_partial(x0, N)
        x0_dot = Dot(axes.c2p(x0, y0), color=ACCENT_PINK, radius=0.08)
        x0_label = MathTex(r"x_0 = 0", font_size=22, color=ACCENT_PINK)
        x0_label.move_to([axes.c2p(0, 0)[0], axes.c2p(0, 0)[1] - 0.30, 0])
        self.play(FadeIn(x0_dot), FadeIn(x0_label), run_time=0.5)

        # Secants
        colors = [ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK, TEXT_WHITE]
        h_vals = [0.10, 0.05, 0.02, 0.01]
        slope_rows = VGroup()
        for h, col in zip(h_vals, colors):
            y_h = _weierstrass_partial(x0 + h, N)
            slope = (y_h - y0) / h
            # Draw secant through (x0, y0) and (x0+h, y_h), extended slightly
            ext = 0.15
            p1 = axes.c2p(x0 - ext, y0 - slope * ext)
            p2 = axes.c2p(x0 + h + ext, y_h + slope * ext)
            secant = Line(p1, p2, color=col, stroke_width=2.4, stroke_opacity=0.85)
            self.play(Create(secant), run_time=0.35)

            row = MathTex(
                rf"h = {h:.2f},\;\;\text{{slope}} \approx {slope:+.2f}",
                font_size=22, color=col,
            )
            row.move_to([3.2, 1.7 - 0.45 * len(slope_rows), 0])
            slope_rows.add(row)
            self.play(FadeIn(row), run_time=0.25)

        verdict = Text(
            "h を小さくしても傾きは一つに定まらない", font=FONT,
            font_size=20, color=ACCENT_PINK,
        )
        verdict.move_to([0, -1.85, 0])
        self.play(FadeIn(verdict), run_time=0.6)

        anim_total = 0.6 + 0.8 + 0.5 + (0.35 + 0.25) * 4 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "intuition": {"people": [], "years": []},
    "partial_sum_build": {"people": [], "years": []},
    "zoom_in": {"people": [], "years": []},
    "no_tangent": {"people": [], "years": []},
}

SCENES = {
    "intuition": WeierstrassFunction,
    "partial_sum_build": WeierstrassFunction,
    "zoom_in": WeierstrassFunction,
    "no_tangent": WeierstrassFunction,
}
