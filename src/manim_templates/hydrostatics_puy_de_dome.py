"""
hydrostatics_puy_de_dome.py - Pascal's hydrostatic experiments (1647-1648)

Following Torricelli's 1643 vacuum experiment, Pascal hypothesised that
atmospheric pressure should decrease with altitude. On 19 September 1648
his brother-in-law Florin Périer (husband of Pascal's elder sister
Gilberte) carried out the experiment at Clermont-Ferrand: the height of
mercury in a Torricellian barometer was measured both at the base
(courtyard of the Minim monastery, ~711 mm) and at the summit of
Puy-de-Dôme (altitude ~1465 m, mercury ~627 mm). The difference of
about 84 mm of mercury provided direct evidence that air has weight.
Pascal himself did not climb the mountain because of his chronic illness.
Pascal published the result the same year as 'Récit de la grande
expérience de l'équilibre des liqueurs' (Paris, 1648) and later
systematised it in 'Traités de l'équilibre des liqueurs et de la
pesanteur de la masse de l'air' (published posthumously 1663). The
related law of hydrostatics — pressure in a fluid is transmitted equally
in all directions and increases linearly with depth as P = ρgh — bears
his name. The SI unit of pressure (1 Pa = 1 N/m²) was officially named
'pascal' at the 14th CGPM (1971).

Modes:
    mercury_column
        Show a Torricelli mercury barometer: a vertical glass tube, sealed
        at top, inverted into a mercury reservoir. The mercury column
        rises to about 760 mm and the space above is vacuum. Label the
        vacuum at top, mercury column with height ≈ 760 mm at sea level,
        and reservoir at bottom.
        Fixed params: sea-level reference height 760 mm.

    mountain_comparison
        Side-by-side: left panel shows plain (altitude 0 m) with mercury
        column 711 mm, right panel shows Puy-de-Dôme summit (altitude
        1465 m) with mercury column 627 mm. Highlight the 84 mm
        difference and label it as 'air has weight'. Use the numbers from
        Périer's 1648 measurement (711 / 627 / Δ ≈ 84).
        Fixed params: plain 711 mm, summit 627 mm, altitude 1465 m.

    pascal_principle
        Sketch a rectangular fluid-filled container; at depth h, arrows
        emanating in four directions from a single interior point show
        that pressure acts isotropically. A small formula P = ρgh next to
        an arrow labelled 'depth h' summarises Pascal's principle. Below,
        annotate 'SI 単位 1 Pa = 1 N/m² (1971 CGPM)'.
        Fixed params: container 4.0 wide × 2.4 tall, sample point at
        depth h = 1.5.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.3, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 029 (Pascal), 遺産3 - ピュイ・ド・ドーム実験とパスカルの原理.
"""

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
    load_params,
)

config.background_color = BG_COLOR


def _build_barometer(
    center_x,
    mm_height,
    ref_mm=760,
    scale=1.6 / 760.0,
    label_mm=None,
    glass_color=TEXT_DIM,
    mercury_color=ACCENT_CYAN,
):
    """Construct a Torricelli barometer at center_x, mercury column ≈ mm_height.

    Returns a VGroup containing: reservoir rectangle, glass tube outline,
    mercury fill, vacuum label, height label.
    """
    # Geometry (scene units)
    col_height = mm_height * scale  # height of mercury column in scene units
    tube_w = 0.32
    tube_h = ref_mm * scale + 0.45  # extra space above 760 mm for vacuum
    reservoir_w = 1.10
    reservoir_h = 0.45
    base_y = -1.20  # top of reservoir base
    reservoir = Rectangle(
        width=reservoir_w,
        height=reservoir_h,
        color=glass_color,
        stroke_width=2.0,
        fill_color=mercury_color,
        fill_opacity=0.5,
    )
    reservoir.move_to([center_x, base_y - reservoir_h / 2.0, 0])

    tube = Rectangle(
        width=tube_w,
        height=tube_h,
        color=glass_color,
        stroke_width=2.0,
    )
    tube.move_to([center_x, base_y + tube_h / 2.0, 0])

    # Mercury fills tube from base_y up to base_y + col_height
    mercury = Rectangle(
        width=tube_w * 0.94,
        height=col_height,
        color=mercury_color,
        fill_color=mercury_color,
        fill_opacity=0.8,
        stroke_width=0,
    )
    mercury.move_to([center_x, base_y + col_height / 2.0, 0])

    # Vacuum label (region above mercury inside tube)
    vacuum_top_y = base_y + tube_h
    vacuum_mid_y = base_y + col_height + 0.10 + (vacuum_top_y - base_y - col_height - 0.10) / 2.0
    vacuum_lbl = Text("真空", font=FONT, font_size=14, color=ACCENT_PINK)
    vacuum_lbl.move_to([center_x + 0.50, vacuum_mid_y, 0])

    # Mercury height label
    if label_mm is None:
        label_mm = mm_height
    height_lbl = MathTex(f"{label_mm}\\,\\text{{mm}}", font_size=20, color=ACCENT_GOLD)
    height_lbl.move_to([center_x - 0.80, base_y + col_height / 2.0, 0])

    return VGroup(reservoir, tube, mercury, vacuum_lbl, height_lbl)


class HydrostaticsPuyDeDome(Scene):
    """Pascal hydrostatic experiments visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "mercury_column")
        self._duration = float(params.get("duration", 25))

        if mode == "mountain_comparison":
            self._build_mountain_comparison()
        elif mode == "pascal_principle":
            self._build_pascal_principle()
        else:
            self._build_mercury_column()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_mercury_column(self):
        duration = self._duration
        title = self._title("水銀気圧計 ── トリチェリの実験 (1643)")
        self.play(FadeIn(title), run_time=0.6)

        barometer = _build_barometer(center_x=-2.0, mm_height=760, label_mm=760)
        self.play(Create(barometer), run_time=1.4)

        # Right side: explanation (Text for Japanese, MathTex disallowed)
        explanations = VGroup(
            Text("上部: 真空", font=FONT, font_size=22, color=ACCENT_PINK),
            Text("管内水銀高: 760 mm", font=FONT, font_size=22, color=ACCENT_GOLD),
            Text("大気圧が水銀を支える", font=FONT, font_size=22, color=ACCENT_CYAN),
            Text("約 1013 hPa (海面)", font=FONT, font_size=22, color=ACCENT_CYAN),
        )
        for i, e in enumerate(explanations):
            e.move_to([2.2, 1.4 - 0.55 * i, 0])
        self.play(*[FadeIn(e) for e in explanations], run_time=1.0)

        msg = Text(
            "── 大気は本当に重さを持つのか？",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.5)

        anim_total = 0.6 + 1.4 + 1.0 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_mountain_comparison(self):
        duration = self._duration
        title = self._title("1648 年 9 月 19 日 ── ピュイ・ド・ドーム実験")
        self.play(FadeIn(title), run_time=0.6)

        # Left panel: plain (711 mm)
        plain_baro = _build_barometer(center_x=-3.0, mm_height=711, label_mm=711)
        # Right panel: summit (627 mm)
        summit_baro = _build_barometer(center_x=3.0, mm_height=627, label_mm=627)

        # Ground / mountain symbols
        # Plain: a flat line under barometer
        plain_ground = Line([-4.0, -1.65, 0], [-2.0, -1.65, 0], color=TEXT_DIM, stroke_width=2.5)
        plain_lbl = Text("平地 (標高 0 m)", font=FONT, font_size=18, color=TEXT_DIM)
        plain_lbl.move_to([-3.0, -1.92, 0])

        # Summit: a triangular mountain shape under barometer
        mountain = Polygon(
            [1.5, -1.65, 0],
            [4.5, -1.65, 0],
            [3.0, -0.3, 0],
            color=TEXT_DIM,
            fill_color=TEXT_DIM,
            fill_opacity=0.3,
            stroke_width=2.0,
        )
        summit_lbl = Text("山頂 (標高 1465 m)", font=FONT, font_size=18, color=TEXT_DIM)
        summit_lbl.move_to([3.0, -1.92, 0])

        self.play(
            FadeIn(plain_ground),
            FadeIn(plain_lbl),
            Create(plain_baro),
            run_time=1.2,
        )
        self.play(
            Create(mountain),
            FadeIn(summit_lbl),
            Create(summit_baro),
            run_time=1.2,
        )

        # Difference label between them
        diff_lbl = MathTex(
            r"\Delta = 711 - 627 = 84\,\text{mm}",
            font_size=26,
            color=ACCENT_PINK,
        )
        diff_lbl.move_to([0, 1.20, 0])
        conclusion = Text(
            "── 大気には、重さがある",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        conclusion.move_to([0, 0.55, 0])
        self.play(FadeIn(diff_lbl), run_time=0.7)
        self.play(FadeIn(conclusion), run_time=0.6)

        anim_total = 0.6 + 1.2 + 1.2 + 0.7 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_pascal_principle(self):
        duration = self._duration
        title = self._title("パスカルの原理 ── 圧力は等方的に伝わる")
        self.play(FadeIn(title), run_time=0.6)

        # Container of fluid
        cont_w = 4.0
        cont_h = 2.4
        container = Rectangle(
            width=cont_w,
            height=cont_h,
            color=TEXT_DIM,
            stroke_width=2.5,
            fill_color=ACCENT_CYAN,
            fill_opacity=0.25,
        )
        container.move_to([-1.5, 0.0, 0])
        self.play(Create(container), run_time=0.9)

        # Sample point at depth h = 1.5 from top (which is at y = 1.2)
        # → y = 1.2 - 1.5 = -0.3
        sample_y = 1.2 - 1.5
        sample_pt = [-1.5, sample_y, 0]
        from manim import Dot

        dot = Dot(sample_pt, color=ACCENT_PINK, radius=0.10)
        self.play(FadeIn(dot), run_time=0.4)

        # Four arrows emanating in 4 directions (up, down, left, right)
        arr_len = 0.6
        arrs = VGroup(
            Arrow(
                sample_pt,
                [sample_pt[0], sample_pt[1] + arr_len, 0],
                color=ACCENT_GOLD,
                buff=0.10,
                stroke_width=2.4,
                max_tip_length_to_length_ratio=0.30,
            ),
            Arrow(
                sample_pt,
                [sample_pt[0], sample_pt[1] - arr_len, 0],
                color=ACCENT_GOLD,
                buff=0.10,
                stroke_width=2.4,
                max_tip_length_to_length_ratio=0.30,
            ),
            Arrow(
                sample_pt,
                [sample_pt[0] + arr_len, sample_pt[1], 0],
                color=ACCENT_GOLD,
                buff=0.10,
                stroke_width=2.4,
                max_tip_length_to_length_ratio=0.30,
            ),
            Arrow(
                sample_pt,
                [sample_pt[0] - arr_len, sample_pt[1], 0],
                color=ACCENT_GOLD,
                buff=0.10,
                stroke_width=2.4,
                max_tip_length_to_length_ratio=0.30,
            ),
        )
        self.play(*[Create(a) for a in arrs], run_time=0.9)

        # Depth label and formula on the right
        depth_lbl = MathTex(r"\text{depth } h", font_size=22, color=ACCENT_CYAN)
        depth_lbl.move_to([0.6, sample_y + 0.35, 0])
        formula = MathTex(r"P = \rho g h", font_size=32, color=ACCENT_GOLD)
        formula.move_to([2.6, 1.0, 0])
        si_unit = MathTex(
            r"1\,\text{Pa} = 1\,\text{N/m}^2\;(1971\;\text{CGPM})",
            font_size=20,
            color=ACCENT_PINK,
        )
        si_unit.move_to([2.6, 0.0, 0])
        self.play(FadeIn(depth_lbl), FadeIn(formula), FadeIn(si_unit), run_time=0.9)

        msg = Text(
            "深さに比例して圧力が増し、四方八方に等しく伝わる",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.9 + 0.4 + 0.9 + 0.9 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "mercury_column": {"people": [], "years": []},
    "mountain_comparison": {"people": [], "years": []},
    "pascal_principle": {"people": [], "years": []},
}

SCENES = {
    "mercury_column": HydrostaticsPuyDeDome,
    "mountain_comparison": HydrostaticsPuyDeDome,
    "pascal_principle": HydrostaticsPuyDeDome,
}
