"""
bernoulli_numbers.py - Bernoulli numbers and sums of powers for 数学史記

Visualizes Jakob Bernoulli's unified formula for sums of powers
(1^k + 2^k + ... + n^k) and the Bernoulli numbers that appear in it.

Modes:
    sum_of_powers - Animated bar chart of 1^k + 2^k + ... + n^k for
                    increasing k, showing the growth pattern.
                    Fixed params: n=10, k cycles through 1,2,3,4.
                    Then shows B_0=1, B_1=-1/2, B_2=1/6, B_4=-1/30.
    east_west     - Timeline showing independent discovery:
                    Bernoulli 1705 死, Seki 1708 死,
                    Katsuyo Sanpo 1712, Ars Conjectandi 1713.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 011 (Bernoulli), math pillar 2
"""

from manim import (
    DOWN,
    RIGHT,
    UP,
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


class BernoulliNumbers(Scene):
    """Bernoulli numbers / sums of powers. Mode-branching scene.

    Modes:
        sum_of_powers (default) - bar chart of Σ i^k then B_n sequence
        east_west               - timeline of Seki vs Bernoulli discoveries
    """

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        self._highlight_color = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "sum_of_powers")

        if mode == "east_west":
            self.build_east_west()
        else:
            self.build_sum_of_powers()

    # -------------------------------------------------------------------
    # Mode: sum_of_powers
    # -------------------------------------------------------------------
    def build_sum_of_powers(self):
        """Animated visualization of sum of powers with Bernoulli numbers.

        Shows 1^k + 2^k + ... + n^k for n=10, k=1,2,3,4 as bar charts,
        then displays the first few Bernoulli numbers.
        """
        duration = self._duration
        highlight_color = self._highlight_color

        n = 10
        ks = [1, 2, 3, 4]

        # Phase 1: Show formula
        formula = MathTex(
            r"1^k + 2^k + \cdots + n^k",
            font_size=34,
            color=ACCENT_CYAN,
        )
        formula.to_edge(UP, buff=0.3)
        self.play(FadeIn(formula), run_time=0.6)

        phase1_time = max(2.0, (duration - 6.0) * 0.6)
        per_k = phase1_time / len(ks)

        k_label = None
        bars = None
        sum_label = None

        for k in ks:
            # Compute values
            vals = [i**k for i in range(1, n + 1)]
            total = sum(vals)
            max_val = max(vals)

            # k label
            k_label = MathTex(f"k = {k}", font_size=28, color=highlight_color)
            k_label.next_to(formula, DOWN, buff=0.35)

            # Bars (bar_base_y ensures all elements stay above y=-2.0)
            bar_width = 0.55
            max_height = 2.0
            bar_base_y = -1.5
            x_start = -3.5

            bars = VGroup()
            for i, v in enumerate(vals):
                h = max(0.05, (v / max_val) * max_height)
                x = x_start + i * (bar_width + 0.15)
                bar = Rectangle(
                    width=bar_width,
                    height=h,
                    fill_color=ACCENT_CYAN,
                    fill_opacity=0.7,
                    stroke_color=TEXT_WHITE,
                    stroke_width=0.5,
                )
                bar.move_to([x, bar_base_y + h / 2, 0])
                bars.add(bar)

            # Sum label
            sum_label = VGroup(
                MathTex(r"\sum", font_size=24, color=TEXT_DIM),
                MathTex(f"= {total}", font_size=26, color=highlight_color),
            )
            sum_label.arrange(RIGHT, buff=0.15)
            sum_label.next_to(bars, RIGHT, buff=0.5)
            sum_label.shift(UP * 0.3)

            self.play(FadeIn(k_label), FadeIn(bars), FadeIn(sum_label), run_time=0.6)
            self.wait(per_k - 0.6)
            if k < ks[-1]:
                self.play(
                    FadeOut(k_label),
                    FadeOut(bars),
                    FadeOut(sum_label),
                    run_time=0.3,
                )

        # Phase 2: Show Bernoulli numbers sequence
        self.play(FadeOut(k_label), FadeOut(bars), FadeOut(sum_label), run_time=0.3)

        bn_title = Text("Bernoulli numbers", font=FONT, font_size=24, color=TEXT_DIM)
        bn_title.next_to(formula, DOWN, buff=0.35)

        bn_seq = MathTex(
            r"B_0 = 1,\quad",
            r"B_1 = -\tfrac{1}{2},\quad",
            r"B_2 = \tfrac{1}{6},\quad",
            r"B_4 = -\tfrac{1}{30},\quad",
            r"\ldots",
            font_size=26,
        )
        bn_seq[0].set_color(ACCENT_CYAN)
        bn_seq[1].set_color(ACCENT_CYAN)
        bn_seq[2].set_color(highlight_color)
        bn_seq[3].set_color(highlight_color)
        bn_seq.next_to(bn_title, DOWN, buff=0.4)

        self.play(FadeIn(bn_title), run_time=0.4)
        self.play(FadeIn(bn_seq), run_time=0.8)

        phase2_time = max(1.5, (duration - 6.0) * 0.4)
        self.wait(phase2_time)

    # -------------------------------------------------------------------
    # Mode: east_west
    # -------------------------------------------------------------------
    def build_east_west(self):
        """Timeline comparing Seki (1712) and Bernoulli (1713) discoveries."""
        duration = self._duration
        highlight_color = self._highlight_color

        # Title
        title = Text("Bernoulli numbers", font=FONT, font_size=24, color=TEXT_DIM)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        # Timeline axis
        axis_y = 0.0
        axis = Line([-5.5, axis_y, 0], [5.5, axis_y, 0], color=TEXT_DIM, stroke_width=2)
        self.play(FadeIn(axis), run_time=0.4)

        # Year markers
        year_labels = ["1705", "1708", "1712", "1713"]
        x_positions = [-4.0, -1.5, 2.0, 4.0]

        for x, yr in zip(x_positions, year_labels, strict=False):
            tick = Line([x, axis_y - 0.1, 0], [x, axis_y + 0.1, 0], color=TEXT_DIM)
            label = Text(yr, font=FONT, font_size=18, color=TEXT_DIM)
            label.next_to(tick, DOWN, buff=0.15)
            self.play(FadeIn(tick), FadeIn(label), run_time=0.2)

        wait_per = max(0.8, (duration - 7.0) / 4)

        # Bernoulli death 1705
        b_death = Text("Bernoulli", font=FONT, font_size=20, color=ACCENT_CYAN)
        b_death_sub = Text("Basel", font=FONT, font_size=16, color=TEXT_DIM)
        b_death_group = VGroup(b_death, b_death_sub).arrange(DOWN, buff=0.1)
        b_death_group.move_to([x_positions[0], axis_y + 0.9, 0])
        self.play(FadeIn(b_death_group), run_time=0.5)
        self.wait(wait_per)

        # Seki death 1708
        s_death = Text("Seki", font=FONT, font_size=20, color=ACCENT_PINK)
        s_death_sub = Text("Edo", font=FONT, font_size=16, color=TEXT_DIM)
        s_death_group = VGroup(s_death, s_death_sub).arrange(DOWN, buff=0.1)
        s_death_group.move_to([x_positions[1], axis_y - 0.9, 0])
        self.play(FadeIn(s_death_group), run_time=0.5)
        self.wait(wait_per)

        # Katsuyo Sanpo 1712
        ks_pub = Text("Katsuyo Sanpo", font=FONT, font_size=20, color=ACCENT_PINK)
        ks_pub.move_to([x_positions[2], axis_y - 0.9, 0])
        self.play(FadeIn(ks_pub), run_time=0.5)
        self.wait(wait_per)

        # Ars Conjectandi 1713
        ac_pub = Text("Ars Conjectandi", font=FONT, font_size=20, color=ACCENT_CYAN)
        ac_pub.move_to([x_positions[3], axis_y + 0.9, 0])
        self.play(FadeIn(ac_pub), run_time=0.5)
        self.wait(wait_per)

        # Connecting note
        note = Text("Independent discovery", font=FONT, font_size=22, color=highlight_color)
        note.move_to([0, axis_y + 2.5, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(1.5)


# ---------------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "sum_of_powers": {"people": [], "years": []},
    "east_west": {
        "people": [
            ["Bernoulli", "ベルヌーイ", "ヤコブ"],
            ["Seki", "関孝和", "関"],
        ],
        "years": ["1705", "1708", "1712", "1713"],
    },
}


SCENES = {
    "sum_of_powers": BernoulliNumbers,
    "east_west": BernoulliNumbers,
}
