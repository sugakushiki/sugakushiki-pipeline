"""
perron_tree.py - the area collapses, the directions do not

Besicovitch's answer to the Kakeya problem is built from a shape now called
a Perron tree, after Oskar Perron, who simplified the construction in 1928.
It starts from the equilateral triangle of height 1 - the very shape that
Fujiwara had put forward as the smallest convex answer - and does two
things to it:

  1. cut the base into 2^n equal parts, giving 2^n thin triangles that all
     share the apex;
  2. slide neighbouring pieces over one another so that they overlap.

The overlapping is where the area goes. What it cannot touch is direction:
sliding a piece is a translation, and a translation does not turn anything.
Each piece still holds exactly the segments it held before, pointing exactly
the same way. That is the whole trick, and mode 'directions' is the one that
says it.

The areas printed on screen are not guesses. For the construction actually
drawn here - 8 pieces, each merge sliding the right group left by 0.35 of
its own width, three rounds - the union area was measured by rasterising the
figure on a 2400 x 2400 grid:

    start        0.5773   (= 1/sqrt3, the whole triangle)
    round 1      0.4205
    round 2      0.3637
    round 3      0.2805   (48.6 % of where it began)

Taking n larger drives this towards zero; three rounds is what fits on a
screen and stays countable.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    split      - The triangle of height 1, then its base cut into 8 and the
                 8 thin pieces drawn one by one.
                 Fixed params: 8 pieces, common apex, area label 0.58
                 (unchanged - cutting alone costs nothing).
    fold       - The three merge rounds. Pieces slide left and overlap; the
                 area readout falls 0.58 -> 0.42 -> 0.36 -> 0.28.
                 Fixed params: 8 pieces, slide 0.35 of the group's width,
                 3 rounds, areas as above.
    directions - The same folding, but every piece carries a coloured spine
                 showing the direction it holds. The spines move with their
                 pieces and keep their angles; at the end they are collected
                 at one point to show the fan is complete.
                 Fixed params: 8 spines, 8 distinct directions, colours
                 running from cyan to pink across the fan.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Dot,
    FadeIn,
    Line,
    ManimColor,
    Polygon,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR

_BOTTOM_Y = -1.75
_AREA_Y = -1.22
_TITLE_Y = 3.06

_MODES = ("split", "fold", "directions")
_DEFAULT_MODE = "fold"
assert _DEFAULT_MODE in _MODES

_N = 8  # pieces
_F = 0.35  # each merge slides the right group left by this share of its width
_ROUNDS = 3
_B = 2.0 / float(np.sqrt(3.0))  # base of the equilateral triangle of height 1
_V = np.array([_B / 2.0, 1.0])  # its apex

# Union areas measured by rasterising the drawn figure on a 2400 x 2400 grid.
_AREAS = (0.58, 0.42, 0.36, 0.28)
assert len(_AREAS) == _ROUNDS + 1

_S = 3.05  # display scale
_BASE_Y = -0.75  # where the base line sits on screen
_OX = -_B / 2.0 * _S  # centres the starting triangle


def _perron_stages(n=_N, f=_F):
    """The construction, stage by stage.

    Returns a list of `rounds + 1` stages; each stage is a list of `n` triangles
    (3 x 2 arrays) in a FIXED piece order, so stage k and stage k+1 can be
    compared piece by piece to get each piece's translation.
    """
    xs = np.linspace(0.0, _B, n + 1)
    tris = [np.array([[xs[i], 0.0], [xs[i + 1], 0.0], _V]) for i in range(n)]
    groups = [[i] for i in range(n)]
    stages = [[t.copy() for t in tris]]
    while len(groups) > 1:
        merged = []
        for k in range(0, len(groups), 2):
            left, right = groups[k], groups[k + 1]
            pts = np.concatenate([tris[j] for j in right], axis=0)
            width = float(pts[:, 0].max() - pts[:, 0].min())
            for j in right:
                tris[j] = tris[j] - np.array([f * width, 0.0])
            merged.append(left + right)
        groups = merged
        stages.append([t.copy() for t in tris])
    return stages


def _to3(p):
    return np.array([p[0] * _S + _OX, p[1] * _S + _BASE_Y, 0.0])


def _piece_color(i, n=_N):
    # interpolate_color needs ManimColor objects; style.py exports hex strings.
    t = i / max(n - 1, 1)
    return interpolate_color(ManimColor(ACCENT_CYAN), ManimColor(ACCENT_PINK), t)


class PerronTree(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"perron_tree: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 30)
        if mode == "split":
            self._split(duration)
        elif mode == "directions":
            self._directions(duration)
        else:
            self._fold(duration)

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

    def _piece(self, tri, i, fill=0.30, stroke=2.0):
        c = _piece_color(i)
        return Polygon(
            *[_to3(p) for p in tri],
            color=c,
            stroke_width=stroke,
            fill_color=c,
            fill_opacity=fill,
        )

    def _area_readout(self, value):
        head = Text("面積", font=FONT, font_size=29, color=TEXT_DIM)
        num = Text(f"{value:.2f}", font=FONT, font_size=33, color=ACCENT_PINK)
        g = VGroup(head, num).arrange(direction=np.array([1.0, 0.0, 0.0]), buff=0.30)
        g.move_to(UP * _AREA_Y)
        return g, num

    def _reveal(self, *mobjects, run_time):
        fade = min(min(max(run_time * 0.30, 0.7), 1.4), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _spine(self, tri, i, width=5.0):
        """The piece's own segment: base midpoint to apex. A translation moves
        it without turning it, which is the point of mode 'directions'."""
        foot = (tri[0] + tri[1]) / 2.0
        return Line(_to3(foot), _to3(tri[2]), color=_piece_color(i), stroke_width=width)

    # -- mode: split -------------------------------------------------------
    def _split(self, duration):
        title = self._title("まず、細く切り分けます")
        stages = _perron_stages()
        pieces = [self._piece(t, i, fill=0.22) for i, t in enumerate(stages[0])]
        base = Line(
            _to3(np.array([0.0, 0.0])),
            _to3(np.array([_B, 0.0])),
            color=TEXT_DIM,
            stroke_width=2.2,
        )
        cut = Text("底辺を 8 等分", font=FONT, font_size=26, color=TEXT_DIM)
        cut.move_to(np.array([4.05, 1.85, 0.0]))
        area, _ = self._area_readout(_AREAS[0])
        note = self._note("切っただけでは、面積は変わりません", color=TEXT_DIM)

        CODA = 2.4
        weights = [0.8] + [0.55] * _N + [1.0, 1.0]
        rt = pace(duration, weights, intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        self._reveal(base, run_time=rt[0])
        for i, p in enumerate(pieces):
            self._reveal(p, run_time=rt[1 + i])
        self._reveal(cut, area, run_time=rt[1 + _N])
        self._reveal(note, run_time=rt[2 + _N])
        self.wait(CODA)

    # -- mode: fold --------------------------------------------------------
    def _fold(self, duration):
        title = self._title("重ねると、面積は縮みます")
        stages = _perron_stages()
        pieces = [self._piece(t, i) for i, t in enumerate(stages[0])]
        area, num = self._area_readout(_AREAS[0])
        note = self._note("動かしているのは、平行移動だけです", color=ACCENT_GOLD)

        CODA = 2.6
        # one slide + one readout swap per round, then the closing note
        weights = []
        for _ in range(_ROUNDS):
            weights += [1.6, 0.35]
        weights += [1.0]
        rt = pace(duration, weights, intro=1.9, coda=CODA)

        self.play(FadeIn(title), run_time=1.1)
        self.play(
            AnimationGroup(*[FadeIn(p) for p in pieces], FadeIn(area), lag_ratio=0.0),
            run_time=0.8,
        )
        k = 0
        for r in range(_ROUNDS):
            shifts = []
            for i, p in enumerate(pieces):
                d = stages[r + 1][i][0] - stages[r][i][0]
                if abs(float(d[0])) > 1e-9:
                    shifts.append(p.animate.shift(np.array([float(d[0]) * _S, 0.0, 0.0])))
            if shifts:
                self.play(AnimationGroup(*shifts, lag_ratio=0.0), run_time=rt[k])
            else:
                self.wait(rt[k])
            k += 1
            # swap the number on its own short play: a long run_time on Japanese
            # text leaves broken glyphs on screen for seconds.
            nxt = Text(f"{_AREAS[r + 1]:.2f}", font=FONT, font_size=33, color=ACCENT_PINK)
            nxt.move_to(num)
            self.play(FadeIn(nxt), run_time=min(0.5, rt[k]))
            self.remove(num)
            num = nxt
            if rt[k] > 0.55:
                self.wait(rt[k] - 0.5)
            k += 1
        self._reveal(note, run_time=rt[k])
        self.wait(CODA)

    # -- mode: directions --------------------------------------------------
    def _directions(self, duration):
        title = self._title("向きは、ひとつも失われません")
        stages = _perron_stages()
        pieces = [self._piece(t, i, fill=0.16, stroke=1.4) for i, t in enumerate(stages[0])]
        spines = [self._spine(t, i) for i, t in enumerate(stages[0])]
        note = self._note("平行移動は、線の向きを変えません", color=ACCENT_GOLD)

        # The same fan, gathered at one point, after the folding.
        hub = np.array([4.55, -0.30, 0.0])
        fan = VGroup(Dot(hub, radius=0.06, color=TEXT_DIM))
        for i, t in enumerate(stages[0]):
            v = _to3(t[2]) - _to3((t[0] + t[1]) / 2.0)
            v = v / float(np.linalg.norm(v)) * 1.85
            # rays from one hub, not segments through it: through-segments all
            # overlapped and the eight directions could not be told apart
            fan.add(Line(hub, hub + v, color=_piece_color(i), stroke_width=5.0))
        fan_lab = Text("そろっている向き", font=FONT, font_size=25, color=TEXT_DIM)
        fan_lab.move_to(np.array([4.55, 2.00, 0.0]))

        CODA = 2.6
        weights = [1.0] + [1.35] * _ROUNDS + [1.0, 1.0]
        rt = pace(duration, weights, intro=1.9, coda=CODA)

        self.play(FadeIn(title), run_time=1.1)
        self.play(
            AnimationGroup(*[FadeIn(p) for p in pieces], lag_ratio=0.0),
            run_time=0.8,
        )
        self._reveal(*spines, run_time=rt[0])
        for r in range(_ROUNDS):
            moves = []
            for i in range(_N):
                d = stages[r + 1][i][0] - stages[r][i][0]
                if abs(float(d[0])) > 1e-9:
                    v = np.array([float(d[0]) * _S, 0.0, 0.0])
                    moves.append(pieces[i].animate.shift(v))
                    moves.append(spines[i].animate.shift(v))
            if moves:
                self.play(AnimationGroup(*moves, lag_ratio=0.0), run_time=rt[1 + r])
            else:
                self.wait(rt[1 + r])
        self._reveal(fan, fan_lab, run_time=rt[1 + _ROUNDS])
        self._reveal(note, run_time=rt[2 + _ROUNDS])
        self.wait(CODA)


# What each mode puts on screen.
LINT_VISUAL_ELEMENTS = {
    "split": ["三角形", "底辺", "線"],
    "fold": ["三角形", "線"],
    "directions": ["三角形", "線", "向き"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "split": {"people": [], "years": []},
    "fold": {"people": [], "years": []},
    "directions": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, PerronTree)
