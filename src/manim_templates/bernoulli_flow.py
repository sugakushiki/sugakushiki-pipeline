"""
bernoulli_flow.py - Bernoulli's principle and the kinetic theory of gases

Episode 043 (Daniel Bernoulli), block 4 (pillar 2, the fluid-dynamics monument).
In Hydrodynamica (1738) Daniel Bernoulli showed that where a fluid flows faster the
pressure drops (Bernoulli's principle, the first form of energy conservation in a
fluid), and -- in the same book -- pictured a gas as a swarm of fast particles whose
impacts on the walls produce the pressure (the precursor of the kinetic theory of
gases). The popular "equal-transit-time" explanation of lift is a myth and is NOT
shown; only the velocity-up / pressure-down relation is depicted.

Modes:
    venturi (default)
        A pipe that narrows in the middle. Particles flow faster through the
        constriction (continuity: narrower section -> higher speed) and the labels
        read pressure-high / speed-slow in the wide part and pressure-low /
        speed-fast in the throat. Equation p + (1/2) rho v^2 = const on screen.
        Fixed params: half-height f(x)=1.15-0.62*exp(-x^2/1.1); particle speed
        proportional to 1/f(x); 5 streamlines.
    kinetic
        A closed box of gas molecules in fast random motion, bouncing off the walls;
        the sum of their impacts is the pressure. The precursor of kinetic theory.
        Fixed params: 14 molecules, elastic reflection at the box walls.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.7 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import math
import random

import numpy as np
from manim import (
    Create,
    Dot,
    FadeIn,
    MathTex,
    Rectangle,
    Scene,
    Text,
    ValueTracker,
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

_CENTER_Y = 0.2


def _f(x):
    """Pipe half-height: wide at the ends, a narrow throat at the centre."""
    return 1.15 - 0.62 * math.exp(-(x * x) / 1.1)


def _wall(sign, color):
    xs = np.linspace(-5.0, 5.0, 160)
    pts = [np.array([x, sign * _f(x) + _CENTER_Y, 0.0]) for x in xs]
    m = VMobject()
    m.set_points_as_corners(pts)
    m.set_stroke(color=color, width=3.0)
    return m


class BernoulliFlow(Scene):
    """Bernoulli's principle (venturi) and kinetic theory of gases (kinetic)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "venturi")
        duration = float(params.get("duration", 26))
        if mode == "kinetic":
            self._build_kinetic(duration)
        else:
            self._build_venturi(duration)

    # ---------------------------------------------------------------- venturi
    def _build_venturi(self, duration):
        title = Text("ベルヌーイの定理", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        top = _wall(+1, TEXT_DIM)
        bot = _wall(-1, TEXT_DIM)
        self.play(Create(top), Create(bot), run_time=1.1)

        formula = MathTex(
            r"p + \tfrac{1}{2}\,\rho v^2 = \text{const}", font_size=28, color=TEXT_WHITE
        )
        formula.move_to([0, 2.05, 0])
        self.play(FadeIn(formula), run_time=0.6)

        wide = Text("広い管：流速おそく圧力は高い", font=FONT, font_size=18, color=ACCENT_GOLD)
        wide.move_to([-3.0, -1.5, 0])
        narrow = Text("狭い管：流速速く圧力は低い", font=FONT, font_size=18, color=ACCENT_PINK)
        narrow.move_to([2.7, -1.5, 0])
        self.play(FadeIn(wide), FadeIn(narrow), run_time=0.6)

        # flowing particles -- continuous motion across the whole scene
        fracs = [-0.72, -0.36, 0.0, 0.36, 0.72]
        self._parts = []
        for frac in fracs:
            for x0 in np.linspace(-4.8, 4.8, 7):
                d = Dot(
                    [x0, frac * _f(x0) + _CENTER_Y, 0],
                    color=ACCENT_CYAN,
                    radius=0.05,
                )
                self._parts.append({"d": d, "x": float(x0), "frac": frac})
        group = VGroup(*[p["d"] for p in self._parts])

        def _flow(m, dt):
            for p in self._parts:
                p["x"] += dt * 2.2 / _f(p["x"])
                if p["x"] > 5.0:
                    p["x"] -= 10.0
                p["d"].move_to([p["x"], p["frac"] * _f(p["x"]) + _CENTER_Y, 0])

        group.add_updater(_flow)
        self.add(group)

        used = 0.7 + 1.1 + 0.6 + 0.6
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        flow = ValueTracker(0.0)
        self.play(flow.animate.set_value(1.0), run_time=motion, rate_func=lambda t: t)
        group.clear_updaters()
        self.wait(coda)

    # ---------------------------------------------------------------- kinetic
    def _build_kinetic(self, duration):
        title = Text("気体は粒子の運動", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        box = Rectangle(width=6.0, height=3.0, color=EDGE_COLOR, stroke_width=3.0)
        box.move_to([0, 0.2, 0])
        self.play(Create(box), run_time=0.9)

        xmin, xmax = -3.0 + 0.08, 3.0 - 0.08
        ymin, ymax = 0.2 - 1.5 + 0.08, 0.2 + 1.5 - 0.08
        rng = random.Random(43)
        self._mol = []
        for _ in range(14):
            pos = np.array([rng.uniform(xmin, xmax), rng.uniform(ymin, ymax), 0.0])
            ang = rng.uniform(0, 2 * math.pi)
            spd = rng.uniform(1.3, 1.9)
            vel = np.array([spd * math.cos(ang), spd * math.sin(ang), 0.0])
            d = Dot(pos, color=ACCENT_CYAN, radius=0.07)
            self._mol.append({"d": d, "p": pos, "v": vel})
        group = VGroup(*[m["d"] for m in self._mol])
        self.play(FadeIn(group), run_time=0.7)

        caption = Text("壁にぶつかる粒子が、圧力を生む", font=FONT, font_size=20, color=TEXT_WHITE)
        caption.move_to([0, -1.7, 0])
        self.play(FadeIn(caption), run_time=0.6)

        def _bounce(m, dt):
            for mol in self._mol:
                mol["p"] = mol["p"] + mol["v"] * dt
                if mol["p"][0] < xmin:
                    mol["p"][0] = xmin
                    mol["v"][0] = abs(mol["v"][0])
                elif mol["p"][0] > xmax:
                    mol["p"][0] = xmax
                    mol["v"][0] = -abs(mol["v"][0])
                if mol["p"][1] < ymin:
                    mol["p"][1] = ymin
                    mol["v"][1] = abs(mol["v"][1])
                elif mol["p"][1] > ymax:
                    mol["p"][1] = ymax
                    mol["v"][1] = -abs(mol["v"][1])
                mol["d"].move_to(mol["p"])

        group.add_updater(_bounce)

        used = 0.7 + 0.9 + 0.7 + 0.6
        coda = 2.0
        motion = max(3.0, duration - used - coda)
        clock = ValueTracker(0.0)
        self.play(clock.animate.set_value(1.0), run_time=motion, rate_func=lambda t: t)
        group.clear_updaters()
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "venturi": {"people": [], "years": []},
    "kinetic": {"people": [], "years": []},
}

SCENES = {
    "venturi": BernoulliFlow,
    "kinetic": BernoulliFlow,
}
