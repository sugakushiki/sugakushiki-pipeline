"""
vowel_chain_onegin.py - What Markov found when he counted the letters of a poem

In January 1913 Markov reported a count of the first 20,000 letters of Pushkin's
Evgenij Onegin (all of chapter one and sixteen stanzas of chapter two, with the
two silent signs removed). He flattened the text to two classes, vowel and
consonant, and asked whether one letter tells you anything about the next.

If the letters were independent, the chance that a letter is a vowel would be
the same 0.432 whatever came before it, and the 19,999 adjacent pairs would hold
about 3,700 vowel-vowel pairs. He counted 1,104 - under a third. Written out as
conditional chances: after a vowel the next letter is a vowel with chance 0.128,
after a consonant with chance 0.663. The preceding letter moves the odds by a
factor of about five.

SINGLE Scene class with mode dispatch inside construct() (visual_generator's
discover_manim_templates picks only the FIRST Scene subclass per file, so all
modes live in one class and branch on params["mode"]).

Modes:
    stream      - Markov's procedure done to one real line of the poem: the verse
                  as written, then the same letters with spaces and punctuation
                  thrown away, coloured gold for vowel and white for consonant,
                  then the same row reduced to bare cells so only the alternation
                  is left.
                  Fixed params: the opening line of Onegin, 25 letters after
                  stripping, of which 10 are vowels, and exactly 1 of the 24
                  adjacent pairs is vowel-vowel. The letter i-kratkoe is counted
                  as a vowel, which is what Markov's own totals require - and
                  that single vowel-vowel pair is the "oj" of the first word,
                  which exists only because of that choice.
    independent - Two bars of the same length, one for "the letter before was a
                  vowel" and one for "it was a consonant", each filled to the
                  chance that the NEXT letter is a vowel. UNDER INDEPENDENCE THE
                  TWO FILLS ARE IDENTICAL, which is the whole point: the previous
                  letter carries no information. From it, the expected number of
                  vowel-vowel pairs among 19,999.
                  Fixed params: both bars filled to 0.432, about 3,700 expected
                  pairs.
    measured    - The same two bars with Markov's measured chances, so cutting
                  from the previous mode to this one changes only the fills.
                  Fixed params: 0.128 against 0.663, a ratio of about 5.
    compare     - Two columns: the roughly 3,700 pairs independence predicts
                  against the 1,104 Markov counted, under a third.
                  Fixed params: about 3,700 against 1,104.

The two-circle picture of the chain itself is deliberately NOT drawn here - that
is chain_forgets_start's `two_state`. Repeating it would show the same diagram
three times over one episode; bars answer the question this template asks ("does
the previous letter change the odds?") more directly than arrows do.

Every number on screen is recomputed at import time from Markov's four published
totals (8,638 vowels, 11,362 consonants, 1,104 vowel-vowel pairs, 20,000 letters)
and checked with assertions, so editing a total without editing this docstring
makes the render fail rather than quietly show a number the narration contradicts.
The stream mode's vowel pattern is likewise derived from the text, not typed.

The predicted count is deliberately shown ROUNDED to the nearest hundred: the
exact figure moves between about 3,700 and 3,731 depending on how p is rounded,
and the narration says "about 3,700" for that reason.

No person names and no years appear on screen, so LINT_FACTUAL_CLAIMS is empty
for every mode.

Reads params from _manim_params.json in the same directory.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    FadeIn,
    Rectangle,
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
# Markov's published totals (1913), and everything derived from them.
# ---------------------------------------------------------------------------
_N = 20000
_VOWELS = 8638
_CONSONANTS = 11362
_VV = 1104  # vowel immediately followed by vowel

_PAIRS = _N - 1
_P = _VOWELS / _N  # 0.4319
_P1 = _VV / _VOWELS  # vowel after vowel   -> 0.128
_VC = _VOWELS - _VV  # consonant after vowel
_CC = (_CONSONANTS - 1) - _VC  # consonant after consonant -> 3827
_P0 = _VC / (_CONSONANTS - 1)  # vowel after consonant -> 0.663

_EXPECTED_VV = _PAIRS * _P * _P  # about 3730 if the letters were independent
_EXPECTED_ROUND = int(round(_EXPECTED_VV, -2))  # shown as "about 3700"
_RATIO = _P0 / _P1  # the previous letter moves the odds by about 5

# Fail loudly rather than render quietly wrong numbers (fail fast, no silent failures).
assert _VOWELS + _CONSONANTS == _N
assert round(_P, 3) == 0.432
assert round(_P1, 3) == 0.128
assert round(_P0, 3) == 0.663
assert _CC == 3827
assert _EXPECTED_ROUND == 3700
assert _VV * 3 < _EXPECTED_VV  # "under a third" is literally true
assert 5.0 <= round(_RATIO, 1) <= 5.4

# ---------------------------------------------------------------------------
# The stream mode works on a real line of the poem rather than a made-up one.
# Pushkin, Evgenij Onegin, the opening line (1825; public domain).
# ---------------------------------------------------------------------------
_VERSE = "Мой дядя самых честных правил"
# i-kratkoe is in the vowel set: Markov's own totals only reproduce if it is.
# The two silent signs are dropped exactly as he dropped them.
_VOWEL_LETTERS = set("аеёиоуыэюяй")
_SILENT = set("ъь")


def _strip(text):
    """Markov's first step: keep the Russian letters, drop everything else."""
    out = []
    for ch in text.lower():
        if ch in _SILENT:
            continue
        if "а" <= ch <= "я" or ch == "ё":
            out.append(ch)
    return "".join(out)


_LETTERS = _strip(_VERSE)
_IS_VOWEL = [ch in _VOWEL_LETTERS for ch in _LETTERS]
_LINE_VV = sum(1 for i in range(len(_IS_VOWEL) - 1) if _IS_VOWEL[i] and _IS_VOWEL[i + 1])

assert len(_LETTERS) == 25
assert sum(_IS_VOWEL) == 10
# One line is already a small version of the whole finding: out of 24 adjacent
# pairs only one is vowel-vowel. (It is the "oj" of the opening word - the very
# pair that only exists because i-kratkoe counts as a vowel.)
assert _LINE_VV == 1

# The lowest drawn text sits here. Japanese glyphs hang about 0.17 below the
# centre they are placed at, and the subtitle band starts at y = -2.0, so a
# caption centred lower than this breaches it - by four pixels, which is not
# something the eye catches (it was found by measuring the rendered frames).
_BOTTOM_Y = -1.72


class VowelChainOnegin(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "stream")
        duration = params.get("duration", 26)
        if mode == "independent":
            self._bars(duration, independent=True)
        elif mode == "measured":
            self._bars(duration, independent=False)
        elif mode == "compare":
            self._compare(duration)
        else:
            self._stream(duration)

    # -- shared ---------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * 3.06)
        return t

    def _fit(self, group, width):
        if group.width > width:
            group.scale_to_fit_width(width)
        return group

    # -- mode: stream ---------------------------------------------------------
    def _stream(self, duration):
        title = self._title("詩を、文字の列として見る")

        verse = Text(_VERSE, font=FONT, font_size=34, color=TEXT_DIM)
        verse.move_to(UP * 1.95)
        self._fit(verse, 11.5)

        letters = VGroup(
            *[
                Text(
                    ch,
                    font=FONT,
                    font_size=38,
                    color=ACCENT_GOLD if v else TEXT_WHITE,
                )
                for ch, v in zip(_LETTERS, _IS_VOWEL, strict=True)
            ]
        )
        letters.arrange(RIGHT, buff=0.14)
        letters.move_to(UP * 0.75)
        self._fit(letters, 12.0)

        cells = VGroup()
        for v in _IS_VOWEL:
            sq = Square(side_length=0.36)
            sq.set_stroke(EDGE_COLOR, width=1.5)
            # The key below says gold and WHITE, so the consonant cells have to
            # read as white rather than as grey.
            sq.set_fill(ACCENT_GOLD if v else TEXT_WHITE, opacity=0.9)
            cells.add(sq)
        cells.arrange(RIGHT, buff=0.09)
        cells.move_to(DOWN * 0.45)
        self._fit(cells, 12.0)

        key = VGroup(
            Text("金は母音", font=FONT, font_size=24, color=ACCENT_GOLD),
            Text("白は子音", font=FONT, font_size=24, color=TEXT_WHITE),
        )
        key.arrange(RIGHT, buff=1.0)
        key.move_to(DOWN * 1.15)

        note = Text(
            f"母音の次がまた母音なのは、この{len(_LETTERS)}文字で{_LINE_VV}回だけ",
            font=FONT,
            font_size=27,
            color=ACCENT_CYAN,
        )
        note.move_to(UP * _BOTTOM_Y)
        self._fit(note, 12.4)

        CODA = 2.6
        rt = pace(duration, [1.0, 1.4, 1.2, 0.6, 0.9], intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(verse), run_time=rt[0])
        # One letter at a time: this IS the procedure, so it should be watched
        # happening rather than appear finished.
        self.play(FadeIn(letters, lag_ratio=0.22), run_time=rt[1])
        self.play(FadeIn(cells, lag_ratio=0.18), run_time=rt[2])
        self.play(FadeIn(key), run_time=rt[3])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(CODA)

    # -- modes: independent / measured ---------------------------------------
    def _bars(self, duration, independent):
        """The same two bars twice; only the fills and the captions differ.

        Bars rather than a state diagram: the question here is whether the
        previous letter changes the odds, and two fills of visibly different
        length answer it without the viewer having to read arrow thicknesses.
        """
        if independent:
            title = self._title("独立なら、直前が何でも同じ")
            after_v, after_c = _P, _P
        else:
            title = self._title("実際は、直前で大きく変わる")
            after_v, after_c = _P1, _P0

        head = Text("次の一文字が母音である確率", font=FONT, font_size=26, color=TEXT_DIM)
        head.move_to(UP * 2.38)

        TRACK_W = 5.9
        TRACK_H = 0.56
        TRACK_X = 0.75  # centre of the track

        def row(label_text, p, colour, y):
            label = Text(label_text, font=FONT, font_size=27, color=TEXT_WHITE)
            label.move_to(RIGHT * (TRACK_X - TRACK_W / 2 - 0.45) + UP * y, aligned_edge=RIGHT)
            track = Rectangle(width=TRACK_W, height=TRACK_H)
            track.set_stroke(EDGE_COLOR, width=2)
            track.move_to(RIGHT * TRACK_X + UP * y)
            fill = Rectangle(width=TRACK_W * p, height=TRACK_H)
            fill.set_stroke(colour, width=2)
            fill.set_fill(colour, opacity=0.55)
            fill.align_to(track, LEFT)
            fill.set_y(track.get_y())
            value = Text(f"{p:.3f}", font=FONT, font_size=30, color=colour)
            value.next_to(track, RIGHT, buff=0.32)
            return label, track, fill, value

        lab_v, trk_v, fil_v, val_v = row("直前が母音", after_v, ACCENT_GOLD, 1.35)
        lab_c, trk_c, fil_c, val_c = row("直前が子音", after_c, ACCENT_PINK, 0.05)

        if independent:
            body = Text(
                f"19999組のうち、母音・母音はおよそ{_EXPECTED_ROUND}組",
                font=FONT,
                font_size=28,
                color=TEXT_WHITE,
            )
            tail = Text("直前は、何も教えてくれない", font=FONT, font_size=28, color=TEXT_DIM)
        else:
            # NOT a restatement of the two values - they are already on screen
            # beside their bars. This line is what the picture is being compared
            # against, so the pair of scenes reads as one argument.
            body = Text(
                f"独立なら、どちらも{_P:.3f}のはずだった",
                font=FONT,
                font_size=28,
                color=TEXT_DIM,
            )
            tail = Text(
                f"直前の一文字で、およそ{round(_RATIO):.0f}倍変わる",
                font=FONT,
                font_size=28,
                color=ACCENT_CYAN,
            )
        body.move_to(DOWN * 1.05)
        self._fit(body, 12.4)
        tail.move_to(UP * _BOTTOM_Y)
        self._fit(tail, 12.4)

        CODA = 2.6
        rt = pace(duration, [0.7, 1.1, 1.1, 0.9, 1.0], intro=1.2, coda=CODA)
        self.play(FadeIn(title), FadeIn(head), run_time=1.2)
        self.play(FadeIn(lab_v), FadeIn(trk_v), FadeIn(lab_c), FadeIn(trk_c), run_time=rt[0])
        self.play(FadeIn(fil_v), FadeIn(val_v), run_time=rt[1])
        self.play(FadeIn(fil_c), FadeIn(val_c), run_time=rt[2])
        self.play(FadeIn(body), run_time=rt[3])
        self.play(FadeIn(tail), run_time=rt[4])
        self.wait(CODA)

    # -- mode: compare --------------------------------------------------------
    def _compare(self, duration):
        title = self._title("独立ならこれだけ、実際はこれだけ")

        base_y = -1.28
        span = 2.75  # the taller column's height
        w = 1.7

        def column(value, top_value, colour, x):
            h = span * value / top_value
            r = Rectangle(width=w, height=h)
            r.set_stroke(colour, width=2.5)
            r.set_fill(colour, opacity=0.4)
            r.move_to(RIGHT * x + UP * (base_y + h / 2))
            return r

        pred = column(_EXPECTED_VV, _EXPECTED_VV, ACCENT_CYAN, -2.9)
        real = column(_VV, _EXPECTED_VV, ACCENT_PINK, 2.9)

        pred_n = Text(f"およそ{_EXPECTED_ROUND}組", font=FONT, font_size=32, color=ACCENT_CYAN)
        pred_n.next_to(pred, UP, buff=0.22)
        real_n = Text(f"{_VV}組", font=FONT, font_size=32, color=ACCENT_PINK)
        real_n.next_to(real, UP, buff=0.22)

        pred_l = Text("独立と仮定したら", font=FONT, font_size=26, color=TEXT_DIM)
        pred_l.move_to(LEFT * 2.9 + UP * _BOTTOM_Y)
        real_l = Text("実際に数えたら", font=FONT, font_size=26, color=TEXT_DIM)
        real_l.move_to(RIGHT * 2.9 + UP * _BOTTOM_Y)

        verdict = Text("3分の1以下", font=FONT, font_size=34, color=ACCENT_GOLD)
        verdict.move_to(UP * 0.42)

        CODA = 2.8
        rt = pace(duration, [1.0, 0.5, 1.2, 0.5, 1.0], intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(pred), run_time=rt[0])
        self.play(FadeIn(pred_n), FadeIn(pred_l), run_time=rt[1])
        self.play(FadeIn(real), run_time=rt[2])
        self.play(FadeIn(real_n), FadeIn(real_l), run_time=rt[3])
        self.play(FadeIn(verdict), run_time=rt[4])
        self.wait(CODA)


# Factual-claim metadata (read by qa_manim_consistency.py). No person names and no
# years appear on screen; every number shown is derived from Markov's four published
# totals and asserted at import time.
# What each mode actually puts on screen (see chain_forgets_start for why).
# `stream` shows one line of the poem as coloured letters and cells - it does NOT
# draw the ten-by-ten grid or the paired columns the counting method describes.
LINT_VISUAL_ELEMENTS = {
    "stream": ["文字", "マス", "母音", "子音"],
    "independent": ["棒グラフ", "確率"],
    "measured": ["棒グラフ", "確率"],
    "compare": ["棒グラフ", "組数"],
}

LINT_FACTUAL_CLAIMS = {
    "stream": {"people": [], "years": []},
    "independent": {"people": [], "years": []},
    "measured": {"people": [], "years": []},
    "compare": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = {
    "stream": VowelChainOnegin,
    "independent": VowelChainOnegin,
    "measured": VowelChainOnegin,
    "compare": VowelChainOnegin,
}
