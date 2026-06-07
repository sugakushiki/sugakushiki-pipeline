"""
boolean_circuit.py - Boolean algebra and switching circuits for 数学史記

Visualizes the correspondence between Boolean algebra and electrical circuits,
as discovered in Shannon's master's thesis (1937).

Modes:
    switch  - AND = series switches, OR = parallel switches.
              ON/OFF animation shows current flow (color change).
              Fixed params: AND (A·B, series), OR (A+B, parallel), bulb indicator
    formula - Boolean expression A·B + C mapped to a circuit diagram.
              Fixed params: expression A·B+C, series path (A,B) + parallel path (C)

Duration-aware: reads target duration from _manim_params.json.
"""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Circle,
    FadeIn,
    FadeOut,
    Indicate,
    Line,
    MathTex,
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


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _make_switch(label_text, is_on=False):
    """Create a switch element (small rectangle with label)."""
    color = ACCENT_CYAN if is_on else TEXT_DIM
    rect = Rectangle(
        width=1.0,
        height=0.5,
        color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=0.2 if is_on else 0.05,
    )
    label = Text(label_text, font=FONT, font_size=18, color=color)
    label.move_to(rect)
    return VGroup(rect, label)


def _make_wire(start, end, is_on=False):
    """Create a wire (line) between two points."""
    color = ACCENT_CYAN if is_on else TEXT_DIM
    return Line(start, end, color=color, stroke_width=2.5)


class BooleanCircuit(Scene):
    """Visualize Boolean algebra / switching circuit correspondence."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "switch")
        self._duration = params.get("duration", 25)

        if mode == "formula":
            self.build_formula()
        else:
            self.build_switch()

    # -------------------------------------------------------------------
    # Mode: switch
    # -------------------------------------------------------------------
    def build_switch(self):
        """AND = series, OR = parallel switch circuits."""
        dur = self._duration
        anim_time = 9.0
        default_wait_total = 7.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "ブール代数とスイッチ回路",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # --- AND circuit (series) ---
        and_label = Text("AND（直列）", font=FONT, font_size=22, color=ACCENT_GOLD)
        and_label.shift(UP * 2.0 + LEFT * 3.0)

        sw_a1 = _make_switch("A")
        sw_b1 = _make_switch("B")
        sw_a1.shift(UP * 1.2 + LEFT * 4.0)
        sw_b1.shift(UP * 1.2 + LEFT * 2.0)

        wire_and_left = _make_wire(sw_a1.get_left() + LEFT * 0.8, sw_a1.get_left())
        wire_and_mid = _make_wire(sw_a1.get_right(), sw_b1.get_left())
        wire_and_right = _make_wire(sw_b1.get_right(), sw_b1.get_right() + RIGHT * 0.8)

        # Bulb indicator
        bulb_and = Circle(
            radius=0.2,
            color=TEXT_DIM,
            stroke_width=2,
            fill_color=TEXT_DIM,
            fill_opacity=0.1,
        )
        bulb_and.next_to(sw_b1, RIGHT, buff=1.2)
        bulb_and_label = Text("OFF", font=FONT, font_size=14, color=TEXT_DIM)
        bulb_and_label.next_to(bulb_and, DOWN, buff=0.15)

        and_circuit = VGroup(
            and_label,
            sw_a1,
            sw_b1,
            wire_and_left,
            wire_and_mid,
            wire_and_right,
            bulb_and,
            bulb_and_label,
        )

        self.play(FadeIn(and_circuit), run_time=1.0)
        self.wait(0.5 * ws)

        # AND: both ON → light on
        and_formula = MathTex(r"A \cdot B = 1", font_size=28, color=ACCENT_GOLD)
        and_formula.shift(UP * 0.3 + LEFT * 3.0)

        sw_a1_on = _make_switch("A", is_on=True)
        sw_a1_on.move_to(sw_a1)
        sw_b1_on = _make_switch("B", is_on=True)
        sw_b1_on.move_to(sw_b1)
        bulb_and_on = Circle(
            radius=0.2,
            color=ACCENT_GOLD,
            stroke_width=2,
            fill_color=ACCENT_GOLD,
            fill_opacity=0.6,
        )
        bulb_and_on.move_to(bulb_and)
        bulb_and_on_label = Text("ON", font=FONT, font_size=14, color=ACCENT_GOLD)
        bulb_and_on_label.next_to(bulb_and_on, DOWN, buff=0.15)

        self.play(
            FadeOut(sw_a1),
            FadeIn(sw_a1_on),
            FadeOut(sw_b1),
            FadeIn(sw_b1_on),
            FadeOut(bulb_and),
            FadeIn(bulb_and_on),
            FadeOut(bulb_and_label),
            FadeIn(bulb_and_on_label),
            FadeIn(and_formula),
            run_time=1.0,
        )
        self.wait(1.0 * ws)

        # --- OR circuit (parallel) ---
        or_label = Text("OR（並列）", font=FONT, font_size=22, color=ACCENT_GOLD)
        or_label.shift(DOWN * 0.5 + LEFT * 3.0)

        # Two parallel paths
        sw_a2 = _make_switch("A")
        sw_b2 = _make_switch("B")
        sw_a2.shift(DOWN * 1.0 + LEFT * 3.0)
        sw_b2.shift(DOWN * 2.0 + LEFT * 3.0)

        # Junction wires (simplified parallel layout)
        junc_left = LEFT * 4.8 + DOWN * 1.5
        junc_right = LEFT * 1.2 + DOWN * 1.5

        wire_to_a = _make_wire(junc_left + UP * 0.5, sw_a2.get_left())
        wire_to_b = _make_wire(junc_left + DOWN * 0.5, sw_b2.get_left())
        wire_from_a = _make_wire(sw_a2.get_right(), junc_right + UP * 0.5)
        wire_from_b = _make_wire(sw_b2.get_right(), junc_right + DOWN * 0.5)
        wire_left_vert = _make_wire(junc_left + UP * 0.5, junc_left + DOWN * 0.5)
        wire_right_vert = _make_wire(junc_right + UP * 0.5, junc_right + DOWN * 0.5)

        bulb_or = Circle(
            radius=0.2,
            color=TEXT_DIM,
            stroke_width=2,
            fill_color=TEXT_DIM,
            fill_opacity=0.1,
        )
        bulb_or.move_to(junc_right + RIGHT * 1.0)
        bulb_or_label = Text("OFF", font=FONT, font_size=14, color=TEXT_DIM)
        bulb_or_label.next_to(bulb_or, DOWN, buff=0.15)

        or_circuit = VGroup(
            or_label,
            sw_a2,
            sw_b2,
            wire_to_a,
            wire_to_b,
            wire_from_a,
            wire_from_b,
            wire_left_vert,
            wire_right_vert,
            bulb_or,
            bulb_or_label,
        )
        self.play(FadeIn(or_circuit), run_time=1.0)
        self.wait(0.5 * ws)

        # OR: only A ON → light on
        or_formula = MathTex(r"A + B = 1", font_size=28, color=ACCENT_GOLD)
        or_formula.shift(DOWN * 2.8 + LEFT * 3.0)

        sw_a2_on = _make_switch("A", is_on=True)
        sw_a2_on.move_to(sw_a2)
        bulb_or_on = Circle(
            radius=0.2,
            color=ACCENT_GOLD,
            stroke_width=2,
            fill_color=ACCENT_GOLD,
            fill_opacity=0.6,
        )
        bulb_or_on.move_to(bulb_or)
        bulb_or_on_label = Text("ON", font=FONT, font_size=14, color=ACCENT_GOLD)
        bulb_or_on_label.next_to(bulb_or_on, DOWN, buff=0.15)

        self.play(
            FadeOut(sw_a2),
            FadeIn(sw_a2_on),
            FadeOut(bulb_or),
            FadeIn(bulb_or_on),
            FadeOut(bulb_or_label),
            FadeIn(bulb_or_on_label),
            FadeIn(or_formula),
            run_time=1.0,
        )
        self.wait(2.0 * ws)

    # -------------------------------------------------------------------
    # Mode: formula
    # -------------------------------------------------------------------
    def build_formula(self):
        """Boolean expression A·B + C → circuit mapping."""
        dur = self._duration
        anim_time = 7.0
        default_wait_total = 6.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        title = Text(
            "ブール式から回路へ",
            font=FONT,
            font_size=28,
            color=TEXT_WHITE,
        )
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.8)

        # Boolean expression
        expr = MathTex(
            r"A",
            r"\cdot",
            r"B",
            r"+",
            r"C",
            font_size=48,
            color=TEXT_WHITE,
        )
        expr.shift(UP * 2.0)
        self.play(FadeIn(expr), run_time=1.0)
        self.wait(0.5 * ws)

        # Highlight A·B (series)
        self.play(
            Indicate(expr[0], color=ACCENT_CYAN, scale_factor=1.3),
            Indicate(expr[1], color=ACCENT_CYAN, scale_factor=1.3),
            Indicate(expr[2], color=ACCENT_CYAN, scale_factor=1.3),
            run_time=0.8,
        )

        series_label = Text(
            "A \u00b7 B = 直列",
            font=FONT,
            font_size=20,
            color=ACCENT_CYAN,
        )
        series_label.shift(UP * 0.8 + LEFT * 3.0)
        self.play(FadeIn(series_label), run_time=0.5)
        self.wait(0.5 * ws)

        # Highlight + C (parallel)
        self.play(
            Indicate(expr[3], color=ACCENT_PINK, scale_factor=1.3),
            Indicate(expr[4], color=ACCENT_PINK, scale_factor=1.3),
            run_time=0.8,
        )

        parallel_label = Text(
            "+ C = 並列",
            font=FONT,
            font_size=20,
            color=ACCENT_PINK,
        )
        parallel_label.shift(UP * 0.8 + RIGHT * 3.0)
        self.play(FadeIn(parallel_label), run_time=0.5)
        self.wait(0.5 * ws)

        # Circuit diagram for A·B + C
        # Upper path: A in series with B
        sw_a = _make_switch("A")
        sw_b = _make_switch("B")
        sw_a.shift(DOWN * 0.5 + LEFT * 2.0)
        sw_b.shift(DOWN * 0.5 + RIGHT * 0.0)

        wire_ab = _make_wire(sw_a.get_right(), sw_b.get_left())

        # Lower path: C alone
        sw_c = _make_switch("C")
        sw_c.shift(DOWN * 1.7 + LEFT * 1.0)

        # Junction wires
        junc_l = LEFT * 3.5
        junc_r = RIGHT * 1.5

        wire_l_to_a = _make_wire(junc_l + DOWN * 0.5, sw_a.get_left())
        wire_l_to_c = _make_wire(junc_l + DOWN * 1.7, sw_c.get_left())
        wire_b_to_r = _make_wire(sw_b.get_right(), junc_r + DOWN * 0.5)
        wire_c_to_r = _make_wire(sw_c.get_right(), junc_r + DOWN * 1.7)
        wire_l_vert = _make_wire(junc_l + DOWN * 0.5, junc_l + DOWN * 1.7)
        wire_r_vert = _make_wire(junc_r + DOWN * 0.5, junc_r + DOWN * 1.7)

        # Bulb
        bulb = Circle(
            radius=0.2,
            color=TEXT_DIM,
            stroke_width=2,
            fill_color=TEXT_DIM,
            fill_opacity=0.1,
        )
        bulb.move_to(junc_r + RIGHT * 1.2 + DOWN * 1.1)

        circuit = VGroup(
            sw_a,
            sw_b,
            sw_c,
            wire_ab,
            wire_l_to_a,
            wire_l_to_c,
            wire_b_to_r,
            wire_c_to_r,
            wire_l_vert,
            wire_r_vert,
            bulb,
        )
        self.play(FadeIn(circuit), run_time=1.5)
        self.wait(1.0 * ws)

        # Bottom note
        note = Text(
            "ブール代数の演算が回路の接続に一対一対応する",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.0 * ws)


# -----------------------------------------------------------------------
# SCENES registry (used by pipeline auto-discovery)
# -----------------------------------------------------------------------
# no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "switch": {"people": [], "years": []},
    "formula": {"people": [], "years": []},
}


SCENES = {
    "switch": BooleanCircuit,
    "formula": BooleanCircuit,
}
