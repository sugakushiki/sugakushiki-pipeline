"""
quadratic_reciprocity.py - Gauss quadratic reciprocity for 数学史記

Visualizes the law of quadratic reciprocity established by Gauss in his 1801
Disquisitiones Arithmeticae, a concrete numerical example, and the statement
of Hilbert's 9th problem (1900) that generalized it.

Modes:
    gauss_law       - Title 'ガウスの平方剰余の相互法則 (1801)' on top,
                      large MathTex of (p/q)(q/p) = (-1)^{(p-1)(q-1)/4}
                      centered around y=0.6, Legendre symbol definition line
                      below at y=-0.7. Fixed params: formula font_size 56,
                      definition font_size 22.
    examples        - Title 'p=5, q=13 のとき' centered top, two-row table:
                      (5/13)(13/5) = +1 (computed values shown step by step)
                      with (p-1)(q-1)/4 = 4*12/4 = 12 (even) → (-1)^12 = +1.
                      Fixed params: example values p=5, q=13, result +1.
    hilbert_9       - Title 'ヒルベルト第九問題 (1900 パリ)' on top, then
                      the statement text in 3 lines centered at y=0.5, 0.0, -0.5,
                      caption '相互法則の最も一般的な形' at y=-1.2.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 030 (Takagi), reciprocity series introduction.
"""

import numpy as np
from manim import (
    FadeIn,
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


class QuadraticReciprocity(Scene):
    """Gauss quadratic reciprocity, examples, and Hilbert's 9th problem."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 20)
        mode = params.get("mode", "gauss_law")

        if mode == "examples":
            self.build_examples()
        elif mode == "hilbert_9":
            self.build_hilbert_9()
        elif mode == "mod_qr_definition":
            self.build_mod_qr_definition()
        else:
            self.build_gauss_law()

    # -------------------------------------------------------------------
    # Mode: gauss_law
    # -------------------------------------------------------------------
    def build_gauss_law(self):
        duration = self._duration

        title = Text(
            "ガウスの平方剰余の相互法則 (1801)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # Main formula: (p/q)(q/p) = (-1)^((p-1)(q-1)/4)
        formula = MathTex(
            r"\left(\frac{p}{q}\right)\left(\frac{q}{p}\right) = (-1)^{\frac{(p-1)(q-1)}{4}}",
            font_size=56,
            color=TEXT_WHITE,
        )
        formula.move_to(np.array([0, 0.7, 0]))

        # Definition line below
        def_caption = Text(
            "ルジャンドル記号",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        def_caption.move_to(np.array([-3.8, -0.6, 0]))

        def_formula = MathTex(
            r"\left(\frac{p}{q}\right) = \begin{cases} +1 & p \text{ is QR mod } q \\ -1 & \text{otherwise} \end{cases}",
            font_size=28,
            color=TEXT_WHITE,
        )
        def_formula.move_to(np.array([1.0, -0.7, 0]))

        # Bottom caption: golden theorem
        bottom_caption = Text(
            "ガウスが『黄金の定理』と呼んだ ── 八通りの証明を残す",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        bottom_caption.move_to(np.array([0, -1.7, 0]))

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(formula), run_time=1.0)
        self.play(FadeIn(def_caption), FadeIn(def_formula), run_time=0.8)
        self.play(FadeIn(bottom_caption), run_time=0.6)

        anim_overhead = 0.6 + 1.0 + 0.8 + 0.6
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: examples
    # -------------------------------------------------------------------
    def build_examples(self):
        duration = self._duration

        title = Text(
            "具体例 ── p=5, q=13 の場合",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # Step 1: (-1)^((p-1)(q-1)/4) for p=5, q=13
        step1_label = Text("指数を計算", font=FONT, font_size=22, color=ACCENT_CYAN)
        step1_label.move_to(np.array([-4.6, 1.6, 0]))

        step1_formula = MathTex(
            r"\frac{(p-1)(q-1)}{4} = \frac{4 \cdot 12}{4} = 12",
            font_size=36,
            color=TEXT_WHITE,
        )
        step1_formula.move_to(np.array([1.2, 1.6, 0]))

        # Step 2: (-1)^12 = +1
        step2_label = Text("符号を決定", font=FONT, font_size=22, color=ACCENT_CYAN)
        step2_label.move_to(np.array([-4.6, 0.4, 0]))

        step2_formula = MathTex(
            r"(-1)^{12} = +1",
            font_size=36,
            color=ACCENT_GOLD,
        )
        step2_formula.move_to(np.array([1.2, 0.4, 0]))

        # Step 3: Legendre symbols evaluate to +1 each
        step3_label = Text("実値を確認", font=FONT, font_size=22, color=ACCENT_CYAN)
        step3_label.move_to(np.array([-4.6, -0.9, 0]))

        step3_formula = MathTex(
            r"\left(\frac{5}{13}\right)\left(\frac{13}{5}\right) = (-1)(-1) = +1",
            font_size=36,
            color=TEXT_WHITE,
        )
        step3_formula.move_to(np.array([1.2, -0.9, 0]))

        # Bottom caption
        bottom_caption = Text(
            "相互法則は両辺が一致 ── ガウスの定理が成り立つ",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        bottom_caption.move_to(np.array([0, -1.8, 0]))

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(step1_label), FadeIn(step1_formula), run_time=0.8)
        self.play(FadeIn(step2_label), FadeIn(step2_formula), run_time=0.8)
        self.play(FadeIn(step3_label), FadeIn(step3_formula), run_time=0.8)
        self.play(FadeIn(bottom_caption), run_time=0.6)

        anim_overhead = 0.6 + 0.8 * 3 + 0.6
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: hilbert_9
    # -------------------------------------------------------------------
    def build_hilbert_9(self):
        duration = self._duration

        title = Text(
            "ヒルベルト第九問題 (1900 パリ)",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # Subtitle
        subtitle = Text(
            "二十三問題のうちの一つ",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        subtitle.move_to(np.array([0, 2.1, 0]))

        # Statement box (3-line text centered)
        statement_box = Rectangle(
            width=11.0,
            height=2.3,
            color=ACCENT_CYAN,
            stroke_width=2.5,
            fill_opacity=0.08,
            fill_color=ACCENT_CYAN,
        )
        statement_box.move_to(np.array([0, 0.3, 0]))

        line1 = Text(
            "一般代数体における素数冪 k 階の",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        line1.move_to(np.array([0, 0.9, 0]))

        line2 = Text(
            "規範剰余の", font=FONT, font_size=26, color=TEXT_WHITE
        )
        line2_emph = Text(
            "最も一般的な相互法則",
            font=FONT,
            font_size=30,
            color=ACCENT_PINK,
        )
        line2_group = VGroup(line2, line2_emph).arrange(buff=0.2)
        line2_group.move_to(np.array([0, 0.3, 0]))

        line3 = Text(
            "を見出すこと",
            font=FONT,
            font_size=26,
            color=TEXT_WHITE,
        )
        line3.move_to(np.array([0, -0.3, 0]))

        # Bottom caption: who answered
        bottom_caption = Text(
            "高木 (1920) とアルティン (1923-1930) がアーベル拡大版を完全解決",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        bottom_caption.move_to(np.array([0, -1.6, 0]))

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(subtitle), run_time=0.4)
        self.play(FadeIn(statement_box), run_time=0.5)
        self.play(FadeIn(line1), run_time=0.5)
        self.play(FadeIn(line2_group), run_time=0.5)
        self.play(FadeIn(line3), run_time=0.5)
        self.play(FadeIn(bottom_caption), run_time=0.7)

        anim_overhead = 0.6 + 0.4 + 0.5 * 4 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: mod_qr_definition (法と平方剰余の定義)
    # -------------------------------------------------------------------
    def build_mod_qr_definition(self):
        duration = self._duration

        title = Text(
            "用語の整理 ── 法と平方剰余",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.9, 0]))

        # 法 (mod) の定義
        mod_label = Text("法 (mod)", font=FONT, font_size=24, color=ACCENT_CYAN)
        mod_label.move_to(np.array([-4.6, 1.8, 0]))

        mod_def = Text(
            "ある整数で割った余りで考えること",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        mod_def.move_to(np.array([0.6, 1.8, 0]))

        mod_example_text = Text(
            "例: 14 ÷ 5 = 2 余り 4",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        mod_example_text.move_to(np.array([-2.6, 0.9, 0]))

        mod_example_math = MathTex(
            r"\Rightarrow\;\; 14 \equiv 4 \pmod{5}",
            font_size=32,
            color=TEXT_WHITE,
        )
        mod_example_math.move_to(np.array([2.0, 0.9, 0]))

        # 平方剰余 (QR) の定義
        qr_label = Text("平方剰余", font=FONT, font_size=24, color=ACCENT_PINK)
        qr_label.move_to(np.array([-4.6, -0.2, 0]))

        qr_def = Text(
            "ある整数を 2 乗して得られる値",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        qr_def.move_to(np.array([0.4, -0.2, 0]))

        qr_example = MathTex(
            r"\bmod 5:\;\; 1^2 \equiv 1,\; 2^2 \equiv 4,\; 3^2 \equiv 4,\; 4^2 \equiv 1",
            font_size=28,
            color=TEXT_WHITE,
        )
        qr_example.move_to(np.array([0, -1.1, 0]))

        # 結果
        qr_set = Text(
            "→ 法 5 の平方剰余は {1, 4}、剰余でない数 {2, 3} は平方非剰余",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        qr_set.move_to(np.array([0, -1.9, 0]))

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(mod_label), FadeIn(mod_def), run_time=0.5)
        self.play(FadeIn(mod_example_text), FadeIn(mod_example_math), run_time=0.7)
        self.play(FadeIn(qr_label), FadeIn(qr_def), run_time=0.5)
        self.play(FadeIn(qr_example), run_time=0.7)
        self.play(FadeIn(qr_set), run_time=0.6)

        anim_overhead = 0.5 + 0.5 + 0.7 + 0.5 + 0.7 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "gauss_law": {
        "people": [["ガウス", "Gauss"]],
        "years": ["1801"],
    },
    "examples": {
        "people": [["ガウス", "Gauss"]],
        "years": [],
    },
    "mod_qr_definition": {
        "people": [],
        "years": [],
    },
    "hilbert_9": {
        "people": [
            ["ヒルベルト", "Hilbert"],
            ["高木", "Takagi"],
            ["アルティン", "Artin"],
        ],
        "years": ["1900", "1920", "1923", "1930"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "gauss_law": {
        "class": "QuadraticReciprocity",
        "params": {"mode": "gauss_law"},
        "description": "Gauss quadratic reciprocity formula with Legendre symbol definition (1801)",
    },
    "examples": {
        "class": "QuadraticReciprocity",
        "params": {"mode": "examples"},
        "description": "Concrete example p=5, q=13 evaluating to (-1)(-1)=+1, matching (-1)^12=+1",
    },
    "mod_qr_definition": {
        "class": "QuadraticReciprocity",
        "params": {"mode": "mod_qr_definition"},
        "description": "Definitions of 法 (mod) and 平方剰余 (QR) with mod 5 example {1, 4}",
    },
    "hilbert_9": {
        "class": "QuadraticReciprocity",
        "params": {"mode": "hilbert_9"},
        "description": "Hilbert's 9th problem statement (1900 Paris ICM): most general reciprocity law",
    },
}
