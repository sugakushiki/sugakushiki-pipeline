"""
intuitionism_proof.py - 「証明は点を見つけない」: 排中律・弱い反例・不動点の応用 for 数学史記

ブラウワーの不動点定理の証明は「動かない点が無いと仮定して矛盾を出す」だけで、点の位置を
与えない。彼はここに使われる排中律 (A か、A でないか) を、無限を扱うときには使えないと
言い、証明とは頭の中で実際に組み立てることだと言った (直観主義)。
**画面に人名は出さない** (帰属はナレーション側)。年号は pi_digits の「1997」だけ。

Modes:
    excluded_middle  - 証明の流れ図。「動かない点は無い」と仮定 → 縁に潰す写像が作れる →
                       縁に潰すことはできない → 矛盾 → だから「動かない点はある」。
                       右に排中律 (A か、A でないか) と、有限なら一つずつ調べられる /
                       無限なら「無い」の否定は点を見せない、の対比。最後に「では、
                       どこに?」と空欄の x = ? を残す。
                       Fixed params: 箱 5 段。数値なし。

    pi_digits        - 円周率の小数が帯になって流れる (render 時に decimal で 240 桁を計算、
                       Machin の公式。帯は途中の桁が流れるので先頭に『π = 3.』は付けない)。問い「0 1 2 3 4 5 6 7 8 9 は、どこかに並ぶか」。
                       当時は「ある」も「ない」も言えない (空欄)。その後 1997 年、小数点
                       以下 17,387,594,880 桁目から始まる位置で見つかった、と示す。
                       「分かった時点で、命題は値を持つ」。
                       Fixed params: 帯は 240 桁、位置 17,387,594,880 (金田・高橋 1997)。

    nash_equilibrium - 二人ゲームの混合戦略 (p, q) の正方形 [0,1]^2 と、均衡を不動点に持つ
                       連続写像 T (Nash 1951 の写像)。格子点が T の行き先へ滑り、動かない
                       一点 = 均衡が光る。「必ずある」とは言えるが、どこかは写像を見ても
                       分からない、を disk と同じ絵で見せる。
                       Fixed params: 利得 A1 = [[2,-1],[-1,1]] のゼロ和ゲーム。均衡
                       (p*, q*) = (2/5, 2/5) は render 時に無差別条件から解き、T(p*) = p*
                       を assert する。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。末尾 FadeOut なし。

Used by: Episode 073 (L. E. J. ブラウワー) — 数学 6 (excluded_middle) / 数学 7 (pi_digits) /
数学 8 (nash_equilibrium)。
"""

from decimal import Decimal, getcontext

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    AnimationGroup,
    Arrow,
    Dot,
    FadeIn,
    Indicate,
    MathTex,
    Rectangle,
    RoundedRectangle,
    Scene,
    SurroundingRectangle,
    Text,
    ValueTracker,
    VGroup,
    linear,
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

# --- pi_digits ------------------------------------------------------------
PI_DIGITS = 180
PI_POSITION = 17_387_594_880  # 小数点以下の桁位置 (金田・高橋 1997 の発表文)
TAPE_Y = 0.9
TAPE_CHARS = 38  # 帯に見える桁数 (右端 x ≈ 6.6 で画面内)

# --- nash_equilibrium -----------------------------------------------------
A1 = np.array([[2.0, -1.0], [-1.0, 1.0]])  # 行プレイヤーの利得。列プレイヤーは -A1
NSQ = 3.4
NSQ_C = np.array([-2.4, 0.15, 0.0])
NGRID = 7


# ---------------------------------------------------------------------------
# 純粋な計算
# ---------------------------------------------------------------------------
def _pi_string(ndigits):
    """Machin の公式で円周率を ndigits 桁 (小数点以下) 計算し、"3.1415..." を返す。"""
    getcontext().prec = ndigits + 20

    def arctan_inv(n):
        x = Decimal(1) / n
        x2 = x * x
        term = x
        total = Decimal(0)
        k = 0
        while True:
            t = term / (2 * k + 1)
            if abs(t) < Decimal(10) ** (-(ndigits + 10)):
                break
            total += t if k % 2 == 0 else -t
            term *= x2
            k += 1
        return total

    pi = 16 * arctan_inv(5) - 4 * arctan_inv(239)
    s = str(pi)
    assert s.startswith("3.14159265358979")
    return s[: ndigits + 2]


def _nash_map(s):
    """Nash (1951) の連続写像 T。s = (p, q)。不動点 = 均衡。"""
    p, q = float(s[0]), float(s[1])
    x = np.array([p, 1 - p])
    y = np.array([q, 1 - q])
    u1 = float(x @ A1 @ y)
    u2 = float(x @ (-A1) @ y)
    c1 = np.maximum(0.0, A1 @ y - u1)  # 行プレイヤーの純戦略ごとの改善
    c2 = np.maximum(0.0, (-A1).T @ x - u2)
    x2 = (x + c1) / (1 + c1.sum())
    y2 = (y + c2) / (1 + c2.sum())
    return np.array([x2[0], y2[0], 0.0])


def _nash_equilibrium():
    """2x2 ゼロ和ゲームの完全混合均衡を無差別条件から解く。"""
    a = A1
    # 列プレイヤーを無差別にする p: 列 1 と列 2 の行プレイヤー利得が等しい
    p = (a[1, 1] - a[1, 0]) / (a[0, 0] - a[0, 1] - a[1, 0] + a[1, 1])
    # 行プレイヤーを無差別にする q
    q = (a[1, 1] - a[0, 1]) / (a[0, 0] - a[0, 1] - a[1, 0] + a[1, 1])
    s = np.array([p, q, 0.0])
    assert 0 < p < 1 and 0 < q < 1
    assert np.linalg.norm(_nash_map(s) - s) < 1e-12, "equilibrium is not a fixed point of T"
    return s


LINT_FACTUAL_CLAIMS = {
    "excluded_middle": {"people": [], "years": []},
    "pi_digits": {"people": [], "years": ["1997"]},
    "nash_equilibrium": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "excluded_middle": ["矢印", "箱", "流れ図"],
    "pi_digits": ["円周率", "小数", "帯", "桁"],
    "nash_equilibrium": ["正方形", "点", "格子", "矢印"],
}


class IntuitionismProof(Scene):
    """excluded_middle / pi_digits / nash_equilibrium の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "excluded_middle")
        self._duration = float(params.get("duration", 35))
        builders = {
            "excluded_middle": self.build_excluded_middle,
            "pi_digits": self.build_pi_digits,
            "nash_equilibrium": self.build_nash,
        }
        if mode not in builders:
            raise ValueError(
                f"intuitionism_proof: unknown mode {mode!r} (valid: {sorted(builders)})"
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
        """FadeIn → Indicate を別々の play に。"""
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.6, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    @staticmethod
    def _box(s, color, width=5.6, font_size=23, fill="#22223a"):
        t = Text(s, font=FONT, font_size=font_size, color=color)
        r = RoundedRectangle(
            corner_radius=0.12,
            width=width,
            height=0.5,
            color=color,
            stroke_width=2,
            fill_color=fill,
            fill_opacity=1.0,
        )
        return VGroup(r, t)

    # ------------------------------------------------------------------
    def build_excluded_middle(self):
        d = self._duration
        self._title(
            "証明は、点を見つけていない", "『無い』を否定しただけで、『ある』点は一つも見せていない"
        )
        x_flow = -3.4
        ys = [1.8, 1.05, 0.3, -0.45, -1.2]
        labels = [
            ("動かない点は無い、と仮定する", TEXT_WHITE),
            ("すると、円板を縁に潰す写像が作れる", TEXT_WHITE),
            ("円板を縁に潰すことは、できない", TEXT_WHITE),
            ("矛盾", ACCENT_PINK),
            ("だから、動かない点はある", ACCENT_GOLD),
        ]
        boxes = [
            self._box(s, c).move_to([x_flow, y, 0]) for (s, c), y in zip(labels, ys, strict=True)
        ]
        arrows = [
            Arrow(
                boxes[i].get_bottom(),
                boxes[i + 1].get_top(),
                buff=0.04,
                color=EDGE_COLOR,
                stroke_width=3,
            )
            for i in range(4)
        ]
        where = Text("では、その点はどこに?", font=FONT, font_size=26, color=ACCENT_GOLD).move_to(
            [x_flow, -1.88, 0]
        )

        # 右: 排中律
        rx = 3.4
        lem = MathTex(r"A \;\lor\; \lnot A", font_size=40, color=ACCENT_CYAN).move_to([rx, 1.75, 0])
        lem_t = Text(
            "A か、A でないか ── 排中律", font=FONT, font_size=24, color=ACCENT_CYAN
        ).move_to([rx, 1.2, 0])
        fin = Text(
            "有限個なら、一つずつ調べれば決まる", font=FONT, font_size=22, color=TEXT_WHITE
        ).move_to([rx, 0.35, 0])
        fin_dots = VGroup(
            *[Dot([rx - 1.2 + 0.4 * i, -0.15, 0], radius=0.07, color=TEXT_DIM) for i in range(7)]
        )
        inf = Text(
            "無限個なら、『無い』の否定は", font=FONT, font_size=22, color=TEXT_WHITE
        ).move_to([rx, -0.8, 0])
        inf2 = Text("点を一つも見せていない", font=FONT, font_size=22, color=ACCENT_PINK).move_to(
            [rx, -1.2, 0]
        )
        blank = MathTex(r"x = \;?", font_size=40, color=ACCENT_GOLD).move_to([rx, -1.85, 0])

        weights = [0.8, 0.8, 0.8, 0.6, 0.9, 0.7, 0.6, 0.8, 0.8, 0.9, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        for i in range(3):
            anims = [FadeIn(boxes[i], run_time=min(0.6, rt[i]))]
            if i > 0:
                anims.append(FadeIn(arrows[i - 1], run_time=min(0.6, rt[i])))
            self.play(AnimationGroup(*anims, lag_ratio=0.0))
            if rt[i] - 0.6 > 0.02:
                self.wait(rt[i] - 0.6)
        self.play(FadeIn(arrows[2]), run_time=0.3)
        self._pulse(boxes[3], max(0.5, rt[3] - 0.3), ACCENT_PINK)
        self.play(FadeIn(arrows[3]), run_time=0.3)
        self._pulse(boxes[4], max(0.5, rt[4] - 0.3), ACCENT_GOLD)
        self._show([lem, lem_t], rt[5])
        self._show([fin], rt[6], shape_anims=[FadeIn(fin_dots, lag_ratio=0.2, run_time=rt[6])])
        self._show([inf], rt[7])
        self._show([inf2], rt[8])
        self._show([where], rt[9])
        self._pulse(blank, rt[10], ACCENT_GOLD)
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_pi_digits(self):
        d = self._duration
        self._title(
            "『ある』とも『ない』とも、言えなかった", "円周率の小数に、0 1 2 3 4 5 6 7 8 9 は並ぶか"
        )
        pi_s = _pi_string(PI_DIGITS)
        digits = pi_s[2:]  # 小数点以下
        # 帯: 固定幅のフォントに近い表示にするため、1 桁ずつ Text を並べる
        cell = 0.31
        tape = VGroup()
        for i, ch in enumerate(digits):
            tape.add(Text(ch, font=FONT, font_size=30, color=TEXT_WHITE).move_to([i * cell, 0, 0]))
        head = Text(
            "円周率の\n小数", font=FONT, font_size=20, color=ACCENT_CYAN, line_spacing=0.8
        ).move_to([-6.2, TAPE_Y, 0])
        window_x0 = -5.2
        tape.move_to([window_x0 + tape.get_width() / 2, TAPE_Y, 0])
        tape.align_to([window_x0, 0, 0], LEFT)
        # 見える窓 (左右をマスクする代わりに、窓の外の桁は透明にする updater)
        win_left, win_right = window_x0, window_x0 + TAPE_CHARS * cell
        frame = Rectangle(
            width=win_right - win_left, height=0.7, color=EDGE_COLOR, stroke_width=1.5
        ).move_to([(win_left + win_right) / 2, TAPE_Y, 0])

        shift = ValueTracker(0.0)
        base_left = window_x0

        def slide(m):
            m.align_to([base_left - shift.get_value(), 0, 0], LEFT)
            for t in m:
                x = t.get_center()[0]
                t.set_opacity(1.0 if win_left <= x <= win_right else 0.0)

        slide(tape)
        tape.add_updater(slide)

        q = Text("この並びは、どこかに現れるか", font=FONT, font_size=26, color=TEXT_WHITE).move_to(
            [0, -0.1, 0]
        )
        target = Text("0 1 2 3 4 5 6 7 8 9", font=FONT, font_size=34, color=ACCENT_GOLD).move_to(
            [0, 0.45, 0]
        )
        # 「ある」「ない」の空欄
        yes = self._box("ある", TEXT_DIM, width=2.2)
        no = self._box("ない", TEXT_DIM, width=2.2)
        yes.move_to([-1.6, -0.85, 0])
        no.move_to([1.6, -0.85, 0])
        neither = Text(
            "当時は、どちらとも言えなかった", font=FONT, font_size=24, color=ACCENT_PINK
        ).move_to([0, -1.5, 0])
        found = Text(
            f"1997 年、小数点以下 {PI_POSITION:,} 桁目から始まる位置に見つかった",
            font=FONT,
            font_size=23,
            color=ACCENT_GOLD,
        ).move_to([0, -1.5, 0])
        yes_on = self._box("ある", ACCENT_GOLD, width=2.2).move_to([-1.6, -0.85, 0])
        verdict = Text(
            "分かった時点で、命題は値を持つ", font=FONT, font_size=24, color=TEXT_WHITE
        ).move_to([0, -1.9, 0])

        weights = [0.6, 1.6, 0.7, 0.8, 0.7, 0.9, 1.2, 0.9, 0.9]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show([head], rt[0], shape_anims=[FadeIn(frame, run_time=rt[0])])
        self.add(tape)
        total_scroll = (len(digits) - TAPE_CHARS - 2) * cell
        # 帯は本編の残り全部で流し続ける (末尾静止を作らない)
        scroll_time = sum(rt[1:])
        self.play(
            AnimationGroup(
                shift.animate(run_time=scroll_time, rate_func=linear).set_value(total_scroll),
                _seq(
                    [
                        (rt[1], [target]),
                        (rt[2], [q]),
                        (rt[3], [yes, no]),
                        (rt[4], [neither]),
                        (rt[5], []),
                        (rt[6], [found]),
                        (rt[7], [yes_on]),
                        (rt[8], [verdict]),
                    ],
                    swap_out={found: neither},
                ),
                lag_ratio=0.0,
            )
        )
        tape.remove_updater(slide)
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_nash(self):
        d = self._duration
        self._title("『必ずある』── どこにあるかは、言わない", "戦略の正方形を、正方形の中へ写す")
        lo = NSQ_C - NSQ / 2
        box = Rectangle(width=NSQ, height=NSQ, color=EDGE_COLOR, stroke_width=2).move_to(NSQ_C)

        def to_screen(s):
            return np.array([lo[0] + s[0] * NSQ, lo[1] + s[1] * NSQ, 0.0])

        p_lab = MathTex(r"p", font_size=30, color=TEXT_DIM).next_to(
            to_screen([1, 0]), DOWN + RIGHT, buff=0.1
        )
        q_lab = MathTex(r"q", font_size=30, color=TEXT_DIM).next_to(
            to_screen([0, 1]), UP + LEFT, buff=0.1
        )
        zero = MathTex(r"0", font_size=24, color=TEXT_DIM).next_to(
            to_screen([0, 0]), DOWN + LEFT, buff=0.1
        )
        one_p = MathTex(r"1", font_size=24, color=TEXT_DIM).next_to(
            to_screen([1, 0]), DOWN, buff=0.12
        )
        one_q = MathTex(r"1", font_size=24, color=TEXT_DIM).next_to(
            to_screen([0, 1]), LEFT, buff=0.12
        )
        pts = [
            np.array([i / NGRID, j / NGRID, 0.0])
            for i in range(NGRID + 1)
            for j in range(NGRID + 1)
        ]
        dots = VGroup(*[Dot(to_screen(s), radius=0.05, color=ACCENT_CYAN) for s in pts])
        # 行き先が辺の上 (p=0 や 1) に来ると点の半径ぶん枠の外に見えるので、表示だけ僅かに内側へ寄せる
        targets = [to_screen(np.clip(_nash_map(s), 0.015, 0.985)) for s in pts]
        arrows = VGroup()
        for s, t in zip(pts, targets, strict=True):
            a = to_screen(s)
            i, j = int(round(s[0] * NGRID)), int(round(s[1] * NGRID))
            if np.linalg.norm(t - a) > 0.12 and i % 2 == 0 and j % 2 == 0:
                arrows.add(
                    Arrow(
                        a,
                        t,
                        buff=0.03,
                        color=TEXT_DIM,
                        stroke_width=2,
                        tip_length=0.16,
                        max_stroke_width_to_length_ratio=10,
                    )
                )
        eq = _nash_equilibrium()
        eq_dot = Dot(to_screen(eq), radius=0.1, color=ACCENT_GOLD)
        eq_ring = SurroundingRectangle(eq_dot, color=ACCENT_GOLD, buff=0.12, corner_radius=0.1)
        eq_lab = Text("均衡", font=FONT, font_size=24, color=ACCENT_GOLD).next_to(
            eq_ring, UP + RIGHT, buff=0.06
        )

        notes = [
            Text("p = 一人目が手 A を選ぶ確率", font=FONT, font_size=22, color=TEXT_WHITE).move_to(
                [3.7, 1.7, 0]
            ),
            Text("q = 二人目が手 A を選ぶ確率", font=FONT, font_size=22, color=TEXT_WHITE).move_to(
                [3.7, 1.25, 0]
            ),
            Text(
                "『いまより得な手へ少し寄せる』写像 T", font=FONT, font_size=22, color=ACCENT_CYAN
            ).move_to([3.7, 0.55, 0]),
            Text(
                "連続で、正方形を正方形の中へ写す", font=FONT, font_size=22, color=TEXT_WHITE
            ).move_to([3.7, 0.1, 0]),
            Text(
                "だから、動かない点が必ずある", font=FONT, font_size=24, color=ACCENT_GOLD
            ).move_to([3.7, -0.6, 0]),
            Text(
                "動かない点 = 誰も手を変えたくない = 均衡",
                font=FONT,
                font_size=22,
                color=ACCENT_GOLD,
            ).move_to([3.7, -1.05, 0]),
            Text(
                "『ある』と言うだけで、どこかは言わない", font=FONT, font_size=24, color=ACCENT_PINK
            ).move_to([3.7, -1.75, 0]),
        ]
        notes[5].scale(0.92)

        weights = [0.7, 0.7, 0.7, 0.8, 0.7, 2.2, 0.9, 0.8, 0.9]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self._show(
            [p_lab, q_lab, zero, one_p, one_q], rt[0], shape_anims=[FadeIn(box, run_time=rt[0])]
        )
        self._show(
            [notes[0], notes[1]], rt[1], shape_anims=[FadeIn(dots, lag_ratio=0.02, run_time=rt[1])]
        )
        self._show([notes[2]], rt[2], shape_anims=[FadeIn(arrows, run_time=rt[2])])
        self._show([notes[3]], rt[3])
        self.wait(rt[4])
        move = AnimationGroup(
            *[dot.animate.move_to(t) for dot, t in zip(dots, targets, strict=True)],
            lag_ratio=0.0,
            run_time=rt[5],
        )
        self.play(
            AnimationGroup(move, arrows.animate(run_time=0.8).set_opacity(0.0), lag_ratio=0.0)
        )
        self.remove(arrows)
        self._pulse(eq_dot, rt[6], ACCENT_GOLD, extras=(eq_ring, eq_lab))
        self._show([notes[4], notes[5]], rt[7])
        self._show([notes[6]], rt[8])
        self.wait(CODA)


def _seq(steps, swap_out=None):
    """(run_time, [texts]) の列を、一本の逐次アニメにする (帯のスクロールと並走させる)。

    各ステップは「テキストを TEXT_FADE で入れて残りを待つ」。swap_out={new: old} なら
    new を入れる直前に old を消す。
    """
    from manim import FadeOut, Succession, Wait

    swap_out = swap_out or {}
    anims = []
    for run_time, texts in steps:
        t = min(TEXT_FADE, run_time)
        outs = [FadeOut(swap_out[x], run_time=0.3) for x in texts if x in swap_out]
        if outs:
            anims.append(AnimationGroup(*outs, lag_ratio=0.0))
        if texts:
            anims.append(AnimationGroup(*[FadeIn(x) for x in texts], lag_ratio=0.0, run_time=t))
            rest = run_time - t - (0.3 if outs else 0.0)
        else:
            rest = run_time
        if rest > 0.02:
            anims.append(Wait(rest))
    return Succession(*anims, lag_ratio=1.0)


SCENES = {
    "excluded_middle": IntuitionismProof,
    "pi_digits": IntuitionismProof,
    "nash_equilibrium": IntuitionismProof,
}
