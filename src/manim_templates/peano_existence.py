"""
peano_existence.py - 方向場・解の一意性・解の非一意性 (ペアノ 1886/1890) for 数学史記

微分方程式を「平面のどの点にも進む向きが一つ決まっている規則」として描き、
歯止め (リプシッツ条件) があるときの一本道と、歯止めを外したときに現れる
無限の解の束を対比する。解曲線はレンダ時に数値積分または閉じた式から作る
(座標のハードコード無し)。

Modes:
    direction_field  - 格子点に短い線分で向きを描き、出発点に置いた点が向きに沿って
                       進む。道は 1 本だけ (2 本描くと非一意性の先取りに見える)。
                       Fixed params: 向きの規則 dy/dx = x - y、格子は x = -3.2..3.2 を 13 点、
                       y = -1.4..1.8 を 8 点、出発点は (-3.0, 1.4) の 1 点だけ、
                       数値積分は 4 次ルンゲ=クッタ、刻み 0.02。

    lipschitz_unique - 向きが場所だけで決まる規則 dy/dx = 0.45 x を使う。解は上下に
                       平行移動した同じ放物線なので、近い三つの出発点から出た道は
                       どこまでも同じ間隔を保ち、交わらない。真ん中を太く描く。
                       Fixed params: 出発点は x = -3.0 の y = 1.5 / 1.1 / 0.7、間隔 0.4。

    two_futures      - y' = 3 y^(2/3) の原点から、ずっと 0 のままの道と三乗の曲線の
                       二本が同時に伸びる。式は数式記号だけで組む (日本語を入れない)。
                       Fixed params: x = 0..2.0、y = x^3 をそのまま描く (縦は 0..8 の目盛)。

    funnel           - 立ち上がる時刻 t2 を変えた解の族を扇のように描き、最も上を通る道
                       (三乗の曲線) と最も下を通る道 (0 のまま) を太く残す。
                       Fixed params: t2 は 0.0 から 1.5 を 7 等分、x = 0..2.0。

    arbitrary_choice - 横に並ぶ集まり (楕円) から一つずつ選ぶ絵。前半は選ぶ位置が
                       そのつど変わり (任意の規則)、後半は各集まりの一番上の点に
                       固定される (決まった規則)。右端は「…」で無限を示す。
                       Fixed params: 集まりは 5 個 + 省略記号、各集まりの点は 4 個。

    curve_tiles      - 面を埋める曲線。原論文 (Math. Ann. 36) の三進法の式をそのまま
                       実装して点列を作り (_peano_points)、1 段 (9 点) → 2 段 (81 点)
                       → 3 段 (729 点) と細かくして正方形が埋まる様子を見せ、最後に
                       別荘のテラスの白黒タイルに見立てる。
                       Fixed params: 正方形の一辺 3.5、タイルは 1 段目の 3x3 の 9 マスを
                       通る順に白と黒で塗り分ける。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。末尾 FadeOut 無し。

Used by: Episode 076 (ペアノ) — 数学 1〜6、数学 10。
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    AnimationGroup,
    Axes,
    Create,
    Dot,
    Ellipse,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    MoveAlongPath,
    ReplacementTransform,
    Scene,
    Square,
    Text,
    VGroup,
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

CODA = 2.5

# 方向場を描く窓 (direction_field / lipschitz_unique 共通)
X_MIN, X_MAX = -3.2, 3.2
Y_MIN, Y_MAX = -1.4, 1.8


def _slope_xy(x, y):
    """dy/dx = x - y。解は互いに引き寄せ合う (方向場の例として使う)。"""
    return x - y


def _slope_x(x, y):
    """dy/dx = 0.45 x。向きが場所だけで決まるので、解は平行移動した同じ放物線。"""
    return 0.45 * x


def _rk4(slope, x0, y0, x_end, h=0.02):
    """4 次ルンゲ=クッタで解曲線の点列を作る。"""
    pts = [(x0, y0)]
    x, y = x0, y0
    steps = int(abs(x_end - x0) / h)
    sign = 1.0 if x_end >= x0 else -1.0
    for _ in range(steps):
        k1 = slope(x, y)
        k2 = slope(x + sign * h / 2, y + sign * h * k1 / 2)
        k3 = slope(x + sign * h / 2, y + sign * h * k2 / 2)
        k4 = slope(x + sign * h, y + sign * h * k3)
        y = y + sign * h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        x = x + sign * h
        pts.append((x, y))
    return pts


def _peano_points(order):
    """ペアノ 1890 年の論文の式で、正方形を埋める曲線の点列を作る。

    原論文 (Math. Ann. 36, 157-160) の構成をそのまま写す。三進法で
    t = 0.a1 a2 a3 ... に対し

        b1 = a1,                   c1 = k^(a1) a2
        bn = k^(a2+a4+...+a_{2n-2}) a_{2n-1}
        cn = k^(a1+a3+...+a_{2n-1}) a_{2n}

    (k は数字 a を 2 - a に移す操作。偶数回なら元のまま、奇数回なら 2 - a)
    として x = 0.b1 b2 ..., y = 0.c1 c2 ...。order 桁で打ち切ると 9^order 個の点になる。
    """

    def k_pow(m, a):
        return a if m % 2 == 0 else 2 - a

    pts = []
    for idx in range(3 ** (2 * order)):
        a = []  # a[0] = a1, a[1] = a2, ...
        v = idx
        for pos in range(2 * order):
            p = 3 ** (2 * order - 1 - pos)
            a.append(v // p)
            v = v % p
        bs, cs = [], []
        for n in range(1, order + 1):
            odd_sum = sum(a[2 * j] for j in range(n - 1))  # a1, a3, ... a_{2n-3}
            even_sum = sum(a[2 * j + 1] for j in range(n - 1))  # a2, a4, ... a_{2n-2}
            bs.append(k_pow(even_sum, a[2 * n - 2]))
            cs.append(k_pow(odd_sum + a[2 * n - 2], a[2 * n - 1]))
        x = sum(b / 3 ** (i + 1) for i, b in enumerate(bs))
        y = sum(c / 3 ** (i + 1) for i, c in enumerate(cs))
        pts.append((x, y))
    return pts


LINT_FACTUAL_CLAIMS = {
    "direction_field": {"people": [], "years": []},
    "lipschitz_unique": {"people": [], "years": []},
    "two_futures": {"people": [], "years": []},
    "funnel": {"people": [], "years": []},
    "arbitrary_choice": {"people": [], "years": []},
    "curve_tiles": {"people": [], "years": []},
}

# 「その mode が画面に出すもの」の宣言。矢印は描いていないので挙げない
# (方向場は矢じりの無い短い線分、選択の印も短い線)。
LINT_VISUAL_ELEMENTS = {
    "direction_field": ["縦軸", "横軸", "線分", "点", "曲線", "格子"],
    "lipschitz_unique": ["縦軸", "横軸", "線分", "曲線", "点"],
    "two_futures": ["縦軸", "横軸", "曲線", "点", "式"],
    "funnel": ["縦軸", "横軸", "曲線", "点", "束"],
    "arbitrary_choice": ["点", "集まり", "印"],
    "curve_tiles": ["正方形", "曲線", "格子", "タイル"],
}


class PeanoExistence(Scene):
    """direction_field / lipschitz_unique / two_futures / funnel / arbitrary_choice。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = float(params.get("duration", 20.0))
        mode = params.get("mode", "direction_field")

        if mode == "lipschitz_unique":
            self._lipschitz_unique(duration)
        elif mode == "two_futures":
            self._two_futures(duration)
        elif mode == "funnel":
            self._funnel(duration)
        elif mode == "arbitrary_choice":
            self._arbitrary_choice(duration)
        elif mode == "curve_tiles":
            self._curve_tiles(duration)
        else:
            self._direction_field(duration)

    # ------------------------------------------------------------------ 共通
    def _field_axes(self):
        axes = Axes(
            x_range=[X_MIN, X_MAX, 1.0],
            y_range=[Y_MIN, Y_MAX, 1.0],
            x_length=9.4,
            y_length=3.9,
            axis_config={"color": EDGE_COLOR, "include_ticks": False, "stroke_width": 2},
        )
        axes.move_to([0.0, 0.25, 0.0])
        return axes

    def _cubic_axes(self):
        """非一意性の例を描く窓。縦は 0..8 まで取り、三乗の曲線を切らずに描く。"""
        axes = Axes(
            x_range=[-0.15, 2.05, 0.5],
            y_range=[-0.6, 8.6, 2.0],
            x_length=8.2,
            y_length=4.1,
            axis_config={"color": EDGE_COLOR, "include_ticks": False, "stroke_width": 2},
        )
        axes.move_to([0.3, 0.15, 0.0])
        return axes

    def _field_segments(self, axes, slope, nx=13, ny=8):
        segs = VGroup()
        for xi in np.linspace(X_MIN + 0.25, X_MAX - 0.25, nx):
            for yi in np.linspace(Y_MIN + 0.2, Y_MAX - 0.2, ny):
                ang = np.arctan(slope(xi, yi))
                dx = 0.16 * np.cos(ang)
                dy = 0.16 * np.sin(ang)
                segs.add(
                    Line(
                        axes.c2p(xi - dx, yi - dy),
                        axes.c2p(xi + dx, yi + dy),
                        color=TEXT_DIM,
                        stroke_width=2.2,
                    )
                )
        return segs

    def _solution_path(self, axes, slope, x0, y0, x_end, color, width):
        pts = [axes.c2p(x, y) for x, y in _rk4(slope, x0, y0, x_end)]
        line = Line(pts[0], pts[1], color=color, stroke_width=width)
        line.set_points_as_corners(pts)
        return line

    def _cubic_path(self, axes, t2, color, width, x_from=0.0, x_to=2.0):
        """t2 で立ち上がる解 (x <= t2 では 0、x > t2 では (x - t2)^3)。"""
        pts = []
        for x in np.linspace(x_from, x_to, 240):
            y = 0.0 if x <= t2 else (x - t2) ** 3
            pts.append(axes.c2p(x, y))
        line = Line(pts[0], pts[1], color=color, stroke_width=width)
        line.set_points_as_corners(pts)
        return line

    # ------------------------------------------------------- mode: 方向場
    def _direction_field(self, duration):
        axes = self._field_axes()
        segs = self._field_segments(axes, _slope_xy)
        title = Text(
            "どの点にも、進む向きが決まっている", font=FONT, font_size=26, color=ACCENT_GOLD
        )
        title.move_to([0.0, 2.85, 0.0])

        rt = pace(duration, [1.0, 1.0, 3.4, 0.8], intro=0.6, coda=CODA)

        self.play(Create(axes), run_time=rt[0])
        self.play(FadeIn(segs), FadeIn(title, run_time=0.5), run_time=rt[1])

        # 道は 1 本だけ描く。2 本出すと、この時点ではまだ伏せている非一意性
        # (同じ出発点から複数の道) を先取りして見えてしまう
        curve = self._solution_path(axes, _slope_xy, -3.0, 1.4, 3.0, ACCENT_CYAN, 5.0)
        dot = Dot(axes.c2p(-3.0, 1.4), color=ACCENT_CYAN, radius=0.08)
        self.add(dot)
        self.play(
            AnimationGroup(
                Create(curve, run_time=rt[2]),
                MoveAlongPath(dot, curve, run_time=rt[2]),
                lag_ratio=0.0,
            )
        )
        note = Text("出発点を決めれば、道は一本", font=FONT, font_size=21, color=TEXT_WHITE)
        note.move_to([0.0, -1.85, 0.0])
        self.play(FadeIn(note), run_time=rt[3])
        self.wait(CODA)

    # --------------------------------------------------- mode: 一意性 (歯止め)
    def _lipschitz_unique(self, duration):
        axes = self._field_axes()
        segs = self._field_segments(axes, _slope_x, nx=11, ny=7)
        title = Text("歯止めがあるなら、道はただ一つ", font=FONT, font_size=26, color=ACCENT_GOLD)
        title.move_to([0.0, 2.85, 0.0])

        rt = pace(duration, [1.0, 0.9, 2.4, 1.3, 1.3], intro=0.6, coda=CODA)

        self.play(Create(axes), run_time=rt[0])
        self.play(FadeIn(segs), FadeIn(title, run_time=0.5), run_time=rt[1])

        main = self._solution_path(axes, _slope_x, -3.0, 1.1, 3.0, ACCENT_CYAN, 6.0)
        dot = Dot(axes.c2p(-3.0, 1.1), color=ACCENT_CYAN, radius=0.08)
        self.add(dot)
        self.play(
            AnimationGroup(
                Create(main, run_time=rt[2]),
                MoveAlongPath(dot, main, run_time=rt[2]),
                lag_ratio=0.0,
            )
        )

        for i, y0 in enumerate((1.5, 0.7)):
            near = self._solution_path(axes, _slope_x, -3.0, y0, 3.0, TEXT_DIM, 2.8)
            self.play(Create(near), run_time=rt[3 + i])

        note = Text("近くから出た道も、交わらない", font=FONT, font_size=21, color=TEXT_WHITE)
        note.move_to([0.0, -1.8, 0.0])
        self.play(FadeIn(note), run_time=0.5)
        self.wait(CODA)

    # ------------------------------------------------------ mode: 二つの未来
    def _two_futures(self, duration):
        axes = self._cubic_axes()
        eq = MathTex(r"y' = 3\,y^{2/3}", color=ACCENT_GOLD, font_size=44)
        eq.move_to([-4.1, 2.6, 0.0])

        rt = pace(duration, [1.0, 0.8, 2.2, 2.2, 1.0], intro=0.6, coda=CODA)

        self.play(Create(axes), run_time=rt[0])
        origin = Dot(axes.c2p(0.0, 0.0), color=ACCENT_GOLD, radius=0.09)
        start = Text("同じ出発点", font=FONT, font_size=21, color=TEXT_WHITE)
        start.next_to(origin, DOWN, buff=0.24)
        self.play(FadeIn(eq), FadeIn(origin), FadeIn(start), run_time=rt[1])

        flat = self._cubic_path(axes, 2.4, ACCENT_CYAN, 6.0)
        flat_dot = Dot(axes.c2p(0.0, 0.0), color=ACCENT_CYAN, radius=0.075)
        self.add(flat_dot)
        self.play(
            AnimationGroup(
                Create(flat, run_time=rt[2]),
                MoveAlongPath(flat_dot, flat, run_time=rt[2]),
                lag_ratio=0.0,
            )
        )
        flat_lab = Text("ずっと 0 のままの道", font=FONT, font_size=21, color=ACCENT_CYAN)
        flat_lab.next_to(axes.c2p(1.35, 0.0), DOWN, buff=0.3)
        self.play(FadeIn(flat_lab), run_time=0.5)

        cubic = self._cubic_path(axes, 0.0, ACCENT_PINK, 6.0)
        cubic_dot = Dot(axes.c2p(0.0, 0.0), color=ACCENT_PINK, radius=0.075)
        self.add(cubic_dot)
        self.play(
            AnimationGroup(
                Create(cubic, run_time=rt[3]),
                MoveAlongPath(cubic_dot, cubic, run_time=rt[3]),
                lag_ratio=0.0,
            )
        )
        cubic_lab = Text("三乗の曲線の道", font=FONT, font_size=21, color=ACCENT_PINK)
        cubic_lab.next_to(axes.c2p(1.62, 4.6), LEFT, buff=0.22)
        self.play(FadeIn(cubic_lab), run_time=rt[4])
        self.wait(CODA)

    # ---------------------------------------------------------- mode: 束
    def _funnel(self, duration):
        axes = self._cubic_axes()
        title = Text(
            "立ち上がる時刻を変えると、道は無限にある", font=FONT, font_size=25, color=ACCENT_GOLD
        )
        title.move_to([0.0, 2.85, 0.0])

        t2s = [float(v) for v in np.linspace(0.0, 1.5, 7)]
        rt = pace(duration, [1.0, 0.8] + [0.6] * len(t2s) + [1.2, 1.2], intro=0.6, coda=CODA)

        self.play(Create(axes), run_time=rt[0])
        origin = Dot(axes.c2p(0.0, 0.0), color=ACCENT_GOLD, radius=0.09)
        self.play(FadeIn(title, run_time=0.5), FadeIn(origin), run_time=rt[1])

        for i, t2 in enumerate(t2s):
            self.play(Create(self._cubic_path(axes, t2, TEXT_DIM, 2.6)), run_time=rt[2 + i])

        n = 2 + len(t2s)
        upper = self._cubic_path(axes, 0.0, ACCENT_PINK, 6.0)
        upper_lab = Text("最も上を通る道", font=FONT, font_size=21, color=ACCENT_PINK)
        upper_lab.next_to(axes.c2p(1.05, 5.2), LEFT, buff=0.25)
        self.play(Create(upper), run_time=rt[n])
        self.play(FadeIn(upper_lab), run_time=0.45)

        lower = self._cubic_path(axes, 2.4, ACCENT_CYAN, 6.0)
        lower_lab = Text("最も下を通る道", font=FONT, font_size=21, color=ACCENT_CYAN)
        lower_lab.next_to(axes.c2p(1.45, 0.0), DOWN, buff=0.3)
        self.play(Create(lower), run_time=rt[n + 1])
        self.play(FadeIn(lower_lab), run_time=0.45)
        self.wait(CODA)

    # -------------------------------------------------- mode: 無限回の選択
    def _arbitrary_choice(self, duration):
        title = Text(
            "無限に並ぶ集まりから、一つずつ選ぶ", font=FONT, font_size=26, color=ACCENT_GOLD
        )
        title.move_to([0.0, 2.85, 0.0])

        xs = [-4.3, -2.6, -0.9, 0.8, 2.5]
        bags = VGroup()
        dots_per_bag = []
        for bx in xs:
            bag = Ellipse(width=1.25, height=2.15, color=EDGE_COLOR, stroke_width=2.4)
            bag.move_to([bx, 0.35, 0.0])
            bags.add(bag)
            col = []
            for dy in (0.78, 0.26, -0.26, -0.78):
                d = Dot([bx, 0.35 + dy, 0.0], color=TEXT_DIM, radius=0.075)
                col.append(d)
                bags.add(d)
            dots_per_bag.append(col)
        ellipsis = Text("…", font=FONT, font_size=40, color=TEXT_DIM)
        ellipsis.move_to([3.9, 0.35, 0.0])

        # pace の外で固定尺の play を 4 つ使う (ラベルの出し入れ 0.5+0.35+0.5、印 0.5)
        # ので、その分を intro に積んで予算を閉じる (閉じないと末尾が切り詰められる)
        fixed = 0.5 + 0.35 + 0.5 + 0.5
        rt = pace(duration, [1.0, 1.1, 1.1, 1.1, 1.4], intro=0.6 + fixed, coda=CODA)

        self.play(FadeIn(bags), FadeIn(ellipsis), FadeIn(title, run_time=0.5), run_time=rt[0])

        arb_lab = Text(
            "任意の規則では、無限回は適用できない", font=FONT, font_size=22, color=ACCENT_PINK
        )
        arb_lab.move_to([0.0, -1.55, 0.0])
        self.play(FadeIn(arb_lab), run_time=0.5)

        picks = VGroup()
        for col in dots_per_bag:
            picks.add(col[1].copy().set_color(ACCENT_PINK).scale(1.35))
        self.play(FadeIn(picks), run_time=rt[1])

        # 選ぶ位置は集まりごとにばらばらで、そのつど変わる (= 任意の規則)
        for offsets in ((3, 1, 0, 2, 1), (0, 2, 3, 1, 3), (2, 3, 1, 0, 2)):
            self.play(
                AnimationGroup(
                    *[
                        picks[i].animate.move_to(dots_per_bag[i][offsets[i]].get_center())
                        for i in range(len(picks))
                    ],
                    lag_ratio=0.05,
                ),
                run_time=rt[2] / 3.0,
            )

        # 後半: 決まった規則 (各集まりの一番上を取る)
        rule_lab = Text(
            "決まった規則なら、無限回でも決まる", font=FONT, font_size=22, color=ACCENT_CYAN
        )
        rule_lab.move_to([0.0, -1.55, 0.0])
        self.play(FadeOut(arb_lab), run_time=0.35)
        self.play(FadeIn(rule_lab), run_time=0.5)
        self.play(
            AnimationGroup(
                *[
                    picks[i].animate.move_to(dots_per_bag[i][0].get_center()).set_color(ACCENT_CYAN)
                    for i in range(len(picks))
                ],
                lag_ratio=0.08,
            ),
            run_time=rt[3],
        )

        marks = VGroup()
        for bx in xs:
            marks.add(Line([bx, 1.62, 0.0], [bx, 1.28, 0.0], color=ACCENT_CYAN, stroke_width=3.0))
        rule_note = Text("一番上を取る", font=FONT, font_size=20, color=ACCENT_CYAN)
        rule_note.move_to([0.0, 2.05, 0.0])
        self.play(FadeIn(marks), FadeIn(rule_note, run_time=0.5), run_time=0.5)
        self.wait(max(0.0, rt[4] - 0.5))
        self.wait(CODA)

    # ------------------------------------------------- mode: 面を埋める曲線
    def _curve_tiles(self, duration):
        """原論文の三進法の式で作った曲線を 1 段ずつ細かくし、最後にタイルに見立てる。"""
        side = 3.5
        cx, cy = 0.0, 0.45
        x0, y0 = cx - side / 2, cy - side / 2

        def to_scene(p, span):
            """打ち切りで [0, span] に収まる点を、正方形いっぱいに伸ばす。"""
            return [x0 + p[0] / span * side, y0 + p[1] / span * side, 0.0]

        corners = [
            [x0, y0, 0.0],
            [x0 + side, y0, 0.0],
            [x0 + side, y0 + side, 0.0],
            [x0, y0 + side, 0.0],
            [x0, y0, 0.0],
        ]
        frame = Line(corners[0], corners[1], color=EDGE_COLOR, stroke_width=2.5)
        frame.set_points_as_corners(corners)
        title = Text("一本の線が、正方形を埋め尽くす", font=FONT, font_size=26, color=ACCENT_GOLD)
        title.move_to([0.0, 2.85, 0.0])

        rt = pace(duration, [0.8, 1.3, 1.5, 1.7, 1.5], intro=0.6, coda=CODA)

        self.play(Create(frame), FadeIn(title, run_time=0.5), run_time=rt[0])

        curve = None
        for i, order in enumerate((1, 2, 3)):
            raw = _peano_points(order)
            span = 1.0 - 1.0 / 3**order  # 打ち切った終点 (= (1-3^-n, 1-3^-n))
            pts = [to_scene(p, span) for p in raw]
            nxt = Line(pts[0], pts[1], color=ACCENT_CYAN, stroke_width=max(1.5, 5.0 - 1.5 * i))
            nxt.set_points_as_corners(pts)
            if curve is None:
                self.play(Create(nxt), run_time=rt[1])
            else:
                self.play(ReplacementTransform(curve, nxt), run_time=rt[2 + (i - 1)])
            curve = nxt

        # 1 段目の 9 マスを、通る順に白と黒で塗り分ける (テラスに敷いたタイル)
        cell = side / 3.0
        tiles = VGroup()
        for i, p in enumerate(_peano_points(1)):
            sq = Square(side_length=cell * 0.97)
            sq.set_stroke(color=EDGE_COLOR, width=1.5)
            sq.set_fill(TEXT_WHITE if i % 2 == 0 else BG_COLOR, opacity=0.92)
            sq.move_to([x0 + (p[0] * 3 + 0.5) * cell, y0 + (p[1] * 3 + 0.5) * cell, 0.0])
            tiles.add(sq)
        note = Text("テラスに敷いた白と黒のタイル", font=FONT, font_size=21, color=TEXT_DIM)
        note.move_to([0.0, -1.8, 0.0])
        # タイルの上に 1 段目の経路を重ね、タイルの並びが曲線そのものだと見せる
        base = _peano_points(1)
        path_pts = [[x0 + (q[0] * 3 + 0.5) * cell, y0 + (q[1] * 3 + 0.5) * cell, 0.0] for q in base]
        trace = Line(path_pts[0], path_pts[1], color=ACCENT_GOLD, stroke_width=5.0)
        trace.set_points_as_corners(path_pts)

        self.play(FadeOut(curve), run_time=0.4)
        self.play(FadeIn(tiles), run_time=max(0.6, rt[4] - 1.4))
        self.play(Create(trace), run_time=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(CODA)


SCENES = {
    "direction_field": PeanoExistence,
    "lipschitz_unique": PeanoExistence,
    "two_futures": PeanoExistence,
    "funnel": PeanoExistence,
    "arbitrary_choice": PeanoExistence,
    "curve_tiles": PeanoExistence,
}
