"""
brouwer_fixed_point.py - ブラウワーの不動点定理と、その周辺 (次元の不変性・毛玉の定理) for 数学史記

「円板を連続に変形して円板の中に収めれば、元の場所から動いていない点が必ず一つはある」
(Brouwer, Math. Ann. 71, 1911/12)。証明は「無いと仮定して縁に潰す矛盾」で、点の位置を
与えない (非構成的)。**画面に人名・年号は出さない** (帰属はナレーション側)。

Modes:
    line       - 一次元。区間 [0,1] を [0,1] に写す連続関数のグラフと対角線 y = x。
                 左端ではグラフが対角線の上、右端では下にあるので途中で必ず横切る。
                 横切った点で f(x) = x (動かない点)。交点は最後にだけ光る (「どこで
                 横切るかはこの論法では分からない」)。
                 Fixed params: f(x) = 0.25 + 0.5x + 0.08 sin(4.5x + 1) (単調減少の
                 g = f - x なので交点はちょうど 1 つ)。交点は render 時に二分法で求める。

    disk       - 円板 (半径 2) の格子点 (間隔 0.42、約 70 点) を、連続な「かき混ぜ」
                 (半径を 0.85 倍し、中心ほど大きくひねり、少しずらす) で行き先へ滑らせる。
                 ひねりの剪断は縁で 1 を超えるので縮小写像ではない (「縮める必要はない」)。
                 全点が動く中で、動かない一点 (render 時に格子探索 + ニュートン法で求める)
                 だけが残る。
                 Fixed params: f(r, φ) = (0.85 r, φ + 1.1 (1 - r/2)) + (0.22, -0.14)。

    retraction - 証明の骨格。動かない点が無いと仮定し、f(x) から x へ向かう半直線を縁まで
                 延ばして r(x) を作る (3 つの見本点)。縁の点は動かない。これで円板が縁に
                 潰れるが、右の図: 円板の中では縁の円は一点に縮む、円周の中では縮まない。
                 矛盾。最後に「では、どこに?」を残す。
                 Fixed params: 見本点 3 つ、写像は disk と同じ。交点は render 時に計算。

    hairy_ball - 球面 (見かけの半径 2.1、北極を 35° 手前に傾けた正射影) の可視半球に
                 毛 (接ベクトル) を約 150 本描く。最初は乱れた向き、梳かすと回転場
                 (z 軸まわり) に揃い、北極で長さがゼロになる = つむじ。最後に「地球の
                 風なら、風の無い点」。
                 Fixed params: 緯度 8 段 x 経度 24 本のうち可視のもの。場は v = ẑ × p。

    dimension  - 左: 正方形を埋めていく曲線 (ヒルベルト曲線の 1〜4 次、64→256 点。同じ
                 点を何度も通る=一対一でない)。右: 区間の点と正方形の点の一対一対応
                 (近い点が遠くへ飛ぶ=連続でない)。下: 一対一で連続で逆も連続なら次元は
                 変わらない → 直線と平面は本当に違う。
                 Fixed params: ヒルベルト曲線 4 次まで、対応の見本 6 組。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。末尾 FadeOut なし。

Used by: Episode 073 (L. E. J. ブラウワー) — 数学 1 (line) / 数学 2 (disk) /
数学 3 (retraction) / 数学 4 (hairy_ball) / 数学 5 (dimension)。
"""

import math
import random

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Arc,
    Arrow,
    Circle,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    MoveAlongPath,
    Rectangle,
    Scene,
    Text,
    Transform,
    VGroup,
    VMobject,
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

TITLE_Y = 2.95
SUB_Y = 2.45
CODA = 3.0
TEXT_FADE = 0.6

# --- line -----------------------------------------------------------------
SQ = 3.4  # 単位正方形の一辺 (画面単位)
SQ_C = np.array([-2.3, 0.15, 0.0])  # 正方形の中心
NOTE_X = 3.55

# --- disk / retraction ----------------------------------------------------
R = 2.0
DISK_C = np.array([-2.6, 0.25, 0.0])
GRID = 0.42
TWIST = 1.1
SHRINK = 0.85
SHIFT = np.array([0.22, -0.14, 0.0])

# --- hairy_ball -----------------------------------------------------------
BALL_R = 2.1
BALL_C = np.array([-2.5, 0.15, 0.0])
TILT = math.radians(35)
HAIR = 0.34  # 毛の長さ (接ベクトルの長さ 1 に対する画面倍率)

# --- dimension ------------------------------------------------------------
HSQ = 2.8
HSQ_C = np.array([-3.6, 0.35, 0.0])
SEG_X0, SEG_X1, SEG_Y = 1.3, 3.1, 1.6
RSQ = 1.8
RSQ_C = np.array([4.6, -0.15, 0.0])


# ---------------------------------------------------------------------------
# 純粋な計算 (render 時に数値を決める。hardcode しない)
# ---------------------------------------------------------------------------
def _f_line(x):
    return 0.25 + 0.5 * x + 0.08 * math.sin(4.5 * x + 1.0)


def _line_crossing():
    """g(x) = f(x) - x の符号が変わる点を二分法で求める。"""
    lo, hi = 0.0, 1.0
    g = lambda x: _f_line(x) - x  # noqa: E731
    assert g(lo) > 0 > g(hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if g(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _stir(p):
    """円板 (半径 R、中心原点) を円板の中へ写す連続写像 (縮小写像ではない)。"""
    x, y = float(p[0]), float(p[1])
    r = math.hypot(x, y) / R
    phi = math.atan2(y, x)
    r2 = SHRINK * r
    phi2 = phi + TWIST * (1.0 - r)
    return np.array([R * r2 * math.cos(phi2), R * r2 * math.sin(phi2), 0.0]) + SHIFT


def _stir_fixed_point():
    """格子探索 + ニュートン法 (数値ヤコビアン) で f(p) = p を解く。"""
    best, best_v = None, 1e9
    n = 160
    for i in range(n + 1):
        for j in range(n + 1):
            p = np.array([-R + 2 * R * i / n, -R + 2 * R * j / n, 0.0])
            if math.hypot(p[0], p[1]) > R * 0.995:
                continue
            v = float(np.linalg.norm(_stir(p) - p))
            if v < best_v:
                best, best_v = p, v
    p = best.copy()
    h = 1e-6
    for _ in range(30):
        g = (_stir(p) - p)[:2]
        if np.linalg.norm(g) < 1e-11:
            break
        jac = np.zeros((2, 2))
        for k in range(2):
            dp = np.zeros(3)
            dp[k] = h
            jac[:, k] = ((_stir(p + dp) - (p + dp)) - (_stir(p - dp) - (p - dp)))[:2] / (2 * h)
        step = np.linalg.solve(jac, -g)
        p = p + np.array([step[0], step[1], 0.0])
    assert np.linalg.norm(_stir(p) - p) < 1e-7, "fixed point not found"
    assert math.hypot(p[0], p[1]) < R, "fixed point outside the disk"
    return p


def _ray_to_rim(fx, x):
    """f(x) から x へ向かう半直線と円周 |q| = R の交点 (x の先)。"""
    d = x - fx
    a = float(np.dot(d, d))
    b = 2.0 * float(np.dot(fx, d))
    c = float(np.dot(fx, fx)) - R * R
    t = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
    assert t > 1.0  # x 自身 (t=1) より先で縁に当たる
    return fx + t * d


def _sphere_view(p):
    """単位球面上の点 p を、北極を手前に TILT 傾けた正射影の画面座標 (x, y, depth) に。"""
    x, y, z = p
    y2 = y * math.cos(TILT) + z * math.sin(TILT)
    z2 = -y * math.sin(TILT) + z * math.cos(TILT)
    return np.array([x, y2, z2])


def _hilbert_points(order):
    n = 2**order
    pts = []
    for d in range(n * n):
        x = y = 0
        t = d
        s = 1
        while s < n:
            rx = 1 & (t // 2)
            ry = 1 & (t ^ rx)
            if ry == 0:
                if rx == 1:
                    x = s - 1 - x
                    y = s - 1 - y
                x, y = y, x
            x += s * rx
            y += s * ry
            t //= 4
            s *= 2
        pts.append(((x + 0.5) / n, (y + 0.5) / n))
    return pts


LINT_FACTUAL_CLAIMS = {
    "line": {"people": [], "years": []},
    "disk": {"people": [], "years": []},
    "retraction": {"people": [], "years": []},
    "hairy_ball": {"people": [], "years": []},
    "dimension": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "line": ["グラフ", "対角線", "正方形", "点"],
    "disk": ["円板", "点", "格子"],
    "retraction": ["円板", "半直線", "縁", "円"],
    "hairy_ball": ["球", "毛", "つむじ"],
    "dimension": ["曲線", "正方形", "区間", "点"],
}


class BrouwerFixedPoint(Scene):
    """line / disk / retraction / hairy_ball / dimension の 5 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "disk")
        self._duration = float(params.get("duration", 35))
        builders = {
            "line": self.build_line,
            "disk": self.build_disk,
            "retraction": self.build_retraction,
            "hairy_ball": self.build_hairy_ball,
            "dimension": self.build_dimension,
        }
        if mode not in builders:
            raise ValueError(
                f"brouwer_fixed_point: unknown mode {mode!r} (valid: {sorted(builders)})"
            )
        builders[mode]()

    # ------------------------------------------------------------------
    def _title(self, main, sub):
        t = Text(main, font=FONT, font_size=34, color=ACCENT_GOLD).move_to(UP * TITLE_Y)
        s = Text(sub, font=FONT, font_size=22, color=TEXT_DIM).move_to(UP * SUB_Y)
        self.play(FadeIn(t), FadeIn(s), run_time=1.0)

    def _show(self, texts, run_time, shape_anims=()):
        """テキストは短く入れて保持し、長い run_time は図形側だけに使う (規約「罠 2」)。

        shape_anims の run_time が run_time より短ければ、残りを wait で埋める (初回レンダで
        line 35 s / retraction 36 s / dimension 37.7 s と 40 s に届かなかった真因)。
        """
        t = min(TEXT_FADE, run_time)
        if shape_anims:
            self.play(
                AnimationGroup(*shape_anims, *[FadeIn(x, run_time=t) for x in texts], lag_ratio=0.0)
            )
            longest = max([t] + [float(getattr(a, "run_time", 0.0)) for a in shape_anims])
            if run_time - longest > 0.02:
                self.wait(run_time - longest)
        else:
            self.play(*[FadeIn(x) for x in texts], run_time=t)
            if run_time - t > 0.02:
                self.wait(run_time - t)

    def _pulse(self, m, run_time, color, extras=()):
        """FadeIn → Indicate を別々の play に (ある回: 同じ play に入れると消える)。"""
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.6, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    @staticmethod
    def _notes(lines, x=NOTE_X, y0=1.55, gap=0.62, size=24):
        out = []
        for i, (s, c) in enumerate(lines):
            out.append(Text(s, font=FONT, font_size=size, color=c).move_to([x, y0 - gap * i, 0]))
        return out

    # ------------------------------------------------------------------
    def build_line(self):
        d = self._duration
        self._title("一本の線なら、途中で必ず横切る", "区間を区間に写す連続関数と、対角線 y = x")
        lo = SQ_C - SQ / 2
        box = Rectangle(width=SQ, height=SQ, color=EDGE_COLOR, stroke_width=2).move_to(SQ_C)

        def to_screen(x, y):
            return np.array([lo[0] + x * SQ, lo[1] + y * SQ, 0.0])

        diag = DashedLine(to_screen(0, 0), to_screen(1, 1), color=TEXT_DIM, dash_length=0.12)
        diag_label = MathTex(r"y=x", font_size=28, color=TEXT_DIM).move_to(to_screen(0.6, 0.74))
        curve = VMobject(color=ACCENT_CYAN, stroke_width=4)
        curve.set_points_smoothly([to_screen(x, _f_line(x)) for x in np.linspace(0, 1, 120)])
        f_label = MathTex(r"y=f(x)", font_size=28, color=ACCENT_CYAN).move_to(to_screen(0.2, 0.62))
        zero = MathTex(r"0", font_size=24, color=TEXT_DIM).next_to(
            to_screen(0, 0), DOWN + LEFT, buff=0.1
        )
        one_x = MathTex(r"1", font_size=24, color=TEXT_DIM).next_to(
            to_screen(1, 0), DOWN, buff=0.12
        )
        one_y = MathTex(r"1", font_size=24, color=TEXT_DIM).next_to(
            to_screen(0, 1), LEFT, buff=0.12
        )

        c = _line_crossing()
        cross = Dot(to_screen(c, c), radius=0.09, color=ACCENT_GOLD)
        drop = DashedLine(to_screen(c, c), to_screen(c, 0), color=ACCENT_GOLD, dash_length=0.1)
        c_label = MathTex(r"f(c)=c", font_size=30, color=ACCENT_GOLD).next_to(
            to_screen(c, 0), DOWN, buff=0.15
        )
        # 左端・右端の目印 (上か下か)
        left_mark = Dot(to_screen(0, _f_line(0)), radius=0.07, color=ACCENT_PINK)
        right_mark = Dot(to_screen(1, _f_line(1)), radius=0.07, color=ACCENT_PINK)
        tracer = Dot(to_screen(0, _f_line(0)), radius=0.08, color=TEXT_WHITE)

        notes = self._notes(
            [
                ("左端では、線は対角線の上にある", TEXT_WHITE),
                ("右端では、対角線の下にある", TEXT_WHITE),
                ("切れ目のない線は、必ず横切る", ACCENT_CYAN),
                ("横切った点では f(x) = x", ACCENT_GOLD),
                ("── 動かない点", ACCENT_GOLD),
                ("どこで横切るかは、この論法では分からない", TEXT_DIM),
            ],
            y0=1.45,
            gap=0.6,
        )
        notes[5].scale(0.9)

        weights = [0.7, 0.9, 0.6, 0.6, 2.0, 0.6, 0.6, 1.0]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show(
            [diag_label, zero, one_x, one_y],
            rt[0],
            shape_anims=[FadeIn(box, run_time=rt[0]), FadeIn(diag, run_time=rt[0])],
        )
        self._show([f_label], rt[1], shape_anims=[Create(curve, run_time=rt[1])])
        self._show([notes[0]], rt[2], shape_anims=[FadeIn(left_mark, run_time=0.4)])
        self._show([notes[1]], rt[3], shape_anims=[FadeIn(right_mark, run_time=0.4)])
        # 追跡点が曲線を走り、交点で止まる
        self.add(tracer)
        path = VMobject().set_points_smoothly(
            [to_screen(x, _f_line(x)) for x in np.linspace(0, c, 60)]
        )
        self.play(
            AnimationGroup(
                FadeIn(notes[2], run_time=TEXT_FADE),
                MoveAlongPath(tracer, path, run_time=rt[4]),
                lag_ratio=0.0,
            )
        )
        self._pulse(cross, rt[5], ACCENT_GOLD, extras=(drop, c_label))
        self._show([notes[3], notes[4]], rt[6])
        self._show([notes[5]], rt[7])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def _disk_grid(self):
        pts = []
        n = int(R / GRID) + 1
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                p = np.array([i * GRID, j * GRID, 0.0])
                if math.hypot(p[0], p[1]) <= R - 0.12:
                    pts.append(p)
        return pts

    def build_disk(self):
        d = self._duration
        self._title("かき混ぜても、動かない点が必ずある", "円板を、連続に、円板の中へ")
        disk = Circle(
            radius=R, color=EDGE_COLOR, stroke_width=2.5, fill_color="#22223a", fill_opacity=1.0
        )
        disk.move_to(DISK_C)
        pts = self._disk_grid()
        dots = VGroup(*[Dot(DISK_C + p, radius=0.055, color=ACCENT_CYAN) for p in pts])
        targets = [DISK_C + _stir(p) for p in pts]
        fp = _stir_fixed_point()
        fp_dot = Dot(DISK_C + fp, radius=0.1, color=ACCENT_GOLD)
        fp_ring = Circle(radius=0.22, color=ACCENT_GOLD, stroke_width=2.5).move_to(DISK_C + fp)
        fp_label = Text("動かない点", font=FONT, font_size=24, color=ACCENT_GOLD)
        fp_label.next_to(fp_ring, UP + RIGHT, buff=0.08)
        # 点群の上に載るので、文字の下に背景色の板を敷いて可読性を保つ (run2 Vision QA)
        fp_label.add_background_rectangle(color=BG_COLOR, opacity=0.85, buff=0.06)
        # 数本の矢印で「行き先」を示す (全部だと煩い)
        sample_idx = list(range(0, len(pts), max(1, len(pts) // 12)))
        arrows = VGroup()
        for i in sample_idx:
            a, b = DISK_C + pts[i], targets[i]
            if np.linalg.norm(b - a) > 0.15:
                arrows.add(
                    Arrow(
                        a,
                        b,
                        buff=0.04,
                        color=TEXT_DIM,
                        stroke_width=2.5,
                        max_tip_length_to_length_ratio=0.2,
                    )
                )

        notes = self._notes(
            [
                ("引き伸ばしても、回しても", TEXT_WHITE),
                ("折り返しても、押しつぶしても", TEXT_WHITE),
                ("破らず、穴を開けず、円板の中に収めるなら", TEXT_WHITE),
                ("元の場所から動いていない点が", ACCENT_GOLD),
                ("必ず一つはある", ACCENT_GOLD),
                ("縮める必要はない", ACCENT_PINK),
            ],
            y0=1.5,
            gap=0.6,
        )
        notes[2].scale(0.88)

        weights = [0.7, 0.8, 0.6, 0.6, 2.4, 0.5, 0.9, 0.7, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(disk), run_time=rt[0])
        self.play(FadeIn(dots, lag_ratio=0.02), run_time=rt[1])
        self._show([notes[0]], rt[2])
        self._show([notes[1]], rt[3], shape_anims=[FadeIn(arrows, run_time=rt[3])])
        # かき混ぜ: 全点が行き先へ滑る (矢印は消す)
        move = AnimationGroup(
            *[dot.animate.move_to(t) for dot, t in zip(dots, targets, strict=True)],
            lag_ratio=0.0,
            run_time=rt[4],
        )
        self.play(
            AnimationGroup(
                move,
                FadeIn(notes[2], run_time=TEXT_FADE),
                arrows.animate(run_time=0.8).set_opacity(0.0),
                lag_ratio=0.0,
            )
        )
        self.remove(arrows)
        self.wait(rt[5])
        self._pulse(fp_dot, rt[6], ACCENT_GOLD, extras=(fp_ring, fp_label))
        self._show([notes[3], notes[4]], rt[7])
        self._show([notes[5]], rt[8])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_retraction(self):
        d = self._duration
        self._title("無いと仮定すると、矛盾する", "証明は『無い』を否定するだけで、点を見せない")
        disk = Circle(
            radius=R, color=EDGE_COLOR, stroke_width=2.5, fill_color="#22223a", fill_opacity=1.0
        )
        disk.move_to(DISK_C)
        rim = Circle(radius=R, color=ACCENT_GOLD, stroke_width=3).move_to(DISK_C)

        samples = [np.array(v) for v in ([-0.9, 0.8, 0.0], [0.7, -0.35, 0.0], [1.15, 1.05, 0.0])]
        groups = []
        for x in samples:
            fx = _stir(x)
            rx = _ray_to_rim(fx, x)
            g = VGroup(
                Dot(DISK_C + fx, radius=0.07, color=ACCENT_CYAN),
                Dot(DISK_C + x, radius=0.07, color=TEXT_WHITE),
                Line(DISK_C + fx, DISK_C + rx, color=ACCENT_PINK, stroke_width=2.5),
                Dot(DISK_C + rx, radius=0.09, color=ACCENT_GOLD),
            )
            groups.append(g)
        x0 = samples[0]
        lab_x = MathTex(r"x", font_size=28, color=TEXT_WHITE).next_to(
            DISK_C + x0, UP + LEFT, buff=0.06
        )
        lab_fx = MathTex(r"f(x)", font_size=28, color=ACCENT_CYAN).next_to(
            DISK_C + _stir(x0), DOWN, buff=0.08
        )
        lab_rx = MathTex(r"r(x)", font_size=28, color=ACCENT_GOLD).next_to(
            DISK_C + _ray_to_rim(_stir(x0), x0), UP + LEFT, buff=0.06
        )

        # 右の対比図: 円板の中では縁の円は一点に縮む / 円周の中では縮まない
        cx1, cx2, cy, rr = 2.35, 5.15, 0.9, 0.7
        d1 = Circle(radius=rr, color=EDGE_COLOR, fill_color="#22223a", fill_opacity=1.0).move_to(
            [cx1, cy, 0]
        )
        ring1 = Circle(radius=rr, color=ACCENT_GOLD, stroke_width=3).move_to([cx1, cy, 0])
        ring1_small = Circle(radius=0.06, color=ACCENT_GOLD, stroke_width=3).move_to([cx1, cy, 0])
        cap1 = Text(
            "円板の中なら\n縁は一点に縮む",
            font=FONT,
            font_size=18,
            color=TEXT_WHITE,
            line_spacing=0.8,
        ).move_to([cx1, cy - rr - 0.42, 0])
        ring2 = Circle(radius=rr, color=ACCENT_GOLD, stroke_width=3).move_to([cx2, cy, 0])
        cross1 = Line(
            [cx2 - 0.3, cy - 0.3, 0], [cx2 + 0.3, cy + 0.3, 0], color=ACCENT_PINK, stroke_width=4
        )
        cross2 = Line(
            [cx2 - 0.3, cy + 0.3, 0], [cx2 + 0.3, cy - 0.3, 0], color=ACCENT_PINK, stroke_width=4
        )
        cap2 = Text(
            "円周の中では\n縮められない",
            font=FONT,
            font_size=18,
            color=TEXT_WHITE,
            line_spacing=0.8,
        ).move_to([cx2, cy - rr - 0.42, 0])

        notes = [
            Text("動かない点が無い、と仮定する", font=FONT, font_size=24, color=TEXT_WHITE).move_to(
                [3.75, 2.0, 0]
            ),
            Text(
                "f(x) から x へ向かう半直線を、縁まで延ばす",
                font=FONT,
                font_size=20,
                color=TEXT_DIM,
            ).move_to([3.75, -0.85, 0]),
            Text(
                "r は縁の点を動かさない。円板全体が縁へ潰れる",
                font=FONT,
                font_size=20,
                color=TEXT_DIM,
            ).move_to([3.75, -1.2, 0]),
            Text(
                "矛盾 ── だから、動かない点はある", font=FONT, font_size=24, color=ACCENT_PINK
            ).move_to([3.75, -1.55, 0]),
            Text("では、どこに?", font=FONT, font_size=26, color=ACCENT_GOLD).move_to(
                [3.75, -1.92, 0]
            ),
        ]
        # キャプション (2 行、下端 ≈ cy - rr - 0.7 = -0.5) と注記 1 (上端 ≈ -0.7) が離れていること
        assert cap1.get_bottom()[1] > notes[1].get_top()[1] + 0.1

        # 中心のまわりの小さな円 (半径 0.35) を r で写すと、縁の小さな弧に収まる (連続性)。
        # 円板の中心そのものはこの写像の不動点のすぐ近くで、囲むと弧が一周になる (数学的に正しい
        # 挙動)。「不動点が無い」世界の絵なので、不動点を囲まない位置に小さな円を置く。
        small_r = 0.35
        small_c = np.array([-0.9, -0.7, 0.0])
        assert np.linalg.norm(_stir_fixed_point() - small_c) > small_r + 0.2
        small = Circle(radius=small_r, color=ACCENT_CYAN, stroke_width=2.5).move_to(
            DISK_C + small_c
        )
        angs = []
        for k in range(36):
            th = 2 * math.pi * k / 36
            q = small_c + np.array([small_r * math.cos(th), small_r * math.sin(th), 0.0])
            rq = _ray_to_rim(_stir(q), q)
            angs.append(math.atan2(rq[1], rq[0]))
        # 弧の範囲: 角度を円周上で見て、最大の空きの補集合を取る (±π の継ぎ目をまたいでもよい)
        sa = sorted(angs)
        gaps = [(sa[(k + 1) % len(sa)] - sa[k]) % (2 * math.pi) for k in range(len(sa))]
        kmax = max(range(len(sa)), key=lambda k: gaps[k])
        lo_a = sa[(kmax + 1) % len(sa)]
        span = 2 * math.pi - gaps[kmax]
        assert span < math.pi, "small circle does not map into a small arc; pick another radius"
        arc = Arc(radius=R, start_angle=lo_a, angle=span, color=ACCENT_CYAN, stroke_width=7)
        arc.move_arc_center_to(DISK_C)
        small_cap = Text(
            "小さな円は、縁の小さな弧に写る", font=FONT, font_size=20, color=ACCENT_CYAN
        )
        small_cap.move_to([-2.6, -1.92, 0])

        weights = [0.6, 0.6, 1.0, 0.8, 0.8, 0.7, 0.9, 0.9, 0.8, 1.1, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(disk), FadeIn(rim), run_time=rt[0])
        self._show([notes[0]], rt[1])
        # 見本点 1: 段階的に
        g = groups[0]
        self.play(FadeIn(g[1]), FadeIn(lab_x), run_time=min(0.5, rt[2] / 3))
        self.play(FadeIn(g[0]), FadeIn(lab_fx), run_time=min(0.5, rt[2] / 3))
        self.play(Create(g[2]), run_time=max(0.3, rt[2] - min(0.5, rt[2] / 3) * 2))
        self._pulse(g[3], rt[3], ACCENT_GOLD, extras=(lab_rx,))
        self._show([notes[1]], rt[4])
        for g in groups[1:]:
            self.play(FadeIn(g[1]), FadeIn(g[0]), run_time=0.3)
            self.play(Create(g[2]), FadeIn(g[3]), run_time=max(0.3, rt[5] / 2 - 0.3))
        self._show([notes[2]], rt[6])
        self._show(
            [cap1], rt[7] * 0.4, shape_anims=[FadeIn(d1, run_time=0.5), FadeIn(ring1, run_time=0.5)]
        )
        self.play(Transform(ring1, ring1_small), run_time=max(0.3, rt[7] * 0.6))
        self._show([cap2], max(0.3, rt[8] - 0.4), shape_anims=[FadeIn(ring2, run_time=0.5)])
        self.play(FadeIn(cross1), FadeIn(cross2), run_time=0.4)
        # 小さな円 → 縁の小さな弧 (一周する輪が、一周しない輪になる)
        self.play(Create(small), run_time=min(0.8, rt[9] * 0.3))
        self._show(
            [small_cap],
            max(0.3, rt[9] - min(0.8, rt[9] * 0.3)),
            shape_anims=[Create(arc, run_time=max(0.5, rt[9] * 0.5))],
        )
        self._show([notes[3]], rt[10] * 0.6)
        self._show([notes[4]], rt[10] * 0.4)
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_hairy_ball(self):
        d = self._duration
        self._title("球の毛には、必ずつむじができる", "接ベクトル場は、どこかで必ずゼロになる")
        rng = random.Random(73)
        ball = Circle(
            radius=BALL_R,
            color=EDGE_COLOR,
            stroke_width=2.5,
            fill_color="#22223a",
            fill_opacity=1.0,
        )
        ball.move_to(BALL_C)
        # 緯線 (装飾)
        lat_lines = VGroup()
        for lat in (-60, -30, 0, 30, 60):
            la = math.radians(lat)
            pts = []
            for k in range(0, 361, 6):
                lo = math.radians(k)
                p = np.array(
                    [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)]
                )
                v = _sphere_view(p)
                if v[2] > 0:
                    pts.append(BALL_C + BALL_R * np.array([v[0], v[1], 0.0]))
            if len(pts) > 3:
                m = VMobject(color=EDGE_COLOR, stroke_width=1.0, stroke_opacity=0.6)
                m.set_points_as_corners(pts)
                lat_lines.add(m)

        # 毛の根元 (可視半球)
        roots = []
        for i in range(1, 8):
            la = math.radians(-75 + 22.5 * i)  # -52.5 .. 82.5
            for k in range(24):
                lo = math.radians(k * 15 + (7.5 if i % 2 else 0))
                p = np.array(
                    [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)]
                )
                if _sphere_view(p)[2] > 0.08:
                    roots.append(p)
        pole = np.array([0.0, 0.0, 1.0])
        roots.append(pole)  # 北極そのもの (毛の長さゼロ)

        def screen(p):
            v = _sphere_view(p)
            return BALL_C + BALL_R * np.array([v[0], v[1], 0.0])

        def hair_line(p, tangent, color):
            tip = p + HAIR * tangent
            tip = tip / np.linalg.norm(tip)  # 球面上に戻す
            return Line(screen(p), screen(tip), color=color, stroke_width=2.2)

        messy = VGroup()
        combed = VGroup()
        for p in roots:
            # 乱れた向き: 接平面内のランダム方向
            a = rng.uniform(0, 2 * math.pi)
            e1 = np.cross(p, [0, 0, 1.0])
            if np.linalg.norm(e1) < 1e-6:
                e1 = np.array([1.0, 0, 0])
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(p, e1)
            t_rand = math.cos(a) * e1 + math.sin(a) * e2
            messy.add(hair_line(p, t_rand, ACCENT_CYAN))
            t_rot = np.cross([0, 0, 1.0], p)  # v = ẑ × p (北極でゼロ)
            combed.add(hair_line(p, t_rot, ACCENT_CYAN))
        pole_s = screen(pole)
        cowlick = Dot(pole_s, radius=0.1, color=ACCENT_GOLD)
        cowlick_ring = Circle(radius=0.28, color=ACCENT_GOLD, stroke_width=2.5).move_to(pole_s)
        cowlick_label = Text("つむじ", font=FONT, font_size=26, color=ACCENT_GOLD).next_to(
            cowlick_ring, RIGHT, buff=0.12
        )

        notes = self._notes(
            [
                ("球に生えた毛を、寝かせるように梳かす", TEXT_WHITE),
                ("どう梳かしても、どこかで毛が立つ", ACCENT_CYAN),
                ("そこでは毛の向きが決まらない", ACCENT_CYAN),
                ("── 接ベクトルがゼロになる点", ACCENT_GOLD),
                ("地球の風なら、風の無い点", TEXT_WHITE),
                ("ココナッツは、平らに梳かせない", TEXT_DIM),
            ],
            y0=1.5,
            gap=0.6,
        )
        notes[0].scale(0.9)

        weights = [0.7, 0.9, 0.7, 2.2, 0.8, 0.9, 0.8, 0.8, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(ball), FadeIn(lat_lines), run_time=rt[0])
        self.play(FadeIn(messy, lag_ratio=0.01), run_time=rt[1])
        self._show([notes[0]], rt[2])
        # 梳かす: 乱れた毛が回転場に揃う
        self.play(
            AnimationGroup(
                *[Transform(m, c) for m, c in zip(messy, combed, strict=True)],
                lag_ratio=0.0,
            ),
            run_time=rt[3],
        )
        self._show([notes[1]], rt[4])
        self._pulse(cowlick, rt[5], ACCENT_GOLD, extras=(cowlick_ring, cowlick_label))
        self._show([notes[2], notes[3]], rt[6])
        self._show([notes[4]], rt[7])
        self._show([notes[5]], rt[8])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_dimension(self):
        d = self._duration
        self._title("直線と平面は、本当に違うのか", "面を埋める曲線があっても、次元は変わらない")
        lo = HSQ_C - HSQ / 2
        box = Rectangle(width=HSQ, height=HSQ, color=EDGE_COLOR, stroke_width=2).move_to(HSQ_C)

        def hpts(order):
            return [
                np.array([lo[0] + x * HSQ, lo[1] + y * HSQ, 0.0]) for x, y in _hilbert_points(order)
            ]

        curves = []
        for order in range(1, 5):
            m = VMobject(color=ACCENT_CYAN, stroke_width=max(1.2, 4.0 - 0.8 * order))
            m.set_points_as_corners(hpts(order))
            curves.append(m)
        left_cap = Text(
            "正方形を埋めていく曲線", font=FONT, font_size=22, color=ACCENT_CYAN
        ).move_to([HSQ_C[0], HSQ_C[1] + HSQ / 2 + 0.28, 0])
        left_note = Text(
            "連続。だが同じ点を何度も通る (一対一でない)", font=FONT, font_size=19, color=TEXT_DIM
        ).move_to([HSQ_C[0], HSQ_C[1] - HSQ / 2 - 0.32, 0])

        # 右: 区間と正方形の一対一対応 (見本 6 組、近い点が遠くへ)
        seg = Line([SEG_X0, SEG_Y, 0], [SEG_X1, SEG_Y, 0], color=TEXT_WHITE, stroke_width=3)
        rbox = Rectangle(width=RSQ, height=RSQ, color=EDGE_COLOR, stroke_width=2).move_to(RSQ_C)
        rng = random.Random(1878)
        us = [0.08, 0.12, 0.16, 0.55, 0.85, 0.9]
        pairs = VGroup()
        colors = [ACCENT_GOLD, ACCENT_GOLD, ACCENT_GOLD, ACCENT_PINK, ACCENT_CYAN, ACCENT_CYAN]
        for u, c in zip(us, colors, strict=True):
            a = np.array([SEG_X0 + u * (SEG_X1 - SEG_X0), SEG_Y, 0.0])
            b = RSQ_C + np.array(
                [(rng.random() - 0.5) * RSQ * 0.9, (rng.random() - 0.5) * RSQ * 0.9, 0.0]
            )
            pairs.add(
                VGroup(
                    Dot(a, radius=0.06, color=c),
                    Dot(b, radius=0.06, color=c),
                    Line(a, b, color=c, stroke_width=1.2, stroke_opacity=0.7),
                )
            )
        right_cap = Text(
            "点を一対一に対応させる", font=FONT, font_size=22, color=ACCENT_GOLD
        ).move_to([3.9, SEG_Y + 0.42, 0])
        right_note = Text(
            "一対一。だが近い点が遠くへ飛ぶ (連続でない)", font=FONT, font_size=19, color=TEXT_DIM
        ).move_to([3.9, RSQ_C[1] - RSQ / 2 - 0.32, 0])
        concl1 = Text(
            "一対一で、連続で、逆も連続なら、次元は変わらない ── 直線と平面は本当に違う",
            font=FONT,
            font_size=23,
            color=ACCENT_GOLD,
        ).move_to([0.2, -1.88, 0])
        assert left_note.get_bottom()[1] > -1.6 and right_note.get_bottom()[1] > -1.6

        weights = [0.6, 2.0, 0.7, 0.6, 1.2, 0.7, 0.9, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([left_cap], rt[0], shape_anims=[FadeIn(box, run_time=rt[0])])
        cur = curves[0]
        per = max(0.3, rt[1] / len(curves))
        self.play(Create(cur), run_time=per)
        for nxt in curves[1:]:
            self.play(Transform(cur, nxt), run_time=per)
        self._show([left_note], rt[2])
        self._show(
            [right_cap], rt[3], shape_anims=[FadeIn(seg, run_time=0.5), FadeIn(rbox, run_time=0.5)]
        )
        per = max(0.2, rt[4] / len(pairs))
        for pr in pairs:
            self.play(FadeIn(pr), run_time=per)
        self._show([right_note], rt[5])
        self._show([concl1], rt[6])
        self.wait(rt[7])
        self.wait(CODA)


SCENES = {
    "line": BrouwerFixedPoint,
    "disk": BrouwerFixedPoint,
    "retraction": BrouwerFixedPoint,
    "hairy_ball": BrouwerFixedPoint,
    "dimension": BrouwerFixedPoint,
}
