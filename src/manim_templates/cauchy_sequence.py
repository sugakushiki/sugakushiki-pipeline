"""
cauchy_sequence.py - Cauchy's convergence criterion (the Cauchy sequence)

Cauchy characterised convergence without naming the limit in advance: a
sequence converges if its terms eventually crowd together - for every error
epsilon there is an index N beyond which any two terms differ by less than
epsilon. The tail {a_n : n >= N} has a diameter that shrinks to zero. This is
the mathematical centrepiece of Episode 041 (Cauchy), block 5: we deliberately
never mark the limit value on the line, because the whole point is that you do
not need to know where the sequence is going to guarantee that it arrives.

NOTE: this template is intentionally separate from series_convergence.py, which
is Ramanujan-1/pi specific (it stamps a "Ramanujan (1914)" label on screen and
carries a LINT_FACTUAL_CLAIMS guard against being reused for a Cauchy/Abel
convergence scene). This template renders only math symbols and generic labels.

Modes:
    clustering (default)
        A number line on [0, 3]. An oscillating sequence
        a_n = 1.6 + 1.05 * (-0.5)^(n-1) is plotted dot by dot (a_1..a_4 labelled,
        later terms crowd in unlabelled near ~1.6). A bracket spans the tail
        {a_n : n >= N}; as a tracker drives N from 1 to 6 the bracket's width
        (the tail diameter, halving each step) shrinks toward zero, while the
        criterion |a_m - a_n| < epsilon is shown. The limit (~1.6) is marked
        only with a dim "?", never as a value.
        Fixed params: 12 precomputed terms, cluster near 1.6 (unlabelled),
        N driven 1 -> 6.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -1.6 to +3.05, subtitle clearance preserved. No trailing FadeOut.
Duration-aware: the shrinking tail bracket fills the body (no static tail).
"""

from manim import (
    UP,
    Dot,
    FadeIn,
    Line,
    MathTex,
    NumberLine,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    linear,
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

# Oscillating sequence converging (inward) to 1.6; the limit is never labelled.
_CLUSTER = 1.6
_TERMS = [_CLUSTER + 1.05 * ((-0.5) ** k) for k in range(12)]  # a_1 = _TERMS[0]
_N_MAX = 6
_LINE_Y = -0.35


class CauchySequence(Scene):
    """Cauchy convergence criterion - single mode (clustering)."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = float(params.get("duration", 30))
        self._build_clustering(duration)

    def _build_clustering(self, duration):
        # --- titles ---
        title = Text("コーシー列", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        subtitle = Text(
            "── 行き先を知らずに、到着を約束する", font=FONT, font_size=22, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.7)

        # --- number line ---
        nl = NumberLine(
            x_range=[0, 3, 0.5],
            length=10.0,
            color=TEXT_DIM,
            stroke_width=2.0,
            include_ticks=True,
            include_numbers=False,
        )
        nl.move_to([0, _LINE_Y, 0])
        self.play(FadeIn(nl), run_time=0.5)

        # --- reveal a_1..a_4 with labels above each dot ---
        for i in range(4):
            pt = nl.n2p(_TERMS[i])
            dot = Dot(pt, color=ACCENT_CYAN, radius=0.09)
            lab = MathTex(rf"a_{{{i + 1}}}", font_size=26, color=ACCENT_CYAN)
            lab.next_to(dot, UP, buff=0.18)
            self.play(FadeIn(dot), FadeIn(lab), run_time=0.45)

        gap_note = Text(
            "項どうしの間隔が、どんどん縮んでいく", font=FONT, font_size=22, color=ACCENT_PINK
        )
        gap_note.move_to([0, 1.55, 0])
        self.play(FadeIn(gap_note), run_time=0.5)

        # --- later terms crowd into the cluster (unlabelled, smaller) ---
        for i in range(4, len(_TERMS)):
            dot = Dot(nl.n2p(_TERMS[i]), color=ACCENT_CYAN, radius=0.07)
            self.play(FadeIn(dot), run_time=0.18)

        # --- the limit stays unknown: a dim "?" above the cluster, never a value ---
        q = MathTex(r"?", font_size=40, color=TEXT_DIM)
        q.move_to([nl.n2p(_CLUSTER)[0], _LINE_Y + 0.95, 0])
        q_note = Text("極限値は、まだ知らなくていい", font=FONT, font_size=20, color=TEXT_DIM)
        q_note.move_to([nl.n2p(_CLUSTER)[0], _LINE_Y + 1.45, 0])
        self.play(FadeIn(q), FadeIn(q_note), run_time=0.5)

        # --- the criterion ---
        crit = MathTex(r"|a_m - a_n| < \varepsilon", font_size=34, color=TEXT_WHITE)
        crit.move_to([0, 2.0, 0])
        # (gap_note occupied y=1.55; fade it as the criterion takes over)
        self.play(FadeIn(crit), gap_note.animate.set_opacity(0.0), run_time=0.6)

        # --- shrinking tail bracket drives the body (no static tail) ---
        n_tracker = ValueTracker(1.0)

        def _tail_bounds():
            n = max(1, min(_N_MAX, int(n_tracker.get_value())))
            tail = _TERMS[n - 1 :]
            return n, min(tail), max(tail)

        def make_bracket():
            _, lo, hi = _tail_bounds()
            y = _LINE_Y - 0.85
            left = [nl.n2p(lo)[0], y, 0]
            right = [nl.n2p(hi)[0], y, 0]
            span = Line(left, right, color=ACCENT_GOLD, stroke_width=4.0)
            # upward-only ticks -> reads as a width-measuring bracket pointing at
            # the terms, not a free-standing glyph when it collapses
            tick_l = Line(
                [left[0], y, 0],
                [left[0], y + 0.16, 0],
                color=ACCENT_GOLD,
                stroke_width=4.0,
            )
            tick_r = Line(
                [right[0], y, 0],
                [right[0], y + 0.16, 0],
                color=ACCENT_GOLD,
                stroke_width=4.0,
            )
            return VGroup(span, tick_l, tick_r)

        bracket = always_redraw(make_bracket)
        n_label = always_redraw(
            lambda: MathTex(
                rf"n \geq {_tail_bounds()[0]}", font_size=26, color=ACCENT_GOLD
            ).move_to([nl.n2p(_tail_bounds()[2])[0] + 0.5, _LINE_Y - 0.85, 0])
        )
        spread_note = Text("この先の項の、ちらばりの幅", font=FONT, font_size=20, color=ACCENT_GOLD)
        spread_note.move_to([0, _LINE_Y - 1.35, 0])
        self.add(bracket, n_label)
        self.play(FadeIn(spread_note), run_time=0.4)

        used = 0.7 + 0.5 + 4 * 0.45 + 0.5 + (len(_TERMS) - 4) * 0.18 + 0.5 + 0.6 + 0.4
        coda = 2.5
        motion = max(3.0, duration - used - coda)
        self.play(
            n_tracker.animate.set_value(float(_N_MAX)),
            run_time=motion,
            rate_func=linear,
        )

        # the bracket has collapsed toward a point: the tail differences -> 0
        done = Text("幅は、どんな ε よりも小さくなる", font=FONT, font_size=22, color=ACCENT_PINK)
        done.move_to([0, _LINE_Y - 1.35, 0])
        self.play(spread_note.animate.set_opacity(0.0), FadeIn(done), run_time=0.5)
        self.wait(coda)


# ---------------------------------------------------------------------------
# Factual-claim metadata (read by qa_manim_consistency.py).
# Renders only math symbols (a_n, epsilon, n >= N, "?") and generic Japanese
# labels - deliberately NO person names or years (contrast series_convergence).
# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "clustering": {"people": [], "years": []},
}

SCENES = {
    "clustering": CauchySequence,
}
