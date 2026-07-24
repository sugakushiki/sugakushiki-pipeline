"""
class_field_theory.py - Takagi's class field theory for 数学史記

Visualizes the core correspondence of class field theory established by
Teiji Takagi in 1920 (existence theorem) and completed by Emil Artin
in 1923-1930 (Artin reciprocity), and the chronological chain of the
reciprocity-law lineage that runs from Gauss (1801) to Artin (1930).

Modes:
    field_tower             - Field tower K subset L drawn as two horizontal
                              bars (K at y=-0.7, L at y=1.5), connecting line
                              between them on the right, labels 'Gal(L/K)
                              abelian' and 'K の有限アーベル拡大 L' next to
                              the tower. Fixed params: K bar y=-0.7,
                              L bar y=1.5, tower line x=2.2.
    takagi_correspondence   - Two boxes side by side, left = '合同類群
                              Cl_𝔪(K)/H_L' (cyan), right = 'アーベル拡大
                              Gal(L/K)' (pink), double-arrow between them
                              labeled 'Takagi (1920) ≅ Artin (1930)'.
                              Fixed params: left box center (-3.0, 0),
                              right box center (3.0, 0).
    reciprocity_chain       - 5 events as boxes arranged on a horizontal
                              timeline at y=0: 1801 Gauss / 1844 Eisenstein /
                              1900 Hilbert / 1920 Takagi / 1930 Artin,
                              connected by arrows. Fixed params: 5 events
                              at x ∈ {-5.0, -2.5, 0.0, 2.5, 5.0}.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 030 (Takagi), core class field theory exposition.
"""

import numpy as np
from manim import (
    Arrow,
    DoubleArrow,
    FadeIn,
    Line,
    MathTex,
    Rectangle,
    RoundedRectangle,
    Scene,
    Text,
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


class ClassFieldTheory(Scene):
    """Class field theory: field tower, Takagi correspondence, reciprocity chain."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 20)
        mode = params.get("mode", "field_tower")

        if mode == "takagi_correspondence":
            self.build_takagi_correspondence()
        elif mode == "reciprocity_chain":
            self.build_reciprocity_chain()
        else:
            self.build_field_tower()

    # -------------------------------------------------------------------
    # Mode: field_tower
    # -------------------------------------------------------------------
    def build_field_tower(self):
        duration = self._duration

        title = Text(
            "体の塔 ── アーベル拡大 L / K",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # K bar (base field, bottom)
        K_bar = Rectangle(
            width=3.6,
            height=0.7,
            color=ACCENT_CYAN,
            stroke_width=3,
            fill_opacity=0.18,
            fill_color=ACCENT_CYAN,
        )
        K_bar.move_to(np.array([-1.0, -0.7, 0]))
        K_label = MathTex(r"K", font_size=44, color=TEXT_WHITE)
        K_label.move_to(np.array([-1.0, -0.7, 0]))

        # L bar (extension field, top)
        L_bar = Rectangle(
            width=3.6,
            height=0.7,
            color=ACCENT_PINK,
            stroke_width=3,
            fill_opacity=0.18,
            fill_color=ACCENT_PINK,
        )
        L_bar.move_to(np.array([-1.0, 1.5, 0]))
        L_label = MathTex(r"L", font_size=44, color=TEXT_WHITE)
        L_label.move_to(np.array([-1.0, 1.5, 0]))

        # Connecting line (vertical, on the right edge of bars)
        tower_line = Line(
            np.array([0.8, -0.35, 0]),
            np.array([0.8, 1.15, 0]),
            color=EDGE_COLOR,
            stroke_width=3,
        )

        # Galois group label (on the right of the line)
        gal_label = MathTex(
            r"\mathrm{Gal}(L/K)",
            font_size=36,
            color=ACCENT_GOLD,
        )
        gal_label.move_to(np.array([3.2, 0.7, 0]))

        gal_caption = Text(
            "アーベル群",
            font=FONT,
            font_size=24,
            color=ACCENT_GOLD,
        )
        gal_caption.move_to(np.array([3.2, 0.1, 0]))

        # K caption (left)
        K_caption = Text(
            "数体 K",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        K_caption.move_to(np.array([-4.5, -0.7, 0]))

        # L caption (left)
        L_caption = Text(
            "K のアーベル拡大",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        L_caption.move_to(np.array([-4.5, 1.5, 0]))

        # Bottom note
        bottom_note = Text(
            "ガロア群がアーベル群であるような有限拡大",
            font=FONT,
            font_size=22,
            color=TEXT_DIM,
        )
        bottom_note.move_to(np.array([0, -1.8, 0]))

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(K_bar), FadeIn(K_label), FadeIn(K_caption), run_time=0.7)
        self.play(FadeIn(tower_line), run_time=0.4)
        self.play(FadeIn(L_bar), FadeIn(L_label), FadeIn(L_caption), run_time=0.7)
        self.play(FadeIn(gal_label), FadeIn(gal_caption), run_time=0.6)
        self.play(FadeIn(bottom_note), run_time=0.5)

        anim_overhead = 0.6 + 0.7 + 0.4 + 0.7 + 0.6 + 0.5
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: takagi_correspondence
    # -------------------------------------------------------------------
    def build_takagi_correspondence(self):
        duration = self._duration

        title = Text(
            "類体論の核心 ── 高木の対応",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # Left box: 合同類群 (ideal class group)
        left_box = RoundedRectangle(
            width=4.6,
            height=2.0,
            corner_radius=0.15,
            color=ACCENT_CYAN,
            stroke_width=3,
            fill_opacity=0.15,
            fill_color=ACCENT_CYAN,
        )
        left_box.move_to(np.array([-3.4, 0.2, 0]))

        left_jp = Text(
            "K の合同類群",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        left_jp.move_to(np.array([-3.4, 0.7, 0]))

        left_math = MathTex(
            r"\mathrm{Cl}_{\mathfrak{m}}(K) / H_L",
            font_size=36,
            color=ACCENT_CYAN,
        )
        left_math.move_to(np.array([-3.4, -0.2, 0]))

        # Right box: アーベル拡大 (abelian extension)
        right_box = RoundedRectangle(
            width=4.6,
            height=2.0,
            corner_radius=0.15,
            color=ACCENT_PINK,
            stroke_width=3,
            fill_opacity=0.15,
            fill_color=ACCENT_PINK,
        )
        right_box.move_to(np.array([3.4, 0.2, 0]))

        right_jp = Text(
            "K のアーベル拡大",
            font=FONT,
            font_size=24,
            color=TEXT_WHITE,
        )
        right_jp.move_to(np.array([3.4, 0.7, 0]))

        right_math = MathTex(
            r"\mathrm{Gal}(L/K)",
            font_size=36,
            color=ACCENT_PINK,
        )
        right_math.move_to(np.array([3.4, -0.2, 0]))

        # Double arrow between boxes
        d_arrow = DoubleArrow(
            start=np.array([-1.1, 0.2, 0]),
            end=np.array([1.1, 0.2, 0]),
            color=ACCENT_GOLD,
            buff=0.05,
            stroke_width=4,
            tip_length=0.22,
            max_tip_length_to_length_ratio=0.5,
        )

        # Arrow label: ≅ Takagi (1920) / Artin (1930)
        cong_label = MathTex(
            r"\cong",
            font_size=44,
            color=ACCENT_GOLD,
        )
        cong_label.move_to(np.array([0, 0.7, 0]))

        # Bottom captions: who did what
        takagi_caption = Text(
            "高木 ── 存在定理 (1920)",
            font=FONT,
            font_size=22,
            color=ACCENT_CYAN,
        )
        takagi_caption.move_to(np.array([-3.4, -1.6, 0]))

        artin_caption = Text(
            "アルティン ── 相互法則 (1923-1930)",
            font=FONT,
            font_size=22,
            color=ACCENT_PINK,
        )
        artin_caption.move_to(np.array([3.4, -1.6, 0]))

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(left_box), FadeIn(left_jp), FadeIn(left_math), run_time=0.8)
        self.play(FadeIn(right_box), FadeIn(right_jp), FadeIn(right_math), run_time=0.8)
        self.play(FadeIn(d_arrow), FadeIn(cong_label), run_time=0.7)
        self.play(FadeIn(takagi_caption), FadeIn(artin_caption), run_time=0.7)

        anim_overhead = 0.6 + 0.8 + 0.8 + 0.7 + 0.7
        self.wait(max(1.0, duration - anim_overhead))

    # -------------------------------------------------------------------
    # Mode: reciprocity_chain
    # -------------------------------------------------------------------
    def build_reciprocity_chain(self):
        duration = self._duration

        title = Text(
            "相互法則の系譜 ── 1801 から 1930 へ",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.move_to(np.array([0, 2.8, 0]))

        # 5 events on a horizontal timeline at y=0.
        # Original layout: box width 2.0, spacing 2.5, arrow length 0.4.
        # For long person names (e.g. アイゼンシュタイン 8 chars) shrink font
        # only for that text (others stay font_size 18). Box/spacing/arrow
        # geometry preserved for visual balance -- confirmed against the
        # rendered frame rather than guessed.
        events = [
            ("-5.0", "1801", "ガウス", "平方剰余", ACCENT_CYAN),
            ("-2.5", "1844", "アイゼンシュタイン", "三次・四次", ACCENT_CYAN),
            ("0.0", "1900", "ヒルベルト", "第9問題", ACCENT_GOLD),
            ("2.5", "1920", "高木", "存在定理", ACCENT_PINK),
            ("5.0", "1930", "アルティン", "相互法則", ACCENT_PINK),
        ]

        boxes = []
        year_texts = []
        person_texts = []
        topic_texts = []

        for x_str, year, person, topic, color in events:
            x = float(x_str)
            box = RoundedRectangle(
                width=2.0,
                height=1.8,
                corner_radius=0.12,
                color=color,
                stroke_width=2.5,
                fill_opacity=0.15,
                fill_color=color,
            )
            box.move_to(np.array([x, 0.2, 0]))
            boxes.append(box)

            year_t = Text(year, font=FONT, font_size=24, color=color)
            year_t.move_to(np.array([x, 0.8, 0]))
            year_texts.append(year_t)

            # Shrink font only for long person names (アイゼンシュタイン: 8 char).
            # Box width 2.0 fits up to 6 chars at font 18; 7-8 chars at font 14.
            person_font = 14 if len(person) >= 7 else 18
            person_t = Text(person, font=FONT, font_size=person_font, color=TEXT_WHITE)
            person_t.move_to(np.array([x, 0.25, 0]))
            person_texts.append(person_t)

            topic_t = Text(topic, font=FONT, font_size=16, color=TEXT_DIM)
            topic_t.move_to(np.array([x, -0.3, 0]))
            topic_texts.append(topic_t)

        # Arrows connecting consecutive events (box half-width 1.0 + buff 0.05)
        arrows = []
        xs = [float(e[0]) for e in events]
        for i in range(len(xs) - 1):
            arr = Arrow(
                start=np.array([xs[i] + 1.05, 0.2, 0]),
                end=np.array([xs[i + 1] - 1.05, 0.2, 0]),
                color=EDGE_COLOR,
                buff=0.05,
                stroke_width=2.5,
                tip_length=0.18,
                max_tip_length_to_length_ratio=0.6,
            )
            arrows.append(arr)

        # Bottom caption
        bottom_caption = Text(
            "百三十年に渡る数論の中央問題 ── アーベル版が完全解決された",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        bottom_caption.move_to(np.array([0, -1.8, 0]))

        self.play(FadeIn(title), run_time=0.6)
        for box, year_t, person_t, topic_t in zip(
            boxes, year_texts, person_texts, topic_texts, strict=False
        ):
            self.play(FadeIn(box), FadeIn(year_t), FadeIn(person_t), FadeIn(topic_t), run_time=0.4)
        self.play(*[FadeIn(a) for a in arrows], run_time=0.6)
        self.play(FadeIn(bottom_caption), run_time=0.6)

        anim_overhead = 0.6 + 0.4 * 5 + 0.6 + 0.6
        self.wait(max(1.0, duration - anim_overhead))


# -----------------------------------------------------------------------
# LINT_FACTUAL_CLAIMS metadata (qa_manim_consistency.py uses this)
# -----------------------------------------------------------------------
LINT_FACTUAL_CLAIMS = {
    "field_tower": {
        "people": [],
        "years": [],
    },
    "takagi_correspondence": {
        "people": [
            ["高木", "Takagi"],
            ["アルティン", "Artin"],
        ],
        "years": ["1920", "1923", "1930"],
    },
    "reciprocity_chain": {
        "people": [
            ["ガウス", "Gauss"],
            ["アイゼンシュタイン", "Eisenstein"],
            ["ヒルベルト", "Hilbert"],
            ["高木", "Takagi"],
            ["アルティン", "Artin"],
        ],
        "years": ["1801", "1844", "1900", "1920", "1930"],
    },
}


# -----------------------------------------------------------------------
# SCENES dict for template auto-discovery
# -----------------------------------------------------------------------
SCENES = {
    "field_tower": {
        "class": "ClassFieldTheory",
        "params": {"mode": "field_tower"},
        "description": "Field tower K subset L with Gal(L/K) abelian group label",
    },
    "takagi_correspondence": {
        "class": "ClassFieldTheory",
        "params": {"mode": "takagi_correspondence"},
        "description": "Takagi's bijection: Cl_𝔪(K)/H_L ≅ Gal(L/K) shown as two boxes with double-arrow",
    },
    "reciprocity_chain": {
        "class": "ClassFieldTheory",
        "params": {"mode": "reciprocity_chain"},
        "description": "Timeline 1801 Gauss → 1844 Eisenstein → 1900 Hilbert → 1920 Takagi → 1930 Artin",
    },
}
