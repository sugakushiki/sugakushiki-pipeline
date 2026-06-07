"""
power_set_hierarchy.py - Cantor's theorem and the aleph tower for 数学史記

Visualizes Cantor's 1891 theorem |A| < |P(A)| and the resulting
hierarchy of infinite cardinalities.

Modes:
    finite_power - Table + explicit example of P(A) doubling as |A| grows.
                   Fixed params: |A| = 0,1,2,3,4 -> |P(A)| = 1,2,4,8,16.
                   Also shows P({a,b}) = {∅, {a}, {b}, {a,b}} explicitly.
    alef_tower   - Vertical stack of infinite cardinals:
                   ℵ₀ < 2^{ℵ₀} < 2^{2^{ℵ₀}} < 2^{2^{2^{ℵ₀}}} < ...
                   Ends with the open question "ℵ₀ と 2^{ℵ₀} のあいだには？"
                   (Continuum Hypothesis bridge).
                   Fixed params: 4 visible levels + continuation.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 016 (Cantor), math pillar 4.
"""

from manim import (
    RIGHT,
    UP,
    FadeIn,
    MathTex,
    Scene,
    SurroundingRectangle,
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


class PowerSetHierarchy(Scene):
    """Cantor's theorem and the infinite hierarchy. Mode-branching scene.

    Modes:
        finite_power (default) - |A|=0..4 -> |P(A)|=1..16, plus P({a,b})
        alef_tower             - infinite cardinal tower + CH question
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "finite_power")

        if mode == "alef_tower":
            self.build_alef_tower()
        else:
            self.build_finite_power()

    # -------------------------------------------------------------------
    # Mode: finite_power
    # -------------------------------------------------------------------
    def build_finite_power(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text(
            "カントールの定理 ── べき集合は必ず大きい", font=FONT, font_size=26, color=TEXT_DIM
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        # Left side: explicit example P({a,b}) = {∅, {a}, {b}, {a,b}}
        left_header = MathTex(r"A = \{a,\, b\}", font_size=32, color=ACCENT_CYAN)
        left_header.move_to([-3.8, 2.0, 0])
        self.play(FadeIn(left_header), run_time=0.4)

        power_formula = MathTex(
            r"\mathcal{P}(A) = \bigl\{\,",
            r"\varnothing",
            r",\; \{a\}",
            r",\; \{b\}",
            r",\; \{a,b\}",
            r"\,\bigr\}",
            font_size=30,
        )
        power_formula.move_to([-3.8, 1.2, 0])
        for piece in power_formula:
            self.play(FadeIn(piece), run_time=0.2)

        subset_count = MathTex(r"|\mathcal{P}(A)| = 2^2 = 4", font_size=30, color=highlight)
        subset_count.move_to([-3.8, 0.3, 0])
        self.play(FadeIn(subset_count), run_time=0.5)

        # Right side: table |A| -> |P(A)|
        table_x = 2.8
        header_y = 2.0

        hdr_a = MathTex(r"|A|", font_size=30, color=ACCENT_CYAN)
        hdr_p = MathTex(r"|\mathcal{P}(A)|", font_size=30, color=ACCENT_PINK)
        hdr_a.move_to([table_x - 1.0, header_y, 0])
        hdr_p.move_to([table_x + 1.2, header_y, 0])
        self.play(FadeIn(hdr_a), FadeIn(hdr_p), run_time=0.4)

        rows_data = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
        row_spacing = 0.55
        for i, (a, p) in enumerate(rows_data):
            y = header_y - 0.7 - i * row_spacing
            a_cell = MathTex(str(a), font_size=28, color=TEXT_WHITE)
            p_cell = MathTex(rf"2^{{{a}}} = {p}", font_size=28, color=TEXT_WHITE)
            a_cell.move_to([table_x - 1.0, y, 0])
            p_cell.move_to([table_x + 1.2, y, 0])
            self.play(FadeIn(a_cell), FadeIn(p_cell), run_time=0.25)

        conclusion = MathTex(r"|A| \;<\; |\mathcal{P}(A)|", font_size=42, color=highlight)
        conclusion.move_to([0, -1.8, 0])
        self.play(FadeIn(conclusion), run_time=0.7)

        anim_overhead = 0.5 + 0.4 + 0.2 * 6 + 0.5 + 0.4 + 0.25 * len(rows_data) + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: alef_tower
    # -------------------------------------------------------------------
    def build_alef_tower(self):
        duration = self._duration
        highlight = self._highlight_color

        title = Text("無限の階層 ── どこまでも続く塔", font=FONT, font_size=28, color=TEXT_DIM)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        # Tower from bottom up: ℵ₀, 2^ℵ₀, 2^(2^ℵ₀), 2^(2^(2^ℵ₀))
        levels = [
            (r"\aleph_0", "自然数 N の濃度"),
            (r"2^{\aleph_0}", "実数 R の濃度"),
            (r"2^{2^{\aleph_0}}", ""),
            (r"2^{2^{2^{\aleph_0}}}", ""),
        ]

        # Bottom level at y = -1.1 so box bottom stays clear of
        # ch_question at y = -2.0.
        level_y_start = -1.1
        level_spacing = 0.85
        x_center = -1.5

        boxes = []
        labels = []
        descriptions = []

        for i, (tex, desc) in enumerate(levels):
            y = level_y_start + i * level_spacing
            label = MathTex(tex, font_size=34, color=ACCENT_CYAN)
            label.move_to([x_center, y, 0])
            box = SurroundingRectangle(label, color=ACCENT_CYAN, buff=0.18, stroke_width=2)
            labels.append(label)
            boxes.append(box)
            if desc:
                desc_text = Text(desc, font=FONT, font_size=22, color=TEXT_DIM)
                desc_text.move_to([x_center + 3.4, y, 0])
                descriptions.append(desc_text)
            else:
                descriptions.append(None)

        # Play bottom-up
        for i in range(len(levels)):
            self.play(FadeIn(boxes[i]), FadeIn(labels[i]), run_time=0.4)
            if descriptions[i] is not None:
                self.play(FadeIn(descriptions[i]), run_time=0.3)

        # Trailing dots "..." above the top box
        top_y = level_y_start + len(levels) * level_spacing
        dots = MathTex(r"\vdots", font_size=34, color=TEXT_DIM)
        dots.move_to([x_center, top_y - 0.1, 0])
        self.play(FadeIn(dots), run_time=0.3)

        # Less-than signs between levels
        for i in range(len(levels) - 1):
            mid_y = (
                level_y_start + i * level_spacing + level_y_start + (i + 1) * level_spacing
            ) / 2
            lt_sign = MathTex(r"<", font_size=28, color=highlight)
            lt_sign.move_to([x_center - 1.6, mid_y, 0])
            self.play(FadeIn(lt_sign), run_time=0.15)

        # CH question: between aleph_0 and 2^aleph_0
        # Mix Japanese Text with MathTex for the math symbols
        # (BIZ UDMincho does not cover aleph/subscripts).
        ch_q_left = MathTex(r"\aleph_0", font_size=26, color=ACCENT_PINK)
        ch_q_and = Text(" と ", font=FONT, font_size=22, color=ACCENT_PINK)
        ch_q_mid = MathTex(r"2^{\aleph_0}", font_size=26, color=ACCENT_PINK)
        ch_q_right = Text(" のあいだに何かあるか？", font=FONT, font_size=22, color=ACCENT_PINK)
        ch_question = VGroup(ch_q_left, ch_q_and, ch_q_mid, ch_q_right)
        ch_question.arrange(RIGHT, buff=0.1)
        ch_question.move_to([0, -2.0, 0])
        self.play(FadeIn(ch_question), run_time=0.6)

        anim_overhead = 0.5 + (0.4 + 0.3) * len(levels) + 0.3 + 0.15 * (len(levels) - 1) + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "finite_power": {"people": [["Cantor", "カントール"]], "years": []},
    "alef_tower": {"people": [["Cantor", "カントール"]], "years": []},
}


SCENES = {
    "finite_power": {
        "class": "PowerSetHierarchy",
        "params": {"mode": "finite_power"},
        "description": "Finite power sets |A|=0..4, |P(A)|=1,2,4,8,16",
    },
    "alef_tower": {
        "class": "PowerSetHierarchy",
        "params": {"mode": "alef_tower"},
        "description": "Infinite cardinal tower aleph_0 < 2^aleph_0 < ... with CH question",
    },
}
