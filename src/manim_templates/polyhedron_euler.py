"""
polyhedron_euler.py - Euler's polyhedron formula V − E + F = 2 for 数学史記

Visualizes Euler's 1750 discovery (letter to Goldbach, Nov 14):
for every convex polyhedron the vertex, edge and face counts satisfy
    V − E + F = 2.
This is the first example of the Euler characteristic χ, the seed of
topology.

Historical note: Descartes c.1630 had an equivalent result in the
manuscript De solidorum elementis, unpublished until 1860. Euler
rediscovered it independently and proved / popularised it.

Modes:
    solids       - Five Platonic solids as 2D icons; table of
                   V, E, F, V−E+F = 2 for all five.
                   Fixed params: tetrahedron, cube, octahedron,
                   dodecahedron, icosahedron.
    non_regular  - Two non-Platonic convex polyhedra (triangular
                   prism, truncated cube) with their counts: the
                   identity still holds.
                   Fixed params: prism V=6 E=9 F=5, truncated cube
                   V=24 E=36 F=14.
    formula      - Central display of V − E + F = 2, dated quote
                   from the 1750 letter, and a closing note naming
                   the Euler characteristic.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 019 (Euler applied), math pillar 1b.
"""

import math

import numpy as np
from manim import (
    FadeIn,
    Line,
    MathTex,
    Scene,
    SurroundingRectangle,
    Text,
    VGroup,
    config,
)
from scipy.spatial import ConvexHull
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


# ---------------------------------------------------------------------------
# Polyhedron icon helpers: 3D wireframe projected to 2D
#
# Each polyhedron is defined by a list of 3D vertex coordinates; edges are
# auto-detected by nearest-neighbour distance. A single 3/4 perspective
# projection (rotate around z then tilt around x) is used throughout, so
# all shapes share a consistent viewing angle.
# ---------------------------------------------------------------------------
PHI = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio
IPHI = 1.0 / PHI
XI = math.sqrt(2.0) - 1.0  # truncated-cube parameter


def _project(v, scale=1.0):
    """3/4 perspective projection: rotate around z by 25°, tilt around x by 20°."""
    x, y, z = v
    theta = math.radians(25.0)
    phi = math.radians(20.0)
    # z-rotation
    x1 = x * math.cos(theta) - y * math.sin(theta)
    y1 = x * math.sin(theta) + y * math.cos(theta)
    z1 = z
    # x-tilt
    x2 = x1
    y2 = y1 * math.cos(phi) - z1 * math.sin(phi)
    # (z after tilt not needed for orthographic 2D)
    return (x2 * scale, y2 * scale)


def _depth(v):
    """View-direction depth after rotate-then-tilt. Larger = further from viewer."""
    x, y, z = v
    theta = math.radians(25.0)
    phi = math.radians(20.0)
    y1 = x * math.sin(theta) + y * math.cos(theta)
    z1 = z
    # After x-tilt, the view direction is +y (into the screen), so depth = y1*sin + z1*cos
    return y1 * math.sin(phi) + z1 * math.cos(phi)


def _camera_direction():
    """Unit vector from origin toward the camera (in object-local coords).

    Projection does rotate(z, +theta) then tilt(x, +phi), then orthographic
    project onto the XY plane (dropping post-transform Z). Camera is at
    +Z in the post-transform frame (depth axis), so camera direction from
    object is inverse-rotate(0,0,1) = (sin(phi)sin(theta), sin(phi)cos(theta), cos(phi)).
    """
    theta = math.radians(25.0)
    phi = math.radians(20.0)
    return np.array(
        [
            math.sin(phi) * math.sin(theta),
            math.sin(phi) * math.cos(theta),
            math.cos(phi),
        ]
    )


def _face_visibility_map(vertices_3d):
    """Return a dict: (i,j) -> bool (True if edge is visible from camera).

    Uses scipy ConvexHull to triangulate the convex polyhedron and compute
    outward face normals. An edge is visible iff at least one adjacent
    triangulated face has a front-facing normal. For convex polyhedra this
    yields exact hidden-line removal.
    """
    pts = np.array(vertices_3d, dtype=float)
    hull = ConvexHull(pts)
    # hull.equations: [a, b, c, d] so the plane is ax+by+cz+d=0, outward normal = (a,b,c)
    normals = hull.equations[:, :3]
    camera_dir = _camera_direction()
    front_facing = (normals @ camera_dir) > 1e-9  # shape (n_faces,)

    edge_faces = {}
    for f_idx, simplex in enumerate(hull.simplices):
        for k in range(3):
            a, b = int(simplex[k]), int(simplex[(k + 1) % 3])
            key = (min(a, b), max(a, b))
            edge_faces.setdefault(key, []).append(f_idx)

    visibility = {}
    for key, faces in edge_faces.items():
        visibility[key] = any(front_facing[f] for f in faces)
    return visibility


def _auto_edges(vertices_3d, tol=0.05):
    """Return (i, j) pairs for edges: all vertex pairs at the minimum distance."""
    dists = []
    for i in range(len(vertices_3d)):
        for j in range(i + 1, len(vertices_3d)):
            dx = vertices_3d[i][0] - vertices_3d[j][0]
            dy = vertices_3d[i][1] - vertices_3d[j][1]
            dz = vertices_3d[i][2] - vertices_3d[j][2]
            dists.append((math.sqrt(dx * dx + dy * dy + dz * dz), i, j))
    min_d = min(d for d, _, _ in dists)
    return [(i, j) for d, i, j in dists if abs(d - min_d) < tol]


def _polyhedron_wireframe(vertices_3d, center, size, color, stroke=1.5, edges=None, tol=0.05):
    """Render a polyhedron as projected edges with depth cueing.

    Front-facing edges (nearer to the camera) get full stroke and full
    opacity; back-facing edges are drawn thinner and semi-transparent so
    the 3D structure reads clearly even as a flat image.
    """
    cx, cy = center[0], center[1]
    projected = [_project(v) for v in vertices_3d]
    # Normalise so all fit inside unit square, then scale to `size`
    xs = [p[0] for p in projected]
    ys = [p[1] for p in projected]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    scale = size * 2.0 / span  # size is half-extent; diameter ≈ 2*size
    pts = [[cx + p[0] * scale, cy + p[1] * scale, 0] for p in projected]

    if edges is None:
        edges = _auto_edges(vertices_3d, tol=tol)

    # Face-based visibility (exact hidden-line removal for convex polyhedra)
    try:
        visibility = _face_visibility_map(vertices_3d)
    except Exception:
        visibility = None

    # Sort: draw hidden edges first so visible edges appear on top
    def edge_is_visible(i, j):
        if visibility is None:
            return True
        return visibility.get((min(i, j), max(i, j)), True)

    edges_sorted = sorted(edges, key=lambda e: 0 if not edge_is_visible(*e) else 1)

    # Parse hex colour once for background mixing of hidden edges
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[k : k + 2], 16) for k in (0, 2, 4))

    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(c))) for c in rgb])

    fg_rgb = hex_to_rgb(color)
    bg_rgb = hex_to_rgb(BG_COLOR)

    lines = VGroup()
    for i, j in edges_sorted:
        visible = edge_is_visible(i, j)
        if visible:
            width = stroke * 1.3
            edge_color = color
        else:
            width = stroke * 0.6
            mix = 0.60
            mixed_rgb = tuple(fg_rgb[k] * (1 - mix) + bg_rgb[k] * mix for k in range(3))
            edge_color = rgb_to_hex(mixed_rgb)
        lines.add(Line(pts[i], pts[j], color=edge_color, stroke_width=width))
    return lines


# --- Platonic + Archimedean vertex data ------------------------------------
TETRA_V = [
    (1, 1, 1),
    (-1, -1, 1),
    (-1, 1, -1),
    (1, -1, -1),
]

CUBE_V = [
    (-1, -1, -1),
    (1, -1, -1),
    (1, 1, -1),
    (-1, 1, -1),
    (-1, -1, 1),
    (1, -1, 1),
    (1, 1, 1),
    (-1, 1, 1),
]

OCTA_V = [
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
]

DODECA_V = [
    # 8 cube vertices
    (1, 1, 1),
    (1, 1, -1),
    (1, -1, 1),
    (1, -1, -1),
    (-1, 1, 1),
    (-1, 1, -1),
    (-1, -1, 1),
    (-1, -1, -1),
    # (0, ±1/φ, ±φ)
    (0, IPHI, PHI),
    (0, IPHI, -PHI),
    (0, -IPHI, PHI),
    (0, -IPHI, -PHI),
    # (±1/φ, ±φ, 0)
    (IPHI, PHI, 0),
    (IPHI, -PHI, 0),
    (-IPHI, PHI, 0),
    (-IPHI, -PHI, 0),
    # (±φ, 0, ±1/φ)
    (PHI, 0, IPHI),
    (PHI, 0, -IPHI),
    (-PHI, 0, IPHI),
    (-PHI, 0, -IPHI),
]

ICOSA_V = [
    (0, 1, PHI),
    (0, 1, -PHI),
    (0, -1, PHI),
    (0, -1, -PHI),
    (1, PHI, 0),
    (1, -PHI, 0),
    (-1, PHI, 0),
    (-1, -PHI, 0),
    (PHI, 0, 1),
    (PHI, 0, -1),
    (-PHI, 0, 1),
    (-PHI, 0, -1),
]

TRUNC_CUBE_V = [
    # All permutations of (±ξ, ±1, ±1) with ξ = √2-1
    (XI, 1, 1),
    (XI, 1, -1),
    (XI, -1, 1),
    (XI, -1, -1),
    (-XI, 1, 1),
    (-XI, 1, -1),
    (-XI, -1, 1),
    (-XI, -1, -1),
    (1, XI, 1),
    (1, XI, -1),
    (1, -XI, 1),
    (1, -XI, -1),
    (-1, XI, 1),
    (-1, XI, -1),
    (-1, -XI, 1),
    (-1, -XI, -1),
    (1, 1, XI),
    (1, 1, -XI),
    (1, -1, XI),
    (1, -1, -XI),
    (-1, 1, XI),
    (-1, 1, -XI),
    (-1, -1, XI),
    (-1, -1, -XI),
]

# Triangular prism: two equilateral triangles stacked along z.
# Triangle side = √3 (unit-circle inscribed); set z = ±√3/2 so lateral edges
# also have length √3 → all 9 edges equal, picked up by _auto_edges.
PRISM_V = [
    (1.0, 0.0, -0.866),
    (-0.5, 0.866, -0.866),
    (-0.5, -0.866, -0.866),
    (1.0, 0.0, 0.866),
    (-0.5, 0.866, 0.866),
    (-0.5, -0.866, 0.866),
]


def tetrahedron_icon(center, size=0.5, color=TEXT_WHITE):
    return _polyhedron_wireframe(TETRA_V, center, size, color, stroke=1.8)


def cube_icon(center, size=0.5, color=TEXT_WHITE):
    return _polyhedron_wireframe(CUBE_V, center, size, color, stroke=1.8)


def octahedron_icon(center, size=0.5, color=TEXT_WHITE):
    return _polyhedron_wireframe(OCTA_V, center, size, color, stroke=1.8)


def dodecahedron_icon(center, size=0.55, color=TEXT_WHITE):
    return _polyhedron_wireframe(DODECA_V, center, size, color, stroke=1.4, tol=0.05)


def icosahedron_icon(center, size=0.5, color=TEXT_WHITE):
    return _polyhedron_wireframe(ICOSA_V, center, size, color, stroke=1.4, tol=0.05)


def prism_icon(center, size=0.55, color=TEXT_WHITE):
    return _polyhedron_wireframe(PRISM_V, center, size, color, stroke=1.8, tol=0.05)


def truncated_cube_icon(center, size=0.55, color=TEXT_WHITE):
    return _polyhedron_wireframe(TRUNC_CUBE_V, center, size, color, stroke=1.2, tol=0.05)


class PolyhedronEuler(Scene):
    """Euler's polyhedron formula V-E+F=2. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "solids")

        if mode == "non_regular":
            self.build_non_regular()
        elif mode == "formula":
            self.build_formula()
        else:
            self.build_solids()

    # -------------------------------------------------------------------
    # Mode: solids
    # -------------------------------------------------------------------
    def build_solids(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan (5 Platonic solids in a row + table below)
        # title:    y = +3.15
        # subtitle: y = +2.55
        # icons:    y = +1.60 (5 icons in a row)
        # names:    y = +0.85
        # V row:    y = +0.15
        # E row:    y = -0.40
        # F row:    y = -0.95
        # VEF row:  y = -1.55 (all = 2, gold highlight)

        title = Text("5つの正多面体で V − E + F = 2", font=FONT, font_size=26, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        subtitle = Text(
            "── オイラー 1750年、ゴルトバッハへの手紙", font=FONT, font_size=20, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # 5 column x-positions
        col_xs = [-5.0, -2.5, 0.0, 2.5, 5.0]
        icon_y = 1.60

        # Icons
        icons = VGroup(
            tetrahedron_icon([col_xs[0], icon_y, 0], size=0.45, color=ACCENT_CYAN),
            cube_icon([col_xs[1], icon_y, 0], size=0.45, color=ACCENT_CYAN),
            octahedron_icon([col_xs[2], icon_y, 0], size=0.45, color=ACCENT_CYAN),
            dodecahedron_icon([col_xs[3], icon_y, 0], size=0.50, color=ACCENT_CYAN),
            icosahedron_icon([col_xs[4], icon_y, 0], size=0.45, color=ACCENT_CYAN),
        )

        # Names
        names_text = ["正四面体", "立方体", "正八面体", "正十二面体", "正二十面体"]
        names = VGroup()
        for i, n in enumerate(names_text):
            name = Text(n, font=FONT, font_size=18, color=TEXT_WHITE)
            name.move_to([col_xs[i], 0.85, 0])
            names.add(name)

        self.play(FadeIn(icons), run_time=0.9)
        self.play(FadeIn(names), run_time=0.5)
        self.wait(0.4)

        # Data: V, E, F for each
        data = [
            (4, 6, 4),
            (8, 12, 6),
            (6, 12, 8),
            (20, 30, 12),
            (12, 30, 20),
        ]

        # Row labels on the far left (x=-6.3)
        label_x = -6.3
        row_V = MathTex(r"V", font_size=24, color=ACCENT_PINK)
        row_V.move_to([label_x, 0.15, 0])
        row_E = MathTex(r"E", font_size=24, color=ACCENT_PINK)
        row_E.move_to([label_x, -0.40, 0])
        row_F = MathTex(r"F", font_size=24, color=ACCENT_PINK)
        row_F.move_to([label_x, -0.95, 0])
        row_VEF = MathTex(r"V - E + F", font_size=20, color=highlight)
        row_VEF.move_to([label_x, -1.55, 0])

        self.play(FadeIn(row_V), FadeIn(row_E), FadeIn(row_F), FadeIn(row_VEF), run_time=0.6)

        # Cell values
        cells = VGroup()
        for i, (v, e, f) in enumerate(data):
            cv = MathTex(f"{v}", font_size=26, color=TEXT_WHITE)
            cv.move_to([col_xs[i], 0.15, 0])
            ce = MathTex(f"{e}", font_size=26, color=TEXT_WHITE)
            ce.move_to([col_xs[i], -0.40, 0])
            cf = MathTex(f"{f}", font_size=26, color=TEXT_WHITE)
            cf.move_to([col_xs[i], -0.95, 0])
            cvef = MathTex(r"2", font_size=30, color=highlight)
            cvef.move_to([col_xs[i], -1.55, 0])
            cells.add(cv, ce, cf, cvef)

        # Fade in per column
        per_col = VGroup()
        wait_per_col = max(0.3, (duration - 6.0) / 5.0)
        for i in range(5):
            col_cells = VGroup(cells[4 * i], cells[4 * i + 1], cells[4 * i + 2], cells[4 * i + 3])
            self.play(FadeIn(col_cells), run_time=0.4)
            self.wait(wait_per_col * 0.25)

        self.wait(max(1.0, duration * 0.10))

    # -------------------------------------------------------------------
    # Mode: non_regular
    # -------------------------------------------------------------------
    def build_non_regular(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:    y = +3.15
        # subtitle: y = +2.55
        # icons:    y = +1.10 (2 icons, left and right)
        # names:    y = +0.20
        # counts:   y = -0.50  (V=, E=, F=)
        # check:    y = -1.20  (V-E+F=2 computation)
        # closing:  y = -1.85  "非正則でも成り立つ"

        title = Text("非正則な凸多面体でも V − E + F = 2", font=FONT, font_size=26, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        subtitle = Text("── 三角柱と切頂立方体で確認", font=FONT, font_size=20, color=TEXT_DIM)
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Two icons
        prism_pos = [-3.2, 1.10, 0]
        trunc_pos = [3.2, 1.10, 0]
        icon_prism = prism_icon(prism_pos, size=0.60, color=ACCENT_CYAN)
        icon_trunc = truncated_cube_icon(trunc_pos, size=0.55, color=ACCENT_CYAN)

        # Names
        name_prism = Text("三角柱", font=FONT, font_size=22, color=TEXT_WHITE)
        name_prism.move_to([-3.2, 0.20, 0])
        name_trunc = Text("切頂立方体", font=FONT, font_size=22, color=TEXT_WHITE)
        name_trunc.move_to([3.2, 0.20, 0])

        self.play(FadeIn(icon_prism), FadeIn(icon_trunc), run_time=0.8)
        self.play(FadeIn(name_prism), FadeIn(name_trunc), run_time=0.5)
        self.wait(0.3)

        # Counts
        counts_prism = MathTex(r"V=6,\ E=9,\ F=5", font_size=28, color=TEXT_WHITE)
        counts_prism.move_to([-3.2, -0.50, 0])
        counts_trunc = MathTex(r"V=24,\ E=36,\ F=14", font_size=28, color=TEXT_WHITE)
        counts_trunc.move_to([3.2, -0.50, 0])

        self.play(FadeIn(counts_prism), FadeIn(counts_trunc), run_time=0.7)
        self.wait(0.4)

        # V - E + F = 2 verification
        check_prism = MathTex(r"6 - 9 + 5 = 2", font_size=30, color=highlight)
        check_prism.move_to([-3.2, -1.20, 0])
        check_trunc = MathTex(r"24 - 36 + 14 = 2", font_size=30, color=highlight)
        check_trunc.move_to([3.2, -1.20, 0])

        self.play(FadeIn(check_prism), FadeIn(check_trunc), run_time=0.7)
        self.wait(0.5)

        # Closing
        closing = Text("凸多面体ならば、必ず 2 になる", font=FONT, font_size=24, color=ACCENT_GOLD)
        closing.move_to([0, -1.85, 0])
        self.play(FadeIn(closing), run_time=0.7)

        anim_overhead = 0.5 + 0.5 + 0.8 + 0.5 + 0.3 + 0.7 + 0.4 + 0.7 + 0.5 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: formula
    # -------------------------------------------------------------------
    def build_formula(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan
        # title:      y = +3.15
        # subtitle:   y = +2.55
        # formula:    y = +0.60  (large central display)
        # quote_date: y = -0.50
        # quote:      y = -1.10
        # closing:    y = -1.85

        title = Text("多面体公式", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        subtitle = Text("── 形の数学の最初の一滴", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Large formula (central)
        formula = MathTex(
            r"V",  # 0
            r"-",  # 1
            r"E",  # 2
            r"+",  # 3
            r"F",  # 4
            r"=",  # 5
            r"2",  # 6
            font_size=72,
        )
        formula[0].set_color(ACCENT_PINK)
        formula[2].set_color(ACCENT_CYAN)
        formula[4].set_color(ACCENT_GOLD)
        formula[6].set_color(highlight)
        formula.move_to([0, 0.80, 0])

        self.play(FadeIn(formula), run_time=1.0)
        box = SurroundingRectangle(formula, color=highlight, buff=0.20)
        self.play(FadeIn(box), run_time=0.5)
        self.wait(0.6)

        # Quote date
        quote_date = Text(
            "1750年11月14日、ペテルブルクのゴルトバッハ宛書簡",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        quote_date.move_to([0, -0.85, 0])
        self.play(FadeIn(quote_date), run_time=0.6)
        self.wait(0.5)

        # Closing note
        closing = Text(
            "のちに「オイラー特性数 χ」と呼ばれる量の出発点",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        closing.move_to([0, -1.80, 0])
        self.play(FadeIn(closing), run_time=0.7)

        anim_overhead = 0.5 + 0.5 + 1.0 + 0.5 + 0.6 + 0.6 + 0.5 + 0.7
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "solids": {"people": [], "years": []},
    "non_regular": {"people": [], "years": []},
    "formula": {"people": [["オイラー", "Euler"]], "years": ["1750"]},
}


SCENES = {
    "solids": {
        "class": "PolyhedronEuler",
        "params": {"mode": "solids"},
        "description": "5 Platonic solids + V,E,F,V-E+F table (all = 2)",
    },
    "non_regular": {
        "class": "PolyhedronEuler",
        "params": {"mode": "non_regular"},
        "description": "Triangular prism and truncated cube: V-E+F=2 verification",
    },
    "formula": {
        "class": "PolyhedronEuler",
        "params": {"mode": "formula"},
        "description": "V-E+F=2 centered display with 1750 Goldbach letter attribution",
    },
}
