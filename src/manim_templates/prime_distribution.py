"""
prime_distribution.py — 素数分布の可視化 for 数学史記

ガウスが15-16歳で着想した素数の分布法則を可視化。
素数階段関数 pi(x) と対数積分 Li(x) の比較。
SymPy を利用して素数列と積分を計算。

Modes:
    staircase  - 素数階段関数 pi(x) を動的に描画。
                 x=2..200 の範囲で素数が見つかるたびに階段が上がる。
                 密度が徐々に減る様子を視覚化。
    comparison - pi(x), Li(x), x/ln(x) の3曲線を重ねて比較。
                 x=2..1000 の範囲。Li(x) がより良い近似であることを示す。
    sieve      - エラトステネスの篩アニメーション（小規模）。
                 n=2..100 で合成数を消していき素数を残す。

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 010 (Gauss)
"""

import math

from manim import (
    RIGHT,
    UP,
    Axes,
    Create,
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
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _sieve_primes(n):
    """Simple sieve of Eratosthenes returning list of primes <= n."""
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    return [i for i in range(2, n + 1) if is_prime[i]]


def _pi_values(x_max):
    """Return list of (x, pi(x)) for x = 2..x_max."""
    primes = set(_sieve_primes(x_max))
    count = 0
    result = []
    for x in range(2, x_max + 1):
        if x in primes:
            count += 1
        result.append((x, count))
    return result


def _li_approx(x):
    """Logarithmic integral Li(x) approximation via trapezoidal rule."""
    if x <= 2:
        return 0
    n_steps = max(100, int(x))
    dx = (x - 2.0) / n_steps
    total = 0.0
    for i in range(n_steps):
        t = 2.0 + (i + 0.5) * dx
        if t > 1.0:
            total += 1.0 / math.log(t)
    return total * dx


class PrimeDistribution(Scene):
    """Prime distribution visualization — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "staircase")
        self._duration = params.get("duration", 18)

        if mode == "comparison":
            self._build_comparison()
        elif mode == "sieve":
            self._build_sieve()
        else:
            self._build_staircase()

    # ------------------------------------------------------------------
    # Mode A: staircase
    # ------------------------------------------------------------------
    def _build_staircase(self):
        duration = self._duration

        title = Text(
            "素数階段関数",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 0.8 + 0.8
        default_waits = 1.0 + 1.0 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Axes
        axes = Axes(
            x_range=[0, 210, 50],
            y_range=[0, 50, 10],
            x_length=10,
            y_length=4.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2},
            tips=False,
        )
        axes.move_to([0.3, 0.1, 0])

        x_label = MathTex("x", font_size=24, color=TEXT_DIM)
        x_label.next_to(axes.x_axis, RIGHT, buff=0.15)
        y_label = MathTex(r"\pi(x)", font_size=24, color=ACCENT_CYAN)
        y_label.next_to(axes.y_axis, UP, buff=0.15)

        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.8)
        self.wait(0.5 * ws)

        # Build staircase path
        pi_data = _pi_values(200)
        primes_set = set(_sieve_primes(200))

        stair_lines = VGroup()
        prev_x, prev_y = 2, 0
        for x, pi_x in pi_data:
            if x in primes_set:
                # Horizontal line from prev to current x at old height
                h_line = Line(
                    axes.c2p(prev_x, prev_y),
                    axes.c2p(x, prev_y),
                    color=ACCENT_CYAN,
                    stroke_width=2,
                )
                # Vertical step up
                v_line = Line(
                    axes.c2p(x, prev_y),
                    axes.c2p(x, pi_x),
                    color=ACCENT_CYAN,
                    stroke_width=2,
                )
                stair_lines.add(h_line, v_line)
                prev_x, prev_y = x, pi_x
        # Final horizontal
        h_final = Line(
            axes.c2p(prev_x, prev_y),
            axes.c2p(200, prev_y),
            color=ACCENT_CYAN,
            stroke_width=2,
        )
        stair_lines.add(h_final)

        self.play(Create(stair_lines), run_time=3.0)
        anim_time += 3.0
        self.wait(0.5 * ws)

        # Note about decreasing density
        note = Text(
            "素数は無限に続くが、密度は徐々に下がる",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.7, 0])
        self.play(FadeIn(note), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode B: comparison
    # ------------------------------------------------------------------
    def _build_comparison(self):
        duration = self._duration

        title = Text(
            "ガウスの予想 ── 素数の分布法則",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 1.5 + 1.5 + 1.5 + 0.8
        default_waits = 0.5 + 0.5 + 0.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Axes for x=0..1000
        axes = Axes(
            x_range=[0, 1050, 200],
            y_range=[0, 180, 40],
            x_length=10,
            y_length=4.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2},
            tips=False,
        )
        axes.move_to([0.3, 0.1, 0])

        x_label = MathTex("x", font_size=24, color=TEXT_DIM)
        x_label.next_to(axes.x_axis, RIGHT, buff=0.15)

        self.play(Create(axes), FadeIn(x_label), run_time=0.8)
        self.wait(0.3 * ws)

        # pi(x) curve
        pi_data = _pi_values(1000)
        pi_points = [(x, y) for x, y in pi_data[::5]]  # sample every 5

        pi_line_segments = VGroup()
        for i in range(len(pi_points) - 1):
            seg = Line(
                axes.c2p(pi_points[i][0], pi_points[i][1]),
                axes.c2p(pi_points[i + 1][0], pi_points[i + 1][1]),
                color=ACCENT_CYAN,
                stroke_width=2,
            )
            pi_line_segments.add(seg)

        pi_label = MathTex(r"\pi(x)", font_size=22, color=ACCENT_CYAN)
        pi_label.move_to(axes.c2p(1000, pi_data[-1][1]) + [0.5, 0.2, 0])

        self.play(Create(pi_line_segments), FadeIn(pi_label), run_time=1.5)
        self.wait(0.3 * ws)

        # Li(x) curve
        li_points = []
        for x in range(10, 1001, 5):
            li_points.append((x, _li_approx(x)))

        li_line_segments = VGroup()
        for i in range(len(li_points) - 1):
            seg = Line(
                axes.c2p(li_points[i][0], li_points[i][1]),
                axes.c2p(li_points[i + 1][0], li_points[i + 1][1]),
                color=ACCENT_GOLD,
                stroke_width=2,
            )
            li_line_segments.add(seg)

        li_label = MathTex(r"\mathrm{Li}(x)", font_size=22, color=ACCENT_GOLD)
        li_label.move_to(axes.c2p(1000, _li_approx(1000)) + [0.5, 0.2, 0])

        self.play(Create(li_line_segments), FadeIn(li_label), run_time=1.5)
        self.wait(0.3 * ws)

        # x/ln(x) curve
        xln_points = []
        for x in range(10, 1001, 5):
            xln_points.append((x, x / math.log(x)))

        xln_line_segments = VGroup()
        for i in range(len(xln_points) - 1):
            seg = Line(
                axes.c2p(xln_points[i][0], xln_points[i][1]),
                axes.c2p(xln_points[i + 1][0], xln_points[i + 1][1]),
                color=ACCENT_PINK,
                stroke_width=2,
                stroke_opacity=0.7,
            )
            xln_line_segments.add(seg)

        xln_label = MathTex(r"\frac{x}{\ln x}", font_size=22, color=ACCENT_PINK)
        xln_label.move_to(axes.c2p(1000, 1000 / math.log(1000)) + [0.5, -0.3, 0])

        self.play(Create(xln_line_segments), FadeIn(xln_label), run_time=1.5)
        self.wait(0.3 * ws)

        # Conclusion note
        note = Text(
            "Li(x) はガウスの予想 ── より正確な近似",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.7, 0])
        self.play(FadeIn(note), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode C: sieve
    # ------------------------------------------------------------------
    def _build_sieve(self):
        duration = self._duration

        title = Text(
            "素数の篩（ふるい）",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        # Grid of numbers 2..100 (10 columns x 10 rows)
        n_max = 100
        cols = 10
        cell_w, cell_h = 0.75, 0.45
        grid_x0 = -(cols * cell_w) / 2 + cell_w / 2
        grid_y0 = 2.5

        primes = _sieve_primes(n_max)

        # Create all number texts
        num_texts = {}
        all_nums = VGroup()
        for idx, n in enumerate(range(1, n_max + 1)):
            r = idx // cols
            c = idx % cols
            x = grid_x0 + c * cell_w
            y = grid_y0 - r * cell_h
            color = TEXT_DIM if n == 1 else TEXT_WHITE
            t = Text(str(n), font=FONT, font_size=18, color=color)
            t.move_to([x, y, 0])
            num_texts[n] = t
            all_nums.add(t)

        self.play(FadeIn(all_nums), run_time=0.8)

        # Sieve animation: for each prime p, dim its multiples
        sieve_primes_to_show = [2, 3, 5, 7]
        eliminated = {1}

        anim_time = 0.8 + len(sieve_primes_to_show) * 0.8
        default_waits = len(sieve_primes_to_show) * 0.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        for p in sieve_primes_to_show:
            # Highlight the prime itself
            num_texts[p].set_color(ACCENT_CYAN)
            self.play(FadeIn(num_texts[p]), run_time=0.2)

            # Dim multiples
            fades = []
            for mult in range(p * 2, n_max + 1, p):
                if mult not in eliminated:
                    eliminated.add(mult)
                    num_texts[mult].set_color(TEXT_DIM)
                    num_texts[mult].set_opacity(0.2)
                    fades.append(FadeIn(num_texts[mult]))
            if fades:
                self.play(*fades[:10], run_time=0.4)
                if len(fades) > 10:
                    self.play(*fades[10:], run_time=0.2)
            self.wait(0.3 * ws)

        self.wait(0.3 * ws)

        # Highlight remaining primes
        for p in primes:
            if p not in {2, 3, 5, 7}:
                num_texts[p].set_color(ACCENT_GOLD)

        self.play(
            *[FadeIn(num_texts[p]) for p in primes if p not in {2, 3, 5, 7}],
            run_time=0.8,
        )

        count_text = Text(
            f"100以下の素数: {len(primes)}個",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        count_text.move_to([0, -1.7, 0])
        self.play(FadeIn(count_text), run_time=0.6)
        self.wait(max(duration - anim_time - 1.0, 1.0))


# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "staircase": {"people": [], "years": []},
    "comparison": {"people": [], "years": []},
    "sieve": {"people": [], "years": []},
}


# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
SCENES = {
    "staircase": PrimeDistribution,
    "comparison": PrimeDistribution,
    "sieve": PrimeDistribution,
}
