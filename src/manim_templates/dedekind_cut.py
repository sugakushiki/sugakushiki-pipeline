"""
dedekind_cut.py - Dedekind's construction of the reals by cutting the rationals (数学史記)

Episode 053 (Richard Dedekind). Two intuition-level views of how Dedekind gave
the irrational numbers a rigorous existence. First the PROBLEM: the rational
number line is dense yet full of invisible GAPS -- at the position of sqrt(2) no
rational number ever lands. Then the ANSWER: cut the rationals into a lower class
A and an upper class B; when the cut has no boundary rational (a gap), the cut
itself CREATES a new irrational number. Continuity = every cut is filled by
exactly one number (completeness), taken as an axiom, not proved.

Modes:
    gaps (default)
        A horizontal number line 0..2.5. Rational points are scattered densely
        (denominators 1..7), showing that between any two rationals there is
        another (dense) -- yet the position of sqrt(2) ~ 1.414 stays empty: a GAP.
        Rationals alone do not fill the line.
        Fixed params: x_of(v) = -4.2 + 3.4*v; ticks at 0,1,2; sqrt(2)~1.414.
    cut
        Cut the rationals into A | B (A's every element < B's every element).
        If the cut has a boundary rational -> an existing number. If the cut is a
        gap (no boundary rational) -> a NEW irrational is created. sqrt(2) is the
        cut  A = {x^2 < 2},  B = {x^2 > 2}. Continuity: every cut filled by exactly
        one number.
        Fixed params: same x_of; cut shown at v=1 (rational case, then faded) and
        at sqrt(2) (gap case, the heart).

All Text uses FONT (BIZ UDMincho). MathTex holds only ASCII (numbers / symbols),
no Japanese. Y range: about -1.85 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    DOWN,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    FadeOut,
    Indicate,
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
    pace,
)

config.background_color = BG_COLOR

# ----------------------------------------------------------------- number-line map
_LINE_Y = 0.55
_X0 = -4.2  # x-position of value 0
_UNIT = 3.4  # x-length of one unit


def _x_of(v):
    return _X0 + _UNIT * v


class DedekindCut(Scene):
    """Dedekind's cut: gaps in the rationals, and cutting to create new numbers."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "gaps")
        duration = float(params.get("duration", 26))
        if mode == "cut":
            self._build_cut(duration)
        else:
            self._build_gaps(duration)

    # ----------------------------------------------------------------- base line
    def _number_line(self):
        line = Line(
            [_x_of(-0.18), _LINE_Y, 0],
            [_x_of(2.62), _LINE_Y, 0],
            color=TEXT_WHITE,
            stroke_width=3,
        )
        ticks = VGroup()
        labels = VGroup()
        for v in (0, 1, 2):
            t = Line(
                [_x_of(v), _LINE_Y - 0.14, 0],
                [_x_of(v), _LINE_Y + 0.14, 0],
                color=TEXT_WHITE,
                stroke_width=3,
            )
            lab = MathTex(str(v), font_size=26, color=TEXT_WHITE)
            lab.move_to([_x_of(v), _LINE_Y - 0.42, 0])
            ticks.add(t)
            labels.add(lab)
        return line, ticks, labels

    # --------------------------------------------------------------------- gaps
    def _build_gaps(self, duration):
        title = Text(
            "有理数の直線には、すき間がある",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "どんなに細かく並べても、√2 の場所には有理数が来ない",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        line, ticks, labels = self._number_line()
        self.play(Create(line), FadeIn(ticks), FadeIn(labels), run_time=1.0)

        # dense rational dots (deterministic, denominators 1..7)
        seen = set()
        vals = []
        for q in range(1, 8):
            for p in range(0, int(2.55 * q) + 1):
                v = p / q
                if 0.0 <= v <= 2.55:
                    key = round(v, 3)
                    if key not in seen:
                        seen.add(key)
                        vals.append(v)
        # keep gap around sqrt(2) visibly empty
        s2 = float(np.sqrt(2))
        dots = VGroup()
        for v in sorted(vals):
            if abs(v - s2) < 0.05:
                continue
            d = Dot([_x_of(v), _LINE_Y, 0], radius=0.045, color=ACCENT_CYAN)
            dots.add(d)
        half = len(dots) // 2
        note_dense = Text(
            "有理数はどこまでも細かい（どの二つの間にも別の有理数）",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        ).move_to([0, 1.55, 0])

        # the gap at sqrt(2)
        gap_line = DashedLine(
            [_x_of(s2), _LINE_Y - 0.55, 0],
            [_x_of(s2), _LINE_Y + 1.05, 0],
            color=ACCENT_PINK,
            stroke_width=3,
            dash_length=0.12,
        )
        gap_lab = MathTex(r"\sqrt{2}", font_size=32, color=ACCENT_PINK)
        gap_lab.move_to([_x_of(s2), _LINE_Y + 1.35, 0])
        gap_word = Text("すき間", font=FONT, font_size=20, color=ACCENT_PINK)
        gap_word.next_to(gap_line, DOWN, buff=0.12)
        note_gap = Text(
            "有理数だけでは、直線はすき間だらけ ── 連続ではない",
            font=FONT,
            font_size=21,
            color=ACCENT_PINK,
        ).move_to([0, -1.55, 0])

        # pace() splits the budget by weight (denominator = sum of weights) so the
        # gap reveal + coda hold are never clipped. intro = title+sub+line FadeIns.
        coda = 3.5
        rt = pace(duration, [0.9, 1.0, 0.5, 1.0, 1.0, 0.8], intro=0.6 + 0.5 + 1.0, coda=coda)
        self.play(FadeIn(dots[:half]), run_time=rt[0])
        self.play(FadeIn(dots[half:]), FadeIn(note_dense), run_time=rt[1])
        self.wait(rt[2])
        self.play(Create(gap_line), FadeIn(gap_lab), FadeIn(gap_word), run_time=rt[3])
        self.play(FadeIn(note_gap), run_time=rt[4])
        self.play(Indicate(gap_line, color=ACCENT_PINK, scale_factor=1.02), run_time=rt[5])
        self.wait(coda)

    # ---------------------------------------------------------------------- cut
    def _build_cut(self, duration):
        title = Text(
            "有理数を《切る》 ── すき間から数を創る",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "有理数の全体を、順序を保って二つの組 A・B に切り分ける",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        line, ticks, labels = self._number_line()
        self.play(Create(line), FadeIn(ticks), FadeIn(labels), run_time=0.9)

        s2 = float(np.sqrt(2))
        # A (lower, cyan) and B (upper, gold) as underlines just below the line
        seg_y = _LINE_Y - 0.02
        a_seg = Line(
            [_x_of(-0.18), seg_y, 0],
            [_x_of(s2), seg_y, 0],
            color=ACCENT_CYAN,
            stroke_width=7,
        )
        b_seg = Line(
            [_x_of(s2), seg_y, 0],
            [_x_of(2.62), seg_y, 0],
            color=ACCENT_GOLD,
            stroke_width=7,
        )
        a_lab = MathTex(r"A", font_size=30, color=ACCENT_CYAN).move_to(
            [_x_of(0.55), _LINE_Y + 0.5, 0]
        )
        b_lab = MathTex(r"B", font_size=30, color=ACCENT_GOLD).move_to(
            [_x_of(2.1), _LINE_Y + 0.5, 0]
        )
        a_note = Text("A のどの数も", font=FONT, font_size=17, color=ACCENT_CYAN).move_to(
            [_x_of(0.55), _LINE_Y + 0.9, 0]
        )
        b_note = Text("B のどの数より小さい", font=FONT, font_size=17, color=ACCENT_GOLD).move_to(
            [_x_of(2.05), _LINE_Y + 0.9, 0]
        )
        self.play(Create(a_seg), Create(b_seg), FadeIn(a_lab), FadeIn(b_lab), run_time=0.9)
        self.play(FadeIn(a_note), FadeIn(b_note), run_time=0.7)

        # case 1: rational cut at v = 1 (has a boundary rational) -> existing number
        cut1 = DashedLine(
            [_x_of(1.0), _LINE_Y - 0.5, 0],
            [_x_of(1.0), _LINE_Y + 0.35, 0],
            color=TEXT_DIM,
            stroke_width=3,
            dash_length=0.1,
        )
        cut1_dot = Dot([_x_of(1.0), _LINE_Y, 0], radius=0.06, color=TEXT_WHITE)
        case1 = Text(
            "切り口にちょうど有理数があれば ── それは《既にある数》",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        ).move_to([0, -0.85, 0])

        # case 2: gap cut at sqrt(2) -> a NEW irrational is created
        cut2 = DashedLine(
            [_x_of(s2), _LINE_Y - 0.5, 0],
            [_x_of(s2), _LINE_Y + 1.0, 0],
            color=ACCENT_PINK,
            stroke_width=3,
            dash_length=0.12,
        )
        s2_lab = MathTex(r"\sqrt{2}", font_size=30, color=ACCENT_PINK).move_to(
            [_x_of(s2), _LINE_Y + 1.32, 0]
        )
        case2 = Text(
            "切り口がすき間なら ── その切断が《新しい無理数》を創る",
            font=FONT,
            font_size=21,
            color=ACCENT_PINK,
        ).move_to([0, -0.85, 0])

        # the sqrt(2) cut written arithmetically (negatives all belong to the lower
        # class A: A is every rational < sqrt(2), B every rational > sqrt(2))
        a_def = MathTex(r"A=\{x<0\}\cup\{x^2<2\}", font_size=24, color=ACCENT_CYAN).move_to(
            [-3.0, -1.45, 0]
        )
        b_def = MathTex(r"B=\{x>0\}\cap\{x^2>2\}", font_size=24, color=ACCENT_GOLD).move_to(
            [3.0, -1.45, 0]
        )
        cont = Text(
            "あらゆる切断が、ちょうど一つの数で埋まる ── これが《連続》",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        ).move_to([0, -1.9, 0])

        # pace(): denominator = sum of weights, so the √2 definition + 連続 conclusion +
        # coda are not clipped. intro = title+sub+line+segments+notes FadeIns.
        coda = 4.0
        rt = pace(
            duration,
            [1.0, 0.4, 0.5, 1.0, 1.0, 1.0, 0.7],
            intro=0.6 + 0.5 + 0.9 + 0.9 + 0.7,
            coda=coda,
        )
        # rational case
        self.play(Create(cut1), FadeIn(cut1_dot), FadeIn(case1), run_time=rt[0])
        self.wait(rt[1])
        self.play(FadeOut(case1), FadeOut(cut1), FadeOut(cut1_dot), run_time=rt[2])
        # gap case (the heart)
        self.play(Create(cut2), FadeIn(s2_lab), FadeIn(case2), run_time=rt[3])
        self.play(FadeIn(a_def), FadeIn(b_def), run_time=rt[4])
        self.play(FadeIn(cont), run_time=rt[5])
        self.play(Indicate(cut2, color=ACCENT_PINK, scale_factor=1.02), run_time=rt[6])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "gaps": {"people": [], "years": []},
    "cut": {"people": [], "years": []},
}

SCENES = {
    "gaps": DedekindCut,
    "cut": DedekindCut,
}
