"""
fermat_last_theorem.py - Fermat's Last Theorem (the conjecture) intro for 数学史記

Visualizes the STATEMENT of Fermat's Last Theorem as the setup for Sophie
Germain's attack on it (Episode 036):
  - n = 2 (Pythagorean): x^2 + y^2 = z^2 has infinitely many natural-number
    solutions (concrete triples).
  - n >= 3: x^n + y^n = z^n has NO positive-integer solutions (the conjecture
    Fermat scribbled in a margin; only fully proved in 1995 by Wiles - that
    history is carried by the narration, NOT shown on screen).

Modes:
    pythagoras - n=2 case. Equation x^2+y^2=z^2, a 3-4-5 right triangle, and the
                 triples (3,4,5),(5,12,13),(8,15,17) revealed one by one, with a
                 dot orbiting the triangle for continuous motion. Message: there
                 are infinitely many natural-number solutions.
                 Fixed params: triples (3,4,5),(5,12,13),(8,15,17).
    conjecture - n>=3 case. Generalized equation x^n+y^n=z^n, the exponents
                 n=3,4,5 shown, and the claim "no positive-integer solutions"
                 boxed, with a tracer dot sweeping under the equation for motion.
                 Pure math: no names/years on screen.
                 Fixed params: exponents shown n=3,4,5.

Duration-aware: reads target duration from _manim_params.json.
No trailing FadeOut (final frame held; transitions handled by video_assembler).

Used by: Episode 036 (Sophie Germain), math pillar 1 (number theory)
"""

from manim import (
    DOWN,
    UP,
    FadeIn,
    MathTex,
    Polygon,
    Scene,
    SurroundingRectangle,
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


class FermatLastTheorem(Scene):
    """Fermat's Last Theorem statement. Mode-branching scene.

    Modes:
        pythagoras (default) - n=2 has infinitely many integer solutions
        conjecture           - n>=3 has no positive-integer solutions
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "pythagoras")

        if mode == "conjecture":
            self.build_conjecture()
        else:
            self.build_pythagoras()

    # -------------------------------------------------------------------
    # Mode: pythagoras  (n = 2, infinitely many solutions)
    # -------------------------------------------------------------------
    def build_pythagoras(self):
        """n=2 case: x^2+y^2=z^2 with a 3-4-5 triangle and three triples.

        Fixed parameters: triples (3,4,5), (5,12,13), (8,15,17).
        """
        duration = self._duration

        title = Text("n = 2 のとき", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.35)

        eq = MathTex(r"x^2", r"+", r"y^2", r"=", r"z^2", font_size=46)
        eq[0].set_color(ACCENT_CYAN)
        eq[2].set_color(ACCENT_CYAN)
        eq[4].set_color(ACCENT_GOLD)
        eq.next_to(title, DOWN, buff=0.35)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(eq), run_time=0.6)

        # 3-4-5 right triangle on the left
        scale = 0.5
        leg_a, leg_b = 3, 4
        ox, oy = -4.3, -1.4
        p0 = [ox, oy, 0]
        p1 = [ox + leg_a * scale, oy, 0]
        p2 = [ox + leg_a * scale, oy + leg_b * scale, 0]
        triangle = Polygon(p0, p1, p2, color=ACCENT_CYAN, stroke_width=3)
        lab_a = MathTex("3", font_size=24, color=TEXT_WHITE)
        lab_a.move_to([ox + leg_a * scale / 2, oy - 0.3, 0])
        lab_b = MathTex("4", font_size=24, color=TEXT_WHITE)
        lab_b.move_to([ox + leg_a * scale + 0.32, oy + leg_b * scale / 2, 0])
        lab_c = MathTex("5", font_size=24, color=ACCENT_GOLD)
        lab_c.move_to([ox + leg_a * scale / 2 - 0.35, oy + leg_b * scale / 2 + 0.18, 0])
        tri_group = VGroup(triangle, lab_a, lab_b, lab_c)
        self.play(FadeIn(tri_group), run_time=0.6)

        # Three triples revealed one by one on the right
        triples = [(3, 4, 5), (5, 12, 13), (8, 15, 17)]
        col_x = 1.1
        top_y = 0.7
        triple_mobs = []
        for i, (x, y, z) in enumerate(triples):
            yy = top_y - 0.72 * i
            m = MathTex(f"{x}^2 + {y}^2 = {z}^2", font_size=30, color=TEXT_WHITE)
            m.move_to([col_x, yy, 0])
            triple_mobs.append(m)

        # Closing "infinitely many" message.
        msg = Text("自然数の解は無数にある", font=FONT, font_size=26, color=ACCENT_GOLD)
        msg.move_to([col_x, top_y - 0.72 * len(triples) - 0.25, 0])

        # Pace the reveals across the narration so on-screen motion always
        # means "new information appearing" - no time-filler animation. The
        # triples then the message are spread over the available time, ending
        # with a short, deliberate hold.
        reveals = list(triple_mobs) + [msg]
        coda = 2.0
        setup = 0.5 + 0.6 + 0.6  # title + equation + triangle
        gap = (duration - setup - coda) / len(reveals)
        inter = gap - 0.5
        if inter < 0.0:
            inter = 0.0
        for mob in reveals:
            self.play(FadeIn(mob), run_time=0.5)
            self.wait(inter)
        self.wait(coda)

    # -------------------------------------------------------------------
    # Mode: conjecture  (n >= 3, no solutions)
    # -------------------------------------------------------------------
    def build_conjecture(self):
        """n>=3 case: x^n+y^n=z^n has no positive-integer solutions.

        Fixed parameters: exponents shown n=3, 4, 5. Pure math, no names/years.
        """
        duration = self._duration

        title = Text("n が 3 以上のとき", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.35)

        eq = MathTex(r"x^n", r"+", r"y^n", r"=", r"z^n", font_size=52)
        eq[0].set_color(ACCENT_CYAN)
        eq[2].set_color(ACCENT_CYAN)
        eq[4].set_color(ACCENT_GOLD)
        eq.next_to(title, DOWN, buff=0.45)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(eq), run_time=0.7)

        # Exponents n = 3, 4, 5 shown as concrete instances
        rows = [
            r"x^3 + y^3 = z^3",
            r"x^4 + y^4 = z^4",
            r"x^5 + y^5 = z^5",
        ]
        row_mobs = []
        top_y = 0.3
        for i, r in enumerate(rows):
            m = MathTex(r, font_size=32, color=TEXT_WHITE)
            m.move_to([0.0, top_y - 0.7 * i, 0])
            row_mobs.append(m)

        # Boxed conclusion: no positive-integer solutions.
        msg = Text(
            "自然数の解は ひとつも存在しない",
            font=FONT,
            font_size=28,
            color=ACCENT_PINK,
        )
        msg.move_to([0.0, top_y - 0.7 * len(rows) - 0.5, 0])
        box = SurroundingRectangle(msg, color=ACCENT_PINK, buff=0.2, stroke_width=2)

        # Pace the reveals across the narration (no filler motion): each
        # exponent case appears in turn, then the boxed conclusion, ending
        # with a short hold.
        reveals = list(row_mobs) + [VGroup(msg, box)]
        coda = 2.0
        setup = 0.5 + 0.7  # title + equation
        gap = (duration - setup - coda) / len(reveals)
        inter = gap - 0.5
        if inter < 0.0:
            inter = 0.0
        for mob in reveals:
            self.play(FadeIn(mob), run_time=0.5)
            self.wait(inter)
        self.wait(coda)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS: on-screen factual claims per mode.
# Both modes are pure mathematics (no people/years displayed); the historical
# attribution (Fermat, the 1995 Wiles proof) is carried by the narration.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "pythagoras": {"people": [], "years": []},
    "conjecture": {"people": [], "years": []},
}


SCENES = {
    "pythagoras": {
        "class": "FermatLastTheorem",
        "params": {"mode": "pythagoras"},
        "description": "n=2: x^2+y^2=z^2 with 3-4-5 triangle and triples, infinitely many solutions",
    },
    "conjecture": {
        "class": "FermatLastTheorem",
        "params": {"mode": "conjecture"},
        "description": "n>=3: x^n+y^n=z^n has no positive-integer solutions (the conjecture)",
    },
}
