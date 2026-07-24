"""
cubic_resolution.py - 三次方程式の解法をめぐる継承と確執 (数学史記)

カルダノ回 の数学的主軸。三次方程式 x^3+px=q の解法が
デル・フェロ → タルタリア → カルダノ と受け継がれ、『アルス・マグナ』(1545)
で公刊されるまでの優先権ドラマを可視化する。「発見=デル・フェロ、公刊=カルダノ」
を明示し、「カルダノが発見した」という誤解を視覚的に避ける。

Modes:
    timeline  - 解法の継承を横方向の年表で示す。4ノード
                (デル・フェロ=16世紀初頭/発見・秘匿、タルタリア=1535/独自に再発見、
                 カルダノ=1539・1543/誓いの下で入手→遺稿で先行発見を確認、
                 アルス・マグナ=1545/公刊)。下部に「発見=デル・フェロ／公刊=カルダノ」。
                Fixed params: 4 nodes, years 1535/1539/1543/1545.
    geometric - カルダノの幾何学的発想。x^3+px=q を「立方体 x^3 ＋ 角柱 p*x ＝ q」の
                体積として示し、解法の核となる恒等式
                (u-v)^3 + 3uv(u-v) = u^3 - v^3、3uv=p・u^3-v^3=q、
                および根号による解の形を段階表示する。2D の cabinet 投影で軽量化。
                Fixed params: equation x^3+px=q, substitution x=u-v.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 039 (Cardano), math pillar (cubic equation drama).
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    Arrow,
    Dot,
    FadeIn,
    Indicate,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _box(w, h, d, fbl, color, fill=0.22):
    """Three visible faces of a box in cabinet projection.

    fbl: front-bottom-left corner as a 3-vector (z stays 0).
    Returns VGroup(top, right, front) so the front face draws on top.
    """
    fbl = np.array(fbl, dtype=float)
    dvec = np.array([0.34 * d, 0.30 * d, 0.0])
    fbr = fbl + np.array([w, 0, 0])
    ftr = fbl + np.array([w, h, 0])
    ftl = fbl + np.array([0, h, 0])
    btr = ftr + dvec
    btl = ftl + dvec
    bbr = fbr + dvec

    front = Polygon(
        fbl,
        fbr,
        ftr,
        ftl,
        stroke_color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=fill,
    )
    top = Polygon(
        ftl,
        ftr,
        btr,
        btl,
        stroke_color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=fill * 0.6,
    )
    right = Polygon(
        fbr,
        ftr,
        btr,
        bbr,
        stroke_color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=fill * 0.4,
    )
    return VGroup(top, right, front)


class CubicResolution(Scene):
    """三次方程式の解法ドラマ — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "timeline")
        self._duration = params.get("duration", 28)

        if mode == "geometric":
            self._build_geometric()
        else:
            self._build_timeline()

    # ------------------------------------------------------------------
    # Mode: timeline
    # ------------------------------------------------------------------
    def _build_timeline(self):
        duration = self._duration

        title = Text(
            "三次方程式の解法 ── 受け継がれた秘伝",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.7)

        line_y = 0.55
        axis = Line([-5.6, line_y, 0], [5.6, line_y, 0], color=EDGE_COLOR, stroke_width=2)
        self.play(FadeIn(axis), run_time=0.5)

        # node: (name, name_color, year_text, year_is_math, role)
        nodes = [
            ("デル・フェロ", ACCENT_CYAN, "16世紀初頭", False, "発見し秘匿"),
            ("タルタリア", ACCENT_GOLD, "1535", True, "独自に再発見"),
            ("カルダノ", TEXT_WHITE, "1539 / 1543", True, "誓いの下で入手\n→ 遺稿で先行を確認"),
            ("アルス・マグナ", ACCENT_PINK, "1545", True, "公刊"),
        ]
        xs = [-4.5, -1.5, 1.5, 4.5]

        dots, groups = [], []
        for (name, ncol, year, is_math, role), x in zip(nodes, xs, strict=False):
            dot = Dot([x, line_y, 0], radius=0.08, color=ncol)
            dots.append(dot)

            if is_math:
                year_m = MathTex(year, font_size=30, color=TEXT_DIM)
            else:
                year_m = Text(year, font=FONT, font_size=22, color=TEXT_DIM)
            year_m.move_to([x, 1.55, 0])

            name_t = Text(name, font=FONT, font_size=23, color=ncol)
            name_t.move_to([x, -0.15, 0])

            role_t = Text(
                role, font=FONT, font_size=16, color=TEXT_WHITE, line_spacing=0.7
            ).set_opacity(0.8)
            role_t.move_to([x, -0.95, 0])

            groups.append(VGroup(year_m, name_t, role_t))

        arrows = []
        for i in range(3):
            arr = Arrow(
                [xs[i] + 0.55, line_y, 0],
                [xs[i + 1] - 0.55, line_y, 0],
                buff=0,
                stroke_width=2.5,
                color=TEXT_DIM,
                max_tip_length_to_length_ratio=0.18,
            ).set_opacity(0.6)
            arrows.append(arr)

        n = len(nodes)
        anim_time = 0.7 + 0.5 + n * 0.7 + 3 * 0.4 + 1.0
        default_waits = n * 0.9 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for i in range(n):
            anims = [FadeIn(dots[i]), FadeIn(groups[i])]
            if i > 0:
                anims.append(FadeIn(arrows[i - 1]))
            self.play(*anims, run_time=0.7)
            self.wait(0.9 * ws)

        # Bottom banner: 発見=デル・フェロ ／ 公刊=カルダノ
        banner = VGroup(
            Text("発見 ＝ ", font=FONT, font_size=24, color=TEXT_WHITE),
            Text("デル・フェロ", font=FONT, font_size=24, color=ACCENT_CYAN),
            Text("　／　公刊 ＝ ", font=FONT, font_size=24, color=TEXT_WHITE),
            Text("カルダノ", font=FONT, font_size=24, color=ACCENT_PINK),
        ).arrange(RIGHT, buff=0.08)
        banner.move_to([0, -1.8, 0])
        self.play(FadeIn(banner), run_time=0.7)
        self.play(Indicate(dots[0], color=ACCENT_CYAN, scale_factor=1.6), run_time=0.5)
        self.wait(max(1.0, duration - anim_time - n * 0.9 * ws))

    # ------------------------------------------------------------------
    # Mode: geometric
    # ------------------------------------------------------------------
    def _build_geometric(self):
        duration = self._duration

        title = Text(
            "立体としての三次方程式",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        eq = MathTex(r"x^3 + p\,x = q", font_size=40, color=TEXT_WHITE)
        eq.move_to([0, 2.35, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(eq), run_time=0.6)

        # Left third: cube (x^3) + slab (p*x) illustrate the two volumes.
        cube = _box(1.15, 1.15, 1.15, [-5.5, -0.15, 0], ACCENT_CYAN)
        cube_lbl = MathTex(r"x^3", font_size=30, color=ACCENT_CYAN)
        cube_lbl.move_to([-4.92, 0.42, 0])

        plus = MathTex(r"+", font_size=40, color=TEXT_WHITE)
        plus.move_to([-3.65, 0.35, 0])

        slab = _box(1.2, 0.4, 1.15, [-3.25, 0.15, 0], ACCENT_GOLD)
        slab_lbl = MathTex(r"p\,x", font_size=28, color=ACCENT_GOLD)
        slab_lbl.move_to([-2.55, 1.05, 0])

        vol_cap = Text("二つの体積の和が q", font=FONT, font_size=18, color=TEXT_DIM)
        vol_cap.move_to([-3.45, -1.4, 0])

        self.play(FadeIn(cube), FadeIn(cube_lbl), run_time=0.8)
        self.play(FadeIn(plus), FadeIn(slab), FadeIn(slab_lbl), run_time=0.8)
        self.play(FadeIn(vol_cap), run_time=0.5)

        # Right: the algebraic heart of del Ferro / Cardano's method.
        steps = VGroup(
            MathTex(r"x = u - v", font_size=32, color=ACCENT_CYAN),
            MathTex(r"(u-v)^3 + 3uv(u-v) = u^3 - v^3", font_size=28, color=TEXT_WHITE),
            MathTex(r"3uv = p,\quad u^3 - v^3 = q", font_size=28, color=ACCENT_GOLD),
            MathTex(
                r"x = \sqrt[3]{\tfrac{q}{2}+\sqrt{\left(\tfrac{q}{2}\right)^2+\left(\tfrac{p}{3}\right)^3}}"
                r"-\sqrt[3]{-\tfrac{q}{2}+\sqrt{\left(\tfrac{q}{2}\right)^2+\left(\tfrac{p}{3}\right)^3}}",
                font_size=24,
                color=ACCENT_PINK,
            ),
        )
        steps.arrange(DOWN, buff=0.42, aligned_edge=LEFT)
        for s in steps:
            if s.width > 5.6:
                s.scale_to_fit_width(5.6)
        steps.move_to([3.3, 0.25, 0])

        anim_time = 0.6 + 0.6 + 0.8 + 0.8 + 0.5 + 4 * 0.7
        default_waits = 4 * 0.9 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for s in steps:
            self.play(FadeIn(s), run_time=0.7)
            self.wait(0.9 * ws)

        self.wait(max(1.0, duration - anim_time - 4 * 0.9 * ws))


# Factual-claim metadata (read by qa_manim_consistency.py).
# timeline displays surnames + the publication-chain years; geometric is
# pure math with no on-screen person/year claims.
LINT_FACTUAL_CLAIMS = {
    "timeline": {
        "people": [
            ["デル・フェロ", "del Ferro", "フェロ"],
            ["タルタリア", "Tartaglia"],
            ["カルダノ", "Cardano"],
        ],
        "years": ["1535", "1539", "1543", "1545"],
    },
    "geometric": {"people": [], "years": []},
}


SCENES = {
    "timeline": CubicResolution,
    "geometric": CubicResolution,
}
