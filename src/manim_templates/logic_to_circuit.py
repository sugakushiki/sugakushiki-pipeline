"""
logic_to_circuit.py - From 0 and 1 to the logic of machines (George Boole)

Episode 046 (George Boole). The modern payoff: Boole's algebra of 0 and 1 slept
for ~80 years, then matched electric switching exactly. Switch on/off = 1/0,
series = AND, parallel = OR. Shannon (1937) showed Boole's algebra IS the
language of circuits. Presented as historical fact, not a cross-episode teaser.

Modes:
    gate (default)
        Three logic gates -- AND (かつ), OR (または), NOT (でない) -- each as a
        labelled box with input/output lines and a compact truth table beneath.
        Point: Boole's multiply / add / (1-x) become the logic gates.
        Fixed params: gates at x = -4.3, 0, +4.3; AND/OR have 4-row tables, NOT
        a 2-row table.
        On screen: no proper nouns, no years.
    switch
        Two switch circuits: series (= AND, lamp lights only if BOTH closed) on
        the left and parallel (= OR, lamp lights if EITHER closed) on the right,
        with switch on = 1 / off = 0, and the 1854 (Boole) -> 1937 (Shannon)
        timeline note.
        Fixed params: series and parallel panels at x = -3.4 and +3.4; lamp lit
        (gold); switches drawn as gold blades.
        On screen: names Boole (ブール), Shannon (シャノン); years 1854, 1937.

All Text uses FONT (BIZ UDMincho). No MathTex (digits are plain Text).
Y range: about -1.72 to +3.05. No trailing FadeOut.
"""

from manim import (
    Circle,
    Create,
    Dot,
    FadeIn,
    Indicate,
    Line,
    RoundedRectangle,
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


class LogicToCircuit(Scene):
    """Boole's 0-and-1 algebra becomes the logic of machines -- two modes."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "gate")
        duration = float(params.get("duration", 24))
        if mode == "switch":
            self._build_switch(duration)
        else:
            self._build_gate(duration)

    # ---------------------------------------------------------------------- gate
    def _build_gate(self, duration):
        title = Text("0 と 1 の論理 ── 論理ゲート", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        gates = [
            (-4.3, "AND", "かつ", 2, ["0  0 → 0", "0  1 → 0", "1  0 → 0", "1  1 → 1"], 3),
            (0.0, "OR", "または", 2, ["0  0 → 0", "0  1 → 1", "1  0 → 1", "1  1 → 1"], 3),
            (4.3, "NOT", "でない", 1, ["0 → 1", "1 → 0"], -1),
        ]

        built = []
        for cx, name, jp, n_in, rows, hi in gates:
            box = RoundedRectangle(
                width=1.5, height=1.0, corner_radius=0.12, color=ACCENT_CYAN, stroke_width=3
            )
            box.move_to([cx, 1.7, 0])
            name_t = Text(name, font=FONT, font_size=22, color=TEXT_WHITE)
            name_t.move_to([cx, 1.85, 0])
            jp_t = Text(jp, font=FONT, font_size=15, color=TEXT_DIM)
            jp_t.move_to([cx, 1.5, 0])
            io = VGroup()
            if n_in == 2:
                io.add(
                    Line([cx - 1.35, 1.9, 0], [cx - 0.75, 1.9, 0], color=TEXT_DIM, stroke_width=2)
                )
                io.add(
                    Line([cx - 1.35, 1.5, 0], [cx - 0.75, 1.5, 0], color=TEXT_DIM, stroke_width=2)
                )
            else:
                io.add(
                    Line([cx - 1.35, 1.7, 0], [cx - 0.75, 1.7, 0], color=TEXT_DIM, stroke_width=2)
                )
            io.add(Line([cx + 0.75, 1.7, 0], [cx + 1.35, 1.7, 0], color=TEXT_DIM, stroke_width=2))
            io.add(Dot([cx + 1.35, 1.7, 0], color=ACCENT_GOLD, radius=0.055))
            gate_group = VGroup(box, name_t, jp_t, io)

            header = Text("入力 → 出力", font=FONT, font_size=15, color=ACCENT_GOLD)
            header.move_to([cx, 0.62, 0])
            table = VGroup(header)
            for i, r in enumerate(rows):
                color = ACCENT_GOLD if i == hi else TEXT_WHITE
                row_t = Text(r, font=FONT, font_size=17, color=color)
                row_t.move_to([cx, 0.18 - i * 0.4, 0])
                table.add(row_t)
            built.append((gate_group, table))

        takeaway = Text(
            "ブールの「かつ・または・でない」が、そのまま論理ゲートに",
            font=FONT,
            font_size=20,
            color=ACCENT_GOLD,
        )
        takeaway.move_to([0, -1.68, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 7.0
        for gate_group, table in built:
            self.play(FadeIn(gate_group), run_time=per)
            self.play(FadeIn(table), run_time=per * 0.9)
        self.play(FadeIn(takeaway), run_time=per)
        self.wait(coda)

    # -------------------------------------------------------------------- switch
    def _switch_blade(self, px, py, length=0.62, up=0.0):
        """A closed switch: pivot dot, gold blade, contact dot."""
        pivot = Dot([px, py, 0], color=TEXT_WHITE, radius=0.05)
        blade = Line([px, py, 0], [px + length, py + up, 0], color=ACCENT_GOLD, stroke_width=4)
        contact = Dot([px + length + 0.06, py, 0], color=TEXT_WHITE, radius=0.05)
        return VGroup(pivot, blade, contact)

    def _lamp(self, cx, cy):
        lamp = Circle(radius=0.22, color=ACCENT_GOLD, stroke_width=3)
        lamp.move_to([cx, cy, 0]).set_fill(ACCENT_GOLD, opacity=0.45)
        cross = VGroup(
            Line(
                [cx - 0.15, cy - 0.15, 0],
                [cx + 0.15, cy + 0.15, 0],
                color=ACCENT_GOLD,
                stroke_width=2,
            ),
            Line(
                [cx - 0.15, cy + 0.15, 0],
                [cx + 0.15, cy - 0.15, 0],
                color=ACCENT_GOLD,
                stroke_width=2,
            ),
        )
        return VGroup(lamp, cross)

    def _build_switch(self, duration):
        title = Text("スイッチの オン・オフ ＝ 1・0", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to([0, 3.05, 0])
        self.play(FadeIn(title), run_time=0.7)

        lab_l = Text("直列 ＝ かつ（AND）", font=FONT, font_size=20, color=ACCENT_CYAN)
        lab_l.move_to([-3.4, 2.35, 0])
        lab_r = Text("並列 ＝ または（OR）", font=FONT, font_size=20, color=ACCENT_GOLD)
        lab_r.move_to([3.4, 2.35, 0])

        # --- series (AND), center x = -3.4, wires at y = 0.95 ---
        cs = -3.4
        y = 0.95
        series = VGroup(
            Line([cs - 1.7, y, 0], [cs - 1.25, y, 0], color=TEXT_DIM, stroke_width=2),
            Line([cs - 0.57, y, 0], [cs - 0.15, y, 0], color=TEXT_DIM, stroke_width=2),
            Line([cs + 0.53, y, 0], [cs + 1.08, y, 0], color=TEXT_DIM, stroke_width=2),
        )
        series.add(self._switch_blade(cs - 1.25, y))
        series.add(self._switch_blade(cs - 0.15, y))
        series.add(self._lamp(cs + 1.3, y))
        sa = Text("A", font=FONT, font_size=16, color=TEXT_DIM).move_to([cs - 0.9, y - 0.4, 0])
        sb = Text("B", font=FONT, font_size=16, color=TEXT_DIM).move_to([cs + 0.2, y - 0.4, 0])
        series.add(sa, sb)
        note_l = Text("両方 オン のときだけ 点灯", font=FONT, font_size=17, color=TEXT_WHITE)
        note_l.move_to([-3.4, -0.35, 0])

        # --- parallel (OR), center x = +3.4 ---
        cp = 3.4
        yt, yb = 1.35, 0.55
        parallel = VGroup(
            Line([cp - 1.9, y, 0], [cp - 1.5, y, 0], color=TEXT_DIM, stroke_width=2),
            Line([cp - 1.5, yb, 0], [cp - 1.5, yt, 0], color=TEXT_DIM, stroke_width=2),
            Line([cp - 0.82, yt, 0], [cp + 0.55, yt, 0], color=TEXT_DIM, stroke_width=2),
            Line([cp - 0.82, yb, 0], [cp + 0.55, yb, 0], color=TEXT_DIM, stroke_width=2),
            Line([cp + 0.55, yb, 0], [cp + 0.55, yt, 0], color=TEXT_DIM, stroke_width=2),
            Line([cp + 0.55, y, 0], [cp + 1.08, y, 0], color=TEXT_DIM, stroke_width=2),
        )
        parallel.add(self._switch_blade(cp - 1.5, yt))
        parallel.add(self._switch_blade(cp - 1.5, yb))
        parallel.add(self._lamp(cp + 1.3, y))
        note_r = Text("どちらか オン なら 点灯", font=FONT, font_size=17, color=TEXT_WHITE)
        note_r.move_to([3.4, -0.35, 0])

        mid = Text("スイッチの オン ＝ 1、　オフ ＝ 0", font=FONT, font_size=18, color=TEXT_DIM)
        mid.move_to([0, -1.05, 0])
        timeline = Text(
            "1854 ブール『思考の法則』 ── 1937 シャノンが回路の言葉に",
            font=FONT,
            font_size=19,
            color=ACCENT_GOLD,
        )
        timeline.move_to([0, -1.68, 0])

        used = 0.7
        coda = 2.5
        body = max(3.0, duration - used - coda)
        per = body / 6.0
        self.play(FadeIn(lab_l), FadeIn(lab_r), run_time=per * 0.8)
        self.play(Create(series), FadeIn(note_l), run_time=per * 1.2)
        self.play(Create(parallel), FadeIn(note_r), run_time=per * 1.2)
        self.play(
            Indicate(series[-3], color=ACCENT_PINK),
            Indicate(parallel[-1], color=ACCENT_PINK),
            run_time=per * 0.8,
        )
        self.play(FadeIn(mid), run_time=per * 0.8)
        self.play(FadeIn(timeline), run_time=per)
        self.wait(coda)


LINT_FACTUAL_CLAIMS = {
    "gate": {"people": [], "years": []},
    "switch": {
        "people": [["ブール", "Boole"], ["シャノン", "Shannon"]],
        "years": ["1854", "1937"],
    },
}

SCENES = {
    "gate": LogicToCircuit,
    "switch": LogicToCircuit,
}
