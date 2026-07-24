"""
pascaline_mechanism.py - Pascal's mechanical calculator (Pascaline, 1642-1645)

Pascal designed the Pascaline beginning in 1642 (age 19) to ease the long
tax-court arithmetic of his father Étienne Pascal, then a tax-court judge
at Rouen. The machine used a chain of geared wheels, one per decimal digit,
in which a full revolution of one wheel (advance by 10) automatically
advanced the next wheel by one. Pascal completed the first working machine
in 1645 and dedicated it to Chancellor Pierre Séguier with a formal letter
of dedication (Lettre dédicatoire à Monseigneur le Chancelier Séguier).
About 20 additional units were produced during his lifetime; roughly 8-9
survive today (CNAM Paris holds 4, the Henri-Lecoq museum in Clermont
holds 2, others in private collections).

This template focuses on the conceptual carry mechanism, not the actual
gear engineering (which used a sautoir, a hooked weighted lever, to
transmit carries even across multiple stages).

Modes:
    gears_view
        Display 6 decimal-digit gears side by side as labeled circles
        (positions 100000, 10000, 1000, 100, 10, 1), each showing the
        current digit at its center, with small tick marks around the
        circle suggesting teeth. All gears initially read 0.
        Fixed params: 6 digit positions, initial value 000000.

    carry_propagation
        Animate the addition of +1 repeatedly to drive the rightmost gear
        through 0..9 and trigger a carry to the next gear. Sequence shown:
            000007 → 000008 → 000009 → 000010 (single carry)
            ... then jump to 000098 → 000099 → 000100 (double carry)
            ... then jump to 000998 → 000999 → 001000 (triple carry)
        At each carry, the affected gear momentarily highlights in
        ACCENT_PINK.
        Fixed params: 6 digit positions, three demonstration sequences.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.3, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 029 (Pascal), 遺産2 - パスカリーヌ.
"""

import math

from manim import (
    Circle,
    Create,
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
    load_params,
)

config.background_color = BG_COLOR

# 6 decimal digits (right-most = 1's place)
N_DIGITS = 6
GEAR_SPACING = 1.10
GEAR_RADIUS = 0.42
GEAR_Y = 0.3  # vertical center for gears
DIGIT_LABELS = ["100000", "10000", "1000", "100", "10", "1"]


def _gear_x(i):
    """X position of digit i (0=leftmost=100000, 5=rightmost=1)."""
    return (i - (N_DIGITS - 1) / 2.0) * GEAR_SPACING


def _make_gear(value, i, color=ACCENT_CYAN):
    """Return a VGroup representing the gear at position i with given digit."""
    cx = _gear_x(i)
    body = Circle(radius=GEAR_RADIUS, color=color, stroke_width=2.0)
    body.move_to([cx, GEAR_Y, 0])
    # Tick marks suggesting teeth — 10 ticks around the circle
    ticks = VGroup()
    for k in range(10):
        a = 2 * math.pi * k / 10
        rin = GEAR_RADIUS * 0.92
        rout = GEAR_RADIUS * 1.08
        p1 = [cx + rin * math.cos(a), GEAR_Y + rin * math.sin(a), 0]
        p2 = [cx + rout * math.cos(a), GEAR_Y + rout * math.sin(a), 0]
        ticks.add(Line(p1, p2, color=color, stroke_width=1.4))
    digit = MathTex(str(value), font_size=28, color=ACCENT_GOLD)
    digit.move_to([cx, GEAR_Y, 0])
    return VGroup(body, ticks, digit)


def _digits_of(n):
    """Return list of 6 decimal digits (msb-first) of n."""
    s = f"{n:06d}"
    return [int(c) for c in s]


class PascalineMechanism(Scene):
    """Pascaline gear-carry mechanism visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "gears_view")
        self._duration = float(params.get("duration", 25))

        if mode == "carry_propagation":
            self._build_carry_propagation()
        else:
            self._build_gears_view()

    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=24, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    def _place_labels(self):
        """Place place-value labels under each gear."""
        labels = VGroup()
        for i, s in enumerate(DIGIT_LABELS):
            lbl = MathTex(s, font_size=18, color=TEXT_DIM)
            lbl.move_to([_gear_x(i), GEAR_Y - GEAR_RADIUS - 0.40, 0])
            labels.add(lbl)
        return labels

    # ------------------------------------------------------------------
    def _build_gears_view(self):
        duration = self._duration
        title = self._title("パスカリーヌ ── 6 桁の歯車")
        self.play(FadeIn(title), run_time=0.6)

        digits = _digits_of(0)
        gears = VGroup(*[_make_gear(d, i) for i, d in enumerate(digits)])
        self.play(*[Create(g) for g in gears], run_time=1.4)

        labels = self._place_labels()
        self.play(*[FadeIn(lab) for lab in labels], run_time=0.6)

        # Explanation message lower
        msg1 = Text(
            "各桁は 0 から 9 を表す歯車",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg1.move_to([0, -1.55, 0])
        self.play(FadeIn(msg1), run_time=0.5)

        msg2 = Text(
            "9 から 10 に進むと、次の桁が一つ進む",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg2.move_to([0, -1.92, 0])
        self.play(FadeIn(msg2), run_time=0.5)

        anim_total = 0.6 + 1.4 + 0.6 + 0.5 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_carry_propagation(self):
        duration = self._duration
        title = self._title("繰り上がり ── 9 から 10、99 から 100、999 から 1000")
        self.play(FadeIn(title), run_time=0.6)

        # Build initial gears at value 7
        current_value = 7
        digits = _digits_of(current_value)
        gears = [_make_gear(d, i) for i, d in enumerate(digits)]
        gear_group = VGroup(*gears)
        self.play(*[Create(g) for g in gears], run_time=1.0)

        labels = self._place_labels()
        self.play(*[FadeIn(lab) for lab in labels], run_time=0.5)

        # Value display below labels
        value_lbl = MathTex(f"= {current_value}", font_size=26, color=ACCENT_GOLD)
        value_lbl.move_to([0, -1.55, 0])
        self.play(FadeIn(value_lbl), run_time=0.4)

        def update_to(new_value, highlight_carry_cols):
            """Update gear digits to new_value, highlighting carry cols in PINK."""
            nonlocal gears, gear_group, value_lbl
            new_digits = _digits_of(new_value)
            new_gears = []
            for i in range(N_DIGITS):
                col = ACCENT_PINK if i in highlight_carry_cols else ACCENT_CYAN
                new_gears.append(_make_gear(new_digits[i], i, color=col))
            new_value_lbl = MathTex(f"= {new_value}", font_size=26, color=ACCENT_GOLD)
            new_value_lbl.move_to([0, -1.55, 0])
            new_group = VGroup(*new_gears)
            self.play(
                gear_group.animate.set_opacity(0.0),
                value_lbl.animate.set_opacity(0.0),
                run_time=0.20,
            )
            self.remove(gear_group, value_lbl)
            self.play(FadeIn(new_group), FadeIn(new_value_lbl), run_time=0.30)
            gears = new_gears
            gear_group = new_group
            value_lbl = new_value_lbl

        # Sequence 1: 7 → 8 → 9 → 10 (single carry into 10's place)
        for v, carries in [(8, []), (9, []), (10, [4, 5])]:
            update_to(v, carries)

        # Sequence 2: jump to 98 → 99 → 100 (double carry)
        update_to(98, [])
        for v, carries in [(99, []), (100, [3, 4, 5])]:
            update_to(v, carries)

        # Sequence 3: jump to 998 → 999 → 1000 (triple carry)
        update_to(998, [])
        for v, carries in [(999, []), (1000, [2, 3, 4, 5])]:
            update_to(v, carries)

        msg = Text(
            "桁上がりが歯車の連動で自動に伝わる ── これがパスカリーヌの仕組み",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        msg.move_to([0, -1.92, 0])
        self.play(FadeIn(msg), run_time=0.6)

        anim_total = 0.6 + 1.0 + 0.5 + 0.4 + (0.20 + 0.30) * 11 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "gears_view": {"people": [], "years": []},
    "carry_propagation": {"people": [], "years": []},
}

SCENES = {
    "gears_view": PascalineMechanism,
    "carry_propagation": PascalineMechanism,
}
