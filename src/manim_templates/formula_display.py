"""
formula_display.py - Mathematical formula display with LaTeX for 数学史記

Displays a mathematical formula (LaTeX) with optional Japanese subtitle.
Uses MathTex for crisp rendering of mathematical notation.

Modes:
    static    - Show formula with fade-in, hold
    highlight - Show formula, then highlight specific parts in sequence

Params:
    formula: LaTeX string (required)
    subtitle: Japanese text below formula (optional, **plain text only — LaTeX commands
              like \\alpha, \\mathbb, $...$ are auto-detected, stripped with WARN, and
              fall back to plain rendering. See _sanitize_subtitle for detection rules.**)
    highlight_parts: list of part indices to highlight in sequence (highlight mode)

Duration-aware: reads target duration from _manim_params.json.
"""

import re
import sys

from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    FadeIn,
    Indicate,
    Line,
    MathTex,
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


# subtitle field is for plain Japanese text. LaTeX commands rendered via
# Text() show as raw "\alpha \in \mathbb{R}" (moriarty math_01 で顕在化). Detect and
# strip with WARN to prevent silent disfigurement.
_LATEX_TOKEN_RE = re.compile(r"\\[a-zA-Z]+|[\$_^{}]")


def _sanitize_subtitle(subtitle: str) -> str:
    """Strip LaTeX-looking tokens from subtitle, log WARN if any found.

    Common LaTeX tokens stripped: \\command, $, _, ^, {, }.
    Plain Japanese text passes through untouched.
    """
    if not subtitle or not _LATEX_TOKEN_RE.search(subtitle):
        return subtitle
    cleaned = _LATEX_TOKEN_RE.sub("", subtitle).strip()
    print(
        f"[formula_display WARN] subtitle に LaTeX トークン検出。strip しました。\n"
        f"  before: {subtitle!r}\n"
        f"  after:  {cleaned!r}\n"
        f"  推奨: scene_definition.json の subtitle は平文日本語のみ使う (LaTeX は formula 側に移す)。",
        file=sys.stderr,
    )
    return cleaned


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


def _looks_cjk(s: str) -> bool:
    """True if the string contains Japanese/Chinese characters.

    Covers CJK punctuation/symbols, Hiragana, Katakana, CJK Unified
    (incl. Ext-A), CJK compatibility, and fullwidth forms.
    """
    return any(
        0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF or 0xFF00 <= ord(c) <= 0xFFEF
        for c in s
    )


def _formula_mobject(tex: str, font_size: int, color):
    """Return a MathTex for LaTeX, or a Text fallback if `tex` contains CJK.

    script_generator occasionally emits Japanese/Chinese inside the `latex`
    field (e.g. ``\\text{冪勢既同、則積不容異}``), which crashes the
    LaTeX->dvi compile and breaks the whole scene。CJK を含む式は Text(font=FONT) で
    描画して落とさない (layered defense / no scene-wide failure)。
    """
    if _looks_cjk(tex):
        return Text(tex, font=FONT, font_size=max(int(font_size * 0.62), 22), color=color)
    return MathTex(tex, font_size=font_size, color=color)


# Factual-claim metadata (read by qa_manim_consistency.py). Single-class
# template with no on-screen person/year claims — declared empty under the
# lint's "default" fallback key (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {"default": {"people": [], "years": []}}


class FormulaDisplay(Scene):
    """Display a mathematical formula with LaTeX rendering."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "static")
        self._duration = params.get("duration", 30)
        self._formula = params.get(
            "formula", r"f(x) = \sum_{n=0}^{\infty} a_n \cos(nx) + b_n \sin(nx)"
        )
        # subtitle に LaTeX が混入していたら strip + WARN (Text() が LaTeX レンダリング不可のため)
        self._subtitle = _sanitize_subtitle(params.get("subtitle", ""))
        self._highlight_parts = params.get("highlight_parts", [])
        # Multi-formula support: list of LaTeX strings + optional Japanese labels per formula
        self._formulas = params.get("formulas") or []
        self._labels = list(params.get("labels", []))

        # Normalize dict-form formulas [{"latex":..,"label":..}] to a parallel
        # latex-string list + labels list. script_generator may emit either
        # schema; without this MathTex() receives a dict and the scene renders
        # broken。
        # Defensive: accepts both the string form and the dict form.
        if self._formulas and any(isinstance(f, dict) for f in self._formulas):
            norm_f, norm_l = [], list(self._labels)
            for idx, f in enumerate(self._formulas):
                if isinstance(f, dict):
                    norm_f.append(f.get("latex") or f.get("formula") or "")
                    lbl = f.get("label", "")
                    if idx < len(norm_l):
                        if not norm_l[idx]:
                            norm_l[idx] = lbl
                    else:
                        norm_l.append(lbl)
                else:
                    norm_f.append(f)
                    if idx >= len(norm_l):
                        norm_l.append("")
            self._formulas = norm_f
            self._labels = norm_l

        # Auto-promote 1-element `formulas` list to singular `formula`.
        # Previously this case fell through to build_static() which only reads
        # `self._formula` (default = hardcoded Fourier series), silently rendering
        # the wrong formula. found 4 scenes affected this way.
        if self._formulas and len(self._formulas) == 1:
            self._formula = self._formulas[0]
            if self._labels and not self._subtitle:
                self._subtitle = _sanitize_subtitle(self._labels[0])

        if self._formulas and len(self._formulas) >= 2:
            self.build_multi()
        elif mode == "highlight" and self._highlight_parts:
            self.build_highlight()
        else:
            self.build_static()

    def build_multi(self):
        """Display multiple formulas stacked vertically with optional Japanese labels."""
        dur = self._duration
        formulas_list = self._formulas
        labels_list = self._labels
        n = len(formulas_list)

        # Adapt font sizes for layout (smaller as count grows)
        formula_font = 44 if n <= 2 else (38 if n == 3 else 32)
        label_font = 22 if n <= 2 else 20

        # Build formula+label units
        units = []
        for i, f_tex in enumerate(formulas_list):
            formula = _formula_mobject(f_tex, formula_font, ACCENT_GOLD)
            parts = [formula]
            if i < len(labels_list) and labels_list[i]:
                label = Text(labels_list[i], font=FONT, font_size=label_font, color=TEXT_DIM)
                label.next_to(formula, DOWN, buff=0.18)
                parts.append(label)
            units.append(VGroup(*parts))

        # Stack vertically, centered
        group = VGroup(*units).arrange(DOWN, buff=0.7)
        # Constrain to safe Y range (subtitle clearance at y = -2.0)
        if group.height > 4.5:
            scale = 4.5 / group.height
            group.scale(scale)
        group.move_to(ORIGIN)

        # Animate FadeIn sequentially
        per_unit_anim = 1.5
        per_unit_wait = 0.4
        for unit in units:
            self.play(FadeIn(unit), run_time=per_unit_anim)
            self.wait(per_unit_wait)

        anim_total = (per_unit_anim + per_unit_wait) * n
        self.wait(max(dur - anim_total, 1.0))

    def build_static(self):
        """Show formula with fade-in, then hold."""
        dur = self._duration
        anim_time = 3.0
        default_wait_total = dur - anim_time
        ws = _calc_wait_scale(dur, anim_time, max(default_wait_total, 1.0))

        # Formula
        formula = _formula_mobject(self._formula, 52, ACCENT_GOLD)

        if self._subtitle:
            formula.shift(UP * 0.5)

        self.play(FadeIn(formula), run_time=1.5)
        self.wait(0.5 * ws)

        # Subtitle
        if self._subtitle:
            # Separator line
            line = Line(
                LEFT * 2.5,
                RIGHT * 2.5,
                color=ACCENT_GOLD,
                stroke_width=1.5,
                stroke_opacity=0.6,
            )
            line.next_to(formula, DOWN, buff=0.4)

            subtitle = Text(
                self._subtitle,
                font=FONT,
                font_size=26,
                color=TEXT_WHITE,
            )
            subtitle.next_to(line, DOWN, buff=0.3)

            self.play(FadeIn(line), FadeIn(subtitle), run_time=1.0)

        self.wait(max(dur - 3.0, 1.0))

    def build_highlight(self):
        """Show formula, then highlight specific parts in sequence."""
        # Highlight indexes into MathTex submobjects; a Text fallback would
        # break that. If the formula contains CJK (invalid LaTeX), degrade to
        # the static (Text-safe) renderer instead of crashing.
        if _looks_cjk(self._formula):
            self.build_static()
            return
        dur = self._duration
        parts = self._highlight_parts
        n_highlights = len(parts)

        anim_time = 2.0 + n_highlights * 1.5
        default_wait_total = n_highlights * 1.0 + 2.0
        ws = _calc_wait_scale(dur, anim_time, default_wait_total)

        # Formula (split into parts for highlighting)
        formula = MathTex(
            self._formula,
            font_size=52,
            color=TEXT_WHITE,
        )

        if self._subtitle:
            formula.shift(UP * 0.5)

        self.play(FadeIn(formula), run_time=1.5)
        self.wait(1.0 * ws)

        # Subtitle
        if self._subtitle:
            line = Line(
                LEFT * 2.5,
                RIGHT * 2.5,
                color=ACCENT_GOLD,
                stroke_width=1.5,
                stroke_opacity=0.6,
            )
            line.next_to(formula, DOWN, buff=0.4)

            subtitle = Text(
                self._subtitle,
                font=FONT,
                font_size=26,
                color=TEXT_DIM,
            )
            subtitle.next_to(line, DOWN, buff=0.3)
            self.play(FadeIn(line), FadeIn(subtitle), run_time=0.5)

        # Highlight parts
        highlight_colors = [ACCENT_GOLD, ACCENT_CYAN, ACCENT_PINK]
        for i, part_idx in enumerate(parts):
            color = highlight_colors[i % len(highlight_colors)]
            if part_idx < len(formula[0]):
                self.play(
                    Indicate(formula[0][part_idx], color=color, scale_factor=1.2),
                    run_time=1.0,
                )
                self.wait(1.0 * ws)

        self.wait(1.0 * ws)
