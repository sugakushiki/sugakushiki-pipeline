"""
counting_rod_root_extraction.py - 正負開方術: 高次方程式の実数解を桁ごとに取り出す for 数学史記

『数書九章』の正負開方術は、高次方程式の実数解を上の桁から一つずつ立てていく手順で
ある。桁を一つ立てるたびに方程式そのものを書き換え、残りの實 (定数項) を零へ近づける。
本質的に同じ手順は十一世紀の賈憲の増乗開方法にさかのぼり、北宋の劉益が負の係数を含む
場合へ進めた。秦九韶はそれを任意の次数まで一般化して体系化した側である。
**「秦九韶が発明した」ではない。**

Modes:
    board    - 田域類「尖田求積」の四次方程式を桁ごとに解く。
               二つの尖った田について 大斜 39 歩・小斜 25 歩・中広 30 歩 から面積を問う問題で、
               -x^4 + 763200 x^2 - 40642560000 = 0、答は「積八百四十歩」。
               **840 は面積 (歩) であって長さではない。** 術の末尾が「開翻法三乗方得積」で、
               開いて出た数がそのまま積になる (遙度圓城のような自乗は要らない)。
               百の位に 8、十の位に 4 と立てるたびに、残りの實が
               -40,642,560,000 → +38,205,440,000 → 0 と動く。
               **画面に出る實はレンダ時に係数から計算する** (書き写した数を並べない)。
               この式は正の根を二つ持つ (240 と 840)。正負開方術は問題に合う実数解を
               求める手順であって、根を全部列挙する手順ではない。

    degree10 - 測望類「遙度圓城」の十次方程式を盤に並べる。
               x^10 + 15x^8 + 72x^6 - 864x^4 - 11664x^2 - 34992 = 0、解 x = 3。
               奇数次の位はすべて空位なので、盤には穴があく。
               **解の 3 は長さではない。** 原文の術は「得數自乗為徑」と言い、
               3 を自乗した 九里 が城の直径、三倍した 二十七里 が周である
               (円周率を三とする古率)。

固定値の出どころ: 係数は維基文庫の四庫全書本『數學九章』で確認し、**どちらの式も術文の指示
どおりに問題の数値から組み立て直して一致を確かめた**。遙度圓城は 北里 3・東行 9 から
1・15・72・-864・-11664・-34992 が、尖田求積は 大斜 39・小斜 25・中広 30 から
半冪 225 → 小率 90000 / 大率 291600 → 實 40642560000・從上亷 763200・益隅 -1 が出る。x=3 を代入すると厳密に零になり、因数分解は
(x-3)(x+3)(x^2+6)^2(x^4+12x^2+108) で実根は 3 と -3 の二つ (長さなので負の根は
問題に合わず、正負開方術は問題に合う解を取り出す手順なので 3 を採る。2026-09-06 に
「実根は 3 のみ」という誤記を訂正。画面には出していないので描画は不変)。四次式のほうは f(840)=0、
f(240)=0 を数値で確認した。

**注意して書くこと**: 解法の呼び名の由来 (「玲瓏」) は裏が取れていないので画面に出さない。
画面に人名・年号は出さない。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 070 (秦九韶) — 数学 C (正負開方術 / 遙度圓城の十次方程式)。
"""

from manim import (
    FadeIn,
    Line,
    MathTex,
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

# 尖田求積 (田域類) の四次方程式 — 降冪
QUARTIC = [-1, 0, 763200, 0, -40642560000]
QUARTIC_DIGITS = [800, 40]  # 上の桁から立てていく (合計 840)

# 遙度圓城 (測望類) の十次方程式 — 降冪 (x^10 .. x^0)
DEGREE10 = [1, 0, 15, 0, 72, 0, -864, 0, -11664, 0, -34992]
DEGREE10_ROOT = 3


def _horner(coeffs, x):
    """降冪の係数列に x を代入した値。"""
    v = 0
    for c in coeffs:
        v = v * x + c
    return v


def _comma(n):
    """桁区切りを入れた文字列。負号はマイナス記号を使う。"""
    return f"{n:,}".replace("-", "−")


LINT_FACTUAL_CLAIMS = {
    "board": {"people": [], "years": []},
    "degree10": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "board": ["式", "数値", "桁", "行"],
    "degree10": ["盤", "ます目", "空位", "数値", "次数"],
}


class CountingRodRootExtraction(Scene):
    """桁ごとの開方 / 十次方程式の盤 の 2 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "board")
        self._duration = float(params.get("duration", 25))

        if mode == "degree10":
            self.build_degree10()
        else:
            self.build_board()

    # ------------------------------------------------------------------
    # mode: board — 桁を一つ立てるたびに残りの實が縮む
    # ------------------------------------------------------------------
    def build_board(self):
        CODA = 3.0
        # play は 式 1 + 見出し 1 + 初期の實 1 + 桁 2 + 結論 1 = 6 回。重みも 6 個そろえる
        rt = pace(self._duration, [1.0, 0.9, 1.2, 1.2, 1.2, 1.0], intro=0.6, coda=CODA)

        title = Text(
            "上の桁から一つずつ立てていく", font=FONT, font_size=28, color=TEXT_WHITE
        ).move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.6)

        eq = MathTex(
            r"-x^{4} + 763200\,x^{2} - 40642560000 = 0",
            font_size=38,
            color=ACCENT_CYAN,
        ).move_to([0, 2.25, 0])
        self.play(FadeIn(eq), run_time=rt[0])

        # 見出し
        head_l = Text("立てた桁", font=FONT, font_size=22, color=TEXT_DIM).move_to([-3.5, 1.35, 0])
        head_r = Text("残りの實", font=FONT, font_size=22, color=TEXT_DIM).move_to([2.3, 1.35, 0])
        rule = Line([-5.4, 1.05, 0], [5.4, 1.05, 0], color=EDGE_COLOR, stroke_width=2.0)
        self.play(FadeIn(VGroup(head_l, head_r, rule)), run_time=rt[1])

        # 最初の實 = 定数項
        ys = [0.55, -0.15, -0.85]
        row0 = VGroup(
            Text("──", font=FONT, font_size=26, color=TEXT_DIM).move_to([-3.5, ys[0], 0]),
            Text(_comma(QUARTIC[-1]), font=FONT, font_size=28, color=TEXT_WHITE).move_to(
                [2.3, ys[0], 0]
            ),
        )
        self.play(FadeIn(row0), run_time=rt[2])

        # 桁を立てるたびに實を計算し直す
        placed = 0
        for i, d in enumerate(QUARTIC_DIGITS):
            placed += d
            rest = _horner(QUARTIC, placed)
            col = ACCENT_GOLD if rest != 0 else ACCENT_PINK
            row = VGroup(
                Text(_comma(d), font=FONT, font_size=28, color=ACCENT_GOLD).move_to(
                    [-3.5, ys[i + 1], 0]
                ),
                Text(_comma(rest), font=FONT, font_size=28, color=col).move_to([2.3, ys[i + 1], 0]),
            )
            self.play(FadeIn(row), run_time=rt[3 + i])

        total = sum(QUARTIC_DIGITS)
        concl = Text(
            f"實が零になったところで止まる ── 田の面積 {_comma(total)} 歩",
            font=FONT,
            font_size=26,
            color=ACCENT_PINK,
        ).move_to([0, -1.75, 0])
        self.play(FadeIn(concl), run_time=rt[5])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: degree10 — 盤に係数を並べ、空位を見せる
    # ------------------------------------------------------------------
    def build_degree10(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 1.0, 1.0, 1.1, 1.1], intro=0.6, coda=CODA)

        title = Text(
            "十次の方程式を、盤の上に置く", font=FONT, font_size=28, color=TEXT_WHITE
        ).move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.6)

        n = len(DEGREE10)  # 11 (x^10 .. x^0)
        x0, step = -5.30, 1.15
        cells = VGroup()
        powers = VGroup()
        values = VGroup()

        for i, c in enumerate(DEGREE10):
            x = x0 + i * step
            deg = n - 1 - i
            cells.add(
                Line([x - 0.5, 1.05, 0], [x - 0.5, 1.95, 0], color=EDGE_COLOR, stroke_width=1.6)
            )
            powers.add(
                Text(str(deg), font=FONT, font_size=20, color=TEXT_DIM).move_to([x, 2.25, 0])
            )
            if c == 0:
                # 空位 — 何も置かない位を点で示す
                values.add(
                    Text("・", font=FONT, font_size=26, color=EDGE_COLOR).move_to([x, 1.5, 0])
                )
            else:
                values.add(
                    Text(str(c), font=FONT, font_size=21, color=ACCENT_CYAN).move_to([x, 1.5, 0])
                )
        cells.add(
            Line(
                [x0 + n * step - 0.5, 1.05, 0],
                [x0 + n * step - 0.5, 1.95, 0],
                color=EDGE_COLOR,
                stroke_width=1.6,
            )
        )
        top = Line(
            [x0 - 0.5, 1.95, 0], [x0 + n * step - 0.5, 1.95, 0], color=EDGE_COLOR, stroke_width=1.6
        )
        bot = Line(
            [x0 - 0.5, 1.05, 0], [x0 + n * step - 0.5, 1.05, 0], color=EDGE_COLOR, stroke_width=1.6
        )

        deg_cap = Text("次数", font=FONT, font_size=20, color=TEXT_DIM).move_to(
            [x0 - 1.05, 2.25, 0]
        )
        self.play(FadeIn(VGroup(cells, top, bot, powers, deg_cap)), run_time=rt[0])
        self.play(FadeIn(values), run_time=rt[1])

        gap = Text(
            "一つおきに何も置かれない位が並ぶ", font=FONT, font_size=24, color=TEXT_DIM
        ).move_to([0, 0.55, 0])
        self.play(FadeIn(gap), run_time=rt[2])

        root = Text(
            f"桁ごとに立てて出てくる数は {DEGREE10_ROOT}",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        ).move_to([0, -0.35, 0])
        self.play(FadeIn(root), run_time=rt[3])

        d = DEGREE10_ROOT * DEGREE10_ROOT
        concl = VGroup(
            Text(
                f"ただしこれは長さではない ── 自乗して 徑 {d} 里",
                font=FONT,
                font_size=26,
                color=ACCENT_PINK,
            ).move_to([0, -1.15, 0]),
            Text(
                f"三倍して 周 {3 * d} 里 (円周率を三とする古率)",
                font=FONT,
                font_size=24,
                color=TEXT_DIM,
            ).move_to([0, -1.80, 0]),
        )
        self.play(FadeIn(concl), run_time=rt[4])
        self.wait(CODA)


SCENES = {
    "board": CountingRodRootExtraction,
    "degree10": CountingRodRootExtraction,
}
