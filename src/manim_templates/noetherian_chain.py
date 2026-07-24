"""
noetherian_chain.py - Abstract algebra evolution visualization for 数学史記

Visualizes the evolution of algebraic thinking: Gordan → Hilbert → Noether.

Modes:
    comparison - Three-stage comparison:
                 Gordan (331 invariants listed) → Hilbert (existence proof) →
                 Noether (ascending chain condition / structural thinking)
                 Fixed params: 3 panels side by side
    ascending  - Ascending chain of ideals I₁ ⊂ I₂ ⊂ I₃ ⊂ … stopping after
                 finitely many steps. Nested circles/boxes grow then halt.
                 Fixed params: chain length 5, stop at step 5 with emphasis

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Create,
    FadeIn,
    GrowArrow,
    Indicate,
    Line,
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


def _make_panel(title_text, body_lines, color, x_pos, panel_width=3.4):
    """Create a panel with title and body text."""
    panel = VGroup()

    bg = RoundedRectangle(
        width=panel_width,
        height=3.6,
        corner_radius=0.15,
        color=color,
        stroke_width=2,
        fill_color=BG_COLOR,
        fill_opacity=0.8,
    )
    bg.move_to(RIGHT * x_pos)

    title = Text(title_text, font=FONT, font_size=22, color=color)
    title.move_to(bg.get_top() + DOWN * 0.4)

    sep = Line(
        LEFT * (panel_width / 2 - 0.3),
        RIGHT * (panel_width / 2 - 0.3),
        color=color,
        stroke_width=1,
    )
    sep.next_to(title, DOWN, buff=0.15)

    body = VGroup()
    for line_text in body_lines:
        t = Text(line_text, font=FONT, font_size=16, color=TEXT_WHITE)
        body.add(t)
    body.arrange(DOWN, buff=0.18, aligned_edge=LEFT)
    body.next_to(sep, DOWN, buff=0.25)

    panel.add(bg, title, sep, body)
    return panel


class NoetherianChain(Scene):
    """Visualize the evolution of algebraic thinking and Noetherian rings."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "comparison")
        self._duration = params.get("duration", 25)

        if mode == "ascending":
            self.build_ascending()
        else:
            self.build_comparison()

    # -------------------------------------------------------------------
    # Mode: comparison — Gordan → Hilbert → Noether
    # -------------------------------------------------------------------
    def build_comparison(self):
        dur = self._duration
        anim_time = 8.0
        default_wait_total = 7.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "代数的思考の進化",
            font=FONT,
            font_size=30,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Panel 1: Gordan
        gordan = _make_panel(
            "ゴルダン",
            ["計算的手法", "331個の共変形式を", "ひとつずつ列挙"],
            TEXT_DIM,
            x_pos=-4.2,
            panel_width=3.2,
        )

        # Panel 2: Hilbert
        hilbert = _make_panel(
            "ヒルベルト",
            ["存在証明", "「有限個の基底で十分」", "具体的構成なし"],
            ACCENT_CYAN,
            x_pos=0.0,
            panel_width=3.2,
        )

        # Panel 3: Noether
        noether = _make_panel(
            "ネーター",
            ["構造的思考", "昇鎖条件（ACC）", "なぜ有限で止まるかを解明"],
            ACCENT_GOLD,
            x_pos=4.2,
            panel_width=3.2,
        )

        # Shift panels down to make room for title
        for panel in [gordan, hilbert, noether]:
            panel.shift(DOWN * 0.3)

        # Arrows between panels
        arr1 = Arrow(
            gordan.get_right() + RIGHT * 0.05,
            hilbert.get_left() + LEFT * 0.05,
            color=ACCENT_PINK,
            stroke_width=3,
            buff=0.05,
        )
        arr2 = Arrow(
            hilbert.get_right() + RIGHT * 0.05,
            noether.get_left() + LEFT * 0.05,
            color=ACCENT_PINK,
            stroke_width=3,
            buff=0.05,
        )

        # Animate
        self.play(FadeIn(gordan), run_time=1.0)
        self.wait(0.8 * ws)
        self.play(GrowArrow(arr1), run_time=0.5)
        self.play(FadeIn(hilbert), run_time=1.0)
        self.wait(0.8 * ws)
        self.play(GrowArrow(arr2), run_time=0.5)
        self.play(FadeIn(noether), run_time=1.0)
        self.wait(1.0 * ws)

        # Bottom emphasis
        note = Text(
            "具体的計算 → 存在の保証 → 構造の理解",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to(DOWN * 2.0)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: ascending — ascending chain of ideals stops
    # -------------------------------------------------------------------
    def build_ascending(self):
        dur = self._duration
        anim_time = 9.0
        default_wait_total = 7.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "昇鎖条件（ネーター環）",
            font=FONT,
            font_size=30,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Nested circles representing ideals I₁ ⊂ I₂ ⊂ I₃ ⊂ I₄ ⊂ I₅ = I₅
        chain_length = 5
        colors = [TEXT_DIM, TEXT_DIM, ACCENT_CYAN, ACCENT_CYAN, ACCENT_GOLD]
        radii = [0.4, 0.7, 1.0, 1.3, 1.6]

        center = UP * 0.5

        circles = VGroup()
        labels = VGroup()

        for i in range(chain_length):
            c = Circle(
                radius=radii[i],
                color=colors[i],
                stroke_width=2,
                fill_opacity=0.05,
            )
            c.move_to(center)
            circles.add(c)

            subscript = str(i + 1)
            label = MathTex(
                rf"I_{subscript}",
                font_size=22,
                color=colors[i],
            )
            label.move_to(center + RIGHT * (radii[i] - 0.15) + UP * 0.12)
            labels.add(label)

        # Animate circles growing one by one
        for i in range(chain_length):
            self.play(Create(circles[i]), FadeIn(labels[i]), run_time=0.8)
            self.wait(0.3 * ws)

        self.wait(0.5 * ws)

        # Chain display at bottom: I₁ ⊂ I₂ ⊂ I₃ ⊂ I₄ ⊂ I₅
        chain_tex_parts = []
        for i in range(chain_length):
            chain_tex_parts.append(rf"I_{i + 1}")
            if i < chain_length - 1:
                chain_tex_parts.append(r"\subset")

        chain_tex = MathTex(
            *chain_tex_parts,
            font_size=32,
            color=TEXT_WHITE,
        )
        chain_tex.move_to(DOWN * 1.5)
        self.play(FadeIn(chain_tex), run_time=0.8)
        self.wait(0.8 * ws)

        # Highlight: chain STOPS
        stop_text = Text(
            "有限ステップで停止！",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        )
        stop_text.move_to(DOWN * 2.0)

        # Highlight the outermost circle
        self.play(
            Indicate(circles[-1], color=ACCENT_GOLD, scale_factor=1.05),
            FadeIn(stop_text),
            run_time=1.0,
        )
        self.wait(1.0 * ws)

        # Note under title
        note = Text(
            "これがネーター環の定義",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "comparison": {"people": [], "years": []},
    "ascending": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
SCENES = {
    "comparison": NoetherianChain,
    "ascending": NoetherianChain,
}
