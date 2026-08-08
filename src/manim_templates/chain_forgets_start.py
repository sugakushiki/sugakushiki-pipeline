"""
chain_forgets_start.py - Why giving up independence does not cost you the law of
large numbers

Markov's answer to the claim that the law of large numbers REQUIRES independence
was a counterexample, and the counterexample is as small as a counterexample can
be: two states, and a rule that looks only one step back. What comes next depends
on the state you are in now and on nothing before it.

The point of the second mode is that such a chain FORGETS WHERE IT STARTED. Run
it from the vowel state and from the consonant state and the two answers to "is
step k a vowel?" swing past each other, closing in on one value. After about
eight steps they are indistinguishable. The long-run share does not depend on the
starting point - which is exactly what it means for the law of large numbers to
survive without independence.

The value they close in on is worth the payoff: feeding Markov's own two measured
chances into the chain gives 0.4319, and the average he measured by hand over two
hundred blocks of a hundred letters was 43.19 vowels per hundred. The theory
points at the number the counting found.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    two_state - The rule itself: two states, four arrows, each arrow labelled
                with its chance. The caption says what the rule leaves out -
                anything before the current state.
                Fixed params: 0.128 / 0.872 out of the vowel state, 0.663 /
                0.337 out of the consonant state; the two pairs each sum to 1.
    converge  - The forgetting, drawn. Two lines, one starting at 1 (began on a
                vowel) and one at 0 (began on a consonant), plotted for nine
                steps against the settled value. They oscillate towards it from
                opposite sides and are within 0.01 of each other by step eight.
                Fixed params: settled value 0.4319, nine steps plotted, and the
                measured average 43.19 vowels per hundred letters shown last.

The transition numbers are Markov's published estimates; the settled value, the
two sequences and the step at which they meet are all computed at import time and
asserted, so editing a number without editing this docstring makes the render
fail rather than quietly show a curve the narration contradicts.

Geometry note (found by rendering, not by reading the code): a self-loop drawn
with ArcBetweenPoints bulges to the LEFT of the start-to-end direction, so the
loop endpoints must be placed symmetrically about the OUTWARD direction and the
angle must be NEGATIVE. Getting either wrong draws the loop straight through the
node and its label. The two helpers below are measured: every point of a loop
lies between 0.85 and 1.58 from the node centre, i.e. on or outside the circle.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    ArcBetweenPoints,
    Axes,
    Circle,
    Create,
    CurvedArrow,
    DashedLine,
    Dot,
    FadeIn,
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

# ---------------------------------------------------------------------------
# Markov's two measured chances, and everything derived from them.
# ---------------------------------------------------------------------------
_P_VV = 0.128  # vowel   -> vowel
_P_CV = 0.663  # consonant -> vowel
_P_VC = 1.0 - _P_VV
_P_CC = 1.0 - _P_CV

# The settled (stationary) share of vowels. Solving pi = pi * P for two states.
_SETTLED = _P_CV / (1.0 - _P_VV + _P_CV)

_STEPS = 9  # k = 0 .. 8


def _run(start_is_vowel):
    """Chance that step k is a vowel, given where the chain started."""
    v = 1.0 if start_is_vowel else 0.0
    out = []
    for _ in range(_STEPS):
        out.append(v)
        v = v * _P_VV + (1.0 - v) * _P_CV
    return out


_FROM_V = _run(True)
_FROM_C = _run(False)

# The step by which the two runs are indistinguishable on this plot.
_MEET = next(
    k for k in range(_STEPS) if all(abs(_FROM_V[j] - _FROM_C[j]) < 0.01 for j in range(k, _STEPS))
)

# The hand count this is supposed to land on: 43.19 vowels per hundred letters.
_MEASURED_PER_HUNDRED = 43.19

# The lowest drawn text sits here. Japanese glyphs hang about 0.17 below the
# centre they are placed at and the subtitle band starts at y = -2.0, so a
# caption centred lower than this breaches it - by a handful of pixels, which is
# not something the eye catches (it was found by measuring rendered frames).
_BOTTOM_Y = -1.72

_NODE_R = 0.85

# Fail loudly rather than render quietly wrong numbers (fail fast, no silent failures).
assert abs(_P_VV + _P_VC - 1.0) < 1e-12
assert abs(_P_CV + _P_CC - 1.0) < 1e-12
assert round(_SETTLED, 4) == 0.4319
# The theory lands on the measurement.
assert abs(_SETTLED * 100.0 - _MEASURED_PER_HUNDRED) < 0.01
# The two runs really do start apart, really do straddle the settled value, and
# really do close up - the three things the picture claims.
assert _FROM_V[0] == 1.0 and _FROM_C[0] == 0.0
assert all(
    (_FROM_V[k] - _SETTLED) * (_FROM_C[k] - _SETTLED) < 0 for k in range(1, _STEPS)
)  # opposite sides at every step after the first
assert all(
    abs(_FROM_V[k + 1] - _SETTLED) < abs(_FROM_V[k] - _SETTLED) for k in range(_STEPS - 1)
)  # monotonically closer, even though it oscillates
assert _MEET == 8


def _loop_endpoints(centre, out_deg):
    """The two points where a self-loop meets its node, straddling `out_deg`."""
    pts = []
    for d in (out_deg + 25.0, out_deg - 25.0):
        r = math.radians(d)
        pts.append(centre + np.array([_NODE_R * math.cos(r), _NODE_R * math.sin(r), 0.0]))
    return pts


def _loop_reaches_outward(out_deg):
    """Check that the loop lies on or outside the node - measured, not assumed."""
    a, b = _loop_endpoints(np.zeros(3), out_deg)
    pts = ArcBetweenPoints(a, b, angle=-4.6).get_all_points()
    return float(np.linalg.norm(pts[:, :2], axis=1).min())


# Both loops attach at the circle and bulge away from it, never through it.
assert abs(_loop_reaches_outward(180.0) - _NODE_R) < 1e-6
assert abs(_loop_reaches_outward(0.0) - _NODE_R) < 1e-6


class ChainForgetsStart(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "two_state")
        duration = params.get("duration", 26)
        if mode == "converge":
            self._converge(duration)
        else:
            self._two_state(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, group, width):
        if group.width > width:
            group.scale_to_fit_width(width)
        return group

    def _self_loop(self, circle, out_deg, colour, width):
        a, b = _loop_endpoints(circle.get_center(), out_deg)
        loop = ArcBetweenPoints(a, b, angle=-4.6, color=colour, stroke_width=width)
        loop.add_tip(tip_length=0.2)
        return loop

    # -- mode: two_state ------------------------------------------------------
    def _two_state(self, duration):
        title = self._title("次に来るものは、直前だけで決まる")

        NODE_Y = 0.60
        left = Circle(radius=_NODE_R, color=ACCENT_GOLD, stroke_width=3)
        left.set_fill(ACCENT_GOLD, opacity=0.16)
        left.move_to(LEFT * 2.9 + UP * NODE_Y)
        right = Circle(radius=_NODE_R, color=TEXT_WHITE, stroke_width=3)
        right.set_fill(TEXT_WHITE, opacity=0.1)
        right.move_to(RIGHT * 2.9 + UP * NODE_Y)

        lab_l = Text("母音", font=FONT, font_size=30, color=ACCENT_GOLD).move_to(left)
        lab_r = Text("子音", font=FONT, font_size=30, color=TEXT_WHITE).move_to(right)

        loop_v = self._self_loop(left, 180.0, ACCENT_GOLD, 4)
        loop_c = self._self_loop(right, 0.0, TEXT_WHITE, 4)

        # The crossing arrows arc gently: a fat arc reaches up into the title and
        # leaves nowhere to put its own label.
        cross_cv = CurvedArrow(
            right.get_top(),
            left.get_top(),
            angle=0.6,
            color=ACCENT_PINK,
            stroke_width=5,
            tip_length=0.24,
        )
        cross_vc = CurvedArrow(
            left.get_bottom(),
            right.get_bottom(),
            angle=0.6,
            color=ACCENT_CYAN,
            stroke_width=5,
            tip_length=0.24,
        )

        # Labels go clear of their arcs rather than on top of them.
        n_vv = Text(f"{_P_VV:.3f}", font=FONT, font_size=27, color=ACCENT_GOLD)
        n_vv.move_to(LEFT * 5.35 + UP * NODE_Y)
        n_cc = Text(f"{_P_CC:.3f}", font=FONT, font_size=27, color=TEXT_WHITE)
        n_cc.move_to(RIGHT * 5.35 + UP * NODE_Y)
        n_cv = Text(f"{_P_CV:.3f}", font=FONT, font_size=27, color=ACCENT_PINK)
        n_cv.next_to(cross_cv, UP, buff=0.2)
        n_vc = Text(f"{_P_VC:.3f}", font=FONT, font_size=27, color=ACCENT_CYAN)
        n_vc.next_to(cross_vc, DOWN, buff=0.2)

        rule = Text(
            "それより前のことは、一切問わない",
            font=FONT,
            font_size=29,
            color=ACCENT_CYAN,
        )
        rule.move_to(UP * _BOTTOM_Y)
        self._fit(rule, 12.4)

        CODA = 2.6
        rt = pace(duration, [0.9, 1.1, 1.1, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(left), FadeIn(right), run_time=1.2)
        self.play(FadeIn(lab_l), FadeIn(lab_r), run_time=rt[0])
        self.play(FadeIn(cross_vc), FadeIn(n_vc), FadeIn(cross_cv), FadeIn(n_cv), run_time=rt[1])
        self.play(FadeIn(loop_v), FadeIn(n_vv), FadeIn(loop_c), FadeIn(n_cc), run_time=rt[2])
        self.play(FadeIn(rule), run_time=rt[3])
        self.wait(CODA)

    # -- mode: converge -------------------------------------------------------
    def _converge(self, duration):
        title = self._title("どこから始めても、同じ値に落ち着く")

        axes = Axes(
            x_range=[0, _STEPS - 1, 1],
            y_range=[0, 1, 0.25],
            x_length=8.2,
            y_length=3.5,
            tips=False,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_ticks": True,
                "include_numbers": True,
                "numbers_to_exclude": [0],
                "font_size": 20,
                "decimal_number_config": {"num_decimal_places": 0},
            },
            y_axis_config={"decimal_number_config": {"num_decimal_places": 2}},
        )
        axes.move_to(LEFT * 1.35 + UP * 0.62)

        # Just past the right-hand end of the axis, level with it. Placed under
        # the plot it lands on top of the closing caption (that is what happened).
        x_lab = Text("手数", font=FONT, font_size=23, color=TEXT_DIM)
        x_lab.next_to(axes.x_axis, RIGHT, buff=0.28)

        settled = DashedLine(
            axes.c2p(0, _SETTLED),
            axes.c2p(_STEPS - 1, _SETTLED),
            color=ACCENT_GOLD,
            stroke_width=3,
            dash_length=0.13,
        )
        settled_lab = Text(f"{_SETTLED:.4f}", font=FONT, font_size=27, color=ACCENT_GOLD)
        settled_lab.move_to(RIGHT * 4.55 + UP * 0.72)

        head = Text("その手が母音である確率", font=FONT, font_size=23, color=TEXT_DIM)
        head.move_to(RIGHT * 4.55 + UP * 2.42)
        self._fit(head, 3.9)

        key_v = Text("母音から出発", font=FONT, font_size=23, color=ACCENT_PINK)
        key_v.move_to(RIGHT * 4.55 + UP * 1.72)
        key_c = Text("子音から出発", font=FONT, font_size=23, color=ACCENT_CYAN)
        key_c.move_to(RIGHT * 4.55 + UP * 1.22)

        dots_v = VGroup(
            *[Dot(axes.c2p(k, y), radius=0.075, color=ACCENT_PINK) for k, y in enumerate(_FROM_V)]
        )
        dots_c = VGroup(
            *[Dot(axes.c2p(k, y), radius=0.075, color=ACCENT_CYAN) for k, y in enumerate(_FROM_C)]
        )

        meet = Text(
            f"{_MEET}手で、ほとんど重なる",
            font=FONT,
            font_size=25,
            color=TEXT_WHITE,
        )
        meet.move_to(RIGHT * 4.55 + DOWN * 0.35)
        self._fit(meet, 4.1)

        payoff = Text(
            f"手で数えた平均は、100文字あたり{_MEASURED_PER_HUNDRED}",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        payoff.move_to(UP * _BOTTOM_Y)
        self._fit(payoff, 12.4)

        CODA = 2.8
        # The slack goes into stepping the chain forward, one step at a time, so
        # the scene keeps moving instead of standing still at the end.
        weights = [0.7, 0.6] + [0.85] * (_STEPS - 1) + [0.7, 1.0]
        rt = pace(duration, weights, intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(axes), FadeIn(x_lab), run_time=1.2)
        self.play(FadeIn(head), FadeIn(key_v), FadeIn(key_c), run_time=rt[0])
        self.play(FadeIn(dots_v[0]), FadeIn(dots_c[0]), run_time=rt[1])

        for k in range(_STEPS - 1):
            seg_v = axes.plot_line_graph(
                x_values=[k, k + 1],
                y_values=[_FROM_V[k], _FROM_V[k + 1]],
                line_color=ACCENT_PINK,
                add_vertex_dots=False,
                stroke_width=4,
            )
            seg_c = axes.plot_line_graph(
                x_values=[k, k + 1],
                y_values=[_FROM_C[k], _FROM_C[k + 1]],
                line_color=ACCENT_CYAN,
                add_vertex_dots=False,
                stroke_width=4,
            )
            self.play(
                Create(seg_v),
                Create(seg_c),
                FadeIn(dots_v[k + 1]),
                FadeIn(dots_c[k + 1]),
                run_time=rt[2 + k],
            )
            if k == 0:
                # Drawn once the two runs are on their way, so the settled value
                # reads as where they are heading rather than as a given.
                self.add(settled, settled_lab)

        self.play(FadeIn(meet), run_time=rt[-2])
        self.play(FadeIn(payoff), run_time=rt[-1])
        self.wait(CODA)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; every number shown is derived from Markov's two measured
# chances and asserted at import time.
# What each mode actually puts on screen, so a narration that promises something
# else can be caught before the build ships (read by
# qa_manim_consistency.check_narration_names_absent_visual). An earlier episode shipped a cut
# where the narration described the four arrows while `converge` was on screen.
LINT_VISUAL_ELEMENTS = {
    "two_state": ["矢印", "状態", "確率"],
    "converge": ["縦軸", "横軸", "折れ線", "点", "破線"],
}

LINT_FACTUAL_CLAIMS = {
    "two_state": {"people": [], "years": []},
    "converge": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "two_state": ChainForgetsStart,
    "converge": ChainForgetsStart,
}
