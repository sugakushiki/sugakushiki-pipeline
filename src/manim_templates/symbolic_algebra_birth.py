"""
symbolic_algebra_birth.py - How a problem stopped being one problem

Before Viete, an equation was a sentence. Cardano's rules for the cubic are
prose, and because the given numbers are written into the prose, changing a
coefficient means starting the whole argument again. What Viete did in 1591 was
not to invent a symbol for the unknown - people had been writing letters for the
unknown since Jordanus - but to give the GIVEN quantities letters too, and then
to keep calculating with those letters to the end. He called that the reckoning
by species, and set it above the reckoning by numbers.

The moment the givens have names, what you write down is no longer a problem but
the SHAPE of a problem, and solving it once solves every instance at the same
time. That is what modes 'words' -> 'species' -> 'general' walk through, using
three quadratics that differ only in their two given numbers.

The fourth mode is the price he paid. Viete kept the law of homogeneous
magnitudes: only quantities of the same kind may be added, so a length can never
be added to an area. That is why his B has to be announced as "B plano" and his
Z as "Z solido". It is a letter algebra still tied to the dimensions of figures,
and it is half of why Descartes' notation replaced his.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    words       - The same shape of problem stated three times as prose, the way
                  it was written before letters for the givens.
                  Fixed params: three cases x^2 + b x = z with (b, z, x) =
                  (10, 39, 3), (8, 20, 2), (6, 7, 1). Every case is checked at
                  import time.
    species     - The three collapse into one lettered equation in Viete's own
                  form, A quadratum + B in A = Z, with the vowel (the unknown)
                  and the consonants (the givens) in different colours.
                  Fixed params: one equation, two colour keys.
    general     - The single equation on top, one arrow down, and the three
                  cases recovered from it by naming B and Z. Answers 3, 2, 1.
                  Fixed params: the same three cases as 'words'. One arrow, not
                  one per row: a fan of arrows from the equation draws diagonals
                  straight through the rows above the one it points at.
    homogeneity - The constraint. A length, a square and a cube; area plus area
                  allowed, length plus area struck out; and the form Viete
                  actually had to write, B plano in A = Z solido.
                  Fixed params: three kinds, one allowed sum, one refused sum.

The three cases are asserted at import time, so editing a number without editing
this docstring fails the render rather than quietly showing arithmetic the
narration contradicts.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    FadeIn,
    Line,
    MathTex,
    Scene,
    Square,
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

# ---------------------------------------------------------------------------
# Three problems of the same shape: x^2 + b x = z. They differ only in the two
# given numbers, which is the whole point - before the givens had names, that
# similarity could not be written down.
# ---------------------------------------------------------------------------
_CASES = (
    (10, 39, 3),
    (8, 20, 2),
    (6, 7, 1),
)

# Fail loudly rather than render arithmetic the narration contradicts.
for _b, _z, _x in _CASES:
    assert _x * _x + _b * _x == _z, (_b, _z, _x)
# They really are three different problems of one shape.
assert len({(b, z) for b, z, _ in _CASES}) == 3
assert len({x for _, _, x in _CASES}) == 3

# The lowest drawn text sits here. Japanese glyphs hang about 0.17 below the
# centre they are placed at and the subtitle band starts at y = -2.0.
_BOTTOM_Y = -1.72


class SymbolicAlgebraBirth(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "words")
        duration = params.get("duration", 26)
        if mode == "species":
            self._species(duration)
        elif mode == "general":
            self._general(duration)
        elif mode == "homogeneity":
            self._homogeneity(duration)
        else:
            self._words(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    def _viete_form(self, font_size=40):
        """A quadratum + B in A = Z, with the vowel and consonants coloured.

        Built from separate tex strings so the colouring keys off whole parts
        instead of matching the letter A inside the word quadratum.
        """
        eq = MathTex(
            r"A",
            r"\,\mathrm{quadratum}",
            r"\;+\;",
            r"B",
            r"\,\mathrm{in}\;",
            r"A",
            r"\;=\;",
            r"Z",
            font_size=font_size,
        )
        eq[0].set_color(ACCENT_GOLD)
        eq[5].set_color(ACCENT_GOLD)
        eq[3].set_color(ACCENT_CYAN)
        eq[7].set_color(ACCENT_CYAN)
        eq[1].set_color(TEXT_DIM)
        eq[2].set_color(TEXT_WHITE)
        eq[4].set_color(TEXT_DIM)
        eq[6].set_color(TEXT_WHITE)
        return eq

    # -- mode: words ----------------------------------------------------------
    def _words(self, duration):
        title = self._title("かつて、式は文章だった")

        lines = VGroup()
        for i, (b, z, _) in enumerate(_CASES):
            t = Text(
                f"ある数の2乗に、その数の{b}倍を足すと{z}",
                font=FONT,
                font_size=30,
                color=TEXT_WHITE,
            )
            self._fit(t, 11.6)
            t.move_to(UP * (1.55 - i * 0.95))
            lines.add(t)

        note = Text(
            "同じ形の問いなのに、同じとは書けない",
            font=FONT,
            font_size=29,
            color=ACCENT_PINK,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.0, 1.0, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        for i, line in enumerate(lines):
            self.play(FadeIn(line), run_time=rt[i])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(CODA)

    # -- mode: species --------------------------------------------------------
    def _species(self, duration):
        title = self._title("与えられた量にも、名前をつける")

        eq = self._viete_form(font_size=44)
        self._fit(eq, 11.0)
        eq.move_to(UP * 1.62)

        key_vowel = Text(
            "母音 A  ──  まだ分からない量",
            font=FONT,
            font_size=29,
            color=ACCENT_GOLD,
        )
        key_vowel.move_to(UP * 0.30)
        self._fit(key_vowel, 11.0)

        key_cons = Text(
            "子音 B, Z  ──  与えられた量",
            font=FONT,
            font_size=29,
            color=ACCENT_CYAN,
        )
        key_cons.move_to(DOWN * 0.42)
        self._fit(key_cons, 11.0)

        note = Text(
            "数を当てはめずに、このまま計算する",
            font=FONT,
            font_size=29,
            color=TEXT_WHITE,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.6
        rt = pace(duration, [1.2, 1.0, 1.0, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(eq), run_time=rt[0])
        self.play(FadeIn(key_vowel), run_time=rt[1])
        self.play(FadeIn(key_cons), run_time=rt[2])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(CODA)

    # -- mode: general --------------------------------------------------------
    def _general(self, duration):
        title = self._title("一度解けば、すべて解けている")

        eq = self._viete_form(font_size=38)
        self._fit(eq, 9.6)
        eq.move_to(UP * 2.10)

        # A single arrow straight down the middle. Fanning one arrow per row from
        # the equation looks tidy in code and draws diagonals straight through the
        # rows above the one being pointed at (found by rendering, not by reading).
        descend = Arrow(
            start=eq.get_bottom() + DOWN * 0.10,
            end=eq.get_bottom() + DOWN * 0.86,
            buff=0.0,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.28,
            color=EDGE_COLOR,
        )

        rows = VGroup()
        for i, (b, z, x) in enumerate(_CASES):
            y = 0.72 - i * 0.86
            # The vowel/consonant colour code is what this template teaches, so
            # "A =" has to be gold like every other A, not swept into the dim
            # arrow fragment.
            row = MathTex(
                r"B = ",
                str(b),
                r",\;\; Z = ",
                str(z),
                r"\;\;\longrightarrow\;\;",
                r"A = ",
                str(x),
                font_size=36,
            )
            for j in range(4):
                row[j].set_color(ACCENT_CYAN)
            row[4].set_color(TEXT_DIM)
            row[5].set_color(ACCENT_GOLD)
            row[6].set_color(ACCENT_GOLD)
            self._fit(row, 9.2)
            row.move_to(UP * y)
            rows.add(row)

        note = Text(
            "解いたのは、三つの問いではなく一つの型",
            font=FONT,
            font_size=29,
            color=ACCENT_PINK,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.6
        rt = pace(duration, [1.1, 0.95, 0.95, 0.95, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(eq), FadeIn(descend), run_time=rt[0])
        for i in range(len(_CASES)):
            self.play(FadeIn(rows[i]), run_time=rt[1 + i])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(CODA)

    # -- mode: homogeneity ----------------------------------------------------
    def _cube(self, side, colour):
        """A cheap wireframe cube: two squares and four struts."""
        front = Square(side_length=side, color=colour, stroke_width=3)
        back = Square(side_length=side, color=colour, stroke_width=2)
        back.set_opacity(0.0)
        back.set_stroke(colour, width=2, opacity=0.55)
        back.shift(RIGHT * side * 0.32 + UP * side * 0.32)
        struts = VGroup(
            *[
                Line(
                    front.get_vertices()[i],
                    back.get_vertices()[i],
                    color=colour,
                    stroke_width=2,
                ).set_stroke(opacity=0.55)
                for i in range(4)
            ]
        )
        return VGroup(back, struts, front)

    def _homogeneity(self, duration):
        title = self._title("足せるものと、足せないもの")

        seg = Line(LEFT * 0.55, RIGHT * 0.55, color=ACCENT_CYAN, stroke_width=6)
        sq = Square(side_length=1.0, color=ACCENT_CYAN, stroke_width=3)
        sq.set_fill(ACCENT_CYAN, opacity=0.18)
        cube = self._cube(0.92, ACCENT_CYAN)

        # The three shapes have three different heights, so next_to(DOWN) puts
        # their labels at three different heights and the row reads as crooked
        # (found by rendering). Both the shapes and the labels are pinned to a
        # fixed y instead.
        SHAPE_Y = 1.90
        LABEL_Y = 0.98
        kinds = VGroup()
        for shape, name, x in ((seg, "線", -4.0), (sq, "面", 0.0), (cube, "立体", 4.0)):
            shape.move_to(RIGHT * x + UP * SHAPE_Y)
            lab = Text(name, font=FONT, font_size=27, color=TEXT_WHITE)
            lab.move_to(RIGHT * x + UP * LABEL_Y)
            kinds.add(VGroup(shape, lab))

        ok_sum = Text("面 + 面", font=FONT, font_size=31, color=ACCENT_GOLD)
        ok_tail = Text("ならばよい", font=FONT, font_size=31, color=ACCENT_GOLD)
        ok_row = VGroup(ok_sum, ok_tail).arrange(RIGHT, buff=0.55)
        ok_row.move_to(UP * 0.05)
        self._fit(ok_row, 11.0)

        # The strike belongs on the sum, not on the words saying it cannot be
        # written - striking the whole sentence reads as cancelling the verdict.
        ng_sum = Text("線 + 面", font=FONT, font_size=31, color=ACCENT_PINK)
        ng_tail = Text("は、書けない", font=FONT, font_size=31, color=ACCENT_PINK)
        ng_row = VGroup(ng_sum, ng_tail).arrange(RIGHT, buff=0.55)
        ng_row.move_to(DOWN * 0.72)
        self._fit(ng_row, 11.0)

        strike = Line(
            ng_sum.get_left() + LEFT * 0.14,
            ng_sum.get_right() + RIGHT * 0.14,
            color=ACCENT_PINK,
            stroke_width=4,
        )

        latin = MathTex(
            r"B\,\mathrm{plano}\;\mathrm{in}\;",
            r"A",
            r"\;=\;",
            r"Z\,\mathrm{solido}",
            font_size=34,
        )
        latin[0].set_color(ACCENT_CYAN)
        latin[1].set_color(ACCENT_GOLD)
        latin[2].set_color(TEXT_WHITE)
        latin[3].set_color(ACCENT_CYAN)
        self._fit(latin, 10.4)
        latin.move_to(UP * _BOTTOM_Y)

        CODA = 2.6
        rt = pace(duration, [1.1, 0.9, 0.9, 0.7, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(*[FadeIn(k) for k in kinds], run_time=rt[0])
        self.play(FadeIn(ok_row), run_time=rt[1])
        self.play(FadeIn(ng_row), run_time=rt[2])
        self.play(FadeIn(strike), run_time=rt[3])
        self.play(FadeIn(latin), run_time=rt[4])
        self.wait(CODA)


# What each mode actually puts on screen, so a narration that promises something
# else can be caught before the build ships (read by
# qa_manim_consistency.check_narration_names_absent_visual). The checker only
# compares against its own list of "promise" nouns (arrow, contour, polyline,
# bar chart, x-axis, y-axis, timeline, grid squares, lattice, coordinates), so
# the other words here are documentation of the frame rather than things that
# get matched. 'general' is the one that matters: it really does draw an arrow.
LINT_VISUAL_ELEMENTS = {
    "words": ["文章", "式"],
    "species": ["式", "色"],
    "general": ["矢印", "式"],
    "homogeneity": ["図形", "正方形", "立方体", "式"],
}

# No person names and no years appear on screen in any mode; every number shown
# is one of the three cases, all asserted at import time.
LINT_FACTUAL_CLAIMS = {
    "words": {"people": [], "years": []},
    "species": {"people": [], "years": []},
    "general": {"people": [], "years": []},
    "homogeneity": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "words": SymbolicAlgebraBirth,
    "species": SymbolicAlgebraBirth,
    "general": SymbolicAlgebraBirth,
    "homogeneity": SymbolicAlgebraBirth,
}
