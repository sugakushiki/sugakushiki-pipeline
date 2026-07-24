"""
axiomatic_edifice.py - How Euclid's Elements is built (数学史記)

Episode 052 (Euclid). Intuition-level visuals for the deductive architecture of
the Elements: constructing from a handful of accepted starting points, the one
odd fifth postulate, and the tower of propositions that rises from the base.
No formal logic -- wonder and intuition only.

Modes:
    construction (default)
        Book I, Proposition 1: build an equilateral triangle on a given segment
        AB using two circles (each centred at an endpoint, radius = AB) and their
        intersection C. Ruler-and-compass steps revealed one at a time.
        Fixed params: segment AB length 1.8 at y=0.2 (A=(-0.9,0.2), B=(0.9,0.2));
        two circles radius 1.8; apex C=(0,1.76); triangle ABC.
    postulates
        The five postulates. Four short, obviously-true ones (each a tiny diagram)
        vs the one long, complex fifth (parallel postulate: a transversal cutting
        two lines whose same-side interior angles sum to less than two right
        angles, so the lines meet on that side).
        Fixed params: P1-P4 as a 2x2 grid of mini-diagrams on the left; P5 as a
        larger diagram on the right.
    tree
        A deductive tower: a base band (definitions / postulates / common notions)
        with propositions rising in levels, each supported by earlier ones.
        Fixed params: base band at y=-1.4; three levels of nodes at y=-0.4/0.6/1.5;
        a few labelled I.1, I.4, I.47, IX.20, XIII.18.

All Text uses FONT (BIZ UDMincho). MathTex holds only ASCII (labels/numbers), no
Japanese. Y range: about -1.85 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    DOWN,
    UP,
    Circle,
    Create,
    DashedVMobject,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Polygon,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class AxiomaticEdifice(Scene):
    """The deductive architecture of Euclid's Elements -- three intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "construction")
        duration = float(params.get("duration", 26))
        if mode == "postulates":
            self._build_postulates(duration)
        elif mode == "tree":
            self._build_tree(duration)
        else:
            self._build_construction(duration)

    # --------------------------------------------------------------- construction
    def _build_construction(self, duration):
        title = Text(
            "『原論』第一巻・命題1 ── 正三角形を作図する",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.7)

        y0 = 0.2
        L = 1.8
        A = np.array([-0.9, y0, 0.0])
        B = np.array([0.9, y0, 0.0])
        C = np.array([0.0, y0 + L * np.sqrt(3) / 2.0, 0.0])  # top intersection

        seg = Line(A, B, color=TEXT_WHITE, stroke_width=5)
        a_dot = Dot(A, color=TEXT_WHITE, radius=0.06)
        b_dot = Dot(B, color=TEXT_WHITE, radius=0.06)
        a_lab = MathTex(r"A", font_size=30, color=TEXT_WHITE).next_to(A, DOWN, buff=0.15)
        b_lab = MathTex(r"B", font_size=30, color=TEXT_WHITE).next_to(B, DOWN, buff=0.15)
        seg_note = Text("与えられた線分", font=FONT, font_size=19, color=TEXT_DIM).move_to(
            [0, y0 - 0.95, 0]
        )

        circ_a = Circle(radius=L, color=ACCENT_CYAN, stroke_width=2.5).move_to(A)
        circ_b = Circle(radius=L, color=ACCENT_CYAN, stroke_width=2.5).move_to(B)

        c_dot = Dot(C, color=ACCENT_GOLD, radius=0.07)
        c_lab = MathTex(r"C", font_size=30, color=ACCENT_GOLD).next_to(C, UP, buff=0.12)
        ca = Line(C, A, color=ACCENT_GOLD, stroke_width=4)
        cb = Line(C, B, color=ACCENT_GOLD, stroke_width=4)
        tri = Polygon(A, B, C, color=ACCENT_GOLD, stroke_width=4).set_fill(
            ACCENT_GOLD, opacity=0.10
        )

        eq = MathTex(r"AB = AC = BC", font_size=30, color=ACCENT_PINK)
        eq.move_to([0, -1.55, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 7.0
        self.play(Create(seg), FadeIn(a_dot), FadeIn(b_dot), run_time=per)
        self.play(FadeIn(a_lab), FadeIn(b_lab), FadeIn(seg_note), run_time=per * 0.7)
        self.play(Create(circ_a), run_time=per)
        self.play(Create(circ_b), run_time=per)
        self.play(FadeIn(c_dot), FadeIn(c_lab), run_time=per * 0.7)
        self.play(Create(ca), Create(cb), FadeIn(tri), run_time=per)
        self.play(FadeIn(eq), run_time=per)
        self.play(Indicate(eq, color=ACCENT_PINK, scale_factor=1.08), run_time=per)
        self.wait(coda)

    # ----------------------------------------------------------------- postulates
    def _build_postulates(self, duration):
        title = Text("『原論』── 5つの公準", font=FONT, font_size=27, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        head_l = Text("4つは、短くて当たり前", font=FONT, font_size=20, color=ACCENT_CYAN)
        head_l.move_to([-3.15, 2.3, 0])

        # 2x2 grid of mini-diagrams (P1..P4)
        centers = {
            1: np.array([-4.2, 1.3, 0.0]),
            2: np.array([-2.1, 1.3, 0.0]),
            3: np.array([-4.2, -0.5, 0.0]),
            4: np.array([-2.1, -0.5, 0.0]),
        }
        p1 = self._mini_p1(centers[1])
        p2 = self._mini_p2(centers[2])
        p3 = self._mini_p3(centers[3])
        p4 = self._mini_p4(centers[4])
        lab1 = Text("1. 二点に直線", font=FONT, font_size=15, color=TEXT_WHITE)
        lab1.next_to(centers[1], DOWN, buff=0.42)
        lab2 = Text("2. 線分を延ばす", font=FONT, font_size=15, color=TEXT_WHITE)
        lab2.next_to(centers[2], DOWN, buff=0.42)
        lab3 = Text("3. 円を描く", font=FONT, font_size=15, color=TEXT_WHITE)
        lab3.next_to(centers[3], DOWN, buff=0.42)
        lab4 = Text("4. 直角はみな等しい", font=FONT, font_size=15, color=TEXT_WHITE)
        lab4.next_to(centers[4], DOWN, buff=0.42)
        left_group = VGroup(p1, p2, p3, p4, lab1, lab2, lab3, lab4)

        head_r = Text("5つめだけ、長く複雑", font=FONT, font_size=20, color=ACCENT_PINK)
        head_r.move_to([2.3, 2.3, 0])
        p5 = self._mini_p5(np.array([2.3, 0.75, 0.0]))
        p5_txt = Text(
            "内角の和が二直角より小さい側で、\n二直線は交わる",
            font=FONT,
            font_size=16,
            color=ACCENT_PINK,
            line_spacing=0.7,
        )
        p5_txt.move_to([2.3, -0.85, 0])

        note = Text(
            "ただ一本だけ、証明されるべき定理のよう ── この違和感が、二千年後に実を結ぶ",
            font=FONT,
            font_size=19,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.75, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(FadeIn(head_l), run_time=per * 0.5)
        self.play(FadeIn(left_group), run_time=per * 1.4)
        self.play(FadeIn(head_r), run_time=per * 0.5)
        self.play(Create(p5), FadeIn(p5_txt), run_time=per * 1.3)
        self.play(Indicate(p5, color=ACCENT_PINK, scale_factor=1.06), run_time=per)
        self.play(FadeIn(note), run_time=per)
        self.wait(coda)

    def _mini_p1(self, c):
        a = c + np.array([-0.6, -0.1, 0.0])
        b = c + np.array([0.6, 0.15, 0.0])
        return VGroup(
            Dot(a, color=TEXT_WHITE, radius=0.05),
            Dot(b, color=TEXT_WHITE, radius=0.05),
            Line(a, b, color=ACCENT_CYAN, stroke_width=3),
        )

    def _mini_p2(self, c):
        a = c + np.array([-0.35, 0.0, 0.0])
        b = c + np.array([0.35, 0.0, 0.0])
        seg = Line(a, b, color=TEXT_WHITE, stroke_width=4)
        ext = DashedVMobject(
            Line(
                c + np.array([-0.8, 0, 0]),
                c + np.array([0.8, 0, 0]),
                color=ACCENT_CYAN,
                stroke_width=2,
            ),
            num_dashes=10,
        )
        return VGroup(ext, seg)

    def _mini_p3(self, c):
        return VGroup(
            Dot(c, color=TEXT_WHITE, radius=0.05),
            Circle(radius=0.55, color=ACCENT_CYAN, stroke_width=3).move_to(c),
        )

    def _mini_p4(self, c):
        l1a = c + np.array([-0.7, -0.35, 0.0])
        r1 = VGroup(
            Line(l1a, l1a + np.array([0, 0.7, 0]), color=ACCENT_CYAN, stroke_width=3),
            Line(l1a, l1a + np.array([0.5, 0, 0]), color=ACCENT_CYAN, stroke_width=3),
        )
        l2a = c + np.array([0.2, -0.35, 0.0])
        r2 = VGroup(
            Line(l2a, l2a + np.array([0, 0.7, 0]), color=ACCENT_CYAN, stroke_width=3),
            Line(l2a, l2a + np.array([0.5, 0, 0]), color=ACCENT_CYAN, stroke_width=3),
        )
        eq = MathTex(r"=", font_size=26, color=TEXT_WHITE).move_to(c + np.array([-0.03, 0.0, 0.0]))
        return VGroup(r1, eq, r2)

    def _mini_p5(self, c):
        # transversal cutting two lines that converge to the right
        base = Line(
            c + np.array([-1.5, -0.75, 0]),
            c + np.array([1.5, -0.55, 0]),
            color=TEXT_WHITE,
            stroke_width=3,
        )
        top = Line(
            c + np.array([-1.5, 0.85, 0]),
            c + np.array([1.5, 0.05, 0]),
            color=TEXT_WHITE,
            stroke_width=3,
        )
        trans = Line(
            c + np.array([-1.0, 1.2, 0]),
            c + np.array([-0.2, -1.2, 0]),
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        meet = Dot(c + np.array([1.5, -0.25, 0]), color=ACCENT_PINK, radius=0.06)
        return VGroup(base, top, trans, meet)

    # ------------------------------------------------------------------------ tree
    def _build_tree(self, duration):
        title = Text(
            "定義・公準・公理から、命題が積み上がる",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        base = Rectangle(width=7.0, height=0.72, color=ACCENT_CYAN, stroke_width=2.5).move_to(
            [0, -1.42, 0]
        )
        base.set_fill(ACCENT_CYAN, opacity=0.10)
        base_lab = Text(
            "定義23・公準5・共通概念5", font=FONT, font_size=19, color=ACCENT_CYAN
        ).move_to([0, -1.42, 0])
        base_group = VGroup(base, base_lab)

        # three levels of nodes
        levels = [
            (-0.45, [-2.6, -1.3, 0.0, 1.3, 2.6], {2: r"\mathrm{I.1}", 3: r"\mathrm{I.4}"}),
            (0.6, [-1.9, -0.6, 0.7, 2.0], {2: r"\mathrm{I.47}"}),
            (1.55, [-1.1, 0.3, 1.7], {1: r"\mathrm{IX.20}", 2: r"\mathrm{XIII.18}"}),
        ]
        node_groups = []
        node_pos = []
        for y, xs, labels in levels:
            row = VGroup()
            pos_row = []
            for i, x in enumerate(xs):
                col = ACCENT_GOLD if i in labels else EDGE_COLOR
                node = Dot([x, y, 0], color=col, radius=0.11 if i in labels else 0.07)
                row.add(node)
                if i in labels:
                    lab = MathTex(labels[i], font_size=22, color=ACCENT_GOLD)
                    lab.next_to([x, y, 0], UP, buff=0.22)
                    row.add(lab)
                pos_row.append(np.array([x, y, 0.0]))
            node_groups.append(row)
            node_pos.append(pos_row)

        # representative edges (base -> L0 -> L1 -> L2)
        def edges_between(lower_pts, upper_pts, pairs):
            g = VGroup()
            for lo, up in pairs:
                g.add(Line(lower_pts[lo], upper_pts[up], color=EDGE_COLOR, stroke_width=1.5))
            return g

        base_top = [np.array([x, -1.06, 0.0]) for x in [-2.6, -1.3, 0.0, 1.3, 2.6]]
        e0 = edges_between(base_top, node_pos[0], [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)])
        e1 = edges_between(node_pos[0], node_pos[1], [(1, 0), (2, 1), (3, 2), (2, 2), (4, 3)])
        e2 = edges_between(node_pos[1], node_pos[2], [(0, 0), (2, 1), (2, 2), (3, 2)])

        cap = Text("全13巻・約465の命題", font=FONT, font_size=20, color=TEXT_WHITE)
        cap.move_to([0, 2.35, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(FadeIn(base_group), run_time=per)
        self.play(Create(e0), FadeIn(node_groups[0]), run_time=per)
        self.play(Create(e1), FadeIn(node_groups[1]), run_time=per)
        self.play(Create(e2), FadeIn(node_groups[2]), run_time=per)
        self.play(FadeIn(cap), run_time=per)
        self.play(Indicate(cap, color=ACCENT_GOLD, scale_factor=1.06), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "construction": {"people": [], "years": []},
    "postulates": {"people": [], "years": []},
    "tree": {"people": [], "years": []},
}

SCENES = {
    "construction": AxiomaticEdifice,
    "postulates": AxiomaticEdifice,
    "tree": AxiomaticEdifice,
}
