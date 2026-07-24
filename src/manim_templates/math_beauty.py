"""
math_beauty.py - The criteria of mathematical beauty (数学史記)

In 'A Mathematician's Apology' Hardy names the qualities of a beautiful proof:
unexpectedness, inevitability, and economy. This template presents the three
as side-by-side cards.

Modes:
    criteria - Three cards: 意外性 (unexpectedness), 必然性 (inevitability),
               簡潔性 (economy), under Hardy's remark that two thousand years
               have not wrinkled the classic proofs.
               Fixed params: exactly 3 cards.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 035 (Hardy), pillar on what makes a proof beautiful.
"""

from manim import (
    DOWN,
    FadeIn,
    Rectangle,
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


class MathBeauty(Scene):
    """Hardy's three criteria of mathematical beauty as cards."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 24)
        _mode = params.get("mode", "criteria")
        self.build_criteria()

    def build_criteria(self):
        duration = self._duration

        title = Text("数学の美とは", font=FONT, font_size=34, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        subtitle = Text(
            "ハーディが挙げた、美しい証明の3つの条件",
            font=FONT,
            font_size=23,
            color=TEXT_DIM,
        )
        subtitle.move_to([0, 2.4, 0])

        cards_data = [
            ("意外性", "予想もしない\n結びつき", ACCENT_CYAN),
            ("必然性", "逃れられない\n論理の流れ", ACCENT_GOLD),
            ("簡潔性", "最小限の\n手段で", ACCENT_PINK),
        ]
        xs = [-4.3, 0.0, 4.3]
        cards = VGroup()
        for (head, body, col), x in zip(cards_data, xs, strict=True):
            rect = Rectangle(width=3.9, height=2.4, color=col, stroke_width=3)
            h = Text(head, font=FONT, font_size=30, color=col)
            b = Text(body, font=FONT, font_size=21, color=TEXT_WHITE, line_spacing=0.9)
            inner = VGroup(h, b).arrange(DOWN, buff=0.3)
            inner.move_to(rect.get_center())
            card = VGroup(rect, inner)
            card.move_to([x, 0.4, 0])
            cards.add(card)

        note = Text(
            "二千年が、どちらの証明にも一本の皺も刻んでいない",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.75, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(subtitle), run_time=0.5)

        fade = 0.7
        coda = 5.0
        items = list(cards) + [note]
        intro = 0.6 + 0.5
        n = len(items)
        gaps = max(1, n - 1)
        slack = max(0.0, duration - intro - n * fade - coda)
        step_wait = slack / gaps
        for idx, it in enumerate(items):
            self.play(FadeIn(it), run_time=fade)
            if idx < n - 1:
                self.wait(max(0.4, step_wait))
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "criteria": {"people": [["ハーディ", "Hardy"]], "years": []},
}


SCENES = {
    "criteria": {
        "class": "MathBeauty",
        "params": {"mode": "criteria"},
        "description": "Hardy's three criteria of mathematical beauty: unexpectedness, inevitability, economy",
    },
}
