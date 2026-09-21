"""
latitude_of_forms.py - 形態の緯度 (質を図形にする) と 平均速度の定理 for 数学史記

オレーム『質と運動の配置について』は、質の強さ (intensio) を縦の線の長さ (latitudo)、
質の広がり (時間や長さ、extensio) を横の線 (longitudo) にとり、質の全体を平面図形として
描く。一様な質は長方形、一様に変化する質は直角三角形 (または台形) になり、量は面積で
測られる。速さを緯度、時間を経度にとれば運動に使え、一様加速の距離 = 三角形の面積 =
高さ半分の長方形の面積、が「平均速度の定理」の幾何的証明になる。

Modes:
    uniform_difform - 横線 (広がり) の上に縦線 (強さ) を立てていく。左: 一様 (全部同じ
                      高さ → 長方形)、中: 一様に変化 (直線的に伸びる → 三角形)、右:
                      一様に変化・出発点あり (台形)。最後に「量 = 面積」。
                      Fixed params: 3 図、縦線 各 9 本、高さ 1.6 / 0→1.6 / 0.6→1.6。
                      画面に年号・人名なし。

    mean_speed      - 横軸 = 時間、縦軸 = 速さ。原点から (T, v) への直角三角形 (一様加速)
                      と、高さ v/2 の長方形 (一定速度)。長方形からはみ出す右上の小三角形を
                      中点 E のまわりに 180° 回して左の空きに移し、面積が等しいことを見せる。
                      Fixed params: T = 6.0 単位、v = 2.6 単位、E = (T/2, v/2)。
                      画面に出す年は 1335 (言葉で述べられた) と 1638 (同じ図が使われた) の
                      二つだけ。人名は出さない。

固定値の出どころ: Clagett (1968) の Tractatus de configurationibus の英訳 (二次資料経由)、
ヘイツベリー『詭弁解決規則』(1335 年ごろ) の言明、ガリレオ『新科学対話』(1638) 第三日の図。
episode_config の verified_facts と一致する。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 072 (ニコル・オレーム) — 数学 4 (uniform_difform) / 数学 5 (mean_speed)。
"""

import math

import numpy as np
from manim import (
    PI,
    UP,
    AnimationGroup,
    Arrow,
    DashedLine,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Polygon,
    Rotate,
    Scene,
    Text,
    VGroup,
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

TITLE_Y = 2.95
SUB_Y = 2.45
CODA = 3.0
TEXT_FADE = 0.6

# --- uniform_difform ------------------------------------------------------
N_LINES = 9
PANEL_W = 3.3
PANEL_X = [-4.4, 0.0, 4.4]  # 各図の中心 x
BASE_Y = -1.15
H_MAX = 1.6
# (見出し, 左端の高さ, 右端の高さ, 色)
PANELS = [
    ("一様", H_MAX, H_MAX, ACCENT_CYAN),
    ("一様に変化", 0.0, H_MAX, ACCENT_GOLD),
    ("一様に変化 (出発点あり)", 0.6, H_MAX, ACCENT_PINK),
]

# --- mean_speed -----------------------------------------------------------
T_LEN = 6.0
V_MAX = 2.6
OX = -3.9
OY = -1.45

LINT_FACTUAL_CLAIMS = {
    "uniform_difform": {"people": [], "years": []},
    "mean_speed": {"people": [], "years": ["1335", "1638"]},
}

LINT_VISUAL_ELEMENTS = {
    "uniform_difform": ["縦線", "横線", "長方形", "三角形", "台形", "面積"],
    "mean_speed": ["縦軸", "横軸", "三角形", "長方形", "面積"],
}


class LatitudeOfForms(Scene):
    """形態の緯度 / 平均速度の定理 の 2 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "uniform_difform")
        self._duration = float(params.get("duration", 35))
        if mode == "mean_speed":
            self.build_mean_speed()
        else:
            self.build_uniform_difform()

    # ------------------------------------------------------------------
    def _title(self, main, sub):
        t = Text(main, font=FONT, font_size=34, color=ACCENT_GOLD).move_to(UP * TITLE_Y)
        s = Text(sub, font=FONT, font_size=22, color=TEXT_DIM).move_to(UP * SUB_Y)
        self.play(FadeIn(t), FadeIn(s), run_time=1.0)

    def _show(self, texts, run_time, shape_anims=()):
        t = min(TEXT_FADE, run_time)
        if shape_anims:
            self.play(
                AnimationGroup(*shape_anims, *[FadeIn(x, run_time=t) for x in texts], lag_ratio=0.0)
            )
        else:
            self.play(*[FadeIn(x) for x in texts], run_time=t)
            if run_time - t > 0.02:
                self.wait(run_time - t)

    # ------------------------------------------------------------------
    def build_uniform_difform(self):
        d = self._duration
        self._title("見えない量を、図形にする", "強さを縦の線に、広がりを横の線にとる")

        panels = []
        for (head, h0, h1, color), cx in zip(PANELS, PANEL_X, strict=True):
            x0, x1 = cx - PANEL_W / 2, cx + PANEL_W / 2
            base = Line([x0, BASE_Y, 0], [x1, BASE_Y, 0], color=TEXT_WHITE, stroke_width=3)
            lines = VGroup()
            for i in range(N_LINES):
                f = i / (N_LINES - 1)
                x = x0 + PANEL_W * f
                h = h0 + (h1 - h0) * f
                if h > 0.01:
                    lines.add(Line([x, BASE_Y, 0], [x, BASE_Y + h, 0], color=color, stroke_width=3))
            shape = Polygon(
                [x0, BASE_Y, 0],
                [x1, BASE_Y, 0],
                [x1, BASE_Y + h1, 0],
                [x0, BASE_Y + h0, 0],
                color=color,
                fill_color=color,
                fill_opacity=0.28,
                stroke_width=2,
            )
            label = Text(head, font=FONT, font_size=22, color=TEXT_WHITE).move_to(
                [cx, BASE_Y + H_MAX + 0.45, 0]
            )
            name = {ACCENT_CYAN: "長方形", ACCENT_GOLD: "三角形", ACCENT_PINK: "台形"}[color]
            fig_name = Text(name, font=FONT, font_size=22, color=color).move_to(
                [cx, BASE_Y - 0.4, 0]
            )
            panels.append((base, lines, shape, label, fig_name))

        axis_note = VGroup(
            Text("縦 = 強さ", font=FONT, font_size=20, color=TEXT_DIM),
            Text("横 = 広がり (時間・長さ)", font=FONT, font_size=20, color=TEXT_DIM),
        )
        axis_note[0].move_to([-4.4, 1.55, 0])
        axis_note[1].move_to([0.0, 1.55, 0])
        area = Text("量 = 面積", font=FONT, font_size=28, color=ACCENT_GOLD).move_to([4.4, 1.55, 0])

        weights = [0.6] + [1.0, 1.2, 1.2] + [0.9]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([axis_note], rt[0])
        for i, (base, lines, shape, label, fig_name) in enumerate(panels):
            r = rt[1 + i]
            self._show([label], r * 0.2, shape_anims=[FadeIn(base, run_time=r * 0.2)])
            self.play(FadeIn(lines, lag_ratio=0.2), run_time=max(0.3, r * 0.45))
            self._show([fig_name], r * 0.35, shape_anims=[FadeIn(shape, run_time=r * 0.35)])
        self._show([area], rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_mean_speed(self):
        d = self._duration
        self._title("平均速度の定理", "一様に加速して進む距離 = 最終速度の半分で進む距離")

        def p(t, v):
            return np.array([OX + t, OY + v, 0.0])

        x_axis = Arrow(p(-0.2, 0), p(T_LEN + 0.6, 0), color=TEXT_WHITE, stroke_width=3, buff=0)
        y_axis = Arrow(p(0, -0.2), p(0, V_MAX + 0.5), color=TEXT_WHITE, stroke_width=3, buff=0)
        x_label = Text("時間", font=FONT, font_size=22, color=TEXT_WHITE).move_to(
            p(T_LEN + 0.6, 0.3)
        )
        y_label = Text("速さ", font=FONT, font_size=22, color=TEXT_WHITE).move_to(
            p(-0.55, V_MAX + 0.35)
        )

        A, C, G = p(0, 0), p(T_LEN, 0), p(T_LEN, V_MAX)
        E = p(T_LEN / 2, V_MAX / 2)
        F, Dp = p(0, V_MAX / 2), p(T_LEN, V_MAX / 2)

        tri = Polygon(
            A, C, G, color=ACCENT_GOLD, fill_color=ACCENT_GOLD, fill_opacity=0.25, stroke_width=3
        )
        tri_label = Text("一様に加速", font=FONT, font_size=22, color=ACCENT_GOLD).move_to(
            p(T_LEN * 0.72, V_MAX * 0.2)
        )
        rect = Polygon(A, C, Dp, F, color=ACCENT_CYAN, fill_opacity=0.0, stroke_width=3)
        # 長方形の左外 (回転してくる小三角形の着地先 A-E-F を避ける)
        rect_label = Text("半分の速さで一定", font=FONT, font_size=22, color=ACCENT_CYAN).move_to(
            [-5.75, OY + V_MAX / 4, 0]
        )
        half_tick = MathTex(r"\tfrac{v}{2}", font_size=30, color=ACCENT_CYAN).move_to(
            p(-0.4, V_MAX / 2)
        )
        v_tick = MathTex(r"v", font_size=30, color=ACCENT_GOLD).move_to(p(-0.4, V_MAX))
        mid_line = DashedLine(p(T_LEN / 2, 0), E, color=TEXT_DIM, stroke_width=2, dash_length=0.1)
        e_dot = Dot(E, color=ACCENT_PINK, radius=0.07)

        # 長方形からはみ出す小三角形 E-G-D と、左の空き A-E-F (合同)
        extra = Polygon(
            E, G, Dp, color=ACCENT_PINK, fill_color=ACCENT_PINK, fill_opacity=0.75, stroke_width=2
        )
        gap = Polygon(A, E, F, color=ACCENT_PINK, fill_opacity=0.0, stroke_width=2)
        gap_dash = DashedLine(A, E, color=ACCENT_PINK, stroke_width=2, dash_length=0.1)
        # 小三角形が左へ移ったあとも元の位置 (E-G-D) に輪郭を残す。manim_vision_qa:
        # 「はみ出す部分」と「足りない部分」の両方が見えていないと合同が伝わらない
        extra_ghost = Polygon(
            E, G, Dp, color=ACCENT_PINK, fill_color=ACCENT_PINK, fill_opacity=0.22, stroke_width=2
        )
        same = Text("同じ形、同じ面積", font=FONT, font_size=24, color=ACCENT_PINK).move_to(
            p(T_LEN * 0.5, V_MAX + 0.35)
        )
        concl = Text(
            "距離 = 面積。三角形と長方形は等しい", font=FONT, font_size=26, color=ACCENT_GOLD
        ).move_to([0.3, -1.85, 0])
        # 右上の小さな年ラベル (y 軸ラベルから離れた位置)
        years = VGroup(
            Text("1335  言葉で述べられた規則", font=FONT, font_size=18, color=TEXT_DIM),
            Text("1638  同じ図が使われる", font=FONT, font_size=18, color=TEXT_DIM),
        )
        years[0].move_to([4.4, 1.85, 0])
        years[1].move_to([4.4, 1.5, 0])

        assert math.isclose(T_LEN * V_MAX / 2, T_LEN * (V_MAX / 2))

        weights = [0.7, 1.0, 0.8, 1.0, 0.6, 0.8, 1.6, 0.9, 0.9]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show(
            [x_label, y_label],
            rt[0],
            shape_anims=[FadeIn(x_axis, run_time=rt[0]), FadeIn(y_axis, run_time=rt[0])],
        )
        self._show([tri_label, v_tick], rt[1], shape_anims=[FadeIn(tri, run_time=rt[1])])
        self._show(
            [half_tick],
            rt[2],
            shape_anims=[FadeIn(mid_line, run_time=rt[2]), FadeIn(e_dot, run_time=rt[2])],
        )
        self._show([rect_label], rt[3], shape_anims=[FadeIn(rect, run_time=rt[3])])
        self.play(FadeIn(extra), run_time=rt[4])
        self._show(
            [],
            rt[5],
            shape_anims=[
                FadeIn(gap, run_time=rt[5]),
                FadeIn(gap_dash, run_time=rt[5]),
                FadeIn(extra_ghost, run_time=rt[5]),
            ],
        )
        self.play(Rotate(extra, angle=PI, about_point=E), run_time=rt[6])
        self._show([same], rt[7])
        self._show([concl, years], rt[8])
        self.wait(CODA)


SCENES = {
    "uniform_difform": LatitudeOfForms,
    "mean_speed": LatitudeOfForms,
}
