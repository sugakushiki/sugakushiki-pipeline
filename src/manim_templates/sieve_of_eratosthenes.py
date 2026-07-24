"""
sieve_of_eratosthenes.py - The Sieve of Eratosthenes for primes up to 49.

The earliest documented attribution of the sieve to Eratosthenes is in
Nicomachus of Gerasa's "Introduction to Arithmetic" (early 2nd century CE).
The procedure: list integers from 2 upward; the smallest unmarked integer is
prime; mark all its multiples; repeat. Modern optimization: it is enough to
sieve up to the square root of the upper bound (here sqrt(49) = 7), since any
composite n <= 49 has a prime factor at most sqrt(n).

Modes:
    grid       - Seven-by-seven grid of integers 1..49. Step 1: mark 1 as
                 non-prime (gray). Then for each prime p in {2, 3, 5, 7}:
                 highlight p, then sweep its multiples 2p, 3p, ... and mark
                 them as composite. After p = 7 = floor(sqrt(49)), all
                 remaining unmarked numbers (2,3,5,7,11,13,17,19,23,29,31,37,
                 41,43,47) are prime. Footer: sqrt(49) = 7 で十分.
                 Fixed params: N = 49, cols = 7, rows = 7. Primes sieved by:
                 2, 3, 5, 7.

All Text uses FONT (BIZ UDMincho). MathTex contains ASCII/LaTeX only.
Y range: -2.0 to +3.0. No trailing FadeOut. Duration-aware.

Used by: Episode 027 (Eratosthenes), interlude — sieve of Eratosthenes.
"""

from manim import (
    FadeIn,
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


class SieveOfEratosthenes(Scene):
    """Sieve of Eratosthenes — primes up to 49."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Only one mode currently
        _ = params.get("mode", "grid")
        self._duration = params.get("duration", 30)
        self._build_grid()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=26, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_grid(self):
        duration = float(self._duration)
        title = self._title("エラトステネスのふるい ── 二から四十九まで")
        self.play(FadeIn(title), run_time=0.6)

        N = 49
        cols, rows = 7, 7
        cell_w = 0.78
        cell_h = 0.48
        grid_w = cols * cell_w
        rows * cell_h
        ox = -grid_w / 2 + cell_w / 2
        # Center the grid in the band between y = +2.6 (below title) and y = -1.6
        # (above footer). Band center is ≈ +0.5.
        oy = 2.40 - cell_h / 2

        # Build cells: dict n -> (rectangle, text)
        cells = {}
        cell_group = VGroup()
        for n in range(1, N + 1):
            r = (n - 1) // cols
            c = (n - 1) % cols
            x = ox + c * cell_w
            y = oy - r * cell_h
            rect = Rectangle(
                width=cell_w * 0.88, height=cell_h * 0.84, color=TEXT_DIM, stroke_width=1.4
            )
            rect.move_to([x, y, 0])
            txt = Text(str(n), font=FONT, font_size=20, color=TEXT_WHITE)
            txt.move_to([x, y, 0])
            cells[n] = (rect, txt)
            cell_group.add(rect, txt)

        self.play(FadeIn(cell_group), run_time=1.0)

        # Step 1: mark 1 as non-prime (gray it out)
        rect1, txt1 = cells[1]
        self.play(
            rect1.animate.set_stroke(TEXT_DIM, opacity=0.4),
            txt1.animate.set_color(TEXT_DIM),
            run_time=0.4,
        )

        # Helper: highlight a prime
        def highlight_prime(p, color):
            r, t = cells[p]
            return [
                r.animate.set_stroke(color, width=3.0),
                t.animate.set_color(color).set_weight("BOLD")
                if hasattr(t, "set_weight")
                else t.animate.set_color(color),
            ]

        # Helper: mark multiples of p (excluding p itself) as composite (gray)
        def mark_multiples(p):
            anims = []
            for k in range(2 * p, N + 1, p):
                r, t = cells[k]
                # Only mark if still white-ish (not already a smaller-prime multiple
                # — visually, just always re-color; safe).
                anims.append(r.animate.set_stroke(TEXT_DIM, opacity=0.35))
                anims.append(t.animate.set_color(TEXT_DIM))
            return anims

        primes_sieved = [2, 3, 5, 7]
        prime_colors = [ACCENT_CYAN, ACCENT_PINK, ACCENT_GOLD, ACCENT_CYAN]

        for p, c in zip(primes_sieved, prime_colors, strict=False):
            anims_p = highlight_prime(p, c)
            self.play(*anims_p, run_time=0.5)
            mult_anims = mark_multiples(p)
            if mult_anims:
                self.play(*mult_anims, run_time=0.8)

        # Final pass: re-color all remaining un-grayed-out numbers as primes
        # (gold) — these are the 15 primes up to 49.
        primes_up_to_49 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        final_anims = []
        for p in primes_up_to_49:
            r, t = cells[p]
            final_anims.append(r.animate.set_stroke(ACCENT_GOLD, width=2.6))
            final_anims.append(t.animate.set_color(ACCENT_GOLD))
        self.play(*final_anims, run_time=1.0)

        # Footer
        footer = Text(
            "残った 15 個が素数 ── 判定は √49 = 7 まででよい",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        footer.move_to([0, -1.95, 0])
        self.play(FadeIn(footer), run_time=0.6)

        # Animation total (rough)
        anim_total = 0.6 + 1.0 + 0.4 + (0.5 + 0.8) * len(primes_sieved) + 1.0 + 0.6
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "grid": {"people": [], "years": []},
}

SCENES = {
    "grid": SieveOfEratosthenes,
}
