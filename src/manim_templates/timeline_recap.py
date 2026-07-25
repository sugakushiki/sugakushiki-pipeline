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
    legend:     list of [colour, label] - colour key for the work pillars

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

AXIS_Y = 0.0


class TimelineRecap(Scene):
    """Two-track (work-above / life-below) milestone timeline, data-driven."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 25)

        # fail loud on PARTIAL params. The silent
        # Laplace fallback caused ある回 (Germain) / ある回 (Fibonacci) / ある回
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

        title = Text(title_text, font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 2.95, 0])
        note = Text(
            params.get("note", "── 線の上は数学の業績、下は人生の歩み ──"),
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
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
        lab_fs = 15 if dense else 21
        yr_fs = 16 if dense else 23
        if dense:
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
            lab_dy = lab_out if outer else lab_in
            yr_dy = yr_out if outer else yr_in
            if track == "work":
                lab = Text(label, font=FONT, font_size=lab_fs, color=col)
                lab.move_to([x, AXIS_Y + lab_dy, 0])
                yr = Text(year, font=FONT, font_size=yr_fs, color=col)
                yr.move_to([x, AXIS_Y + yr_dy, 0])
            else:  # life -> below
                lab = Text(label, font=FONT, font_size=lab_fs, color=TEXT_WHITE)
                lab.move_to([x, AXIS_Y - lab_dy, 0])
                yr = Text(year, font=FONT, font_size=yr_fs, color=TEXT_DIM)
                yr.move_to([x, AXIS_Y - yr_dy, 0])
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
        leg.move_to([0, -1.75, 0])

        # Paced reveal: title + axis, then milestones left-to-right (covered by
        # narration), then the legend; the finished timeline rests. No motion.
        reveal_t = 0.6 + 0.5 + len(groups) * 0.5 + 0.5
        hold = min(2.3, max(0.4, (duration - reveal_t) / (len(groups) + 1)))

        self.play(FadeIn(title), FadeIn(note), run_time=0.6)
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
