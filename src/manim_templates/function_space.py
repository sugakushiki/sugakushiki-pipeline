"""
function_space.py - Functions become points of a space

Banach's dissertation treats each function as a single POINT, measures the
distance between two functions as their largest gap (sup norm), and demands
that the resulting space has no holes (completeness). This template draws
that conceptual move - the foundation everything else in the episode
stands on.

SINGLE Scene class with mode dispatch inside construct().

Modes:
    curves_to_points - The move itself. Four different curves appear, then
              each one shrinks into a single dot inside a soft ellipse
              labeled as the space; a few dim dots join them.
              Fixed params: 4 curves -> 4 dots, 8 extra dim dots, 1 ellipse.
    distance - How far apart are two functions? Two non-crossing curves on
              axes, thin sample gaps at 5 positions, and the LARGEST gap
              highlighted as the distance (computed numerically in code, so
              the highlighted gap really is the maximum).
              Fixed params: 2 curves, 5 dim gap lines, 1 highlighted gap,
              formula d(f,g) = max|f(x)-g(x)|.
    completeness - No holes. Two panels: on the left a converging sequence
              whose destination is MISSING (dashed hole), on the right the
              same sequence landing on an existing point.
              Fixed params: 2 panels, 6 dots per panel, 1 dashed hole,
              1 gold limit dot.

No person names and no years appear on screen in any mode - the narration
carries Banach and the dates.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Axes,
    Circle,
    DashedVMobject,
    Dot,
    Ellipse,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    ParametricFunction,
    ReplacementTransform,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR

# Japanese glyphs hang ~0.17 below their centre; subtitle band starts at -2.0.
_BOTTOM_Y = -1.72

_MODES = ("curves_to_points", "distance", "completeness")
_DEFAULT_MODE = "curves_to_points"
assert _DEFAULT_MODE in _MODES


class FunctionSpace(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly instead of silently drawing
        # the default picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"function_space: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "distance":
            self._distance(duration)
        elif mode == "completeness":
            self._completeness(duration)
        else:
            self._curves_to_points(duration)

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
        """FadeIn crisply, hold the remainder (fade + rest == run_time exactly,
        so the scene cannot overrun - an earlier episode)."""
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _pulse(self, m, run_time, color):
        """FadeIn, then Indicate, as SEPARATE plays. Never combine them in one
        AnimationGroup: Indicate records the mobject's state at begin() as the
        restore target, and inside a shared group that state is the transparent
        pre-FadeIn one - the object ends invisible (found on the first an earlier episode
        render: the max-gap line, both limit markers and both fixed-point dots
        vanished). fade + indicate + wait == run_time exactly."""
        fade = min(0.8, run_time)
        self.play(FadeIn(m), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.6, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    # -- mode: curves_to_points -------------------------------------------------
    def _curves_to_points(self, duration):
        title = self._title("関数の一つひとつが、点になる")

        curve_specs = (
            (lambda t: 0.45 * np.sin(3.0 * t), ACCENT_CYAN, -4.6),
            (lambda t: 0.38 * np.exp(0.9 * t) - 0.55, ACCENT_GOLD, -1.55),
            (lambda t: 0.50 * t * t - 0.30, TEXT_WHITE, 1.5),
            (lambda t: 0.42 * np.sin(6.0 * t) * np.exp(-t * t), ACCENT_PINK, 4.55),
        )
        curves = []
        for fn, color, cx in curve_specs:
            c = ParametricFunction(
                lambda t, fn=fn: np.array([t, fn(t), 0.0]),
                t_range=[-1.1, 1.1],
                color=color,
                stroke_width=3.4,
            )
            c.move_to(np.array([cx, 1.75, 0.0]))
            curves.append(c)

        region = Ellipse(width=9.4, height=2.0, color=TEXT_DIM, stroke_width=2.0)
        region.move_to(np.array([0.0, -0.45, 0.0]))
        region_label = Text("関数の空間", font=FONT, font_size=24, color=TEXT_DIM)
        region_label.move_to(np.array([5.95, -0.45, 0.0]))

        dot_positions = ((-3.1, -0.35), (-1.0, -0.95), (1.15, -0.25), (3.2, -0.75))
        dots = []
        for (_fn, color, _cx), (dx, dy) in zip(curve_specs, dot_positions, strict=True):
            d = Dot(np.array([dx, dy, 0.0]), radius=0.11, color=color)
            dots.append(d)

        extra_positions = (
            (-3.9, -0.85),
            (-2.2, -0.25),
            (-0.1, -0.5),
            (0.5, -1.05),
            (2.1, -0.9),
            (2.5, -0.15),
            (3.9, -0.45),
            (-1.6, -0.7),
        )
        extras = VGroup(
            *[Dot(np.array([x, y, 0.0]), radius=0.055, color=TEXT_DIM) for x, y in extra_positions]
        )

        note = self._note("曲線の集まりが、点の集まり ── 空間になる", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.1, 0.9, 1.2, 0.8, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(*curves, run_time=rt[0])
        self._reveal(region, region_label, run_time=rt[1])
        # Each curve folds into its dot. Shapes may take the long run_time;
        # nothing textual is transformed here.
        self.play(
            AnimationGroup(
                *[ReplacementTransform(c, d) for c, d in zip(curves, dots, strict=True)],
                lag_ratio=0.12,
                run_time=rt[2],
            )
        )
        self._reveal(extras, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: distance ----------------------------------------------------------
    def _distance(self, duration):
        title = self._title("二つの関数のあいだの距離")

        axes = Axes(
            x_range=[0.0, 4.0, 1.0],
            y_range=[0.0, 3.6, 1.0],
            x_length=8.6,
            y_length=3.2,
            axis_config={
                "include_ticks": False,
                "include_tip": False,
                "stroke_width": 2.0,
                "color": TEXT_DIM,
            },
        )
        axes.move_to(np.array([-0.6, 0.55, 0.0]))

        def f(x):
            return 1.1 + 0.5 * np.sin(1.7 * x)

        def g(x):
            return 2.3 + 0.42 * np.sin(1.7 * x + 1.2)

        f_graph = axes.plot(f, x_range=[0.05, 3.95], color=ACCENT_CYAN, stroke_width=3.6)
        g_graph = axes.plot(g, x_range=[0.05, 3.95], color=ACCENT_GOLD, stroke_width=3.6)
        f_label = MathTex("f", color=ACCENT_CYAN).scale(0.9)
        f_label.move_to(axes.c2p(0.05, f(0.05)) + np.array([-0.42, 0.0, 0.0]))
        g_label = MathTex("g", color=ACCENT_GOLD).scale(0.9)
        g_label.move_to(axes.c2p(0.05, g(0.05)) + np.array([-0.42, 0.0, 0.0]))

        # The largest gap is found numerically, so the highlighted line really
        # is the maximum (do not hand-pick it).
        xs_dense = np.linspace(0.1, 3.9, 400)
        gaps = np.abs(g(xs_dense) - f(xs_dense))
        x_max = float(xs_dense[int(np.argmax(gaps))])

        sample_lines = VGroup()
        for x in (0.5, 1.3, 2.1, 2.9, 3.7):
            sample_lines.add(
                Line(axes.c2p(x, f(x)), axes.c2p(x, g(x)), color=TEXT_DIM, stroke_width=2.2)
            )
        max_line = Line(
            axes.c2p(x_max, f(x_max)),
            axes.c2p(x_max, g(x_max)),
            color=ACCENT_PINK,
            stroke_width=5.0,
        )

        formula = MathTex(r"d(f,g) = \max_x \left| f(x) - g(x) \right|", color=ACCENT_PINK)
        formula.scale(0.9)
        formula.move_to(np.array([3.2, 2.42, 0.0]))
        self._fit(formula, 5.6)

        note = self._note("距離 = いちばん大きなずれ", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.1, 0.9, 1.1, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(axes, run_time=rt[0])
        self._reveal(f_graph, f_label, g_graph, g_label, run_time=rt[1])
        self._reveal(sample_lines, run_time=rt[2])
        self._pulse(max_line, run_time=rt[3], color=ACCENT_PINK)
        self._reveal(formula, note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: completeness ------------------------------------------------------
    def _completeness(self, duration):
        title = self._title("穴のない空間 ── 完備性")

        def panel(cx, heading, heading_color):
            box = RoundedRectangle(
                corner_radius=0.25,
                width=5.6,
                height=3.0,
                color=TEXT_DIM,
                stroke_width=2.0,
            )
            box.move_to(np.array([cx, 0.35, 0.0]))
            head = Text(heading, font=FONT, font_size=26, color=heading_color)
            head.move_to(np.array([cx, 2.32, 0.0]))
            return box, head

        left_box, left_head = panel(-3.35, "行き先が空間にない", ACCENT_PINK)
        right_box, right_head = panel(3.35, "行き先が必ずある ── 完備", ACCENT_GOLD)
        self._fit(right_head, 5.6)
        self._fit(left_head, 5.6)

        def sequence(cx, with_limit):
            # p_k walks geometrically toward the limit; gaps shrink like 0.55^k.
            limit = np.array([cx + 1.55, 0.05, 0.0])
            start = np.array([cx - 2.25, 1.05, 0.0])
            q = 0.55
            pts = [limit + (start - limit) * (q**k) for k in range(6)]
            dots = VGroup(*[Dot(p, radius=0.075, color=ACCENT_CYAN) for p in pts])
            links = VGroup(
                *[
                    Line(a, b, color=TEXT_DIM, stroke_width=1.8)
                    for a, b in zip(pts[:-1], pts[1:], strict=True)
                ]
            )
            if with_limit:
                target = Dot(limit, radius=0.11, color=ACCENT_GOLD)
            else:
                target = DashedVMobject(
                    Circle(radius=0.17, color=ACCENT_PINK, stroke_width=3.0),
                    num_dashes=10,
                )
                target.move_to(limit)
            return links, dots, target

        l_links, l_dots, l_target = sequence(-3.35, with_limit=False)
        r_links, r_dots, r_target = sequence(3.35, with_limit=True)

        note = self._note("近づき続ける列に、行き先があるか", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.0, 0.9, 1.0, 0.9, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(left_box, left_head, right_box, right_head, run_time=rt[0])
        self._reveal(l_links, l_dots, run_time=rt[1])
        self._pulse(l_target, run_time=rt[2], color=ACCENT_PINK)
        self._reveal(r_links, r_dots, run_time=rt[3])
        self._pulse(r_target, run_time=rt[4], color=ACCENT_GOLD)
        self._reveal(note, run_time=rt[5])
        self.wait(CODA)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "curves_to_points": ["曲線", "点"],
    "distance": ["曲線", "縦線", "数式"],
    "completeness": ["点", "破線"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "curves_to_points": {"people": [], "years": []},
    "distance": {"people": [], "years": []},
    "completeness": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, FunctionSpace)
