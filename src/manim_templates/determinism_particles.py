"""
determinism_particles.py - Laplace's "intelligence" thought experiment (数学史記)

Visualizes the determinism passage of the Essai philosophique (1814):
particles whose trajectories are fully determined by equations, seen from
three viewpoints - the clockwork universe, the all-knowing "intelligence"
(later nicknamed Laplace's demon), and the human view where unknown
futures dissolve into a fog of probability.

Modes:
    clockwork  - Five particles move CONTINUOUSLY along fixed Lissajous-type
                 curves (drawn faintly) for the whole scene; the equations
                 decide every trajectory. Note fades in mid-motion.
                 Fixed params: 5 particles, paths x = ax sin(fx t + px),
                 y = 0.55 + ay sin(fy t + py); ~2 s static coda.
    demon_view - The same five paths fully lit in gold; dots then ride along
                 the whole curves continuously (the "intelligence" sweeps over
                 past and future at once). [not used by ある回.]
                 Fixed params: same 5 paths; ~2 s static coda.
    human_fog  - Only one particle is tracked: a short observed past segment
                 (cyan), then three dashed hypothetical futures revealed one
                 at a time, each ending in "?"; a dot then keeps riding the
                 observed past up to the present. Other particles barely
                 visible.
                 Fixed params: tracked particle = #1 path, past segment
                 t in [0.10, 0.35] * 2pi, 3 dashed future branches.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 034 (Laplace), demon pillar (math_2).
"""

import math

import numpy as np
from manim import (
    DashedVMobject,
    Dot,
    FadeIn,
    ParametricFunction,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    config,
    linear,
)
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    BG_COLOR,
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

# Fixed particle paths: x = ax sin(fx t + px), y = CY + ay sin(fy t + py)
CY = 0.55
PARTICLES = [
    # (ax,   ay,   fx, fy, px,  py)
    (3.9, 1.55, 1, 2, 0.0, 0.7),
    (3.2, 1.30, 2, 3, 1.1, 0.0),
    (4.3, 1.05, 1, 3, 2.3, 1.6),
    (2.6, 1.60, 3, 2, 0.6, 2.4),
    (3.6, 0.85, 2, 1, 3.4, 0.9),
]
T_NOW = 0.35 * 2 * math.pi


def _pos(spec, t):
    ax, ay, fx, fy, px, py = spec
    return np.array([ax * math.sin(fx * t + px), CY + ay * math.sin(fy * t + py), 0.0])


def _vel(spec, t):
    ax, ay, fx, fy, px, py = spec
    return np.array([ax * fx * math.cos(fx * t + px), ay * fy * math.cos(fy * t + py), 0.0])


def _path_curve(spec, t0, t1, color, stroke_width, opacity):
    curve = ParametricFunction(
        lambda t: _pos(spec, t),
        t_range=[t0, t1],
        color=color,
        stroke_width=stroke_width,
    )
    curve.set_stroke(opacity=opacity)
    return curve


class DeterminismParticles(Scene):
    """Deterministic trajectories: clockwork / demon's view / human fog."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 24)
        mode = params.get("mode", "clockwork")

        if mode == "demon_view":
            self.build_demon_view()
        elif mode == "human_fog":
            self.build_human_fog()
        else:
            self.build_clockwork()

    # ------------------------------------------------------------------
    # Mode: clockwork
    # ------------------------------------------------------------------
    def build_clockwork(self):
        duration = self._duration

        title = Text("時計仕掛けの宇宙", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        self.play(FadeIn(title), run_time=0.6)

        paths = VGroup(*[_path_curve(s, 0, 2 * math.pi, EDGE_COLOR, 2, 0.65) for s in PARTICLES])
        self.play(FadeIn(paths), run_time=1.0)

        tracker = ValueTracker(0.0)
        dots = VGroup()
        for spec in PARTICLES:
            dot = Dot(_pos(spec, 0.0), color=ACCENT_CYAN, radius=0.08)
            dot.add_updater(lambda m, s=spec: m.move_to(_pos(s, tracker.get_value())))
            dots.add(dot)
        self.play(FadeIn(dots), run_time=0.5)

        note = Text(
            "現在の状態が、次の瞬間を完全に決めている", font=FONT, font_size=24, color=TEXT_WHITE
        )
        note.move_to([0, -1.7, 0])

        # Particles keep moving along their fixed curves for the whole scene;
        # the note appears mid-motion. Only a short static coda.
        setup, coda = 0.6 + 1.0 + 0.5, 2.0
        motion = max(5.0, duration - setup - coda)
        span = motion * 0.45  # parameter advance rate (rad/s of the slowest)
        self.play(tracker.animate.set_value(0.6 * span), run_time=0.6 * motion, rate_func=linear)
        self.play(
            tracker.animate.set_value(span), FadeIn(note), run_time=0.4 * motion, rate_func=linear
        )
        for dot in dots:
            dot.clear_updaters()
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: demon_view
    # ------------------------------------------------------------------
    def build_demon_view(self):
        duration = self._duration

        title = Text("『ある知性』の視点", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        self.play(FadeIn(title), run_time=0.6)

        # Dim base paths first, then the full curves light up in gold.
        base = VGroup(*[_path_curve(s, 0, 2 * math.pi, EDGE_COLOR, 2, 0.35) for s in PARTICLES])
        self.play(FadeIn(base), run_time=0.8)

        lit = VGroup(*[_path_curve(s, 0, 2 * math.pi, ACCENT_GOLD, 3.5, 0.9) for s in PARTICLES])
        self.play(FadeIn(lit), run_time=2.0)

        # Dots ride along the FULL lit curves for the whole scene: the
        # "intelligence" sweeps over every trajectory, past and future, at once.
        s = ValueTracker(0.0)
        dots = VGroup()
        for spec in PARTICLES:
            dot = Dot(_pos(spec, 0.0), color=ACCENT_CYAN, radius=0.09)
            dot.add_updater(lambda m, sp=spec: m.move_to(_pos(sp, s.get_value())))
            dots.add(dot)
        self.play(FadeIn(dots), run_time=0.5)

        note = Text(
            "過去も未来も、ひと続きの曲線として見えている",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note.move_to([0, -1.7, 0])
        self.play(FadeIn(note), run_time=0.6)

        setup, coda = 0.6 + 0.8 + 2.0 + 0.5 + 0.6, 2.0
        motion = max(5.0, duration - setup - coda)
        self.play(s.animate.set_value(motion * 0.5), run_time=motion, rate_func=linear)
        for dot in dots:
            dot.clear_updaters()
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: human_fog
    # ------------------------------------------------------------------
    def build_human_fog(self):
        duration = self._duration
        # Static diagram: short holds (<=3.5 s) build it over the first part of
        # the scene; the complete diagram then rests (no fill-motion).
        reveal_t = 0.6 + 0.8 + 0.9 + 3 * 0.6 + 0.6
        hold = min(3.5, max(0.5, (duration - reveal_t) / 7.0))

        title = Text("人間の視点", font=FONT, font_size=30, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.wait(hold)

        # Other particles barely visible
        others = VGroup(
            *[_path_curve(s, 0, 2 * math.pi, EDGE_COLOR, 2, 0.12) for s in PARTICLES[1:]]
        )
        other_dots = VGroup(
            *[Dot(_pos(s, T_NOW), color=TEXT_DIM, radius=0.06) for s in PARTICLES[1:]]
        )
        other_dots.set_opacity(0.25)
        self.play(FadeIn(others), FadeIn(other_dots), run_time=0.8)
        self.wait(hold)

        # Tracked particle: observed past segment + present dot
        spec = PARTICLES[0]
        past_seg = _path_curve(spec, 0.10 * 2 * math.pi, T_NOW, ACCENT_CYAN, 3.5, 0.95)
        now = Dot(_pos(spec, T_NOW), color=ACCENT_CYAN, radius=0.10)
        past_label = Text("観測できた過去", font=FONT, font_size=20, color=ACCENT_CYAN)
        past_label.move_to([5.3, 0.55, 0])
        self.play(FadeIn(past_seg), FadeIn(now), FadeIn(past_label), run_time=0.9)
        self.wait(hold)

        # Three dashed hypothetical futures diverging from the present
        p0 = _pos(spec, T_NOW)
        v = _vel(spec, T_NOW)
        d = v / np.linalg.norm(v)
        n = np.array([-d[1], d[0], 0.0])
        branches = VGroup()
        marks = VGroup()
        for c1, c2, c3 in [(0.3, 0.9, 1.7), (0.0, 0.1, 0.1), (-0.35, -0.95, -1.75)]:
            pts = [
                p0,
                p0 + d * 1.2 + n * c1,
                p0 + d * 2.4 + n * c2,
                p0 + d * 3.4 + n * c3,
            ]
            raw = VMobject(color=TEXT_DIM, stroke_width=2.5)
            raw.set_points_smoothly(pts)
            branch = DashedVMobject(raw, num_dashes=26)
            branch.set_stroke(opacity=0.5)
            branches.add(branch)
            q = Text("?", font=FONT, font_size=26, color=TEXT_DIM)
            q.move_to(pts[-1] + d * 0.35)
            marks.add(q)

        # Reveal the three hypothetical futures one at a time, paced.
        for br, mk in zip(branches, marks, strict=True):
            self.play(FadeIn(br), FadeIn(mk), run_time=0.6)
            self.wait(hold)

        note = Text(
            "全体を知り得ない者にとって、未来は確率でしか語れない",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note.move_to([0, -1.7, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(max(1.0, duration - reveal_t - 6 * hold))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# Abstract particle visualization: no people or years displayed.
LINT_FACTUAL_CLAIMS = {
    "clockwork": {"people": [], "years": []},
    "demon_view": {"people": [], "years": []},
    "human_fog": {"people": [], "years": []},
}


SCENES = {
    "clockwork": {
        "class": "DeterminismParticles",
        "params": {"mode": "clockwork"},
        "description": "Particles move along fixed deterministic curves (clockwork universe)",
    },
    "demon_view": {
        "class": "DeterminismParticles",
        "params": {"mode": "demon_view"},
        "description": "All trajectories lit at once: past and future visible to the intelligence",
    },
    "human_fog": {
        "class": "DeterminismParticles",
        "params": {"mode": "human_fog"},
        "description": "Only a short observed past is known; futures diverge into dashed uncertainty",
    },
}
