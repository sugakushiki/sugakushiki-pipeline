"""
kepler_polyhedra.py - Kepler's Mysterium Cosmographicum (1596) for 数学史記

Visualizes the young Kepler's first cosmological model from Mysterium
Cosmographicum (Tübingen, 1596): the spacing of the six known planets is
governed by the five Platonic solids nested between six spheres. From the
inside out the solids are octahedron, icosahedron, dodecahedron,
tetrahedron, cube, separating Mercury, Venus, Earth, Mars, Jupiter and
Saturn. The model was beautiful but wrong; it shows Kepler's Pythagorean
conviction that the cosmos is built on geometric harmony.

Modes:
    five_solids        - The five regular (Platonic) solids as 2D schematic
                         icons in a row with Japanese names and face counts
                         (4, 6, 8, 12, 20).
                         Fixed params: tetra 4, cube 6, octa 8, dodeca 12,
                         icosa 20 faces.
    cosmographic_model - Sun at centre, six concentric circles (planetary
                         spheres) labelled 水星..土星, and the five solids
                         named along the +x spoke between consecutive spheres
                         in Kepler's order.
                         Fixed params: 6 spheres, radii 0.45..2.45 step 0.4.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 031 (Kepler), early-cosmology pillar.
"""

import numpy as np
from manim import (
    Circle,
    Dot,
    FadeIn,
    Scene,
    Text,
    VGroup,
    config,
)
from polyhedron_euler import (
    CUBE_V,
    DODECA_V,
    ICOSA_V,
    OCTA_V,
    TETRA_V,
    _polyhedron_wireframe,
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


_SOLID_VERTS = {
    "tetra": TETRA_V,
    "cube": CUBE_V,
    "octa": OCTA_V,
    "dodeca": DODECA_V,
    "icosa": ICOSA_V,
}


def _solid_icon(kind, size, color, stroke=2.0):
    """3D wireframe of a Platonic solid (projected, with hidden-line removal).

    Reuses polyhedron_euler's perspective projection + ConvexHull hidden-line
    removal so the solids read as recognisable 3D shapes.
    """
    verts = _SOLID_VERTS.get(kind, TETRA_V)
    return _polyhedron_wireframe(verts, [0, 0, 0], size, color, stroke=stroke)


class KeplerPolyhedra(Scene):
    """Kepler's nested Platonic-solids cosmological model (1596)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 14)
        mode = params.get("mode", "cosmographic_model")

        if mode == "five_solids":
            self._build_five_solids()
        else:
            self._build_cosmographic_model()

    # ------------------------------------------------------------------
    # Mode: five_solids
    # ------------------------------------------------------------------
    def _build_five_solids(self):
        duration = self._duration

        title = Text(
            "5つの正多面体 (プラトン立体)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.8, 0])

        solids = [
            ("tetra", "正四面体", "4面", ACCENT_CYAN),
            ("cube", "立方体", "6面", ACCENT_PINK),
            ("octa", "正八面体", "8面", ACCENT_GOLD),
            ("dodeca", "正十二面体", "12面", ACCENT_CYAN),
            ("icosa", "正二十面体", "20面", ACCENT_PINK),
        ]
        xs = [-5.0, -2.5, 0.0, 2.5, 5.0]

        icons = VGroup()
        names = VGroup()
        faces = VGroup()
        for (kind, name, face, color), x in zip(solids, xs, strict=False):
            icon = _solid_icon(kind, 0.55, color)
            icon.move_to([x, 0.7, 0])
            icons.add(icon)
            nm = Text(name, font=FONT, font_size=20, color=TEXT_WHITE)
            nm.move_to([x, -0.65, 0])
            names.add(nm)
            fc = Text(face, font=FONT, font_size=18, color=TEXT_DIM)
            fc.move_to([x, -1.2, 0])
            faces.add(fc)

        note = Text(
            "すべての面が合同な正多角形 ── 古代から知られた5種類のみ",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.85, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(icons), run_time=1.2)
        self.play(FadeIn(names), FadeIn(faces), run_time=0.9)
        self.play(FadeIn(note), run_time=0.6)

        anim_overhead = 0.7 + 1.2 + 0.9 + 0.6
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: cosmographic_model
    # ------------------------------------------------------------------
    def _build_cosmographic_model(self):
        duration = self._duration

        title = Text(
            "宇宙の神秘 ── 入れ子の多面体 (1596)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.85, 0])

        # Centre: six concentric planetary spheres around the Sun
        center = np.array([-1.7, 0.3, 0.0])
        radii = [0.40, 0.72, 1.04, 1.36, 1.68, 2.00]
        sun = Dot(center, color=ACCENT_GOLD, radius=0.1)
        circles = VGroup()
        for r in radii:
            circ = Circle(radius=r, color=ACCENT_CYAN, stroke_width=1.8)
            circ.move_to(center)
            circ.set_stroke(opacity=0.7)
            circles.add(circ)

        # Left column: the six planets (outer -> inner, top -> bottom)
        planets = ["土星", "木星", "火星", "地球", "金星", "水星"]
        planet_ys = [1.5, 0.9, 0.3, -0.3, -0.9, -1.5]
        planet_head = Text("6つの惑星", font=FONT, font_size=20, color=ACCENT_CYAN)
        planet_head.move_to([-6.0, 2.1, 0])
        planet_lbls = VGroup()
        for pname, y in zip(planets, planet_ys, strict=False):
            lbl = Text(pname, font=FONT, font_size=20, color=TEXT_WHITE)
            lbl.move_to([-6.0, y, 0])
            planet_lbls.add(lbl)

        # Right column: the five solids at the gaps between planets
        solids = [
            ("cube", "立方体", ACCENT_PINK),
            ("tetra", "正四面体", ACCENT_GOLD),
            ("dodeca", "正十二面体", ACCENT_CYAN),
            ("icosa", "正二十面体", ACCENT_PINK),
            ("octa", "正八面体", ACCENT_GOLD),
        ]
        solid_ys = [1.2, 0.6, 0.0, -0.6, -1.2]
        solid_head = Text("5つの正多面体", font=FONT, font_size=20, color=ACCENT_GOLD)
        solid_head.move_to([3.9, 2.1, 0])
        legend = VGroup()
        for (kind, name, color), y in zip(solids, solid_ys, strict=False):
            icon = _solid_icon(kind, 0.26, color)
            icon.move_to([2.7, y, 0])
            nm = Text(name, font=FONT, font_size=19, color=TEXT_WHITE)
            nm.move_to([4.4, y, 0])
            legend.add(VGroup(icon, nm))

        order_note = Text(
            "惑星球の間に正多面体を入れ子にした最初の宇宙像",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        order_note.move_to([-0.3, -2.0, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(sun), FadeIn(circles), run_time=1.1)
        self.play(FadeIn(planet_head), FadeIn(planet_lbls), run_time=0.7)
        self.play(FadeIn(solid_head), FadeIn(legend), run_time=1.0)
        self.play(FadeIn(order_note), run_time=0.6)

        anim_overhead = 0.7 + 1.1 + 0.7 + 1.0 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "five_solids": {
        "people": [],
        "years": [],
    },
    "cosmographic_model": {
        "people": [["ケプラー", "Kepler"]],
        "years": ["1596"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "five_solids": {
        "class": "KeplerPolyhedra",
        "params": {"mode": "five_solids"},
        "description": "The five Platonic solids as schematic icons with face counts 4/6/8/12/20",
    },
    "cosmographic_model": {
        "class": "KeplerPolyhedra",
        "params": {"mode": "cosmographic_model"},
        "description": "Mysterium Cosmographicum (1596): six planetary spheres nesting the five Platonic solids",
    },
}
