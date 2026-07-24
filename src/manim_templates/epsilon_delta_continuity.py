"""
epsilon_delta_continuity.py - Weierstrass's epsilon-delta rigorization of analysis

Karl Weierstrass (1815-1897) formalized in his Berlin lectures of the early
1860s the modern definition of continuity: f is continuous at a iff
    for every epsilon > 0, there exists delta > 0 such that
    |x - a| < delta  implies  |f(x) - f(a)| < epsilon.
Precursors include Cauchy 1821 (Cours d'analyse, infinitesimal-based) and
Bolzano 1817 (essentially modern but unpublished and unknown until later).
He also lifted the Bolzano-Weierstrass theorem (every bounded sequence in R
has a convergent subsequence) from an implicit lemma in Bolzano's 1817
intermediate-value-theorem proof to an independent pillar of analysis.

Modes:
    cauchy_legacy
        Sketch of Cauchy's 1821 infinitesimal-style formulation: a function
        f(x) is "continuous" if an infinitely small change alpha in x produces
        an infinitely small change in f. We show the alpha notation and a
        question mark indicating the missing rigorous quantifier formulation.
        Fixed params: graph of f(x) = (x-1)^2 + 0.5 shown on a small axes,
        infinitesimal alpha drawn as a tiny bracket near a chosen point.

    epsilon_delta_definition
        The modern epsilon-delta definition. We draw a parabola y = (x-1)^2 + 0.5
        on a small axes, mark point a = 1.0, then show a horizontal epsilon band
        of width 2*eps around f(a) = 0.5 and the matching vertical delta band of
        width 2*del around x = a. We then shrink epsilon (with a smaller eps2)
        and shrink delta accordingly to convey "for every epsilon, there is a
        delta".
        Fixed params: a = 1.0, f(a) = 0.5, eps1 = 0.6, del1 = 0.45,
        eps2 = 0.3, del2 = 0.30 (visually chosen so that |f(x)-f(a)| <= eps
        whenever |x-a| <= del).

    bolzano_weierstrass
        A bounded infinite sequence on the real line, drawn as dots scattered
        inside [-3, 3]. We then highlight a subset of dots that cluster near a
        single accumulation point a* ~ 1.2, illustrating the convergent
        subsequence guaranteed by the theorem. A horizontal bracket marks the
        bounded interval; an upward arrow points to a*.
        Fixed params: bound interval = [-3, 3] on a number line at y = -0.5;
        accumulation point a_star = 1.2; 14 dots total, 7 of which form the
        convergent subsequence.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 028 (Weierstrass), pillar A - epsilon-delta rigorization.
"""

from manim import (
    Arrow,
    Axes,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
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


class EpsilonDeltaContinuity(Scene):
    """Epsilon-delta rigorization of continuity (Weierstrass)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "epsilon_delta_definition")
        self._duration = float(params.get("duration", 30))

        if mode == "cauchy_legacy":
            self._build_cauchy_legacy()
        elif mode == "bolzano_weierstrass":
            self._build_bolzano_weierstrass()
        else:
            self._build_epsilon_delta_definition()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_cauchy_legacy(self):
        duration = self._duration
        title = self._title("コーシーの定式化 ── 無限小に頼った1821年")
        self.play(FadeIn(title), run_time=0.6)

        # Small axes on the left side
        axes = Axes(
            x_range=[-0.2, 2.2, 1],
            y_range=[-0.2, 2.2, 1],
            x_length=4.0,
            y_length=2.6,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([-2.6, 0.6, 0])

        # f(x) = (x-1)^2 + 0.5
        curve = axes.plot(lambda x: (x - 1) ** 2 + 0.5, x_range=[-0.2, 2.2], color=ACCENT_CYAN)
        self.play(Create(axes), Create(curve), run_time=0.9)

        # Point a on the axis
        a_val = 1.0
        fa_val = 0.5
        a_pt = axes.c2p(a_val, fa_val)
        a_dot = Dot(a_pt, color=ACCENT_GOLD, radius=0.07)
        a_label = MathTex(r"a", font_size=22, color=ACCENT_GOLD)
        a_label.move_to([a_pt[0], axes.c2p(a_val, 0)[1] - 0.30, 0])
        self.play(FadeIn(a_dot), FadeIn(a_label), run_time=0.4)

        # Tiny "alpha" bracket near a, suggesting an infinitesimal increment
        alpha_left = axes.c2p(a_val - 0.05, 0)
        alpha_right = axes.c2p(a_val + 0.05, 0)
        alpha_bracket = Line(
            [alpha_left[0], alpha_left[1] - 0.10, 0],
            [alpha_right[0], alpha_right[1] - 0.10, 0],
            color=ACCENT_PINK,
            stroke_width=3.5,
        )
        alpha_label = MathTex(r"\alpha", font_size=26, color=ACCENT_PINK)
        alpha_label.move_to([(alpha_left[0] + alpha_right[0]) / 2, alpha_left[1] - 0.50, 0])
        self.play(Create(alpha_bracket), FadeIn(alpha_label), run_time=0.5)

        # Right-side explanation: "alpha is infinitely small"
        note1 = Text("α は無限小", font=FONT, font_size=22, color=ACCENT_PINK)
        note1.move_to([2.3, 1.4, 0])
        formal = MathTex(
            r"\alpha \to 0 \;\Rightarrow\; f(a+\alpha) - f(a) \to 0",
            font_size=26,
            color=TEXT_WHITE,
        )
        formal.move_to([2.3, 0.6, 0])
        question = Text("（『無限小』とは何か？）", font=FONT, font_size=20, color=ACCENT_GOLD)
        question.move_to([2.3, -0.2, 0])
        self.play(FadeIn(note1), run_time=0.5)
        self.play(FadeIn(formal), run_time=0.6)
        self.play(FadeIn(question), run_time=0.5)

        # Footer
        footer = Text(
            "コーシー『解析教程』1821年 ── 量化子はまだ無い",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        footer.move_to([0, -1.85, 0])
        self.play(FadeIn(footer), run_time=0.5)

        anim_total = 0.6 + 0.9 + 0.4 + 0.5 + 0.5 + 0.6 + 0.5 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_epsilon_delta_definition(self):
        duration = self._duration
        title = self._title("ε-δ による連続性の定義")
        self.play(FadeIn(title), run_time=0.6)

        # Axes
        axes = Axes(
            x_range=[-0.2, 2.2, 1],
            y_range=[-0.2, 2.2, 1],
            x_length=4.6,
            y_length=2.8,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.6},
        )
        axes.move_to([-2.3, 0.6, 0])

        curve = axes.plot(lambda x: (x - 1) ** 2 + 0.5, x_range=[-0.2, 2.2], color=ACCENT_CYAN)
        self.play(Create(axes), Create(curve), run_time=0.9)

        a_val = 1.0
        fa_val = 0.5
        a_pt = axes.c2p(a_val, fa_val)
        a_dot = Dot(a_pt, color=ACCENT_GOLD, radius=0.07)
        a_label = MathTex(r"a", font_size=22, color=ACCENT_GOLD)
        a_label.move_to([a_pt[0] + 0.15, axes.c2p(a_val, 0)[1] - 0.30, 0])
        fa_label = MathTex(r"f(a)", font_size=22, color=ACCENT_GOLD)
        fa_label.move_to([axes.c2p(0, fa_val)[0] - 0.50, a_pt[1], 0])
        self.play(FadeIn(a_dot), FadeIn(a_label), FadeIn(fa_label), run_time=0.5)

        # ----- First pass: epsilon1 / delta1 -----
        eps1 = 0.6
        del1 = 0.45
        eps_band = Rectangle(
            width=axes.c2p(2.2, 0)[0] - axes.c2p(-0.2, 0)[0],
            height=axes.c2p(0, 2 * eps1)[1] - axes.c2p(0, 0)[1],
            color=ACCENT_PINK,
            stroke_width=2.0,
            fill_opacity=0.18,
            fill_color=ACCENT_PINK,
        )
        eps_band.move_to(
            [
                (axes.c2p(-0.2, 0)[0] + axes.c2p(2.2, 0)[0]) / 2,
                a_pt[1],
                0,
            ]
        )
        eps_label = MathTex(r"2\varepsilon", font_size=22, color=ACCENT_PINK)
        eps_label.move_to([axes.c2p(2.2, 0)[0] + 0.35, a_pt[1], 0])
        self.play(FadeIn(eps_band), FadeIn(eps_label), run_time=0.6)

        del_band = Rectangle(
            width=axes.c2p(2 * del1, 0)[0] - axes.c2p(0, 0)[0],
            height=axes.c2p(0, 2.2)[1] - axes.c2p(0, -0.2)[1],
            color=ACCENT_GOLD,
            stroke_width=2.0,
            fill_opacity=0.18,
            fill_color=ACCENT_GOLD,
        )
        del_band.move_to(
            [
                a_pt[0],
                (axes.c2p(0, -0.2)[1] + axes.c2p(0, 2.2)[1]) / 2,
                0,
            ]
        )
        del_label = MathTex(r"2\delta", font_size=22, color=ACCENT_GOLD)
        del_label.move_to([a_pt[0], axes.c2p(0, 2.2)[1] + 0.20, 0])
        self.play(FadeIn(del_band), FadeIn(del_label), run_time=0.6)

        # ----- Second pass: shrunk epsilon2 / delta2 -----
        eps2 = 0.30
        del2 = 0.30
        eps_band2 = Rectangle(
            width=axes.c2p(2.2, 0)[0] - axes.c2p(-0.2, 0)[0],
            height=axes.c2p(0, 2 * eps2)[1] - axes.c2p(0, 0)[1],
            color=ACCENT_PINK,
            stroke_width=2.6,
            fill_opacity=0.35,
            fill_color=ACCENT_PINK,
        )
        eps_band2.move_to(
            [
                (axes.c2p(-0.2, 0)[0] + axes.c2p(2.2, 0)[0]) / 2,
                a_pt[1],
                0,
            ]
        )
        del_band2 = Rectangle(
            width=axes.c2p(2 * del2, 0)[0] - axes.c2p(0, 0)[0],
            height=axes.c2p(0, 2.2)[1] - axes.c2p(0, -0.2)[1],
            color=ACCENT_GOLD,
            stroke_width=2.6,
            fill_opacity=0.35,
            fill_color=ACCENT_GOLD,
        )
        del_band2.move_to(
            [
                a_pt[0],
                (axes.c2p(0, -0.2)[1] + axes.c2p(0, 2.2)[1]) / 2,
                0,
            ]
        )
        self.play(FadeIn(eps_band2), FadeIn(del_band2), run_time=0.6)

        # Right-side definition
        defn = MathTex(
            r"\forall\, \varepsilon > 0,\; \exists\, \delta > 0",
            font_size=26,
            color=TEXT_WHITE,
        )
        defn.move_to([3.3, 1.6, 0])
        impl = MathTex(
            r"|x - a| < \delta \;\Rightarrow\; |f(x) - f(a)| < \varepsilon",
            font_size=22,
            color=ACCENT_GOLD,
        )
        impl.move_to([3.3, 0.9, 0])
        note = Text("ε を小さくすれば δ も取り直す", font=FONT, font_size=18, color=ACCENT_PINK)
        note.move_to([3.3, 0.2, 0])
        self.play(FadeIn(defn), run_time=0.5)
        self.play(FadeIn(impl), run_time=0.6)
        self.play(FadeIn(note), run_time=0.4)

        footer = Text(
            "ヴァイエルシュトラス・1860年代ベルリン大学講義",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        footer.move_to([0, -1.85, 0])
        self.play(FadeIn(footer), run_time=0.5)

        anim_total = 0.6 + 0.9 + 0.5 + 0.6 + 0.6 + 0.6 + 0.5 + 0.6 + 0.4 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_bolzano_weierstrass(self):
        duration = self._duration
        title = self._title("ボルツァーノ＝ヴァイエルシュトラスの定理")
        self.play(FadeIn(title), run_time=0.6)

        # Statement just below the title, font reduced to avoid wide overlap.
        statement = Text(
            "有界な無限数列は、収束する部分列を必ず持つ",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        statement.move_to([0, 2.30, 0])
        self.play(FadeIn(statement), run_time=0.5)

        # Number line in the lower-middle band.
        line_y = -0.40
        x_left = -4.5
        x_right = 4.5
        nl = Line([x_left, line_y, 0], [x_right, line_y, 0], color=TEXT_DIM, stroke_width=2.0)
        self.play(Create(nl), run_time=0.4)

        # Tick marks at -3, 0, 3
        for x in (-3.0, 0.0, 3.0):
            tick = Line(
                [x, line_y - 0.10, 0], [x, line_y + 0.10, 0], color=TEXT_DIM, stroke_width=2.0
            )
            lbl = MathTex(f"{int(x)}", font_size=18, color=TEXT_DIM)
            lbl.move_to([x, line_y - 0.30, 0])
            self.add(tick, lbl)

        # Bounded interval bracket [-3, 3] — placed close to the number line
        # so the "有界な区間" label has room above the footer.
        bracket_y = line_y - 0.75
        bracket_l = Line(
            [-3, bracket_y + 0.05, 0],
            [-3, bracket_y - 0.10, 0],
            color=ACCENT_PINK,
            stroke_width=3.0,
        )
        bracket_r = Line(
            [3, bracket_y + 0.05, 0], [3, bracket_y - 0.10, 0], color=ACCENT_PINK, stroke_width=3.0
        )
        bracket_line = Line(
            [-3, bracket_y, 0], [3, bracket_y, 0], color=ACCENT_PINK, stroke_width=2.6
        )
        bracket_label = Text(
            "有界な区間",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        bracket_label.move_to([0, bracket_y - 0.40, 0])
        self.play(Create(bracket_l), Create(bracket_r), Create(bracket_line), run_time=0.5)
        self.play(FadeIn(bracket_label), run_time=0.4)

        # 14 dots in [-3, 3]
        a_star = 1.4  # accumulation point (shifted right to free left half for label)
        subseq = []
        for k in range(7):
            sign = (-1) ** k
            radius = 1.4 * (0.55**k)
            x_pos = a_star + sign * radius
            subseq.append(x_pos)
        noise = [-2.8, -2.2, -1.5, -0.6, 0.3, -0.0, 2.6]

        noise_dots = VGroup()
        for x in noise:
            d = Dot([x, line_y, 0], color=TEXT_WHITE, radius=0.06)
            noise_dots.add(d)
        self.play(FadeIn(noise_dots), run_time=0.6)

        subseq_dots = VGroup()
        for x in subseq:
            d = Dot([x, line_y, 0], color=ACCENT_GOLD, radius=0.08)
            subseq_dots.add(d)
        self.play(FadeIn(subseq_dots), run_time=0.6)

        # Accumulation arrow pointing down to a_star on the number line.
        arrow_start = [a_star, line_y + 0.80, 0]
        arrow_end = [a_star, line_y + 0.18, 0]
        arrow = Arrow(
            arrow_start,
            arrow_end,
            color=ACCENT_PINK,
            stroke_width=4.0,
            max_tip_length_to_length_ratio=0.18,
            buff=0.0,
        )
        a_star_label = MathTex(r"a^{*}", font_size=22, color=ACCENT_PINK)
        a_star_label.move_to([a_star + 0.35, line_y + 0.95, 0])

        # cluster_label moved to the LEFT side so it never overlaps the arrow
        # or the a_star label area. Placed above noise dots in the left band.
        cluster_label = Text(
            "収束する部分列",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        cluster_label.move_to([-2.6, line_y + 0.95, 0])
        self.play(Create(arrow), FadeIn(a_star_label), FadeIn(cluster_label), run_time=0.7)

        # Footer attribution at the very bottom.
        footer = Text(
            "ボルツァーノ1817 補題 → ヴァイエルシュトラス1860年代 主要定理",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        footer.move_to([0, -1.95, 0])
        self.play(FadeIn(footer), run_time=0.5)

        anim_total = 0.6 + 0.5 + 0.4 + 0.5 + 0.4 + 0.6 + 0.6 + 0.7 + 0.5
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "cauchy_legacy": {
        "people": [["コーシー", "Cauchy"]],
        "years": ["1821"],
    },
    "epsilon_delta_definition": {
        "people": [["ヴァイエルシュトラス", "Weierstrass"]],
        "years": ["1860"],
    },
    "bolzano_weierstrass": {
        "people": [["ボルツァーノ", "Bolzano"], ["ヴァイエルシュトラス", "Weierstrass"]],
        "years": ["1817", "1860"],
    },
}

SCENES = {
    "cauchy_legacy": EpsilonDeltaContinuity,
    "epsilon_delta_definition": EpsilonDeltaContinuity,
    "bolzano_weierstrass": EpsilonDeltaContinuity,
}
