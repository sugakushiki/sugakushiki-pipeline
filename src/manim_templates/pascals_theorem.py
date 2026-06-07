"""
pascals_theorem.py - Pascal's theorem (mystic hexagram) for 数学史記

Pascal's theorem (Essay pour les coniques, Paris 1640, age 16):
If a hexagon P1P2P3P4P5P6 is inscribed in any conic (circle, ellipse,
parabola, or hyperbola), then the three intersection points of the three
pairs of opposite sides
    L1 = P1P2 ∩ P4P5
    L2 = P2P3 ∩ P5P6
    L3 = P3P4 ∩ P6P1
are collinear. The line through L1, L2, L3 is called the Pascal line.

This template visualizes the theorem on a circle (the simplest conic).

Modes:
    mystic_hexagram
        Draw a circle (center (0, 0.4), radius 1.6 in scene units), place
        six points on the circle at angles 20°, 75°, 130°, 200°, 255°, 320°,
        draw the hexagon, then extend the three pairs of opposite sides,
        mark the three intersection points L1, L2, L3, and finally draw
        the Pascal line through them.
        Fixed params: circle center (0, 0.4), radius 1.6, point angles in
        degrees [20, 75, 130, 200, 255, 320].

    construction
        Build the configuration incrementally:
            Step 1: draw circle and six points only.
            Step 2: draw and extend opposite-side pair (P1P2, P4P5),
                    mark intersection L1.
            Step 3: add second opposite-side pair (P2P3, P5P6),
                    mark intersection L2.
            Step 4: add third opposite-side pair (P3P4, P6P1),
                    mark intersection L3, then draw Pascal line through
                    L1, L2, L3.
        Same circle / angles as mystic_hexagram mode.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.3, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 029 (Pascal), 遺産1 - パスカルの定理 (mystic hexagram).
"""

import math

import numpy as np
from manim import (
    Circle,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
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

# Configuration shared across modes. The six angles are deliberately
# non-symmetric: symmetric (regular-hexagon-like) angles make the three
# pairs of opposite sides nearly parallel, sending their intersections to
# (or near) infinity and placing the Pascal line off-screen. With the
# chosen angles [0, 30, 70, 80, 150, 220] and circle (center (0, 0),
# radius 1.0), the three intersections L1, L2, L3 fall at approximately
# (0.67, 1.22), (-1.00, 2.07), and (2.21, 0.44), all within the visible
# window y ∈ [-2.0, +2.5] and x ∈ [-2, +3].
CIRCLE_CENTER = np.array([0.0, 0.0, 0.0])
CIRCLE_RADIUS = 1.0
POINT_ANGLES_DEG = [0.0, 30.0, 70.0, 80.0, 150.0, 220.0]


def _point_on_circle(angle_deg):
    rad = math.radians(angle_deg)
    return CIRCLE_CENTER + CIRCLE_RADIUS * np.array(
        [math.cos(rad), math.sin(rad), 0.0]
    )


def _line_intersection(p1, p2, p3, p4):
    """Return intersection point of lines (p1,p2) and (p3,p4) in 2D (z=0).

    Returns None if the lines are parallel or numerically singular.
    """
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = p3[0], p3[1]
    x4, y4 = p4[0], p4[1]
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    x = x1 + t * (x2 - x1)
    y = y1 + t * (y2 - y1)
    return np.array([x, y, 0.0])


def _extended_segment(p_a, p_b, target):
    """Return endpoints of segment from p_a through p_b extended to reach target.

    The returned line is drawn from p_a, through p_b, and on to target so that
    the user can see the side extended to its intersection.
    """
    return p_a, target


class PascalsTheorem(Scene):
    """Pascal's theorem (mystic hexagram) visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "mystic_hexagram")
        self._duration = float(params.get("duration", 25))

        if mode == "construction":
            self._build_construction()
        else:
            self._build_mystic_hexagram()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _make_circle(self):
        c = Circle(radius=CIRCLE_RADIUS, color=TEXT_DIM, stroke_width=2.0)
        c.move_to(CIRCLE_CENTER)
        return c

    def _make_points_and_labels(self):
        pts = [_point_on_circle(a) for a in POINT_ANGLES_DEG]
        dots = [Dot(p, color=ACCENT_CYAN, radius=0.07) for p in pts]
        labels = []
        for i, p in enumerate(pts):
            # Push label slightly outward from circle center
            v = p - CIRCLE_CENTER
            v_norm = v / np.linalg.norm(v)
            label_pos = p + 0.35 * v_norm
            lbl = MathTex(f"P_{i + 1}", font_size=22, color=ACCENT_CYAN)
            lbl.move_to(label_pos)
            labels.append(lbl)
        return pts, dots, labels

    def _make_hexagon(self, pts):
        lines = []
        for i in range(6):
            j = (i + 1) % 6
            seg = Line(pts[i], pts[j], color=ACCENT_GOLD, stroke_width=2.2)
            lines.append(seg)
        return VGroup(*lines)

    # ------------------------------------------------------------------
    def _build_mystic_hexagram(self):
        duration = self._duration
        title = self._title("パスカルの定理 ── 神秘の六角形")
        self.play(FadeIn(title), run_time=0.6)

        circle = self._make_circle()
        self.play(Create(circle), run_time=0.8)

        pts, dots, labels = self._make_points_and_labels()
        self.play(*[FadeIn(d) for d in dots], *[FadeIn(l) for l in labels], run_time=0.9)

        hexagon = self._make_hexagon(pts)
        self.play(Create(hexagon), run_time=1.0)

        # Compute three intersection points
        # Pair 1: (P1P2, P4P5)
        L1 = _line_intersection(pts[0], pts[1], pts[3], pts[4])
        # Pair 2: (P2P3, P5P6)
        L2 = _line_intersection(pts[1], pts[2], pts[4], pts[5])
        # Pair 3: (P3P4, P6P1)
        L3 = _line_intersection(pts[2], pts[3], pts[5], pts[0])

        # Draw extended sides to each intersection (dim)
        ext_lines = VGroup()
        for (a, b), L, col in [
            ((pts[0], pts[1]), L1, ACCENT_PINK),
            ((pts[3], pts[4]), L1, ACCENT_PINK),
            ((pts[1], pts[2]), L2, ACCENT_CYAN),
            ((pts[4], pts[5]), L2, ACCENT_CYAN),
            ((pts[2], pts[3]), L3, ACCENT_GOLD),
            ((pts[5], pts[0]), L3, ACCENT_GOLD),
        ]:
            if L is None:
                continue
            seg = DashedLine(a, L, color=col, stroke_width=1.6, dash_length=0.08)
            seg_b = DashedLine(b, L, color=col, stroke_width=1.6, dash_length=0.08)
            ext_lines.add(seg, seg_b)
        self.play(Create(ext_lines), run_time=1.2)

        # Mark intersection points
        L_dots = VGroup()
        L_labels = VGroup()
        for L, name, col in [(L1, "L_1", ACCENT_PINK), (L2, "L_2", ACCENT_CYAN), (L3, "L_3", ACCENT_GOLD)]:
            if L is None:
                continue
            d = Dot(L, color=col, radius=0.09)
            lbl = MathTex(name, font_size=24, color=col)
            lbl.move_to(L + np.array([0.30, 0.20, 0]))
            L_dots.add(d)
            L_labels.add(lbl)
        self.play(*[FadeIn(d) for d in L_dots], *[FadeIn(l) for l in L_labels], run_time=0.8)

        # Draw the Pascal line covering all 3 intersection points (L1, L2, L3).
        # Day 20 ある回 fix: previously drew line from L1 to L3 only, which left
        # L2 (mathematically collinear but geometrically outside L1-L3 segment)
        # appearing off-line on screen. Now compute parameter range covering all
        # 3 points + pad, so the drawn line passes visibly through all of them.
        if L1 is not None and L2 is not None and L3 is not None:
            dir_vec = L3 - L1
            norm = np.linalg.norm(dir_vec)
            if norm > 1e-6:
                unit = dir_vec / norm
                # Project all 3 L points onto unit direction (relative to L1)
                projections = [float(np.dot(p - L1, unit)) for p in (L1, L2, L3)]
                pad = 0.5
                min_proj = min(projections) - pad
                max_proj = max(projections) + pad
                a = L1 + min_proj * unit
                b = L1 + max_proj * unit
                pascal_line = Line(a, b, color=ACCENT_GOLD, stroke_width=3.2)
                self.play(Create(pascal_line), run_time=1.0)

        msg = Text(
            "三つの交点はいつも一直線上に並ぶ ── Pascal 線",
            font=FONT, font_size=20, color=ACCENT_PINK,
        )
        msg.move_to([0, -1.85, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.8 + 0.9 + 1.0 + 1.2 + 0.8 + 1.0 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_construction(self):
        duration = self._duration
        title = self._title("パスカル線の構成 ── 三組の対辺から")
        self.play(FadeIn(title), run_time=0.6)

        circle = self._make_circle()
        self.play(Create(circle), run_time=0.6)

        pts, dots, labels = self._make_points_and_labels()
        self.play(*[FadeIn(d) for d in dots], *[FadeIn(l) for l in labels], run_time=0.8)

        # Step 2: pair (P1P2, P4P5) → L1
        L1 = _line_intersection(pts[0], pts[1], pts[3], pts[4])
        s12 = Line(pts[0], pts[1], color=ACCENT_PINK, stroke_width=2.4)
        s45 = Line(pts[3], pts[4], color=ACCENT_PINK, stroke_width=2.4)
        self.play(Create(s12), Create(s45), run_time=0.7)
        if L1 is not None:
            e12 = DashedLine(pts[1], L1, color=ACCENT_PINK, stroke_width=1.6, dash_length=0.08)
            e45 = DashedLine(pts[4], L1, color=ACCENT_PINK, stroke_width=1.6, dash_length=0.08)
            d1 = Dot(L1, color=ACCENT_PINK, radius=0.09)
            l1_lbl = MathTex("L_1", font_size=24, color=ACCENT_PINK)
            l1_lbl.move_to(L1 + np.array([0.30, 0.20, 0]))
            self.play(Create(e12), Create(e45), FadeIn(d1), FadeIn(l1_lbl), run_time=0.9)

        # Step 3: pair (P2P3, P5P6) → L2
        L2 = _line_intersection(pts[1], pts[2], pts[4], pts[5])
        s23 = Line(pts[1], pts[2], color=ACCENT_CYAN, stroke_width=2.4)
        s56 = Line(pts[4], pts[5], color=ACCENT_CYAN, stroke_width=2.4)
        self.play(Create(s23), Create(s56), run_time=0.7)
        if L2 is not None:
            e23 = DashedLine(pts[2], L2, color=ACCENT_CYAN, stroke_width=1.6, dash_length=0.08)
            e56 = DashedLine(pts[5], L2, color=ACCENT_CYAN, stroke_width=1.6, dash_length=0.08)
            d2 = Dot(L2, color=ACCENT_CYAN, radius=0.09)
            l2_lbl = MathTex("L_2", font_size=24, color=ACCENT_CYAN)
            l2_lbl.move_to(L2 + np.array([0.30, 0.20, 0]))
            self.play(Create(e23), Create(e56), FadeIn(d2), FadeIn(l2_lbl), run_time=0.9)

        # Step 4: pair (P3P4, P6P1) → L3, then draw Pascal line
        L3 = _line_intersection(pts[2], pts[3], pts[5], pts[0])
        s34 = Line(pts[2], pts[3], color=ACCENT_GOLD, stroke_width=2.4)
        s61 = Line(pts[5], pts[0], color=ACCENT_GOLD, stroke_width=2.4)
        self.play(Create(s34), Create(s61), run_time=0.7)
        if L3 is not None:
            e34 = DashedLine(pts[3], L3, color=ACCENT_GOLD, stroke_width=1.6, dash_length=0.08)
            e61 = DashedLine(pts[0], L3, color=ACCENT_GOLD, stroke_width=1.6, dash_length=0.08)
            d3 = Dot(L3, color=ACCENT_GOLD, radius=0.09)
            l3_lbl = MathTex("L_3", font_size=24, color=ACCENT_GOLD)
            l3_lbl.move_to(L3 + np.array([0.30, 0.20, 0]))
            self.play(Create(e34), Create(e61), FadeIn(d3), FadeIn(l3_lbl), run_time=0.9)

        # Draw Pascal line covering all 3 intersection points (L1, L2, L3).
        # Day 20 ある回 fix (same as mystic_hexagram mode): project L1, L2, L3
        # onto line direction, draw segment covering min..max + pad so all
        # 3 points appear visibly on the line.
        if L1 is not None and L2 is not None and L3 is not None:
            dir_vec = L3 - L1
            norm = np.linalg.norm(dir_vec)
            if norm > 1e-6:
                unit = dir_vec / norm
                projections = [float(np.dot(p - L1, unit)) for p in (L1, L2, L3)]
                pad = 0.5
                min_proj = min(projections) - pad
                max_proj = max(projections) + pad
                a = L1 + min_proj * unit
                b = L1 + max_proj * unit
                pascal_line = Line(a, b, color=ACCENT_GOLD, stroke_width=3.2)
                self.play(Create(pascal_line), run_time=1.0)

        msg = Text(
            "三点 L1, L2, L3 は一直線上に並ぶ",
            font=FONT, font_size=20, color=ACCENT_PINK,
        )
        msg.move_to([0, -1.85, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 0.6 + 0.8 + (0.7 + 0.9) * 3 + 1.0 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "mystic_hexagram": {"people": [], "years": []},
    "construction": {"people": [], "years": []},
}

SCENES = {
    "mystic_hexagram": PascalsTheorem,
    "construction": PascalsTheorem,
}
