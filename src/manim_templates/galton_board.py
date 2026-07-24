"""
galton_board.py - Galton board / order emerging from summed chance (数学史記)

Visual for Laplace's 1810 theorem (the first general form of what was later
named the central limit theorem): each individual ball bounces left or right
unpredictably, yet the accumulated whole forms a bell-shaped pile.

Modes:
    drop       - A 6-row peg board. Balls fall one by one along zig-zag paths
                 into 7 bins; bars grow as balls land. The number of balls
                 SCALES with the scene duration (~1 ball / 0.62 s, capped
                 14-48) so the drop fills the whole scene; "the whole forms a
                 hill" note appears once the shape emerges.
                 Fixed params: 6 peg rows, 7 bins; left/right drawn from a
                 fixed-seed RNG (random.Random(20240611)) so the render is
                 reproducible; bar unit auto-scaled to clear the pegs.
    bell_curve - Static diagram. The limit picture: a 13-bin histogram with
                 binomial(12) proportions, then a smooth gold bell curve
                 overlaid. Elements are revealed PACED across the scene (holds
                 covered by narration), then the figure rests; no fill-motion.
                 Fixed params: binomial coefficients C(12,k), peak height
                 2.55 scene units, gaussian sigma = sqrt(3) * 0.36 ~= 0.62.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 034 (Laplace), probability pillar (math_3).
"""

import math
import random

import numpy as np
from manim import (
    Dot,
    FadeIn,
    FadeOut,
    Indicate,
    LaggedStart,
    Line,
    MoveAlongPath,
    ParametricFunction,
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
)

config.background_color = BG_COLOR

# ---------------------------------------------------------------------------
# drop mode geometry
# ---------------------------------------------------------------------------
ROWS = 6
DX = 0.42  # horizontal peg spacing
DY = 0.38  # vertical row spacing
TOP_Y = 2.0  # y of first peg row
ENTRY = np.array([0.0, 2.45, 0.0])
BASE_Y = -1.3  # bin baseline
UNIT_H = 0.20  # bar growth per ball
BAR_W = 0.30

# 14 hand-fixed left/right sequences (deterministic; no runtime randomness).
# Number of 'R' = final bin index k (0..6). Final counts: [1,1,3,4,3,1,1].
BALL_PATHS = [
    "RRLRLL",  # k=3
    "LRLLRL",  # k=2
    "RLRRLR",  # k=4
    "LLLLLL",  # k=0
    "RLLRLR",  # k=3
    "RRRLRR",  # k=5
    "RLLLLR",  # k=2
    "RLRLRR",  # k=4
    "LRRLRL",  # k=3
    "RRRRRR",  # k=6
    "LLRRLL",  # k=2
    "RRLLRL",  # k=3
    "LLRLLL",  # k=1
    "RRRLLR",  # k=4
]

# ---------------------------------------------------------------------------
# bell_curve mode geometry
# ---------------------------------------------------------------------------
BINOM12 = [1, 12, 66, 220, 495, 792, 924, 792, 495, 220, 66, 12, 1]
PEAK_H = 2.55
DX2 = 0.36
BASE2_Y = -1.6
SIGMA = math.sqrt(3) * DX2  # binomial(12, 1/2) variance 3 in index units


class GaltonBoard(Scene):
    """Galton board: individual chance, collective bell-shaped law."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 26)
        mode = params.get("mode", "drop")

        if mode == "bell_curve":
            self.build_bell_curve()
        else:
            self.build_drop()

    # ------------------------------------------------------------------
    # Mode: drop
    # ------------------------------------------------------------------
    def build_drop(self):
        duration = self._duration

        title = Text("ガルトンボード", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Pegs: row i (0..5) has i+1 pegs at x = (k - i/2) * DX
        pegs = VGroup()
        for i in range(ROWS):
            y = TOP_Y - i * DY
            for k in range(i + 1):
                x = (k - i / 2.0) * DX
                pegs.add(Dot([x, y, 0], radius=0.045, color=TEXT_DIM))
        baseline = Line([-2.0, BASE_Y, 0], [2.0, BASE_Y, 0], color=EDGE_COLOR, stroke_width=2)
        self.play(FadeIn(pegs), FadeIn(baseline), run_time=0.9)

        note1 = Text("一粒の行き先は、誰にも分からない", font=FONT, font_size=22, color=TEXT_WHITE)
        note1.move_to([-4.1, 1.6, 0])
        self.play(FadeIn(note1), run_time=0.6)

        # Number of balls scales with the scene length, so the drop fills the
        # whole duration instead of finishing early. Deterministic seed keeps
        # the render reproducible.
        setup = 0.6 + 0.9 + 0.6
        tail = 0.7 + 0.8 + 0.6  # note2 + Indicate + short coda
        drop_budget = max(6.0, duration - setup - tail)
        n_balls = int(min(48, max(14, drop_budget / 0.62)))
        rng = random.Random(20240611)
        seqs = [
            "".join("R" if rng.random() < 0.5 else "L" for _ in range(ROWS)) for _ in range(n_balls)
        ]
        final = [0] * (ROWS + 1)
        for sq in seqs:
            final[sq.count("R")] += 1
        maxc = max(final) or 1
        unit = min(0.26, 1.25 / maxc)  # tallest bar stays clear of the pegs
        per_ball = drop_budget / n_balls

        # Bars (start at zero height)
        counts = [0] * (ROWS + 1)
        bars = []
        for k in range(ROWS + 1):
            x = (k - ROWS / 2.0) * DX
            bar = Rectangle(
                width=BAR_W,
                height=0.001,
                fill_color=ACCENT_CYAN,
                fill_opacity=0.75,
                stroke_color=ACCENT_CYAN,
                stroke_width=1,
            )
            bar.move_to([x, BASE_Y + 0.0005, 0])
            bars.append(bar)
            self.add(bar)

        note2 = Text("それでも、全体は山の形になる", font=FONT, font_size=22, color=ACCENT_GOLD)
        note2.move_to([-4.1, 0.9, 0])
        note2_shown = False

        # Drop the balls one by one along deterministic zig-zag paths.
        for bi, seq in enumerate(seqs):
            k = seq.count("R")
            waypoints = [ENTRY.copy()]
            x = 0.0
            for i, step in enumerate(seq):
                x += DX / 2.0 if step == "R" else -DX / 2.0
                waypoints.append(np.array([x, TOP_Y - i * DY - 0.10, 0.0]))
            new_h = (counts[k] + 1) * unit
            waypoints.append(np.array([x, BASE_Y + new_h + 0.07, 0.0]))

            path = VMobject()
            path.set_points_as_corners(waypoints)
            ball = Dot(ENTRY, color=ACCENT_GOLD, radius=0.07)
            self.add(ball)
            self.play(MoveAlongPath(ball, path), run_time=per_ball * 0.7)

            counts[k] += 1
            x_bin = (k - ROWS / 2.0) * DX
            self.play(
                FadeOut(ball),
                bars[k]
                .animate.stretch_to_fit_height(new_h)
                .move_to([x_bin, BASE_Y + new_h / 2.0, 0]),
                run_time=per_ball * 0.3,
            )

            # Reveal "the whole forms a hill" once the shape is emerging.
            if not note2_shown and bi >= int(n_balls * 0.55):
                self.play(FadeIn(note2), run_time=0.7)
                note2_shown = True

        if not note2_shown:
            self.play(FadeIn(note2), run_time=0.7)
        self.play(Indicate(bars[3], color=ACCENT_PINK, scale_factor=1.1), run_time=0.8)
        self.wait(0.6)

    # ------------------------------------------------------------------
    # Mode: bell_curve
    # ------------------------------------------------------------------
    def build_bell_curve(self):
        duration = self._duration

        title = Text("偶然の和に現れる秩序", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        topnote = Text("玉の数を増やしていくと——", font=FONT, font_size=22, color=TEXT_DIM)
        topnote.move_to([0, 2.55, 0])
        # Static diagram: short holds (<=3.5 s) build it over the first part of
        # the scene; the complete figure then rests (no fill-motion).
        reveal_t = 0.6 + 0.4 + 1.6 + 1.6 + 0.6 + 0.6
        hold = min(3.5, max(0.5, (duration - reveal_t) / 6.0))

        self.play(FadeIn(title), FadeIn(topnote), run_time=0.6)
        self.wait(hold)

        baseline = Line([-2.6, BASE2_Y, 0], [2.6, BASE2_Y, 0], color=EDGE_COLOR, stroke_width=2)
        self.play(FadeIn(baseline), run_time=0.4)
        self.wait(hold)

        peak = max(BINOM12)
        bars = VGroup()
        for k, c in enumerate(BINOM12):
            h = PEAK_H * c / peak
            x = (k - (len(BINOM12) - 1) / 2.0) * DX2
            bar = Rectangle(
                width=BAR_W,
                height=max(h, 0.02),
                fill_color=ACCENT_CYAN,
                fill_opacity=0.75,
                stroke_color=ACCENT_CYAN,
                stroke_width=1,
            )
            bar.move_to([x, BASE2_Y + max(h, 0.02) / 2.0, 0])
            bars.add(bar)
        self.play(
            LaggedStart(*[FadeIn(b) for b in bars], lag_ratio=0.08),
            run_time=1.6,
        )
        self.wait(hold)

        curve = ParametricFunction(
            lambda t: np.array([t, BASE2_Y + PEAK_H * math.exp(-t * t / (2 * SIGMA * SIGMA)), 0.0]),
            t_range=[-2.5, 2.5],
            color=ACCENT_GOLD,
            stroke_width=5,
        )
        self.play(FadeIn(curve), run_time=1.6)
        self.wait(hold)

        side1 = Text("滑らかな釣鐘型が浮かび上がる", font=FONT, font_size=22, color=ACCENT_GOLD)
        side1.move_to([4.45, 1.5, 0])
        side2 = Text("後に『正規分布』と呼ばれる曲線", font=FONT, font_size=20, color=TEXT_DIM)
        side2.move_to([4.45, 0.9, 0])
        self.play(FadeIn(side1), run_time=0.6)
        self.wait(hold)
        self.play(FadeIn(side2), run_time=0.6)
        self.wait(max(1.0, duration - reveal_t - 5 * hold))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# Abstract probability visualization: no people or years displayed.
LINT_FACTUAL_CLAIMS = {
    "drop": {"people": [], "years": []},
    "bell_curve": {"people": [], "years": []},
}


SCENES = {
    "drop": {
        "class": "GaltonBoard",
        "params": {"mode": "drop"},
        "description": "14 balls fall through a 6-row peg board into 7 bins; pile forms a hill (counts 1,1,3,4,3,1,1)",
    },
    "bell_curve": {
        "class": "GaltonBoard",
        "params": {"mode": "bell_curve"},
        "description": "Binomial(12) histogram with smooth gold bell curve (normal distribution) overlaid",
    },
}
