"""
lie_group_generator.py - from a continuous family to its infinitesimal
generator, and back

A continuous family of transformations has infinitely many members - one
for every value of the parameter. Lie's decisive move was to stop
handling the family and look only at how it STARTS to move: differentiate
at parameter zero. What is left is one arrow at each point of the plane -
a vector field - and flowing along that field rebuilds the whole family.
A curved object has been replaced by a flat one.

The family drawn here is the rotation group of the plane: the
transformation with parameter t turns everything by the angle t about a
fixed centre. Its infinitesimal generator is the velocity field

    (x, y) -> (-y, x)

(the derivative at t = 0 of the rotation by t), which is what mode
'generator' draws: at every lattice point an arrow perpendicular to the
radius, of length proportional to the distance from the centre. Mode
'algebra' shows the same statement as a picture of shapes: the family is
a curve (drawn as a circle), the generators form the straight tangent
line at the identity, and flowing carries the flat line back onto the
curved family.

The word "Lie algebra" is deliberately NOT drawn on screen anywhere: it
was coined by Weyl in 1934, thirty-five years after Lie's death, and the
narration is what carries that point.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    flow      - The family. A hand turns continuously about the centre
                for the whole scene while a trail arc grows behind it,
                so the parameter is visibly a continuum, not a list.
                Fixed params: 1 circle (radius 1.5), 1 turning hand,
                1 growing trail, total turn 0.92 of a full turn, motion
                runs the entire scene.
    generator - The derivative at zero. The same circle, then the single
                velocity arrow at the starting point, then the whole
                velocity field on a lattice.
                Fixed params: 5 x 5 lattice, spacing 0.72, circle of
                radius 1.44 through the seed point, arrows perpendicular
                to the radius with length 0.30 * distance (24 cyan
                arrows plus the pink seed, which replaces one of them).
    algebra   - The exchange. Left: the family as a curve (circle) with
                the identity marked. At the identity, the straight
                tangent line carrying the velocities. A curved arrow
                takes the flat line back onto the curve.
                Fixed params: 1 circle (radius 1.45), 1 tangent line,
                4 velocity dots on it, 1 curved arrow, 3 labels,
                2 short leaders.

No person names and no years appear on screen in any mode.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Arc,
    Arrow,
    Circle,
    CurvedArrow,
    Dot,
    FadeIn,
    Indicate,
    Line,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    linear,
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

# Japanese glyphs hang ~0.17 below their centre; the subtitle band starts at -2.0.
_BOTTOM_Y = -1.72

_MODES = ("flow", "generator", "algebra")
_DEFAULT_MODE = "generator"
assert _DEFAULT_MODE in _MODES

# Fraction of a full turn swept by mode 'flow' (kept under 1 so the trail
# never closes on itself and the start of the sweep stays readable).
_TOTAL_TURN = 0.92
_LATTICE_N = 5
_LATTICE_STEP = 0.72
_ARROW_RATIO = 0.30


def _perp(v):
    """The rotation generator's value at offset v: (x, y) -> (-y, x)."""
    return np.array([-v[1], v[0], 0.0])


class LieGroupGenerator(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly instead of silently
        # drawing the default picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"lie_group_generator: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "flow":
            self._flow(duration)
        elif mode == "algebra":
            self._algebra(duration)
        else:
            self._generator(duration)

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

    def _label(self, s, pos, color, font_size=25):
        """`pos` may be (x, y) or (x, y, z); move_to needs all three."""
        t = Text(s, font=FONT, font_size=font_size, color=color)
        xyz = tuple(pos) + (0.0,) * (3 - len(pos))
        t.move_to(np.array(xyz))
        return t

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

    # -- mode: flow (the continuum) ----------------------------------------------
    def _flow(self, duration):
        title = self._title("動かし方が、ひと続きに並んでいる")

        centre = np.array([0.0, 0.75, 0.0])
        radius = 1.5
        ring = Circle(radius=radius, color=TEXT_DIM, stroke_width=2.2)
        ring.move_to(centre)
        hub = Dot(centre, radius=0.07, color=TEXT_DIM)

        turn = ValueTracker(0.0)

        def _hand():
            a = turn.get_value()
            u = np.array([np.cos(a), np.sin(a), 0.0])
            return VGroup(
                Line(centre, centre + radius * u, color=ACCENT_GOLD, stroke_width=5),
                Dot(centre + radius * u, radius=0.11, color=ACCENT_GOLD),
                Dot(centre + 0.55 * radius * u, radius=0.07, color=ACCENT_CYAN),
            )

        def _trail():
            a = max(turn.get_value(), 1e-3)
            return Arc(
                radius=radius,
                start_angle=0.0,
                angle=a,
                arc_center=centre,
                color=ACCENT_PINK,
                stroke_width=6,
            )

        hand = always_redraw(_hand)
        trail = always_redraw(_trail)

        start_mark = Dot(centre + radius * np.array([1.0, 0.0, 0.0]), radius=0.07, color=TEXT_WHITE)
        start_label = self._label("はじめの位置", (4.05, 0.72), TEXT_DIM, font_size=24)
        param_label = self._label("動かす量", (-3.55, 2.05), ACCENT_PINK, font_size=26)
        note = self._note("量をなめらかに変えると、変換もなめらかに変わります", color=ACCENT_GOLD)

        CODA = 2.2
        INTRO = 1.2
        self.play(FadeIn(title), run_time=INTRO)
        self.play(FadeIn(ring), FadeIn(hub), FadeIn(start_mark), run_time=0.9)
        self.add(trail, hand)

        # The hand turns for the WHOLE remaining scene; the labels ride along
        # inside the same plays so the motion never stops.
        motion = max(3.0, duration - INTRO - 0.9 - CODA)
        legs = (0.30, 0.34, 0.36)
        riders = (start_label, param_label, note)
        swept = 0.0
        for frac, rider in zip(legs, riders, strict=True):
            swept += frac
            self.play(
                AnimationGroup(
                    turn.animate(run_time=motion * frac, rate_func=linear).set_value(
                        2.0 * np.pi * _TOTAL_TURN * swept
                    ),
                    FadeIn(rider, run_time=0.6),
                    lag_ratio=0.0,
                )
            )
        self.wait(CODA)

    # -- mode: generator (THE key mode) ------------------------------------------
    def _generator(self, duration):
        title = self._title("動かし始めの、速度だけを見る")

        # Centre and lattice size chosen together: the top-right arrow reaches
        # y = 2.55 and the bottom-left one y = -1.19, so the field clears both
        # the title (3.06) and the bottom note (-1.72).
        centre = np.array([0.0, 0.68, 0.0])
        radius = 2.0 * _LATTICE_STEP
        ring = Circle(radius=radius, color=TEXT_DIM, stroke_width=2.2)
        ring.move_to(centre)
        hub = Dot(centre, radius=0.06, color=TEXT_DIM)

        # The seed sits ON a lattice point and uses the SAME formula as the
        # field, so the single pink arrow the scene starts from is literally
        # one of the cyan arrows it ends with (that point is skipped below).
        seed_off = np.array([radius, 0.0, 0.0])
        start = centre + seed_off
        start_dot = Dot(start, radius=0.11, color=ACCENT_GOLD)
        seed_arrow = Arrow(
            start,
            start + _ARROW_RATIO * _perp(seed_off),
            buff=0.0,
            color=ACCENT_PINK,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.34,
        )

        span = (_LATTICE_N - 1) / 2.0
        field = VGroup()
        for ix in range(_LATTICE_N):
            for iy in range(_LATTICE_N):
                off = np.array([(ix - span) * _LATTICE_STEP, (iy - span) * _LATTICE_STEP, 0.0])
                if float(np.linalg.norm(off)) < 1e-9:
                    continue
                if float(np.linalg.norm(off - seed_off)) < 1e-9:
                    continue  # already drawn as the pink seed arrow
                p = centre + off
                v = _ARROW_RATIO * _perp(off)
                field.add(
                    Arrow(
                        p,
                        p + v,
                        buff=0.0,
                        color=ACCENT_CYAN,
                        stroke_width=3,
                        max_tip_length_to_length_ratio=0.38,
                    )
                )

        ring_label = self._label("回す変換", (-4.30, 2.30), TEXT_DIM, font_size=25)
        seed_label = self._label("動かし始めの速度", (4.05, 2.35), ACCENT_PINK, font_size=25)
        field_label = self._label("すべての点での速度", (4.15, -0.75), ACCENT_CYAN, font_size=25)
        note = self._note("これが、無限小の変換です", color=ACCENT_GOLD)

        CODA = 2.4
        rt = pace(duration, [0.9, 1.1, 1.3, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(ring, hub, start_dot, ring_label, run_time=rt[0])
        self._pulse(seed_arrow, run_time=rt[1], color=ACCENT_PINK, extras=(seed_label,))
        self.play(
            AnimationGroup(
                *[FadeIn(a) for a in field],
                lag_ratio=0.06,
                run_time=max(1.0, rt[2] * 0.72),
            )
        )
        self._reveal(field_label, run_time=max(0.5, rt[2] * 0.28))
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)

    # -- mode: algebra (curved becomes flat) -------------------------------------
    def _algebra(self, duration):
        title = self._title("曲がったものが、平らなものになる")

        centre = np.array([-3.70, 0.90, 0.0])
        radius = 1.45
        family = Circle(radius=radius, color=ACCENT_CYAN, stroke_width=4)
        family.move_to(centre)

        identity = centre + radius * np.array([1.0, 0.0, 0.0])
        id_dot = Dot(identity, radius=0.11, color=ACCENT_GOLD)

        tangent = Line(
            identity + np.array([0.0, -1.40, 0.0]),
            identity + np.array([0.0, 1.40, 0.0]),
            color=ACCENT_PINK,
            stroke_width=4.5,
        )
        speeds = VGroup(
            *[
                Dot(identity + np.array([0.0, dy, 0.0]), radius=0.07, color=ACCENT_PINK)
                for dy in (-1.10, -0.55, 0.55, 1.10)
            ]
        )

        back = CurvedArrow(
            identity + np.array([0.0, 1.10, 0.0]),
            centre + radius * np.array([np.cos(1.15), np.sin(1.15), 0.0]),
            angle=1.0,
            color=ACCENT_GOLD,
            stroke_width=3.5,
            tip_length=0.22,
        )

        # Labels sit next to what they name, with SHORT leaders only. The
        # first cut ran three long leaders from a right-hand stack across the
        # figure; they crossed each other and the curved arrow, and the
        # topmost one grazed the title.
        lab_family = self._label("連続な変換の集まり", (-3.70, -0.95), ACCENT_CYAN, font_size=26)
        lab_speed = self._label("動かし始めの速度", (0.75, 1.30), ACCENT_PINK, font_size=26)
        lead_speed = Line(
            np.array([-0.55, 1.30, 0.0]),
            identity + np.array([0.09, 0.55, 0.0]),
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        lab_back = self._label("流すと、戻る", (-0.30, 2.35), ACCENT_GOLD, font_size=26)
        lead_back = Line(
            np.array([-1.45, 2.35, 0.0]),
            identity + np.array([-0.30, 1.28, 0.0]),
            color=TEXT_DIM,
            stroke_width=1.5,
        )

        note = self._note("曲がった集まりが、平らな一本に置きかわります", color=ACCENT_GOLD)

        CODA = 2.4
        rt = pace(duration, [1.0, 0.9, 1.2, 1.2, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(family, lab_family, run_time=rt[0])
        self._pulse(id_dot, run_time=rt[1], color=ACCENT_GOLD)
        self._pulse(
            tangent,
            run_time=rt[2],
            color=ACCENT_PINK,
            extras=(speeds, lab_speed, lead_speed),
        )
        self._pulse(back, run_time=rt[3], color=ACCENT_GOLD, extras=(lab_back, lead_back))
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "flow": ["円", "点", "線", "弧"],
    "generator": ["矢印", "円", "点", "格子", "ベクトル場"],
    "algebra": ["円", "直線", "接線", "矢印", "点"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "flow": {"people": [], "years": []},
    "generator": {"people": [], "years": []},
    "algebra": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, LieGroupGenerator)
