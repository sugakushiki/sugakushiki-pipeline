"""
card_shuffle_histogram.py - Filling a hole in a proof by measuring it (Student, 1908)

Gosset could not prove that his distribution was exact - his 1908 paper says so
outright ("although we have no actual proof we shall assume it") - so he checked
it by hand. He copied a table of 3000 records onto 3000 pieces of cardboard,
shuffled them thoroughly, drew them at random and took every consecutive four as
one sample, 750 samples in all, then compared the 750 results with the curve his
theory predicted. It is one of the earliest examples of what was later called the
Monte Carlo method.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    shuffle   - One sample, end to end: the deck of 3000 cards on the left, four
                cards drawn out, their mean and s computed, and the single point
                that one sample contributes to the histogram.
                Fixed params (numpy default_rng(1908), hardcoded so the render is
                reproducible): the four values 67, 65, 68, 66; mean 66.5; s 1.29;
                population mean 68 (known, because the whole deck is in hand);
                resulting statistic -2.32. Number line spans -5..+5.
    histogram - The check itself. 20 bins of width 0.5 over -5..+5 fill up in six
                waves (125, 250, 375, 500, 625, 750 samples), then the theoretical
                curve for 4 observations is laid over the finished bars.
                Fixed params (numpy default_rng(1908025), counts hardcoded): final
                counts peak at 136 and 132 in the two central bins; 745 of the 750
                samples land inside the frame and 5 fall outside (largest 9.9); the
                theory curve is the t density for 3 degrees of freedom scaled by
                750 x 0.5 = 375, whose peak 137.9 matches the tallest bar.

No on-screen person names or years - the numbers shown are the deck size, the
sample counts and the sample statistics documented above - so
LINT_FACTUAL_CLAIMS is empty for both modes.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    Create,
    Dot,
    FadeIn,
    LaggedStart,
    Line,
    MathTex,
    Rectangle,
    ReplacementTransform,
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
    pace,
)

config.background_color = BG_COLOR

CARD_FILL = "#252540"

# --- fixed data: one drawn sample of four, and the population mean -------------
_DRAWN = [67, 65, 68, 66]
_MEAN = "66.5"
_S = "1.29"
_MU = "68"
_STAT = "-2.32"

# --- fixed data: cumulative bin counts, 20 bins of width 0.5 over [-5, 5] ------
_STAGES = [
    (125, [0, 0, 3, 0, 2, 3, 5, 5, 15, 24, 32, 9, 10, 9, 2, 3, 0, 0, 1, 0]),
    (250, [0, 0, 3, 2, 6, 11, 6, 18, 27, 46, 55, 27, 15, 17, 5, 8, 1, 0, 1, 0]),
    (375, [0, 2, 5, 3, 13, 15, 12, 29, 42, 60, 71, 50, 26, 21, 8, 10, 4, 0, 1, 1]),
    (500, [1, 3, 5, 5, 15, 17, 21, 46, 52, 82, 90, 70, 33, 28, 10, 12, 5, 0, 1, 1]),
    (625, [1, 3, 5, 5, 19, 20, 27, 63, 63, 104, 112, 89, 43, 32, 12, 14, 6, 0, 2, 2]),
    (750, [3, 3, 6, 6, 20, 24, 34, 68, 80, 132, 136, 99, 54, 37, 16, 16, 6, 0, 3, 2]),
]
_BIN_W = 0.5
_X_MIN = -5.0
_Y_MAX = 145.0  # count axis ceiling; tallest bar is 136, theory peak 137.9
_THEORY_SCALE = 750 * _BIN_W  # counts = scale * density


def _t_pdf(x, nu):
    c = math.gamma((nu + 1) / 2.0) / (math.sqrt(nu * math.pi) * math.gamma(nu / 2.0))
    return c * (1.0 + x * x / nu) ** (-(nu + 1) / 2.0)


class CardShuffleHistogram(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "shuffle")
        duration = params.get("duration", 26)
        if mode == "histogram":
            self._histogram(duration)
        else:
            self._shuffle(duration)

    # -- mode: shuffle --------------------------------------------------------
    def _shuffle(self, duration):
        title = Text("3000枚の厚紙から、4枚を引く", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        deck_c = LEFT * 5.0 + UP * 1.15
        deck = VGroup()
        for i in range(9):
            card = Rectangle(
                width=1.05,
                height=1.45,
                color=EDGE_COLOR,
                stroke_width=2,
                fill_color=CARD_FILL,
                fill_opacity=1.0,
            )
            card.move_to(deck_c + RIGHT * (i * 0.035) + UP * (i * 0.035))
            deck.add(card)
        deck_lab = Text("3000枚", font=FONT, font_size=22, color=TEXT_WHITE)
        deck_lab.move_to(deck_c + DOWN * 1.15)

        known = Text("全部の平均は分かっている", font=FONT, font_size=20, color=ACCENT_GOLD)
        known.move_to(LEFT * 1.45 + UP * 2.42)
        known_mu = MathTex(rf"\mu = {_MU}", font_size=28, color=ACCENT_GOLD)
        known_mu.move_to(RIGHT * 1.75 + UP * 2.42)

        row_head = Text("引いた4枚", font=FONT, font_size=20, color=TEXT_DIM)
        row_head.move_to(LEFT * 2.55 + UP * 1.15)

        cards = VGroup()
        numbers = VGroup()
        slots_x = [-0.85, 0.25, 1.35, 2.45]
        for x, v in zip(slots_x, _DRAWN, strict=True):
            card = Rectangle(
                width=0.95,
                height=1.3,
                color=ACCENT_CYAN,
                stroke_width=2.5,
                fill_color=CARD_FILL,
                fill_opacity=1.0,
            )
            card.move_to(deck_c)
            cards.add(card)
            num = MathTex(str(v), font_size=32, color=TEXT_WHITE)
            num.move_to(RIGHT * x + UP * 1.15)
            numbers.add(num)

        mean_t = MathTex(rf"\bar{{x}} = {_MEAN}", font_size=30, color=ACCENT_CYAN)
        mean_t.move_to(LEFT * 1.35 + UP * 0.22)
        s_t = MathTex(rf"s = {_S}", font_size=30, color=ACCENT_CYAN)
        s_t.move_to(RIGHT * 1.55 + UP * 0.22)

        stat_t = MathTex(
            rf"\frac{{\bar{{x}}-\mu}}{{s/\sqrt{{n}}}} = {_STAT}", font_size=34, color=ACCENT_PINK
        )
        stat_t.move_to(RIGHT * 0.1 + DOWN * 0.62)

        # number line: -5 .. +5
        nl_scale = 0.72
        nl = Line(
            RIGHT * (-5 * nl_scale) + DOWN * 1.52,
            RIGHT * (5 * nl_scale) + DOWN * 1.52,
            color=EDGE_COLOR,
            stroke_width=2,
        )
        ticks = VGroup()
        for tv in (-4, -2, 0, 2, 4):
            tx = tv * nl_scale
            ticks.add(
                Line(
                    RIGHT * tx + DOWN * 1.42,
                    RIGHT * tx + DOWN * 1.62,
                    color=EDGE_COLOR,
                    stroke_width=2,
                )
            )
            lab = MathTex(str(tv), font_size=22, color=TEXT_DIM)
            lab.move_to(RIGHT * tx + DOWN * 1.88)
            ticks.add(lab)
        point = Dot(RIGHT * (-2.32 * nl_scale) + DOWN * 1.52, color=ACCENT_PINK, radius=0.11)
        point_lab = MathTex(_STAT, font_size=26, color=ACCENT_PINK)
        point_lab.move_to(RIGHT * (-2.32 * nl_scale) + DOWN * 1.12)

        rep_a = Text("これを", font=FONT, font_size=22, color=TEXT_WHITE)
        rep_a.move_to(RIGHT * 4.85 + UP * 0.55)
        rep_b = Text("750回", font=FONT, font_size=30, color=ACCENT_GOLD)
        rep_b.move_to(RIGHT * 4.85 + UP * 0.08)
        rep_c = Text("くり返した", font=FONT, font_size=22, color=TEXT_WHITE)
        rep_c.move_to(RIGHT * 4.85 + DOWN * 0.42)

        rt = pace(duration, [1.0, 1.15, 0.9, 1.0, 1.0, 1.0], intro=1.8, coda=3.0)
        self.play(FadeIn(title), FadeIn(deck), FadeIn(deck_lab), run_time=1.0)
        self.play(FadeIn(known), FadeIn(known_mu), FadeIn(row_head), run_time=0.8)
        self.play(
            LaggedStart(
                *[
                    card.animate.move_to(RIGHT * x + UP * 1.15)
                    for card, x in zip(cards, slots_x, strict=True)
                ],
                lag_ratio=0.35,
            ),
            run_time=rt[0],
        )
        self.play(FadeIn(numbers), run_time=rt[1])
        self.play(FadeIn(mean_t), FadeIn(s_t), run_time=rt[2])
        self.play(FadeIn(stat_t), run_time=rt[3])
        self.play(Create(nl), FadeIn(ticks), FadeIn(point), FadeIn(point_lab), run_time=rt[4])
        self.play(FadeIn(rep_a), FadeIn(rep_b), FadeIn(rep_c), run_time=rt[5])
        self.wait(3.0)

    # -- mode: histogram ------------------------------------------------------
    def _histogram(self, duration):
        title = Text("750組が、曲線に積み上がった", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        axes = Axes(
            x_range=[-5, 5, 1],
            y_range=[0, _Y_MAX, 25],
            x_length=10.4,
            y_length=3.1,
            tips=False,
            axis_config={"stroke_width": 2, "color": EDGE_COLOR},
            x_axis_config={"numbers_to_include": [-4, -2, 0, 2, 4], "font_size": 20},
            y_axis_config={"include_ticks": False, "stroke_width": 0},
        )
        axes.move_to(UP * 0.10)

        y_len = 3.1
        bar_w = abs(axes.c2p(_BIN_W, 0)[0] - axes.c2p(0.0, 0)[0])

        def bar_height(count):
            return max(float(count), 0.5) / _Y_MAX * y_len

        centers = [_X_MIN + (i + 0.5) * _BIN_W for i in range(20)]

        bars = VGroup()
        for cx in centers:
            h = bar_height(0)
            rect = Rectangle(
                width=bar_w * 0.92,
                height=h,
                color=ACCENT_CYAN,
                stroke_width=1.5,
                fill_color=ACCENT_CYAN,
                fill_opacity=0.55,
            )
            rect.move_to(axes.c2p(cx, 0) + UP * (h / 2))
            bars.add(rect)

        def counter(n):
            t = Text(f"{n}組", font=FONT, font_size=26, color=ACCENT_GOLD)
            t.move_to(RIGHT * 4.75 + UP * 2.42)
            return t

        outside = Text("枠の外に5組", font=FONT, font_size=19, color=TEXT_DIM)
        outside.move_to(LEFT * 4.55 + UP * 2.42)

        theory = axes.plot(
            lambda x: _THEORY_SCALE * _t_pdf(x, 3),
            x_range=[-5, 5, 0.02],
            color=ACCENT_GOLD,
            stroke_width=4,
        )
        theory_lab = Text("理論の曲線", font=FONT, font_size=21, color=ACCENT_GOLD)
        theory_lab.move_to(axes.c2p(2.75, 62))

        # The centre at y = 2.0 grazes the peak bar (top y ~= 1.23) and the apex of
        # the theory curve, so the closing line goes over the low left-hand bars.
        closing = Text("証明がないので、確かめた", font=FONT, font_size=23, color=TEXT_WHITE)
        closing.move_to(LEFT * 4.35 + UP * 1.75)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.15, 1.1], intro=1.8, coda=3.0)
        self.play(FadeIn(title), Create(axes), run_time=1.0)
        self.play(FadeIn(bars), FadeIn(outside), run_time=0.8)

        count_lab = counter(0)
        self.add(count_lab)
        for i, (n, counts) in enumerate(_STAGES):
            anims = []
            for rect, cx, cnt in zip(bars, centers, counts, strict=True):
                h = bar_height(cnt)
                anims.append(
                    rect.animate.stretch_to_fit_height(h).move_to(axes.c2p(cx, 0) + UP * (h / 2))
                )
            new_lab = counter(n)
            anims.append(ReplacementTransform(count_lab, new_lab))
            self.play(*anims, run_time=rt[i])
            count_lab = new_lab

        self.play(Create(theory), FadeIn(theory_lab), run_time=rt[6])
        self.play(FadeIn(closing), run_time=rt[7])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; the numbers shown are the deck size (3000), the number of
# samples (750), the drawn values and the sample statistics listed in the docstring.
LINT_FACTUAL_CLAIMS = {
    "shuffle": {"people": [], "years": []},
    "histogram": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "shuffle": CardShuffleHistogram,
    "histogram": CardShuffleHistogram,
}
