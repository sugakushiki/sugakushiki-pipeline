"""
lagrangian_mechanics.py - Mechanics without figures: Newton's geometry vs L = T - V (数学史記)

Episode 055 (Joseph-Louis Lagrange). The thesis "a mechanics with not a single
figure": Newton solved motion with force diagrams and case-by-case geometric
insight; Lagrange wrote one quantity L = T - V (kinetic minus potential energy)
in generalized coordinates and turned a fixed crank. L = T - V and the equation
d/dt(dL/dq') - dL/dq = 0 are the MODERN distillation named after him (he started
from d'Alembert's principle; he did not literally write the symbol L = T - V).

Modes:
    newton_vs_lagrange (default)
        Left: a block on an incline with weight / normal / down-slope force arrows
        -- a cluttered geometric figure. Right: the algebraic recipe L = T - V,
        the Lagrange equation, and "the equation of motion falls out" -- no figure.
        Fixed params: schematic incline (right triangle), one block, three force
        arrows; right column is pure MathTex. No numbers, no years, no names.
    pendulum
        One generalized coordinate theta: draw the pendulum, then T, V, L = T - V,
        the Lagrange equation, and the result theta'' = -(g/L) sin(theta). One
        coordinate suffices; no free-body figure needed.
        Fixed params: pendulum at fixed angle ~30 deg; symbolic MathTex column.
    no_figures
        A mock page of 'Mecanique analytique': dense equation lines and the boast
        "not a single figure". Book title only (no year / no person on screen).
        Fixed params: one page rectangle, six equation lines.

All Japanese labels use Text(font=FONT). MathTex holds only ASCII/LaTeX, no
Japanese. Y range: about -1.9 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    PI,
    Arc,
    Arrow,
    Create,
    DashedLine,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    Rectangle,
    Scene,
    Square,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR


class LagrangianMechanics(Scene):
    """Newton's force diagram vs Lagrange's L = T - V recipe (figure-free mechanics)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "newton_vs_lagrange")
        duration = float(params.get("duration", 26))
        if mode == "pendulum":
            self._build_pendulum(duration)
        elif mode == "no_figures":
            self._build_no_figures(duration)
        else:
            self._build_newton_vs_lagrange(duration)

    def _titles(self, title, subtitle):
        t = Text(title, font=FONT, font_size=27, color=ACCENT_GOLD).move_to([0, 3.0, 0])
        s = Text(subtitle, font=FONT, font_size=18, color=TEXT_DIM).move_to([0, 2.45, 0])
        self.play(FadeIn(t), run_time=0.6)
        self.play(FadeIn(s), run_time=0.5)
        return t, s

    # ------------------------------------------------ newton_vs_lagrange
    def _build_newton_vs_lagrange(self, duration):
        self._titles(
            "図なしの力学 ── 力の図か、一つの式か", "同じ運動を、片や作図で、片や代数で解く"
        )

        divider = DashedLine([0, 2.0, 0], [0, -1.7, 0], color=EDGE_COLOR, stroke_width=2)
        head_l = Text("ニュートン ── 力の図", font=FONT, font_size=19, color=ACCENT_CYAN).move_to(
            [-3.45, 1.95, 0]
        )
        head_r = Text(
            "ラグランジュ ── 一つの式", font=FONT, font_size=19, color=ACCENT_GOLD
        ).move_to([3.4, 1.95, 0])

        # --- left: incline + block + force arrows ---
        a = np.array([-5.0, -1.0, 0.0])
        b = np.array([-1.9, -1.0, 0.0])
        c = np.array([-1.9, 0.35, 0.0])
        incline = Polygon(a, b, c, color=EDGE_COLOR, stroke_width=3, fill_opacity=0.12)
        d = c - a
        d_unit = d / np.linalg.norm(d)
        n_unit = np.array([-d_unit[1], d_unit[0], 0.0])  # up-left normal
        m = (a + c) / 2
        block_c = m + 0.28 * n_unit
        block = Square(
            side_length=0.45, color=TEXT_WHITE, stroke_width=3, fill_opacity=0.25
        ).move_to(block_c)
        grav = Arrow(
            block_c,
            block_c + np.array([0, -0.82, 0]),
            color=ACCENT_GOLD,
            buff=0.05,
            stroke_width=4,
            max_tip_length_to_length_ratio=0.28,
        )
        normal = Arrow(
            block_c,
            block_c + 0.72 * n_unit,
            color=ACCENT_CYAN,
            buff=0.05,
            stroke_width=4,
            max_tip_length_to_length_ratio=0.3,
        )
        comp = Arrow(
            block_c,
            block_c - 0.62 * d_unit,
            color=ACCENT_PINK,
            buff=0.05,
            stroke_width=4,
            max_tip_length_to_length_ratio=0.32,
        )
        theta = Arc(
            arc_center=a,
            radius=0.6,
            start_angle=0.0,
            angle=float(np.arctan2(d[1], d[0])),
            color=TEXT_DIM,
            stroke_width=2,
        )
        cap_l = Text(
            "作図と、そのつどの工夫が要る", font=FONT, font_size=15, color=TEXT_DIM
        ).move_to([-3.45, -1.55, 0])

        # --- right: the algebraic recipe ---
        ltv = MathTex(r"L = T - V", font_size=34, color=ACCENT_GOLD).move_to([3.4, 1.0, 0])
        ltv_box = SurroundingRectangle(ltv, color=ACCENT_GOLD, buff=0.12)
        crank = MathTex(
            r"\frac{d}{dt}\frac{\partial L}{\partial \dot q}-\frac{\partial L}{\partial q}=0",
            font_size=30,
            color=TEXT_WHITE,
        ).move_to([3.4, 0.05, 0])
        arrow_dn = Arrow([3.4, -0.5, 0], [3.4, -0.9, 0], color=TEXT_DIM, buff=0.05, stroke_width=3)
        result = Text("運動の方程式が、出る", font=FONT, font_size=20, color=ACCENT_CYAN).move_to(
            [3.4, -1.2, 0]
        )
        cap_r = Text("図はいらない", font=FONT, font_size=15, color=TEXT_DIM).move_to(
            [3.4, -1.62, 0]
        )

        coda = 3.0
        rt = pace(duration, [0.8, 1.0, 1.0, 0.9, 0.9, 0.8, 0.8], intro=1.1, coda=coda)
        self.play(Create(divider), FadeIn(head_l), FadeIn(head_r), run_time=rt[0])
        self.play(Create(incline), Create(theta), FadeIn(block), run_time=rt[1])
        self.play(FadeIn(grav), FadeIn(normal), FadeIn(comp), FadeIn(cap_l), run_time=rt[2])
        self.play(FadeIn(ltv), Create(ltv_box), run_time=rt[3])
        self.play(FadeIn(crank), run_time=rt[4])
        self.play(Create(arrow_dn), FadeIn(result), run_time=rt[5])
        self.play(FadeIn(cap_r), run_time=rt[6])
        self.wait(coda)

    # ------------------------------------------------------------ pendulum
    def _build_pendulum(self, duration):
        self._titles(
            "振り子 ── 座標は θ 一つでよい", "L = T − V を書けば、決まった手続きで運動が出る"
        )

        pivot = np.array([-3.4, 1.9, 0.0])
        th0 = 30.0 * PI / 180.0
        rod_len = 1.7
        bob_c = pivot + rod_len * np.array([np.sin(th0), -np.cos(th0), 0.0])
        rod = Line(pivot, bob_c, color=TEXT_WHITE, stroke_width=3)
        bob = Square(side_length=0.34, color=ACCENT_CYAN, stroke_width=3, fill_opacity=0.4).move_to(
            bob_c
        )
        vref = DashedLine(pivot, pivot + np.array([0, -1.5, 0]), color=TEXT_DIM, stroke_width=2)
        pin = Rectangle(
            width=0.5, height=0.12, color=EDGE_COLOR, fill_opacity=0.6, stroke_width=2
        ).move_to(pivot + np.array([0, 0.12, 0]))
        arc = Arc(
            arc_center=pivot,
            radius=0.55,
            start_angle=-PI / 2,
            angle=th0,
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        th_lab = MathTex(r"\theta", font_size=30, color=ACCENT_GOLD).move_to(
            pivot + np.array([0.42, -0.72, 0])
        )

        col_x = 2.5
        t_eq = MathTex(
            r"T=\tfrac{1}{2}mL^2\dot\theta^{2}", font_size=28, color=ACCENT_CYAN
        ).move_to([col_x, 1.55, 0])
        v_eq = MathTex(r"V=-mgL\cos\theta", font_size=28, color=ACCENT_CYAN).move_to(
            [col_x, 0.9, 0]
        )
        l_eq = MathTex(r"L=T-V", font_size=30, color=ACCENT_GOLD).move_to([col_x, 0.22, 0])
        l_box = SurroundingRectangle(l_eq, color=ACCENT_GOLD, buff=0.1)
        crank = MathTex(
            r"\frac{d}{dt}\frac{\partial L}{\partial \dot\theta}-\frac{\partial L}{\partial\theta}=0",
            font_size=26,
            color=TEXT_WHITE,
        ).move_to([col_x, -0.6, 0])
        res = MathTex(
            r"\ddot\theta=-\tfrac{g}{L}\sin\theta", font_size=30, color=ACCENT_PINK
        ).move_to([col_x, -1.35, 0])
        note = Text(
            "図に頼らず、一つの式から運動が出る", font=FONT, font_size=17, color=TEXT_DIM
        ).move_to([0, -1.88, 0])

        coda = 3.2
        rt = pace(duration, [1.0, 0.8, 0.8, 0.9, 0.9, 0.9, 0.9], intro=1.1, coda=coda)
        self.play(FadeIn(pin), FadeIn(vref), Create(rod), FadeIn(bob), run_time=rt[0])
        self.play(Create(arc), FadeIn(th_lab), run_time=rt[1])
        self.play(FadeIn(t_eq), run_time=rt[2])
        self.play(FadeIn(v_eq), run_time=rt[3])
        self.play(FadeIn(l_eq), Create(l_box), run_time=rt[4])
        self.play(FadeIn(crank), run_time=rt[5])
        self.play(FadeIn(res), FadeIn(note), run_time=rt[6])
        self.wait(coda)

    # ----------------------------------------------------------- no_figures
    def _build_no_figures(self, duration):
        self._titles("『解析力学』── 一枚の図もない", "力学を、作図なしに、代数の手続きだけで")

        page = Rectangle(
            width=6.2,
            height=3.5,
            color=EDGE_COLOR,
            stroke_width=2.5,
            fill_color=TEXT_WHITE,
            fill_opacity=0.05,
        ).move_to([0, -0.05, 0])
        lines = [
            r"L = T - V",
            r"\frac{d}{dt}\frac{\partial L}{\partial \dot q_i}-\frac{\partial L}{\partial q_i}=0",
            r"T=\tfrac{1}{2}\sum_i m_i\,\dot q_i^{2}",
            r"\delta\!\int L\,dt = 0",
            r"p_i=\frac{\partial L}{\partial \dot q_i}",
        ]
        ys = [1.2, 0.55, -0.12, -0.78, -1.42]
        eqs = VGroup(
            *[
                MathTex(
                    s,
                    font_size=(26 if i == 0 else 23),
                    color=(ACCENT_GOLD if i == 0 else TEXT_WHITE),
                ).move_to([0, ys[i], 0])
                for i, s in enumerate(lines)
            ]
        )
        boast = Text(
            "『本書には一枚の図もない』", font=FONT, font_size=20, color=ACCENT_PINK
        ).move_to([0, 2.0, 0])

        coda = 3.2
        n = len(eqs)
        weights = [0.9] + [0.7] * n + [0.9]
        rt = pace(duration, weights, intro=1.1, coda=coda)
        self.play(Create(page), run_time=rt[0])
        for i, eq in enumerate(eqs):
            self.play(FadeIn(eq), run_time=rt[1 + i])
        self.play(FadeIn(boast), run_time=rt[-1])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "newton_vs_lagrange": {"people": [], "years": []},
    "pendulum": {"people": [], "years": []},
    "no_figures": {"people": [], "years": []},
}

SCENES = {
    "newton_vs_lagrange": LagrangianMechanics,
    "pendulum": LagrangianMechanics,
    "no_figures": LagrangianMechanics,
}
