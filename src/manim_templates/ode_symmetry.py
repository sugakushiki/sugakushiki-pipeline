"""
ode_symmetry.py - Lie's symmetry view of first order ODEs

The textbook lists solution recipes by type - separable, homogeneous,
integrating factor - and each comes with its own drill. Lie showed that
MOST of them are the same statement wearing different clothes: the
equation is unchanged by one continuous transformation. Find that
transformation, change coordinates so it becomes a plain translation,
and what is left is an integration.

The equation drawn in modes 'scaling' and 'rectify' is

    dy/dx = (x + y) / (x - y),

i.e. the direction field  (dx, dy) proportional to  (x - y, x + y).
Everything shown about it is exact:

  * the field is invariant under (x, y) -> (L x, L y) for every L > 0,
    because (L x - L y, L x + L y) = L (x - y, x + y) is the SAME
    direction;
  * in polar coordinates  dr/dt = r,  d(theta)/dt = 1, so the integral
    curves are  ln r = theta + c  - logarithmic spirals;
  * therefore in the coordinates (theta, ln r) the solutions are
    straight PARALLEL lines of slope 1, and the scaling symmetry is a
    vertical translation. That is exactly Lie's canonical-coordinate
    move.

The polar sampling grid in mode 'scaling' is built so the invariance is
visible as an exact coincidence, not as an approximation: the radii form
a geometric sequence of ratio 1.625 and each segment's half-length is
0.30 * r, so scaling the whole picture by 1.625 about the centre carries
ring k onto ring k+1 point for point, segment for segment.

'catalog' deliberately says "many of the recipes", never "all of them":
the source claim is that NEARLY all standard first-order methods are
characterised by symmetries.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    catalog - The framing. Three recipe cards (separable / homogeneous /
              integrating factor) drop down onto one gold bar carrying
              the single reason.
              Fixed params: 3 cards, 3 arrows, 1 bar, 1 note.
    scaling - The invariance. A polar direction field of the equation
              above, revealed ring by ring, then the second ring is
              copied and blown up by the ring ratio so it lands exactly
              on the third.
              Fixed params: 4 rings x 12 directions = 48 segments,
              radii 0.33 * 1.625^k, half-length 0.30 * r, scale factor
              1.625, sampling angles offset by half a step.
    rectify - The pay-off. Left: the same field with three gold spiral
              solutions. Right: the same family in the coordinates
              (turned angle, log size) - five parallel straight lines of
              slope 1, gold again, with scaling shown as a vertical
              shift. Gold means 'a solution' in both panels, cyan means
              'the field'.
              Fixed params: 3 rings x 12 directions on the left, 3
              solution spirals, 5 parallel lines of slope 1 on the right.

No person names and no years appear on screen in any mode - the
narration carries Lie, Galois and the dates.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Arrow,
    CurvedArrow,
    Dot,
    FadeIn,
    Indicate,
    Line,
    ParametricFunction,
    Rectangle,
    RoundedRectangle,
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

# Japanese glyphs hang ~0.17 below their centre; the subtitle band starts at -2.0.
_BOTTOM_Y = -1.72

_MODES = ("catalog", "scaling", "rectify")
_DEFAULT_MODE = "scaling"
assert _DEFAULT_MODE in _MODES

# Geometry of the polar sampling grid (mode 'scaling'). The outermost ring
# plus its segment reaches 1.74 above/below the centre, which is what keeps
# the picture clear of the title (y 3.06) and the bottom note (y -1.72).
_RING_RATIO = 1.625
_RING_BASE = 0.33
_N_ANGLES = 12
_HALF_LEN_RATIO = 0.30
# Half a sampling step, so no segment sits exactly at the top or bottom of
# the ring where the vertical clearance is tightest.
_ANGLE_OFFSET = np.pi / _N_ANGLES


def _field_direction(point, centre):
    """Unit direction of dy/dx = (x+y)/(x-y), i.e. (x-y, x+y), at `point`.

    Scale invariant by construction: replacing (x, y) by (Lx, Ly)
    multiplies the vector by L and leaves the direction untouched.
    """
    v = point - centre
    d = np.array([v[0] - v[1], v[0] + v[1], 0.0])
    n = float(np.linalg.norm(d))
    if n < 1e-9:
        return np.array([1.0, 0.0, 0.0])
    return d / n


def _field_rings(centre, radii, color, stroke_width, unit=1.0):
    """One VGroup of direction segments per radius, outermost last.

    Half-length is proportional to r, so a scaling about `centre` maps a
    ring onto the next one exactly (positions AND lengths).
    """
    rings = []
    for r in radii:
        ring = VGroup()
        for k in range(_N_ANGLES):
            a = _ANGLE_OFFSET + 2.0 * np.pi * k / _N_ANGLES
            p = centre + unit * r * np.array([np.cos(a), np.sin(a), 0.0])
            d = _field_direction(p, centre)
            half = _HALF_LEN_RATIO * unit * r
            ring.add(Line(p - half * d, p + half * d, color=color, stroke_width=stroke_width))
        rings.append(ring)
    return rings


class OdeSymmetry(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly instead of silently
        # drawing the default picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"ode_symmetry: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "catalog":
            self._catalog(duration)
        elif mode == "rectify":
            self._rectify(duration)
        else:
            self._scaling(duration)

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
        """FadeIn crisply, then hold: fade + rest == run_time exactly, so the
        scene can never overrun its budget."""
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _pulse(self, m, run_time, color, extras=()):
        """FadeIn (m plus extras), THEN Indicate m, as separate plays.

        Never put FadeIn and Indicate in one AnimationGroup: Indicate stores
        the state at begin() as its restore target, which inside a shared
        group is the transparent pre-FadeIn state, so the object ends up
        invisible. smoke test section 31 checks for this.
        """
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.6, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    # -- mode: catalog -----------------------------------------------------------
    def _catalog(self, duration):
        title = self._title("ばらばらの解法が、ひとつの理由に")

        recipes = ("変数分離形", "同次形", "積分因子")
        card_xs = (-4.05, 0.0, 4.05)
        cards = VGroup()
        for name, x in zip(recipes, card_xs, strict=True):
            box = RoundedRectangle(
                width=3.5,
                height=1.05,
                corner_radius=0.16,
                color=ACCENT_CYAN,
                stroke_width=3,
            )
            label = Text(name, font=FONT, font_size=28, color=TEXT_WHITE)
            self._fit(label, 3.1)
            group = VGroup(box, label)
            group.move_to(np.array([x, 1.9, 0.0]))
            label.move_to(group.get_center())
            cards.add(group)

        arrows = VGroup()
        for x in card_xs:
            arrows.add(
                Arrow(
                    np.array([x, 1.32, 0.0]),
                    np.array([x, 0.52, 0.0]),
                    buff=0.0,
                    color=TEXT_DIM,
                    stroke_width=3,
                    max_tip_length_to_length_ratio=0.32,
                )
            )

        bar = RoundedRectangle(
            width=10.4,
            height=1.0,
            corner_radius=0.18,
            color=ACCENT_GOLD,
            stroke_width=4,
        )
        bar.move_to(np.array([0.0, 0.0, 0.0]))
        bar_label = Text(
            "ある一つの連続な変換で、方程式が変わらない",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        self._fit(bar_label, 9.8)
        bar_label.move_to(bar.get_center())
        bar_group = VGroup(bar, bar_label)

        note = self._note("教科書の解法の多くは、この一つの理由の別の顔です", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 0.9, 1.2, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(cards, run_time=rt[0])
        self._reveal(arrows, run_time=rt[1])
        self._pulse(bar_group, run_time=rt[2], color=ACCENT_GOLD)
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)

    # -- mode: scaling (THE invariance) ------------------------------------------
    def _scaling(self, duration):
        title = self._title("拡大しても、向きは変わらない")

        centre = np.array([0.0, 0.68, 0.0])
        radii = [_RING_BASE * _RING_RATIO**k for k in range(4)]
        rings = _field_rings(centre, radii, ACCENT_CYAN, 3.6)
        origin_dot = Dot(centre, radius=0.06, color=TEXT_DIM)

        # The ring that will be blown up, and the ring it must land on. The
        # copy is drawn THIN and the target is widened as the copy flies in,
        # so the landing reads as a coincidence (thin pink inside thick cyan)
        # instead of pink simply hiding cyan.
        source = rings[1].copy().set_color(ACCENT_PINK).set_stroke(width=2.4)
        target = rings[2]

        legend = Text("方向場", font=FONT, font_size=26, color=ACCENT_CYAN)
        legend.move_to(np.array([-4.85, 2.35, 0.0]))
        moving_label = Text("拡大したもの", font=FONT, font_size=26, color=ACCENT_PINK)
        moving_label.move_to(np.array([4.55, 2.35, 0.0]))

        note = self._note("同じ方向場に、そのまま重なります", color=ACCENT_GOLD)

        CODA = 2.4
        rt = pace(duration, [0.8, 0.8, 0.8, 0.8, 0.9, 1.4, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(rings[0], origin_dot, legend, run_time=rt[0])
        self._reveal(rings[1], run_time=rt[1])
        self._reveal(rings[2], run_time=rt[2])
        self._reveal(rings[3], run_time=rt[3])
        self._reveal(source, moving_label, run_time=rt[4])
        # Scaling by the ring ratio about the centre carries ring 1 onto
        # ring 2 exactly - positions and segment lengths both.
        self.play(
            source.animate.scale(_RING_RATIO, about_point=centre),
            target.animate.set_stroke(width=8.0),
            run_time=rt[5],
        )
        self.play(Indicate(target, color=ACCENT_GOLD), run_time=min(1.5, rt[6]))
        if rt[6] > 1.5:
            self.wait(rt[6] - 1.5)
        self._reveal(note, run_time=max(0.6, CODA * 0.45))
        self.wait(CODA * 0.55)

    # -- mode: rectify (the pay-off) ---------------------------------------------
    def _rectify(self, duration):
        title = self._title("座標を取り替えると、まっすぐになる")

        # --- left: the curved picture -------------------------------------
        # Centre pushed left to 4.30 so the bridge label between the panels
        # clears the field's right edge (field reaches x = -2.74).
        lc = np.array([-4.30, 1.00, 0.0])
        radii = [_RING_BASE * _RING_RATIO**k for k in range(3)]
        rings = _field_rings(lc, radii, ACCENT_CYAN, 2.8, unit=1.45)
        field = VGroup(*rings)

        # Three EXACT solution curves: r = 0.55 e^t with theta = t + phi
        # satisfies d(ln r)/d(theta) = 1, which is what the field says, for
        # every offset phi. The range is trimmed to the annulus the field
        # occupies (r from 0.30 to 1.57) - the radius grows by a factor e per
        # radian, so no more than about 95 degrees of any one solution can be
        # shown at a readable size, and pushing further in only crams radians
        # into invisible radii. Three offset copies show the FAMILY, which is
        # what the straightened panel on the right also shows.
        def _solution(phi):
            return ParametricFunction(
                lambda t: lc + 0.55 * np.exp(t) * np.array([np.cos(t + phi), np.sin(t + phi), 0.0]),
                t_range=[-0.62, 1.05, 0.02],
                color=ACCENT_GOLD,
                stroke_width=5.0,
            )

        solutions = VGroup(*[_solution(k * 2.0 * np.pi / 3.0) for k in range(3)])
        left_cap = Text("もとの座標", font=FONT, font_size=25, color=TEXT_DIM)
        left_cap.move_to(np.array([-4.30, -0.95, 0.0]))

        # --- middle: the change of coordinates ----------------------------
        bridge = Arrow(
            np.array([-2.60, 1.00, 0.0]),
            np.array([-0.35, 1.00, 0.0]),
            buff=0.0,
            color=TEXT_WHITE,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.28,
        )
        bridge_label = Text("座標を取り替える", font=FONT, font_size=23, color=TEXT_WHITE)
        bridge_label.move_to(np.array([-1.48, 1.78, 0.0]))

        # --- right: the straightened picture -------------------------------
        rc = np.array([3.30, 1.00, 0.0])
        half_w, half_h = 2.55, 1.45
        frame = Rectangle(width=2 * half_w, height=2 * half_h, color=EDGE_COLOR, stroke_width=2.5)
        frame.move_to(rc)

        # Same colour as the curved solutions on the left: gold means "a
        # solution" in both panels, cyan means "the field". These lines ARE
        # the left-hand spirals, drawn in the new coordinates.
        lines = VGroup()
        for c in (-2.4, -1.2, 0.0, 1.2, 2.4):
            lo = max(-half_w, -half_h - c)
            hi = min(half_w, half_h - c)
            if hi - lo < 0.15:
                continue
            lines.add(
                Line(
                    rc + np.array([lo, lo + c, 0.0]),
                    rc + np.array([hi, hi + c, 0.0]),
                    color=ACCENT_GOLD,
                    stroke_width=4.0,
                )
            )

        x_cap = Text("回した角", font=FONT, font_size=23, color=TEXT_DIM)
        x_cap.move_to(rc + np.array([0.0, -half_h - 0.42, 0.0]))
        y_cap = Text("大きさの対数", font=FONT, font_size=23, color=TEXT_DIM)
        y_cap.rotate(np.pi / 2)
        y_cap.move_to(rc + np.array([-half_w - 0.40, 0.0, 0.0]))

        shift_arrow = CurvedArrow(
            rc + np.array([1.85, -0.55, 0.0]),
            rc + np.array([1.85, 0.75, 0.0]),
            angle=-0.9,
            color=ACCENT_PINK,
            stroke_width=3,
            tip_length=0.2,
        )
        # The label sits OUTSIDE the frame, level with the arrow head: inside
        # it would land on the parallel lines, and below the frame it would
        # collide with the horizontal-axis caption.
        shift_label = Text("拡大", font=FONT, font_size=25, color=ACCENT_PINK)
        shift_label.move_to(np.array([6.42, 1.75, 0.0]))

        note = self._note("あとは、積分するだけです", color=ACCENT_GOLD)

        CODA = 2.4
        rt = pace(duration, [1.0, 1.0, 0.8, 1.1, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(field, left_cap, run_time=rt[0])
        self._reveal(solutions, run_time=rt[1])
        self._reveal(bridge, bridge_label, run_time=rt[2])
        self._reveal(frame, x_cap, y_cap, lines, run_time=rt[3])
        self._pulse(shift_arrow, run_time=rt[4], color=ACCENT_PINK, extras=(shift_label,))
        self.play(Indicate(lines, color=ACCENT_GOLD), run_time=min(1.4, rt[5]))
        if rt[5] > 1.4:
            self.wait(rt[5] - 1.4)
        self._reveal(note, run_time=max(0.6, CODA * 0.45))
        self.wait(CODA * 0.55)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "catalog": ["カード", "矢印", "帯"],
    "scaling": ["方向場", "線分", "矢印", "点"],
    "rectify": ["方向場", "線分", "曲線", "直線", "矢印", "座標", "縦軸", "横軸", "枠"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "catalog": {"people": [], "years": []},
    "scaling": {"people": [], "years": []},
    "rectify": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, OdeSymmetry)
