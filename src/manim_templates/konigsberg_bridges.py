"""
konigsberg_bridges.py - Seven Bridges of Königsberg for 数学史記

Visualizes Euler's 1736 paper that founded graph theory:
    Solutio problematis ad geometriam situs pertinentis (E053).

Four landmasses — North bank (A), South bank (B), Kneiphof island (C),
and East island (D) — are connected by 7 bridges:
    A-C: 2 bridges    B-C: 2 bridges
    A-D: 1 bridge     B-D: 1 bridge     C-D: 1 bridge

The vertex degrees are therefore  A=3, B=3, C=5, D=3  (all odd),
so no Eulerian path exists (Euler's necessary condition fails).

Modes:
    map       - 18th-century schematic of Königsberg: river,
                4 landmasses, 7 labeled bridges. Question posed.
    abstract  - Transform map to a multigraph: landmasses become
                vertices, bridges become edges (2 parallel edges
                for A-C and B-C). This abstraction *is* graph theory.
    degree    - Count the degree at each vertex; all four odd →
                Eulerian path impossible. Euler's necessary condition
                stated as the conclusion.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 019 (Euler applied), math pillar 1a.
"""

from manim import (
    ArcBetweenPoints,
    Dot,
    FadeIn,
    Line,
    MathTex,
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


# ---------------------------------------------------------------------------
# Shared geometry: landmass / vertex positions (used in all three modes)
# ---------------------------------------------------------------------------
# x = -2.5 .. +2.5, y = -1.2 .. +1.2 (within safe zone)
POS_A = [-2.8, 1.15, 0]  # North bank
POS_B = [-2.8, -1.15, 0]  # South bank
POS_C = [-0.3, 0.0, 0]  # Kneiphof (center island)
POS_D = [2.5, 0.0, 0]  # East island

LAND_COLOR = "#3a5a7a"  # muted blue-green (landmass fill)
RIVER_COLOR = "#2a3a6e"  # darker blue (river)
BRIDGE_COLOR = TEXT_WHITE


class KonigsbergBridges(Scene):
    """Königsberg bridges + graph theory. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "map")

        if mode == "abstract":
            self.build_abstract()
        elif mode == "degree":
            self.build_degree()
        else:
            self.build_map()

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _landmass(self, pos, width, height, label, color=LAND_COLOR):
        """Create a rounded landmass rectangle + letter label."""
        rect = Rectangle(
            width=width,
            height=height,
            color=color,
            fill_opacity=0.6,
            stroke_width=1.5,
        )
        rect.move_to(pos)
        letter = Text(label, font=FONT, font_size=26, color=TEXT_WHITE)
        letter.move_to(pos)
        return VGroup(rect, letter)

    def _straight_bridge(self, p1, p2, color=BRIDGE_COLOR, stroke=3):
        """A straight line bridge."""
        return Line(start=p1, end=p2, color=color, stroke_width=stroke)

    def _curved_bridge(self, p1, p2, curve=0.4, color=BRIDGE_COLOR, stroke=3):
        """A slightly curved bridge (for parallel bridge pairs)."""
        return ArcBetweenPoints(
            p1,
            p2,
            angle=curve,
            color=color,
            stroke_width=stroke,
        )

    # -------------------------------------------------------------------
    # Mode: map
    # -------------------------------------------------------------------
    def build_map(self):
        duration = self._duration

        # --- Layout plan
        # title:    y = +3.15
        # year:     y = +2.50   (subtitle line)
        # map area: y = -1.5 .. +1.5 (4 landmasses + river + 7 bridges)
        # question: y = -1.70  (problem statement)

        title = Text("ケーニヒスベルクの7つの橋", font=FONT, font_size=28, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        year = Text("── 1736年、オイラーの散歩問題", font=FONT, font_size=22, color=TEXT_DIM)
        year.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(year), run_time=0.5)

        # Pregel river: horizontal strip across center
        river = Rectangle(
            width=7.5,
            height=2.2,
            color=RIVER_COLOR,
            fill_opacity=0.5,
            stroke_width=0,
        )
        river.move_to([0, 0, 0])
        river_label = Text("プレーゲル川", font=FONT, font_size=18, color=TEXT_DIM)
        river_label.move_to([3.5, 0.9, 0])

        self.play(FadeIn(river), FadeIn(river_label), run_time=0.6)

        # Landmasses
        land_A = self._landmass(POS_A, width=3.2, height=0.9, label="A")
        land_B = self._landmass(POS_B, width=3.2, height=0.9, label="B")
        land_C = self._landmass(POS_C, width=1.4, height=0.7, label="C")
        land_D = self._landmass(POS_D, width=1.6, height=1.6, label="D")

        self.play(
            FadeIn(land_A),
            FadeIn(land_B),
            FadeIn(land_C),
            FadeIn(land_D),
            run_time=0.8,
        )

        # 7 Bridges
        # A-C: 2 bridges (upper pair)
        ac1 = self._straight_bridge([-2.0, POS_A[1] - 0.45, 0], [-0.8, POS_C[1] + 0.35, 0])
        ac2 = self._straight_bridge([-1.2, POS_A[1] - 0.45, 0], [-0.2, POS_C[1] + 0.35, 0])

        # B-C: 2 bridges (lower pair)
        bc1 = self._straight_bridge([-2.0, POS_B[1] + 0.45, 0], [-0.8, POS_C[1] - 0.35, 0])
        bc2 = self._straight_bridge([-1.2, POS_B[1] + 0.45, 0], [-0.2, POS_C[1] - 0.35, 0])

        # A-D: 1 bridge (upper east)
        ad = self._straight_bridge([-1.4, POS_A[1] - 0.45, 0], [1.9, POS_D[1] + 0.6, 0])

        # B-D: 1 bridge (lower east)
        bd = self._straight_bridge([-1.4, POS_B[1] + 0.45, 0], [1.9, POS_D[1] - 0.6, 0])

        # C-D: 1 bridge (middle)
        cd = self._straight_bridge([POS_C[0] + 0.7, 0, 0], [POS_D[0] - 0.8, 0, 0])

        bridges = VGroup(ac1, ac2, bc1, bc2, ad, bd, cd)
        self.play(FadeIn(bridges), run_time=0.9)
        self.wait(0.4)

        # Question
        question = Text(
            "すべての橋を一度ずつ渡り、出発点に戻れるか？",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        question.move_to([0, -1.75, 0])

        self.play(FadeIn(question), run_time=0.8)

        anim_overhead = 0.5 + 0.5 + 0.6 + 0.8 + 0.9 + 0.4 + 0.8
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: abstract
    # -------------------------------------------------------------------
    def build_abstract(self):
        duration = self._duration

        # --- Layout plan
        # title:       y = +3.15
        # subtitle:    y = +2.50
        # graph area:  y = -1.2 .. +1.2
        # annotation:  y = -1.75

        title = Text("陸地を点に、橋を線に", font=FONT, font_size=28, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        subtitle = Text("── 世界最初のグラフ", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Vertices (larger dots, colored)
        v_A = Dot(POS_A, color=ACCENT_CYAN, radius=0.16)
        v_B = Dot(POS_B, color=ACCENT_CYAN, radius=0.16)
        v_C = Dot(POS_C, color=ACCENT_PINK, radius=0.18)  # central, highlighted
        v_D = Dot(POS_D, color=ACCENT_CYAN, radius=0.16)

        # Vertex labels
        lA = MathTex(r"A", font_size=28, color=TEXT_WHITE)
        lA.move_to([POS_A[0] - 0.35, POS_A[1], 0])
        lB = MathTex(r"B", font_size=28, color=TEXT_WHITE)
        lB.move_to([POS_B[0] - 0.35, POS_B[1], 0])
        lC = MathTex(r"C", font_size=28, color=TEXT_WHITE)
        lC.move_to([POS_C[0], POS_C[1] + 0.35, 0])
        lD = MathTex(r"D", font_size=28, color=TEXT_WHITE)
        lD.move_to([POS_D[0] + 0.35, POS_D[1], 0])

        vertices = VGroup(v_A, v_B, v_C, v_D, lA, lB, lC, lD)

        self.play(FadeIn(vertices), run_time=0.7)
        self.wait(0.3)

        # Edges
        # A-C: 2 parallel arcs
        e_ac1 = ArcBetweenPoints(POS_A, POS_C, angle=0.5, color=TEXT_WHITE, stroke_width=2.5)
        e_ac2 = ArcBetweenPoints(POS_A, POS_C, angle=-0.5, color=TEXT_WHITE, stroke_width=2.5)
        # B-C: 2 parallel arcs
        e_bc1 = ArcBetweenPoints(POS_B, POS_C, angle=0.5, color=TEXT_WHITE, stroke_width=2.5)
        e_bc2 = ArcBetweenPoints(POS_B, POS_C, angle=-0.5, color=TEXT_WHITE, stroke_width=2.5)
        # Single edges
        e_ad = Line(POS_A, POS_D, color=TEXT_WHITE, stroke_width=2.5)
        e_bd = Line(POS_B, POS_D, color=TEXT_WHITE, stroke_width=2.5)
        e_cd = Line(POS_C, POS_D, color=TEXT_WHITE, stroke_width=2.5)

        edges = VGroup(e_ac1, e_ac2, e_bc1, e_bc2, e_ad, e_bd, e_cd)
        self.play(FadeIn(edges), run_time=0.9)
        self.wait(0.4)

        # Counts
        count_text = Text(
            "4つの頂点と、7本の辺（うち2組は平行辺）", font=FONT, font_size=22, color=TEXT_DIM
        )
        count_text.move_to([0, -1.80, 0])
        self.play(FadeIn(count_text), run_time=0.7)

        anim_overhead = 0.5 + 0.5 + 0.7 + 0.3 + 0.9 + 0.4 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: degree
    # -------------------------------------------------------------------
    def build_degree(self):
        duration = self._duration
        highlight = self._highlight_color

        # --- Layout plan (graph left, degree table right)
        # title:       y = +3.15
        # subtitle:    y = +2.50
        # graph area:  x = [-6, 0]    (local positions, shifted from global)
        # degree table:x = [+2, +6]
        # rule:        y = -1.35
        # conclusion:  y = -1.85

        title = Text("4つの頂点、すべて奇数次数", font=FONT, font_size=28, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        subtitle = Text("── オイラー路は存在するか", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Local positions: shift graph leftward to leave room for table
        pa = [-4.8, 1.05, 0]
        pb = [-4.8, -1.05, 0]
        pc = [-3.0, 0.0, 0]
        pd = [-0.8, 0.0, 0]

        v_A = Dot(pa, color=ACCENT_CYAN, radius=0.14)
        v_B = Dot(pb, color=ACCENT_CYAN, radius=0.14)
        v_C = Dot(pc, color=ACCENT_PINK, radius=0.16)
        v_D = Dot(pd, color=ACCENT_CYAN, radius=0.14)

        lA = MathTex(r"A", font_size=24, color=TEXT_WHITE)
        lA.move_to([pa[0] - 0.3, pa[1], 0])
        lB = MathTex(r"B", font_size=24, color=TEXT_WHITE)
        lB.move_to([pb[0] - 0.3, pb[1], 0])
        lC = MathTex(r"C", font_size=24, color=TEXT_WHITE)
        lC.move_to([pc[0], pc[1] + 0.30, 0])
        lD = MathTex(r"D", font_size=24, color=TEXT_WHITE)
        lD.move_to([pd[0] + 0.30, pd[1], 0])

        e_ac1 = ArcBetweenPoints(pa, pc, angle=0.5, color=TEXT_DIM, stroke_width=2.0)
        e_ac2 = ArcBetweenPoints(pa, pc, angle=-0.5, color=TEXT_DIM, stroke_width=2.0)
        e_bc1 = ArcBetweenPoints(pb, pc, angle=0.5, color=TEXT_DIM, stroke_width=2.0)
        e_bc2 = ArcBetweenPoints(pb, pc, angle=-0.5, color=TEXT_DIM, stroke_width=2.0)
        e_ad = Line(pa, pd, color=TEXT_DIM, stroke_width=2.0)
        e_bd = Line(pb, pd, color=TEXT_DIM, stroke_width=2.0)
        e_cd = Line(pc, pd, color=TEXT_DIM, stroke_width=2.0)

        graph = VGroup(
            e_ac1,
            e_ac2,
            e_bc1,
            e_bc2,
            e_ad,
            e_bd,
            e_cd,
            v_A,
            v_B,
            v_C,
            v_D,
            lA,
            lB,
            lC,
            lD,
        )
        self.play(FadeIn(graph), run_time=0.7)
        self.wait(0.3)

        # Degree table on the right (table_x around x=+3.8)
        table_x = 3.8
        table_header = Text("次数", font=FONT, font_size=24, color=TEXT_DIM)
        table_header.move_to([table_x, 1.40, 0])

        rows_data = [
            ("A", 3, ACCENT_GOLD, 0.80),
            ("B", 3, ACCENT_GOLD, 0.30),
            ("C", 5, ACCENT_PINK, -0.20),
            ("D", 3, ACCENT_GOLD, -0.75),
        ]
        row_mobjects = VGroup()
        for name, deg, color, y in rows_data:
            row = MathTex(f"{name} = {deg}", font_size=28, color=color)
            row.move_to([table_x, y, 0])
            row_mobjects.add(row)

        self.play(FadeIn(table_header), run_time=0.4)
        self.play(FadeIn(row_mobjects), run_time=0.9)
        self.wait(0.5)

        # Necessary condition rule
        rule = Text(
            "オイラー路の存在条件：奇数次数の頂点は0個または2個",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        rule.move_to([0, -1.30, 0])

        self.play(FadeIn(rule), run_time=0.7)
        self.wait(0.4)

        # Conclusion (safe zone: bottom >= -2.0, no box for vertical space)
        conclusion = Text(
            "4つすべて奇数 → オイラー路は存在しない", font=FONT, font_size=24, color=highlight
        )
        conclusion.move_to([0, -1.80, 0])

        self.play(FadeIn(conclusion), run_time=0.8)

        anim_overhead = 0.5 + 0.5 + 0.7 + 0.3 + 0.4 + 0.9 + 0.5 + 0.7 + 0.4 + 0.8
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "map": {"people": [["オイラー", "Euler"]], "years": ["1736"]},
    "abstract": {"people": [["オイラー", "Euler"]], "years": []},
    "degree": {"people": [["オイラー", "Euler"]], "years": []},
}


SCENES = {
    "map": {
        "class": "KonigsbergBridges",
        "params": {"mode": "map"},
        "description": "18th-century schematic: Pregel river, 4 landmasses, 7 bridges",
    },
    "abstract": {
        "class": "KonigsbergBridges",
        "params": {"mode": "abstract"},
        "description": "Abstraction to multigraph: landmass → vertex, bridge → edge",
    },
    "degree": {
        "class": "KonigsbergBridges",
        "params": {"mode": "degree"},
        "description": "Degree count (3,3,5,3) all odd → no Eulerian path",
    },
}
