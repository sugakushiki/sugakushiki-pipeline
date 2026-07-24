"""
pi_polygon_squeeze.py - Zu Chongzhi's pi: squeezing a circle with polygons

Zu Chongzhi (祖沖之, 429-500) pushed Liu Hui's 割円術 (method of exhaustion:
inscribe a regular polygon in a circle and keep doubling its sides) far enough
to bracket pi between 3.1415926 and 3.1415927 (7 decimal places) - a record
that stood for ~900 years. He also gave the fraction 355/113 (密率, milü),
correct to 6 decimal places with a mere 3-digit denominator.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes must live in one class and branch on params["mode"]).

Modes:
    polygon_squeeze - A circle with an inscribed regular polygon whose side
                      count doubles (6 -> 12 -> 24 -> ...). The polygon merges
                      into the circle while a running lower bound (inscribed
                      perimeter / diameter) gains decimal digits toward pi.
                      Fixed: doubling sequence 6,12,24,48,96,384,1536,6144,24576;
                      drawn polygon capped at 192 sides (already circle-like);
                      final lower bound ~3.1415926.
    bounds          - Number-interval squeeze. Inscribed (lower) and
                      circumscribed (upper) bounds trap pi; the bracket tightens
                      6-gon -> 96-gon -> 1536-gon and ends on the HISTORICAL
                      result 3.1415926 < pi < 3.1415927 (7 decimals).
    milu            - Digit-match comparison of the two Zu ratios: 約率 22/7
                      (matches pi to 2 decimals) and 密率 355/113 (matches pi to
                      6 decimals, diverging at the 7th digit). Matching prefix in
                      gold, first diverging digit in pink.

No on-screen person names or years (all values are mathematical), so
LINT_FACTUAL_CLAIMS is empty for every mode.

Reads params from _manim_params.json in the same directory.
"""

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    WHITE,
    Circle,
    Create,
    Dot,
    FadeIn,
    Line,
    MathTex,
    RegularPolygon,
    ReplacementTransform,
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


# ---------------------------------------------------------------------------
# Math helpers (perimeter / diameter for a regular n-gon; diameter cancels)
# ---------------------------------------------------------------------------
def pi_lower(n):
    """Lower bound for pi from an inscribed regular n-gon."""
    return n * math.sin(math.pi / n)


def pi_upper(n):
    """Upper bound for pi from a circumscribed regular n-gon."""
    return n * math.tan(math.pi / n)


class PiPolygonSqueeze(Scene):
    """Single class; construct() dispatches on params['mode']."""

    STEPS = [6, 12, 24, 48, 96, 384, 1536, 6144, 24576]
    DRAW_CAP = 192  # above this the polygon is visually a circle; stop adding sides

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "polygon_squeeze")
        duration = params.get("duration", 26)
        if mode == "bounds":
            self._bounds(duration)
        elif mode == "milu":
            self._milu(duration)
        else:
            self._polygon_squeeze(duration)

    # -- mode: polygon_squeeze ------------------------------------------------
    def _polygon_squeeze(self, duration):
        title = Text("円を、多角形で挟む", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)

        circle_center = LEFT * 3.3
        radius = 1.75
        circle = Circle(radius=radius, color=WHITE, stroke_width=2)
        circle.move_to(circle_center)

        count_header = Text("辺の数", font=FONT, font_size=20, color=TEXT_DIM)
        count_header.move_to(RIGHT * 2.9 + UP * 2.2)
        val_header = Text("内接多角形の周 ÷ 直径", font=FONT, font_size=18, color=ACCENT_CYAN)
        val_header.move_to(RIGHT * 2.9 + DOWN * 0.2)
        caption = Text("辺を倍にするほど、円に近づく", font=FONT, font_size=18, color=TEXT_DIM)
        caption.move_to(RIGHT * 2.9 + DOWN * 1.7)

        self.play(FadeIn(title), Create(circle), run_time=1.2)
        self.play(FadeIn(count_header), FadeIn(val_header), FadeIn(caption), run_time=0.6)

        rt = pace(duration, [1.0] * len(self.STEPS), intro=1.8, coda=3.0)

        prev_poly = prev_count = prev_val = None
        for i, n in enumerate(self.STEPS):
            n_draw = min(n, self.DRAW_CAP)
            poly = RegularPolygon(n=n_draw, color=ACCENT_CYAN, stroke_width=2.5)
            poly.scale(radius)
            poly.move_to(circle_center)

            # The exact side count Zu Chongzhi reached is a reconstruction
            # (12288 / 24576 both cited); the treatise is lost. Show the concrete
            # doubling but hedge the final magnitude to match the narration.
            label = "一万を超える角形" if n == self.STEPS[-1] else f"{n} 角形"
            count = Text(label, font=FONT, font_size=30, color=TEXT_WHITE)
            count.move_to(RIGHT * 2.9 + UP * 1.5)

            val = MathTex(f"{pi_lower(n):.7f}", font_size=34, color=ACCENT_CYAN)
            val.move_to(RIGHT * 2.9 + DOWN * 0.9)

            if prev_poly is None:
                self.play(Create(poly), FadeIn(count), FadeIn(val), run_time=rt[i])
            else:
                self.play(
                    ReplacementTransform(prev_poly, poly),
                    ReplacementTransform(prev_count, count),
                    ReplacementTransform(prev_val, val),
                    run_time=rt[i],
                )
            prev_poly, prev_count, prev_val = poly, count, val

        self.wait(3.0)

    # -- mode: bounds ---------------------------------------------------------
    def _bounds(self, duration):
        title = Text("上から、下から、挟み込む", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        steps = [
            ("6 角形", 3.0, f"{pi_lower(6):.2f} < \\pi < {pi_upper(6):.2f}"),
            ("96 角形", 1.6, f"{pi_lower(96):.4f} < \\pi < {pi_upper(96):.4f}"),
            ("1536 角形", 0.8, f"{pi_lower(1536):.6f} < \\pi < {pi_upper(1536):.6f}"),
        ]
        final_bracket = r"3.1415926 < \pi < 3.1415927"

        rt = pace(duration, [1.0, 1.0, 1.0, 1.3], intro=1.0, coda=3.5)

        count_pos = UP * 1.8
        bar_pos = UP * 0.6
        bracket_pos = DOWN * 0.7

        prev_count = prev_bar = prev_bracket = None
        for i, (label, half, bracket) in enumerate(steps):
            count = Text(label, font=FONT, font_size=26, color=TEXT_WHITE)
            count.move_to(count_pos)

            bar = Line(LEFT * half, RIGHT * half, color=TEXT_DIM, stroke_width=5)
            bar.move_to(bar_pos)
            lo_tick = Line(UP * 0.15, DOWN * 0.15, color=ACCENT_CYAN, stroke_width=5)
            lo_tick.move_to(bar.get_start())
            hi_tick = Line(UP * 0.15, DOWN * 0.15, color=ACCENT_PINK, stroke_width=5)
            hi_tick.move_to(bar.get_end())
            pi_dot = Dot(point=bar_pos, color=ACCENT_GOLD, radius=0.07)
            bar_grp = VGroup(bar, lo_tick, hi_tick, pi_dot)

            br = MathTex(bracket, font_size=34, color=TEXT_WHITE)
            br.move_to(bracket_pos)

            if prev_count is None:
                self.play(FadeIn(count), Create(bar_grp), FadeIn(br), run_time=rt[i])
            else:
                self.play(
                    ReplacementTransform(prev_count, count),
                    ReplacementTransform(prev_bar, bar_grp),
                    ReplacementTransform(prev_bracket, br),
                    run_time=rt[i],
                )
            prev_count, prev_bar, prev_bracket = count, bar_grp, br

        final_count = Text("さらに増やして", font=FONT, font_size=26, color=TEXT_WHITE)
        final_count.move_to(count_pos)
        final_br = MathTex(final_bracket, font_size=40, color=ACCENT_GOLD)
        final_br.move_to(bracket_pos)
        note = Text("小数第7位まで挟み込んだ", font=FONT, font_size=24, color=ACCENT_PINK)
        note.move_to(DOWN * 1.7)
        self.play(
            ReplacementTransform(prev_count, final_count),
            ReplacementTransform(prev_bracket, final_br),
            FadeIn(note),
            run_time=rt[3],
        )
        self.wait(3.5)

    # -- mode: milu -----------------------------------------------------------
    def _milu(self, duration):
        title = Text("密率 355 / 113", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to(UP * 3.0)
        self.play(FadeIn(title), run_time=1.0)

        def make_row(label_str, label_color, pieces, colors, y):
            label = Text(label_str, font=FONT, font_size=24, color=label_color)
            label.move_to(LEFT * 4.4 + UP * y)
            label.set_x(-4.4 + label.width / 2)
            value = MathTex(*pieces, font_size=36)
            for k, c in enumerate(colors):
                value[k].set_color(c)
            value.move_to(LEFT * 0.4 + UP * y)
            value.set_x(-1.2 + value.width / 2)
            return VGroup(label, value)

        pi_row = make_row(
            "円周率 π",
            TEXT_WHITE,
            ["3.141592", "653589", r"\ldots"],
            [ACCENT_GOLD, TEXT_DIM, TEXT_DIM],
            1.7,
        )
        yaku_row = make_row(
            "約率 22 / 7",
            ACCENT_CYAN,
            ["3.14", "2", "857", r"\ldots"],
            [ACCENT_GOLD, ACCENT_PINK, TEXT_DIM, TEXT_DIM],
            0.3,
        )
        milu_row = make_row(
            "密率 355 / 113",
            ACCENT_CYAN,
            ["3.141592", "9", "2035", r"\ldots"],
            [ACCENT_GOLD, ACCENT_PINK, TEXT_DIM, TEXT_DIM],
            -0.9,
        )

        note = Text(
            "分母わずか113で、小数第6位まで一致",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.move_to(DOWN * 1.9)

        rt = pace(duration, [1.0, 1.0, 1.3, 0.8], intro=1.0, coda=3.5)
        self.play(FadeIn(pi_row), run_time=rt[0])
        self.play(FadeIn(yaku_row), run_time=rt[1])
        self.play(FadeIn(milu_row), run_time=rt[2])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(3.5)


# Factual-claim metadata (read by qa_manim_consistency.py). All modes render
# only mathematical values (pi, side counts, fractions) - no person/year claims.
LINT_FACTUAL_CLAIMS = {
    "polygon_squeeze": {"people": [], "years": []},
    "bounds": {"people": [], "years": []},
    "milu": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "polygon_squeeze": PiPolygonSqueeze,
    "bounds": PiPolygonSqueeze,
    "milu": PiPolygonSqueeze,
}
