"""
boolean_algebra_logic.py - Turning thought into calculation (George Boole)

Episode 046 (George Boole). Intuition-level visuals for Boole's algebra of
classes: treating "and / or / not" as multiply / add / (1 - x), the fingerprint
law x^2 = x (and its restatement x(1-x)=0 = the law of non-contradiction), and
a word syllogism turned into an algebraic calculation. No proofs -- wonder and
intuition only.

Modes:
    classes (default)
        Three small Venn panels sharing the same two classes x (cyan = white
        things) and y (gold = sheep) inside a universe box (1 = all, 0 = none):
        AND (xy, the lens), OR (x+y, the union), NOT (1-x, the box minus x).
        Point: "and / or / not" become multiply / add / subtract-from-one.
        Fixed params: box 3.5x2.2 at each panel center x = -4.5, 0, +4.5;
        circles radius 0.72 at center +/-0.42; regions filled pink.
        On screen: no proper nouns (x, y, sheep).
    idempotent
        The law x^2 = x ("a white white thing is just a white thing"), its
        restatement x(1-x)=0 ("nothing is both x and not-x") = Aristotle's law
        of non-contradiction, and a number line showing x^2 = x holds for 0 and
        1 only -- the birth of a two-valued world.
        Fixed params: number line values -1..2 at scale 1.2, y = -1.15; dots at
        0 and 1 (pink).
        On screen: name Aristotle (アリストテレス).
    syllogism
        A word syllogism on the left (all men die; Socrates is a man; therefore
        Socrates dies) and its algebraic encoding on the right (h=hm, s=sh,
        s=sh=shm=sm, so s=sm). Reasoning becomes calculation.
        Fixed params: two columns at x = -3.7 (words) and +3.0 (algebra);
        legend h=man, m=mortal, s=Socrates.
        On screen: name Socrates (ソクラテス).

All Text uses FONT (BIZ UDMincho). MathTex holds LaTeX only (no Japanese).
Y range: about -1.8 to +3.05. No trailing FadeOut.
"""

from manim import (
    Circle,
    Create,
    DashedLine,
    Difference,
    Dot,
    FadeIn,
    Indicate,
    Intersection,
    Line,
    MathTex,
    Rectangle,
    Scene,
    SurroundingRectangle,
    Text,
    Union,
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


def _venn_panel(cx, kind):
    """A small universe box with classes x (cyan) and y (gold) and one region."""
    box = Rectangle(width=3.5, height=2.2, color=TEXT_DIM, stroke_width=2)
    box.move_to([cx, 0.65, 0])
    xc = Circle(radius=0.72, color=ACCENT_CYAN, stroke_width=3)
    xc.move_to([cx - 0.42, 0.65, 0])
    yc = Circle(radius=0.72, color=ACCENT_GOLD, stroke_width=3)
    yc.move_to([cx + 0.42, 0.65, 0])
    if kind == "and":
        region = Intersection(xc, yc)
    elif kind == "or":
        region = Union(xc, yc)
    else:  # not
        region = Difference(box, xc)
    region.set_fill(ACCENT_PINK, opacity=0.5)
    region.set_stroke(width=0)
    return VGroup(box, xc, yc), region


class BooleanAlgebraLogic(Scene):
    """Boole's algebra of thought -- three intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "classes")
        duration = float(params.get("duration", 26))
        if mode == "idempotent":
            self._build_idempotent(duration)
        elif mode == "syllogism":
            self._build_syllogism(duration)
        else:
            self._build_classes(duration)

    # ------------------------------------------------------------------- classes
    def _build_classes(self, duration):
        title = Text(
            "「かつ・または・でない」を、代数にする", font=FONT, font_size=27, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        legend = Text(
            "x（青）＝白いもの　　y（金）＝羊　　　1＝全体　　0＝無",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        legend.move_to([0, 2.4, 0])

        panels = [
            (-4.5, "and", "xy ＝ x かつ y", "（論理積）"),
            (0.0, "or", "x ＋ y ＝ x または y", "（論理和）"),
            (4.5, "not", "1 − x ＝ x でない", "（否定）"),
        ]
        built = []
        for cx, kind, main, sub in panels:
            outline, region = _venn_panel(cx, kind)
            main_t = Text(main, font=FONT, font_size=21, color=TEXT_WHITE)
            main_t.move_to([cx, -1.0, 0])
            sub_t = Text(sub, font=FONT, font_size=16, color=TEXT_DIM)
            sub_t.move_to([cx, -1.42, 0])
            built.append((outline, region, main_t, sub_t))

        takeaway = Text(
            "「かつ・または・でない」が、掛け算・足し算・引き算になる",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        takeaway.move_to([0, -1.83, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 8.0
        self.play(FadeIn(legend), run_time=per * 0.7)
        for outline, region, main_t, sub_t in built:
            self.play(FadeIn(outline), FadeIn(main_t), FadeIn(sub_t), run_time=per)
            self.play(FadeIn(region), run_time=per * 0.8)
            self.bring_to_back(region)
        self.play(FadeIn(takeaway), run_time=per)
        self.wait(coda)

    # ---------------------------------------------------------------- idempotent
    def _build_idempotent(self, duration):
        title = Text("思考の指紋 ── x² ＝ x", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        eq1 = MathTex(r"x^{2} = x", font_size=54, color=ACCENT_CYAN)
        eq1.move_to([0, 2.05, 0])
        t1 = Text(
            "「白くて白いもの」は、ただ「白いもの」", font=FONT, font_size=23, color=TEXT_WHITE
        )
        t1.move_to([0, 1.35, 0])

        eq2 = MathTex(r"x(1 - x) = 0", font_size=46, color=ACCENT_GOLD)
        eq2.move_to([0, 0.55, 0])
        t2 = Text("「x であって、x でないもの」は、無い", font=FONT, font_size=21, color=TEXT_WHITE)
        t2.move_to([0, -0.1, 0])
        t3 = Text("＝ アリストテレスの 矛盾律", font=FONT, font_size=21, color=ACCENT_PINK)
        t3.move_to([0, -0.55, 0])

        # number line: values -1..2 at scale 1.2, at y = -1.15
        axis_y = -1.15
        scale = 1.2
        axis = Line([-1.4, axis_y, 0], [2.6, axis_y, 0], color=TEXT_DIM, stroke_width=2)
        nl = VGroup(axis)
        for v in (-1, 0, 1, 2):
            tick = Line(
                [v * scale, axis_y - 0.09, 0],
                [v * scale, axis_y + 0.09, 0],
                color=TEXT_DIM,
                stroke_width=2,
            )
            nl.add(tick)
        d0 = Dot([0 * scale, axis_y, 0], color=ACCENT_PINK, radius=0.09)
        d1 = Dot([1 * scale, axis_y, 0], color=ACCENT_PINK, radius=0.09)
        l0 = Text("0", font=FONT, font_size=20, color=ACCENT_PINK).move_to([0, axis_y + 0.33, 0])
        l1 = Text("1", font=FONT, font_size=20, color=ACCENT_PINK).move_to([1.2, axis_y + 0.33, 0])
        nl.add(d0, d1, l0, l1)

        caption = Text(
            "普通の数でこの式が成り立つのは、0 と 1 だけ",
            font=FONT,
            font_size=19,
            color=ACCENT_GOLD,
        )
        caption.move_to([0, -1.78, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 7.0
        self.play(FadeIn(eq1), run_time=per)
        self.play(FadeIn(t1), run_time=per * 0.9)
        self.play(FadeIn(eq2), run_time=per)
        self.play(FadeIn(t2), run_time=per * 0.9)
        self.play(FadeIn(t3), run_time=per)
        self.play(Indicate(eq2, color=ACCENT_PINK, scale_factor=1.08), run_time=per * 0.8)
        self.play(Create(axis), FadeIn(nl[1:]), run_time=per)
        self.play(FadeIn(caption), run_time=per)
        self.wait(coda)

    # ----------------------------------------------------------------- syllogism
    def _build_syllogism(self, duration):
        title = Text("推論が、計算になる", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        head_l = Text("言葉の三段論法", font=FONT, font_size=20, color=ACCENT_CYAN)
        head_l.move_to([-3.7, 2.4, 0])
        head_r = Text("記号の計算", font=FONT, font_size=20, color=ACCENT_CYAN)
        head_r.move_to([3.0, 2.4, 0])
        divider = DashedLine([-0.5, 2.65, 0], [-0.5, -0.7, 0], color=TEXT_DIM, stroke_width=1.5)

        s1 = Text("すべての人は、死ぬ", font=FONT, font_size=20, color=TEXT_WHITE)
        s1.move_to([-3.7, 1.6, 0])
        s2 = Text("ソクラテスは、人である", font=FONT, font_size=20, color=TEXT_WHITE)
        s2.move_to([-3.7, 0.85, 0])
        s3 = Text("ゆえに、ソクラテスは死ぬ", font=FONT, font_size=20, color=ACCENT_GOLD)
        s3.move_to([-3.7, 0.05, 0])

        a1 = MathTex(r"h = hm", font_size=34, color=ACCENT_CYAN).move_to([3.0, 1.6, 0])
        a2 = MathTex(r"s = sh", font_size=34, color=ACCENT_CYAN).move_to([3.0, 0.85, 0])
        a3 = MathTex(r"s = sh = shm = sm", font_size=30, color=TEXT_WHITE).move_to([3.0, 0.05, 0])
        a4 = MathTex(r"s = sm", font_size=36, color=ACCENT_GOLD).move_to([3.0, -0.75, 0])
        a4box = SurroundingRectangle(a4, color=ACCENT_GOLD, buff=0.14)

        legend = Text(
            "h＝人　　m＝死ぬもの　　s＝ソクラテス", font=FONT, font_size=17, color=TEXT_DIM
        )
        legend.move_to([0, -1.32, 0])
        takeaway = Text("推論が、式の計算になった", font=FONT, font_size=20, color=ACCENT_GOLD)
        takeaway.move_to([0, -1.8, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 7.0
        self.play(FadeIn(head_l), FadeIn(head_r), Create(divider), run_time=per * 0.8)
        self.play(FadeIn(s1), FadeIn(a1), run_time=per)
        self.play(FadeIn(s2), FadeIn(a2), run_time=per)
        self.play(FadeIn(a3), run_time=per)
        self.play(FadeIn(s3), FadeIn(a4), Create(a4box), run_time=per)
        self.play(FadeIn(legend), run_time=per * 0.7)
        self.play(FadeIn(takeaway), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "classes": {"people": [], "years": []},
    "idempotent": {"people": [["アリストテレス", "Aristotle"]], "years": []},
    "syllogism": {"people": [["ソクラテス", "Socrates"]], "years": []},
}

SCENES = {
    "classes": BooleanAlgebraLogic,
    "idempotent": BooleanAlgebraLogic,
    "syllogism": BooleanAlgebraLogic,
}
