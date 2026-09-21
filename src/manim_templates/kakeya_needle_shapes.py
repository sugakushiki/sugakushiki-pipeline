"""
kakeya_needle_shapes.py - the shrinking staircase of the Kakeya needle
problem, and the one word that ends it

A unit segment has to be turned through a full turn without leaving the
region. How small can the region be? The four candidates that appeared in
Sendai in November 1916 and in the five years after it are drawn here at
one and the same scale, each with the needle actually turning inside it:

    circle of diameter 1      pi/4        ~ 0.785   (the obvious start)
    Reuleaux triangle         (pi-sqrt3)/2 ~ 0.705  (Kakeya's own answer)
    equilateral triangle,
      height 1                1/sqrt3     ~ 0.577   (Fujiwara's)
    deltoid                   pi/8        ~ 0.393   (Kubota's)

The first three are convex; the deltoid is not. That single dropped word
is the hinge of the whole episode, so mode 'convexity' shows it directly:
a chord of the triangle never leaves the triangle, a chord of the deltoid
does.

Every motion here is the true one, checked numerically before the
template was written, not an approximation drawn by eye:

  circle    - the needle is a diameter and turns about the centre.
  reuleaux  - the needle pivots about one vertex through 60 degrees, from
              one neighbouring vertex to the other; its far end runs along
              the arc of radius 1 centred on the pivot, which IS the
              opposite edge of the region. Three such pivots turn it by
              180 degrees, six by a full turn.
  triangle  - for a direction u, the set of positions of the needle that
              stay inside the triangle is T intersect (T - u), a convex
              polygon; the needle is placed at that polygon's centroid, so
              the motion is continuous and provably inside. The polygon is
              non-empty for every direction because the triangle's minimal
              width is exactly the height, 1.
  deltoid   - with the deltoid P(t) = (2r cos t + r cos 2t,
              2r sin t - r sin 2t) and r = 1/4, the segment from
              P(pi - s) to P(-s) has length exactly 4r = 1 for every s, it
              lies inside the region, and its direction turns once as s
              runs over a full turn. (It is the tangent chord: the tangent
              at parameter t is met again at pi - t/2 and -t/2.)

SINGLE Scene class with mode dispatch inside construct().

Modes:
    delta_curve - What Fujiwara was holding: a convex curve that turns inside
                the equilateral triangle while touching all three sides at
                once (a delta curve). Since the triangle's three inward
                normals are 120 degrees apart, Viviani's theorem makes the
                condition exact: a convex curve does this iff its support
                function satisfies h(p) + h(p+120) + h(p+240) = H, the
                triangle's height. The curve drawn is the classical one: a
                lens of two 60-degree arcs of radius H meeting at two
                corners, so its length is exactly the triangle's height.
                Checked before it was drawn: the support sum is H to machine
                precision and over 360 rotation angles the three tangency
                equations agree to 3e-16 while the curve stays inside.
                Fixed params: triangle of height 1, 2-arc lens of length 1
                and thickness 0.268, 3 tangency dots, one full turn.
    circle    - Diameter-1 circle, the needle turning about its centre for
                the whole scene.
                Fixed params: 1 circle, 1 needle, 1 full turn, area label
                pi/4 ~ 0.785.
    reuleaux  - The Reuleaux triangle of width 1 (three arcs of radius 1),
                the needle pivoting about the vertices.
                Fixed params: 3 arcs, 3 vertex dots, 6 pivots of 60
                degrees, area label (pi - sqrt 3)/2 ~ 0.705.
    triangle  - The equilateral triangle of height 1, the needle turning
                inside it by the centroid rule above.
                Fixed params: 1 triangle (side 2/sqrt3), 1 needle, 1 full
                turn, area label 1/sqrt3 ~ 0.577.
    deltoid   - The deltoid: first the rolling circle that generates it
                (radii 3:1), then the needle turning inside.
                Fixed params: outer circle radius 3r, rolling circle
                radius r with r = 1/4, 3 cusps, 1 full turn, area label
                pi/8 ~ 0.393.
    staircase - All four at one scale, left to right, with the area under
                each and the name of whoever put it forward.
                Fixed params: 4 shapes, scale 1.5, areas 0.785 / 0.705 /
                0.577 / 0.393; names Kakeya / Fujiwara / Kubota on the
                last three.
    convexity - What "convex" means, and which of the two has it. Left the
                triangle, right the deltoid, each with a moving chord.
                Fixed params: 2 shapes, 2 moving endpoint pairs, 1 chord
                each.

Reads params from _manim_params.json in the same directory.
"""

import numpy as np
from manim import (
    UP,
    AnimationGroup,
    Circle,
    Dot,
    FadeIn,
    Indicate,
    Line,
    MathTex,
    Polygon,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    always_redraw,
    config,
    linear,
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
    pace,
)

config.background_color = BG_COLOR

# Japanese glyphs hang ~0.17 below their centre; the subtitle band starts at -2.0.
_BOTTOM_Y = -1.75
_AREA_Y = -1.15
_TITLE_Y = 3.06

_MODES = ("delta_curve", "circle", "reuleaux", "triangle", "deltoid", "staircase", "convexity")
_DEFAULT_MODE = "staircase"
assert _DEFAULT_MODE in _MODES

# Display scale: a needle of length 1 becomes this many Manim units.
_S = 2.30
_S_ROW = 1.50

_SQRT3 = float(np.sqrt(3.0))
_DELTOID_R = 0.25  # needle length 1 == 4r


# ---------------------------------------------------------------------------
# Geometry (unit-size, centred on the origin; callers scale by _S)
# ---------------------------------------------------------------------------
def _circle_pts(n=240):
    a = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([0.5 * np.cos(a), 0.5 * np.sin(a)], axis=1)


def _reuleaux_vertices():
    """Equilateral triangle of side 1, centred on its centroid."""
    v = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, _SQRT3 / 2.0]])
    return v - v.mean(axis=0)


def _reuleaux_pts(per_arc=80):
    """Three arcs of radius 1, each centred on the opposite vertex."""
    v = _reuleaux_vertices()
    out = []
    for i in range(3):
        centre = v[i]
        start = v[(i + 1) % 3] - centre
        a0 = float(np.arctan2(start[1], start[0]))
        for a in np.linspace(a0, a0 + np.pi / 3.0, per_arc, endpoint=False):
            out.append(centre + np.array([np.cos(a), np.sin(a)]))
    return np.array(out)


def _triangle_vertices():
    """Equilateral triangle of height 1, centred on its centroid."""
    a = 2.0 / _SQRT3
    v = np.array([[0.0, 0.0], [a, 0.0], [a / 2.0, 1.0]])
    return v - v.mean(axis=0)


def _deltoid_point(t, r=_DELTOID_R):
    return np.array(
        [
            2.0 * r * np.cos(t) + r * np.cos(2.0 * t),
            2.0 * r * np.sin(t) - r * np.sin(2.0 * t),
        ]
    )


def _deltoid_pts(n=300):
    return np.array([_deltoid_point(t) for t in np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)])


def _deltoid_needle(s):
    """Endpoints of the unit tangent chord at phase s (length exactly 1)."""
    return _deltoid_point(np.pi - s), _deltoid_point(-s)


# -- the delta curve: rotates inside the triangle touching all three sides --
# The classical delta curve: a lens bounded by TWO arcs of radius equal to the
# triangle's height H, each spanning 60 degrees and meeting at two corners. Its
# length is exactly H. A convex curve can be turned inside an equilateral
# triangle touching all three sides iff its support function satisfies
# h(p) + h(p+120) + h(p+240) = H (the three inward normals are 120 degrees
# apart, so this is Viviani's theorem). Checked before it was drawn: the sum is
# H to machine precision, and over 360 rotation angles the three tangency
# equations agree to 3e-16 while the curve never leaves the triangle.
_DELTA_R = 1.0
_DELTA_C1 = np.array([0.0, -_SQRT3 / 2.0])  # centre of the upper arc
_DELTA_C2 = np.array([0.0, _SQRT3 / 2.0])  # centre of the lower arc
_DELTA_P = np.array([0.5, 0.0])  # the two corners
_DELTA_Q = np.array([-0.5, 0.0])


def _delta_support_point(p):
    """Boundary point whose outward normal points at angle p."""
    u = np.array([np.cos(p), np.sin(p)])
    pm = float(p) % (2.0 * np.pi)
    if np.pi / 3.0 <= pm <= 2.0 * np.pi / 3.0:
        return _DELTA_C1 + _DELTA_R * u
    if 4.0 * np.pi / 3.0 <= pm <= 5.0 * np.pi / 3.0:
        return _DELTA_C2 + _DELTA_R * u
    return _DELTA_P if float(_DELTA_P @ u) >= float(_DELTA_Q @ u) else _DELTA_Q


def _delta_h(p):
    u = np.array([np.cos(p), np.sin(p)])
    return float(_delta_support_point(p) @ u)


def _delta_boundary(n=360):
    pts = []
    for t in np.linspace(-np.pi / 6.0, np.pi / 6.0, n // 2):
        a = np.pi / 2.0 + t
        pts.append(_DELTA_C1 + _DELTA_R * np.array([np.cos(a), np.sin(a)]))
    for t in np.linspace(-np.pi / 6.0, np.pi / 6.0, n // 2):
        a = -np.pi / 2.0 + t
        pts.append(_DELTA_C2 + _DELTA_R * np.array([np.cos(a), np.sin(a)]))
    return np.array(pts)


def _tri_sides(tri):
    """Inward unit normals and offsets: the triangle is {x : x.n >= -a}."""
    out = []
    c = tri.mean(axis=0)
    for i in range(3):
        q, r = tri[i], tri[(i + 1) % 3]
        e = r - q
        n = np.array([-e[1], e[0]])
        n = n / float(np.linalg.norm(n))
        if float(n @ (c - q)) < 0.0:
            n = -n
        out.append((n, -float(n @ q)))
    return out


def _delta_placement(sides, theta):
    """Translation putting the theta-rotated curve tangent to all three sides."""
    rows, rhs = [], []
    for n, a in sides[:2]:
        phi = float(np.arctan2(-n[1], -n[0]))
        rows.append(n)
        rhs.append(_delta_h(phi - theta) - a)
    return np.linalg.solve(np.array(rows), np.array(rhs))


# -- the triangle motion: T intersect (T - u), then its centroid ------------
def _halfplanes(tri):
    """Inward half-planes n.x >= b of a triangle given as three 2-vectors."""
    c = tri.mean(axis=0)
    out = []
    for i in range(3):
        p, q = tri[i], tri[(i + 1) % 3]
        e = q - p
        n = np.array([-e[1], e[0]])
        if float(n @ (c - p)) < 0.0:
            n = -n
        out.append((n, float(n @ p)))
    return out


def _clip(poly, n, b):
    """Sutherland-Hodgman: keep the part of `poly` where n.x >= b."""
    out = []
    m = len(poly)
    for i in range(m):
        a = poly[i]
        c = poly[(i + 1) % m]
        da = float(n @ a - b)
        dc = float(n @ c - b)
        if da >= 0.0:
            out.append(a)
        if (da > 0.0) != (dc > 0.0) and abs(da - dc) > 1e-12:
            out.append(a + (c - a) * (da / (da - dc)))
    return out


def _polygon_centroid(poly):
    if len(poly) < 3:
        return np.mean(np.array(poly), axis=0)
    p = np.array(poly)
    q = np.roll(p, -1, axis=0)
    cross = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
    area = float(cross.sum()) / 2.0
    if abs(area) < 1e-9:
        return p.mean(axis=0)
    cx = float(((p[:, 0] + q[:, 0]) * cross).sum()) / (6.0 * area)
    cy = float(((p[:, 1] + q[:, 1]) * cross).sum()) / (6.0 * area)
    return np.array([cx, cy])


def _triangle_needle(tri, theta, fallback=None):
    """A unit needle of direction theta that fits inside `tri` (height 1)."""
    u = np.array([np.cos(theta), np.sin(theta)])
    poly = [np.array(v, dtype=float) for v in tri]
    for n, b in _halfplanes(tri - u):
        poly = _clip(poly, n, b)
        if not poly:
            break
    if not poly:
        return fallback
    tail = _polygon_centroid(poly)
    return tail, tail + u


# ---------------------------------------------------------------------------
def _to3(p, scale=1.0, shift=(0.0, 0.0)):
    return np.array([p[0] * scale + shift[0], p[1] * scale + shift[1], 0.0])


class KakeyaNeedleShapes(Scene):
    """Single class; construct() dispatches on params['mode']."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        # Unknown modes fail loudly rather than silently
        # drawing some other picture.
        mode = params.get("mode")
        if mode is not None and mode not in _MODES:
            raise ValueError(
                f"kakeya_needle_shapes: unknown mode {mode!r}. Valid modes are {'/'.join(_MODES)}."
            )
        mode = mode or _DEFAULT_MODE
        duration = params.get("duration", 28)
        if mode == "delta_curve":
            self._delta_curve(duration)
        elif mode == "circle":
            self._circle(duration)
        elif mode == "reuleaux":
            self._reuleaux(duration)
        elif mode == "triangle":
            self._triangle(duration)
        elif mode == "deltoid":
            self._deltoid(duration)
        elif mode == "convexity":
            self._convexity(duration)
        else:
            self._staircase(duration)

    # -- shared ------------------------------------------------------------
    def _title(self, s):
        t = Text(s, font=FONT, font_size=30, color=ACCENT_GOLD)
        t.move_to(UP * _TITLE_Y)
        return self._fit(t, 12.6)

    def _fit(self, m, width):
        if m.width > width:
            m.scale_to_fit_width(width)
        return m

    def _note(self, s, color=TEXT_WHITE, y=_BOTTOM_Y, font_size=28):
        t = Text(s, font=FONT, font_size=font_size, color=color)
        t.move_to(UP * y)
        return self._fit(t, 12.6)

    def _region(self, pts, scale, shift=(0.0, 0.0), color=ACCENT_CYAN, fill=0.10):
        poly = Polygon(
            *[_to3(p, scale, shift) for p in pts],
            color=color,
            stroke_width=3.0,
            fill_color=color,
            fill_opacity=fill,
        )
        return poly

    def _needle(self, a, b):
        return VGroup(
            Line(a, b, color=ACCENT_GOLD, stroke_width=6.5),
            Dot(a, radius=0.075, color=ACCENT_GOLD),
            Dot(b, radius=0.075, color=ACCENT_GOLD),
        )

    def _area_label(self, tex, y=_AREA_Y, color=ACCENT_PINK, font_size=30):
        head = Text("面積", font=FONT, font_size=font_size, color=TEXT_DIM)
        body = MathTex(tex, color=color).scale(0.95)
        g = VGroup(head, body).arrange(direction=np.array([1.0, 0.0, 0.0]), buff=0.28)
        g.move_to(UP * y)
        return g

    def _reveal(self, *mobjects, run_time):
        """FadeIn, then hold; fade + rest == run_time exactly."""
        fade = min(min(max(run_time * 0.30, 0.7), 1.4), run_time)
        if run_time - fade <= 0.05:
            fade = run_time
        self.play(AnimationGroup(*[FadeIn(m, run_time=fade) for m in mobjects], lag_ratio=0.0))
        if run_time > fade:
            self.wait(run_time - fade)

    def _pulse(self, m, run_time, color, extras=()):
        """FadeIn then Indicate, as SEPARATE plays (an earlier episode: never in one group)."""
        fade = min(0.9, run_time)
        self.play(AnimationGroup(*[FadeIn(x) for x in (m, *extras)], lag_ratio=0.0), run_time=fade)
        rest = run_time - fade
        if rest > 0.05:
            ind = min(1.5, rest)
            self.play(Indicate(m, color=color), run_time=ind)
            if rest - ind > 0.05:
                self.wait(rest - ind)

    def _turn(self, tracker, motion, reveals):
        """Run the needle for `motion` seconds, folding label reveals into the
        same span so the picture never stops moving (anti-pattern)."""
        if not reveals:
            self.play(tracker.animate.set_value(1.0), run_time=motion, rate_func=linear)
            return
        share = motion / (len(reveals) + 1)
        done = 0.0
        for i, group in enumerate(reveals, start=1):
            target = i / (len(reveals) + 1)
            self.play(
                AnimationGroup(
                    tracker.animate.set_value(target),
                    *[FadeIn(m) for m in group],
                    lag_ratio=0.0,
                ),
                run_time=share,
                rate_func=linear,
            )
            done = target
        self.play(
            tracker.animate.set_value(1.0),
            run_time=motion - share * len(reveals),
            rate_func=linear,
        )
        _ = done

    # -- mode: delta_curve -------------------------------------------------
    def _delta_curve(self, duration):
        title = self._title("三角形の中で、回る図形")
        shift = (0.0, 0.72)
        tri = _triangle_vertices()
        sides = _tri_sides(tri)
        region = Polygon(
            *[_to3(q, _S, shift) for q in tri],
            color=TEXT_DIM,
            stroke_width=3.0,
            fill_color=ACCENT_CYAN,
            fill_opacity=0.05,
        )
        base = _delta_boundary()

        tau = ValueTracker(0.0)

        def _curve_now():
            th = 2.0 * np.pi * tau.get_value()
            rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
            c = _delta_placement(sides, th)
            pts = (rot @ base.T).T + c
            body = Polygon(
                *[_to3(q, _S, shift) for q in pts],
                color=ACCENT_GOLD,
                stroke_width=4.0,
                fill_color=ACCENT_GOLD,
                fill_opacity=0.16,
            )
            dots = VGroup()
            for n, _a in sides:
                phi = float(np.arctan2(-n[1], -n[0]))
                q = rot @ _delta_support_point(phi - th) + c
                dots.add(Dot(_to3(q, _S, shift), radius=0.065, color=ACCENT_PINK))
            return VGroup(body, dots)

        shape = always_redraw(_curve_now)
        lab = Text("正三角形の内転形", font=FONT, font_size=27, color=ACCENT_GOLD)
        lab.move_to(np.array([-4.15, 2.15, 0.0]))
        touch = Text("三辺に触れたまま", font=FONT, font_size=25, color=ACCENT_PINK)
        touch.move_to(np.array([4.05, 2.15, 0.0]))
        note = self._note("回しても、三つの接点は離れません", color=TEXT_DIM)

        CODA = 2.2
        setup = 2.4
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(region), run_time=0.7)
        self.add(shape)
        self.wait(0.6)  # always_redraw: FadeIn cannot show
        motion = max(3.0, duration - setup - CODA)
        self._turn(tau, motion, [(lab,), (touch,), (note,)])
        self.wait(CODA)

    # -- mode: circle ------------------------------------------------------
    def _circle(self, duration):
        title = self._title("いちばん素直な答え")
        centre = np.array([0.0, 0.72, 0.0])
        ring = Circle(radius=0.5 * _S, color=ACCENT_CYAN, stroke_width=3.0)
        ring.set_fill(ACCENT_CYAN, opacity=0.10)
        ring.move_to(centre)
        hub = Dot(centre, radius=0.06, color=TEXT_DIM)

        tau = ValueTracker(0.0)

        def _needle_now():
            th = 2.0 * np.pi * tau.get_value()
            u = np.array([np.cos(th), np.sin(th), 0.0])
            return self._needle(centre - 0.5 * _S * u, centre + 0.5 * _S * u)

        needle = always_redraw(_needle_now)
        diam = Text("直径 1", font=FONT, font_size=26, color=TEXT_DIM)
        diam.move_to(np.array([3.55, 0.72, 0.0]))
        area = self._area_label(r"\pi/4 \approx 0.785")
        note = self._note("長さ 1 の針は、まん中を軸にして回れます", color=TEXT_DIM)

        CODA = 2.2
        setup = 2.4
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(ring), FadeIn(hub), run_time=0.7)
        self.add(needle)
        self.wait(0.6)  # always_redraw: FadeIn cannot show (updater rebuilds each frame)
        motion = max(3.0, duration - setup - CODA)
        self._turn(tau, motion, [(diam,), (area,), (note,)])
        self.wait(CODA)

    # -- mode: reuleaux ----------------------------------------------------
    def _reuleaux(self, duration):
        title = self._title("掛谷が書きとめた答え")
        shift = (0.0, 0.72)
        v = _reuleaux_vertices()
        region = self._region(_reuleaux_pts(), _S, shift, color=ACCENT_CYAN)
        corners = VGroup(*[Dot(_to3(p, _S, shift), radius=0.07, color=TEXT_DIM) for p in v])

        # (pivot, from, to) -- each step turns the needle by exactly 60 degrees.
        seq = ((0, 1, 2), (2, 0, 1), (1, 2, 0))
        tau = ValueTracker(0.0)

        def _needle_now():
            phase = 6.0 * tau.get_value()
            k = int(np.floor(phase)) % 3
            f = phase - np.floor(phase)
            pv, a, b = seq[k]
            p = v[pv]
            a0 = np.arctan2(*(v[a] - p)[::-1])
            ang = a0 + f * (np.pi / 3.0)
            tip = p + np.array([np.cos(ang), np.sin(ang)])
            _ = b
            return self._needle(_to3(p, _S, shift), _to3(tip, _S, shift))

        needle = always_redraw(_needle_now)
        lab = Text("ルーローの三角形", font=FONT, font_size=27, color=ACCENT_CYAN)
        lab.move_to(np.array([-4.15, 2.15, 0.0]))
        width = Text("幅はどこで測っても 1", font=FONT, font_size=24, color=TEXT_DIM)
        width.move_to(np.array([3.88, 2.15, 0.0]))
        area = self._area_label(r"(\pi-\sqrt{3})/2 \approx 0.705")
        note = self._note("角を軸に 60 度ずつ、三回で半回転", color=TEXT_DIM)

        CODA = 2.2
        setup = 2.4
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(region), FadeIn(corners), run_time=0.7)
        self.add(needle)
        self.wait(0.6)  # always_redraw: FadeIn cannot show (updater rebuilds each frame)
        motion = max(3.0, duration - setup - CODA)
        self._turn(tau, motion, [(lab,), (width,), (area,), (note,)])
        self.wait(CODA)

    # -- mode: triangle ----------------------------------------------------
    def _triangle(self, duration):
        title = self._title("もっと狭くできる")
        shift = (0.0, 0.72)
        tri = _triangle_vertices()
        region = self._region(tri, _S, shift, color=ACCENT_CYAN)
        h_line = Line(
            _to3(np.array([tri[2][0], tri[0][1]]), _S, shift),
            _to3(tri[2], _S, shift),
            color=TEXT_DIM,
            stroke_width=2.0,
        )
        h_lab = Text("高さ 1", font=FONT, font_size=25, color=TEXT_DIM)
        h_lab.move_to(np.array([0.95, 1.0, 0.0]))

        tau = ValueTracker(0.0)
        state = {"last": None}

        def _needle_now():
            th = 2.0 * np.pi * tau.get_value()
            got = _triangle_needle(tri, th, fallback=state["last"])
            if got is None:
                got = _triangle_needle(tri, th + 1e-3, fallback=None)
            if got is None:
                got = (np.array([0.0, 0.0]), np.array([1.0, 0.0]))
            state["last"] = got
            a, b = got
            return self._needle(_to3(a, _S, shift), _to3(b, _S, shift))

        needle = always_redraw(_needle_now)
        lab = Text("高さ 1 の正三角形", font=FONT, font_size=27, color=ACCENT_CYAN)
        lab.move_to(np.array([-4.1, 2.15, 0.0]))
        area = self._area_label(r"1/\sqrt{3} \approx 0.577")
        note = self._note("辺をすべらせながら、針は向きを変えていきます", color=TEXT_DIM)

        CODA = 2.2
        setup = 2.4
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(region), run_time=0.7)
        self.add(needle)
        self.wait(0.6)  # always_redraw: FadeIn cannot show (updater rebuilds each frame)
        motion = max(3.0, duration - setup - CODA)
        self._turn(tau, motion, [(lab,), (h_line, h_lab), (area,), (note,)])
        self.wait(CODA)

    # -- mode: deltoid -----------------------------------------------------
    def _deltoid(self, duration):
        title = self._title("凸をやめると、こうなる")
        shift = (0.0, 0.72)
        r = _DELTOID_R
        region = self._region(_deltoid_pts(), _S, shift, color=ACCENT_PINK, fill=0.10)
        outer = Circle(radius=3.0 * r * _S, color=EDGE_COLOR, stroke_width=1.8)
        outer.move_to(_to3(np.array([0.0, 0.0]), _S, shift))

        roll = ValueTracker(0.0)

        def _roller():
            t = 2.0 * np.pi * roll.get_value()
            c = np.array([2.0 * r * np.cos(t), 2.0 * r * np.sin(t)])
            small = Circle(radius=r * _S, color=TEXT_DIM, stroke_width=1.8)
            small.move_to(_to3(c, _S, shift))
            p = _deltoid_point(t)
            return VGroup(small, Dot(_to3(p, _S, shift), radius=0.075, color=ACCENT_PINK))

        roller = always_redraw(_roller)

        def _trace():
            """The curve as it is drawn, so the rolling phase actually shows the
            deltoid appear instead of two bare circles."""
            end = max(2.0 * np.pi * roll.get_value(), 1e-3)
            n = max(4, int(240 * roll.get_value()) + 4)
            pts = [_to3(_deltoid_point(t), _S, shift) for t in np.linspace(0.0, end, n)]
            m = VMobject(color=ACCENT_PINK, stroke_width=3.0)
            m.set_points_as_corners(pts)
            return m

        trace = always_redraw(_trace)

        tau = ValueTracker(0.0)

        def _needle_now():
            s = -2.0 * np.pi * tau.get_value()
            a, b = _deltoid_needle(s)
            return self._needle(_to3(a, _S, shift), _to3(b, _S, shift))

        needle = always_redraw(_needle_now)
        lab = Text("デルトイド", font=FONT, font_size=28, color=ACCENT_PINK)
        lab.move_to(np.array([-4.3, 2.15, 0.0]))
        gen = Text("半径 3 対 1 で内側を転がした跡", font=FONT, font_size=24, color=TEXT_DIM)
        gen.move_to(np.array([3.20, 2.18, 0.0]))
        area = self._area_label(r"\pi/8 \approx 0.393", y=-1.20)
        note = self._note("針の両端は、へこんだ縁の上をすべります", color=TEXT_DIM)

        CODA = 2.2
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(outer), FadeIn(gen), run_time=0.5)
        self.add(trace, roller)
        self.wait(0.5)  # always_redraw: FadeIn cannot show
        # First draw the curve by rolling, then turn the needle inside it.
        rt = pace(duration, [1.5, 0.5, 2.6], intro=2.1, coda=CODA)
        self.play(roll.animate.set_value(1.0), run_time=rt[0], rate_func=linear)
        # The scaffolding has done its job; drop it so the region has room.
        self.remove(roller, trace, outer)
        self.play(AnimationGroup(FadeIn(region), FadeIn(lab), lag_ratio=0.0), run_time=rt[1])
        self.add(needle)
        self._turn(tau, rt[2], [(area,), (note,)])
        self.wait(CODA)

    # -- mode: staircase ---------------------------------------------------
    def _staircase(self, duration):
        title = self._title("同じ縮尺で並べる")
        row_y = 1.30
        specs = (
            (_circle_pts(), ACCENT_CYAN, r"\dfrac{\pi}{4} \approx 0.785", "円", ""),
            (
                _reuleaux_pts(),
                ACCENT_CYAN,
                r"\dfrac{\pi-\sqrt{3}}{2} \approx 0.705",
                "ルーローの三角形",
                "掛谷",
            ),
            (
                _triangle_vertices(),
                ACCENT_CYAN,
                r"\dfrac{1}{\sqrt{3}} \approx 0.577",
                "正三角形",
                "藤原",
            ),
            (_deltoid_pts(), ACCENT_PINK, r"\dfrac{\pi}{8} \approx 0.393", "デルトイド", "窪田"),
        )
        xs = (-5.05, -1.72, 1.62, 4.95)

        shapes, values, names = [], [], []
        for (pts, color, tex, name, who), x in zip(specs, xs, strict=True):
            shapes.append(self._region(pts, _S_ROW, (x, row_y), color=color))
            val = MathTex(tex, color=color).scale(0.72)
            val.move_to(np.array([x, -0.32, 0.0]))
            values.append(val)
            # Shape name and the person who put it forward go on ONE line: two
            # stacked lines left no room above the closing note and the two
            # collided in the rendered frame.
            nm = Text(name, font=FONT, font_size=23, color=TEXT_WHITE)
            if who:
                wh = Text(who, font=FONT, font_size=23, color=ACCENT_GOLD)
                row = VGroup(nm, wh).arrange(direction=np.array([1.0, 0.0, 0.0]), buff=0.22)
            else:
                row = VGroup(nm)
            row.move_to(np.array([x, -1.00, 0.0]))
            names.append(self._fit(row, 3.20))

        note = self._note("左から右へ、狭くなっていきます", color=ACCENT_GOLD)

        CODA = 2.6
        weights = [1.0, 0.35, 1.0, 0.35, 1.0, 0.35, 1.15, 0.45, 0.9]
        rt = pace(duration, weights, intro=1.1, coda=CODA)
        self.play(FadeIn(title), run_time=1.1)
        k = 0
        for i in range(4):
            extras = [values[i], names[i]]
            self._reveal(shapes[i], run_time=rt[k])
            k += 1
            self._reveal(*extras, run_time=rt[k])
            k += 1
        self._reveal(note, run_time=rt[k])
        self.wait(CODA)

    # -- mode: convexity ---------------------------------------------------
    def _convexity(self, duration):
        title = self._title("「凸」とは、へこみがないこと")
        scale = 1.95
        left = (-3.45, 0.72)
        right = (3.45, 0.72)
        tri = _triangle_vertices()
        tri_region = self._region(tri, scale, left, color=ACCENT_CYAN)
        del_region = self._region(_deltoid_pts(), scale, right, color=ACCENT_PINK)

        tau = ValueTracker(0.0)

        def _tri_chord():
            t = tau.get_value()
            a = _tri_boundary(tri, t * 0.85 + 0.05)
            b = _tri_boundary(tri, t * 0.85 + 0.47)
            return VGroup(
                Line(
                    _to3(a, scale, left),
                    _to3(b, scale, left),
                    color=ACCENT_GOLD,
                    stroke_width=5.0,
                ),
                Dot(_to3(a, scale, left), radius=0.07, color=ACCENT_GOLD),
                Dot(_to3(b, scale, left), radius=0.07, color=ACCENT_GOLD),
            )

        def _del_chord():
            # BOTH endpoints on the SAME concave arc (cusps sit at 0, 2pi/3,
            # 4pi/3), so the straight chord lies entirely OUTSIDE the region --
            # which is what the label claims. Checked numerically: the fraction
            # of the chord outside is 1.000 at every position of the sweep.
            # (A chord between DIFFERENT arcs runs through the inside, which is
            # what the first draft drew: the picture then contradicted the label.)
            t = tau.get_value()
            lo = 0.06 + 0.33 * t
            a = _deltoid_point(2.0 * np.pi / 3.0 * lo)
            b = _deltoid_point(2.0 * np.pi / 3.0 * (lo + 0.55))
            return VGroup(
                Line(
                    _to3(a, scale, right),
                    _to3(b, scale, right),
                    color=ACCENT_GOLD,
                    stroke_width=5.0,
                ),
                Dot(_to3(a, scale, right), radius=0.07, color=ACCENT_GOLD),
                Dot(_to3(b, scale, right), radius=0.07, color=ACCENT_GOLD),
            )

        tri_chord = always_redraw(_tri_chord)
        del_chord = always_redraw(_del_chord)

        lab_l = Text("凸", font=FONT, font_size=32, color=ACCENT_CYAN)
        lab_l.move_to(np.array([left[0], 2.42, 0.0]))
        lab_r = Text("凸でない", font=FONT, font_size=32, color=ACCENT_PINK)
        lab_r.move_to(np.array([right[0], 2.42, 0.0]))
        sub_l = Text("二点を結ぶ線は外に出ない", font=FONT, font_size=24, color=TEXT_DIM)
        sub_l.move_to(np.array([left[0], -1.12, 0.0]))
        sub_r = Text("外に出てしまう", font=FONT, font_size=24, color=TEXT_DIM)
        sub_r.move_to(np.array([right[0], -1.12, 0.0]))
        note = self._note("掛谷が問うたのは、左だけの世界でした", color=ACCENT_GOLD)

        CODA = 2.4
        setup = 2.6
        self.play(FadeIn(title), run_time=1.1)
        self.play(FadeIn(tri_region), FadeIn(del_region), run_time=0.9)
        self.add(tri_chord, del_chord)
        self.wait(0.6)  # always_redraw: FadeIn cannot show
        motion = max(3.0, duration - setup - CODA)
        self._turn(tau, motion, [(lab_l, lab_r), (sub_l, sub_r), (note,)])
        self.wait(CODA)


def _tri_boundary(tri, t):
    """Point at fraction t of the way round the triangle's perimeter."""
    t = float(t) % 1.0
    seg = np.array([np.linalg.norm(tri[(i + 1) % 3] - tri[i]) for i in range(3)])
    cum = np.cumsum(seg) / seg.sum()
    for i in range(3):
        lo = 0.0 if i == 0 else cum[i - 1]
        if t <= cum[i]:
            f = (t - lo) / (cum[i] - lo)
            return tri[i] + (tri[(i + 1) % 3] - tri[i]) * f
    return tri[0]


# What each mode puts on screen (read by qa_manim_consistency's
# narration-vs-visual check).
LINT_VISUAL_ELEMENTS = {
    "delta_curve": ["三角形", "曲線", "点"],
    "circle": ["円", "線", "点"],
    "reuleaux": ["弧", "線", "点"],
    "triangle": ["三角形", "線", "点"],
    "deltoid": ["円", "曲線", "線", "点"],
    "staircase": ["円", "三角形", "曲線"],
    "convexity": ["三角形", "曲線", "線", "点"],
}

# Only 'staircase' puts names on screen; no years appear in any mode.
LINT_FACTUAL_CLAIMS = {
    "delta_curve": {"people": [], "years": []},
    "circle": {"people": [], "years": []},
    "reuleaux": {"people": [], "years": []},
    "triangle": {"people": [], "years": []},
    "deltoid": {"people": [], "years": []},
    "staircase": {
        "people": [["掛谷", "Kakeya"], ["藤原", "Fujiwara"], ["窪田", "Kubota"]],
        "years": [],
    },
    "convexity": {"people": [], "years": []},
}


# =========================================================
# Entry point for pipeline. ONE class handles all modes (dispatch inside
# construct); SCENES maps every mode to it so the QA tools resolve correctly.
# =========================================================
SCENES = dict.fromkeys(_MODES, KakeyaNeedleShapes)
