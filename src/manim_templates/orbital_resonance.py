"""
orbital_resonance.py - Jupiter-Saturn great inequality and 5:2 near resonance (数学史記)

Laplace's 1785 resolution of the "great inequality": Jupiter appears to
accelerate and Saturn to slow down, but the deviation is not cumulative -
it is a long-period oscillation (~900 years) caused by the 5:2 near
resonance (5 Jupiter periods ~= 2 Saturn periods ~= 59 years).

Modes:
    great_inequality - Sun at centre, Jupiter (inner, cyan) and Saturn
                       (outer, pink) orbit CONTINUOUSLY for the whole scene
                       (Jupiter visibly laps Saturn); a static colour legend
                       sits upper-left, and the observed-anomaly labels
                       (Jupiter speeds up / Saturn slows) fade in mid-motion.
                       Fixed params: orbit radii 1.1 / 1.9 (scene units),
                       angular speed ratio w_S/w_J = 11.86/29.46 ~= 0.403,
                       Jupiter ~1 revolution per 12 s; ~2.5 s static coda.
    resonance_cycle  - Static diagram. The near resonance as numbers:
                       5 x 11.86 ~= 59.3 and 2 x 29.46 ~= 58.9 (years), then a
                       time-vs-deviation sine graph over 1800 years showing one
                       full oscillation per ~900 years (no cumulative drift).
                       Elements are revealed PACED across the scene (holds
                       covered by narration), then the graph rests; no
                       fill-motion.
                       Fixed params: T_J = 11.86 yr, T_S = 29.46 yr,
                       oscillation period ~900 yr, graph spans 1800 yr.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 034 (Laplace), celestial-mechanics pillar (math_1).
"""

import math

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    Axes,
    Circle,
    DashedLine,
    Dot,
    FadeIn,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    config,
    linear,
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
    styled_text,
)

config.background_color = BG_COLOR

# Shared geometry (scene units)
ORBIT_CENTER = np.array([0.0, 0.4, 0.0])
R_JUP = 1.1
R_SAT = 1.9
# Angular speed ratio from real periods: T_J = 11.86 yr, T_S = 29.46 yr
W_RATIO = 11.86 / 29.46  # = w_S / w_J ~= 0.403


def _orbit_point(radius, theta):
    return ORBIT_CENTER + np.array([radius * math.cos(theta), radius * math.sin(theta), 0.0])


class OrbitalResonance(Scene):
    """Jupiter-Saturn great inequality / 5:2 near resonance. Mode-branching."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 24)
        mode = params.get("mode", "great_inequality")

        if mode == "resonance_cycle":
            self.build_resonance_cycle()
        else:
            self.build_great_inequality()

    # ------------------------------------------------------------------
    # Mode: great_inequality
    # ------------------------------------------------------------------
    def build_great_inequality(self):
        duration = self._duration

        title = Text("木星と土星の謎", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        sun = Dot(ORBIT_CENTER, color=ACCENT_GOLD, radius=0.14)
        orbit_j = Circle(radius=R_JUP, color=EDGE_COLOR, stroke_width=2)
        orbit_j.move_to(ORBIT_CENTER)
        orbit_s = Circle(radius=R_SAT, color=EDGE_COLOR, stroke_width=2)
        orbit_s.move_to(ORBIT_CENTER)

        jup = Dot(_orbit_point(R_JUP, 0.0), color=ACCENT_CYAN, radius=0.09)
        sat = Dot(_orbit_point(R_SAT, 2.6), color=ACCENT_PINK, radius=0.09)

        # Static colour legend (upper-left) — robust vs the moving planets.
        leg_j = VGroup(
            Dot(color=ACCENT_CYAN, radius=0.08),
            Text("木星", font=FONT, font_size=22, color=ACCENT_CYAN),
        ).arrange(RIGHT, buff=0.15)
        leg_s = VGroup(
            Dot(color=ACCENT_PINK, radius=0.08),
            Text("土星", font=FONT, font_size=22, color=ACCENT_PINK),
        ).arrange(RIGHT, buff=0.15)
        legend = VGroup(leg_j, leg_s).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        legend.move_to([-5.0, 1.5, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(
            FadeIn(sun),
            FadeIn(orbit_j),
            FadeIn(orbit_s),
            FadeIn(jup),
            FadeIn(sat),
            FadeIn(legend),
            run_time=0.9,
        )

        # Planets orbit CONTINUOUSLY for the whole scene (Jupiter faster).
        theta = ValueTracker(0.0)
        jup.add_updater(lambda m: m.move_to(_orbit_point(R_JUP, theta.get_value())))
        sat.add_updater(lambda m: m.move_to(_orbit_point(R_SAT, 2.6 + W_RATIO * theta.get_value())))

        obs1 = Text("木星は、加速して見える", font=FONT, font_size=22, color=ACCENT_CYAN)
        obs1.move_to([4.3, 1.0, 0])
        obs2 = Text("土星は、減速して見える", font=FONT, font_size=22, color=ACCENT_PINK)
        obs2.move_to([4.3, 0.3, 0])
        note = Text(
            "このまま軌道は崩れていくのか——160年の謎", font=FONT, font_size=24, color=TEXT_WHITE
        )
        note.move_to([0, -1.7, 0])

        # Spread the orbital motion across the whole scene; reveal the
        # explanatory labels mid-motion. Small static coda only.
        setup, coda = 0.6 + 0.9, 2.5
        motion = max(8.0, duration - setup - coda)
        omega = 2 * math.pi / 12.0  # Jupiter ~1 revolution per 12 s
        big = motion * omega
        self.play(theta.animate.set_value(0.40 * big), run_time=0.40 * motion, rate_func=linear)
        self.play(
            theta.animate.set_value(0.65 * big),
            FadeIn(obs1),
            run_time=0.25 * motion,
            rate_func=linear,
        )
        self.play(
            theta.animate.set_value(0.85 * big),
            FadeIn(obs2),
            run_time=0.20 * motion,
            rate_func=linear,
        )
        self.play(
            theta.animate.set_value(big), FadeIn(note), run_time=0.15 * motion, rate_func=linear
        )
        jup.clear_updaters()
        sat.clear_updaters()
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: resonance_cycle
    # ------------------------------------------------------------------
    def build_resonance_cycle(self):
        duration = self._duration

        # This scene is a static diagram. Build every element first, then
        # reveal them paced across the scene so the diagram DEVELOPS while the
        # narration plays. The holds are covered by narration audio (not dead
        # air); the completed graph simply rests at the end. NO fill-motion.
        title = Text("ラプラスが見つけた近共鳴", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])

        # 5 Jupiter periods ~= 2 Saturn periods ~= 59 years
        row1 = styled_text(
            ("木星 5周： ", "text"),
            (r"5 \times 11.86 \approx 59.3", "math"),
            (" 年", "text"),
            font_size=27,
        )
        row1.set_color(ACCENT_CYAN)
        row1.move_to([0, 2.45, 0])
        row2 = styled_text(
            ("土星 2周： ", "text"),
            (r"2 \times 29.46 \approx 58.9", "math"),
            (" 年", "text"),
            font_size=27,
        )
        row2.set_color(ACCENT_PINK)
        row2.move_to([0, 1.85, 0])

        match = Text(
            "ほとんど同じ時間で、めぐり合いが繰り返される",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        match.move_to([0, 1.25, 0])

        # Deviation-vs-time graph: one oscillation per ~900 years
        axes = Axes(
            x_range=[0, 1800, 450],
            y_range=[-1.2, 1.2, 1.2],
            x_length=8.4,
            y_length=1.7,
            axis_config={
                "stroke_width": 2,
                "color": EDGE_COLOR,
                "include_ticks": True,
                "include_tip": False,
            },
        )
        axes.move_to([0, -0.15, 0])
        curve = axes.plot(
            lambda t: math.sin(2 * math.pi * t / 900.0),
            x_range=[0, 1800],
            color=ACCENT_GOLD,
            stroke_width=4,
        )
        y_label = Text("軌道のずれ", font=FONT, font_size=18, color=TEXT_DIM)
        y_label.move_to([-5.35, 0.55, 0])
        x0 = Text("0", font=FONT, font_size=18, color=TEXT_DIM)
        x0.next_to(axes.c2p(0, -1.2), DOWN, buff=0.15)
        x900 = Text("900年", font=FONT, font_size=18, color=TEXT_DIM)
        x900.next_to(axes.c2p(900, -1.2), DOWN, buff=0.15)
        x1800 = Text("1800年", font=FONT, font_size=18, color=TEXT_DIM)
        x1800.next_to(axes.c2p(1800, -1.2), DOWN, buff=0.15)

        marker = DashedLine(axes.c2p(900, -1.2), axes.c2p(900, 1.2), color=TEXT_DIM, stroke_width=2)

        note = Text(
            "ずれは蓄積しない——約900年でもとに戻る振動だった",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note.move_to([0, -1.8, 0])

        # Paced reveal: short holds (<=3.5 s, no empty early frames) build the
        # diagram over the first part of the scene; the COMPLETE diagram then
        # rests for the remainder (narration-covered, no fill-motion).
        reveal_t = 0.6 + 0.7 + 0.7 + 0.7 + 0.7 + 1.6 + 0.5 + 0.6
        hold = min(3.5, max(0.5, (duration - reveal_t) / 6.0))
        self.play(FadeIn(title), run_time=0.6)
        self.wait(hold)
        self.play(FadeIn(row1), run_time=0.7)
        self.play(FadeIn(row2), run_time=0.7)
        self.wait(hold)
        self.play(FadeIn(match), run_time=0.7)
        self.wait(hold)
        self.play(
            FadeIn(axes), FadeIn(y_label), FadeIn(x0), FadeIn(x900), FadeIn(x1800), run_time=0.7
        )
        self.wait(hold)
        self.play(FadeIn(curve), run_time=1.6)
        self.wait(hold)
        self.play(FadeIn(marker), run_time=0.5)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(max(1.0, duration - reveal_t - 5 * hold))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# Planet names (木星/土星) are not people; displayed numbers are durations,
# not calendar years.
LINT_FACTUAL_CLAIMS = {
    "great_inequality": {"people": [], "years": []},
    "resonance_cycle": {"people": [], "years": []},
}


SCENES = {
    "great_inequality": {
        "class": "OrbitalResonance",
        "params": {"mode": "great_inequality"},
        "description": "Jupiter and Saturn orbit the Sun; observed anomaly (Jupiter accelerating, Saturn slowing)",
    },
    "resonance_cycle": {
        "class": "OrbitalResonance",
        "params": {"mode": "resonance_cycle"},
        "description": "5 x 11.86 ~= 2 x 29.46 ~= 59 yr near resonance; deviation oscillates with ~900 yr period",
    },
}
