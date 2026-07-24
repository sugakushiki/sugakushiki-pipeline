"""
cauchy_kovalevskaya.py - When does a differential equation have a solution?

Episode 047 (Sofya Kovalevskaya). Intuition-level visuals for the
Cauchy-Kovalevskaya theorem: the Cauchy (initial-value) problem for an analytic
partial differential equation, and the construction of a local analytic
solution as a power series whose coefficients are forced one after another --
giving local existence and uniqueness. No proofs -- wonder and intuition only.
Cauchy proved a special case; Kovalevskaya generalized it (hence both names).

Modes:
    problem (default)
        The Cauchy problem: a differential equation together with data given on
        an initial surface (t = 0). Question: does a solution exist near that
        surface? Left: an (x, t) diagram with the initial line highlighted and a
        neighborhood above it. Right: the equation and the initial condition.
        Fixed params: initial data as 5 dots on the t=0 axis; neighborhood band
        above; PDE du/dt = F(...) and u(x,0)=phi(x).
        On screen: name Cauchy (コーシー, in the term "Cauchy problem").
    series
        Constructing the solution as a power series in t, u = a0 + a1 t + a2 t^2
        + ..., whose coefficients (functions of x) are determined one by one:
        a0 from the initial condition, then a1, a2, ... forced by the equation.
        Result: a unique local analytic solution (local existence + uniqueness).
        Attribution: Cauchy showed a special case, Kovalevskaya generalized it.
        Fixed params: ansatz with 4 explicit coefficients a0..a3 lit in sequence.
        On screen: names Cauchy (コーシー), Kovalevskaya (コワレフスカヤ).

All Text uses FONT (BIZ UDMincho). MathTex holds LaTeX only (no Japanese).
Y range: about -1.75 to +3.05. No trailing FadeOut.
"""

from manim import (
    Arrow,
    Create,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Rectangle,
    Scene,
    SurroundingRectangle,
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


class CauchyKovalevskaya(Scene):
    """The Cauchy-Kovalevskaya theorem -- two intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "problem")
        duration = float(params.get("duration", 26))
        if mode == "series":
            self._build_series(duration)
        else:
            self._build_problem(duration)

    # ------------------------------------------------------------------ problem
    def _build_problem(self, duration):
        title = Text(
            "コーシー問題 ── いつ、解はあるのか", font=FONT, font_size=27, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        ox, oy = -3.3, -0.55
        x_axis = Line([ox - 2.1, oy, 0], [ox + 2.1, oy, 0], color=TEXT_DIM, stroke_width=2)
        t_axis = Line([ox, oy - 0.3, 0], [ox, oy + 2.5, 0], color=TEXT_DIM, stroke_width=2)
        x_lab = MathTex("x", font_size=26, color=TEXT_DIM).move_to([ox + 2.35, oy, 0])
        t_lab = MathTex("t", font_size=26, color=TEXT_DIM).move_to([ox, oy + 2.75, 0])

        init_line = Line([ox - 1.95, oy, 0], [ox + 1.95, oy, 0], color=ACCENT_GOLD, stroke_width=5)
        init_lab = Text("初期の面（t ＝ 0）", font=FONT, font_size=18, color=ACCENT_GOLD)
        init_lab.move_to([ox, oy - 0.62, 0])
        dots = VGroup(
            *[Dot([ox - 1.6 + i * 0.8, oy, 0], color=ACCENT_GOLD, radius=0.07) for i in range(5)]
        )
        data_lab = Text("与えられた初期の値", font=FONT, font_size=16, color=TEXT_DIM)
        data_lab.move_to([ox, oy + 2.15, 0])

        band = Rectangle(width=3.9, height=1.35, color=ACCENT_CYAN, stroke_width=1.5)
        band.set_fill(ACCENT_CYAN, opacity=0.07)
        band.move_to([ox, oy + 0.9, 0])
        arrows = VGroup(
            *[
                Arrow(
                    [ox - 1.2 + i * 1.2, oy + 0.06, 0],
                    [ox - 1.2 + i * 1.2, oy + 1.05, 0],
                    color=ACCENT_CYAN,
                    stroke_width=3,
                    buff=0.0,
                    max_tip_length_to_length_ratio=0.28,
                )
                for i in range(3)
            ]
        )
        band_lab = Text("この近くに、解はあるか？", font=FONT, font_size=18, color=ACCENT_CYAN)
        band_lab.move_to([ox, oy + 1.75, 0])

        pde = MathTex(
            r"\frac{\partial u}{\partial t} = F\!\left(x, t, u, \frac{\partial u}{\partial x}\right)",
            font_size=30,
            color=ACCENT_CYAN,
        ).move_to([3.0, 1.55, 0])
        ic = MathTex(r"u(x, 0) = \varphi(x)", font_size=32, color=ACCENT_GOLD).move_to(
            [3.0, 0.55, 0]
        )
        r1 = Text("初期の面の上で、解を与える", font=FONT, font_size=19, color=TEXT_WHITE)
        r1.move_to([3.0, -0.25, 0])
        r2 = Text("その近くに、解はあるのか？", font=FONT, font_size=21, color=ACCENT_GOLD)
        r2.move_to([3.0, -0.85, 0])
        bottom = Text(
            "微分方程式は、いつ解を持つと保証できるのか", font=FONT, font_size=19, color=TEXT_DIM
        )
        bottom.move_to([0, -1.7, 0])

        steps = [
            ([Create(x_axis), Create(t_axis), FadeIn(x_lab), FadeIn(t_lab)], 1.0),
            ([Create(init_line), FadeIn(init_lab)], 1.0),
            ([FadeIn(dots), FadeIn(data_lab)], 1.0),
            ([FadeIn(pde)], 1.1),
            ([FadeIn(ic)], 1.0),
            ([FadeIn(r1)], 0.9),
            ([FadeIn(band), FadeIn(arrows), FadeIn(band_lab)], 1.1),
            ([FadeIn(r2), Indicate(band, color=ACCENT_GOLD, scale_factor=1.03)], 1.1),
            ([FadeIn(bottom)], 0.9),
        ]
        self._run(steps, duration, used=0.7)

    # ------------------------------------------------------------------- series
    def _build_series(self, duration):
        title = Text("べき級数で、解を組み立てる", font=FONT, font_size=27, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        ansatz = MathTex(
            "u",
            "=",
            "a_0",
            "+",
            "a_1 t",
            "+",
            "a_2 t^2",
            "+",
            "a_3 t^3",
            "+",
            r"\cdots",
            font_size=44,
            color=ACCENT_CYAN,
        )
        ansatz.move_to([0, 1.95, 0])
        idx = {"a0": 2, "a1": 4, "a2": 6, "a3": 8}

        sub = Text(
            "解を、t のべき級数と考える（係数は x の関数）", font=FONT, font_size=19, color=TEXT_DIM
        )
        sub.move_to([0, 1.15, 0])

        note0 = Text("初期条件が、最初の係数を決める", font=FONT, font_size=20, color=ACCENT_GOLD)
        note0.move_to([0, 0.45, 0])
        note1 = Text(
            "あとは方程式が、残りの係数を次々に決める", font=FONT, font_size=20, color=TEXT_WHITE
        )
        note1.move_to([0, -0.1, 0])

        concl = Text(
            "初期の面の近くに、解析的な解が ただ一つ", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        concl.move_to([0, -0.75, 0])
        cbox = SurroundingRectangle(concl, color=ACCENT_GOLD, buff=0.14)
        csub = Text("＝ 局所的な、存在と一意性", font=FONT, font_size=19, color=ACCENT_PINK)
        csub.move_to([0, -1.25, 0])

        attrib = Text(
            "コーシーが特別な場合を示し、コワレフスカヤが一般化した",
            font=FONT,
            font_size=17,
            color=TEXT_DIM,
        )
        attrib.move_to([0, -1.72, 0])

        steps = [
            ([FadeIn(ansatz)], 1.1),
            ([FadeIn(sub)], 0.9),
            (
                [
                    ansatz[idx["a0"]].animate.set_color(ACCENT_GOLD),
                    Indicate(ansatz[idx["a0"]], color=ACCENT_GOLD),
                    FadeIn(note0),
                ],
                1.1,
            ),
            (
                [
                    ansatz[idx["a1"]].animate.set_color(ACCENT_GOLD),
                    Indicate(ansatz[idx["a1"]], color=ACCENT_GOLD),
                ],
                0.7,
            ),
            (
                [
                    ansatz[idx["a2"]].animate.set_color(ACCENT_GOLD),
                    Indicate(ansatz[idx["a2"]], color=ACCENT_GOLD),
                ],
                0.7,
            ),
            (
                [
                    ansatz[idx["a3"]].animate.set_color(ACCENT_GOLD),
                    Indicate(ansatz[idx["a3"]], color=ACCENT_GOLD),
                    FadeIn(note1),
                ],
                1.0,
            ),
            ([FadeIn(concl), Create(cbox)], 1.1),
            ([FadeIn(csub)], 0.9),
            ([Indicate(concl, color=ACCENT_PINK, scale_factor=1.05)], 0.8),
            ([FadeIn(attrib)], 0.9),
        ]
        self._run(steps, duration, used=0.7)

    # --------------------------------------------------------------------- util
    def _run(self, steps, duration, used, coda=2.2):
        # Boole-style: scale the staged reveals to span the scene (slow but
        # continuous "information appearing"); end with a short constant coda.
        base = sum(rt for _, rt in steps)
        body = max(base, duration - used - coda)
        scale = min(body / base, 4.5) if base > 0 else 1.0
        for mobs, rt in steps:
            self.play(*mobs, run_time=rt * scale)
        # bounded hold only if the target far exceeds our scaled reveals
        leftover = duration - used - base * scale - coda
        if leftover > 0.4:
            self.wait(min(leftover, coda))
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "problem": {"people": [["コーシー", "Cauchy"]], "years": []},
    "series": {
        "people": [["コーシー", "Cauchy"], ["コワレフスカヤ", "Kovalevskaya"]],
        "years": [],
    },
}

SCENES = {
    "problem": CauchyKovalevskaya,
    "series": CauchyKovalevskaya,
}
