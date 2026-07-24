"""
brownian_ito_calculus.py - Why calculus breaks on a Brownian path, and Itô's fix (数学史記)

Episode 054 (Kiyosi Itô). Two intuition-level views of the heart of stochastic
calculus.

Modes:
    path (default)
        A Brownian sample path: continuous but nowhere differentiable. A smooth
        curve, magnified, approaches a straight tangent line -- but the Brownian
        path stays equally jagged at every magnification (statistical self-similar-
        ity), so no tangent exists and the slope dX/dt is undefined. Classical
        calculus df = f'(x)dx cannot be applied directly.
        Fixed params: deterministic path from numpy rng seed 7; main path on
        x in [-5, 5], baseline y=1.05, amplitude 1.0; two zoom insets below.
    ito
        The scaling that saves calculus: a Brownian increment is of size sqrt(dt),
        not dt, so in the Taylor expansion the second-order term (dX)^2 does NOT
        vanish -- it becomes dt: the rule (dW)^2 = dt. That leaves the extra
        correction (1/2)f''(X)dt, giving Ito's lemma
        df = f'(X)dX + (1/2)f''(X)dt. The (1/2)f'' term is the fingerprint of
        stochastic calculus.
        Fixed params: symbolic MathTex only (no path), pink highlight on the
        (dX)^2 term and on the (1/2)f'' correction.

All Japanese labels use Text(font=FONT). MathTex holds only ASCII/symbols, no
Japanese. Y range: about -1.9 to +3.05. No trailing FadeOut. Randomness is a
fixed numpy seed (deterministic render).
"""

import numpy as np
from manim import (
    Create,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Rectangle,
    Scene,
    SurroundingRectangle,
    Text,
    VGroup,
    VMobject,
    config,
)
from style import (
    ACCENT_CYAN,
    ACCENT_GOLD,
    ACCENT_PINK,
    BG_COLOR,
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
    pace,
)

config.background_color = BG_COLOR


def _polyline(pts, color, width=2.4, smooth=False):
    m = VMobject(color=color, stroke_width=width)
    corners = [np.array([x, y, 0.0]) for x, y in pts]
    if smooth:
        m.set_points_smoothly(corners)
    else:
        m.set_points_as_corners(corners)
    return m


class BrownianItoCalculus(Scene):
    """Brownian path (no tangent) and the (dW)^2 = dt rule behind Itô's lemma."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "path")
        duration = float(params.get("duration", 26))
        if mode == "ito":
            self._build_ito(duration)
        else:
            self._build_path(duration)

    # -------------------------------------------------------------- helpers
    def _master(self, n=1200, seed=7):
        rng = np.random.default_rng(seed)
        w = np.cumsum(rng.standard_normal(n))
        return w

    def _map_path(self, w, xl, xr, yb, amp):
        seg = w - w.mean()
        seg = seg / (np.abs(seg).max() + 1e-9) * amp
        xs = np.linspace(xl, xr, len(w))
        return list(zip(xs, yb + seg, strict=True))

    def _inset_pts(self, w, i0, i1, cx, cy, bw, bh):
        seg = w[i0:i1].astype(float)
        seg = seg - seg.mean()
        seg = seg / (np.abs(seg).max() + 1e-9) * (bh / 2 * 0.82)
        xs = np.linspace(cx - bw / 2 * 0.88, cx + bw / 2 * 0.88, len(seg))
        return list(zip(xs, cy + seg, strict=True))

    # ------------------------------------------------------------------ path
    def _build_path(self, duration):
        title = Text(
            "なめらかでない道 ── 接線が引けない",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "ブラウン運動は連続だが、どこを拡大しても同じ粗さ（自己相似）",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        # --- stage A: a smooth curve, magnified, becomes a straight tangent ---
        xs_s = np.linspace(-5.0, 5.0, 200)
        ys_s = 1.05 + 0.85 * np.exp(-(((xs_s + 1.2) / 2.6) ** 2)) - 0.15 * xs_s * 0.0
        smooth = _polyline(list(zip(xs_s, ys_s, strict=True)), ACCENT_CYAN, width=3.0, smooth=True)
        # point + small window near x = 1.4
        px = 1.4
        py = 1.05 + 0.85 * np.exp(-(((px + 1.2) / 2.6) ** 2))
        wbox = Rectangle(width=0.7, height=0.5, color=TEXT_DIM, stroke_width=2).move_to([px, py, 0])
        # inset: a near-straight tangent segment
        ins_c = [2.9, -0.75]
        ins_box = Rectangle(width=3.0, height=1.5, color=EDGE_COLOR, stroke_width=2).move_to(
            [ins_c[0], ins_c[1], 0]
        )
        tangent = Line(
            [ins_c[0] - 1.1, ins_c[1] - 0.28, 0],
            [ins_c[0] + 1.1, ins_c[1] + 0.32, 0],
            color=ACCENT_CYAN,
            stroke_width=4,
        )
        conn_a = Line(
            [px + 0.35, py - 0.25, 0],
            [ins_c[0] - 1.5, ins_c[1] + 0.75, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        labA = Text(
            "なめらかな曲線 ── 拡大すれば《接線》に近づく",
            font=FONT,
            font_size=19,
            color=ACCENT_CYAN,
        ).move_to([-2.4, -0.75, 0])
        groupA = VGroup(smooth, wbox, ins_box, tangent, conn_a, labA)

        # --- stage B: a Brownian path stays jagged at every magnification ---
        w = self._master()
        main_pts = self._map_path(w, -5.0, 5.0, 1.05, 1.0)
        bpath = _polyline(main_pts, TEXT_WHITE, width=2.2)
        blab = Text("ブラウン運動の道", font=FONT, font_size=18, color=TEXT_WHITE).move_to(
            [-4.0, 2.05, 0]
        )
        # window on the main path
        i0, i1 = 560, 720
        xs_main = np.linspace(-5.0, 5.0, len(w))
        seg_disp = (w - w.mean()) / (np.abs(w - w.mean()).max() + 1e-9) * 1.0 + 1.05
        wx0, wx1 = xs_main[i0], xs_main[i1]
        wy0, wy1 = seg_disp[i0:i1].min(), seg_disp[i0:i1].max()
        win = Rectangle(
            width=(wx1 - wx0) + 0.1,
            height=(wy1 - wy0) + 0.2,
            color=ACCENT_PINK,
            stroke_width=2.5,
        ).move_to([(wx0 + wx1) / 2, (wy0 + wy1) / 2, 0])
        # inset 1 (blow up window) -- still jagged; its own sub-window highlighted
        b1c = [-2.4, -0.72]
        box1 = Rectangle(width=3.1, height=1.5, color=EDGE_COLOR, stroke_width=2).move_to(
            [b1c[0], b1c[1], 0]
        )
        ins1 = _polyline(
            self._inset_pts(w, i0, i1, b1c[0], b1c[1], 3.1, 1.5), ACCENT_CYAN, width=2.0
        )
        sub1 = Rectangle(width=0.85, height=0.7, color=ACCENT_PINK, stroke_width=2).move_to(
            [b1c[0] + 0.2, b1c[1], 0]
        )
        conn1 = Line(
            [(wx0 + wx1) / 2, wy0 - 0.15, 0],
            [b1c[0] + 0.4, b1c[1] + 0.78, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        # inset 2 (blow up the sub-window) -- STILL jagged
        b2c = [2.4, -0.72]
        box2 = Rectangle(width=3.1, height=1.5, color=EDGE_COLOR, stroke_width=2).move_to(
            [b2c[0], b2c[1], 0]
        )
        ins2 = _polyline(
            self._inset_pts(w, 620, 680, b2c[0], b2c[1], 3.1, 1.5), ACCENT_GOLD, width=2.0
        )
        conn2 = Line(
            [b1c[0] + 0.55, b2c[1] + 0.05, 0],
            [b2c[0] - 1.4, b2c[1] + 0.05, 0],
            color=TEXT_DIM,
            stroke_width=1.5,
        )
        concl = Text(
            "どれだけ拡大しても同じギザギザ ── 傾き dX/dt が定まらない＝微分できない",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        ).move_to([0, -1.85, 0])

        coda = 3.2
        rt = pace(
            duration,
            [1.0, 0.9, 0.4, 0.5, 1.0, 0.7, 0.9, 0.9, 1.0],
            intro=0.6 + 0.5,
            coda=coda,
        )
        # stage A
        self.play(Create(smooth), run_time=rt[0])
        self.play(
            FadeIn(wbox),
            FadeIn(ins_box),
            Create(tangent),
            Create(conn_a),
            FadeIn(labA),
            run_time=rt[1],
        )
        self.wait(rt[2])
        self.play(FadeOut(groupA), run_time=rt[3])
        # stage B
        self.play(Create(bpath), FadeIn(blab), run_time=rt[4])
        self.play(Create(win), run_time=rt[5])
        self.play(FadeIn(box1), Create(ins1), FadeIn(sub1), Create(conn1), run_time=rt[6])
        self.play(FadeIn(box2), Create(ins2), Create(conn2), run_time=rt[7])
        self.play(FadeIn(concl), run_time=rt[8])
        self.wait(coda)

    # ------------------------------------------------------------------- ito
    def _build_ito(self, duration):
        title = Text(
            "√dt の魔法 ── 伊藤の補題",
            font=FONT,
            font_size=27,
            color=ACCENT_GOLD,
        ).move_to([0, 3.0, 0])
        sub = Text(
            "ブラウン運動の増分は dt でなく √dt で効く",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        ).move_to([0, 2.45, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(sub), run_time=0.5)

        # scaling comparison
        lab_ord = Text("ふつうの運動", font=FONT, font_size=18, color=TEXT_DIM).move_to(
            [-3.3, 1.72, 0]
        )
        eq_ord = MathTex(r"\Delta X \sim \Delta t", font_size=30, color=TEXT_DIM).move_to(
            [-3.3, 1.25, 0]
        )
        lab_bm = Text("ブラウン運動", font=FONT, font_size=18, color=ACCENT_CYAN).move_to(
            [2.9, 1.72, 0]
        )
        eq_bm = MathTex(r"\Delta X \sim \sqrt{\Delta t}", font_size=30, color=ACCENT_CYAN).move_to(
            [2.9, 1.22, 0]
        )

        # Taylor expansion, with the (dX)^2 term isolated
        taylor = MathTex(
            r"f(X+\Delta X)\approx f(X)+f'(X)\,\Delta X+",
            r"\tfrac{1}{2}f''(X)\,(\Delta X)^2",
            font_size=28,
            color=TEXT_WHITE,
        ).move_to([0, 0.5, 0])
        taylor[1].set_color(ACCENT_PINK)
        t_box = SurroundingRectangle(taylor[1], color=ACCENT_PINK, buff=0.06)

        # the famous rule: the surviving second-order term becomes dt
        rule = MathTex(r"(dW)^2 = dt", font_size=34, color=ACCENT_GOLD).move_to([0, -0.2, 0])
        rule_box = SurroundingRectangle(rule, color=ACCENT_GOLD, buff=0.1)
        note_sq = Text(
            "二次の項が消えず dt に化ける ── 補正項が残る",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        ).move_to([0, -0.75, 0])

        # Itô's lemma, correction term isolated
        lemma = MathTex(
            r"df = f'(X)\,dX + ",
            r"\tfrac{1}{2}f''(X)\,dt",
            font_size=30,
            color=TEXT_WHITE,
        ).move_to([0, -1.35, 0])
        lemma[1].set_color(ACCENT_PINK)
        l_box = SurroundingRectangle(lemma[1], color=ACCENT_PINK, buff=0.07)
        finger = Text(
            "この余分な項が、確率解析の《指紋》",
            font=FONT,
            font_size=17,
            color=ACCENT_PINK,
        ).move_to([0, -1.9, 0])

        coda = 3.5
        rt = pace(
            duration,
            [1.0, 1.0, 1.0, 0.9, 0.6, 0.8, 1.0, 0.7, 0.8],
            intro=0.6 + 0.5,
            coda=coda,
        )
        self.play(FadeIn(lab_ord), FadeIn(eq_ord), run_time=rt[0])
        self.play(FadeIn(lab_bm), FadeIn(eq_bm), run_time=rt[1])
        self.play(FadeIn(taylor), run_time=rt[2])
        self.play(Create(t_box), run_time=rt[3])
        self.play(FadeIn(rule), Create(rule_box), run_time=rt[4])
        self.play(FadeIn(note_sq), run_time=rt[5])
        self.play(FadeIn(lemma), run_time=rt[6])
        self.play(Create(l_box), run_time=rt[7])
        self.play(FadeIn(finger), run_time=rt[8])
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "path": {"people": [], "years": []},
    "ito": {"people": [], "years": []},
}

SCENES = {
    "path": BrownianItoCalculus,
    "ito": BrownianItoCalculus,
}
