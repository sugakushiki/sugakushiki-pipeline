"""
turing_machine.py - Turing machine visualization for 数学史記

Visualizes a Turing machine's tape, head, and state transitions.

Modes:
    tape      - Basic tape operation: binary increment (0101 + 1 = 0110).
                Head moves left, reads/writes symbols, state transitions shown.
    universal - Universal Turing Machine concept: shows how a program
                description on tape can simulate another machine.

Params:
    mode: "tape" or "universal" (default: "tape")
    duration: target duration in seconds

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    Arrow,
    FadeIn,
    FadeOut,
    Indicate,
    Rectangle,
    Scene,
    Text,
    Triangle,
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
    load_params,
)

config.background_color = BG_COLOR

TAPE_CELL_W = 0.8
TAPE_CELL_H = 0.8
HEAD_COLOR = ACCENT_PINK
STATE_COLOR = ACCENT_GOLD
SYMBOL_COLOR = ACCENT_CYAN


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class TuringMachine(Scene):
    """Turing machine tape and state transition visualization."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "tape")
        self._duration = params.get("duration", 30)

        if mode == "universal":
            self._build_universal()
        else:
            self._build_tape()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_tape(self, symbols, center_idx, y=0.5):
        """Create a row of tape cells with symbols."""
        cells = VGroup()
        texts = VGroup()
        n = len(symbols)
        start_x = -(n / 2 - 0.5) * TAPE_CELL_W
        for i, s in enumerate(symbols):
            rect = Rectangle(
                width=TAPE_CELL_W,
                height=TAPE_CELL_H,
                stroke_color=TEXT_DIM,
                stroke_width=2,
            ).move_to([start_x + i * TAPE_CELL_W, y, 0])
            cells.add(rect)
            txt = Text(str(s), font=FONT, font_size=32, color=SYMBOL_COLOR)
            txt.move_to(rect.get_center())
            texts.add(txt)
        return cells, texts

    def _make_head(self, tape_cells, idx, state_label="q0"):
        """Create head triangle + state label below tape."""
        cell = tape_cells[idx]
        tri = (
            Triangle(
                fill_color=HEAD_COLOR,
                fill_opacity=0.9,
                stroke_width=0,
            )
            .scale(0.25)
            .next_to(cell, DOWN, buff=0.15)
        )
        st = Text(state_label, font=FONT, font_size=24, color=STATE_COLOR)
        st.next_to(tri, DOWN, buff=0.1)
        return VGroup(tri, st)

    # ------------------------------------------------------------------
    # Mode: tape — binary increment
    # ------------------------------------------------------------------
    def _build_tape(self):
        duration = self._duration

        title = Text(
            "チューリングマシン",
            font=FONT,
            font_size=36,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)
        subtitle = Text(
            "二進数 0101 に 1 を加える",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        ).next_to(title, DOWN, buff=0.2)

        # Initial tape: _ 0 1 0 1 _  (blanks on edges)
        symbols = ["", "0", "1", "0", "1", ""]
        cells, texts = self._make_tape(symbols, center_idx=3, y=0.5)
        head = self._make_head(cells, 4, "q0")

        # Steps: head at idx 4 (rightmost '1')
        # Step 1: read '1', write '0', move left, stay q0
        # Step 2: read '0', write '1', halt (q_halt)
        # Result: _ 0 1 1 0 _

        steps = [
            # (head_idx, read, write, new_state, direction_label)
            (4, "1", "0", "q0", "LEFT"),
            (3, "0", "1", "q_halt", "HALT"),
        ]

        anim_time = 6.0
        default_wait_total = 8.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        # Show title + tape + head
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.8)
        self.play(FadeIn(cells), FadeIn(texts), run_time=0.6)
        self.play(FadeIn(head), run_time=0.5)
        self.wait(1.5 * ws)

        # Rule display area
        rule_area_y = -1.8
        rule_label = Text(
            "規則:",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        ).move_to([-3.5, rule_area_y, 0])
        self.play(FadeIn(rule_label), run_time=0.3)

        prev_rule_text = None
        current_head_idx = 4

        for step_i, (h_idx, read_s, write_s, new_state, direction) in enumerate(steps):
            # Show rule
            if direction == "HALT":
                dir_ja = "停止"
            else:
                dir_ja = "左へ"
            rule_str = f"({read_s}, q) -> ({write_s}, {dir_ja})"
            rule_text = Text(
                rule_str,
                font=FONT,
                font_size=22,
                color=ACCENT_CYAN,
            ).next_to(rule_label, RIGHT, buff=0.3)

            if prev_rule_text:
                self.play(
                    FadeOut(prev_rule_text),
                    FadeIn(rule_text),
                    run_time=0.4,
                )
            else:
                self.play(FadeIn(rule_text), run_time=0.4)
            prev_rule_text = rule_text

            # Highlight current cell
            self.play(
                Indicate(cells[h_idx], color=HEAD_COLOR, scale_factor=1.1),
                run_time=0.5,
            )

            # Write new symbol
            new_txt = Text(
                write_s,
                font=FONT,
                font_size=32,
                color=ACCENT_PINK,
            ).move_to(cells[h_idx].get_center())
            self.play(
                FadeOut(texts[h_idx]),
                FadeIn(new_txt),
                run_time=0.5,
            )
            texts.submobjects[h_idx] = new_txt
            self.wait(0.5 * ws)

            # Move head (if not halt)
            if direction == "LEFT" and h_idx > 0:
                new_head = self._make_head(cells, h_idx - 1, new_state)
                self.play(
                    FadeOut(head),
                    FadeIn(new_head),
                    run_time=0.6,
                )
                head = new_head
                current_head_idx = h_idx - 1
            elif direction == "HALT":
                # Update state label
                new_head = self._make_head(cells, h_idx, new_state)
                self.play(
                    FadeOut(head),
                    FadeIn(new_head),
                    run_time=0.5,
                )
                head = new_head

            self.wait(1.0 * ws)

        # Show result
        result = Text(
            "結果: 0110 (= 6)",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        ).move_to([0, -1.8, 0])
        self.play(FadeIn(result), run_time=0.5)
        self.wait(max(duration - 8.0, 1.5))

    # ------------------------------------------------------------------
    # Mode: universal — Universal TM concept
    # ------------------------------------------------------------------
    def _build_universal(self):
        duration = self._duration

        title = Text(
            "万能チューリングマシン",
            font=FONT,
            font_size=36,
            color=ACCENT_GOLD,
        ).to_edge(UP, buff=0.4)

        anim_time = 5.0
        default_wait_total = 8.0
        ws = _calc_wait_scale(duration, anim_time, default_wait_total)

        self.play(FadeIn(title), run_time=0.6)
        self.wait(0.8 * ws)

        # Show Machine M description on tape
        tape_label_m = Text(
            "マシン M の規則",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).move_to([-3.0, 2.2, 0])

        # Small tape for M
        m_symbols = ["q0", "0->1", "R", "q1", "1->0", "L"]
        m_cells = VGroup()
        m_texts = VGroup()
        start_x = -4.5
        for i, s in enumerate(m_symbols):
            rect = Rectangle(
                width=1.0,
                height=0.55,
                stroke_color=TEXT_DIM,
                stroke_width=1.5,
            ).move_to([start_x + i * 1.0, 1.5, 0])
            m_cells.add(rect)
            txt = Text(s, font=FONT, font_size=16, color=ACCENT_CYAN)
            txt.move_to(rect.get_center())
            m_texts.add(txt)

        self.play(FadeIn(tape_label_m), FadeIn(m_cells), FadeIn(m_texts), run_time=0.8)
        self.wait(1.0 * ws)

        # Arrow down
        arrow_down = Arrow(
            start=[0, 0.9, 0],
            end=[0, 0.1, 0],
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        encode_label = Text(
            "テープに符号化",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        ).next_to(arrow_down, RIGHT, buff=0.3)
        self.play(FadeIn(arrow_down), FadeIn(encode_label), run_time=0.5)
        self.wait(0.5 * ws)

        # Universal TM tape
        u_label = Text(
            "万能マシン U のテープ",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).move_to([-2.5, 0.0, 0])

        u_symbols = ["[M]", "#", "0", "1", "0", "1"]
        u_cells = VGroup()
        u_texts = VGroup()
        start_x = -3.5
        for i, s in enumerate(u_symbols):
            w = 1.2 if i == 0 else 0.8
            rect = Rectangle(
                width=w,
                height=TAPE_CELL_H,
                stroke_color=ACCENT_GOLD if i == 0 else TEXT_DIM,
                stroke_width=2.5 if i == 0 else 1.5,
            ).move_to([start_x + (i * 0.9 if i > 0 else 0), -0.5, 0])
            if i > 0:
                rect.move_to([start_x + 0.6 + (i - 1) * 0.8, -0.5, 0])
            u_cells.add(rect)
            col = ACCENT_GOLD if i == 0 else SYMBOL_COLOR
            txt = Text(s, font=FONT, font_size=24 if i == 0 else 28, color=col)
            txt.move_to(rect.get_center())
            u_texts.add(txt)

        self.play(FadeIn(u_label), FadeIn(u_cells), FadeIn(u_texts), run_time=0.8)

        # Head for U
        u_head = self._make_head(u_cells, 0, "U")
        self.play(FadeIn(u_head), run_time=0.5)
        self.wait(1.0 * ws)

        # Key insight
        insight = Text(
            "プログラムもデータも同じテープ上に",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        ).move_to([0, -1.4, 0])
        sub_insight = Text(
            "= プログラム内蔵式コンピュータの原理",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        ).next_to(insight, DOWN, buff=0.15)
        self.play(FadeIn(insight), run_time=0.5)
        self.play(FadeIn(sub_insight), run_time=0.4)
        self.wait(max(duration - 6.0, 1.5))
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "tape": {"people": [], "years": []},
    "universal": {"people": [], "years": []},
}



SCENES = {
    "tape": TuringMachine,
    "universal": TuringMachine,
}
