"""
sde_black_scholes.py - The SDE dX=mu dt+sigma dW, and taming chance in Black-Scholes (数学史記)

Episode 054 (Kiyosi Itô). Two intuition-level views of what stochastic
differential equations are, and how Itô's calculus underlies option pricing.

Modes:
    sde (default)
        The stochastic differential equation dX = mu dt + sigma dW as the sum of
        a smooth drift (mu dt) and Brownian noise (sigma dW). Several sample paths
        from the same equation share the common drift yet fan out with different
        wiggles -- the language of anything driven by continuous chance.
        Fixed params: deterministic paths from numpy rng seeds 3/11/21; drift
        d(x)=0.25+0.16x on x in [-4.5, 4.3]; diffusion scale 0.045.
    bs
        Black-Scholes: a stock price as geometric Brownian motion; applying Itô's
        lemma to the option value V brings the correction (1/2)sigma^2 S^2 V_SS;
        delta-hedging cancels the random sigma dW term, leaving the deterministic
        Black-Scholes PDE. Chance is tamed by Itô's calculus. (No PDE derivation,
        just the intuition that the random term is struck out.)
        Fixed params: geometric BM path from seed 5; the dW term is struck through.

All Japanese labels use Text(font=FONT). MathTex holds only ASCII/symbols, no
Japanese. Y range: about -2.05 to +3.05. No trailing FadeOut. Randomness is a
fixed numpy seed (deterministic render).
"""

import numpy as np
from manim import (
    Create,
    FadeIn,
    Line,
    MathTex,
    Scene,
    SurroundingRectangle,
    Text,
    VMobject,
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
    pace,
)

config.background_color = BG_COLOR


def _polyline(pts, color, width=2.2, smooth=False):
    m = VMobject(color=color, stroke_width=width)
    corners = [np.array([x, y, 0.0]) for x, y in pts]
    if smooth:
        m.set_points_smoothly(corners)
    else:
        m.set_points_as_corners(corners)
    return m


class SdeBlackScholes(Scene):
    """SDE dX=mu dt+sigma dW and how delta-hedging cancels chance in Black-Scholes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "sde")
        duration = float(params.get("duration", 26))
        if mode == "bs":
            self._build_bs(duration)
        else:
            self._build_sde(duration)

    # ------------------------------------------------------------------- sde
    def _build_sde(self, duration):
        title = Text(
            "偶然の運動方程式",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "なめらかな流れと、ブラウン運動の揺らぎの和",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.5, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        eq = MathTex(
            r"dX = ", r"\mu\,dt", r"\;+\;", r"\sigma\,dW", font_size=38, color=TEXT_WHITE
        ).move_to([0, 1.95, 0])
        eq[1].set_color(ACCENT_CYAN)  # drift
        eq[3].set_color(ACCENT_PINK)  # diffusion

        xs = np.linspace(-4.5, 4.3, 300)
        drift = 0.25 + 0.16 * xs
        drift_line = _polyline(
            list(zip(xs, drift, strict=True)), ACCENT_CYAN, width=3.0, smooth=True
        )
        drift_lab = Text(
            "なめらかな流れ（ドリフト）",
            font=FONT,
            font_size=17,
            color=ACCENT_CYAN,
        ).move_to([-2.7, 1.15, 0])
        diff_lab = Text(
            "ブラウン運動の揺らぎ（拡散）",
            font=FONT,
            font_size=17,
            color=ACCENT_PINK,
        ).move_to([2.3, -1.15, 0])

        colors = [TEXT_WHITE, ACCENT_GOLD, ACCENT_PINK]
        seeds = [3, 11, 21]
        paths = []
        for c, s in zip(colors, seeds, strict=True):
            rng = np.random.default_rng(s)
            wig = np.cumsum(rng.standard_normal(len(xs))) * 0.045
            wig = wig - wig[0]
            paths.append(_polyline(list(zip(xs, drift + wig, strict=True)), c, width=1.8))

        concl = Text(
            "連続な偶然に駆動される、あらゆる現象の言語",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        ).move_to([0, -1.9, 0])

        coda = 3.2
        rt = pace(
            duration,
            [0.7, 1.0, 0.9, 0.9, 0.9, 1.0],
            intro=0.6 + 0.5,
            coda=coda,
        )
        self.play(FadeIn(eq), run_time=rt[0])
        self.play(Create(drift_line), FadeIn(drift_lab), run_time=rt[1])
        self.play(Create(paths[0]), FadeIn(diff_lab), run_time=rt[2])
        self.play(Create(paths[1]), run_time=rt[3])
        self.play(Create(paths[2]), run_time=rt[4])
        self.play(FadeIn(concl), run_time=rt[5])
        self.wait(coda)

    # -------------------------------------------------------------------- bs
    def _build_bs(self, duration):
        title = Text(
            "ウォール街を動かした一行",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "オプション価格に伊藤の補題を当てると、偶然が消える",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.5, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        # geometric Brownian motion: a stock price rising while wiggling
        xs = np.linspace(-4.6, 4.6, 300)
        tnorm = (xs + 4.6) / 9.2
        rng = np.random.default_rng(5)
        wig = np.cumsum(rng.standard_normal(len(xs))) * 0.04
        wig = wig - wig.mean()
        wig = wig / (np.abs(wig).max() + 1e-9) * 0.30
        # keep the price in a high band (y ~ 1.2..1.9) so the wiggling path never
        # crosses the dV equation at y=0.35 below
        price = 1.52 + 0.13 * tnorm + wig
        price_path = _polyline(list(zip(xs, price, strict=True)), ACCENT_CYAN, width=2.4)
        price_lab = Text(
            "株価（幾何ブラウン運動）",
            font=FONT,
            font_size=17,
            color=ACCENT_CYAN,
        ).move_to([-3.1, 2.18, 0])

        # Itô applied to the option value V: drift bracket (with correction) + dW term
        ito_v = MathTex(
            r"dV=\left(\frac{\partial V}{\partial t}+\tfrac12\sigma^2 S^2\frac{\partial^2 V}{\partial S^2}\right)dt",
            r"+\,\sigma S\frac{\partial V}{\partial S}\,dW",
            font_size=27,
            color=TEXT_WHITE,
        ).move_to([0, 0.35, 0])
        ito_v[1].set_color(ACCENT_PINK)
        corr_note = Text(
            "括弧の中に、伊藤の補題の《補正項》が現れる",
            font=FONT,
            font_size=16,
            color=ACCENT_GOLD,
        ).move_to([0, -0.15, 0])

        # delta-hedge strikes out the dW term
        strike = Line(
            ito_v[1].get_left() + np.array([0.05, 0.0, 0.0]),
            ito_v[1].get_right() + np.array([-0.05, 0.0, 0.0]),
            color=ACCENT_PINK,
            stroke_width=5,
        )
        hedge_note = Text(
            "保有量を調整して、偶然の項を打ち消す",
            font=FONT,
            font_size=17,
            color=ACCENT_PINK,
        ).move_to([0, -0.72, 0])

        # the deterministic Black-Scholes PDE that remains
        bs_pde = MathTex(
            r"\frac{\partial V}{\partial t}+\tfrac12\sigma^2 S^2\frac{\partial^2 V}{\partial S^2}"
            r"+rS\frac{\partial V}{\partial S}-rV=0",
            font_size=28,
            color=TEXT_WHITE,
        ).move_to([0, -1.35, 0])
        bs_box = SurroundingRectangle(bs_pde, color=ACCENT_GOLD, buff=0.12)
        tamed = Text(
            "偶然の項が消え、確定的な方程式が残る ── 偶然を飼いならす",
            font=FONT,
            font_size=18,
            color=ACCENT_GOLD,
        ).move_to([0, -1.9, 0])

        coda = 3.5
        rt = pace(
            duration,
            [1.0, 0.9, 0.6, 0.9, 0.6, 1.0, 0.7, 0.9],
            intro=0.6 + 0.5,
            coda=coda,
        )
        self.play(Create(price_path), FadeIn(price_lab), run_time=rt[0])
        self.play(FadeIn(ito_v), run_time=rt[1])
        self.play(FadeIn(corr_note), run_time=rt[2])
        self.play(FadeIn(hedge_note), run_time=rt[3])
        self.play(Create(strike), run_time=rt[4])
        self.play(FadeIn(bs_pde), Create(bs_box), run_time=rt[5])
        self.wait(rt[6])
        self.play(FadeIn(tamed), run_time=rt[7])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "sde": {"people": [], "years": []},
    "bs": {"people": [], "years": []},
}

SCENES = {
    "sde": SdeBlackScholes,
    "bs": SdeBlackScholes,
}
