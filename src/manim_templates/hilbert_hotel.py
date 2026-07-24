"""
hilbert_hotel.py - Hilbert's infinite hotel for 数学史記

Visualizes Hilbert's Grand Hotel paradox of countable infinity: a fully
occupied hotel with infinitely many rooms can still take in more guests.

Modes:
    shift_one - One new guest arrives; every guest moves from room n to room
                n+1, freeing room 1.
                Fixed params: 5 visible rooms + ellipsis, guests shift right.
    double    - Infinitely many new guests arrive; every guest moves from
                room n to room 2n, freeing all odd-numbered rooms.
                Fixed params: 5 visible rooms, guest n -> room 2n.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 038 (Hilbert), the infinite-optimism beat.
Source: Hilbert's 1924 lecture (unpublished), popularized by Gamow (1947).
"""

import numpy as np
from manim import (
    Dot,
    FadeIn,
    FadeOut,
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
    EDGE_COLOR,
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR

ROOM_Y = 0.4
ROOM_W = 1.4
ROOM_H = 1.1
ROOM_CENTERS = [-3.1, -1.55, 0.0, 1.55, 3.1]
ELLIPSIS_X = 4.3


def _calc_wait_scale(duration, anim_time, default_wait_total):
    """Calculate wait time multiplier to fill target duration."""
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class HilbertHotel(Scene):
    """Hilbert's Grand Hotel. Mode-branching scene."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        self._duration = params.get("duration", 25)
        mode = params.get("mode", "shift_one")
        if mode == "double":
            self.build_double()
        else:
            self.build_shift_one()

    def _build_hotel(self):
        rooms = VGroup()
        labels = VGroup()
        for i, cx in enumerate(ROOM_CENTERS):
            room = Rectangle(
                width=ROOM_W,
                height=ROOM_H,
                color=EDGE_COLOR,
                stroke_width=2.5,
                fill_color="#22223a",
                fill_opacity=0.6,
            )
            room.move_to(np.array([cx, ROOM_Y, 0]))
            rooms.add(room)
            num = MathTex(str(i + 1), font_size=26, color=TEXT_DIM)
            num.move_to(np.array([cx, ROOM_Y + ROOM_H / 2 + 0.3, 0]))
            labels.add(num)
        ellipsis = MathTex(r"\cdots", font_size=34, color=TEXT_DIM)
        ellipsis.move_to(np.array([ELLIPSIS_X, ROOM_Y, 0]))
        return rooms, labels, ellipsis

    def _guest(self, x, y=ROOM_Y, color=ACCENT_CYAN):
        return Dot(np.array([x, y, 0]), radius=0.17, color=color)

    # -------------------------------------------------------------------
    # Mode: shift_one
    # -------------------------------------------------------------------
    def build_shift_one(self):
        dur = self._duration
        title = Text("満室でも、もう一人泊められる", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to(np.array([0, 3.0, 0]))
        rooms, labels, ellipsis = self._build_hotel()

        guests = VGroup(*[self._guest(cx) for cx in ROOM_CENTERS])
        new_guest = self._guest(-5.4, color=ACCENT_PINK)

        caption = Text(
            "全員が n号室から n+1号室へ移れば、1号室が空く",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        caption.move_to(np.array([0, -1.5, 0]))

        total_anim = 0.6 + 1.0 + 1.0 + 0.6 + 1.6 + 0.4 + 1.0 + 0.6
        coda = 2.5
        gap = max(0.5, (dur - total_anim - coda) / 3)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(rooms), FadeIn(labels), FadeIn(ellipsis), run_time=1.0)
        self.play(FadeIn(guests), run_time=1.0)
        self.wait(gap)
        self.play(FadeIn(new_guest), run_time=0.6)
        self.wait(gap)

        # shift each guest one room right; the last one moves into the "..."
        n_rooms = len(ROOM_CENTERS)
        shifts = []
        for i in range(n_rooms):
            if i == n_rooms - 1:
                target_x = ELLIPSIS_X + 0.7
            else:
                target_x = ROOM_CENTERS[i + 1]
            shifts.append(guests[i].animate.move_to(np.array([target_x, ROOM_Y, 0])))
        self.play(*shifts, run_time=1.6)
        self.play(FadeOut(guests[n_rooms - 1]), run_time=0.4)
        self.wait(gap)
        self.play(new_guest.animate.move_to(np.array([ROOM_CENTERS[0], ROOM_Y, 0])), run_time=1.0)
        self.play(FadeIn(caption), run_time=0.6)
        self.wait(coda)

    # -------------------------------------------------------------------
    # Mode: double
    # -------------------------------------------------------------------
    def build_double(self):
        dur = self._duration
        title = Text("無限の客にも、部屋は足りる", font=FONT, font_size=28, color=ACCENT_GOLD)
        title.move_to(np.array([0, 3.0, 0]))
        rooms, labels, ellipsis = self._build_hotel()
        guests = VGroup(*[self._guest(cx) for cx in ROOM_CENTERS])

        caption = Text(
            "全員が n号室から 2n号室へ移れば、奇数室が無限に空く",
            font=FONT,
            font_size=22,
            color=TEXT_WHITE,
        )
        caption.move_to(np.array([0, -1.5, 0]))

        total_anim = 0.6 + 1.0 + 1.0 + 1.8 + 0.4 + 0.5 + 1.0 + 0.6
        coda = 2.5
        gap = max(0.5, (dur - total_anim - coda) / 3)

        self.play(FadeIn(title), run_time=0.6)
        self.play(FadeIn(rooms), FadeIn(labels), FadeIn(ellipsis), run_time=1.0)
        self.play(FadeIn(guests), run_time=1.0)
        self.wait(gap)

        # guest in room n -> room 2n; rooms beyond the visible 5 go off-screen
        n_rooms = len(ROOM_CENTERS)
        shifts = []
        fade_after = []
        for i in range(n_rooms):
            n = i + 1
            target_room = 2 * n
            if target_room <= n_rooms:
                tx = ROOM_CENTERS[target_room - 1]
            else:
                tx = ELLIPSIS_X + 0.7 + (target_room - n_rooms) * 0.04
                fade_after.append(guests[i])
            shifts.append(guests[i].animate.move_to(np.array([tx, ROOM_Y, 0])))
        self.play(*shifts, run_time=1.8)
        if fade_after:
            self.play(*[FadeOut(g) for g in fade_after], run_time=0.4)
        self.wait(gap)

        # new guests drop into the freed odd rooms 1, 3, 5
        odd_x = [ROOM_CENTERS[0], ROOM_CENTERS[2], ROOM_CENTERS[4]]
        new_guests = VGroup(*[self._guest(cx, y=2.0, color=ACCENT_PINK) for cx in odd_x])
        self.play(FadeIn(new_guests), run_time=0.5)
        self.wait(gap)
        self.play(
            *[
                g.animate.move_to(np.array([cx, ROOM_Y, 0]))
                for g, cx in zip(new_guests, odd_x, strict=False)
            ],
            run_time=1.0,
        )
        self.play(FadeIn(caption), run_time=0.6)
        self.wait(coda)


# Factual-claim metadata (read by qa_manim_consistency.py). Room numbers are
# not historical years/people; declared empty (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "shift_one": {"people": [], "years": []},
    "double": {"people": [], "years": []},
}


SCENES = {
    "shift_one": {
        "class": "HilbertHotel",
        "params": {"mode": "shift_one"},
        "description": "Infinite hotel: all guests n->n+1 free room 1",
    },
    "double": {
        "class": "HilbertHotel",
        "params": {"mode": "double"},
        "description": "Infinite hotel: all guests n->2n free all odd rooms",
    },
}
