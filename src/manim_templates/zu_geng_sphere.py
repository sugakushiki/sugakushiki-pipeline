"""
zu_geng_sphere.py - Zu Geng's sphere volume via the bicylinder and his principle

Zu Geng (祖暅, son of Zu Chongzhi) found the volume of a sphere by solving the
problem Liu Hui (劉徽, 3rd c.) had left open: Liu Hui saw that a sphere and the
"bicylinder" 牟合方蓋 (the common part of two equal cylinders crossing at right
angles) stand in the ratio pi:4, but could not compute the bicylinder's volume.
Zu Geng closed it with his principle - "if the cross-sectional areas at every
height are equal, the volumes are equal" (equivalent to Cavalieri's principle,
~1100 years before Cavalieri).

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes must live in one class and branch on params["mode"]).

Modes:
    bicylinder    - Schematic 2D sketch of two cylinders crossing at right
                    angles, their common solid (bicylinder) with the sphere
                    inside, and the ratio sphere : solid = pi : 4 (Liu Hui),
                    with the solid's volume marked unknown.
    cross_section - Zu Geng's principle. At height a, the cube-minus-bicylinder
                    "gap" cross-section (a gold frame) and an inverted pyramid's
                    cross-section (a gold square) both have area a^2. A height
                    slider grows both cross-sections together, staying equal.
    sphere_volume - The result chain: gap = pyramid = 1/3 cube -> bicylinder =
                    2/3 cube -> sphere = (pi/4) bicylinder -> V = (4/3) pi r^3.

No on-screen person names or years, so LINT_FACTUAL_CLAIMS is empty per mode.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    WHITE,
    Circle,
    Create,
    Ellipse,
    FadeIn,
    MathTex,
    Rectangle,
    Scene,
    Square,
    SurroundingRectangle,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    linear,
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


class ZuGengSphere(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "bicylinder")
        duration = params.get("duration", 24)
        if mode == "cross_section":
            self._cross_section(duration)
        elif mode == "sphere_volume":
            self._sphere_volume(duration)
        else:
            self._bicylinder(duration)

    # -- mode: bicylinder -----------------------------------------------------
    def _bicylinder(self, duration):
        title = Text("二本の円柱が、直角に交わる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)

        sk = LEFT * 3.2 + UP * 0.15  # sketch center
        v_body = Rectangle(width=1.5, height=2.6, color=ACCENT_CYAN, stroke_width=2.5)
        v_top = Ellipse(width=1.5, height=0.45, color=ACCENT_CYAN, stroke_width=2.5)
        v_bot = Ellipse(width=1.5, height=0.45, color=ACCENT_CYAN, stroke_width=2.5)
        v_body.move_to(sk)
        v_top.move_to(sk + UP * 1.3)
        v_bot.move_to(sk + DOWN * 1.3)
        v_cyl = VGroup(v_body, v_top, v_bot)

        h_body = Rectangle(width=2.6, height=1.5, color=ACCENT_PINK, stroke_width=2.5)
        h_left = Ellipse(width=0.45, height=1.5, color=ACCENT_PINK, stroke_width=2.5)
        h_right = Ellipse(width=0.45, height=1.5, color=ACCENT_PINK, stroke_width=2.5)
        h_body.move_to(sk)
        h_left.move_to(sk + LEFT * 1.3)
        h_right.move_to(sk + RIGHT * 1.3)
        h_cyl = VGroup(h_body, h_left, h_right)

        common = Square(side_length=1.5, color=ACCENT_GOLD, stroke_width=3)
        common.set_fill(ACCENT_GOLD, opacity=0.2)
        common.move_to(sk)

        sphere = Circle(radius=0.75, color=WHITE, stroke_width=2.5)
        sphere.move_to(sk)

        name = Text("牟合方蓋", font=FONT, font_size=20, color=TEXT_DIM)
        name.move_to(sk + DOWN * 1.75)

        ratio_label = Text("球 ： この立体", font=FONT, font_size=26, color=TEXT_WHITE)
        ratio_label.move_to(RIGHT * 3.0 + UP * 1.5)
        ratio = MathTex(r"=\; \pi \,:\, 4", font_size=44, color=ACCENT_GOLD)
        ratio.move_to(RIGHT * 3.0 + UP * 0.5)
        q = MathTex(r"?", font_size=60, color=ACCENT_PINK)
        q.move_to(RIGHT * 3.0 + DOWN * 0.7)
        q_note = Text("立体の体積は、まだ解けない", font=FONT, font_size=20, color=TEXT_DIM)
        q_note.move_to(RIGHT * 3.0 + DOWN * 1.6)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0], intro=1.2, coda=3.5)
        self.play(FadeIn(title), run_time=1.2)
        self.play(Create(v_cyl), Create(h_cyl), run_time=rt[0])
        self.play(FadeIn(common), FadeIn(name), run_time=rt[1])
        self.play(Create(sphere), run_time=rt[2])
        self.play(FadeIn(ratio_label), FadeIn(ratio), run_time=rt[3])
        self.play(FadeIn(q), FadeIn(q_note), run_time=rt[4])
        self.wait(3.5)

    # -- mode: cross_section (Zu Geng's principle) ----------------------------
    def _cross_section(self, duration):
        title = Text("断面積が等しければ、体積も等しい", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)
        sub = Text("同じ高さ a で切った断面", font=FONT, font_size=20, color=TEXT_DIM)
        sub.move_to(UP * 2.1)

        S = 1.7  # square side at a = r
        left_c = LEFT * 3.3 + UP * 0.15
        right_c = RIGHT * 3.3 + UP * 0.15
        t = ValueTracker(0.05)  # normalized height a / r in [0,1]

        outer = Square(side_length=S, color=TEXT_DIM, stroke_width=2)
        outer.set_fill(ACCENT_GOLD, opacity=0.5)
        outer.move_to(left_c)

        def inner_sq():
            side = S * float(np.sqrt(max(0.0004, 1.0 - t.get_value() ** 2)))
            sq = Square(side_length=side, color=ACCENT_CYAN, stroke_width=2)
            sq.set_fill(BG_COLOR, opacity=1.0)
            sq.move_to(left_c)
            return sq

        inner = always_redraw(inner_sq)

        def pyr_sq():
            side = max(0.02, S * t.get_value())
            sq = Square(side_length=side, color=ACCENT_GOLD, stroke_width=2)
            sq.set_fill(ACCENT_GOLD, opacity=0.5)
            sq.move_to(right_c)
            return sq

        pyr = always_redraw(pyr_sq)

        eq = MathTex(r"=", font_size=48, color=ACCENT_PINK)
        eq.move_to(UP * 0.15)

        left_lbl = VGroup(
            Text("隙間の断面", font=FONT, font_size=20, color=TEXT_WHITE),
            MathTex(r"a^2", font_size=30, color=ACCENT_GOLD),
        ).arrange(RIGHT, buff=0.15)
        left_lbl.move_to(left_c + DOWN * 1.35)
        right_lbl = VGroup(
            Text("四角錐の断面", font=FONT, font_size=20, color=TEXT_WHITE),
            MathTex(r"a^2", font_size=30, color=ACCENT_GOLD),
        ).arrange(RIGHT, buff=0.15)
        right_lbl.move_to(right_c + DOWN * 1.35)

        # NOTE: the son's name 祖暅 contains 暅 (U+6685), which BIZ UDMincho
        # cannot render (shows tofu). Keep it OUT of on-screen Text.
        foot = Text("── これが、球の体積を解く鍵", font=FONT, font_size=22, color=ACCENT_PINK)
        foot.move_to(DOWN * 1.75)

        self.play(FadeIn(title), FadeIn(sub), run_time=1.2)
        self.play(Create(outer), FadeIn(eq), run_time=1.2)
        self.add(inner, pyr)
        self.play(FadeIn(left_lbl), FadeIn(right_lbl), run_time=1.0)
        self.play(FadeIn(foot), run_time=0.6)

        body = max(4.0, duration - 4.0 - 3.0)
        self.play(t.animate.set_value(1.0), run_time=body * 0.62, rate_func=linear)
        self.play(t.animate.set_value(0.45), run_time=body * 0.38, rate_func=linear)
        self.wait(3.0)

    # -- mode: sphere_volume --------------------------------------------------
    def _sphere_volume(self, duration):
        title = Text("球の体積が、決まる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)

        # Define d up-front: the cube's side equals the sphere's diameter, so
        # 立方体 = d^3. Without this the boxed V = (pi/6) d^3 is a non-sequitur --
        # the derivation above is all in terms of 立方体.
        defn = VGroup(
            MathTex("d", font_size=27, color=ACCENT_GOLD),
            Text("＝ 球の直径 ＝ 立方体の一辺", font=FONT, font_size=23, color=TEXT_DIM),
        ).arrange(RIGHT, buff=0.15)
        defn.move_to(UP * 2.45)

        def row(text_str, tex_str, color, y):
            grp = VGroup(
                Text(text_str, font=FONT, font_size=25, color=TEXT_WHITE),
                MathTex(tex_str, font_size=34, color=color),
            ).arrange(RIGHT, buff=0.2)
            grp.move_to(UP * y)
            return grp

        r1 = row("隙間 ＝ 逆さの四角錐 ＝ 立方体 ×", r"\tfrac{1}{3}", ACCENT_CYAN, 1.85)
        r2 = row("だから この立体 ＝ 立方体 ×", r"\tfrac{2}{3}", ACCENT_CYAN, 0.85)
        r3 = row("球 ＝ この立体 ×", r"\tfrac{\pi}{4}", ACCENT_PINK, -0.15)

        final = MathTex(
            r"V = \tfrac{\pi}{6}\,d^3 = \tfrac{4}{3}\pi r^3",
            font_size=42,
            color=ACCENT_GOLD,
        )
        final.move_to(DOWN * 1.4)
        box = SurroundingRectangle(final, color=ACCENT_GOLD, buff=0.22)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.3], intro=1.2, coda=3.5)
        self.play(FadeIn(title), FadeIn(defn), run_time=1.2)
        self.play(FadeIn(r1), run_time=rt[0])
        self.play(FadeIn(r2), run_time=rt[1])
        self.play(FadeIn(r3), run_time=rt[2])
        self.play(FadeIn(final), Create(box), run_time=rt[3])
        self.wait(3.5)


# Factual-claim metadata (read by qa_manim_consistency.py). All modes render
# only geometric shapes and formulas - no person/year claims.
LINT_FACTUAL_CLAIMS = {
    "bicylinder": {"people": [], "years": []},
    "cross_section": {"people": [], "years": []},
    "sphere_volume": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "bicylinder": ZuGengSphere,
    "cross_section": ZuGengSphere,
    "sphere_volume": ZuGengSphere,
}
