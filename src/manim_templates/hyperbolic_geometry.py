"""
hyperbolic_geometry.py - Doubting the one line, and the world it opened

Episode 045 (Nikolai Lobachevsky). Intuition-level visuals for Euclid's fifth
postulate, the radical move of denying it, and the hyperbolic world that appears.
No proofs, no rigorous definitions -- wonder and intuition only.

Modes:
    fifth_postulate (default)
        Euclid's four short postulates on the left vs the one long, complex fifth
        (the parallel postulate) on the right. Point: four are obvious and brief,
        only the fifth is long -- and for 2000 years no one could prove it.
        Fixed params: four short rule rows; one long fifth-postulate paraphrase.
        On screen: name Euclid (ユークリッド).
    parallels
        Deny the fifth postulate. Through one point P above a line, Euclid allows
        exactly one parallel (cyan); Lobachevsky allows infinitely many lines that
        never meet the line (a gold fan). Angle of parallelism is narrated.
        Fixed params: base line at y=-0.6; point P at (0,1.3); 7 lines through P
        with slopes 0, +/-0.15, +/-0.3, +/-0.45 (slope-0 = cyan Euclid parallel).
    triangle
        A geodesic triangle in the Poincare disk (a later map): its three sides bow
        inward, so the angle sum is < 180 degrees; the larger the triangle, the
        bigger the defect -- the defect is proportional to area.
        Fixed params: disk center (0,0.4) radius 2.0; triangle vertices at radius
        1.4, angles 90/210/330 deg; a second, larger triangle to show growing defect.
        On screen: name Poincare (ポアンカレ).

All Text uses FONT (BIZ UDMincho). No MathTex, no Japanese-in-LaTeX risk.
Y range: about -1.9 to +3.05. No trailing FadeOut.
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    ArcBetweenPoints,
    Circle,
    Create,
    DashedVMobject,
    Dot,
    FadeIn,
    Indicate,
    Line,
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


def _geodesic_arc(a, b, center, mag=0.85, color=ACCENT_GOLD, width=4):
    """An arc from a to b that bulges toward `center` (a Poincare-disk geodesic)."""
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(center, dtype=float)
    d = b - a
    mid = (a + b) / 2.0
    left_normal = np.array([-d[1], d[0], 0.0])
    # Bulge TOWARD `center` so the sides bow inward (hyperbolic, angle sum < 180).
    # ArcBetweenPoints(+angle) bows to the right of a->b, so flip against left_normal.
    sign = -1.0 if float(np.dot(left_normal, c - mid)) > 0 else 1.0
    arc = ArcBetweenPoints(a, b, angle=sign * mag)
    arc.set_stroke(color, width)
    return arc


class HyperbolicGeometry(Scene):
    """Euclid's fifth postulate and the hyperbolic world -- three intuition modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "fifth_postulate")
        duration = float(params.get("duration", 26))
        if mode == "parallels":
            self._build_parallels(duration)
        elif mode == "triangle":
            self._build_triangle(duration)
        else:
            self._build_fifth_postulate(duration)

    # ---------------------------------------------------------- fifth_postulate
    def _build_fifth_postulate(self, duration):
        title = Text("ユークリッド『原論』── 5つの公準", font=FONT, font_size=27, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        head_l = Text("4つは、短い", font=FONT, font_size=22, color=ACCENT_CYAN)
        head_l.move_to([-3.6, 2.25, 0])
        shorts = [
            "1. 二点に直線を引ける",
            "2. 線分は延ばせる",
            "3. 円を描ける",
            "4. 直角はみな等しい",
        ]
        rows = VGroup()
        for i, s in enumerate(shorts):
            row = Text(s, font=FONT, font_size=19, color=TEXT_WHITE)
            row.move_to([-3.6, 1.55 - i * 0.5, 0])
            rows.add(row)

        head_r = Text("5つめだけ、長い", font=FONT, font_size=22, color=ACCENT_PINK)
        head_r.move_to([2.5, 2.25, 0])
        fifth = Text(
            "一直線が二直線に交わり、\n"
            "片側の内角の和が二直角より小さいなら、\n"
            "その二直線は延ばすと、その側で交わる",
            font=FONT,
            font_size=16,
            color=ACCENT_PINK,
            line_spacing=0.7,
        )
        fifth.move_to([2.5, 1.15, 0])

        note1 = Text(
            "他の4つから導ける定理のはず ── と誰もが信じた",
            font=FONT,
            font_size=21,
            color=TEXT_WHITE,
        )
        note1.move_to([0, -1.35, 0])
        note2 = Text(
            "だが2000年、誰もそれを導けなかった", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        note2.move_to([0, -1.78, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(FadeIn(head_l), run_time=per * 0.5)
        self.play(FadeIn(rows), run_time=per)
        self.play(FadeIn(head_r), run_time=per * 0.5)
        self.play(FadeIn(fifth), run_time=per)
        self.play(Indicate(fifth, color=ACCENT_PINK, scale_factor=1.06), run_time=per)
        self.play(FadeIn(note1), run_time=per)
        self.play(FadeIn(note2), run_time=per)
        self.wait(coda)

    # ----------------------------------------------------------------- parallels
    def _build_parallels(self, duration):
        title = Text("公準を捨てる ── 平行線は無数に", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        base = Line([-3.4, -0.6, 0], [3.4, -0.6, 0], color=ACCENT_CYAN, stroke_width=3)
        base_label = Text("もとの直線", font=FONT, font_size=20, color=ACCENT_CYAN)
        base_label.next_to([3.4, -0.6, 0], RIGHT, buff=0.1)
        p = np.array([0.0, 1.3, 0.0])
        p_dot = Dot(p, color=ACCENT_GOLD, radius=0.07)
        p_label = Text("点P", font=FONT, font_size=20, color=ACCENT_GOLD)
        p_label.next_to(p, UP, buff=0.12)
        self.play(Create(base), FadeIn(base_label), run_time=0.9)
        self.play(FadeIn(p_dot), FadeIn(p_label), run_time=0.5)

        euclid_line = DashedVMobject(
            Line(p + LEFT * 3.4, p + RIGHT * 3.4, color=ACCENT_CYAN, stroke_width=3),
            num_dashes=26,
        )
        euclid_label = Text(
            "ユークリッド：平行は1本だけ", font=FONT, font_size=20, color=ACCENT_CYAN
        )
        euclid_label.move_to([0, 2.35, 0])

        slopes = [0.15, 0.30, 0.45, -0.15, -0.30, -0.45]
        fan = VGroup()
        for s in slopes:
            left_pt = p + np.array([-3.4, -3.4 * s, 0.0])
            right_pt = p + np.array([3.4, 3.4 * s, 0.0])
            fan.add(Line(left_pt, right_pt, color=ACCENT_GOLD, stroke_width=2))

        lob_label = Text(
            "ロバチェフスキー：交わらない直線が、無数に", font=FONT, font_size=21, color=ACCENT_GOLD
        )
        lob_label.move_to([0, -1.05, 0])
        note = Text("矛盾を探しても、出てこなかった", font=FONT, font_size=22, color=ACCENT_PINK)
        note.move_to([0, -1.7, 0])

        used = 0.7 + 0.9 + 0.5
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 4.0
        self.play(Create(euclid_line), FadeIn(euclid_label), run_time=per)
        self.play(Create(fan), run_time=per * 1.4)
        self.play(FadeIn(lob_label), run_time=per)
        self.play(FadeIn(note), run_time=per)
        self.wait(coda)

    # ------------------------------------------------------------------ triangle
    def _build_triangle(self, duration):
        title = Text(
            "三角形の内角の和は、180°より小さい", font=FONT, font_size=27, color=ACCENT_GOLD
        )
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        center = np.array([0.0, 0.4, 0.0])
        disk = Circle(radius=2.0, color=ACCENT_CYAN, stroke_width=2.5).move_to(center)
        disk.set_fill(ACCENT_CYAN, opacity=0.05)
        disk_label = Text(
            "ポアンカレ円板（後の世が作った地図）", font=FONT, font_size=18, color=TEXT_DIM
        )
        disk_label.move_to([0, -1.85, 0])
        self.play(Create(disk), run_time=1.0)
        self.play(FadeIn(disk_label), run_time=0.5)

        r = 1.4
        angs = [np.pi / 2, np.pi * 7 / 6, np.pi * 11 / 6]
        verts = [center + r * np.array([np.cos(a), np.sin(a), 0.0]) for a in angs]
        v_dots = VGroup(*[Dot(v, color=ACCENT_GOLD, radius=0.05) for v in verts])
        sides = VGroup(
            _geodesic_arc(verts[0], verts[1], center),
            _geodesic_arc(verts[1], verts[2], center),
            _geodesic_arc(verts[2], verts[0], center),
        )
        sum_label = Text("内角の和 ＜ 180°", font=FONT, font_size=24, color=TEXT_WHITE)
        sum_label.move_to([0, -1.35, 0])

        r2 = 1.85
        verts2 = [center + r2 * np.array([np.cos(a), np.sin(a), 0.0]) for a in angs]
        big_sides = VGroup(
            _geodesic_arc(verts2[0], verts2[1], center, mag=1.15, color=ACCENT_PINK, width=3),
            _geodesic_arc(verts2[1], verts2[2], center, mag=1.15, color=ACCENT_PINK, width=3),
            _geodesic_arc(verts2[2], verts2[0], center, mag=1.15, color=ACCENT_PINK, width=3),
        )
        defect_label = Text("大きいほど、欠損が増える", font=FONT, font_size=19, color=ACCENT_PINK)
        defect_label.move_to([4.3, 0.85, 0])
        defect_label2 = Text("＝ 欠損は面積に比例", font=FONT, font_size=19, color=ACCENT_PINK)
        defect_label2.next_to(defect_label, DOWN, buff=0.18)

        used = 0.7 + 1.0 + 0.5
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(FadeIn(v_dots), run_time=per * 0.5)
        self.play(Create(sides), run_time=per * 1.4)
        self.play(FadeIn(sum_label), run_time=per)
        self.play(Create(big_sides), run_time=per * 1.1)
        self.play(FadeIn(defect_label), run_time=per)
        self.play(FadeIn(defect_label2), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "fifth_postulate": {"people": [["ユークリッド", "Euclid"]], "years": []},
    "parallels": {
        "people": [["ロバチェフスキー", "Lobachevsky"], ["ユークリッド", "Euclid"]],
        "years": [],
    },
    "triangle": {"people": [["ポアンカレ", "Poincare"]], "years": []},
}

SCENES = {
    "fifth_postulate": HyperbolicGeometry,
    "parallels": HyperbolicGeometry,
    "triangle": HyperbolicGeometry,
}
