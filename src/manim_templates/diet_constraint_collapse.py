"""
diet_constraint_collapse.py - The answer is only as sensible as the constraints

The first practical problem ever solved by the simplex method was a nutrition
problem: find the cheapest diet that meets the requirements. The system had 9
equations and 77 unknowns, nine clerks turned hand-cranked desk calculators for
about 120 days' worth of work, and the answer came out at $39.69 a year. That
scale is `table`.

`collapse` carries the point of the episode. A linear programme answers exactly
the question it was asked. Leave a condition out and the optimum sits somewhere
absurd - not because the arithmetic failed, but because nothing in the model
forbade it. As conditions are added the region closes and the optimal CORNER
walks in from the extreme towards something a person could actually eat. The
objective is never touched; only the constraints move.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    table    - The size of the 1947 computation and its answer.
               Fixed params: 9 nutrient conditions, 77 foods (20 columns are
               drawn, followed by an ellipsis), 9 clerks, 120 days' work,
               $39.69 a year.
    collapse - Three stages of the same minimisation. The horizontal axis is
               how much of one cheap item the diet leans on, the vertical axis
               is everything else, and the goal (fixed throughout) is to spend
               as little as possible.
               Fixed params: with the bulk condition alone the best corner is
               at (10, 0) - the far edge, everything from the one cheap item.
               Capping that item moves it to (6, 4). Adding a floor for the
               rest moves it to (4, 6). The cost of the optimum RISES at every
               stage, which is the honest shape of the thing: each condition
               you remembered to write makes the answer dearer and saner.
               These coordinates are schematic - they illustrate the mechanism,
               they are not the 1947 data - so no numbers are put on screen in
               this mode.

The polygons and the optimal corner of every stage in `collapse` are computed
here by intersecting the half-planes, not typed in, and checked with
assertions, so the drawing cannot drift away from the claim the narration
makes.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for both modes.

Reads params from _manim_params.json in the same directory.
"""

import itertools
import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Axes,
    DashedLine,
    Dot,
    FadeIn,
    Polygon,
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
# table: the 1947 computation (Dantzig, "The Diet Problem", Interfaces, 1990)
# ---------------------------------------------------------------------------
_N_CONDITIONS = 9
_N_FOODS = 77
_N_CLERKS = 9
_N_DAYS = 120
_ANSWER = "39ドル69セント"
_DRAWN_COLS = 20  # the rest of the 77 is carried by an ellipsis

# ---------------------------------------------------------------------------
# collapse: three nested feasible regions, all computed
# ---------------------------------------------------------------------------
_XMAX, _YMAX = 12.0, 8.0
# Rows are (a, b, c) meaning a*x + b*y <= c. The window is part of the system so
# that a region left open by the conditions still closes into a drawable polygon.
_WINDOW = [(-1.0, 0.0, 0.0), (1.0, 0.0, _XMAX), (0.0, -1.0, 0.0), (0.0, 1.0, _YMAX)]
_BULK = (-1.0, -1.0, -10.0)  # x + y >= 10   : the diet has to add up to something
_CAP = (1.0, 0.0, 6.0)  # x <= 6        : a ceiling on the one cheap item
_FLOOR = (0.0, -1.0, -6.0)  # y >= 6        : a floor for everything else
_STAGES = [
    _WINDOW + [_BULK],
    _WINDOW + [_BULK, _CAP],
    _WINDOW + [_BULK, _CAP, _FLOOR],
]
_COST = (0.2, 1.0)  # minimise 0.2x + y: the item on the x axis is the cheap one
_EPS = 1e-9


def _cost(pt):
    return _COST[0] * pt[0] + _COST[1] * pt[1]


def _polygon(rows):
    """Feasible intersection of the half-planes, as corners in drawing order."""
    found = []
    for (a1, b1, c1), (a2, b2, c2) in itertools.combinations(rows, 2):
        det = a1 * b2 - a2 * b1
        if abs(det) < _EPS:
            continue
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        if any(a * x + b * y > c + 1e-7 for a, b, c in rows):
            continue
        if not any(abs(x - u) < 1e-7 and abs(y - v) < 1e-7 for u, v in found):
            found.append((round(x, 9) + 0.0 or 0.0, round(y, 9) + 0.0 or 0.0))
    cx = sum(p[0] for p in found) / len(found)
    cy = sum(p[1] for p in found) / len(found)
    found.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    return found


_POLYS = [_polygon(rows) for rows in _STAGES]
_OPTIMA = [min(poly, key=_cost) for poly in _POLYS]
_OPT_COSTS = [_cost(p) for p in _OPTIMA]

# Fail loudly rather than render quietly wrong geometry (fail fast, no silent failures).
assert _OPTIMA == [(10.0, 0.0), (6.0, 4.0), (4.0, 6.0)]
assert all(_OPT_COSTS[i] < _OPT_COSTS[i + 1] for i in range(len(_OPT_COSTS) - 1))
# Each stage really is a tightening of the one before it.
assert all(
    all(a * x + b * y <= c + 1e-7 for a, b, c in _STAGES[i])
    for i in range(len(_STAGES) - 1)
    for x, y in _POLYS[i + 1]
)
# The first optimum sits on the far edge of the drawn window - that is the whole
# point of the first stage, so it must not quietly drift inwards.
assert _OPTIMA[0][0] >= _XMAX - 2.0 and _OPTIMA[0][1] == 0.0
assert _DRAWN_COLS < _N_FOODS


class DietConstraintCollapse(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "table")
        duration = params.get("duration", 26)
        if mode == "collapse":
            self._collapse(duration)
        else:
            self._table(duration)

    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    # -- mode: table ----------------------------------------------------------
    def _table(self, duration):
        title = self._title("必要な栄養を満たす、いちばん安い食事")

        cw, ch = 0.28, 0.22
        grid = VGroup()
        for r in range(_N_CONDITIONS):
            row = VGroup()
            for c in range(_DRAWN_COLS):
                sq = Square(side_length=0.155, stroke_width=1.1, color=EDGE_COLOR)
                sq.move_to(RIGHT * (c * cw) + DOWN * (r * ch))
                row.add(sq)
            more = Text("…", font=FONT, font_size=26, color=TEXT_DIM)
            more.move_to(RIGHT * (_DRAWN_COLS * cw + 0.16) + DOWN * (r * ch))
            row.add(more)
            grid.add(row)
        grid.move_to(UP * 1.52)

        rows_lab = Text(f"栄養の条件 {_N_CONDITIONS}本", font=FONT, font_size=26, color=ACCENT_CYAN)
        rows_lab.next_to(grid, LEFT, buff=0.42)
        cols_lab = Text(f"食品 {_N_FOODS}種類", font=FONT, font_size=26, color=ACCENT_CYAN)
        cols_lab.next_to(grid, DOWN, buff=0.34)

        how = VGroup(
            Text(f"事務員 {_N_CLERKS}人", font=FONT, font_size=27, color=TEXT_WHITE),
            Text("手回し計算機", font=FONT, font_size=27, color=TEXT_WHITE),
            Text(f"延べ{_N_DAYS}日", font=FONT, font_size=27, color=TEXT_WHITE),
        )
        how.arrange(RIGHT, buff=0.9)
        how.move_to(DOWN * 0.78)

        # y = -1.56 with a 40pt line leaves ~0.2 units of clearance over the
        # subtitle band at -2.0; at -1.72 the measured margin was 3 px.
        answer = Text(f"年間 {_ANSWER}", font=FONT, font_size=40, color=ACCENT_GOLD)
        answer.move_to(DOWN * 1.56)

        CODA = 2.6
        weights = [0.42] * _N_CONDITIONS + [0.7, 0.7, 0.7, 0.7, 1.0]
        rt = pace(duration, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(title), run_time=1.0)
        for i, row in enumerate(grid):
            self.play(FadeIn(row, lag_ratio=0.04), run_time=rt[i])
        k = _N_CONDITIONS
        self.play(FadeIn(rows_lab), run_time=rt[k])
        self.play(FadeIn(cols_lab), run_time=rt[k + 1])
        self.play(FadeIn(how[0]), FadeIn(how[1]), run_time=rt[k + 2])
        self.play(FadeIn(how[2]), run_time=rt[k + 3])
        self.play(FadeIn(answer), run_time=rt[k + 4])
        self.wait(CODA)

    # -- mode: collapse -------------------------------------------------------
    def _collapse(self, duration):
        title = self._title("式は変えていない。動いたのは制約だけ")

        axes = Axes(
            x_range=[0, _XMAX, 2],
            y_range=[0, _YMAX, 2],
            x_length=5.4,
            y_length=3.6,
            tips=False,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_ticks": True,
                "include_numbers": False,
            },
        )
        axes.move_to(LEFT * 2.75 + UP * 0.46)

        x_lab = Text("酢の量", font=FONT, font_size=23, color=TEXT_DIM)
        x_lab.next_to(axes, DOWN, buff=0.2)
        y_lab = Text("ほかの食品", font=FONT, font_size=23, color=TEXT_DIM)
        y_lab.rotate(math.pi / 2).next_to(axes, LEFT, buff=0.2)

        # The goal never changes, so its arrow is drawn once and never touched.
        #
        # It points toward MORE VINEGAR, not toward cheapness. This scene is
        # Dantzig's own diet, and there he replaced the objective: "the objective
        # function had to be changed (I wasn't interested in saving money) ...
        # maximize the feeling of feeling full", scored as a food's weight minus
        # the weight of its water (Dantzig 1990). The data listed vinegar's water
        # content as zero, so vinegar maximised that score and the optimum ran to
        # the all-vinegar corner.
        #
        # The arrow used to point down-left and read 安いほう, carried over from the
        # Stigler cost problem of the previous scene. That drew the wrong lesson on
        # screen -- it said the answer was vinegar because vinegar is cheap - and a
        # viewer asked exactly that question.
        goal = Arrow(
            axes.c2p(0.7, 1.15),
            axes.c2p(2.7, 1.15),
            buff=0,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.22,
            color=ACCENT_GOLD,
        )
        goal_lab = Text("満腹感が大きいほう", font=FONT, font_size=22, color=ACCENT_GOLD)
        goal_lab.next_to(goal, DOWN, buff=0.14)

        # What the corner of each stage MEANS belongs in this column, not floating
        # on the plot: a label pinned next to the moving dot is orphaned the moment
        # the dot leaves, and ends up naming empty space.
        rows = [
            ("栄養の条件だけ", "答えは酢だけ"),
            ("酢に上限を足す", ""),
            ("ほかの食品にも下限を足す", "食べられる献立へ"),
        ]
        captions = VGroup()
        for head, sub in rows:
            block = VGroup(Text(head, font=FONT, font_size=27, color=TEXT_WHITE))
            if sub:
                tail = Text(sub, font=FONT, font_size=23, color=ACCENT_PINK)
                tail.next_to(block[0], DOWN, buff=0.16, aligned_edge=LEFT)
                block.add(tail)
            captions.add(block)
        captions.arrange(DOWN, buff=0.42, aligned_edge=LEFT)
        captions.move_to(RIGHT * 3.4 + UP * 1.25)

        CODA = 2.8
        rt = pace(duration, [0.7, 0.6] + [1.35, 0.75] * len(_POLYS), intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(axes), run_time=1.2)
        self.play(FadeIn(x_lab), FadeIn(y_lab), run_time=rt[0])
        self.play(FadeIn(goal), FadeIn(goal_lab), run_time=rt[1])

        region = None
        dot = None
        for i, poly in enumerate(_POLYS):
            nxt = Polygon(
                *[axes.c2p(x, y) for x, y in poly],
                color=ACCENT_CYAN,
                fill_color=ACCENT_CYAN,
                fill_opacity=0.2,
                stroke_width=2.5,
            )
            if region is None:
                self.play(FadeIn(nxt), FadeIn(captions[i]), run_time=rt[2 + 2 * i])
            else:
                # The region tightens; the picture, not a caption, carries that.
                self.play(
                    region.animate.become(nxt),
                    FadeIn(captions[i]),
                    run_time=rt[2 + 2 * i],
                )
                nxt = region
            region = nxt

            target = axes.c2p(*_OPTIMA[i])
            if dot is None:
                dot = Dot(target, radius=0.12, color=ACCENT_PINK)
                self.play(FadeIn(dot), run_time=rt[3 + 2 * i])
            else:
                # A faint marker is left behind at each previous optimum, with a
                # dashed link, so that how FAR the answer travelled stays visible
                # once it has arrived somewhere sensible.
                ghost = Dot(
                    axes.c2p(*_OPTIMA[i - 1]),
                    radius=0.075,
                    color=ACCENT_PINK,
                    fill_opacity=0.4,
                )
                link = DashedLine(
                    axes.c2p(*_OPTIMA[i - 1]),
                    target,
                    color=ACCENT_PINK,
                    stroke_width=2,
                    stroke_opacity=0.5,
                    dash_length=0.1,
                )
                self.add(ghost, link)
                self.play(dot.animate.move_to(target), run_time=rt[3 + 2 * i])

        self.wait(CODA)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; the figures in `table` are the ones documented in the
# module docstring, and `collapse` puts no numbers on screen at all.
LINT_FACTUAL_CLAIMS = {
    "table": {"people": [], "years": []},
    "collapse": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "table": DietConstraintCollapse,
    "collapse": DietConstraintCollapse,
}
