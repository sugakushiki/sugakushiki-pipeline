"""
vibrating_string.py - 張った弦の振動とダランベールの解 for 数学史記

両端を固定した長さ L の弦。ダランベール (1747) の解 y = f(x+ct) + g(x-ct) を、
弦の形 (初期形の奇周期延長) からレンダ時に数値で計算して描く。座標のハードコード無し。

Modes:
    force_element        - 曲がった弦の一片に働く二本の張力と、その合力が曲がりの向きに
                           戻すことを示す。弦はゆっくり呼吸するように振幅を変え続ける
                           (静止しない)。最後に波動方程式と一文を出す。
                           Fixed params: 弦の形 y = A sin(pi s / L)、A は 0.1〜1.0 を周期 8 秒で
                           往復、一片は s = 6.5 (L = 10) の幅 1.0。

    traveling_waves      - 右へ進む波 (丸い山) と左へ進む波 (三角の山と谷) を別々の段に
                           薄く描き、下の段にその和を太く描く。山と山が重なると高くなり、
                           山と谷が重なると消える瞬間を見せる。scene 全編で動き続ける。
                           Fixed params: 周期 L = 10、速さ c = 2 (単位/秒)、振幅 0.4、
                           右へ進む波 = 幅 0.9 の丸い山 (位置 2.5)、左へ進む波 = 幅 3 の
                           三角の山 (位置 0/10) と谷 (位置 5)。

    plucked_reflection   - 前半: 正弦の形 (2 山) の右進行波と左進行波が重なって定在波に
                           なり、動かない点 (節) と大きく揺れる点 (腹) を示す。
                           後半: はじいた三角形の弦が半分の高さの二つの三角形に割れて
                           左右へ進み、固定端で裏返って戻り、また重なる (奇周期延長)。
                           Fixed params: 前半は sin(2 pi s / L)、節は s = 0, L/2, L の 3 点、
                           腹は s = L/4, 3L/4 の 2 点。後半は s = 3.5 ではじいた高さ 1.4 の三角形、
                           速さ c = 2。

    analytic_vs_freehand - 左に一つの式で書ける滑らかな曲線 (正弦の一山)、右に指で
                           はじいた角のある折れ線。角の点を拡大して「ここでは二階微分が
                           無い」の札。下に三人の主張を三行で並べる。
                           Fixed params: 三行 = ダランベール / オイラー / ベルヌーイ。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。末尾 FadeOut 無し。

Used by: Episode 075 (ダランベール) — 数学 1〜4。
"""

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    AnimationGroup,
    Arrow,
    Circle,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MathTex,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    always_redraw,
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
# 弦の共通定数
# ---------------------------------------------------------------------------
L = 10.0  # 弦の長さ (scene 単位。x = -5 〜 +5 に置く)
X_LEFT = -5.0
N_PTS = 241
TITLE_Y = 3.05
TEXT_FADE = 0.5
C_SPEED = 2.0  # 波の速さ (単位/秒)


def _s_grid(n=N_PTS):
    return np.linspace(0.0, L, n)


def _polyline(ss, ys, baseline, color, width, opacity=1.0):
    """弦上の点列 (s, y) を scene 座標の折れ線にする。"""
    pts = [np.array([X_LEFT + s, baseline + y, 0.0]) for s, y in zip(ss, ys, strict=True)]
    m = VMobject()
    m.set_points_as_corners(pts)
    m.set_stroke(color=color, width=width, opacity=opacity)
    return m


def _odd_periodic(f):
    """[0, L] 上の f を奇関数・周期 2L に延長した関数を返す (固定端の反射)。"""

    def F(u):
        u = np.asarray(u, dtype=float)
        v = np.mod(u + L, 2.0 * L) - L  # [-L, L)
        return np.where(v >= 0.0, f(np.abs(v)), -f(np.abs(v)))

    return F


def _triangle(s, peak_s, height):
    """s = peak_s ではじいた三角形 (両端 0)。"""
    s = np.asarray(s, dtype=float)
    left = height * s / peak_s
    right = height * (L - s) / (L - peak_s)
    return np.where(s <= peak_s, left, right)


def _posts(baseline, color=TEXT_DIM):
    """固定端の小さな柱。"""
    g = VGroup()
    for x in (X_LEFT, X_LEFT + L):
        g.add(
            Line(
                [x, baseline - 0.35, 0],
                [x, baseline + 0.35, 0],
                color=color,
                stroke_width=4,
            )
        )
    return g


# 画面に出る固有名 (Text) — qa_manim_consistency が narration と照合する。
LINT_FACTUAL_CLAIMS = {
    "force_element": {"people": [], "years": []},
    "traveling_waves": {"people": [], "years": []},
    "plucked_reflection": {"people": [], "years": []},
    "analytic_vs_freehand": {
        "people": [
            ["ダランベール", "d'Alembert"],
            ["オイラー", "Euler"],
            ["ベルヌーイ", "Bernoulli"],
        ],
        "years": [],
    },
}

# ナレーションと画面の不一致 lint 用。この mode が実際に描くもの。
LINT_VISUAL_ELEMENTS = {
    "force_element": ["弦", "矢印", "一片", "張力", "合力", "式"],
    "traveling_waves": ["波", "弦", "山", "谷", "和", "式", "矢印"],
    "plucked_reflection": ["弦", "波", "三角形", "端", "点", "節", "腹"],
    "analytic_vs_freehand": ["曲線", "折れ線", "角", "弦", "式", "円"],
}


class VibratingString(Scene):
    """force_element / traveling_waves / plucked_reflection / analytic_vs_freehand。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "traveling_waves")
        self._duration = float(params.get("duration", 30))
        builders = {
            "force_element": self.build_force_element,
            "traveling_waves": self.build_traveling_waves,
            "plucked_reflection": self.build_plucked_reflection,
            "analytic_vs_freehand": self.build_analytic_vs_freehand,
        }
        if mode not in builders:
            raise ValueError(f"vibrating_string: unknown mode {mode!r} (valid: {sorted(builders)})")
        builders[mode]()

    # ------------------------------------------------------------------
    # 共通部品
    # ------------------------------------------------------------------
    def _title(self, main, color=ACCENT_GOLD):
        t = Text(main, font=FONT, font_size=30, color=color).move_to([0, TITLE_Y, 0])
        self.play(FadeIn(t), run_time=0.6)
        return t

    def _show(self, mobjs, run_time, shape_anims=()):
        """テキストは短く入れて保持し、長い run_time は図形側 (または wait) に使う。"""
        t = min(TEXT_FADE, run_time)
        anims = [FadeIn(m, run_time=t) for m in mobjs]
        anims += list(shape_anims)
        self.play(AnimationGroup(*anims, lag_ratio=0.0))
        longest = max([t] + [getattr(a, "run_time", t) for a in shape_anims])
        if run_time > longest:
            self.wait(run_time - longest)

    def _clock(self):
        """play / wait のあいだ勝手に進む時計 (updater 駆動の運動に使う)。"""
        tr = ValueTracker(0.0)
        tr.add_updater(lambda m, dt: m.increment_value(dt))
        self.add(tr)
        return tr

    # ------------------------------------------------------------------
    # mode: force_element
    # ------------------------------------------------------------------
    def build_force_element(self):
        CODA = 3.0
        # 弦 -> 一片 -> 張力 2 本 -> 合力 -> 式 -> 一文
        weights = [0.8, 0.8, 1.0, 1.0, 1.0, 0.8]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("弦の一片に働く力")

        BASE = 0.35
        S0, DS = 5.0, 1.2
        PERIOD = 8.0
        clock = self._clock()

        def amp():
            return 0.75 + 0.45 * np.cos(2 * np.pi * clock.get_value() / PERIOD)

        def shape(s, a=None):
            a = amp() if a is None else a
            return a * np.sin(np.pi * np.asarray(s) / L)

        def slope(s, a=None):
            a = amp() if a is None else a
            return a * np.pi / L * np.cos(np.pi * s / L)

        def pt(s, a=None):
            return np.array([X_LEFT + s, BASE + float(shape(s, a)), 0.0])

        def tangent(s, a=None):
            v = np.array([1.0, float(slope(s, a)), 0.0])
            return v / np.linalg.norm(v)

        ss = _s_grid()
        string = always_redraw(lambda: _polyline(ss, shape(ss), BASE, TEXT_WHITE, 3.5))
        self._show([_posts(BASE)], rt[0], shape_anims=[FadeIn(string, run_time=0.5)])

        s1, s2 = S0 - DS / 2, S0 + DS / 2
        sub = np.linspace(s1, s2, 24)
        element = always_redraw(lambda: _polyline(sub, shape(sub), BASE, ACCENT_GOLD, 9.0))
        el_lab = Text("弦の一片", font=FONT, font_size=20, color=ACCENT_GOLD)
        el_lab.move_to([X_LEFT + S0, BASE + 1.2 + 0.5, 0])
        self._show([el_lab], rt[1], shape_anims=[FadeIn(element, run_time=0.5)])

        T_LEN = 1.5

        def tension_arrow(s_end, sign):
            def make():
                p = pt(s_end)
                d = sign * tangent(s_end)
                return Arrow(
                    p,
                    p + T_LEN * d,
                    buff=0.0,
                    color=ACCENT_CYAN,
                    stroke_width=4,
                    max_tip_length_to_length_ratio=0.18,
                )

            return always_redraw(make)

        a1 = tension_arrow(s1, -1.0)
        a2 = tension_arrow(s2, +1.0)
        t_lab1 = Text("張力", font=FONT, font_size=20, color=ACCENT_CYAN)
        t_lab1.move_to(pt(s1, 0.75) - 0.5 * T_LEN * tangent(s1, 0.75) + np.array([0, -0.6, 0]))
        t_lab2 = Text("張力", font=FONT, font_size=20, color=ACCENT_CYAN)
        t_lab2.move_to(pt(s2, 0.75) + 0.5 * T_LEN * tangent(s2, 0.75) + np.array([0, -0.6, 0]))
        self._show(
            [t_lab1, t_lab2],
            rt[2],
            shape_anims=[FadeIn(a1, run_time=0.5), FadeIn(a2, run_time=0.5)],
        )

        def resultant():
            p = pt(S0)
            d = tangent(s2) - tangent(s1)  # 曲がりの向き (凹側) を向く
            n = np.linalg.norm(d)
            if n < 1e-6:
                d = np.array([0.0, -1.0, 0.0])
                n = 1.0
            vec = d / n * min(1.3, max(0.4, 8.0 * n * T_LEN))
            return Arrow(
                p,
                p + vec,
                buff=0.0,
                color=ACCENT_GOLD,
                stroke_width=5,
                max_tip_length_to_length_ratio=0.2,
            )

        res = always_redraw(resultant)
        r_lab = Text("合力: 曲がりの向きに戻す", font=FONT, font_size=20, color=ACCENT_GOLD)
        r_lab.move_to([X_LEFT + S0 + 2.6, BASE - 0.9, 0])
        self._show([r_lab], rt[3], shape_anims=[FadeIn(res, run_time=0.5)])

        eq = MathTex(
            r"\frac{\partial^2 y}{\partial t^2}",
            "=",
            r"c^2\,\frac{\partial^2 y}{\partial x^2}",
            font_size=36,
            color=TEXT_WHITE,
        )
        eq.move_to([-3.6, 2.3, 0])
        eq[0].set_color(ACCENT_GOLD)
        eq[2].set_color(ACCENT_CYAN)
        eq_lab = VGroup(
            Text("加速度", font=FONT, font_size=18, color=ACCENT_GOLD),
            Text("曲がり具合", font=FONT, font_size=18, color=ACCENT_CYAN),
        )
        eq_lab[0].next_to(eq[0], DOWN, buff=0.12)
        eq_lab[1].next_to(eq[2], DOWN, buff=0.12)
        self._show([eq, eq_lab], rt[4])

        sent = Text(
            "各点の加速度は、その点の曲がり具合に比例する",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        sent.move_to([0, -1.75, 0])
        self._show([sent], rt[5])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: traveling_waves
    # ------------------------------------------------------------------
    def build_traveling_waves(self):
        CODA = 3.0
        # 段と札 -> 式 -> 運動 (長い) -> 一文 -> 運動の続き
        weights = [0.8, 0.8, 3.0, 0.6, 1.5]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("右へ進む波と、左へ進む波の和")

        AMP = 0.4
        Y_R, Y_L, Y_SUM = 1.85, 0.75, -0.75
        clock = self._clock()

        def right_shape(u):
            # 周期 L の丸い山 (位置 2.5)
            u = np.mod(np.asarray(u, dtype=float), L)
            return AMP * np.exp(-(((u - 2.5) / 0.9) ** 2))

        def left_shape(u):
            # 周期 L の三角の山 (位置 0 / 10) と谷 (位置 5)、幅 3
            u = np.mod(np.asarray(u, dtype=float), L)
            hill = np.clip(1.0 - np.minimum(u, L - u) / 1.5, 0.0, None)
            valley = np.clip(1.0 - np.abs(u - 5.0) / 1.5, 0.0, None)
            return AMP * (hill - valley)

        ss = _s_grid()

        def yr():
            return right_shape(ss - C_SPEED * clock.get_value())

        def yl():
            return left_shape(ss + C_SPEED * clock.get_value())

        wave_r = always_redraw(lambda: _polyline(ss, yr(), Y_R, ACCENT_CYAN, 3.0, 0.9))
        wave_l = always_redraw(lambda: _polyline(ss, yl(), Y_L, ACCENT_PINK, 3.0, 0.9))
        wave_s = always_redraw(lambda: _polyline(ss, yr() + yl(), Y_SUM, ACCENT_GOLD, 4.5))
        ghost_r = always_redraw(lambda: _polyline(ss, yr(), Y_SUM, ACCENT_CYAN, 1.5, 0.35))
        ghost_l = always_redraw(lambda: _polyline(ss, yl(), Y_SUM, ACCENT_PINK, 1.5, 0.35))

        def lab(txt, y, color, direction):
            t = Text(txt, font=FONT, font_size=20, color=color)
            t.move_to([-6.05, y + 0.22, 0])
            ar = Arrow(
                [-6.35, y - 0.2, 0],
                [-5.75, y - 0.2, 0],
                buff=0.0,
                color=color,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.3,
            )
            if direction < 0:
                ar = Arrow(
                    [-5.75, y - 0.2, 0],
                    [-6.35, y - 0.2, 0],
                    buff=0.0,
                    color=color,
                    stroke_width=3,
                    max_tip_length_to_length_ratio=0.3,
                )
            return VGroup(t, ar)

        labels = VGroup(
            lab("右へ進む波", Y_R, ACCENT_CYAN, +1),
            lab("左へ進む波", Y_L, ACCENT_PINK, -1),
            Text("二つの和", font=FONT, font_size=20, color=ACCENT_GOLD).move_to([-6.05, Y_SUM, 0]),
        )
        posts = VGroup(_posts(Y_R), _posts(Y_L), _posts(Y_SUM))
        self._show(
            [posts, labels],
            rt[0],
            shape_anims=[
                FadeIn(wave_r, run_time=0.5),
                FadeIn(wave_l, run_time=0.5),
                FadeIn(ghost_r, run_time=0.5),
                FadeIn(ghost_l, run_time=0.5),
                FadeIn(wave_s, run_time=0.5),
            ],
        )

        eq = MathTex("y", "=", "f(x+ct)", "+", "g(x-ct)", font_size=32, color=TEXT_WHITE)
        eq.move_to([0, 2.58, 0])
        eq[2].set_color(ACCENT_PINK)
        eq[4].set_color(ACCENT_CYAN)
        self._show([eq], rt[1])

        self.wait(rt[2])
        note = Text(
            "山と山が重なると高くなり、山と谷が重なると消える",
            font=FONT,
            font_size=20,
            color=TEXT_WHITE,
        )
        note.move_to([0.4, -1.85, 0])
        self._show([note], rt[3])
        self.wait(rt[4])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: plucked_reflection
    # ------------------------------------------------------------------
    def build_plucked_reflection(self):
        CODA = 3.0
        # 前半: 正弦 (段) -> 節・腹 -> 運動 / 後半: 入れ替え -> 三角形 -> 割れる -> 運動 -> 一文
        weights = [0.7, 0.9, 2.2, 0.5, 0.8, 0.9, 3.0, 0.7]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        title = self._title("端で裏返って戻り、重なる")
        clock = self._clock()
        ss = _s_grid()

        # ---------- 前半: 正弦 2 山の定在波 ----------
        BASE1, A1 = 0.55, 1.0
        F1 = _odd_periodic(lambda s: A1 * np.sin(2 * np.pi * s / L))

        def y_right():
            return 0.5 * F1(ss - C_SPEED * clock.get_value())

        def y_left():
            return 0.5 * F1(ss + C_SPEED * clock.get_value())

        w_r = always_redraw(lambda: _polyline(ss, y_right(), BASE1, ACCENT_CYAN, 2.0, 0.5))
        w_l = always_redraw(lambda: _polyline(ss, y_left(), BASE1, ACCENT_PINK, 2.0, 0.5))
        w_s = always_redraw(lambda: _polyline(ss, y_right() + y_left(), BASE1, TEXT_WHITE, 4.0))
        lab1 = Text("正弦の形なら", font=FONT, font_size=20, color=TEXT_DIM)
        lab1.move_to([-4.2, 2.35, 0])
        legend = VGroup(
            Text("右へ進む波", font=FONT, font_size=18, color=ACCENT_CYAN),
            Text("左へ進む波", font=FONT, font_size=18, color=ACCENT_PINK),
            Text("その和 = 弦", font=FONT, font_size=18, color=TEXT_WHITE),
        ).arrange(RIGHT, buff=0.6)
        legend.move_to([2.2, 2.35, 0])
        posts1 = _posts(BASE1)
        self._show(
            [posts1, lab1, legend],
            rt[0],
            shape_anims=[
                FadeIn(w_r, run_time=0.5),
                FadeIn(w_l, run_time=0.5),
                FadeIn(w_s, run_time=0.5),
            ],
        )

        nodes = VGroup(
            *[Dot([X_LEFT + s, BASE1, 0], radius=0.09, color=ACCENT_GOLD) for s in (0, L / 2, L)]
        )
        n_lab = Text("節: 動かない点", font=FONT, font_size=20, color=ACCENT_GOLD)
        n_lab.move_to([0, BASE1 - 1.45, 0])
        anti = VGroup()
        for s in (L / 4, 3 * L / 4):
            anti.add(
                Line(
                    [X_LEFT + s, BASE1 - A1 - 0.1, 0],
                    [X_LEFT + s, BASE1 + A1 + 0.1, 0],
                    color=ACCENT_PINK,
                    stroke_width=1.5,
                ).set_opacity(0.6)
            )
        a_lab = Text("腹: 大きく揺れる点", font=FONT, font_size=20, color=ACCENT_PINK)
        a_lab.move_to([-4.6, BASE1 - 1.45, 0])
        n_lab.move_to([3.6, BASE1 - 1.45, 0])
        self._show([nodes, n_lab, anti, a_lab], rt[1])
        self.wait(rt[2])

        # ---------- 後半: はじいた三角形 ----------
        first_half = VGroup(w_r, w_l, w_s, posts1, lab1, legend, nodes, n_lab, anti, a_lab)
        BASE2, H2, SP = 0.35, 1.4, 3.5
        F2 = _odd_periodic(lambda s: _triangle(s, SP, H2))
        t0 = [0.0]  # 後半の時計の原点

        def tau():
            return clock.get_value() - t0[0]

        def y2_right():
            return 0.5 * F2(ss - C_SPEED * tau())

        def y2_left():
            return 0.5 * F2(ss + C_SPEED * tau())

        tri_full = _polyline(ss, _triangle(ss, SP, H2), BASE2, TEXT_WHITE, 4.0)
        lab2 = Text("指ではじいた三角形の弦", font=FONT, font_size=20, color=TEXT_DIM)
        lab2.move_to([-3.6, 2.35, 0])
        posts2 = _posts(BASE2)
        new_title = Text(
            "はじいた弦は、二つに割れて進む", font=FONT, font_size=30, color=ACCENT_GOLD
        )
        new_title.move_to([0, TITLE_Y, 0])
        self.play(
            AnimationGroup(
                FadeOut(first_half, run_time=0.5),
                FadeOut(title, run_time=0.5),
                FadeIn(new_title, run_time=0.5),
                lag_ratio=0.0,
            )
        )
        if rt[3] > 0.5:
            self.wait(rt[3] - 0.5)
        self._show([posts2, lab2], rt[4], shape_anims=[FadeIn(tri_full, run_time=0.5)])

        # 割れる: 半分の高さの二つの三角形を薄く重ね、以後は時計で動かす
        t0[0] = clock.get_value()
        h_r = always_redraw(lambda: _polyline(ss, y2_right(), BASE2, ACCENT_CYAN, 2.5, 0.75))
        h_l = always_redraw(lambda: _polyline(ss, y2_left(), BASE2, ACCENT_PINK, 2.5, 0.75))
        s_full = always_redraw(
            lambda: _polyline(ss, y2_right() + y2_left(), BASE2, TEXT_WHITE, 4.0)
        )
        legend2 = VGroup(
            Text("右へ進む半分", font=FONT, font_size=18, color=ACCENT_CYAN),
            Text("左へ進む半分", font=FONT, font_size=18, color=ACCENT_PINK),
        ).arrange(RIGHT, buff=0.6)
        legend2.move_to([3.4, 2.35, 0])
        # 静止した三角形を、同じ形の「二つの和」に差し替えてから半分を出す
        t0[0] = clock.get_value()
        self.remove(tri_full)
        self.add(s_full)
        self.play(
            AnimationGroup(
                FadeIn(h_r, run_time=0.5),
                FadeIn(h_l, run_time=0.5),
                FadeIn(legend2, run_time=0.5),
                lag_ratio=0.0,
            )
        )
        if rt[5] > 0.5:
            self.wait(rt[5] - 0.5)
        self.wait(rt[6])
        sent = Text(
            "端で裏返って戻り、また重なる ── 弦はこの二つの和のまま動く",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        sent.move_to([0, -1.85, 0])
        self._show([sent], rt[7])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: analytic_vs_freehand
    # ------------------------------------------------------------------
    def build_analytic_vs_freehand(self):
        CODA = 3.0
        # 左 (式の曲線) -> 右 (角のある折れ線) -> 角の拡大 -> 三行
        weights = [1.0, 1.0, 1.2, 0.9, 0.9, 0.9]
        rt = pace(self._duration, weights, intro=1.2, coda=CODA)

        self._title("一つの式か、手で描いた曲線か")

        BASE = 0.95
        HALF = 4.4  # 各パネルの弦の長さ
        H = 1.05

        def panel_posts(cx):
            g = VGroup()
            for x in (cx - HALF / 2, cx + HALF / 2):
                g.add(Line([x, BASE - 0.3, 0], [x, BASE + 0.3, 0], color=TEXT_DIM, stroke_width=4))
            return g

        # 左: 一つの式で書ける曲線
        cxl = -3.4
        us = np.linspace(0.0, HALF, 121)
        ys = H * np.sin(np.pi * us / HALF)
        curve = VMobject()
        curve.set_points_as_corners(
            [np.array([cxl - HALF / 2 + u, BASE + y, 0.0]) for u, y in zip(us, ys, strict=True)]
        )
        curve.set_stroke(color=ACCENT_CYAN, width=4.0)
        l_lab = Text("一つの式で書ける曲線", font=FONT, font_size=22, color=ACCENT_CYAN)
        l_lab.move_to([cxl, 2.5, 0])
        l_eq = MathTex(r"y = A\sin\!\left(\tfrac{\pi x}{L}\right)", font_size=28, color=ACCENT_CYAN)
        l_eq.move_to([cxl, BASE - 0.55, 0])
        self._show(
            [panel_posts(cxl), l_lab, l_eq], rt[0], shape_anims=[FadeIn(curve, run_time=0.5)]
        )

        # 右: 指ではじいた角のある折れ線
        cxr = 3.4
        peak_u = 1.5
        corner = np.array([cxr - HALF / 2 + peak_u, BASE + H, 0.0])
        poly = VMobject()
        poly.set_points_as_corners(
            [
                np.array([cxr - HALF / 2, BASE, 0.0]),
                corner,
                np.array([cxr + HALF / 2, BASE, 0.0]),
            ]
        )
        poly.set_stroke(color=ACCENT_PINK, width=4.0)
        r_lab = Text("指ではじいた形 (角がある)", font=FONT, font_size=22, color=ACCENT_PINK)
        r_lab.move_to([cxr, 2.5, 0])
        r_note = Text("一つの式では書けない", font=FONT, font_size=20, color=ACCENT_PINK)
        r_note.move_to([cxr - 0.8, BASE - 0.55, 0])
        self._show(
            [panel_posts(cxr), r_lab, r_note], rt[1], shape_anims=[FadeIn(poly, run_time=0.5)]
        )

        # 角の拡大: 小さな円 -> 大きな円の中に折れ線を拡大して描く
        small = Circle(radius=0.28, color=ACCENT_GOLD, stroke_width=2.5).move_to(corner)
        big_c = np.array([5.3, -0.7, 0.0])
        big_r = 0.85
        big = Circle(radius=big_r, color=ACCENT_GOLD, stroke_width=2.5).move_to(big_c)
        k = big_r / 0.28 * 0.8
        zoom_pts = []
        for u in (peak_u - 0.22, peak_u, peak_u + 0.22):
            base_pt = np.array(
                [cxr - HALF / 2 + u, BASE + float(_triangle_local(u, peak_u, H, HALF)), 0.0]
            )
            zoom_pts.append(big_c + k * (base_pt - corner))
        zoom_poly = VMobject()
        zoom_poly.set_points_as_corners(zoom_pts)
        zoom_poly.set_stroke(color=ACCENT_PINK, width=5.0)
        z_dot = Dot(big_c, radius=0.07, color=ACCENT_GOLD)
        z_lab = Text("ここでは二階微分が無い", font=FONT, font_size=20, color=ACCENT_GOLD)
        z_lab.next_to(big, LEFT, buff=0.25)
        self.play(FadeIn(small), run_time=0.4)
        self._show(
            [z_lab],
            max(0.5, rt[2] - 0.4),
            shape_anims=[
                FadeIn(big, run_time=0.5),
                FadeIn(zoom_poly, run_time=0.5),
                FadeIn(z_dot, run_time=0.5),
            ],
        )

        # 三行: 三人の主張
        lines = VGroup(
            Text(
                "ダランベール: 一つの式で書ける曲線だけ", font=FONT, font_size=20, color=ACCENT_CYAN
            ),
            Text("オイラー: 手で描いた曲線でもよい", font=FONT, font_size=20, color=ACCENT_PINK),
            Text("ベルヌーイ: 正弦の和で尽きる", font=FONT, font_size=20, color=ACCENT_GOLD),
        ).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        lines.move_to([-3.35, -1.15, 0])
        for i, ln in enumerate(lines):
            self._show([ln], rt[3 + i])
        self.wait(CODA)


def _triangle_local(u, peak_u, height, length):
    """パネル内 (長さ length) の三角形の高さ。"""
    if u <= peak_u:
        return height * u / peak_u
    return height * (length - u) / (length - peak_u)


SCENES = {
    "force_element": VibratingString,
    "traveling_waves": VibratingString,
    "plucked_reflection": VibratingString,
    "analytic_vs_freehand": VibratingString,
}
