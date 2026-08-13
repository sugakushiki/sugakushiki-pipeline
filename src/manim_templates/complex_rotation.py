"""
complex_rotation.py - Complex multiplication as rotation in the plane (数学史記)

Motivates Hamilton's quaternions: a complex number a+bi is a "2D number"
whose multiplication acts as a rotation (and scaling) of the plane. This is
the starting point Hamilton tried to generalise to 3D rotation.

Modes:
    multiply_i  - The point z = 2 + i, drawn as a vector from the origin,
                  is multiplied by i, rotating it 90 degrees CCW to
                  i*z = -1 + 2i. "Multiplying by i is a quarter turn."
                  Fixed params: z = 2 + i, i*z = -1 + 2i.
    rotate_scale- Multiplying by a general complex number w = 1 + i
                  (magnitude sqrt(2), argument 45 deg) rotates by 45 deg
                  AND scales by sqrt(2):  z = 1.5 + 0.5i -> w*z = 1 + 2i.
                  Fixed params: w = 1+i, z = 1.5+0.5i, w*z = 1+2i.
    contour_taste- A taste of complex analysis (an earlier episode Cauchy, block 8): a
                  closed contour C drawn on the complex plane with an interior
                  singular point z_0 (a small cross), and a point running once
                  around C while the contour integral oint_C f(z) dz is named
                  but NOT evaluated (no residue mechanism - door-opener only).
                  Fixed params: contour = circle centre (0.4, 0.3) radius 1.4
                  in data units, singular point at the centre.
    residue_integral- The concrete fruit (an earlier episode Cauchy, block 8): evaluate the
                  real definite integral int_{-inf}^{inf} dx/(1+x^2) = pi by
                  residues. The plane sits on the left with the real-axis path
                  (cyan) closed by an upper semicircular arc (gold, radius 2.3
                  data units), the pole at z=i marked by a cross; a point
                  traverses the closed contour while the computation stack
                  (f(z)=1/(1+z^2); Res_{z=i}=1/(2i); oint=2*pi*i*(1/2i)=pi; arc
                  -> 0; int dx/(1+x^2)=pi) reveals on the right. One worked
                  example, mechanism illustrated not proved. The specific
                  integral is a modern illustration, NOT asserted as Cauchy's
                  own computation (hedge belongs in narration).

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 033 (Hamilton), quaternion pillar (2D motivation);
         Episode 041 (Cauchy), block 8 (contour_taste / residue_integral).
"""

import math

from manim import (
    DOWN,
    PI,
    RIGHT,
    UP,
    UR,
    Arc,
    Arrow,
    Axes,
    Circle,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
    ReplacementTransform,
    Rotate,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    linear,
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


class ComplexRotation(Scene):
    """Complex multiplication as planar rotation. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 22)
        self._highlight = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "multiply_i")

        if mode == "rotate_scale":
            self.build_rotate_scale()
        elif mode == "contour_taste":
            self.build_contour_taste()
        elif mode == "residue_integral":
            self.build_residue_integral()
        else:
            self.build_multiply_i()

    # ------------------------------------------------------------------
    def _make_axes(self):
        # Isotropic scaling (square unit cells): both axes use 0.8 screen
        # units per data unit, so a 90 deg SCREEN rotation equals "times i"
        # in DATA space and rotated vector tips land exactly on c2p() points.
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2.5, 2.5, 1],
            x_length=4.8,
            y_length=4.0,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_ticks": True,
                "include_tip": True,
            },
        )
        axes.move_to([0, 0.2, 0])
        re_label = MathTex(r"\mathrm{Re}", font_size=26, color=TEXT_DIM)
        re_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.1)
        im_label = MathTex(r"\mathrm{Im}", font_size=26, color=TEXT_DIM)
        im_label.next_to(axes.y_axis.get_end(), UP, buff=0.1)
        return axes, VGroup(re_label, im_label)

    # ------------------------------------------------------------------
    # Mode: multiply_i
    # ------------------------------------------------------------------
    def build_multiply_i(self):
        duration = self._duration

        title = Text("複素数に i を掛ける", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        subtitle = Text("── 平面を 90度 回す", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.6, 0])

        axes, axis_labels = self._make_axes()
        origin = axes.c2p(0, 0)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(axis_labels), run_time=0.7)

        # z = 2 + i
        z_pt = axes.c2p(2, 1)
        z_arrow = Arrow(origin, z_pt, buff=0, color=ACCENT_CYAN, stroke_width=5)
        z_dot = Dot(z_pt, color=ACCENT_CYAN, radius=0.07)
        z_label = MathTex(r"z = 2 + i", font_size=30, color=ACCENT_CYAN)
        z_label.next_to(z_dot, UR, buff=0.12)

        self.play(FadeIn(z_arrow), FadeIn(z_dot), FadeIn(z_label), run_time=0.7)
        self.wait(0.5)

        # Multiply by i: rotate 90 deg CCW -> -1 + 2i
        iz_pt = axes.c2p(-1, 2)
        rotating = z_arrow.copy().set_color(self._highlight)
        self.add(rotating)
        turn_label = MathTex(r"\times\, i", font_size=30, color=self._highlight)
        turn_label.move_to([2.4, 1.7, 0])
        self.play(FadeIn(turn_label), run_time=0.4)
        self.play(Rotate(rotating, angle=PI / 2, about_point=origin), run_time=2.0)

        iz_dot = Dot(iz_pt, color=self._highlight, radius=0.07)
        iz_label = MathTex(r"i\,z = -1 + 2i", font_size=30, color=self._highlight)
        iz_label.next_to(iz_dot, UP, buff=0.12)
        self.play(FadeIn(iz_dot), FadeIn(iz_label), run_time=0.6)

        note = Text(
            "i を掛けることは、原点まわりに 90度 回すこと",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.7, 0])
        self.play(FadeIn(note), run_time=0.6)

        used = 0.6 + 0.7 + 0.7 + 0.5 + 0.4 + 2.0 + 0.6 + 0.6
        self.wait(max(1.0, duration - used))

    # ------------------------------------------------------------------
    # Mode: rotate_scale
    # ------------------------------------------------------------------
    def build_rotate_scale(self):
        duration = self._duration

        title = Text("一般の複素数を掛ける", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        subtitle = Text("── 回転 ＋ 拡大", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.6, 0])

        axes, axis_labels = self._make_axes()
        origin = axes.c2p(0, 0)

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(axis_labels), run_time=0.7)

        # z = 1.5 + 0.5 i
        z_pt = axes.c2p(1.5, 0.5)
        z_arrow = Arrow(origin, z_pt, buff=0, color=ACCENT_CYAN, stroke_width=5)
        z_dot = Dot(z_pt, color=ACCENT_CYAN, radius=0.07)
        z_label = MathTex(r"z", font_size=32, color=ACCENT_CYAN)
        z_label.next_to(z_dot, DOWN, buff=0.12)

        self.play(FadeIn(z_arrow), FadeIn(z_dot), FadeIn(z_label), run_time=0.7)
        self.wait(0.4)

        w_label = MathTex(
            r"w = 1 + i = \sqrt{2}\,e^{\,i\pi/4}", font_size=30, color=self._highlight
        )
        w_label.move_to([0, -1.15, 0])
        self.play(FadeIn(w_label), run_time=0.6)

        # w * z = 1 + 2i  (rotate 45 deg, scale sqrt(2))
        wz_pt = axes.c2p(1, 2)
        wz_arrow = Arrow(origin, wz_pt, buff=0, color=self._highlight, stroke_width=5)
        moving = z_arrow.copy().set_color(self._highlight)
        self.add(moving)
        self.play(ReplacementTransform(moving, wz_arrow), run_time=2.0)

        wz_dot = Dot(wz_pt, color=self._highlight, radius=0.07)
        wz_label = MathTex(r"w\,z = 1 + 2i", font_size=30, color=self._highlight)
        wz_label.next_to(wz_dot, UP, buff=0.12)
        self.play(FadeIn(wz_dot), FadeIn(wz_label), run_time=0.6)

        note = Text(
            "複素数を掛けると、回転と拡大が同時に起こる", font=FONT, font_size=22, color=ACCENT_PINK
        )
        note.move_to([0, -1.78, 0])
        self.play(FadeIn(note), run_time=0.6)

        used = 0.6 + 0.7 + 0.7 + 0.4 + 0.6 + 2.0 + 0.6 + 0.6
        self.wait(max(1.0, duration - used))

    # ------------------------------------------------------------------
    # Mode: contour_taste
    # ------------------------------------------------------------------
    def build_contour_taste(self):
        """A taste of complex analysis: a closed contour C with an interior
        singular point z_0 and a point running around it. No mechanism is shown
        (no residue computation) - this only opens the door (an earlier episode block 8)."""
        duration = self._duration

        title = Text("複素解析の扉", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.1, 0])
        subtitle = Text(
            "── なめらかな関数を、閉じた経路で積分する", font=FONT, font_size=22, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])

        axes, axis_labels = self._make_axes()
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(axis_labels), run_time=0.7)

        # Closed contour C (axes are isotropic at 0.8 screen units / data unit)
        cx, cy, r = 0.4, 0.3, 1.4
        contour = Circle(radius=0.8 * r, color=ACCENT_GOLD, stroke_width=4.0)
        contour.move_to(axes.c2p(cx, cy))
        c_label = MathTex(r"C", font_size=30, color=ACCENT_GOLD)
        c_label.next_to(contour, UP, buff=0.08)
        self.play(Create(contour), FadeIn(c_label), run_time=1.0)

        # Interior singular point z_0, drawn as a small cross
        s_pt = axes.c2p(cx, cy)
        cross = VGroup(
            Line(
                s_pt + [-0.13, -0.13, 0], s_pt + [0.13, 0.13, 0], color=ACCENT_PINK, stroke_width=4
            ),
            Line(
                s_pt + [-0.13, 0.13, 0], s_pt + [0.13, -0.13, 0], color=ACCENT_PINK, stroke_width=4
            ),
        )
        s_label = MathTex(r"z_0", font_size=28, color=ACCENT_PINK)
        s_label.next_to(cross, RIGHT, buff=0.12)
        s_note = Text("特異点", font=FONT, font_size=20, color=ACCENT_PINK)
        s_note.next_to(cross, DOWN, buff=0.12)
        self.play(FadeIn(cross), FadeIn(s_label), FadeIn(s_note), run_time=0.6)

        # The contour integral, named but not evaluated
        oint = MathTex(r"\oint_C f(z)\,dz", font_size=34, color=TEXT_WHITE)
        oint.move_to([3.9, 1.3, 0])
        note = Text("厳密な基礎が、新しい数学を開いた", font=FONT, font_size=20, color=ACCENT_GOLD)
        note.move_to([3.3, -1.2, 0])
        self.play(FadeIn(oint), run_time=0.5)

        # A point runs around the contour, filling the body (no static tail)
        theta = ValueTracker(0.0)
        mover = always_redraw(
            lambda: Dot(
                axes.c2p(
                    cx + r * math.cos(theta.get_value()),
                    cy + r * math.sin(theta.get_value()),
                ),
                color=ACCENT_CYAN,
                radius=0.10,
            )
        )
        self.add(mover)
        self.play(FadeIn(note), run_time=0.4)

        used = 0.6 + 0.7 + 1.0 + 0.6 + 0.5 + 0.4
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        self.play(theta.animate.set_value(2 * PI), run_time=motion, rate_func=linear)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: residue_integral
    # ------------------------------------------------------------------
    def build_residue_integral(self):
        """The concrete fruit (an earlier episode block 8): evaluate a real definite integral
        by residues. Integral_{-inf}^{inf} dx/(1+x^2) = pi via the upper
        semicircle contour and the residue 1/(2i) at the pole z=i. The plane
        sits on the left; the computation stack reveals on the right while a
        point traverses the closed contour (real axis -> arc), so there is no
        static tail. Mechanism is illustrated for one example only, not proved.
        NOTE: this specific integral is a modern illustration of Cauchy's
        method, not asserted as Cauchy's own computation (hedge lives in
        narration)."""
        duration = self._duration
        R = 2.3  # contour radius in data units

        title = Text(
            "厳密さが開いた果実 ── 留数で実積分を解く", font=FONT, font_size=26, color=TEXT_DIM
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.6)

        axes, _ = self._make_axes()
        axes.move_to([-1.6, 0.1, 0])
        origin = axes.c2p(0, 0)
        re_label = MathTex(r"\mathrm{Re}", font_size=24, color=TEXT_DIM)
        re_label.next_to(axes.c2p(R, 0), DOWN, buff=0.12)
        im_label = MathTex(r"\mathrm{Im}", font_size=24, color=TEXT_DIM)
        im_label.next_to(axes.c2p(0, R + 0.4), RIGHT, buff=0.08)
        self.play(FadeIn(axes), FadeIn(re_label), FadeIn(im_label), run_time=0.6)

        # Real-axis integration path (cyan)
        real_path = Line(axes.c2p(-R, 0), axes.c2p(R, 0), color=ACCENT_CYAN, stroke_width=5)
        real_note = Text("実軸 (積分路)", font=FONT, font_size=20, color=ACCENT_CYAN)
        real_note.move_to([axes.c2p(0, 0)[0], axes.c2p(0, 0)[1] - 0.55, 0])
        self.play(Create(real_path), FadeIn(real_note), run_time=0.6)

        # Closing semicircular arc (gold), upper half-plane
        arc = Arc(
            radius=0.8 * R,
            start_angle=0,
            angle=PI,
            arc_center=origin,
            color=ACCENT_GOLD,
            stroke_width=4,
        )
        self.play(Create(arc), run_time=0.8)

        # Pole at z = i, drawn as a cross
        s_pt = axes.c2p(0, 1)
        cross = VGroup(
            Line(
                s_pt + [-0.12, -0.12, 0], s_pt + [0.12, 0.12, 0], color=ACCENT_PINK, stroke_width=4
            ),
            Line(
                s_pt + [-0.12, 0.12, 0], s_pt + [0.12, -0.12, 0], color=ACCENT_PINK, stroke_width=4
            ),
        )
        z_lab = MathTex(r"z=i", font_size=26, color=ACCENT_PINK)
        z_lab.next_to(cross, RIGHT, buff=0.12)
        pole_note = Text("極", font=FONT, font_size=20, color=ACCENT_PINK)
        pole_note.next_to(cross, UP, buff=0.10)
        self.play(FadeIn(cross), FadeIn(z_lab), FadeIn(pole_note), run_time=0.6)

        # Traveling point along the closed contour (real axis -> arc)
        def contour_point(u):
            if u <= 0.5:
                x, y = -R + (u / 0.5) * 2 * R, 0.0
            else:
                th = ((u - 0.5) / 0.5) * PI
                x, y = R * math.cos(th), R * math.sin(th)
            return axes.c2p(x, y)

        tracker = ValueTracker(0.0)
        mover = always_redraw(
            lambda: Dot(contour_point(tracker.get_value()), color=ACCENT_PINK, radius=0.10)
        )
        self.add(mover)

        # Computation stack on the right, revealed in sync with the traversal
        col_x = 3.7
        f1 = MathTex(r"f(z)=\dfrac{1}{1+z^{2}}", font_size=30, color=TEXT_WHITE).move_to(
            [col_x, 1.9, 0]
        )
        f2 = MathTex(
            r"\operatorname{Res}_{z=i} f=\dfrac{1}{2i}", font_size=30, color=TEXT_WHITE
        ).move_to([col_x, 1.0, 0])
        f3 = MathTex(
            r"\oint_{C} f\,dz=2\pi i\cdot\dfrac{1}{2i}=\pi", font_size=30, color=TEXT_WHITE
        ).move_to([col_x, 0.1, 0])
        arc_note = Text("弧の寄与 → 0  (半径→∞)", font=FONT, font_size=20, color=TEXT_DIM).move_to(
            [col_x, -0.7, 0]
        )
        f4 = MathTex(
            r"\int_{-\infty}^{\infty}\dfrac{dx}{1+x^{2}}=\pi", font_size=38, color=ACCENT_GOLD
        ).move_to([col_x, -1.5, 0])
        reveals = [f1, f2, f3, arc_note, f4]

        coda = 2.2
        used = 0.6 + 0.6 + 0.6 + 0.8 + 0.6
        motion = max(3.0, duration - used - coda)
        seg = motion / len(reveals)
        for k, item in enumerate(reveals):
            self.play(
                tracker.animate.set_value((k + 1) / len(reveals)),
                FadeIn(item),
                run_time=seg,
                rate_func=linear,
            )

        self.wait(coda)


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# No people/years displayed on screen (math only).
LINT_FACTUAL_CLAIMS = {
    "multiply_i": {"people": [], "years": []},
    "rotate_scale": {"people": [], "years": []},
    "contour_taste": {"people": [], "years": []},
    "residue_integral": {"people": [], "years": []},
}


SCENES = {
    "multiply_i": {
        "class": "ComplexRotation",
        "params": {"mode": "multiply_i"},
        "description": "z=2+i times i rotates 90 deg to -1+2i (multiplying by i = quarter turn)",
    },
    "rotate_scale": {
        "class": "ComplexRotation",
        "params": {"mode": "rotate_scale"},
        "description": "Multiplying by w=1+i rotates 45 deg and scales by sqrt(2)",
    },
    "contour_taste": {
        "class": "ComplexRotation",
        "params": {"mode": "contour_taste"},
        "description": "Closed contour C with interior singular point z_0; a point circles it. Cauchy integral theorem, taste only (no residue computation)",
    },
    "residue_integral": {
        "class": "ComplexRotation",
        "params": {"mode": "residue_integral"},
        "description": "Evaluate the real integral int dx/(1+x^2)=pi by residues: upper semicircle contour, pole at z=i, residue 1/(2i). One worked example (an earlier episode Cauchy fruit), mechanism illustrated not proved",
    },
}
