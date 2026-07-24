"""
game_of_life.py - ライフゲーム: 四つの規則から生まれる複雑さと計算 (数学史記)

ジョン・ホートン・コンウェイ回 の数学的主軸。たった四つの局所規則
(B3/S23) から、動く生き物 (グライダー)、無限成長 (グライダー銃)、予測不能な
振る舞い (メトセラ) が生まれる。<最も単純な規則の奥に最も深い構造がある> と
いう軸を、実際のライフゲームのシミュレーションで可視化する。

numpy で本物のライフゲーム (ムーア近傍) を各世代シミュレートし、生きたマスを
塗った正方形として、世代ごとにコマ送り (discrete step) で描く。世代数は尺に
合わせて決め、末尾の長い静止 (anti-pattern) を避ける。glider は有界グリッドで
数マス歩いてループ (トーラス境界の分裂を回避)、gun/rpentomino は有界宇宙。

Modes:
    rules       - 四つの規則を、中央マスと周囲8マスの生きた数え方で図示する
                  静止図解: 生存 (仲間2-3), 死 (過疎<2 / 過密>3), 誕生 (ちょうど3)。
                  Fixed: B3/S23, Moore neighborhood (8 neighbors), 2 states.
    glider      - 5マスのグライダーが4世代で斜めに1マス進む。有界グリッドで数マス
                  歩いてループ (トーラス境界での分裂を避け常に一貫した形) (grid 16x16).
                  Fixed: glider = (0,1),(1,2),(2,0),(2,1),(2,2); period 4, drift (1,1).
    gun         - ゴスパーのグライダー銃 (36セル) が周期30で無限にグライダーを
                  打ち出す = 有限の種からの無限成長 (grid 52x38, bounded).
                  Fixed: Gosper glider gun (36 live cells), period 30.
    rpentomino  - たった5マスのRペントミノが長く暴れ続けるメトセラ。「1103世代
                  続く」と注記 (grid 44x40, bounded).
                  Fixed: R-pentomino = (0,1),(0,2),(1,0),(1,1),(2,1); 1103 gens, 116 cells.

画面に人名・年号は出さない (narration が担う)。数字 (3, 8, 30, 1103 等) は
数学的な値であり年号ではない。
Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 050 (John Horton Conway), math pillar (Game of Life / computation).
"""

import numpy as np
from manim import (
    RIGHT,
    FadeIn,
    Rectangle,
    Scene,
    Square,
    Text,
    VGroup,
    config,
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
)

config.background_color = BG_COLOR


# ---------------------------------------------------------------------------
# Life engine
# ---------------------------------------------------------------------------
def _life_step(grid: np.ndarray, toroidal: bool = False) -> np.ndarray:
    """One generation of Conway's Life (B3/S23)."""
    if toroidal:
        n = np.zeros(grid.shape, dtype=np.int16)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                n += np.roll(np.roll(grid, dr, axis=0), dc, axis=1)
    else:
        n = np.zeros(grid.shape, dtype=np.int16)
        n[1:, :] += grid[:-1, :]
        n[:-1, :] += grid[1:, :]
        n[:, 1:] += grid[:, :-1]
        n[:, :-1] += grid[:, 1:]
        n[1:, 1:] += grid[:-1, :-1]
        n[1:, :-1] += grid[:-1, 1:]
        n[:-1, 1:] += grid[1:, :-1]
        n[:-1, :-1] += grid[1:, 1:]
    born = (grid == 0) & (n == 3)
    survive = (grid == 1) & ((n == 2) | (n == 3))
    return (born | survive).astype(np.int8)


def _simulate(grid: np.ndarray, generations: int, toroidal: bool = False):
    """Return list of grids [gen0, gen1, ..., gen_generations]."""
    frames = [grid.copy()]
    g = grid
    for _ in range(generations):
        g = _life_step(g, toroidal=toroidal)
        frames.append(g.copy())
    return frames


# Standard patterns (row, col), row increases downward
_GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
_R_PENTOMINO = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
# Canonical Gosper glider gun (36 cells), spans cols 0..35, rows 0..8
_GOSPER_GUN = [
    (0, 24),
    (1, 22), (1, 24),
    (2, 12), (2, 13), (2, 20), (2, 21), (2, 34), (2, 35),
    (3, 11), (3, 15), (3, 20), (3, 21), (3, 34), (3, 35),
    (4, 0), (4, 1), (4, 10), (4, 16), (4, 20), (4, 21),
    (5, 0), (5, 1), (5, 10), (5, 14), (5, 16), (5, 17), (5, 22), (5, 24),
    (6, 10), (6, 16), (6, 24),
    (7, 11), (7, 15),
    (8, 12), (8, 13),
]  # fmt: skip


def _place(cells, H, W, offset=(0, 0)):
    """Build a HxW int8 grid with given (row,col) cells placed at offset."""
    grid = np.zeros((H, W), dtype=np.int8)
    dr, dc = offset
    for r, c in cells:
        rr, cc = r + dr, c + dc
        if 0 <= rr < H and 0 <= cc < W:
            grid[rr, cc] = 1
    return grid


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration (static modes)."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class GameOfLife(Scene):
    """ライフゲーム ── multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "glider")
        self._duration = params.get("duration", 26)

        if mode == "rules":
            self._build_rules()
        elif mode == "gun":
            self._build_gun()
        elif mode == "rpentomino":
            self._build_rpentomino()
        else:
            self._build_glider()

    # ------------------------------------------------------------------
    # Shared: render a life grid frame (only live cells drawn) as VGroup
    # ------------------------------------------------------------------
    @staticmethod
    def _cell_size(H, W, box_w, box_h):
        return min(box_w / W, box_h / H)

    def _frame_group(self, grid, cell, top_left, color):
        """VGroup of small squares for live cells in `grid`."""
        squares = []
        rows, cols = np.nonzero(grid)
        side = cell * 0.9
        x0, y0 = top_left
        for r, c in zip(rows, cols, strict=True):
            sq = Square(side_length=side, stroke_width=0, fill_opacity=1.0, color=color)
            sq.move_to([x0 + c * cell + cell / 2, y0 - r * cell - cell / 2, 0])
            squares.append(sq)
        return VGroup(*squares)

    def _play_life(
        self,
        init_grid,
        toroidal,
        cell,
        top_left,
        board,
        title,
        subtitle,
        note,
        color,
        loop_gens=None,
    ):
        """Step through generations as discrete frames, sized to fill duration.

        The number of generations is chosen so the stepping animation itself
        fills (duration - intro - coda); the tail is a fixed short coda, so
        there is no long static tail.

        loop_gens: if set, simulate only that many coherent generations and tile
        them to fill the scene (a clean walk that restarts). Used by glider so it
        never fragments at a torus boundary -- it stays a single coherent shape.
        """
        duration = self._duration
        dt_target = 0.14
        coda = 1.5
        min_frames, max_frames = 24, 240

        self.play(FadeIn(title), run_time=0.7)
        intro = 0.7
        if subtitle is not None:
            self.play(FadeIn(subtitle), run_time=0.5)
            intro += 0.5
        self.play(FadeIn(board), run_time=0.5)
        intro += 0.5

        span = max(2.0, duration - intro - coda)
        nframes = int(round(span / dt_target))
        nframes = max(min_frames, min(nframes, max_frames))
        dt = span / nframes

        if loop_gens:
            base = _simulate(init_grid, loop_gens, toroidal=toroidal)
            frames = [base[i % len(base)] for i in range(nframes + 1)]
        else:
            frames = _simulate(init_grid, nframes, toroidal=toroidal)

        cur = VGroup()
        self.add(cur)
        note_shown = False
        for i, grid in enumerate(frames):
            newgrp = self._frame_group(grid, cell, top_left, color)
            self.remove(cur)
            self.add(newgrp)
            cur = newgrp
            if note is not None and not note_shown and i >= len(frames) // 3:
                self.add(note)
                note_shown = True
            self.wait(dt)
        if note is not None and not note_shown:
            self.add(note)
        self.wait(coda)

    # ------------------------------------------------------------------
    # Mode: rules  ── 四つの規則 (静止図解)
    # ------------------------------------------------------------------
    def _mini_grid(self, live, cell=0.34, center_gold=False):
        """3x3 neighborhood; `live` = set of (r,c) live cells. Center is (1,1)."""
        group = VGroup()
        for r in range(3):
            for c in range(3):
                if (r, c) in live:
                    col = ACCENT_GOLD if (center_gold and (r, c) == (1, 1)) else ACCENT_CYAN
                    sq = Square(
                        side_length=cell * 0.92, stroke_width=1.0, fill_opacity=1.0, color=col
                    )
                else:
                    sq = Square(
                        side_length=cell * 0.92,
                        stroke_width=1.2,
                        fill_opacity=0.0,
                        color=EDGE_COLOR,
                    )
                sq.move_to([(c - 1) * cell, (1 - r) * cell, 0])
                group.add(sq)
        return group

    def _result_cell(self, alive):
        if alive:
            return Square(
                side_length=0.34 * 0.92, stroke_width=1.0, fill_opacity=1.0, color=ACCENT_GOLD
            )
        return Square(side_length=0.34 * 0.92, stroke_width=1.4, fill_opacity=0.0, color=EDGE_COLOR)

    def _rule_row(self, live, result_alive, caption, y):
        before = self._mini_grid(live, center_gold=True)
        arrow = Text("→", font=FONT, font_size=34, color=TEXT_DIM)
        after = self._result_cell(result_alive)
        cap = Text(caption, font=FONT, font_size=23, color=TEXT_WHITE)
        left = VGroup(before, arrow, after).arrange(RIGHT, buff=0.35)
        row = VGroup(left, cap).arrange(RIGHT, buff=0.5)
        row.move_to([0, y, 0])
        return row

    def _build_rules(self):
        duration = self._duration

        title = Text("ライフゲーム ── 四つの規則", font=FONT, font_size=34, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        subtitle = Text(
            "生きたマスは、まわりの8マスの仲間を数える", font=FONT, font_size=24, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.35, 0])

        # center live (gold), 2 live neighbors -> survives
        row1 = self._rule_row(
            {(1, 1), (0, 0), (2, 2)}, True, "生存：仲間が2か3なら生き延びる", 1.35
        )
        # center live, 1 neighbor -> dies (underpopulation)
        row2 = self._rule_row(
            {(1, 1), (2, 2)}, False, "死：0か1（過疎）、4以上（過密）で死ぬ", 0.15
        )
        # center dead, exactly 3 neighbors -> born
        row3 = self._rule_row(
            {(0, 0), (0, 2), (2, 1)}, True, "誕生：まわりにちょうど3で新しく生まれる", -1.05
        )

        # Legend: gold = the focus cell being judged (and its result),
        # cyan = the live neighbours being counted.
        def _leg_item(col, label):
            sq = Square(side_length=0.26, stroke_width=0, fill_opacity=1.0, color=col)
            txt = Text(label, font=FONT, font_size=21, color=TEXT_DIM)
            return VGroup(sq, txt).arrange(RIGHT, buff=0.16)

        legend = VGroup(
            _leg_item(ACCENT_GOLD, "注目のマス・結果"),
            _leg_item(ACCENT_CYAN, "まわりの仲間"),
        ).arrange(RIGHT, buff=0.7)
        legend.move_to([0, -1.7, 0])

        anim_time = 0.7 + 0.5 + 0.7 + 0.7 + 0.7 + 0.6
        ws = _calc_wait_scale(duration, anim_time, 4.5)

        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(subtitle), run_time=0.5)
        self.play(FadeIn(row1), run_time=0.7)
        self.wait(0.9 * ws)
        self.play(FadeIn(row2), run_time=0.7)
        self.wait(0.9 * ws)
        self.play(FadeIn(row3), run_time=0.7)
        self.wait(0.9 * ws)
        self.play(FadeIn(legend), run_time=0.6)
        self.wait(max(1.0, duration - anim_time - 2.7 * ws - 0.6))

    # ------------------------------------------------------------------
    # Mode: glider  ── 動く生き物 (トーラスで歩き続ける)
    # ------------------------------------------------------------------
    def _build_glider(self):
        H = W = 16
        grid = _place(_GLIDER, H, W, offset=(1, 1))

        box_w, box_h = 4.4, 3.8
        cell = self._cell_size(H, W, box_w, box_h)
        gw, gh = W * cell, H * cell
        top_left = (-gw / 2, gh / 2 + 0.2)

        board = Rectangle(
            width=gw + 0.1,
            height=gh + 0.1,
            stroke_width=1.5,
            stroke_color=EDGE_COLOR,
            fill_opacity=0.0,
        )
        board.move_to([0, top_left[1] - gh / 2, 0])

        title = Text("動く生き物 ── グライダー", font=FONT, font_size=32, color=ACCENT_GOLD)
        title.move_to([0, 3.1, 0])
        subtitle = Text(
            "5つのマスが、4世代ごとに斜めへ1マス進む", font=FONT, font_size=24, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.5, 0])
        note = Text("規則だけで、図形が「歩く」", font=FONT, font_size=26, color=ACCENT_PINK)
        note.move_to([0, -1.85, 0])

        # Bounded grid + short coherent loop: the glider walks diagonally a few
        # cells and restarts, so it never fragments at a torus wrap.
        self._play_life(
            grid, False, cell, top_left, board, title, subtitle, note, ACCENT_CYAN, loop_gens=40
        )

    # ------------------------------------------------------------------
    # Mode: gun  ── 無限成長
    # ------------------------------------------------------------------
    def _build_gun(self):
        H, W = 38, 52
        grid = _place(_GOSPER_GUN, H, W, offset=(3, 2))

        box_w, box_h = 8.6, 3.8
        cell = self._cell_size(H, W, box_w, box_h)
        gw, gh = W * cell, H * cell
        top_left = (-gw / 2, gh / 2 + 0.2)

        board = Rectangle(
            width=gw + 0.1,
            height=gh + 0.1,
            stroke_width=1.2,
            stroke_color=EDGE_COLOR,
            fill_opacity=0.0,
        )
        board.move_to([0, top_left[1] - gh / 2, 0])

        title = Text("無限に生み出す ── グライダー銃", font=FONT, font_size=32, color=ACCENT_GOLD)
        title.move_to([0, 3.15, 0])
        subtitle = None
        note = Text(
            "有限の種から、生き物が無限に増え続ける", font=FONT, font_size=25, color=ACCENT_PINK
        )
        note.move_to([0, -1.85, 0])

        self._play_life(grid, False, cell, top_left, board, title, subtitle, note, ACCENT_CYAN)

    # ------------------------------------------------------------------
    # Mode: rpentomino  ── メトセラ (予測不能)
    # ------------------------------------------------------------------
    def _build_rpentomino(self):
        H, W = 40, 44
        grid = _place(_R_PENTOMINO, H, W, offset=(H // 2 - 1, W // 2 - 1))

        box_w, box_h = 7.4, 3.8
        cell = self._cell_size(H, W, box_w, box_h)
        gw, gh = W * cell, H * cell
        top_left = (-gw / 2, gh / 2 + 0.2)

        board = Rectangle(
            width=gw + 0.1,
            height=gh + 0.1,
            stroke_width=1.2,
            stroke_color=EDGE_COLOR,
            fill_opacity=0.0,
        )
        board.move_to([0, top_left[1] - gh / 2, 0])

        title = Text("たった5つのマスが、あばれ続ける", font=FONT, font_size=32, color=ACCENT_GOLD)
        title.move_to([0, 3.15, 0])
        subtitle = Text(
            "Rペントミノ ── 1103世代も続いてから、ようやく静まる",
            font=FONT,
            font_size=23,
            color=TEXT_DIM,
        )
        subtitle.move_to([0, 2.55, 0])
        note = Text(
            "単純な種の結末は、動かしてみるまで読めない", font=FONT, font_size=25, color=ACCENT_PINK
        )
        note.move_to([0, -1.85, 0])

        self._play_life(grid, False, cell, top_left, board, title, subtitle, note, ACCENT_CYAN)


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# No on-screen person names or years in any mode. On-screen numbers
# (3, 8, B3/S23, 1103) are mathematical values / rule strings, not years.
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "rules": {"people": [], "years": []},
    "glider": {"people": [], "years": []},
    "gun": {"people": [], "years": []},
    "rpentomino": {"people": [], "years": []},
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "rules": GameOfLife,
    "glider": GameOfLife,
    "gun": GameOfLife,
    "rpentomino": GameOfLife,
}
