"""
brahmagupta_identity.py - Brahmagupta–Fibonacci identity and Pell precursor

Visualizes Brahmagupta's identity, his composition (samāsa / bhāvanā) method
for the Pell equation, and the historical line from Brahmagupta (628) to
Bhāskara II's chakravala method (c. 1150) and beyond.

Modes:
    identity
        The Brahmagupta–Fibonacci identity for a fixed n:
            (a^2 + n b^2)(c^2 + n d^2) = (a c - n b d)^2 + n (a d + b c)^2
        Concrete numerical example: n = 2, a = 1, b = 1, c = 3, d = 1.
        LHS = (1 + 2)(9 + 2) = 3 * 11 = 33.
        RHS = (1*3 - 2*1*1)^2 + 2*(1*1 + 1*3)^2 = 1^2 + 2 * 4^2 = 1 + 32 = 33.
    pell_seed
        Brahmagupta's samāsa (composition) for the Pell-like equation
            x^2 - N y^2 = 1
        Fixed example: N = 92. Brahmagupta found (x, y) = (1151, 120) by
        composing intermediate triples. Display the equation and the
        verified pair.
    chakravala_path
        Historical arrow diagram showing the line of descent of the
        composition method:
            Brahmagupta (628)
                |
            Jayadeva (~9c)
                |
            Bhaskara II (1150)
                |
            Lagrange (1768)
        Each node is a small labeled box. No portraits, only year + name.

Fixed parameters (verified by hand):
    Identity example: n=2, a=b=d=1, c=3 -> both sides equal 33.
    Pell example: N = 92, smallest solution (1151, 120) verified
        (1151^2 - 92 * 120^2 = 1324801 - 1324800 = 1).
    Y range: -2.0 to +3.0, subtitle clearance preserved.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 025 (Brahmagupta), math pillar — composition method and
the line to chakravala.
"""


from manim import (
    Arrow,
    FadeIn,
    MathTex,
    Rectangle,
    Scene,
    Text,
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


class BrahmaguptaIdentity(Scene):
    """Brahmagupta identity and Pell precursor — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "identity")
        self._duration = params.get("duration", 35)

        if mode == "pell_seed":
            self._build_pell_seed()
        elif mode == "chakravala_path":
            self._build_chakravala_path()
        else:
            self._build_identity()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_identity(self):
        """The Brahmagupta-Fibonacci identity with a numerical check."""
        duration = self._duration

        title = self._title("ブラフマグプタの恒等式")
        self.play(FadeIn(title), run_time=0.5)

        # General identity
        identity = MathTex(
            r"(a^2 + n b^2)(c^2 + n d^2) = (a c - n b d)^2 + n (a d + b c)^2",
            font_size=32,
            color=ACCENT_CYAN,
        )
        identity.move_to([0, 1.9, 0])
        self.play(FadeIn(identity), run_time=0.8)

        # Parameter line
        param = MathTex(
            r"n = 2,\quad a = 1,\quad b = 1,\quad c = 3,\quad d = 1",
            font_size=28,
            color=TEXT_WHITE,
        )
        param.move_to([0, 0.9, 0])
        self.play(FadeIn(param), run_time=0.5)

        # LHS evaluation
        lhs_lbl = Text("左辺", font=FONT, font_size=24, color=ACCENT_PINK)
        lhs_lbl.move_to([-4.3, 0.0, 0])
        self.play(FadeIn(lhs_lbl), run_time=0.3)
        lhs = MathTex(
            r"(1 + 2 \cdot 1)(9 + 2 \cdot 1) = 3 \cdot 11 = 33",
            font_size=30,
            color=TEXT_WHITE,
        )
        lhs.move_to([1.0, 0.0, 0])
        self.play(FadeIn(lhs), run_time=0.5)

        # RHS evaluation
        rhs_lbl = Text("右辺", font=FONT, font_size=24, color=ACCENT_PINK)
        rhs_lbl.move_to([-4.3, -1.0, 0])
        self.play(FadeIn(rhs_lbl), run_time=0.3)
        rhs = MathTex(
            r"(3 - 2)^2 + 2 \cdot (1 + 3)^2 = 1 + 32 = 33",
            font_size=30,
            color=TEXT_WHITE,
        )
        rhs.move_to([1.0, -1.0, 0])
        self.play(FadeIn(rhs), run_time=0.5)

        # Verified marker
        check = MathTex(r"33 = 33", font_size=36, color=ACCENT_GOLD)
        check.move_to([0, -2.0, 0])
        self.play(FadeIn(check), run_time=0.5)

        anim_total = 0.5 + 0.8 + 0.5 + 0.3 + 0.5 + 0.3 + 0.5 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_pell_seed(self):
        """Pell equation x^2 - N y^2 = 1 with Brahmagupta's N=92 solution."""
        duration = self._duration

        title = self._title("ペル型方程式と合成法")
        self.play(FadeIn(title), run_time=0.5)

        # The equation
        eq = MathTex(r"x^2 - N y^2 = 1", font_size=44, color=ACCENT_CYAN)
        eq.move_to([0, 1.9, 0])
        self.play(FadeIn(eq), run_time=0.7)

        # Specific case N = 92
        n_lbl = MathTex(r"N = 92", font_size=36, color=ACCENT_GOLD)
        n_lbl.move_to([0, 1.0, 0])
        self.play(FadeIn(n_lbl), run_time=0.5)

        # The solution found by Brahmagupta
        sol_lbl = Text("ブラフマグプタの解", font=FONT, font_size=22, color=TEXT_DIM)
        sol_lbl.move_to([-3.5, 0.1, 0])
        self.play(FadeIn(sol_lbl), run_time=0.4)
        sol = MathTex(r"(x, y) = (1151, 120)", font_size=34, color=TEXT_WHITE)
        sol.move_to([1.5, 0.1, 0])
        self.play(FadeIn(sol), run_time=0.5)

        # Verification
        verify_lbl = Text("検算", font=FONT, font_size=22, color=TEXT_DIM)
        verify_lbl.move_to([-3.5, -0.8, 0])
        self.play(FadeIn(verify_lbl), run_time=0.4)
        verify = MathTex(
            r"1151^2 - 92 \cdot 120^2 = 1324801 - 1324800 = 1",
            font_size=26,
            color=TEXT_WHITE,
        )
        verify.move_to([1.5, -0.8, 0])
        self.play(FadeIn(verify), run_time=0.6)

        note = Text(
            "恒等式を合成法で繰り返し用いて整数解を得る",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -2.0, 0])
        self.play(FadeIn(note), run_time=0.5)

        anim_total = 0.5 + 0.7 + 0.5 + 0.4 + 0.5 + 0.4 + 0.6 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_chakravala_path(self):
        """Historical line of descent: Brahmagupta -> Bhaskara II -> Lagrange."""
        duration = self._duration

        title = self._title("合成法からチャクラバラ法へ")
        self.play(FadeIn(title), run_time=0.5)

        # Four nodes vertically
        nodes = [
            ("ブラフマグプタ", "628 年", ACCENT_CYAN, 1.7),
            ("ジャヤデーヴァ", "9 世紀頃", TEXT_WHITE, 0.55),
            ("バースカラ 2 世", "1150 年", ACCENT_PINK, -0.6),
            ("ラグランジュ", "1768 年", ACCENT_GOLD, -1.75),
        ]
        box_w = 4.2
        box_h = 0.85
        rects = []
        for name, year, color, y in nodes:
            rect = Rectangle(
                width=box_w,
                height=box_h,
                color=color,
                stroke_width=2.5,
            )
            rect.move_to([0, y, 0])
            self.play(FadeIn(rect), run_time=0.3)
            rects.append(rect)
            name_lbl = Text(name, font=FONT, font_size=22, color=color)
            name_lbl.move_to([-1.0, y, 0])
            year_lbl = Text(year, font=FONT, font_size=20, color=TEXT_DIM)
            year_lbl.move_to([1.2, y, 0])
            self.play(FadeIn(name_lbl), FadeIn(year_lbl), run_time=0.35)

        # Arrows between adjacent boxes
        arrow_x = 0
        for i in range(len(nodes) - 1):
            y_top = nodes[i][3] - box_h / 2.0 - 0.02
            y_bot = nodes[i + 1][3] + box_h / 2.0 + 0.02
            ar = Arrow(
                start=[arrow_x, y_top, 0],
                end=[arrow_x, y_bot, 0],
                color=TEXT_DIM,
                stroke_width=2,
                buff=0.0,
                max_tip_length_to_length_ratio=0.25,
            )
            self.play(FadeIn(ar), run_time=0.3)

        anim_total = 0.5 + (0.3 + 0.35) * 4 + 0.3 * 3
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "identity": {"people": [], "years": []},
    "pell_seed": {"people": [], "years": []},
    "chakravala_path": {
        "people": [
            ["ブラフマグプタ", "Brahmagupta"],
            ["ジャヤデーヴァ", "Jayadeva"],
            ["バースカラ 2 世", "バースカラ2世", "Bhaskara II", "Bhāskara II"],
            ["ラグランジュ", "Lagrange"],
        ],
        "years": ["628", "1150", "1768"],
    },
}

SCENES = {
    "identity": BrahmaguptaIdentity,
    "pell_seed": BrahmaguptaIdentity,
    "chakravala_path": BrahmaguptaIdentity,
}
