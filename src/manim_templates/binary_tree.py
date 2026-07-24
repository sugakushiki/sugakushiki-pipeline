"""
binary_tree.py - Binary tree / 20 questions visualization for 数学史記

Visualizes how binary questions efficiently narrow down possibilities,
illustrating the concept of information content = log₂(N).

Modes:
    questions - Binary tree: 8 choices narrowed by 3 yes/no questions.
                Tree grows level by level with FadeIn.
                Fixed params: 8 choices (A-H), depth 3, result = 3 bits
    encoding  - Variable-length encoding: frequent chars get short codes,
                rare chars get long codes.
                Fixed params: 4 chars (A=50%, B=25%, C=15%, D=10%),
                fixed codes (00,01,10,11), variable codes (0,10,110,111)

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Circle,
    FadeIn,
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


class BinaryTree(Scene):
    """Visualize binary search / information content."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "questions")
        self._duration = params.get("duration", 25)

        if mode == "encoding":
            self.build_encoding()
        else:
            self.build_questions()

    # -------------------------------------------------------------------
    # Mode: questions
    # -------------------------------------------------------------------
    def build_questions(self):
        """Binary tree: 8 choices → 3 questions to identify."""
        dur = self._duration
        anim_time = 8.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "20の質問ゲーム ── 二分探索",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Build a depth-3 binary tree (root + 3 levels, 8 leaves)
        # Positions
        node_radius = 0.15
        root_pos = UP * 2.8
        level_gap_y = 1.2
        # x_spread at each level (root, L1, L2, L3)
        spreads = [0, 3.2, 1.6, 0.7]

        # Generate tree nodes level by level
        levels = []
        # Level 0: root
        levels.append([root_pos])
        # Level 1
        l1 = []
        for px in levels[0]:
            l1.append(px + DOWN * level_gap_y + LEFT * spreads[1])
            l1.append(px + DOWN * level_gap_y + RIGHT * spreads[1])
        levels.append(l1)
        # Level 2
        l2 = []
        for px in levels[1]:
            l2.append(px + DOWN * level_gap_y + LEFT * spreads[2])
            l2.append(px + DOWN * level_gap_y + RIGHT * spreads[2])
        levels.append(l2)
        # Level 3 (leaves)
        l3 = []
        for px in levels[2]:
            l3.append(px + DOWN * level_gap_y + LEFT * spreads[3])
            l3.append(px + DOWN * level_gap_y + RIGHT * spreads[3])
        levels.append(l3)

        # Leaf labels (8 items)
        leaf_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]

        # Draw level by level
        all_circles = []
        all_edges = []

        for level_idx, positions in enumerate(levels):
            level_circles = VGroup()
            level_edges = VGroup()

            for i, pos in enumerate(positions):
                c = Circle(
                    radius=node_radius,
                    color=ACCENT_CYAN if level_idx < 3 else ACCENT_GOLD,
                    fill_color=BG_COLOR,
                    fill_opacity=0.9,
                    stroke_width=2,
                )
                c.move_to(pos)

                if level_idx == 3:
                    # Leaf: add label
                    lbl = Text(
                        leaf_labels[i],
                        font=FONT,
                        font_size=14,
                        color=ACCENT_GOLD,
                    )
                    lbl.move_to(pos)
                    level_circles.add(VGroup(c, lbl))
                else:
                    q_mark = Text(
                        "?",
                        font=FONT,
                        font_size=14,
                        color=ACCENT_CYAN,
                    )
                    q_mark.move_to(pos)
                    level_circles.add(VGroup(c, q_mark))

                # Edge from parent
                if level_idx > 0:
                    parent_idx = i // 2
                    parent_pos = levels[level_idx - 1][parent_idx]
                    edge = Line(
                        parent_pos + DOWN * node_radius,
                        pos + UP * node_radius,
                        color=TEXT_DIM,
                        stroke_width=1.5,
                    )
                    level_edges.add(edge)

            all_circles.append(level_circles)
            all_edges.append(level_edges)

        # Animate: root first, then each level
        self.play(FadeIn(all_circles[0]), run_time=0.6)
        self.wait(0.5 * ws)

        for level_idx in range(1, 4):
            self.play(
                FadeIn(all_edges[level_idx]),
                FadeIn(all_circles[level_idx]),
                run_time=1.0,
            )
            # Level label
            q_num = Text(
                f"質問{level_idx}",
                font=FONT,
                font_size=18,
                color=TEXT_DIM,
            )
            q_num.shift(LEFT * 6.5 + levels[level_idx][0][1] * UP)
            self.play(FadeIn(q_num), run_time=0.3)
            self.wait(0.8 * ws)

        # Result annotation
        result = MathTex(
            r"8 = 2^3 \quad \Rightarrow \quad 3 \text{ bit}",
            font_size=36,
            color=ACCENT_GOLD,
        )
        result.move_to(DOWN * 1.8)
        self.play(FadeIn(result), run_time=0.8)
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: encoding
    # -------------------------------------------------------------------
    def build_encoding(self):
        """Variable-length encoding comparison."""
        dur = self._duration
        anim_time = 6.0
        default_wait_total = 5.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "頻度に応じた符号長",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Data: char, frequency, fixed code, variable code
        chars = [
            ("A", 0.50, "00", "0"),
            ("B", 0.25, "01", "10"),
            ("C", 0.15, "10", "110"),
            ("D", 0.10, "11", "111"),
        ]

        # Header row
        headers = VGroup()
        col_positions = [-3.5, -1.8, 0.0, 2.0, 4.0]
        header_texts = ["文字", "頻度", "固定長", "可変長", "節約"]
        for i, ht in enumerate(header_texts):
            h = Text(ht, font=FONT, font_size=22, color=ACCENT_GOLD)
            h.move_to(RIGHT * col_positions[i] + UP * 1.8)
            headers.add(h)

        sep_line = Line(
            LEFT * 5.5 + UP * 1.5,
            RIGHT * 5.5 + UP * 1.5,
            color=TEXT_DIM,
            stroke_width=1,
        )

        self.play(FadeIn(headers), FadeIn(sep_line), run_time=0.5)

        # Data rows
        for row_idx, (char, freq, fixed, variable) in enumerate(chars):
            y_pos = 0.8 - row_idx * 0.8
            row_elements = VGroup()

            t_char = Text(char, font=FONT, font_size=24, color=TEXT_WHITE)
            t_char.move_to(RIGHT * col_positions[0] + UP * y_pos)

            t_freq = Text(f"{freq:.0%}", font=FONT, font_size=24, color=TEXT_DIM)
            t_freq.move_to(RIGHT * col_positions[1] + UP * y_pos)

            t_fixed = Text(fixed, font=FONT, font_size=24, color=TEXT_DIM)
            t_fixed.move_to(RIGHT * col_positions[2] + UP * y_pos)

            var_color = ACCENT_CYAN if len(variable) <= len(fixed) else ACCENT_PINK
            t_var = Text(variable, font=FONT, font_size=24, color=var_color)
            t_var.move_to(RIGHT * col_positions[3] + UP * y_pos)

            saving = len(fixed) - len(variable)
            saving_text = f"{saving:+d}" if saving != 0 else "0"
            save_color = ACCENT_CYAN if saving > 0 else (ACCENT_PINK if saving < 0 else TEXT_DIM)
            t_save = Text(saving_text, font=FONT, font_size=24, color=save_color)
            t_save.move_to(RIGHT * col_positions[4] + UP * y_pos)

            row_elements.add(t_char, t_freq, t_fixed, t_var, t_save)
            self.play(FadeIn(row_elements), run_time=0.6)
            self.wait(0.3 * ws)

        self.wait(1.0 * ws)

        # Bottom note
        note = Text(
            "頻度の高い文字に短い符号 = 平均符号長を最小化",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "questions": {"people": [], "years": []},
    "encoding": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
SCENES = {
    "questions": BinaryTree,
    "encoding": BinaryTree,
}
