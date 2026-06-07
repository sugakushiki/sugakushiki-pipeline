"""
lhopital_rule.py - L'Hôpital's rule: the statement, an example, and the
                    history of the "sold theorem"

Visualizes the 0/0 form limit rule that was communicated by Johann Bernoulli
to the Marquis de l'Hôpital in 1694 and published in l'Hôpital's 1696
textbook. The true authorship was confirmed only in 1921 by the discovery
of Bernoulli's lecture manuscript.

Modes:
    statement         - Present the rule itself. Shows the 0/0 and ∞/∞ forms
                        with the derivative substitution.
                        Fixed params: f(x)/g(x) -> f'(x)/g'(x), with color-
                        coded numerator/denominator.
    example_sinx_x    - Work through lim(x→0) sin(x)/x step by step,
                        showing 0/0 -> cos(x)/1 -> 1.
                        Fixed params: uses lim(x→0) sin(x)/x as the canonical
                        example (result = 1).
    contract_timeline - Historical timeline from 1691 (Paris meeting) to
                        1921 (Basel manuscript discovery). Shows five
                        key events as cards arranged horizontally.
                        Fixed params: 5 events at years 1691, 1694, 1696,
                        1704, 1921.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 017 (Johann Bernoulli), math pillar 1 (ロピタルの定理)
"""

from manim import (
    DOWN,
    ORIGIN,
    RIGHT,
    UP,
    Dot,
    FadeIn,
    Indicate,
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


class LHopitalRule(Scene):
    """L'Hôpital's rule visualization. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "statement")

        if mode == "example_sinx_x":
            self.build_example_sinx_x()
        elif mode == "contract_timeline":
            self.build_contract_timeline()
        else:
            self.build_statement()

    # -------------------------------------------------------------------
    # Mode: statement
    # -------------------------------------------------------------------
    def build_statement(self):
        duration = self._duration

        title = Text(
            "ロピタルの定理",
            font=FONT,
            font_size=36,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.5)

        subtitle = Text(
            "0/0 または ∞/∞ 型の極限",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        subtitle.next_to(title, DOWN, buff=0.25)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(subtitle), run_time=0.5)

        # Main statement
        lhs = MathTex(
            r"\lim_{x \to a} \frac{f(x)}{g(x)}",
            font_size=48,
        )
        arrow = MathTex(r"=", font_size=48, color=TEXT_WHITE)
        rhs = MathTex(
            r"\lim_{x \to a} \frac{f'(x)}{g'(x)}",
            font_size=48,
        )

        statement = VGroup(lhs, arrow, rhs).arrange(RIGHT, buff=0.3)
        statement.move_to([0, 0.6, 0])

        # Color-code numerator and denominator
        lhs.set_color_by_tex("f(x)", ACCENT_CYAN)
        lhs.set_color_by_tex("g(x)", ACCENT_PINK)
        rhs.set_color_by_tex("f'(x)", ACCENT_CYAN)
        rhs.set_color_by_tex("g'(x)", ACCENT_PINK)

        self.play(FadeIn(lhs), run_time=0.8)
        self.play(FadeIn(arrow), FadeIn(rhs), run_time=1.0)

        # Condition note
        condition = Text(
            "条件: 分子分母がともに 0 または ±∞ に収束すること",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        condition.move_to([0, -1.0, 0])

        self.play(FadeIn(condition), run_time=0.6)

        # Meaning gloss
        gloss = Text(
            "分子と分母をそれぞれ微分してよい",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        gloss.to_edge(DOWN, buff=2.3)
        self.play(FadeIn(gloss), run_time=0.6)

        anim_time = 0.6 + 0.5 + 0.8 + 1.0 + 0.6 + 0.6
        self.wait(max(0.5, duration - anim_time))

    # -------------------------------------------------------------------
    # Mode: example_sinx_x
    # -------------------------------------------------------------------
    def build_example_sinx_x(self):
        duration = self._duration

        title = Text(
            "例題  sin(x) / x の極限",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.5)
        self.play(FadeIn(title), run_time=0.5)

        # Step 1: the limit in 0/0 form
        step1 = MathTex(
            r"\lim_{x \to 0} \frac{\sin x}{x}",
            font_size=44,
        )
        step1.move_to([0, 1.6, 0])

        indet = MathTex(
            r"\left(\frac{0}{0}\ \text{type}\right)",
            font_size=26,
            color=ACCENT_PINK,
        )
        indet.next_to(step1, RIGHT, buff=0.4)

        self.play(FadeIn(step1), run_time=0.8)
        self.play(FadeIn(indet), run_time=0.6)

        # Step 2: apply the rule -> differentiate numerator and denominator
        arrow_down = Text("↓ 分子分母を微分", font=FONT, font_size=20, color=TEXT_DIM)
        arrow_down.move_to([0, 0.6, 0])
        self.play(FadeIn(arrow_down), run_time=0.5)

        step2 = MathTex(
            r"= \lim_{x \to 0} \frac{\cos x}{1}",
            font_size=44,
        )
        step2.move_to([0, -0.3, 0])
        step2.set_color_by_tex(r"\cos x", ACCENT_CYAN)
        self.play(FadeIn(step2), run_time=1.0)

        # Step 3: evaluate at x=0
        arrow_down2 = Text("↓ x → 0 を代入", font=FONT, font_size=20, color=TEXT_DIM)
        arrow_down2.move_to([0, -1.15, 0])
        self.play(FadeIn(arrow_down2), run_time=0.5)

        step3 = MathTex(
            r"= \frac{\cos 0}{1} = 1",
            font_size=44,
            color=ACCENT_GOLD,
        )
        step3.move_to([0, -1.85, 0])  # y=-1.85 stays above subtitle area
        self.play(FadeIn(step3), run_time=0.8)

        self.play(Indicate(step3, color=ACCENT_GOLD, scale_factor=1.15), run_time=0.8)

        anim_time = 0.5 + 0.8 + 0.6 + 0.5 + 1.0 + 0.5 + 0.8 + 0.8
        self.wait(max(0.5, duration - anim_time))

    # -------------------------------------------------------------------
    # Mode: contract_timeline
    # -------------------------------------------------------------------
    def build_contract_timeline(self):
        duration = self._duration

        title = Text(
            "『売られた定理』 230年の決着",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        # 5 events on a horizontal timeline
        events = [
            ("1691", "パリで出会い", "ロピタルがヨハンに個人授業を依頼", ACCENT_CYAN),
            ("1694", "300リーブル契約", "3月17日、発見の独占使用権を購入", ACCENT_PINK),
            ("1696", "『無限小解析』", "史上初の微積分教科書として出版", ACCENT_CYAN),
            ("1704", "ロピタル急死", "42歳。ヨハンが著者権を主張", ACCENT_PINK),
            ("1921", "講義ノート発見", "バーゼル大学で原典が確認される", ACCENT_GOLD),
        ]

        # Timeline axis
        axis_y = 0.2
        x_left = -5.5
        x_right = 5.5
        axis = Line([x_left, axis_y, 0], [x_right, axis_y, 0], color=TEXT_DIM, stroke_width=2)
        self.play(FadeIn(axis), run_time=0.5)

        n = len(events)
        xs = [x_left + (x_right - x_left) * (i + 0.5) / n for i in range(n)]

        # Place event cards alternating above/below the axis
        cards = VGroup()
        anim_unit = max(0.6, (duration - 3.0) / n)

        for i, ((year, head, desc, color), x) in enumerate(zip(events, xs, strict=False)):
            dot = Dot([x, axis_y, 0], radius=0.1, color=color)

            # Card stacked: year (big) / headline (medium) / desc (small)
            year_t = Text(year, font=FONT, font_size=26, color=color)
            head_t = Text(head, font=FONT, font_size=20, color=TEXT_WHITE)
            desc_t = Text(desc, font=FONT, font_size=14, color=TEXT_DIM)

            card = VGroup(year_t, head_t, desc_t).arrange(
                DOWN,
                buff=0.1,
                aligned_edge=ORIGIN,
            )

            # Alternate above/below the axis
            if i % 2 == 0:
                card.move_to([x, axis_y + 1.5, 0])
            else:
                card.move_to([x, axis_y - 1.5, 0])

            # Connector line from card to axis
            connector = Line(
                [x, axis_y, 0],
                card.get_center() + (DOWN if i % 2 == 0 else UP) * (card.height / 2),
                color=color,
                stroke_width=1.5,
                stroke_opacity=0.6,
            )

            cards.add(VGroup(dot, connector, card))
            self.play(
                FadeIn(dot), FadeIn(connector), FadeIn(card), run_time=min(1.0, anim_unit * 0.6)
            )
            self.wait(max(0.1, anim_unit * 0.4))

        anim_time = 0.5 + 0.5 + n * anim_unit
        self.wait(max(0.3, duration - anim_time))


# ---------------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "statement": {"people": [], "years": []},
    "example_sinx_x": {"people": [], "years": []},
    "contract_timeline": {
        "people": [
            ["ロピタル", "L'Hopital", "ロピタール"],
            ["ヨハン", "Johann"],
        ],
        "years": ["1691", "1694", "1696", "1704", "1921"],
    },
}


SCENES = {
    "statement": LHopitalRule,
    "example_sinx_x": LHopitalRule,
    "contract_timeline": LHopitalRule,
}
