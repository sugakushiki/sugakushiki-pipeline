"""
borel_projection_shadow.py - The shadow of a set, and the line that was false

In 1905 Lebesgue wrote down, without proof, that the projection of a Borel set
of the plane onto an axis is again Borel. Cast a shadow, he was saying, and the
shadow keeps the parentage of the thing that cast it. The proof was short and it
was wrong, and the mistake sits in one silent step: he took it that projecting
commutes with the limit of a DECREASING sequence of sets.

Mode 'decreasing' is the whole error in one picture. Take slabs that march
upward for ever. Every slab throws the same shadow, so the shadows have that
shadow in common; but no point of the plane lies in all the slabs, so the common
part is empty and its shadow is nothing. The common part of the shadows is not
the shadow of the common part.

This is deliberately the same shape of failure as the one the Lebesgue integral
was built to repair - a limit that refuses to pass through an operation. The
episode says so out loud, so do not retitle these modes into something that
hides the echo.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    shadow     - A blob in the plane, rays dropped from it, and the segment it
                 covers on the axis. This mode only DEFINES what a projection
                 is; the blob is tame and its shadow is one clean interval, so
                 the closing line asks whether shadows keep their parentage
                 rather than asserting they do not. The failure is 'decreasing'.
                 Fixed params: one blob, 7 rays, one shadow segment.
    decreasing - The error. Three slabs at rising heights, all with the same
                 shadow, and the two verdicts side by side: the common part of
                 the shadows is that segment, the shadow of the common part is
                 empty.
                 Fixed params: 3 slabs drawn, shadow segment shared by all,
                 intersection empty.
    hierarchy  - Where the projections landed. Borel sets inside, analytic sets
                 outside, one arrow marked "projection" pointing out, and
                 Suslin's way back in.
                 Fixed params: 2 nested regions, 1 arrow.

No person names and no years appear on screen in any mode, so
LINT_FACTUAL_CLAIMS is empty throughout - the narration carries Suslin and the
dates.

Reads params from _manim_params.json in the same directory.
"""

import math

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Arrow,
    Ellipse,
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

# The lowest drawn text sits here. Japanese glyphs hang about 0.17 below the
# centre they are placed at and the subtitle band starts at y = -2.0.
_BOTTOM_Y = -1.72

_RAYS = 7
_SLABS = 3
assert _SLABS >= 3, "two slabs do not read as a sequence marching upward"

# The single source of truth for the mode names. construct() validates against
# it and SCENES is built from it, so the dispatch and the registry cannot drift.
_MODES = ("shadow", "decreasing", "hierarchy")
_DEFAULT_MODE = "shadow"
assert _DEFAULT_MODE in _MODES


class BorelProjectionShadow(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # A mode name that does not exist used to fall through to the default and
        # render the WRONG picture in silence. An earlier episode's generated script asked for
        # 'default' on the scene that carries the 1905 error, which would have
        # drawn the definition of a projection instead of the failure that is the
        # whole point of the scene. Nothing downstream catches that - the
        # check only warns when mode is MISSING. Fail loudly instead: a raise fails the render and raises the placeholder banner.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"borel_projection_shadow: unknown mode {mode!r}. "
                f"Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "decreasing":
            self._decreasing(duration)
        elif mode == "hierarchy":
            self._hierarchy(duration)
        else:
            self._shadow(duration)

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

        Same helper as lebesgue_vs_riemann.py, and for the same reason: these
        scenes really run 40-60 seconds, so one pace() step is 6-9 seconds, and
        handing that to FadeIn on Japanese text leaves the line at half opacity
        until the narration has moved on. Cap the fade, give the
        remainder back as a wait.

        fade + rest == run_time exactly, so the scene cannot overrun.

        Shapes are NOT put through this - the blob, the axis and the slabs read
        well appearing slowly, and leaving them long keeps the frame moving.
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

    def _axis(self, y, x0, x1):
        return Line(
            np.array([x0, y, 0.0]),
            np.array([x1, y, 0.0]),
            color=EDGE_COLOR,
            stroke_width=3,
        )

    def _blob(self, cx, cy, rx, ry, color, samples=160):
        """A closed wobbly region, so the shadow is visibly not the blob."""
        pts = []
        for i in range(samples + 1):
            a = 2.0 * math.pi * i / samples
            r = 1.0 + 0.22 * math.sin(3.0 * a) + 0.10 * math.sin(5.0 * a + 0.9)
            pts.append(np.array([cx + rx * r * math.cos(a), cy + ry * r * math.sin(a), 0.0]))
        m = VMobject(color=color, stroke_width=3)
        m.set_points_as_corners(pts)
        m.set_fill(color, opacity=0.20)
        return m

    # -- mode: shadow ---------------------------------------------------------
    def _shadow(self, duration):
        title = self._title("平面の集合と、その影")

        axis_y = -1.05
        axis = self._axis(axis_y, -5.6, 5.6)

        blob = self._blob(-0.20, 1.10, 2.45, 1.05, ACCENT_CYAN)
        blob_label = Text("平面の集合", font=FONT, font_size=27, color=ACCENT_CYAN)
        blob_label.move_to(np.array([3.55, 1.75, 0.0]))

        left = blob.get_left()[0]
        right = blob.get_right()[0]
        shadow = Line(
            np.array([left, axis_y, 0.0]),
            np.array([right, axis_y, 0.0]),
            color=ACCENT_GOLD,
            stroke_width=9,
        )
        shadow_label = Text("影", font=FONT, font_size=27, color=ACCENT_GOLD)
        shadow_label.move_to(np.array([right + 0.62, axis_y, 0.0]))

        rays = VGroup()
        for i in range(_RAYS):
            x = left + (right - left) * (i + 0.5) / _RAYS
            # Drop from the underside of the blob at this x.
            top = blob.get_center()[1]
            rays.add(
                Line(
                    np.array([x, top, 0.0]),
                    np.array([x, axis_y + 0.06, 0.0]),
                    color=TEXT_DIM,
                    stroke_width=1.6,
                ).set_stroke(opacity=0.55)
            )

        # This mode only DEFINES the projection; the blob drawn here is tame and
        # its shadow really is one clean interval. Asserting here that shadows do
        # not keep their parentage would be a claim the frame does not show - the
        # failure belongs to 'decreasing'. So this poses the question instead.
        note = self._note("では、影はもとの素性を受け継ぐのか", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.0, 0.8, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(axis), run_time=rt[0])
        self._reveal(blob, blob_label, run_time=rt[1])
        # Pure shape: the rays keep the long fade so the frame has motion here.
        self.play(FadeIn(rays), run_time=rt[2])
        self._reveal(shadow, shadow_label, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: decreasing (the 1905 error) ------------------------------------
    def _decreasing(self, duration):
        title = self._title("影の共通部分と、共通部分の影")

        axis_y = -0.92
        axis = self._axis(axis_y, -6.5, -0.9)

        slab_x0, slab_x1 = -5.55, -2.15
        slabs = VGroup()
        for i in range(_SLABS):
            r = Rectangle(
                width=slab_x1 - slab_x0,
                height=0.36,
                color=ACCENT_CYAN,
                stroke_width=2.4,
            )
            r.set_fill(ACCENT_CYAN, opacity=0.24 - i * 0.05)
            r.move_to(np.array([(slab_x0 + slab_x1) / 2.0, 0.06 + i * 0.80, 0.0]))
            slabs.add(r)

        upward = Text("さらに上へ、限りなく", font=FONT, font_size=25, color=TEXT_DIM)
        upward.move_to(np.array([(slab_x0 + slab_x1) / 2.0, 2.52, 0.0]))
        self._fit(upward, 3.9)

        shadow = Line(
            np.array([slab_x0, axis_y, 0.0]),
            np.array([slab_x1, axis_y, 0.0]),
            color=ACCENT_GOLD,
            stroke_width=9,
        )
        shadow_cap = Text("どれも同じ影", font=FONT, font_size=25, color=ACCENT_GOLD)
        # ABOVE the axis, in the gap between the lowest slab (bottom y=-0.12) and
        # the axis (y=-0.92). Hung below the axis it landed on the bottom note -
        # found by rendering, not by reading.
        shadow_cap.move_to(np.array([(slab_x0 + slab_x1) / 2.0, -0.48, 0.0]))
        self._fit(shadow_cap, 3.9)

        divider = Line(
            np.array([-0.30, 2.30, 0.0]),
            np.array([-0.30, -1.30, 0.0]),
            color=EDGE_COLOR,
            stroke_width=2,
        ).set_stroke(opacity=0.6)

        head_a = Text("影の共通部分", font=FONT, font_size=28, color=ACCENT_GOLD)
        head_a.move_to(np.array([3.15, 1.62, 0.0]))
        seg_a = Line(
            np.array([1.95, 0.92, 0.0]),
            np.array([4.35, 0.92, 0.0]),
            color=ACCENT_GOLD,
            stroke_width=9,
        )

        head_b = Text("共通部分の影", font=FONT, font_size=28, color=ACCENT_PINK)
        head_b.move_to(np.array([3.15, -0.10, 0.0]))
        empty = Text("空", font=FONT, font_size=34, color=ACCENT_PINK)
        empty.move_to(np.array([3.15, -0.86, 0.0]))

        note = self._note("減っていく集合では、影と極限は入れ替わらない", color=TEXT_WHITE)

        CODA = 2.8
        rt = pace(duration, [0.9, 1.0, 0.8, 0.9, 0.9, 0.9, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self.play(FadeIn(axis), run_time=rt[0])
        self._reveal(slabs, upward, run_time=rt[1])
        self._reveal(shadow, shadow_cap, run_time=rt[2])
        # Pure shape: the divider keeps the long fade.
        self.play(FadeIn(divider), run_time=rt[3])
        self._reveal(head_a, seg_a, run_time=rt[4])
        self._reveal(head_b, empty, run_time=rt[5])
        self._reveal(note, run_time=rt[6])
        self.wait(CODA)

    # -- mode: hierarchy ------------------------------------------------------
    def _hierarchy(self, duration):
        title = self._title("射影は、外側へ出る")

        outer = Ellipse(width=7.0, height=2.6, color=ACCENT_CYAN, stroke_width=3)
        outer.set_fill(ACCENT_CYAN, opacity=0.10)
        outer.move_to(np.array([0.0, 1.35, 0.0]))

        inner = Ellipse(width=3.4, height=1.5, color=ACCENT_GOLD, stroke_width=3)
        inner.set_fill(ACCENT_GOLD, opacity=0.16)
        inner.move_to(np.array([0.0, 1.15, 0.0]))

        outer_label = Text("解析集合", font=FONT, font_size=27, color=ACCENT_CYAN)
        outer_label.move_to(np.array([0.0, 2.28, 0.0]))

        inner_label = Text("ボレル集合", font=FONT, font_size=27, color=ACCENT_GOLD)
        inner_label.move_to(np.array([0.0, 1.15, 0.0]))

        arrow = Arrow(
            start=np.array([1.85, 1.15, 0.0]),
            end=np.array([3.10, 1.15, 0.0]),
            buff=0.0,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.28,
            color=TEXT_WHITE,
        )
        arrow_label = Text("射影", font=FONT, font_size=25, color=TEXT_WHITE)
        arrow_label.move_to(np.array([2.48, 1.66, 0.0]))

        line1 = Text(
            "ボレル集合を射影しても、ボレル集合とは限らない",
            font=FONT,
            font_size=28,
            color=ACCENT_PINK,
        )
        line1.move_to(np.array([0.0, -0.38, 0.0]))
        self._fit(line1, 12.4)

        line2 = Text(
            "補集合も解析集合なら、ボレル集合に戻る",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        line2.move_to(np.array([0.0, -1.24, 0.0]))
        self._fit(line2, 12.4)

        CODA = 2.8
        rt = pace(duration, [1.0, 1.0, 0.9, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        # Every step here carries a label, so all of them are capped.
        self._reveal(outer, outer_label, run_time=rt[0])
        self._reveal(inner, inner_label, run_time=rt[1])
        self._reveal(arrow, arrow_label, run_time=rt[2])
        self._reveal(line1, run_time=rt[3])
        self._reveal(line2, run_time=rt[4])
        self.wait(CODA)


# What each mode actually puts on screen (read by
# qa_manim_consistency.check_narration_names_absent_visual). 'hierarchy' is the
# only mode that draws an arrow, so a narration promising 矢印 over 'shadow' or
# 'decreasing' will be caught.
LINT_VISUAL_ELEMENTS = {
    "shadow": ["横軸", "集合", "影", "線分"],
    "decreasing": ["横軸", "帯", "影", "線分"],
    "hierarchy": ["矢印", "集合", "図"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "shadow": {"people": [], "years": []},
    "decreasing": {"people": [], "years": []},
    "hierarchy": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, BorelProjectionShadow)
