"""
hilbert_program.py - Hilbert's program and formal systems for 数学史記

Visualizes the dream of Hilbert's foundational program (the three pillars
of completeness, consistency, decidability) and the basic structure of a
formal system (axioms → inference rules → theorems).

Modes:
    three_pillars - Three vertical columns/pillars labeled
                    完全性 (completeness), 無矛盾性 (consistency),
                    決定可能性 (decidability) with subtitle captions.
                    Fixed params: pillar x ∈ {-3.6, 0, 3.6}, height 2.4,
                    width 1.5. Pillar tops y=1.7, bases y=-0.7.
    formal_system - Tree of: 3 axiom boxes (top tier) → 1 inference rule box
                    (middle) → 4 theorem boxes (bottom tier), with arrows.
                    Fixed params: axioms y=1.7, rule y=0.2, theorems y=-1.3.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 021 (Gödel), math pillar 1.
"""

import numpy as np
from manim import (
    Arrow,
    FadeIn,
    Line,
    Rectangle,
    RoundedRectangle,
    Scene,
    Text,
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

SUBTITLE_Y_LIMIT = -2.0


class HilbertProgram(Scene):
    """Hilbert's program and formal system structure. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 20)
        mode = params.get("mode", "three_pillars")

        if mode == "formal_system":
            self.build_formal_system()
        else:
            self.build_three_pillars()

    # -------------------------------------------------------------------
    # Mode: three_pillars
    # -------------------------------------------------------------------
    def build_three_pillars(self):
        duration = self._duration

        title = Text(
            "ヒルベルトの夢 ── 三本の柱",
            font=FONT,
            font_size=32,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        pillar_specs = [
            (-3.6, "完全性", "すべての真理は\n証明可能", ACCENT_CYAN),
            (0.0, "無矛盾性", "矛盾は\n導かれない", ACCENT_GOLD),
            (3.6, "決定可能性", "任意の命題は\n機械的に判定可能", ACCENT_PINK),
        ]

        pillar_h = 2.4
        pillar_w = 1.6
        pillar_top_y = 1.7
        pillar_bottom_y = pillar_top_y - pillar_h
        pillar_center_y = (pillar_top_y + pillar_bottom_y) / 2

        # Pillars (rectangles)
        pillars = []
        labels_top = []
        labels_bot = []
        for x, jp_label, jp_subtitle, color in pillar_specs:
            pillar = Rectangle(
                width=pillar_w,
                height=pillar_h,
                color=color,
                stroke_width=3,
                fill_opacity=0.18,
                fill_color=color,
            )
            pillar.move_to(np.array([x, pillar_center_y, 0]))
            pillars.append(pillar)

            # Label on top of pillar
            label = Text(jp_label, font=FONT, font_size=26, color=color)
            label.move_to(np.array([x, pillar_top_y + 0.4, 0]))
            labels_top.append(label)

            # Subtitle below pillar
            subtitle = Text(
                jp_subtitle,
                font=FONT,
                font_size=18,
                color=TEXT_WHITE,
                line_spacing=0.8,
            )
            subtitle.move_to(np.array([x, pillar_bottom_y - 0.5, 0]))
            labels_bot.append(subtitle)

        # Foundation line (ground)
        ground = Line(
            np.array([-5.0, pillar_bottom_y - 0.05, 0]),
            np.array([5.0, pillar_bottom_y - 0.05, 0]),
            color=TEXT_DIM,
            stroke_width=2,
        )

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(ground), run_time=0.4)

        for pillar, label_top, label_bot in zip(pillars, labels_top, labels_bot, strict=False):
            self.play(
                FadeIn(pillar),
                FadeIn(label_top),
                FadeIn(label_bot),
                run_time=0.7,
            )

        anim_overhead = 0.6 + 0.4 + 0.7 * 3
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: formal_system
    # -------------------------------------------------------------------
    def build_formal_system(self):
        duration = self._duration

        title = Text(
            "形式体系 ── 機械的な証明の世界",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # Tier 1: 3 axiom boxes
        axiom_y = 1.7
        axiom_xs = [-3.6, 0.0, 3.6]
        axiom_box_w = 2.0
        axiom_box_h = 0.7
        axiom_labels = ["公理 1", "公理 2", "公理 3"]
        axiom_boxes = []
        axiom_text = []
        for x, label in zip(axiom_xs, axiom_labels, strict=False):
            box = RoundedRectangle(
                width=axiom_box_w,
                height=axiom_box_h,
                corner_radius=0.1,
                color=ACCENT_CYAN,
                stroke_width=2.5,
                fill_opacity=0.15,
                fill_color=ACCENT_CYAN,
            )
            box.move_to(np.array([x, axiom_y, 0]))
            t = Text(label, font=FONT, font_size=22, color=TEXT_WHITE)
            t.move_to(np.array([x, axiom_y, 0]))
            axiom_boxes.append(box)
            axiom_text.append(t)

        # Tier label (left side)
        tier1_label = Text("公理", font=FONT, font_size=20, color=TEXT_DIM)
        tier1_label.move_to(np.array([-5.5, axiom_y, 0]))

        # Tier 2: inference rule box (center)
        rule_y = 0.2
        rule_box = RoundedRectangle(
            width=4.0,
            height=0.8,
            corner_radius=0.15,
            color=ACCENT_GOLD,
            stroke_width=3,
            fill_opacity=0.2,
            fill_color=ACCENT_GOLD,
        )
        rule_box.move_to(np.array([0, rule_y, 0]))
        rule_text = Text("推論規則", font=FONT, font_size=24, color=TEXT_WHITE)
        rule_text.move_to(np.array([0, rule_y, 0]))

        tier2_label = Text("規則", font=FONT, font_size=20, color=TEXT_DIM)
        tier2_label.move_to(np.array([-5.5, rule_y, 0]))

        # Tier 3: 4 theorem boxes
        thm_y = -1.3
        thm_xs = [-4.2, -1.4, 1.4, 4.2]
        thm_box_w = 2.0
        thm_box_h = 0.7
        thm_labels = ["定理 1", "定理 2", "定理 3", "定理 4"]
        thm_boxes = []
        thm_text = []
        for x, label in zip(thm_xs, thm_labels, strict=False):
            box = RoundedRectangle(
                width=thm_box_w,
                height=thm_box_h,
                corner_radius=0.1,
                color=ACCENT_PINK,
                stroke_width=2.5,
                fill_opacity=0.15,
                fill_color=ACCENT_PINK,
            )
            box.move_to(np.array([x, thm_y, 0]))
            t = Text(label, font=FONT, font_size=22, color=TEXT_WHITE)
            t.move_to(np.array([x, thm_y, 0]))
            thm_boxes.append(box)
            thm_text.append(t)

        tier3_label = Text("定理", font=FONT, font_size=20, color=TEXT_DIM)
        tier3_label.move_to(np.array([-5.5, thm_y, 0]))

        # Animate: title and tier labels first
        self.play(FadeIn(title), run_time=0.5)
        self.play(
            FadeIn(tier1_label),
            FadeIn(tier2_label),
            FadeIn(tier3_label),
            run_time=0.4,
        )

        # Axioms
        for box, t in zip(axiom_boxes, axiom_text, strict=False):
            self.play(FadeIn(box), FadeIn(t), run_time=0.3)

        # Arrows: axioms → rule
        arrows_a_to_r = []
        for x in axiom_xs:
            arr = Arrow(
                start=np.array([x, axiom_y - axiom_box_h / 2 - 0.05, 0]),
                end=np.array([x * 0.4, rule_y + 0.45, 0]),
                color=EDGE_COLOR,
                buff=0.02,
                stroke_width=2,
                tip_length=0.18,
                max_tip_length_to_length_ratio=1.0,
            )
            arrows_a_to_r.append(arr)
        self.play(*[FadeIn(a) for a in arrows_a_to_r], run_time=0.5)

        # Rule
        self.play(FadeIn(rule_box), FadeIn(rule_text), run_time=0.5)

        # Arrows: rule → theorems
        arrows_r_to_t = []
        for x in thm_xs:
            arr = Arrow(
                start=np.array([x * 0.3, rule_y - 0.45, 0]),
                end=np.array([x, thm_y + thm_box_h / 2 + 0.05, 0]),
                color=EDGE_COLOR,
                buff=0.02,
                stroke_width=2,
                tip_length=0.18,
                max_tip_length_to_length_ratio=1.0,
            )
            arrows_r_to_t.append(arr)
        self.play(*[FadeIn(a) for a in arrows_r_to_t], run_time=0.5)

        # Theorems
        for box, t in zip(thm_boxes, thm_text, strict=False):
            self.play(FadeIn(box), FadeIn(t), run_time=0.3)

        anim_overhead = 0.5 + 0.4 + 0.3 * 3 + 0.5 + 0.5 + 0.5 + 0.3 * 4
        self.wait(max(1.0, duration - anim_overhead))
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "three_pillars": {"people": [], "years": []},
    "formal_system": {"people": [], "years": []},
}



# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "three_pillars": {
        "class": "HilbertProgram",
        "params": {"mode": "three_pillars"},
        "description": "Three pillars: completeness, consistency, decidability",
    },
    "formal_system": {
        "class": "HilbertProgram",
        "params": {"mode": "formal_system"},
        "description": "Axioms → inference rule → theorems tree (3-1-4)",
    },
}
