"""
equation_history: 2次〜5次方程式の解法史をカード形式のタイムラインで表示する。

モード:
- timeline: 2次→3次→4次→5次を段階的に表示。各次数に解法者名と年代を付し、5次は❓で終わる
- final: 全次数に✅/❌と可解性の理由（ガロア群）を表示する。動画のまとめ用
"""

import numpy as np
from manim import *

BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
FONT = "BIZ UDMincho"
GREEN_OK = "#2ecc71"
RED_NG = "#e74c3c"


def get_duration(mode):
    defaults = {"timeline": 25, "final": 30}
    return defaults.get(mode, 25)


def make_eq_card(
    degree,
    equation_tex,
    solver_text,
    year_text,
    status=None,
    reason_math=None,
    center=ORIGIN,
    width=2.8,
    height=3.2,
):
    card = VGroup()

    bg = RoundedRectangle(
        corner_radius=0.12,
        width=width,
        height=height,
        color=WHITE,
        stroke_width=1.5,
        stroke_opacity=0.3,
        fill_color=WHITE,
        fill_opacity=0.04,
    )
    bg.move_to(center)
    card.add(bg)

    # Degree header (pure math, no Japanese)
    degree_label = MathTex(f"{degree}", font_size=44, color=GOLD)
    degree_label.move_to(center + UP * (height / 2 - 0.4))
    card.add(degree_label)

    # Equation — auto-shrink to fit card width with side padding
    eq = MathTex(equation_tex, font_size=28, color=CYAN)
    max_eq_width = width * 0.85
    if eq.width > max_eq_width:
        eq.scale_to_fit_width(max_eq_width)
    eq.move_to(center + UP * (height / 2 - 0.95))
    card.add(eq)

    # Solver name
    solver = Text(solver_text, font=FONT, font_size=20, color=WHITE).set_opacity(0.8)
    solver.move_to(center + UP * (height / 2 - 1.45))
    card.add(solver)

    # Year
    if year_text:
        year = Text(year_text, font=FONT, font_size=17, color=WHITE).set_opacity(0.5)
        year.move_to(center + UP * (height / 2 - 1.8))
        card.add(year)

    # Status icon
    if status == "ok":
        icon = MathTex(r"\checkmark", font_size=44, color=GREEN_OK)
        icon.move_to(center + DOWN * (height / 2 - 0.9))
        card.add(icon)
    elif status == "ng":
        icon = MathTex(r"\times", font_size=44, color=RED_NG)
        icon.move_to(center + DOWN * (height / 2 - 0.9))
        card.add(icon)
    elif status == "unknown":
        icon = MathTex(r"?", font_size=48, color=PINK)
        icon.move_to(center + DOWN * (height / 2 - 0.9))
        card.add(icon)

    # Reason (math only, e.g. "S₂")
    if reason_math is not None:
        reason = MathTex(reason_math, font_size=24, color=WHITE).set_opacity(0.7)
        reason.move_to(center + DOWN * (height / 2 - 0.45))
        card.add(reason)

    return card


class EquationHistoryTimeline(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("timeline")

        cards_data = [
            {
                "degree": 2,
                "equation": r"ax^2+bx+c=0",
                "solver": "古代〜中世",
                "year": "",
                "status": "ok",
            },
            {
                "degree": 3,
                "equation": r"ax^3+bx^2+cx+d=0",
                "solver": "タルターリア",
                "year": "1535",
                "status": "ok",
            },
            {
                "degree": 4,
                "equation": r"ax^4+bx^3+\cdots+e=0",
                "solver": "フェラーリ",
                "year": "1540",
                "status": "ok",
            },
            {
                "degree": 5,
                "equation": r"ax^5+bx^4+\cdots+f=0",
                "solver": "???",
                "year": "",
                "status": "unknown",
            },
        ]

        card_width = 2.8
        card_height = 3.0
        total_width = card_width * 4 + 0.4 * 3
        start_x = -total_width / 2 + card_width / 2

        cards, arrows = [], []
        for i, data in enumerate(cards_data):
            x = start_x + i * (card_width + 0.4)
            card = make_eq_card(
                degree=data["degree"],
                equation_tex=data["equation"],
                solver_text=data["solver"],
                year_text=data["year"],
                status=data["status"],
                center=np.array([x, 0, 0]),
                width=card_width,
                height=card_height,
            )
            cards.append(card)

        for i in range(3):
            x1 = start_x + i * (card_width + 0.4) + card_width / 2
            x2 = start_x + (i + 1) * (card_width + 0.4) - card_width / 2
            arr = Arrow(
                start=np.array([x1 + 0.05, 0, 0]),
                end=np.array([x2 - 0.05, 0, 0]),
                buff=0,
                stroke_width=2.0,
                color=WHITE,
                max_tip_length_to_length_ratio=0.3,
            ).set_opacity(0.4)
            arrows.append(arr)

        for i, card in enumerate(cards):
            anims = [FadeIn(card)]
            if i > 0:
                anims.append(FadeIn(arrows[i - 1]))
            self.play(*anims, run_time=0.7)
            self.wait(0.5 if i < 3 else 1.0)

        elapsed = (0.7 + 0.5) * 3 + 0.7 + 1.0
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End-of-scene FadeOut removed: if audio is longer than this
        # animation, FFmpeg pads with the last rendered frame and FadeOut
        # would leave the padded tail black. Scene transitions are handled
        # at video_assembler time, not inside Manim.


class EquationHistoryFinal(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("final")

        cards_data = [
            {
                "degree": 2,
                "equation": r"ax^2+bx+c=0",
                "solver": "解の公式あり",
                "year": "",
                "status": "ok",
                "reason": r"S_2",
            },
            {
                "degree": 3,
                "equation": r"ax^3+bx^2+\cdots=0",
                "solver": "解の公式あり",
                "year": "",
                "status": "ok",
                "reason": r"S_3",
            },
            {
                "degree": 4,
                "equation": r"ax^4+bx^3+\cdots+e=0",
                "solver": "解の公式あり",
                "year": "",
                "status": "ok",
                "reason": r"S_4",
            },
            {
                "degree": 5,
                "equation": r"ax^5+bx^4+\cdots+f=0",
                "solver": "一般の公式なし",
                "year": "",
                "status": "ng",
                "reason": r"S_5",
            },
        ]

        card_width = 2.8
        card_height = 3.2
        total_width = card_width * 4 + 0.4 * 3
        start_x = -total_width / 2 + card_width / 2

        cards = []
        for i, data in enumerate(cards_data):
            x = start_x + i * (card_width + 0.4)
            card = make_eq_card(
                degree=data["degree"],
                equation_tex=data["equation"],
                solver_text=data["solver"],
                year_text=data["year"],
                status=data["status"],
                reason_math=data["reason"],
                center=np.array([x, 0, 0]),
                width=card_width,
                height=card_height,
            )
            cards.append(card)

        # First 3 together
        self.play(*[FadeIn(cards[i]) for i in range(3)], run_time=0.8)
        self.wait(0.8)

        # 5th with emphasis
        self.play(FadeIn(cards[3]), run_time=0.8)
        fifth_bg = cards[3][0]
        self.play(fifth_bg.animate.set_stroke(color=RED_NG, width=3, opacity=0.8), run_time=0.4)
        self.wait(1.0)

        elapsed = 0.8 + 0.8 + 0.8 + 0.4 + 1.0
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End-of-scene FadeOut removed: if audio is longer than this
        # animation, FFmpeg pads with the last rendered frame and FadeOut
        # would leave the padded tail black. Scene transitions are handled
        # at video_assembler time, not inside Manim.


# B-10: factual claims displayed in each mode. Aliases (list within list)
# allow Latin/kana variants — narration only needs to mention one alias.
LINT_FACTUAL_CLAIMS = {
    "timeline": {
        "people": [
            ["タルターリア", "Tartaglia"],
            ["フェラーリ", "Ferrari"],
        ],
        "years": ["1535", "1540"],
    },
    "final": {
        "people": [],
        "years": [],
    },
}


SCENES = {
    "timeline": EquationHistoryTimeline,
    "final": EquationHistoryFinal,
}
