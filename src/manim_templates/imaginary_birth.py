"""
imaginary_birth.py - 虚数の誕生 (数学史記)

カルダノ回 の数学的本質。『アルス・マグナ』(1545) で、カルダノが
「10 を二つに分け積を 40 に」という問題から 5±√(-15) を導き、人類で初めて
負の数の平方根を含む計算を書き残した瞬間を可視化する。

Modes:
    no_real_root  - 放物線 y = x^2 - 10x + 40 が x 軸と交わらない (頂点 (5,15)) =
                    実数解が存在しないことを示す。判別式 D = -60 < 0。
                    Fixed params: parabola x^2-10x+40, vertex (5,15), D=-60.
    formal_product- 5±√(-15) の形式計算を段階表示する。
                    10=a+b, ab=40 → x^2-10x+40=0 → x=5±√(-15)、
                    「精神の拷問は脇に置き」、(5+√(-15))(5-√(-15))=25-(-15)=40。
                    最後に数直線→平面への跳躍を一瞬だけ示唆する (深入りしない)。
                    Fixed params: 5±√(-15), product = 40.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 039 (Cardano), math pillar (birth of complex numbers).
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Axes,
    DashedLine,
    Dot,
    FadeIn,
    Indicate,
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


class ImaginaryBirth(Scene):
    """虚数の誕生 — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "no_real_root")
        self._duration = params.get("duration", 26)

        if mode == "formal_product":
            self._build_formal_product()
        else:
            self._build_no_real_root()

    # ------------------------------------------------------------------
    # Mode: no_real_root
    # ------------------------------------------------------------------
    def _build_no_real_root(self):
        duration = self._duration

        title = Text(
            "答えがあるはずなのに ── x 軸と交わらない",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 45, 15],
            x_length=5.0,
            y_length=3.2,
            tips=False,
            axis_config={"color": EDGE_COLOR, "stroke_width": 2, "include_numbers": False},
        )
        axes.shift(LEFT * 2.3 + UP * 0.2)
        x_axis_lbl = MathTex("x", font_size=26, color=TEXT_DIM)
        x_axis_lbl.next_to(axes.x_axis.get_end(), DOWN, buff=0.15)

        parabola = axes.plot(
            lambda x: x * x - 10 * x + 40,
            x_range=[0.4, 9.6],
            color=ACCENT_CYAN,
            stroke_width=4,
        )

        self.play(FadeIn(axes), FadeIn(x_axis_lbl), run_time=0.7)
        self.play(FadeIn(parabola), run_time=1.0)

        # Vertex and the gap to the x-axis.
        vtx = axes.c2p(5, 15)
        foot = axes.c2p(5, 0)
        vtx_dot = Dot(vtx, radius=0.07, color=ACCENT_PINK)
        gap = DashedLine(vtx, foot, color=ACCENT_PINK, stroke_width=2.5)
        gap_lbl = Text("谷でも 0 に届かない", font=FONT, font_size=18, color=ACCENT_PINK)
        gap_lbl.next_to(gap, RIGHT, buff=0.15)

        self.play(FadeIn(vtx_dot), FadeIn(gap), run_time=0.7)
        self.play(FadeIn(gap_lbl), run_time=0.5)

        # Right-side annotations.
        notes = VGroup(
            MathTex(r"x^2 - 10x + 40 = 0", font_size=30, color=TEXT_WHITE),
            MathTex(r"D = (-10)^2 - 4\cdot 40 = -60", font_size=28, color=ACCENT_GOLD),
            Text("判別式が負 → 実数解なし", font=FONT, font_size=22, color=ACCENT_PINK),
        )
        notes.arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        notes.move_to([3.0, 0.2, 0])

        anim_time = 0.7 + 0.7 + 1.0 + 0.7 + 0.5 + 3 * 0.7
        default_waits = 3 * 0.9 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for nb in notes:
            self.play(FadeIn(nb), run_time=0.7)
            self.wait(0.9 * ws)

        self.wait(max(1.0, duration - anim_time - 3 * 0.9 * ws))

    # ------------------------------------------------------------------
    # Mode: formal_product
    # ------------------------------------------------------------------
    def _build_formal_product(self):
        duration = self._duration

        title = Text(
            "10 を二つに分け、積を 40 に",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to([0, 3.1, 0])
        self.play(FadeIn(title), run_time=0.7)

        # Left: the formal derivation.
        steps = VGroup(
            MathTex(r"a + b = 10,\quad ab = 40", font_size=30, color=TEXT_WHITE),
            MathTex(r"x^2 - 10x + 40 = 0", font_size=30, color=TEXT_WHITE),
            MathTex(
                r"x = 5 \pm \sqrt{25 - 40} = 5 \pm \sqrt{-15}", font_size=30, color=ACCENT_CYAN
            ),
            MathTex(
                r"(5+\sqrt{-15})(5-\sqrt{-15}) = 25-(-15) = 40", font_size=27, color=ACCENT_GOLD
            ),
        )
        steps.arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        for s in steps:
            if s.width > 5.9:
                s.scale_to_fit_width(5.9)
        steps.move_to([-3.2, 0.55, 0])

        # The famous aside, placed under the derivation.
        aside_ja = Text("「精神の拷問は脇に置き」", font=FONT, font_size=22, color=ACCENT_PINK)
        aside_la = Text("dimissis incruciationibus", font=FONT, font_size=16, color=TEXT_DIM)
        aside = VGroup(aside_ja, aside_la).arrange(DOWN, buff=0.12)
        aside.move_to([-3.2, -1.55, 0])

        anim_time = 0.7 + 4 * 0.7 + 0.6 + 0.6 + 1.0
        default_waits = 4 * 0.8 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for i, s in enumerate(steps):
            self.play(FadeIn(s), run_time=0.7)
            self.wait(0.8 * ws)
            if i == 2:
                self.play(FadeIn(aside), run_time=0.6)
                self.wait(0.6 * ws)

        self.play(Indicate(steps[3], color=ACCENT_GOLD, scale_factor=1.06), run_time=0.6)

        # Right: a brief hint that these live off the real line — on a plane.
        cx, cy = 4.0, 0.25
        real_axis = Line([cx - 1.5, cy, 0], [cx + 1.5, cy, 0], color=EDGE_COLOR, stroke_width=2)
        imag_axis = Line([cx, cy - 1.1, 0], [cx, cy + 1.3, 0], color=EDGE_COLOR, stroke_width=2)
        five = Dot([cx, cy, 0], radius=0.05, color=TEXT_DIM)
        five_lbl = MathTex("5", font_size=22, color=TEXT_DIM)
        five_lbl.next_to(five, DOWN, buff=0.12)
        top_dot = Dot([cx, cy + 0.75, 0], radius=0.06, color=ACCENT_PINK)
        bot_dot = Dot([cx, cy - 0.75, 0], radius=0.06, color=ACCENT_PINK)
        conj_lbl = MathTex(r"5 \pm i\sqrt{15}", font_size=24, color=ACCENT_PINK)
        conj_lbl.move_to([cx + 0.05, cy + 1.55, 0])
        plane_cap = Text("実数の外 ── 平面の数へ", font=FONT, font_size=18, color=TEXT_DIM)
        plane_cap.move_to([cx, cy - 1.5, 0])

        plane = VGroup(real_axis, imag_axis, five, five_lbl, top_dot, bot_dot, conj_lbl, plane_cap)
        self.play(FadeIn(plane), run_time=0.9)

        self.wait(max(1.2, duration - anim_time - 4 * 0.8 * ws - 0.6 * ws))


# Factual-claim metadata (read by qa_manim_consistency.py).
# Both modes are pure mathematics — no on-screen person/year claims.
LINT_FACTUAL_CLAIMS = {
    "no_real_root": {"people": [], "years": []},
    "formal_product": {"people": [], "years": []},
}


SCENES = {
    "no_real_root": ImaginaryBirth,
    "formal_product": ImaginaryBirth,
}
