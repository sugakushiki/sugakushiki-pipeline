"""
st_petersburg_risk.py - The St. Petersburg paradox and logarithmic utility

Episode 043 (Daniel Bernoulli), blocks 1 and 3 (the risk / expected-utility axis).
A coin game pays a pot that starts at 2 and doubles on every head, ending at the
first tail. The prize 2^n occurs with probability 1/2^n, so every term contributes
2^n * (1/2^n) = 1 to the expected value, and 1 + 1 + 1 + ... diverges to infinity --
yet nobody pays much to play. Daniel Bernoulli's resolution: people maximise not
expected money but expected utility, with utility growing like the logarithm of
wealth (diminishing marginal utility). The problem was first posed by Nicolaus
Bernoulli (1713) and a utility solution was anticipated by Cramer (1728); that
credit belongs in the narration, not on screen.

Modes:
    paradox (default)
        The doubling-pot table: rows 2 x 1/2 = 1, 4 x 1/4 = 1, 8 x 1/8 = 1, ...
        A running partial sum ticks upward without bound while the price a person
        will actually pay stays small. Expected value = infinity.
        Fixed params: prizes 2,4,8,16; probabilities 1/2,1/4,1/8,1/16; each term = 1;
        partial sum N after N terms -> infinity.
    utility
        The concave curve u = log(w). Two equal wealth steps (1->2 and 5->6) give a
        large then a small rise in utility, showing diminishing marginal utility.
        A dot traces the curve.
        Fixed params: u = log(w); steps w:1->2 (rise ~0.69) and w:5->6 (rise ~0.18).

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.9 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math

from manim import (
    DOWN,
    RIGHT,
    UP,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Integer,
    MathTex,
    Scene,
    Text,
    ValueTracker,
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


class StPetersburgRisk(Scene):
    """St. Petersburg paradox (paradox) and logarithmic utility (utility)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "paradox")
        duration = float(params.get("duration", 26))
        if mode == "utility":
            self._build_utility(duration)
        else:
            self._build_paradox(duration)

    # ---------------------------------------------------------------- paradox
    def _build_paradox(self, duration):
        title = Text("倍々の賭け、その期待値は", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        header = Text("賞金 × その確率 = 寄与", font=FONT, font_size=22, color=TEXT_DIM)
        header.move_to([-1.5, 2.15, 0])
        self.play(FadeIn(header), run_time=0.4)

        row_tex = [
            r"2 \times \tfrac{1}{2} = 1",
            r"4 \times \tfrac{1}{4} = 1",
            r"8 \times \tfrac{1}{8} = 1",
            r"16 \times \tfrac{1}{16} = 1",
            r"\vdots",
        ]
        rows = VGroup(*[MathTex(t, font_size=30, color=ACCENT_CYAN) for t in row_tex])
        rows.arrange(DOWN, buff=0.22, aligned_edge=RIGHT)
        rows.move_to([-1.5, 0.5, 0])

        # running partial-sum readout on the right
        sum_label = Text("ここまでの合計", font=FONT, font_size=20, color=TEXT_DIM)
        sum_label.move_to([2.9, 1.15, 0])
        n_tracker = ValueTracker(1)
        counter = Integer(1, font_size=30).set_color(ACCENT_GOLD)

        def _upd(m):
            m.set_value(int(round(n_tracker.get_value())))
            m.move_to([2.9, 0.45, 0])

        counter.add_updater(_upd)

        per = 0.45
        for r in rows:
            self.play(FadeIn(r), run_time=per)
        self.play(FadeIn(sum_label), run_time=0.4)
        self.add(counter)

        sum_eq = MathTex(r"1 + 1 + 1 + \cdots = \infty", font_size=36, color=ACCENT_PINK)
        sum_eq.move_to([0, -1.35, 0])
        self.play(FadeIn(sum_eq), run_time=0.8)

        caption = Text(
            "足すほど際限なく増え、期待値は無限大", font=FONT, font_size=20, color=TEXT_WHITE
        )
        caption.move_to([0, -1.85, 0])
        self.play(FadeIn(caption), run_time=0.5)

        used = 0.7 + 0.4 + per * len(rows) + 0.4 + 0.8 + 0.5
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        self.play(n_tracker.animate.set_value(40), run_time=motion, rate_func=lambda t: t)
        counter.clear_updaters()
        self.wait(coda)

    # ---------------------------------------------------------------- utility
    def _build_utility(self, duration):
        title = Text("効用は富の対数", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[0, 8, 2],
            y_range=[0, 2.2, 1],
            x_length=6.8,
            y_length=2.9,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0.2, 0.15, 0])
        x_lab = Text("富 w", font=FONT, font_size=22, color=TEXT_DIM)
        x_lab.next_to(axes.x_axis, RIGHT, buff=0.12)
        y_lab = Text("効用 u", font=FONT, font_size=22, color=TEXT_DIM)
        y_lab.next_to(axes.y_axis, UP, buff=0.1)
        self.play(FadeIn(axes), FadeIn(x_lab), FadeIn(y_lab), run_time=0.8)

        def u(w):
            return math.log(w)

        curve = axes.plot(u, x_range=[1.0, 8.0], color=ACCENT_CYAN, stroke_width=3.5)
        self.play(Create(curve), run_time=1.3)

        formula = MathTex(r"u = \log(w)", font_size=32, color=ACCENT_CYAN)
        formula.move_to([2.7, 1.95, 0])
        self.play(FadeIn(formula), run_time=0.6)

        # two equal wealth steps: 1->2 (big rise) and 5->6 (small rise)
        steps = [(1.0, 2.0, ACCENT_GOLD), (5.0, 6.0, ACCENT_PINK)]
        for w0, w1, col in steps:
            d0 = Dot(axes.c2p(w0, u(w0)), color=col, radius=0.05)
            d1 = Dot(axes.c2p(w1, u(w1)), color=col, radius=0.05)
            guide = DashedLine(axes.c2p(w1, u(w0)), axes.c2p(w1, u(w1)), color=col, stroke_width=3)
            base = DashedLine(axes.c2p(w0, u(w0)), axes.c2p(w1, u(w0)), color=col, stroke_width=2)
            rise = MathTex(rf"\Delta u \approx {u(w1) - u(w0):.2f}", font_size=24, color=col)
            rise.next_to(guide, RIGHT, buff=0.12)
            self.play(FadeIn(d0), FadeIn(d1), FadeIn(base), run_time=0.4)
            self.play(Create(guide), FadeIn(rise), run_time=0.6)

        caption = Text(
            "富が増えるほど、同じ +1 の値打ちは小さくなる",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        )
        caption.move_to([0, -1.7, 0])
        self.play(FadeIn(caption), run_time=0.6)

        # tracer dot along the curve fills the remaining time
        w_tracker = ValueTracker(1.0)
        tracer = Dot(color=TEXT_WHITE, radius=0.07)

        def _trace(m):
            w = w_tracker.get_value()
            m.move_to(axes.c2p(w, u(w)))

        tracer.add_updater(_trace)
        self.add(tracer)

        used = 0.7 + 0.8 + 1.3 + 0.6 + len(steps) * 1.0 + 0.6
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        self.play(w_tracker.animate.set_value(8.0), run_time=motion, rate_func=lambda t: t)
        tracer.clear_updaters()
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "paradox": {"people": [], "years": []},
    "utility": {"people": [], "years": []},
}

SCENES = {
    "paradox": StPetersburgRisk,
    "utility": StPetersburgRisk,
}
