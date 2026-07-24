"""
halting_to_polynomial.py - the Fibonacci key and the bridge to the halting problem

The MRDP theorem (completed by Matiyasevich in 1970 on Julia Robinson's
groundwork) proves Diophantine sets = recursively enumerable sets. The last
missing piece was the Julia Robinson hypothesis - the existence of a Diophantine
relation of exponential growth - which Matiyasevich supplied using Fibonacci
numbers (the relation v = F_{2u} is Diophantine and grows like the golden ratio's
powers). The striking payoff: the halting problem is recursively enumerable, so it
becomes a single polynomial equation - an ancient question about integer solutions
turns out to BE the modern question "does this program halt?", which is why no
deciding machine can exist.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    fibonacci   - The sequence 1,1,2,3,5,8,13,21 revealed with rising heights that
                  shoot up exponentially; the relation v=F_{2u} is the "last key"
                  (a Diophantine relation of exponential growth = the J.R.
                  hypothesis).
    equivalence - Two worlds become one set: the Diophantine set (integer solutions
                  of polynomials, ancient number theory) equals the recursively
                  enumerable set (what an algorithm can list, modern computability)
                  - the MRDP theorem.
    halting     - The undecidable halting problem ("does program e halt?") is
                  translated into ONE fixed polynomial P(e,x_1,...,x_n)=0: it has an
                  integer solution IFF e halts, so a solvability-deciding machine
                  cannot exist.

No on-screen person names or years (all values are mathematical / conceptual), so
LINT_FACTUAL_CLAIMS is empty for every mode.

Reads params from _manim_params.json in the same directory.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Create,
    Dot,
    FadeIn,
    GrowArrow,
    Indicate,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR


class HaltingToPolynomial(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "fibonacci")
        duration = params.get("duration", 24)
        if mode == "equivalence":
            self._equivalence(duration)
        elif mode == "halting":
            self._halting(duration)
        else:
            self._fibonacci(duration)

    # -- mode: fibonacci ------------------------------------------------------
    def _fibonacci(self, duration):
        title = Text(
            "指数で増える ── 最後の鍵",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        fibs = [1, 1, 2, 3, 5, 8, 13, 21]
        n = len(fibs)
        # sequence tiles across the top band
        tile_w = 0.72
        x0 = -tile_w * (n - 1) / 2
        seq = {}
        for i, f in enumerate(fibs):
            t = MathTex(str(f), font_size=32, color=TEXT_WHITE)
            t.move_to(RIGHT * (x0 + i * tile_w) + UP * 1.75)
            seq[i] = t

        # rising dots (exponential feel), baseline y=-1.5, on the same x columns
        baseline = -1.5
        scale = 2.0 / max(fibs)  # tallest ~ +0.5
        dots = {}
        for i, f in enumerate(fibs):
            px = x0 + i * tile_w
            dots[i] = Dot(RIGHT * px + UP * (baseline + f * scale), color=ACCENT_CYAN, radius=0.06)

        relation = MathTex("v = F_{2u}", font_size=40, color=ACCENT_GOLD)
        relation.move_to(RIGHT * 3.6 + UP * 0.9)
        note = Text(
            "指数のように増える関係",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.move_to(LEFT * 3.6 + UP * 0.9)

        weights = [1.0] * n + [1.1, 0.9]
        rt = pace(duration, weights, intro=1.0, coda=3.0)

        prev_dot = None
        for i in range(n):
            anims = [FadeIn(seq[i]), FadeIn(dots[i])]
            if prev_dot is not None:
                seg = Line(
                    prev_dot.get_center(), dots[i].get_center(), color=TEXT_DIM, stroke_width=2
                )
                anims.append(Create(seg))
            self.play(*anims, run_time=rt[i])
            prev_dot = dots[i]

        self.play(FadeIn(relation), run_time=rt[n])
        self.play(FadeIn(note), run_time=rt[n + 1])
        self.wait(3.0)

    # -- mode: equivalence ----------------------------------------------------
    def _equivalence(self, duration):
        title = Text(
            "二つの世界が、重なった",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        # left world: Diophantine set (ancient number theory)
        lc = LEFT * 3.5 + UP * 0.3
        left_circle = Circle(radius=0.95, color=ACCENT_CYAN, stroke_width=3).move_to(lc)
        left_inner = MathTex("P(\\bar x,\\bar y)=0", font_size=26, color=ACCENT_CYAN).move_to(lc)
        left_name = Text("ディオファントス集合", font=FONT, font_size=22, color=TEXT_WHITE)
        left_name.move_to(LEFT * 3.5 + UP * 2.0)
        left_desc = Text("整数解を探す", font=FONT, font_size=18, color=TEXT_DIM)
        left_desc.move_to(LEFT * 3.5 + DOWN * 1.1)

        # right world: recursively enumerable set (computability)
        rc = RIGHT * 3.5 + UP * 0.3
        right_circle = Circle(radius=0.95, color=ACCENT_PINK, stroke_width=3).move_to(rc)
        right_inner = Text("算法で一覧", font=FONT, font_size=22, color=ACCENT_PINK).move_to(rc)
        right_name = Text("帰納的可算集合", font=FONT, font_size=22, color=TEXT_WHITE)
        right_name.move_to(RIGHT * 3.5 + UP * 2.0)
        right_desc = Text("算法で数え上げる", font=FONT, font_size=18, color=TEXT_DIM)
        right_desc.move_to(RIGHT * 3.5 + DOWN * 1.1)

        eq = MathTex("=", font_size=64, color=ACCENT_GOLD).move_to(UP * 0.3)

        caption = Text(
            "同じ一つの集合だった ── MRDP定理",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        caption.move_to(DOWN * 1.78)

        rt = pace(duration, [1.2, 1.2, 1.0, 1.2], intro=1.0, coda=3.0)
        self.play(
            FadeIn(left_name),
            Create(left_circle),
            FadeIn(left_inner),
            FadeIn(left_desc),
            run_time=rt[0],
        )
        self.play(
            FadeIn(right_name),
            Create(right_circle),
            FadeIn(right_inner),
            FadeIn(right_desc),
            run_time=rt[1],
        )
        self.play(FadeIn(eq), run_time=rt[2])
        self.play(
            FadeIn(caption),
            Indicate(eq, color=ACCENT_GOLD, scale_factor=1.3),
            run_time=rt[3],
        )
        self.wait(3.0)

    # -- mode: halting --------------------------------------------------------
    def _halting(self, duration):
        title = Text(
            "古代の問いは、現代の問い",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        q_text = Text(
            "プログラム e は、いつか止まる?",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        q_box = Rectangle(
            width=q_text.width + 0.6,
            height=q_text.height + 0.4,
            color=ACCENT_PINK,
            stroke_width=2.5,
        )
        q_group = VGroup(q_box, q_text).move_to(UP * 1.75)

        arrow = Arrow(UP * 1.15, UP * 0.45, color=TEXT_DIM, buff=0.05, stroke_width=4)

        poly = MathTex("P(e,\\ x_1,\\dots,x_n) = 0", font_size=42, color=ACCENT_CYAN)
        poly.move_to(DOWN * 0.05)

        # Build the biconditional as Text + MathTex(\Leftrightarrow) + Text so the
        # arrow glyph comes from LaTeX (BIZ UDMincho lacks U+27FA and would tofu).
        equiv_l = Text("整数解をもつ", font=FONT, font_size=24, color=TEXT_WHITE)
        equiv_arrow = MathTex("\\Leftrightarrow", font_size=34, color=ACCENT_GOLD)
        equiv_r = Text("e が止まる", font=FONT, font_size=24, color=TEXT_WHITE)
        equiv = VGroup(equiv_l, equiv_arrow, equiv_r).arrange(RIGHT, buff=0.22)
        equiv.move_to(DOWN * 1.05)

        concl = Text(
            "だから、判定する機械は存在しない",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        concl.move_to(DOWN * 1.72)

        rt = pace(duration, [1.1, 0.8, 1.1, 1.0, 1.0, 0.6], intro=1.0, coda=3.0)
        self.play(FadeIn(q_group), run_time=rt[0])
        self.play(GrowArrow(arrow), run_time=rt[1])
        self.play(FadeIn(poly), run_time=rt[2])
        self.play(FadeIn(equiv), run_time=rt[3])
        self.play(FadeIn(concl), run_time=rt[4])
        self.play(Indicate(concl, color=ACCENT_PINK, scale_factor=1.15), run_time=rt[5])
        self.wait(3.0)


# Factual-claim metadata (read by qa_manim_consistency.py). All modes render
# only mathematical / conceptual content - no person or year claims on screen.
LINT_FACTUAL_CLAIMS = {
    "fibonacci": {"people": [], "years": []},
    "equivalence": {"people": [], "years": []},
    "halting": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "fibonacci": HaltingToPolynomial,
    "equivalence": HaltingToPolynomial,
    "halting": HaltingToPolynomial,
}
