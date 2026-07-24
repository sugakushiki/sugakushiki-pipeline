"""
sphere_packing.py - Kepler's conjecture and the six-cornered snowflake for 数学史記

Visualizes the packing problem Kepler raised in his 1611 New Year pamphlet
Strena Seu de Nive Sexangula (On the Six-Cornered Snowflake): what is the
densest way to pack equal spheres? Kepler conjectured that no arrangement
beats the face-centred-cubic / hexagonal close packing, with density
    pi / sqrt(18) = pi / (3*sqrt(2)) ~= 0.74048 (about 74%).
Each sphere then touches twelve others. The conjecture resisted proof until
Thomas Hales announced one in 1998 (formally verified by the Flyspeck
project in 2014). The pamphlet also asked why snowflakes have six-fold
symmetry, an early question of crystallography.

Modes:
    hexagonal_layer - A single close-packed layer of equal circles; the
                      central circle is highlighted touching its six
                      neighbours (planar packing).
                      Fixed params: circle radius 0.40, hex lattice, |centre|
                      <= 1.7.
    cannonball      - A triangular stack of circles (the cannonball pile),
                      with the density pi/sqrt(18) ~= 0.7405 and the note that
                      Hales proved it in 1998.
                      Fixed params: rows of 5,4,3,2,1; radius 0.38.
    snowflake       - A six-fold symmetric snowflake built from six rotated
                      arms, linking hexagonal symmetry to close packing.
                      Fixed params: 6 arms, 60-degree rotation.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 031 (Kepler), packing / crystallography pillar.
"""

import math

import numpy as np
from manim import (
    Circle,
    Dot,
    FadeIn,
    Line,
    MathTex,
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


class SpherePacking(Scene):
    """Kepler's conjecture (1611) on the densest packing of equal spheres."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 14)
        mode = params.get("mode", "hexagonal_layer")

        if mode == "cannonball":
            self._build_cannonball()
        elif mode == "snowflake":
            self._build_snowflake()
        else:
            self._build_hexagonal_layer()

    # ------------------------------------------------------------------
    # Mode: hexagonal_layer
    # ------------------------------------------------------------------
    def _build_hexagonal_layer(self):
        duration = self._duration

        title = Text(
            "ケプラー予想 ── 最密充填 (1611)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.85, 0])

        r = 0.40
        center_off = np.array([-1.4, 0.25, 0.0])
        a1 = np.array([2 * r, 0.0, 0.0])
        a2 = np.array([r, r * math.sqrt(3), 0.0])

        centers = []
        for i in range(-3, 4):
            for j in range(-3, 4):
                p = i * a1 + j * a2
                if np.linalg.norm(p) <= 1.75:
                    centers.append(p)

        circ_group = VGroup()
        for p in centers:
            is_center = np.linalg.norm(p) < 1e-6
            color = ACCENT_GOLD if is_center else ACCENT_CYAN
            c = Circle(radius=r, color=color, stroke_width=2.2)
            c.set_fill(color, opacity=0.18 if not is_center else 0.35)
            c.move_to(center_off + p)
            circ_group.add(c)

        # Lines from the central circle to its six touching neighbours
        contact_lines = VGroup()
        for ang in range(0, 360, 60):
            d = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0.0])
            neigh = center_off + 2 * r * d
            contact_lines.add(Line(center_off, neigh, color=ACCENT_PINK, stroke_width=2.0))

        note1 = Text(
            "平面では各円が",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        note1.move_to([3.0, 1.1, 0])
        note2 = Text(
            "6個に接する",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        note2.move_to([3.0, 0.5, 0])
        note3 = Text(
            "立体では12個に接し",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note3.move_to([3.0, -0.4, 0])
        note4 = Text(
            "それが最密 ── とケプラーは予想した",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        note4.move_to([2.7, -1.85, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(circ_group), run_time=1.2)
        self.play(FadeIn(contact_lines), FadeIn(note1), FadeIn(note2), run_time=0.9)
        self.play(FadeIn(note3), FadeIn(note4), run_time=0.7)

        anim_overhead = 0.7 + 1.2 + 0.9 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: cannonball
    # ------------------------------------------------------------------
    def _build_cannonball(self):
        duration = self._duration

        title = Text(
            "砲弾の積み方 ── 面心立方の最密充填",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.85, 0])

        r = 0.38
        dy = r * math.sqrt(3)
        stack_center = np.array([-2.7, -0.45, 0.0])

        circ_group = VGroup()
        rows = [5, 4, 3, 2, 1]
        for row_idx, count in enumerate(rows):
            y = stack_center[1] + row_idx * dy
            x_start = stack_center[0] + row_idx * r
            for k in range(count):
                x = x_start + k * 2 * r
                c = Circle(radius=r, color=ACCENT_CYAN, stroke_width=2.2)
                c.set_fill(ACCENT_CYAN, opacity=0.22)
                c.move_to([x, y, 0])
                circ_group.add(c)

        density = MathTex(
            r"\frac{\pi}{\sqrt{18}} \approx 0.7405",
            font_size=48,
            color=ACCENT_GOLD,
        )
        density.move_to([3.4, 1.0, 0])

        note1 = Text(
            "空間の約74%を埋める",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        note1.move_to([3.4, 0.0, 0])
        note2 = Text(
            "ヘイルズが1998年に証明",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note2.move_to([3.4, -0.8, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(circ_group), run_time=1.3)
        self.play(FadeIn(density), run_time=0.8)
        self.play(FadeIn(note1), FadeIn(note2), run_time=0.8)

        anim_overhead = 0.7 + 1.3 + 0.8 + 0.8
        self.wait(max(1.0, duration - anim_overhead))

    # ------------------------------------------------------------------
    # Mode: snowflake
    # ------------------------------------------------------------------
    def _build_snowflake(self):
        duration = self._duration

        title = Text(
            "六角の雪片 (1611)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 2.85, 0])

        center = np.array([0.0, 0.5, 0.0])

        def arm(angle_deg):
            a = math.radians(angle_deg)
            d = np.array([math.cos(a), math.sin(a), 0.0])
            perp1 = np.array([math.cos(a + math.radians(60)), math.sin(a + math.radians(60)), 0.0])
            perp2 = np.array([math.cos(a - math.radians(60)), math.sin(a - math.radians(60)), 0.0])
            length = 1.7
            tip = center + length * d
            g = VGroup(Line(center, tip, color=ACCENT_CYAN, stroke_width=3.0))
            for frac, blen in ((0.45, 0.4), (0.7, 0.3)):
                base = center + length * frac * d
                g.add(Line(base, base + blen * perp1, color=ACCENT_CYAN, stroke_width=2.2))
                g.add(Line(base, base + blen * perp2, color=ACCENT_CYAN, stroke_width=2.2))
            return g

        flake = VGroup(*[arm(k * 60) for k in range(6)])
        hub = Dot(center, color=ACCENT_GOLD, radius=0.06)

        note = Text(
            "なぜ雪は六方対称か ── 最密充填への問い",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.85, 0])

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(flake), FadeIn(hub), run_time=1.4)
        self.play(FadeIn(note), run_time=0.6)

        anim_overhead = 0.7 + 1.4 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "hexagonal_layer": {
        "people": [["ケプラー", "Kepler"]],
        "years": ["1611"],
    },
    "cannonball": {
        "people": [["ヘイルズ", "Hales"]],
        "years": ["1998"],
    },
    "snowflake": {
        "people": [],
        "years": ["1611"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "hexagonal_layer": {
        "class": "SpherePacking",
        "params": {"mode": "hexagonal_layer"},
        "description": "One close-packed layer; central circle touches six neighbours (Kepler conjecture, 1611)",
    },
    "cannonball": {
        "class": "SpherePacking",
        "params": {"mode": "cannonball"},
        "description": "Triangular cannonball stack; density pi/sqrt(18) ~= 0.7405, proved by Hales 1998",
    },
    "snowflake": {
        "class": "SpherePacking",
        "params": {"mode": "snowflake"},
        "description": "Six-fold symmetric snowflake from Strena de Nive Sexangula (1611)",
    },
}
