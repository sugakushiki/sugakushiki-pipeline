"""
subharmonic_staircase.py - 分数調波の階段と、飛び移りの境目 for 数学史記

外から周期的な力を加えたファン・デル・ポール方程式

    y'' - k(1 - y^2) y' + y = A cos(lambda t)

で、外力の周波数 lambda を上げていくと、応答の周期が外力の 1 周期分、2 周期分、
3 周期分 …… と階段状に飛び移る (分数調波、周波数の分周)。そして段と段のあいだに、
どちらの周期にも落ち着かない帯がある。1927 年にファン・デル・ポールとファン・デル・
マルクが受話器で聞いた不規則な音は、この帯にあたる。

Modes:
    entrainment - 上に外力、下に応答を並べ、応答が外力に引き込まれて同じ周期で
                  進む様子を見せる。
                  Fixed params: k=5.0、A=2.0、lambda=0.70 (実測で分周比 1、ばらつき 0)

    staircase   - 横軸に外力の周波数 lambda、縦軸に「応答の周期 ÷ 外力の周期」を取る。
                  平坦な段 (引き込まれている) を金、定まらない帯を桃色の縦棒
                  (平均±標準偏差) で描く。
                  Fixed params: k=5.0、A=2.0、lambda=0.50〜3.50 を 0.05 刻みで 61 点。
                  段のラベルは周期比 (n 倍) で出す ── 縦軸が「応答の周期 ÷ 外力の周期」なので、
                  周波数比 1/n を書くと軸と逆数になって食い違う。段は n=1 (lambda 0.50-0.90) / n=2 (1.05-1.10) / n=3 (1.20-1.95) /
                  n=4 (2.20) / n=5 (2.45-2.95) / n=6 (3.30)。
                  **幅の広い段は n=1,3,5 の奇数側で、偶数側は狭い。**

    irregular   - lambda=2.00 の応答波形。外力の周期ごとに縦の目盛りを立て、
                  1 サイクルの長さが外力の何周期ぶんかを読む。
                  Fixed params: k=5.0、A=2.0、lambda=2.00 (外力周期 3.1416)、
                  表示する時間窓は 50。
                  **画面に出る数値はレンダ時に実際に描いた区間から計算する**
                  (固定の数列を並べると画面のサイクル数と個数が食い違うため)。
                  参照として事前に実測した連続 9 サイクルの比は
                  3.09, 3.56, 3.30, 3.07, 3.09, 3.61, 3.24, 3.06, 3.10 で、
                  3 でも 4 でもなく、同じ値も戻ってこない。窓の取り方で
                  どこから始まるかは変わるが、並びは同じものである。

固定値の出どころ: 本ファイル内の _integrate() と同じ RK4 (dt=0.004、t=0..300 のうち
後半だけを計測、1 サイクルは y が -1 を下回ったあと +1 を上抜けた時刻で数える) で
事前に実測した。段の値は標準偏差がちょうど 0.0000 で、定まらない帯は 0.10〜0.28。

**注意して書くこと**: これは実験の再現ではなく方程式の数値解である。ファン・デル・
ポールらの回路 (ネオン管の弛張発振器) とパラメータは対応しない。画面に「1/40 まで」
などの実験値を出さない。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 069 (カートライト) — 数学 B (引き込み / 分数調波 / 飛び移りの境目)。
"""

import math

from manim import (
    UP,
    Axes,
    Create,
    DashedLine,
    Dot,
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
    pace,
)

config.background_color = BG_COLOR

K = 5.0
A = 2.0

# (lambda, 応答周期/外力周期 の平均, その標準偏差) — 上の docstring の条件で実測。
# 標準偏差 0.0 の行が「引き込まれている」= 段。
STAIRCASE = [
    (0.50, 1.0, 0.0),
    (0.55, 1.0, 0.0),
    (0.60, 1.0, 0.0),
    (0.65, 1.0, 0.0),
    (0.70, 1.0, 0.0),
    (0.75, 1.0, 0.0),
    (0.80, 1.0, 0.0),
    (0.85, 1.0, 0.0),
    (0.90, 1.0, 0.0),
    (0.95, 1.2764, 0.2607),
    (1.00, 1.6855, 0.2038),
    (1.05, 2.0, 0.0),
    (1.10, 2.0, 0.0),
    (1.15, 2.2108, 0.1803),
    (1.20, 3.0, 0.0),
    (1.25, 3.0, 0.0),
    (1.30, 3.0, 0.0),
    (1.35, 3.0, 0.0),
    (1.40, 3.0, 0.0),
    (1.45, 3.0, 0.0),
    (1.50, 3.0, 0.0),
    (1.55, 3.0, 0.0),
    (1.60, 3.0, 0.0),
    (1.65, 3.0, 0.0),
    (1.70, 3.0, 0.0),
    (1.75, 3.0, 0.0),
    (1.80, 3.0, 0.0),
    (1.85, 3.0, 0.0),
    (1.90, 3.0, 0.0),
    (1.95, 3.0, 0.0),
    (2.00, 3.277, 0.2474),
    (2.05, 3.479, 0.2725),
    (2.10, 3.6556, 0.1156),
    (2.15, 3.8663, 0.1032),
    (2.20, 4.0, 0.0),
    (2.25, 4.0889, 0.0431),
    (2.30, 4.3006, 0.1384),
    (2.35, 4.4548, 0.2359),
    (2.40, 4.7271, 0.2815),
    (2.45, 5.0, 0.0),
    (2.50, 5.0, 0.0),
    (2.55, 5.0, 0.0),
    (2.60, 5.0, 0.0),
    (2.65, 5.0, 0.0),
    (2.70, 5.0, 0.0),
    (2.75, 5.0, 0.0),
    (2.80, 5.0, 0.0),
    (2.85, 5.0, 0.0),
    (2.90, 5.0, 0.0),
    (2.95, 5.0, 0.0),
    (3.00, 5.1602, 0.1648),
    (3.05, 5.3758, 0.1526),
    (3.10, 5.5213, 0.1095),
    (3.15, 5.6668, 0.066),
    (3.20, 5.791, 0.0518),
    (3.25, 5.9122, 0.0394),
    (3.30, 6.0, 0.0),
    (3.35, 6.1379, 0.0361),
    (3.40, 6.25, 0.0741),
    (3.45, 6.3677, 0.1207),
    (3.50, 6.5072, 0.2165),
]

# lambda=2.00 で実測した、連続する 9 サイクルの (サイクル長 / 外力周期)。
UNSETTLED_RATIOS = [3.09, 3.56, 3.30, 3.07, 3.09, 3.61, 3.24, 3.06, 3.10]


# ---------------------------------------------------------------------------
# 数値積分。sibling import を避けて自前に持つ (1 ファイル 1 Scene クラスを保つため)。
# ---------------------------------------------------------------------------
def _integrate(k, amp, lam, t_end, dt, y0=2.0, v0=0.0):
    """強制ファン・デル・ポールを RK4 で積分し (ts, ys) を返す。"""

    def f(t, y, v):
        return v, k * (1.0 - y * y) * v - y + amp * math.cos(lam * t)

    t, y, v = 0.0, y0, v0
    ts, ys = [t], [y]
    for _ in range(int(round(t_end / dt))):
        k1y, k1v = f(t, y, v)
        k2y, k2v = f(t + dt / 2, y + dt / 2 * k1y, v + dt / 2 * k1v)
        k3y, k3v = f(t + dt / 2, y + dt / 2 * k2y, v + dt / 2 * k2v)
        k4y, k4v = f(t + dt, y + dt * k3y, v + dt * k3v)
        y += dt / 6 * (k1y + 2 * k2y + 2 * k3y + k4y)
        v += dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        t += dt
        ts.append(t)
        ys.append(y)
    return ts, ys


def _tail(ts, ys, window, drop=0.5):
    """過渡を drop の割合だけ捨て、先頭を 0 に直した window 秒ぶんを返す。"""
    cut = int(len(ts) * drop)
    t0 = ts[cut]
    out = [(ts[i] - t0, ys[i]) for i in range(cut, len(ts)) if ts[i] - t0 <= window]
    step = max(1, len(out) // 800)
    return out[::step]


def _cycle_starts(pts, lo=-1.0, hi=1.0):
    """y が lo を下回ったあと hi を上抜けした時刻 = 1 サイクルの開始。"""
    out = []
    armed = False
    for i in range(1, len(pts)):
        if pts[i][1] < lo:
            armed = True
        elif armed and pts[i - 1][1] <= hi < pts[i][1]:
            out.append(pts[i][0])
            armed = False
    return out


LINT_FACTUAL_CLAIMS = {
    "entrainment": {"people": [], "years": []},
    "staircase": {"people": [], "years": []},
    "irregular": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "entrainment": ["波", "波形", "軸", "周期", "外力", "応答"],
    "staircase": ["階段", "段", "点", "軸", "棒", "平ら", "飛び移り"],
    "irregular": ["波", "波形", "軸", "目盛り", "間隔", "数値"],
}


class SubharmonicStaircase(Scene):
    """引き込み・分数調波の階段・飛び移りの境目の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "staircase")
        self._duration = float(params.get("duration", 25))

        if mode == "entrainment":
            self.build_entrainment()
        elif mode == "irregular":
            self.build_irregular()
        else:
            self.build_staircase()

    # ------------------------------------------------------------------
    # mode: entrainment
    # ------------------------------------------------------------------
    def build_entrainment(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 1.0, 0.6, 1.0, 0.8], intro=1.2, coda=CODA)
        lam = 0.70
        window = 40.0

        title = Text(
            "外から揺すると、その周期に引き込まれる", font=FONT, font_size=28, color=TEXT_WHITE
        )
        title.to_edge(UP, buff=0.5)

        def panel(cy, ylen):
            ax = Axes(
                x_range=[0, window, 10],
                y_range=[-2.8, 2.8, 1],
                x_length=10.4,
                y_length=ylen,
                axis_config={
                    "color": TEXT_DIM,
                    "stroke_width": 1.5,
                    "include_ticks": False,
                    "include_tip": False,
                },
            )
            ax.move_to([0.35, cy, 0])
            return ax

        ax_top = panel(1.60, 1.5)
        ax_bot = panel(-0.60, 1.6)

        lab_top = Text("外力", font=FONT, font_size=22, color=TEXT_DIM)
        lab_top.move_to([-6.10, 1.60, 0])
        lab_bot = Text("応答", font=FONT, font_size=22, color=ACCENT_CYAN)
        lab_bot.move_to([-6.10, -0.60, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(ax_top), FadeIn(ax_bot), FadeIn(lab_top), FadeIn(lab_bot), run_time=0.6)

        drive = ax_top.plot(
            lambda t: 2.2 * math.cos(lam * t),
            x_range=[0, window, 0.05],
            color=TEXT_DIM,
            stroke_width=3.0,
        )
        self.play(Create(drive), run_time=rt[0])

        ts, ys = _integrate(K, A, lam, 200.0, 0.004)
        pts = _tail(ts, ys, window)
        resp = ax_bot.plot_line_graph(
            x_values=[p[0] for p in pts],
            y_values=[p[1] for p in pts],
            line_color=ACCENT_CYAN,
            stroke_width=3.5,
            add_vertex_dots=False,
        )
        self.play(Create(resp), run_time=rt[1])
        self.wait(rt[2])

        # 外力の山ごとに縦線を立て、応答が同じ拍で立ち上がることを見せる
        grid = VGroup()
        Td = 2 * math.pi / lam
        n = 0
        while n * Td <= window:
            x = ax_top.c2p(n * Td, 0)[0]
            grid.add(
                DashedLine(
                    [x, ax_top.c2p(0, 2.8)[1], 0],
                    [x, ax_bot.c2p(0, -2.8)[1], 0],
                    color=ACCENT_GOLD,
                    stroke_width=1.4,
                    stroke_opacity=0.55,
                    dash_length=0.10,
                    dashed_ratio=0.45,
                )
            )
            n += 1
        note = Text("外力 1 回に、応答 1 回", font=FONT, font_size=24, color=ACCENT_GOLD)
        note.move_to([0.35, -1.92, 0])

        self.play(Create(grid), run_time=rt[3])
        self.play(FadeIn(note), run_time=rt[4])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: staircase
    # ------------------------------------------------------------------
    def build_staircase(self):
        CODA = 3.5
        rt = pace(self._duration, [1.0, 1.2, 1.0, 1.0, 0.8], intro=1.2, coda=CODA)

        title = Text(
            "外力を速くしていくと、応答の周期は段を登る", font=FONT, font_size=28, color=TEXT_WHITE
        )
        title.to_edge(UP, buff=0.5)

        axes = Axes(
            x_range=[0.4, 3.6, 0.5],
            y_range=[0, 7, 1],
            x_length=10.4,
            y_length=3.8,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0.30, 0.15, 0])

        y_cap = Text("応答の周期 ÷ 外力の周期", font=FONT, font_size=20, color=TEXT_DIM)
        y_cap.move_to([-3.55, 2.45, 0])
        x_cap = Text("外力の周波数 →", font=FONT, font_size=20, color=TEXT_DIM)
        x_cap.move_to([4.35, -1.92, 0])

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(axes), FadeIn(y_cap), FadeIn(x_cap), run_time=0.6)

        # 段 (標準偏差 0 = 引き込まれている) を連結して横棒にする
        locked = [(lam, ratio) for lam, ratio, sd in STAIRCASE if sd == 0.0]
        runs = []
        for lam, ratio in locked:
            n = round(ratio)
            if runs and runs[-1][0] == n and abs(lam - runs[-1][2] - 0.05) < 1e-6:
                runs[-1][2] = lam
            else:
                runs.append([n, lam, lam])

        bars = VGroup()
        tags = VGroup()
        for n, lo, hi in runs:
            x0 = axes.c2p(max(0.42, lo - 0.022), n)
            x1 = axes.c2p(min(3.58, hi + 0.022), n)
            bars.add(Line(x0, x1, color=ACCENT_GOLD, stroke_width=7.0))
            tag = Text(f"{n} 倍", font=FONT, font_size=20, color=ACCENT_GOLD)
            tag.move_to([(x0[0] + x1[0]) / 2, x0[1] + 0.30, 0])
            tags.add(tag)
        self.play(Create(bars), run_time=rt[0])
        self.play(FadeIn(tags), run_time=rt[1])

        # 定まらない帯 (平均 ± 標準偏差)
        spread = VGroup()
        for lam, ratio, sd in STAIRCASE:
            if sd == 0.0:
                continue
            top = axes.c2p(lam, min(6.9, ratio + sd))
            bot = axes.c2p(lam, max(0.1, ratio - sd))
            spread.add(Line(bot, top, color=ACCENT_PINK, stroke_width=3.0))
            spread.add(Dot(axes.c2p(lam, ratio), radius=0.035, color=ACCENT_PINK))
        self.play(Create(spread), run_time=rt[2])

        note = Text("段のあいだは決まらない", font=FONT, font_size=24, color=ACCENT_PINK)
        # 下端は「外力の周波数 →」が占めているので、右上の空きに置く。
        note.move_to([3.75, 2.45, 0])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(rt[4])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: irregular
    # ------------------------------------------------------------------
    def build_irregular(self):
        CODA = 4.0
        rt = pace(self._duration, [1.0, 0.9, 1.1, 1.0, 0.8], intro=1.2, coda=CODA)
        lam = 2.00
        Td = 2 * math.pi / lam
        window = 50.0

        title = Text(
            "段の境目では、次がいつ来るか決まらない", font=FONT, font_size=28, color=TEXT_WHITE
        )
        title.to_edge(UP, buff=0.5)

        axes = Axes(
            x_range=[0, window, 5],
            y_range=[-2.8, 2.8, 1],
            x_length=11.2,
            y_length=3.0,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0, 0.45, 0])

        eq = MathTex(
            r"\ddot{y} - k(1-y^{2})\,\dot{y} + y = A\cos(\lambda t)",
            font_size=28,
            color=ACCENT_CYAN,
        )
        eq.move_to([0, 2.62, 0])

        self.play(FadeIn(title), FadeIn(eq), run_time=0.6)
        self.play(FadeIn(axes), run_time=0.5)

        # 外力の周期ごとの目盛り
        grid = VGroup()
        n = 0
        while n * Td <= window:
            x = axes.c2p(n * Td, 0)[0]
            grid.add(
                DashedLine(
                    [x, axes.c2p(0, -2.8)[1], 0],
                    [x, axes.c2p(0, 2.8)[1], 0],
                    color=TEXT_DIM,
                    stroke_width=1.2,
                    stroke_opacity=0.45,
                    dash_length=0.09,
                    dashed_ratio=0.45,
                )
            )
            n += 1
        self.play(Create(grid), run_time=rt[0])

        ts, ys = _integrate(K, A, lam, 220.0, 0.004)
        pts = _tail(ts, ys, window)
        resp = axes.plot_line_graph(
            x_values=[p[0] for p in pts],
            y_values=[p[1] for p in pts],
            line_color=ACCENT_CYAN,
            stroke_width=3.5,
            add_vertex_dots=False,
        )
        self.play(Create(resp), run_time=rt[1])

        # サイクルの立ち上がりに印を打つ
        marks = VGroup()
        starts = _cycle_starts(pts)
        for s in starts:
            marks.add(Dot(axes.c2p(s, 1.0), radius=0.055, color=ACCENT_GOLD))
        self.play(FadeIn(marks), run_time=rt[2])

        # 各サイクルの長さが外力の何周期ぶんかを、その区間の真下に置く。
        # (固定の数列を並べると画面のサイクル数と個数が食い違う。UNSETTLED_RATIOS は
        #  docstring に残した実測の記録で、画面には実際に描いた区間の値を出す。)
        row = VGroup()
        for i in range(len(starts) - 1):
            ratio = (starts[i + 1] - starts[i]) / Td
            mid_x = (axes.c2p(starts[i], 0)[0] + axes.c2p(starts[i + 1], 0)[0]) / 2
            row.add(
                Text(f"{ratio:.2f}", font=FONT, font_size=26, color=ACCENT_GOLD).move_to(
                    [mid_x, -1.35, 0]
                )
            )
        cap = Text(
            "外力の何周期ぶんか ── 3 でも 4 でもない", font=FONT, font_size=22, color=ACCENT_PINK
        )
        cap.move_to([0, -1.92, 0])
        self.play(FadeIn(row), run_time=rt[3])
        self.play(FadeIn(cap), run_time=rt[4])
        self.wait(CODA)


SCENES = {
    "entrainment": SubharmonicStaircase,
    "staircase": SubharmonicStaircase,
    "irregular": SubharmonicStaircase,
}
