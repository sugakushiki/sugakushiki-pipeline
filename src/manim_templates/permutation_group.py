"""
permutation_group: 置換群S₃の元を矢印図で表示し、置換の合成をアニメーションで可視化する。

モード:
- s3_elements: S₃の6つの元を矢印図で一覧表示する
- composition: 2つの置換の合成 σ_1∘σ_3 = σ_4 を段階的にアニメーションし、「群の性質」を示す
- commutative_compare: σ_1∘σ_3 と σ_3∘σ_1 を並べて結果が異なることを示す（S_3が非可換）。
                      後段で σ・τ = τ・σ となる場合（アーベル方程式）に接続する。
                      Fixed params: σ_1=[1,0,2], σ_3=[0,2,1], σ_1∘σ_3=σ_4=[1,2,0]=(1 ω ω²),
                      σ_3∘σ_1=σ_5=[2,0,1]=(1 ω² ω). 約50秒。
"""

import numpy as np
from manim import *

BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
FONT = "BIZ UDMincho"
ROOT_COLORS = [GOLD, CYAN, PINK]

# Subtitle safe zone: y > -2.0 (Manim scene uses 240px bottom margin)
SUBTITLE_Y_LIMIT = -2.0


def get_duration(mode):
    defaults = {"s3_elements": 25, "composition": 40, "commutative_compare": 50}
    return defaults.get(mode, 35)


# Red-ish color for ≠ symbol in commutative_compare mode
NEQ_COLOR = "#e74c3c"


def make_perm_diagram(mapping, center=ORIGIN, scale_factor=0.65, label_text=None):
    root_labels = [r"1", r"\omega", r"\omega^2"]
    src_group, tgt_group, arrows = VGroup(), VGroup(), VGroup()
    y_positions = [0.7, 0, -0.7]
    sf = scale_factor

    for i in range(3):
        y = y_positions[i] * sf
        src_dot = Dot(
            center + LEFT * 0.9 * sf + UP * y, radius=0.07 * sf, color=ROOT_COLORS[i], z_index=2
        )
        src_label = MathTex(root_labels[i], font_size=int(28 * sf / 0.65), color=ROOT_COLORS[i])
        src_label.next_to(src_dot, LEFT, buff=0.12 * sf)
        src_group.add(VGroup(src_dot, src_label))

        j = mapping[i]
        arrow = Arrow(
            start=src_dot.get_center() + RIGHT * 0.1 * sf,
            end=center + RIGHT * 0.75 * sf + UP * y_positions[j] * sf,
            buff=0.05 * sf,
            stroke_width=2.5,
            color=ROOT_COLORS[i],
            max_tip_length_to_length_ratio=0.2,
        )
        arrows.add(arrow)

    for j in range(3):
        y = y_positions[j] * sf
        tgt_dot = Dot(
            center + RIGHT * 0.9 * sf + UP * y, radius=0.07 * sf, color=ROOT_COLORS[j], z_index=2
        )
        tgt_label = MathTex(root_labels[j], font_size=int(28 * sf / 0.65), color=ROOT_COLORS[j])
        tgt_label.next_to(tgt_dot, RIGHT, buff=0.12 * sf)
        tgt_group.add(VGroup(tgt_dot, tgt_label))

    result = VGroup(src_group, tgt_group, arrows)
    if label_text is not None:
        label = MathTex(label_text, font_size=int(30 * sf / 0.65), color=WHITE)
        label.next_to(result, UP, buff=0.18 * sf)
        result.add(label)
    return result


class PermutationGroupS3Elements(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("s3_elements")

        s3_label = MathTex(r"S_3", font_size=52, color=GOLD)
        s3_label.to_edge(UP, buff=0.5)
        self.play(FadeIn(s3_label), run_time=0.5)

        perms = [
            ([0, 1, 2], r"e"),
            ([1, 0, 2], r"\sigma_1"),
            ([2, 1, 0], r"\sigma_2"),
            ([0, 2, 1], r"\sigma_3"),
            ([1, 2, 0], r"\sigma_4"),
            ([2, 0, 1], r"\sigma_5"),
        ]
        cycle_notations = [
            r"\mathrm{id}",
            r"(1\;\omega)",
            r"(1\;\omega^2)",
            r"(\omega\;\omega^2)",
            r"(1\;\omega\;\omega^2)",
            r"(1\;\omega^2\;\omega)",
        ]

        # 2 rows x 3 columns — shifted up to stay above subtitle zone
        # Top row center: y=1.0, bottom row center: y=-1.0
        positions = [
            LEFT * 3.8 + UP * 1.0,
            ORIGIN + UP * 1.0,
            RIGHT * 3.8 + UP * 1.0,
            LEFT * 3.8 + DOWN * 1.0,
            ORIGIN + DOWN * 1.0,
            RIGHT * 3.8 + DOWN * 1.0,
        ]

        diagrams = VGroup()
        for i, (mapping, label) in enumerate(perms):
            diag = make_perm_diagram(
                mapping, center=positions[i], scale_factor=0.5, label_text=label
            )
            cycle = MathTex(cycle_notations[i], font_size=20, color=WHITE).set_opacity(0.7)
            cycle.next_to(diag, DOWN, buff=0.1)
            diagrams.add(VGroup(diag, cycle))

        for i in range(0, 6, 2):
            pair = [diagrams[i]]
            if i + 1 < 6:
                pair.append(diagrams[i + 1])
            self.play(*[FadeIn(d) for d in pair], run_time=0.7)
            self.wait(0.5)
        self.wait(0.5)

        elapsed = 0.5 + (0.7 + 0.5) * 3 + 0.5
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class PermutationGroupComposition(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("composition")

        col_left, col_mid, col_right = LEFT * 4.0, ORIGIN, RIGHT * 4.0

        # Headers at top
        header_l = MathTex(r"\sigma_3", font_size=42, color=CYAN)
        header_l.move_to(col_left + UP * 3.0)
        subtitle_l = MathTex(r"(\omega\;\omega^2)", font_size=28, color=CYAN).set_opacity(0.7)
        subtitle_l.next_to(header_l, DOWN, buff=0.1)

        header_m = MathTex(r"\sigma_1", font_size=42, color=PINK)
        header_m.move_to(col_mid + UP * 3.0)
        subtitle_m = MathTex(r"(1\;\omega)", font_size=28, color=PINK).set_opacity(0.7)
        subtitle_m.next_to(header_m, DOWN, buff=0.1)

        header_r = MathTex(r"\sigma_1 \circ \sigma_3", font_size=42, color=GOLD)
        header_r.move_to(col_right + UP * 3.0)
        subtitle_r = MathTex(r"= \;?", font_size=32, color=GOLD)
        subtitle_r.next_to(header_r, DOWN, buff=0.1)

        then1 = MathTex(r"\Rightarrow", font_size=42, color=WHITE).set_opacity(0.5)
        then1.move_to((col_left + col_mid) / 2 + UP * 0.8)
        then2 = MathTex(r"=", font_size=42, color=WHITE).set_opacity(0.5)
        then2.move_to((col_mid + col_right) / 2 + UP * 0.8)

        self.play(
            FadeIn(header_l),
            FadeIn(subtitle_l),
            FadeIn(header_m),
            FadeIn(subtitle_m),
            FadeIn(header_r),
            FadeIn(subtitle_r),
            FadeIn(then1),
            FadeIn(then2),
            run_time=0.8,
        )

        # Diagrams centered at y=0.8
        diag_l = make_perm_diagram([0, 2, 1], center=col_left + UP * 0.8, scale_factor=0.65)
        diag_m = make_perm_diagram([1, 0, 2], center=col_mid + UP * 0.8, scale_factor=0.65)

        self.play(FadeIn(diag_l), run_time=0.7)
        self.wait(0.8)
        self.play(FadeIn(diag_m), run_time=0.7)
        self.wait(0.8)

        # Trace composition — placed at y=-0.5 to y=-1.5 (above subtitle zone)
        trace_texts = [
            (r"1 \xrightarrow{\sigma_3} 1 \xrightarrow{\sigma_1} \omega", GOLD),
            (r"\omega \xrightarrow{\sigma_3} \omega^2 \xrightarrow{\sigma_1} \omega^2", CYAN),
            (r"\omega^2 \xrightarrow{\sigma_3} \omega \xrightarrow{\sigma_1} 1", PINK),
        ]
        for i, (tex, color) in enumerate(trace_texts):
            trace = MathTex(tex, font_size=30, color=color)
            trace.move_to(DOWN * 0.5 + DOWN * i * 0.5)
            self.play(FadeIn(trace), run_time=0.5)
            self.wait(0.6)
        self.wait(0.5)

        # Reveal result
        diag_r = make_perm_diagram([1, 2, 0], center=col_right + UP * 0.8, scale_factor=0.65)
        answer = MathTex(r"= \sigma_4 = (1\;\omega\;\omega^2)", font_size=28, color=GOLD)
        answer.next_to(header_r, DOWN, buff=0.1)

        self.play(FadeIn(diag_r), FadeOut(subtitle_r), FadeIn(answer), run_time=0.8)
        self.play(header_r.animate.scale(1.2), run_time=0.3)
        self.play(header_r.animate.scale(1 / 1.2), run_time=0.3)

        elapsed = 0.8 + 0.7 + 0.8 + 0.7 + 0.8 + (0.5 + 0.6) * 3 + 0.5 + 0.8 + 0.6
        remaining = max(0, duration - elapsed - 1.0)
        if remaining > 0:
            self.wait(remaining)
        # End FadeOut removed: leaves the last frame visible for FFmpeg
        # to pad when audio exceeds animation length. Scene transitions
        # are handled at video_assembler time, not inside Manim.


class PermutationGroupCommutativeCompare(Scene):
    """非可換性の対比とアーベル方程式の概念。

    左に σ_1∘σ_3 = σ_4、右に σ_3∘σ_1 = σ_5 を並べ、結果が異なる（≠）ことで
    S_3 が非可換であることを示す。後段で σ・τ = τ・σ となる場合（可換）が
    「アーベル方程式」であることを画面に示す。
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        duration = get_duration("commutative_compare")
        # Allow override via _manim_params.json (visual_generator integration)
        try:
            import json
            import os

            params_path = "_manim_params.json"
            if os.path.exists(params_path):
                with open(params_path, encoding="utf-8") as f:
                    params = json.load(f)
                duration = params.get("duration", duration)
        except Exception:
            pass

        # ===== Phase 1 layout =====
        # Title (y=3.0)
        title = Text(
            "置換の合成は順序によって変わるか？",
            font=FONT,
            font_size=30,
            color=GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        col_left_x = -3.5
        col_right_x = 3.5

        # Left column: σ_1 ∘ σ_3 = σ_4
        header_l = MathTex(r"\sigma_1 \circ \sigma_3", font_size=40, color=CYAN)
        header_l.move_to(np.array([col_left_x, 2.2, 0]))

        # σ_1 ∘ σ_3 = [1, 2, 0] (apply σ_3 first, then σ_1)
        diag_l = make_perm_diagram(
            [1, 2, 0],
            center=np.array([col_left_x, 0.85, 0]),
            scale_factor=0.55,
        )

        result_l = MathTex(r"= \sigma_4 = (1\;\omega\;\omega^2)", font_size=26, color=GOLD)
        result_l.move_to(np.array([col_left_x, -0.35, 0]))

        # Right column: σ_3 ∘ σ_1 = σ_5
        header_r = MathTex(r"\sigma_3 \circ \sigma_1", font_size=40, color=PINK)
        header_r.move_to(np.array([col_right_x, 2.2, 0]))

        # σ_3 ∘ σ_1 = [2, 0, 1] (apply σ_1 first, then σ_3)
        diag_r = make_perm_diagram(
            [2, 0, 1],
            center=np.array([col_right_x, 0.85, 0]),
            scale_factor=0.55,
        )

        result_r = MathTex(r"= \sigma_5 = (1\;\omega^2\;\omega)", font_size=26, color=GOLD)
        result_r.move_to(np.array([col_right_x, -0.35, 0]))

        # Center ≠ symbol
        neq_symbol = MathTex(r"\neq", font_size=80, color=NEQ_COLOR)
        neq_symbol.move_to(np.array([0, 0.85, 0]))

        # Bottom conclusion (y = -1.5, safely above subtitle zone -2.0)
        conclusion = Text(
            "順序を変えると結果が違う ── 群は非可換",
            font=FONT,
            font_size=24,
            color=WHITE,
        )
        conclusion.move_to(np.array([0, -1.55, 0]))

        # ===== Phase 1 animation: build up =====
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(header_l), FadeIn(header_r), run_time=0.6)
        self.wait(0.3)
        self.play(FadeIn(diag_l), run_time=0.7)
        self.play(FadeIn(result_l), run_time=0.5)
        self.wait(0.4)
        self.play(FadeIn(diag_r), run_time=0.7)
        self.play(FadeIn(result_r), run_time=0.5)
        self.wait(0.4)
        self.play(FadeIn(neq_symbol), run_time=0.6)
        self.play(neq_symbol.animate.scale(1.15), run_time=0.3)
        self.play(neq_symbol.animate.scale(1 / 1.15), run_time=0.3)
        self.wait(0.3)
        self.play(FadeIn(conclusion), run_time=0.6)

        elapsed_phase1 = (
            0.6 + 0.6 + 0.3 + 0.7 + 0.5 + 0.4 + 0.7 + 0.5 + 0.4 + 0.6 + 0.3 + 0.3 + 0.3 + 0.6
        )

        # Reserve time for Phase 3
        phase3_budget = 12.0
        # Phase 2: hold the comparison
        hold_phase = max(1.0, duration - elapsed_phase1 - phase3_budget - 1.0)
        self.wait(hold_phase)

        # ===== Phase 3: transition to commutative case (Abelian equation) =====
        phase1_objs = VGroup(
            title,
            header_l,
            header_r,
            diag_l,
            result_l,
            diag_r,
            result_r,
            neq_symbol,
            conclusion,
        )
        self.play(FadeOut(phase1_objs), run_time=0.7)

        # Commutative formula
        commute_eq = MathTex(
            r"\sigma \cdot \tau = \tau \cdot \sigma",
            font_size=72,
            color=CYAN,
        )
        commute_eq.move_to(np.array([0, 0.7, 0]))

        abelian_text = Text(
            "可換であれば代数的に解ける ── アーベル方程式",
            font=FONT,
            font_size=28,
            color=GOLD,
        )
        abelian_text.move_to(np.array([0, -1.0, 0]))

        self.play(FadeIn(commute_eq), run_time=0.8)
        self.wait(0.6)
        self.play(FadeIn(abelian_text), run_time=0.7)

        # Hold to end of duration (no end-of-scene FadeOut so last frame is preserved)
        elapsed_phase3 = 0.7 + 0.8 + 0.6 + 0.7
        remaining_phase3 = max(0.5, phase3_budget - elapsed_phase3)
        self.wait(remaining_phase3)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "s3_elements": {"people": [], "years": []},
    "composition": {"people": [], "years": []},
    "commutative_compare": {"people": [], "years": []},
}



SCENES = {
    "s3_elements": PermutationGroupS3Elements,
    "composition": PermutationGroupComposition,
    "commutative_compare": PermutationGroupCommutativeCompare,
}
