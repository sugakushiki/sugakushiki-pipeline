"""
harmonic_series_oresme.py - 調和級数の発散 (オレームの塊分け) と、その対照 for 数学史記

1 + 1/2 + 1/3 + 1/4 + … は、足す数が限りなくゼロに近づくのに、和は限りなく大きくなる。
オレーム (1350 年ごろ、『ユークリッド幾何学問題集』第 2 問) の証明は、項を
[1/3, 1/4], [1/5 … 1/8], [1/9 … 1/16], … と塊に分け、どの塊も 1/2 より大きいので
「1/2 より大きい塊が無限にある = 全体は無限」と言う。

Modes:
    grouping              - 塊ごとに 1 行。各行は項の幅を横に並べた棒で、破線が 1/2 の
                            基準。塊の合計が基準を越えることを行ごとに見せ、最後に
                            H > 1 + 1/2 + 1/2 + 1/2 + … を出す。
                            Fixed params: 行 = [1], [1/2], [1/3,1/4], [1/5…1/8],
                            [1/9…1/16], [1/17…1/32]。塊の合計は render 時に計算する
                            (0.5833 / 0.6345 / 0.6629 / 0.6766)。

    geometric_vs_harmonic - 上段: 1/2 + 1/4 + 1/8 + … を長さ 1 の枠の中に詰める
                            (枠を越えない)。下段: 1 + 1/2 + 1/3 + … を端から並べ、
                            目盛り 1, 2, 3 を順に越えていく。「足す数がゼロに向かう」
                            だけでは和が止まるかどうか決まらない、の対照。
                            Fixed params: 上段 10 項、下段 11 項 (H_11 ≈ 3.02 > 3)。
                            部分和は render 時に計算する。

    staircase             - 1/2 + 2/4 + 3/8 + 4/16 + … = 2 の図。幅 1/2, 1/4, 1/8, …
                            で高さ 1, 2, 3, … の柱を並べ (柱の面積 = n/2^n)、横の層に
                            切り直すと層の幅は 1, 1/2, 1/4, … になり、端から並べると
                            長さ 2 に収まる。
                            Fixed params: 柱 6 本 (7 本目以降は「…」)、層 6 段。
                            合計 2 は等比級数 1 + 1/2 + 1/4 + … の和。

固定値の出どころ: 塊分けの証明は Grant 訳 (A Source Book in Medieval Science, 1974,
pp. 131–135)。階段図は『質と運動の配置について』に帰されるが部・章は未確認 (画面に書名は
出さない)。**画面に人名・年号は出さない** (帰属はナレーション側)。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 072 (ニコル・オレーム) — 数学 1 (grouping) / 数学 2 (geometric_vs_harmonic) /
数学 3 (staircase)。
"""

from manim import (
    RIGHT,
    UP,
    AnimationGroup,
    DashedLine,
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
TEXT_FADE = 0.6

# --- grouping -------------------------------------------------------------
# (行ラベルの MathTex, 項の並び)
GROUPS = [
    (r"1", [1]),
    (r"\tfrac{1}{2}", [2]),
    (r"\tfrac{1}{3}+\tfrac{1}{4}", [3, 4]),
    (r"\tfrac{1}{5}+\cdots+\tfrac{1}{8}", list(range(5, 9))),
    (r"\tfrac{1}{9}+\cdots+\tfrac{1}{16}", list(range(9, 17))),
    (r"\tfrac{1}{17}+\cdots+\tfrac{1}{32}", list(range(17, 33))),
]
ROW_Y0 = 1.55
ROW_GAP = 0.52
BAR_X0 = -2.3  # 棒の左端
HALF_LEN = 3.1  # 1/2 に相当する長さ
BAR_H = 0.3
LABEL_X = -4.3

# --- geometric_vs_harmonic -----------------------------------------------
UNIT = 3.4  # 数値 1 に相当する長さ
GX0 = -5.6
GEO_Y = 1.35
HAR_Y = -0.85
GEO_TERMS = 10
HAR_TERMS = 11

# --- staircase ------------------------------------------------------------
COLS = 6
W_UNIT = 3.2  # 幅 1 に相当する長さ
H_UNIT = 0.34  # 高さ 1 に相当する長さ
ST_X0 = -6.6
ST_Y0 = -1.55
ROW_X0 = -2.6
ROW_Y = -1.55
LAYER_COLORS = [ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK, ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK]


def _group_sums():
    return [sum(1.0 / n for n in terms) for _, terms in GROUPS]


def _partial_sums(terms):
    out, s = [], 0.0
    for t in terms:
        s += t
        out.append(s)
    return out


LINT_FACTUAL_CLAIMS = {
    "grouping": {"people": [], "years": []},
    "geometric_vs_harmonic": {"people": [], "years": []},
    "staircase": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "grouping": ["棒", "破線", "塊"],
    "geometric_vs_harmonic": ["枠", "目盛り", "棒"],
    "staircase": ["柱", "階段", "層", "長方形"],
}


class HarmonicSeriesOresme(Scene):
    """調和級数の塊分け / 等比との対照 / 階段図 の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "grouping")
        self._duration = float(params.get("duration", 35))
        if mode == "geometric_vs_harmonic":
            self.build_contrast()
        elif mode == "staircase":
            self.build_staircase()
        else:
            self.build_grouping()

    # ------------------------------------------------------------------
    def _title(self, main, sub):
        t = Text(main, font=FONT, font_size=34, color=ACCENT_GOLD).move_to(UP * TITLE_Y)
        s = Text(sub, font=FONT, font_size=22, color=TEXT_DIM).move_to(UP * SUB_Y)
        self.play(FadeIn(t), FadeIn(s), run_time=1.0)

    def _show(self, texts, run_time, shape_anims=()):
        """テキストは短く入れて保持し、長い run_time は図形側だけに使う (規約「罠 2」)。"""
        t = min(TEXT_FADE, run_time)
        if shape_anims:
            self.play(
                AnimationGroup(*shape_anims, *[FadeIn(x, run_time=t) for x in texts], lag_ratio=0.0)
            )
        else:
            self.play(*[FadeIn(x) for x in texts], run_time=t)
            if run_time - t > 0.02:
                self.wait(run_time - t)

    @staticmethod
    def _bar_segments(terms, x0, y, scale, color, h=BAR_H):
        """項ごとの幅 (値 × scale) を横に並べた長方形の列。"""
        segs = VGroup()
        x = x0
        for n in terms:
            w = scale / n
            r = Rectangle(
                width=w,
                height=h,
                color=BG_COLOR,
                fill_color=color,
                fill_opacity=0.9,
                stroke_width=1.0 if w > 0.05 else 0,
            ).move_to([x + w / 2, y, 0])
            segs.add(r)
            x += w
        return segs, x

    # ------------------------------------------------------------------
    def build_grouping(self):
        d = self._duration
        self._title(
            "2 分の 1 より大きい塊が、無限にある", "足す数はゼロに向かう。それでも和は無限になる"
        )
        scale = 2 * HALF_LEN  # 値 1 の長さ
        sums = _group_sums()

        half_x = BAR_X0 + HALF_LEN
        guide = DashedLine(
            [half_x, ROW_Y0 + 0.3, 0],
            [half_x, ROW_Y0 - ROW_GAP * (len(GROUPS) - 1) - 0.3, 0],
            color=TEXT_DIM,
            stroke_width=2,
            dash_length=0.12,
        )
        guide_label = MathTex(r"\tfrac{1}{2}", font_size=30, color=TEXT_DIM).next_to(
            guide, UP, buff=0.08
        )

        rows = []
        colors = [TEXT_WHITE, TEXT_WHITE, ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK, ACCENT_GOLD]
        for i, ((tex, terms), s) in enumerate(zip(GROUPS, sums, strict=True)):
            y = ROW_Y0 - ROW_GAP * i
            label = MathTex(tex, font_size=30, color=TEXT_WHITE).move_to([LABEL_X, y, 0])
            label.align_to([LABEL_X + 1.6, 0, 0], RIGHT)
            segs, x_end = self._bar_segments(terms, BAR_X0, y, scale, colors[i])
            if i == 0:
                val = Text("= 1", font=FONT, font_size=22, color=TEXT_DIM)
            elif i == 1:
                val = Text("= 2 分の 1", font=FONT, font_size=22, color=TEXT_DIM)
            else:
                val = Text(f"{s:.3f} > 2 分の 1", font=FONT, font_size=22, color=colors[i])
            val.next_to(segs, RIGHT, buff=0.18)
            rows.append((label, segs, val))

        # 破線 (x≈0.4、下端 y≈-1.35) と結論の式 (y=-1.8) を避けて右に置く
        more = Text("…  塊は無限に続く", font=FONT, font_size=24, color=ACCENT_PINK).move_to(
            [3.0, -1.4, 0]
        )
        # 結論の式 (y=-1.85、右寄せ。行ラベル列 x≈-5 とは離れている)
        concl = MathTex(
            r"1+\tfrac{1}{2}+\tfrac{1}{3}+\tfrac{1}{4}+\cdots \;>\; 1+\tfrac{1}{2}+\tfrac{1}{2}+\tfrac{1}{2}+\cdots \;=\; \infty",
            font_size=30,
            color=ACCENT_GOLD,
        ).move_to([0.2, -1.8, 0])

        weights = [0.6] + [0.7, 0.7, 1.0, 1.1, 1.1, 1.1] + [0.8, 1.2]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([guide_label], rt[0], shape_anims=[FadeIn(guide, run_time=rt[0])])
        for i, (label, segs, val) in enumerate(rows):
            r = rt[1 + i]
            t1 = min(TEXT_FADE, r * 0.3)
            t2 = max(0.3, r * 0.45)
            self.play(FadeIn(label), run_time=t1)
            self.play(FadeIn(segs, lag_ratio=0.15), run_time=t2)
            self._show([val], max(0.3, r - t1 - t2))  # 行の残り時間を使い切る
        self._show([more], rt[-2])
        self._show([concl], rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_contrast(self):
        d = self._duration
        self._title(
            "足す数がゼロに向かうだけでは、決まらない",
            "半分ずつ足せば 1 を越えない。逆数を足せば、どんな線も越える",
        )
        geo_terms = [1.0 / 2**k for k in range(1, GEO_TERMS + 1)]
        har_terms = [1.0 / n for n in range(1, HAR_TERMS + 1)]
        geo_ps = _partial_sums(geo_terms)
        har_ps = _partial_sums(har_terms)

        # 上段: 長さ 1 の枠
        frame = Rectangle(
            width=UNIT, height=BAR_H + 0.16, color=ACCENT_CYAN, stroke_width=2.5
        ).move_to([GX0 + UNIT / 2, GEO_Y, 0])
        geo_label = MathTex(
            r"\tfrac{1}{2}+\tfrac{1}{4}+\tfrac{1}{8}+\tfrac{1}{16}+\cdots",
            font_size=32,
            color=TEXT_WHITE,
        ).move_to([1.0, GEO_Y + 0.55, 0])
        one_tick = Text("1", font=FONT, font_size=22, color=ACCENT_CYAN).next_to(
            frame, RIGHT, buff=0.12
        )
        geo_segs = VGroup()
        x = GX0
        for t in geo_terms:
            w = t * UNIT
            geo_segs.add(
                Rectangle(
                    width=w,
                    height=BAR_H,
                    color=BG_COLOR,
                    fill_color=ACCENT_CYAN,
                    fill_opacity=0.9,
                    stroke_width=1.0 if w > 0.04 else 0,
                ).move_to([x + w / 2, GEO_Y, 0])
            )
            x += w
        geo_val = Text("1 を越えない", font=FONT, font_size=24, color=ACCENT_CYAN).move_to(
            [1.0, GEO_Y - 0.5, 0]
        )

        # 下段: 目盛り 1, 2, 3
        ticks = VGroup()
        for v in (1, 2, 3):
            tx = GX0 + v * UNIT
            ticks.add(
                Line([tx, HAR_Y - 0.45, 0], [tx, HAR_Y + 0.45, 0], color=EDGE_COLOR, stroke_width=2)
            )
            ticks.add(
                Text(str(v), font=FONT, font_size=22, color=TEXT_DIM).move_to([tx, HAR_Y + 0.62, 0])
            )
        # 級数の式は棒の左下に置く (目盛りラベルは棒の上)
        har_label = MathTex(
            r"1+\tfrac{1}{2}+\tfrac{1}{3}+\tfrac{1}{4}+\cdots", font_size=32, color=TEXT_WHITE
        ).move_to([-3.0, HAR_Y - 0.65, 0])
        har_segs = VGroup()
        x = GX0
        hcolors = [ACCENT_GOLD, ACCENT_PINK]
        for i, t in enumerate(har_terms):
            w = t * UNIT
            har_segs.add(
                Rectangle(
                    width=w,
                    height=BAR_H,
                    color=BG_COLOR,
                    fill_color=hcolors[i % 2],
                    fill_opacity=0.9,
                    stroke_width=1.0,
                ).move_to([x + w / 2, HAR_Y, 0])
            )
            x += w
        har_val = Text("どの目盛りも越える", font=FONT, font_size=24, color=ACCENT_GOLD).move_to(
            [-3.0, HAR_Y - 1.0, 0]
        )
        # 下段の途中経過 (目盛りを越えた瞬間に出す)
        cross_notes = []
        for v, ny in ((2, -1.5), (3, -1.85)):  # 二つの注記が横に重ならないよう段違いに
            k = next(i for i, s in enumerate(har_ps) if s > v)
            cross_notes.append(
                (
                    k,
                    Text(
                        f"{k + 1} 項で {v} を越える", font=FONT, font_size=20, color=TEXT_DIM
                    ).move_to([GX0 + v * UNIT, ny, 0]),
                )
            )
        both = Text(
            "足す数は、どちらも限りなくゼロに近づく", font=FONT, font_size=24, color=TEXT_WHITE
        ).move_to([0, 0.25, 0])
        assert geo_ps[-1] < 1.0 and har_ps[-1] > 3.0

        weights = [0.7, 1.4, 0.6, 0.7, 0.7, 2.0, 0.7, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([geo_label, one_tick], rt[0], shape_anims=[FadeIn(frame, run_time=rt[0])])
        self.play(FadeIn(geo_segs, lag_ratio=0.3), run_time=rt[1])
        self._show([geo_val], rt[2])
        self._show([both], rt[3])
        self._show([har_label], rt[4], shape_anims=[FadeIn(ticks, run_time=rt[4])])
        # 下段は項を一つずつ (目盛りを越えたところで注記)
        note_t = 0.4
        per = max(0.12, (rt[5] - note_t * len(cross_notes)) / len(har_segs))
        for i, seg in enumerate(har_segs):
            self.play(FadeIn(seg), run_time=per)
            for k, note in cross_notes:
                if k == i:
                    self.play(FadeIn(note), run_time=note_t)
        self._show([har_val], rt[6])
        self.wait(rt[7])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_staircase(self):
        d = self._duration
        self._title("無限に足しても、2 に収まる", "柱を横の層に切り直すと、層の幅は 1, 1/2, 1/4, …")
        formula = MathTex(
            r"\tfrac{1}{2}+\tfrac{2}{4}+\tfrac{3}{8}+\tfrac{4}{16}+\tfrac{5}{32}+\cdots \;=\; 2",
            font_size=36,
            color=TEXT_WHITE,
        ).move_to([0, 1.75, 0])

        # 柱: 幅 1/2^n, 高さ n (n=1..COLS)。cells[layer][col]
        cells = [[None] * COLS for _ in range(COLS)]
        x = ST_X0
        cols = VGroup()
        ghost = VGroup()  # 柱の輪郭。層を運び出したあとも元の形が残る
        for c in range(COLS):
            w = W_UNIT / 2 ** (c + 1)
            col = VGroup()
            ghost.add(
                Rectangle(
                    width=w,
                    height=H_UNIT * (c + 1),
                    color=TEXT_DIM,
                    stroke_width=1.5,
                    fill_opacity=0,
                ).move_to([x + w / 2, ST_Y0 + H_UNIT * (c + 1) / 2, 0])
            )
            for layer in range(c + 1):
                r = Rectangle(
                    width=w,
                    height=H_UNIT,
                    color=BG_COLOR,
                    fill_color=LAYER_COLORS[layer],
                    fill_opacity=0.9,
                    stroke_width=1.0 if w > 0.05 else 0,
                ).move_to([x + w / 2, ST_Y0 + H_UNIT * (layer + 0.5), 0])
                cells[layer][c] = r
                col.add(r)
            cols.add(col)
            x += w
        col_labels = VGroup()
        for c in range(3):
            w = W_UNIT / 2 ** (c + 1)
            cx = ST_X0 + W_UNIT * (1 - 1 / 2**c) + w / 2
            col_labels.add(
                MathTex(
                    rf"\tfrac{{{c + 1}}}{{{2 ** (c + 1)}}}", font_size=26, color=TEXT_DIM
                ).move_to([cx, ST_Y0 - 0.32, 0])
            )
        dots = Text("…", font=FONT, font_size=26, color=TEXT_DIM).move_to(
            [ST_X0 + W_UNIT + 0.25, ST_Y0 + 0.4, 0]
        )
        left_cap = Text("柱の面積を足す", font=FONT, font_size=22, color=TEXT_DIM).move_to(
            [ST_X0 + W_UNIT / 2, ST_Y0 + H_UNIT * COLS + 0.35, 0]
        )

        # 層 → 横一列に並べ直したときの目標位置
        layers = [VGroup(*[cells[k][c] for c in range(k, COLS)]) for k in range(COLS)]
        targets = []
        rx = ROW_X0
        for k in range(COLS):
            w = W_UNIT / 2**k
            targets.append([rx + w / 2, ROW_Y + H_UNIT / 2, 0])
            rx += w
        row_frame = Rectangle(
            width=2 * W_UNIT, height=H_UNIT + 0.12, color=TEXT_WHITE, stroke_width=2
        ).move_to([ROW_X0 + W_UNIT, ROW_Y + H_UNIT / 2, 0])
        row_labels = VGroup()
        for k, tex in enumerate([r"1", r"\tfrac{1}{2}", r"\tfrac{1}{4}"]):
            w = W_UNIT / 2**k
            row_labels.add(
                MathTex(tex, font_size=26, color=LAYER_COLORS[k]).move_to(
                    [targets[k][0], ROW_Y - 0.32, 0]
                )
            )
        two = Text("= 2", font=FONT, font_size=30, color=ACCENT_GOLD).next_to(
            row_frame, RIGHT, buff=0.2
        )
        right_cap = Text("層の幅を足す", font=FONT, font_size=22, color=TEXT_DIM).move_to(
            [ROW_X0 + W_UNIT, ROW_Y + H_UNIT + 0.45, 0]
        )
        geo = MathTex(
            r"1+\tfrac{1}{2}+\tfrac{1}{4}+\tfrac{1}{8}+\cdots \;=\; 2",
            font_size=32,
            color=ACCENT_GOLD,
        ).move_to([ROW_X0 + W_UNIT, ROW_Y + H_UNIT + 1.05, 0])

        weights = [0.8, 1.6, 0.6, 0.6, 2.2, 0.6, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([formula], rt[0])
        cap_t = 0.5
        per = max(0.15, (rt[1] - cap_t) / COLS)
        self.play(FadeIn(left_cap), run_time=cap_t)
        for col, g in zip(cols, ghost, strict=True):
            self.play(FadeIn(col), FadeIn(g), run_time=per)
        self._show([col_labels, dots], rt[2])
        # 層ごとに強調 (色は既に層ごと)。右側の枠を出す
        self._show([right_cap], rt[3], shape_anims=[FadeIn(row_frame, run_time=rt[3])])
        lab_t = 0.3
        per = max(0.5, rt[4] / COLS)
        for k in range(COLS):
            extra = lab_t if k < 3 else 0.0
            self.play(layers[k].animate.move_to(targets[k]), run_time=max(0.2, per - extra))
            if k < 3:
                self.play(FadeIn(row_labels[k]), run_time=lab_t)
        self._show([two], rt[5])
        self._show([geo], rt[6])
        # 柱 6 本 + 層 6 段で play が 20 回を超える。ループ内で per を分割した run_time は
        # pace() の切り下げを通らないので、余韻から 0.5 秒引いて尺を閉じる
        self.wait(CODA - 0.5)


SCENES = {
    "grouping": HarmonicSeriesOresme,
    "geometric_vs_harmonic": HarmonicSeriesOresme,
    "staircase": HarmonicSeriesOresme,
}
