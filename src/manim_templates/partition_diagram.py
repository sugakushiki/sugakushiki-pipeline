"""
partition_diagram.py - Integer partition visualization for 数学史記

Visualizes the partition function p(n) using Young diagram-style blocks.

Modes:
    small_n  - Show all partitions of a small number (e.g. p(4)=5)
               with block diagrams for each partition
    growth   - Show p(n) values growing rapidly in a table/bar display
    table    - Display a table of n vs p(n) values

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 004 (Ramanujan), math_01, math_02
"""

from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    UP,
    FadeIn,
    MathTex,
    Scene,
    Square,
    Table,
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
    load_params,
)

config.background_color = BG_COLOR


def partitions_of(n):
    """Generate all partitions of n as sorted tuples (descending)."""
    if n == 0:
        return [()]
    results = []

    def helper(remaining, max_val, current):
        if remaining == 0:
            results.append(tuple(current))
            return
        for i in range(min(remaining, max_val), 0, -1):
            helper(remaining - i, i, current + [i])

    helper(n, n, [])
    return results


def make_young_diagram(partition, cell_size=0.3, color=ACCENT_CYAN):
    """Create a Young diagram (Ferrers diagram) from a partition tuple."""
    group = VGroup()
    for row_idx, part in enumerate(partition):
        for col_idx in range(part):
            sq = Square(
                side_length=cell_size,
                color=color,
                fill_opacity=0.6,
                stroke_width=1,
                stroke_color=color,
            )
            sq.move_to(
                [
                    col_idx * cell_size * 1.05,
                    -row_idx * cell_size * 1.05,
                    0,
                ]
            )
            group.add(sq)
    group.move_to(ORIGIN)
    return group


class PartitionSmallN(Scene):
    """Show all partitions of a small n with Young diagrams."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 20)
        n = params.get("n", 4)
        highlight_color = params.get("highlight_color", ACCENT_CYAN)

        parts = partitions_of(n)

        # Title
        title = MathTex(f"p({n}) = {len(parts)}", font_size=48, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.5)
        self.play(FadeIn(title), run_time=0.8)

        wait_per = max(0.3, (duration - 3 - len(parts) * 0.8) / len(parts))

        # Layout partitions in a grid
        diagrams = VGroup()
        labels = VGroup()
        for p in parts:
            d = make_young_diagram(p, cell_size=0.25, color=highlight_color)
            label_str = " + ".join(str(x) for x in p)
            lbl = MathTex(label_str, font_size=20, color=TEXT_DIM)
            diagrams.add(d)
            labels.add(lbl)

        # Arrange in rows
        cols = min(5, len(parts))
        rows_needed = (len(parts) + cols - 1) // cols
        for i, (d, lbl) in enumerate(zip(diagrams, labels, strict=False)):
            row = i // cols
            col = i % cols
            x = (col - (cols - 1) / 2) * 2.2
            y = 1.0 - row * 2.0
            d.move_to([x, y, 0])
            lbl.next_to(d, DOWN, buff=0.15)

        # Animate each partition
        for d, lbl in zip(diagrams, labels, strict=False):
            self.play(FadeIn(d), FadeIn(lbl), run_time=0.6)
            self.wait(wait_per)

        self.wait(1.0)


class PartitionGrowth(Scene):
    """Show the rapid growth of p(n) values."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 20)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        # Known p(n) values
        pn_data = [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 5),
            (5, 7),
            (10, 42),
            (20, 627),
            (50, 204226),
            (100, 190569292),
            (200, 3972999029388),
        ]

        title = Text("p(n)", font=FONT, font_size=42, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.5)
        self.play(FadeIn(title), run_time=0.6)

        wait_per = max(0.3, (duration - 4) / len(pn_data))

        # Build entries one by one
        entries = VGroup()
        for idx, (n, pn) in enumerate(pn_data):
            if pn < 10000:
                pn_str = str(pn)
            else:
                # Scientific notation for large numbers
                exp = len(str(pn)) - 1
                pn_str = f"\\approx 10^{{{exp}}}"

            entry = MathTex(
                f"p({n})",
                "=",
                pn_str if pn < 10000 else pn_str,
                font_size=32,
            )
            entry[0].set_color(ACCENT_CYAN)
            if pn >= 10000:
                entry[2].set_color(ACCENT_PINK)
            else:
                entry[2].set_color(highlight_color)
            entries.add(entry)

        # Arrange vertically
        entries.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        entries.move_to([0, -0.3, 0])

        for entry in entries:
            self.play(FadeIn(entry), run_time=0.5)
            self.wait(wait_per)

        self.wait(1.0)


class PartitionTable(Scene):
    """Display a formatted table of n vs p(n)."""

    def construct(self):
        params = load_params()
        duration = params.get("duration", 15)
        highlight_color = params.get("highlight_color", ACCENT_GOLD)

        rows = [
            ["1", "1"],
            ["2", "2"],
            ["3", "3"],
            ["4", "5"],
            ["5", "7"],
            ["10", "42"],
            ["50", "204,226"],
            ["100", "190,569,292"],
        ]

        table = Table(
            rows,
            col_labels=[
                MathTex("n", font_size=28),
                MathTex("p(n)", font_size=28),
            ],
            include_outer_lines=True,
            line_config={"color": TEXT_DIM, "stroke_width": 1},
        )
        table.scale(0.6)
        table.move_to([0, 0.3, 0])

        # Color p(n) column
        for i in range(len(rows)):
            entry = table.get_entries((i + 2, 2))
            entry.set_color(highlight_color)

        title = Text("n", font=FONT, font_size=18, color=TEXT_DIM)

        self.play(FadeIn(table), run_time=1.5)
        wait_time = max(1.0, duration - 3)
        self.wait(wait_time)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "small_n": {"people": [], "years": []},
    "growth": {"people": [], "years": []},
    "table": {"people": [], "years": []},
}



# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
SCENES = {
    "small_n": PartitionSmallN,
    "growth": PartitionGrowth,
    "table": PartitionTable,
}
