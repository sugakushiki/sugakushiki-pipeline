"""
chladni_figures.py - Chladni figures (vibrating plate / nodal lines) for 数学史記

Episode 036 (Sophie Germain), math pillar 2 (elasticity, visualization-only).

Visualization-focused: shows HOW sand on a bowed metal plate collects along the
"nodal lines" that do not move, forming symmetric geometric figures. Sophie
Germain built the first mathematical theory of these vibrations. The governing
partial differential equation is NOT shown - this is a visual, not a derivation.

Japanese reading is "クラドニ" (Ernst Chladni, German "ch" = k), never シャドニ.

Modes:
    plate       - One square plate. Sand (many dots) is sprinkled, vibrates,
                  then settles onto a cross-shaped set of nodal lines. A tracer
                  dot then traces the nodal cross for continuous motion.
                  Fixed params: ~80 sand dots, cross nodal pattern, seed 36.
    nodal_lines - One plate whose nodal pattern morphs through three vibration
                  modes (cross, diagonal cross, grid), showing that different
                  ways of vibrating give different symmetric figures.
                  Fixed params: 3 patterns cycled.

Duration-aware: reads target duration from _manim_params.json.
No trailing FadeOut (final frame held; transitions handled by video_assembler).
"""

import math
import random

from manim import (
    DOWN,
    UP,
    Dot,
    FadeIn,
    Line,
    Scene,
    Square,
    Text,
    Transform,
    ValueTracker,
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

# Plate geometry (shared)
_CX, _CY = 0.0, -0.15
_HALF = 1.5


class ChladniFigures(Scene):
    """Chladni figures on a vibrating plate. Mode-branching scene.

    Modes:
        plate (default) - sand settles onto a cross-shaped nodal pattern
        nodal_lines     - nodal pattern morphs through three vibration modes
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "plate")

        if mode == "nodal_lines":
            self.build_nodal_lines()
        else:
            self.build_plate()

    def _plate_square(self):
        sq = Square(side_length=2 * _HALF, color=TEXT_DIM, stroke_width=2)
        sq.move_to([_CX, _CY, 0])
        return sq

    # -------------------------------------------------------------------
    # Mode: plate
    # -------------------------------------------------------------------
    def build_plate(self):
        """Sand sprinkled on a plate vibrates and settles onto nodal lines.

        Fixed parameters: ~80 sand dots, cross nodal pattern, random seed 36.
        """
        duration = self._duration
        random.seed(36)

        title = Text("クラドニ図形", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.3)
        subtitle = Text(
            "板に砂をまき、弓で擦って振動させると", font=FONT, font_size=22, color=TEXT_WHITE
        )
        subtitle.next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        plate = self._plate_square()
        self.play(FadeIn(plate), run_time=0.5)

        # Sprinkle sand: many small dots at random positions inside the plate.
        n = 80
        m = 0.18
        sand = []
        base_pos = []
        for _ in range(n):
            x = random.uniform(_CX - _HALF + m, _CX + _HALF - m)
            y = random.uniform(_CY - _HALF + m, _CY + _HALF - m)
            d = Dot(point=[x, y, 0], radius=0.035, color=TEXT_WHITE)
            sand.append(d)
            base_pos.append([x, y, 0])
        sand_group = VGroup(*sand)
        self.play(FadeIn(sand_group), run_time=0.6)

        # Vibrate: small random jitter a couple of times.
        for _ in range(2):
            anims = []
            for d, bp in zip(sand, base_pos, strict=False):
                jx = random.uniform(-0.06, 0.06)
                jy = random.uniform(-0.06, 0.06)
                anims.append(d.animate.move_to([bp[0] + jx, bp[1] + jy, 0]))
            self.play(*anims, run_time=0.35, rate_func=lambda t: t)

        # Reveal the cross nodal lines (the lines that stay still).
        v_line = Line(
            [_CX, _CY - _HALF, 0], [_CX, _CY + _HALF, 0], color=ACCENT_GOLD, stroke_width=2
        )
        h_line = Line(
            [_CX - _HALF, _CY, 0], [_CX + _HALF, _CY, 0], color=ACCENT_GOLD, stroke_width=2
        )
        cross = VGroup(v_line, h_line)
        self.play(FadeIn(cross), run_time=0.5)

        # Settle: each grain moves to the nearer nodal line; remember where.
        settled = []
        settle_anims = []
        for d, bp in zip(sand, base_pos, strict=False):
            if abs(bp[0] - _CX) <= abs(bp[1] - _CY):
                target = [_CX, bp[1], 0]  # vertical line
            else:
                target = [bp[0], _CY, 0]  # horizontal line
            settled.append(target)
            settle_anims.append(d.animate.move_to(target))
        self.play(*settle_anims, run_time=1.6, rate_func=lambda t: t)

        label = Text("砂は動かない「節線」に集まる", font=FONT, font_size=22, color=ACCENT_GOLD)
        label.move_to([0.0, _CY - _HALF - 0.35, 0])
        self.play(FadeIn(label), run_time=0.5)

        # Meaningful continuous motion: the plate is still vibrating, so the
        # settled grains keep trembling slightly IN PLACE on the nodal lines
        # (they jitter around their node - they do NOT wander off it). This is
        # the physical vibration itself, not a time-filler.
        phases = [random.uniform(0.0, 6.2832) for _ in sand]
        amp = 0.03
        tracker = ValueTracker(0.0)

        def tremble(group):
            v = tracker.get_value()
            for i, d in enumerate(sand):
                sx, sy, _sz = settled[i]
                d.move_to(
                    [
                        sx + amp * math.sin(v + phases[i]),
                        sy + amp * math.cos(1.13 * v + phases[i]),
                        0,
                    ]
                )

        sand_group.add_updater(tremble)

        coda = 2.0
        setup = 0.5 + 0.5 + 0.5 + 0.6 + 0.7 + 0.5 + 1.6 + 0.5
        motion = duration - setup - coda
        if motion < 2.0:
            motion = 2.0
        cycles = motion / 1.2
        self.play(
            tracker.animate.set_value(cycles * 6.2832),
            run_time=motion,
            rate_func=lambda t: t,
        )
        sand_group.clear_updaters()
        self.wait(coda)

    # -------------------------------------------------------------------
    # Mode: nodal_lines
    # -------------------------------------------------------------------
    def build_nodal_lines(self):
        """Nodal pattern morphs through three vibration modes.

        Fixed parameters: 3 patterns (cross, diagonal cross, grid) cycled.
        """
        duration = self._duration

        title = Text("クラドニ図形", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.3)
        caption = Text(
            "振動の仕方で、さまざまな対称模様が現れる", font=FONT, font_size=22, color=TEXT_WHITE
        )
        caption.next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(caption), run_time=0.5)

        plate = self._plate_square()
        self.play(FadeIn(plate), run_time=0.5)

        def make_cross():
            return VGroup(
                Line(
                    [_CX, _CY - _HALF, 0], [_CX, _CY + _HALF, 0], color=ACCENT_GOLD, stroke_width=3
                ),
                Line(
                    [_CX - _HALF, _CY, 0], [_CX + _HALF, _CY, 0], color=ACCENT_GOLD, stroke_width=3
                ),
            )

        def make_diagonal():
            return VGroup(
                Line(
                    [_CX - _HALF, _CY - _HALF, 0],
                    [_CX + _HALF, _CY + _HALF, 0],
                    color=ACCENT_CYAN,
                    stroke_width=3,
                ),
                Line(
                    [_CX - _HALF, _CY + _HALF, 0],
                    [_CX + _HALF, _CY - _HALF, 0],
                    color=ACCENT_CYAN,
                    stroke_width=3,
                ),
            )

        def make_grid():
            g = 0.7
            return VGroup(
                Line(
                    [_CX - g, _CY - _HALF, 0],
                    [_CX - g, _CY + _HALF, 0],
                    color=ACCENT_PINK,
                    stroke_width=3,
                ),
                Line(
                    [_CX + g, _CY - _HALF, 0],
                    [_CX + g, _CY + _HALF, 0],
                    color=ACCENT_PINK,
                    stroke_width=3,
                ),
                Line(
                    [_CX - _HALF, _CY - g, 0],
                    [_CX + _HALF, _CY - g, 0],
                    color=ACCENT_PINK,
                    stroke_width=3,
                ),
                Line(
                    [_CX - _HALF, _CY + g, 0],
                    [_CX + _HALF, _CY + g, 0],
                    color=ACCENT_PINK,
                    stroke_width=3,
                ),
            )

        patterns = [make_cross(), make_diagonal(), make_grid()]

        current = patterns[0].copy()
        self.play(FadeIn(current), run_time=0.6)

        # Each pattern is a real vibration mode, so changing pattern is
        # meaningful. Hold on each mode so it is readable, then move to the
        # next; pace to the narration instead of morphing nonstop.
        coda = 2.0
        setup = 0.5 + 0.5 + 0.5 + 0.6
        budget = duration - setup - coda
        if budget < 3.0:
            budget = 3.0
        morph_t = 1.2
        hold = 1.0
        steps = int(budget / (morph_t + hold))
        if steps < len(patterns) - 1:
            steps = len(patterns) - 1
        self.wait(hold)
        for k in range(steps):
            nxt = patterns[(k + 1) % len(patterns)].copy()
            self.play(Transform(current, nxt), run_time=morph_t, rate_func=lambda t: t)
            self.wait(hold)
        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS: on-screen factual claims per mode.
# Only "クラドニ" (Chladni) appears, as the figure's name; no years on screen.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "plate": {"people": [["クラドニ", "Chladni"]], "years": []},
    "nodal_lines": {"people": [["クラドニ", "Chladni"]], "years": []},
}


SCENES = {
    "plate": {
        "class": "ChladniFigures",
        "params": {"mode": "plate"},
        "description": "Sand on a vibrating plate settles onto cross-shaped nodal lines",
    },
    "nodal_lines": {
        "class": "ChladniFigures",
        "params": {"mode": "nodal_lines"},
        "description": "Nodal pattern morphs through three vibration modes (cross, diagonal, grid)",
    },
}
