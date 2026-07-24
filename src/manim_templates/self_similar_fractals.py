"""
self_similar_fractals.py - Self-similarity and the fractional dimension

Episode 042 (Mandelbrot), block 4 (pillar 2). A fractal's parts are scaled
copies of the whole. The Koch snowflake has finite area but infinite perimeter
and dimension log4/log3 ~ 1.26; the Sierpinski triangle is three half-size
copies of itself, dimension log3/log2 ~ 1.585. The dimension is D = log N / log s
for a shape made of N copies each scaled by 1/s. (The notion of dimension goes
back to Hausdorff, 1918; the "monster" curves predate Mandelbrot -- credited in
the narration, not on screen.)

Modes:
    koch (default)
        A Koch snowflake grows from a triangle (depth 0) to depth 4. A side
        panel notes perimeter x4/3 each step (-> infinity), finite area, and
        dimension log4/log3 ~ 1.2619.
        Fixed params: depths 0..4; perimeter factor 4/3; D = log4/log3.
    sierpinski
        The Sierpinski triangle is built depth 0..5 by removing middle
        triangles; three 1/2-copies; dimension log3/log2 ~ 1.585.
        Fixed params: depths 0..5; 3 copies scaled 1/2; D = log3/log2.
    dimension
        Counting argument D = log N / log s for: line (N=2, s=2 -> D=1),
        square (N=4, s=2 -> D=2), Koch (N=4, s=3 -> D~1.26).
        Fixed params: three rows; formula D = log N / log s.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.6 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    Create,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Polygon,
    Scene,
    Square,
    Text,
    Transform,
    VGroup,
    VMobject,
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


def _koch(p0, p1, depth):
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    if depth == 0:
        return [p0]
    a = p0 + (p1 - p0) / 3.0
    b = p0 + 2.0 * (p1 - p0) / 3.0
    d = b - a
    ang = math.pi / 3.0
    rot = np.array(
        [
            d[0] * math.cos(ang) - d[1] * math.sin(ang),
            d[0] * math.sin(ang) + d[1] * math.cos(ang),
            0.0,
        ]
    )
    peak = a + rot
    return (
        _koch(p0, a, depth - 1)
        + _koch(a, peak, depth - 1)
        + _koch(peak, b, depth - 1)
        + _koch(b, p1, depth - 1)
    )


def _koch_snowflake(center, radius, depth):
    cx, cy = center[0], center[1]
    verts = [
        np.array(
            [
                cx + radius * math.cos(math.pi / 2 + k * 2 * math.pi / 3),
                cy + radius * math.sin(math.pi / 2 + k * 2 * math.pi / 3),
                0.0,
            ]
        )
        for k in range(3)
    ]
    pts = []
    for i in range(3):
        pts += _koch(verts[i], verts[(i + 1) % 3], depth)
    pts.append(pts[0])
    return pts


def _snowflake_mob(center, radius, depth, color):
    m = VMobject()
    m.set_points_as_corners(_koch_snowflake(center, radius, depth))
    m.set_stroke(color=color, width=3.0)
    return m


def _sierpinski(a, b, c, depth):
    if depth == 0:
        return [(a, b, c)]
    ab = (a + b) / 2.0
    bc = (b + c) / 2.0
    ca = (c + a) / 2.0
    return (
        _sierpinski(a, ab, ca, depth - 1)
        + _sierpinski(ab, b, bc, depth - 1)
        + _sierpinski(ca, bc, c, depth - 1)
    )


def _sierpinski_mob(a, b, c, depth, color):
    tris = _sierpinski(np.array(a, float), np.array(b, float), np.array(c, float), depth)
    g = VGroup()
    for t in tris:
        g.add(Polygon(*t, color=color, stroke_width=1.4, fill_color=color, fill_opacity=0.55))
    return g


class SelfSimilarFractals(Scene):
    """Self-similar fractals and fractional dimension - three modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "koch")
        duration = float(params.get("duration", 26))
        if mode == "sierpinski":
            self._build_sierpinski(duration)
        elif mode == "dimension":
            self._build_dimension(duration)
        else:
            self._build_koch(duration)

    # -------------------------------------------------------------------- koch
    def _build_koch(self, duration):
        title = Text(
            "コッホ雪片 ── 有限の面積、無限の周", font=FONT, font_size=28, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        center = [-1.4, 0.25]
        radius = 1.7
        flake = _snowflake_mob(center, radius, 0, ACCENT_CYAN)
        self.play(Create(flake), run_time=0.9)

        panel = VGroup(
            Text("各辺を 4 つに折る", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("周の長さ ×4/3 ずつ", font=FONT, font_size=22, color=ACCENT_PINK),
            Text("→ 限りなく長く", font=FONT, font_size=22, color=ACCENT_PINK),
            Text("面積は有限のまま", font=FONT, font_size=22, color=ACCENT_CYAN),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
        panel.move_to([3.4, 0.7, 0])
        dim = MathTex(r"D = \frac{\log 4}{\log 3} \approx 1.2619", font_size=30, color=ACCENT_GOLD)
        dim.move_to([3.4, -1.2, 0])

        used = 0.7 + 0.9
        coda = 2.4
        body = max(3.0, duration - used - coda)
        steps = 4
        per = body / (steps + len(panel) + 1)

        for line in panel:
            self.play(FadeIn(line), run_time=per * 0.6)

        for d in range(1, steps + 1):
            nxt = _snowflake_mob(center, radius, d, ACCENT_CYAN)
            self.play(Transform(flake, nxt), run_time=per)

        self.play(FadeIn(dim), run_time=per)
        self.wait(coda)

    # ------------------------------------------------------------- sierpinski
    def _build_sierpinski(self, duration):
        title = Text(
            "シェルピンスキーの三角形 ── 3つの自分自身", font=FONT, font_size=26, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        a = [-1.5, -1.35, 0]
        b = [1.5, -1.35, 0]
        c = [0.0, 1.25, 0]
        cur = _sierpinski_mob(a, b, c, 0, ACCENT_GOLD)
        cur.shift(LEFT * 1.6)
        self.play(FadeIn(cur), run_time=0.7)

        panel = VGroup(
            Text("中央を抜く", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("3 つの 1/2 コピー", font=FONT, font_size=22, color=ACCENT_PINK),
            Text("が、また同じ形", font=FONT, font_size=22, color=ACCENT_PINK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        panel.move_to([3.5, 0.9, 0])
        dim = MathTex(r"D = \frac{\log 3}{\log 2} \approx 1.585", font_size=30, color=ACCENT_GOLD)
        dim.move_to([3.5, -0.9, 0])

        used = 0.7 + 0.7
        coda = 2.4
        body = max(3.0, duration - used - coda)
        steps = 5
        per = body / (steps + len(panel) + 1)

        for line in panel:
            self.play(FadeIn(line), run_time=per * 0.6)

        for d in range(1, steps + 1):
            nxt = _sierpinski_mob(a, b, c, d, ACCENT_GOLD)
            nxt.shift(LEFT * 1.6)
            self.play(FadeOut(cur), FadeIn(nxt), run_time=per)
            cur = nxt

        self.play(FadeIn(dim), run_time=per)
        self.wait(coda)

    # -------------------------------------------------------------- dimension
    def _build_dimension(self, duration):
        title = Text("整数でない、次元", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        formula = MathTex(r"D = \frac{\log N}{\log s}", font_size=40, color=TEXT_WHITE)
        formula.move_to([0, 2.05, 0])
        sub = Text("N 個の 1/s コピーから成る形の次元", font=FONT, font_size=20, color=TEXT_DIM)
        sub.next_to(formula, DOWN, buff=0.18)
        self.play(FadeIn(formula), FadeIn(sub), run_time=0.8)

        rows_y = [0.55, -0.55, -1.5]
        icon_x = -4.2
        rows = []

        # line: N=2, s=2 -> D=1
        ln = VGroup(
            Line(
                [icon_x - 0.6, rows_y[0], 0],
                [icon_x, rows_y[0], 0],
                color=ACCENT_CYAN,
                stroke_width=5,
            ),
            Line(
                [icon_x, rows_y[0], 0],
                [icon_x + 0.6, rows_y[0], 0],
                color=ACCENT_PINK,
                stroke_width=5,
            ),
        )
        rows.append((ln, "直線", r"N=2,\ s=2", r"D = \tfrac{\log 2}{\log 2} = 1"))

        # square: N=4, s=2 -> D=2
        sq = VGroup()
        for ix in range(2):
            for iy in range(2):
                cell = Square(
                    side_length=0.34,
                    color=(ACCENT_CYAN if (ix + iy) % 2 == 0 else ACCENT_PINK),
                    stroke_width=3,
                    fill_opacity=0.25,
                )
                cell.move_to([icon_x - 0.17 + ix * 0.34, rows_y[1] - 0.17 + iy * 0.34, 0])
                sq.add(cell)
        rows.append((sq, "正方形", r"N=4,\ s=2", r"D = \tfrac{\log 4}{\log 2} = 2"))

        # koch: N=4, s=3 -> D~1.26
        kc = VMobject()
        kc.set_points_as_corners(
            _koch([icon_x - 0.7, rows_y[2], 0], [icon_x + 0.7, rows_y[2], 0], 2)
        )
        kc.set_stroke(color=ACCENT_GOLD, width=3.5)
        rows.append((kc, "コッホ", r"N=4,\ s=3", r"D = \tfrac{\log 4}{\log 3} \approx 1.26"))

        used = 0.7 + 0.8
        coda = 2.4
        body = max(3.0, duration - used - coda)
        per = body / (len(rows) * 2 + 1)

        for icon, name, ns, deq in rows:
            y = icon.get_center()[1]
            name_t = Text(name, font=FONT, font_size=22, color=TEXT_WHITE)
            name_t.move_to([-2.5, y, 0])
            ns_t = MathTex(ns, font_size=26, color=TEXT_DIM)
            ns_t.move_to([-0.6, y, 0])
            d_t = MathTex(deq, font_size=28, color=ACCENT_GOLD)
            d_t.move_to([2.7, y, 0])
            self.play(FadeIn(icon), FadeIn(name_t), run_time=per)
            self.play(FadeIn(ns_t), FadeIn(d_t), run_time=per)

        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "koch": {"people": [], "years": []},
    "sierpinski": {"people": [], "years": []},
    "dimension": {"people": [], "years": []},
}

SCENES = {
    "koch": SelfSimilarFractals,
    "sierpinski": SelfSimilarFractals,
    "dimension": SelfSimilarFractals,
}
