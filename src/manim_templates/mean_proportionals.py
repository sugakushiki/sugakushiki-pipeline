"""
mean_proportionals.py - The Delian problem and Hippocrates of Chios' reduction
to two mean proportionals.

The Delian problem (cube doubling) asks for a length x such that x^3 = 2 a^3.
Hippocrates of Chios (5th century BC) reduced this to finding two geometric
mean proportionals r, s between a and 2a, that is, a : r = r : s = s : 2a, from
which r = a * cube_root(2) follows directly. Eratosthenes of Cyrene (3rd
century BC) then built a mechanical device (the mesolabion) that produces
these means physically; see mesolabion.py for the device.

The mean-proportionals reduction itself was Hippocrates', not Eratosthenes' —
this template focuses on that algebraic step.

Modes:
    problem    - Two cubes side-by-side: side a (volume a^3) and side x
                 (volume 2 a^3 = x^3). The unknown x = a * cube_root(2). Caption
                 notes that compass-and-straightedge construction is impossible
                 (Wantzel 1837), shown as a footer note only.
                 Fixed params: a_side = 1.0, x_side = a_side * 2**(1/3) ~ 1.26.
    chain      - The proportional chain a : x = x : y = y : 2a shown as four
                 stacked horizontal segments of lengths a, x, y, 2a. From a:x =
                 x:y comes x^2 = a*y. From x:y = y:2a comes y^2 = 2*a*x.
                 Combining gives x^3 = 2 a^3 (the Delian equation).
                 Fixed params: a = 1.0, x = 2**(1/3), y = 2**(2/3), 2a = 2.0.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0. No trailing FadeOut. Duration-aware.

Used by: Episode 027 (Eratosthenes), pillar B — Delian problem reduction.
"""

import math

from manim import (
    Arrow,
    Create,
    FadeIn,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


class MeanProportionals(Scene):
    """Delian problem and Hippocrates' reduction to two mean proportionals."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "problem")
        self._duration = params.get("duration", 28)

        if mode == "chain":
            self._build_chain()
        else:
            self._build_problem()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=26, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _cube_iso(self, center, side, color, fill_opacity=0.18):
        """Return a VGroup drawing an isometric cube outline at center."""
        cx, cy = center[0], center[1]
        s = side
        # Depth offset (back face shifted up-right)
        d = s * 0.40
        # Front face corners
        fbl = [cx - s / 2, cy - s / 2, 0]
        fbr = [cx + s / 2, cy - s / 2, 0]
        ftr = [cx + s / 2, cy + s / 2, 0]
        ftl = [cx - s / 2, cy + s / 2, 0]
        # Back face corners (shifted by (d*0.7, d*0.5))
        dx, dy = d * 0.75, d * 0.55
        bbl = [fbl[0] + dx, fbl[1] + dy, 0]
        bbr = [fbr[0] + dx, fbr[1] + dy, 0]
        btr = [ftr[0] + dx, ftr[1] + dy, 0]
        btl = [ftl[0] + dx, ftl[1] + dy, 0]
        # Front face polygon (filled)
        front = Polygon(fbl, fbr, ftr, ftl, color=color, stroke_width=2.4)
        front.set_fill(color, opacity=fill_opacity)
        # Top face
        top = Polygon(ftl, ftr, btr, btl, color=color, stroke_width=2.4)
        top.set_fill(color, opacity=fill_opacity * 0.6)
        # Right face
        right = Polygon(fbr, ftr, btr, bbr, color=color, stroke_width=2.4)
        right.set_fill(color, opacity=fill_opacity * 0.8)
        return VGroup(front, top, right)

    # ------------------------------------------------------------------
    def _build_problem(self):
        duration = float(self._duration)
        title = self._title("倍積問題 ── 立方体を二倍に")
        self.play(FadeIn(title), run_time=0.6)

        a_side = 1.20
        x_side = a_side * (2 ** (1 / 3))

        # Left cube: side a, volume a^3
        left_center = [-2.3, 0.4, 0]
        left_cube = self._cube_iso(left_center, a_side, ACCENT_CYAN)
        left_label = MathTex(r"V = a^3", font_size=32, color=ACCENT_CYAN)
        left_label.move_to([left_center[0], left_center[1] - 1.55, 0])
        left_side_lbl = MathTex(r"a", font_size=30, color=ACCENT_CYAN)
        left_side_lbl.move_to([left_center[0] - a_side / 2 - 0.30, left_center[1], 0])

        self.play(Create(left_cube), run_time=0.8)
        self.play(FadeIn(left_label), FadeIn(left_side_lbl), run_time=0.5)

        # Arrow
        arrow = Arrow(
            [-0.85, 0.4, 0], [0.45, 0.4, 0],
            color=ACCENT_GOLD, stroke_width=4, buff=0.0,
            max_tip_length_to_length_ratio=0.20,
        )
        arrow_lbl = Text("二倍にせよ", font=FONT, font_size=18, color=ACCENT_GOLD)
        arrow_lbl.move_to([-0.20, 0.85, 0])
        self.play(Create(arrow), FadeIn(arrow_lbl), run_time=0.6)

        # Right cube: side x, volume x^3 = 2 a^3
        right_center = [2.4, 0.4, 0]
        right_cube = self._cube_iso(right_center, x_side, ACCENT_PINK)
        right_label = MathTex(r"V = x^3 = 2 a^3", font_size=32, color=ACCENT_PINK)
        right_label.move_to([right_center[0], right_center[1] - 1.55, 0])
        right_side_lbl = MathTex(r"x", font_size=32, color=ACCENT_PINK)
        right_side_lbl.move_to([right_center[0] - x_side / 2 - 0.30, right_center[1], 0])

        self.play(Create(right_cube), run_time=0.8)
        self.play(FadeIn(right_label), FadeIn(right_side_lbl), run_time=0.5)

        # Question: x = ?
        question = MathTex(
            r"x \;=\; a \cdot \sqrt[3]{2}",
            font_size=36, color=ACCENT_GOLD,
        )
        question.move_to([0, -1.55, 0])
        self.play(FadeIn(question), run_time=0.7)

        # Footer note
        footer = Text(
            "定規とコンパスでは作図できない（後にヴァンツェル 1837 年証明）",
            font=FONT, font_size=14, color=TEXT_DIM,
        )
        footer.move_to([0, -1.95, 0])
        self.play(FadeIn(footer), run_time=0.5)

        anim_total = 0.6 + 0.8 + 0.5 + 0.6 + 0.8 + 0.5 + 0.7 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_chain(self):
        duration = float(self._duration)
        title = self._title("ヒッポクラテス・ヒオスの帰着 ── 二つの比例中項")
        self.play(FadeIn(title), run_time=0.6)

        # Four segment lengths
        # Use display scale so all fit comfortably
        scale = 2.4
        a = 1.0
        x = 2 ** (1 / 3)
        y = 2 ** (2 / 3)
        two_a = 2.0
        lengths = [a, x, y, two_a]
        labels = [r"a", r"x", r"y", r"2a"]
        colors = [ACCENT_CYAN, ACCENT_PINK, ACCENT_PINK, ACCENT_CYAN]

        # Stack horizontally to the left, with rows y = 1.7, 1.05, 0.40, -0.25
        seg_left_x = -3.0
        ys = [1.55, 0.85, 0.15, -0.55]
        seg_group = VGroup()
        for L, lbl_txt, c, yy in zip(lengths, labels, colors, ys):
            seg = Line([seg_left_x, yy, 0], [seg_left_x + L * scale, yy, 0],
                       color=c, stroke_width=5)
            lbl = MathTex(lbl_txt, font_size=30, color=c)
            lbl.move_to([seg_left_x - 0.45, yy, 0])
            len_lbl = MathTex(rf"{lbl_txt}", font_size=22, color=c)
            len_lbl.move_to([seg_left_x + L * scale + 0.35, yy, 0])
            seg_group.add(seg, lbl)
        self.play(FadeIn(seg_group), run_time=1.0)

        # Proportional chain (header)
        chain_header = MathTex(
            r"a : x \;=\; x : y \;=\; y : 2a",
            font_size=34, color=ACCENT_GOLD,
        )
        chain_header.move_to([0, 2.4, 0])
        self.play(FadeIn(chain_header), run_time=0.6)

        # Algebraic derivation on the right side
        deriv_x = 2.3
        eq1 = MathTex(r"x^2 \;=\; a\,y", font_size=26, color=ACCENT_PINK)
        eq1.move_to([deriv_x, 1.4, 0])
        eq2 = MathTex(r"y^2 \;=\; 2 a\,x", font_size=26, color=ACCENT_PINK)
        eq2.move_to([deriv_x, 0.8, 0])
        eq3 = MathTex(r"\Rightarrow \; x^3 \;=\; 2\,a^3", font_size=30, color=ACCENT_GOLD)
        eq3.move_to([deriv_x, 0.1, 0])
        self.play(FadeIn(eq1), run_time=0.5)
        self.play(FadeIn(eq2), run_time=0.5)
        self.play(FadeIn(eq3), run_time=0.7)

        # Conclusion at bottom
        concl = MathTex(
            r"\therefore \; x \;=\; a \cdot \sqrt[3]{2}",
            font_size=34, color=ACCENT_GOLD,
        )
        concl.move_to([0, -1.55, 0])
        self.play(FadeIn(concl), run_time=0.7)

        # Footer attribution
        footer = Text(
            "比例中項二つへの帰着 ── 前五世紀キオス島の数学者ヒッポクラテスの発見",
            font=FONT, font_size=14, color=TEXT_DIM,
        )
        footer.move_to([0, -1.95, 0])
        self.play(FadeIn(footer), run_time=0.5)

        anim_total = 0.6 + 1.0 + 0.6 + 0.5 + 0.5 + 0.7 + 0.7 + 0.5
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "problem": {"people": [], "years": ["1837"]},
    "chain": {"people": [], "years": []},
}

SCENES = {
    "problem": MeanProportionals,
    "chain": MeanProportionals,
}
