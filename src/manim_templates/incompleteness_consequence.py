"""
incompleteness_consequence.py - Consequences of Gödel's incompleteness for 数学史記

Visualizes the two main consequences of Gödel's 1931 results: (i) the
collapse of the three pillars of Hilbert's program, (ii) the second
incompleteness theorem PA ⊬ Cons(PA) — a formal system cannot prove
its own consistency.

Modes:
    hilbert_program_collapse - Three pillars labeled completeness,
                               consistency, decidability stand upright,
                               then fall (rotate down to the ground)
                               in sequence to show Hilbert's dream
                               ending.
                               Fixed params: 3 pillars at x={-3.6,0,3.6},
                               height 2.4, width 1.6, fall sequence
                               left → right.
    second_undecidable       - Large rounded box representing PA system.
                               Inside: small Cons(PA) box (the target).
                               Arrow tries to derive Cons(PA) inside the
                               system, blocked with red X. Below: formula
                               PA ⊬ Cons(PA). Caption explains that the
                               system cannot prove its own consistency.
                               Fixed params: PA box at center y=0.7,
                               width 6.0, height 2.4. Cons(PA) inside.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 021 (Gödel), math pillar 3.
"""

import numpy as np
from manim import (
    PI,
    Arrow,
    Cross,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
    Rotate,
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

SUBTITLE_Y_LIMIT = -2.0


class IncompletenessConsequence(Scene):
    """Consequences of Gödel's incompleteness theorems. Mode-branching."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 18)
        mode = params.get("mode", "hilbert_program_collapse")

        if mode == "second_undecidable":
            self.build_second_undecidable()
        else:
            self.build_hilbert_program_collapse()

    # -------------------------------------------------------------------
    # Mode: hilbert_program_collapse
    # -------------------------------------------------------------------
    def build_hilbert_program_collapse(self):
        duration = self._duration

        title = Text(
            "ヒルベルトの夢の終焉",
            font=FONT,
            font_size=32,
            color=ACCENT_PINK,
        )
        title.move_to(np.array([0, 3.0, 0]))

        pillar_specs = [
            (-3.6, "完全性", ACCENT_CYAN),
            (0.0, "無矛盾性", ACCENT_GOLD),
            (3.6, "決定可能性", ACCENT_PINK),
        ]

        pillar_h = 2.4
        pillar_w = 1.6
        pillar_top_y = 1.7
        pillar_bottom_y = pillar_top_y - pillar_h
        pillar_center_y = (pillar_top_y + pillar_bottom_y) / 2

        # Build pillars and labels (groups so we can rotate them as units)
        pillar_groups = []
        for x, jp_label, color in pillar_specs:
            pillar = Rectangle(
                width=pillar_w,
                height=pillar_h,
                color=color,
                stroke_width=3,
                fill_opacity=0.18,
                fill_color=color,
            )
            pillar.move_to(np.array([x, pillar_center_y, 0]))

            label = Text(jp_label, font=FONT, font_size=24, color=color)
            label.move_to(np.array([x, pillar_top_y + 0.4, 0]))

            group = VGroup(pillar, label)
            pillar_groups.append((group, x, color))

        # Foundation line (ground)
        ground = Line(
            np.array([-5.0, pillar_bottom_y - 0.05, 0]),
            np.array([5.0, pillar_bottom_y - 0.05, 0]),
            color=TEXT_DIM,
            stroke_width=2,
        )

        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(ground), run_time=0.4)

        # Show all pillars upright first
        for group, _, _ in pillar_groups:
            self.play(FadeIn(group), run_time=0.5)

        self.wait(0.6)

        # Each pillar rotates around its base and falls
        # We rotate -PI/2 (90 degrees clockwise for left, CCW for right)
        # so they all fall outward. Use base of pillar as pivot.
        for i, (group, x, color) in enumerate(pillar_groups):
            base_point = np.array([x, pillar_bottom_y, 0])
            # Falling direction: pillar 0 falls left (-PI/2),
            # pillar 1 falls left (-PI/2), pillar 2 falls right (+PI/2).
            angle = PI / 2 if i == 2 else -PI / 2
            self.play(
                Rotate(group, angle=angle, about_point=base_point),
                run_time=0.9,
            )

        # Subtitle after fall
        bottom_note = Text(
            "三本の柱はすべて崩れ落ちた",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        bottom_note.move_to(np.array([0, -1.85, 0]))
        self.play(FadeIn(bottom_note), run_time=0.6)

        anim_overhead = 0.5 + 0.4 + 0.5 * 3 + 0.6 + 0.9 * 3 + 0.6
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: second_undecidable
    # -------------------------------------------------------------------
    def build_second_undecidable(self):
        duration = self._duration

        title = Text(
            "第二不完全性定理 ── 自分の無矛盾性は証明できない",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # PA system as a large rounded box
        pa_y = 0.8
        pa_box = RoundedRectangle(
            width=7.0,
            height=2.6,
            corner_radius=0.25,
            color=ACCENT_CYAN,
            stroke_width=3,
            fill_opacity=0.08,
            fill_color=ACCENT_CYAN,
        )
        pa_box.move_to(np.array([0, pa_y, 0]))

        # Label PA above the box (header style) so the long text doesn't
        # overflow the box's left edge.
        pa_label = Text(
            "ペアノ算術 PA",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        pa_label.move_to(np.array([0, pa_y + 1.6, 0]))

        # Inside the PA box: a smaller Cons(PA) box
        cons_box_x = 1.5
        cons_box_y = pa_y + 0.1
        cons_box = RoundedRectangle(
            width=2.6,
            height=1.0,
            corner_radius=0.12,
            color=ACCENT_PINK,
            stroke_width=2.5,
            fill_opacity=0.15,
            fill_color=ACCENT_PINK,
        )
        cons_box.move_to(np.array([cons_box_x, cons_box_y, 0]))

        cons_tex = MathTex(r"\mathrm{Cons}(\mathrm{PA})", font_size=32, color=TEXT_WHITE)
        cons_tex.move_to(np.array([cons_box_x, cons_box_y + 0.15, 0]))

        cons_jp = Text(
            "PAは無矛盾",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        cons_jp.move_to(np.array([cons_box_x, cons_box_y - 0.25, 0]))

        # Arrow from PA axioms (left) to Cons(PA) (right) attempting proof
        # Goes inside the PA box
        arrow_start = np.array([-2.0, pa_y + 0.1, 0])
        arrow_end = np.array([cons_box_x - 1.4, pa_y + 0.1, 0])
        proof_arrow = Arrow(
            start=arrow_start,
            end=arrow_end,
            color=ACCENT_GOLD,
            buff=0.1,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.18,
        )

        proof_label = Text(
            "証明？",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        proof_label.move_to(
            np.array(
                [
                    (arrow_start[0] + arrow_end[0]) / 2,
                    pa_y + 0.5,
                    0,
                ]
            )
        )

        # X mark on top of the arrow (showing proof fails)
        cross = Cross(
            stroke_color=ACCENT_PINK,
            stroke_width=6,
        ).scale(0.35)
        cross.move_to(
            np.array(
                [
                    (arrow_start[0] + arrow_end[0]) / 2,
                    pa_y + 0.05,
                    0,
                ]
            )
        )

        # Bottom formula: PA ⊬ Cons(PA)
        bottom_formula = MathTex(
            r"\mathrm{PA} \;\nvdash\; \mathrm{Cons}(\mathrm{PA})",
            font_size=44,
            color=ACCENT_PINK,
        )
        bottom_formula.move_to(np.array([0, -1.2, 0]))

        # Bottom caption
        bottom_note = Text(
            "体系は自分自身の無矛盾性を証明できない",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        bottom_note.move_to(np.array([0, -1.85, 0]))

        # Animate
        self.play(FadeIn(title), run_time=0.5)
        self.play(FadeIn(pa_box), FadeIn(pa_label), run_time=0.7)
        self.play(FadeIn(cons_box), FadeIn(cons_tex), FadeIn(cons_jp), run_time=0.7)
        self.play(FadeIn(proof_arrow), FadeIn(proof_label), run_time=0.7)
        self.play(FadeIn(cross), run_time=0.5)
        self.play(FadeIn(bottom_formula), run_time=0.7)
        self.play(FadeIn(bottom_note), run_time=0.6)

        anim_overhead = 0.5 + 0.7 + 0.7 + 0.7 + 0.5 + 0.7 + 0.6
        self.wait(max(1.0, duration - anim_overhead))
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "hilbert_program_collapse": {"people": [], "years": []},
    "second_undecidable": {"people": [], "years": []},
}



# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "hilbert_program_collapse": {
        "class": "IncompletenessConsequence",
        "params": {"mode": "hilbert_program_collapse"},
        "description": "Three pillars (completeness/consistency/decidability) fall",
    },
    "second_undecidable": {
        "class": "IncompletenessConsequence",
        "params": {"mode": "second_undecidable"},
        "description": "PA system cannot prove its own consistency Cons(PA)",
    },
}
