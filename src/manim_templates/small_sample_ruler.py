"""
small_sample_ruler.py - When the ruler itself wobbles (Student's small-sample problem)

The accuracy of a mean is measured in units of the spread. In practice the true
spread sigma is unknown, so it is estimated by s from the sample at hand. With
hundreds of observations s is essentially sigma and nothing goes wrong; with four
observations s itself swings by a factor of two or three, so the quantity
(xbar - mu)/(s/sqrt(n)) is no longer normal - its tails are much heavier. That is
the distribution Gosset derived in 1908.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    ruler    - Five samples of 4 drawn from the SAME standard-normal population.
               Each row: a strip plot of its four values, the length of its
               estimated s as a bar, and the numeric s. A gold reference bar and a
               dashed vertical line mark the true sigma = 1, so the eye sees the
               bars fall short of / overshoot it.
               Fixed params (numpy default_rng(19080609), hardcoded so the render
               is reproducible): s = 1.32, 1.00, 0.81, 1.03, 0.48; min 0.48,
               max 1.32, ratio 2.8x. Bar scale 1.7 scene units per 1.0 sigma,
               strip scale 0.42 per unit.
    tails    - The consequence, with numbers. Standard normal (cyan) and t with 3
               degrees of freedom (pink) on one axis; the tails beyond +/-2 are
               shaded and labelled.
               Fixed params: two-sided P(|X| > 2) = 4.55% for the normal and
               13.93% for t(3) (about 3x); two-sided 5% critical value 1.96 vs
               3.182. n = 4 means 3 degrees of freedom.
    converge - Why the problem is a small-sample problem. The t curve is replaced
               in turn by 3 -> 9 -> 29 degrees of freedom against a fixed dashed
               normal, with the tail percentage updating each time.
               Fixed params: 13.93% (df 3) -> 7.66% (df 9) -> 5.49% (df 29) ->
               4.55% (normal).

All tail percentages and critical values were computed with scipy.stats
(norm.sf / t.sf / t.isf) and are hardcoded here so the screen cannot drift from
the narration.

No on-screen person names or years - every label is either statistical
vocabulary or one of the numbers above - so LINT_FACTUAL_CLAIMS is empty for
every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Axes,
    Create,
    DashedLine,
    DashedVMobject,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
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

# --- fixed data: five samples of 4 from default_rng(19080609), sigma = 1 -------
_SAMPLES = [
    ([0.41, -2.24, 0.67, -0.26], 1.32),
    ([1.10, -0.16, 1.41, -0.69], 1.00),
    ([0.92, -0.24, -1.01, 0.20], 0.81),
    ([0.76, -1.06, -1.21, 0.51], 1.03),
    ([-0.09, -1.13, -0.15, -0.44], 0.48),
]

# --- fixed numbers: two-sided tail beyond 2, and the 5% critical value ---------
_TAIL_NORMAL = "4.55"
_TAIL_T3 = "13.93"
_CONVERGE = [(3, "13.93"), (9, "7.66"), (29, "5.49")]


def _norm_pdf(x):
    return math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)


def _t_pdf(x, nu):
    c = math.gamma((nu + 1) / 2.0) / (math.sqrt(nu * math.pi) * math.gamma(nu / 2.0))
    return c * (1.0 + x * x / nu) ** (-(nu + 1) / 2.0)


class SmallSampleRuler(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "ruler")
        duration = params.get("duration", 26)
        if mode == "tails":
            self._tails(duration)
        elif mode == "converge":
            self._converge(duration)
        else:
            self._ruler(duration)

    # -- shared axis for the two curve modes ----------------------------------
    def _curve_axes(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 0.45, 0.1],
            x_length=9.4,
            y_length=2.9,
            tips=False,
            axis_config={"stroke_width": 2, "color": EDGE_COLOR, "include_ticks": True},
            x_axis_config={"numbers_to_include": [-4, -2, 0, 2, 4], "font_size": 20},
            y_axis_config={"include_ticks": False, "stroke_width": 0},
        )
        axes.move_to(UP * 0.05)
        return axes

    # -- mode: ruler ----------------------------------------------------------
    def _ruler(self, duration):
        title = Text("ものさし自身が、測るたびに変わる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        bar_x0 = -1.5  # every bar starts here
        bar_scale = 1.7  # scene units per 1.0 of spread
        strip_cx = -3.3  # centre of each strip plot
        strip_scale = 0.42
        num_x = 1.55  # numeric s column
        sigma_y = 2.35
        row_ys = [1.55, 1.00, 0.45, -0.10, -0.65]

        # true sigma = 1: gold reference bar + dashed line down the rows
        sigma_bar = Line(
            RIGHT * bar_x0 + UP * sigma_y,
            RIGHT * (bar_x0 + bar_scale) + UP * sigma_y,
            color=ACCENT_GOLD,
            stroke_width=9,
        )
        sigma_lab = Text("本当のばらつき（未知）", font=FONT, font_size=20, color=ACCENT_GOLD)
        sigma_lab.move_to(RIGHT * (strip_cx - 0.15) + UP * sigma_y)
        sigma_num = MathTex(r"\sigma = 1.00", font_size=26, color=ACCENT_GOLD)
        sigma_num.move_to(RIGHT * num_x + UP * sigma_y)
        guide = DashedLine(
            RIGHT * (bar_x0 + bar_scale) + UP * (sigma_y - 0.22),
            RIGHT * (bar_x0 + bar_scale) + UP * (row_ys[-1] - 0.3),
            color=ACCENT_GOLD,
            stroke_width=2,
            dash_length=0.09,
        )
        guide.set_opacity(0.55)

        head = Text("4個の標本から見積もると", font=FONT, font_size=20, color=TEXT_DIM)
        head.move_to(RIGHT * (strip_cx - 0.15) + UP * 1.98)

        rows = []
        for (vals, s_val), y in zip(_SAMPLES, row_ys, strict=True):
            grp = VGroup()
            base = Line(
                RIGHT * (strip_cx - 1.15) + UP * y,
                RIGHT * (strip_cx + 1.15) + UP * y,
                color=EDGE_COLOR,
                stroke_width=1.5,
            )
            grp.add(base)
            for v in vals:
                grp.add(
                    Dot(
                        RIGHT * (strip_cx + v * strip_scale) + UP * y,
                        color=ACCENT_CYAN,
                        radius=0.075,
                    )
                )
            grp.add(
                Line(
                    RIGHT * bar_x0 + UP * y,
                    RIGHT * (bar_x0 + s_val * bar_scale) + UP * y,
                    color=ACCENT_CYAN,
                    stroke_width=9,
                )
            )
            num = MathTex(rf"s = {s_val:.2f}", font_size=26, color=TEXT_WHITE)
            num.move_to(RIGHT * num_x + UP * y)
            grp.add(num)
            rows.append(grp)

        note_a = Text("0.48 から 1.32 まで動く", font=FONT, font_size=21, color=ACCENT_PINK)
        note_a.move_to(RIGHT * 4.35 + UP * 0.85)
        note_b = Text("同じ母集団なのに 2.8倍", font=FONT, font_size=21, color=ACCENT_PINK)
        note_b.move_to(RIGHT * 4.35 + UP * 0.40)

        closing = Text(
            "割る数が揺れれば、確からしさも揺れる", font=FONT, font_size=22, color=TEXT_WHITE
        )
        closing.move_to(DOWN * 1.62)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0, 0.9, 1.1], intro=1.9, coda=3.0)
        self.play(FadeIn(title), FadeIn(head), run_time=0.9)
        self.play(
            FadeIn(sigma_lab), Create(sigma_bar), FadeIn(sigma_num), Create(guide), run_time=1.0
        )
        for i, grp in enumerate(rows):
            self.play(FadeIn(grp), run_time=rt[i])
        self.play(FadeIn(note_a), FadeIn(note_b), run_time=rt[5])
        self.play(FadeIn(closing), run_time=rt[6])
        self.wait(3.0)

    # -- mode: tails ----------------------------------------------------------
    def _tails(self, duration):
        title = Text("同じ「2の外」が、3倍になる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        stat = MathTex(r"\frac{\bar{x}-\mu}{s/\sqrt{n}}", font_size=34, color=TEXT_WHITE)
        stat.move_to(LEFT * 5.1 + UP * 2.35)

        axes = self._curve_axes()
        normal = axes.plot(_norm_pdf, x_range=[-4, 4, 0.02], color=ACCENT_CYAN, stroke_width=4)
        tcurve = axes.plot(
            lambda x: _t_pdf(x, 3), x_range=[-4, 4, 0.02], color=ACCENT_PINK, stroke_width=4
        )

        leg_n = Text("正規分布", font=FONT, font_size=21, color=ACCENT_CYAN)
        leg_n.move_to(RIGHT * 3.95 + UP * 2.45)
        leg_t = Text("標本4個の分布", font=FONT, font_size=21, color=ACCENT_PINK)
        leg_t.move_to(RIGHT * 3.95 + UP * 2.02)

        cut_r = DashedVMobject(
            Line(axes.c2p(2, 0), axes.c2p(2, 0.40), color=TEXT_DIM, stroke_width=2), num_dashes=11
        )
        cut_l = DashedVMobject(
            Line(axes.c2p(-2, 0), axes.c2p(-2, 0.40), color=TEXT_DIM, stroke_width=2), num_dashes=11
        )
        cut_lab = MathTex(r"\pm 2", font_size=28, color=TEXT_DIM)
        cut_lab.move_to(axes.c2p(2, 0.40) + UP * 0.22)

        area_n_r = axes.get_area(normal, x_range=(2, 4), color=ACCENT_CYAN, opacity=0.55)
        area_n_l = axes.get_area(normal, x_range=(-4, -2), color=ACCENT_CYAN, opacity=0.55)
        area_t_r = axes.get_area(tcurve, x_range=(2, 4), color=ACCENT_PINK, opacity=0.45)
        area_t_l = axes.get_area(tcurve, x_range=(-4, -2), color=ACCENT_PINK, opacity=0.45)

        pct_n = MathTex(rf"{_TAIL_NORMAL}\%", font_size=30, color=ACCENT_CYAN)
        pct_n.move_to(axes.c2p(3.3, 0.16))
        lead_n = Line(
            pct_n.get_bottom() + DOWN * 0.06,
            axes.c2p(2.55, 0.012),
            color=ACCENT_CYAN,
            stroke_width=2,
        )
        pct_t = MathTex(rf"{_TAIL_T3}\%", font_size=30, color=ACCENT_PINK)
        pct_t.move_to(axes.c2p(3.3, 0.30))
        lead_t = Line(
            pct_t.get_bottom() + DOWN * 0.06,
            axes.c2p(2.45, 0.045),
            color=ACCENT_PINK,
            stroke_width=2,
        )

        # Kept clear of the x = -2 cut line (scene x ~= -2.35): the widest item here
        # is the critical-value row, so it sits furthest left.
        note_a = Text("標本が4個なら", font=FONT, font_size=21, color=TEXT_WHITE)
        note_a.move_to(LEFT * 3.85 + UP * 1.15)
        note_b = Text("外れる確率は3倍", font=FONT, font_size=21, color=TEXT_WHITE)
        note_b.move_to(LEFT * 3.85 + UP * 0.72)
        crit = MathTex(r"1.96 \;\longrightarrow\; 3.182", font_size=28, color=ACCENT_GOLD)
        crit.move_to(LEFT * 3.95 + UP * 0.18)
        crit_lab = Text("5%の境界", font=FONT, font_size=19, color=ACCENT_GOLD)
        crit_lab.move_to(LEFT * 3.95 + DOWN * 0.22)

        rt = pace(duration, [1.0, 1.0, 0.9, 1.0, 1.1, 1.0, 1.0], intro=1.8, coda=3.0)
        self.play(FadeIn(title), FadeIn(stat), run_time=0.9)
        self.play(Create(axes), run_time=0.9)
        self.play(Create(normal), FadeIn(leg_n), run_time=rt[0])
        self.play(Create(cut_l), Create(cut_r), FadeIn(cut_lab), run_time=rt[1])
        self.play(FadeIn(area_n_l), FadeIn(area_n_r), FadeIn(pct_n), Create(lead_n), run_time=rt[2])
        self.play(Create(tcurve), FadeIn(leg_t), run_time=rt[3])
        self.play(FadeIn(area_t_l), FadeIn(area_t_r), FadeIn(pct_t), Create(lead_t), run_time=rt[4])
        self.play(FadeIn(note_a), FadeIn(note_b), run_time=rt[5])
        self.play(FadeIn(crit), FadeIn(crit_lab), run_time=rt[6])
        self.wait(3.0)

    # -- mode: converge -------------------------------------------------------
    def _converge(self, duration):
        title = Text("標本が増えれば、正規分布に戻る", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        axes = self._curve_axes()
        normal = DashedVMobject(
            axes.plot(_norm_pdf, x_range=[-4, 4, 0.02], color=ACCENT_GOLD, stroke_width=4),
            num_dashes=110,
        )
        leg_n = Text("正規分布", font=FONT, font_size=21, color=ACCENT_GOLD)
        leg_n.move_to(RIGHT * 3.95 + UP * 2.45)

        cut_r = DashedVMobject(
            Line(axes.c2p(2, 0), axes.c2p(2, 0.40), color=TEXT_DIM, stroke_width=2), num_dashes=11
        )
        cut_lab = MathTex(r"+2", font_size=26, color=TEXT_DIM)
        cut_lab.move_to(axes.c2p(2, 0.40) + UP * 0.22)

        def df_label(nu):
            t = Text(f"標本 {nu + 1}個（自由度 {nu}）", font=FONT, font_size=22, color=ACCENT_PINK)
            t.move_to(LEFT * 3.5 + UP * 1.15)
            return t

        def pct_label(txt, color):
            t = MathTex(rf"{txt}\%", font_size=32, color=color)
            t.move_to(LEFT * 3.5 + UP * 0.62)
            return t

        nu0, p0 = _CONVERGE[0]
        curve = axes.plot(
            lambda x: _t_pdf(x, nu0), x_range=[-4, 4, 0.02], color=ACCENT_PINK, stroke_width=4
        )
        dfl = df_label(nu0)
        pctl = pct_label(p0, ACCENT_PINK)
        tail_head = Text("2の外に出る確率", font=FONT, font_size=19, color=TEXT_DIM)
        tail_head.move_to(LEFT * 3.5 + UP * 0.14)

        # Weights: initial reveal, then (label swap, curve morph) x 3, then closing.
        # The labels are swapped by a SHORT fade rather than morphed for the whole
        # step: a 4-second ReplacementTransform between two Japanese labels renders
        # as unreadable half-formed glyphs for most of the scene (seen at t=13s in
        # the first render). Only the curve gets the long run_time.
        rt = pace(duration, [1.0, 0.25, 1.0, 0.25, 1.0, 0.25, 1.0, 0.9], intro=1.9, coda=3.0)
        self.play(FadeIn(title), Create(axes), run_time=1.0)
        self.play(Create(normal), FadeIn(leg_n), Create(cut_r), FadeIn(cut_lab), run_time=0.9)
        # Labels get a SHORT fade of their own inside the group so they are readable
        # for the whole step; only the curve consumes the long run_time. (Passing
        # run_time to self.play() would rescale every child, which is what left the
        # labels at partial opacity for seconds in the first render.)
        self.play(
            AnimationGroup(
                Create(curve, run_time=rt[0]),
                FadeIn(dfl, run_time=0.6),
                FadeIn(pctl, run_time=0.6),
                FadeIn(tail_head, run_time=0.6),
                lag_ratio=0.0,
            )
        )

        for i, (nu, pct) in enumerate(_CONVERGE[1:], start=1):
            nxt = axes.plot(
                lambda x, nu=nu: _t_pdf(x, nu),
                x_range=[-4, 4, 0.02],
                color=ACCENT_PINK,
                stroke_width=4,
            )
            # Bind the new labels to names and carry THOSE forward; re-calling
            # df_label()/pct_label() would leave the on-screen ones behind and stack
            # every generation on top of each other.
            nxt_dfl = df_label(nu)
            nxt_pctl = pct_label(pct, ACCENT_PINK)
            self.play(FadeOut(dfl), FadeOut(pctl), run_time=rt[2 * i - 1])
            self.play(
                AnimationGroup(
                    ReplacementTransform(curve, nxt, run_time=rt[2 * i]),
                    FadeIn(nxt_dfl, run_time=0.5),
                    FadeIn(nxt_pctl, run_time=0.5),
                    lag_ratio=0.0,
                )
            )
            curve = nxt
            dfl = nxt_dfl
            pctl = nxt_pctl

        final_pct = pct_label(_TAIL_NORMAL, ACCENT_GOLD)
        final_df = Text("標本が十分に多いとき", font=FONT, font_size=22, color=ACCENT_GOLD)
        final_df.move_to(LEFT * 3.5 + UP * 1.15)
        self.play(FadeOut(dfl), FadeOut(pctl), run_time=rt[5])
        self.play(
            AnimationGroup(
                FadeIn(final_df, run_time=0.5),
                FadeIn(final_pct, run_time=0.5),
                curve.animate(run_time=rt[6]).set_stroke(opacity=0.35),
                lag_ratio=0.0,
            )
        )

        # Below the axis is the x-number band (y ~= -1.7), so the closing line goes
        # above the plot instead of under it.
        closing = Text(
            "少ないときだけ現れる、ずれだった", font=FONT, font_size=22, color=TEXT_WHITE
        )
        closing.move_to(LEFT * 1.35 + UP * 2.42)
        self.play(FadeIn(closing), run_time=rt[7])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; the only numbers shown are the sample statistics and the
# tail percentages documented in the module docstring.
LINT_FACTUAL_CLAIMS = {
    "ruler": {"people": [], "years": []},
    "tails": {"people": [], "years": []},
    "converge": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "ruler": SmallSampleRuler,
    "tails": SmallSampleRuler,
    "converge": SmallSampleRuler,
}
