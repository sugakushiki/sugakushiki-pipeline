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
