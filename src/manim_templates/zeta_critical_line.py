"""
zeta_critical_line.py - Zeros of the Riemann zeta function on the critical line (数学史記)

Hardy proved in 1914 that infinitely many non-trivial zeros of zeta(s) lie on
the critical line Re(s) = 1/2. This is weaker than (and must not be confused
with) the still-unsolved Riemann Hypothesis, which claims ALL non-trivial
zeros lie there.

Modes:
    zeros - Complex plane with the critical line Re(s)=1/2 highlighted and
            conceptual zeros placed on the line (vertical dots indicate they
            continue infinitely). A side panel contrasts Hardy 1914 ("infinitely
            many on the line") with the Riemann Hypothesis ("all of them?
            unsolved").
            Fixed params: critical line at Re=1/2, 3 zero pairs + vdots above/below.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 035 (Hardy), pillar 3 (analytic number theory, Hardy-Littlewood).
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class ZetaCriticalLine(Scene):
    """Zeros of zeta on the critical line Re(s)=1/2 (Hardy 1914)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        _mode = params.get("mode", "zeros")
        self.build_zeros()

    def build_zeros(self):
        duration = self._duration

        title = Text("ゼータ関数の零点と臨界線", font=FONT, font_size=32, color=ACCENT_GOLD)
        title.move_to([0, 3.15, 0])

        axes = Axes(
            x_range=[-1, 2, 1],
            y_range=[-3, 3, 1],
            x_length=3.8,
            y_length=3.4,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_tip": True,
            },
        )
        axes.move_to([-3.3, 0.2, 0])
        re_label = MathTex(r"\mathrm{Re}", font_size=24, color=TEXT_DIM)
        re_label.next_to(axes.x_axis.get_end(), DOWN, buff=0.1)
        im_label = MathTex(r"\mathrm{Im}", font_size=24, color=TEXT_DIM)
        im_label.next_to(axes.y_axis.get_end(), RIGHT, buff=0.1)

        crit_line = Line(axes.c2p(0.5, -3), axes.c2p(0.5, 3), color=ACCENT_GOLD, stroke_width=4)
        crit_label = MathTex(r"\mathrm{Re}(s)=\tfrac{1}{2}", font_size=24, color=ACCENT_GOLD)
        crit_label.next_to(axes.c2p(0.5, 3), UP, buff=0.12)

        zeros = VGroup()
        for im in (0.9, 1.7, 2.5):
            for sgn in (1, -1):
                zeros.add(Dot(axes.c2p(0.5, sgn * im), color=ACCENT_CYAN, radius=0.08))
        vdots_top = MathTex(r"\vdots", font_size=28, color=ACCENT_CYAN)
        vdots_top.next_to(axes.c2p(0.5, 2.5), UP, buff=0.06)
        vdots_bot = MathTex(r"\vdots", font_size=28, color=ACCENT_CYAN)
        vdots_bot.next_to(axes.c2p(0.5, -2.5), DOWN, buff=0.06)

        hardy = VGroup(
            Text("ハーディ 1914", font=FONT, font_size=26, color=ACCENT_CYAN),
            Text("この直線上に零点が無限個", font=FONT, font_size=20, color=TEXT_WHITE),
        ).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        hardy.move_to([3.0, 1.25, 0])

        riemann = VGroup(
            Text("リーマン予想（未解決）", font=FONT, font_size=26, color=ACCENT_PINK),
            Text("すべての零点が この上にある？", font=FONT, font_size=20, color=TEXT_DIM),
        ).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        riemann.move_to([3.0, -0.65, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(re_label), FadeIn(im_label), run_time=0.8)
        self.play(FadeIn(crit_line), FadeIn(crit_label), run_time=0.7)

        fade = 0.5
        coda = 5.0
        reveal_items = list(zeros) + [vdots_top, vdots_bot, hardy, riemann]
        intro = 0.6 + 0.8 + 0.7
        n = len(reveal_items)
        gaps = max(1, n - 1)
        slack = max(0.0, duration - intro - n * fade - coda)
        step_wait = slack / gaps
        for idx, it in enumerate(reveal_items):
            self.play(FadeIn(it), run_time=fade)
            if idx < n - 1:
                self.wait(max(0.3, step_wait))
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "zeros": {
        "people": [["ハーディ", "Hardy"], ["リーマン", "Riemann"]],
        "years": ["1914"],
    },
}


SCENES = {
    "zeros": {
        "class": "ZetaCriticalLine",
        "params": {"mode": "zeros"},
        "description": "Critical line Re(s)=1/2 with infinitely many zeros (Hardy 1914) vs the Riemann Hypothesis",
    },
}
