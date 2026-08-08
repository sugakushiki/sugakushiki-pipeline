"""
degree45_trigonometric.py - The equation of the forty-fifth degree, and the
twenty-three roots Viete brought back

In 1593 Adriaan van Roomen opened his Ideae mathematicae with an equation of
degree 45 and threw it at the mathematicians of the world. An ambassador from
the Netherlands told Henri IV that France had nobody who could solve it. Viete
saw at once what it was: put x = 2 sin(theta) and the whole left-hand side is
2 sin(45 theta). The equation is not a monster, it is the instruction "divide
this angle into forty-five", and 45 = 3 x 3 x 5, so it is a trisection inside a
trisection inside a fifth.

He gave one root immediately and twenty-two more the next day. Twenty-three, out
of forty-five. The other twenty-two are negative, and Viete did not count
negative quantities as roots at all - the 1911 Britannica still reports his
twenty-three as "all the positive roots of which the said equation was capable".
The third mode is that sentence, drawn: forty-five marks on a line, and the
colour splits exactly where his arithmetic stopped.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    challenge - The equation as posed: the low-order terms, an ellipsis, the
                leading term, and the two facts you can read off it.
                Fixed params: coefficients 45, -3795, 95634, -1138500 on
                x, x^3, x^5, x^7 and 1 on x^45; only odd powers occur.
    unfold    - The substitution. x = 2 sin(theta) turns the left-hand side into
                2 sin(45 theta). The equation therefore fixes the 45-FOLD angle,
                not theta: with 45 theta = alpha known, theta = alpha/45 -- which
                is what "divide an angle into 45 parts" means. (theta may not be
                the thing divided by 45; it is already bound by the
                substitution.) And 45 = 3 x 3 x 5.
                Fixed params: the factorisation 3 x 3 x 5 = 45.
    roots     - Forty-five roots on a line from -2 to 2, the 23 positive ones in
                gold and the 22 negative ones dimmed.
                Fixed params: 45 roots, 23 positive, 22 negative, all in
                [-2, 2]. Computed and asserted at import time.
                NOTE: the right-hand side drawn here is a representative value,
                NOT van Roomen's own constant (a nested radical, not reproduced
                here). The 23/22 split is asserted to hold for every right-hand
                side strictly between 0 and 2, so nothing on screen depends on
                which one was picked.

Everything numeric here is regenerated at import time from an integer Chebyshev
recurrence and checked against the published coefficients, so editing a number
without editing this docstring fails the render rather than quietly showing an
equation the narration contradicts. sympy is deliberately NOT imported: the
recurrence is exact, takes under a millisecond, and this module is imported by
template discovery on every smoke test.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math
from fractions import Fraction

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Dot,
    FadeIn,
    Line,
    MathTex,
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

_N = 45
_FACTORS = (3, 3, 5)


def _chebyshev_T(n):
    """Coefficients of T_n, ascending, by the integer recurrence."""
    a, b = [1], [0, 1]
    for _ in range(n - 1):
        c = [2 * v for v in ([0] + b)]
        for i, v in enumerate(a):
            c[i] -= v
        a, b = b, c
    return b


def _expansion(n):
    """Coefficients (ascending) of Q with 2 sin(n t) = Q(u), u = 2 sin t.

    For odd n, sin(n t) = (-1)^((n-1)/2) T_n(sin t); with n = 45 the sign is +1,
    so Q(u) = 2 T_45(u / 2).
    """
    assert n % 2 == 1
    assert (-1) ** ((n - 1) // 2) == 1, "the sign below assumes (n-1)/2 is even"
    t = _chebyshev_T(n)
    out = [Fraction(2 * c, 2**k) for k, c in enumerate(t)]
    assert all(v.denominator == 1 for v in out)
    return [int(v) for v in out]


_COEFFS = _expansion(_N)  # index = power of x

# The four low-order coefficients as van Roomen printed them.
assert _COEFFS[1] == 45
assert _COEFFS[3] == -3795
assert _COEFFS[5] == 95634
assert _COEFFS[7] == -1138500
assert _COEFFS[_N] == 1
# Only odd powers occur - the thing you can see at a glance.
assert all(_COEFFS[k] == 0 for k in range(0, _N + 1, 2))
assert math.prod(_FACTORS) == _N


def _roots(a):
    """The 45 roots of Q(x) = a, built from the angles rather than numerically.

    2 sin(45 s) = a means 45 s = theta + 2 pi k or 45 s = pi - theta + 2 pi k,
    with theta = arcsin(a / 2). Taking x = 2 sin s over both families and k in
    0..44 gives every root; the two families overlap in value, so they are
    deduplicated.
    """
    theta = math.asin(a / 2.0)
    seen = []
    for k in range(_N):
        for s in ((theta + 2 * math.pi * k) / _N, (math.pi - theta + 2 * math.pi * k) / _N):
            seen.append(2.0 * math.sin(s))
    seen.sort()
    out = []
    for v in seen:
        if not out or abs(v - out[-1]) > 1e-9:
            out.append(v)
    return out


# The right-hand side used for the picture. This is NOT van Roomen's own
# constant (his was a nested radical, and it is not reproduced here); it is a
# representative value chosen so the drawing is legible. That is sound only
# because the 23/22 split does not depend on it, which is asserted below rather
# than claimed in prose.
_A = 1.0
_ROOTS = _roots(_A)
_POS = [x for x in _ROOTS if x > 0]
_NEG = [x for x in _ROOTS if x < 0]

assert len(_ROOTS) == _N
assert len(_POS) == 23
assert len(_NEG) == 22
assert len(_POS) + len(_NEG) == _N
assert all(-2.0 <= x <= 2.0 for x in _ROOTS)

# The split is a property of the open interval, not of the value picked above:
# every a strictly between 0 and 2 gives 45 distinct roots, 23 of them positive.
# (At exactly a = 2 the roots pair up into double roots and only 23 distinct
# values remain, which is why the endpoint is excluded.)
for _i in (1, 7, 40, 199, 399):
    _r = _roots(2.0 * _i / 400.0)
    assert len(_r) == _N
    assert sum(1 for _x in _r if _x > 0) == 23
    assert sum(1 for _x in _r if _x < 0) == 22
assert len(_roots(2.0)) == 23  # degenerate endpoint, kept as a guard rail

# The lowest drawn text sits here (subtitle band starts at y = -2.0).
_BOTTOM_Y = -1.72


class Degree45Trigonometric(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "challenge")
        duration = params.get("duration", 26)
        if mode == "unfold":
            self._unfold(duration)
        elif mode == "roots":
            self._roots_mode(duration)
        else:
            self._challenge(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    # -- mode: challenge ------------------------------------------------------
    def _challenge(self, duration):
        title = self._title("1593年、世界中の数学者への挑戦")

        eq = MathTex(
            f"{_COEFFS[1]}x",
            f"{_COEFFS[3]}x^{{3}}",
            f"+{_COEFFS[5]}x^{{5}}",
            f"{_COEFFS[7]}x^{{7}}",
            r"+\;\cdots\;+",
            f"x^{{{_N}}}",
            r"\;=\;A",
            font_size=40,
        )
        eq[0].set_color(TEXT_WHITE)
        eq[1].set_color(TEXT_WHITE)
        eq[2].set_color(TEXT_WHITE)
        eq[3].set_color(TEXT_WHITE)
        eq[4].set_color(TEXT_DIM)
        eq[5].set_color(ACCENT_PINK)
        eq[6].set_color(ACCENT_CYAN)
        self._fit(eq, 12.4)
        eq.move_to(UP * 1.42)

        f1 = Text("次数は45", font=FONT, font_size=32, color=ACCENT_PINK)
        f1.move_to(UP * 0.10)

        f2 = Text("奇数乗しか出てこない", font=FONT, font_size=32, color=ACCENT_GOLD)
        f2.move_to(DOWN * 0.72)

        note = Text(
            "フランスには解ける者がいない、と大使は言った",
            font=FONT,
            font_size=29,
            color=TEXT_WHITE,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.6
        rt = pace(duration, [1.3, 0.9, 0.9, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(eq), run_time=rt[0])
        self.play(FadeIn(f1), run_time=rt[1])
        self.play(FadeIn(f2), run_time=rt[2])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(CODA)

    # -- mode: unfold ---------------------------------------------------------
    def _unfold(self, duration):
        title = self._title("それは、角を45等分する式だった")

        sub = MathTex(r"x \;=\; 2\sin\theta", font_size=44, color=ACCENT_GOLD)
        sub.move_to(UP * 1.86)

        becomes = MathTex(
            f"{_COEFFS[1]}x{_COEFFS[3]}x^{{3}}+\\cdots+x^{{{_N}}}",
            r"\;=\;",
            f"2\\sin {_N}\\theta",
            font_size=38,
        )
        becomes[0].set_color(TEXT_WHITE)
        becomes[1].set_color(TEXT_WHITE)
        becomes[2].set_color(ACCENT_PINK)
        self._fit(becomes, 12.0)
        becomes.move_to(UP * 0.66)

        # theta is already bound by `x = 2 sin(theta)` two lines up, so it must
        # NOT be the thing divided by 45. What the equation hands you is the
        # 45-FOLD angle: 2 sin(45 theta) equals the given number, so 45 theta is
        # known -- call it alpha -- and theta is alpha/45. Writing
        # `x = 2 sin(theta/45)` here (as this did) reads literally as
        # theta = theta/45. Caught by manim_vision_qa on an earlier episode build.
        answer = MathTex(
            r"45\theta \;=\; \alpha \;\Longrightarrow\; \theta \;=\; \dfrac{\alpha}{45}",
            font_size=42,
            color=ACCENT_CYAN,
        )
        self._fit(answer, 12.0)
        answer.move_to(DOWN * 0.62)

        fact = MathTex(
            f"{_N} \\;=\\; {_FACTORS[0]} \\times {_FACTORS[1]} \\times {_FACTORS[2]}",
            font_size=36,
            color=TEXT_WHITE,
        )
        fact.move_to(UP * _BOTTOM_Y)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.2, 1.1, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(sub), run_time=rt[0])
        self.play(FadeIn(becomes), run_time=rt[1])
        self.play(FadeIn(answer), run_time=rt[2])
        self.play(FadeIn(fact), run_time=rt[3])
        self.wait(CODA)

    # -- mode: roots ----------------------------------------------------------
    def _roots_mode(self, duration):
        title = self._title("持ち帰ったのは、23個")

        HALF = 5.7  # x = +-2 maps to +-HALF
        AXIS_Y = 0.72

        axis = Line(
            LEFT * HALF + UP * AXIS_Y,
            RIGHT * HALF + UP * AXIS_Y,
            color=EDGE_COLOR,
            stroke_width=2,
        )
        zero = Line(
            UP * (AXIS_Y + 0.30),
            UP * (AXIS_Y - 0.30),
            color=TEXT_DIM,
            stroke_width=2,
        )
        zero_lab = Text("0", font=FONT, font_size=24, color=TEXT_DIM)
        zero_lab.move_to(UP * (AXIS_Y - 0.58))

        def px(x):
            return RIGHT * (x / 2.0 * HALF) + UP * AXIS_Y

        neg_dots = VGroup(
            *[Dot(px(x), radius=0.075, color=TEXT_DIM).set_opacity(0.55) for x in _NEG]
        )
        pos_dots = VGroup(*[Dot(px(x), radius=0.085, color=ACCENT_GOLD) for x in _POS])

        neg_lab = Text(
            f"負の根 {len(_NEG)}個",
            font=FONT,
            font_size=29,
            color=TEXT_DIM,
        )
        neg_lab.move_to(LEFT * 3.15 + DOWN * 0.52)

        pos_lab = Text(
            f"正の根 {len(_POS)}個",
            font=FONT,
            font_size=29,
            color=ACCENT_GOLD,
        )
        pos_lab.move_to(RIGHT * 3.15 + DOWN * 0.52)

        note = Text(
            "彼にとって、負は根ではなかった",
            font=FONT,
            font_size=30,
            color=ACCENT_PINK,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.8
        rt = pace(duration, [0.9, 1.1, 0.9, 1.0, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(axis), FadeIn(zero), FadeIn(zero_lab), run_time=1.2)
        self.play(FadeIn(pos_dots), run_time=rt[0])
        self.play(FadeIn(pos_lab), run_time=rt[1])
        self.play(FadeIn(neg_dots), run_time=rt[2])
        self.play(FadeIn(neg_lab), run_time=rt[3])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(CODA)


# What each mode actually puts on screen (read by
# qa_manim_consistency.check_narration_names_absent_visual). The checker only
# compares against its own list of "promise" nouns (arrow, contour, polyline,
# bar chart, x-axis, y-axis, timeline, grid squares, lattice, coordinates), so
# the other words here are documentation of the frame rather than things that
# get matched. Declare what is really there either way: an entry that is missing
# is what lets a narration promise something the frame does not have.
LINT_VISUAL_ELEMENTS = {
    "challenge": ["式"],
    "unfold": ["式"],
    "roots": ["横軸", "点", "数直線"],
}

# No person names and no years appear on screen. The year 1593 is spoken in the
# 'challenge' title, so it is declared here.
LINT_FACTUAL_CLAIMS = {
    "challenge": {"people": [], "years": ["1593"]},
    "unfold": {"people": [], "years": []},
    "roots": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "challenge": Degree45Trigonometric,
    "unfold": Degree45Trigonometric,
    "roots": Degree45Trigonometric,
}
