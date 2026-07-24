"""
dice_sample_space.py - カルダノの確率の発想 (数学史記)

カルダノ回 の数学的第三の柱。賭博のサイコロから、カルダノは
「起こりうる場合をすべて数え、有利な場合と全体の比で測る」という確率の
出発点に到達した。二つのサイコロの標本空間 (全36通り) を可視化する。

Modes:
    two_dice      - 二つのサイコロの全36通りを 6x6 グリッドで並べ、各セルに目の和を
                    表示する。和が 7 になる 6 通り (反対角線) をハイライトし、
                    有利/全体 = 6/36 = 1/6 を示す。
                    Fixed params: 6x6 = 36 cells, sum=7 has 6 ways, 6/36=1/6.
    distribution  - 目の和 2〜12 の場合の数 (1,2,3,4,5,6,5,4,3,2,1) を棒で示し、
                    和が 7 のとき最大 (6通り) になることを示す。
                    Fixed params: sums 2..12, counts triangular peak 6 at 7.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 039 (Cardano), math pillar (origin of probability).
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    Dot,
    FadeIn,
    Indicate,
    LaggedStart,
    MathTex,
    Rectangle,
    Scene,
    Square,
    Text,
    VGroup,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _dice_face(value, center, size, color):
    """A small dice face (rounded square + pips) for the given value (1..6)."""
    center = np.array(center, dtype=float)
    face = Square(
        side_length=size, color=color, stroke_width=2, fill_color=color, fill_opacity=0.12
    )
    face.move_to(center)
    o = size * 0.27
    pos = {
        "TL": center + np.array([-o, o, 0]),
        "TR": center + np.array([o, o, 0]),
        "ML": center + np.array([-o, 0, 0]),
        "MR": center + np.array([o, 0, 0]),
        "BL": center + np.array([-o, -o, 0]),
        "BR": center + np.array([o, -o, 0]),
        "C": center,
    }
    layout = {
        1: ["C"],
        2: ["TL", "BR"],
        3: ["TL", "C", "BR"],
        4: ["TL", "TR", "BL", "BR"],
        5: ["TL", "TR", "C", "BL", "BR"],
        6: ["TL", "TR", "ML", "MR", "BL", "BR"],
    }
    pips = VGroup(*[Dot(pos[k], radius=size * 0.07, color=color) for k in layout[value]])
    return VGroup(face, pips)


class DiceSampleSpace(Scene):
    """二つのサイコロの標本空間 — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "two_dice")
        self._duration = params.get("duration", 28)

        if mode == "distribution":
            self._build_distribution()
        else:
            self._build_two_dice()

    # ------------------------------------------------------------------
    # Mode: two_dice
    # ------------------------------------------------------------------
    def _build_two_dice(self):
        duration = self._duration

        title = Text(
            "起こりうる場合を、すべて数える",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.7)

        cell = 0.58
        x0, y0 = -3.2, 1.65  # center of col 0 / row 0

        def cpos(col, row):
            return np.array([x0 + col * cell, y0 - row * cell, 0])

        # Headers: die A across the top, die B down the left.
        headers = VGroup()
        for col in range(6):
            headers.add(_dice_face(col + 1, cpos(col, -1), cell * 0.82, ACCENT_CYAN))
        for row in range(6):
            headers.add(_dice_face(row + 1, cpos(-1, row), cell * 0.82, ACCENT_GOLD))
        self.play(FadeIn(headers), run_time=0.9)

        # 36 cells, each showing the sum (col+1)+(row+1).
        cells = {}
        cell_group = VGroup()
        for row in range(6):
            for col in range(6):
                s = (col + 1) + (row + 1)
                is7 = s == 7
                sq = Square(
                    side_length=cell * 0.9,
                    color=ACCENT_PINK if is7 else EDGE_COLOR,
                    stroke_width=1.5,
                    fill_color=ACCENT_PINK if is7 else ACCENT_CYAN,
                    fill_opacity=0.05,
                )
                sq.move_to(cpos(col, row))
                num = MathTex(str(s), font_size=22, color=TEXT_WHITE).set_opacity(0.85)
                num.move_to(cpos(col, row))
                cells[(col, row)] = VGroup(sq, num)
                cell_group.add(cells[(col, row)])

        self.play(
            LaggedStart(*[FadeIn(c) for c in cell_group], lag_ratio=0.02),
            run_time=2.0,
        )

        # Highlight the six sum-7 cells (anti-diagonal: col+row=5).
        seven = [cells[(c, 5 - c)] for c in range(6)]
        self.play(
            *[
                cells_i[0]
                .animate.set_fill(ACCENT_PINK, opacity=0.45)
                .set_stroke(ACCENT_PINK, width=2.5)
                for cells_i in seven
            ],
            run_time=0.8,
        )

        # Right-side conclusion.
        notes = VGroup(
            Text("二つのサイコロ", font=FONT, font_size=24, color=TEXT_WHITE),
            Text("＝ 全 36 通り", font=FONT, font_size=24, color=ACCENT_CYAN),
            Text("和が 7 ＝ 6 通り", font=FONT, font_size=24, color=ACCENT_PINK),
            MathTex(r"\frac{6}{36} = \frac{1}{6}", font_size=40, color=ACCENT_GOLD),
        )
        notes.arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        notes.move_to([3.4, 0.3, 0])

        anim_time = 0.7 + 0.9 + 2.0 + 0.8 + 4 * 0.6
        default_waits = 4 * 0.8 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for nb in notes:
            self.play(FadeIn(nb), run_time=0.6)
            self.wait(0.8 * ws)

        self.wait(max(1.0, duration - anim_time - 4 * 0.8 * ws))

    # ------------------------------------------------------------------
    # Mode: distribution
    # ------------------------------------------------------------------
    def _build_distribution(self):
        duration = self._duration

        title = Text(
            "目の和の出やすさ ＝ 場合の数",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.7)

        sums = list(range(2, 13))
        counts = [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        step = 0.66
        bar_w = 0.5
        unit = 0.28
        base_y = -1.3
        x_start = -(len(sums) - 1) / 2.0 * step

        bars, labels, cnums = VGroup(), VGroup(), VGroup()
        for i, (s, c) in enumerate(zip(sums, counts, strict=False)):
            x = x_start + i * step
            h = c * unit
            is7 = s == 7
            bar = Rectangle(
                width=bar_w,
                height=h,
                fill_color=ACCENT_PINK if is7 else ACCENT_CYAN,
                fill_opacity=0.8 if is7 else 0.65,
                stroke_color=ACCENT_PINK if is7 else ACCENT_CYAN,
                stroke_width=1.5,
            )
            bar.move_to([x, base_y + h / 2.0, 0])
            bars.add(bar)

            sl = MathTex(str(s), font_size=22, color=TEXT_DIM)
            sl.move_to([x, base_y - 0.28, 0])
            labels.add(sl)

            cn = MathTex(str(c), font_size=20, color=ACCENT_PINK if is7 else TEXT_DIM)
            cn.move_to([x, base_y + h + 0.2, 0])
            cnums.add(cn)

        axis = Rectangle(
            width=len(sums) * step,
            height=0.02,
            fill_color=EDGE_COLOR,
            fill_opacity=1,
            stroke_width=0,
        )
        axis.move_to([0, base_y, 0])
        self.play(FadeIn(axis), FadeIn(labels), run_time=0.7)

        anim_time = 0.7 + 0.7 + 1.6 + 0.6 + 0.7
        default_waits = 3.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(
            LaggedStart(*[FadeIn(b) for b in bars], lag_ratio=0.08),
            run_time=1.6,
        )
        self.play(FadeIn(cnums), run_time=0.6)
        self.wait(1.2 * ws)

        peak_note = Text("和 7 が最も多い ── 6 通り", font=FONT, font_size=22, color=ACCENT_PINK)
        peak_note.move_to([0, 1.5, 0])
        self.play(
            FadeIn(peak_note), Indicate(bars[5], color=ACCENT_PINK, scale_factor=1.12), run_time=0.7
        )
        self.wait(max(1.0, duration - anim_time - 1.2 * ws))


# Factual-claim metadata (read by qa_manim_consistency.py).
# Both modes are abstract probability — no on-screen person/year claims
# (the digits shown are dice values and counts, not historical years).
LINT_FACTUAL_CLAIMS = {
    "two_dice": {"people": [], "years": []},
    "distribution": {"people": [], "years": []},
}


SCENES = {
    "two_dice": DiceSampleSpace,
    "distribution": DiceSampleSpace,
}
