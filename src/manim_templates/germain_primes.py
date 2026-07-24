"""
germain_primes.py - Sophie Germain primes & Germain's theorem for 数学史記

Episode 036 (Sophie Germain), math pillar 1 (number theory, primary pillar).

Modes:
    primes  - Definition of a Sophie Germain prime: a prime p such that 2p+1 is
              also prime. Two-column reveal p -> 2p+1 for 2,3,5,11,23 (both
              prime, cyan), plus ONE counter-example 7 -> 15 = 3x5 (not prime,
              pink) so the definition is unambiguous.
              Fixed params: pairs (2,5),(3,7),(5,11),(11,23),(23,47); 7->15.
    theorem - Germain's theorem (standard statement): if p is a Germain prime
              (2p+1 prime) then Case 1 of Fermat's Last Theorem holds for
              exponent p. Noted as a special case of her auxiliary-prime method,
              with which she covered every odd prime below 100. Deliberately
              does NOT claim a full proof and does NOT use the popular
              "30-digit" claim (unverified in primary sources).
              Fixed params: none (static statement + motion).

Duration-aware: reads target duration from _manim_params.json.
No trailing FadeOut (final frame held; transitions handled by video_assembler).
"""

from manim import (
    DOWN,
    UP,
    FadeIn,
    Line,
    MathTex,
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


class GermainPrimes(Scene):
    """Sophie Germain primes and Germain's theorem. Mode-branching scene.

    Modes:
        primes (default) - definition + examples + one counter-example
        theorem          - Case 1 implication (special case of auxiliary method)
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "primes")

        if mode == "theorem":
            self.build_theorem()
        else:
            self.build_primes()

    # -------------------------------------------------------------------
    # Mode: primes
    # -------------------------------------------------------------------
    def build_primes(self):
        """Definition and examples of Sophie Germain primes.

        Fixed parameters: pairs (2,5),(3,7),(5,11),(11,23),(23,47);
        counter-example 7 -> 15 = 3x5.
        """
        duration = self._duration

        title = Text("ソフィ・ジェルマン素数", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.3)

        subtitle = Text("p が素数 かつ 2p + 1 も素数", font=FONT, font_size=24, color=TEXT_WHITE)
        subtitle.next_to(title, DOWN, buff=0.3)

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Two-column header: p  |  2p+1
        col_p_x = -1.6
        col_q_x = 1.6
        header_y = 1.35
        head_p = MathTex("p", font_size=30, color=ACCENT_GOLD).move_to([col_p_x, header_y, 0])
        head_q = MathTex("2p+1", font_size=30, color=ACCENT_GOLD).move_to([col_q_x, header_y, 0])
        arrow_h = MathTex(r"\rightarrow", font_size=28, color=TEXT_DIM).move_to([0.0, header_y, 0])
        hline = Line(
            [col_p_x - 0.9, header_y - 0.28, 0],
            [col_q_x + 0.9, header_y - 0.28, 0],
            color=TEXT_DIM,
            stroke_width=1,
        )
        self.play(FadeIn(VGroup(head_p, head_q, arrow_h, hline)), run_time=0.4)

        # Valid Germain-prime pairs
        pairs = [(2, 5), (3, 7), (5, 11), (11, 23), (23, 47)]
        row_mobs = []
        for i, (p, q) in enumerate(pairs):
            y = header_y - 0.45 * (i + 1)
            mp = MathTex(str(p), font_size=28, color=ACCENT_CYAN).move_to([col_p_x, y, 0])
            ar = MathTex(r"\rightarrow", font_size=24, color=TEXT_DIM).move_to([0.0, y, 0])
            mq = MathTex(str(q), font_size=28, color=ACCENT_CYAN).move_to([col_q_x, y, 0])
            row_mobs.append(VGroup(mp, ar, mq))

        # One counter-example: 7 -> 15 = 3x5 (not prime).
        cy = header_y - 0.45 * (len(pairs) + 1) - 0.1
        c_p = MathTex("7", font_size=28, color=TEXT_DIM).move_to([col_p_x, cy, 0])
        c_ar = MathTex(r"\rightarrow", font_size=24, color=TEXT_DIM).move_to([0.0, cy, 0])
        c_q = MathTex(r"15 = 3 \times 5", font_size=26, color=ACCENT_PINK).move_to(
            [col_q_x + 0.45, cy, 0]
        )
        c_note = Text(
            "(素数でない → ジェルマン素数ではない)",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        c_note.move_to([0.4, cy - 0.4, 0])

        # Pace the reveals across the narration (no filler loop): the valid
        # pairs in turn, then the counter-example.
        reveals = list(row_mobs) + [VGroup(c_p, c_ar, c_q), c_note]
        coda = 2.0
        setup = 0.5 + 0.5 + 0.4  # title + subtitle + header
        pass_t = min(2.5, 0.45 * len(row_mobs))  # one highlight pass
        gap = (duration - setup - coda - pass_t) / len(reveals)
        inter = gap - 0.5
        if inter < 0.0:
            inter = 0.0
        for mob in reveals:
            self.play(FadeIn(mob), run_time=0.5)
            self.wait(inter)

        # ONE deliberate pass of a highlight box over the valid pairs - says
        # "every one of these is a Germain prime", then rests (no looping).
        box = SurroundingRectangle(row_mobs[0], color=ACCENT_GOLD, buff=0.12, stroke_width=2)
        self.play(FadeIn(box), run_time=0.3)
        step_t = (pass_t - 0.3) / max(1, len(row_mobs) - 1)
        for rm in row_mobs[1:]:
            self.play(box.animate.move_to(rm.get_center()), run_time=step_t, rate_func=lambda t: t)
        self.wait(coda)

    # -------------------------------------------------------------------
    # Mode: theorem
    # -------------------------------------------------------------------
    def build_theorem(self):
        """Germain's theorem: Germain prime => Case 1 of FLT for exponent p.

        Accurate framing: a special case of her auxiliary-prime method, which
        covered every odd prime below 100. No full-proof claim, no 30-digit
        claim.
        """
        duration = self._duration

        title = Text("ジェルマンの定理", font=FONT, font_size=32, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.5)

        premise = Text(
            "p がジェルマン素数 (2p + 1 も素数) のとき",
            font=FONT,
            font_size=26,
            color=ACCENT_CYAN,
        )
        premise.move_to([0.0, 1.2, 0])

        arrow = MathTex(r"\Downarrow", font_size=44, color=TEXT_WHITE)
        arrow.move_to([0.0, 0.4, 0])

        conclusion = Text(
            "フェルマー予想の「第一の場合」が成り立つ",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        conclusion.move_to([0.0, -0.4, 0])
        con_box = SurroundingRectangle(conclusion, color=ACCENT_GOLD, buff=0.18, stroke_width=2)

        note1 = Text(
            "補助素数を用いる方法の、わかりやすい特別な場合",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note1.move_to([0.0, -1.25, 0])
        note2 = Text(
            "この方法で 100 未満のすべての奇素数について示した",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        )
        note2.move_to([0.0, -1.65, 0])

        # Pace the logical statement across the narration (no filler motion):
        # premise, implication arrow, boxed conclusion, then the two clarifying
        # notes - spread over the available time, ending with a short hold.
        reveals = [premise, arrow, VGroup(conclusion, con_box), note1, note2]
        coda = 2.0
        setup = 0.5  # title
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
# Only the subject's own name (Germain) appears; no years are shown on screen.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "primes": {"people": [["ジェルマン", "Germain", "ソフィ・ジェルマン"]], "years": []},
    "theorem": {"people": [["ジェルマン", "Germain"]], "years": []},
}


SCENES = {
    "primes": {
        "class": "GermainPrimes",
        "params": {"mode": "primes"},
        "description": "Sophie Germain primes: p & 2p+1 prime, examples 2,3,5,11,23 + counter-example 7",
    },
    "theorem": {
        "class": "GermainPrimes",
        "params": {"mode": "theorem"},
        "description": "Germain's theorem: Germain prime => Case 1 of FLT (special case of auxiliary-prime method, primes < 100)",
    },
}
