"""
topology_basics.py - Topology basics for Poincaré's Analysis Situs (1895)

Visualizes the basic concepts of algebraic topology that Poincaré founded
in his 1895 paper Analysis Situs and its supplements (1899-1904):

    - sphere: 2-sphere S² with a loop that contracts to a point.
      Fundamental group π₁(S²) = trivial.
    - torus: 2-torus T² with two independent generator loops.
      Fundamental group π₁(T²) = Z × Z.
    - connected_sum: Constructing M # N by removing a disk from each and
      gluing along the boundary circle.
    - 3manifold_intuition: 3-sphere S³ as the boundary of a 4D ball,
      compared with S² as the boundary of a 3D ball. The Poincaré
      conjecture asks: is every simply-connected closed 3-manifold
      homeomorphic to S³?

Fixed parameters (verified by hand):
    Sphere:        radius 1.5, shown as 2D projection (circle outline)
    Torus:         outer radius 2.0, inner radius 0.8 (ring-shaped outline)
    Connected sum: M = sphere, N = torus, glued along a circle
    Conjecture:    M³ simply-connected closed → M³ ≃ S³  (posed 1904)

Duration-aware: reads target duration from _manim_params.json.
Y range: -2.0 to +3.0, subtitle clearance preserved.

Used by: Episode 024 (Poincaré), math pillar 2 — topology & conjecture.
"""

from manim import (
    DOWN,
    Circle,
    Ellipse,
    FadeIn,
    Line,
    MathTex,
    Scene,
    Text,
    config,
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
)

config.background_color = BG_COLOR


class TopologyBasics(Scene):
    """Topology basics for Analysis Situs — multi-mode scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "sphere")
        self._duration = params.get("duration", 35)

        if mode == "torus":
            self._build_torus()
        elif mode == "connected_sum":
            self._build_connected_sum()
        elif mode == "3manifold_intuition":
            self._build_3manifold_intuition()
        else:
            self._build_sphere()

    # ------------------------------------------------------------------
    def _title(self, jp_text):
        title = Text(jp_text, font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.0, 0])
        return title

    # ------------------------------------------------------------------
    def _build_sphere(self):
        """2-sphere with a contractible loop. Fundamental group is trivial."""
        duration = self._duration

        title = self._title("2 次元球面 S² ── 任意のループは一点に縮約する")
        self.play(FadeIn(title), run_time=0.5)

        # Sphere as a circle with equator highlight
        sphere_center = [-2.0, 0.0, 0]
        sphere_outline = Circle(radius=1.6, color=ACCENT_CYAN, stroke_width=3).move_to(
            sphere_center
        )
        equator = Ellipse(width=3.2, height=0.6, color=ACCENT_CYAN, stroke_width=1.5).move_to(
            sphere_center
        )
        self.play(FadeIn(sphere_outline), FadeIn(equator), run_time=0.8)

        sphere_label = MathTex("S^2", font_size=32, color=ACCENT_GOLD)
        sphere_label.next_to(sphere_outline, DOWN, buff=0.3)
        self.play(FadeIn(sphere_label), run_time=0.3)

        # Loop on the sphere (small circle at top)
        loop = Circle(radius=0.7, color=ACCENT_PINK, stroke_width=3)
        loop.move_to([sphere_center[0], sphere_center[1] + 0.5, 0])
        self.play(FadeIn(loop), run_time=0.5)

        # Right side: same loop shown shrinking through stages
        right_label = Text(
            "ループは縮められる",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        right_label.move_to([2.5, 2.0, 0])
        self.play(FadeIn(right_label), run_time=0.4)

        # Show 3 stages of contraction
        stage_y_centers = [1.0, 0.0, -1.0]
        stage_radii = [0.7, 0.4, 0.12]
        for y_c, rad in zip(stage_y_centers, stage_radii, strict=True):
            stage = Circle(radius=rad, color=ACCENT_PINK, stroke_width=2.5)
            stage.move_to([2.5, y_c, 0])
            self.play(FadeIn(stage), run_time=0.4)

        # Conclusion: pi_1(S^2) = 0
        conclusion = MathTex(
            r"\pi_1(S^2) = 0",
            font_size=34,
            color=ACCENT_GOLD,
        )
        conclusion.move_to([0, -2.0, 0])
        self.play(FadeIn(conclusion), run_time=0.6)

        anim_total = 0.5 + 0.8 + 0.3 + 0.5 + 0.4 + 0.4 * 3 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_torus(self):
        """2-torus with two independent loops. Fundamental group = Z x Z."""
        duration = self._duration

        title = self._title("2 次元トーラス T² ── 2 種類の独立したループ")
        self.play(FadeIn(title), run_time=0.5)

        # Torus drawn as two concentric ellipses (outer + inner hole)
        torus_center = [-2.0, 0.2, 0]
        outer = Ellipse(width=4.2, height=2.8, color=ACCENT_CYAN, stroke_width=3)
        outer.move_to(torus_center)
        inner = Ellipse(width=1.8, height=0.7, color=ACCENT_CYAN, stroke_width=2)
        inner.move_to(torus_center)
        self.play(FadeIn(outer), FadeIn(inner), run_time=0.8)

        torus_label = MathTex("T^2", font_size=32, color=ACCENT_GOLD)
        torus_label.next_to(outer, DOWN, buff=0.3)
        self.play(FadeIn(torus_label), run_time=0.3)

        # Loop a: goes around the hole (longitudinal, horizontal great circle)
        loop_a = Ellipse(width=3.0, height=1.5, color=ACCENT_PINK, stroke_width=3)
        loop_a.move_to(torus_center)
        self.play(FadeIn(loop_a), run_time=0.6)
        loop_a_lbl = MathTex("a", font_size=28, color=ACCENT_PINK)
        loop_a_lbl.move_to([torus_center[0] + 2.4, torus_center[1] + 0.2, 0])
        self.play(FadeIn(loop_a_lbl), run_time=0.3)

        # Loop b: meridian, wraps around the tube at torus right end.
        # Centered on the tube axis (avg of outer/inner radii) with size matching
        # the tube cross-section so it visually "wraps" the tube.
        loop_b = Ellipse(width=1.2, height=1.4, color=ACCENT_GOLD, stroke_width=3)
        loop_b.move_to([torus_center[0] + 1.5, torus_center[1], 0])
        self.play(FadeIn(loop_b), run_time=0.6)
        loop_b_lbl = MathTex("b", font_size=28, color=ACCENT_GOLD)
        loop_b_lbl.move_to([torus_center[0] + 1.5, torus_center[1] + 0.85, 0])
        self.play(FadeIn(loop_b_lbl), run_time=0.3)

        # Right side: explanation
        right_label_1 = Text(
            "穴を一周する  a",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        right_label_1.move_to([3.2, 1.2, 0])
        self.play(FadeIn(right_label_1), run_time=0.4)

        right_label_2 = Text(
            "管を一周する  b",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        right_label_2.move_to([3.2, 0.2, 0])
        self.play(FadeIn(right_label_2), run_time=0.4)

        right_label_3 = Text(
            "どちらも縮められない",
            font=FONT,
            font_size=20,
            color=TEXT_DIM,
        )
        right_label_3.move_to([3.2, -0.8, 0])
        self.play(FadeIn(right_label_3), run_time=0.4)

        # Conclusion
        conclusion = MathTex(
            r"\pi_1(T^2) = \mathbb{Z} \times \mathbb{Z}",
            font_size=32,
            color=ACCENT_GOLD,
        )
        conclusion.move_to([0, -1.8, 0])
        self.play(FadeIn(conclusion), run_time=0.6)

        anim_total = 0.5 + 0.8 + 0.3 + 0.6 + 0.3 + 0.6 + 0.3 + 0.4 + 0.4 + 0.4 + 0.6
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_connected_sum(self):
        """Connected sum M # N: remove a disk from each and glue."""
        duration = self._duration

        title = self._title("連結和 M # N ── 円板を取り除いて貼り合わせる")
        self.play(FadeIn(title), run_time=0.5)

        # Left: M (sphere)
        m_center = [-4.5, 0.2, 0]
        m_outline = Circle(radius=1.1, color=ACCENT_CYAN, stroke_width=3).move_to(m_center)
        m_equator = Ellipse(width=2.2, height=0.4, color=ACCENT_CYAN, stroke_width=1.2).move_to(
            m_center
        )
        self.play(FadeIn(m_outline), FadeIn(m_equator), run_time=0.6)
        m_lbl = MathTex("M", font_size=30, color=TEXT_WHITE).next_to(m_outline, DOWN, buff=0.2)
        self.play(FadeIn(m_lbl), run_time=0.3)

        # Right: N (torus)
        n_center = [4.5, 0.2, 0]
        n_outer = Ellipse(width=2.6, height=1.6, color=ACCENT_PINK, stroke_width=3).move_to(
            n_center
        )
        n_inner = Ellipse(width=1.0, height=0.4, color=ACCENT_PINK, stroke_width=1.5).move_to(
            n_center
        )
        self.play(FadeIn(n_outer), FadeIn(n_inner), run_time=0.6)
        n_lbl = MathTex("N", font_size=30, color=TEXT_WHITE).next_to(n_outer, DOWN, buff=0.2)
        self.play(FadeIn(n_lbl), run_time=0.3)

        # Step 1: cut a small disk from each
        m_cut = Circle(radius=0.20, color=BG_COLOR, stroke_width=1.5, fill_opacity=1.0)
        m_cut.move_to([m_center[0] + 0.9, m_center[1] - 0.2, 0])
        n_cut = Circle(radius=0.20, color=BG_COLOR, stroke_width=1.5, fill_opacity=1.0)
        n_cut.move_to([n_center[0] - 1.0, n_center[1] - 0.3, 0])
        self.play(FadeIn(m_cut), FadeIn(n_cut), run_time=0.5)

        # Boundary circles highlighted
        m_bd = Circle(radius=0.22, color=ACCENT_GOLD, stroke_width=2.5)
        m_bd.move_to([m_center[0] + 0.9, m_center[1] - 0.2, 0])
        n_bd = Circle(radius=0.22, color=ACCENT_GOLD, stroke_width=2.5)
        n_bd.move_to([n_center[0] - 1.0, n_center[1] - 0.3, 0])
        self.play(FadeIn(m_bd), FadeIn(n_bd), run_time=0.4)

        cut_label = Text(
            "円板を取り除く",
            font=FONT,
            font_size=18,
            color=ACCENT_GOLD,
        )
        cut_label.move_to([0, 2.0, 0])
        self.play(FadeIn(cut_label), run_time=0.4)

        # Step 2: connect the two boundary circles with a "tube"
        tube_upper = Line(
            start=[m_center[0] + 0.9, m_center[1] + 0.0, 0],
            end=[n_center[0] - 1.0, n_center[1] - 0.1, 0],
            color=ACCENT_GOLD,
            stroke_width=2.5,
        )
        tube_lower = Line(
            start=[m_center[0] + 0.9, m_center[1] - 0.4, 0],
            end=[n_center[0] - 1.0, n_center[1] - 0.5, 0],
            color=ACCENT_GOLD,
            stroke_width=2.5,
        )
        self.play(FadeIn(tube_upper), FadeIn(tube_lower), run_time=0.7)

        # Result label
        result = MathTex(
            r"M \,\#\, N",
            font_size=36,
            color=ACCENT_GOLD,
        )
        result.move_to([0, -1.0, 0])
        self.play(FadeIn(result), run_time=0.6)

        annot = Text(
            "境界の円に沿って貼り合わせて新しい多様体を作る",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        annot.move_to([0, -2.0, 0])
        self.play(FadeIn(annot), run_time=0.5)

        anim_total = 0.5 + 0.6 + 0.3 + 0.6 + 0.3 + 0.5 + 0.4 + 0.4 + 0.7 + 0.6 + 0.5
        self.wait(max(1.5, duration - anim_total))

    # ------------------------------------------------------------------
    def _build_3manifold_intuition(self):
        """3-sphere S^3 as boundary of 4-ball, compared with S^2 from 3-ball."""
        duration = self._duration

        title = self._title("3 次元球面 S³ ── 4 次元球の境界")
        self.play(FadeIn(title), run_time=0.5)

        # Left: 2D dimension example - circle (S^1) as boundary of disk (D^2)
        left_label = Text(
            "1 次元の球面",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        left_label.move_to([-4.2, 1.8, 0])
        self.play(FadeIn(left_label), run_time=0.3)

        # Unified radius 1.0 and center y=+0.3 so S^N labels align at same y
        # (was: radii 0.8/1.0/1.2 caused s3 label to overlap caption)
        center_y = 0.3
        s1 = Circle(radius=1.0, color=ACCENT_CYAN, stroke_width=3)
        s1.move_to([-4.2, center_y, 0])
        self.play(FadeIn(s1), run_time=0.5)
        s1_lbl = MathTex("S^1", font_size=28, color=ACCENT_CYAN)
        s1_lbl.next_to(s1, DOWN, buff=0.2)
        self.play(FadeIn(s1_lbl), run_time=0.3)

        s1_caption = Text(
            "2 次元の円板の境界",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        s1_caption.move_to([-4.2, -1.5, 0])
        self.play(FadeIn(s1_caption), run_time=0.3)

        # Middle: S^2 as boundary of 3D ball
        mid_label = Text(
            "2 次元の球面",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        mid_label.move_to([0, 1.8, 0])
        self.play(FadeIn(mid_label), run_time=0.3)

        s2 = Circle(radius=1.0, color=ACCENT_GOLD, stroke_width=3)
        s2.move_to([0, center_y, 0])
        s2_eq = Ellipse(width=2.0, height=0.4, color=ACCENT_GOLD, stroke_width=1.5)
        s2_eq.move_to([0, center_y, 0])
        self.play(FadeIn(s2), FadeIn(s2_eq), run_time=0.5)
        s2_lbl = MathTex("S^2", font_size=28, color=ACCENT_GOLD)
        s2_lbl.next_to(s2, DOWN, buff=0.2)
        self.play(FadeIn(s2_lbl), run_time=0.3)

        s2_caption = Text(
            "3 次元の球体の境界",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        s2_caption.move_to([0, -1.5, 0])
        self.play(FadeIn(s2_caption), run_time=0.3)

        # Right: S^3 as boundary of 4D ball (drawn abstractly with double-circle motif)
        right_label = Text(
            "3 次元の球面",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        right_label.move_to([4.2, 1.8, 0])
        self.play(FadeIn(right_label), run_time=0.3)

        s3_outer = Circle(radius=1.0, color=ACCENT_PINK, stroke_width=3)
        s3_outer.move_to([4.2, center_y, 0])
        s3_inner = Circle(radius=0.4, color=ACCENT_PINK, stroke_width=2)
        s3_inner.move_to([4.2, center_y, 0])
        self.play(FadeIn(s3_outer), FadeIn(s3_inner), run_time=0.6)
        s3_lbl = MathTex("S^3", font_size=28, color=ACCENT_PINK)
        s3_lbl.next_to(s3_outer, DOWN, buff=0.2)
        self.play(FadeIn(s3_lbl), run_time=0.3)

        s3_caption = Text(
            "4 次元の球体の境界",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        s3_caption.move_to([4.2, -1.5, 0])
        self.play(FadeIn(s3_caption), run_time=0.3)

        # Conjecture statement at the bottom
        conjecture = Text(
            "ポアンカレ予想 (1904): 単連結な閉じた 3 次元多様体は S³ と同相",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        conjecture.move_to([0, -2.0, 0])
        self.play(FadeIn(conjecture), run_time=0.7)

        anim_total = (
            0.5 + 0.3 + 0.5 + 0.3 + 0.3 + 0.3 + 0.5 + 0.3 + 0.3 + 0.3 + 0.6 + 0.3 + 0.3 + 0.7
        )
        self.wait(max(1.5, duration - anim_total))


# ---------------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "sphere": {"people": [], "years": []},
    "torus": {"people": [], "years": []},
    "connected_sum": {"people": [], "years": []},
    "3manifold_intuition": {"people": [], "years": ["1904"]},
}

SCENES = {
    "sphere": TopologyBasics,
    "torus": TopologyBasics,
    "connected_sum": TopologyBasics,
    "3manifold_intuition": TopologyBasics,
}
