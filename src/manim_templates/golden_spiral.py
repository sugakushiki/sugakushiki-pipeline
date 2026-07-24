"""
golden_spiral.py - 数列の後日譚: 黄金比と自然界 (数学史記)

フィボナッチ回 の後半。有名な数列の「長い後日譚」── 隣り合う項の比が
黄金比 phi=(1+sqrt5)/2 に収束すること、フィボナッチ正方形から描かれる螺旋、
ひまわりの葉序 (黄金角での充填、実在する現象) を可視化する。さらに「オウムガイの
殻は黄金螺旋」という俗説を、実測 (比は約1.33で黄金比1.618ではない) で正直に否定する。

Modes:
    ratio_converges - 隣項比 F(n+1)/F(n) (1, 2, 1.5, 1.667, 1.6, 1.625, ...) が
                      phi≈1.618 に収束する様子を点列で示す。
                      Fixed params: fibs up to 55, phi=(1+sqrt5)/2.
    spiral          - フィボナッチ正方形 (1,1,2,3,5,8) のタイリングと、各正方形の
                      四分円をつないだフィボナッチ螺旋を描く。
                      Fixed params: squares of size 1,1,2,3,5,8.
    phyllotaxis     - 黄金角 (約137.5°) でずらして種を打つと、ひまわり型に
                      すきまなく詰まる (実在する最適充填) を点で示す。
                      Fixed params: ~210 seeds, golden angle = pi*(3-sqrt5).
    myth            - 「オウムガイ＝黄金螺旋」は俗説。黄金螺旋 (1周で約6.85倍) と
                      オウムガイ (実測 1周で約3倍 → 比 約1.33) の対数螺旋を並べ、
                      黄金比1.618ではないことを示す。
                      Fixed params: growth per turn golden 6.85x vs nautilus 3x.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 040 (Fibonacci), the sequence's afterlife (golden ratio & nature).
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    PI,
    UP,
    Arc,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    LaggedStart,
    Line,
    MathTex,
    Scene,
    Square,
    Text,
    VGroup,
    VMobject,
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

PHI = (1 + 5**0.5) / 2  # 1.6180339887...


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _lerp_color(c1, c2, t):
    """Linear interpolate two #rrggbb hex colors; return #rrggbb."""
    a = [int(c1[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i : i + 2], 16) for i in (1, 3, 5)]
    rgb = [int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _log_spiral(center, b, turns, max_r, color):
    """Logarithmic spiral r=exp(b*t), normalized so end radius == max_r."""
    center = np.array(center, dtype=float)
    ts = np.linspace(0.0, turns * 2 * PI, 180)
    rs = np.exp(b * ts)
    rs = rs / rs[-1] * max_r
    pts = [
        center + np.array([r * np.cos(t), r * np.sin(t), 0.0]) for r, t in zip(rs, ts, strict=False)
    ]
    vm = VMobject()
    vm.set_points_smoothly(pts)
    vm.set_stroke(color, width=4)
    return vm


class GoldenSpiral(Scene):
    """黄金比と自然界 — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "spiral")
        self._duration = params.get("duration", 26)

        if mode == "ratio_converges":
            self._build_ratio()
        elif mode == "phyllotaxis":
            self._build_phyllotaxis()
        elif mode == "myth":
            self._build_myth()
        else:
            self._build_spiral()

    # ------------------------------------------------------------------
    # Mode: ratio_converges
    # ------------------------------------------------------------------
    def _build_ratio(self):
        duration = self._duration

        title = Text("となりどうしの比は、黄金比へ", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.2, 0])
        self.play(FadeIn(title), run_time=0.7)

        fibs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        ratios = [fibs[i + 1] / fibs[i] for i in range(len(fibs) - 1)]

        y0, yscale = 0.2, 2.6
        x_left, x_right = -4.4, 3.0
        dx = (x_right - x_left) / (len(ratios) - 1)

        def pos(i, r):
            return np.array([x_left + i * dx, y0 + (r - 1.5) * yscale, 0])

        # phi reference line (gold dashed) + label
        y_phi = y0 + (PHI - 1.5) * yscale
        phi_line = DashedLine(
            [x_left - 0.3, y_phi, 0],
            [x_right + 0.9, y_phi, 0],
            color=ACCENT_GOLD,
            stroke_width=3,
            dash_length=0.12,
        )
        phi_label = MathTex(r"\varphi \approx 1.618", font_size=30, color=ACCENT_GOLD)
        phi_label.next_to(phi_line.get_end(), UP, buff=0.12).shift(LEFT * 0.3)

        formula = MathTex(r"\varphi=\frac{1+\sqrt{5}}{2}", font_size=34, color=TEXT_WHITE)
        formula.move_to([-4.7, 2.4, 0])

        self.play(Create(phi_line), FadeIn(phi_label), FadeIn(formula), run_time=0.9)

        anim = 0.7 + 0.9
        per = 0.5
        waits = len(ratios) * 0.45
        ws = _calc_wait_scale(duration, anim + len(ratios) * per, waits)

        prev = None
        dots = VGroup()
        for i, r in enumerate(ratios):
            p = pos(i, r)
            d = Dot(p, radius=0.07, color=ACCENT_CYAN)
            anims = [FadeIn(d)]
            if prev is not None:
                seg = Line(prev, p, color=ACCENT_CYAN, stroke_width=2)
                seg.set_opacity(0.55)
                anims.append(Create(seg))
            # value label for first and a late one
            if i in (1, len(ratios) - 1):
                lbl = MathTex(f"{r:.3f}", font_size=22, color=TEXT_DIM)
                lbl.next_to(d, UP if r > PHI else DOWN, buff=0.12)
                anims.append(FadeIn(lbl))
            self.play(*anims, run_time=per)
            self.wait(0.45 * ws)
            prev = p
            dots.add(d)

        self.wait(max(1.2, duration - anim - len(ratios) * (per + 0.45 * ws)))

    # ------------------------------------------------------------------
    # Mode: spiral
    # ------------------------------------------------------------------
    def _build_spiral(self):
        duration = self._duration

        title = Text("フィボナッチ正方形と螺旋", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.2, 0])
        self.play(FadeIn(title), run_time=0.7)

        # (x0, y0, size) lower-left corners; counterclockwise growth
        squares = [
            (0, 0, 1),
            (-1, 0, 1),
            (-1, -2, 2),
            (1, -2, 3),
            (-1, 1, 5),
            (-9, -2, 8),
        ]
        # (center, radius, start_angle, sweep) quarter-circle arcs
        arcs_p = [
            ((1, 1), 1, -PI / 2, -PI / 2),
            ((0, 0), 1, PI / 2, PI / 2),
            ((1, 0), 2, PI, PI / 2),
            ((1, 1), 3, -PI / 2, PI / 2),
            ((4, 6), 5, -PI / 2, -PI / 2),
            ((-9, 6), 8, 0, -PI / 2),
        ]

        sq_group = VGroup()
        lbl_group = VGroup()
        for x0, y0, s in squares:
            sq = Square(
                side_length=s,
                stroke_color=EDGE_COLOR,
                stroke_width=2,
                fill_color=ACCENT_CYAN,
                fill_opacity=0.05,
            )
            sq.move_to([x0 + s / 2.0, y0 + s / 2.0, 0])
            sq_group.add(sq)
            lbl = MathTex(str(s), font_size=26 + s, color=TEXT_DIM)
            lbl.move_to([x0 + s / 2.0, y0 + s / 2.0, 0])
            lbl_group.add(lbl)

        arc_group = VGroup()
        for c, r, sa, ang in arcs_p:
            arc = Arc(
                radius=r,
                start_angle=sa,
                angle=ang,
                arc_center=[c[0], c[1], 0],
                color=ACCENT_PINK,
                stroke_width=5,
            )
            arc_group.add(arc)

        whole = VGroup(sq_group, lbl_group, arc_group)
        whole.scale(0.46).move_to([0, 0.45, 0])

        anim = 0.7
        per_sq = 0.4
        per_arc = 0.45
        waits = 2.0
        ws = _calc_wait_scale(duration, anim + len(squares) * per_sq + len(arcs_p) * per_arc, waits)

        for sq, lbl in zip(sq_group, lbl_group, strict=False):
            self.play(FadeIn(sq), FadeIn(lbl), run_time=per_sq)
        self.wait(0.6 * ws)
        for arc in arc_group:
            self.play(Create(arc), run_time=per_arc)
        self.wait(
            max(1.5, duration - anim - len(squares) * per_sq - len(arcs_p) * per_arc - 0.6 * ws)
        )

    # ------------------------------------------------------------------
    # Mode: phyllotaxis
    # ------------------------------------------------------------------
    def _build_phyllotaxis(self):
        duration = self._duration

        title = Text(
            "黄金角でずらすと、すきまなく詰まる", font=FONT, font_size=28, color=ACCENT_GOLD
        )
        title.move_to([0, 3.2, 0])
        self.play(FadeIn(title), run_time=0.7)

        n = 210
        golden_angle = PI * (3 - 5**0.5)  # ~2.39996 rad = 137.5 deg
        c = 1.65 / (n**0.5)
        center = np.array([0, 0.35, 0])
        seeds = VGroup()
        for i in range(n):
            r = c * (i**0.5)
            th = i * golden_angle
            p = center + np.array([r * np.cos(th), r * np.sin(th), 0])
            col = _lerp_color(ACCENT_GOLD, ACCENT_CYAN, i / (n - 1))
            seeds.add(Dot(p, radius=0.05, color=col))

        angle_lbl = MathTex(r"\approx 137.5^{\circ}", font_size=30, color=ACCENT_PINK)
        angle_lbl.move_to([4.6, 2.4, 0])
        caption = Text(
            "ひまわりの種の並び ── 実在する数学", font=FONT, font_size=22, color=TEXT_DIM
        )
        caption.move_to([0, -1.75, 0])

        anim = 0.7 + 2.6 + 0.6 + 0.6
        ws = _calc_wait_scale(duration, anim, 2.0)

        self.play(LaggedStart(*[FadeIn(s) for s in seeds], lag_ratio=0.012), run_time=2.6)
        self.play(FadeIn(angle_lbl), run_time=0.6)
        self.wait(1.0 * ws)
        self.play(FadeIn(caption), run_time=0.6)
        self.wait(max(1.5, duration - anim - 1.0 * ws))

    # ------------------------------------------------------------------
    # Mode: myth
    # ------------------------------------------------------------------
    def _build_myth(self):
        duration = self._duration

        title = Text("『オウムガイ＝黄金螺旋』は、俗説", font=FONT, font_size=30, color=ACCENT_PINK)
        title.move_to([0, 3.2, 0])
        self.play(FadeIn(title), run_time=0.7)

        # golden spiral: ~6.85x per turn -> b = ln(6.854)/(2pi)
        b_gold = np.log(6.854) / (2 * PI)
        # nautilus: ~3x per turn -> b = ln(3)/(2pi)
        b_naut = np.log(3.0) / (2 * PI)

        sp_gold = _log_spiral([-3.3, 0.55, 0], b_gold, 2.3, 1.25, ACCENT_GOLD)
        sp_naut = _log_spiral([3.3, 0.55, 0], b_naut, 2.3, 1.25, ACCENT_CYAN)

        lab_gold = VGroup(
            Text("黄金螺旋", font=FONT, font_size=24, color=ACCENT_GOLD),
            Text("1周で約6.85倍", font=FONT, font_size=20, color=TEXT_DIM),
        ).arrange(DOWN, buff=0.12)
        lab_gold.move_to([-3.3, -1.35, 0])

        lab_naut = VGroup(
            Text("オウムガイ（実測）", font=FONT, font_size=24, color=ACCENT_CYAN),
            Text("1周で約3倍 → 比 約1.33", font=FONT, font_size=20, color=TEXT_DIM),
        ).arrange(DOWN, buff=0.12)
        lab_naut.move_to([3.3, -1.35, 0])

        note = Text(
            "黄金比は 1.618 ── 殻の比は約1.33で、別物です",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        note.move_to([0, 2.45, 0])

        anim = 0.7 + 1.1 + 1.1 + 0.6 + 0.6 + 0.6
        ws = _calc_wait_scale(duration, anim, 2.5)

        self.play(FadeIn(note), run_time=0.6)
        self.play(Create(sp_gold), run_time=1.1)
        self.play(FadeIn(lab_gold), run_time=0.6)
        self.wait(0.8 * ws)
        self.play(Create(sp_naut), run_time=1.1)
        self.play(FadeIn(lab_naut), run_time=0.6)
        self.wait(max(1.5, duration - anim - 0.8 * ws))


# Factual-claim metadata (read by qa_manim_consistency.py).
# On-screen numbers are ratios / phi / angles / Fibonacci values, not years;
# no person names appear. All modes explicitly empty.
LINT_FACTUAL_CLAIMS = {
    "ratio_converges": {"people": [], "years": []},
    "spiral": {"people": [], "years": []},
    "phyllotaxis": {"people": [], "years": []},
    "myth": {"people": [], "years": []},
}


SCENES = {
    "ratio_converges": GoldenSpiral,
    "spiral": GoldenSpiral,
    "phyllotaxis": GoldenSpiral,
    "myth": GoldenSpiral,
}
