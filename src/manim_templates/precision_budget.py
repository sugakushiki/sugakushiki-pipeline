"""
precision_budget.py - Deciding the error budget before the calculation

Al-Kashi's 1424 Treatise on the Circumference did not chase digits. It declared
a required precision first - the circumference of a circle 600,000 times the
Earth's diameter, correct to within the thickness of a horse's hair - and then
worked BACKWARD to the polygon that precision demands: 3 x 2^28 sides. The
answer, 2 pi to sixteen decimal places, was fixed before the computing began.
Mode 'backward' is that reversal in one picture and is the load-bearing mode of
the episode; do not turn it into a forward "we computed a lot" picture.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file).

Modes:
    question - The race that had no finish line. Three rows of digits:
               Archimedes pinching 3.14 between bounds, Zu Chongzhi 3.1415926
               (7 decimals), Madhava 3.14159265359 (11 decimals), then the
               question nobody had answered.
               Fixed params: 3 rows; digit counts shown are 7 and 11 only
               (Archimedes row deliberately carries no digit count - his bounds
               give 2 correct decimals and the episode makes no digit claim).
    universe - The declared goal. A small disc (the Earth), an arrow saying
               "diameter x 600,000", the largest circle that means anything,
               and the allowed error: one horse's hair.
               Fixed params: 1 small disc, 1 great arc, 1 hair-thin segment.
    backward - The reversal (THE key mode). Top row, dimmed: the usual order
               [calculate] -> [digits appear] -> [when to stop?]. Bottom row,
               gold: his order [fix the error] -> [derive the sides] ->
               [calculate]. Below: 3 x 2^28 = 805,306,368 sides.
               Fixed params: 2 rows of 3 boxes; the side count 805,306,368
               (= 8 oku 530 man 6368 - the 530 is correct, 540 was this
               config's own early transcription slip).
    digits   - The answer. 2 pi = 6.2831853071795865, all sixteen decimals
               correct (verified against mpmath 2026-08-16), converted from
               nine sexagesimal places by al-Kashi himself. The sexagesimal
               digit string is NOT shown (source OCR unverified; see config
               common_errors). No years on screen - the record's timeline
               belongs to timeline_recap.
               Fixed params: 16 decimal digits, badge "16", note "~170 years".

Only mode 'question' shows person names (Archimedes / Zu Chongzhi / Madhava),
declared in LINT_FACTUAL_CLAIMS; the narration names all three (they are in the
episode's key_topics/key_episodes). No years appear on screen in any mode.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Arrow,
    BackgroundRectangle,
    Circle,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
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

# Japanese glyphs hang ~0.17 below their centre and the subtitle band starts at
# y = -2.0, so the lowest text centre sits here.
_BOTTOM_Y = -1.72

_MODES = ("question", "universe", "backward", "digits")
_DEFAULT_MODE = "backward"
assert _DEFAULT_MODE in _MODES


class PrecisionBudget(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown mode names must fail loudly, not fall through to a default
        # that silently draws the wrong picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"precision_budget: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 26)
        if mode == "question":
            self._question(duration)
        elif mode == "universe":
            self._universe(duration)
        elif mode == "digits":
            self._digits(duration)
        else:
            self._backward(duration)

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

        Same helper as borel_projection_shadow.py and for the same reason:
        these scenes run 25-60 seconds, one pace() step can be 4-9 seconds, and
        a fade that long leaves Japanese text half-transparent while the
        narration moves on (an earlier episode trap). fade + rest == run_time exactly,
        so the scene cannot overrun.
        """
        fade = min(min(max(run_time * 0.30, 0.8), 1.5), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    # -- mode: question -------------------------------------------------------
    def _question(self, duration):
        title = self._title("桁の競争には、終わりがなかった")

        # (name, value string, digit-count label or None)
        rows_data = [
            ("アルキメデス", "3.14", "上下から挟んだ"),
            ("祖沖之", "3.1415926", "7桁"),
            ("マーダヴァ", "3.14159265359", "11桁"),
        ]
        rows = []
        ys = (1.85, 0.95, 0.05)
        for (name, value, tag), y in zip(rows_data, ys, strict=True):
            n = Text(name, font=FONT, font_size=27, color=TEXT_WHITE)
            n.move_to(np.array([-4.35, y, 0.0]))
            self._fit(n, 2.9)
            v = Text(value, font=FONT, font_size=30, color=ACCENT_CYAN)
            v.move_to(np.array([-2.65, y, 0.0]), aligned_edge=np.array([-1.0, 0.0, 0.0]))
            t = Text(tag, font=FONT, font_size=24, color=TEXT_DIM)
            t.move_to(np.array([4.55, y, 0.0]))
            self._fit(t, 2.6)
            rows.append(VGroup(n, v, t))

        rule = Line(
            np.array([-5.9, -0.65, 0.0]),
            np.array([5.9, -0.65, 0.0]),
            color=EDGE_COLOR,
            stroke_width=2,
        ).set_stroke(opacity=0.6)

        q1 = Text("桁は、伸びていく", font=FONT, font_size=28, color=TEXT_WHITE)
        q1.move_to(np.array([0.0, -1.02, 0.0]))
        q2 = self._note("けれど ── どこで止めてよいのかを、誰も決めていない", color=ACCENT_PINK)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.0, 1.0, 0.7, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(rows[0], run_time=rt[0])
        self._reveal(rows[1], run_time=rt[1])
        self._reveal(rows[2], run_time=rt[2])
        self.play(FadeIn(rule, q1), run_time=rt[3])
        self._reveal(q2, run_time=rt[4])
        self.wait(CODA)

    def _backed(self, m, buff=0.12):
        """Opaque backing plate so the great arc cannot cut through a label.

        an earlier episode Vision QA flagged 'universe': the gold circle crosses the title,
        the x600,000 label and the error line, eating glyph outlines. Any
        full-width text here WILL be crossed by a circle this large, so instead
        of shuffling coordinates the labels carry their own background.
        """
        return VGroup(BackgroundRectangle(m, color=BG_COLOR, fill_opacity=0.90, buff=buff), m)

    # -- mode: universe -------------------------------------------------------
    def _universe(self, duration):
        title = self._backed(self._title("考えうるかぎり、大きな円"))

        earth = Circle(radius=0.16, color=ACCENT_CYAN, stroke_width=3)
        earth.set_fill(ACCENT_CYAN, opacity=0.35)
        earth.move_to(np.array([-4.6, 1.35, 0.0]))
        earth_label = Text("地球", font=FONT, font_size=26, color=ACCENT_CYAN)
        earth_label.move_to(np.array([-4.6, 2.12, 0.0]))

        arrow = Arrow(
            start=np.array([-3.95, 1.35, 0.0]),
            end=np.array([-1.85, 1.35, 0.0]),
            buff=0.0,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.18,
            color=TEXT_WHITE,
        )
        arrow_label = Text("直径を60万倍に", font=FONT, font_size=25, color=TEXT_WHITE)
        arrow_label.move_to(np.array([-2.9, 1.95, 0.0]))
        self._fit(arrow_label, 2.6)
        arrow_label = self._backed(arrow_label)

        # The great circle: drawn large and cut by the frame, so it reads as
        # something that does not fit on screen.
        great = Circle(radius=5.4, color=ACCENT_GOLD, stroke_width=4)
        great.move_to(np.array([3.4, 1.35, 0.0]))
        great_label = Text("その円周を求める", font=FONT, font_size=27, color=ACCENT_GOLD)
        great_label.move_to(np.array([3.05, 0.62, 0.0]))
        self._fit(great_label, 3.6)
        great_label = self._backed(great_label)

        hair = Line(
            np.array([-1.55, -1.02, 0.0]),
            np.array([1.55, -1.02, 0.0]),
            color=ACCENT_PINK,
            stroke_width=2,
        )
        hair_label = Text("許す誤差 ── 馬の毛1本の太さ", font=FONT, font_size=27, color=ACCENT_PINK)
        hair_label.move_to(np.array([0.0, -0.52, 0.0]))
        self._fit(hair_label, 6.6)
        hair_label = self._backed(hair_label)

        note = self._backed(
            self._note("それより細かな精度は、どんな測定にも現れない", color=TEXT_WHITE)
        )

        CODA = 2.6
        rt = pace(duration, [0.9, 0.9, 1.1, 1.0, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(earth, earth_label, run_time=rt[0])
        self._reveal(arrow, arrow_label, run_time=rt[1])
        self._reveal(great, great_label, run_time=rt[2])
        # The arc was added after the earlier labels, so it draws on top of
        # them; pop the backed labels (and the arrow head) back above the arc.
        self.bring_to_front(title, arrow_label, arrow)
        self._reveal(hair, hair_label, run_time=rt[3])
        self._reveal(note, run_time=rt[4])
        self.wait(CODA)

    # -- mode: backward (THE key mode) ----------------------------------------
    def _box(self, s, x, y, color, dim=False):
        w, h = 3.55, 0.86
        r = Rectangle(width=w, height=h, color=color, stroke_width=2.4)
        if dim:
            r.set_stroke(opacity=0.55)
        t = Text(s, font=FONT, font_size=24, color=color)
        if dim:
            t.set_opacity(0.75)
        g = VGroup(r, t)
        t.move_to(np.array([x, y, 0.0]))
        self._fit(t, w - 0.35)
        r.move_to(np.array([x, y, 0.0]))
        return g

    def _chain_arrow(self, x0, x1, y, color, dim=False):
        a = Arrow(
            start=np.array([x0, y, 0.0]),
            end=np.array([x1, y, 0.0]),
            buff=0.0,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.30,
            color=color,
        )
        if dim:
            a.set_opacity(0.55)
        return a

    def _backward(self, duration):
        title = self._title("精度から、逆算する")

        xs = (-4.15, 0.0, 4.15)
        gap0, gap1 = (-2.30, -1.85), (1.85, 2.30)

        y_top = 2.02
        top_tag = Text("ふつうの順序", font=FONT, font_size=23, color=TEXT_DIM)
        top_tag.move_to(np.array([-4.9, 2.72, 0.0]))
        self._fit(top_tag, 2.6)
        top = VGroup(
            self._box("計算する", xs[0], y_top, TEXT_DIM, dim=True),
            self._chain_arrow(gap0[0], gap0[1], y_top, TEXT_DIM, dim=True),
            self._box("桁が出る", xs[1], y_top, TEXT_DIM, dim=True),
            self._chain_arrow(gap1[0], gap1[1], y_top, TEXT_DIM, dim=True),
            self._box("どこで止める?", xs[2], y_top, TEXT_DIM, dim=True),
        )

        y_bot = 0.62
        bot_tag = Text("彼の順序", font=FONT, font_size=23, color=ACCENT_GOLD)
        bot_tag.move_to(np.array([-4.9, 1.32, 0.0]))
        self._fit(bot_tag, 2.6)
        bot = VGroup(
            self._box("許す誤差を決める", xs[0], y_bot, ACCENT_GOLD),
            self._chain_arrow(gap0[0], gap0[1], y_bot, ACCENT_GOLD),
            self._box("必要な辺の数を逆算", xs[1], y_bot, ACCENT_GOLD),
            self._chain_arrow(gap1[0], gap1[1], y_bot, ACCENT_GOLD),
            self._box("計算する", xs[2], y_bot, ACCENT_GOLD),
        )

        sides = MathTex(r"3 \times 2^{28} = 805{,}306{,}368", color=ACCENT_CYAN)
        sides.scale(1.05)
        sides.move_to(np.array([-1.55, -0.62, 0.0]))
        sides_label = Text("8億をこえる辺の多角形", font=FONT, font_size=26, color=ACCENT_CYAN)
        sides_label.move_to(np.array([3.45, -0.62, 0.0]))
        self._fit(sides_label, 4.6)

        note = self._note("答えの精度は、計算を始める前に決まっていた", color=ACCENT_PINK)

        CODA = 2.8
        rt = pace(duration, [1.0, 1.1, 0.9, 1.1], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(top_tag, top, run_time=rt[0])
        self._reveal(bot_tag, bot, run_time=rt[1])
        self._reveal(sides, sides_label, run_time=rt[2])
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)

    # -- mode: digits ----------------------------------------------------------
    def _digits(self, duration):
        title = self._title("彼の答え")

        # 2 pi to 16 decimal places - verified against mpmath (2026-08-16):
        # |2pi - 6.2831853071795865| = 2.3e-17 < 5e-17. Digits grouped in fours.
        value = MathTex(r"2\pi = 6.2831\,8530\,7179\,5865", color=TEXT_WHITE)
        value.scale(1.5)
        value.move_to(np.array([0.0, 1.45, 0.0]))
        self._fit(value, 12.4)

        underline = Line(
            np.array([value.get_left()[0], 0.72, 0.0]),
            np.array([value.get_right()[0], 0.72, 0.0]),
            color=ACCENT_GOLD,
            stroke_width=5,
        )
        badge = Text("小数点以下16桁 ── すべて正しい", font=FONT, font_size=30, color=ACCENT_GOLD)
        badge.move_to(np.array([0.0, 0.10, 0.0]))
        self._fit(badge, 9.0)

        how = Text("60進小数9桁で求め、自ら10進に換算した", font=FONT, font_size=26, color=TEXT_DIM)
        how.move_to(np.array([0.0, -0.78, 0.0]))
        self._fit(how, 10.0)

        note = self._note("この値は、およそ170年、破られなかった", color=ACCENT_PINK)

        CODA = 2.8
        rt = pace(duration, [1.2, 1.0, 0.9, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), run_time=1.2)
        self._reveal(value, run_time=rt[0])
        self._reveal(underline, badge, run_time=rt[1])
        self._reveal(how, run_time=rt[2])
        self._reveal(note, run_time=rt[3])
        self.wait(CODA)


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check). Only promise-words that actually appear.
LINT_VISUAL_ELEMENTS = {
    "question": ["数字"],
    "universe": ["円", "矢印"],
    "backward": ["矢印", "枠"],
    "digits": ["数式", "数字"],
}

# 'question' is the only mode that shows person names; no years anywhere.
LINT_FACTUAL_CLAIMS = {
    "question": {
        "people": [
            ["アルキメデス", "Archimedes"],
            ["祖沖之", "そちゅうし", "Zu Chongzhi"],
            ["マーダヴァ", "Madhava"],
        ],
        "years": [],
    },
    "universe": {"people": [], "years": []},
    "backward": {"people": [], "years": []},
    "digits": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, PrecisionBudget)
