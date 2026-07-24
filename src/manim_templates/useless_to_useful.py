"""
useless_to_useful.py - 'Useless' number theory powering the modern world (数学史記)

Hardy proudly claimed his mathematics was useless. This template shows the
irony: number theory became the basis of public-key cryptography (RSA), and a
result he dismissed as trivial became the Hardy-Weinberg law of population
genetics.

Modes:
    applications - A central "number theory / primes" box branches by arrows to
                   public-key cryptography (RSA) and population genetics
                   (Hardy-Weinberg), under Hardy's quote that he never did
                   anything useful.
                   Fixed params: 1 source box, 2 application boxes.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 035 (Hardy), pillar 3 (the irony of useless mathematics).
"""

from manim import (
    DOWN,
    Arrow,
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


class UselessToUseful(Scene):
    """Useless number theory -> RSA cryptography and population genetics."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 26)
        _mode = params.get("mode", "applications")
        self.build_applications()

    def _box(self, head, body, col, width=4.2):
        rect = Rectangle(width=width, height=1.35, color=col, stroke_width=3)
        h = Text(head, font=FONT, font_size=25, color=col)
        b = Text(body, font=FONT, font_size=18, color=TEXT_WHITE)
        inner = VGroup(h, b).arrange(DOWN, buff=0.12)
        inner.move_to(rect.get_center())
        return VGroup(rect, inner)

    def build_applications(self):
        duration = self._duration

        title = Text(
            "役に立たないと思った数学が、世界を動かす",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.15, 0])

        # Left column: pure number theory -> RSA cryptography
        nt = self._box("整数論・素数", "役に立たないと誇った", ACCENT_GOLD, width=5.4)
        nt.move_to([-3.6, 1.45, 0])
        rsa = self._box("公開鍵暗号 (RSA)", "ネット通信を守る", ACCENT_CYAN, width=5.4)
        rsa.move_to([-3.6, -0.6, 0])

        # Right column: a throwaway algebra result -> population genetics
        hw = self._box("ハーディ=ワインベルクの法則", "片手間に解いた代数", ACCENT_GOLD, width=5.6)
        hw.move_to([3.6, 1.45, 0])
        genetics = self._box("集団遺伝学", "遺伝の法則の基礎", ACCENT_PINK, width=5.4)
        genetics.move_to([3.6, -0.6, 0])

        arrow_l = Arrow(nt.get_bottom(), rsa.get_top(), color=TEXT_DIM, buff=0.12, stroke_width=4)
        arrow_r = Arrow(
            hw.get_bottom(), genetics.get_top(), color=TEXT_DIM, buff=0.12, stroke_width=4
        )

        note = Text(
            "「私は役に立つことを、何ひとつしていない」",
            font=FONT,
            font_size=21,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.7, 0])

        self.play(FadeIn(title), run_time=0.6)

        fade = 0.7
        coda = 5.0
        items = [nt, arrow_l, rsa, hw, arrow_r, genetics, note]
        intro = 0.6
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
    "applications": {
        "people": [["ハーディ", "Hardy"], ["ワインベルク", "Weinberg"]],
        "years": [],
    },
}


SCENES = {
    "applications": {
        "class": "UselessToUseful",
        "params": {"mode": "applications"},
        "description": "Useless number theory -> RSA cryptography and Hardy-Weinberg population genetics",
    },
}
