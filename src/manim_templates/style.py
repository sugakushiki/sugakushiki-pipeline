"""
style.py - Shared Manim style configuration for 数学史記

All templates import from this module to maintain visual consistency.
Settings match STYLE_GUIDE.md confirmed values.
"""

import json
import os

# ---------------------------------------------------------------------------
# Colors (from STYLE_GUIDE.md)
# ---------------------------------------------------------------------------
BG_COLOR = "#1a1a2e"
ACCENT_GOLD = "#e2b714"
ACCENT_CYAN = "#4cc9f0"
ACCENT_PINK = "#ff66b3"
TEXT_WHITE = "#ffffff"
TEXT_DIM = "#aaaabb"
EDGE_COLOR = "#555577"

# ---------------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------------
FONT = "BIZ UDMincho"

# ---------------------------------------------------------------------------
# Parameter loading
# ---------------------------------------------------------------------------
PARAMS_FILE = "_manim_params.json"


def load_params() -> dict:
    """Load template parameters from _manim_params.json.

    visual_generator.py writes this file before calling manim render.
    """
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def pace(duration, weights, intro=0.0, coda=0.0, floor=0.12):
    """Split a scene's animation budget across steps by weight.

    Returns a list of run_times = w_i * per, where per = budget / sum(weights) and
    budget = (duration - intro - coda). Because the denominator is ALWAYS the actual
    sum of the weights, the animations fill exactly (duration - intro - coda), so the
    scene's conclusion + the trailing coda hold are NOT clipped when the rendered mp4
    is later trimmed to the audio length.

    This replaces the error-prone hand-written `per = body / N` pattern: if N was typed
    smaller than the true weight-sum, the animations overran `duration`, Manim rendered
    a too-long mp4, the assembler cut it to the audio, and the final reveal + coda were
    lost.

    Args:
        duration: total scene seconds (usually the audio length passed via params).
        weights:  run_time weight of each play()/wait() step, in play order.
        intro:    fixed run_time consumed BEFORE the weighted steps (e.g. title+sub
                  FadeIns done at constant run_time), excluded from the split.
        coda:     the trailing self.wait(coda) hold, excluded from the split.
        floor:    minimum per-step run_time, so a tiny weight never renders to ~0s.

    Usage:
        CODA = 4.5
        rt = pace(duration, [1, 1, 0.4, 0.7, 1, 0.9, 1, 1, 0.7], intro=1.1, coda=CODA)
        self.play(FadeIn(a), run_time=rt[0]); ...; self.wait(CODA)
    """
    total_w = sum(weights) or 1.0
    budget = max(floor * total_w, float(duration) - intro - coda)
    per = budget / total_w
    return [max(floor, w * per) for w in weights]


# ---------------------------------------------------------------------------
# Helper: styled_text (from STYLE_GUIDE.md)
# ---------------------------------------------------------------------------
def styled_text(*parts, font_size=28):
    """Create mixed Japanese text + MathTex group.

    Args:
        parts: tuples of (content, kind) where kind is "text" or "math"
        font_size: base font size

    Returns:
        VGroup with properly sized and arranged elements

    Usage:
        styled_text(("素数 ", "text"), ("p", "math"), (" は", "text"))
    """
    from manim import RIGHT, MathTex, Text, VGroup

    group = VGroup()
    text_ref = None
    for content, kind in parts:
        if kind == "math":
            t = MathTex(content, font_size=font_size)
        else:
            t = Text(content, font=FONT, font_size=font_size)
            if text_ref is None:
                text_ref = t
        group.add(t)
    if text_ref is not None:
        for item in group:
            if isinstance(item, MathTex):
                item.match_height(text_ref)
                item.scale(0.85)
    group.arrange(RIGHT, buff=0.15)
    return group
