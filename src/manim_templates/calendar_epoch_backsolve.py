"""
calendar_epoch_backsolve.py - 三つの周期の余りから、暦元を逆算する for 数学史記

中国の暦を作るとは、いくつかの周期が同時に振り出しに戻った過去の一点 (暦元) を
決めることだった。観測して分かるのは「今、それぞれの周期のどこにいるか」= 余りだけ
で、そこから何十万年もさかのぼって暦元を求める。『数書九章』天時類の「治暦演紀」が
これにあたり、大衍の術が本当に必要とされた場面である。

Modes:
    three_cycles - 三本の周期の帯を並べ、右端の「今」に立って、それぞれの周期が
                   最後に振り出しへ戻ってから何日たっているか (余り) を読む。
                   周期の帯は左から右へ流れ続けるので全編に動きがある。

    backsolve    - 「今」から時間を戻していき、三つの余りが同時に零になる点で止める。
                   そこが暦元。戻した量が積年にあたる。

**画面に出す周期の数値は実際の暦定数ではない。** 冬至の間隔も朔望月も整数日では
なく、本物の上元積年は何十万年という桁になる。ここでは仕組みだけを見せるために
小さな数を選んだ。画面にもそう書く。

Fixed params: 周期 5・8・12 (このうち 8 と 12 は公約数 4 を持つ ── 暦の周期どうしが
互いに素とは限らないことが、秦九韶が一般の場合を扱った理由である)、今の余り 3・3・11、
三つが同時に零になるのは 120 を法として 83 手前。いずれも全探索で一意であることを
確認済み (lcm(5,8,12) = 120、83 % 5 = 3、83 % 8 = 3、83 % 12 = 11)。

固定値の出どころ: 本ファイルの定数から Python の全探索で検算した。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 070 (秦九韶) — 数学 B (上元積年 = 余りから始まりを逆算する)。
"""

from manim import (
    DecimalNumber,
    FadeIn,
    Line,
    Rectangle,
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

# 説明用の周期 (実際の暦定数ではない)
PERIODS = [5, 8, 12]
CYCLE_NAMES = ["冬至の周期", "朔の周期", "干支の周期"]
EPOCH_AGO = 83  # 「今」から戻る量。83 % 5 = 3, % 8 = 3, % 12 = 11

X_LEFT = -3.6
X_RIGHT = 5.4
SPAN = 30.0  # 帯に見えている日数


def _xof(v):
    """0..SPAN の値を画面の x 座標に写す。"""
    return X_LEFT + (X_RIGHT - X_LEFT) * (v / SPAN)


LINT_FACTUAL_CLAIMS = {
    "three_cycles": {"people": [], "years": []},
    "backsolve": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "three_cycles": ["帯", "目盛り", "余り", "縦線", "周期"],
    "backsolve": ["帯", "目盛り", "余り", "縦線", "数値"],
}


class CalendarEpochBacksolve(Scene):
    """三つの周期の余りを読む / 余りから暦元へ遡る の 2 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "three_cycles")
        self._duration = float(params.get("duration", 25))

        if mode == "backsolve":
            self.build_backsolve()
        else:
            self.build_three_cycles()

    # ------------------------------------------------------------------
    # 共通: 三本の帯を組み立てる
    # ------------------------------------------------------------------
    def _build_bands(self, tracker):
        """周期の帯・目盛り・余りの表示を作る。

        tracker は「今が何日目か」を持つ。帯の目盛りは tracker に応じて
        左右に流れるので、scene 全編に動きが残る。
        """
        colors = [ACCENT_CYAN, ACCENT_GOLD, ACCENT_PINK]
        ys = [1.85, 0.75, -0.35]
        bands = VGroup()
        marks = VGroup()
        readouts = VGroup()

        for p, name, y, col in zip(PERIODS, CYCLE_NAMES, ys, colors, strict=True):
            box = Rectangle(
                width=X_RIGHT - X_LEFT,
                height=0.5,
                stroke_color=EDGE_COLOR,
                stroke_width=2.0,
                fill_opacity=0.0,
            ).move_to([(X_LEFT + X_RIGHT) / 2, y, 0])
            lab = Text(f"{name} ({p})", font=FONT, font_size=20, color=col)
            lab.move_to([X_LEFT - 1.55, y, 0])
            bands.add(VGroup(box, lab))

            # 周期の切れ目 (振り出しに戻る点)。now に合わせて流れる。
            def make_marks(pp=p, yy=y, cc=col):
                now = tracker.get_value()
                g = VGroup()
                k = 0
                while True:
                    # now から左へ、周期 pp ごとの切れ目を置く
                    v = SPAN - (now % pp) - k * pp
                    if v < 0:
                        break
                    x = _xof(v)
                    g.add(Line([x, yy - 0.25, 0], [x, yy + 0.25, 0], color=cc, stroke_width=4.0))
                    k += 1
                return g

            marks.add(always_redraw(make_marks))

            num = DecimalNumber(0, num_decimal_places=0, font_size=30, color=col)
            num.move_to([X_RIGHT + 0.55, y, 0])

            def upd(mo, pp=p):
                mo.set_value(int(tracker.get_value()) % pp)

            num.add_updater(upd)
            readouts.add(num)

        return bands, marks, readouts

    # ------------------------------------------------------------------
    # mode: three_cycles
    # ------------------------------------------------------------------
    def build_three_cycles(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 5.0, 1.0], intro=0.6, coda=CODA)

        title = Text(
            "三つの周期は、それぞれ別の位置にいる", font=FONT, font_size=28, color=TEXT_WHITE
        ).move_to([0, 3.05, 0])
        note = Text(
            "周期の数は仕組みを見るための例です", font=FONT, font_size=19, color=TEXT_DIM
        ).move_to([0, 2.6, 0])
        self.play(FadeIn(title), run_time=0.6)

        tracker = ValueTracker(0.0)
        bands, marks, readouts = self._build_bands(tracker)
        self.play(FadeIn(VGroup(bands, note)), run_time=rt[0])

        now_line = Line(
            [_xof(SPAN), -0.85, 0], [_xof(SPAN), 2.35, 0], color=TEXT_WHITE, stroke_width=3.0
        )
        now_lab = Text("今", font=FONT, font_size=24, color=TEXT_WHITE).move_to(
            [_xof(SPAN), -1.2, 0]
        )
        cap = Text(
            "最後に振り出しへ戻ってからの日数 = 余り", font=FONT, font_size=22, color=TEXT_DIM
        )
        cap.move_to([0, -1.85, 0])
        self.add(*marks, *readouts, now_line, now_lab)

        # 時間を進めて帯を流す。余りが刻々と変わることを見せる。
        self.play(tracker.animate.set_value(float(EPOCH_AGO)), run_time=rt[1])
        self.play(FadeIn(cap), run_time=rt[2])
        self.wait(CODA)

    # ------------------------------------------------------------------
    # mode: backsolve
    # ------------------------------------------------------------------
    def build_backsolve(self):
        CODA = 3.0
        rt = pace(self._duration, [1.0, 5.5, 1.0], intro=0.6, coda=CODA)

        title = Text(
            "三つの余りが同時に零になる点まで戻る", font=FONT, font_size=28, color=TEXT_WHITE
        ).move_to([0, 3.05, 0])
        note = Text(
            "周期の数は仕組みを見るための例です", font=FONT, font_size=19, color=TEXT_DIM
        ).move_to([0, 2.6, 0])
        self.play(FadeIn(title), run_time=0.6)

        tracker = ValueTracker(float(EPOCH_AGO))
        bands, marks, readouts = self._build_bands(tracker)
        self.play(FadeIn(VGroup(bands, note)), run_time=rt[0])

        now_line = Line(
            [_xof(SPAN), -0.85, 0], [_xof(SPAN), 2.35, 0], color=TEXT_WHITE, stroke_width=3.0
        )
        back = DecimalNumber(0, num_decimal_places=0, font_size=30, color=TEXT_WHITE)
        back_lab = Text("戻った量", font=FONT, font_size=22, color=TEXT_DIM).move_to(
            [-1.4, -1.25, 0]
        )

        def upd_back(mo):
            mo.set_value(EPOCH_AGO - int(tracker.get_value()))
            mo.move_to([0.45, -1.25, 0])

        back.add_updater(upd_back)
        self.add(*marks, *readouts, now_line, back, back_lab)

        # 時間を戻す。三つの余りが同時に零になったところで止まる。
        self.play(tracker.animate.set_value(0.0), run_time=rt[1])

        concl = Text(
            "ここが暦元 ── 余りだけを手がかりに遡って見つける",
            font=FONT,
            font_size=26,
            color=ACCENT_GOLD,
        ).move_to([0, -1.85, 0])
        self.play(FadeIn(concl), run_time=rt[2])
        self.wait(CODA)


SCENES = {
    "three_cycles": CalendarEpochBacksolve,
    "backsolve": CalendarEpochBacksolve,
}
