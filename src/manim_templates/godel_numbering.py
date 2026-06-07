"""
godel_numbering.py - Gödel numbering and self-reference for 数学史記

Visualizes the central technique of Gödel's 1931 proof of the first
incompleteness theorem: encoding symbols, formulas, and proofs as natural
numbers, then constructing a self-referential proposition via the
diagonal lemma.

Modes:
    symbol_codes      - 3x3 grid of (symbol → code) mappings.
                        Fixed params: 9 symbols (¬,∨,∀,x,=,0,S,(,))
                        mapped to codes 1..9. 3 cols at x={-3.5,0,3.5},
                        3 rows at y={1.5,0.3,-0.9}.
    formula_encoding  - Encode ∀x(x=x) step by step:
                        symbols → codes [3,4,8,4,5,4,9]
                        → product 2^3 · 3^4 · 5^8 · 7^4 · 11^5 · 13^4 · 17^9
                        → single huge natural number N.
                        Fixed params: formula = ∀x(x=x), 7 symbols, 7 primes
                        (2,3,5,7,11,13,17).
    self_reference    - Enumerated propositions P_1..P_5 with the last G
                        asserting "this proposition is unprovable", drawn
                        with a self-referential loop arrow.
                        Fixed params: 5 propositions, G = P_5.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 021 (Gödel), math pillar 2 — the central scene of the
entire episode (4 minutes target).
"""

import numpy as np
from manim import (
    PI,
    RIGHT,
    Arrow,
    CurvedArrow,
    FadeIn,
    MathTex,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

SUBTITLE_Y_LIMIT = -2.0

# Fixed symbol-to-code mapping (9 symbols, codes 1..9)
SYMBOL_MAP = [
    (r"\neg", 1),  # ¬
    (r"\vee", 2),  # ∨
    (r"\forall", 3),  # ∀
    ("x", 4),
    ("=", 5),
    ("0", 6),
    ("S", 7),
    ("(", 8),
    (")", 9),
]

# For formula_encoding: ∀x(x=x) → codes [3,4,8,4,5,4,9]
FORMULA_SYMBOLS = [r"\forall", "x", "(", "x", "=", "x", ")"]
FORMULA_CODES = [3, 4, 8, 4, 5, 4, 9]
PRIMES = [2, 3, 5, 7, 11, 13, 17]


class GodelNumbering(Scene):
    """Gödel numbering and self-reference. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 30)
        mode = params.get("mode", "symbol_codes")

        if mode == "formula_encoding":
            self.build_formula_encoding()
        elif mode == "self_reference":
            self.build_self_reference()
        else:
            self.build_symbol_codes()

    # -------------------------------------------------------------------
    # Mode: symbol_codes
    # -------------------------------------------------------------------
    def build_symbol_codes(self):
        duration = self._duration

        title = Text(
            "ゲーデル番号化 ── 記号に数を割り振る",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # 3x3 grid layout
        col_xs = [-3.5, 0.0, 3.5]
        row_ys = [1.5, 0.3, -0.9]

        cells = []
        for idx, (sym_tex, code) in enumerate(SYMBOL_MAP):
            row = idx // 3
            col = idx % 3
            cx = col_xs[col]
            cy = row_ys[row]

            # Cell background
            cell = RoundedRectangle(
                width=2.6,
                height=0.95,
                corner_radius=0.1,
                color=EDGE_COLOR,
                stroke_width=1.5,
                fill_opacity=0.1,
                fill_color=ACCENT_CYAN,
            )
            cell.move_to(np.array([cx, cy, 0]))

            # Symbol on left, arrow, code on right
            symbol = MathTex(sym_tex, font_size=40, color=ACCENT_CYAN)
            symbol.move_to(np.array([cx - 0.8, cy, 0]))

            arrow = MathTex(r"\to", font_size=30, color=TEXT_DIM)
            arrow.move_to(np.array([cx - 0.05, cy, 0]))

            code_tex = MathTex(str(code), font_size=38, color=ACCENT_GOLD)
            code_tex.move_to(np.array([cx + 0.7, cy, 0]))

            cells.append((cell, symbol, arrow, code_tex))

        self.play(FadeIn(title), run_time=0.5)

        for cell, sym, arr, code in cells:
            self.play(
                FadeIn(cell),
                FadeIn(sym),
                FadeIn(arr),
                FadeIn(code),
                run_time=0.35,
            )

        anim_overhead = 0.5 + 0.35 * 9
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: formula_encoding
    # -------------------------------------------------------------------
    def build_formula_encoding(self):
        duration = self._duration

        title = Text(
            "式から自然数へ ── ∀x(x = x) の符号化",
            font=FONT,
            font_size=28,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # Tier 1: original formula symbols laid out horizontally
        formula_y = 2.0
        symbol_spacing = 0.85
        n_sym = len(FORMULA_SYMBOLS)
        x_start = -(n_sym - 1) * symbol_spacing / 2

        symbols = []
        codes_below = []
        for i, sym_tex in enumerate(FORMULA_SYMBOLS):
            x = x_start + i * symbol_spacing
            sym = MathTex(sym_tex, font_size=44, color=ACCENT_CYAN)
            sym.move_to(np.array([x, formula_y, 0]))
            symbols.append(sym)

            # Code below
            code = MathTex(str(FORMULA_CODES[i]), font_size=32, color=ACCENT_GOLD)
            code.move_to(np.array([x, formula_y - 0.85, 0]))
            codes_below.append(code)

        # Tier 2: code list as a tuple
        list_y = 0.0
        list_str = "[" + ", ".join(str(c) for c in FORMULA_CODES) + "]"
        code_list = MathTex(list_str, font_size=34, color=ACCENT_GOLD)
        code_list.move_to(np.array([0, list_y, 0]))

        # Tier 3: product expression
        product_y = -1.0
        # Build readable LaTeX string
        product_parts = []
        for p, c in zip(PRIMES, FORMULA_CODES, strict=False):
            product_parts.append(f"{p}^{{{c}}}")
        product_str = r" \cdot ".join(product_parts)
        product_tex = MathTex(product_str, font_size=32, color=ACCENT_PINK)
        product_tex.move_to(np.array([0, product_y, 0]))

        # Final caption: gives the natural number N
        caption = Text(
            "→ 一つの自然数 N",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        caption.move_to(np.array([0, -1.85, 0]))

        # Animate
        self.play(FadeIn(title), run_time=0.5)

        for sym in symbols:
            self.play(FadeIn(sym), run_time=0.18)

        for code in codes_below:
            self.play(FadeIn(code), run_time=0.18)

        # Arrow down to code list
        arrow1 = Arrow(
            start=np.array([0, formula_y - 1.15, 0]),
            end=np.array([0, list_y + 0.25, 0]),
            color=EDGE_COLOR,
            buff=0.05,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(FadeIn(arrow1), FadeIn(code_list), run_time=0.6)

        # Arrow down to product
        arrow2 = Arrow(
            start=np.array([0, list_y - 0.25, 0]),
            end=np.array([0, product_y + 0.3, 0]),
            color=EDGE_COLOR,
            buff=0.05,
            stroke_width=2,
            max_tip_length_to_length_ratio=0.15,
        )
        self.play(FadeIn(arrow2), FadeIn(product_tex), run_time=0.7)

        # Final caption
        self.play(FadeIn(caption), run_time=0.5)

        anim_overhead = 0.5 + 0.18 * len(symbols) + 0.18 * len(codes_below) + 0.6 + 0.7 + 0.5
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: self_reference
    # -------------------------------------------------------------------
    def build_self_reference(self):
        duration = self._duration

        title = Text(
            "対角化補題 ── 自分自身を指す命題 G",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 3.0, 0]))

        # Enumerated propositions P_1..P_5
        # P_1: 0 = 0
        # P_2: ∀x(x = x)
        # P_3: ¬(0 = S(0))
        # P_4: ∀x(x = S(0))
        # P_5: G (the self-referential proposition)
        prop_specs = [
            (r"P_1: \;\; 0 = 0", ACCENT_CYAN),
            (r"P_2: \;\; \forall x\, (x = x)", ACCENT_CYAN),
            (r"P_3: \;\; \neg\,(0 = S(0))", ACCENT_CYAN),
            (r"P_4: \;\; \forall x\, (x = S(0))", ACCENT_CYAN),
            (r"P_5: \;\; G", ACCENT_GOLD),
        ]
        row_ys = [2.0, 1.3, 0.6, -0.1, -0.85]

        prop_mobs = []
        for (tex, color), y in zip(prop_specs, row_ys, strict=False):
            mob = MathTex(tex, font_size=32, color=color)
            mob.move_to(np.array([-2.5, y, 0]))
            prop_mobs.append(mob)

        # Caption for G (right side) — split text/math because BIZ UDMincho
        # cannot render Unicode subscripts (P_5 must come from MathTex).
        cap_lq = Text("「", font=FONT, font_size=22, color=ACCENT_PINK)
        cap_p5 = MathTex("P_5", font_size=26, color=ACCENT_PINK)
        cap_rest = Text(
            "は証明できない」",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        g_caption = VGroup(cap_lq, cap_p5, cap_rest)
        g_caption.arrange(RIGHT, buff=0.06)
        g_caption.move_to(np.array([2.9, -0.85, 0]))

        # Self-reference loop arrow: from P_5 caption back to P_5 label
        # Curved arrow from right of caption looping back to left of P_5
        loop = CurvedArrow(
            start_point=np.array([2.7, -1.25, 0]),
            end_point=np.array([-2.5, -1.25, 0]),
            angle=-PI / 2.5,
            color=ACCENT_PINK,
            stroke_width=2.5,
            tip_length=0.18,
        )

        # Bottom note
        bottom_note = Text(
            "G は真であるが、体系の中では証明できない",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        bottom_note.move_to(np.array([0, -1.85, 0]))

        self.play(FadeIn(title), run_time=0.5)

        # Show P_1..P_4 first
        for mob in prop_mobs[:4]:
            self.play(FadeIn(mob), run_time=0.4)

        # Show P_5 (G) with emphasis
        self.play(FadeIn(prop_mobs[4]), run_time=0.6)

        # Show caption explaining what G says
        self.play(FadeIn(g_caption), run_time=0.5)

        # Show self-referential loop
        self.play(FadeIn(loop), run_time=0.7)

        # Bottom conclusion
        self.play(FadeIn(bottom_note), run_time=0.6)

        anim_overhead = 0.5 + 0.4 * 4 + 0.6 + 0.5 + 0.7 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
# B-10 / B-24: no hardcoded people/years in display Text() (docstring only).
LINT_FACTUAL_CLAIMS = {
    "symbol_codes": {"people": [], "years": []},
    "formula_encoding": {"people": [], "years": []},
    "self_reference": {"people": [], "years": []},
}


SCENES = {
    "symbol_codes": {
        "class": "GodelNumbering",
        "params": {"mode": "symbol_codes"},
        "description": "3x3 grid mapping 9 logic symbols to codes 1..9",
    },
    "formula_encoding": {
        "class": "GodelNumbering",
        "params": {"mode": "formula_encoding"},
        "description": "Encode ∀x(x=x) into a single natural number via primes",
    },
    "self_reference": {
        "class": "GodelNumbering",
        "params": {"mode": "self_reference"},
        "description": "Construct self-referential proposition G via diagonal lemma",
    },
}
