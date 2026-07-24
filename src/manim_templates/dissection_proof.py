"""
dissection_proof.py - Liu Hui's out-in complementary principle (出入相補)

Liu Hui cut figures and rearranged the pieces to prove area/volume relations,
and decomposed a box into qiandu / yangma / bie'nao solids whose 2:1 volume
ratio he settled by an infinite-bisection (limit) argument — the same limit
idea shown for the circle in circle_division.py, applied to a solid.

Redesigned: gougu now shows the actual 弦図
(hypotenuse-square = 4 right triangles + a central square) instead of empty
boxes, with NO caption overlapping the figure; solids draws schematic
isometric solids instead of a flat box + romaji; limit uses Japanese text
only (no romaji).

Modes:
    gougu  - The 弦図 dissection proof of 勾股 (a^2 + b^2 = c^2): the square
             on the hypotenuse is shown as 4 congruent right triangles (朱/青)
             around a central square; rearranged to a^2 + b^2.
             Fixed params: outer square side L=2.3, offset p=0.85.
    solids - A cuboid split (schematic isometric) into 塹堵 (triangular prism,
             1/2), then 陽馬 (rectangular pyramid, 1/3) + 鱉臑 (tetrahedron,
             1/6). Shows 塹堵 = 陽馬 + 鱉臑 and 陽馬 : 鱉臑 = 2 : 1.
             Fixed params: fractions 1/2, 1/3, 1/6; ratio 2:1.
    limit  - 陽馬術: the remainder is 1/4 of the previous each step; in the
             limit it vanishes ("微・無形"); same idea as the circle limit.
             Fixed params: 5 shrinking squares, ratio 1/4 per step.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only; any
CJK content is rendered with Text(font=FONT), never MathTex.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 026 (Liu Hui), pillar B — out-in principle and solid limit.
"""

from manim import (
    Arrow,
    DashedLine,
    FadeIn,
    Line,
    MathTex,
    Polygon,
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


class DissectionProof(Scene):
    """Liu Hui's 出入相補 dissection reasoning — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "gougu")
        self._duration = params.get("duration", 30)

        if mode == "solids":
            self._build_solids()
        elif mode == "limit":
            self._build_limit()
        elif mode == "subdivision_proof":
            self._build_subdivision_proof()
        else:
            self._build_gougu()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _sq(self, x, y, s, color, op):
        """Axis-aligned square from bottom-left (x,y), side s."""
        sq = Polygon(
            [x, y, 0],
            [x + s, y, 0],
            [x + s, y + s, 0],
            [x, y + s, 0],
            color=color,
            stroke_width=2.0,
        )
        sq.set_fill(color, opacity=op)
        return sq

    def _build_gougu(self):
        """出入相補: same outer square (a+b)² shown TWO ways.

        Redesign: the previous layout did not
        visibly "cut and rearrange" -- a^2/b^2 just sat next to a c^2 box.
        Now we show the two classical dissections of the SAME outer square
        of side (a+b):
          Left : (a+b)^2 = a^2 + b^2 + 4 right triangles  (a^2 & b^2 visible)
          Right: (a+b)^2 = c^2          + 4 right triangles  (c^2 tilted)
        The 4 right triangles are the same in both -- their rearrangement
        IS the "出入相補" cut, and a^2 + b^2 = c^2 follows by equating.
        """
        duration = self._duration

        title = self._title("出入相補 ── 同じ正方形を 2 通りに分ける")
        self.play(FadeIn(title), run_time=0.6)

        cap = Text(
            "外側の (a＋b)² は同じ。 中の組み替えで a² ＋ b² ＝ c²",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        cap.move_to([0, 2.35, 0])
        self.play(FadeIn(cap), run_time=0.5)

        # Display sides
        a = 0.95
        b = 1.30
        L = a + b  # outer square side

        # ----- LEFT diagram: (a+b)² = a² + b² + 4 right triangles -----
        Lx, Ly = -3.85, -1.20  # bottom-left of left outer square

        left_outer = Polygon(
            [Lx, Ly, 0],
            [Lx + L, Ly, 0],
            [Lx + L, Ly + L, 0],
            [Lx, Ly + L, 0],
            color=TEXT_WHITE,
            stroke_width=2.2,
        )

        # a² at bottom-left
        Lsq_a = Polygon(
            [Lx, Ly, 0],
            [Lx + a, Ly, 0],
            [Lx + a, Ly + a, 0],
            [Lx, Ly + a, 0],
            color=ACCENT_PINK,
            stroke_width=1.8,
        )
        Lsq_a.set_fill(ACCENT_PINK, opacity=0.34)
        Lla = MathTex(r"a^2", font_size=26, color=ACCENT_PINK)
        Lla.move_to([Lx + a / 2, Ly + a / 2, 0])

        # b² at top-right
        Lsq_b = Polygon(
            [Lx + a, Ly + a, 0],
            [Lx + L, Ly + a, 0],
            [Lx + L, Ly + L, 0],
            [Lx + a, Ly + L, 0],
            color=ACCENT_CYAN,
            stroke_width=1.8,
        )
        Lsq_b.set_fill(ACCENT_CYAN, opacity=0.34)
        Llb = MathTex(r"b^2", font_size=26, color=ACCENT_CYAN)
        Llb.move_to([Lx + a + b / 2, Ly + a + b / 2, 0])

        # Bottom-right a×b rect split into 2 triangles by diagonal (a,0)-(a+b,a)
        Lt_br_lo = Polygon(
            [Lx + a, Ly, 0],
            [Lx + L, Ly, 0],
            [Lx + L, Ly + a, 0],
            color=ACCENT_GOLD,
            stroke_width=1.4,
        )
        Lt_br_lo.set_fill(ACCENT_GOLD, opacity=0.30)
        Lt_br_up = Polygon(
            [Lx + a, Ly, 0],
            [Lx + L, Ly + a, 0],
            [Lx + a, Ly + a, 0],
            color=ACCENT_GOLD,
            stroke_width=1.4,
        )
        Lt_br_up.set_fill(ACCENT_GOLD, opacity=0.18)

        # Top-left a×b rect split into 2 triangles by diagonal (0,a)-(a,a+b)
        Lt_tl_lo = Polygon(
            [Lx, Ly + a, 0],
            [Lx + a, Ly + a, 0],
            [Lx + a, Ly + L, 0],
            color=ACCENT_GOLD,
            stroke_width=1.4,
        )
        Lt_tl_lo.set_fill(ACCENT_GOLD, opacity=0.30)
        Lt_tl_up = Polygon(
            [Lx, Ly + a, 0],
            [Lx + a, Ly + L, 0],
            [Lx, Ly + L, 0],
            color=ACCENT_GOLD,
            stroke_width=1.4,
        )
        Lt_tl_up.set_fill(ACCENT_GOLD, opacity=0.18)

        left_caption = Text("a² ＋ b² ＋ 4 直角三角形", font=FONT, font_size=16, color=TEXT_WHITE)
        left_caption.move_to([Lx + L / 2, Ly - 0.30, 0])

        self.play(FadeIn(left_outer), run_time=0.4)
        self.play(FadeIn(Lsq_a), FadeIn(Lla), FadeIn(Lsq_b), FadeIn(Llb), run_time=0.7)
        self.play(
            FadeIn(Lt_br_lo), FadeIn(Lt_br_up), FadeIn(Lt_tl_lo), FadeIn(Lt_tl_up), run_time=0.6
        )
        self.play(FadeIn(left_caption), run_time=0.35)

        # ----- Arrow in middle -----
        arrow = MathTex(r"\longrightarrow", font_size=44, color=ACCENT_GOLD)
        arrow.move_to([-0.1, Ly + L / 2, 0])
        cut = Text("組み替え", font=FONT, font_size=18, color=TEXT_DIM)
        cut.move_to([-0.1, Ly + L / 2 + 0.50, 0])
        self.play(FadeIn(arrow), FadeIn(cut), run_time=0.5)

        # ----- RIGHT diagram: (a+b)² = c² + 4 right triangles (windmill) -----
        Rx, Ry = 1.40, Ly  # same baseline as left

        right_outer = Polygon(
            [Rx, Ry, 0],
            [Rx + L, Ry, 0],
            [Rx + L, Ry + L, 0],
            [Rx, Ry + L, 0],
            color=TEXT_WHITE,
            stroke_width=2.2,
        )

        # PQRS: marked points on each side, distance b from one corner
        # (each side split into segments of length b then a, going CCW from BL).
        P = [Rx + b, Ry, 0]  # bottom
        Q = [Rx + L, Ry + b, 0]  # right
        R = [Rx + a, Ry + L, 0]  # top   (a from top-left going right -> (a, a+b))
        S = [Rx, Ry + a, 0]  # left  (a from bottom-left going up -> (0, a))

        # Tilted c² square in the middle
        tilted_c = Polygon(P, Q, R, S, color=ACCENT_GOLD, stroke_width=2.2)
        tilted_c.set_fill(ACCENT_GOLD, opacity=0.40)
        Rlc = MathTex(r"c^2", font_size=30, color=ACCENT_GOLD)
        Rlc.move_to([Rx + L / 2, Ry + L / 2, 0])

        # 4 corner right-triangles (same shape as the 4 in the left diagram)
        # Bottom-left: (0,0)-P-S    legs: b along bottom, a along left
        Rt_bl = Polygon([Rx, Ry, 0], P, S, color=ACCENT_GOLD, stroke_width=1.4)
        Rt_bl.set_fill(ACCENT_GOLD, opacity=0.18)
        # Bottom-right: P-(L,0)-Q   legs: a along bottom, b along right
        Rt_br = Polygon(P, [Rx + L, Ry, 0], Q, color=ACCENT_GOLD, stroke_width=1.4)
        Rt_br.set_fill(ACCENT_GOLD, opacity=0.30)
        # Top-right: Q-(L,L)-R   legs: a along right, b along top
        Rt_tr = Polygon(Q, [Rx + L, Ry + L, 0], R, color=ACCENT_GOLD, stroke_width=1.4)
        Rt_tr.set_fill(ACCENT_GOLD, opacity=0.18)
        # Top-left: R-(0,L)-S    legs: b along top, a along left
        Rt_tl = Polygon(R, [Rx, Ry + L, 0], S, color=ACCENT_GOLD, stroke_width=1.4)
        Rt_tl.set_fill(ACCENT_GOLD, opacity=0.30)

        right_caption = Text("c² ＋ 同じ 4 直角三角形", font=FONT, font_size=16, color=TEXT_WHITE)
        right_caption.move_to([Rx + L / 2, Ry - 0.30, 0])

        self.play(FadeIn(right_outer), run_time=0.4)
        self.play(FadeIn(Rt_bl), FadeIn(Rt_br), FadeIn(Rt_tr), FadeIn(Rt_tl), run_time=0.6)
        self.play(FadeIn(tilted_c), FadeIn(Rlc), run_time=0.6)
        self.play(FadeIn(right_caption), run_time=0.35)

        concl = MathTex(r"a^2 + b^2 = c^2", font_size=34, color=ACCENT_GOLD)
        concl.move_to([0, -1.92, 0])
        self.play(FadeIn(concl), run_time=0.7)

        anim = 0.6 + 0.5 + 0.4 + 0.7 + 0.6 + 0.35 + 0.5 + 0.4 + 0.6 + 0.6 + 0.35 + 0.7
        self.wait(max(1.5, duration - anim))

    # ------------------------------------------------------------------
    def _iso_box(self, x, y, w, h, dx, dy, color, op=0.22):
        """A schematic isometric cuboid (front + top + right faces)."""
        front = Polygon(
            [x, y, 0], [x + w, y, 0], [x + w, y + h, 0], [x, y + h, 0], color=color, stroke_width=2
        )
        top = Polygon(
            [x, y + h, 0],
            [x + w, y + h, 0],
            [x + w + dx, y + h + dy, 0],
            [x + dx, y + h + dy, 0],
            color=color,
            stroke_width=2,
        )
        side = Polygon(
            [x + w, y, 0],
            [x + w + dx, y + dy, 0],
            [x + w + dx, y + h + dy, 0],
            [x + w, y + h, 0],
            color=color,
            stroke_width=2,
        )
        for f in (front, top, side):
            f.set_fill(color, opacity=op)
        return VGroup(top, side, front)

    def _iso_prism(self, x, y, w, h, dx, dy, color, op=0.22):
        """Right-triangular prism (塹堵): triangular cross-section, extruded."""
        A, B, C = [x, y, 0], [x + w, y, 0], [x, y + h, 0]
        A2 = [x + dx, y + dy, 0]
        B2 = [x + w + dx, y + dy, 0]
        C2 = [x + dx, y + h + dy, 0]
        front = Polygon(A, B, C, color=color, stroke_width=2)
        hyp = Polygon(C, B, B2, C2, color=color, stroke_width=2)
        bottom = Polygon(A, B, B2, A2, color=color, stroke_width=2)
        back = Polygon(A2, B2, C2, color=color, stroke_width=1.5)
        for f in (bottom, hyp):
            f.set_fill(color, opacity=op * 0.6)
        front.set_fill(color, opacity=op)
        return VGroup(back, bottom, hyp, front)

    def _iso_pyramid(self, x, y, w, h, dx, dy, color, op=0.22):
        """Square pyramid with apex over one base corner (陽馬)."""
        B1 = [x, y, 0]
        B2 = [x + w, y, 0]
        B3 = [x + w + dx, y + dy, 0]
        B4 = [x + dx, y + dy, 0]
        ap = [x, y + h, 0]  # apex directly above corner B1
        base = Polygon(B1, B2, B3, B4, color=color, stroke_width=2)
        f1 = Polygon(B1, B2, ap, color=color, stroke_width=2)
        f2 = Polygon(B2, B3, ap, color=color, stroke_width=2)
        edge4 = Polygon(B4, ap, B1, color=color, stroke_width=1.5)
        base.set_fill(color, opacity=op * 0.5)
        f1.set_fill(color, opacity=op)
        f2.set_fill(color, opacity=op * 0.7)
        return VGroup(base, edge4, f2, f1)

    def _iso_pyramid_nested(self, x, y, w, h, dx, dy, color, op=0.22):
        """陽馬 with a nested 1/2-scale similar yangma sharing the apex.

        The nested small yangma is drawn as a stroke-only wireframe so the
        big-yangma fill stays visible underneath; this visualises that the
        big陽馬 strictly contains a self-similar half-scale copy of itself.
        """
        big = self._iso_pyramid(x, y, w, h, dx, dy, color, op)
        # Shared apex of big and small
        ap = [x, y + h, 0]
        # Big-base corners (must mirror _iso_pyramid)
        B1 = [x, y, 0]
        B2 = [x + w, y, 0]
        B3 = [x + w + dx, y + dy, 0]
        B4 = [x + dx, y + dy, 0]
        # Small base corners: midpoints of (apex, big-base-corner)
        s1 = [(B1[0] + ap[0]) / 2, (B1[1] + ap[1]) / 2, 0]
        s2 = [(B2[0] + ap[0]) / 2, (B2[1] + ap[1]) / 2, 0]
        s3 = [(B3[0] + ap[0]) / 2, (B3[1] + ap[1]) / 2, 0]
        s4 = [(B4[0] + ap[0]) / 2, (B4[1] + ap[1]) / 2, 0]
        # Visible faces of the small yangma (front-bottom + 2 sides).
        small_base = Polygon(s1, s2, s3, s4, color=color, stroke_width=1.4)
        small_base.set_fill(color, opacity=0)
        small_f1 = Polygon(s1, s2, ap, color=color, stroke_width=1.4)
        small_f1.set_fill(color, opacity=0)
        small_f2 = Polygon(s2, s3, ap, color=color, stroke_width=1.4)
        small_f2.set_fill(color, opacity=0)
        return VGroup(big, small_base, small_f1, small_f2)

    def _iso_tetra(self, x, y, w, h, dx, dy, color, op=0.22):
        """Tetrahedron (鱉臑): triangular base + apex, all-triangular faces."""
        T1 = [x, y, 0]
        T2 = [x + w, y, 0]
        T3 = [x + w * 0.5 + dx, y + dy, 0]
        T4 = [x + w * 0.45, y + h, 0]  # apex
        base = Polygon(T1, T2, T3, color=color, stroke_width=1.5)
        fa = Polygon(T1, T2, T4, color=color, stroke_width=2)
        fb = Polygon(T2, T3, T4, color=color, stroke_width=2)
        edge = Polygon(T1, T4, T3, color=color, stroke_width=1.5)
        base.set_fill(color, opacity=op * 0.4)
        fa.set_fill(color, opacity=op)
        fb.set_fill(color, opacity=op * 0.6)
        return VGroup(base, edge, fb, fa)

    def _iso_tetra_nested(self, x, y, w, h, dx, dy, color, op=0.22):
        """鱉臑 with a nested 1/2-scale similar tetra sharing the apex.

        Stroke-only wireframe so the big-tetra fill stays visible; this
        visualises self-similarity of the 鱉臑 under bisection.
        """
        big = self._iso_tetra(x, y, w, h, dx, dy, color, op)
        T1 = [x, y, 0]
        T2 = [x + w, y, 0]
        T3 = [x + w * 0.5 + dx, y + dy, 0]
        T4 = [x + w * 0.45, y + h, 0]
        # Small tetra: midpoints of (T4=apex, other vertex)
        s1 = [(T1[0] + T4[0]) / 2, (T1[1] + T4[1]) / 2, 0]
        s2 = [(T2[0] + T4[0]) / 2, (T2[1] + T4[1]) / 2, 0]
        s3 = [(T3[0] + T4[0]) / 2, (T3[1] + T4[1]) / 2, 0]
        sf1 = Polygon(s1, s2, T4, color=color, stroke_width=1.4)
        sf1.set_fill(color, opacity=0)
        sf2 = Polygon(s2, s3, T4, color=color, stroke_width=1.4)
        sf2.set_fill(color, opacity=0)
        sbase = Polygon(s1, s2, s3, color=color, stroke_width=1.4)
        sbase.set_fill(color, opacity=0)
        return VGroup(big, sbase, sf2, sf1)

    # ------------------------------------------------------------------
    # Helpers for the subdivision_proof mode (math_11b).
    # ------------------------------------------------------------------
    def _iso_box_split_diag(self, x, y, w, h, dx, dy, color1, color2, op=0.30):
        """Iso cube with internal diagonal split (front-lower / back-upper).

        - Front face (y=ymin) : entirely color1 (e.g. 陽馬-side, GOLD)
        - Top face   (z=zmax) : entirely color2 (e.g. 鱉臑-side, CYAN)
        - Right face (x=xmax) : split diagonally -- lower-front color1 +
                                upper-back color2, separated by a visible
                                diagonal from TRF (top-right-front) to BRB
                                (bottom-right-back). This visualises the
                                slanted internal plane y = b(1 - z/c) that
                                separates 陽馬 / 鱉臑 inside this sub-octant.
        """
        BLF = [x, y, 0]
        BRF = [x + w, y, 0]
        TLF = [x, y + h, 0]
        TRF = [x + w, y + h, 0]
        BRB = [x + w + dx, y + dy, 0]
        TRB = [x + w + dx, y + h + dy, 0]
        TLB = [x + dx, y + h + dy, 0]
        # Front face : color1
        front = Polygon(BLF, BRF, TRF, TLF, color=color1, stroke_width=1.5)
        front.set_fill(color1, opacity=op)
        # Top face : color2
        top = Polygon(TLF, TRF, TRB, TLB, color=color2, stroke_width=1.5)
        top.set_fill(color2, opacity=op)
        # Right face: lower-front triangle color1, upper-back triangle color2
        right_lower = Polygon(BRF, BRB, TRF, color=color1, stroke_width=1.2)
        right_lower.set_fill(color1, opacity=op * 0.75)
        right_upper = Polygon(BRB, TRB, TRF, color=color2, stroke_width=1.2)
        right_upper.set_fill(color2, opacity=op * 0.75)
        return VGroup(front, top, right_lower, right_upper)

    def _iso_prism_stroke(self, x, y, w, h, dx, dy, color, sw=1.2):
        """Wireframe-only wedge (no fill) -- used to draw a nested
        half-scale self-similar 小塹堵 inside a filled residue piece.
        Visible edges only (front triangle + slanted back face)."""
        A, B, C = [x, y, 0], [x + w, y, 0], [x, y + h, 0]
        B2 = [x + w + dx, y + dy, 0]
        C2 = [x + dx, y + h + dy, 0]
        front = Polygon(A, B, C, color=color, stroke_width=sw)
        front.set_fill(color, opacity=0)
        hyp = Polygon(C, B, B2, C2, color=color, stroke_width=sw)
        hyp.set_fill(color, opacity=0)
        return VGroup(front, hyp)

    def _build_solids(self):
        """立体の分解: definitions of 直方体 / 塹堵 / 陽馬 / 鱉臑 with fractions.

        Matches the existing math_11 narration (mentions 直方体, 1/2, 1/3,
        1/6, and the resulting 2:1). The geometric proof of WHY 2:1 lives
        in the new math_11b (subdivision_proof) and the limit argument is
        in math_12; this scene is just the definitions + the statement.
        """
        duration = self._duration

        title = self._title("立体の分解 ── 塹堵・陽馬・鱉臑")
        self.play(FadeIn(title), run_time=0.6)

        box = self._iso_box(-5.0, 0.5, 1.5, 1.3, 0.55, 0.45, TEXT_WHITE, 0.16)
        bl = Text("直方体", font=FONT, font_size=20, color=TEXT_WHITE)
        bl.move_to([-4.0, -0.05, 0])
        self.play(FadeIn(box), FadeIn(bl), run_time=0.8)

        rows = [
            (self._iso_prism, "塹堵 (三角柱)", r"\tfrac12", ACCENT_CYAN, 1.6),
            (self._iso_pyramid, "陽馬 (四角錐)", r"\tfrac13", ACCENT_GOLD, 0.45),
            (self._iso_tetra, "鱉臑 (四面体)", r"\tfrac16", ACCENT_PINK, -0.7),
        ]
        for shape, name, frac, col, y in rows:
            ic = shape(-2.0, y - 0.34, 0.85, 0.7, 0.34, 0.26, col, 0.24)
            nm = Text(name, font=FONT, font_size=24, color=col)
            nm.move_to([0.9, y, 0])
            fr = MathTex(frac, font_size=34, color=col)
            fr.move_to([3.3, y, 0])
            self.play(FadeIn(ic), FadeIn(nm), FadeIn(fr), run_time=0.55)

        rel = Text("塹堵 ＝ 陽馬 ＋ 鱉臑", font=FONT, font_size=22, color=TEXT_DIM)
        rel.move_to([0.4, -1.55, 0])
        ratio_jp = Text("陽馬 ： 鱉臑 ＝ 2 ： 1", font=FONT, font_size=26, color=ACCENT_GOLD)
        ratio_jp.move_to([0, -1.95, 0])
        self.play(FadeIn(rel), run_time=0.5)
        self.play(FadeIn(ratio_jp), run_time=0.6)

        anim = 0.6 + 0.8 + 0.55 * 3 + 0.5 + 0.6
        self.wait(max(1.5, duration - anim))

    # ------------------------------------------------------------------
    def _build_limit(self):
        """陽馬術 — 4-cell countable bar with self-similarity zoom cones (v3).

        Each bar splits into 4 unit cells [gold | gold | cyan | pink]:
          2 gold = 陽馬 portion (settled), 1 cyan = 鱉臑 (settled),
          1 pink = residue handed to next step. 2:1 readable by cell count.
        Dashed pink leaders connect each pink → the entire next bar so the
        self-similarity of the residue is visually explicit.
        """
        duration = self._duration

        title = self._title("陽馬術 ── 残差は段ごとに 1/4")
        self.play(FadeIn(title), run_time=0.6)

        cap = Text(
            "各段: 3/4 (陽馬:鱉臑=2:1) 確定 + 1/4 ピンクは 1 段小さい同じ塹堵 (自相似)",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        cap.move_to([0, 2.35, 0])
        self.play(FadeIn(cap), run_time=0.5)

        # Bar split into 4 equal-width unit cells: [gold | gold | cyan | pink]
        # 2 gold cells vs 1 cyan cell = 2:1 directly readable by cell count.
        def _bar3(cx, cy, w, h, with_legend=False):
            cell_w = w / 4.0
            x_left = cx - w / 2.0
            gap = 0.025  # small visual gap between the 2 gold cells

            g1 = Polygon(
                [x_left, cy - h / 2, 0],
                [x_left + cell_w - gap, cy - h / 2, 0],
                [x_left + cell_w - gap, cy + h / 2, 0],
                [x_left, cy + h / 2, 0],
                color=ACCENT_GOLD,
                stroke_width=1.6,
            )
            g1.set_fill(ACCENT_GOLD, opacity=0.45)
            g2 = Polygon(
                [x_left + cell_w + gap, cy - h / 2, 0],
                [x_left + 2 * cell_w, cy - h / 2, 0],
                [x_left + 2 * cell_w, cy + h / 2, 0],
                [x_left + cell_w + gap, cy + h / 2, 0],
                color=ACCENT_GOLD,
                stroke_width=1.6,
            )
            g2.set_fill(ACCENT_GOLD, opacity=0.45)
            cyan = Polygon(
                [x_left + 2 * cell_w, cy - h / 2, 0],
                [x_left + 3 * cell_w, cy - h / 2, 0],
                [x_left + 3 * cell_w, cy + h / 2, 0],
                [x_left + 2 * cell_w, cy + h / 2, 0],
                color=ACCENT_CYAN,
                stroke_width=1.6,
            )
            cyan.set_fill(ACCENT_CYAN, opacity=0.45)
            pink = Polygon(
                [x_left + 3 * cell_w, cy - h / 2, 0],
                [x_left + 4 * cell_w, cy - h / 2, 0],
                [x_left + 4 * cell_w, cy + h / 2, 0],
                [x_left + 3 * cell_w, cy + h / 2, 0],
                color=ACCENT_PINK,
                stroke_width=1.6,
            )
            pink.set_fill(ACCENT_PINK, opacity=0.45)

            extras = []
            if with_legend:
                lg = Text("陽馬", font=FONT, font_size=18, color=ACCENT_GOLD)
                lg.move_to([x_left + cell_w, cy + h / 2 + 0.27, 0])
                lc = Text("鱉臑", font=FONT, font_size=18, color=ACCENT_CYAN)
                lc.move_to([x_left + 2.5 * cell_w, cy + h / 2 + 0.27, 0])
                lp = Text("残差", font=FONT, font_size=18, color=ACCENT_PINK)
                lp.move_to([x_left + 3.5 * cell_w, cy + h / 2 + 0.27, 0])
                unit2 = MathTex(r"2", font_size=28, color=ACCENT_GOLD)
                unit2.move_to([x_left + cell_w, cy - h / 2 - 0.34, 0])
                colon = MathTex(r":", font_size=28, color=TEXT_DIM)
                colon.move_to([x_left + 1.75 * cell_w, cy - h / 2 - 0.34, 0])
                unit1 = MathTex(r"1", font_size=28, color=ACCENT_CYAN)
                unit1.move_to([x_left + 2.5 * cell_w, cy - h / 2 - 0.34, 0])
                extras = [lg, lc, lp, unit2, colon, unit1]
            return VGroup(g1, g2, cyan, pink, *extras), pink

        # Four levels: visual half-width per step (geometric 1/2 proxy for
        # the actual 1/4 volume shrinkage; the math labels carry the exact
        # ratio). Fixed label_x prevents (1/64) overlapping the smallest bar.
        label_x = 3.95
        levels = [
            # (cy, w,  h,  label_tex, with_legend)
            (1.55, 6.0, 0.55, r"= 1", True),
            (0.30, 3.0, 0.40, r"= \tfrac{1}{4}", False),
            (-0.60, 1.5, 0.28, r"= \tfrac{1}{16}", False),
            (-1.30, 0.75, 0.18, r"= \tfrac{1}{64}", False),
        ]
        for cy, w, h, scale_tex, with_legend in levels:
            bar_grp, _pink = _bar3(0.0, cy, w, h, with_legend=with_legend)
            scale_lbl = MathTex(scale_tex, font_size=24, color=TEXT_DIM)
            scale_lbl.move_to([label_x, cy, 0])
            self.play(FadeIn(bar_grp), FadeIn(scale_lbl), run_time=0.5)

        # Self-similarity zoom cones: pink of bar N → full top of bar N+1
        sim_leaders = VGroup()
        for i in range(len(levels) - 1):
            cy_n, w_n, h_n, _, _ = levels[i]
            cy_next, w_next, h_next, _, _ = levels[i + 1]
            pink_bl = [w_n * 0.25, cy_n - h_n / 2, 0]
            pink_br = [w_n * 0.50, cy_n - h_n / 2, 0]
            next_tl = [-w_next / 2, cy_next + h_next / 2, 0]
            next_tr = [w_next / 2, cy_next + h_next / 2, 0]
            sim_leaders.add(
                DashedLine(
                    pink_bl,
                    next_tl,
                    color=ACCENT_PINK,
                    stroke_width=1.0,
                    stroke_opacity=0.55,
                    dash_length=0.07,
                )
            )
            sim_leaders.add(
                DashedLine(
                    pink_br,
                    next_tr,
                    color=ACCENT_PINK,
                    stroke_width=1.0,
                    stroke_opacity=0.55,
                    dash_length=0.07,
                )
            )
        self.play(FadeIn(sim_leaders), run_time=0.7)

        concl = Text(
            "残差 → 0  で  陽馬 ： 鱉臑 ＝ 2 ： 1  が成立",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        concl.move_to([0, -1.92, 0])
        self.play(FadeIn(concl), run_time=0.7)

        anim = 0.6 + 0.5 + 0.5 * len(levels) + 0.7 + 0.7
        self.wait(max(1.5, duration - anim))

    # ------------------------------------------------------------------
    def _draw_6piece_subdivision(self, px, py, su, sdx, sdy, gap):
        """Draw the 6-piece subdivision of a 塹堵 at the given anchor (px, py).

        Returns (VGroup of pieces, VGroup of unit labels). Same color scheme
        as the main proof; used at TWO scales -- once for the big 塹堵 and
        once for ONE of its pink residues (zoomed up to be visible). That
        repetition makes the recursion (residue = 同じ塹堵 with same 2:1
        inside) directly visible.
        """

        def sub_pos(i, j, k):
            return (px + i * (su + gap) + j * sdx, py + k * (su + gap) + j * sdy)

        pieces = []
        labels = []

        # (0,1,1): CYAN wedge (all 鱉臑) -- furthest back, drawn first
        x, y = sub_pos(0, 1, 1)
        pieces.append(self._iso_prism(x, y, su, su, sdx, sdy, ACCENT_CYAN, op=0.65))
        lbl = MathTex(r"\tfrac12", font_size=16, color=ACCENT_CYAN)
        lbl.move_to([x - 0.22, y + su * 0.55, 0])
        labels.append(lbl)

        # (1,1,0): PINK wedge (residue) + dividing line (small陽馬 vs 小鱉臑)
        x, y = sub_pos(1, 1, 0)
        pieces.append(self._iso_prism(x, y, su, su, sdx, sdy, ACCENT_PINK, op=0.55))
        # Dividing plane inside this small 塹堵: triangle front-top → back-bottom edge.
        # Most visible edge = diagonal on the hypotenuse face (C → B2).
        split_line = Line(
            [x, y + su, 0],  # C: front-top corner
            [x + su + sdx, y + sdy, 0],  # B2: back-bottom-right corner
            color=TEXT_WHITE,
            stroke_width=1.8,
            stroke_opacity=0.85,
        )
        pieces.append(split_line)
        lbl = MathTex(r"\tfrac12", font_size=16, color=ACCENT_PINK)
        lbl.move_to([x + su + 0.20, y + su * 0.30, 0])
        labels.append(lbl)

        # (0,1,0): full cube split (front=GOLD, top=CYAN, right diagonal)
        x, y = sub_pos(0, 1, 0)
        pieces.append(
            self._iso_box_split_diag(x, y, su, su, sdx, sdy, ACCENT_GOLD, ACCENT_CYAN, op=0.65)
        )
        lbl_g = MathTex(r"\tfrac12", font_size=13, color=ACCENT_GOLD)
        lbl_g.move_to([x + su * 0.50, y + su * 0.50, 0])
        lbl_c = MathTex(r"\tfrac12", font_size=13, color=ACCENT_CYAN)
        lbl_c.move_to([x + su * 0.65 + sdx * 0.5, y + su + sdy * 0.5, 0])
        labels.extend([lbl_g, lbl_c])

        # (0,0,1): PINK wedge (residue) + dividing line (small陽馬 vs 小鱉臑)
        x, y = sub_pos(0, 0, 1)
        pieces.append(self._iso_prism(x, y, su, su, sdx, sdy, ACCENT_PINK, op=0.55))
        # Same dividing plane geometry: front-top corner → back-bottom edge.
        split_line = Line(
            [x, y + su, 0],  # C: front-top corner
            [x + su + sdx, y + sdy, 0],  # B2: back-bottom-right corner
            color=TEXT_WHITE,
            stroke_width=1.8,
            stroke_opacity=0.85,
        )
        pieces.append(split_line)
        lbl = MathTex(r"\tfrac12", font_size=16, color=ACCENT_PINK)
        lbl.move_to([x - 0.22, y + su * 0.55, 0])
        labels.append(lbl)

        # (1,0,0): GOLD wedge
        x, y = sub_pos(1, 0, 0)
        pieces.append(self._iso_prism(x, y, su, su, sdx, sdy, ACCENT_GOLD, op=0.65))
        lbl = MathTex(r"\tfrac12", font_size=16, color=ACCENT_GOLD)
        lbl.move_to([x + su + 0.20, y + su * 0.30, 0])
        labels.append(lbl)

        # (0,0,0): GOLD cube -- the unique full-unit piece
        x, y = sub_pos(0, 0, 0)
        pieces.append(self._iso_box(x, y, su, su, sdx, sdy, ACCENT_GOLD, op=0.65))
        lbl = MathTex(r"1", font_size=20, color=ACCENT_GOLD)
        lbl.move_to([x + su / 2, y - 0.20, 0])
        labels.append(lbl)

        return VGroup(*pieces), VGroup(*labels)

    def _build_subdivision_proof(self):
        """math_11b: 3D proof of 陽馬:鱉臑 = 2:1 with explicit recursion.

        TWO panes (same 6-piece subdivision pattern at two scales):
          LEFT  pane = the big 塹堵's subdivision
          RIGHT pane = ONE residue (small 塹堵) zoomed up so its identical
                       6-piece subdivision is visible at readable size.

        An arrow from the LEFT's residue → RIGHT pane labels the move
        "residue 拡大 → 同じ 6 ピース構造". This is the proof-relevant
        similarity: residue = 元の塹堵の 1/2 サイズ版, with the same 2:1
        inside. The recursion (and limit) is what nails the ratio.

        Sub-piece table (per pane, in local i, j, k each in {0,1}):
          (0,0,0)  full cube                  -> GOLD,        1   unit
          (1,0,0)  wedge                      -> GOLD,        1/2 unit
          (0,1,0)  full cube w/ diagonal split -> GOLD + CYAN, 1/2 + 1/2
          (0,1,1)  wedge                      -> CYAN,        1/2 unit
          (1,1,0)  wedge                      -> PINK,        1/2 unit (residue)
          (0,0,1)  wedge                      -> PINK,        1/2 unit (residue)
          (1,0,1) and (1,1,1) are EMPTY.
        """
        duration = self._duration

        title = self._title("塹堵を 8 等分 ── residue は同じ塹堵 (再帰で 2:1)")
        self.play(FadeIn(title), run_time=0.6)

        cap = Text(
            "中身の 6 ピースを色分け。 残差は元の塹堵の 1/2 サイズ → 中も同じ 6 ピース",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        cap.move_to([0, 2.50, 0])
        self.play(FadeIn(cap), run_time=0.4)

        # Iso projection params: sdx > su keeps j=1 layer clear of j=0.
        su = 0.50
        sdx = 0.72
        sdy = 0.40
        gap = 0.05

        # ----- LEFT pane: the big 塹堵 -----
        L_px, L_py = -5.40, -0.90
        L_pieces, L_labels = self._draw_6piece_subdivision(
            L_px,
            L_py,
            su,
            sdx,
            sdy,
            gap,
        )
        L_caption = Text("元の塹堵 (8 等分)", font=FONT, font_size=15, color=TEXT_DIM)
        L_caption.move_to([L_px + su + sdx * 0.5, L_py - 0.45, 0])

        # ----- RIGHT pane: ONE residue, zoomed (same 6-piece pattern) -----
        R_px, R_py = -0.50, -0.90
        R_pieces, R_labels = self._draw_6piece_subdivision(
            R_px,
            R_py,
            su,
            sdx,
            sdy,
            gap,
        )
        R_caption = Text(
            "residue 拡大 ＝ 同じ 6 ピース構造 (1 段小さい塹堵)",
            font=FONT,
            font_size=15,
            color=TEXT_DIM,
        )
        R_caption.move_to([R_px + su + sdx * 0.5, R_py - 0.45, 0])

        # Show LEFT first, then arrow, then RIGHT
        self.play(FadeIn(L_pieces), FadeIn(L_labels), FadeIn(L_caption), run_time=0.9)

        # Arrow from left pink residue → right pane (visually:
        # "this small residue, expanded, is the right pane").
        arrow = Arrow(
            start=[-2.55, 0.10, 0],
            end=[-0.95, 0.10, 0],
            color=ACCENT_PINK,
            stroke_width=3.0,
            buff=0.05,
            max_tip_length_to_length_ratio=0.10,
        )
        arrow_lbl = Text("residue 拡大", font=FONT, font_size=15, color=ACCENT_PINK)
        arrow_lbl.move_to([(arrow.get_start()[0] + arrow.get_end()[0]) / 2, 0.42, 0])
        self.play(FadeIn(arrow), FadeIn(arrow_lbl), run_time=0.4)

        self.play(FadeIn(R_pieces), FadeIn(R_labels), FadeIn(R_caption), run_time=0.9)

        # ----- Bottom: counting summary (BOTH panes share the same count) -----
        cnt_y = -1.70
        yg_lbl = Text("陽馬", font=FONT, font_size=18, color=ACCENT_GOLD)
        yg_eq = MathTex(r"= 1 + \tfrac12 + \tfrac12 = 2", font_size=22, color=ACCENT_GOLD)
        sep1 = Text("、", font=FONT, font_size=18, color=TEXT_DIM)
        bb_lbl = Text("鱉臑", font=FONT, font_size=18, color=ACCENT_CYAN)
        bb_eq = MathTex(r"= \tfrac12 + \tfrac12 = 1", font_size=22, color=ACCENT_CYAN)
        sep2 = Text("、", font=FONT, font_size=18, color=TEXT_DIM)
        zr_lbl = Text("residue", font=FONT, font_size=18, color=ACCENT_PINK)
        zr_eq = MathTex(r"= 1", font_size=22, color=ACCENT_PINK)
        count_grp = VGroup(yg_lbl, yg_eq, sep1, bb_lbl, bb_eq, sep2, zr_lbl, zr_eq).arrange(
            buff=0.08
        )
        count_grp.move_to([0, cnt_y, 0])
        self.play(FadeIn(count_grp), run_time=0.6)

        # ----- Conclusion -----
        concl = Text(
            "⇒ residue 内も同じ 2:1。 全体で 陽馬 ： 鱉臑 ＝ 2 ： 1",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        concl.move_to([0, -2.05, 0])
        self.play(FadeIn(concl), run_time=0.6)

        anim = 0.6 + 0.4 + 0.9 + 0.4 + 0.9 + 0.6 + 0.6
        self.wait(max(1.5, duration - anim))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "gougu": {"people": [], "years": []},
    "solids": {"people": [], "years": []},
    "limit": {"people": [], "years": []},
    "subdivision_proof": {"people": [], "years": []},
}

SCENES = {
    "gougu": DissectionProof,
    "solids": DissectionProof,
    "limit": DissectionProof,
    "subdivision_proof": DissectionProof,
}
