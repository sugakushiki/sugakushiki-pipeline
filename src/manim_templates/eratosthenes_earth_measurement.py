"""
eratosthenes_earth_measurement.py - Eratosthenes' measurement of the Earth's circumference

Eratosthenes of Cyrene (c. 276 - c. 194 BC), third head of the Library of
Alexandria, computed the Earth's circumference around 240 BC by comparing the
noon shadow at the summer solstice between Syene (modern Aswan) and Alexandria.
At Syene the sun was directly overhead (light reached the bottom of a well),
while at the same hour in Alexandria a vertical gnomon cast a shadow whose
angle was 7°12' (= 7.2°) = 1/50 of a full circle. With the distance between
the two cities given as 5,000 stadia (measured by professional bematists), and
the sun treated as effectively at infinity (parallel rays), similarity of
triangles gives the full circumference as 50 × 5,000 = 250,000 stadia. Using
the scholarly standard stadion of 157.5 m this is ~39,375 km, about 1.4% off
the modern polar circumference (39,941 km) or ~1.7% off the equatorial value
(40,075 km).

Layout note:
- Title at y = +3.0 must not collide with diagram elements below it.
- Sun disc kept compact and centered horizontally; sun text label removed.
- For earth_arc, the central computation formula is in a separate
  formula_display scene (math_05); this template focuses on the geometry.
- 7°12' is labelled with "(= 7.2°)" so the relation 7.2 × 50 = 360 is
  immediately readable (avoids parsing "7°12'" as decimal "7.12").

Modes:
    syene_well         - Sun directly overhead at Syene at noon on the summer
                         solstice; light reaches the bottom of a well; a vertical
                         gnomon next to it casts no shadow.
                         Fixed params: sun_y = 2.0, well_x = -2.0, gnomon_x = 1.5.
    alexandria_shadow  - At the same hour in Alexandria, a vertical gnomon casts
                         a short shadow; the right triangle highlights the angle
                         7°12' = 7.2° = 1/50 * 360°.
                         Fixed params: visual_angle_deg = 25 (exaggerated), gnomon
                         at origin.
    earth_arc          - Earth as a circle, two cities on the surface, parallel
                         sun rays from above, central angle 7°12' at the center,
                         arc length 5000 stadia, total circumference = 50 * 5000 =
                         250,000 stadia.
                         Fixed params: R_display = 1.5, visual_angle_deg = 50
                         (exaggerated for readability; label says 7°12' = 7.2°).

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 027 (Eratosthenes), pillar A — Earth circumference measurement.
"""

import math

from manim import (
    Arc,
    Arrow,
    Circle,
    Create,
    DashedLine,
    Dot,
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


class EratosthenesEarthMeasurement(Scene):
    """Earth circumference measurement by Eratosthenes — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "earth_arc")
        self._duration = params.get("duration", 30)

        if mode == "syene_well":
            self._build_syene_well()
        elif mode == "alexandria_shadow":
            self._build_alexandria_shadow()
        else:
            self._build_earth_arc()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _sun_disc(self, x, y, radius=0.30):
        sun = Circle(radius=radius, color=ACCENT_GOLD, fill_opacity=0.9, stroke_width=0)
        sun.move_to([x, y, 0])
        return sun

    # ------------------------------------------------------------------
    def _build_syene_well(self):
        duration = float(self._duration)
        title = self._title("シエネ ── 夏至正午、太陽が真上")
        self.play(FadeIn(title), run_time=0.6)

        ground_y = -0.8
        ground = Line([-5.5, ground_y, 0], [5.5, ground_y, 0],
                      color=TEXT_DIM, stroke_width=2.0)
        self.play(Create(ground), run_time=0.4)

        # Sun centered, smaller, lower
        sun = self._sun_disc(0, 2.0, 0.30)
        self.play(FadeIn(sun), run_time=0.4)

        # Parallel rays straight down (between title and ground)
        rays = VGroup()
        for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
            rays.add(Line([x, 1.6, 0], [x, ground_y, 0],
                          color=ACCENT_GOLD, stroke_width=1.6, stroke_opacity=0.55))
        self.play(FadeIn(rays), run_time=0.5)

        # Well: a vertical slot with a lit bottom
        well_x = -2.0
        well_top_y = ground_y
        well_depth = 0.85
        well_bottom_y = ground_y - well_depth
        well_left = well_x - 0.30
        well_right = well_x + 0.30
        well_walls = VGroup(
            Line([well_left, well_top_y, 0], [well_left, well_bottom_y, 0],
                 color=TEXT_DIM, stroke_width=2.0),
            Line([well_right, well_top_y, 0], [well_right, well_bottom_y, 0],
                 color=TEXT_DIM, stroke_width=2.0),
            Line([well_left, well_bottom_y, 0], [well_right, well_bottom_y, 0],
                 color=ACCENT_PINK, stroke_width=3.0),
        )
        # Light into the well — direct ray reaching bottom
        well_ray = Line([well_x, 1.6, 0], [well_x, well_bottom_y, 0],
                        color=ACCENT_GOLD, stroke_width=2.4, stroke_opacity=0.95)
        well_label = Text("井戸の底まで光が届く", font=FONT, font_size=18, color=ACCENT_PINK)
        well_label.move_to([-2.0, -1.95, 0])
        self.play(Create(well_walls), FadeIn(well_ray), run_time=0.6)
        self.play(FadeIn(well_label), run_time=0.4)

        # Gnomon: vertical stick with NO shadow
        gnomon_x = 1.5
        gnomon_top_y = ground_y + 0.9
        gnomon = Line([gnomon_x, ground_y, 0], [gnomon_x, gnomon_top_y, 0],
                      color=ACCENT_CYAN, stroke_width=4.0)
        gnomon_label = Text("グノモン（垂直の棒）", font=FONT, font_size=15, color=ACCENT_CYAN)
        gnomon_label.move_to([3.4, gnomon_top_y - 0.05, 0])
        no_shadow_label = Text("影なし", font=FONT, font_size=18, color=ACCENT_PINK)
        no_shadow_label.move_to([1.5, -1.95, 0])
        self.play(Create(gnomon), FadeIn(gnomon_label), run_time=0.5)
        self.play(FadeIn(no_shadow_label), run_time=0.4)

        anim_total = 0.6 + 0.4 + 0.4 + 0.5 + 0.6 + 0.4 + 0.5 + 0.4
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_alexandria_shadow(self):
        duration = float(self._duration)
        title = self._title("アレクサンドリア ── 同時刻、七度十二分の影")
        self.play(FadeIn(title), run_time=0.6)

        ground_y = -0.8
        ground = Line([-5.5, ground_y, 0], [5.5, ground_y, 0],
                      color=TEXT_DIM, stroke_width=2.0)
        self.play(Create(ground), run_time=0.4)

        # Sun off-vertical by visual angle (exaggerated for visibility, ~25 deg)
        visual_angle_deg = 25.0
        sun_x = 1.6
        sun_y = 2.0
        sun = self._sun_disc(sun_x, sun_y, 0.30)
        self.play(FadeIn(sun), run_time=0.4)

        # Vertical gnomon at x = 0
        gnomon_x = 0.0
        gnomon_top_y = ground_y + 1.5
        gnomon = Line([gnomon_x, ground_y, 0], [gnomon_x, gnomon_top_y, 0],
                      color=ACCENT_CYAN, stroke_width=4.0)
        gnomon_label = Text("グノモン", font=FONT, font_size=15, color=ACCENT_CYAN)
        gnomon_label.move_to([-1.10, gnomon_top_y - 0.05, 0])
        self.play(Create(gnomon), FadeIn(gnomon_label), run_time=0.5)

        # Sun ray hitting top of gnomon — drawn at the visual angle from vertical
        a_rad = math.radians(visual_angle_deg)
        ray_start_x = gnomon_x + 1.6 * math.sin(a_rad)
        ray_start_y = gnomon_top_y + 1.6 * math.cos(a_rad)
        ray = Line([ray_start_x, ray_start_y, 0],
                   [gnomon_x, gnomon_top_y, 0],
                   color=ACCENT_GOLD, stroke_width=2.4)
        # Extension to ground at shadow tip
        shadow_len = gnomon_top_y - ground_y  # vertical drop
        shadow_dx = shadow_len * math.tan(a_rad)
        shadow_tip_x = gnomon_x - shadow_dx
        ray_ext = DashedLine([gnomon_x, gnomon_top_y, 0],
                             [shadow_tip_x, ground_y, 0],
                             color=ACCENT_GOLD, stroke_width=1.4,
                             dash_length=0.10, stroke_opacity=0.6)
        self.play(Create(ray), Create(ray_ext), run_time=0.6)

        # Shadow on the ground
        shadow = Line([gnomon_x, ground_y, 0], [shadow_tip_x, ground_y, 0],
                      color=ACCENT_PINK, stroke_width=4.0)
        shadow_label = Text("影", font=FONT, font_size=18, color=ACCENT_PINK)
        shadow_label.move_to([(gnomon_x + shadow_tip_x) / 2, ground_y - 0.30, 0])
        self.play(Create(shadow), FadeIn(shadow_label), run_time=0.4)

        # Angle arc at top of gnomon between vertical and ray
        angle_arc = Arc(
            radius=0.45, start_angle=math.pi / 2,
            angle=-a_rad,
            color=ACCENT_PINK, stroke_width=2.6,
        )
        angle_arc.move_arc_center_to([gnomon_x, gnomon_top_y, 0])

        # Angle label inside wedge
        angle_label = MathTex(r"7^\circ 12'", font_size=28, color=ACCENT_PINK)
        label_offset = 0.70
        angle_label.move_to([
            gnomon_x + label_offset * math.sin(a_rad / 2),
            gnomon_top_y - label_offset * math.cos(a_rad / 2) + 0.10,
            0,
        ])
        self.play(Create(angle_arc), FadeIn(angle_label), run_time=0.6)

        # Formula bar at bottom — keep at y = -1.95 (above subtitle clearance)
        formula = MathTex(
            r"7^\circ 12' = 7.2^\circ = \tfrac{1}{50}\times 360^\circ",
            font_size=30, color=ACCENT_GOLD,
        )
        formula.move_to([0, -1.95, 0])
        self.play(FadeIn(formula), run_time=0.6)

        anim_total = 0.6 + 0.4 + 0.4 + 0.5 + 0.6 + 0.4 + 0.6 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_earth_arc(self):
        duration = float(self._duration)
        title = self._title("地球と弧 ── 五千スタディアの五十倍")
        self.play(FadeIn(title), run_time=0.6)

        # Earth circle — placed slightly above center so labels fit underneath
        center = [0.0, 0.10, 0]
        R = 1.45
        earth = Circle(radius=R, color=ACCENT_CYAN, stroke_width=2.6)
        earth.move_to(center)
        center_dot = Dot(center, color=TEXT_DIM, radius=0.05)

        # Visual angle exaggerated for clarity (50°); label is 7°12'
        visual_angle_deg = 50.0
        theta_alex = math.radians(90 + visual_angle_deg / 2)
        theta_syene = math.radians(90 - visual_angle_deg / 2)
        alex_pt = [center[0] + R * math.cos(theta_alex),
                   center[1] + R * math.sin(theta_alex), 0]
        syene_pt = [center[0] + R * math.cos(theta_syene),
                    center[1] + R * math.sin(theta_syene), 0]

        # Two radii to the cities (from center to surface)
        radius_alex = Line(center, alex_pt, color=ACCENT_GOLD, stroke_width=2.0)
        radius_syene = Line(center, syene_pt, color=ACCENT_GOLD, stroke_width=2.0)

        # Arc on top between the two cities (north of center)
        arc_between = Arc(
            radius=R, start_angle=theta_syene,
            angle=theta_alex - theta_syene,
            color=ACCENT_PINK, stroke_width=4.5,
        )
        arc_between.move_arc_center_to(center)

        self.play(Create(earth), FadeIn(center_dot), run_time=0.7)
        self.play(Create(radius_alex), Create(radius_syene), run_time=0.5)
        self.play(Create(arc_between), run_time=0.5)

        # City labels above the arc, separated and out of the diagram
        alex_dot = Dot(alex_pt, color=ACCENT_GOLD, radius=0.07)
        syene_dot = Dot(syene_pt, color=ACCENT_GOLD, radius=0.07)
        alex_label = Text("アレクサンドリア", font=FONT, font_size=15, color=ACCENT_GOLD)
        alex_label.move_to([alex_pt[0] - 0.40, alex_pt[1] + 0.35, 0])
        syene_label = Text("シエネ", font=FONT, font_size=15, color=ACCENT_GOLD)
        syene_label.move_to([syene_pt[0] + 0.40, syene_pt[1] + 0.35, 0])
        self.play(FadeIn(alex_dot), FadeIn(syene_dot),
                  FadeIn(alex_label), FadeIn(syene_label), run_time=0.6)

        # Parallel sun rays from top (between title and arc)
        rays = VGroup()
        for x in (-2.4, -1.2, 0.0, 1.2, 2.4):
            rays.add(Line([x, 2.55, 0], [x, 2.05, 0],
                          color=ACCENT_GOLD, stroke_width=1.6, stroke_opacity=0.55))
        self.play(FadeIn(rays), run_time=0.5)

        # Central angle label and arc near center (below the city dots)
        ctr_arc = Arc(
            radius=0.45, start_angle=theta_syene,
            angle=theta_alex - theta_syene,
            color=ACCENT_PINK, stroke_width=2.4,
        )
        ctr_arc.move_arc_center_to(center)
        ctr_lbl = MathTex(r"7^\circ 12'", font_size=22, color=ACCENT_PINK)
        ctr_lbl.move_to([center[0] + 0.95, center[1] + 0.35, 0])
        ctr_lbl_decimal = MathTex(r"(= 7.2^\circ)", font_size=18, color=ACCENT_PINK)
        ctr_lbl_decimal.move_to([center[0] + 0.95, center[1] + 0.08, 0])
        self.play(Create(ctr_arc), FadeIn(ctr_lbl), FadeIn(ctr_lbl_decimal), run_time=0.5)

        # Arc-length label — to the LEFT of the diagram, well above subtitle
        # (Japanese label split from MathTex to satisfy CLAUDE.md MathTex rule)
        arc_lbl_jp = Text("弧長", font=FONT, font_size=18, color=ACCENT_PINK)
        arc_lbl_jp.move_to([-3.50, 2.40, 0])
        arc_lbl_math = MathTex(r"\approx 5{,}000 \;\text{stadia}",
                               font_size=22, color=ACCENT_PINK)
        arc_lbl_math.move_to([-2.55, 2.40, 0])
        self.play(FadeIn(arc_lbl_jp), FadeIn(arc_lbl_math), run_time=0.4)

        # The key relation — to the RIGHT of the diagram
        formula = MathTex(
            r"\tfrac{7.2^\circ}{360^\circ} = \tfrac{1}{50}",
            font_size=24, color=ACCENT_GOLD,
        )
        formula.move_to([2.95, 2.40, 0])
        self.play(FadeIn(formula), run_time=0.5)

        # Footer: total circumference
        total = MathTex(
            r"C = 50 \times 5{,}000 = 250{,}000 \;\text{stadia}",
            font_size=26, color=ACCENT_GOLD,
        )
        total.move_to([0, -1.85, 0])
        self.play(FadeIn(total), run_time=0.6)

        anim_total = 0.6 + 0.7 + 0.5 + 0.5 + 0.6 + 0.5 + 0.5 + 0.4 + 0.5 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "syene_well": {"people": [], "years": []},
    "alexandria_shadow": {"people": [], "years": []},
    "earth_arc": {"people": [], "years": []},
}

SCENES = {
    "syene_well": EratosthenesEarthMeasurement,
    "alexandria_shadow": EratosthenesEarthMeasurement,
    "earth_arc": EratosthenesEarthMeasurement,
}
