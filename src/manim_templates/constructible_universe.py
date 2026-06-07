"""
constructible_universe.py - Cumulative hierarchy V and constructible L

Visualizes the von Neumann cumulative hierarchy V and Gödel's
constructible universe L. The key insight: L is built from V by
restricting each successor stage to definable subsets only, making L
"thinner" than V. Gödel showed in 1940 that CH (and AC) hold inside L,
hence Con(ZFC) → Con(ZFC + GCH).

Modes:
    cumulative_hierarchy - 5 widening horizontal strips stacked upward
                           representing V_0, V_1, V_2, V_3, V_omega.
                           Side text shows formal definitions:
                           V_0 = ∅, V_{α+1} = P(V_α), V_λ = ⋃ V_α.
                           Fixed params: 5 levels at y={-0.5, 0.0, 0.5,
                           1.0, 1.5}, widths {0.5, 1.5, 2.5, 3.5, 4.5}.
    constructible_L      - Side-by-side comparison: V (cyan, wide) on
                           the left, L (gold, narrow) on the right.
                           Caption: "L は V より細い". Bottom note:
                           "L の中では CH が成立する".
                           Fixed params: V centered x=-2.7 with widths
                           {0.4, 1.2, 2.0, 2.8, 3.4}; L centered x=+2.7
                           with widths {0.4, 0.7, 1.0, 1.3, 1.6}.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 021 (Gödel), math pillar 4 (light, ~1 minute).
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    FadeIn,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

SUBTITLE_Y_LIMIT = -2.0


# Cumulative hierarchy V (mode 1): widening strips
V_LEVELS = [
    # (label_tex, width, y, color)
    (r"V_0", 0.5, -0.5, ACCENT_CYAN),
    (r"V_1", 1.5, 0.0, ACCENT_CYAN),
    (r"V_2", 2.5, 0.5, ACCENT_CYAN),
    (r"V_3", 3.5, 1.0, ACCENT_CYAN),
    (r"V_\omega", 4.5, 1.5, ACCENT_GOLD),
]
LEVEL_HEIGHT = 0.42

# V vs L side-by-side (mode 2)
V_WIDTHS = [0.4, 1.2, 2.0, 2.8, 3.4]
L_WIDTHS = [0.4, 0.7, 1.0, 1.3, 1.6]
V_LABELS = [r"V_0", r"V_1", r"V_2", r"V_3", r"V_\omega"]
L_LABELS = [r"L_0", r"L_1", r"L_2", r"L_3", r"L_\omega"]
SIDE_LEVEL_YS = [-0.5, -0.05, 0.4, 0.85, 1.3]
V_CENTER_X = -2.7
L_CENTER_X = +2.7


class ConstructibleUniverse(Scene):
    """V cumulative hierarchy and L constructible universe."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 15)
        mode = params.get("mode", "cumulative_hierarchy")

        if mode == "constructible_L":
            self.build_constructible_L()
        else:
            self.build_cumulative_hierarchy()

    # -------------------------------------------------------------------
    # Mode: cumulative_hierarchy
    # -------------------------------------------------------------------
    def build_cumulative_hierarchy(self):
        duration = self._duration

        title = Text(
            "累積階層 V ── 集合宇宙の構成",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # Strips and labels
        strips = []
        labels = []
        for label_tex, width, y, color in V_LEVELS:
            strip = Rectangle(
                width=width,
                height=LEVEL_HEIGHT,
                color=color,
                stroke_width=2,
                fill_opacity=0.25,
                fill_color=color,
            )
            strip.move_to(np.array([0, y, 0]))
            strips.append(strip)

            label = MathTex(label_tex, font_size=28, color=color)
            # Place label to the right of the widest strip extent + buffer
            label.move_to(np.array([width / 2 + 0.5, y, 0]))
            labels.append(label)

        # Side definitions on left
        defs = VGroup(
            MathTex(r"V_0 = \emptyset", font_size=26, color=TEXT_WHITE),
            MathTex(r"V_{\alpha+1} = \mathcal{P}(V_\alpha)", font_size=26, color=TEXT_WHITE),
            MathTex(
                r"V_\lambda = \bigcup_{\alpha < \lambda} V_\alpha", font_size=26, color=TEXT_WHITE
            ),
        )
        defs.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        defs.move_to(np.array([-4.7, 0.5, 0]))

        # Bottom caption
        bottom_note = Text(
            "公理から積み上げる集合の宇宙",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        bottom_note.move_to(np.array([0, -1.85, 0]))

        # Animate
        self.play(FadeIn(title), run_time=0.5)

        # Definitions on left
        for d in defs:
            self.play(FadeIn(d), run_time=0.4)

        # Strips, bottom up
        for strip, label in zip(strips, labels, strict=False):
            self.play(FadeIn(strip), FadeIn(label), run_time=0.45)

        self.play(FadeIn(bottom_note), run_time=0.5)

        anim_overhead = 0.5 + 0.4 * len(defs) + 0.45 * len(strips) + 0.5
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: constructible_L
    # -------------------------------------------------------------------
    def build_constructible_L(self):
        duration = self._duration

        title = Text(
            "構成的宇宙 L ── V より細い宇宙",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # Build V cone (left) and L cone (right)
        v_strips = []
        v_labels_only_top = None
        for i, (w, y, lab) in enumerate(zip(V_WIDTHS, SIDE_LEVEL_YS, V_LABELS, strict=False)):
            strip = Rectangle(
                width=w,
                height=LEVEL_HEIGHT * 0.85,
                color=ACCENT_CYAN,
                stroke_width=2,
                fill_opacity=0.25,
                fill_color=ACCENT_CYAN,
            )
            strip.move_to(np.array([V_CENTER_X, y, 0]))
            v_strips.append(strip)

        l_strips = []
        for i, (w, y, lab) in enumerate(zip(L_WIDTHS, SIDE_LEVEL_YS, L_LABELS, strict=False)):
            strip = Rectangle(
                width=w,
                height=LEVEL_HEIGHT * 0.85,
                color=ACCENT_GOLD,
                stroke_width=2,
                fill_opacity=0.3,
                fill_color=ACCENT_GOLD,
            )
            strip.move_to(np.array([L_CENTER_X, y, 0]))
            l_strips.append(strip)

        # Top labels above each cone
        v_top_label = Text(
            "V (累積階層)",
            font=FONT,
            font_size=24,
            color=ACCENT_CYAN,
        )
        v_top_label.move_to(np.array([V_CENTER_X, 2.1, 0]))

        l_top_label = Text(
            "L (構成的宇宙)",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        l_top_label.move_to(np.array([L_CENTER_X, 2.1, 0]))

        # Center caption between cones
        compare = Text(
            "L は V\nより細い",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
            line_spacing=0.8,
        )
        compare.move_to(np.array([0, 0.6, 0]))

        # Bottom: L definition + key result
        l_def_left = MathTex(
            r"L_{\alpha+1} = \mathrm{Def}(L_\alpha)",
            font_size=26,
            color=TEXT_WHITE,
        )
        l_def_left.move_to(np.array([-3.3, -1.25, 0]))

        ch_result = MathTex(
            r"L \models \mathrm{CH}",
            font_size=30,
            color=ACCENT_GOLD,
        )
        ch_result.move_to(np.array([3.0, -1.25, 0]))

        bottom_note = Text(
            "L の中では連続体仮説 CH が成立する",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        bottom_note.move_to(np.array([0, -1.85, 0]))

        # Animate
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(v_top_label), FadeIn(l_top_label), run_time=0.5)

        # Build cones bottom-up
        for vs, ls in zip(v_strips, l_strips, strict=False):
            self.play(FadeIn(vs), FadeIn(ls), run_time=0.4)

        # Center comparison label
        self.play(FadeIn(compare), run_time=0.5)

        # Definitions and CH result
        self.play(FadeIn(l_def_left), FadeIn(ch_result), run_time=0.6)

        self.play(FadeIn(bottom_note), run_time=0.6)

        anim_overhead = 0.5 + 0.5 + 0.4 * len(v_strips) + 0.5 + 0.6 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "cumulative_hierarchy": {"people": [], "years": []},
    "constructible_L": {"people": [], "years": []},
}


SCENES = {
    "cumulative_hierarchy": {
        "class": "ConstructibleUniverse",
        "params": {"mode": "cumulative_hierarchy"},
        "description": "Von Neumann cumulative hierarchy V_0 .. V_omega",
    },
    "constructible_L": {
        "class": "ConstructibleUniverse",
        "params": {"mode": "constructible_L"},
        "description": "Compare V (wide) vs L (narrow): L models CH",
    },
}
