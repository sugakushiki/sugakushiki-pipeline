"""
tower_of_hanoi_recursion.py - 大きな問題を小さな同じ問題に畳む: ハノイの塔 (数学史記)

エドゥアール・リュカ回 の数学的主軸のひとつ。リュカが1883年に世に
出したハノイの塔は、<n枚の問題を n-1枚の同じ問題に畳む> という再帰の考え方
そのものであり、巨大素数を125回の数列に畳んだのと同じ<賢い計算>の精神を持つ。

Modes:
    solve     - 三本の柱と3枚の円盤で、一度に一枚・大を小の上に置かない、という
                規則のもと、すべてを別の柱へ移す最小手順 (7手) を段階アニメする。
                最後に 3枚なら 2^3-1=7 手を示す。
                Fixed params: 3 pegs, 3 disks, minimal solution = 7 moves.
    recursion - n枚を移すには <上の n-1枚を移す→最大の1枚を動かす→n-1枚を戻す>
                と自分自身の小さな場合に帰着する再帰構造を図示し、
                T(n)=2T(n-1)+1=2^n-1 を導く。64枚なら 2^64-1 で約5850億年。
                Fixed params: T(n)=2T(n-1)+1=2^n-1; T(64)~1.8e19, ~585 billion yr.

画面に人名・年号は出さない (narration が担う)。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 049 (Edouard Lucas), math pillar (recursion / Tower of Hanoi).
"""

import numpy as np
from manim import (
    RIGHT,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    ReplacementTransform,
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


class TowerOfHanoiRecursion(Scene):
    """ハノイの塔と再帰 ── multi-mode scene."""

    _PEG_X = {"A": -3.6, "B": 0.0, "C": 3.6}
    _BASE_Y = -1.5
    _DISK_H = 0.34
    _LIFT_Y = 1.55

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "solve")
        self._duration = params.get("duration", 26)

        if mode == "recursion":
            self._build_recursion()
        else:
            self._build_solve()

    # ------------------------------------------------------------------
    # Mode: solve  ── 3枚の最小手順 (7手) を段階アニメ
    # ------------------------------------------------------------------
    def _peg_pos(self, peg, level):
        return np.array(
            [self._PEG_X[peg], self._BASE_Y + self._DISK_H / 2 + level * self._DISK_H, 0.0]
        )

    def _build_solve(self):
        duration = self._duration

        title = Text(
            "ハノイの塔 ── 一度に一枚、大を小の上に置かない",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        rule = Text(
            "3枚を、すべて別の柱へ移すには？",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        rule.move_to([0, 2.4, 0])

        # base + pegs
        base = Line(
            [-5.0, self._BASE_Y, 0], [5.0, self._BASE_Y, 0], color=EDGE_COLOR, stroke_width=6
        )
        pegs = VGroup()
        for px in self._PEG_X.values():
            pegs.add(Line([px, self._BASE_Y, 0], [px, 1.2, 0], color=EDGE_COLOR, stroke_width=5))

        peg_labels = VGroup()
        for name, px in self._PEG_X.items():
            lbl = Text(name, font=FONT, font_size=26, color=TEXT_DIM)
            lbl.move_to([px, self._BASE_Y - 0.32, 0])
            peg_labels.add(lbl)

        # disks (1=small ... 3=large)
        disk_specs = {1: (1.0, ACCENT_CYAN), 2: (1.55, ACCENT_GOLD), 3: (2.1, ACCENT_PINK)}
        disks = {}
        for d, (w, col) in disk_specs.items():
            r = RoundedRectangle(
                width=w, height=self._DISK_H, corner_radius=0.08, color=col, stroke_width=3
            )
            r.set_fill(col, opacity=0.85)
            disks[d] = r

        # initial stacks: A holds [3,2,1] bottom->top
        stacks = {"A": [3, 2, 1], "B": [], "C": []}
        for peg, order in stacks.items():
            for level, d in enumerate(order):
                disks[d].move_to(self._peg_pos(peg, level))

        # setup animation
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(rule), run_time=0.5)
        self.play(FadeIn(base), FadeIn(pegs), FadeIn(peg_labels), run_time=0.7)
        self.play(*[FadeIn(disks[d]) for d in (3, 2, 1)], run_time=0.7)

        setup_time = 0.6 + 0.5 + 0.7 + 0.7

        # minimal 7-move solution for 3 disks (A -> C)
        moves = [
            (1, "A", "C"),
            (2, "A", "B"),
            (1, "C", "B"),
            (3, "A", "C"),
            (1, "B", "A"),
            (2, "B", "C"),
            (1, "A", "C"),
        ]
        motion = max(6.0, duration - setup_time - 3.0)
        move_rt = min(0.5, max(0.18, motion / (len(moves) * 3)))

        # working copy of stacks for level bookkeeping
        work = {"A": [3, 2, 1], "B": [], "C": []}
        for d, frm, to in moves:
            work[frm].pop()
            target = self._peg_pos(to, len(work[to]))
            work[to].append(d)
            cur = disks[d].get_center()
            up = np.array([cur[0], self._LIFT_Y, 0.0])
            over = np.array([target[0], self._LIFT_Y, 0.0])
            self.play(disks[d].animate.move_to(up), run_time=move_rt)
            self.play(disks[d].animate.move_to(over), run_time=move_rt)
            self.play(disks[d].animate.move_to(target), run_time=move_rt)

        # final formula (replace the rule line)
        formula = VGroup(
            Text("3枚なら、最小 ", font=FONT, font_size=28, color=ACCENT_GOLD),
            MathTex(r"2^{3} - 1 = 7", font_size=36, color=ACCENT_GOLD),
            Text(" 手", font=FONT, font_size=28, color=ACCENT_GOLD),
        ).arrange(RIGHT, buff=0.15)
        formula.move_to([0, 2.4, 0])

        self.play(ReplacementTransform(rule, formula), run_time=0.7)
        self.play(Indicate(formula, color=ACCENT_GOLD, scale_factor=1.1), run_time=0.6)

        elapsed = setup_time + len(moves) * 3 * move_rt + 0.7 + 0.6
        coda = max(1.0, duration - elapsed - 0.4)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: recursion  ── n枚 = n-1枚 + 1枚 + n-1枚、T(n)=2T(n-1)+1=2^n-1
    # ------------------------------------------------------------------
    def _build_recursion(self):
        duration = self._duration

        title = Text(
            "大きな問題を、小さな同じ問題に畳む",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.05, 0])

        steps = [
            ("(1)  上の n-1 枚を\n予備の柱へ移す", -4.2, ACCENT_CYAN),
            ("(2)  最大の 1 枚を\n動かす", 0.0, ACCENT_GOLD),
            ("(3)  n-1 枚を\n戻す", 4.2, ACCENT_CYAN),
        ]
        cards = VGroup()
        for txt, x, col in steps:
            card = RoundedRectangle(
                width=3.4, height=1.35, corner_radius=0.12, color=col, stroke_width=2
            )
            card.move_to([x, 1.55, 0])
            card.set_fill(col, opacity=0.06)
            label = Text(txt, font=FONT, font_size=22, color=TEXT_WHITE, line_spacing=0.8)
            label.move_to([x, 1.55, 0])
            cards.add(VGroup(card, label))

        recur = MathTex(
            r"T(n) = 2\,T(n-1) + 1 = 2^{n} - 1",
            font_size=42,
            color=ACCENT_CYAN,
        )
        recur.move_to([0, 0.15, 0])

        legend64 = MathTex(
            r"T(64) = 2^{64} - 1 \approx 1.8 \times 10^{19}",
            font_size=32,
            color=TEXT_WHITE,
        )
        legend64.move_to([0, -0.9, 0])

        years = Text(
            "一秒に一手でも、約5850億年（宇宙の年齢の40倍以上）",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        )
        years.move_to([0, -1.75, 0])

        anim_time = 0.7 + 3 * 0.6 + 0.8 + 0.7 + 0.7
        default_waits = 5.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        self.play(FadeIn(title), run_time=0.7)
        for c in cards:
            self.play(FadeIn(c), run_time=0.6)
        self.wait(1.0 * ws)
        self.play(FadeIn(recur), run_time=0.8)
        self.wait(1.1 * ws)
        self.play(FadeIn(legend64), run_time=0.7)
        self.play(FadeIn(years), run_time=0.7)
        self.play(Indicate(years, color=ACCENT_PINK, scale_factor=1.1), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.1 * ws - 0.6))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years in any mode. On-screen numbers
# (2^3-1=7, 2^64-1, 5850億) are mathematical values, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "solve": {"people": [], "years": []},
    "recursion": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "solve": TowerOfHanoiRecursion,
    "recursion": TowerOfHanoiRecursion,
}
