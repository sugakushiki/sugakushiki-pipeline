"""
rabbit_sequence.py - うさぎ問題から数列を導く (数学史記)

フィボナッチ回 の数列パート。『Liber Abaci』第12章のうさぎの問題
(一つがいが生後二か月で毎月一つがいを産み、決して死なない) を月ごとに数えると
1,1,2,3,5,8,13 という数列が現れる。おとな (産む) のつがいとこどものつがいを
色分けして月送りで段階表示し、最後に漸化式 F(n)=F(n-1)+F(n-2) を提示する。

このモデルは生物学的事実ではなく数学的な仮想設定 (トイモデル) である。

Modes:
    default - 月0〜4のつがい (おとな=金 / こども=水色) を行で段階表示し、各月の
              総数 1,1,2,3,5 を示す。続いて数列 1,1,2,3,5,8,13,21 と、となりどうしの
              和が次の数になる漸化式 F(n)=F(n-1)+F(n-2) を提示する。
              Fixed params: months 0..4 -> totals [1,1,2,3,5];
                            sequence [1,1,2,3,5,8,13,21]; recurrence additive.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 040 (Fibonacci), the rabbit problem / sequence.
"""

import numpy as np
from manim import (
    RIGHT,
    Dot,
    FadeIn,
    FadeOut,
    Indicate,
    LaggedStart,
    MathTex,
    RoundedRectangle,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _pair_glyph(center, color, w=0.36):
    """A small pair-of-rabbits glyph: a rounded box with two dots."""
    center = np.array(center, dtype=float)
    box = RoundedRectangle(
        width=w,
        height=w * 0.72,
        corner_radius=0.06,
        stroke_color=color,
        stroke_width=2.0,
        fill_color=color,
        fill_opacity=0.18,
    )
    box.move_to(center)
    o = w * 0.2
    d1 = Dot(center + np.array([-o, 0, 0]), radius=w * 0.1, color=color)
    d2 = Dot(center + np.array([o, 0, 0]), radius=w * 0.1, color=color)
    return VGroup(box, d1, d2)


class RabbitSequence(Scene):
    """うさぎ問題 -> フィボナッチ数列 -> 漸化式."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 24)
        # single concept; mode kept for forward-compat
        self._build()

    def _build(self):
        duration = self._duration
        # split the timeline: mechanism rows, then sequence + recurrence
        dur_a = duration * 0.46
        dur_b = duration - dur_a

        # ---------------- Phase A: month-by-month pairs ----------------
        title = Text("うさぎは、何つがいになる？", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.2, 0])
        self.play(FadeIn(title), run_time=0.7)

        legend = VGroup(
            _pair_glyph([0, 0, 0], ACCENT_GOLD, w=0.3),
            Text("おとな（産む）", font=FONT, font_size=18, color=TEXT_DIM),
            _pair_glyph([0, 0, 0], ACCENT_CYAN, w=0.3),
            Text("こども", font=FONT, font_size=18, color=TEXT_DIM),
        ).arrange(RIGHT, buff=0.18)
        legend.move_to([0, 2.62, 0])
        self.play(FadeIn(legend), run_time=0.6)

        # (mature, young) per month -> totals 1,1,2,3,5
        rows_data = [
            (0, 0, 1),  # month 0: 1 young
            (1, 1, 0),  # month 1: 1 mature
            (2, 1, 1),  # month 2: 2
            (3, 2, 1),  # month 3: 3
            (4, 3, 2),  # month 4: 5
        ]
        row_y0 = 2.05
        row_gap = 0.6
        x_start = -3.3
        pitch = 0.46

        phase_a = VGroup(title, legend)
        a_anim = 0.7 + 0.6
        a_waits = len(rows_data) * 0.6
        ws_a = _calc_wait_scale(dur_a, a_anim + len(rows_data) * 0.55, a_waits)

        for month, mature, young in rows_data:
            ry = row_y0 - month * row_gap
            mlabel = Text(f"{month}か月", font=FONT, font_size=20, color=TEXT_WHITE)
            mlabel.move_to([-5.0, ry, 0])
            glyphs = VGroup()
            idx = 0
            for _ in range(mature):
                glyphs.add(_pair_glyph([x_start + idx * pitch, ry, 0], ACCENT_GOLD))
                idx += 1
            for _ in range(young):
                glyphs.add(_pair_glyph([x_start + idx * pitch, ry, 0], ACCENT_CYAN))
                idx += 1
            total = mature + young
            cnt = MathTex(str(total), font_size=34, color=ACCENT_GOLD)
            cnt.move_to([4.7, ry, 0])
            eq = Text("つがい", font=FONT, font_size=16, color=TEXT_DIM)
            eq.next_to(cnt, RIGHT, buff=0.12)
            self.play(FadeIn(mlabel), FadeIn(glyphs), run_time=0.55)
            self.play(FadeIn(cnt), FadeIn(eq), run_time=0.3)
            self.wait(0.55 * ws_a)
            phase_a.add(mlabel, glyphs, cnt, eq)

        self.wait(0.6 * ws_a)
        self.play(FadeOut(phase_a), run_time=0.6)

        # ---------------- Phase B: the sequence & recurrence ----------------
        title2 = Text("となりどうしの和が、次の数", font=FONT, font_size=30, color=ACCENT_GOLD)
        title2.move_to([0, 3.2, 0])
        self.play(FadeIn(title2), run_time=0.6)

        seq_vals = [1, 1, 2, 3, 5, 8, 13, 21]
        seq = VGroup(*[MathTex(str(v), font_size=44, color=TEXT_WHITE) for v in seq_vals])
        seq.arrange(RIGHT, buff=0.5)
        seq.move_to([0, 1.35, 0])

        b_anim = 0.6 + 1.4 + 0.6 + 0.6 + 0.7
        b_waits = 3.4
        ws_b = _calc_wait_scale(dur_b, b_anim, b_waits)

        self.play(LaggedStart(*[FadeIn(t) for t in seq], lag_ratio=0.18), run_time=1.4)
        self.wait(0.8 * ws_b)

        # example 1: 5 + 8 = 13  (indices 4,5 -> 6)
        ex1 = MathTex("5", "+", "8", "=", "13", font_size=40)
        ex1.set_color_by_tex("5", ACCENT_CYAN)
        ex1.set_color_by_tex("8", ACCENT_CYAN)
        ex1.set_color_by_tex("13", ACCENT_PINK)
        ex1.move_to([0, 0.1, 0])
        self.play(
            Indicate(seq[4], color=ACCENT_CYAN, scale_factor=1.25),
            Indicate(seq[5], color=ACCENT_CYAN, scale_factor=1.25),
            run_time=0.6,
        )
        self.play(FadeIn(ex1), Indicate(seq[6], color=ACCENT_PINK, scale_factor=1.25), run_time=0.6)
        self.wait(0.9 * ws_b)

        # example 2: 8 + 13 = 21
        ex2 = MathTex("8", "+", "13", "=", "21", font_size=40)
        ex2.set_color_by_tex("8", ACCENT_CYAN)
        ex2.set_color_by_tex("13", ACCENT_CYAN)
        ex2.set_color_by_tex("21", ACCENT_PINK)
        ex2.move_to([0, -0.65, 0])
        self.play(FadeIn(ex2), run_time=0.5)
        self.wait(0.7 * ws_b)

        formula = MathTex(r"F_{n} = F_{n-1} + F_{n-2}", font_size=46, color=ACCENT_GOLD)
        formula.move_to([0, -1.55, 0])
        self.play(FadeIn(formula), run_time=0.7)
        self.wait(max(1.5, dur_b - b_anim - (0.8 + 0.9 + 0.7) * ws_b))


# Factual-claim metadata (read by qa_manim_consistency.py).
# Numbers on screen are sequence values (pair counts), not years; no people.
LINT_FACTUAL_CLAIMS = {
    "default": {"people": [], "years": []},
}


SCENES = {
    "default": RabbitSequence,
    "rabbits": RabbitSequence,
}
