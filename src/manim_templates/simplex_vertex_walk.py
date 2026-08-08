"""
simplex_vertex_walk.py - Why the best answer is always at a corner, and why
walking to it is still not obvious

A linear programme is a linear goal over a set carved out by linear
inequalities. Each inequality cuts the plane in half; the overlap is a
cornered region. Because the goal is linear too, its level lines are
parallel, so the last point the sweeping level line touches on its way out of
the region is a CORNER. The interior never has to be searched: infinitely many
candidates collapse onto finitely many corners.

That observation is easy, and Dantzig threw it away when he first had it in the
summer of 1947 - the corners are far too numerous to enumerate. The scene that
carries that objection is `explosion`. What rescued the idea was not a new
method but a change of viewpoint (he looked at the geometry of the columns
rather than of the rows), after which the walk turned out to finish in about as
many steps as there are equations.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

The worked instance is the same in the first three modes:

    maximise   z = 4x + 3y
    subject to 2x +  y <= 10
                x + 3y <= 15
                x       <=  4
                x >= 0,  y >= 0

Modes:
    feasible  - The three inequalities are drawn one at a time as lines; once
                all three are up, their overlap is shaded and its corners are
                marked and counted. The region is revealed whole at the end
                rather than shrinking line by line - watching an answer move as
                conditions are added is the job of diet_constraint_collapse.
                Fixed params: 5 corners at (0,0), (4,0), (4,2), (3,4), (0,5).
    contour   - The level line 4x + 3y = k slides outwards across the region
                with its value shown. It leaves the region at a single corner.
                Fixed params: the sweep runs k = 0 -> 24; the optimum is
                z = 24 at the corner (3, 4), and it is unique (no edge of the
                pentagon is parallel to the objective).
    walk      - The simplex walk itself, corner to corner along edges, with the
                objective value swapped in at each stop.
                Fixed params: (0,0) -> (4,0) -> (4,2) -> (3,4), i.e. 3 moves,
                z = 0 -> 16 -> 22 -> 24. There are 3 inequalities, which is the
                point: the walk lands in about as many steps as there are
                equations.
    explosion - The objection. Assigning 70 people to 70 jobs gives 140
                restrictions and 4900 person-job pairs but 70 factorial
                orderings. The screen is careful not to call the 4900 "ways":
                4900 counts the zero-one decision variables, and the ways are
                the factorial - calling both of them ways is exactly the
                confusion this scene exists to undo.
                Fixed params: 140 restrictions, 4900 pairs, 70! written out in
                full = 101 digits.

Every number on screen is recomputed at import time - the corners by
intersecting each pair of boundary lines and keeping the feasible ones, the
walk by actually walking it (greedy improvement to the best adjacent corner),
the factorial by math.factorial - and checked with assertions. Editing the
instance without editing the docstring makes the render fail rather than
quietly show numbers the narration contradicts.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

import itertools
import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    Scene,
    Text,
    ValueTracker,
    VGroup,
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
    pace,
)

config.background_color = BG_COLOR

# ---------------------------------------------------------------------------
# The instance, and everything derived from it, computed rather than typed.
# ---------------------------------------------------------------------------
# Each row is (a, b, c) meaning a*x + b*y <= c. The last two are x >= 0, y >= 0
# written as -x <= 0 and -y <= 0 so that one loop handles every boundary line.
_ROWS = [
    (2.0, 1.0, 10.0),
    (1.0, 3.0, 15.0),
    (1.0, 0.0, 4.0),
    (-1.0, 0.0, 0.0),
    (0.0, -1.0, 0.0),
]
_OBJ = (4.0, 3.0)  # maximise 4x + 3y
_EPS = 1e-9


def _z(pt):
    return _OBJ[0] * pt[0] + _OBJ[1] * pt[1]


def _feasible(pt):
    return all(a * pt[0] + b * pt[1] <= c + _EPS for a, b, c in _ROWS)


def _tight(pt):
    """Indices of the constraints the point sits exactly on."""
    return frozenset(
        i for i, (a, b, c) in enumerate(_ROWS) if abs(a * pt[0] + b * pt[1] - c) < 1e-7
    )


def _corners():
    """Every feasible intersection of two boundary lines, deduplicated."""
    found = []
    for (a1, b1, c1), (a2, b2, c2) in itertools.combinations(_ROWS, 2):
        det = a1 * b2 - a2 * b1
        if abs(det) < _EPS:
            continue
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        if not _feasible((x, y)):
            continue
        if not any(abs(x - u) < 1e-7 and abs(y - v) < 1e-7 for u, v in found):
            # Normalise -0.0 away: it compares equal to 0.0 but formats as "-0".
            found.append((round(x, 9) + 0.0 or 0.0, round(y, 9) + 0.0 or 0.0))
    # Order them the way the boundary runs, so the polygon draws without crossing.
    cx = sum(p[0] for p in found) / len(found)
    cy = sum(p[1] for p in found) / len(found)
    found.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    return found


_CORNERS = _corners()
_BEST = max(_CORNERS, key=_z)


def _neighbours(pt):
    """Corners joined to pt by an edge, i.e. sharing a tight constraint."""
    return [q for q in _CORNERS if q != pt and len(_tight(pt) & _tight(q)) >= 1]


def _greedy_walk(start=(0.0, 0.0)):
    """The path the scene draws, WALKED rather than typed in.

    From the origin, step to the adjacent corner that improves the objective the
    most and stop when no neighbour improves - which is Dantzig's rule read off
    the picture (entering the variable with the largest objective coefficient
    picks exactly this first move). Every step strictly increases z, so the loop
    cannot revisit a corner and always terminates.
    """
    cur = start
    path = [cur]
    while True:
        better = [q for q in _neighbours(cur) if _z(q) > _z(cur)]
        if not better:
            return path
        cur = max(better, key=_z)
        path.append(cur)


_WALK = _greedy_walk()
_WALK_Z = [_z(p) for p in _WALK]
_N_INEQ = 3  # the three real inequalities; the two sign conditions are not counted

_ASSIGN_N = 70
_ASSIGN_RESTRICTIONS = 2 * _ASSIGN_N
_ASSIGN_ACTIVITIES = _ASSIGN_N * _ASSIGN_N
_ASSIGN_ORDERINGS = str(math.factorial(_ASSIGN_N))

# Fail loudly rather than render quietly wrong numbers (fail fast, no silent failures).
assert _CORNERS == [(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (3.0, 4.0), (0.0, 5.0)]
assert [_z(p) for p in _CORNERS] == [0.0, 16.0, 22.0, 24.0, 15.0]
assert _BEST == (3.0, 4.0) and _z(_BEST) == 24.0
# The optimum is a single corner: no edge of the pentagon is level for the objective,
# so "the last point the level line touches" really is one point.
assert sum(1 for p in _CORNERS if abs(_z(p) - _z(_BEST)) < _EPS) == 1
# The walk is a walk: each stop is a corner, consecutive stops share a tight
# constraint (they are joined by an edge), and the objective strictly rises.
assert all(p in _CORNERS for p in _WALK)
assert all(len(_tight(_WALK[i]) & _tight(_WALK[i + 1])) >= 1 for i in range(len(_WALK) - 1))
assert all(_WALK_Z[i] < _WALK_Z[i + 1] for i in range(len(_WALK_Z) - 1))
assert _WALK[-1] == _BEST
assert _WALK == [(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (3.0, 4.0)]
assert _WALK_Z == [0.0, 16.0, 22.0, 24.0]
assert len(_WALK) - 1 == _N_INEQ  # 3 moves for 3 inequalities
assert (_ASSIGN_RESTRICTIONS, _ASSIGN_ACTIVITIES) == (140, 4900)
assert len(_ASSIGN_ORDERINGS) == 101


class SimplexVertexWalk(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "feasible")
        duration = params.get("duration", 28)
        if mode == "contour":
            self._contour(duration)
        elif mode == "walk":
            self._walk(duration)
        elif mode == "explosion":
            self._explosion(duration)
        else:
            self._feasible(duration)

    # -- shared plot ----------------------------------------------------------
    def _plot(self):
        """Axes on the left. Data x in [0,5], y in [0,6]; screen y stays >= -1.9.

        The tick numbers are drawn: without them "x <= 4" on the right-hand panel
        cannot be checked against the vertical line in the picture. The zero is
        dropped from both axes so the two of them do not print on top of each
        other at the origin, and the data all sits above the horizontal axis, so
        the x numbers have the strip below the axis to themselves.
        """
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 6, 1],
            x_length=5.3,
            y_length=3.7,
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
        )
        axes.move_to(LEFT * 2.75 + UP * 0.42)
        return axes

    def _boundary(self, axes, row, colour):
        """The line a*x + b*y = c, clipped to the drawn window."""
        a, b, c = row
        lo, hi = (0.0, 5.0), (0.0, 6.0)
        pts = []
        if abs(b) > _EPS:
            for x in (lo[0], lo[1]):
                y = (c - a * x) / b
                if hi[0] - 1e-9 <= y <= hi[1] + 1e-9:
                    pts.append((x, y))
        if abs(a) > _EPS:
            for y in (hi[0], hi[1]):
                x = (c - b * y) / a
                if lo[0] - 1e-9 <= x <= lo[1] + 1e-9:
                    pts.append((x, y))
        uniq = []
        for p in pts:
            if not any(abs(p[0] - q[0]) < 1e-7 and abs(p[1] - q[1]) < 1e-7 for q in uniq):
                uniq.append(p)
        return Line(axes.c2p(*uniq[0]), axes.c2p(*uniq[1]), color=colour, stroke_width=3)

    def _region(self, axes, opacity=0.22):
        return Polygon(
            *[axes.c2p(x, y) for x, y in _CORNERS],
            color=ACCENT_CYAN,
            fill_color=ACCENT_CYAN,
            fill_opacity=opacity,
            stroke_width=2.5,
        )

    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    # -- mode: feasible -------------------------------------------------------
    def _feasible(self, duration):
        axes = self._plot()
        title = self._title("条件の重なりが、角ばった領域を作る")

        ineqs = VGroup(
            MathTex(r"2x + y \le 10", font_size=32, color=TEXT_WHITE),
            MathTex(r"x + 3y \le 15", font_size=32, color=TEXT_WHITE),
            MathTex(r"x \le 4", font_size=32, color=TEXT_WHITE),
        )
        ineqs.arrange(DOWN, buff=0.42, aligned_edge=LEFT)
        ineqs.move_to(RIGHT * 3.6 + UP * 1.62)

        signs = MathTex(r"x \ge 0, \; y \ge 0", font_size=26, color=TEXT_DIM)
        signs.next_to(ineqs, DOWN, buff=0.5)

        lines = [self._boundary(axes, _ROWS[i], ACCENT_PINK) for i in range(3)]
        region = self._region(axes)
        caption = Text("実行可能領域", font=FONT, font_size=25, color=ACCENT_CYAN)
        caption.move_to(RIGHT * 3.6 + DOWN * 0.72)
        count = Text(f"角は{len(_CORNERS)}つ", font=FONT, font_size=27, color=ACCENT_GOLD)
        count.move_to(RIGHT * 3.6 + DOWN * 1.42)

        dots = VGroup(*[Dot(axes.c2p(x, y), radius=0.075, color=ACCENT_GOLD) for x, y in _CORNERS])

        CODA = 2.5
        rt = pace(duration, [0.9, 1.0, 1.0, 1.0, 0.5, 1.1, 0.9], intro=1.1, coda=CODA)
        self.play(FadeIn(title), FadeIn(axes), run_time=1.1)
        self.play(Create(lines[0]), FadeIn(ineqs[0]), run_time=rt[0])
        self.play(Create(lines[1]), FadeIn(ineqs[1]), run_time=rt[1])
        self.play(Create(lines[2]), FadeIn(ineqs[2]), run_time=rt[2])
        self.play(FadeIn(signs), run_time=rt[3])
        self.play(FadeIn(region), FadeIn(caption), run_time=rt[4])
        self.play(FadeIn(dots, lag_ratio=0.25), run_time=rt[5])
        self.play(FadeIn(count), run_time=rt[6])
        self.wait(CODA)

    # -- mode: contour --------------------------------------------------------
    def _contour(self, duration):
        axes = self._plot()
        title = self._title("一番良い答えは、必ず角にある")
        region = self._region(axes, opacity=0.18)
        dots = VGroup(*[Dot(axes.c2p(x, y), radius=0.07, color=TEXT_DIM) for x, y in _CORNERS])

        obj = MathTex(r"z = 4x + 3y", font_size=34, color=ACCENT_GOLD)
        obj.move_to(RIGHT * 3.6 + UP * 1.9)
        note = Text("等高線を、外へずらしていく", font=FONT, font_size=24, color=TEXT_DIM)
        note.move_to(RIGHT * 3.6 + UP * 1.1)

        a, b = _OBJ
        k = ValueTracker(0.0)

        def level():
            """The segment 4x + 3y = k inside the drawn window."""
            v = k.get_value()
            pts = []
            for x in (0.0, 5.0):
                y = (v - a * x) / b
                if -1e-9 <= y <= 6.0 + 1e-9:
                    pts.append((x, y))
            for y in (0.0, 6.0):
                x = (v - b * y) / a
                if -1e-9 <= x <= 5.0 + 1e-9:
                    pts.append((x, y))
            uniq = []
            for p in pts:
                if not any(abs(p[0] - q[0]) < 1e-7 and abs(p[1] - q[1]) < 1e-7 for q in uniq):
                    uniq.append(p)
            if len(uniq) < 2:
                uniq = [(0.0, 0.0), (0.0, 0.0)]
            return Line(axes.c2p(*uniq[0]), axes.c2p(*uniq[1]), color=ACCENT_PINK, stroke_width=4)

        sweep = level()
        sweep.add_updater(lambda m: m.become(level()))

        readout = MathTex(r"z = 0", font_size=32, color=ACCENT_PINK)
        readout.move_to(RIGHT * 3.6 + UP * 0.3)

        def refresh(m):
            m.become(
                MathTex(rf"z = {k.get_value():.0f}", font_size=32, color=ACCENT_PINK).move_to(
                    RIGHT * 3.6 + UP * 0.3
                )
            )

        readout.add_updater(refresh)

        CODA = 3.0
        rt = pace(duration, [0.7, 0.5, 3.4, 0.8, 0.9], intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(axes), FadeIn(region), run_time=1.2)
        self.play(FadeIn(dots), FadeIn(obj), run_time=rt[0])
        self.play(FadeIn(note), FadeIn(sweep), FadeIn(readout), run_time=rt[1])
        # The whole slack of the scene goes into the sweep, so nothing stands still.
        self.play(k.animate.set_value(_z(_BEST)), run_time=rt[2], rate_func=linear)
        sweep.clear_updaters()
        readout.clear_updaters()

        hit = Dot(axes.c2p(*_BEST), radius=0.11, color=ACCENT_GOLD)
        halo = Dot(axes.c2p(*_BEST), radius=0.2, color=ACCENT_GOLD, fill_opacity=0.28)
        last = Text("最後に触れたのは、角", font=FONT, font_size=26, color=ACCENT_GOLD)
        last.move_to(RIGHT * 3.6 + DOWN * 0.55)
        best = MathTex(rf"({_BEST[0]:.0f},\, {_BEST[1]:.0f})", font_size=32, color=ACCENT_GOLD)
        best.move_to(RIGHT * 3.6 + DOWN * 1.3)

        self.play(FadeIn(halo), FadeIn(hit), run_time=rt[3])
        self.play(FadeIn(last), FadeIn(best), run_time=rt[4])
        self.wait(CODA)

    # -- mode: walk -----------------------------------------------------------
    def _walk(self, duration):
        axes = self._plot()
        title = self._title("角から角へ、辺を伝って歩く")
        region = self._region(axes, opacity=0.16)
        dots = VGroup(*[Dot(axes.c2p(x, y), radius=0.07, color=TEXT_DIM) for x, y in _CORNERS])

        obj = MathTex(r"z = 4x + 3y", font_size=32, color=TEXT_DIM)
        obj.move_to(RIGHT * 3.6 + UP * 2.15)

        walker = Dot(axes.c2p(*_WALK[0]), radius=0.12, color=ACCENT_PINK)

        def value_label(v):
            return MathTex(rf"z = {v:.0f}", font_size=40, color=ACCENT_PINK).move_to(
                RIGHT * 3.6 + UP * 1.35
            )

        readout = value_label(_WALK_Z[0])

        steps = VGroup()
        for i, v in enumerate(_WALK_Z):
            steps.add(
                MathTex(
                    rf"({_WALK[i][0]:.0f},\, {_WALK[i][1]:.0f}) \;\to\; {v:.0f}",
                    font_size=26,
                    color=TEXT_DIM,
                )
            )
        steps.arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        steps.move_to(RIGHT * 3.6 + DOWN * 0.25)

        CODA = 2.8
        weights = [0.7, 0.5] + [1.25] * (len(_WALK) - 1) + [0.9]
        rt = pace(duration, weights, intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(axes), FadeIn(region), run_time=1.2)
        self.play(FadeIn(dots), FadeIn(obj), run_time=rt[0])
        self.play(FadeIn(walker), FadeIn(readout), FadeIn(steps[0]), run_time=rt[1])

        trail = VGroup()
        for i in range(len(_WALK) - 1):
            edge = Line(
                axes.c2p(*_WALK[i]),
                axes.c2p(*_WALK[i + 1]),
                color=ACCENT_PINK,
                stroke_width=6,
            )
            trail.add(edge)
            self.play(
                Create(edge),
                walker.animate.move_to(axes.c2p(*_WALK[i + 1])),
                run_time=rt[2 + i],
            )
            # A number that changes is swapped, never tweened: an animated
            # hand-over leaves both readings overlapping for the whole play.
            nxt = value_label(_WALK_Z[i + 1])
            self.remove(readout)
            self.add(nxt)
            readout = nxt
            self.add(steps[i + 1])

        # Kept in the right-hand column: the strip under the plot now carries the
        # x-axis numbers, and a caption centred there would sit on top of them.
        done = Text(
            f"式は{_N_INEQ}本、乗り換えも{len(_WALK) - 1}回",
            font=FONT,
            font_size=25,
            color=ACCENT_GOLD,
        )
        done.move_to(RIGHT * 3.6 + DOWN * 1.62)
        self.play(FadeIn(done), run_time=rt[-1])
        self.wait(CODA)

    # -- mode: explosion ------------------------------------------------------
    def _explosion(self, duration):
        title = self._title("70人を、70の仕事に割り当てる")

        facts = VGroup(
            Text(f"条件は{_ASSIGN_RESTRICTIONS}本", font=FONT, font_size=28, color=TEXT_WHITE),
            # Not "4900 ways": 4900 is the number of person-job pairs (the zero-one
            # decision variables). The WAYS are the 70 factorial orderings, and
            # calling both of them "ways" is the confusion this scene exists to undo.
            Text(f"人と仕事の組は{_ASSIGN_ACTIVITIES}", font=FONT, font_size=28, color=TEXT_WHITE),
            Text("並べ方は70の階乗", font=FONT, font_size=28, color=ACCENT_CYAN),
        )
        facts.arrange(RIGHT, buff=0.95)
        facts.move_to(UP * 2.16)
        if facts.width > 12.4:
            facts.scale_to_fit_width(12.4)

        chunk = 26
        rows = [_ASSIGN_ORDERINGS[i : i + chunk] for i in range(0, len(_ASSIGN_ORDERINGS), chunk)]
        digits = VGroup(*[Text(r, font=FONT, font_size=34, color=ACCENT_GOLD) for r in rows])
        for row in digits:
            if row.width > 10.6:
                row.scale_to_fit_width(10.6)
        digits.arrange(DOWN, buff=0.3)
        digits.move_to(UP * 0.36)

        size = Text(f"{len(_ASSIGN_ORDERINGS)}桁の数", font=FONT, font_size=32, color=ACCENT_PINK)
        size.move_to(DOWN * 1.42)

        CODA = 2.6
        rt = pace(duration, [0.8, 0.8, 0.8] + [0.85] * len(rows) + [1.0], intro=1.0, coda=CODA)
        self.play(FadeIn(title), run_time=1.0)
        for i in range(3):
            self.play(FadeIn(facts[i]), run_time=rt[i])
        for i, row in enumerate(digits):
            self.play(FadeIn(row), run_time=rt[3 + i])
        self.play(FadeIn(size), run_time=rt[-1])
        self.wait(CODA)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; every number shown is derived from the instance in the
# module docstring and asserted at import time.
LINT_FACTUAL_CLAIMS = {
    "feasible": {"people": [], "years": []},
    "contour": {"people": [], "years": []},
    "walk": {"people": [], "years": []},
    "explosion": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "feasible": SimplexVertexWalk,
    "contour": SimplexVertexWalk,
    "walk": SimplexVertexWalk,
    "explosion": SimplexVertexWalk,
}
