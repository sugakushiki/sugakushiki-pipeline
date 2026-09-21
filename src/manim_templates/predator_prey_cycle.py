"""
predator_prey_cycle.py - 捕食者と獲物の二本の式 (ロトカ・ヴォルテラ) for 数学史記

    dx/dt = a x - b x y      (獲物 x: 放っておけば増え、出会うと減る)
    dy/dt = -c y + d x y     (捕食者 y: 放っておけば飢え、出会うと増える)

すべての mode で a=1.0, b=0.5, c=0.75, d=0.25 を使う。
平衡点 (c/d, a/b) = (3.0, 2.0)。小さな揺れの周期 2π/√(ac) = 7.255。
保存量 V = d x - c ln x + b y - a ln y。軌道・平均・周期はレンダ時に RK4 で計算する
(座標のハードコード無し)。

Modes:
    fish_market - フィウメの魚市場でサメ・エイ (軟骨魚) が水揚げに占める割合、
                  1914〜1923 年の折れ線。戦争の期間 (1915〜18) を薄い帯で示し、
                  1914 / 1918 / 1923 の三点にラベル。
                  Fixed params: 12, 21, 22, 21, 36, 27, 16, 16, 15, 11 (%) の 10 点
                  (Braun, Differential Equations and Their Applications §4.10 の表を
                  Duke Univ. CCP 教材の丸め値で照合したもの)。

    equations   - 二本の式を項ごとに組み上げ、各項に日本語の札を付ける。
                  Fixed params: 式は上の 2 本、札は 4 枚 (放っておけば増える / 出会うと減る /
                  放っておけば飢える / 出会うと増える)。

    time_series - x(t) と y(t) の波を 0〜3 周期ぶん描き、獲物の山の後に捕食者の山が
                  来ることを破線で示す。
                  Fixed params: 初期値 (x, y) = (1.5, 2.0)、時間窓 0〜22 (約 3 周期)。

    phase_plane - 横 x 縦 y の平面に同心の閉軌道 3 本、中心に平衡点。点が中央の軌道を
                  scene 全編回り続ける (ValueTracker)。
                  Fixed params: 初期値 (x0, 2.0) で x0 = 2.2 / 1.4 / 0.7 の 3 本。

    averages    - 大小 2 本の軌道について一周の時間平均を数値で求め、どちらも中心に
                  落ちることを示す。
                  Fixed params: x0 = 2.2 (小) と 0.7 (大)。平均は (3.0, 2.0) に一致する
                  (小数第 1 位で表示)。

    harvesting  - 一律の間引き ε を入れる (a → a-ε, c → c+ε)。中心が (3.0, 2.0) から
                  ((c+ε)/d, (a-ε)/b) = (4.2, 1.4) へ動く: 獲物の平均が増え、捕食者の
                  平均が減る (第三法則)。
                  Fixed params: ε = 0.3。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 074 (ヴォルテラ) — 数学 1〜6。
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Arrow,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
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
    pace,
)

config.background_color = BG_COLOR

# ---------------------------------------------------------------------------
# モデル定数 (全 mode 共通)
# ---------------------------------------------------------------------------
A, B, C, D = 1.0, 0.5, 0.75, 0.25
EQ_X, EQ_Y = C / D, A / B  # 平衡点 (3.0, 2.0)
TITLE_Y = 3.05
TEXT_FADE = 0.5

# フィウメの魚市場: 軟骨魚の割合 (%)、1914〜1923 (丸め値)
FIUME_YEARS = list(range(1914, 1924))
FIUME_PCT = [12, 21, 22, 21, 36, 27, 16, 16, 15, 11]


# ---------------------------------------------------------------------------
# 数値積分 (RK4)。外部依存を増やさず、レンダのたびに同じ軌道を出す。
# ---------------------------------------------------------------------------
def _deriv(a, b, c, d):
    def f(x, y):
        return a * x - b * x * y, -c * y + d * x * y

    return f


def _integrate(f, x0, y0, t_end, dt):
    """RK4 で (t, x, y) の列を返す。"""
    t, x, y = 0.0, x0, y0
    ts, xs, ys = [t], [x], [y]
    steps = int(round(t_end / dt))
    for _ in range(steps):
        k1x, k1y = f(x, y)
        k2x, k2y = f(x + dt / 2 * k1x, y + dt / 2 * k1y)
        k3x, k3y = f(x + dt / 2 * k2x, y + dt / 2 * k2y)
        k4x, k4y = f(x + dt * k3x, y + dt * k3y)
        x += dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
        y += dt / 6 * (k1y + 2 * k2y + 2 * k3y + k4y)
        t += dt
        ts.append(t)
        xs.append(x)
        ys.append(y)
    return ts, xs, ys


def _one_period(f, x0, y0, dt=0.002, t_max=60.0):
    """(x0, y0) から出発して一周した点列 (閉軌道) と周期を返す。

    出発点は y = y0 の水平線上に取り、同じ向きに同じ線を横切った時点を一周とする。
    """
    ts, xs, ys = _integrate(f, x0, y0, t_max, dt)
    sign0 = ys[1] - ys[0]  # 出発直後に y が増えるか減るか
    for i in range(2, len(ts)):
        crossed = (ys[i - 1] - y0) * (ys[i] - y0) <= 0
        same_dir = (ys[i] - ys[i - 1]) * sign0 > 0
        if crossed and same_dir and ts[i] > dt * 10:
            return ts[: i + 1], xs[: i + 1], ys[: i + 1]
    raise RuntimeError("predator_prey_cycle: 一周を検出できない (t_max を増やす)")


def _thin(points, target=700):
    step = max(1, len(points) // target)
    return points[::step]


def _period_average(f, x0, y0):
    """一周の時間平均 (x̄, ȳ)。等間隔サンプルなので単純平均でよい。"""
    _ts, xs, ys = _one_period(f, x0, y0)
    n = len(xs) - 1  # 終点は始点と同じ位置なので外す
    return sum(xs[:n]) / n, sum(ys[:n]) / n


# Factual-claim metadata (qa_manim_consistency.py が読む)
LINT_FACTUAL_CLAIMS = {
    "fish_market": {"people": [], "years": ["1914", "1918", "1923"]},
    "equations": {"people": [], "years": []},
    "time_series": {"people": [], "years": []},
    "phase_plane": {"people": [], "years": []},
    "averages": {"people": [], "years": []},
    "harvesting": {"people": [], "years": []},
}

# ナレーションと画面の不一致 lint 用。この mode が実際に描くもの。
LINT_VISUAL_ELEMENTS = {
    "fish_market": ["折れ線", "点", "縦軸", "横軸", "帯", "割合"],
    "equations": ["式", "札", "文字"],
    "time_series": ["波", "曲線", "軸", "破線", "山", "時間"],
    "phase_plane": ["軌道", "輪", "閉曲線", "等高線", "点", "縦軸", "横軸", "平面", "中心"],
    "averages": ["軌道", "輪", "点", "中心", "平均", "座標"],
    "harvesting": ["軌道", "輪", "点", "中心", "矢印", "平均"],
}


class PredatorPreyCycle(Scene):
    """fish_market / equations / time_series / phase_plane / averages / harvesting。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "phase_plane")
        self._duration = float(params.get("duration", 30))
        builders = {
            "fish_market": self.build_fish_market,
            "equations": self.build_equations,
            "time_series": self.build_time_series,
            "phase_plane": self.build_phase_plane,
            "averages": self.build_averages,
            "harvesting": self.build_harvesting,
        }
        if mode not in builders:
            raise ValueError(
                f"predator_prey_cycle: unknown mode {mode!r} (valid: {sorted(builders)})"
            )
        builders[mode]()

    # ------------------------------------------------------------------
    # 共通部品
    # ------------------------------------------------------------------
    def _title(self, main, color=ACCENT_GOLD):
        t = Text(main, font=FONT, font_size=30, color=color).move_to([0, TITLE_Y, 0])
        self.play(FadeIn(t), run_time=0.6)
        return t

    def _show(self, mobjs, run_time, shape_anims=()):
        """テキストは短く入れて保持し、長い run_time は図形側だけに使う。"""
        t = min(TEXT_FADE, run_time)
        anims = [FadeIn(m, run_time=t) for m in mobjs]
        anims += [a for a in shape_anims]
        self.play(AnimationGroup(*anims, lag_ratio=0.0))
        longest = max([t] + [getattr(a, "run_time", t) for a in shape_anims])
        if run_time > longest:
            self.wait(run_time - longest)

    def _phase_axes(self, cx=-0.6, cy=0.35):
        axes = Axes(
            x_range=[0, 8.5, 1],
            y_range=[0, 5.2, 1],
            x_length=7.6,
            y_length=4.0,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": True,
                "tip_width": 0.15,
                "tip_height": 0.15,
            },
        )
        axes.move_to([cx, cy, 0])
        x_lab = Text("獲物の数", font=FONT, font_size=20, color=TEXT_DIM)
        x_lab.next_to(axes.c2p(8.5, 0), RIGHT, buff=0.15)
        y_lab = Text("捕食者の数", font=FONT, font_size=20, color=TEXT_DIM)
        y_lab.next_to(axes.c2p(0, 5.2), RIGHT, buff=0.15)
        return axes, VGroup(x_lab, y_lab)

    def _orbit_graph(self, axes, f, x0, color, width=2.5, opacity=0.85):
        _ts, xs, ys = _one_period(f, x0, EQ_Y)
        pts = _thin(list(zip(xs, ys, strict=True)), target=600)
        g = axes.plot_line_graph(
            x_values=[p[0] for p in pts],
            y_values=[p[1] for p in pts],
            line_color=color,
            stroke_width=width,
            add_vertex_dots=False,
        )
        g.set_stroke(opacity=opacity)
        return g, (xs, ys)

    # ------------------------------------------------------------------
    # mode: fish_market
    # ------------------------------------------------------------------
    def build_fish_market(self):
        CODA = 3.0
        n = len(FIUME_YEARS)
        # 帯 -> 点を一つずつ (10) -> ラベル 3 枚 -> 間
        weights = [0.6] + [0.5] * n + [0.8, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("フィウメの魚市場 ── サメ・エイの割合")

        axes = Axes(
            x_range=[1913.5, 1923.5, 1],
            y_range=[0, 42, 10],
            x_length=9.6,
            y_length=3.9,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0.2, 0.35, 0])
        year_labs = VGroup()
        for yr in FIUME_YEARS:
            lab = Text(str(yr), font=FONT, font_size=16, color=TEXT_DIM)
            lab.next_to(axes.c2p(yr, 0), DOWN, buff=0.12)
            year_labs.add(lab)
        pct_labs = VGroup()
        for v in (10, 20, 30, 40):
            lab = Text(f"{v}%", font=FONT, font_size=16, color=TEXT_DIM)
            lab.next_to(axes.c2p(1913.5, v), LEFT, buff=0.12)
            pct_labs.add(lab)
        self.play(FadeIn(axes), FadeIn(year_labs), FadeIn(pct_labs), run_time=0.6)

        # 戦争の期間 1915〜1918 を薄い帯で
        p0 = axes.c2p(1914.5, 0)
        p1 = axes.c2p(1918.5, 42)
        band = Rectangle(
            width=p1[0] - p0[0],
            height=p1[1] - p0[1],
            stroke_width=0,
            fill_color=ACCENT_PINK,
            fill_opacity=0.12,
        )
        band.move_to([(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0])
        band_lab = Text("第一次世界大戦 (漁が止まる)", font=FONT, font_size=18, color=ACCENT_PINK)
        band_lab.next_to(band, UP, buff=0.08)
        self._show([band, band_lab], rt[0])

        # 点を一つずつ、折れ線で結ぶ
        dots = []
        prev = None
        for i, (yr, v) in enumerate(zip(FIUME_YEARS, FIUME_PCT, strict=True)):
            p = axes.c2p(yr, v)
            dot = Dot(p, radius=0.07, color=ACCENT_CYAN)
            anims = [FadeIn(dot, run_time=min(0.4, rt[1 + i]))]
            if prev is not None:
                seg = Line(prev, p, color=ACCENT_CYAN, stroke_width=3.0)
                anims.append(Create(seg, run_time=rt[1 + i]))
            self.play(AnimationGroup(*anims, lag_ratio=0.0))
            if prev is None and rt[1 + i] > 0.4:
                self.wait(rt[1 + i] - 0.4)
            dots.append(dot)
            prev = p

        # 三点のラベル
        def tag(yr, v, txt, color, direction):
            t = Text(txt, font=FONT, font_size=22, color=color)
            t.next_to(axes.c2p(yr, v), direction, buff=0.18)
            return t

        tags = VGroup(
            tag(1914, 12, "12%", TEXT_WHITE, DOWN + LEFT * 0.3),
            tag(1918, 36, "36%", ACCENT_GOLD, UP),
            tag(1923, 11, "11%", TEXT_WHITE, DOWN + RIGHT * 0.3),
        )
        self._show(list(tags), rt[-2])
        note = Text(
            "漁をやめたら、\n食う側の取り分が増えた",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
            line_spacing=0.9,
        )
        note.move_to(axes.c2p(1921.8, 27))
        self._show([note], rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: equations
    # ------------------------------------------------------------------
    def build_equations(self):
        CODA = 3.0
        # 変数の説明 -> 式1 左辺 -> 項1 -> 項2 -> 式2 左辺 -> 項3 -> 項4 -> 間
        weights = [0.8, 0.6, 1.0, 1.0, 0.6, 1.0, 1.0, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("食う者と食われる者を、二本の式に書く")

        legend = VGroup(
            VGroup(
                MathTex("x", font_size=34, color=ACCENT_CYAN),
                Text("獲物の数", font=FONT, font_size=22, color=ACCENT_CYAN),
            ).arrange(RIGHT, buff=0.25),
            VGroup(
                MathTex("y", font_size=34, color=ACCENT_PINK),
                Text("捕食者の数", font=FONT, font_size=22, color=ACCENT_PINK),
            ).arrange(RIGHT, buff=0.25),
        ).arrange(RIGHT, buff=1.2)
        legend.move_to([0, 2.25, 0])
        self._show([legend], rt[0])

        # 式 1: dx/dt = a x - b x y
        e1 = MathTex(
            r"\frac{dx}{dt}", "=", r"a\,x", "-", r"b\,x\,y", font_size=44, color=TEXT_WHITE
        )
        e1.move_to([-0.6, 1.05, 0])
        e1[2].set_color(ACCENT_CYAN)
        e1[4].set_color(ACCENT_CYAN)
        # 式 2: dy/dt = -c y + d x y
        e2 = MathTex(
            r"\frac{dy}{dt}", "=", r"-\,c\,y", "+", r"d\,x\,y", font_size=44, color=TEXT_WHITE
        )
        e2.move_to([-0.6, -0.75, 0])
        e2[2].set_color(ACCENT_PINK)
        e2[4].set_color(ACCENT_PINK)

        def card(txt, target, color, direction=DOWN):
            t = Text(txt, font=FONT, font_size=20, color=color)
            # 上に置く札は項の左端に揃える (分数の分子に被らないように)
            if direction is UP:
                t.next_to(target, UP, buff=0.22, aligned_edge=LEFT)
            else:
                t.next_to(target, direction, buff=0.22)
            return t

        self._show([e1[0], e1[1]], rt[1])
        self._show([e1[2], card("放っておけば増える", e1[2], ACCENT_CYAN, UP)], rt[2])
        self._show([e1[3], e1[4], card("出会うと減る", e1[4], ACCENT_CYAN)], rt[3])
        self._show([e2[0], e2[1]], rt[4])
        self._show([e2[2], card("放っておけば飢える", e2[2], ACCENT_PINK, UP)], rt[5])
        self._show([e2[3], e2[4], card("出会うと増える", e2[4], ACCENT_PINK)], rt[6])

        side = VGroup(
            Text("出会う回数は", font=FONT, font_size=20, color=TEXT_DIM),
            MathTex(r"x \times y", font_size=30, color=TEXT_DIM),
            Text("に比例する", font=FONT, font_size=20, color=TEXT_DIM),
        ).arrange(DOWN, buff=0.18)
        side.move_to([4.6, 0.15, 0])
        self._show([side], rt[7])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: time_series
    # ------------------------------------------------------------------
    def build_time_series(self):
        CODA = 3.0
        # 軸 -> 波を描く (長い) -> 遅れの破線 -> 結び
        weights = [0.5, 3.0, 1.0, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("誰も揺らしていないのに、揺れ続ける")

        T_END = 22.0
        axes = Axes(
            x_range=[0, T_END, 5],
            y_range=[0, 6.2, 1],
            x_length=10.4,
            y_length=3.7,
            axis_config={
                "color": TEXT_DIM,
                "stroke_width": 1.5,
                "include_ticks": False,
                "include_tip": False,
            },
        )
        axes.move_to([0, 0.35, 0])
        t_lab = Text("時間", font=FONT, font_size=20, color=TEXT_DIM)
        t_lab.next_to(axes.c2p(T_END, 0), DOWN, buff=0.12)
        legend = VGroup(
            Text("獲物", font=FONT, font_size=22, color=ACCENT_CYAN),
            Text("捕食者", font=FONT, font_size=22, color=ACCENT_PINK),
        ).arrange(RIGHT, buff=0.8)
        legend.move_to([0, 2.45, 0])
        self._show([axes, t_lab, legend], rt[0])

        f = _deriv(A, B, C, D)
        ts, xs, ys = _integrate(f, 1.5, 2.0, T_END, 0.004)
        pts_x = _thin(list(zip(ts, xs, strict=True)), target=900)
        pts_y = _thin(list(zip(ts, ys, strict=True)), target=900)
        gx = axes.plot_line_graph(
            x_values=[p[0] for p in pts_x],
            y_values=[p[1] for p in pts_x],
            line_color=ACCENT_CYAN,
            stroke_width=3.5,
            add_vertex_dots=False,
        )
        gy = axes.plot_line_graph(
            x_values=[p[0] for p in pts_y],
            y_values=[p[1] for p in pts_y],
            line_color=ACCENT_PINK,
            stroke_width=3.5,
            add_vertex_dots=False,
        )
        self.play(Create(gx), Create(gy), run_time=rt[1], rate_func=linear)

        # 山の位置 (獲物の最初の山と、その後に来る捕食者の山)
        def first_peak(vals, start=1):
            for i in range(start, len(vals) - 1):
                if vals[i - 1] < vals[i] >= vals[i + 1]:
                    return i
            return None

        ix = first_peak(xs)
        iy = first_peak(ys, start=ix)
        lines = VGroup()
        for i, col in ((ix, ACCENT_CYAN), (iy, ACCENT_PINK)):
            lines.add(
                DashedLine(
                    axes.c2p(ts[i], 0),
                    axes.c2p(ts[i], 6.0),
                    color=col,
                    stroke_width=2.0,
                    dash_length=0.12,
                )
            )
        lag = Text("獲物の山のあとに、捕食者の山", font=FONT, font_size=22, color=ACCENT_GOLD)
        lag.move_to([0, -1.85, 0])
        self._show([lines], rt[2])
        self._show([lag], rt[3])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: phase_plane
    # ------------------------------------------------------------------
    def build_phase_plane(self):
        CODA = 3.0
        x0s = [2.2, 1.4, 0.7]
        # 軸 -> 軌道 3 本 -> 中心 -> 運動 (点が回り続ける。重みを大きく取る)
        weights = [0.5, 1.0, 1.0, 1.0, 0.8, 4.0]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)
        motion = max(2.0, rt[5])

        self._title("一周する軌道")
        axes, labs = self._phase_axes()
        self._show([axes, labs], rt[0])

        f = _deriv(A, B, C, D)
        orbits = []
        for i, (x0, col) in enumerate(
            zip(x0s, (ACCENT_CYAN, ACCENT_CYAN, ACCENT_CYAN), strict=True)
        ):
            g, data = self._orbit_graph(axes, f, x0, col, opacity=0.55 + 0.15 * i)
            orbits.append((g, data))
            self.play(Create(g), run_time=rt[1 + i])

        center = Dot(axes.c2p(EQ_X, EQ_Y), radius=0.09, color=ACCENT_GOLD)
        c_lab = Text("中心: どちらの数も動かない", font=FONT, font_size=20, color=ACCENT_GOLD)
        c_lab.move_to([4.55, 1.9, 0])
        self._show([center, c_lab], rt[4])

        # 中央の軌道を点が回り続ける (scene 全編)
        xs, ys = orbits[1][1]
        n = len(xs)
        tracker = ValueTracker(0.0)

        def make_dot():
            k = int(tracker.get_value()) % n
            return Dot(axes.c2p(xs[k], ys[k]), radius=0.1, color=ACCENT_PINK)

        runner = always_redraw(make_dot)
        self.add(runner)
        laps = max(1.0, motion / 6.0)
        self.play(tracker.animate.set_value(n * laps), run_time=motion, rate_func=linear)
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: averages
    # ------------------------------------------------------------------
    def build_averages(self):
        CODA = 3.0
        # 軸 -> 軌道 2 本 -> 平均点 2 つ -> 数値 -> 結び
        weights = [0.5, 1.0, 1.0, 1.0, 1.0, 0.8, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("揺れの大きさによらず、平均は同じ")
        axes, labs = self._phase_axes()
        self._show([axes, labs], rt[0])

        f = _deriv(A, B, C, D)
        g_small, _ = self._orbit_graph(axes, f, 2.2, ACCENT_CYAN)
        g_large, _ = self._orbit_graph(axes, f, 0.7, ACCENT_PINK)
        s_lab = Text("小さな揺れ", font=FONT, font_size=20, color=ACCENT_CYAN)
        s_lab.move_to([4.55, 2.35, 0])
        l_lab = Text("大きな揺れ", font=FONT, font_size=20, color=ACCENT_PINK)
        l_lab.move_to([4.55, 1.85, 0])
        self._show([s_lab], rt[1], shape_anims=[Create(g_small, run_time=rt[1])])
        self._show([l_lab], rt[2], shape_anims=[Create(g_large, run_time=rt[2])])

        avg_s = _period_average(f, 2.2, EQ_Y)
        avg_l = _period_average(f, 0.7, EQ_Y)
        d_s = Dot(axes.c2p(*avg_s), radius=0.11, color=ACCENT_CYAN)
        d_l = Dot(axes.c2p(*avg_l), radius=0.08, color=ACCENT_PINK)
        self._show([d_s], rt[3])
        self._show([d_l], rt[4])

        nums = VGroup(
            Text(
                f"獲物の平均  {avg_s[0]:.1f} / {avg_l[0]:.1f}",
                font=FONT,
                font_size=20,
                color=TEXT_WHITE,
            ),
            Text(
                f"捕食者の平均  {avg_s[1]:.1f} / {avg_l[1]:.1f}",
                font=FONT,
                font_size=20,
                color=TEXT_WHITE,
            ),
        ).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        nums.move_to([4.55, 0.55, 0])
        self._show([nums], rt[5])
        concl = Text("どちらも、輪の中心に落ちる", font=FONT, font_size=24, color=ACCENT_GOLD)
        concl.move_to([0, -1.85, 0])
        self._show([concl], rt[6])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: harvesting
    # ------------------------------------------------------------------
    def build_harvesting(self):
        CODA = 3.0
        EPS = 0.3
        # 軸 -> 軌道 (漁なし) + 中心 -> 漁を入れる (軌道 + 中心 + 矢印) -> 二行の結論 -> 結び
        weights = [0.5, 1.2, 0.6, 1.4, 1.0, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("両方を一律に間引くと")
        axes, labs = self._phase_axes()
        self._show([axes, labs], rt[0])

        f0 = _deriv(A, B, C, D)
        g0, _ = self._orbit_graph(axes, f0, 1.4, ACCENT_CYAN)
        c0 = Dot(axes.c2p(EQ_X, EQ_Y), radius=0.09, color=ACCENT_CYAN)
        lab0 = Text("漁なし", font=FONT, font_size=20, color=ACCENT_CYAN)
        lab0.next_to(g0, UP, buff=0.12)
        self._show([c0, lab0], rt[1], shape_anims=[Create(g0, run_time=rt[1])])
        self.wait(rt[2])

        # 一律の間引き: a -> a - eps, c -> c + eps
        a1, c1 = A - EPS, C + EPS
        ex, ey = c1 / D, a1 / B
        f1 = _deriv(a1, B, c1, D)
        _ts, xs1, ys1 = _one_period(f1, ex - (EQ_X - 1.4), ey)
        pts = _thin(list(zip(xs1, ys1, strict=True)), target=600)
        g1 = axes.plot_line_graph(
            x_values=[p[0] for p in pts],
            y_values=[p[1] for p in pts],
            line_color=ACCENT_PINK,
            stroke_width=2.5,
            add_vertex_dots=False,
        )
        c1_dot = Dot(axes.c2p(ex, ey), radius=0.09, color=ACCENT_PINK)
        lab1 = Text("漁あり", font=FONT, font_size=20, color=ACCENT_PINK)
        lab1.next_to(g1, DOWN, buff=0.12)
        arrow = Arrow(
            axes.c2p(EQ_X, EQ_Y),
            axes.c2p(ex, ey),
            buff=0.12,
            color=ACCENT_GOLD,
            stroke_width=4,
            max_tip_length_to_length_ratio=0.25,
        )
        self._show([c1_dot, lab1, arrow], rt[3], shape_anims=[Create(g1, run_time=rt[3])])

        concl = VGroup(
            Text("獲物の平均は 増える", font=FONT, font_size=22, color=ACCENT_CYAN),
            Text("捕食者の平均は 減る", font=FONT, font_size=22, color=ACCENT_PINK),
        ).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        concl.move_to([4.55, 2.1, 0])
        self._show([concl], rt[4])
        tail = Text("獲るのをやめると、逆向きに戻る", font=FONT, font_size=24, color=ACCENT_GOLD)
        tail.move_to([0, -1.85, 0])
        self._show([tail], rt[5])
        self.wait(CODA)


SCENES = {
    "fish_market": PredatorPreyCycle,
    "equations": PredatorPreyCycle,
    "time_series": PredatorPreyCycle,
    "phase_plane": PredatorPreyCycle,
    "averages": PredatorPreyCycle,
    "harvesting": PredatorPreyCycle,
}
