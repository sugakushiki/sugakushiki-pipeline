"""
heptadecagon_construction.py — 正17角形のコンパス・定規作図 for 数学史記

2000年以上誰も成し遂げなかった正17角形の作図可能性を18歳のガウスが証明。
フェルマー素数との関係を可視化。

Modes:
    circle_and_polygon - 単位円上に正17角形の頂点を配置しアニメーション描画。
                         17頂点を順番にプロットし辺で結ぶ。
                         比較として正3,5角形も薄く表示。
    fermat_condition   - 作図可能条件 n = 2^k × (異なるフェルマー素数の積) を可視化。
                         既知のフェルマー素数 3,5,17,257,65537 を表示。
                         n=3,4,5,...,20 で作図可/不可をハイライト。

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 010 (Gauss)
"""

import math

from manim import (
    DOWN,
    UP,
    Circle,
    Create,
    Dot,
    FadeIn,
    FadeOut,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _regular_polygon_vertices(n, radius=2.0, center=(0, 0), start_angle=math.pi / 2):
    """Return list of (x, y, 0) for a regular n-gon."""
    cx, cy = center
    return [
        (
            cx + radius * math.cos(start_angle + 2 * math.pi * k / n),
            cy + radius * math.sin(start_angle + 2 * math.pi * k / n),
            0,
        )
        for k in range(n)
    ]


class HeptadecagonConstruction(Scene):
    """Regular 17-gon construction and Fermat prime condition."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "circle_and_polygon")
        self._duration = params.get("duration", 18)

        if mode == "fermat_condition":
            self._build_fermat_condition()
        else:
            self._build_circle_and_polygon()

    # ------------------------------------------------------------------
    # Mode A: circle_and_polygon
    # ------------------------------------------------------------------
    def _build_circle_and_polygon(self):
        duration = self._duration

        title = Text(
            "正17角形 ── 2000年の壁を破る",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)

        # Unit circle (center raised to keep bottom above year_label at y=-1.7)
        circle = Circle(radius=1.7, color=TEXT_DIM, stroke_width=2)
        circle.move_to([0, 0.8, 0])

        anim_time = 0.8 + 0.8 + 0.6 + 17 * 0.08 + 0.8 + 0.8
        default_waits = 1.0 + 0.8 + 1.0 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.8)
        self.play(Create(circle), run_time=0.8)
        self.wait(0.5 * ws)

        # Ghost: regular pentagon (dim) for comparison
        pent_verts = _regular_polygon_vertices(5, radius=1.7, center=(0, 0.8))
        pent_poly = Polygon(
            *pent_verts,
            color=TEXT_DIM,
            stroke_width=1,
            stroke_opacity=0.3,
        )
        pent_label = Text("正5角形", font=FONT, font_size=16, color=TEXT_DIM)
        pent_label.move_to([3.5, 2.5, 0])

        self.play(FadeIn(pent_poly, run_time=0.3), FadeIn(pent_label, run_time=0.3))
        self.wait(0.3 * ws)

        # Now build the 17-gon
        verts_17 = _regular_polygon_vertices(17, radius=1.7, center=(0, 0.8))
        dots = VGroup()
        for v in verts_17:
            d = Dot(v, color=ACCENT_CYAN, radius=0.06)
            dots.add(d)
            self.play(FadeIn(d), run_time=0.08)

        self.wait(0.4 * ws)

        # Draw edges
        edges = VGroup()
        for i in range(17):
            edge = Line(
                verts_17[i],
                verts_17[(i + 1) % 17],
                color=ACCENT_CYAN,
                stroke_width=2,
            )
            edges.add(edge)
        self.play(FadeIn(edges), run_time=0.8)
        self.wait(0.5 * ws)

        # Fade out pentagon
        self.play(FadeOut(pent_poly), FadeOut(pent_label), run_time=0.4)

        # Label
        label_17 = Text(
            "正17角形",
            font=FONT,
            font_size=28,
            color=ACCENT_CYAN,
        )
        label_17.move_to([3.8, 2.5, 0])

        year_label = Text(
            "1796年3月30日  ガウス（18歳）",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        year_label.move_to([0, -1.7, 0])

        self.play(FadeIn(label_17), FadeIn(year_label), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode B: fermat_condition
    # ------------------------------------------------------------------
    def _build_fermat_condition(self):
        duration = self._duration

        title = Text(
            "作図可能な正多角形の条件",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 5 * 0.5 + 0.8 + 0.8
        default_waits = 5 * 0.5 + 1.5 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Gauss-Wantzel theorem
        theorem = MathTex(
            r"n = 2^k \times p_1 \times p_2 \times \cdots \times p_t",
            font_size=38,
            color=TEXT_WHITE,
        )
        theorem.move_to([0, 1.8, 0])

        condition_note = Text(
            "pi は互いに異なるフェルマー素数",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        condition_note.next_to(theorem, DOWN, buff=0.25)

        self.play(FadeIn(theorem), FadeIn(condition_note), run_time=0.8)
        self.wait(0.8 * ws)

        # Fermat primes
        fermat_primes = [3, 5, 17, 257, 65537]
        fermat_formulas = [
            r"2^{2^0}+1=3",
            r"2^{2^1}+1=5",
            r"2^{2^2}+1=17",
            r"2^{2^3}+1=257",
            r"2^{2^4}+1=65537",
        ]

        fp_title = Text(
            "既知のフェルマー素数（5つのみ）",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        fp_title.move_to([-3.0, 0.5, 0])
        self.play(FadeIn(fp_title), run_time=0.4)

        fp_group = VGroup()
        for i, formula in enumerate(fermat_formulas):
            tex = MathTex(formula, font_size=28, color=ACCENT_CYAN)
            tex.move_to([-3.0, 0.0 - i * 0.45, 0])
            fp_group.add(tex)
            self.play(FadeIn(tex), run_time=0.35)
            self.wait(0.15 * ws)

        self.wait(0.5 * ws)

        # n = 3..20 grid: constructible or not
        grid_title = Text(
            "n = 3 ~ 20",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        grid_title.move_to([3.5, 0.5, 0])
        self.play(FadeIn(grid_title), run_time=0.3)

        constructible = {3, 4, 5, 6, 8, 10, 12, 15, 16, 17, 20}
        grid = VGroup()
        for i, n in enumerate(range(3, 21)):
            row = i // 6
            col = i % 6
            x = 1.8 + col * 0.7
            y = -0.0 - row * 0.6
            color = ACCENT_GOLD if n in constructible else ACCENT_PINK
            opacity = 1.0 if n in constructible else 0.4
            t = Text(str(n), font=FONT, font_size=22, color=color, opacity=opacity)
            t.move_to([x, y, 0])
            grid.add(t)

        self.play(FadeIn(grid), run_time=0.8)
        self.wait(0.5 * ws)

        # Highlight 17
        highlight_note = Text(
            "17はフェルマー素数 ── 作図可能",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        highlight_note.move_to([0, -1.7, 0])
        self.play(FadeIn(highlight_note), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))


# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "circle_and_polygon": {
        "people": [["ガウス", "Gauss"]],
        "years": ["1796"],
    },
    "fermat_condition": {"people": [], "years": []},
}


SCENES = {
    "circle_and_polygon": HeptadecagonConstruction,
    "fermat_condition": HeptadecagonConstruction,
}
