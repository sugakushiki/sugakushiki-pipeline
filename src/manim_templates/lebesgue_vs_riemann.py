"""
lebesgue_vs_riemann.py - What changes when you cut the other way

Riemann fixes the integral by cutting the DOMAIN: tall thin strips stand side by
side under the curve, and you add width times height. Lebesgue cut the RANGE
instead: gather the points where the function takes roughly one value, measure
how big that SET is, and add height times size. The picture flips from upright
strips to flat layers, which is why the narration must say "domain" and "range"
and never "vertical" or "horizontal" on its own - said alone those words land on
the viewer the wrong way round.

The reason for the change was not elegance. Riemann's integral does not survive
a limit: mode 'escape' shows a sequence that stays inside Riemann's reach at
every step and whose limit falls straight out of it. Mode 'dirichlet' is the
same limit seen with a measure in hand, where the set of rationals has size zero
and the integral is zero, so the limit and the integral finally commute.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    vertical   - Riemann. The domain is cut into 14 equal pieces and 14 upright
                 strips are drawn under one fixed curve.
                 Fixed params: 14 strips, midpoint heights, curve
                 F(t) = 0.22 + 0.62 sin(2 pi t)^2 on t in [0, 1].
    horizontal - Lebesgue. The same curve, the range cut into 6 levels, one band
                 picked out, and the set of t landing in that band marked on the
                 domain axis. The band is chosen so that set is FOUR separate
                 pieces, not an interval - that is the whole reason a notion of
                 size is needed.
                 Fixed params: 6 level lines, band [0.50, 0.62], 4 preimage
                 pieces (asserted at import time).
    coins      - The metaphor from his 1926 Copenhagen lecture. Ten coins
                 counted in the order they came to hand, against the same ten
                 sorted into stacks of 5, 3 and 2 by denomination.
                 Fixed params: 10 coins, 3 denominations, 5 + 3 + 2 = 10
                 (asserted at import time).
    escape     - Why the integral had to be rebuilt. f_n is 1 on the first n
                 rationals of [0, 1] and 0 elsewhere. Every f_n is Riemann
                 integrable with integral 0; the pointwise limit is not Riemann
                 integrable at all.
                 Fixed params: stages n = 1, 3, 8, 24, rationals enumerated by
                 increasing denominator (1/2, 1/3, 2/3, 1/4, 3/4, ...).
    dirichlet  - The same limit with a measure in hand. Upper sum 1, lower sum
                 0, so Riemann cannot decide; the rationals have size 0, so the
                 Lebesgue integral is 0 and the limit commutes.
                 Fixed params: 90 rationals drawn, upper 1 / lower 0.

'escape' and 'dirichlet' are a pair and must be used in that order: the first is
the problem, the second is the payoff. Do NOT illustrate the problem with a
moving spike - the spike defeats Lebesgue too, so it would show a limit that
never commutes rather than one that starts to.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Circle,
    Dot,
    FadeIn,
    Line,
    Rectangle,
    Scene,
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
    pace,
)

config.background_color = BG_COLOR

# ---------------------------------------------------------------------------
# One curve, used by both cutting modes so the two pictures are comparable.
# Two humps, so a mid-height band meets it in four separate pieces.
# ---------------------------------------------------------------------------
_PLOT_X0, _PLOT_X1 = -5.2, 5.2
_PLOT_YB, _PLOT_YT = -1.15, 2.45  # screen y for value 0 and value 1


def _F(t):
    return 0.22 + 0.62 * math.sin(2.0 * math.pi * t) ** 2


def _P(t, v):
    """Curve coordinates -> screen coordinates."""
    return np.array(
        [
            _PLOT_X0 + (_PLOT_X1 - _PLOT_X0) * t,
            _PLOT_YB + (_PLOT_YT - _PLOT_YB) * v,
            0.0,
        ]
    )


_STRIPS = 14
_BAND_LO, _BAND_HI = 0.50, 0.62
_LEVELS = 6


def _preimage_pieces(lo, hi, samples=4000):
    """The t-intervals where lo <= F(t) <= hi, as (start, end) pairs."""
    pieces = []
    start = None
    for i in range(samples + 1):
        t = i / samples
        inside = lo <= _F(t) <= hi
        if inside and start is None:
            start = t
        elif not inside and start is not None:
            pieces.append((start, (i - 1) / samples))
            start = None
    if start is not None:
        pieces.append((start, 1.0))
    return pieces


_PIECES = _preimage_pieces(_BAND_LO, _BAND_HI)

# Fail loudly rather than render a picture the narration contradicts: the point
# of the band is that its preimage is NOT an interval.
assert len(_PIECES) == 4, _PIECES
assert 0.0 < _F(0.25) <= 1.0 and abs(_F(0.25) - 0.84) < 1e-9
assert _F(0.0) == _F(0.5) == _F(1.0)

# Coins: the same ten, counted two ways.
_COIN_STACKS = (5, 3, 2)
_COIN_TOTAL = 10
assert sum(_COIN_STACKS) == _COIN_TOTAL
_COIN_COLORS = (ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK)
assert len(_COIN_COLORS) == len(_COIN_STACKS)


def _rationals(n):
    """The first n rationals of (0, 1), by increasing denominator."""
    out = []
    q = 2
    while len(out) < n:
        for p in range(1, q):
            if math.gcd(p, q) == 1:
                out.append(p / q)
                if len(out) == n:
                    break
        q += 1
    return out


assert _rationals(5) == [1 / 2, 1 / 3, 2 / 3, 1 / 4, 3 / 4]

_ESCAPE_STAGES = (1, 3, 8, 24)
_DIRICHLET_DOTS = 90

# The single source of truth for the mode names. construct() validates against
# it and SCENES is built from it, so the dispatch and the registry cannot drift.
_MODES = ("vertical", "horizontal", "coins", "escape", "dirichlet")
_DEFAULT_MODE = "vertical"
assert _DEFAULT_MODE in _MODES

# The lowest drawn text sits here. Japanese glyphs hang about 0.17 below the
# centre they are placed at and the subtitle band starts at y = -2.0.
_BOTTOM_Y = -1.72


class LebesgueVsRiemann(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # A mode name that does not exist used to fall through to the default and
        # render the WRONG picture in silence. An earlier episode's generated script asked for
        # 'riemann' and 'lebesgue'; both fell through to 'vertical', so the scene
        # whose narration says "the range is cut, the strips lie down" would have
        # shipped showing upright strips. Nothing downstream catches that - the
        # check only warns when mode is MISSING. Fail loudly instead: a raise here fails the render and raises the pipeline's
        # placeholder banner.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"lebesgue_vs_riemann: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "horizontal":
            self._horizontal(duration)
        elif mode == "coins":
            self._coins(duration)
        elif mode == "escape":
            self._escape(duration)
        elif mode == "dirichlet":
            self._dirichlet(duration)
        else:
            self._vertical(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    def _note(self, s, color=TEXT_WHITE, y=_BOTTOM_Y, font_size=29):
        t = Text(s, font=FONT, font_size=font_size, color=color)
        t.move_to(UP * y)
        return self._fit(t, 12.4)

    def _reveal(self, *mobjects, run_time):
        """FadeIn crisply, then hold for the rest of this step's budget.

        pace() hands out one step of the scene, and these scenes really run 40-60
        seconds (median 41s over the last twelve episodes; 53% at or above 40s),
        so one step is 6-9 seconds. Handing that straight to FadeIn on Japanese
        text leaves the line at half opacity for almost all of it, and it only
        becomes readable as the narration moves on - an earlier episode trap. Spend a
        capped slice on the fade and give the remainder back as a wait.

        fade + rest == run_time exactly, so the step consumes what pace() gave it
        and the scene cannot overrun.

        Shapes are NOT put through this: axes, curves, strips and bands read well
        appearing slowly, and leaving them on the long fade keeps the frame from
        going still for the whole hold.
        """
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        # When the leftover would be too small to be worth a wait() call, spend
        # it on the fade instead of dropping it, so fade + rest == run_time for
        # EVERY run_time. Dropping it silently shortened the step by up to 0.05s
        # (reachable: a weight-0.8 step of 'decreasing' at a ~10.6s scene).
        if run_time - fade <= 0.05:
            fade = run_time
        # run_time is deliberately NOT passed to self.play(): it would rescale
        # every child animation and undo the cap.
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _frame(self):
        """Domain axis along the bottom, value axis up the left."""
        x_axis = Line(
            _P(0, 0) + LEFT * 0.34,
            _P(1, 0) + RIGHT * 0.34,
            color=EDGE_COLOR,
            stroke_width=3,
        )
        y_axis = Line(
            _P(0, 0) + DOWN * 0.16,
            _P(0, 1) + UP * 0.16,
            color=EDGE_COLOR,
            stroke_width=3,
        )
        return VGroup(x_axis, y_axis)

    def _curve(self, color=TEXT_WHITE, stroke_width=4, samples=260):
        m = VMobject(color=color, stroke_width=stroke_width)
        m.set_points_as_corners([_P(i / samples, _F(i / samples)) for i in range(samples + 1)])
        return m

    # -- mode: vertical (Riemann) ---------------------------------------------
    def _vertical(self, duration):
        title = self._title("定義域を刻む")
        frame = self._frame()
        curve = self._curve()

        strips = VGroup()
        for i in range(_STRIPS):
            t0, t1 = i / _STRIPS, (i + 1) / _STRIPS
            v = _F((t0 + t1) / 2.0)
            left = _P(t0, 0)[0]
            right = _P(t1, 0)[0]
            top = _P(0, v)[1]
            r = Rectangle(
                width=right - left,
                height=top - _PLOT_YB,
                color=ACCENT_CYAN,
                stroke_width=1.6,
            )
            r.set_fill(ACCENT_CYAN, opacity=0.22)
            r.move_to(np.array([(left + right) / 2.0, (_PLOT_YB + top) / 2.0, 0.0]))
            strips.add(r)

        note = self._note("幅と高さを掛けて、足していく", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.3, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(frame), FadeIn(curve), run_time=rt[0])
        self.play(FadeIn(strips), run_time=rt[1])
        self._reveal(note, run_time=rt[2])
        self.wait(CODA)

    # -- mode: horizontal (Lebesgue) ------------------------------------------
    def _horizontal(self, duration):
        title = self._title("値域を刻む")
        frame = self._frame()
        curve = self._curve(color=TEXT_DIM, stroke_width=3)

        levels = VGroup()
        for k in range(1, _LEVELS + 1):
            v = k / _LEVELS
            levels.add(
                Line(_P(0, v), _P(1, v), color=EDGE_COLOR, stroke_width=1.6).set_stroke(opacity=0.7)
            )

        band = Rectangle(
            width=_PLOT_X1 - _PLOT_X0,
            height=_P(0, _BAND_HI)[1] - _P(0, _BAND_LO)[1],
            color=ACCENT_CYAN,
            stroke_width=0,
        )
        band.set_fill(ACCENT_CYAN, opacity=0.26)
        band.move_to(
            np.array(
                [
                    (_PLOT_X0 + _PLOT_X1) / 2.0,
                    (_P(0, _BAND_LO)[1] + _P(0, _BAND_HI)[1]) / 2.0,
                    0.0,
                ]
            )
        )

        # The four pieces of the domain that land in the band. This is what gets
        # measured, and it is the reason "length" had to be defined first.
        marks = VGroup()
        for t0, t1 in _PIECES:
            marks.add(Line(_P(t0, 0), _P(t1, 0), color=ACCENT_GOLD, stroke_width=9))

        label = Text(
            "この値をとる点の集合",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        )
        # Sits in the empty band between the curve's trough (value 0.22, y=-0.36)
        # and the domain axis (y=-1.15). Hung BELOW the axis it landed on top of
        # the bottom note - found by rendering, not by reading.
        label.move_to(UP * -0.80)
        self._fit(label, 6.4)

        note = self._note("その集合の大きさを、先に測る", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 0.9, 0.9, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(frame), FadeIn(curve), run_time=rt[0])
        self.play(FadeIn(levels), run_time=rt[1])
        self.play(FadeIn(band), run_time=rt[2])
        # The gold marks are a shape but they land WITH their label, so the pair
        # goes through _reveal together - otherwise the label would still crawl.
        self._reveal(marks, label, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: coins ----------------------------------------------------------
    def _coins(self, duration):
        title = self._title("数える順序を変える")

        left_head = Text("手に取った順に", font=FONT, font_size=28, color=TEXT_WHITE)
        left_head.move_to(np.array([-3.55, 2.10, 0.0]))

        # The same ten coins, in the order they came to hand.
        order = []
        for idx, count in enumerate(_COIN_STACKS):
            order.extend([idx] * count)
        shuffled = [order[(i * 7 + 3) % _COIN_TOTAL] for i in range(_COIN_TOTAL)]
        assert sorted(shuffled) == sorted(order)

        loose = VGroup()
        for i, kind in enumerate(shuffled):
            c = Circle(radius=0.17, color=_COIN_COLORS[kind], stroke_width=3)
            c.set_fill(_COIN_COLORS[kind], opacity=0.30)
            c.move_to(np.array([-6.00 + i * 0.545, 1.30, 0.0]))
            loose.add(c)

        left_note = Text("一枚ずつ足していく", font=FONT, font_size=26, color=TEXT_DIM)
        left_note.move_to(np.array([-3.55, 0.52, 0.0]))

        divider = Line(
            np.array([-0.10, 1.95, 0.0]),
            np.array([-0.10, -1.15, 0.0]),
            color=EDGE_COLOR,
            stroke_width=2,
        ).set_stroke(opacity=0.6)

        right_head = Text("同じ額面ごとに", font=FONT, font_size=28, color=TEXT_WHITE)
        right_head.move_to(np.array([3.30, 2.10, 0.0]))

        stacks = VGroup()
        counts = VGroup()
        for idx, count in enumerate(_COIN_STACKS):
            x = 1.55 + idx * 1.75
            for j in range(count):
                c = Circle(radius=0.17, color=_COIN_COLORS[idx], stroke_width=3)
                c.set_fill(_COIN_COLORS[idx], opacity=0.30)
                c.move_to(np.array([x, -0.42 + j * 0.33, 0.0]))
                stacks.add(c)
            n = Text(str(count), font=FONT, font_size=26, color=_COIN_COLORS[idx])
            n.move_to(np.array([x, -0.98, 0.0]))
            counts.add(n)

        note = self._note("答えは同じ。数える順序だけが違う", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 0.8, 0.9, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        # Every step here carries a caption, so all of them are capped.
        self._reveal(left_head, loose, run_time=rt[0])
        self._reveal(left_note, divider, run_time=rt[1])
        self._reveal(right_head, run_time=rt[2])
        self._reveal(stacks, counts, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- modes: escape / dirichlet --------------------------------------------
    def _number_line(self, y):
        return Line(
            np.array([_PLOT_X0 - 0.34, y, 0.0]),
            np.array([_PLOT_X1 + 0.34, y, 0.0]),
            color=EDGE_COLOR,
            stroke_width=3,
        )

    def _ones_row(self, values, y, color=ACCENT_CYAN, radius=0.055):
        g = VGroup()
        for v in values:
            d = Dot(
                np.array([_PLOT_X0 + (_PLOT_X1 - _PLOT_X0) * v, y, 0.0]),
                radius=radius,
                color=color,
            )
            g.add(d)
        return g

    def _escape(self, duration):
        title = self._title("極限が、リーマンの外へ出る")

        base_y = -0.58
        one_y = 1.32
        base = self._number_line(base_y)
        zero_line = Line(
            np.array([_PLOT_X0, base_y, 0.0]),
            np.array([_PLOT_X1, base_y, 0.0]),
            color=TEXT_WHITE,
            stroke_width=5,
        )
        one_mark = Line(
            np.array([_PLOT_X0 - 0.34, one_y, 0.0]),
            np.array([_PLOT_X1 + 0.34, one_y, 0.0]),
            color=EDGE_COLOR,
            stroke_width=1.6,
        ).set_stroke(opacity=0.55)
        one_label = Text("1", font=FONT, font_size=24, color=TEXT_DIM)
        one_label.move_to(np.array([_PLOT_X0 - 0.62, one_y, 0.0]))
        zero_label = Text("0", font=FONT, font_size=24, color=TEXT_DIM)
        zero_label.move_to(np.array([_PLOT_X0 - 0.62, base_y, 0.0]))

        stage_rows = [self._ones_row(_rationals(n), one_y) for n in _ESCAPE_STAGES]
        stage_caps = []
        for n in _ESCAPE_STAGES:
            c = Text(f"有理数を{n}個だけ1にする", font=FONT, font_size=27, color=TEXT_WHITE)
            c.move_to(UP * 2.22)
            stage_caps.append(self._fit(c, 9.0))

        mid = Text("どの段階でも積分できて、答えは0", font=FONT, font_size=27, color=ACCENT_CYAN)
        mid.move_to(np.array([0.0, 0.36, 0.0]))
        self._fit(mid, 11.0)

        note = self._note("極限は、リーマンでは積分できない", color=ACCENT_PINK)

        CODA = 2.6
        weights = [1.0] + [0.85] * len(_ESCAPE_STAGES) + [1.0, 1.0]
        rt = pace(duration, weights, intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(base, zero_line, one_mark, one_label, zero_label, run_time=rt[0])
        shown_cap = None
        shown_row = None
        for i in range(len(_ESCAPE_STAGES)):
            anims = [FadeIn(stage_rows[i], run_time=rt[1 + i])]
            if shown_cap is None:
                anims.append(FadeIn(stage_caps[i], run_time=0.5))
            else:
                # Text swaps are kept short on purpose: a multi-second run_time
                # on Japanese glyphs shows them half-formed for seconds.
                anims.append(FadeIn(stage_caps[i], run_time=0.5))
                anims.append(shown_cap.animate(run_time=0.4).set_opacity(0.0))
                anims.append(shown_row.animate(run_time=0.4).set_opacity(0.35))
            self.play(*anims)
            shown_cap = stage_caps[i]
            shown_row = stage_rows[i]
        self._reveal(mid, run_time=rt[1 + len(_ESCAPE_STAGES)])
        self._reveal(note, run_time=rt[2 + len(_ESCAPE_STAGES)])
        self.wait(CODA)

    def _dirichlet(self, duration):
        title = self._title("測れるなら、積分できる")

        base_y = 0.92
        one_y = 2.06
        base = self._number_line(base_y)
        zero_line = Line(
            np.array([_PLOT_X0, base_y, 0.0]),
            np.array([_PLOT_X1, base_y, 0.0]),
            color=TEXT_WHITE,
            stroke_width=5,
        )
        one_mark = Line(
            np.array([_PLOT_X0 - 0.34, one_y, 0.0]),
            np.array([_PLOT_X1 + 0.34, one_y, 0.0]),
            color=EDGE_COLOR,
            stroke_width=1.6,
        ).set_stroke(opacity=0.55)
        # Without these the two rows are just an unlabelled line and a scatter of
        # dots; the viewer cannot tell that one row is the value 1 and the other 0.
        one_label = Text("1", font=FONT, font_size=24, color=TEXT_DIM)
        one_label.move_to(np.array([_PLOT_X0 - 0.62, one_y, 0.0]))
        zero_label = Text("0", font=FONT, font_size=24, color=TEXT_DIM)
        zero_label.move_to(np.array([_PLOT_X0 - 0.62, base_y, 0.0]))
        dots = self._ones_row(_rationals(_DIRICHLET_DOTS), one_y, radius=0.048)

        riemann = Text(
            "リーマン ── 上からは1、下からは0。決まらない",
            font=FONT,
            font_size=28,
            color=ACCENT_PINK,
        )
        riemann.move_to(np.array([0.0, 0.02, 0.0]))
        self._fit(riemann, 12.4)

        lebesgue = Text(
            "ルベーグ ── 有理数全体の大きさは0。積分は0",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        lebesgue.move_to(np.array([0.0, -0.84, 0.0]))
        self._fit(lebesgue, 12.4)

        note = self._note("極限と積分が、入れ替わる", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.0, 1.0, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(base, zero_line, one_mark, one_label, zero_label, run_time=rt[0])
        # The dots are the only pure-shape step here, so they keep the long fade
        # and give the scene some motion between the capped caption reveals.
        self.play(FadeIn(dots), run_time=rt[1])
        self._reveal(riemann, run_time=rt[2])
        self._reveal(lebesgue, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)


# What each mode actually puts on screen, so a narration that promises something
# else can be caught before the build ships (read by
# qa_manim_consistency.check_narration_names_absent_visual). The checker matches
# only its own list of "promise" nouns (arrow, contour, polyline, bar chart,
# x-axis, y-axis, timeline, grid, lattice, coordinates); the rest documents the
# frame. Note that no mode draws an arrow, so a narration saying 矢印 over any of
# these will be caught.
LINT_VISUAL_ELEMENTS = {
    "vertical": ["横軸", "縦軸", "曲線", "短冊"],
    "horizontal": ["横軸", "縦軸", "曲線", "帯", "線分"],
    "coins": ["硬貨", "積み上げ"],
    "escape": ["横軸", "点"],
    "dirichlet": ["横軸", "点"],
}

# Only two names ever reach the screen, both in the verdict rows of 'dirichlet'
# and one in the title of 'escape'. No years are shown in any mode.
LINT_FACTUAL_CLAIMS = {
    "vertical": {"people": [], "years": []},
    "horizontal": {"people": [], "years": []},
    "coins": {"people": [], "years": []},
    "escape": {"people": [["リーマン", "Riemann"]], "years": []},
    "dirichlet": {
        "people": [["リーマン", "Riemann"], ["ルベーグ", "Lebesgue"]],
        "years": [],
    },
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, LebesgueVsRiemann)
