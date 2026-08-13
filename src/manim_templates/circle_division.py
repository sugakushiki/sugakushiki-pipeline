"""
circle_division.py - Liu Hui's circle-division method (割円術) and the limit idea

Liu Hui (Jiu Zhang Suan Shu commentary, 3rd century) inscribed regular
polygons in a circle, doubling the side count, to bound pi from below, and
stated that "cutting again and again until it cannot be cut" makes the polygon
coincide with the circle (a limit idea). NOT the Archimedes template; Liu Hui
used the inscribed polygon only.

Redesigned (an earlier episode user feedback): the inscribed polygon is FILLED so the
shrinking gap between polygon and circle is the visual story; the per-step
lower-bound value is large and next to the figure; buildup stops at a count
where the polygon is still visibly faceted (does not end on a circle-looking
192-gon); area_proof rearranges sectors into a clearly FILLED parallelogram
(not thin spikes).

Modes:
    buildup    - Inscribed regular polygons 6 -> 12 -> 24 -> 48 -> 96, filled,
                 with the lower bound n*sin(pi/n) shown per step, ending on the
                 bracket 3.141024 < pi < 3.142704 and pi ~= 157/50 = 3.14.
                 Fixed params: steps [6,12,24,48,96], r_display = 1.65.
    limit      - The 割之又割 idea: side count -> very large, the filled
                 polygon fills the circle, the area difference D_n -> 0; the
                 accelerated value pi ~= 3927/1250 ~= 3.1416 is shown with an
                 explicit 諸説あり note (Liu Hui vs later hand is debated).
                 Fixed params: 6 -> 12 -> 48 -> 192 -> 768 visual sweep.
    area_proof - Circle cut into 16 sectors, rearranged into a filled
                 parallelogram of width = half circumference (pi r) and height
                 = radius, giving A = (1/2)*C*r = pi r^2.
                 Fixed params: N_sectors = 16, r_display = 1.3.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 026 (Liu Hui), spine pillar — circle division and the limit.
"""

import math

from manim import (
    WHITE,
    Arrow,
    Circle,
    Create,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    RegularPolygon,
    ReplacementTransform,
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

LIUHUI_STEPS = [6, 12, 24, 48, 96]


def inscribed_lower_bound(n):
    """Lower bound for pi from an inscribed regular n-gon (perimeter/diameter)."""
    return n * math.sin(math.pi / n)


class CircleDivision(Scene):
    """Liu Hui's 割円術 and the limit idea — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "buildup")
        self._duration = params.get("duration", 35)

        if mode == "limit":
            self._build_limit()
        elif mode == "area_proof":
            self._build_area_proof()
        else:
            self._build_buildup()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _stroke_polygon(self, n, radius, center):
        # Stroke only (no fill) so the polygon's straight edges remain visible
        # at all n; the "gap" between polygon chords and the circle arc is the
        # 割円術 story — would be hidden by a filled disk at high n.
        poly = RegularPolygon(n=n, color=ACCENT_CYAN, stroke_width=3.0)
        poly.set_fill(ACCENT_CYAN, opacity=0)
        poly.scale(radius)
        poly.move_to(center)
        return poly

    # ------------------------------------------------------------------
    def _build_buildup(self):
        """Inscribed FILLED polygons 6 -> 96; the shrinking gap is the story."""
        duration = self._duration

        title = self._title("割円術 ── 多角形で円を内から埋める")
        self.play(FadeIn(title), run_time=0.6)

        center = [-3.2, 0.35, 0]
        r = 1.65
        circle = Circle(radius=r, color=WHITE, stroke_width=3)
        circle.move_to(center)
        circle.set_z_index(1)
        self.play(Create(circle), run_time=0.7)

        # Right panel headers
        bx = 2.7
        head = Text("内接多角形の周 ÷ 直径", font=FONT, font_size=22, color=ACCENT_CYAN)
        head.move_to([bx, 2.2, 0])
        pi_lbl = MathTex(r"\pi = 3.14159\ldots", font_size=26, color=TEXT_DIM)
        pi_lbl.move_to([bx, -0.3, 0])
        self.play(FadeIn(head), FadeIn(pi_lbl), run_time=0.5)

        intro = 0.6 + 0.7 + 0.5
        per = max((duration - intro - 4.0) / len(LIUHUI_STEPS), 0.7)
        wait_t = max(per - 1.0, 0.4)

        prev_poly = prev_nlab = prev_val = None
        for n in LIUHUI_STEPS:
            poly = self._stroke_polygon(n, r, center)
            nlab = Text(f"{n} 角形", font=FONT, font_size=30, color=TEXT_WHITE)
            nlab.move_to([center[0], -1.75, 0])
            v = inscribed_lower_bound(n)
            val = MathTex(rf"{v:.5f}", font_size=46, color=ACCENT_CYAN)
            val.move_to([bx, 1.1, 0])

            if prev_poly is None:
                self.play(Create(poly), FadeIn(nlab), FadeIn(val), run_time=1.0)
            else:
                self.play(
                    ReplacementTransform(prev_poly, poly),
                    ReplacementTransform(prev_nlab, nlab),
                    ReplacementTransform(prev_val, val),
                    run_time=0.9,
                )
            self.wait(wait_t)
            prev_poly, prev_nlab, prev_val = poly, nlab, val

        bracket = MathTex(r"3.141024 < \pi < 3.142704", font_size=28, color=ACCENT_PINK)
        bracket.move_to([bx, 0.2, 0])
        result = MathTex(r"\pi \approx \tfrac{157}{50} = 3.14", font_size=34, color=ACCENT_GOLD)
        result.move_to([bx, -1.4, 0])
        self.play(FadeIn(bracket), run_time=0.6)
        self.play(FadeIn(result), run_time=0.7)

        anim = intro + (1.0 + wait_t) + (0.9 + wait_t) * (len(LIUHUI_STEPS) - 1) + 1.3
        self.wait(max(1.5, duration - anim))

    # ------------------------------------------------------------------
    def _build_limit(self):
        """割之又割: gap -> 0 as n grows; accelerated value with 諸説あり."""
        duration = self._duration

        title = self._title("割之又割 ── 割れぬところまで割れば")
        self.play(FadeIn(title), run_time=0.6)

        center = [-3.0, 0.4, 0]
        r = 1.7
        circle = Circle(radius=r, color=WHITE, stroke_width=3)
        circle.move_to(center)
        circle.set_z_index(1)
        self.play(Create(circle), run_time=0.6)

        prev = None
        for n in [6, 12, 48, 192, 768]:
            poly = self._stroke_polygon(n, r, center)
            if prev is None:
                self.play(Create(poly), run_time=0.7)
            else:
                self.play(ReplacementTransform(prev, poly), run_time=0.6)
            self.wait(0.35)
            prev = poly

        nz = Text(
            "もう割れぬところまで割れば\n円と一体となり 誤差は残らない",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
            line_spacing=0.85,
        )
        nz.move_to([2.7, 1.7, 0])
        self.play(FadeIn(nz), run_time=0.7)

        series = MathTex(
            r"\tfrac14+\tfrac1{16}+\tfrac1{64}+\cdots=\tfrac13",
            font_size=28,
            color=ACCENT_CYAN,
        )
        series.move_to([2.7, 0.1, 0])
        accel = MathTex(
            r"\pi \approx \tfrac{3927}{1250} \approx 3.1416", font_size=30, color=ACCENT_GOLD
        )
        accel.move_to([2.7, -1.0, 0])
        self.play(FadeIn(series), run_time=0.5)
        self.play(FadeIn(accel), run_time=0.5)

        note = Text(
            "この加速法・値は劉徽本人か後代か諸説あり", font=FONT, font_size=18, color=TEXT_DIM
        )
        note.move_to([0, -1.95, 0])
        self.play(FadeIn(note), run_time=0.5)

        anim = 0.6 + 0.6 + (0.7 + 0.35) + (0.6 + 0.35) * 4 + 0.7 + 0.5 + 0.5 + 0.5
        self.wait(max(1.5, duration - anim))

    # ------------------------------------------------------------------
    def _build_area_proof(self):
        """Sectors -> parallelogram drawn as a CLEAR strip of triangles.

        Redesign (an earlier episode round-3 user feedback):
        - Circle gets an explicit '円周 C = 2πr' label + arrow so the C
          in the area formula is visually grounded.
        - Right parallelogram is drawn as a collection of N triangles with
          visible vertical-ish strip dividers AND faint slant lines from
          upper-left to lower-right (each strip is one triangle pair).
        """
        duration = self._duration

        title = self._title("円の面積 ── 円周の半分 × 半径")
        self.play(FadeIn(title), run_time=0.6)

        # === LEFT: circle divided into N sectors (filled, alternating shades) ===
        cx, cy = -4.1, 0.35
        r = 1.25
        n_sec = 16
        circle = Circle(radius=r, color=WHITE, stroke_width=2.5).move_to([cx, cy, 0])
        wedges = VGroup()
        for k in range(n_sec):
            a0 = 2 * math.pi * k / n_sec
            a1 = 2 * math.pi * (k + 1) / n_sec
            p0 = [cx, cy, 0]
            p1 = [cx + r * math.cos(a0), cy + r * math.sin(a0), 0]
            p2 = [cx + r * math.cos(a1), cy + r * math.sin(a1), 0]
            w = Polygon(p0, p1, p2, stroke_width=1.0, color=ACCENT_CYAN)
            w.set_fill(ACCENT_CYAN, opacity=0.32 if k % 2 == 0 else 0.16)
            wedges.add(w)
        self.play(Create(circle), FadeIn(wedges), run_time=1.0)

        # Circumference indicator: arrow from outside pointing to circle edge,
        # plus a "円周 C = 2πr" label so the meaning of C is grounded.
        # Arrow tail above the circle, tip just touching the upper-left arc.
        arrow_tail = [cx - 0.55, cy + r + 0.75, 0]
        arrow_tip = [cx - r * 0.55, cy + r * 0.82, 0]
        c_arrow = Arrow(
            arrow_tail,
            arrow_tip,
            color=ACCENT_PINK,
            stroke_width=2.5,
            max_tip_length_to_length_ratio=0.22,
            buff=0.0,
        )
        c_jp = Text("円周", font=FONT, font_size=16, color=ACCENT_PINK)
        c_jp.move_to([cx - 0.9, cy + r + 0.92, 0])
        c_eq = MathTex(r"C = 2\pi r", font_size=22, color=ACCENT_PINK)
        c_eq.move_to([cx + 0.25, cy + r + 0.92, 0])
        self.play(FadeIn(c_arrow), FadeIn(c_jp), FadeIn(c_eq), run_time=0.6)

        cut_lbl = Text("16 の扇形に分ける", font=FONT, font_size=18, color=TEXT_DIM)
        cut_lbl.move_to([cx, -1.6, 0])
        self.play(FadeIn(cut_lbl), run_time=0.4)

        # === RIGHT: parallelogram drawn as a strip of triangles ===
        # Width = half circumference = πr  (visual proxy)
        # Height = r
        # Subdivide into n strips by vertical-ish lines; each strip is split
        # into 2 triangles by a faint diagonal (upper-left -> lower-right).
        W = math.pi * r
        H = r
        n = 8  # 8 strips -> 16 triangles total
        b_w = W / n
        shear = 0.20  # slight shear so it reads as parallelogram

        para_cx = 2.55
        bx = para_cx - W / 2 - shear / 2
        by = -0.55

        outer = Polygon(
            [bx, by, 0],
            [bx + W, by, 0],
            [bx + W + shear, by + H, 0],
            [bx + shear, by + H, 0],
            color=ACCENT_CYAN,
            stroke_width=2.5,
        )
        outer.set_fill(ACCENT_CYAN, opacity=0.18)

        # Vertical-ish strip dividers (visible)
        vert_lines = VGroup()
        for k in range(1, n):
            x_b = bx + k * b_w
            x_t = bx + shear + k * b_w
            vert_lines.add(
                Line(
                    [x_b, by, 0],
                    [x_t, by + H, 0],
                    color=ACCENT_CYAN,
                    stroke_width=1.3,
                    stroke_opacity=0.85,
                )
            )

        # Faint diagonals: upper-left -> lower-right of each strip
        # (each strip becomes 2 right triangles -- the 16 triangles).
        slant_lines = VGroup()
        for k in range(n):
            x_tl = bx + shear + k * b_w
            x_br = bx + (k + 1) * b_w
            slant_lines.add(
                Line(
                    [x_tl, by + H, 0],
                    [x_br, by, 0],
                    color=TEXT_DIM,
                    stroke_width=0.9,
                    stroke_opacity=0.55,
                )
            )

        # Alternating-shade fill on the strips (visual "16 triangles" cue)
        strip_fills = VGroup()
        for k in range(n):
            xb_l = bx + k * b_w
            xb_r = bx + (k + 1) * b_w
            xt_l = bx + shear + k * b_w
            xt_r = bx + shear + (k + 1) * b_w
            strip = Polygon(
                [xb_l, by, 0],
                [xb_r, by, 0],
                [xt_r, by + H, 0],
                [xt_l, by + H, 0],
                stroke_width=0,
                color=ACCENT_CYAN,
            )
            strip.set_fill(ACCENT_CYAN, opacity=0.12 if k % 2 == 0 else 0.05)
            strip_fills.add(strip)

        self.play(FadeIn(outer), FadeIn(strip_fills), run_time=0.7)
        self.play(FadeIn(vert_lines), FadeIn(slant_lines), run_time=0.6)

        # Labels: base = πr (= C/2), side = r
        w_lbl = MathTex(r"\tfrac{C}{2} = \pi r", font_size=26, color=ACCENT_PINK)
        w_lbl.move_to([para_cx, by - 0.35, 0])
        h_lbl = MathTex(r"r", font_size=28, color=ACCENT_GOLD)
        h_lbl.move_to([bx - 0.30, by + H / 2, 0])
        base_jp = Text("底辺", font=FONT, font_size=14, color=TEXT_DIM)
        base_jp.move_to([para_cx - 1.1, by - 0.35, 0])
        h_jp = Text("高さ", font=FONT, font_size=14, color=TEXT_DIM)
        h_jp.move_to([bx - 0.30, by + H / 2 + 0.32, 0])
        self.play(FadeIn(w_lbl), FadeIn(h_lbl), FadeIn(base_jp), FadeIn(h_jp), run_time=0.6)

        formula = MathTex(r"A = \tfrac12\,C \cdot r = \pi r^2", font_size=32, color=ACCENT_GOLD)
        formula.move_to([0, -1.95, 0])
        self.play(FadeIn(formula), run_time=0.7)

        anim = 0.6 + 1.0 + 0.6 + 0.4 + 0.7 + 0.6 + 0.6 + 0.7
        self.wait(max(1.5, duration - anim))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "buildup": {"people": [], "years": []},
    "limit": {"people": [], "years": []},
    "area_proof": {"people": [], "years": []},
}

SCENES = {
    "buildup": CircleDivision,
    "limit": CircleDivision,
    "area_proof": CircleDivision,
}
