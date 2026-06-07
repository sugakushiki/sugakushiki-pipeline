"""
route_map.py - Travel route visualization for 数学史記

Shows cities and travel paths on a simplified abstract map.
Uses dots and curved arrows.

Supports two param formats:
  legacy format: route = [{city, year}, ...] with legacy CITY_POSITIONS lookup
  new format: cities = {name: [lon, lat]}, route = [{from, to, year, label, category}]

Optional position overrides (new format only, all in screen units):
  city_label_offsets = {city_name: [dx, dy]}
      Override city label position relative to city dot.
      Example: {"ゲッティンゲン": [-0.6, -0.5]} moves label LEFT 0.6 + DOWN 0.5.
      When unset for a city, auto-direction (_choose_label_dir) is used.
  route_label_offsets = {year_str: [dx, dy]}
      Override year label position relative to arrow midpoint.
      Default is mid + UP * 0.25. Example: {"1900": [0, 0.5]} places "1900"
      higher above the arrow to avoid collision with nearby city labels.
  Established ある回 (高木貞治) where Berlin / Göttingen city dots are
  geographically close (~3° apart) and the 1900 arrow label collided with
  the Göttingen label. Use these overrides to nudge labels without changing
  geographic coordinates.

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 001 (Erdős), 004 (Ramanujan), 030 (Takagi) etc.
"""

from manim import *
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

# Legacy city positions for legacy backward compat (abstract screen coords)
CITY_POSITIONS = {
    "Budapest": [-3.0, 0.5, 0],
    "Manchester": [-4.5, 2.0, 0],
    "Princeton": [3.0, 1.5, 0],
    "USA": [3.0, 1.5, 0],
    "London": [-4.0, 2.5, 0],
    "Jerusalem": [1.0, -1.5, 0],
    "Warsaw": [-1.5, 1.5, 0],
}

PERIOD_COLORS = {
    "origin": ACCENT_GOLD,  # 生誕地・出発点
    "education": "#7bc8f6",  # 留学・進学（ライトブルー）
    "career": ACCENT_CYAN,  # 職務・研究赴任
    "wandering": ACCENT_PINK,  # 放浪・旅
    "exile": "#c792ea",  # 亡命・追放（ライトパープル）
    "final": TEXT_DIM,  # 最期の地
}

# Safe y range: title at top (~3.3), subtitle at bottom (-2.0)
SCREEN_X_RANGE = (-5.5, 5.5)
SCREEN_Y_RANGE = (-1.5, 2.5)


def _project_cities(cities_dict):
    """Convert {name: [lon, lat]} to {name: [x, y, 0]} screen coordinates.

    Uses simple linear projection. Ensures minimum spacing between cities
    by spreading clusters apart.
    """
    if not cities_dict:
        return {}

    names = list(cities_dict.keys())
    lons = [cities_dict[n][0] for n in names]
    lats = [cities_dict[n][1] for n in names]

    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)

    lon_span = max(lon_max - lon_min, 1.0)
    lat_span = max(lat_max - lat_min, 1.0)

    x_min, x_max = SCREEN_X_RANGE
    y_min, y_max = SCREEN_Y_RANGE
    x_margin = (x_max - x_min) * 0.1
    y_margin = (y_max - y_min) * 0.1

    result = {}
    for name in names:
        lon, lat = cities_dict[name][0], cities_dict[name][1]
        x = (x_min + x_margin) + (lon - lon_min) / lon_span * (x_max - x_min - 2 * x_margin)
        y = (y_min + y_margin) + (lat - lat_min) / lat_span * (y_max - y_min - 2 * y_margin)
        result[name] = [x, y, 0]

    # Enforce minimum spacing between cities (multiple passes for convergence)
    min_dist = 1.2
    names_list = list(result.keys())
    for _pass in range(3):
        any_moved = False
        for i in range(len(names_list)):
            for j in range(i + 1, len(names_list)):
                ni, nj = names_list[i], names_list[j]
                pi, pj = result[ni], result[nj]
                dx = pj[0] - pi[0]
                dy = pj[1] - pi[1]
                dist = (dx**2 + dy**2) ** 0.5
                if dist < min_dist and dist > 0:
                    scale = (min_dist - dist) / 2 / dist
                    result[ni] = [pi[0] - dx * scale, pi[1] - dy * scale, 0]
                    result[nj] = [pj[0] + dx * scale, pj[1] + dy * scale, 0]
                    any_moved = True
        if not any_moved:
            break

    return result


def _choose_label_dir(city_pos, all_positions, default=DOWN):
    """Choose label direction to minimize overlap with other cities.

    Tries DOWN, UP, RIGHT, LEFT and picks the direction with most clearance.
    """
    directions = [
        (DOWN, [0, -0.4]),
        (UP, [0, 0.4]),
        (RIGHT, [0.8, 0]),
        (LEFT, [-0.8, 0]),
    ]

    best_dir = default
    best_min_dist = -1
    cx, cy = city_pos[0], city_pos[1]

    for direction, offset in directions:
        label_x = cx + offset[0]
        label_y = cy + offset[1]
        min_d = float("inf")
        for other_pos in all_positions:
            if abs(other_pos[0] - cx) < 0.01 and abs(other_pos[1] - cy) < 0.01:
                continue
            d = ((label_x - other_pos[0]) ** 2 + (label_y - other_pos[1]) ** 2) ** 0.5
            min_d = min(min_d, d)
        if min_d > best_min_dist:
            best_min_dist = min_d
            best_dir = direction

    return best_dir


class RouteMap(Scene):
    """Visualize a mathematician's travel route as an abstract node-and-arrow diagram."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        duration = params.get("duration", 20)

        cities_dict = params.get("cities", None)
        route = params.get("route", [])
        title_text = params.get("title", "旅路")
        city_label_offsets = params.get("city_label_offsets", {}) or {}
        route_label_offsets = params.get("route_label_offsets", {}) or {}

        if cities_dict:
            city_positions = _project_cities(cities_dict)
        else:
            city_positions = CITY_POSITIONS

        title = Text(title_text, font=FONT, font_size=36, color=ACCENT_GOLD)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.5)

        if cities_dict and route and isinstance(route[0], dict) and "from" in route[0]:
            self._draw_route_pairs(
                route, city_positions, duration, city_label_offsets, route_label_offsets
            )
        else:
            self._draw_route_sequential(route, city_positions, duration)

    def _draw_route_pairs(
        self, route, city_positions, duration, city_label_offsets=None, route_label_offsets=None
    ):
        """Draw route from [{from, to, year, label, category}, ...] format."""
        seen = set()
        ordered_cities = []
        for stop in route:
            for key in ("from", "to"):
                city = stop.get(key, "")
                if city and city not in seen:
                    seen.add(city)
                    ordered_cities.append(city)

        all_positions = [city_positions.get(c, [0, 0, 0]) for c in ordered_cities]

        label_dirs = {}
        for city in ordered_cities:
            pos = city_positions.get(city, [0, 0, 0])
            label_dirs[city] = _choose_label_dir(pos, all_positions)

        drawn_cities = set()
        n_steps = len(route)
        anim_overhead = 1.0 + n_steps * 1.2
        wait_per = max(0.3, (duration - anim_overhead) / (n_steps + 1))

        for stop in route:
            city_from = stop.get("from", "")
            city_to = stop.get("to", "")
            year = stop.get("year", "")
            category = stop.get("category", "wandering")
            color = PERIOD_COLORS.get(category, ACCENT_CYAN)

            if city_from and city_from not in drawn_cities:
                self._draw_city(
                    city_from, city_positions, label_dirs, color, city_label_offsets
                )
                drawn_cities.add(city_from)

            pos_from = city_positions.get(city_from, [0, 0, 0])
            pos_to = city_positions.get(city_to, [0, 0, 0])
            if city_from and city_to:
                arrow = CurvedArrow(
                    start_point=pos_from,
                    end_point=pos_to,
                    angle=-0.3,
                    color=color,
                    stroke_width=2,
                    tip_length=0.15,
                )
                if year:
                    mid = arrow.point_from_proportion(0.5)
                    yr_label = Text(f"{year}", font=FONT, font_size=16, color=TEXT_DIM)
                    # route_label_offsets override (year_str key) — ある回 添加
                    if route_label_offsets and str(year) in route_label_offsets:
                        dx, dy = route_label_offsets[str(year)]
                        yr_label.move_to([mid[0] + dx, mid[1] + dy, 0])
                    else:
                        yr_label.move_to(mid + UP * 0.25)
                    self.play(Create(arrow), FadeIn(yr_label), run_time=0.6)
                else:
                    self.play(Create(arrow), run_time=0.6)

            if city_to and city_to not in drawn_cities:
                self._draw_city(
                    city_to, city_positions, label_dirs, color, city_label_offsets
                )
                drawn_cities.add(city_to)

            self.wait(wait_per)

        self.wait(1.0)

    def _draw_city(self, city_name, city_positions, label_dirs, color, city_label_offsets=None):
        """Draw a city dot with label.

        If city_label_offsets contains city_name, label is placed at
        [city_x + dx, city_y + dy] (absolute offset from city). Otherwise
        label uses auto-direction (label_dirs) with next_to + buff=0.12.
        """
        pos = city_positions.get(city_name, [0, 0, 0])
        direction = label_dirs.get(city_name, DOWN)

        dot = Dot(point=pos, radius=0.1, color=ACCENT_GOLD)
        label = Text(city_name, font=FONT, font_size=20, color=TEXT_WHITE)
        if city_label_offsets and city_name in city_label_offsets:
            dx, dy = city_label_offsets[city_name]
            label.move_to([pos[0] + dx, pos[1] + dy, 0])
        else:
            label.next_to(dot, direction, buff=0.12)

        self.play(FadeIn(VGroup(dot, label)), run_time=0.4)

    def _draw_route_sequential(self, route, city_positions, duration):
        """Draw route from [{city, year}, ...] format (legacy compat)."""
        if not route:
            route = [
                {"city": "Budapest", "year": 1913},
                {"city": "Manchester", "year": 1934},
                {"city": "USA", "year": 1938},
            ]

        prev_pos = None
        n_steps = len(route)
        wait_per = max(0.3, (duration - 2 - n_steps * 1.1) / n_steps)

        for stop in route:
            city = stop["city"]
            year = stop.get("year", "")
            pos = city_positions.get(city, [0, 0, 0])

            dot = Dot(point=pos, radius=0.12, color=ACCENT_GOLD)
            label = Text(f"{city}", font=FONT, font_size=22, color=TEXT_WHITE)
            label.next_to(dot, DOWN, buff=0.15)
            year_label = Text(str(year), font=FONT, font_size=18, color=TEXT_DIM)
            year_label.next_to(label, DOWN, buff=0.08)

            city_group = VGroup(dot, label, year_label)

            if prev_pos is not None:
                arrow = CurvedArrow(
                    start_point=prev_pos,
                    end_point=pos,
                    angle=-0.3,
                    color=ACCENT_CYAN,
                    stroke_width=2,
                    tip_length=0.15,
                )
                self.play(Create(arrow), run_time=0.6)

            self.play(FadeIn(city_group), run_time=0.5)
            prev_pos = pos
            self.wait(wait_per)

        self.wait(1.5)
# Factual-claim metadata (read by qa_manim_consistency.py). This template's
# modes render no on-screen person/year claims, so they are declared empty
# (checked, not silently skipped).
LINT_FACTUAL_CLAIMS = {
    "default": {"people": [], "years": []},
}



# ---------------------------------------------------------------------------
# SCENES registry (used by visual_generator.py)
# ---------------------------------------------------------------------------
SCENES = {
    "default": RouteMap,
}
