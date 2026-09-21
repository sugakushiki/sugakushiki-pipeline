"""
van_der_pol_limit_cycle.py - 自励振動とリミットサイクル for 数学史記

ファン・デル・ポール方程式

    y'' - k(1 - y^2) y' + y = 0

の振る舞いを描く。減衰して止まる振り子と違い、この系はどの初期状態から
出発しても同じ一つの閉じた振動に落ち着く。これがリミットサイクルであり、
三極管を使った発振回路が一定の振幅で鳴り続ける理由でもある。

Modes:
    damped_vs_self - 左に減衰振動 (y'' + 0.3 y' + y = 0)、右にファン・デル・ポール
                     (k=1) を並べ、それぞれ大小 2 つの初期振幅から出発させる。
                     左は 2 本とも 0 へ、右は 2 本とも同じ振幅へ。
                     Fixed params: 減衰係数 0.3、k=1.0、初期振幅 y0=0.4 と y0=3.0、
                     時間窓 t=0..40、収束先の振幅 |y| = 2.009

    phase_plane    - 相平面 (横軸 y、縦軸 y') に 5 本の軌道を流す。内側の 3 本は
                     外へ、外側の 2 本は内へ巻き、すべて同じ閉曲線に漸近する。
                     最後にその閉曲線を金色で重ねる。
                     Fixed params: k=1.0、初期値 (0.1,0) (0.5,0) (3.0,0) (0,3.0)
                     (-2.5,-1.0)、閉曲線は y in [-2.009, +2.009]、|y'|max = 2.678、
                     周期 6.664

    relaxation     - k を 0.3 -> 1 -> 3 -> 6 と上げ、波形が正弦波から
                     「急に立ち上がってゆっくり戻る」鋸の歯へ変わり、周期が
                     伸びていく様子を見せる。
                     Fixed params: 時間窓 t=0..30 固定、
                     周期は k=0.3 で 6.318、k=1 で 6.663、k=3 で 8.859、k=6 で 13.062、
                     振幅はどの k でも |y| ~ 2.0 のまま

固定値の出どころ: すべて本ファイル内の _integrate() と同じ RK4 で事前に実測した
(dt=0.0005〜0.002、過渡を半分捨てて計測)。k=1 の 5 通りの初期値はいずれも
y in [-2.009, +2.009]、|y'|max = 2.678、周期 6.664 で小数第 3 位まで一致した。
**k が大きいときの漸近公式 (3 - 2 log 2) k は k=6 では 9.68 で実測 13.06 と合わない
ので、画面には出さない。**

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 069 (カートライト) — 数学 A (自励振動とリミットサイクル / 緩和振動)。
"""

from manim import (
    RIGHT,
    UP,
    AnimationGroup,
    Axes,
    Create,
    DashedLine,
    FadeIn,
    FadeOut,
    MathTex,
    ReplacementTransform,
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
    pace,
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# 数値積分 (RK4)。外部依存を増やさず、レンダのたびに同じ軌道を出す。
# ---------------------------------------------------------------------------
def _integrate(deriv, y0, v0, t_end, dt):
    """RK4 で (t, y, v) の列を返す。deriv(t, y, v) -> (dy, dv)。"""
    t, y, v = 0.0, y0, v0
    ts, ys, vs = [t], [y], [v]
    steps = int(round(t_end / dt))
    for _ in range(steps):
        k1y, k1v = deriv(t, y, v)
        k2y, k2v = deriv(t + dt / 2, y + dt / 2 * k1y, v + dt / 2 * k1v)
        k3y, k3v = deriv(t + dt / 2, y + dt / 2 * k2y, v + dt / 2 * k2v)
        k4y, k4v = deriv(t + dt, y + dt * k3y, v + dt * k3v)
        y += dt / 6 * (k1y + 2 * k2y + 2 * k3y + k4y)
        v += dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        t += dt
        ts.append(t)
        ys.append(y)
        vs.append(v)
    return ts, ys, vs


def _vdp(k):
    """ファン・デル・ポール: y'' - k(1-y^2) y' + y = 0"""

    def deriv(_t, y, v):
        return v, k * (1.0 - y * y) * v - y

    return deriv


def _damped(c):
    """減衰振動: y'' + c y' + y = 0"""

    def deriv(_t, y, v):
        return v, -c * v - y

    return deriv


def _thin(points, target=700):
    """点列を target 点程度に間引く (描画コスト対策)。"""
    step = max(1, len(points) // target)
    return points[::step]


# Factual-claim metadata (qa_manim_consistency.py が読む)
LINT_FACTUAL_CLAIMS = {
    "damped_vs_self": {"people": [], "years": []},
    "phase_plane": {"people": [], "years": []},
    "relaxation": {"people": [], "years": []},
}

# ナレーションと画面の不一致 lint 用。この mode が実際に描くもの。
LINT_VISUAL_ELEMENTS = {
    "damped_vs_self": ["波", "振動", "軸", "曲線", "振幅", "時間"],
    "phase_plane": ["軌道", "曲線", "閉曲線", "渦", "軸", "縦軸", "横軸", "平面", "初期値"],
    "relaxation": ["波", "波形", "曲線", "軸", "周期", "時間"],
}


class VanDerPolLimitCycle(Scene):
    """自励振動・リミットサイクル・緩和振動の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "phase_plane")
        self._duration = float(params.get("duration", 25))

        if mode == "damped_vs_self":
            self.build_damped_vs_self()
        elif mode == "relaxation":
            self.build_relaxation()
        else:
            self.build_phase_plane()

    # ------------------------------------------------------------------
    # mode: damped_vs_self
    # ------------------------------------------------------------------
    def build_damped_vs_self(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 1.0, 0.5, 1.0, 1.0, 0.6, 1.0], intro=1.2, coda=CODA)

        title = Text(
            "放っておくと止まる振動と、止まらない振動", font=FONT, font_size=28, color=TEXT_WHITE
        )
        title.to_edge(UP, buff=0.5)

        def panel(cx):
            ax = Axes(
                x_range=[0, 40, 10],
                y_range=[-3.2, 3.2, 1],
                x_length=5.4,
                y_length=3.2,
                axis_config={
                    "color": TEXT_DIM,
                    "stroke_width": 1.5,
                    "include_ticks": False,
                    "include_tip": False,
                },
            )
            ax.move_to([cx, -0.05, 0])
            return ax

        ax_l, ax_r = panel(-3.5), panel(3.5)

        lab_l = Text("ふつうの振り子", font=FONT, font_size=24, color=TEXT_DIM)
        lab_l.move_to([-3.5, 2.55, 0])
        lab_r = Text("発振回路", font=FONT, font_size=24, color=ACCENT_GOLD)
        lab_r.move_to([3.5, 2.55, 0])

        eq_l = MathTex(r"\ddot{y} + 0.3\,\dot{y} + y = 0", font_size=26, color=TEXT_DIM)
        eq_l.move_to([-3.5, 1.95, 0])
        eq_r = MathTex(r"\ddot{y} - k(1-y^{2})\,\dot{y} + y = 0", font_size=26, color=ACCENT_CYAN)
        eq_r.move_to([3.5, 1.95, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(
            FadeIn(ax_l),
            FadeIn(ax_r),
            FadeIn(lab_l),
            FadeIn(lab_r),
            FadeIn(eq_l),
            FadeIn(eq_r),
            run_time=0.6,
        )

        # 左: 減衰 (2 つの初期振幅から、どちらも 0 へ)
        curves_l = []
        for y0, col in ((3.0, ACCENT_PINK), (0.4, ACCENT_CYAN)):
            ts, ys, _ = _integrate(_damped(0.3), y0, 0.0, 40.0, 0.005)
            pts = _thin(list(zip(ts, ys, strict=True)))
            curves_l.append(
                ax_l.plot_line_graph(
                    x_values=[p[0] for p in pts],
                    y_values=[p[1] for p in pts],
                    line_color=col,
                    stroke_width=3.0,
                    add_vertex_dots=False,
                )
            )
        self.play(Create(curves_l[0]), run_time=rt[0])
        self.play(Create(curves_l[1]), run_time=rt[1])
        self.wait(rt[2])

        # 右: ファン・デル・ポール (2 つの初期振幅から、どちらも同じ振幅へ)
        curves_r = []
        for y0, col in ((3.0, ACCENT_PINK), (0.4, ACCENT_CYAN)):
            ts, ys, _ = _integrate(_vdp(1.0), y0, 0.0, 40.0, 0.005)
            pts = _thin(list(zip(ts, ys, strict=True)))
            curves_r.append(
                ax_r.plot_line_graph(
                    x_values=[p[0] for p in pts],
                    y_values=[p[1] for p in pts],
                    line_color=col,
                    stroke_width=3.0,
                    add_vertex_dots=False,
                )
            )
        self.play(Create(curves_r[0]), run_time=rt[3])
        self.play(Create(curves_r[1]), run_time=rt[4])

        # 共通の振幅 (実測 2.009) を破線で示す
        guides = VGroup()
        for sgn in (+1, -1):
            p0 = ax_r.c2p(0, sgn * 2.009)
            p1 = ax_r.c2p(40, sgn * 2.009)
            guides.add(
                DashedLine(
                    p0, p1, color=ACCENT_GOLD, stroke_width=2.0, dash_length=0.12, dashed_ratio=0.5
                )
            )
        note = Text("同じ振幅に落ち着く", font=FONT, font_size=22, color=ACCENT_GOLD)
        note.move_to([3.5, -1.95, 0])

        self.play(Create(guides), FadeIn(note), run_time=rt[5])
        self.wait(rt[6])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: phase_plane
    # ------------------------------------------------------------------
    def build_phase_plane(self):
        CODA = 3.5
        inits = [(0.1, 0.0), (0.5, 0.0), (3.0, 0.0), (0.0, 3.0), (-2.5, -1.0)]
        # 重みは play 順に 1 対 1 で消費する (余らせると尺が埋まらない)。
        # 軌道 5 本 -> 閉曲線 -> 余韻前の間。
        weights = [1.0] * len(inits) + [1.2, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        title = Text(
            "どこから出発しても、同じ一つの振動へ", font=FONT, font_size=28, color=TEXT_WHITE
        )
        title.to_edge(UP, buff=0.5)

        axes = Axes(
            x_range=[-3.4, 3.4, 1],
            y_range=[-3.6, 3.6, 1],
            x_length=6.4,
            y_length=4.0,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0, 0.30, 0])

        x_lab = MathTex("y", font_size=28, color=TEXT_DIM)
        x_lab.next_to(axes.c2p(3.4, 0), RIGHT, buff=0.15)
        y_lab = MathTex(r"\dot{y}", font_size=28, color=TEXT_DIM)
        y_lab.next_to(axes.c2p(0, 3.6), UP, buff=0.10)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(x_lab), FadeIn(y_lab), run_time=0.6)

        # 5 本の軌道。内側から出るものと外側から入るものを色で分ける。
        idx = 0
        for y0, v0 in inits:
            ts, ys, vs = _integrate(_vdp(1.0), y0, v0, 26.0, 0.004)
            pts = _thin(list(zip(ys, vs, strict=True)), target=800)
            inside = (y0 * y0 + v0 * v0) < 4.0
            curve = axes.plot_line_graph(
                x_values=[p[0] for p in pts],
                y_values=[p[1] for p in pts],
                line_color=ACCENT_PINK if inside else ACCENT_CYAN,
                stroke_width=2.0,
                add_vertex_dots=False,
            )
            curve.set_stroke(opacity=0.75)
            self.play(Create(curve), run_time=rt[idx])
            idx += 1

        # 閉曲線そのもの (十分に時間を進めてから 1 周ぶんだけ取る)
        ts, ys, vs = _integrate(_vdp(1.0), 2.0, 0.0, 40.0, 0.002)
        start = int(len(ts) * 0.6)
        span = int(6.664 / 0.002)
        loop = list(zip(ys[start : start + span + 1], vs[start : start + span + 1], strict=True))
        loop = _thin(loop, target=800)
        cycle = axes.plot_line_graph(
            x_values=[p[0] for p in loop],
            y_values=[p[1] for p in loop],
            line_color=ACCENT_GOLD,
            stroke_width=5.0,
            add_vertex_dots=False,
        )

        cyc_lab = Text("リミットサイクル", font=FONT, font_size=22, color=ACCENT_GOLD)
        cyc_lab.move_to([4.75, 1.30, 0])
        init_lab = Text("初期値はばらばら", font=FONT, font_size=20, color=TEXT_DIM)
        init_lab.move_to([-4.95, 1.30, 0])

        self.play(Create(cycle), FadeIn(cyc_lab), FadeIn(init_lab), run_time=rt[-2])
        self.wait(rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: relaxation
    # ------------------------------------------------------------------
    def build_relaxation(self):
        CODA = 3.5
        # (k, 実測周期, 積分の刻み)
        table = [
            (0.3, 6.318, 0.002),
            (1.0, 6.663, 0.002),
            (3.0, 8.859, 0.001),
            (6.0, 13.062, 0.0005),
        ]
        # 重みは play 順に 1 対 1 で消費する。各 k について (変形, 間) の 2 つ。
        # intro には冒頭の固定 2 play (0.6+0.6) と末尾の tail play (0.5) を含める。
        weights = [1.0, 0.55] * len(table)
        rt = pace(self._duration, weights, intro=1.7, coda=CODA)

        title = Text("強くするほど、波は鋸の歯になる", font=FONT, font_size=28, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.5)
        eq = MathTex(r"\ddot{y} - k(1-y^{2})\,\dot{y} + y = 0", font_size=30, color=ACCENT_CYAN)
        eq.move_to([0, 2.62, 0])

        axes = Axes(
            x_range=[0, 30, 5],
            y_range=[-2.7, 2.7, 1],
            x_length=11.0,
            y_length=3.4,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0, 0.05, 0])
        t_lab = Text("時間", font=FONT, font_size=20, color=TEXT_DIM)
        t_lab.move_to([6.15, -1.85, 0])

        self.play(FadeIn(title), FadeIn(eq), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(t_lab), run_time=0.6)

        def curve_for(k, dt):
            # 過渡を捨ててから 30 秒ぶんを取る
            ts, ys, _ = _integrate(_vdp(k), 2.0, 0.0, 30.0 + 40.0, dt)
            off = int(40.0 / dt)
            seg = [(ts[i] - ts[off], ys[i]) for i in range(off, len(ts))]
            seg = [p for p in seg if p[0] <= 30.0]
            seg = _thin(seg, target=900)
            return axes.plot_line_graph(
                x_values=[p[0] for p in seg],
                y_values=[p[1] for p in seg],
                line_color=ACCENT_CYAN,
                stroke_width=3.5,
                add_vertex_dots=False,
            )

        def readout(k, period):
            g = VGroup(
                Text(f"k = {k:g}", font=FONT, font_size=26, color=ACCENT_GOLD),
                Text(f"周期 {period:.2f}", font=FONT, font_size=26, color=TEXT_WHITE),
            )
            g.arrange(RIGHT, buff=0.55)
            g.move_to([0, 1.98, 0])
            return g

        cur_curve = None
        cur_read = None
        step = 0
        for k, period, dt in table:
            new_curve = curve_for(k, dt)
            new_read = readout(k, period)
            if cur_curve is None:
                self.play(Create(new_curve), FadeIn(new_read), run_time=rt[step])
            else:
                # 曲線の変形だけを長く取り、文字は短く入れ替える。
                self.play(
                    AnimationGroup(
                        ReplacementTransform(cur_curve, new_curve, run_time=rt[step]),
                        FadeOut(cur_read, run_time=0.35),
                        FadeIn(new_read, run_time=0.45),
                        lag_ratio=0.0,
                    )
                )
            cur_curve, cur_read = new_curve, new_read
            step += 1
            self.wait(rt[step])
            step += 1

        tail = Text(
            "実際の発振回路は、この k が大きい側にある", font=FONT, font_size=22, color=ACCENT_GOLD
        )
        tail.move_to([0, -1.85, 0])
        self.play(FadeOut(t_lab), FadeIn(tail), run_time=0.5)
        self.wait(CODA)


SCENES = {
    "damped_vs_self": VanDerPolLimitCycle,
    "phase_plane": VanDerPolLimitCycle,
    "relaxation": VanDerPolLimitCycle,
}
