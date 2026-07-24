"""
sea_island_survey.py - Liu Hui's Sea Island Manual (海島算経) double-difference

Visualizes the first problem of the Haidao Suanjing (Sea Island Mathematical
Manual, 263, originally an appendix to Liu Hui's commentary): the height and
distance of an unreachable sea island found by two equal poles a known
distance apart and two backward sightings — the double-difference (重差)
method, based on similar right triangles (a proto-survey, NOT trigonometry).

Modes:
    setup            - The scene: sea, island on the right, two equal vertical
                       poles on a baseline, an observer stepping back behind
                       each pole until the island summit lines up with the
                       pole tip. Labels: 表 (pole), 島 (island), 却行 (offset).
                       Fixed params: two poles, equal height, schematic.
    double_difference - The two similar right triangles extracted, with the
                       formulas
                         island height = pole_h * span / (s2 - s1) + pole_h
                         distance      = s1 * span / (s2 - s1)
                       and the original numbers: pole 3 zhang, span 1000 bu,
                       answer island 4 li 55 bu, distance 102 li 150 bu.
                       Fixed params: those exact numbers.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 026 (Liu Hui), pillar C — measuring the unreachable.
"""

from manim import (
    DOWN,
    LEFT,
    Create,
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


class SeaIslandSurvey(Scene):
    """Liu Hui's 海島算経 double-difference survey — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "setup")
        self._duration = params.get("duration", 28)

        if mode == "double_difference":
            self._build_double_difference()
        else:
            self._build_setup()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_setup(self):
        """The sea-island sighting layout with two equal poles."""
        duration = self._duration

        title = self._title("海島算経 ── 近づけない島を測る")
        self.play(FadeIn(title), run_time=0.6)

        # Geometry built so each line of sight is COLINEAR through
        # eye(ground) -> pole tip -> island summit (the essence of 重差術).
        ground_y = -0.6
        h = 1.0  # equal pole height (表高)
        ground = Line([-6.0, ground_y, 0], [6.0, ground_y, 0], color=TEXT_DIM, stroke_width=2)
        self.play(Create(ground), run_time=0.5)

        # Island (mountain shape) on the right
        isl_x, isl_h = 4.6, 2.0
        sx, sy = isl_x, ground_y + isl_h  # summit
        island = Polygon(
            [isl_x - 0.9, ground_y, 0],
            [isl_x + 0.9, ground_y, 0],
            [sx, sy, 0],
            color=ACCENT_PINK,
            stroke_width=2.5,
        )
        isl_lbl = Text("島", font=FONT, font_size=24, color=ACCENT_PINK)
        isl_lbl.move_to([isl_x, sy + 0.3, 0])
        self.play(Create(island), FadeIn(isl_lbl), run_time=0.7)

        # Two equal-height poles: 前表 (near island) and 後表 (far)
        p1x, p2x = 2.0, 0.4  # 前表, 後表
        tip_y = ground_y + h
        # eye x so that line (pole tip -> summit) meets ground:
        #   ex = px - (sx - px) * h / (sy - ground_y - h)
        denom = sy - ground_y - h
        e1x = p1x - (sx - p1x) * h / denom
        e2x = p2x - (sx - p2x) * h / denom

        pole1 = Line([p1x, ground_y, 0], [p1x, tip_y, 0], color=ACCENT_CYAN, stroke_width=4)
        pole2 = Line([p2x, ground_y, 0], [p2x, tip_y, 0], color=ACCENT_CYAN, stroke_width=4)
        pl1 = Text("前表", font=FONT, font_size=18, color=ACCENT_CYAN)
        pl1.move_to([p1x + 0.05, tip_y + 0.25, 0])
        pl2 = Text("後表", font=FONT, font_size=18, color=ACCENT_CYAN)
        pl2.move_to([p2x - 0.05, tip_y + 0.25, 0])
        self.play(Create(pole1), Create(pole2), FadeIn(pl1), FadeIn(pl2), run_time=0.8)

        # Sight lines: eye(ground) -> (through pole tip) -> summit, colinear
        sight1 = DashedLine([e1x, ground_y, 0], [sx, sy, 0], color=TEXT_WHITE, stroke_width=1.5)
        sight2 = DashedLine([e2x, ground_y, 0], [sx, sy, 0], color=TEXT_WHITE, stroke_width=1.5)
        eye1 = Text("目", font=FONT, font_size=16, color=TEXT_DIM)
        eye1.move_to([e1x, ground_y - 0.28, 0])
        eye2 = Text("目", font=FONT, font_size=16, color=TEXT_DIM)
        eye2.move_to([e2x, ground_y - 0.28, 0])
        self.play(Create(sight1), Create(sight2), FadeIn(eye1), FadeIn(eye2), run_time=0.9)

        # Offsets (却行 = eye -> pole) brackets along the ground
        off1 = Line(
            [e1x, ground_y - 0.4, 0], [p1x, ground_y - 0.4, 0], color=ACCENT_GOLD, stroke_width=3
        )
        off2 = Line(
            [e2x, ground_y - 0.7, 0], [p2x, ground_y - 0.7, 0], color=ACCENT_PINK, stroke_width=3
        )
        offl = Text("却行 ＝ 目から表までの後退距離", font=FONT, font_size=18, color=ACCENT_GOLD)
        offl.move_to([0.2, ground_y - 1.0, 0])
        self.play(Create(off1), Create(off2), FadeIn(offl), run_time=0.7)

        note = Text(
            "二度の観測の差から島の高さと距離を求める", font=FONT, font_size=20, color=TEXT_WHITE
        )
        note.move_to([0, -2.0, 0])
        self.play(FadeIn(note), run_time=0.6)

        anim_total = 0.6 + 0.5 + 0.7 + 0.8 + 0.9 + 0.7 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_double_difference(self):
        """重差術 — full two-pole geometry with EVERY variable labelled.

        Redesign: the previous figure showed
        only one similar-triangle pair (eye_1 / pole_1 / summit) and the
        formula contained an undefined 'd' that did not appear on the
        figure. Variable conventions also drifted between modes (a vs h,
        b_1/b_2 vs s_1/s_2). Now we draw the COMPLETE classical setup --
        two eyes, two poles, two sight lines converging at the summit --
        with ALL of {h, d, s_1, s_2, L, H} explicitly labelled on the
        figure, plus a small Japanese key tying each symbol to the
        narration term (表高 / 表間 / 却行 / 距離 / 島高).
        """
        duration = self._duration

        title = self._title("重差術 ── 二本の表で島高と距離を出す")
        self.play(FadeIn(title), run_time=0.6)

        cap = Text(
            "表 (ポール) 2 本・目 2 つの照準線が島頂に収束 ── すべての記号を図上で定義",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        cap.move_to([0, 2.45, 0])
        self.play(FadeIn(cap), run_time=0.4)

        # === Geometric parameters (chosen so the figure stays on screen
        # AND satisfies the colinear-sight-line constraint exactly) ===
        s1, s2, d = 1.20, 1.50, 0.60  # display-unit lengths
        h_pole = 0.62  # display pole height
        # L follows from the geometry: L = s_1 d / (s_2 - s_1)
        L_val = s1 * d / (s2 - s1)  # = 2.40
        # And H from similarity: H = h (L + s_1) / s_1
        H_val = h_pole * (L_val + s1) / s1  # = 3 * h_pole = 1.86

        # Anchor 前表 at x=0 in local coords, then shift so the figure sits
        # in the LEFT half of the canvas and the formula panel fits on the
        # right.
        x_shift = -2.55
        x_p1 = 0.0 + x_shift  # 前表 foot
        x_p2 = -d + x_shift  # 後表 foot
        x_e1 = -s1 + x_shift  # 目_1 (front sighting)
        x_e2 = -d - s2 + x_shift  # 目_2 (back sighting)
        x_sf = L_val + x_shift  # summit foot
        gy = -0.55  # ground y (raised so brackets fit)

        # Ground line spanning the whole figure
        ground = Line([x_e2 - 0.35, gy, 0], [x_sf + 0.35, gy, 0], color=TEXT_DIM, stroke_width=2)
        self.play(Create(ground), run_time=0.35)

        # Island (mountain on the right)
        summit = [x_sf, gy + H_val, 0]
        island = Polygon(
            [x_sf - 0.40, gy, 0],
            [x_sf + 0.40, gy, 0],
            summit,
            color=ACCENT_PINK,
            stroke_width=2.2,
        )
        isl_lbl = Text("島頂", font=FONT, font_size=14, color=ACCENT_PINK)
        isl_lbl.move_to([x_sf, gy + H_val + 0.22, 0])
        self.play(FadeIn(island), FadeIn(isl_lbl), run_time=0.45)

        # Two equal-height poles
        p1 = Line([x_p1, gy, 0], [x_p1, gy + h_pole, 0], color=ACCENT_CYAN, stroke_width=3)
        p2 = Line([x_p2, gy, 0], [x_p2, gy + h_pole, 0], color=ACCENT_CYAN, stroke_width=3)
        p1_lbl = Text("前表", font=FONT, font_size=13, color=ACCENT_CYAN)
        p1_lbl.move_to([x_p1 + 0.22, gy + h_pole + 0.16, 0])
        p2_lbl = Text("後表", font=FONT, font_size=13, color=ACCENT_CYAN)
        p2_lbl.move_to([x_p2 - 0.22, gy + h_pole + 0.16, 0])
        self.play(Create(p1), Create(p2), FadeIn(p1_lbl), FadeIn(p2_lbl), run_time=0.55)

        # h label (pole height) between the two pole tips (centered)
        h_fig = MathTex(r"h", font_size=22, color=ACCENT_CYAN)
        h_fig.move_to([x_p1 + 0.22, gy + h_pole / 2, 0])

        # H label (island height)
        H_fig = MathTex(r"H", font_size=26, color=ACCENT_PINK)
        H_fig.move_to([x_sf + 0.30, gy + H_val / 2, 0])
        self.play(FadeIn(h_fig), FadeIn(H_fig), run_time=0.4)

        # Two sight lines from each eye through the matching pole tip to the
        # summit (the construction MUST be colinear by our parameter choice).
        sight1 = DashedLine([x_e1, gy, 0], summit, color=TEXT_WHITE, stroke_width=1.4)
        sight2 = DashedLine([x_e2, gy, 0], summit, color=TEXT_WHITE, stroke_width=1.4)
        eye1 = Text("目 1", font=FONT, font_size=13, color=TEXT_DIM)
        eye1.move_to([x_e1, gy - 0.22, 0])
        eye2 = Text("目 2", font=FONT, font_size=13, color=TEXT_DIM)
        eye2.move_to([x_e2, gy - 0.22, 0])
        self.play(Create(sight1), Create(sight2), FadeIn(eye1), FadeIn(eye2), run_time=0.7)

        # === Distance brackets below the ground (two rows to avoid overlap) ===
        # Row 1 (closer to ground): s_2 and d (they are adjacent, no overlap).
        row1_y = gy - 0.50
        s2_br = Line([x_e2, row1_y, 0], [x_p2, row1_y, 0], color=ACCENT_PINK, stroke_width=2.2)
        s2_lbl = MathTex(r"s_2", font_size=20, color=ACCENT_PINK)
        s2_lbl.move_to([(x_e2 + x_p2) / 2, row1_y - 0.22, 0])

        d_br = Line([x_p2, row1_y, 0], [x_p1, row1_y, 0], color=ACCENT_GOLD, stroke_width=2.2)
        d_lbl = MathTex(r"d", font_size=22, color=ACCENT_GOLD)
        d_lbl.move_to([(x_p2 + x_p1) / 2, row1_y - 0.22, 0])

        # Row 2 (further from ground): s_1 and L (overlap with row 1 horizontally).
        row2_y = gy - 0.95
        s1_br = Line([x_e1, row2_y, 0], [x_p1, row2_y, 0], color=ACCENT_CYAN, stroke_width=2.2)
        s1_lbl = MathTex(r"s_1", font_size=20, color=ACCENT_CYAN)
        s1_lbl.move_to([(x_e1 + x_p1) / 2, row2_y - 0.22, 0])

        L_br = Line([x_p1, row2_y, 0], [x_sf, row2_y, 0], color=ACCENT_GOLD, stroke_width=2.2)
        L_lbl = MathTex(r"L", font_size=22, color=ACCENT_GOLD)
        L_lbl.move_to([(x_p1 + x_sf) / 2, row2_y - 0.22, 0])

        self.play(FadeIn(s2_br), FadeIn(s2_lbl), FadeIn(d_br), FadeIn(d_lbl), run_time=0.5)
        self.play(FadeIn(s1_br), FadeIn(s1_lbl), FadeIn(L_br), FadeIn(L_lbl), run_time=0.5)

        # === RIGHT panel: Japanese key + similarity + formulas ===
        panel_x = 4.55

        # Variable key tying the symbols to narration vocabulary.
        def _def_row(var_tex, jp_desc, color):
            v = MathTex(var_tex, font_size=20, color=color)
            eq = Text("：", font=FONT, font_size=14, color=TEXT_DIM)
            d_ = Text(jp_desc, font=FONT, font_size=13, color=TEXT_DIM)
            return VGroup(v, eq, d_).arrange(buff=0.06)

        defs = VGroup(
            _def_row(r"h", "表 (ポール) の高さ", ACCENT_CYAN),
            _def_row(r"d", "表の間隔", ACCENT_GOLD),
            _def_row(r"s_1", "前表の却行", ACCENT_CYAN),
            _def_row(r"s_2", "後表の却行", ACCENT_PINK),
            _def_row(r"L", "前表から島までの距離", ACCENT_GOLD),
            _def_row(r"H", "島の高さ", ACCENT_PINK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.09)
        defs.move_to([panel_x, 1.10, 0])
        self.play(FadeIn(defs), run_time=0.6)

        # Similarity statement + the master ratio (both similar pairs).
        ratio = MathTex(
            r"\dfrac{H}{h} \;=\; \dfrac{L+s_1}{s_1} \;=\; \dfrac{L+d+s_2}{s_2}",
            font_size=20,
            color=ACCENT_CYAN,
        )
        ratio.move_to([panel_x, -0.55, 0])

        # Solving for H and L (the double-difference formulas).
        fH = MathTex(r"H = \dfrac{h\,d}{s_2 - s_1} + h", font_size=22, color=ACCENT_GOLD)
        fH.move_to([panel_x, -1.15, 0])
        fL = MathTex(r"L = \dfrac{s_1\,d}{s_2 - s_1}", font_size=22, color=ACCENT_CYAN)
        fL.move_to([panel_x, -1.65, 0])
        self.play(FadeIn(ratio), run_time=0.5)
        self.play(FadeIn(fH), FadeIn(fL), run_time=0.6)

        # Bottom strip: original problem & answer
        ans = Text(
            "原問: 表高 3丈・表間 1000歩  →  島高 4里55歩・距離 102里150歩",
            font=FONT,
            font_size=18,
            color=ACCENT_GOLD,
        )
        ans.move_to([0, -1.95, 0])
        self.play(FadeIn(ans), run_time=0.6)

        anim_total = 0.6 + 0.4 + 0.35 + 0.45 + 0.55 + 0.4 + 0.7 + 0.5 + 0.5 + 0.6 + 0.5 + 0.6 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "setup": {"people": [], "years": []},
    "double_difference": {"people": [], "years": []},
}

SCENES = {
    "setup": SeaIslandSurvey,
    "double_difference": SeaIslandSurvey,
}
