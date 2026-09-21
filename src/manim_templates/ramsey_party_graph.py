"""
ramsey_party_graph.py - 六人いれば必ず起こること (R(3,3) = 6) for 数学史記

六人が集まれば、どの二人が知り合いでどの二人が初対面であっても、互いに全員が
知り合いの三人か、互いに全員が初対面の三人が必ずいる。五人では、そうはいかない。
点を人、辺を二人の関係 (赤 = 知り合い、青 = 初対面) とすれば、これは
「完全グラフの辺を二色で塗ると単色の三角形が現れるか」という問題になる。

Modes:
    k5_counterexample - 五人を五角形に置く。五角形の辺 (5 本) を赤、対角線 (星形、
                        5 本) を青に塗ると、単色の三角形が一つも無い。十個の三角形を
                        順に走査して「赤 2 本・青 1 本」か「赤 1 本・青 2 本」しか
                        出ないことを見せる。
                        Fixed params: 頂点 5、辺 10 (赤 5・青 5)、三角形 10、単色 0。
                        **三角形の色数はレンダ時に塗りから数える** (書き写さない)。

    k6_pigeonhole     - 六人を六角形に置き、一人 v から出る五本の辺を二色で塗る。
                        鳩の巣原理で三本は同じ色 (赤とする)。その三人 a, b, c の間の
                        三辺を調べ、(場合 1) 一本でも赤なら v と合わせて赤の三角形、
                        (場合 2) 三本とも青なら a, b, c が青の三角形、の両方を描く。
                        Fixed params: 頂点 6、v から赤 3 本・青 2 本、
                        a, b, c は v の隣でない三点 (図が見やすいよう交互に取る)。
                        結論 R(3,3) = 6。

    party_intro       - 導入用。六つの点 (人) が一つずつ現れて数えられ、辺がでたらめに
                        赤 (知り合い) と青 (初対面) に塗られ、同じ色の三角形が必ず一つ光る。
                        続けて五角形の反例 (単色三角形なし) を小さく見せ、「六人が境目」で
                        閉じる。Fixed params: 頂点 6 (番号 1〜6)、辺 15、二色、乱数の種は
                        固定 (どの種でも K6 には単色三角形が必ずある = 定理そのもの)。
                        **画面に出す数字は 1〜6 の番号だけ** (年号・人名なし)。

    general           - 点を 6 → 9 → 12 と増やしながら辺をでたらめに二色で塗り
                        (乱数の種は固定)、最後に「同じ色だけで結ばれた四人組」を
                        探して光らせる。定理の主張 (十分に多ければ同色の k 人組が
                        必ず現れる) と、定理が「何人から」には答えないことを画面に出す。
                        Fixed params: 頂点 6 / 9 / 12、二色、探すのは K4。
                        **K4 の探索はレンダ時に総当たりで行う** (C(12,4) = 495 組)。
                        種は 12 点の塗りに単色 K4 が存在する最小の種を探して使う。

固定値の出どころ: R(3,3) = 6 の上界 (鳩の巣) と下界 (五角形の塗り) は標準的な証明で、
本ファイル内で三角形ごとの色数を実際に数えて確認している (k5 モードのカウンタは
書き写した 0 ではなく、走査の結果として 0 になる)。

**画面に人名・年号は出さない** (帰属の主張はナレーション側で行う)。

Duration-aware: _manim_params.json の duration を読み、style.pace() で配分する。
Y 範囲: -2.0 〜 +3.3 (字幕クリアランス確保)。

Used by: Episode 071 (フランク・ラムゼー) — 数学 1〜3 (五人では足りない / 六人なら必ず /
ラムゼーの定理)。
"""

import itertools
import math
import random

from manim import (
    LEFT,
    UP,
    AnimationGroup,
    Dot,
    FadeIn,
    FadeOut,
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

# 赤 = 知り合い、青 = 初対面。ナレーションが「赤」「青」と言うので色は意味を持つ。
RED = "#ff4d4d"
BLUE = ACCENT_CYAN

# グラフの置き場 (左) と説明パネル (右)。
# 中心 y=0.2・半径 1.7 で、六角形の最上点 (y=1.9) がサブタイトル (y=2.45) に触れず、
# 最下点のラベル (中心 y≈-1.78) が字幕域 (y<-2.0) に入らない。
G_CENTER = (-2.75, 0.2)
G_RADIUS = 1.7
PANEL_X = 3.55  # 右パネルの中心 x
TITLE_Y = 2.95
SUB_Y = 2.45
CODA = 3.0
TEXT_FADE = 0.6  # テキストの FadeIn はこの秒数で入れて、残りは保持する


def _ring(n, radius=G_RADIUS, center=G_CENTER):
    """n 点を円周上に置く (0 番が真上)。"""
    cx, cy = center
    pts = []
    for i in range(n):
        ang = math.pi / 2 - 2 * math.pi * i / n
        pts.append([cx + radius * math.cos(ang), cy + radius * math.sin(ang), 0])
    return pts


def _pentagon_coloring():
    """K5: 五角形の辺を赤、対角線を青。"""
    col = {}
    for i, j in itertools.combinations(range(5), 2):
        d = (j - i) % 5
        col[(i, j)] = RED if d in (1, 4) else BLUE
    return col


def _triangle_counts(col, n):
    """各三角形の (赤の本数, 青の本数) をレンダ時に数える。"""
    out = []
    for tri in itertools.combinations(range(n), 3):
        reds = sum(1 for e in itertools.combinations(tri, 2) if col[e] == RED)
        out.append((tri, reds, 3 - reds))
    return out


def _random_coloring(n, seed):
    rng = random.Random(seed)
    return {e: (RED if rng.random() < 0.5 else BLUE) for e in itertools.combinations(range(n), 2)}


def _find_mono_clique(col, n, k):
    """同色 k 人組を総当たりで探す。無ければ None。"""
    for sub in itertools.combinations(range(n), k):
        colors = {col[e] for e in itertools.combinations(sub, 2)}
        if len(colors) == 1:
            return sub, colors.pop()
    return None


def _seed_with_mono_k4(n=12, k=4):
    """12 点の塗りに単色 K4 が存在する最小の種を返す (決定論)。"""
    for seed in range(200):
        if _find_mono_clique(_random_coloring(n, seed), n, k) is not None:
            return seed
    raise RuntimeError("no seed with a monochromatic K4 found (unexpected)")


LINT_FACTUAL_CLAIMS = {
    "k5_counterexample": {"people": [], "years": []},
    "k6_pigeonhole": {"people": [], "years": []},
    "general": {"people": [], "years": []},
    "party_intro": {"people": [], "years": []},
}

LINT_VISUAL_ELEMENTS = {
    "k5_counterexample": ["五角形", "点", "辺", "対角線", "三角形", "赤", "青"],
    "k6_pigeonhole": ["六角形", "点", "辺", "三角形", "赤", "青"],
    "general": ["点", "辺", "赤", "青", "四人組"],
    "party_intro": ["点", "辺", "赤", "青", "三角形", "五角形"],
}


class RamseyPartyGraph(Scene):
    """五人の反例 / 六人の鳩の巣 / 一般化 の 3 モード。"""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "k6_pigeonhole")
        self._duration = float(params.get("duration", 30))

        if mode == "k5_counterexample":
            self.build_k5()
        elif mode == "general":
            self.build_general()
        elif mode == "party_intro":
            self.build_party_intro()
        else:
            self.build_k6()

    # ------------------------------------------------------------------
    def _title(self, main, sub):
        t = Text(main, font=FONT, font_size=34, color=ACCENT_GOLD).move_to(UP * TITLE_Y)
        s = Text(sub, font=FONT, font_size=22, color=TEXT_DIM).move_to(UP * SUB_Y)
        self.play(FadeIn(t), FadeIn(s), run_time=1.0)
        return t, s

    def _dots(self, pts):
        g = VGroup()
        for p in pts:
            g.add(Dot(p, color=TEXT_WHITE, radius=0.09))
        return g

    def _edge(self, pts, e, color, width=4.0):
        a, b = e
        return Line(pts[a], pts[b], color=color, stroke_width=width)

    def _panel_line(self, text, y, color=TEXT_WHITE, size=26):
        return Text(text, font=FONT, font_size=size, color=color).move_to([PANEL_X, y, 0])

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
    def build_k5(self):
        d = self._duration
        pts = _ring(5)
        col = _pentagon_coloring()
        tris = _triangle_counts(col, 5)
        mono = sum(1 for _, r, b in tris if r == 3 or b == 3)

        self._title("五人では足りない", "五角形の辺を赤、対角線を青に塗る")
        dots = self._dots(pts)
        red_edges = VGroup(*[self._edge(pts, e, RED) for e, c in col.items() if c == RED])
        blue_edges = VGroup(*[self._edge(pts, e, BLUE) for e, c in col.items() if c == BLUE])

        # 右パネル
        p1 = self._panel_line("赤 = 知り合い", 1.55, RED)
        p2 = self._panel_line("青 = 初対面", 1.05, BLUE)
        counter_label = self._panel_line("同じ色だけの三角形", 0.15, TEXT_DIM, 24)
        counter = Text(f"0 / {len(tris)}", font=FONT, font_size=40, color=ACCENT_GOLD).move_to(
            [PANEL_X, -0.55, 0]
        )
        verdict = self._panel_line("五人では「必ず」とは言えない", -1.55, ACCENT_PINK, 26)

        # 重み: 点 / 赤辺 / 青辺 / 凡例 / 三角形の走査 ×10 / 結論
        weights = [0.8, 1.2, 1.2, 0.6] + [0.55] * len(tris) + [1.0]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        self.play(FadeIn(dots), run_time=rt[0])
        self._show([p1], rt[1], shape_anims=[FadeIn(red_edges, lag_ratio=0.15, run_time=rt[1])])
        self._show([p2], rt[2], shape_anims=[FadeIn(blue_edges, lag_ratio=0.15, run_time=rt[2])])
        self._show([counter_label, counter], rt[3])

        found = 0
        for idx, (tri, reds, blues) in enumerate(tris):
            hl = VGroup(
                *[self._edge(pts, e, col[e], width=11) for e in itertools.combinations(tri, 2)]
            )
            tag = Text(f"赤 {reds}・青 {blues}", font=FONT, font_size=24, color=TEXT_WHITE).move_to(
                [PANEL_X, -1.05, 0]
            )
            if reds == 3 or blues == 3:
                found += 1
            new_counter = Text(
                f"{found} / {len(tris)}", font=FONT, font_size=40, color=ACCENT_GOLD
            ).move_to(counter.get_center())
            # 1 三角形あたり step 秒をきっちり使う (fade_in + hold + fade_out = step)
            step = rt[4 + idx]
            fade_in = min(0.5, step * 0.4)
            fade_out = 0.25
            self.play(FadeIn(hl), FadeIn(tag), run_time=fade_in)
            self.wait(max(0.05, step - fade_in - fade_out))
            self.play(FadeOut(hl), FadeOut(tag), run_time=fade_out)
            self.remove(counter)
            counter = new_counter
            self.add(counter)
        assert found == mono == 0, (found, mono)

        self._show([verdict], rt[-1])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_k6(self):
        d = self._duration
        pts = _ring(6)
        v = 0
        abc = [1, 3, 5]  # v の隣でない三点 (交互) → 三角形が大きく見える
        others = [2, 4]
        self._title("六人なら必ず", "一人から出る五本の辺を、二色で塗る")

        dots = self._dots(pts)
        v_dot = Dot(pts[v], color=ACCENT_GOLD, radius=0.13)
        # ラベルは左に出す (真上だとサブタイトルの行と重なる)
        v_label = Text("v", font=FONT, font_size=24, color=ACCENT_GOLD).next_to(
            v_dot, LEFT, buff=0.15
        )
        # 背景の辺 (薄く): v の辺と abc の辺以外
        bg = VGroup()
        for e in itertools.combinations(range(6), 2):
            if v in e or set(e) <= set(abc):
                continue
            bg.add(self._edge(pts, e, EDGE_COLOR, width=2.0))
        spokes_red = VGroup(*[self._edge(pts, (v, x), RED) for x in abc])
        spokes_blue = VGroup(*[self._edge(pts, (v, x), BLUE) for x in others])
        abc_labels = VGroup(
            *[
                Text(n, font=FONT, font_size=24, color=TEXT_WHITE).move_to(
                    [
                        pts[x][0] + 0.32 * (pts[x][0] - G_CENTER[0]) / G_RADIUS,
                        pts[x][1] + 0.32 * (pts[x][1] - G_CENTER[1]) / G_RADIUS,
                        0,
                    ]
                )
                for n, x in zip(["a", "b", "c"], abc, strict=True)
            ]
        )

        p1 = self._panel_line("五本を二色で塗れば", 1.7, TEXT_WHITE, 25)
        p2 = self._panel_line("三本は同じ色 (鳩の巣)", 1.2, RED, 25)
        case1 = self._panel_line("a-b が赤なら → v と赤の三角形", 0.35, RED, 23)
        case2 = self._panel_line("三本とも青なら → a b c が青の三角形", -0.35, BLUE, 23)
        concl = self._panel_line("どちらに転んでも、同じ色の三角形", -1.15, ACCENT_GOLD, 24)
        r33 = MathTex(r"R(3,3) = 6", font_size=44, color=ACCENT_GOLD).move_to([PANEL_X, -1.75, 0])

        # 固定尺: タイトル 1.0 + 場合 1 の保持 0.3 + 消去 0.4 = 1.7 を intro に含める
        # (含めないと合計が duration を超え、末尾の R(3,3)=6 と余韻が切られる)
        weights = [0.8, 0.8, 1.0, 0.8, 1.2, 0.6, 1.2, 0.6, 1.0, 0.8]
        rt = pace(d, weights, intro=1.0 + 0.3 + 0.4, coda=CODA)
        self.play(FadeIn(dots), FadeIn(bg), run_time=rt[0])
        self._show([v_dot, v_label], rt[1])
        self.play(
            FadeIn(spokes_red, lag_ratio=0.2), FadeIn(spokes_blue, lag_ratio=0.2), run_time=rt[2]
        )
        self._show([p1, p2, abc_labels], rt[3])

        # 場合 1: a-b が赤 → v,a,b の赤三角形
        ab = self._edge(pts, (abc[0], abc[1]), RED)
        tri1 = VGroup(
            *[
                self._edge(pts, e, RED, width=11)
                for e in [(v, abc[0]), (v, abc[1]), (abc[0], abc[1])]
            ]
        )
        self._show([case1], rt[4], shape_anims=[FadeIn(ab, run_time=rt[4])])
        self.play(FadeIn(tri1), run_time=rt[5])
        self.wait(0.3)
        self.play(FadeOut(tri1), FadeOut(ab), run_time=0.4)

        # 場合 2: a-b, b-c, c-a が全部青 → a,b,c の青三角形
        abc_blue = VGroup(*[self._edge(pts, e, BLUE) for e in itertools.combinations(abc, 2)])
        tri2 = VGroup(*[self._edge(pts, e, BLUE, width=11) for e in itertools.combinations(abc, 2)])
        self._show([case2], rt[6], shape_anims=[FadeIn(abc_blue, run_time=rt[6])])
        self.play(FadeIn(tri2), run_time=rt[7])
        self._show([concl], rt[8])
        self._show([r33], rt[9])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_general(self):
        d = self._duration
        seed = _seed_with_mono_k4()
        self._title("ラムゼーの定理", "何人集めても、何色で塗っても")

        p1 = self._panel_line("十分に多く集めれば", 1.6, TEXT_WHITE, 26)
        p2 = self._panel_line("同じ色だけで結ばれた", 1.1, TEXT_WHITE, 26)
        p3 = self._panel_line("k 人組が必ず現れる", 0.6, ACCENT_GOLD, 28)
        p4 = self._panel_line("ただし「何人から」は", -0.75, TEXT_DIM, 24)
        p5 = self._panel_line("定理は教えない", -1.25, ACCENT_PINK, 28)

        sizes = [6, 9, 12]
        weights = [1.0, 1.0, 1.0, 1.0, 1.2, 0.8, 1.0]
        rt = pace(d, weights, intro=1.0, coda=CODA)

        current = None
        for i, n in enumerate(sizes):
            pts = _ring(n)
            col = _random_coloring(n, seed) if n == 12 else _random_coloring(n, seed + n)
            edges = VGroup(*[self._edge(pts, e, c, width=2.2) for e, c in col.items()])
            dots = self._dots(pts)
            g = VGroup(edges, dots)
            if current is None:
                self.play(FadeIn(g), run_time=rt[i])
            else:
                self.play(FadeOut(current), FadeIn(g), run_time=rt[i])
            current = g
            if i == 0:
                self._show([p1, p2], rt[3] * 0.5)
        self._show([p3], rt[3] * 0.5)

        # 12 点の塗りから単色 K4 を探して光らせる (レンダ時に総当たり)
        pts = _ring(12)
        col = _random_coloring(12, seed)
        found = _find_mono_clique(col, 12, 4)
        assert found is not None
        sub, color = found
        hl = VGroup(*[self._edge(pts, e, color, width=9) for e in itertools.combinations(sub, 2)])
        hl_dots = VGroup(*[Dot(pts[x], color=ACCENT_GOLD, radius=0.13) for x in sub])
        tag = Text("同じ色だけの四人組", font=FONT, font_size=24, color=color).move_to(
            [PANEL_X, 0.05, 0]
        )
        self.play(FadeIn(hl), FadeIn(hl_dots), run_time=rt[4])
        self._show([tag], rt[5])
        self._show([p4, p5], rt[6])
        self.wait(CODA)

    # ------------------------------------------------------------------
    def build_party_intro(self):
        """導入: 六人が一人ずつ現れ、関係が赤青に塗られ、同色の三角形が必ず光る。"""
        d = self._duration
        n = 6
        pts = _ring(n)
        # 種は固定。K6 の二色塗りには単色三角形が必ずあるので探索は必ず成功する
        col = _random_coloring(n, 7)
        found = _find_mono_clique(col, n, 3)
        assert found is not None
        tri, tri_color = found

        self._title("六人のパーティー", "知り合いは赤、初対面は青")
        p1 = self._panel_line("六人が集まる", 1.55, TEXT_WHITE, 26)
        p2 = self._panel_line("どの二人も、知り合いか初対面", 1.0, TEXT_DIM, 23)
        # 右パネル: 文字 3 行 (y=1.55 / 1.05 / 0.45)、その下に小さな五角形 (中心 y=-0.45、
        # 半径 0.45 → y は -0.9〜0.0)、さらに下に文字 2 行 (y=-1.2 / -1.75)。互いに重ならない。
        p3 = self._panel_line("同じ色の三角形が、必ずある", 0.45, ACCENT_GOLD, 26)
        p4 = self._panel_line("五人なら、無い配置が作れる", -1.2, TEXT_DIM, 23)
        p5 = self._panel_line("六人が境目", -1.75, ACCENT_PINK, 30)

        # 六人を一人ずつ (番号付きで数えられるように)
        dots = [Dot(p, color=TEXT_WHITE, radius=0.11) for p in pts]
        nums = []
        for i, p in enumerate(pts):
            dx = 0.3 * (p[0] - G_CENTER[0]) / G_RADIUS
            dy = 0.3 * (p[1] - G_CENTER[1]) / G_RADIUS
            nums.append(
                Text(str(i + 1), font=FONT, font_size=22, color=TEXT_DIM).move_to(
                    [p[0] + dx, p[1] + dy, 0]
                )
            )
        edges = VGroup(*[self._edge(pts, e, c, width=3.0) for e, c in col.items()])
        hl = VGroup(
            *[self._edge(pts, e, tri_color, width=11) for e in itertools.combinations(tri, 2)]
        )
        hl_dots = VGroup(*[Dot(pts[x], color=ACCENT_GOLD, radius=0.14) for x in tri])

        # 五角形の反例 (小さく、右下のパネルの下に置く)
        small_c = (3.55, -0.45)
        small_r = 0.45
        spts = _ring(5, radius=small_r, center=small_c)
        scol = _pentagon_coloring()
        small = VGroup(
            *[Line(spts[a], spts[b], color=c, stroke_width=2.5) for (a, b), c in scol.items()],
            *[Dot(p, color=TEXT_WHITE, radius=0.06) for p in spts],
        )

        weights = [0.5] * n + [1.4, 0.8, 1.2, 0.8, 1.0, 0.8]
        rt = pace(d, weights, intro=1.0, coda=CODA)
        for i in range(n):
            self.play(FadeIn(dots[i]), FadeIn(nums[i]), run_time=min(0.5, rt[i]))
            if rt[i] - 0.5 > 0.02:
                self.wait(rt[i] - 0.5)
        self._show([p1], rt[n], shape_anims=[FadeIn(edges, lag_ratio=0.08, run_time=rt[n])])
        self._show([p2], rt[n + 1])
        self._show(
            [p3],
            rt[n + 2],
            shape_anims=[FadeIn(hl, run_time=rt[n + 2]), FadeIn(hl_dots, run_time=rt[n + 2])],
        )
        self._show([p4], rt[n + 3])
        self._show([], rt[n + 4], shape_anims=[FadeIn(small, run_time=rt[n + 4])])
        self._show([p5], rt[n + 5])
        self.wait(CODA)


SCENES = {
    "k5_counterexample": RamseyPartyGraph,
    "k6_pigeonhole": RamseyPartyGraph,
    "general": RamseyPartyGraph,
    "party_intro": RamseyPartyGraph,
}
