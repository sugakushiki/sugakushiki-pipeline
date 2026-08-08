"""
spec_z_arithmetic_line.py - Rebuilding a figure out of the functions on it

Grothendieck's starting point is to stop treating a figure as a bag of points.
Put the ring of functions on the figure first, and recover the points from the
ring. Once that is done consistently, ANY commutative ring defines a figure -
including the ring of integers, whose figure Spec Z looks like a line with one
point for every prime. Arithmetic and geometry become the same language, and a
single equation becomes a FAMILY of figures sitting over that line, one above
each prime. That family is what gets counted in the Weil conjectures.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    functions - The circle on the left, the ring of polynomial functions on it
                on the right, and arrows both ways between them.
                Fixed params: the circle x^2 + y^2 = 1 and the ring
                k[x,y]/(x^2+y^2-1).
    spec      - The ring of integers turned into a figure. A horizontal line
                labelled Spec Z carries one dot per prime.
                Fixed params: 11 primes shown, 2 through 31, evenly spaced
                (the spacing is schematic, not to scale).
    fiber     - The same line with a fibre drawn above four of its points: the
                solutions of y^2 = x^3 - x + 1 read modulo that prime, each
                drawn inside a box of the same size.
                Fixed params: p = 5, 7, 11, 13 with N_p = 8, 12, 10, 19. The
                affine solutions (7, 11, 9 and 18) are filled dots placed by
                their coordinates; the remaining point of each count is the
                point at infinity, drawn as a small RING at the box corner so
                that counting the box gives the N_p on the label. Leaving it
                out made every box one dot short of its own label.

The solution sets in the fibre mode are recomputed at import time by brute force
over F_p and checked against the counts above with assertions, so the picture
cannot drift away from the narration.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Arrow,
    Circle,
    Create,
    DashedLine,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR

_SPEC_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
_FIBER_PRIMES = [5, 7, 11, 13]
_CURVE = (1, 0, -1, 1)  # x^3 - x + 1


def _affine_points(coeffs, p):
    """Solutions (x, y) of y^2 = f(x) over F_p; coeffs highest degree first."""
    pts = []
    for x in range(p):
        v = 0
        for c in coeffs:
            v = (v * x + c) % p
        for y in range(p):
            if (y * y - v) % p == 0:
                pts.append((x, y))
    return pts


_FIBERS = {p: _affine_points(_CURVE, p) for p in _FIBER_PRIMES}

# Fail loudly rather than draw quietly wrong fibres (fail fast, no silent failures).
assert [len(_FIBERS[p]) for p in _FIBER_PRIMES] == [7, 11, 9, 18]
assert [len(_FIBERS[p]) + 1 for p in _FIBER_PRIMES] == [8, 12, 10, 19]


class SpecZArithmeticLine(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "functions")
        duration = params.get("duration", 26)
        if mode == "spec":
            self._spec(duration)
        elif mode == "fiber":
            self._fiber(duration)
        else:
            self._functions(duration)

    # -- shared: the Spec Z line ----------------------------------------------
    def _spec_line(self, y, x_half, primes, label_font=20):
        line = Line(
            RIGHT * -x_half + UP * y, RIGHT * x_half + UP * y, color=EDGE_COLOR, stroke_width=3
        )
        span = 2 * x_half * 0.88
        step = span / (len(primes) - 1)
        dots, labels, xs = VGroup(), VGroup(), []
        for k, q in enumerate(primes):
            x = -span / 2 + k * step
            xs.append(x)
            dots.add(Dot(RIGHT * x + UP * y, radius=0.075, color=ACCENT_CYAN))
            t = Text(str(q), font=FONT, font_size=label_font, color=TEXT_DIM)
            t.move_to(RIGHT * x + UP * (y - 0.42))
            labels.add(t)
        return line, dots, labels, xs

    # -- mode: functions ------------------------------------------------------
    def _functions(self, duration):
        title = Text("図形を、その上の関数から作り直す", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        circle = Circle(radius=1.05, color=ACCENT_CYAN, stroke_width=4)
        circle.move_to(LEFT * 3.85 + UP * 0.55)
        fig_lab = Text("図形", font=FONT, font_size=24, color=TEXT_WHITE)
        fig_lab.move_to(LEFT * 3.85 + UP * 1.98)
        fig_eq = MathTex(r"x^2 + y^2 = 1", font_size=28, color=TEXT_DIM)
        fig_eq.move_to(LEFT * 3.85 + DOWN * 0.92)

        box = Rectangle(width=4.5, height=1.35, color=EDGE_COLOR, stroke_width=2)
        box.move_to(RIGHT * 3.45 + UP * 0.55)
        ring = MathTex(r"k[x,y]\,/\,(x^2+y^2-1)", font_size=28, color=ACCENT_GOLD)
        ring.move_to(box.get_center())
        ring_lab = Text("その上の関数がなす環", font=FONT, font_size=24, color=TEXT_WHITE)
        ring_lab.move_to(RIGHT * 3.45 + UP * 1.98)

        arrow_r = Arrow(
            LEFT * 2.45 + UP * 1.15,
            RIGHT * 1.05 + UP * 1.15,
            color=TEXT_DIM,
            stroke_width=3,
            buff=0,
            max_tip_length_to_length_ratio=0.09,
        )
        lab_r = Text("関数を集める", font=FONT, font_size=20, color=TEXT_DIM)
        lab_r.move_to(LEFT * 0.7 + UP * 1.52)

        arrow_l = Arrow(
            RIGHT * 1.05 + DOWN * 0.05,
            LEFT * 2.45 + DOWN * 0.05,
            color=ACCENT_PINK,
            stroke_width=3,
            buff=0,
            max_tip_length_to_length_ratio=0.09,
        )
        lab_l = Text("点を取り出す", font=FONT, font_size=20, color=ACCENT_PINK)
        lab_l.move_to(LEFT * 0.7 + DOWN * 0.42)

        note = Text(
            "どちらから出発しても、同じ一つのものを見ている",
            font=FONT,
            font_size=23,
            color=TEXT_WHITE,
        )
        note.move_to(DOWN * 1.75)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.1, 1.0], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)
        self.play(FadeIn(fig_lab), Create(circle), FadeIn(fig_eq), run_time=rt[0])
        self.play(FadeIn(arrow_r), FadeIn(lab_r), run_time=rt[1])
        self.play(FadeIn(ring_lab), Create(box), FadeIn(ring), run_time=rt[2])
        self.play(FadeIn(arrow_l), FadeIn(lab_l), run_time=rt[3])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(3.0)

    # -- mode: spec -----------------------------------------------------------
    def _spec(self, duration):
        title = Text("整数全体という環から、図形を作る", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.08)

        src_lab = Text("整数全体のなす環", font=FONT, font_size=24, color=TEXT_WHITE)
        src_lab.move_to(LEFT * 1.15 + UP * 2.25)
        src = MathTex(r"\mathbb{Z}", font_size=36, color=ACCENT_GOLD)
        src.next_to(src_lab, RIGHT, buff=0.35)

        down = Arrow(
            UP * 1.88,
            UP * 1.05,
            color=TEXT_DIM,
            stroke_width=3,
            buff=0,
            max_tip_length_to_length_ratio=0.18,
        )

        line, dots, labels, _ = self._spec_line(0.35, 6.1, _SPEC_PRIMES)
        spec_lab = MathTex(r"\operatorname{Spec}\mathbb{Z}", font_size=32, color=ACCENT_CYAN)
        spec_lab.move_to(RIGHT * 4.35 + UP * 1.05)

        note = Text(
            "素数のひとつひとつが、この直線の点になる", font=FONT, font_size=23, color=TEXT_WHITE
        )
        note.move_to(DOWN * 1.05)
        punch = Text(
            "整数の世界が、図形として見えてくる", font=FONT, font_size=25, color=ACCENT_PINK
        )
        punch.move_to(DOWN * 1.78)

        rt = pace(duration, [1.0, 1.0, 1.2, 1.0, 1.0], intro=1.0, coda=3.0)
        self.play(FadeIn(title), run_time=1.0)
        self.play(FadeIn(src_lab), FadeIn(src), run_time=rt[0])
        self.play(FadeIn(down), Create(line), FadeIn(spec_lab), run_time=rt[1])
        self.play(
            AnimationGroup(
                *[
                    AnimationGroup(FadeIn(d, run_time=0.4), FadeIn(t, run_time=0.4))
                    for d, t in zip(dots, labels, strict=True)
                ],
                lag_ratio=0.25,
            ),
            run_time=rt[2],
        )
        self.play(FadeIn(note), run_time=rt[3])
        self.play(FadeIn(punch), run_time=rt[4])
        self.wait(3.0)

    # -- mode: fiber ----------------------------------------------------------
    def _fiber(self, duration):
        title = Text(
            "一つの方程式が、素数ごとの図形になる", font=FONT, font_size=30, color=ACCENT_GOLD
        )
        title.move_to(UP * 3.08)

        eq = MathTex(r"y^2 = x^3 - x + 1", font_size=30, color=TEXT_WHITE)
        eq.move_to(LEFT * 4.55 + UP * 2.38)

        # The line is kept short enough that the Spec Z label clears the last prime
        # label: with x_half = 5.9 the rightmost dot sat at x = 5.19 and the label
        # underneath it collided with this one.
        line, dots, labels, xs = self._spec_line(-1.15, 5.4, _FIBER_PRIMES, label_font=22)
        spec_lab = MathTex(r"\operatorname{Spec}\mathbb{Z}", font_size=26, color=TEXT_DIM)
        spec_lab.move_to(RIGHT * 6.15 + DOWN * 1.15)

        boxes, clouds, counts, stems = VGroup(), VGroup(), VGroup(), VGroup()
        box_w = 1.45
        box_cy = 0.72
        for q, x in zip(_FIBER_PRIMES, xs, strict=True):
            box = Rectangle(width=box_w, height=box_w, color=EDGE_COLOR, stroke_width=2)
            box.move_to(RIGHT * x + UP * box_cy)
            boxes.add(box)

            cloud = VGroup()
            for i, j in _FIBERS[q]:
                px = x + ((i + 0.5) / q - 0.5) * (box_w - 0.18)
                py = box_cy + ((j + 0.5) / q - 0.5) * (box_w - 0.18)
                cloud.add(Dot(RIGHT * px + UP * py, radius=0.045, color=ACCENT_CYAN))
            # The point at infinity, drawn so that a viewer who counts the dots gets the
            # N_p on the label and in the narration. Without it each box was one dot short
            # (7/11/9/18 against N = 8/12/10/19) and the figure contradicted its own label.
            # It is set apart as a small ring, and the next scene names it while counting
            # p = 7 in full ("11 lattice solutions plus the one point at infinity").
            cloud.add(
                Circle(
                    radius=0.062,
                    color=ACCENT_CYAN,
                    stroke_width=2.5,
                    fill_opacity=0,
                ).move_to(RIGHT * (x + box_w / 2 - 0.02) + UP * (box_cy + box_w / 2 - 0.02))
            )
            clouds.add(cloud)

            cnt = MathTex(rf"N_{{{q}}} = {len(_FIBERS[q]) + 1}", font_size=26, color=ACCENT_GOLD)
            cnt.move_to(RIGHT * x + UP * (box_cy + box_w / 2 + 0.34))
            counts.add(cnt)

            stems.add(
                DashedLine(
                    RIGHT * x + UP * (box_cy - box_w / 2),
                    RIGHT * x + UP * -1.15,
                    color=EDGE_COLOR,
                    stroke_width=2,
                    dash_length=0.1,
                )
            )

        note = Text(
            "素数ごとに、有限個の点からなる図形が乗っている",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to(RIGHT * 1.95 + UP * 2.38)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0, 1.0], intro=1.9, coda=3.0)
        self.play(FadeIn(title), FadeIn(eq), run_time=1.0)
        self.play(Create(line), FadeIn(dots), FadeIn(labels), FadeIn(spec_lab), run_time=0.9)
        for k in range(len(_FIBER_PRIMES)):
            self.play(
                AnimationGroup(
                    Create(stems[k], run_time=0.35),
                    Create(boxes[k], run_time=0.4),
                    FadeIn(clouds[k], run_time=0.5),
                    FadeIn(counts[k], run_time=0.4),
                    lag_ratio=0.25,
                ),
                run_time=rt[k],
            )
        self.play(FadeIn(note), run_time=rt[4] + rt[5])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; the only numbers shown are the primes on the Spec Z line
# and the solution counts documented in the module docstring.
LINT_FACTUAL_CLAIMS = {
    "functions": {"people": [], "years": []},
    "spec": {"people": [], "years": []},
    "fiber": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "functions": SpecZArithmeticLine,
    "spec": SpecZArithmeticLine,
    "fiber": SpecZArithmeticLine,
}
