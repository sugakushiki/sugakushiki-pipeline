"""
polynomial_roots: 方程式の根を複素平面上に表示し、根の入れ替え（置換）をアニメーションで可視化する。

モード:
- quadratic: 2次方程式 x²-2=0 の根（±√2）を数直線上に表示し、入れ替えを示す
- cubic: 3次方程式 x³-1=0 の根（1の3乗根）を複素平面の単位円上に表示し、入れ替えを示す
- swap_animation: 3次の根に対して全6通りの置換を順に見せ、「群の元」を可視化する
"""

import numpy as np
from manim import *

BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
FONT = "BIZ UDMincho"
ROOT_COLORS = [GOLD, CYAN, PINK]


def get_duration(mode):
    defaults = {"quadratic": 29, "cubic": 35, "swap_animation": 50}
    return defaults.get(mode, 35)


class PolynomialRootsQuadratic(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("quadratic")

        # Step 1: Show equation
        eq1 = MathTex(r"x^2 - 2 = 0", font_size=56, color=WHITE)
        eq1.move_to(UP * 2.5)
        self.play(FadeIn(eq1), run_time=0.8)
        self.wait(0.8)

        # Step 2: Factored form (parts indexed for individual manipulation)
        # Parts: 0( 1:x 2:- 3:√2 4:) 5:( 6:x 7:+ 8:√2 9:) 10:=0
        eq2 = MathTex(
            r"(",
            r"x",
            r"-",
            r"\sqrt{2}",
            r")",
            r"(",
            r"x",
            r"+",
            r"\sqrt{2}",
            r")",
            r"= 0",
            font_size=52,
            color=WHITE,
        )
        eq2.move_to(ORIGIN)

        eq2[2].set_color(GOLD)  # minus sign
        eq2[3].set_color(GOLD)  # first √2
        eq2[7].set_color(CYAN)  # plus sign
        eq2[8].set_color(CYAN)  # second √2

        self.play(FadeIn(eq2), run_time=0.8)
        self.wait(1.5)

        # Step 3: Highlight the two root groups
        box1 = SurroundingRectangle(eq2[2:4], color=GOLD, buff=0.08, stroke_width=2.5)
        box2 = SurroundingRectangle(eq2[7:9], color=CYAN, buff=0.08, stroke_width=2.5)
        self.play(Create(box1), Create(box2), run_time=0.6)
        self.wait(1.0)

        # Step 4: Swap animation — move the sign+root groups along arcs
        group_a = VGroup(eq2[2], eq2[3]).copy()  # -√2 (gold)
        group_b = VGroup(eq2[7], eq2[8]).copy()  # +√2 (cyan)

        pos_a = VGroup(eq2[2], eq2[3]).get_center()
        pos_b = VGroup(eq2[7], eq2[8]).get_center()

        # Hide originals during swap
        self.play(FadeOut(box1), FadeOut(box2), run_time=0.3)
        self.add(group_a, group_b)
        eq2[2].set_opacity(0)
        eq2[3].set_opacity(0)
        eq2[7].set_opacity(0)
        eq2[8].set_opacity(0)

        arc_over = ArcBetweenPoints(pos_a, pos_b, angle=-PI / 3)
        arc_under = ArcBetweenPoints(pos_b, pos_a, angle=-PI / 3)

        self.play(
            MoveAlongPath(group_a, arc_over),
            MoveAlongPath(group_b, arc_under),
            run_time=1.5,
        )
        self.wait(0.3)

        # Step 5: Replace with clean swapped equation
        eq3 = MathTex(
            r"(",
            r"x",
            r"+",
            r"\sqrt{2}",
            r")",
            r"(",
            r"x",
            r"-",
            r"\sqrt{2}",
            r")",
            r"= 0",
            font_size=52,
            color=WHITE,
        )
        eq3.move_to(ORIGIN)
        eq3[2].set_color(CYAN)
        eq3[3].set_color(CYAN)
        eq3[7].set_color(GOLD)
        eq3[8].set_color(GOLD)

        self.remove(group_a, group_b)
        eq2[2].set_opacity(1)
        eq2[3].set_opacity(1)
        eq2[7].set_opacity(1)
        eq2[8].set_opacity(1)
        self.play(Transform(eq2, eq3), run_time=0.3)
        self.wait(0.5)

        # Step 6: Flash gold — same equation!
        self.play(eq2.animate.set_color(GOLD), eq1.animate.set_color(GOLD), run_time=0.4)
        self.play(eq2.animate.set_color(WHITE), eq1.animate.set_color(WHITE), run_time=0.4)
        eq3[2].set_color(CYAN)
        eq3[3].set_color(CYAN)
        eq3[7].set_color(GOLD)
        eq3[8].set_color(GOLD)

        elapsed = 0.8 + 0.8 + 0.8 + 1.5 + 0.6 + 1.0 + 0.3 + 1.5 + 0.3 + 0.3 + 0.5 + 0.4 + 0.4
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class PolynomialRootsCubic(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("cubic")

        equation = MathTex(r"x^3 - 1 = 0", font_size=56, color=WHITE)
        equation.to_edge(UP, buff=0.8)
        self.play(FadeIn(equation), run_time=0.8)
        self.wait(0.3)

        plane = ComplexPlane(
            x_range=[-2, 2, 1],
            y_range=[-1.8, 1.8, 1],
            x_length=6.5,
            y_length=5.2,
            background_line_style={"stroke_color": WHITE, "stroke_opacity": 0.15},
            axis_config={"stroke_color": WHITE, "stroke_opacity": 0.5},
        )
        plane.shift(DOWN * 0.15)
        re_label = MathTex(r"\mathrm{Re}", font_size=30, color=WHITE).set_opacity(0.6)
        re_label.next_to(plane.get_right(), DOWN, buff=0.15)
        im_label = MathTex(r"\mathrm{Im}", font_size=30, color=WHITE).set_opacity(0.6)
        im_label.next_to(plane.get_top(), RIGHT, buff=0.15)
        unit_circle = Circle(
            radius=plane.get_x_unit_size(), color=WHITE, stroke_opacity=0.3, stroke_width=1.5
        )
        unit_circle.move_to(plane.get_origin())

        self.play(
            FadeIn(plane), FadeIn(re_label), FadeIn(im_label), FadeIn(unit_circle), run_time=0.8
        )

        roots_complex = [
            complex(1, 0),
            complex(np.cos(2 * np.pi / 3), np.sin(2 * np.pi / 3)),
            complex(np.cos(4 * np.pi / 3), np.sin(4 * np.pi / 3)),
        ]
        root_labels_tex = [r"1", r"\omega", r"\omega^2"]

        root_dots, root_labels = [], []
        for i, (rc, ltex) in enumerate(zip(roots_complex, root_labels_tex, strict=False)):
            pos = plane.n2p(rc)
            dot = Dot(pos, radius=0.15, color=ROOT_COLORS[i], z_index=2)
            label = MathTex(ltex, font_size=38, color=ROOT_COLORS[i])
            direction = np.array([rc.real, rc.imag, 0])
            direction = direction / np.linalg.norm(direction)
            label.next_to(dot, direction, buff=0.28)
            root_dots.append(dot)
            root_labels.append(label)

        triangle = Polygon(
            *[plane.n2p(rc) for rc in roots_complex],
            color=WHITE,
            stroke_opacity=0.35,
            stroke_width=1.5,
            fill_opacity=0.03,
        )
        self.play(
            *[FadeIn(d) for d in root_dots],
            *[FadeIn(l) for l in root_labels],
            FadeIn(triangle),
            run_time=1.0,
        )
        self.wait(2.0)

        pos_w1, pos_w2 = plane.n2p(roots_complex[1]), plane.n2p(roots_complex[2])
        arc1 = ArcBetweenPoints(pos_w1, pos_w2, angle=-PI / 3)
        arc2 = ArcBetweenPoints(pos_w2, pos_w1, angle=-PI / 3)
        nd1 = np.array([roots_complex[2].real, roots_complex[2].imag, 0])
        nd1 /= np.linalg.norm(nd1)
        nd2 = np.array([roots_complex[1].real, roots_complex[1].imag, 0])
        nd2 /= np.linalg.norm(nd2)

        self.play(
            MoveAlongPath(root_dots[1], arc1),
            MoveAlongPath(root_dots[2], arc2),
            root_labels[1].animate.next_to(Dot(pos_w2), nd1, buff=0.28),
            root_labels[2].animate.next_to(Dot(pos_w1), nd2, buff=0.28),
            run_time=1.8,
        )
        self.play(equation.animate.set_color(GOLD), run_time=0.3)
        self.play(equation.animate.set_color(WHITE), run_time=0.3)

        elapsed = 0.8 + 0.3 + 0.8 + 1.0 + 2.0 + 1.8 + 0.6
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class PolynomialRootsSwapAnimation(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("swap_animation")

        plane = ComplexPlane(
            x_range=[-1.8, 1.8, 1],
            y_range=[-1.8, 1.8, 1],
            x_length=5.0,
            y_length=5.0,
            background_line_style={"stroke_color": WHITE, "stroke_opacity": 0.1},
            axis_config={"stroke_color": WHITE, "stroke_opacity": 0.4},
        )
        plane.shift(LEFT * 2.3 + DOWN * 0.1)
        unit_circle = Circle(
            radius=plane.get_x_unit_size(), color=WHITE, stroke_opacity=0.25, stroke_width=1.5
        )
        unit_circle.move_to(plane.get_origin())
        self.play(FadeIn(plane), FadeIn(unit_circle), run_time=0.5)

        roots_complex = [
            complex(1, 0),
            complex(np.cos(2 * np.pi / 3), np.sin(2 * np.pi / 3)),
            complex(np.cos(4 * np.pi / 3), np.sin(4 * np.pi / 3)),
        ]
        root_names = [r"1", r"\omega", r"\omega^2"]
        original_positions = [plane.n2p(rc) for rc in roots_complex]

        root_dots, root_labels = [], []
        for i in range(3):
            dot = Dot(original_positions[i], radius=0.14, color=ROOT_COLORS[i], z_index=2)
            label = MathTex(root_names[i], font_size=32, color=ROOT_COLORS[i])
            d = np.array([roots_complex[i].real, roots_complex[i].imag, 0])
            d /= np.linalg.norm(d)
            label.next_to(dot, d, buff=0.22)
            root_dots.append(dot)
            root_labels.append(label)
        self.play(*[FadeIn(d) for d in root_dots], *[FadeIn(l) for l in root_labels], run_time=0.6)

        perms = [
            (r"e", r"(1)(\omega)(\omega^2)", [0, 1, 2]),
            (r"\sigma_1", r"(1\;\omega)", [1, 0, 2]),
            (r"\sigma_2", r"(1\;\omega^2)", [2, 1, 0]),
            (r"\sigma_3", r"(\omega\;\omega^2)", [0, 2, 1]),
            (r"\sigma_4", r"(1\;\omega\;\omega^2)", [1, 2, 0]),
            (r"\sigma_5", r"(1\;\omega^2\;\omega)", [2, 0, 1]),
        ]

        perm_entries = VGroup()
        for i, (name, notation, _) in enumerate(perms):
            entry = MathTex(f"{name}: {notation}", font_size=30, color=WHITE).set_opacity(0.4)
            perm_entries.add(entry)
        perm_entries.arrange(DOWN, buff=0.32, aligned_edge=LEFT)
        perm_entries.shift(RIGHT * 3.2)
        self.play(FadeIn(perm_entries), run_time=0.6)
        self.wait(0.5)

        setup_time = 0.5 + 0.6 + 0.6 + 0.5
        available = duration - setup_time - 1.5
        time_per_perm = max(2.5, available / len(perms))
        current_arrangement = [0, 1, 2]

        for pi, (name, notation, target) in enumerate(perms):
            self.play(perm_entries[pi].animate.set_opacity(1.0).set_color(GOLD), run_time=0.3)
            if pi == 0:
                self.play(*[d.animate.scale(1.3) for d in root_dots], run_time=0.3)
                self.play(*[d.animate.scale(1 / 1.3) for d in root_dots], run_time=0.3)
            else:
                anims, label_anims = [], []
                r2new, r2cur = {}, {}
                for pos, ri in enumerate(target):
                    r2new[ri] = pos
                for pos, ri in enumerate(current_arrangement):
                    r2cur[ri] = pos
                moved = set()
                for ri in range(3):
                    cp, np_ = r2cur[ri], r2new[ri]
                    if cp != np_:
                        pair = tuple(sorted([cp, np_]))
                        angle = -PI / 3 if pair not in moved else PI / 3
                        moved.add(pair)
                        anims.append(
                            MoveAlongPath(
                                root_dots[ri],
                                ArcBetweenPoints(
                                    original_positions[cp], original_positions[np_], angle=angle
                                ),
                            )
                        )
                        nd = np.array([roots_complex[np_].real, roots_complex[np_].imag, 0])
                        nd /= np.linalg.norm(nd)
                        label_anims.append(
                            root_labels[ri].animate.next_to(
                                Dot(original_positions[np_]), nd, buff=0.22
                            )
                        )
                if anims:
                    self.play(*anims, *label_anims, run_time=1.0)
                current_arrangement = list(target)

            self.wait(max(0.3, time_per_perm - 1.6))

            if pi < len(perms) - 1:
                self.play(perm_entries[pi].animate.set_color(CYAN).set_opacity(0.7), run_time=0.2)
                if current_arrangement != [0, 1, 2]:
                    ra, rla = [], []
                    r2c = {}
                    for pos, ri in enumerate(current_arrangement):
                        r2c[ri] = pos
                    for ri in range(3):
                        cp = r2c[ri]
                        if cp != ri:
                            ra.append(
                                MoveAlongPath(
                                    root_dots[ri],
                                    ArcBetweenPoints(
                                        original_positions[cp],
                                        original_positions[ri],
                                        angle=-PI / 4,
                                    ),
                                )
                            )
                            nd = np.array([roots_complex[ri].real, roots_complex[ri].imag, 0])
                            nd /= np.linalg.norm(nd)
                            rla.append(
                                root_labels[ri].animate.next_to(
                                    Dot(original_positions[ri]), nd, buff=0.22
                                )
                            )
                    if ra:
                        self.play(*ra, *rla, run_time=0.6)
                    current_arrangement = [0, 1, 2]

        self.play(*[e.animate.set_color(GOLD).set_opacity(1.0) for e in perm_entries], run_time=0.6)
        self.wait(1.5)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "quadratic": {"people": [], "years": []},
    "cubic": {"people": [], "years": []},
    "swap_animation": {"people": [], "years": []},
}

        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


SCENES = {
    "quadratic": PolynomialRootsQuadratic,
    "cubic": PolynomialRootsCubic,
    "swap_animation": PolynomialRootsSwapAnimation,
}
