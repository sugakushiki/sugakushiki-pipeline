"""
erlangen_hierarchy.py - Klein's Erlangen Program: the group decides the geometry

Klein's 1872 Erlangen Program defines a geometry as the study of the properties
that stay invariant under a chosen group of transformations. Widening the group
destroys invariants one at a time, so the competing geometries line up as one
nested chain, and "what do you want to keep?" becomes "which geometry is this?".

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    invariants      - One square is acted on by a widening group while the
                      invariant list on the right goes out one entry at a time.
                      Fixed chain (5 stages, 7 invariants):
                        合同     -> all 7 lit
                        相似     -> 長さ falls           (6 lit)
                        アフィン -> 角 falls             (5 lit)
                        射影     -> 平行, 線分の比 fall  (3 lit)
                        位相     -> 複比, 共線性 fall    (1 lit: つながり)
    nesting         - The same chain as 5 concentric rectangles
                      (合同 ⊂ 相似 ⊂ アフィン ⊂ 射影 ⊂ 位相同相) with the matching
                      geometry names in a right-hand legend. Fixed: 5 rings.
    curvature_limit - Where the program stops. Left: a homogeneous grid, every
                      point alike, one motion carrying any point to any other.
                      Right: a profile whose bending varies from place to place;
                      5 short tangent segments are the local homogeneous models,
                      and the angle between the transported tangent and the
                      actual one is the curvature. Fixed: 5 tangents.

No on-screen person names or years (every label is geometric vocabulary), so
LINT_FACTUAL_CLAIMS is empty for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    TAU,
    UP,
    Arrow,
    Create,
    DashedVMobject,
    Dot,
    FadeIn,
    Line,
    ParametricFunction,
    Polygon,
    Rectangle,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR


class ErlangenHierarchy(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "invariants")
        duration = params.get("duration", 26)
        if mode == "nesting":
            self._nesting(duration)
        elif mode == "curvature_limit":
            self._curvature_limit(duration)
        else:
            self._invariants(duration)

    # -- mode: invariants -----------------------------------------------------
    def _invariants(self, duration):
        title = Text("どこまで動かしてよいか", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.05)

        shape_c = LEFT * 3.4 + UP * 0.55
        base = Polygon(
            *[
                np.array([x, y, 0.0])
                for x, y in ((-0.75, -0.75), (0.75, -0.75), (0.75, 0.75), (-0.75, 0.75))
            ],
            color=ACCENT_CYAN,
            stroke_width=4,
        )

        congruent = base.copy().rotate(math.radians(18)).move_to(shape_c)
        similar = base.copy().rotate(math.radians(18)).scale(0.66).move_to(shape_c)
        affine = similar.copy().apply_matrix(np.array([[1.0, 0.62], [0.0, 0.82]])).move_to(shape_c)
        projective = Polygon(
            *[
                np.array([x, y, 0.0])
                for x, y in ((-1.02, -0.60), (0.88, -0.86), (0.60, 0.80), (-0.70, 0.50))
            ],
            color=ACCENT_CYAN,
            stroke_width=4,
        ).move_to(shape_c)

        def blob(t):
            r = 0.86 + 0.17 * math.sin(3 * t) + 0.11 * math.cos(2 * t)
            return shape_c + RIGHT * (r * math.cos(t)) + UP * (r * math.sin(t))

        topological = ParametricFunction(blob, t_range=[0, TAU], color=ACCENT_CYAN, stroke_width=4)

        # invariant column: index -> label
        names = ["長さ", "角", "平行", "線分の比", "複比", "共線性", "つながり"]
        col_x = 3.4
        labels = VGroup()
        for i, nm in enumerate(names):
            lab = Text(nm, font=FONT, font_size=23, color=TEXT_WHITE)
            lab.move_to(RIGHT * col_x + UP * (1.75 - i * 0.5))
            labels.add(lab)
        col_head = Text("変わらないもの", font=FONT, font_size=21, color=ACCENT_GOLD)
        col_head.move_to(RIGHT * col_x + UP * 2.35)

        group_name = Text("合同変換", font=FONT, font_size=27, color=ACCENT_GOLD)
        group_name.move_to(shape_c + UP * 1.75)

        self.play(FadeIn(title), FadeIn(col_head), run_time=0.9)
        self.play(FadeIn(congruent), FadeIn(group_name), FadeIn(labels), run_time=1.3)

        # (next shape, next group name, indices of invariants that die here)
        stages = [
            (similar, "相似変換", [0]),
            (affine, "アフィン変換", [1]),
            (projective, "射影変換", [2, 3]),
            (topological, "位相同相", [4, 5]),
        ]
        rt = pace(duration, [1.0, 1.0, 1.15, 1.15, 1.2], intro=2.2, coda=3.0)

        current = congruent
        for i, (nxt, gname, dead) in enumerate(stages):
            new_name = Text(gname, font=FONT, font_size=27, color=ACCENT_GOLD)
            new_name.move_to(shape_c + UP * 1.75)
            anims = [
                ReplacementTransform(current, nxt),
                ReplacementTransform(group_name, new_name),
            ]
            for d in dead:
                lab = labels[d]
                strike = Line(
                    lab.get_left() + LEFT * 0.12,
                    lab.get_right() + RIGHT * 0.12,
                    color=ACCENT_PINK,
                    stroke_width=3,
                )
                anims.append(lab.animate.set_color(TEXT_DIM).set_opacity(0.45))
                anims.append(Create(strike))
            self.play(*anims, run_time=rt[i])
            current = nxt
            group_name = new_name

        closing = Text(
            "許す動きが大きいほど、区別できるものは減る",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        closing.move_to(DOWN * 1.72)
        self.play(FadeIn(closing), run_time=rt[4])
        self.wait(3.0)

    # -- mode: nesting --------------------------------------------------------
    def _nesting(self, duration):
        title = Text("群の入れ子が、幾何の階層になる", font=FONT, font_size=29, color=ACCENT_GOLD)
        title.move_to(UP * 3.15)

        cy = 0.15
        rings = [
            ("合同", "ユークリッド幾何", 2.0, 1.0, ACCENT_GOLD),
            ("相似", "相似の幾何", 3.6, 1.8, ACCENT_CYAN),
            ("アフィン", "アフィン幾何", 5.2, 2.6, ACCENT_CYAN),
            ("射影", "射影幾何", 6.8, 3.4, ACCENT_PINK),
            ("位相同相", "位相幾何", 8.4, 4.2, TEXT_WHITE),
        ]

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.2], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)

        legend_x = 5.7
        for i, (gname, geo, w, h, color) in enumerate(rings):
            rect = Rectangle(width=w, height=h, color=color, stroke_width=3)
            rect.move_to(UP * cy)
            lab = Text(gname, font=FONT, font_size=20, color=color)
            lab.move_to(UP * (cy + h / 2 - 0.22))
            leg = Text(geo, font=FONT, font_size=20, color=color)
            leg.move_to(RIGHT * legend_x + UP * (cy + h / 2 - 0.22))
            self.play(Create(rect), FadeIn(lab), FadeIn(leg), run_time=rt[i])

        note = Text(
            "大きい群ほど、区別できるものが少ない",
            font=FONT,
            font_size=21,
            color=TEXT_DIM,
        )
        note.move_to(UP * 2.68)
        self.play(FadeIn(note), run_time=rt[5])

        answer = Text(
            "何を保ちたいかが、どの幾何かを決める",
            font=FONT,
            font_size=21,
            color=ACCENT_GOLD,
        )
        answer.move_to(UP * 2.68)
        self.play(ReplacementTransform(note, answer), run_time=rt[6])
        self.wait(3.0)

    # -- mode: curvature_limit ------------------------------------------------
    def _curvature_limit(self, duration):
        title = Text("エルランゲンが届かない場所", font=FONT, font_size=29, color=ACCENT_GOLD)
        title.move_to(UP * 3.05)

        lc = LEFT * 3.6
        rc = RIGHT * 3.4

        left_head = Text("どの点も同じに見える", font=FONT, font_size=22, color=ACCENT_CYAN)
        left_head.move_to(lc + UP * 2.15)
        right_head = Text("曲がり方が場所ごとに違う", font=FONT, font_size=22, color=ACCENT_PINK)
        right_head.move_to(rc + UP * 2.15)

        # ---- left: homogeneous grid, the group acts across the whole plane ---
        grid = VGroup()
        for gx in range(-2, 3):
            for gy in range(-2, 2):
                grid.add(
                    Dot(
                        lc + RIGHT * (gx * 0.72) + UP * (gy * 0.72 + 0.35),
                        color=EDGE_COLOR,
                        radius=0.05,
                    )
                )
        a = lc + LEFT * 1.44 + UP * (0.35 - 0.72)
        b = lc + RIGHT * 1.44 + UP * (0.35 + 0.72)
        dot_a = Dot(a, color=ACCENT_GOLD, radius=0.09)
        dot_b = Dot(b, color=ACCENT_GOLD, radius=0.09)
        move = Arrow(
            a, b, buff=0.14, color=ACCENT_GOLD, stroke_width=4, max_tip_length_to_length_ratio=0.12
        )
        left_note = Text("どこへでも運べる", font=FONT, font_size=21, color=TEXT_DIM)
        left_note.move_to(lc + DOWN * 1.72)

        # ---- right: varying curvature, local homogeneous models don't match --
        # The phase offset 0.9 is load-bearing: with a symmetric profile the slope
        # at the first and the last sample would be IDENTICAL (cos is even), so the
        # transported tangent would land exactly on the actual one and the whole
        # "mismatch = curvature" point would render as a zero gap.
        x_scale = 0.70

        def prof(t):
            return rc + RIGHT * (t * x_scale) + UP * (0.5 * math.sin(1.25 * t + 0.9) + 0.35)

        curve = ParametricFunction(prof, t_range=[-2.05, 2.05], color=TEXT_DIM, stroke_width=3)

        def tangent_dir(t):
            dx = x_scale
            dy = 0.5 * 1.25 * math.cos(1.25 * t + 0.9)
            n = math.hypot(dx, dy)
            return np.array([dx / n, dy / n, 0.0])

        ts = [-1.7, -0.85, 0.0, 0.85, 1.7]
        tangents = VGroup()
        for t in ts:
            p = prof(t)
            d = tangent_dir(t) * 0.62
            tangents.add(Line(p - d, p + d, color=ACCENT_GOLD, stroke_width=5))

        # transported (kept parallel to the first tangent) vs the actual last one
        p_last = prof(ts[-1])
        d_first = tangent_dir(ts[0]) * 0.62
        transported = DashedVMobject(
            Line(p_last - d_first, p_last + d_first, color=ACCENT_CYAN, stroke_width=5),
            num_dashes=9,
        )
        gap = Text("ずれ＝曲率", font=FONT, font_size=21, color=ACCENT_CYAN)
        gap.move_to(rc + RIGHT * 1.2 + UP * 1.45)
        right_note = Text("各点に小さな等質空間を貼る", font=FONT, font_size=21, color=TEXT_DIM)
        right_note.move_to(rc + DOWN * 1.72)

        rt = pace(duration, [1.0, 0.9, 1.0, 1.0, 1.0, 1.0], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)
        self.play(FadeIn(left_head), FadeIn(grid), FadeIn(dot_a), FadeIn(dot_b), run_time=rt[0])
        self.play(Create(move), FadeIn(left_note), run_time=rt[1])
        self.play(FadeIn(right_head), Create(curve), run_time=rt[2])
        self.play(FadeIn(tangents), run_time=rt[3])
        self.play(FadeIn(right_note), run_time=rt[4])
        self.play(Create(transported), FadeIn(gap), run_time=rt[5])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). Every on-screen label
# is geometric vocabulary - no person names, no years.
LINT_FACTUAL_CLAIMS = {
    "invariants": {"people": [], "years": []},
    "nesting": {"people": [], "years": []},
    "curvature_limit": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "invariants": ErlangenHierarchy,
    "nesting": ErlangenHierarchy,
    "curvature_limit": ErlangenHierarchy,
}
