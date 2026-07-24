"""
mandelbrot_julia.py - The Mandelbrot set and Julia sets (z -> z^2 + c)

Episode 042 (Mandelbrot), block 6 (pillar 3, the centerpiece). For a complex c,
iterate z -> z^2 + c from z = 0; the c for which the orbit stays bounded form
the Mandelbrot set. Its boundary is infinitely complex and self-similar. The
iteration theory is due to Julia and Fatou (early 20th c.); the set was first
drawn by Brooks-Matelski (1978) and named by Douady -- all credited in the
narration, not on screen. The escape-time field is computed with numpy and
shown as an ImageMobject (fast; no per-pixel VMobjects).

Modes:
    iteration (default)
        One complex plane. First a bounded orbit (c = -0.5, dots cluster), then
        an escaping orbit (c = 0.6 + 0.6i, dots fly out), with the rule
        z -> z^2 + c shown.
        Fixed params: c_bounded = -0.5; c_escape = 0.6 + 0.6i; 9 orbit points.
    set
        The Mandelbrot set over c in [-2.5, 1] x [-1.25, 1.25], escape-time
        coloured; annotations name the rule and the infinitely complex boundary.
        Fixed params: 900x675 grid, max_iter 100.
    zoom
        Three nested views around the seahorse valley (-0.745 + 0.113i) at
        widening magnification, to show self-similarity that never ends.
        Fixed params: center -0.745+0.113i; half-widths 1.9, 0.16, 0.02.
    julia
        One filled Julia set for the fixed c = -0.8 + 0.156i.
        Fixed params: c = -0.8 + 0.156i; 900x675 grid, max_iter 100.

All Text uses FONT (BIZ UDMincho). MathTex is ASCII/LaTeX only.
Y range: about -1.7 to +3.05. No trailing FadeOut. No person names / years on screen.
"""

import numpy as np
from manim import (
    DOWN,
    Arrow,
    Axes,
    Dot,
    FadeIn,
    FadeOut,
    ImageMobject,
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


# --------------------------------------------------------------------------
# Escape-time field + colouring (numpy; fast)
# --------------------------------------------------------------------------
def _escape_counts(cx, cy, hw_x, hw_y, w, h, max_iter, julia_c=None):
    xs = np.linspace(cx - hw_x, cx + hw_x, w)
    ys = np.linspace(cy + hw_y, cy - hw_y, h)
    X, Y = np.meshgrid(xs, ys)
    grid = X + 1j * Y
    if julia_c is None:
        Z = np.zeros_like(grid)
        Cp = grid
    else:
        Z = grid.copy()
        Cp = np.full_like(grid, julia_c)
    counts = np.full(grid.shape, float(max_iter))
    mask = np.ones(grid.shape, dtype=bool)
    for i in range(max_iter):
        Z[mask] = Z[mask] * Z[mask] + Cp[mask]
        esc = mask & (np.abs(Z) > 2.0)
        counts[esc] = i
        mask &= ~esc
    return counts


def _colorize(counts, max_iter):
    nu = np.sqrt(np.clip(counts / max_iter, 0.0, 1.0))
    pos = [0.0, 0.35, 0.7, 1.0]
    cols = [(26, 26, 46), (247, 37, 133), (226, 183, 20), (240, 240, 255)]
    r = np.interp(nu, pos, [c[0] for c in cols])
    g = np.interp(nu, pos, [c[1] for c in cols])
    b = np.interp(nu, pos, [c[2] for c in cols])
    img = np.stack([r, g, b], axis=-1).astype(np.uint8)
    interior = counts >= max_iter
    img[interior] = (12, 12, 28)
    return img


def _fractal_image(cx, cy, hw_x, hw_y, w, h, max_iter, julia_c=None):
    counts = _escape_counts(cx, cy, hw_x, hw_y, w, h, max_iter, julia_c)
    arr = _colorize(counts, max_iter)
    return ImageMobject(arr)


class MandelbrotJulia(Scene):
    """Mandelbrot set and Julia sets - four modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "iteration")
        duration = float(params.get("duration", 28))
        if mode == "set":
            self._build_set(duration)
        elif mode == "zoom":
            self._build_zoom(duration)
        elif mode == "julia":
            self._build_julia(duration)
        else:
            self._build_iteration(duration)

    # --------------------------------------------------------------- iteration
    def _build_iteration(self, duration):
        title = MathTex(r"z \;\to\; z^2 + c", font_size=40, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        self.play(FadeIn(title), run_time=0.7)

        axes = Axes(
            x_range=[-2, 2, 1],
            y_range=[-1.5, 1.5, 1],
            x_length=6.4,
            y_length=4.2,
            tips=False,
            axis_config={"color": TEXT_DIM, "stroke_width": 1.4},
        )
        axes.move_to([0, 0.1, 0])
        self.play(FadeIn(axes), run_time=0.6)

        def orbit(c, n):
            pts = []
            z = 0 + 0j
            for _ in range(n):
                pts.append(z)
                z = z * z + c
                if abs(z) > 6:
                    pts.append(z)
                    break
            return pts

        used = 0.7 + 0.6
        coda = 2.4
        body = max(3.0, duration - used - coda)
        half = body / 2.0

        # --- bounded orbit (c = -0.5) ---
        cb = -0.5 + 0j
        lab_b = Text("c = −0.5 → 有界（集合に入る）", font=FONT, font_size=22, color=ACCENT_CYAN)
        lab_b.move_to([0, -1.95, 0])
        lab_b.move_to([-2.4, 2.0, 0])
        self.play(FadeIn(lab_b), run_time=0.5)
        ob = orbit(cb, 9)
        prev = None
        bgroup = VGroup()
        per_b = max(0.25, (half - 0.5) / len(ob))
        for z in ob:
            p = axes.c2p(z.real, z.imag)
            dot = Dot(p, color=ACCENT_CYAN, radius=0.06)
            if prev is not None:
                arr = Arrow(
                    prev,
                    p,
                    color=ACCENT_CYAN,
                    stroke_width=2,
                    buff=0.02,
                    max_tip_length_to_length_ratio=0.18,
                )
                bgroup.add(arr)
                self.play(FadeIn(arr), FadeIn(dot), run_time=per_b)
            else:
                self.play(FadeIn(dot), run_time=per_b)
            bgroup.add(dot)
            prev = p

        self.play(FadeOut(bgroup), FadeOut(lab_b), run_time=0.4)

        # --- escaping orbit (c = 0.6 + 0.6i) ---
        ce = 0.6 + 0.6j
        lab_e = Text(
            "c = 0.6 + 0.6i → 発散（集合の外）", font=FONT, font_size=22, color=ACCENT_PINK
        )
        lab_e.move_to([-2.0, 2.0, 0])
        self.play(FadeIn(lab_e), run_time=0.5)
        oe = orbit(ce, 7)
        prev = None
        per_e = max(0.25, (half - 0.5) / max(1, len(oe)))
        for z in oe:
            zr = max(-2.4, min(2.4, z.real))
            zi = max(-1.7, min(1.7, z.imag))
            p = axes.c2p(zr, zi)
            dot = Dot(p, color=ACCENT_PINK, radius=0.06)
            if prev is not None:
                arr = Arrow(
                    prev,
                    p,
                    color=ACCENT_PINK,
                    stroke_width=2,
                    buff=0.02,
                    max_tip_length_to_length_ratio=0.18,
                )
                self.play(FadeIn(arr), FadeIn(dot), run_time=per_e)
            else:
                self.play(FadeIn(dot), run_time=per_e)
            prev = p

        self.wait(coda)

    # --------------------------------------------------------------------- set
    def _build_set(self, duration):
        title = Text("マンデルブロ集合", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        img = _fractal_image(-0.75, 0.0, 1.75, 1.25, 900, 643, 100)
        img.height = 3.5
        img.move_to([-1.7, 0.25, 0])
        self.play(FadeIn(img), run_time=1.0)

        rule = MathTex(r"z \to z^2 + c", font_size=32, color=TEXT_WHITE)
        l1 = Text("軌道が有界に", font=FONT, font_size=22, color=ACCENT_CYAN)
        l2 = Text("留まる c の全体", font=FONT, font_size=22, color=ACCENT_CYAN)
        l3 = Text("境界は、いくら", font=FONT, font_size=22, color=ACCENT_PINK)
        l4 = Text("拡大しても複雑", font=FONT, font_size=22, color=ACCENT_PINK)
        panel = VGroup(
            rule, VGroup(l1, l2).arrange(DOWN, buff=0.12), VGroup(l3, l4).arrange(DOWN, buff=0.12)
        ).arrange(DOWN, buff=0.5)
        panel.move_to([3.6, 0.3, 0])

        used = 0.7 + 1.0
        coda = 2.3
        body = max(3.0, duration - used - coda)
        seg = body / 3.0

        # gentle continuous scale keeps motion through the body + staged reveals
        self.play(img.animate.scale(1.03), FadeIn(rule), run_time=seg)
        self.play(img.animate.scale(1.02), FadeIn(panel[1]), run_time=seg)
        self.play(img.animate.scale(1.02), FadeIn(panel[2]), run_time=seg)
        self.wait(coda)

    # -------------------------------------------------------------------- zoom
    def _build_zoom(self, duration):
        title = Text("拡大しても、複雑さは尽きない", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        cx, cy = -0.745, 0.113
        levels = [
            (-0.6, 0.0, 1.85, 1.25, "×1"),
            (cx, cy, 0.16, 0.11, "×12"),
            (cx, cy, 0.02, 0.0135, "×90"),
        ]
        mags = ["×1", "×12", "×90"]

        used = 0.7
        coda = 2.3
        body = max(3.0, duration - used - coda)
        per = body / 3.0

        cur_img = None
        cur_mag = None
        for k, (lx, ly, hwx, hwy, _m) in enumerate(levels):
            img = _fractal_image(lx, ly, hwx, hwy, 760, 514, 130)
            img.height = 3.5
            img.move_to([0, 0.15, 0])
            mag = Text(mags[k], font=FONT, font_size=26, color=ACCENT_GOLD)
            mag.move_to([4.6, 2.3, 0])
            if cur_img is None:
                self.play(FadeIn(img), FadeIn(mag), run_time=per * 0.7)
            else:
                self.play(
                    FadeOut(cur_img), FadeOut(cur_mag), FadeIn(img), FadeIn(mag), run_time=per * 0.7
                )
            # small dwell with a subtle scale so it is not static
            self.play(img.animate.scale(1.04), run_time=per * 0.3)
            cur_img = img
            cur_mag = mag

        note = Text("同じ形が、どこまでも現れる", font=FONT, font_size=22, color=ACCENT_PINK)
        note.move_to([-3.3, 2.3, 0])
        self.play(FadeIn(note), run_time=0.5)
        self.wait(coda)

    # ------------------------------------------------------------------- julia
    def _build_julia(self, duration):
        title = Text("ジュリア集合", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        img = _fractal_image(0.0, 0.0, 1.7, 1.21, 900, 640, 100, julia_c=-0.8 + 0.156j)
        img.height = 3.5
        img.move_to([-1.6, 0.25, 0])
        self.play(FadeIn(img), run_time=1.0)

        c_lab = MathTex(r"c = -0.8 + 0.156\,i", font_size=28, color=TEXT_WHITE)
        n1 = Text("固定した c に対する", font=FONT, font_size=22, color=ACCENT_CYAN)
        n2 = Text("z → z² + c の運命", font=FONT, font_size=22, color=ACCENT_CYAN)
        n3 = Text("をたどった図", font=FONT, font_size=22, color=ACCENT_CYAN)
        panel = VGroup(c_lab, VGroup(n1, n2, n3).arrange(DOWN, buff=0.12)).arrange(DOWN, buff=0.5)
        panel.move_to([3.6, 0.4, 0])

        used = 0.7 + 1.0
        coda = 2.3
        body = max(3.0, duration - used - coda)
        seg = body / 2.0
        self.play(img.animate.scale(1.03), FadeIn(c_lab), run_time=seg)
        self.play(img.animate.scale(1.02), FadeIn(panel[1]), run_time=seg)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "iteration": {"people": [], "years": []},
    "set": {"people": [], "years": []},
    "zoom": {"people": [], "years": []},
    "julia": {"people": [], "years": []},
}

SCENES = {
    "iteration": MandelbrotJulia,
    "set": MandelbrotJulia,
    "zoom": MandelbrotJulia,
    "julia": MandelbrotJulia,
}
