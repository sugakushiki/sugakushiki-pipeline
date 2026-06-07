"""
mesolabion.py - Eratosthenes' mesolabion (the "mean-finder" device).

Eratosthenes of Cyrene (3rd century BC) invented a mechanical device that
produces two mean proportionals between given lengths a and 2a. Three
rectangular plates, each with a diagonal drawn from one corner to the opposite,
slide horizontally in a frame. When the diagonals are aligned so that
successive intersection points coincide on a slanting line, the four vertical
heights at the frame's column lines form the chain a : x : y : 2a, with
x = a * cube_root(2) and y = a * cube_root(4). Thus the device "draws" the
cube root mechanically, bypassing the impossibility of compass-and-straightedge
construction (later proved by Wantzel in 1837).

The 6th-century commentator Eutocius, in his note on Archimedes' On the Sphere
and Cylinder, preserves Eratosthenes' design and a bronze votive inscription
in which he claimed the method dispenses with both Archytas' difficult
construction and Menaechmus' conic-section solution.

Modes:
    device     - Four vertical column lines at x = -3.0, -1.0, 1.0, 3.0 with
                 heights 2a, y, x, a (left to right). Three sliding plates
                 (rectangles with diagonals) between adjacent columns. A common
                 slanting line through the tops shows the proportional alignment.
                 Captions: a : x : y : 2a chain and "対角線のスライドで比例中項".
                 Fixed params: a = 0.7 (display units), 2a = 1.4, x = a*2^(1/3),
                 y = a*2^(2/3). Slant line from (left, 2a) to (right, 0).
    epigram    - Bronze-tablet styled centered text of Eratosthenes' votive
                 inscription as preserved by Eutocius (Japanese paraphrase).
                 Fixed params: 4 lines of paraphrase + attribution.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0. No trailing FadeOut. Duration-aware.

Used by: Episode 027 (Eratosthenes), pillar B — mesolabion device.
"""

import math

from manim import (
    Arrow,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    Rectangle,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
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


class Mesolabion(Scene):
    """Eratosthenes' mesolabion — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "device")
        self._duration = params.get("duration", 28)

        if mode == "epigram":
            self._build_epigram()
        else:
            self._build_device()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=26, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_device(self):
        """Stylized animation of the mesolabion (corrected geometry).

        Following Heath, A History of Greek Mathematics, vol. 1, pp. 258-260:
        The device has two fixed end-columns at x = c0 (height 2a) and x = c3
        (height a). A straight reference line is drawn from (c0, 2a) to
        (c3, a). The three plate diagonals must all lie on this reference
        line — i.e., the diagonals are "aligned" = collinear on the reference
        line.

        For the heights at the intermediate columns to be the geometric means
        y = a·∛4 and x = a·∛2, the intermediate columns must be positioned at
        non-equal x-positions. Solving 2a + (a - 2a) · (c_k - c0)/(c3 - c0) =
        h_k gives:
            c1/L = (2a - y)/a = 2 - 2^(2/3) ≈ 0.413
            c2/L = (2a - x)/a = 2 - 2^(1/3) ≈ 0.740
        where L = c3 - c0.

        Animation:
            - Initial state: intermediate columns equally spaced at L/3 and
              2L/3; the reference line cuts them at heights 5a/3 and 4a/3
              (arithmetic — NOT the geometric means).
            - Plates slide → intermediate columns move to c1 ≈ 0.413·L and
              c2 ≈ 0.740·L.
            - Final state: reference line crosses the now-relocated
              intermediate columns at exactly y and x. The 3 plate diagonals
              all lie on the single reference line.
        """
        duration = float(self._duration)
        title = self._title("メソラビオン ── 比例中項を取り出す機械")
        self.play(FadeIn(title), run_time=0.5)

        # Geometry
        a_disp = 0.7
        two_a = 2.0 * a_disp
        x_len = a_disp * (2 ** (1 / 3))
        y_len = a_disp * (2 ** (2 / 3))

        # End columns fixed; L = total span
        c0_x = -3.0
        c3_x = 3.0
        L = c3_x - c0_x

        # Final positions for intermediate columns (geometric proportional)
        c1_x_final = c0_x + L * (2 - 2 ** (2 / 3)) / 1  # ≈ -0.522
        c2_x_final = c0_x + L * (2 - 2 ** (1 / 3)) / 1  # ≈ +1.440

        # Initial positions for intermediate columns (equally spaced)
        c1_x_initial = c0_x + L / 3.0  # = -1.0
        c2_x_initial = c0_x + 2 * L / 3.0  # = +1.0

        base_y = -1.25
        col_colors = [ACCENT_CYAN, ACCENT_PINK, ACCENT_PINK, ACCENT_CYAN]

        # Frame
        frame = Rectangle(
            width=L + 1.2, height=two_a + 0.5,
            color=TEXT_DIM, stroke_width=2.0,
        )
        frame.move_to([(c0_x + c3_x) / 2,
                        base_y + (two_a + 0.5) / 2 - 0.20, 0])

        # Baseline
        baseline = Line([c0_x - 0.5, base_y, 0],
                        [c3_x + 0.5, base_y, 0],
                        color=TEXT_DIM, stroke_width=2.0)
        self.play(Create(frame), Create(baseline), run_time=0.7)

        # ValueTracker for plate-position interpolation
        t = ValueTracker(0.0)

        def ref_height(x):
            """Height of the reference line from (c0, 2a) to (c3, a) at given x."""
            return two_a + (a_disp - two_a) * (x - c0_x) / L

        # The reference line — fixed from (c0, 2a) to (c3, a)
        ref_line = DashedLine(
            [c0_x, base_y + two_a, 0],
            [c3_x, base_y + a_disp, 0],
            color=ACCENT_GOLD, stroke_width=2.4,
            dash_length=0.16, stroke_opacity=0.55,
        )
        ref_lbl = Text("参照線", font=FONT, font_size=14, color=ACCENT_GOLD)
        ref_lbl.move_to([c0_x - 0.55, base_y + two_a, 0])

        # End columns (fixed)
        col0_line = Line([c0_x, base_y, 0], [c0_x, base_y + two_a, 0],
                          color=ACCENT_CYAN, stroke_width=4)
        col3_line = Line([c3_x, base_y, 0], [c3_x, base_y + a_disp, 0],
                          color=ACCENT_CYAN, stroke_width=4)
        col0_lbl = MathTex(r"2a", font_size=28, color=ACCENT_CYAN)
        col0_lbl.move_to([c0_x, base_y + two_a + 0.30, 0])
        col3_lbl = MathTex(r"a", font_size=28, color=ACCENT_CYAN)
        col3_lbl.move_to([c3_x, base_y + a_disp + 0.30, 0])

        # Each plate has its OWN endpoints that interpolate independently.
        # Initial: plate diagonals have DIFFERENT slopes, and heights at the
        # left/right edges DON'T match between adjacent plates (broken chain).
        # Final: diagonals all lie on the reference line, heights match at
        # boundaries → continuous chain forming the geometric progression.

        # Plate 0 endpoints: (col_0, 2a) fixed; right point slides + rises
        p0_left = [c0_x, base_y + two_a, 0]
        p0_right_initial = [c1_x_initial, base_y + 0.40, 0]
        p0_right_final = [c1_x_final, base_y + y_len, 0]

        # Plate 1 endpoints: both slide; initial left ≠ p0_right (discontinuity)
        p1_left_initial = [c1_x_initial, base_y + 1.20, 0]
        p1_right_initial = [c2_x_initial, base_y + 0.30, 0]
        p1_left_final = [c1_x_final, base_y + y_len, 0]   # matches p0_right_final
        p1_right_final = [c2_x_final, base_y + x_len, 0]

        # Plate 2 endpoints: left slides; right at (c3, a) fixed
        p2_left_initial = [c2_x_initial, base_y + 0.90, 0]
        p2_left_final = [c2_x_final, base_y + x_len, 0]   # matches p1_right_final
        p2_right = [c3_x, base_y + a_disp, 0]

        def lerp(a_pt, b_pt, tv):
            return [a_pt[i] * (1 - tv) + b_pt[i] * tv for i in range(3)]

        def cur_endpoints():
            tv = t.get_value()
            return (
                p0_left,
                lerp(p0_right_initial, p0_right_final, tv),
                lerp(p1_left_initial, p1_left_final, tv),
                lerp(p1_right_initial, p1_right_final, tv),
                lerp(p2_left_initial, p2_left_final, tv),
                p2_right,
            )

        # Three plate diagonals — always redrawn
        def make_diagonals():
            p0L, p0R, p1L, p1R, p2L, p2R = cur_endpoints()
            return VGroup(
                Line(p0L, p0R, color=ACCENT_GOLD, stroke_width=3.4),
                Line(p1L, p1R, color=ACCENT_GOLD, stroke_width=3.4),
                Line(p2L, p2R, color=ACCENT_GOLD, stroke_width=3.4),
            )
        diagonals = always_redraw(make_diagonals)

        # Intermediate columns slide horizontally; their heights show both
        # the plate-i right-edge and plate-(i+1) left-edge stacked.
        def make_mid_cols():
            p0L, p0R, p1L, p1R, p2L, p2R = cur_endpoints()
            # Column 1 at x = p0R.x = p1L.x (they share x position after slide)
            x1 = p0R[0]  # plate boundaries move together
            x2 = p1R[0]
            # In initial state, p0R.y and p1L.y differ — show both ticks
            return VGroup(
                Line([x1, base_y, 0], [x1, base_y + max(p0R[1], p1L[1]) - base_y, 0],
                     color=ACCENT_PINK, stroke_width=4),
                Line([x2, base_y, 0], [x2, base_y + max(p1R[1], p2L[1]) - base_y, 0],
                     color=ACCENT_PINK, stroke_width=4),
            )
        mid_cols = always_redraw(make_mid_cols)

        # Plate fills — between consecutive boundaries
        def make_plates():
            p0L, p0R, p1L, p1R, p2L, p2R = cur_endpoints()
            grp = VGroup()
            for (lx, rx, lh, rh) in [
                (p0L[0], p0R[0], p0L[1] - base_y, p0R[1] - base_y),
                (p1L[0], p1R[0], p1L[1] - base_y, p1R[1] - base_y),
                (p2L[0], p2R[0], p2L[1] - base_y, p2R[1] - base_y),
            ]:
                top = max(lh, rh)
                plate = Rectangle(
                    width=rx - lx, height=top,
                    color=ACCENT_GOLD, stroke_width=0.8,
                )
                plate.move_to([(lx + rx) / 2, base_y + top / 2, 0])
                plate.set_fill(ACCENT_GOLD, opacity=0.05)
                grp.add(plate)
            return grp
        plates = always_redraw(make_plates)

        # Endpoint dots — visible where each plate's diagonal terminates
        def make_dots():
            p0L, p0R, p1L, p1R, p2L, p2R = cur_endpoints()
            return VGroup(
                Dot(p0L, color=ACCENT_CYAN, radius=0.08),
                Dot(p0R, color=ACCENT_GOLD, radius=0.07),
                Dot(p1L, color=ACCENT_GOLD, radius=0.07),
                Dot(p1R, color=ACCENT_GOLD, radius=0.07),
                Dot(p2L, color=ACCENT_GOLD, radius=0.07),
                Dot(p2R, color=ACCENT_CYAN, radius=0.08),
            )
        dots = always_redraw(make_dots)

        # Show initial (mis-aligned) state
        self.add(plates, col0_line, col3_line, mid_cols, diagonals, dots)
        self.play(FadeIn(col0_lbl), FadeIn(col3_lbl),
                  Create(ref_line), FadeIn(ref_lbl), run_time=0.7)
        self.wait(0.3)

        # Annotation: slide instruction
        slide_lbl = Text("板をスライドさせると…", font=FONT, font_size=16,
                          color=ACCENT_PINK)
        slide_lbl.move_to([0, base_y + two_a + 0.55, 0])
        self.play(FadeIn(slide_lbl), run_time=0.4)

        # Animate: intermediate columns slide to their proper proportional positions
        self.play(t.animate.set_value(1.0), run_time=2.2)

        # Final labels at the new intermediate column positions
        y_lbl = MathTex(r"y", font_size=28, color=ACCENT_PINK)
        y_lbl.move_to([c1_x_final, base_y + y_len + 0.30, 0])
        x_lbl = MathTex(r"x", font_size=28, color=ACCENT_PINK)
        x_lbl.move_to([c2_x_final, base_y + x_len + 0.30, 0])
        self.play(FadeIn(y_lbl), FadeIn(x_lbl), run_time=0.5)

        # Final caption — diagonals are now aligned on the reference line
        align_lbl = Text(
            "対角線がそろう = 比例中項",
            font=FONT, font_size=15, color=ACCENT_GOLD,
        )
        align_lbl.move_to([0, base_y + two_a + 0.55, 0])
        self.play(FadeIn(align_lbl), run_time=0.4)
        self.remove(slide_lbl)

        # Chain caption at top
        chain = MathTex(
            r"a : x = x : y = y : 2a",
            font_size=28, color=ACCENT_GOLD,
        )
        chain.move_to([0, 2.40, 0])
        self.play(FadeIn(chain), run_time=0.5)

        # Result note at bottom
        result = MathTex(
            r"x = a\,\sqrt[3]{2}, \; y = a\,\sqrt[3]{4}",
            font_size=22, color=ACCENT_PINK,
        )
        result.move_to([0, -1.90, 0])
        self.play(FadeIn(result), run_time=0.5)

        anim_total = 0.5 + 0.7 + 0.7 + 0.3 + 0.4 + 2.2 + 0.5 + 0.4 + 0.5 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_epigram(self):
        duration = float(self._duration)
        title = self._title("青銅の奉納碑 ── エウトキオスの伝える碑文")
        self.play(FadeIn(title), run_time=0.6)

        # Bronze tablet styled frame
        tablet = Rectangle(
            width=8.6, height=4.0,
            color=ACCENT_GOLD, stroke_width=3.0,
        )
        tablet.set_fill(ACCENT_GOLD, opacity=0.05)
        tablet.move_to([0, 0.20, 0])
        # Inner decorative frame
        inner = Rectangle(
            width=8.2, height=3.6,
            color=ACCENT_GOLD, stroke_width=1.2,
        )
        inner.move_to([0, 0.20, 0])
        self.play(Create(tablet), Create(inner), run_time=0.8)

        # The inscription, paraphrased into Japanese
        lines = [
            "立方体を倍にせよと求められたなら、",
            "いかなる立体も同様にしてよい。",
            "この発見はアルキュタスの面倒な作図にも、",
            "メナイクモスの円錐曲線にもよらない。",
        ]
        y_top = 1.45
        gap = 0.60
        line_group = VGroup()
        for i, ln in enumerate(lines):
            t = Text(ln, font=FONT, font_size=22, color=TEXT_WHITE)
            t.move_to([0, y_top - i * gap, 0])
            line_group.add(t)
        for t in line_group:
            self.play(FadeIn(t), run_time=0.5)

        # Attribution
        attrib = Text(
            "── エラトステネス（六世紀のエウトキオスが伝える）",
            font=FONT, font_size=16, color=ACCENT_PINK,
        )
        attrib.move_to([0, -1.45, 0])
        self.play(FadeIn(attrib), run_time=0.6)

        anim_total = 0.6 + 0.8 + 0.5 * len(lines) + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "device": {"people": [], "years": []},
    "epigram": {
        "people": [
            ["エラトステネス", "Eratosthenes"],
            ["エウトキオス", "Eutocius"],
            ["アルキュタス", "Archytas"],
            ["メナイクモス", "Menaechmus"],
        ],
        "years": [],
    },
}

SCENES = {
    "device": Mesolabion,
    "epigram": Mesolabion,
}
