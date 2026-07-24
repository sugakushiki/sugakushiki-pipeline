"""
tenzan_notation.py — 点竄術（傍書法）visualization for 数学史記

関孝和の点竄術（傍書法）を、フワーリズミー回の修辞的代数と
現代記号の対比で視覚化する。1ファイル1クラス + mode分岐。

Modes:
    rhetorical_vs_tenzan - 3列比較：9世紀バグダード（言葉）vs 17世紀江戸
                           （傍書法）vs 現代（x, y）。
                           Fixed params: example x²+10x=39 (前回継続),
                           3 columns with era labels.
    system_of_equations  - 連立方程式 2x+3y=12, x-y=1 を現代記号と
                           点竄術（甲=x, 乙=y, 商=定数）で並列表示。
                           Fixed params: solution x=3, y=2, elimination
                           yields 5y=10.
    symbolic_manipulation - 天元術（算木、消える）vs 点竄術（紙上、残る）
                           の対比。
                           Fixed params: left column = 算木 (transient),
                           right column = 傍書 (persistent).

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 009 (関孝和)
"""

from manim import (
    DOWN,
    UP,
    Arrow,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class TenzanNotation(Scene):
    """点竄術 visualization — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "rhetorical_vs_tenzan")
        self._duration = params.get("duration", 22)

        if mode == "system_of_equations":
            self._build_system_of_equations()
        elif mode == "symbolic_manipulation":
            self._build_symbolic_manipulation()
        else:
            self._build_rhetorical_vs_tenzan()

    # ------------------------------------------------------------------
    # Mode A: rhetorical_vs_tenzan
    # ------------------------------------------------------------------
    def _build_rhetorical_vs_tenzan(self):
        duration = self._duration

        title = Text(
            "3つの「代数」",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 3 * 1.0 + 0.6
        default_waits = 3 * 1.2 + 1.5
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Column layout: 3 columns centered at x = -4.2, 0, +4.2
        col_x = [-4.2, 0.0, 4.2]

        # Headers (era + region)
        era_data = [
            ("9世紀", "バグダード", TEXT_DIM),
            ("17世紀", "江戸", ACCENT_GOLD),
            ("現代", "世界", TEXT_DIM),
        ]
        headers = VGroup()
        for i, (era, region, color) in enumerate(era_data):
            era_t = Text(era, font=FONT, font_size=22, color=color)
            reg_t = Text(region, font=FONT, font_size=20, color=color)
            reg_t.next_to(era_t, DOWN, buff=0.1)
            h = VGroup(era_t, reg_t)
            h.move_to([col_x[i], 2.0, 0])
            headers.add(h)

        self.play(FadeIn(headers), run_time=0.8)
        self.wait(0.4 * ws)

        # Column contents — the same equation x² + 10x = 39 in 3 notations
        # Left: rhetorical (words)
        left_lines = VGroup(
            Text("正方形と", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("十の根が", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("三十九に等しい", font=FONT, font_size=22, color=TEXT_WHITE),
        )
        left_lines.arrange(DOWN, buff=0.2)
        left_lines.move_to([col_x[0], 0.4, 0])

        # Middle: tenzan (kanji + side numbers) — simulated via Text stack
        # 「甲² 十甲 = 三十九」风格
        mid_lines = VGroup(
            Text("甲甲 十甲", font=FONT, font_size=26, color=ACCENT_GOLD),
            Text("商 三十九", font=FONT, font_size=24, color=ACCENT_GOLD),
        )
        mid_lines.arrange(DOWN, buff=0.3)
        mid_lines.move_to([col_x[1], 0.4, 0])

        # Right: modern
        right_eq = MathTex(r"x^2 + 10x = 39", font_size=32, color=ACCENT_CYAN)
        right_eq.move_to([col_x[2], 0.4, 0])

        self.play(FadeIn(left_lines), run_time=0.9)
        self.wait(0.4 * ws)
        self.play(FadeIn(mid_lines), run_time=0.9)
        self.wait(0.4 * ws)
        self.play(FadeIn(right_eq), run_time=0.9)
        self.wait(0.4 * ws)

        # Characterization labels at bottom
        feature_labels = VGroup()
        features = [
            ("言葉のみ", TEXT_DIM),
            ("漢字＋傍書", ACCENT_PINK),
            ("西洋記号", TEXT_DIM),
        ]
        for i, (txt, color) in enumerate(features):
            t = Text(txt, font=FONT, font_size=20, color=color)
            t.move_to([col_x[i], -1.3, 0])
            feature_labels.add(t)

        arrows = VGroup()
        for i in range(3):
            a = Arrow(
                start=[col_x[i], -0.5, 0],
                end=[col_x[i], -1.0, 0],
                color=TEXT_DIM,
                stroke_width=2,
                buff=0.05,
                max_tip_length_to_length_ratio=0.15,
            )
            arrows.add(a)

        self.play(FadeIn(arrows), FadeIn(feature_labels), run_time=0.8)
        self.wait(1.5 * ws)

        # Highlight middle (avoid overlap with feature label at y=-1.3)
        highlight = Rectangle(
            width=3.2,
            height=3.0,
            color=ACCENT_PINK,
            stroke_width=3,
            fill_opacity=0.0,
        )
        highlight.move_to([col_x[1], 0.9, 0])
        self.play(FadeIn(highlight), run_time=0.6)
        self.wait(max(duration - anim_time - 2.0, 1.0))

    # ------------------------------------------------------------------
    # Mode B: system_of_equations
    # ------------------------------------------------------------------
    def _build_system_of_equations(self):
        duration = self._duration

        title = Text(
            "連立方程式を点竄術で",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        # Column headers
        modern_label = Text("現代記号", font=FONT, font_size=22, color=TEXT_DIM)
        modern_label.move_to([-3.5, 2.1, 0])
        tenzan_label = Text("点竄術（漢字＋傍書）", font=FONT, font_size=22, color=ACCENT_GOLD)
        tenzan_label.move_to([3.2, 2.1, 0])
        self.play(FadeIn(modern_label), FadeIn(tenzan_label), run_time=0.6)

        anim_time = 0.8 + 0.6 + 6 * 0.8 + 0.8
        default_waits = 6 * 0.8 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # System: 2x + 3y = 12 ; x - y = 1 → x=3, y=2
        # Modern (left)
        mod_eq1 = MathTex(r"2x + 3y = 12", font_size=30, color=TEXT_WHITE)
        mod_eq1.move_to([-3.5, 1.1, 0])
        mod_eq2 = MathTex(r"x - y = 1", font_size=30, color=TEXT_WHITE)
        mod_eq2.move_to([-3.5, 0.3, 0])

        # Tenzan (right): 甲=x, 乙=y, 商=constant (number)
        ten_eq1 = Text("甲二 乙三 商十二", font=FONT, font_size=26, color=TEXT_WHITE)
        ten_eq1.move_to([3.2, 1.1, 0])
        ten_eq2 = Text("甲一 乙負一 商一", font=FONT, font_size=26, color=TEXT_WHITE)
        ten_eq2.move_to([3.2, 0.3, 0])

        self.play(FadeIn(mod_eq1), FadeIn(ten_eq1), run_time=0.7)
        self.wait(0.6 * ws)
        self.play(FadeIn(mod_eq2), FadeIn(ten_eq2), run_time=0.7)
        self.wait(0.8 * ws)

        # Elimination arrow
        elim_note = Text("↓ 消去", font=FONT, font_size=22, color=ACCENT_PINK)
        elim_note.move_to([0, -0.3, 0])
        self.play(FadeIn(elim_note), run_time=0.5)
        self.wait(0.4 * ws)

        # After elimination
        mod_eq3 = MathTex(r"5y = 10", font_size=30, color=ACCENT_CYAN)
        mod_eq3.move_to([-3.5, -1.0, 0])
        ten_eq3 = Text("乙五 商十", font=FONT, font_size=26, color=ACCENT_CYAN)
        ten_eq3.move_to([3.2, -1.0, 0])
        self.play(FadeIn(mod_eq3), FadeIn(ten_eq3), run_time=0.7)
        self.wait(0.6 * ws)

        mod_ans = MathTex(r"x = 3,\ y = 2", font_size=32, color=ACCENT_PINK)
        mod_ans.move_to([-3.5, -1.8, 0])
        ten_ans = Text("甲三 乙二", font=FONT, font_size=28, color=ACCENT_PINK)
        ten_ans.move_to([3.2, -1.8, 0])
        self.play(FadeIn(mod_ans), FadeIn(ten_ans), run_time=0.7)
        self.wait(1.5 * ws)

        # Legend
        legend = Text("甲＝x  乙＝y  商＝定数", font=FONT, font_size=18, color=TEXT_DIM)
        legend.move_to([0, -2.0, 0])
        # Clip to safe y range — legend is within -2.0~+3.3
        self.wait(max(duration - anim_time - 3.0, 0.5))

    # ------------------------------------------------------------------
    # Mode C: symbolic_manipulation
    # ------------------------------------------------------------------
    def _build_symbolic_manipulation(self):
        duration = self._duration

        title = Text(
            "天元術 vs 点竄術",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        subtitle = Text(
            "一次元・消える  vs  二次元・残る",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(subtitle), run_time=0.5)

        anim_time = 0.8 + 0.5 + 5 * 0.8 + 0.8
        default_waits = 5 * 0.9 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Left column: 天元術（算木）
        left_header = Text("天元術（算木）", font=FONT, font_size=24, color=ACCENT_CYAN)
        left_header.move_to([-3.5, 1.6, 0])

        # Sangi (counting rods) illustration: vertical/horizontal sticks.
        # Represent a number like "23" in sangi (tens=vertical, units=horiz).
        rods = VGroup()
        rod_specs = [
            # (cx, cy, orientation, length)
            (-4.3, 0.8, "v", 0.5),  # tens: 2 vertical
            (-4.1, 0.8, "v", 0.5),
            (-3.3, 0.9, "h", 0.5),  # units: 3 horizontal
            (-3.3, 0.8, "h", 0.5),
            (-3.3, 0.7, "h", 0.5),
        ]
        for cx, cy, orient, length in rod_specs:
            if orient == "v":
                line = Line(
                    start=[cx, cy - length / 2, 0],
                    end=[cx, cy + length / 2, 0],
                    color=ACCENT_CYAN,
                    stroke_width=4,
                )
            else:
                line = Line(
                    start=[cx - length / 2, cy, 0],
                    end=[cx + length / 2, cy, 0],
                    color=ACCENT_CYAN,
                    stroke_width=4,
                )
            rods.add(line)

        left_caption = Text(
            "計算が終わると  棒を崩し  過程は消える",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        left_caption.move_to([-3.5, -0.3, 0])

        # Right column: 点竄術（紙上）
        right_header = Text("点竄術（紙の上）", font=FONT, font_size=24, color=ACCENT_GOLD)
        right_header.move_to([3.5, 1.6, 0])

        paper_lines = VGroup(
            Text("甲 ＋ 甲 ＝", font=FONT, font_size=24, color=TEXT_WHITE),
            Text("二甲", font=FONT, font_size=26, color=ACCENT_GOLD),
            Text("（甲＋乙）×甲", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("＝ 甲甲 ＋ 甲乙", font=FONT, font_size=22, color=ACCENT_GOLD),
        )
        paper_lines.arrange(DOWN, buff=0.18)
        paper_lines.move_to([3.5, 0.8, 0])

        right_caption = Text(
            "計算の全過程が  紙の上に残る",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        right_caption.move_to([3.5, -0.5, 0])

        # Animate
        self.play(FadeIn(left_header), FadeIn(right_header), run_time=0.7)
        self.wait(0.3 * ws)
        self.play(FadeIn(rods), FadeIn(paper_lines), run_time=1.0)
        self.wait(0.8 * ws)
        self.play(FadeIn(left_caption), FadeIn(right_caption), run_time=0.7)
        self.wait(0.6 * ws)

        # Sangi fade out to show "disappearing"
        self.play(FadeOut(rods), run_time=0.8)
        gone_note = Text("消えた", font=FONT, font_size=22, color=TEXT_DIM)
        gone_note.move_to([-3.5, 0.8, 0])
        self.play(FadeIn(gone_note), run_time=0.5)

        # Paper persists: highlight
        paper_box = Rectangle(
            width=4.0,
            height=1.6,
            color=ACCENT_PINK,
            stroke_width=2,
            fill_opacity=0.0,
        )
        paper_box.move_to([3.5, 0.8, 0])
        self.play(FadeIn(paper_box), run_time=0.5)

        # Bottom summary
        summary = Text(
            "思考過程が残ることが  数学の革命だった",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        summary.move_to([0, -1.6, 0])
        self.play(FadeIn(summary), run_time=0.8)
        self.wait(max(duration - anim_time - 3.0, 1.0))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "rhetorical_vs_tenzan": {"people": [], "years": []},
    "system_of_equations": {"people": [], "years": []},
    "symbolic_manipulation": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
SCENES = {
    "rhetorical_vs_tenzan": TenzanNotation,
    "system_of_equations": TenzanNotation,
    "symbolic_manipulation": TenzanNotation,
}
