"""
problem_of_points.py - Pascal-Fermat problem of points for 数学史記

Visualizes the problem of points (1654), the correspondence between
Pascal and Fermat that gave birth to probability theory.

The problem: Two players A and B each have equal chance of winning each
round. They agree that the first to win a certain number of rounds takes
the entire pot. The game is interrupted - how to divide the pot fairly?

Modes:
    tree        - Decision tree showing all possible continuations.
                  Fixed params: A needs 1 more win, B needs 2 more wins.
                  4 possible paths (AA,AB,BA,BB): A wins 3, B wins 1.
    calculation - Shows the fair division calculation.
                  A gets 3/4 of the pot, B gets 1/4.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 014 (Fermat), math pillar 3
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
    Arrow,
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


class ProblemOfPoints(Scene):
    """Problem of Points visualization. Mode-branching scene.

    Modes:
        tree (default)        - decision tree of all possible game continuations

        calculation           - fair division: A gets 3/4, B gets 1/4

        tree_with_expectation - 決定木 + 期待値計算 (E[A]=48, E[B]=16) 明示。
                                ある回 Pascal 回 math_14 用、Fermat 列挙ブロック削除。
        expectation_comparison - フェルマー方式 vs パスカル方式の対比 + 期待値の
                                 一般式 E[X] = Σ p_i x_i + 「期待値の概念誕生」。
                                 ある回 Pascal 回 math_15 用、新規 mode。
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "tree")

        if mode == "calculation":
            self.build_calculation()
        elif mode == "tree_with_expectation":
            self.build_tree_with_expectation()
        elif mode == "expectation_comparison":
            self.build_expectation_comparison()
        else:
            self.build_tree()

    # -------------------------------------------------------------------
    # Mode: tree
    # -------------------------------------------------------------------
    def build_tree(self):
        """Decision tree for the problem of points.

        Setup: A needs 1 more win, B needs 2 more wins.
        Maximum additional rounds = 2.

        Fermat's method: enumerate all 2^2 = 4 equally likely sequences:
        - AA: A wins round 1 → A wins (already needed just 1)
        - AB: A wins round 1 → A wins (already needed just 1)
        - BA: B wins round 1, A wins round 2 → A wins
        - BB: B wins both rounds → B wins
        Result: A wins 3/4, B wins 1/4.
        """
        duration = self._duration

        # Title
        title = Text("Problem of Points (1654)", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        # Setup description
        setup = VGroup(
            Text("A: あと1勝で賞金", font=FONT, font_size=20, color=ACCENT_CYAN),
            Text("B: あと2勝で賞金", font=FONT, font_size=20, color=ACCENT_PINK),
        )
        setup.arrange(RIGHT, buff=0.8)
        setup.next_to(title, DOWN, buff=0.35)
        self.play(FadeIn(setup), run_time=0.4)

        # Tree structure
        # Root: current state
        root_x, root_y = -4.5, 1.0

        # Level labels
        round1_label = Text("Round 1", font=FONT, font_size=16, color=TEXT_DIM)
        round1_label.move_to([-5.5, 0.0, 0])
        round2_label = Text("Round 2", font=FONT, font_size=16, color=TEXT_DIM)
        round2_label.move_to([-5.5, -1.2, 0])

        # Root node
        root = Text("Start", font=FONT, font_size=18, color=TEXT_WHITE)
        root.move_to([root_x, root_y, 0])

        self.play(FadeIn(root), FadeIn(round1_label), FadeIn(round2_label), run_time=0.3)

        # Round 1 branches
        # A wins round 1 → A wins the game
        r1_a_x, r1_a_y = -2.5, 0.3
        r1_b_x, r1_b_y = -2.5, -0.5

        r1_a_label = Text("A wins", font=FONT, font_size=16, color=ACCENT_CYAN)
        r1_a_label.move_to([r1_a_x, r1_a_y, 0])

        r1_b_label = Text("B wins", font=FONT, font_size=16, color=ACCENT_PINK)
        r1_b_label.move_to([r1_b_x, r1_b_y, 0])

        arrow_r1a = Arrow(
            root.get_right(),
            r1_a_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_r1b = Arrow(
            root.get_right(),
            r1_b_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )

        self.play(
            FadeIn(arrow_r1a),
            FadeIn(r1_a_label),
            FadeIn(arrow_r1b),
            FadeIn(r1_b_label),
            run_time=0.5,
        )

        # A wins round 1 → A already has enough → A wins! (for both AA and AB)
        result_aa = Text("A wins!", font=FONT, font_size=18, color=ACCENT_GOLD)
        result_aa.move_to([0.5, 0.3, 0])
        result_aa_rect = SurroundingRectangle(
            result_aa, color=ACCENT_GOLD, buff=0.08, stroke_width=1.5
        )
        arrow_aa = Arrow(
            r1_a_label.get_right(),
            result_aa.get_left(),
            color=ACCENT_GOLD,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        note_aa = Text("(Aはあと1勝で足りた)", font=FONT, font_size=14, color=TEXT_DIM)
        note_aa.next_to(result_aa, RIGHT, buff=0.2)

        self.play(
            FadeIn(arrow_aa),
            FadeIn(result_aa),
            FadeIn(result_aa_rect),
            FadeIn(note_aa),
            run_time=0.5,
        )

        # B wins round 1 → need round 2: A needs 1, B needs 1
        mid_label = Text("A:1, B:1", font=FONT, font_size=14, color=TEXT_DIM)
        mid_label.next_to(r1_b_label, RIGHT, buff=0.3)

        self.play(FadeIn(mid_label), run_time=0.3)

        # Round 2 branches (only if B won round 1)
        r2_a_x, r2_a_y = 0.5, -0.2
        r2_b_x, r2_b_y = 0.5, -1.0

        r2_a_label = Text("A wins R2", font=FONT, font_size=16, color=ACCENT_CYAN)
        r2_a_label.move_to([r2_a_x, r2_a_y, 0])

        r2_b_label = Text("B wins R2", font=FONT, font_size=16, color=ACCENT_PINK)
        r2_b_label.move_to([r2_b_x, r2_b_y, 0])

        arrow_r2a = Arrow(
            mid_label.get_right(),
            r2_a_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_r2b = Arrow(
            mid_label.get_right(),
            r2_b_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )

        self.play(
            FadeIn(arrow_r2a),
            FadeIn(r2_a_label),
            FadeIn(arrow_r2b),
            FadeIn(r2_b_label),
            run_time=0.5,
        )

        # Round 2 results
        result_ba = Text("A wins!", font=FONT, font_size=18, color=ACCENT_GOLD)
        result_ba.move_to([3.5, -0.2, 0])
        result_ba_rect = SurroundingRectangle(
            result_ba, color=ACCENT_GOLD, buff=0.08, stroke_width=1.5
        )
        arrow_ba = Arrow(
            r2_a_label.get_right(),
            result_ba.get_left(),
            color=ACCENT_GOLD,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )

        result_bb = Text("B wins!", font=FONT, font_size=18, color=ACCENT_PINK)
        result_bb.move_to([3.5, -1.0, 0])
        result_bb_rect = SurroundingRectangle(
            result_bb, color=ACCENT_PINK, buff=0.08, stroke_width=1.5
        )
        arrow_bb = Arrow(
            r2_b_label.get_right(),
            result_bb.get_left(),
            color=ACCENT_PINK,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )

        self.play(
            FadeIn(arrow_ba),
            FadeIn(result_ba),
            FadeIn(result_ba_rect),
            FadeIn(arrow_bb),
            FadeIn(result_bb),
            FadeIn(result_bb_rect),
            run_time=0.5,
        )

        # Summary: count outcomes
        # Fermat's method: enumerate all 4 equally likely sequences of 2 rounds
        # AA→A, AB→A, BA→A, BB→B → A wins 3 out of 4
        summary_label = Text("Fermat:", font=FONT, font_size=18, color=ACCENT_GOLD)
        summary_label.move_to([-3.0, -1.4, 0])

        outcomes = MathTex(
            r"\underbrace{AA, AB, BA}_{A\text{ wins}} \quad "
            r"\underbrace{BB}_{B\text{ wins}}",
            font_size=22,
            color=TEXT_WHITE,
        )
        outcomes.next_to(summary_label, RIGHT, buff=0.3)

        self.play(FadeIn(summary_label), FadeIn(outcomes), run_time=0.5)

        # Division result (字幕クリアランス -2.0 内に収める)
        division = MathTex(r"A : B = 3 : 1", font_size=28, color=ACCENT_GOLD)
        division.move_to([0, -1.85, 0])
        div_rect = SurroundingRectangle(division, color=ACCENT_GOLD, buff=0.12, stroke_width=2)
        self.play(FadeIn(division), FadeIn(div_rect), run_time=0.5)

        self.wait(max(1, duration * 0.15))

    # -------------------------------------------------------------------
    # Mode: calculation
    # -------------------------------------------------------------------
    def build_calculation(self):
        """Fair division calculation: A gets 3/4, B gets 1/4.

        Shows how to count all possible continuations and compute
        the fair share of the prize pot.
        """
        duration = self._duration

        # Title
        title = Text("Fair Division", font=FONT, font_size=26, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        # Setup
        setup = VGroup(
            Text("A: あと1勝  B: あと2勝", font=FONT, font_size=22, color=TEXT_WHITE),
            Text("賞金: 64 pistoles", font=FONT, font_size=20, color=TEXT_DIM),
        )
        setup.arrange(DOWN, buff=0.2)
        setup.next_to(title, DOWN, buff=0.4)
        self.play(FadeIn(setup), run_time=0.4)

        # 全体を上にシフト（title/setup下に余裕があり、conclusionが字幕と被っていた）
        # 新レイアウト: step1_title=1.5, outcomes=0.9, step2=0.3, step3_title=-0.3,
        # division=-0.95, conclusion=-1.65（全て -2.0 クリアランス内）

        # Step 1: Count all possible outcomes
        step1_title = Text(
            "Step 1: 残り最大2回の結果を列挙", font=FONT, font_size=20, color=ACCENT_GOLD
        )
        step1_title.move_to([0, 1.5, 0])
        self.play(FadeIn(step1_title), run_time=0.3)

        outcomes = VGroup(
            MathTex(r"AA \rightarrow A", font_size=22, color=ACCENT_CYAN),
            MathTex(r"AB \rightarrow A", font_size=22, color=ACCENT_CYAN),
            MathTex(r"BA \rightarrow A", font_size=22, color=ACCENT_CYAN),
            MathTex(r"BB \rightarrow B", font_size=22, color=ACCENT_PINK),
        )
        outcomes.arrange(RIGHT, buff=0.5)
        outcomes.move_to([0, 0.9, 0])

        time_per = min(0.4, (duration * 0.15) / 4)
        for o in outcomes:
            self.play(FadeIn(o), run_time=time_per)

        # Step 2: Count
        step2 = VGroup(
            Text("A wins: 3/4", font=FONT, font_size=22, color=ACCENT_CYAN),
            Text("B wins: 1/4", font=FONT, font_size=22, color=ACCENT_PINK),
        )
        step2.arrange(RIGHT, buff=1.0)
        step2.move_to([0, 0.3, 0])
        self.play(FadeIn(step2), run_time=0.4)

        # Step 3: Divide the pot
        step3_title = Text("Step 2: 賞金を分配", font=FONT, font_size=20, color=ACCENT_GOLD)
        step3_title.move_to([0, -0.3, 0])
        self.play(FadeIn(step3_title), run_time=0.3)

        division = VGroup(
            MathTex(r"A: \frac{3}{4} \times 64 = 48", font_size=28, color=ACCENT_CYAN),
            MathTex(r"B: \frac{1}{4} \times 64 = 16", font_size=28, color=ACCENT_PINK),
        )
        division.arrange(RIGHT, buff=1.0)
        division.move_to([0, -0.95, 0])
        self.play(FadeIn(division), run_time=0.5)

        # Conclusion
        conclusion = Text("= 確率論の誕生", font=FONT, font_size=24, color=ACCENT_GOLD)
        conclusion.move_to([0, -1.65, 0])
        self.play(FadeIn(conclusion), run_time=0.5)

        self.wait(max(1, duration * 0.15))

    # -------------------------------------------------------------------
    # Mode: tree_with_expectation
    # -------------------------------------------------------------------
    def build_tree_with_expectation(self):
        """Decision tree + expected value calculation.

        Same setup as `build_tree` (A needs 1 more win, B needs 2 more wins,
        4 possible continuations, A wins 3 of 4) but the lower part of the
        screen shows the **expected value calculation** E[A] = 3/4 × 64 = 48
        pistoles and E[B] = 1/4 × 64 = 16 pistoles, instead of the redundant
        "Fermat: AA, AB, BA / BB" enumeration block.

        Layout (字幕クリアランス y >= -2.0):
            title         y = +3.0
            setup         y = +2.4
            tree (Round 1, Round 2)   y = +1.0 ~ -0.5
            summary       y = -0.9 (Aが3通り/Bが1通り)
            expectation   y = -1.5 (E[A]=48, E[B]=16)

        Used by: Episode 029 (Pascal), math_14.
        """
        duration = self._duration

        # Title
        title = Text("ポイントの問題 (1654)", font=FONT, font_size=24, color=TEXT_DIM)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.4)

        # Setup description (上部、横並び)
        setup = VGroup(
            Text("A: あと1勝で賞金", font=FONT, font_size=18, color=ACCENT_CYAN),
            Text("B: あと2勝で賞金", font=FONT, font_size=18, color=ACCENT_PINK),
        )
        setup.arrange(RIGHT, buff=0.8)
        setup.move_to([0, 2.4, 0])
        self.play(FadeIn(setup), run_time=0.4)

        # Tree structure - shifted slightly higher to leave room for expectation
        root_x, root_y = -4.5, 1.0
        round1_label = Text("Round 1", font=FONT, font_size=14, color=TEXT_DIM)
        round1_label.move_to([-5.5, 0.3, 0])
        round2_label = Text("Round 2", font=FONT, font_size=14, color=TEXT_DIM)
        round2_label.move_to([-5.5, -0.6, 0])

        root = Text("Start", font=FONT, font_size=16, color=TEXT_WHITE)
        root.move_to([root_x, root_y, 0])
        self.play(FadeIn(root), FadeIn(round1_label), FadeIn(round2_label), run_time=0.3)

        # Round 1 branches
        r1_a_label = Text("A wins", font=FONT, font_size=14, color=ACCENT_CYAN)
        r1_a_label.move_to([-2.5, 0.6, 0])
        r1_b_label = Text("B wins", font=FONT, font_size=14, color=ACCENT_PINK)
        r1_b_label.move_to([-2.5, -0.2, 0])
        arrow_r1a = Arrow(
            root.get_right(),
            r1_a_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_r1b = Arrow(
            root.get_right(),
            r1_b_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(
            FadeIn(arrow_r1a),
            FadeIn(r1_a_label),
            FadeIn(arrow_r1b),
            FadeIn(r1_b_label),
            run_time=0.5,
        )

        # A wins R1 -> A wins immediately
        result_aa = Text("A wins!", font=FONT, font_size=16, color=ACCENT_GOLD)
        result_aa.move_to([0.5, 0.6, 0])
        result_aa_rect = SurroundingRectangle(
            result_aa, color=ACCENT_GOLD, buff=0.06, stroke_width=1.5
        )
        arrow_aa = Arrow(
            r1_a_label.get_right(),
            result_aa.get_left(),
            color=ACCENT_GOLD,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(FadeIn(arrow_aa), FadeIn(result_aa), FadeIn(result_aa_rect), run_time=0.4)

        # B wins R1 -> Round 2
        r2_a_label = Text("A wins R2", font=FONT, font_size=14, color=ACCENT_CYAN)
        r2_a_label.move_to([0.5, -0.05, 0])
        r2_b_label = Text("B wins R2", font=FONT, font_size=14, color=ACCENT_PINK)
        r2_b_label.move_to([0.5, -0.6, 0])
        arrow_r2a = Arrow(
            r1_b_label.get_right(),
            r2_a_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        arrow_r2b = Arrow(
            r1_b_label.get_right(),
            r2_b_label.get_left(),
            color=TEXT_DIM,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(
            FadeIn(arrow_r2a),
            FadeIn(r2_a_label),
            FadeIn(arrow_r2b),
            FadeIn(r2_b_label),
            run_time=0.5,
        )

        # Round 2 results
        result_ba = Text("A wins!", font=FONT, font_size=16, color=ACCENT_GOLD)
        result_ba.move_to([3.5, -0.05, 0])
        result_ba_rect = SurroundingRectangle(
            result_ba, color=ACCENT_GOLD, buff=0.06, stroke_width=1.5
        )
        arrow_ba = Arrow(
            r2_a_label.get_right(),
            result_ba.get_left(),
            color=ACCENT_GOLD,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        result_bb = Text("B wins!", font=FONT, font_size=16, color=ACCENT_PINK)
        result_bb.move_to([3.5, -0.6, 0])
        result_bb_rect = SurroundingRectangle(
            result_bb, color=ACCENT_PINK, buff=0.06, stroke_width=1.5
        )
        arrow_bb = Arrow(
            r2_b_label.get_right(),
            result_bb.get_left(),
            color=ACCENT_PINK,
            stroke_width=1.5,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(
            FadeIn(arrow_ba),
            FadeIn(result_ba),
            FadeIn(result_ba_rect),
            FadeIn(arrow_bb),
            FadeIn(result_bb),
            FadeIn(result_bb_rect),
            run_time=0.5,
        )

        # Summary (一行、シンプル)
        summary = Text(
            "4 通り中 A が 3 通り、B が 1 通りで勝利", font=FONT, font_size=18, color=TEXT_WHITE
        )
        summary.move_to([0, -1.1, 0])
        self.play(FadeIn(summary), run_time=0.4)

        # Expectation values (中心メッセージ、字幕クリアランス内 y >= -2.0)
        exp_a = MathTex(r"E[A] = \tfrac{3}{4} \times 64 = 48", font_size=26, color=ACCENT_CYAN)
        exp_b = MathTex(r"E[B] = \tfrac{1}{4} \times 64 = 16", font_size=26, color=ACCENT_PINK)
        exp_group = VGroup(exp_a, exp_b).arrange(RIGHT, buff=0.8)
        exp_group.move_to([0, -1.75, 0])
        self.play(FadeIn(exp_group), run_time=0.6)

        self.wait(max(1, duration * 0.15))

    # -------------------------------------------------------------------
    # Mode: expectation_comparison
    # -------------------------------------------------------------------
    def build_expectation_comparison(self):
        """Fermat vs Pascal methods + birth of 'expectation' concept.

        Two columns side by side:
            Left  - Fermat method (combinatorial enumeration → A: 3/4)
            Right - Pascal method (arithmetic triangle + recursion → A: 3/4)
        Both methods arrive at the same answer; below the conclusion is
        the birth of the 'expectation' concept (E[X] = Σ p_i x_i).

        Layout (字幕クリアランス y >= -2.0、上下バランス):
            title           y = +3.0
            general formula y = +2.3 (E[X] = Σ p_i x_i)
            left/right boxes  y = +0.5 ~ +1.6
            arrows (down)   y = -0.3
            conclusion (同結論)  y = -0.95
            birth notice    y = -1.7

        Used by: Episode 029 (Pascal), math_15.
        """
        duration = self._duration

        # Title
        title = Text("期待値の誕生 (1654)", font=FONT, font_size=24, color=TEXT_DIM)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.4)

        # General formula
        formula = MathTex(r"E[X] = \sum_i p_i \, x_i", font_size=30, color=ACCENT_GOLD)
        formula.move_to([0, 2.3, 0])
        self.play(FadeIn(formula), run_time=0.5)

        # Left box: Fermat method
        left_title = Text("フェルマー方式", font=FONT, font_size=20, color=ACCENT_CYAN)
        left_title.move_to([-3.5, 1.5, 0])
        left_body1 = Text("4 通りを列挙", font=FONT, font_size=18, color=TEXT_WHITE)
        left_body1.move_to([-3.5, 0.95, 0])
        left_body2 = MathTex(r"AA, AB, BA \rightarrow A", font_size=20, color=TEXT_DIM)
        left_body2.move_to([-3.5, 0.40, 0])
        left_body3 = MathTex(r"BB \rightarrow B", font_size=20, color=TEXT_DIM)
        left_body3.move_to([-3.5, -0.05, 0])
        left_result = MathTex(r"\therefore P(A) = \tfrac{3}{4}", font_size=24, color=ACCENT_CYAN)
        left_result.move_to([-3.5, -0.65, 0])
        left_box = SurroundingRectangle(
            VGroup(left_title, left_body1, left_body2, left_body3, left_result),
            color=ACCENT_CYAN,
            buff=0.18,
            stroke_width=1.5,
        )
        self.play(FadeIn(left_box), FadeIn(left_title), run_time=0.4)
        self.play(
            FadeIn(left_body1),
            FadeIn(left_body2),
            FadeIn(left_body3),
            FadeIn(left_result),
            run_time=0.6,
        )

        # Right box: Pascal method
        right_title = Text("パスカル方式", font=FONT, font_size=20, color=ACCENT_PINK)
        right_title.move_to([3.5, 1.5, 0])
        right_body1 = Text("算術三角形 + 再帰", font=FONT, font_size=18, color=TEXT_WHITE)
        right_body1.move_to([3.5, 0.95, 0])
        # Tiny triangle hint (row 2 of Pascal's triangle: 1 2 1, suggesting recursion)
        right_body2 = MathTex(
            r"\binom{2}{0} : \binom{2}{1} : \binom{2}{2}", font_size=20, color=TEXT_DIM
        )
        right_body2.move_to([3.5, 0.40, 0])
        right_body3 = MathTex(r"= 1 : 2 : 1", font_size=20, color=TEXT_DIM)
        right_body3.move_to([3.5, -0.05, 0])
        right_result = MathTex(r"\therefore P(A) = \tfrac{3}{4}", font_size=24, color=ACCENT_PINK)
        right_result.move_to([3.5, -0.65, 0])
        right_box = SurroundingRectangle(
            VGroup(right_title, right_body1, right_body2, right_body3, right_result),
            color=ACCENT_PINK,
            buff=0.18,
            stroke_width=1.5,
        )
        self.play(FadeIn(right_box), FadeIn(right_title), run_time=0.4)
        self.play(
            FadeIn(right_body1),
            FadeIn(right_body2),
            FadeIn(right_body3),
            FadeIn(right_result),
            run_time=0.6,
        )

        # Same conclusion arrows (visual convergence)
        left_arrow = Arrow(
            [-3.5, -1.05, 0],
            [-0.6, -1.4, 0],
            color=ACCENT_GOLD,
            stroke_width=2.0,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        right_arrow = Arrow(
            [3.5, -1.05, 0],
            [0.6, -1.4, 0],
            color=ACCENT_GOLD,
            stroke_width=2.0,
            buff=0.1,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(FadeIn(left_arrow), FadeIn(right_arrow), run_time=0.4)

        # Conclusion
        conclusion = Text(
            "同じ結論 → 期待値の概念が誕生", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        conclusion.move_to([0, -1.75, 0])
        self.play(FadeIn(conclusion), run_time=0.6)

        self.wait(max(1, duration * 0.15))


# Factual-claim metadata (read by qa_manim_consistency.py). The template is the
# Pascal–Fermat "problem of points" (1654); titles render "(1654)" and the
# comparison modes label "パスカル方式 / フェルマー方式".
LINT_FACTUAL_CLAIMS = {
    "tree": {"people": [["パスカル", "Pascal"], ["フェルマー", "Fermat"]], "years": ["1654"]},
    "calculation": {
        "people": [["パスカル", "Pascal"], ["フェルマー", "Fermat"]],
        "years": ["1654"],
    },
    "tree_with_expectation": {
        "people": [["パスカル", "Pascal"], ["フェルマー", "Fermat"]],
        "years": ["1654"],
    },
    "expectation_comparison": {
        "people": [["パスカル", "Pascal"], ["フェルマー", "Fermat"]],
        "years": ["1654"],
    },
}

# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "tree": {
        "class": "ProblemOfPoints",
        "params": {"mode": "tree"},
        "description": "Decision tree showing all possible game paths",
    },
    "calculation": {
        "class": "ProblemOfPoints",
        "params": {"mode": "calculation"},
        "description": "Fair division calculation: A gets 3/4, B gets 1/4",
    },
    "tree_with_expectation": {
        "class": "ProblemOfPoints",
        "params": {"mode": "tree_with_expectation"},
        "description": "Decision tree + expected value (E[A]=48, E[B]=16) for an earlier episode Pascal math_14",
    },
    "expectation_comparison": {
        "class": "ProblemOfPoints",
        "params": {"mode": "expectation_comparison"},
        "description": "Fermat vs Pascal methods + birth of expectation concept (E[X]=Σp_i x_i) for an earlier episode Pascal math_15",
    },
}
