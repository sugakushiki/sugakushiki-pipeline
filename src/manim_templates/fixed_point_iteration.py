"""
fixed_point_iteration.py - Solving sin 1 degree by iteration

Al-Kashi's last treatise finds sin 1 degree from the triple-angle identity:
sin 3deg is constructible, so x = sin 1deg satisfies the cubic
sin 3deg = 3x - 4x^3, rearranged into the fixed-point form
x = (sin 3deg + 4x^3) / 3. Feed an approximation in, a better one comes out,
and the correct digits grow every turn - the shape of modern numerical
root-finding, six centuries early.

ALL iteration values shown in mode 'iterate' are REAL, computed with mpmath
(dps=30) on 2026-08-16 starting from x0 = sin(3deg)/3:
    x0 = 0.017445318747...  -> 4 correct decimals
    x1 = 0.017452397805...  -> 6 correct decimals
    x2 = 0.017452406426...  -> 10 correct decimals
    x3 = 0.017452406437270...-> 13 correct decimals
    x4 = 0.017452406437283497... -> 15 correct decimals
against sin 1deg = 0.0174524064372835128... (do NOT use the DSB-printed
decimal ...571, its last two digits are a misprint - see episode config).

SINGLE Scene class with mode dispatch inside construct().

Modes:
    cubic   - The setup. Triple-angle identity, the remark that sin 3deg is
              constructible while sin 1deg is not, and the fixed-point form.
              Fixed params: 2 formulas, 1 boxed target equation.
    iterate - The engine (THE key mode). The recurrence on top, then five
              generations x0..x4 appearing as rows; in each row the digits
              that already agree with sin 1deg are gold, the rest dim, and the
              gold prefix grows 4 -> 6 -> 10 -> 13 -> 15 correct decimals.
              Fixed params: 5 rows, counts 4/6/10/13/15.
    table   - What it was for. The single stone "sin 1deg" at the bottom and
              the whole sine table (a grid of cells) standing on it.
              Fixed params: 1 stone, 4x7 grid, 1 arrow.

No person names and no years appear on screen in any mode - the narration
carries al-Kashi, Qadi Zada and the dates.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Arrow,
    FadeIn,
    MathTex,
    Rectangle,
    Scene,
    SurroundingRectangle,
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

# Real mpmath values (see module docstring). (label, gold prefix, dim tail,
# correct-decimal count). The prefix is exactly the run of leading characters
# agreeing with sin 1deg = 0.0174524064372835128...
_ITER_ROWS = (
    ("x_0", "0.0174", "45318747\\ldots", "4"),
    ("x_1", "0.017452", "397805\\ldots", "6"),
    ("x_2", "0.0174524064", "2676\\ldots", "10"),
    ("x_3", "0.0174524064372", "707\\ldots", "13"),
    ("x_4", "0.017452406437283", "497\\ldots", "15"),
)

_MODES = ("cubic", "iterate", "table")
_DEFAULT_MODE = "iterate"
assert _DEFAULT_MODE in _MODES


class FixedPointIteration(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly instead of silently drawing
        # the default picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"fixed_point_iteration: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "cubic":
            self._cubic(duration)
        elif mode == "table":
            self._table(duration)
        else:
            self._iterate(duration)

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
        """FadeIn crisply, hold the remainder (same rationale as an earlier episode
        templates: long pace() steps must not stretch text fades). fade + rest
        == run_time exactly, so the scene cannot overrun."""
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    # -- mode: cubic -----------------------------------------------------------
    def _cubic(self, duration):
        title = self._title("作図では出せない角度")

        identity = MathTex(r"\sin 3\theta = 3\sin\theta - 4\sin^3\theta", color=ACCENT_CYAN)
        identity.scale(1.15)
        identity.move_to(np.array([0.0, 1.95, 0.0]))

        known = Text(
            "sin 3度は作図から求められる ── 未知なのは sin 1度",
            font=FONT,
            font_size=27,
            color=TEXT_WHITE,
        )
        known.move_to(np.array([0.0, 0.95, 0.0]))
        self._fit(known, 11.6)

        target = MathTex(r"x = \frac{\sin 3^\circ + 4x^3}{3}", color=ACCENT_GOLD)
        target.scale(1.25)
        target.move_to(np.array([0.0, -0.42, 0.0]))
        frame = SurroundingRectangle(target, color=ACCENT_GOLD, buff=0.28, stroke_width=2.4)

        note = self._note("三次方程式 ── 数で解くしかない", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.1, 1.0, 1.1, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(identity, run_time=rt[0])
        self._reveal(known, run_time=rt[1])
        self._reveal(target, frame, run_time=rt[2])
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)

    # -- mode: iterate (THE key mode) ------------------------------------------
    def _iterate(self, duration):
        title = self._title("回すたびに、正しい桁が増える")

        recurrence = MathTex(r"x_{n+1} = \frac{\sin 3^\circ + 4x_n^3}{3}", color=ACCENT_CYAN)
        recurrence.scale(0.95)
        recurrence.move_to(np.array([-2.2, 2.18, 0.0]))

        head = Text("正しい桁", font=FONT, font_size=22, color=TEXT_DIM)
        head.move_to(np.array([4.85, 2.18, 0.0]))

        rows = []
        ys = (1.38, 0.78, 0.18, -0.42, -1.02)
        for (label, gold, tail, count), y in zip(_ITER_ROWS, ys, strict=True):
            # One MathTex per row, split into three parts so the agreed prefix
            # can be coloured without slicing glyphs of a single submobject.
            m = MathTex(label + " = ", gold, tail, color=TEXT_WHITE)
            m.scale(0.92)
            m[0].set_color(TEXT_WHITE)
            m[1].set_color(ACCENT_GOLD)
            m[2].set_color(TEXT_DIM)
            m.move_to(np.array([-4.55, y, 0.0]), aligned_edge=np.array([-1.0, 0.0, 0.0]))
            c = Text(count, font=FONT, font_size=27, color=ACCENT_GOLD)
            c.move_to(np.array([4.85, y, 0.0]))
            rows.append(VGroup(m, c))

        note = self._note("わずか数回で、円周率と同じ精度に届く", color=ACCENT_PINK)

        CODA = 2.8
        rt = pace(duration, [1.1, 0.8, 0.8, 0.8, 0.8, 0.8, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(recurrence, head, run_time=rt[0])
        for i, row in enumerate(rows):
            self._reveal(row, run_time=rt[1 + i])
        self._reveal(note, run_time=rt[6])
        self.wait(CODA)

    # -- mode: table ------------------------------------------------------------
    def _table(self, duration):
        title = self._title("1度が、表のすべてを決める")

        cols, rows_n = 7, 4
        cw, ch = 0.66, 0.47
        x0 = -(cols - 1) * cw / 2.0
        y_top = 2.25
        cells = VGroup()
        for r in range(rows_n):
            for c in range(cols):
                cell = Rectangle(
                    width=cw - 0.06, height=ch - 0.06, color=ACCENT_CYAN, stroke_width=1.8
                )
                cell.set_fill(ACCENT_CYAN, opacity=0.14)
                cell.move_to(np.array([x0 + c * cw, y_top - r * ch, 0.0]))
                cells.add(cell)
        grid_label = Text("正弦表", font=FONT, font_size=26, color=ACCENT_CYAN)
        grid_label.move_to(np.array([3.75, 2.25, 0.0]))

        arrow = Arrow(
            start=np.array([0.0, -0.62, 0.0]),
            end=np.array([0.0, 0.42, 0.0]),
            buff=0.0,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.22,
            color=TEXT_WHITE,
        )

        stone = Rectangle(width=3.0, height=0.62, color=ACCENT_GOLD, stroke_width=2.6)
        stone.set_fill(ACCENT_GOLD, opacity=0.18)
        stone.move_to(np.array([0.0, -0.98, 0.0]))
        stone_label = MathTex(r"\sin 1^\circ", color=ACCENT_GOLD)
        stone_label.scale(0.95)
        stone_label.move_to(np.array([0.0, -0.98, 0.0]))

        note = self._note("天文表のすべてが、この一つの値の上に建つ", color=TEXT_WHITE)

        CODA = 2.6
        rt = pace(duration, [1.0, 0.9, 1.1, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(stone, stone_label, run_time=rt[0])
        self.play(FadeIn(arrow), run_time=rt[1])
        self._reveal(cells, grid_label, run_time=rt[2])
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "cubic": ["数式"],
    "iterate": ["数式", "数字"],
    "table": ["ます目", "矢印"],
}

# No person names and no years appear on screen in any mode.
LINT_FACTUAL_CLAIMS = {
    "cubic": {"people": [], "years": []},
    "iterate": {"people": [], "years": []},
    "table": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, FixedPointIteration)
