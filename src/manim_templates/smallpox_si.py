"""
smallpox_si.py - Daniel Bernoulli's smallpox inoculation analysis (1760)

Episode 043 (Daniel Bernoulli), block 6 (pillar 3). As a physician-mathematician,
Bernoulli built the first mathematical model in epidemiology: he split a population
into those still susceptible to smallpox and those who had survived it and were
immune, and followed them with differential equations. Using Halley's life table he
argued that inoculation was advantageous when its own risk of death was below about
11 percent, raising life expectancy at birth from 26 years 7 months to 29 years 9
months (about three years). The survival curves here are schematic; the life-
expectancy figures and the 11 percent threshold are the verified claims.

Modes:
    survival (default)
        Two survival curves (fraction alive vs age): lower without inoculation,
        higher with inoculation / no smallpox. Annotated life expectancies
        26y7m vs 29y9m. A dot traces the upper curve.
        Fixed params: schematic survival curves; life expectancy 26y7m -> 29y9m.
    threshold
        A 0-20 percent scale of the inoculation's own death risk, split at 11
        percent: below it inoculation is advantageous, above it not.
        Fixed params: break-even at 11 percent.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.6 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math

from manim import (
    RIGHT,
    UP,
    Axes,
    Create,
    Dot,
    FadeIn,
    Line,
    Rectangle,
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


def _s0(a):
    """Schematic survival without inoculation (with smallpox)."""
    return math.exp(-((a / 48.0) ** 1.6))


def _s1(a):
    """Schematic survival with inoculation (no smallpox) -- always above _s0."""
    return math.exp(-((a / 56.0) ** 1.6))


class SmallpoxSI(Scene):
    """Smallpox survival curves (survival) and the 11% threshold (threshold)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "survival")
        duration = float(params.get("duration", 26))
        if mode == "threshold":
            self._build_threshold(duration)
        else:
            self._build_survival(duration)

    # --------------------------------------------------------------- survival
    def _build_survival(self, duration):
        title = Text("接種は寿命をどれだけ延ばすか", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[0, 80, 20],
            y_range=[0, 1, 0.25],
            x_length=6.8,
            y_length=3.0,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([0.2, 0.05, 0])
        x_lab = Text("年齢", font=FONT, font_size=20, color=TEXT_DIM)
        x_lab.next_to(axes.x_axis, RIGHT, buff=0.12)
        y_lab = Text("生存割合", font=FONT, font_size=20, color=TEXT_DIM)
        y_lab.next_to(axes.y_axis, UP, buff=0.1)
        self.play(FadeIn(axes), FadeIn(x_lab), FadeIn(y_lab), run_time=0.8)

        c0 = axes.plot(_s0, x_range=[0, 80], color=ACCENT_PINK, stroke_width=3.2)
        c1 = axes.plot(_s1, x_range=[0, 80], color=ACCENT_GOLD, stroke_width=3.2)
        self.play(Create(c0), run_time=1.1)
        self.play(Create(c1), run_time=1.1)

        leg0 = Text("接種なし：平均余命 26歳7か月", font=FONT, font_size=20, color=ACCENT_PINK)
        leg0.move_to([0.4, -1.72, 0])
        leg1 = Text("接種あり：平均余命 29歳9か月", font=FONT, font_size=20, color=ACCENT_GOLD)
        leg1.move_to([0.4, 2.15, 0])
        self.play(FadeIn(leg1), run_time=0.5)
        self.play(FadeIn(leg0), run_time=0.5)

        # tracer oscillating along the upper curve fills the remaining time
        tracer = Dot(color=TEXT_WHITE, radius=0.07)
        self._phase = 0.0

        def _trace(m, dt):
            self._phase += dt * 0.8
            a = 40.0 * (1.0 - math.cos(self._phase))  # sweeps 0..80..0
            a = max(0.0, min(80.0, a))
            m.move_to(axes.c2p(a, _s1(a)))

        tracer.add_updater(_trace)
        self.add(tracer)

        used = 0.7 + 0.8 + 1.1 + 1.1 + 0.5 + 0.5
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        clock = ValueTracker(0.0)
        self.play(clock.animate.set_value(1.0), run_time=motion, rate_func=lambda t: t)
        tracer.clear_updaters()
        self.wait(coda)

    # -------------------------------------------------------------- threshold
    def _build_threshold(self, duration):
        title = Text("接種の損得が反転する境目", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        x_left, x_right = -4.8, 4.8
        bar_y = 0.5
        bar_h = 0.9

        def pct_to_x(pct):
            return x_left + (pct / 20.0) * (x_right - x_left)

        x_thr = pct_to_x(11.0)
        adv = Rectangle(
            width=x_thr - x_left,
            height=bar_h,
            color=ACCENT_GOLD,
            fill_color=ACCENT_GOLD,
            fill_opacity=0.22,
            stroke_width=2,
        )
        adv.move_to([(x_left + x_thr) / 2.0, bar_y, 0])
        dis = Rectangle(
            width=x_right - x_thr,
            height=bar_h,
            color=ACCENT_PINK,
            fill_color=ACCENT_PINK,
            fill_opacity=0.22,
            stroke_width=2,
        )
        dis.move_to([(x_thr + x_right) / 2.0, bar_y, 0])
        self.play(FadeIn(adv), FadeIn(dis), run_time=0.8)

        adv_lab = Text("接種が有利", font=FONT, font_size=22, color=ACCENT_GOLD)
        adv_lab.move_to([(x_left + x_thr) / 2.0, bar_y, 0])
        dis_lab = Text("不利", font=FONT, font_size=22, color=ACCENT_PINK)
        dis_lab.move_to([(x_thr + x_right) / 2.0, bar_y, 0])
        self.play(FadeIn(adv_lab), FadeIn(dis_lab), run_time=0.5)

        thr_line = Line(
            [x_thr, bar_y - bar_h / 2 - 0.15, 0],
            [x_thr, bar_y + bar_h / 2 + 0.45, 0],
            color=TEXT_WHITE,
            stroke_width=3,
        )
        thr_lab = Text("11%", font=FONT, font_size=24, color=TEXT_WHITE)
        thr_lab.move_to([x_thr, bar_y + bar_h / 2 + 0.7, 0])
        self.play(Create(thr_line), FadeIn(thr_lab), run_time=0.6)

        # percent scale
        axis = Line([x_left, -0.5, 0], [x_right, -0.5, 0], color=TEXT_DIM, stroke_width=2)
        ticks = VGroup()
        for pct in [0, 5, 10, 15, 20]:
            xt = pct_to_x(pct)
            tick = Line([xt, -0.42, 0], [xt, -0.58, 0], color=TEXT_DIM, stroke_width=2)
            lbl = Text(f"{pct}%", font=FONT, font_size=18, color=TEXT_DIM)
            lbl.move_to([xt, -0.82, 0])
            ticks.add(tick, lbl)
        scale_cap = Text("接種そのもので死ぬ危険", font=FONT, font_size=18, color=TEXT_DIM)
        scale_cap.move_to([0, -1.2, 0])
        self.play(Create(axis), FadeIn(ticks), FadeIn(scale_cap), run_time=0.8)

        caption = Text(
            "接種で死ぬ危険が11%より小さければ、接種は有利",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        )
        caption.move_to([0, -1.55, 0])
        self.play(FadeIn(caption), run_time=0.6)

        # marker sweeping along the scale fills the remaining time
        marker = Dot([pct_to_x(0), -0.5, 0], color=ACCENT_CYAN, radius=0.09)
        self._phase = 0.0

        def _sweep(m, dt):
            self._phase += dt * 1.1
            pct = 10.0 - 10.0 * math.cos(self._phase)  # sweeps 0..20..0
            pct = max(0.0, min(20.0, pct))
            m.move_to([pct_to_x(pct), -0.5, 0])

        marker.add_updater(_sweep)
        self.add(marker)

        used = 0.7 + 0.8 + 0.5 + 0.6 + 0.8 + 0.6
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        clock = ValueTracker(0.0)
        self.play(clock.animate.set_value(1.0), run_time=motion, rate_func=lambda t: t)
        marker.clear_updaters()
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "survival": {"people": [], "years": []},
    "threshold": {"people": [], "years": []},
}

SCENES = {
    "survival": SmallpoxSI,
    "threshold": SmallpoxSI,
}
