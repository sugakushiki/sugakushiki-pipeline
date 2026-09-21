"""
ramsey_bounds_ladder.py - ラムゼー数の「境目」と、上限・下限の九十年 for 数学史記

ラムゼーの定理は「十分に多ければ同じ色の k 人組が必ず現れる」と言うだけで、
何人から現れるか (ラムゼー数 R(k,k)) は教えない。三人組の境目は 6、四人組は 18、
五人組は 43 以上 46 以下、六人組は 102 以上 165 以下 (刊行済みの値) としか
分かっていない。

Modes:
    known_values    - 四行の数直線 (0 〜 170)。三人組 = 6、四人組 = 18 を点で、
                      五人組 = 43〜46、六人組 = 102〜165 を帯で示す。
                      Fixed params: R(3,3)=6 / R(4,4)=18 / 43≤R(5,5)≤46 /
                      102≤R(6,6)≤165。画面に出す年は 1955 (R(4,4))、
                      1989 (R(5,5) 下限)、2024 (R(5,5) 上限) の三つだけ。
                      **165 は刊行済みの上限 (1994)。160 は未刊行の私信なので出さない。**

    exponential_gap - 「指数の底」の物差し (1 〜 4.3)。上限 4 (1935、二項係数
                      C(2k-2,k-1) ≈ 4^k)、下限 √2 ≈ 1.414 (1947、2^(k/2))、
                      2023 年の (4 - 2^-7) ≈ 3.992、2024 年の ≈ 3.799 を目盛りに置く。
                      Fixed params: 底 = 4 / 2^(1/2) / 4 - 2^(-7) / 3.7992。
                      **底の数値はレンダ時に式から計算する** (√2 と 4 - 2^-7)。
                      k 人組の人数そのものを描かない: 小さい k では二項係数の上限の
                      ほうが (4-ε)^k より小さく、人数で描くと 2023 年の改良が
                      「悪化」に見えてしまう (指数的改良は k が大きいときの話)。

固定値の出どころ: R(3,3)=6 は組合せの標準証明、R(4,4)=18 は Greenwood–Gleason (1955)、
R(5,5) の 43 は Exoo (1989)、46 は Angeltveit–McKay (2024)、R(6,6) の 102 は
Kalbfleisch (1966)、165 は Mackey (1994)。上限 4^k は Erdős–Szekeres (1935)、下限 2^(k/2)
は Erdős (1947)、(4-ε)^k (ε=2^-7) は Campos–Griffiths–Morris–Sahasrabudhe (2023)、
3.7992^k は Gupta–Ndiaye–Norin–Wei (2024)。episode_config の verified_facts と一致する。

**画面に人名は出さない** (帰属の主張はナレーション側で行う)。年は上記の範囲だけ。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 071 (フランク・ラムゼー) — 数学 6 (数の壁) / 数学 8 (上限と下限の九十年)。
"""

import math

from manim import (
    DOWN,
    UP,
    AnimationGroup,
    Dot,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
    Scene,
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

TITLE_Y = 2.95
SUB_Y = 2.45
CODA = 3.0
TEXT_FADE = 0.6  # テキストの FadeIn はこの秒数で入れて、残りは保持する

# --- known_values ---------------------------------------------------------
# (行ラベル, MathTex, 下限, 上限 (None = 確定値), 年ラベル)
KNOWN = [
    ("三人組", r"R(3,3)", 6, None, ""),
    ("四人組", r"R(4,4)", 18, None, "1955"),
    ("五人組", r"R(5,5)", 43, 46, "1989 〜 2024"),
    ("六人組", r"R(6,6)", 102, 165, ""),
]
AXIS_MAX = 170
AX_LEFT = -2.6
AX_RIGHT = 5.9
ROW_Y = [1.55, 0.65, -0.25, -1.15]
LABEL_X = -5.2

# --- exponential_gap ------------------------------------------------------
BASE_MIN = 1.0
BASE_MAX = 4.3
BX_LEFT = -5.6
BX_RIGHT = 5.6
BASE_Y = -0.2


def _xv(v):
    return AX_LEFT + (AX_RIGHT - AX_LEFT) * v / AXIS_MAX


def _xb(b):
    return BX_LEFT + (BX_RIGHT - BX_LEFT) * (b - BASE_MIN) / (BASE_MAX - BASE_MIN)


def _bases():
    """指数の底をレンダ時に式から計算する。"""
    return {
        "upper_1935": 4.0,  # C(2k-2, k-1) ~ 4^k / sqrt(k)
        "lower_1947": math.sqrt(2.0),  # 2^(k/2)
        "upper_2023": 4.0 - 2.0**-7,  # (4 - ε)^k, ε = 2^-7
        "upper_2024": 3.7992,  # ≈ (0.14/e 改良後の底、小数 4 桁)
    }


LINT_FACTUAL_CLAIMS = {
    "known_values": {"people": [], "years": ["1955", "1989", "2024"]},
    "exponential_gap": {"people": [], "years": ["1935", "1947", "2023", "2024"]},
}

LINT_VISUAL_ELEMENTS = {
    "known_values": ["数直線", "点", "帯", "目盛り"],
    "exponential_gap": ["物差し", "目盛り", "帯", "矢印"],
}


class RamseyBoundsLadder(Scene):
    """既知のラムゼー数 / 指数の底の物差し の 2 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "known_values")
        self._duration = float(params.get("duration", 30))
        if mode == "exponential_gap":
            self.build_gap()
        else:
            self.build_known()

    # ------------------------------------------------------------------
    def _title(self, main, sub):
        t = Text(main, font=FONT, font_size=34, color=ACCENT_GOLD).move_to(UP * TITLE_Y)
        s = Text(sub, font=FONT, font_size=22, color=TEXT_DIM).move_to(UP * SUB_Y)
        self.play(FadeIn(t), FadeIn(s), run_time=1.0)

    def _show(self, texts, run_time, shape_anims=()):
        """テキストは TEXT_FADE 秒で表示し、残りの時間は保持する (規約「罠 2」対策)。

        テキストの FadeIn に pace() の長い run_time をそのまま渡すと、尺の長い scene で
        文字が数秒間半透明のままになる。shape_anims (図形の FadeIn 等、run_time 付き) だけが
        run_time いっぱいを使い、テキストは短く入れて保持する。
        """
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
    def build_known(self):
        d = self._duration
        self._title("境目の数", "同じ色の k 人組が「必ず」現れるのは、何人から")

        # 共通の目盛り (最下行の下)
        ticks = VGroup()
        for v in (0, 50, 100, 150):
            x = _xv(v)
            ticks.add(Line([x, -1.55, 0], [x, -1.45, 0], color=EDGE_COLOR, stroke_width=2))
            ticks.add(Text(str(v), font=FONT, font_size=18, color=TEXT_DIM).move_to([x, -1.8, 0]))

        rows = []
        for (name, tex, lo, hi, year), y in zip(KNOWN, ROW_Y, strict=True):
            axis = Line([AX_LEFT, y, 0], [AX_RIGHT, y, 0], color=EDGE_COLOR, stroke_width=2)
            label = Text(name, font=FONT, font_size=24, color=TEXT_WHITE).move_to(
                [LABEL_X - 0.75, y, 0]
            )
            mt = MathTex(tex, font_size=30, color=TEXT_DIM).move_to([LABEL_X + 0.9, y, 0])
            if hi is None:
                mark = Dot([_xv(lo), y, 0], color=ACCENT_GOLD, radius=0.11)
                val = Text(f"= {lo}", font=FONT, font_size=24, color=ACCENT_GOLD).next_to(
                    mark, UP, buff=0.12
                )
            else:
                color = ACCENT_PINK if hi - lo < 10 else ACCENT_CYAN
                bar = Rectangle(
                    width=max(0.12, _xv(hi) - _xv(lo)),
                    height=0.22,
                    color=color,
                    fill_color=color,
                    fill_opacity=0.85,
                    stroke_width=0,
                ).move_to([(_xv(lo) + _xv(hi)) / 2, y, 0])
                cap_l = Line(
                    [_xv(lo), y - 0.2, 0], [_xv(lo), y + 0.2, 0], color=color, stroke_width=3
                )
                cap_r = Line(
                    [_xv(hi), y - 0.2, 0], [_xv(hi), y + 0.2, 0], color=color, stroke_width=3
                )
                mark = VGroup(bar, cap_l, cap_r)
                val = Text(f"{lo} 〜 {hi}", font=FONT, font_size=24, color=color).next_to(
                    mark, UP, buff=0.12
                )
            yr = (
                Text(year, font=FONT, font_size=18, color=TEXT_DIM).next_to(mark, DOWN, buff=0.1)
                if year
                else VGroup()
            )
            rows.append((axis, label, mt, mark, val, yr))

        weights = [0.6] + [1.0, 1.0, 1.3, 1.3] + [0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(ticks), *[FadeIn(r[0]) for r in rows], run_time=rt[0])
        for i, (_axis, label, mt, mark, val, yr) in enumerate(rows):
            self._show([label, mt], rt[1 + i] * 0.35)
            self._show(
                [val, yr], rt[1 + i] * 0.65, shape_anims=[FadeIn(mark, run_time=rt[1 + i] * 0.65)]
            )
        # 「= 6」のラベル (x≈-2.3, y≈1.85) と重ならないよう右寄せ
        note = Text(
            "五人組で、もう答えは分からない", font=FONT, font_size=24, color=ACCENT_PINK
        ).move_to([2.6, 2.0, 0])
        self._show([note], rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_gap(self):
        d = self._duration
        b = _bases()
        self._title("上限と下限の九十年", "k 人組の境目を「指数の底」で見る")

        formula = MathTex(
            r"\sqrt{2}^{\,k} \;<\; R(k,k) \;<\; 4^{k}",
            font_size=40,
            color=TEXT_WHITE,
        ).move_to([0, 1.55, 0])
        rule = Line([BX_LEFT, BASE_Y, 0], [BX_RIGHT, BASE_Y, 0], color=EDGE_COLOR, stroke_width=3)
        ticks = VGroup()
        for v in (1, 2, 3, 4):
            x = _xb(v)
            ticks.add(
                Line([x, BASE_Y - 0.12, 0], [x, BASE_Y + 0.12, 0], color=EDGE_COLOR, stroke_width=2)
            )
            ticks.add(
                Text(str(v), font=FONT, font_size=20, color=TEXT_DIM).move_to([x, BASE_Y - 0.42, 0])
            )
        rule_label = Text("底", font=FONT, font_size=20, color=TEXT_DIM).move_to(
            [BX_RIGHT + 0.45, BASE_Y, 0]
        )

        def marker(base, color, above, text, dy=0.0, dx=0.0):
            """物差し上のピンと、そこから伸びる引き出し線つきラベル。

            dx でラベルを横にずらす。2023 と 2024 のピンは 0.65 だけしか離れていないので、
            ラベルを真下に置くと一方の引き出し線が他方のラベルを貫通して所属が逆に見える
            (manim_vision_qa が指摘)。左右に振り分けて斜めの線で結ぶ。
            """
            x = _xb(base)
            pin = Line([x, BASE_Y - 0.25, 0], [x, BASE_Y + 0.25, 0], color=color, stroke_width=5)
            y = BASE_Y + (0.95 + dy if above else -(0.95 + dy))
            lab = Text(text, font=FONT, font_size=22, color=color).move_to([x + dx, y, 0])
            end_y = y - (0.28 if above else -0.28)
            stem = Line(
                [x, BASE_Y + (0.25 if above else -0.25), 0],
                [x + dx, end_y, 0],
                color=color,
                stroke_width=1.5,
            )
            return VGroup(pin, stem, lab)

        lower = marker(b["lower_1947"], ACCENT_CYAN, True, "下限 √2 (1947)")
        upper = marker(b["upper_1935"], ACCENT_GOLD, True, "上限 4 (1935)")
        gap = Rectangle(
            width=_xb(b["upper_1935"]) - _xb(b["lower_1947"]),
            height=0.5,
            color=EDGE_COLOR,
            fill_color=EDGE_COLOR,
            fill_opacity=0.35,
            stroke_width=0,
        ).move_to([(_xb(b["upper_1935"]) + _xb(b["lower_1947"])) / 2, BASE_Y, 0])
        gap_label = Text(
            "九十年、この幅は動かなかった", font=FONT, font_size=24, color=TEXT_DIM
        ).move_to([0, -1.3, 0])
        # 2023 は右下へ (dx=+0.7)、2024 は左下へ (dx=-0.9)。引き出し線が交差せず、
        # どちらの線も他方のラベルを通らない (2023 ラベル x≈4.5〜6.1 / 2024 の線は x≤3.9)。
        m2023 = marker(
            b["upper_2023"], ACCENT_PINK, False, f"2023  {b['upper_2023']:.3f}", dy=0.0, dx=0.7
        )
        m2024 = marker(
            b["upper_2024"], ACCENT_PINK, False, f"2024  {b['upper_2024']:.3f}", dy=0.55, dx=-0.9
        )
        # 2023/2024 のラベルは物差しの下 (y≈-1.15 / -1.7、右端寄り)。最終行はその左に置き、
        # 横に触れないよう中心を x=-1.4 に寄せる (右端 x≈+1.9 < 2024 ラベルの左端 x≈+3.6)
        moved = Text(
            "動いたのは上限だけ。下限は今も √2", font=FONT, font_size=24, color=ACCENT_PINK
        ).move_to([-1.4, -1.85, 0])

        weights = [0.9, 0.8, 1.0, 1.0, 0.9, 1.0, 1.0, 0.9]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([formula], rt[0])
        self._show([ticks, rule_label], rt[1], shape_anims=[FadeIn(rule, run_time=rt[1])])
        self._show([upper], rt[2])
        self._show([lower], rt[3])
        self._show([gap_label], rt[4], shape_anims=[FadeIn(gap, run_time=rt[4])])
        self._show([m2023], rt[5])
        self._show([m2024], rt[6])
        self.remove(gap_label)
        self._show([moved], rt[7])
        self.wait(CODA)


SCENES = {
    "known_values": RamseyBoundsLadder,
    "exponential_gap": RamseyBoundsLadder,
}
