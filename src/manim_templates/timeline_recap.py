"""
timeline_recap.py - Two-track life/work timeline for the closing (数学史記)

Data-driven: title, milestones and legend are read from _manim_params.json
(supplied per-episode through the scene's visual.params in scene_definition.json),
so ANY episode provides its own chronology with no code change. Falls back to the
Laplace data ONLY when NO data params are given at all. If a caller supplies ANY data key
(title, or the LLM's name/birth_year/life_events/work_events shape) but omits
`milestones`, that is a misconfiguration and we raise rather than silently
shipping Laplace's life events under another episode's title. Real pipeline runs
are normalized to the milestones schema upstream by
script_generator.normalize_timeline_recap_scenes(); this raise is the backstop
for un-normalized / novel schemas.

Layout: a single horizontal time axis; to make "math vs life" readable at a
glance the two are split by POSITION -
    - ABOVE the line: 数学の業績 (work) - coloured by pillar
    - BELOW the line: 人生の歩み (life events) - white
revealed left-to-right (chronological, paced to the narration; no fill-motion),
then the completed timeline rests.

params (visual.params in scene_definition.json):
    title:      str  - heading
    milestones: list of [year, label, track, colour]
                  track  : "work" -> above the line, "life" -> below
                  colour : "white" / "gold" / "cyan" / "pink"
                           (legacy keys "life"/"celestial"/"probability" also work)
    legend:     list of [colour, label] - colour key for the work pillars.
                Entries naming a colour that no milestone uses are dropped, and a
                legend left with fewer than 2 entries is suppressed (one swatch
                distinguishes nothing). Pass [] to state "no legend" explicitly --
                OMITTING the key falls back to Laplace's 天体力学/確率論.
    note:       str - the line under the title. Defaults to the two-track sentence
                only when both tracks are present; an all-work timeline gets no
                note rather than a false claim about what is below the line.

Duration-aware: reads target duration from _manim_params.json.

Used by: any closing recap.
"""

from manim import (
    RIGHT,
    Dot,
    FadeIn,
    Line,
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
)

config.background_color = BG_COLOR

# Colour resolution: new generic names + legacy Laplace keys.
_COLOR = {
    "white": TEXT_WHITE,
    "gold": ACCENT_GOLD,
    "cyan": ACCENT_CYAN,
    "pink": ACCENT_PINK,
    "life": TEXT_WHITE,
    "celestial": ACCENT_GOLD,
    "probability": ACCENT_CYAN,
}

# Fallback data - used only when params supply no milestones.
_DEFAULT_TITLE = "ラプラスの歩んだ時間"
_DEFAULT_MILESTONES = [
    ["1749年", "誕生", "life", "life"],
    ["1785年", "大不等性", "work", "celestial"],
    ["1799年", "内務大臣", "life", "life"],
    ["1813年", "娘を亡くす", "life", "life"],
    ["1814年", "確率の試論", "work", "probability"],
    ["1827年", "没", "life", "life"],
    ["20世紀", "カオス・量子", "work", "probability"],
]
_DEFAULT_LEGEND = [["celestial", "天体力学"], ["probability", "確率論"]]

# The two-track sentence is only TRUE when both tracks are actually on screen
#.
_DEFAULT_NOTE = "── 線の上は数学の業績、下は人生の歩み ──"

AXIS_Y = 0.0


def require_title(params: dict) -> None:
    """Refuse to draw a real episode's milestones under the fallback title.

    The mirror image of the milestones guard, and the one an earlier episode fell
    through: milestones WERE supplied but 'title' was not, so the heading fell
    back to _DEFAULT_TITLE - which names Laplace - and a Dantzig timeline went
    out with another mathematician's name across the top. A default that names a
    specific person is only safe for the no-data self-test.

    Module-level (not inline in construct) so the guard can be unit-tested
    without standing up a Manim Scene.
    """
    if "milestones" in params and not params.get("title"):
        raise ValueError(
            "timeline_recap: 'milestones' supplied but no 'title'. The fallback "
            "title names Laplace, so omitting it puts the wrong person's name on "
            "screen. Supply params.title (e.g. '<主題>の歩んだ時間'). Omit ALL "
            "data keys for the self-test."
        )


class TimelineRecap(Scene):
    """Two-track (work-above / life-below) milestone timeline, data-driven."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 25)

        # fail loud on PARTIAL params. The silent
        # Laplace fallback caused an earlier episode (Germain) / an earlier episode (Fibonacci) / an earlier episode
        # (Cauchy) to render Laplace's life events (誕生1749 / 大不等性 /
        # 娘を亡くす) under another episode's title. The original guard only
        # watched the template's OWN keys (title/milestones/legend), so when the
        # LLM emitted its natural {name, birth_year, life_events, work_events}
        # schema -- none of which are in that set -- the guard saw "nothing
        # supplied" and silently defaulted to Laplace. Now ANY data key (anything
        # other than the render-control keys) requires `milestones`, else we
        # raise so the pipeline's placeholder banner flags the scene instead of
        # shipping wrong data. Real pipeline runs are normalized to the
        # milestones schema upstream by
        # script_generator.normalize_timeline_recap_scenes(); this raise is the
        # backstop. The Laplace fallback is ONLY for the no-data self-test
        # (e.g. {} or {"mode": "laplace"}).
        # (no silent failures; see internal notes)
        _CONTROL_KEYS = {"duration", "mode"}
        data_keys = set(params) - _CONTROL_KEYS
        if data_keys and "milestones" not in params:
            raise ValueError(
                "timeline_recap: data params "
                f"{sorted(data_keys)} supplied but no 'milestones'. Supply "
                "milestones (list of [year, label, track, colour]); the LLM's "
                "life/work schema is converted upstream by "
                "script_generator.normalize_timeline_recap_scenes(). Omit ALL "
                "data keys for the Laplace self-test."
            )

        require_title(params)

        title_text = params.get("title", _DEFAULT_TITLE)
        milestones = params.get("milestones", _DEFAULT_MILESTONES)
        legend_data = params.get("legend", _DEFAULT_LEGEND)

        # Shape guard: each milestone MUST be a
        # [year, label, track, colour] sequence. A dict-per-milestone shape
        # ({year, life, work}) or any non-sequence slips past the "milestones
        # present?" check and would KeyError cryptically at m[0]. Fail loudly
        # with a clear message instead (normalize upstream or fix the params).
        if milestones and not all(isinstance(m, (list, tuple)) and len(m) >= 4 for m in milestones):
            raise ValueError(
                "timeline_recap milestones must be [year, label, track, colour] "
                f"4-element lists; got {type(milestones[0]).__name__}: "
                f"{repr(milestones[0])[:120]}. Normalize via "
                "script_generator.normalize_timeline_recap_scenes() or fix "
                "visual.params.milestones."
            )

        # Colour guard: the 4th column and the legend colours are KEYS into
        # _COLOR, not colour values. `_COLOR.get(key, TEXT_WHITE)` meant a hex string
        # fell through to white with no complaint, so an earlier episode passed "#4cc9f0"/"#e2b714"
        # and shipped a timeline where every dot was white and the three-entry colour
        # legend labelled three identical white dots. Fail loudly instead: a wrong
        # colour is a silent semantic failure exactly like the partial params.
        bad_colours = sorted(
            {str(m[3]) for m in (milestones or []) if str(m[3]) not in _COLOR}
            | {str(c[0]) for c in (legend_data or []) if str(c[0]) not in _COLOR}
        )
        if bad_colours:
            raise ValueError(
                "timeline_recap colours must be KEYS of _COLOR "
                f"({'/'.join(sorted(_COLOR))}), not colour values. "
                f"Unknown: {bad_colours}. A hex string silently renders as white "
                "."
            )

        # The legend is the KEY that decodes the picture, so derive what it can be
        # rather than trusting what was authored. Two rules:
        #   - drop entries for colours that never appear -> a legend cannot name a
        #     colour the viewer will not see;
        #   - suppress a legend with fewer than 2 entries -> one swatch distinguishes
        #     nothing, and the note already says what the single colour means.
        # Across the 19 episodes using this template, 6 shipped a one-entry legend
        # and 1 shipped a legend naming a colour that is not on screen.
        # What CANNOT be derived is the LABEL for a colour that is used but unnamed;
        # that is a human decision, so qa_manim_consistency warns about it instead.
        used_colours = {str(m[3]) for m in milestones}
        legend_data = [c for c in legend_data if str(c[0]) in used_colours]
        if len(legend_data) < 2:
            if legend_data:
                print(
                    f"[timeline_recap] legend suppressed: {len(legend_data)} entry "
                    "distinguishes nothing"
                )
            legend_data = []

        tracks = {str(m[2]) for m in milestones}
        note_text = params.get("note") or (_DEFAULT_NOTE if len(tracks) >= 2 else "")

        title = Text(title_text, font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 2.95, 0])
        note = None
        if note_text:
            note = Text(note_text, font=FONT, font_size=20, color=TEXT_DIM)
            note.move_to([0, 2.35, 0])
        axis = Line([-6.4, AXIS_Y, 0], [6.4, AXIS_Y, 0], color=EDGE_COLOR, stroke_width=2)

        # Evenly space the milestones across the axis.
        n = max(1, len(milestones))
        x0, x1 = -5.7, 5.7
        step = (x1 - x0) / (n - 1) if n > 1 else 0.0

        # Dense timelines (many milestones) collide horizontally at one level.
        # Shrink the font and stagger labels across TWO vertical levels per track
        # (inner for even index, outer for odd) so neighbours never share a row.
        # Bounds: outer year stays inside note(+2.35) / subtitle(-2.0) clearance.
        dense = len(milestones) > 8
        if not dense and n > 1:
            # Count alone is the wrong trigger: an earlier episode had exactly 8 milestones (so
            # count said "roomy") with 12-13 character labels, and at the roomy font
            # every label was far wider than its 1.63-unit slot -- the render came
            # out as one illegible smear with the first and last labels off-frame.
            # Measure the widest label at the roomy font and switch to the dense
            # layout when it cannot fit its slot. Layouts that already fit are
            # untouched, so no shipped episode changes.
            widest = max(Text(str(m[1]), font=FONT, font_size=21).width for m in milestones)
            if widest > step * 0.95:
                dense = True
        lab_fs = 15 if dense else 21
        yr_fs = 16 if dense else 23
        # A dense stack reaches y=-1.74, which is where the legend sits: the two do
        # not overlap (their bboxes miss each other horizontally, so the bbox
        # collision QA reports "0 collisions") but they READ as one row --
        # "1942  ● 生涯  ● 業績  ● 転機  1970" across the bottom of the frame. Only
        # looking at the render shows it. When both are present, tighten the stack
        # and drop the legend into a row of its own, staying inside the -2.0
        # subtitle clearance. Timelines without a legend keep the roomier spacing,
        # so no shipped episode moves.
        legend_y = -1.75
        if dense:
            if legend_data:
                lab_in, yr_in, lab_out, yr_out = 0.45, 0.80, 1.12, 1.42
                legend_y = -1.85
            else:
                lab_in, yr_in, lab_out, yr_out = 0.5, 0.92, 1.32, 1.74
        else:
            lab_in = lab_out = 0.55
            yr_in = yr_out = 1.05

        groups = []
        for i, m in enumerate(milestones):
            year, label, track, key = m[0], m[1], m[2], m[3]
            x = x0 + i * step
            col = _COLOR.get(key, TEXT_WHITE)
            dot = Dot([x, AXIS_Y, 0], radius=0.09, color=col)
            outer = dense and (i % 2 == 1)
            # The two tracks differ by POSITION ONLY -- that is the whole design of
            # this template ("math vs life split by position"), so dot, label and year
            # all take the milestone's colour and only the sign of the offset changes.
            # They used to diverge in two ways, and both were wrong for the same
            # reason: the legend is the key that decodes the picture, so any element
            # it cannot account for is unreadable.
            #   - the life LABEL was hardcoded TEXT_WHITE, so a milestone keyed "pink"
            #     got a pink dot and a white label;
            #   - the life YEAR was hardcoded TEXT_DIM while the work year took the
            #     colour, so 1970 sat in grey under a pink 転機 label and belonged to
            #     no legend entry at all.
            # Milestones keyed "white" resolve to TEXT_WHITE; the visible change to
            # already-built episodes is that life YEARS render white instead of dim,
            # and only on a rebuild.
            side = 1 if track == "work" else -1
            lab = Text(label, font=FONT, font_size=lab_fs, color=col)
            lab.move_to([x, AXIS_Y + side * (lab_out if outer else lab_in), 0])
            yr = Text(year, font=FONT, font_size=yr_fs, color=col)
            yr.move_to([x, AXIS_Y + side * (yr_out if outer else yr_in), 0])
            groups.append(VGroup(dot, yr, lab))

        # Colour legend for the work pillars (bottom).
        leg_items = []
        for key, lbl in legend_data:
            col = _COLOR.get(key, TEXT_WHITE)
            leg_items.append(
                VGroup(
                    Dot(color=col, radius=0.07),
                    Text(lbl, font=FONT, font_size=19, color=col),
                ).arrange(RIGHT, buff=0.12)
            )
        leg = VGroup(*leg_items).arrange(RIGHT, buff=0.7)
        leg.move_to([0, legend_y, 0])

        # Paced reveal: title + axis, then milestones left-to-right (covered by
        # narration), then the legend; the finished timeline rests. No motion.
        reveal_t = 0.6 + 0.5 + len(groups) * 0.5 + 0.5
        hold = min(2.3, max(0.4, (duration - reveal_t) / (len(groups) + 1)))

        header = [FadeIn(title)] + ([FadeIn(note)] if note is not None else [])
        self.play(*header, run_time=0.6)
        self.play(FadeIn(axis), run_time=0.5)
        self.wait(hold)
        for g in groups:
            self.play(FadeIn(g), run_time=0.5)
            self.wait(hold)
        if leg_items:
            self.play(FadeIn(leg), run_time=0.5)
        self.wait(max(1.0, duration - reveal_t - (len(groups) + 1) * hold))


# -----------------------------------------------------------------------
# Years/labels are now data-driven (per-episode params); nothing is hard-coded
# on screen here, so no static factual claims to lint.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "laplace": {"people": [], "years": []},
}


SCENES = {
    "laplace": {
        "class": "TimelineRecap",
        "params": {},
        "description": "Data-driven two-track timeline (title/milestones/legend from scene visual.params; Laplace fallback)",
    },
}
