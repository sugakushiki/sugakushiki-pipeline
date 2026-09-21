"""
remainder_reconstruction.py - 余りから元の数を復元する for 数学史記

割った余りだけが分かっているとき、元の数を言い当てられるか。『孫子算経』下巻の
「物不知数」は、三で割ると二余り、五で割ると三余り、七で割ると二余る数を問う。
答えは二十三。ただしそこに書かれているのは三と五と七に対する個別の手引きで、
割る数が変わったときにどうするかは書かれていない。

秦九韶が『数書九章』(1247) の大衍類で書き下したのは、割る数がどんな組であっても
回る一般の手順である。しかも**割る数どうしが互いに素でない場合まで**含む。

Modes:
    sunzi       - 三本の数直線 (目盛りの間隔が 3 / 5 / 7) の上を走査線が右へ進み、
                  各行の「最後の目盛りから今の位置まで」が余りとして伸び縮みする。
                  三つの余りが同時に 2 / 3 / 2 になる位置が答え。
                  Fixed params: 法 3・5・7、余り 2・3・2、答え 23
                  (1 から 105 までの範囲で解はこの一つだけであることを確認済み)。

    dayan_table - 同じ問題を秦九韶の用語で解き直した表。列が三つの定母、行が
                  余り・衍数・奇数・乗率・用数・余り×用数。
                  Fixed params: 衍母 105、衍数 35・21・15、奇数 2・1・1、
                  乗率 2・1・1、用数 70・21・15、積の和 233、233 - 105 - 105 = 23。
                  **表の数値はレンダ時に法と余りから計算する** (書き写した数を
                  並べない)。乗率は「掛けて一余る数」で、この例では 2・1・1 と
                  小さいので求一の手続きは一目で済む ── 手続きが要るのは法が
                  大きいときである。

    non_coprime - 割る数どうしに公約数があると手順が回らないこと、そして公約数を
                  片方に寄せて互いに素な組 (定母) を作れば回ることを見せる。
                  Fixed params: 元数 5・8・12 (8 と 12 が 4 を共有する) →
                  定母 5・8・3。積 5×8×3 = 120 で、これは 5・8・12 の最小公倍数に等しい。
                  **この三つの数は仕組みを見るために選んだ例であって『数書九章』の
                  問題の数値ではない。** 画面にもそう書く。

固定値の出どころ: すべて本ファイル内の計算 (Python の modular inverse と全探索) で
事前に検算した。sunzi の答えは 1..105 の全探索で一意、dayan_table の 233 % 105 = 23、
non_coprime の 5×8×3 = 120 = lcm(5,8,12) を確認している。

**注意して書くこと**: 「秦九韶が中国剰余定理を発見した」ではない。『孫子算経』に
原型があり、秦九韶の独自性は互いに素でない場合まで解いたこと。画面に人名・年号は
出さない (帰属の主張はナレーション側で正確に行う)。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 070 (秦九韶) — 数学 A (物不知数 / 大衍総数術 / 非互素の一般化)。
"""

from manim import (
    LEFT,
    UP,
    DecimalNumber,
    FadeIn,
    Line,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
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

# --- 問題の定義 (孫子算経 下巻「物不知数」) -------------------------------
MODS = [3, 5, 7]
REMS = [2, 3, 2]

# --- 非互素の例 (説明のために選んだ数。原典の数値ではない) ----------------
RAW_MODS = [5, 8, 12]
FIXED_MODS = [5, 8, 3]

# 走査線が見る範囲
N_MAX = 26
X_LEFT = -4.2
X_RIGHT = 5.5


def _dayan_rows(mods, rems):
    """法と余りから、衍母・衍数・奇数・乗率・用数・積を計算して返す。

    書き写した数を並べるのではなく、ここで作った数だけを画面に出す。
    """
    total = 1
    for m in mods:
        total *= m
    rows = []
    for m, r in zip(mods, rems, strict=True):
        yan = total // m  # 衍数
        odd = yan % m  # 奇数
        mul = pow(odd, -1, m)  # 乗率 (掛けて一余る数)
        use = yan * mul  # 用数
        rows.append({"mod": m, "rem": r, "yan": yan, "odd": odd, "mul": mul, "use": use})
    return total, rows


def _xof(v):
    """0..N_MAX の値を画面の x 座標に写す。"""
    return X_LEFT + (X_RIGHT - X_LEFT) * (v / N_MAX)


LINT_FACTUAL_CLAIMS = {
    "sunzi": {"people": [], "years": []},
    "dayan_table": {"people": [], "years": []},
    "non_coprime": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "sunzi": ["数直線", "目盛り", "余り", "走査線", "縦線"],
    "dayan_table": ["表", "行", "列", "数値"],
    "non_coprime": ["箱", "数値", "矢印"],
}


class RemainderReconstruction(Scene):
    """物不知数・大衍の表・非互素の縮約の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "sunzi")
        self._duration = float(params.get("duration", 25))

        if mode == "dayan_table":
            self.build_dayan_table()
        elif mode == "non_coprime":
            self.build_non_coprime()
        else:
            self.build_sunzi()

    # ------------------------------------------------------------------
    # mode: sunzi  — 走査線が右へ進み、三つの余りが同時に揃う点を探す
    # ------------------------------------------------------------------
    def build_sunzi(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 6.0, 0.9], intro=0.6, coda=CODA)

        title = Text(
            "三で割ると二、五で割ると三、七で割ると二",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        ).move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.6)

        tracker = ValueTracker(0.0)
        colors = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK]
        ys = [1.95, 0.85, -0.25]

        rows = VGroup()
        segs = VGroup()
        readouts = VGroup()

        for m, r, y, col in zip(MODS, REMS, ys, colors, strict=True):
            base = Line([X_LEFT, y, 0], [X_RIGHT, y, 0], color=EDGE_COLOR, stroke_width=2.0)
            ticks = VGroup()
            k = 0
            while k * m <= N_MAX:
                x = _xof(k * m)
                ticks.add(
                    Line([x, y - 0.16, 0], [x, y + 0.16, 0], color=EDGE_COLOR, stroke_width=2.0)
                )
                k += 1
            # 探しているものを左に書いておく (これが無いと何を見ればよいか分からない)
            lab = Text(f"{m} で割ると {r}", font=FONT, font_size=21, color=col)
            lab.next_to(base, LEFT, buff=0.16).shift(UP * 0.02)
            rows.add(VGroup(base, ticks, lab))

            # 「最後の目盛りから今の位置まで」= 余り。updater で伸び縮みさせる。
            def make_seg(mm=m, yy=y, cc=col):
                n = tracker.get_value()
                start = (int(n) // mm) * mm
                x0 = _xof(start)
                x1 = _xof(max(n, start + 1e-3))
                return Line([x0, yy, 0], [x1, yy, 0], color=cc, stroke_width=9.0)

            segs.add(always_redraw(make_seg))

            # 今の余りを右端に出す。目標と一致したら白から金へ変える
            # (三つ同時に金になる位置が答え)。
            num = DecimalNumber(0, num_decimal_places=0, font_size=32, color=TEXT_DIM)
            num.move_to([X_RIGHT + 0.5, y, 0])

            def upd(mo, mm=m, rr=r):
                cur = int(tracker.get_value()) % mm
                mo.set_value(cur)
                mo.set_color(ACCENT_GOLD if cur == rr else TEXT_DIM)

            num.add_updater(upd)
            readouts.add(num)

        self.play(FadeIn(rows), run_time=rt[0])

        scan = always_redraw(
            lambda: Line(
                [_xof(tracker.get_value()), -0.75, 0],
                [_xof(tracker.get_value()), 2.35, 0],
                color=TEXT_DIM,
                stroke_width=2.5,
            )
        )
        counter = DecimalNumber(0, num_decimal_places=0, font_size=34, color=TEXT_WHITE)

        def upd_counter(mo):
            mo.set_value(int(tracker.get_value()))
            mo.move_to([_xof(tracker.get_value()), -1.15, 0])

        counter.add_updater(upd_counter)
        # always_redraw / updater を持つものは FadeIn せずに置く
        # (毎フレーム作り直されるので不透明度のアニメが効かない)
        self.add(*segs, *readouts, scan, counter)

        # 走査線を 23 まで進める。ここが scene の大部分を占める。
        self.play(tracker.animate.set_value(23.0), run_time=rt[1])

        found = Text(
            "三つの余りが同時に揃う ── 二十三",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        ).move_to([0, -1.85, 0])
        self.play(FadeIn(found), run_time=rt[2])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: dayan_table  — 同じ問題を秦九韶の用語で解き直す
    # ------------------------------------------------------------------
    def build_dayan_table(self):
        CODA = 3.0
        # play は head 1 回 + 行 6 回 + 結論 2 回 = 9 回。重みも 9 個そろえる
        # (少ないと予算外の play が出て mp4 が指定尺を超え、末尾が切り落とされる)
        rt = pace(
            self._duration,
            [0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.1],
            intro=0.6,
            coda=CODA,
        )

        total, rows = _dayan_rows(MODS, REMS)

        title = Text("同じ問いを、一般の手順で解く", font=FONT, font_size=28, color=TEXT_WHITE)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.6)

        labels = ["定母", "余り", "衍数", "奇数", "乗率", "用数"]
        keys = ["mod", "rem", "yan", "odd", "mul", "use"]
        ys = [2.35, 1.78, 1.21, 0.64, 0.07, -0.50]
        xs = [-0.8, 1.1, 3.0]

        head = VGroup()
        for lab, y in zip(labels, ys, strict=True):
            head.add(Text(lab, font=FONT, font_size=24, color=TEXT_DIM).move_to([-3.1, y, 0]))
        self.play(FadeIn(head), run_time=rt[0])

        # 行ごとに出す (段階リビールで全編に動きを残す)
        for i, (key, y) in enumerate(zip(keys, ys, strict=True)):
            cells = VGroup()
            for x, row in zip(xs, rows, strict=True):
                col = ACCENT_GOLD if key in ("mul", "use") else TEXT_WHITE
                cells.add(
                    Text(str(row[key]), font=FONT, font_size=26, color=col).move_to([x, y, 0])
                )
            self.play(FadeIn(cells), run_time=rt[1 + i])

        prod_sum = sum(r["rem"] * r["use"] for r in rows)
        line1 = Text(
            "余りに用数を掛けて足すと " + str(prod_sum),
            font=FONT,
            font_size=26,
            color=ACCENT_CYAN,
        ).move_to([0, -1.20, 0])
        line2 = Text(
            f"衍母 {total} を引けるだけ引いて {prod_sum % total}",
            font=FONT,
            font_size=28,
            color=ACCENT_PINK,
        ).move_to([0, -1.85, 0])
        self.play(FadeIn(line1), run_time=rt[7])
        self.play(FadeIn(line2), run_time=rt[8])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: non_coprime  — 公約数を片方に寄せて互いに素にする
    # ------------------------------------------------------------------
    def build_non_coprime(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 1.0, 1.0, 1.0, 1.1], intro=0.6, coda=CODA)

        title = Text(
            "割る数どうしに公約数があるとき", font=FONT, font_size=28, color=TEXT_WHITE
        ).move_to([0, 3.05, 0])
        note = Text(
            "仕組みを見るために選んだ数です", font=FONT, font_size=20, color=TEXT_DIM
        ).move_to([0, 2.55, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(note), run_time=rt[0])

        xs = [-3.4, 0.0, 3.4]
        raw = VGroup()
        for x, m in zip(xs, RAW_MODS, strict=True):
            raw.add(Text(str(m), font=FONT, font_size=52, color=TEXT_WHITE).move_to([x, 1.55, 0]))
        cap_raw = Text("元数", font=FONT, font_size=22, color=TEXT_DIM).move_to([-5.4, 1.55, 0])
        self.play(FadeIn(VGroup(raw, cap_raw)), run_time=rt[1])

        # 8 と 12 は 4 を共有している
        share = Text(
            "八と十二は四を共に持つ ── このままでは回らない",
            font=FONT,
            font_size=24,
            color=ACCENT_PINK,
        ).move_to([0, 0.75, 0])
        self.play(FadeIn(share), run_time=rt[2])

        arrows = VGroup()
        for x in xs:
            arrows.add(
                Line([x, 0.25, 0], [x, -0.35, 0], color=EDGE_COLOR, stroke_width=3.0).add_tip(
                    tip_length=0.16
                )
            )
        fixed = VGroup()
        for x, m, raw_m in zip(xs, FIXED_MODS, RAW_MODS, strict=True):
            col = ACCENT_GOLD if m != raw_m else TEXT_WHITE
            fixed.add(Text(str(m), font=FONT, font_size=52, color=col).move_to([x, -0.95, 0]))
        cap_fix = Text("定母", font=FONT, font_size=22, color=TEXT_DIM).move_to([-5.4, -0.95, 0])
        self.play(FadeIn(VGroup(arrows, fixed, cap_fix)), run_time=rt[3])

        prod = 1
        for m in FIXED_MODS:
            prod *= m
        concl = Text(
            "×".join(str(m) for m in FIXED_MODS) + f" = {prod} ── 元の三つの最小公倍数に等しい",
            font=FONT,
            font_size=26,
            color=ACCENT_CYAN,
        ).move_to([0, -1.85, 0])
        self.play(FadeIn(concl), run_time=rt[4])
        self.wait(CODA)


SCENES = {
    "sunzi": RemainderReconstruction,
    "dayan_table": RemainderReconstruction,
    "non_coprime": RemainderReconstruction,
}
