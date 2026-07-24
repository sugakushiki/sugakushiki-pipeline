"""
coherent_sheaf_lineage.py - From Oka's local-to-global tools to the modern language

Episode 044 (Kiyoshi Oka). Two intuition-level diagrams: the Cousin problem
(gluing local data into a global holomorphic function) and the lineage by which
Oka's "ideals of indeterminate domains" became, in others' hands, the language of
coherent sheaves and modern algebraic geometry.

Modes:
    cousin (default)
        Several overlapping local patches, each carrying local data; on the
        overlaps the data agree, and they glue into one global holomorphic
        function. This is what Oka's tools made possible (the Cousin problem).
        Fixed params: 3 overlapping disks, overlap markers, one glued global box.
    lineage
        The attribution chain, drawn accurately: Oka (ideals of indeterminate
        domains / coherence = the foundation) and Leray (sheaves) both feed into
        Cartan & Serre (coherent sheaves, Theorems A and B), which leads on to
        Grothendieck (modern algebraic geometry). Sheaves are Leray's; the term
        "coherent sheaf" and the general theory are Cartan-Serre's; Oka built the
        foundation -- this is stated in the bottom note.
        Fixed params: 4 boxes (Oka, Leray, Cartan/Serre, Grothendieck), 3 arrows.

All Text uses FONT (BIZ UDMincho). No MathTex. On-screen names (lineage mode):
Oka, Leray, Cartan, Serre, Grothendieck -- all also spoken in the narration.
Y range: about -1.65 to +3.05. No trailing FadeOut.
"""

from manim import (
    DOWN,
    RIGHT,
    Arrow,
    Circle,
    Dot,
    FadeIn,
    Rectangle,
    Scene,
    Text,
    VGroup,
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


class CoherentSheafLineage(Scene):
    """Cousin gluing and the Oka -> coherent-sheaf lineage - two modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "cousin")
        duration = float(params.get("duration", 26))
        if mode == "lineage":
            self._build_lineage(duration)
        else:
            self._build_cousin(duration)

    # ----------------------------------------------------------------- cousin
    def _build_cousin(self, duration):
        title = Text("局所をつなぎ、大域をつくる", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        centers = [[-2.2, 1.2, 0], [0, 1.2, 0], [2.2, 1.2, 0]]
        disks, data = [], []
        for c in centers:
            d = Circle(radius=1.3, color=ACCENT_CYAN, stroke_width=2.2).move_to(c)
            d.set_fill(ACCENT_CYAN, opacity=0.08)
            disks.append(d)
            data.append(Dot(c, color=ACCENT_PINK, radius=0.07))

        ov_marks = VGroup(
            Dot([-1.1, 1.2, 0], color=ACCENT_GOLD, radius=0.07),
            Dot([1.1, 1.2, 0], color=ACCENT_GOLD, radius=0.07),
        )
        ov_label = Text("重なりで一致する", font=FONT, font_size=20, color=ACCENT_GOLD)
        ov_label.move_to([0, -0.05, 0])

        arrow = Arrow([0, -0.45, 0], [0, -0.95, 0], color=TEXT_DIM, buff=0.05, stroke_width=4)
        glue = Text("貼り合わせ", font=FONT, font_size=18, color=TEXT_DIM)
        glue.next_to(arrow, RIGHT, buff=0.15)
        box = Rectangle(width=5.2, height=0.7, color=ACCENT_GOLD, stroke_width=2).move_to(
            [0, -1.3, 0]
        )
        box.set_fill(ACCENT_GOLD, opacity=0.12)
        box_label = Text("大域的な正則関数", font=FONT, font_size=22, color=ACCENT_GOLD).move_to(
            [0, -1.3, 0]
        )

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        for i in range(3):
            self.play(FadeIn(disks[i]), FadeIn(data[i]), run_time=per)
        self.play(FadeIn(ov_marks), FadeIn(ov_label), run_time=per)
        self.play(FadeIn(arrow), FadeIn(glue), run_time=per)
        self.play(FadeIn(box), FadeIn(box_label), run_time=per)
        self.wait(coda)

    # ---------------------------------------------------------------- lineage
    def _build_lineage(self, duration):
        title = Text("岡から、現代数学の言葉へ", font=FONT, font_size=30, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        oka = self._box(["岡", "不定域イデアル・連接性"], [-4.3, 1.55, 0], ACCENT_GOLD, 2.7, 1.05)
        leray = self._box(["ルレ", "層"], [-4.3, -0.35, 0], TEXT_DIM, 2.7, 0.9)
        cs = self._box(
            ["カルタン／セール", "連接層・定理A／定理B"], [0, 0.6, 0], ACCENT_CYAN, 3.3, 1.15
        )
        groth = self._box(
            ["グロタンディーク", "現代代数幾何"], [4.4, 0.6, 0], ACCENT_PINK, 2.8, 1.05
        )

        a1 = Arrow([-2.95, 1.35, 0], [-1.7, 0.85, 0], color=ACCENT_GOLD, buff=0.1, stroke_width=4)
        a2 = Arrow([-2.95, -0.3, 0], [-1.7, 0.35, 0], color=TEXT_DIM, buff=0.1, stroke_width=4)
        a3 = Arrow([1.7, 0.6, 0], [2.95, 0.6, 0], color=ACCENT_CYAN, buff=0.1, stroke_width=4)

        note = Text(
            "層はルレ、連接層はカルタン＝セール。岡はその土台を作った",
            font=FONT,
            font_size=18,
            color=TEXT_DIM,
        )
        note.move_to([0, -1.6, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 5.0
        self.play(FadeIn(oka), run_time=per)
        self.play(FadeIn(leray), run_time=per)
        self.play(FadeIn(a1), FadeIn(a2), FadeIn(cs), run_time=per)
        self.play(FadeIn(a3), FadeIn(groth), run_time=per)
        self.play(FadeIn(note), run_time=per)
        self.wait(coda)

    def _box(self, lines, center, color, w, h, fs=20):
        rect = Rectangle(width=w, height=h, color=color, stroke_width=2).move_to(center)
        rect.set_fill(color, opacity=0.10)
        first = Text(lines[0], font=FONT, font_size=fs, color=TEXT_WHITE)
        rest = [Text(s, font=FONT, font_size=fs - 3, color=TEXT_DIM) for s in lines[1:]]
        txt = VGroup(first, *rest).arrange(DOWN, buff=0.12).move_to(center)
        return VGroup(rect, txt)


LINT_FACTUAL_CLAIMS = {
    "cousin": {"people": [], "years": []},
    "lineage": {
        "people": [
            ["岡", "Oka"],
            ["ルレ", "Leray"],
            ["カルタン", "Cartan"],
            ["セール", "Serre"],
            ["グロタンディーク", "Grothendieck"],
        ],
        "years": [],
    },
}

SCENES = {
    "cousin": CoherentSheafLineage,
    "lineage": CoherentSheafLineage,
}
