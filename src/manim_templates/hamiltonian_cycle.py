"""
hamiltonian_cycle.py - The Icosian Game and Hamiltonian cycles (数学史記)

Hamilton's 1857 Icosian Game asks for a closed route that visits each of
the 20 corners of a dodecahedron exactly once. The "visit-every-vertex-once"
closed route is now called a Hamiltonian cycle.

Two views of the same object are used:
    - dodecahedron mode shows the solid dodecahedron itself (DODECA_V from
      polyhedron_euler, with hidden-line removal) so the viewer recognises
      the shape whose corners and edges become a graph.
    - find_cycle mode shows the dodecahedral graph as a clean planar
      (Schlegel-style) diagram. The dodecahedral graph is isomorphic to the
      generalized Petersen graph GP(10,2): an outer 10-cycle u0..u9, an
      inner double-pentagon v0..v9 with vi-v(i+2), and 10 spokes ui-vi.
      A Hamiltonian cycle (found by backtracking) is highlighted in gold.

Modes:
    dodecahedron - The solid dodecahedron wireframe + the counts
                   "20 vertices, 30 edges". Fixed params: V=20, E=30.
    find_cycle   - The dodecahedral graph (GP(10,2), 20 vertices, 30 edges)
                   with one Hamiltonian cycle traced in gold, segment by
                   segment, returning to the start. Fixed params: 20
                   vertices visited once, cycle length 20.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 033 (Hamilton), graph-theory pillar.
"""

import math

import numpy as np
from manim import (
    Dot,
    FadeIn,
    Line,
    Scene,
    Text,
    VGroup,
    config,
)
from polyhedron_euler import DODECA_V, _polyhedron_wireframe
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
# Dodecahedral graph as GP(10,2): planar (Schlegel-style) layout
# ---------------------------------------------------------------------------
def _gp10_2_layout(center=(0.0, 0.35, 0.0), r_out=2.05, r_in=1.05):
    """Return (positions, edges, adjacency) for the dodecahedral graph.

    Vertices 0..9 = outer decagon, 10..19 = inner (10+i = vi).
    Edges: outer ui-u(i+1), spokes ui-vi, inner vi-v(i+2).
    """
    cx, cy, _ = center
    pos = [None] * 20
    for i in range(10):
        ang = math.radians(90 - 36 * i)
        pos[i] = np.array([cx + r_out * math.cos(ang), cy + r_out * math.sin(ang), 0.0])
        pos[10 + i] = np.array([cx + r_in * math.cos(ang), cy + r_in * math.sin(ang), 0.0])

    edges = set()
    for i in range(10):
        edges.add(tuple(sorted((i, (i + 1) % 10))))  # outer cycle
        edges.add(tuple(sorted((i, 10 + i))))  # spoke
        edges.add(tuple(sorted((10 + i, 10 + ((i + 2) % 10)))))  # inner double pentagon
    edges = sorted(edges)

    adj = [[] for _ in range(20)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    for nbrs in adj:
        nbrs.sort()
    return pos, edges, adj


def _find_hamiltonian_cycle(adj, n=20, start=0):
    """Backtracking search for a Hamiltonian cycle. Returns vertex list of
    length n (the closing edge back to start is implied) or None."""
    path = [start]
    used = [False] * n
    used[start] = True

    def dfs(v):
        if len(path) == n:
            return start in adj[v]
        for w in adj[v]:
            if not used[w]:
                used[w] = True
                path.append(w)
                if dfs(w):
                    return True
                path.pop()
                used[w] = False
        return False

    return path if dfs(start) else None


class HamiltonianCycle(Scene):
    """Icosian game / Hamiltonian cycle on the dodecahedral graph."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 26)
        self._highlight = params.get("highlight_color", ACCENT_GOLD)
        mode = params.get("mode", "dodecahedron")

        if mode == "find_cycle":
            self.build_find_cycle()
        else:
            self.build_dodecahedron()

    # ------------------------------------------------------------------
    # Mode: dodecahedron
    # ------------------------------------------------------------------
    def build_dodecahedron(self):
        duration = self._duration

        title = Text("正十二面体", font=FONT, font_size=32, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        subtitle = Text("── 12枚の正五角形からなる立体", font=FONT, font_size=22, color=TEXT_DIM)
        subtitle.move_to([0, 2.55, 0])

        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)

        solid = _polyhedron_wireframe(
            DODECA_V, [0, 0.45, 0], size=1.55, color=ACCENT_CYAN, stroke=2.0
        )
        self.play(FadeIn(solid), run_time=1.0)
        self.wait(0.4)

        v_word = Text("頂点 20、辺 30", font=FONT, font_size=26, color=TEXT_WHITE)
        v_word.move_to([0, -1.45, 0])
        self.play(FadeIn(v_word), run_time=0.6)

        note = Text(
            "角を頂点、稜を辺と見れば、ひとつのグラフになる",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        note.move_to([0, -1.95, 0])
        self.play(FadeIn(note), run_time=0.6)

        used = 0.6 + 1.0 + 0.4 + 0.6 + 0.6
        self.wait(max(1.0, duration - used))

    # ------------------------------------------------------------------
    # Mode: find_cycle
    # ------------------------------------------------------------------
    def build_find_cycle(self):
        duration = self._duration

        title = Text("ハミルトン閉路", font=FONT, font_size=32, color=TEXT_DIM)
        title.move_to([0, 3.15, 0])
        subtitle = Text(
            "── すべての頂点を一度ずつ通って戻る", font=FONT, font_size=22, color=TEXT_DIM
        )
        subtitle.move_to([0, 2.55, 0])
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.6)

        pos, edges, adj = _gp10_2_layout()

        # Base graph: dim edges + vertices
        base_edges = VGroup()
        for a, b in edges:
            base_edges.add(Line(pos[a], pos[b], color=EDGE_COLOR, stroke_width=2.5))
        dots = VGroup()
        for p in pos:
            dots.add(Dot(p, color=ACCENT_CYAN, radius=0.075))

        self.play(FadeIn(base_edges), run_time=0.8)
        self.play(FadeIn(dots), run_time=0.6)
        self.wait(0.4)

        cycle = _find_hamiltonian_cycle(adj, 20, 0)
        if cycle is None:  # safety; the dodecahedral graph is always Hamiltonian
            cycle = list(range(20))

        closed = cycle + [cycle[0]]
        n_seg = len(closed) - 1
        anim_budget = max(4.0, duration - 4.0)
        seg_time = min(0.45, anim_budget / n_seg)

        # start vertex marker
        self.play(dots[cycle[0]].animate.set_color(self._highlight).scale(1.4), run_time=0.4)

        for k in range(n_seg):
            a, b = closed[k], closed[k + 1]
            seg = Line(pos[a], pos[b], color=self._highlight, stroke_width=6)
            self.play(
                FadeIn(seg),
                dots[b].animate.set_color(self._highlight),
                run_time=seg_time,
            )

        note = Text(
            "20個の頂点をちょうど一度ずつ ── これがハミルトン閉路",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        note.move_to([0, -1.95, 0])
        self.play(FadeIn(note), run_time=0.7)

        used = 0.6 + 0.8 + 0.6 + 0.4 + 0.4 + seg_time * n_seg + 0.7
        self.wait(max(1.0, duration - used))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# No people/years displayed on screen (shape + graph only).
LINT_FACTUAL_CLAIMS = {
    "dodecahedron": {"people": [], "years": []},
    "find_cycle": {"people": [], "years": []},
}


SCENES = {
    "dodecahedron": {
        "class": "HamiltonianCycle",
        "params": {"mode": "dodecahedron"},
        "description": "Solid dodecahedron wireframe with V=20, E=30 (the Icosian board's shape)",
    },
    "find_cycle": {
        "class": "HamiltonianCycle",
        "params": {"mode": "find_cycle"},
        "description": "Dodecahedral graph GP(10,2) with one Hamiltonian cycle traced in gold",
    },
}
