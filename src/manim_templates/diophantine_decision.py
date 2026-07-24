"""
diophantine_decision.py - Hilbert's 10th: is there an integer solution?

Hilbert's tenth problem (1900) asked for a single algorithm to decide, for any
Diophantine equation (a polynomial with integer coefficients), whether it has a
solution in integers. Julia Robinson devoted 20+ years to it; the answer (via the
MRDP theorem, completed by Matiyasevich in 1970) turned out to be NO - no such
algorithm can exist. These modes build the *question* intuitively: some equations
are solvable, some are not, and a single polynomial can already paint a whole
arithmetic set (the composites).

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    scan  - A short list of Diophantine equations gets a "?" that flips to
            SOLVABLE / UNSOLVABLE, ending on the question "can one machine decide
            them all?". Fixed equations: x^2-2y^2=1 (yes, (3,2)),
            x^2+y^2=3 (no), x^2+y^2=5 (yes, (1,2)) - the last two share a shape
            but differ in answer, so the verdict is not obvious at a glance.
    sieve - The single polynomial n=(u+2)(v+2) sweeps the integers 2..16 and
            lights up exactly the COMPOSITES (4,6,8,9,10,12,14,15,16), leaving
            the primes (2,3,5,7,11,13) un-lit: one equation draws a whole set.
    pell  - Geometry of solvable vs unsolvable. Left: x^2-2y^2=1 (a hyperbola
            through infinitely many lattice points, e.g. (1,0),(3,2)). Right:
            x^2+y^2=3 (a circle of radius sqrt(3) that no lattice point lies on).

No on-screen person names or years (all values are mathematical), so
LINT_FACTUAL_CLAIMS is empty for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Circle,
    Create,
    Dot,
    FadeIn,
    MathTex,
    ParametricFunction,
    Rectangle,
    ReplacementTransform,
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
    pace,
)

config.background_color = BG_COLOR


class DiophantineDecision(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "scan")
        duration = params.get("duration", 24)
        if mode == "sieve":
            self._sieve(duration)
        elif mode == "pell":
            self._pell(duration)
        else:
            self._scan(duration)

    # -- mode: scan -----------------------------------------------------------
    def _scan(self, duration):
        title = Text("整数の答えは、あるか", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)

        # (equation, solvable?, verdict text)
        rows = [
            ("x^2 - 2y^2 = 1", True, "○ 解あり"),
            ("x^2 + y^2 = 3", False, "× 解なし"),
            ("x^2 + y^2 = 5", True, "○ 解あり"),
        ]
        ys = [1.65, 0.55, -0.55]

        self.play(FadeIn(title), run_time=1.0)

        # weights: per row -> (reveal eq+?, flip ? to verdict); + final question
        rt = pace(duration, [1.0, 0.8, 1.0, 0.8, 1.0, 0.8, 1.2], intro=1.0, coda=3.0)

        k = 0
        for (eq, ok, verdict), y in zip(rows, ys, strict=True):
            eq_m = MathTex(eq, font_size=40, color=ACCENT_CYAN)
            eq_m.move_to(LEFT * 2.7 + UP * y)
            qmark = Text("?", font=FONT, font_size=38, color=TEXT_DIM)
            qmark.move_to(RIGHT * 2.7 + UP * y)
            self.play(FadeIn(eq_m), FadeIn(qmark), run_time=rt[k])
            k += 1

            color = ACCENT_CYAN if ok else ACCENT_PINK
            ver = Text(verdict, font=FONT, font_size=30, color=color)
            ver.move_to(RIGHT * 2.7 + UP * y)
            self.play(ReplacementTransform(qmark, ver), run_time=rt[k])
            k += 1

        question = Text(
            "どんな式でも判定する機械は、作れるか?",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        question.move_to(DOWN * 1.7)
        self.play(FadeIn(question), run_time=rt[k])
        self.wait(3.0)

    # -- mode: sieve ----------------------------------------------------------
    def _sieve(self, duration):
        title = Text("多項式が、集合を描く", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)
        formula = MathTex("n = (u+2)(v+2)", font_size=40, color=ACCENT_CYAN)
        formula.move_to(UP * 2.0)

        nums = list(range(2, 17))  # 2..16
        composites = [4, 6, 8, 9, 10, 12, 14, 15, 16]
        primes = [2, 3, 5, 7, 11, 13]

        tile_w = 0.74
        total = tile_w * len(nums)
        x0 = -total / 2 + tile_w / 2
        tiles = {}
        for i, n in enumerate(nums):
            box = Rectangle(
                width=tile_w * 0.9,
                height=tile_w * 0.9,
                color=TEXT_DIM,
                stroke_width=2,
            )
            lab = Text(str(n), font=FONT, font_size=22, color=TEXT_WHITE)
            grp = VGroup(box, lab)
            grp.move_to(RIGHT * (x0 + i * tile_w) + UP * 0.3)
            tiles[n] = grp

        self.play(FadeIn(title), FadeIn(formula), run_time=1.1)
        self.play(*[FadeIn(tiles[n]) for n in nums], run_time=1.0)

        caption = Text(
            "合成数だけが、塗られていく",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        caption.move_to(DOWN * 1.7)
        self.play(FadeIn(caption), run_time=0.6)

        rt = pace(duration, [1.0] * len(composites) + [1.4], intro=2.7, coda=3.0)
        for i, c in enumerate(composites):
            box = tiles[c][0]
            lab = tiles[c][1]
            self.play(
                box.animate.set_stroke(ACCENT_CYAN).set_fill(ACCENT_CYAN, opacity=0.28),
                lab.animate.set_color(TEXT_WHITE),
                run_time=rt[i],
            )

        prime_note = Text(
            "素数は、ふるい残される",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        prime_note.move_to(DOWN * 1.7)
        self.play(
            *[tiles[p][0].animate.set_stroke(ACCENT_GOLD, width=3) for p in primes],
            *[tiles[p][1].animate.set_color(ACCENT_GOLD) for p in primes],
            ReplacementTransform(caption, prime_note),
            run_time=rt[-1],
        )
        self.wait(3.0)

    # -- mode: pell -----------------------------------------------------------
    def _pell(self, duration):
        title = Text(
            "解のある式と、解のない式",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        s = 0.42
        ol = LEFT * 3.5 + DOWN * 0.35
        orr = RIGHT * 3.5 + DOWN * 0.35

        # ---- left: x^2 - 2y^2 = 1 (hyperbola through lattice points) --------
        left_lab = MathTex("x^2 - 2y^2 = 1", font_size=32, color=ACCENT_CYAN)
        left_lab.move_to(LEFT * 3.5 + UP * 1.5)

        def hyper(t):
            x = math.cosh(t)
            y = math.sinh(t) / math.sqrt(2)
            return ol + RIGHT * (s * x) + UP * (s * y)

        curve_up = ParametricFunction(hyper, t_range=[0, 1.9], color=TEXT_DIM, stroke_width=3)
        curve_dn = ParametricFunction(
            lambda t: ol + RIGHT * (s * math.cosh(t)) + UP * (s * math.sinh(t) / math.sqrt(2)),
            t_range=[-1.9, 0],
            color=TEXT_DIM,
            stroke_width=3,
        )
        sol_pts = [(1, 0), (3, 2)]
        sol_dots = VGroup()
        sol_labs = VGroup()
        for x, y in sol_pts:
            d = Dot(ol + RIGHT * (s * x) + UP * (s * y), color=ACCENT_GOLD, radius=0.08)
            lb = MathTex(f"({x},{y})", font_size=24, color=ACCENT_GOLD)
            lb.next_to(d, UP + RIGHT, buff=0.08)
            sol_dots.add(d)
            sol_labs.add(lb)
        left_note = Text(
            "解が無限にある",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        left_note.move_to(LEFT * 3.5 + DOWN * 1.7)

        # ---- right: x^2 + y^2 = 3 (circle through NO lattice point) ----------
        right_lab = MathTex("x^2 + y^2 = 3", font_size=32, color=ACCENT_PINK)
        right_lab.move_to(RIGHT * 3.5 + UP * 1.5)
        circle = Circle(radius=s * math.sqrt(3), color=ACCENT_PINK, stroke_width=3)
        circle.move_to(orr)
        lattice = VGroup()
        for gx in range(-2, 3):
            for gy in range(-2, 3):
                lattice.add(
                    Dot(orr + RIGHT * (s * gx) + UP * (s * gy), color=TEXT_DIM, radius=0.045)
                )
        right_note = Text(
            "格子点が、ひとつも乗らない",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        right_note.move_to(RIGHT * 3.5 + DOWN * 1.7)

        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0, 1.0], intro=1.0, coda=3.0)
        self.play(FadeIn(left_lab), Create(curve_up), Create(curve_dn), run_time=rt[0])
        self.play(FadeIn(sol_dots), FadeIn(sol_labs), run_time=rt[1])
        self.play(FadeIn(left_note), run_time=rt[2])
        self.play(FadeIn(right_lab), FadeIn(lattice), run_time=rt[3])
        self.play(Create(circle), run_time=rt[4])
        self.play(FadeIn(right_note), run_time=rt[5])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). All modes render
# only mathematical values (equations, integers) - no person/year claims.
LINT_FACTUAL_CLAIMS = {
    "scan": {"people": [], "years": []},
    "sieve": {"people": [], "years": []},
    "pell": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "scan": DiophantineDecision,
    "sieve": DiophantineDecision,
    "pell": DiophantineDecision,
}
