"""
kakeya_dimension.py - when the area is gone, what is left to measure

Besicovitch pushed the area of a Kakeya region as low as anyone likes, so
"how small is the area" stops being a question with an answer. The question
that survives is a different one: is such a set actually THIN? Area is not
the only way to ask. A set can hold every direction and still have area
zero - a plain bundle of segments already does - and yet be far from
one-dimensional.

The measure that answers this counts boxes. Cover the set with a grid of
cell size epsilon and count the cells it touches. If halving epsilon doubles
the count, the set behaves like a line; if it quadruples it, like a surface.
The exponent in that growth is the dimension, and it is what the modern
Kakeya problem is about.

The counts drawn in mode 'box_count' are exact, not sketched. Both objects
sit in the unit square with a corner on the origin and side 3/4, and the
grid is aligned to the origin, so:

    segment (length 3/4)   epsilon = 1/4, 1/8, 1/16  ->  N =  3,  6,  12
    square  (side 3/4)     epsilon = 1/4, 1/8, 1/16  ->  N =  9, 36, 144

Halving epsilon multiplies the segment's count by exactly 2 and the square's
by exactly 4: log2 of those factors is 1 and 2, the dimensions of a line and
of a patch of plane.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    zero_area  - The contrast the narration draws. LEFT: the folded Perron
                 tree with a needle in it -- a region the needle can be
                 TURNED in, whose area can be made small but never zero.
                 RIGHT: 24 unit segments covering every direction, moved
                 apart so they share no point -- a set that merely CONTAINS
                 every direction, and whose area is zero.
                 Fixed params: 8 Perron pieces on the left, 24 segments of
                 length 1 on the right at deterministic offsets, colours
                 running cyan to pink.
    box_count  - The measuring rule. Left a segment, right a filled square,
                 both under grids of cell size 1/4, then 1/8, then 1/16,
                 with the touched cells lit and counted.
                 Fixed params: side 3/4 for both; counts 3/6/12 and
                 9/36/144 as above; factors 2 and 4 per halving.
    conjecture - Where the Kakeya set stands. The claim (a set holding a
                 unit segment in every direction of d-space has dimension d)
                 and the state of play: the plane settled in 1971, three
                 dimensions in 2025, four and up still open.
                 Fixed params: 3 rows; years 1971 and 2025 on screen.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    FadeIn,
    Indicate,
    Line,
    ManimColor,
    Polygon,
    Rectangle,
    Scene,
    Text,
    VGroup,
    config,
    interpolate_color,
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

_BOTTOM_Y = -1.75
_TITLE_Y = 3.06

_MODES = ("zero_area", "box_count", "conjecture")
_DEFAULT_MODE = "box_count"
assert _DEFAULT_MODE in _MODES

_FAN_N = 24
_SIDE = 0.75  # side of both objects in mode box_count
_EPS = (0.25, 0.125, 0.0625)
# Exact because the objects and the grid share the origin and 3/4 is a
# multiple of every epsilon used.
_N_SEG = tuple(int(round(_SIDE / e)) for e in _EPS)
_N_SQ = tuple(int(round((_SIDE / e) ** 2)) for e in _EPS)
assert _N_SEG == (3, 6, 12), _N_SEG
assert _N_SQ == (9, 36, 144), _N_SQ


def _ramp(i, n):
    # interpolate_color needs ManimColor objects; style.py exports hex strings.
    return interpolate_color(ManimColor(ACCENT_CYAN), ManimColor(ACCENT_PINK), i / max(n - 1, 1))


class KakeyaDimension(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"kakeya_dimension: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 30)
        if mode == "zero_area":
            self._zero_area(duration)
        elif mode == "conjecture":
            self._conjecture(duration)
        else:
            self._box_count(duration)

    # -- shared ------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * _TITLE_Y)
        return self._fit(t, 12.6)

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    def _note(self, s, color=TEXT_WHITE, y=_BOTTOM_Y, font_size=28):
        t = Text(s, font=FONT, font_size=font_size, color=color)
        t.move_to(UP * y)
        return self._fit(t, 12.6)

    def _reveal(self, *mobjects, run_time):
        fade = min(min(max(run_time * 0.30, 0.7), 1.4), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _pulse(self, m, run_time, color, extras=()):
        """FadeIn then Indicate, as SEPARATE plays."""
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.5, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    # -- mode: zero_area ---------------------------------------------------
    def _zero_area(self, duration):
        """The distinction the narration is actually making.

        Manim Vision QA (an earlier episode first build) rejected the first version twice,
        and both objections were right: (a) it drew only ONE side of a
        narration whose whole point is a contrast, and (b) drawing every
        segment through one common centre made a dense radial star whose
        middle reads as a filled disc -- the picture contradicted its own
        "area 0" label. So: two panels, and on the right the segments are
        TRANSLATED apart so no point is shared and the set stays visibly
        full of holes.
        """
        title = self._title("回せることと、含んでいること")
        lx, rx, cy = -3.40, 3.55, 0.70

        # LEFT: a region a needle can actually be turned in. It is the Perron
        # tree the audience has just watched being folded, so the two scenes
        # are the same object.
        from perron_tree import _perron_stages

        stage = _perron_stages()[-1]
        pts = np.concatenate(stage, axis=0)
        w = float(pts[:, 0].max() - pts[:, 0].min())
        h = float(pts[:, 1].max() - pts[:, 1].min())
        k = min(2.30 / max(w, 1e-6), 2.35 / max(h, 1e-6))
        cx = float((pts[:, 0].max() + pts[:, 0].min()) / 2.0)
        cyy = float((pts[:, 1].max() + pts[:, 1].min()) / 2.0)

        def L(q):
            return np.array([(q[0] - cx) * k + lx, (q[1] - cyy) * k + cy, 0.0])

        left_shape = VGroup(
            *[
                Polygon(
                    *[L(q) for q in tri],
                    color=ACCENT_CYAN,
                    stroke_width=1.4,
                    fill_color=ACCENT_CYAN,
                    fill_opacity=0.22,
                )
                for tri in stage
            ]
        )
        spine = stage[3]
        needle = Line(
            L((spine[0] + spine[1]) / 2.0), L(spine[2]), color=ACCENT_GOLD, stroke_width=5.0
        )

        # RIGHT: every direction, but the segments are moved apart. Deterministic
        # offsets (no RNG) so the picture is reproducible run to run.
        segs = []
        for i in range(_FAN_N):
            a = np.pi * i / _FAN_N
            u = np.array([np.cos(a), np.sin(a), 0.0])
            ox = 1.30 * np.cos(2.399 * i + 0.7)
            oy = 1.05 * np.sin(1.732 * i + 0.3)
            c = np.array([rx + ox, cy + oy, 0.0])
            segs.append(Line(c - 0.62 * u, c + 0.62 * u, color=_ramp(i, _FAN_N), stroke_width=2.2))

        head_l = Text("回せる図形", font=FONT, font_size=29, color=ACCENT_CYAN)
        head_l.move_to(np.array([lx, 2.42, 0.0]))
        head_r = Text("向きを含むだけの集合", font=FONT, font_size=29, color=ACCENT_PINK)
        head_r.move_to(np.array([rx, 2.42, 0.0]))
        sub_l = Text(
            "面積は小さくできる ── でも 0 にはできない", font=FONT, font_size=24, color=TEXT_DIM
        )
        sub_l.move_to(np.array([lx, -1.12, 0.0]))
        self._fit(sub_l, 5.85)
        sub_r = Text("面積 0", font=FONT, font_size=30, color=ACCENT_PINK)
        sub_r.move_to(np.array([rx, -1.12, 0.0]))
        note = self._note("下限は 0、しかし 0 は達成されません", color=ACCENT_GOLD)

        batch = 4
        groups = [segs[i : i + batch] for i in range(0, _FAN_N, batch)]
        CODA = 2.6
        weights = [1.4, 1.0] + [0.9] * len(groups) + [1.0, 1.3]
        rt = pace(duration, weights, intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        self._reveal(left_shape, needle, head_l, run_time=rt[0])
        self._reveal(sub_l, run_time=rt[1])
        for i, grp in enumerate(groups):
            extras = (head_r,) if i == 0 else ()
            self._reveal(*grp, *extras, run_time=rt[2 + i])
        n = 2 + len(groups)
        self._pulse(sub_r, run_time=rt[n], color=ACCENT_PINK)
        self._reveal(note, run_time=rt[n + 1])
        self.wait(CODA)

    # -- mode: box_count ---------------------------------------------------
    def _box_count(self, duration):
        title = self._title("太さは、覆う箱の数で測る")
        span = 2.55  # the unit square becomes this wide
        lefts = (np.array([-3.45, 0.72, 0.0]), np.array([3.45, 0.72, 0.0]))

        def cell(panel, i, j, eps, color, opacity):
            s = span * eps
            r = Rectangle(width=s, height=s, stroke_width=0.0)
            r.set_fill(color, opacity=opacity)
            r.move_to(
                panel + np.array([(i + 0.5) * s - span / 2.0, (j + 0.5) * s - span / 2.0, 0.0])
            )
            return r

        def grid(panel, eps):
            n = int(round(1.0 / eps))
            g = VGroup()
            for k in range(n + 1):
                t = -span / 2.0 + k * span / n
                g.add(
                    Line(
                        panel + np.array([t, -span / 2.0, 0.0]),
                        panel + np.array([t, span / 2.0, 0.0]),
                        color=EDGE_COLOR,
                        stroke_width=1.0,
                    )
                )
                g.add(
                    Line(
                        panel + np.array([-span / 2.0, t, 0.0]),
                        panel + np.array([span / 2.0, t, 0.0]),
                        color=EDGE_COLOR,
                        stroke_width=1.0,
                    )
                )
            return g

        # the two objects: a segment and a filled square, both of side 3/4
        p0 = lefts[0] + np.array([-span / 2.0, -span / 2.0, 0.0])
        seg = Line(
            p0 + np.array([0.0, span * 0.53125, 0.0]),
            p0 + np.array([span * _SIDE, span * 0.53125, 0.0]),
            color=ACCENT_CYAN,
            stroke_width=5.0,
        )
        sq = Rectangle(width=span * _SIDE, height=span * _SIDE, stroke_width=2.0)
        sq.set_stroke(ACCENT_PINK).set_fill(ACCENT_PINK, opacity=0.22)
        sq.move_to(
            lefts[1]
            + np.array([-span / 2.0 + span * _SIDE / 2.0, -span / 2.0 + span * _SIDE / 2.0, 0.0])
        )

        name_l = Text("線", font=FONT, font_size=30, color=ACCENT_CYAN)
        name_l.move_to(lefts[0] + np.array([0.0, span / 2.0 + 0.42, 0.0]))
        name_r = Text("面", font=FONT, font_size=30, color=ACCENT_PINK)
        name_r.move_to(lefts[1] + np.array([0.0, span / 2.0 + 0.42, 0.0]))

        CODA = 2.6
        weights = [1.0] + [1.25, 0.5] * len(_EPS) + [1.2]
        rt = pace(duration, weights, intro=1.1, coda=CODA)

        self.play(FadeIn(title), run_time=1.1)
        self._reveal(seg, sq, name_l, name_r, run_time=rt[0])

        k = 1
        prev = []
        count_l = None
        count_r = None
        for gi, eps in enumerate(_EPS):
            n = int(round(1.0 / eps))
            row = int(np.floor(0.53125 / eps))
            lit_l = VGroup(
                *[cell(lefts[0], i, row, eps, ACCENT_CYAN, 0.55) for i in range(int(_SIDE * n))]
            )
            m = int(round(_SIDE * n))
            lit_r = VGroup(
                *[cell(lefts[1], i, j, eps, ACCENT_PINK, 0.45) for i in range(m) for j in range(m)]
            )
            g_l = grid(lefts[0], eps)
            g_r = grid(lefts[1], eps)
            for old in prev:
                self.remove(old)
            prev = [g_l, g_r, lit_l, lit_r]
            self.play(
                AnimationGroup(
                    FadeIn(g_l), FadeIn(g_r), FadeIn(lit_l), FadeIn(lit_r), lag_ratio=0.0
                ),
                run_time=rt[k],
            )
            k += 1
            new_l = Text(f"{_N_SEG[gi]} 個", font=FONT, font_size=30, color=ACCENT_CYAN)
            new_l.move_to(lefts[0] + np.array([0.0, -span / 2.0 - 0.58, 0.0]))
            new_r = Text(f"{_N_SQ[gi]} 個", font=FONT, font_size=30, color=ACCENT_PINK)
            new_r.move_to(lefts[1] + np.array([0.0, -span / 2.0 - 0.58, 0.0]))
            self.play(FadeIn(new_l), FadeIn(new_r), run_time=min(0.5, rt[k]))
            if count_l is not None:
                self.remove(count_l, count_r)
            count_l, count_r = new_l, new_r
            if rt[k] > 0.55:
                self.wait(rt[k] - 0.5)
            k += 1

        note = self._note("ます目を半分にすると 線は 2 倍、面は 4 倍", color=ACCENT_GOLD)
        self._reveal(note, run_time=rt[k])
        self.wait(CODA)

    # -- mode: conjecture --------------------------------------------------
    def _conjecture(self, duration):
        title = self._title("残った問いは、次元だった")
        claim = Text(
            "あらゆる向きの線分を含む図形の次元は、その空間の次元に等しい",
            font=FONT,
            font_size=29,
            color=TEXT_WHITE,
        )
        claim.move_to(np.array([0.0, 2.18, 0.0]))
        self._fit(claim, 12.4)

        rows = (
            ("平面", "1971 年に決着", ACCENT_CYAN),
            ("3 次元", "2025 年に証明が公表", ACCENT_GOLD),
            ("4 次元以上", "未解決", ACCENT_PINK),
        )
        ys = (1.10, 0.10, -0.90)
        blocks = []
        for (head, body, color), y in zip(rows, ys, strict=True):
            bar = Line(
                np.array([-1.55, y, 0.0]),
                np.array([-0.95, y, 0.0]),
                color=color,
                stroke_width=3.0,
            )
            # anchor both texts to the bar so the column edges line up
            h = Text(head, font=FONT, font_size=30, color=color)
            h.next_to(bar, LEFT, buff=0.45)
            b = Text(body, font=FONT, font_size=30, color=TEXT_DIM)
            b.next_to(bar, RIGHT, buff=0.45)
            blocks.append(VGroup(h, bar, b))

        note = self._note("面積が消えたあとに、この問いが残りました", color=TEXT_DIM)

        CODA = 2.6
        weights = [1.2, 1.0, 1.0, 1.0, 1.0]
        rt = pace(duration, weights, intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        self._reveal(claim, run_time=rt[0])
        for i, blk in enumerate(blocks):
            self._reveal(blk, run_time=rt[1 + i])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)


# What each mode puts on screen.
LINT_VISUAL_ELEMENTS = {
    "zero_area": ["線", "線分", "向き", "三角形"],
    "box_count": ["ます目", "格子", "線", "面", "四角"],
    "conjecture": ["線", "文字"],
}

# Only 'conjecture' puts years on screen. No person names anywhere.
LINT_FACTUAL_CLAIMS = {
    "zero_area": {"people": [], "years": []},
    "box_count": {"people": [], "years": []},
    "conjecture": {"people": [], "years": ["1971", "2025"]},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, KakeyaDimension)
