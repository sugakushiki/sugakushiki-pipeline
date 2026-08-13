"""route_map_render.py - route_map シーンの描画とレイアウト検査 (matplotlib + Natural Earth).

`visual_generator.py` から分割した。route_map だけで約 2,300 行あり、
ken_burns / text_overlay / manim / Blender / キャッシュと同居していたため、地図を
1 か所直すたびに 4,500 行のファイルを開くことになっていた。route_map は前セッション
だけで 4 回作り直しており、最も頻繁に触るのに最も探しにくい状態だった。

含まれるもの:
  - 描画: `generate_route_map` (matplotlib で地図 PNG -> Ken Burns で動画化)
  - 幾何: 都市/ラベルの座標変換・auto-bounds の padding・Ken Burns 後の可視域
  - レイアウト検査: bbox 衝突 / 枠外見切れ / ラベルの所属 (d2/d1) / 線がラベルを貫く /
    経路ラベルの取り付き / 凡例色の識別可能性
  - 自動修正: `_apply_route_map_auto_fix_stage` (改善したときだけ採用する greedy)
  - `route_map_preflight` (pipeline が visuals step の前に起動する STOP ゲート)

分割にあたって振る舞いは変えていない。`visual_generator` は同じ名前を再輸出するので
既存の呼び出し (`from visual_generator import route_map_preflight` 等) はそのまま動く。

**モンキーパッチの注意**: preflight を掃引してレイアウトを決める手順  で `_check_line_through_label` 等を差し替えるときは、
**このモジュール**の名前を差し替えること。`visual_generator` 側の再輸出名を書き換えても、
内部の呼び出しはこのモジュールの名前空間で解決されるので効かない。
"""

import json
import os

# 既定の出力サイズ。関数のデフォルト引数に使うので遅延 import では間に合わず、
# visual_generator から取ると循環 import になる (向こうがこちらを import している)。
# route_legend_check が `_DEFAULT_LEGEND_LABELS` を複製しているのと同じ扱いで値を複製し、
# **食い違ったら落ちるように** が両者を照合する。
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

# ===========================================================================
# Route map (matplotlib + Natural Earth)
# ===========================================================================

# Natural Earth GeoJSON for world map polygons
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)

# Color mapping for route categories.
#
# 凡例の色は「どの線がどの種類か」を読み解く唯一の鍵なので、**同時に使われうる 2 色は
# 必ず見分けが付かなければならない**。education は元々 #7bc8f6 (ライトブルー) で、
# career の #4cc9f0 (ACCENT_CYAN) との RGB 距離が 47 しかなく、暗い背景に細い線として
# 描くと同色に見えていた。緑に振って距離 106 を確保している。
# 色相ごと変えるのは、細線では明度差より色相差のほうが残るため。
# この表を編集したら `check_route_palette_separation()` (smoke test section 21) が
# 閾値割れを検出する。
_ROUTE_CATEGORY_COLORS = {
    "origin": "#e2b714",  # ACCENT_GOLD — 生誕地・出発点
    "education": "#52b788",  # グリーン — 留学・進学 (was #7bc8f6: career と距離 47)
    "career": "#4cc9f0",  # ACCENT_CYAN — 職務・研究赴任
    "wandering": "#f72585",  # ACCENT_PINK — 放浪・旅
    "exile": "#c792ea",  # ライトパープル — 亡命・追放
    "final": "#aaaabb",  # TEXT_DIM — 最期の地
}

# 2 色が「別の色」として読める最小 RGB ユークリッド距離。背景 (_ROUTE_BG_HEX) との
# 距離にも同じ閾値を使う。現行パレットで最も近い正当なペアは exile/final の 60.2 なので、
# 60 はぎりぎり全ペアを通す較正値 (これ以上上げると正常なパレットが落ちる)。
_ROUTE_COLOR_MIN_DIST = 60.0
_ROUTE_BG_HEX = "#1a1a2e"

# Default map bounds (Europe + North America east coast + Middle East)
_DEFAULT_BOUNDS = {"lon": [-85, 45], "lat": [20, 65]}

# --- auto-bounds padding -------------------------------------------------
# padding は都市名・経路ラベルを置く余白なので、データ範囲に対して過大だと
# 都市が中央の小さな塊に潰れ、全ラベルが同じ場所を奪い合う。
#
# 旧実装は軸ごとに `max(range * 0.20, 5)` という **平坦な下限**だった。小さい地図では
# この下限が支配してしまう: ある回の 5 都市は経度 4.03 度に収まるのに 5 度の下限が
# 14.03 度 (データの 3.5 倍) を描き、レイアウト調整を 8 回繰り返す羽目になった。
#
# 下限自体は「1〜2 都市の地図が極端に寄りすぎない」ために残す。ただし**地図全体の
# 大きさで頭打ちにする**。頭打ちを軸ごとの range で計算しないのが要点で、経度が広く
# 緯度が薄い地図 は緯度側の余白が本当に要る。
# 軸ごとに切ると縦が詰まってラベルが凡例に潰され、実測で 2 シーンが悪化した。
# 全 31 auto-bounds シーンで計測: 軸ごとの cap は 2 件悪化 / 全体スケールの cap は
# 悪化ゼロ + ある回を解消。
_PAD_FRAC = 0.20  # 基準: 軸 range の 20%
_PAD_CAP_FRAC = 0.50  # 平坦な下限は地図全体スケールの 50% を超えない
_PAD_FLOOR_LON = 5.0
_PAD_FLOOR_LAT = 4.0
_PAD_MIN_LON = 1.5  # 退化した地図 (1 都市 / 同一緯度) 用の絶対下限
_PAD_MIN_LAT = 1.2


def _auto_bounds_pad(axis_range: float, scale: float, floor: float, abs_min: float) -> float:
    """auto-bounds の 1 軸ぶんの padding (度)。

    Args:
        axis_range: この軸の都市座標の幅 (度)
        scale: 地図全体のスケール = max(経度幅, 緯度幅)。平坦な下限をここで頭打ちにする
        floor: 平坦な下限 (_PAD_FLOOR_LON / _PAD_FLOOR_LAT)
        abs_min: range が 0 に潰れても残す絶対下限
    """
    return max(axis_range * _PAD_FRAC, min(floor, max(scale * _PAD_CAP_FRAC, abs_min)))


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _color_distance(a: str, b: str) -> float:
    """2 色の RGB ユークリッド距離。"""
    ra, rb = _hex_to_rgb(a), _hex_to_rgb(b)
    return sum((x - y) ** 2 for x, y in zip(ra, rb, strict=False)) ** 0.5


def check_route_palette_separation(
    palette: dict | None = None, categories: list | None = None
) -> list:
    """route_map の凡例色が互いに / 背景と見分けられるかを検査する。

    凡例は絵柄を読み解く鍵なので、**同時に使われる 2 色が同じに見えたら凡例は嘘をつく**。
    色が情報を運ぶのは track を分けるときだけ、という ある回の原則の色版。

    Args:
        palette: 検査するカテゴリ->hex の表 (既定 `_ROUTE_CATEGORY_COLORS`)
        categories: このシーンで実際に使われたカテゴリ。指定時はその部分集合のみ検査
                    (使われていない色同士が近くても画面上は問題にならない)

    Returns:
        [{"kind","a","b","distance","summary"}] の list。空なら問題なし。
    """
    import itertools

    pal = palette if palette is not None else _ROUTE_CATEGORY_COLORS
    if categories is not None:
        pal = {k: v for k, v in pal.items() if k in set(categories)}

    problems = []
    for a, b in itertools.combinations(sorted(pal), 2):
        dist = _color_distance(pal[a], pal[b])
        if dist < _ROUTE_COLOR_MIN_DIST:
            problems.append(
                {
                    "kind": "pair",
                    "a": a,
                    "b": b,
                    "distance": round(dist, 1),
                    "summary": (
                        f"凡例色 '{a}' ({pal[a]}) と '{b}' ({pal[b]}) の RGB 距離が "
                        f"{dist:.1f} (閾値 {_ROUTE_COLOR_MIN_DIST:.0f}) -- "
                        f"細い線では同じ色に見え、凡例が区別を説明できない"
                    ),
                }
            )
    for cat, hexv in sorted(pal.items()):
        dist = _color_distance(hexv, _ROUTE_BG_HEX)
        if dist < _ROUTE_COLOR_MIN_DIST:
            problems.append(
                {
                    "kind": "background",
                    "a": cat,
                    "b": "background",
                    "distance": round(dist, 1),
                    "summary": (
                        f"凡例色 '{cat}' ({hexv}) が背景 {_ROUTE_BG_HEX} との距離 "
                        f"{dist:.1f} (閾値 {_ROUTE_COLOR_MIN_DIST:.0f}) -- 背景に沈む"
                    ),
                }
            )
    return problems


def _get_geojson_cache_dir() -> str:
    """Return cache directory for Natural Earth data, next to this script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _download_natural_earth() -> str:
    """Download Natural Earth GeoJSON if not cached. Returns path to file."""
    cache_dir = _get_geojson_cache_dir()
    cache_file = os.path.join(cache_dir, "ne_110m_countries.geojson")

    if os.path.exists(cache_file):
        return cache_file

    os.makedirs(cache_dir, exist_ok=True)
    print("\n    [DL] Downloading Natural Earth data...")
    import urllib.request

    urllib.request.urlretrieve(_GEOJSON_URL, cache_file)
    print(f"    [DL] Saved: {cache_file}")
    return cache_file


def _load_geojson_polygons(cache_file: str) -> list:
    """Load GeoJSON and return list of polygon coordinate arrays."""
    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)

    polygons = []
    for feature in data["features"]:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                polygons.append(ring)
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                for ring in polygon:
                    polygons.append(ring)
    return polygons


# E: route_map ラベル見切れ検出の許容 px (fig.dpi 基準の display 座標)。
# 軸の左右 margin は 1% (~16px @1600px幅) しかなく、推定幅で auto 配置した label の
# 実レンダが数 px はみ出すことがあるため、既知良好な shipped 28 ep で誤検知ゼロに
# なる値へ calibrate。実測 (2026-06-27, route_map 保有 28 ep 全走査): 唯一の overflow は
# 016_cantor の「サンクトペテルブルク」6px (公開済・実害なし最終字の僅少はみ出し)、
# 他 27 ep は 0px。真の見切れ
# は 390px と桁違い。8px は known-good 6px のすぐ上・gross 390px の遥か下で安全に分離。
_CLIP_TOL_PX = 8.0

# -
#
# ある回は同じ地図で 3 回壊れ、3 回とも決定論チェックは沈黙し、人間の目か
# Manim Vision QA だけが気づいた。bbox の重なりは「読めるか」の代理指標にすぎない、
# という既知の限界 が route_map でも出た形。
#
#   A. ラベルの所属が曖昧: `--auto-fix-route-collisions` が bbox の重なりを消すために
#      フォントネー=ル=コントのラベルを 59.9pt 押し出し、レンヌの点の上に停めた。
#      重なりは確かに 0 件になり preflight は「1 scene(s) auto-fixed and persisted」と
#      報告したが、視聴者はレンヌの点をフォントネー=ル=コントだと読む。後にラ・ロシェル
#      も自分の点から 146px 離れ、隣の点との比が 1.7 倍しかない状態になった。
#      → 自分の点までの距離 d1 と最寄りの他都市の点までの距離 d2 の比を見る。
#
#   B. 経路の線がラベルを貫く: 1580 の点線がレンヌのラベルを、1570 の線がポワティエの
#      ラベルを横切った。決定論層は今まで一度も「線」と「文字」を比べていない
#      (title/label/legend/city のテキスト同士だけ)。
#
# 閾値は route_map を持つ全 37 話 40 scene で較正した (下の各定数のコメント参照)。
#
# d2/d1 の下限。2.0 未満 = 自分の点より「近すぎる」他都市の点がある。
_OWNERSHIP_RATIO_MIN = 2.0
# auto-fix の拒否線 (報告線 _OWNERSHIP_RATIO_MIN とは別物)。1.0 未満 =
# ラベルが**自分の点より他都市の点に近い**、つまり視聴者が読む都市名が入れ替わる。
#
# 報告線で拒否してはいけない: 004_ramanujan で実測すると、collision を 3->0 にする
# 修正は エロード 1.21->1.53、クンバコナム 1.48->1.82 と所属を**改善**しながら
# 「最寄りの他都市」の名前だけが変わる (遠ざかった結果、次点が最寄りに繰り上がる)。
# 報告線 (2.0) や「(都市, 最寄り) の組が増えたか」で拒否すると、この改善を誤って
# 拒否して 7/7 -> 6/7 に落ちる。一方 ある回の事故は比 0.00 -- ラベルがレンヌの点の
# 真上 -- で、1.42 と 0.00 は程度差ではなく種類が違う。曖昧 (advisory) と
# 取り違え (veto) を分ける線が 1.0。
_OWNERSHIP_VETO_RATIO = 1.0
# 距離は必ず**ラベル矩形の最も近い辺**から測る。中心から測ると ha="right" のラベルは
# アンカーが右端なので、幅 190px のラベルは常に中心が自分の点から ~95px 離れることに
# なり、正常な配置が軒並み発火する (実装中に踏んだ)。辺基準なら ha に依存しない。
_OWNERSHIP_EPS_PX = 1.0
# 線がラベル矩形の内側を走る長さ (px)。角をかすめる程度は欠陥ではないので下限を置く。
_LINE_THROUGH_MIN_PX = 8.0
# 判定前に矩形を縮める量。文字の周囲の余白に線がわずかに触れるのは実害がない。
_LINE_THROUGH_INSET_PX = 3.0


def _rect_point_distance(rect, px: float, py: float) -> float:
    """点 (px, py) から矩形 rect=(x0,y0,x1,y1) の最も近い辺までの px 距離 (内側なら 0)。"""
    x0, y0, x1, y1 = rect
    dx = max(x0 - px, 0.0, px - x1)
    dy = max(y0 - py, 0.0, py - y1)
    return (dx * dx + dy * dy) ** 0.5


def _segment_length_inside_rect(x0, y0, x1, y1, rect) -> float:
    """線分のうち矩形の内側にある部分の長さ (px)。Liang-Barsky クリッピング。

    点のサンプリング密度に依存しないので、曲線を線分列として渡せば「線がラベルの
    内側を何 px 走っているか」を正確に測れる (プロトタイプの HTML は点が矩形に入るか
    だけを見ており、50 点サンプルでは高さ 40px の箱を縦に横切る線を取りこぼしうる)。
    """
    rx0, ry0, rx1, ry1 = rect
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - rx0), (dx, rx1 - x0), (-dy, y0 - ry0), (dy, ry1 - y0)):
        if p == 0:
            if q < 0:
                return 0.0  # 平行かつ外側
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return 0.0
            t0 = max(t0, r)
        else:
            if r < t0:
                return 0.0
            t1 = min(t1, r)
    if t1 <= t0:
        return 0.0
    return ((dx * dx + dy * dy) ** 0.5) * (t1 - t0)


def _check_label_ownership(city_label_rects, dots_px, ratio_min=None) -> list[dict]:
    """A: 都市ラベルが自分の点より他都市の点の近くにいないか。

    Args:
        city_label_rects: [(artist, rect, city_name), ...] rect は display 座標
        dots_px: {city_name: (x_px, y_px)} 全都市の点
        ratio_min: d2/d1 の下限 (None = モジュール定数 _OWNERSHIP_RATIO_MIN)

    Returns: 曖昧なラベルの報告 list (空 = 全ラベルの所属が明確)

    Note: 既定値をデフォルト引数に**束縛しない**。デフォルト引数は def 実行時に
    評価されるので、較正スクリプトが `vg._OWNERSHIP_RATIO_MIN = x` と書き換えても
    効かず、閾値を振ったつもりで同じ数字を見続けることになる (較正中に踏んだ)。
    """
    if ratio_min is None:
        ratio_min = _OWNERSHIP_RATIO_MIN
    reports = []
    for artist, rect, name in city_label_rects:
        if rect is None or name not in dots_px:
            continue
        own = dots_px[name]
        d1 = _rect_point_distance(rect, own[0], own[1])
        nearest_name, d2 = None, float("inf")
        for other, (ox, oy) in dots_px.items():
            if other == name:
                continue
            d = _rect_point_distance(rect, ox, oy)
            if d < d2:
                nearest_name, d2 = other, d
        if nearest_name is None:
            continue  # 都市が 1 つだけなら取り違えようがない
        if d1 <= _OWNERSHIP_EPS_PX:
            # 自分の点がラベルの内側/直上。他都市の点まで内側なら曖昧、でなければ明確。
            if d2 > _OWNERSHIP_EPS_PX:
                continue
            ratio = 1.0
        else:
            ratio = d2 / d1
        if ratio >= ratio_min:
            continue
        reports.append(
            {
                "type": "city_label_ownership",
                "severity": "warning",
                # `city` は summary にも入っているが、消費側が人間向け文字列を
                # split("'") で剥がすのは壊れやすい (都市名に ' が入れば終わり)。
                # auto-fix の受理判定 (`_ownership_veto`) がラベル単位で候補と現状の
                # 比を突き合わせるので、識別子として機械可読な形で出す。
                "city": name,
                "summary": (
                    f"city label '{name}' is {int(d1)}px from its own dot but "
                    f"{int(d2)}px from '{nearest_name}' (ratio {ratio:.2f} < {ratio_min})"
                    f" -- viewers may read it as '{nearest_name}'"
                ),
                "overlap_px": (int(d1), int(d2)),
                "ownership_ratio": round(ratio, 3),
                "nearest_other_city": nearest_name,
                "artist": artist,
                "suggestion": (
                    "Pull the label back toward its own dot via "
                    "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}, or "
                    "widen bounds so the two cities are further apart on screen."
                ),
            }
        )
    return reports


def _ownership_ratios(reports) -> dict:
    """{city: (ratio, reads_as)} from `_check_label_ownership`.

    Only ambiguous labels are reported, so a city absent from this map is clear;
    callers treat that as +inf rather than 0 (`_ownership_ratio_of`).

    Ratios, not a count and not a set of names -- both weaker keys were measured
    and both are wrong in a different direction:

      - A count, or a set of city NAMES, cannot tell "イプシロン still reads as
        ゼータ" from "イプシロン now sits on デコイ's dot". On the synthetic trap in
 the name-keyed rule waved a
        stage-5 nudge through that left イプシロン's label 0px from デコイ's dot,
        because イプシロン was already ambiguous against ゼータ and so appeared in
        both the before and after set. That is an earlier episode accident exactly.
      - The (city, reads_as) PAIR catches that, but over-fires: on
        004_ramanujan the pair changes precisely BECAUSE a label improved and
        moved away from its former nearest neighbour (エロード 1.21 -> 1.53).
        Keying on pairs rejects that fix and costs 7/7 -> 6/7.

    The ratio is the only key that separates the two: it says how bad, not just
    what changed.
    """
    return {
        r["city"]: (r.get("ownership_ratio"), r.get("nearest_other_city"))
        for r in reports or []
        if r.get("type") == "city_label_ownership" and r.get("city")
    }


def _ownership_ratio_of(ratios: dict, city: str) -> float:
    """This city's d2/d1, or +inf when it is unambiguous (hence unreported)."""
    hit = ratios.get(city)
    if not hit or hit[0] is None:
        return float("inf")
    return float(hit[0])


def _ownership_veto(cand_reports, base_reports) -> list:
    """an earlier episode: labels a candidate layout pushes onto ANOTHER city's dot.

    Returns [(city, cand_ratio, base_ratio, reads_as), ...]; empty = safe to adopt.

    The an earlier episode accident was a stage-5 nudge that cleared a bbox overlap by parking
    フォントネー=ル=コント on レンヌ's dot. Collisions went to 0, the preflight printed
    "1 scene(s) auto-fixed and persisted", and the frame captioned the wrong city.
    The bbox matrix cannot object -- no two labels overlapped -- so the collision
    count alone must not be the whole acceptance test.

    Module level, not a closure inside the auto-fix loop, because the two clauses
    below are exactly the ones that are easy to get wrong and expensive when wrong
    (each cost a measured 7/7 -> 6/7 during development), and a closure cannot be
    unit-tested. See section [6].

    Three scoping decisions, each measured rather than assumed:

      1. Ownership only, not all advisories. A route line crossing a label is a
         blemish; it does not make a viewer read the wrong city. 041_cauchy trades
         1 line-through for 2 to clear its collision and is still adopted.
      2. The veto line is _OWNERSHIP_VETO_RATIO (1.0, "nearer another city's dot
         than its own"), NOT the advisory line (2.0) -- see that constant.
      3. Relative to the base, not absolute. 004_ramanujan (5 ambiguous labels),
         028_weierstrass (2) and 030_takagi (3) are already ambiguous before the
         auto-fix runs; refusing to touch an already-imperfect map would strand
         exactly the maps that most need repair. Inherited debt is tolerated,
         added debt is not.
    """
    cand = _ownership_ratios(cand_reports)
    base = _ownership_ratios(base_reports)
    out = []
    for city, (ratio, reads_as) in cand.items():
        if ratio is None:
            continue
        base_ratio = _ownership_ratio_of(base, city)
        # BOTH below the veto line AND worse than where it started: a label
        # already at 0.4 that a stage lifts to 0.8 is still bad, but this stage
        # is not what made it bad, and blocking it strands the map.
        if ratio < _OWNERSHIP_VETO_RATIO and ratio < base_ratio:
            out.append((city, ratio, base_ratio, reads_as))
    return sorted(out)


# --- Ken Burns aware clipping --------------------------------------
# The clipping check below measures label boxes against the STILL figure, but a
# route_map is saved as a PNG and then run through generate_ken_burns, which
# upscales by max_zoom and crops inward as the shot progresses. On an earlier episode a label
# that sat 100px inside the still frame ended the shot 4px from the edge, and
# only the LLM vision pass noticed. The crop is arithmetic, so the region that
# stays visible for the WHOLE shot can be computed exactly.
_KEN_BURNS_ZOOM_RANGE = 0.15  # keep in step with generate_ken_burns


def ken_burns_safe_rect(effect: str, width: int, height: int) -> tuple:
    """The sub-rect of a still that remains on screen for every frame.

    Mirrors generate_ken_burns: the still is scaled by max_zoom = 1 + zoom_range,
    each frame crops `width * max_zoom / zoom` from it, and zoom sweeps 1.0 ->
    max_zoom for zoom_in (the reverse for zoom_out, constant with a moving centre
    for the pans). Both ends are extremes because zoom and centre are monotonic
    in t, so intersecting the two endpoint rects gives the always-visible region.

    Returned in the STILL's own pixel coordinates, so it can be compared with
    matplotlib display bboxes directly. Returns the full frame for effects that
    do not move (nothing is ever cropped away).
    """
    zr = _KEN_BURNS_ZOOM_RANGE
    max_zoom = 1.0 + zr
    new_w, new_h = width * max_zoom, height * max_zoom

    def frame(t):
        if effect == "zoom_in":
            zoom = 1.0 + zr * t
        elif effect == "zoom_out":
            zoom = max_zoom - zr * t
        elif effect in ("pan_left", "pan_right"):
            zoom = 1.0 + zr * 0.5
        else:
            zoom = 1.0 + zr * t
        cw, chh = width * max_zoom / zoom, height * max_zoom / zoom
        if effect == "pan_left":
            cx = (new_w - cw) * (1.0 - t * 0.5)
        elif effect == "pan_right":
            cx = (new_w - cw) * (0.5 + t * 0.5)
        else:
            cx = (new_w - cw) / 2.0
        cy = (new_h - chh) / 2.0
        return (cx, cy, cx + cw, cy + chh)

    a, b = frame(0.0), frame(1.0)
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    s = max_zoom  # back to still coordinates
    return (x0 / s, y0 / s, x1 / s, y1 / s)


# --- route label attachment ----------------------------------------
# A route label is anchored on its own curve and displaced by label_offset, with
# a leader drawn back to the curve. Nothing checked how far it was allowed to go.
# asks whether two boxes overlap, whether a box is inside the frame,
# and _check_line_through_label whether a curve passes THROUGH a box -- a label
# parked in a far corner on a 900px leader passes all three. An earlier episode shipped with
# 1573 sitting 330px from its own route and NEARER another one; the user spotted
# it by eye, which is the failure this closes.
# Calibrated on all 40 shipped route_map scenes (125 route labels), 2026-08-05.
#
# _ATTACH_FAR_PX: distance-to-own-route is 0-50px for 111 labels, 50-150px for
# 13, then NOTHING until 372px. 200 sits in the empty band, so it fires on the
# one real outlier (009_seki, a label 372px from its route) and nothing else.
# An earlier episode's 1573 measured 330px before it was fixed and would have fired too.
#
# The wrong-line rule needs two guards. "Any other curve is nearer" alone fires
# on 19 labels, most of them anchored ON their own curve (own 3px, other 0px)
# where two routes simply converge at a shared city -- the label is not
# ambiguous, it is attached. So require the label to be genuinely DISPLACED
# (_ATTACH_MIN_PX) and the other curve to be CLEARLY nearer, not marginally:
# 45px-vs-42px reads fine, 108px-vs-0px does not. Together: 5 findings / 40
# scenes, and an earlier episode's 1570 (57px vs 19px) is one of them.
_ATTACH_FAR_PX = 200.0
_ATTACH_MIN_PX = 30.0
_ATTACH_RATIO_MAX = 0.6


def _rect_curve_distance(rect, points) -> float:
    """Shortest distance from a rect's nearest EDGE to a sampled curve.

    Edge, not centre: a right-anchored label's centre is half its width from its
    own anchor by construction, which is the trap that produced a false 146px
    reading in the label-ownership work.
    """
    x0, y0, x1, y1 = rect
    best = float("inf")
    for px, py in points:
        dx = max(x0 - px, 0.0, px - x1)
        dy = max(y0 - py, 0.0, py - y1)
        d = (dx * dx + dy * dy) ** 0.5
        if d < best:
            best = d
    return best


def route_label_attachment(label_rects, curves_px) -> list[dict]:
    """Route labels that drifted off their own route, or onto another one.

    Args:
        label_rects: [(kind, text, rect, owner_artist), ...] display coords
        curves_px: [{"key", "points", "owner"}, ...] -- same inputs
            _check_line_through_label receives, so the geometry is the
            renderer's own rather than a re-derivation. An earlier attempt to
            model the Bezier by hand got the bow direction wrong and reported
            535px where the renderer says 330.

    Returns advisory findings; never blocking.
    """
    findings = []
    for kind, text, rect, owner in label_rects:
        if kind != "route_label" or rect is None or owner is None:
            continue
        own = nearest_other = None
        other_key = None
        for curve in curves_px:
            d = _rect_curve_distance(rect, curve["points"])
            if curve.get("owner") is owner:
                own = d
            elif nearest_other is None or d < nearest_other:
                nearest_other, other_key = d, curve.get("key")
        if own is None:
            continue
        if (
            nearest_other is not None
            and own > _ATTACH_MIN_PX
            and nearest_other < own * _ATTACH_RATIO_MAX
        ):
            findings.append(
                {
                    "type": "route_label_wrong_line",
                    "severity": "warning",
                    "summary": (
                        f"route label '{text}' is {int(own)}px from its own route but "
                        f"{int(nearest_other)}px from [{other_key}] -- it reads as "
                        f"the wrong route"
                    ),
                    "overlap_px": (int(own), int(nearest_other)),
                    "route_key": other_key,
                    "suggestion": (
                        "Move the label along ITS OWN curve to a stretch the other "
                        "routes do not run beside, via that step's label_offset "
                        "[dlon, dlat]."
                    ),
                }
            )
        elif own > _ATTACH_FAR_PX:
            findings.append(
                {
                    "type": "route_label_detached",
                    "severity": "warning",
                    "summary": (
                        f"route label '{text}' sits {int(own)}px from its own route "
                        f"(leader line crosses the map)"
                    ),
                    "overlap_px": (int(own), 0),
                    "suggestion": (
                        "Shrink that step's label_offset [dlon, dlat] so the label "
                        "sits beside its own curve."
                    ),
                }
            )
    return findings


def _check_line_through_label(label_rects, curves_px) -> list[dict]:
    """B: 経路の線がラベル/枠/タイトル/凡例を貫いていないか。

    Args:
        label_rects: [(kind, text, rect, owner_artist), ...] display 座標
        curves_px: [{"key": str, "points": [(x,y), ...], "owner": artist|None}, ...]

    経路ラベルは設計上**自分の曲線の上に**置かれる (アンカーが曲線上の点) ので、
    自分の曲線は除外する。除外しないと全経路ラベルが毎回発火する。
    """
    reports = []
    for kind, text, rect, owner in label_rects:
        if rect is None:
            continue
        x0, y0, x1, y1 = rect
        inset = (
            x0 + _LINE_THROUGH_INSET_PX,
            y0 + _LINE_THROUGH_INSET_PX,
            x1 - _LINE_THROUGH_INSET_PX,
            y1 - _LINE_THROUGH_INSET_PX,
        )
        if inset[2] <= inset[0] or inset[3] <= inset[1]:
            continue  # 縮めたら潰れる極小ラベル
        for curve in curves_px:
            if owner is not None and curve.get("owner") is owner:
                continue  # 自分の経路ラベルは曲線上に置く設計
            pts = curve["points"]
            inside = 0.0
            for i in range(len(pts) - 1):
                inside += _segment_length_inside_rect(
                    pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], inset
                )
            if inside < _LINE_THROUGH_MIN_PX:
                continue
            reports.append(
                {
                    "type": f"line_through_{kind}",
                    "severity": "warning",
                    "summary": (
                        f"route line [{curve['key']}] runs {int(inside)}px through {kind} '{text}'"
                    ),
                    "overlap_px": (int(inside), 0),
                    "route_key": curve["key"],
                    "artist": owner,
                    "suggestion": (
                        "Move the label off the line: city via "
                        "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}, "
                        "route via that step's label_offset [dlon, dlat], "
                        "legend via legend_loc."
                    ),
                }
            )
    return reports


def _check_route_map_collisions(
    fig,
    title_artist,
    route_label_artists,
    legend,
    city_label_artists=None,
    ax=None,
    city_dots=None,
    route_curves=None,
    effect="zoom_in",
) -> list[dict]:
    """Detect title/route_label/legend/city_label bbox overlaps after layout.

    Calls fig.canvas.draw() to materialize layout, gets pixel-space bboxes via
    get_window_extent(renderer), and checks pairwise overlap. Returns a list of
    collision reports; empty list means clean.

    Each report: {
        "type": "title_vs_route_label" | "title_vs_legend" | "route_label_vs_legend"
                 | "route_label_vs_route_label" | "city_label_vs_route_label"
                 | "city_label_vs_city_label" | "city_label_vs_legend"
                 | "city_label_vs_title",
        "summary": "<human readable>",
        "overlap_px": (dx, dy),
        "suggestion": "<concrete fix proposal>",
    }

    E (an earlier episode Kepler): city_label vs route_label and city_label vs city_label
    were previously unchecked — a displaced route label could land on a city name
    (or two clustered city names overlap) and slip past preflight. Now covered.

    ある回 (ヴィエト): bbox の重なりだけでは「絵が壊れている」ことを検出できない 2 つの
    型を追加した。どちらも ある回で実際に「collisions 0」と報告されながら
    人間の目でしか見つからなかった。

    `ax` / `city_dots` / `route_curves` はそのための追加入力:
      - `city_dots`: {都市名: (lon, lat)} — **点の座標**。これまで本関数は artist しか
        受け取っておらず、ラベルが「どの点のものか」を判定できなかった (A の要)。
      - `route_curves`: [{"key", "points" (データ座標), "owner" (経路ラベル artist)}]
        — 描かれた曲線そのもの。決定論層は今まで線と文字を比べていなかった (B の要)。
      - `ax`: データ座標 → display 座標の変換に使う。
    いずれも省略可 (None) で、その場合は該当チェックだけが静かに無効になる。
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def _bbox(artist):
        if artist is None:
            return None
        try:
            return artist.get_window_extent(renderer=renderer)
        except Exception:
            return None

    def _overlap(a, b):
        """Return (dx, dy) overlap in pixels, or None if disjoint."""
        if a is None or b is None:
            return None
        dx = min(a.x1, b.x1) - max(a.x0, b.x0)
        dy = min(a.y1, b.y1) - max(a.y0, b.y0)
        if dx > 0 and dy > 0:
            return (dx, dy)
        return None

    # --- auto-fix support ------------------------------------
    # Every city-label report carries the displacement that would clear it, so the
    # auto-fix has a lever on the object the report actually names. Before this,
    # the four repair stages could only widen the route-label margin, stretch the
    # latitude bounds, shrink the title and rotate the legend -- while every
    # suggestion string told the human to use `city_offsets`. Measured over the 7
    # colliding scenes in the repo, 6 named a city or route label as the mover and
    # no stage could move either.
    fig_box = fig.bbox  # x0=y0=0, x1=幅px, y1=高px
    _px_to_pt = 72.0 / (fig.dpi or 72.0)
    _PUSH_MARGIN_PX = 6.0

    def _push_clear(a, b):
        """Pixels to move bbox `a` so it clears `b`, along the cheaper axis."""
        dx = min(a.x1, b.x1) - max(a.x0, b.x0)
        dy = min(a.y1, b.y1) - max(a.y0, b.y0)
        if dx <= dy:
            sign = 1.0 if (a.x0 + a.x1) >= (b.x0 + b.x1) else -1.0
            return (sign * (dx + _PUSH_MARGIN_PX), 0.0)
        sign = 1.0 if (a.y0 + a.y1) >= (b.y0 + b.y1) else -1.0
        return (0.0, sign * (dy + _PUSH_MARGIN_PX))

    def _push_inward(bbox):
        """Pixels to move `bbox` back inside the figure from its worst edge."""
        sides = (
            (fig_box.x0 - bbox.x0, (1.0, 0.0)),  # 左切れ -> 右へ
            (bbox.x1 - fig_box.x1, (-1.0, 0.0)),  # 右切れ -> 左へ
            (fig_box.y0 - bbox.y0, (0.0, 1.0)),  # 下切れ -> 上へ
            (bbox.y1 - fig_box.y1, (0.0, -1.0)),  # 上切れ -> 下へ
        )
        amt, (ux, uy) = max(sides, key=lambda s: s[0])
        d = amt + _PUSH_MARGIN_PX
        return (ux * d, uy * d)

    def _city_fix(artist, push_px):
        """Describe how to move this city label, in annotate offset points.

        `city_offset_pts` is what auto-placement chose for this city, so the
        auto-fix can start from the current position instead of guessing: writing
        a `city_offsets` entry bypasses auto-placement entirely.
        """
        if artist is None:
            return None
        off = getattr(artist, "xyann", None) or (0.0, 0.0)
        return {
            "city": artist.get_text(),
            "city_offset_pts": [float(off[0]), float(off[1])],
            "city_ha": artist.get_ha() or "left",
            "push_pts": [push_px[0] * _px_to_pt, push_px[1] * _px_to_pt],
        }

    title_bbox = _bbox(title_artist)
    legend_bbox = _bbox(legend)
    route_bboxes = [(a, _bbox(a)) for a in route_label_artists]

    reports = []

    if title_bbox is not None:
        for artist, bbox in route_bboxes:
            ov = _overlap(title_bbox, bbox)
            if ov is None:
                continue
            label_text = artist.get_text() if artist is not None else "?"
            reports.append(
                {
                    "type": "title_vs_route_label",
                    "summary": f"title overlaps route_label '{label_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Expand bounds.lat[1] upward, shorten title, "
                    "or move the route segment to a lower latitude.",
                }
            )

    if title_bbox is not None and legend_bbox is not None:
        ov = _overlap(title_bbox, legend_bbox)
        if ov is not None:
            reports.append(
                {
                    "type": "title_vs_legend",
                    "summary": f"title overlaps legend ({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Set legend_loc to 'lower right' / 'lower left', "
                    "or shorten the title.",
                }
            )

    if legend_bbox is not None:
        for artist, bbox in route_bboxes:
            ov = _overlap(legend_bbox, bbox)
            if ov is None:
                continue
            label_text = artist.get_text() if artist is not None else "?"
            reports.append(
                {
                    "type": "route_label_vs_legend",
                    "summary": f"legend overlaps route_label '{label_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Move legend to opposite corner via legend_loc / "
                    "legend_bbox_to_anchor.",
                }
            )

    # D: route_label vs route_label (pairwise) — closes preflight gap
    # where two adjacent route labels cluster around a shared pivot city.
    for i in range(len(route_bboxes)):
        for j in range(i + 1, len(route_bboxes)):
            artist_i, bbox_i = route_bboxes[i]
            artist_j, bbox_j = route_bboxes[j]
            ov = _overlap(bbox_i, bbox_j)
            if ov is None:
                continue
            text_i = artist_i.get_text() if artist_i is not None else "?"
            text_j = artist_j.get_text() if artist_j is not None else "?"
            reports.append(
                {
                    "type": "route_label_vs_route_label",
                    "summary": f"route_label '{text_i}' overlaps '{text_j}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "suggestion": "Shorten one of the labels, drop one route, "
                    "or set both year and label of one route to empty string.",
                }
            )

    # E: city_label vs route_label / city_label vs city_label.
    # A displaced route label can land on a city name, or two clustered city
    # names can overlap — both previously slipped past preflight.
    # Require a meaningful 2D overlap (>=4px each way). bbox edges that merely
    # touch (e.g. a city name 1px under a route label) are not a real collision
    #. Real collisions overlap by
    # most of the label height.
    _min_ov = 4
    city_bboxes = [(a, _bbox(a)) for a in (city_label_artists or [])]
    for c_artist, c_bbox in city_bboxes:
        c_text = c_artist.get_text() if c_artist is not None else "?"
        for r_artist, r_bbox in route_bboxes:
            ov = _overlap(c_bbox, r_bbox)
            if ov is None or ov[0] < _min_ov or ov[1] < _min_ov:
                continue
            r_text = r_artist.get_text() if r_artist is not None else "?"
            reports.append(
                {
                    "type": "city_label_vs_route_label",
                    "summary": f"city '{c_text}' overlaps route_label '{r_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "city_fix": _city_fix(c_artist, _push_clear(c_bbox, r_bbox)),
                    "suggestion": "Move the route label via that route step's "
                    "'label_offset' [dlon, dlat], or move the city label via "
                    "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}.",
                }
            )
    for i in range(len(city_bboxes)):
        for j in range(i + 1, len(city_bboxes)):
            a_artist, a_bbox = city_bboxes[i]
            b_artist, b_bbox = city_bboxes[j]
            ov = _overlap(a_bbox, b_bbox)
            if ov is None or ov[0] < _min_ov or ov[1] < _min_ov:
                continue
            a_text = a_artist.get_text() if a_artist is not None else "?"
            b_text = b_artist.get_text() if b_artist is not None else "?"
            reports.append(
                {
                    "type": "city_label_vs_city_label",
                    "summary": f"city '{a_text}' overlaps city '{b_text}' "
                    f"({int(ov[0])}x{int(ov[1])}px)",
                    "overlap_px": ov,
                    "city_fix": _city_fix(a_artist, _push_clear(a_bbox, b_bbox)),
                    "suggestion": "Separate clustered city labels via "
                    "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}.",
                }
            )

    # F: city_label vs legend / vs title.
    # These two pairs were the only ones missing from the matrix, and they are
    # exactly what the Manim Vision QA kept reporting on ある回 ("ベルリンの末尾が
    # 凡例の枠に食い込んでいる", six runs in a row). The deterministic layer could
    # not confirm or deny it because it never compared that pair -- the answer had
    # to be measured by hand off the rendered frame each time (it was clear, by a
    # visible margin). A real overlap here would have shipped silently.
    for c_artist, c_bbox in city_bboxes:
        c_text = c_artist.get_text() if c_artist is not None else "?"
        if legend_bbox is not None:
            ov = _overlap(c_bbox, legend_bbox)
            if ov is not None and ov[0] >= _min_ov and ov[1] >= _min_ov:
                reports.append(
                    {
                        "type": "city_label_vs_legend",
                        "summary": f"city '{c_text}' overlaps legend ({int(ov[0])}x{int(ov[1])}px)",
                        "overlap_px": ov,
                        "city_fix": _city_fix(c_artist, _push_clear(c_bbox, legend_bbox)),
                        "suggestion": "Move the legend to another corner via "
                        "legend_loc, or move the city label via "
                        "visual.city_offsets {city: [x_off_pts, y_off_pts, ha]}.",
                    }
                )
        if title_bbox is not None:
            ov = _overlap(c_bbox, title_bbox)
            if ov is not None and ov[0] >= _min_ov and ov[1] >= _min_ov:
                reports.append(
                    {
                        "type": "city_label_vs_title",
                        "summary": f"city '{c_text}' overlaps title ({int(ov[0])}x{int(ov[1])}px)",
                        "overlap_px": ov,
                        "city_fix": _city_fix(c_artist, _push_clear(c_bbox, title_bbox)),
                        "suggestion": "Expand bounds.lat[1] upward, shorten the "
                        "title, or move the city label via visual.city_offsets.",
                    }
                )

    # E: figure 枠からの見切れ (clipping) 検出。
    # auto 配置 (placement loop, 本関数外) は frame をはみ出す候補 offset を skip するが、
    # 手動 city_offsets override と「全候補不可」fallback はその bounds チェックを通らず、
    # ラベルが PNG 端で切れうる。savefig は bbox_inches='tight' を使わない (line ~2296)
    # ので figure 領域 = 保存 PNG 範囲。各ラベルの実レンダ pixel bbox が fig.bbox を
    # はみ出す = 見切れ。推定 bbox でなく get_window_extent の実 extent でピクセル精密。
    # (fig_box は auto-fix support ブロックで定義済み)

    def _clip_overflow(bbox, tol):
        """Return max px by which bbox exceeds the figure on any side, else None."""
        if bbox is None:
            return None
        worst = max(
            fig_box.x0 - bbox.x0,  # 左切れ
            bbox.x1 - fig_box.x1,  # 右切れ
            fig_box.y0 - bbox.y0,  # 下切れ
            bbox.y1 - fig_box.y1,  # 上切れ
        )
        return worst if worst > tol else None

    # tol は side ごとに分ける: 上下は subtitle-safe 等の余白があり真の見切れのみ、左右は
    # 軸 margin 1% (~16px) しかないので実害が出る幅で。既知良好な shipped 28 ep で
    # 誤検知ゼロになるよう calibrate 済 (_CLIP_TOL_PX)。
    _clip_targets = [("city_label", a, b) for a, b in city_bboxes]
    _clip_targets += [("route_label", a, b) for a, b in route_bboxes]
    if title_artist is not None:
        _clip_targets.append(("title", title_artist, title_bbox))
    for _kind, _artist, _cbbox in _clip_targets:
        amt = _clip_overflow(_cbbox, _CLIP_TOL_PX)
        if amt is None:
            continue
        _text = _artist.get_text() if _artist is not None else "?"
        reports.append(
            {
                "type": f"{_kind}_clipped",
                "summary": f"{_kind} '{_text}' clipped at figure edge ({int(amt)}px past)",
                "overlap_px": (int(amt), 0),
                "city_fix": (
                    _city_fix(_artist, _push_inward(_cbbox)) if _kind == "city_label" else None
                ),
                "suggestion": "Widen bounds.lon/lat to give room, or pull the label "
                "inward: city via visual.city_offsets {city: [x_off, y_off, ha]}, "
                "route via that step's label_offset [dlon, dlat].",
            }
        )

    # -
    # ここまでの検査は全て「テキストとテキストの矩形が重なるか」だけを見ている。
    # 重なりが 0 でも (a) ラベルが他都市の点の上に乗る (b) 経路の線が文字を貫く
    # の 2 通りで絵は壊れる。ある回で 3 回とも「collisions 0」をすり抜けた。
    dots_px: dict = {}
    if ax is not None and city_dots:
        for _name, _coord in dict(city_dots).items():
            try:
                _x, _y = ax.transData.transform((float(_coord[0]), float(_coord[1])))
            except Exception:
                continue
            dots_px[_name] = (float(_x), float(_y))

    if dots_px:
        # ラベルの所属は artist のテキスト = 都市名で引く (cities は dict なので一意)。
        _city_rects = []
        for _a, _b in city_bboxes:
            if _a is None or _b is None:
                continue
            _city_rects.append((_a, (_b.x0, _b.y0, _b.x1, _b.y1), _a.get_text()))
        for _rep in _check_label_ownership(_city_rects, dots_px):
            _art = _rep.pop("artist", None)
            _own = dots_px.get(_art.get_text()) if _art is not None else None
            _bb = _bbox(_art) if _art is not None else None
            if _own is not None and _bb is not None:
                # 曖昧さを消す向き = 自分の点へ引き戻す向き。半分だけ戻すのは、
                # 点まで戻しきるとラベルが自分の点を覆ってしまうため。
                _cx, _cy = (_bb.x0 + _bb.x1) / 2.0, (_bb.y0 + _bb.y1) / 2.0
                _rep["city_fix"] = _city_fix(_art, ((_own[0] - _cx) * 0.5, (_own[1] - _cy) * 0.5))
            reports.append(_rep)

    if ax is not None and route_curves:
        _curves_px = []
        for _c in route_curves:
            _pts = _c.get("points") or []
            if len(_pts) < 2:
                continue
            try:
                _tp = ax.transData.transform(_pts)
            except Exception:
                continue
            _curves_px.append(
                {
                    "key": _c.get("key", "?"),
                    "owner": _c.get("owner"),
                    "points": [(float(p[0]), float(p[1])) for p in _tp],
                }
            )
        if _curves_px:
            _targets = []
            for _a, _b in city_bboxes:
                if _b is not None:
                    _targets.append(
                        (
                            "city_label",
                            _a.get_text() if _a else "?",
                            (_b.x0, _b.y0, _b.x1, _b.y1),
                            _a,
                        )
                    )
            for _a, _b in route_bboxes:
                if _b is not None:
                    _targets.append(
                        (
                            "route_label",
                            _a.get_text() if _a else "?",
                            (_b.x0, _b.y0, _b.x1, _b.y1),
                            _a,
                        )
                    )
            if title_bbox is not None:
                _t_txt = title_artist.get_text() if title_artist is not None else "?"
                _targets.append(
                    (
                        "title",
                        _t_txt,
                        (title_bbox.x0, title_bbox.y0, title_bbox.x1, title_bbox.y1),
                        title_artist,
                    )
                )
            if legend_bbox is not None:
                _targets.append(
                    (
                        "legend",
                        "legend",
                        (legend_bbox.x0, legend_bbox.y0, legend_bbox.x1, legend_bbox.y1),
                        None,
                    )
                )
            # misreading: a route label that drifted off its own route, or onto
            # another one. Advisory -- the user found both by eye on an earlier episode
            # because nothing measured it.
            reports.extend(route_label_attachment(_targets, _curves_px))

            # misreading: the clipping check above measures against the still figure,
            # but the still is then run through generate_ken_burns, which crops
            # inward as the shot runs (125px off each side by the end of a
            # zoom_in). Re-check every box against the region that survives the
            # whole shot. Advisory, not blocking: 12 labels across 10 shipped
            # episodes already fail it, and turning those into build stoppers
            # would block their rebuilds over a defect that already shipped.
            _safe = ken_burns_safe_rect(effect, fig_box.x1 - fig_box.x0, fig_box.y1 - fig_box.y0)
            for _kind, _text, _rect, _ in _targets:
                if _rect is None:
                    continue
                _over = max(
                    _safe[0] - _rect[0],
                    _rect[2] - _safe[2],
                    _safe[1] - _rect[1],
                    _rect[3] - _safe[3],
                )
                if _over <= _CLIP_TOL_PX:
                    continue
                reports.append(
                    {
                        "type": f"{_kind}_clipped_by_zoom",
                        "severity": "warning",
                        "summary": (
                            f"{_kind} '{_text}' leaves the frame {int(_over)}px as the "
                            f"'{effect}' shot crops in "
                            f"(it is inside the still, so the existing clip check passes)"
                        ),
                        "overlap_px": (int(_over), 0),
                        "suggestion": (
                            "Pull it inward: city via visual.city_offsets "
                            "{city: [x_off, y_off, ha]}, route via that step's "
                            "label_offset [dlon, dlat], or widen bounds."
                        ),
                    }
                )

            for _rep in _check_line_through_label(_targets, _curves_px):
                # 線を避ける向きは「線に垂直」で一意に決まらない (どちら側に逃がすかは
                # 周囲次第) ので city_fix は付けない。auto-fix stage 5 の梃子にはせず、
                # 検出と提案に留める。
                _rep.pop("artist", None)
                reports.append(_rep)

    return reports


def generate_route_map(
    visual: dict,
    output_path: str,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    preflight_only: bool = False,
) -> list[dict]:
    """Generate route map visualization as MP4 (or run preflight only).

    When preflight_only=True, the figure is built and collision-checked but not
    saved (no PNG, no Ken Burns). Returns the collision reports list. Use this
    from preflight to detect title/label/legend overlaps before running
    expensive downstream steps.

    Returns:
        list of collision report dicts (empty if no collision detected). For
        the normal path (preflight_only=False), the return value is informational
        only (the function's primary effect is writing output_path).
    """
    """Generate route map visualization as MP4.

    Renders a world map with cities and travel routes using matplotlib,
    saves as temp PNG, then applies Ken Burns effect for video output.

    Visual spec:
        {
            "type": "route_map",
            "title": "エルデシュの旅路（1913–1996）",
            "cities": {
                "ブダペスト": [19.04, 47.50],
                "マンチェスター": [-2.24, 53.48],
                ...
            },
            "route": [
                {"from": "ブダペスト", "to": "マンチェスター",
                 "year": "1934", "label": "ハンガリーを離れる",
                 "category": "exile"}
            ],
            "bounds": {"lon": [-85, 45], "lat": [20, 65]},  // optional, auto-calculated from cities
            "effect": "zoom_in"  // optional, default zoom_in
        }
    """
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    # 地図は PNG に落としてから Ken Burns で動かす -- その 2 つと font 解決だけを
    # visual_generator から借りる。visual_generator はこのモジュールを module 直下で
    # import しているので、ここで module 直下に書くと循環する。関数の中なら安全。
    from visual_generator import find_font, generate_ken_burns, generate_text_overlay

    # Extract params from visual spec
    title = visual.get("title", "")
    cities = visual.get("cities", {})
    route = visual.get("route", [])
    bounds = visual.get("bounds", None)
    effect = visual.get("effect", "zoom_in")

    # Style constants (hex for matplotlib)
    bg_hex = "#1a1a2e"
    land_color = "#2a2a4e"
    land_edge = "#3a3a5e"
    line_color = "#50507a"
    gold_hex = "#e2b714"
    white_hex = "#ffffff"

    # Auto-calculate bounds from city coordinates if not specified.
    # `visual["bounds"]` remains an explicit override and is used verbatim.
    if bounds is None and cities:
        lons = [coord[0] for coord in cities.values()]
        lats = [coord[1] for coord in cities.values()]
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        # Padding: 20% of the axis range, with a flat floor that is itself capped
        # by the overall map scale (see _auto_bounds_pad).
        map_scale = max(lon_max - lon_min, lat_max - lat_min)
        lon_pad = _auto_bounds_pad(lon_max - lon_min, map_scale, _PAD_FLOOR_LON, _PAD_MIN_LON)
        lat_pad = _auto_bounds_pad(lat_max - lat_min, map_scale, _PAD_FLOOR_LAT, _PAD_MIN_LAT)
        bounds = {
            "lon": [lon_min - lon_pad, lon_max + lon_pad],
            "lat": [lat_min - lat_pad, lat_max + lat_pad],
        }
    elif bounds is None:
        bounds = _DEFAULT_BOUNDS
    elif cities and ("lon" not in bounds or "lat" not in bounds):
        # A PARTIAL bounds dict silently drops the missing axis to the hardcoded
        # world default below (lon [-85,45] / lat [20,65]) instead of fitting the
        # cities -- surprising, and easy to write by accident. An earlier episode ships a
        # lat-only bounds and gets the default longitude as a result.
        # Behaviour is left as-is (changing it would reframe that shipped episode);
        # this only refuses to do it silently.
        missing = [k for k in ("lon", "lat") if k not in bounds]
        print(
            f"    [WARN] route_map bounds に {missing} が無いため、その軸は都市座標に"
            f"合わせず既定値 {[_DEFAULT_BOUNDS[k] for k in missing]} を使います。"
            f"意図しないなら両軸を書くか bounds ごと省いて auto に任せてください。"
        )

    # Style constants (hex for matplotlib)
    bg_hex = "#1a1a2e"
    land_color = "#2a2a4e"
    land_edge = "#3a3a5e"
    line_color = "#50507a"
    gold_hex = "#e2b714"
    white_hex = "#ffffff"

    # Load map data
    try:
        cache_file = _download_natural_earth()
        polygons = _load_geojson_polygons(cache_file)
    except Exception as e:
        print(f"\n    [WARN] Failed to load map data: {e}")
        print("    Falling back to text_overlay.")
        fallback = {
            "type": "text_overlay",
            "style": "definition",
            "content": {"main": title or "Route Map", "sub": ""},
        }
        generate_text_overlay(fallback, output_path, duration)
        return

    # Find font for Japanese text
    font_path = find_font()
    font_props = {}
    if font_path:
        from matplotlib.font_manager import FontProperties

        font_props = {"fontproperties": FontProperties(fname=font_path)}

    # Create figure (16:9, high DPI)
    fig, ax = plt.subplots(1, 1, figsize=(16, 9), facecolor=bg_hex)
    ax.set_facecolor(bg_hex)

    # Set map bounds — do NOT use aspect="equal" (wastes space on 16:9)
    lon_range = bounds.get("lon", _DEFAULT_BOUNDS["lon"])
    lat_range = bounds.get("lat", _DEFAULT_BOUNDS["lat"])
    ax.set_xlim(lon_range)
    ax.set_ylim(lat_range)

    # Draw country polygons
    for ring in polygons:
        coords = np.array(ring)
        ax.fill(
            coords[:, 0],
            coords[:, 1],
            facecolor=land_color,
            edgecolor=land_edge,
            linewidth=0.5,
            zorder=1,
        )

    # Grid lines (subtle)
    for lat in range(int(lat_range[0]), int(lat_range[1]) + 1, 10):
        ax.axhline(lat, color=line_color, linewidth=0.3, alpha=0.3, zorder=0)
    for lon in range(int(lon_range[0]), int(lon_range[1]) + 1, 10):
        ax.axvline(lon, color=line_color, linewidth=0.3, alpha=0.3, zorder=0)

    # Scale factor for label offsets based on map extent
    lon_span = lon_range[1] - lon_range[0]
    lat_span = lat_range[1] - lat_range[0]

    # Draw route arrows
    legend_categories = set()
    route_labels = []
    route_curves = []  # ある回 B: 描かれた曲線 (データ座標) を線 vs 文字の検査へ渡す

    # Round-trip overlap fix: pre-count each unordered city pair so outbound/
    # return legs between the SAME two cities (e.g. Paris->Tulle->Paris) fan out
    # onto opposite sides with a growing bow instead of overlapping into one line.
    _pair_total = {}
    for _s in route:
        _p = frozenset((_s.get("from", ""), _s.get("to", "")))
        _pair_total[_p] = _pair_total.get(_p, 0) + 1
    _pair_seen = {}

    for i_step, step in enumerate(route):
        from_city = step.get("from", "")
        to_city = step.get("to", "")
        category = step.get("category", "wandering")
        color = _ROUTE_CATEGORY_COLORS.get(category, "#4cc9f0")
        legend_categories.add(category)

        if from_city not in cities or to_city not in cities:
            continue

        sx, sy = cities[from_city]
        ex, ey = cities[to_city]

        # Bezier curve — alternate direction to spread overlapping routes
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        dist = np.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        _pair = frozenset((from_city, to_city))
        _k = _pair_seen.get(_pair, 0)
        _pair_seen[_pair] = _k + 1
        if _pair_total[_pair] > 1:
            # round-trip leg: keep direction SAME sign for both legs. The
            # return leg's route vector is reversed, so its perpendicular flips
            # automatically -> the two legs bow to OPPOSITE absolute sides
            # (an alternating sign here would cancel that and overlap them).
            # The return leg is also dashed (below) so they never read as one.
            curve_height = dist * (0.32 + 0.24 * _k)
            direction = 1
        else:
            curve_height = dist * 0.12
            direction = 1 if i_step % 2 == 0 else -1
        # Offset the control point PERPENDICULAR to the route direction (not just
        # in +Y). A Y-only offset fails to separate near North-South routes
        # (e.g. Paris<->Tulle), letting the outbound/return legs overlap.
        if dist > 1e-9:
            perp_x, perp_y = -(ey - sy) / dist, (ex - sx) / dist
        else:
            perp_x, perp_y = 0.0, 1.0
        cx = mx + curve_height * direction * perp_x
        cy = my + curve_height * direction * perp_y

        t = np.linspace(0, 1, 50)
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t**2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t**2 * ey

        # Mark the return leg of a round-trip dashed so it never reads as a
        # single overlapping line with the outbound leg (user request: 点線).
        _ls = "--" if (_pair_total[_pair] > 1 and _k > 0) else "-"
        ax.plot(bx, by, color=color, linewidth=3, alpha=0.8, zorder=3, linestyle=_ls)
        # ある回 B: 描いた曲線そのものを控えておく。決定論の衝突検査は今まで
        # 「文字 vs 文字」しか見ておらず、線が文字を貫いても collisions 0 だった。
        route_curves.append(
            {
                "key": f"{step.get('year', '')} {from_city}->{to_city}".strip(),
                "points": list(zip(bx.tolist(), by.tolist(), strict=True)),
                "owner": None,  # 経路ラベル artist は生成後に結び直す
            }
        )
        ax.annotate(
            "",
            xy=(ex, ey),
            xytext=(bx[-3], by[-3]),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=3, mutation_scale=15),
            zorder=3,
        )

        # Place label ON the curve at varying t values.
        # Store curve params so placement loop can compute (Bx,By) at any t,
        # preserving visual correspondence between label and its own arc.
        year = step.get("year", "")
        label = step.get("label", "")
        if year or label:
            label_text = f"{year} {label}" if year and label else (year or label)
            route_labels.append(
                {
                    "sx": sx,
                    "sy": sy,
                    "cx": cx,
                    "cy": cy,
                    "ex": ex,
                    "ey": ey,
                    "direction": direction,
                    "curve_height": curve_height,
                    "text": label_text,
                    "color": color,
                    "label_offset": step.get("label_offset"),
                    # ある回 B: この経路ラベルが乗っている曲線。自分の曲線は
                    # 「線が文字を貫く」判定から除く (設計上ラベルは曲線上に置く)。
                    "curve_idx": len(route_curves) - 1,
                }
            )

    # Determine approximate legend bbox in data coords so that city labels
    # can avoid placing themselves under the legend.
    legend_loc = visual.get("legend_loc", "upper right")
    legend_bbox = tuple(visual.get("legend_bbox_to_anchor", [0.92, 0.98]))
    # Rough estimate based on 6 possible items × 18pt fontsize
    _legend_n = len(legend_categories) if legend_categories else 1
    _leg_w_ax = 0.18
    _leg_h_ax = 0.05 + 0.055 * _legend_n
    if "right" in legend_loc:
        _leg_x0_ax = legend_bbox[0] - _leg_w_ax
    else:
        _leg_x0_ax = legend_bbox[0]
    if "upper" in legend_loc:
        _leg_y1_ax = legend_bbox[1]
        _leg_y0_ax = _leg_y1_ax - _leg_h_ax
    else:
        _leg_y0_ax = legend_bbox[1]
        _leg_y1_ax = _leg_y0_ax + _leg_h_ax
    legend_rect_data = (
        lon_range[0] + _leg_x0_ax * lon_span,
        lat_range[0] + _leg_y0_ax * lat_span,
        lon_range[0] + (_leg_x0_ax + _leg_w_ax) * lon_span,
        lat_range[0] + _leg_y1_ax * lat_span,
    )

    def _in_legend(x, y):
        x0, y0, x1, y1 = legend_rect_data
        return x0 <= x <= x1 and y0 <= y <= y1

    # Draw city dots and labels FIRST (so we can track positions for route label collision)
    city_list = list(cities.items())
    placed_labels = []  # track (x, y) of placed label centers for collision avoidance
    placed_label_bboxes = []  # track (x0, y0, x1, y1) for tighter collision
    city_label_artists = []  # E: track city-label artists for collision check
    # Per-city label position override (ある回で追加 — auto-placement だと
    # 日本語長名 (ゲッティンゲン等) が canvas 端で clipping。scene_def の
    # visual.city_offsets = {city_name: [x_off_pts, y_off_pts, ha]} で固定 placement。
    # ha は "left" | "right" | "center"、省略時 "left"。auto candidates を skip。
    city_offsets_override = visual.get("city_offsets", {}) or {}

    def _estimate_label_w_deg(text: str, fontsize_pt: float, pts_per_lon_local: float) -> float:
        """Estimate rendered text width in longitude degrees.

        Japanese chars are ~1em (full-width); ASCII chars ~0.55em.
        """
        width_pts = 0.0
        for ch in text:
            width_pts += fontsize_pt * (0.55 if ch.isascii() else 1.05)
        return width_pts / pts_per_lon_local

    def _label_bbox(cx, cy, w, h, ha):
        """Return (x0, y0, x1, y1) in data coords for a label anchored at
        (cx, cy) with width w and height h. ha selects horizontal anchor.
        """
        if ha == "left":
            x0, x1 = cx, cx + w
        elif ha == "right":
            x0, x1 = cx - w, cx
        else:
            x0, x1 = cx - w / 2, cx + w / 2
        return (x0, cy - h / 2, x1, cy + h / 2)

    def _bboxes_overlap(a, b):
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

    for _idx, (city_name, (lon, lat)) in enumerate(city_list):
        ax.plot(
            lon,
            lat,
            "o",
            color=gold_hex,
            markersize=14,
            zorder=5,
            markeredgecolor=bg_hex,
            markeredgewidth=2,
        )

        # Smart label offset with collision avoidance.
        # Tries near + far offsets × 4 corners + center, to handle clustered cities.
        candidates = [
            (12, -18, "left"),  # below-right
            (12, 14, "left"),  # above-right
            (-12, -18, "right"),  # below-left
            (-12, 14, "right"),  # above-left
            (0, 22, "center"),  # above-center
            (0, -24, "center"),  # below-center
            # Extra far offsets for dense clusters
            (12, -38, "left"),  # far below-right
            (12, 34, "left"),  # far above-right
            (-12, -38, "right"),  # far below-left
            (-12, 34, "right"),  # far above-left
            (0, 42, "center"),  # far above-center
            (0, -44, "center"),  # far below-center
        ]

        # Prefer placement away from map center
        map_cx = (lon_range[0] + lon_range[1]) / 2
        map_cy = (lat_range[0] + lat_range[1]) / 2
        preferred_x = 1 if lon >= map_cx else -1
        preferred_y = -1 if lat >= map_cy else 1

        # Sort candidates by preference
        def _score_candidate(c, px=preferred_x, py=preferred_y):
            xo, yo, _ = c
            return -(xo * px + yo * py * 0.5)

        candidates.sort(key=_score_candidate)

        # Convert offset points to data coordinates for collision check
        pts_per_lon = fig.get_size_inches()[0] * fig.dpi / lon_span
        pts_per_lat = fig.get_size_inches()[1] * fig.dpi / lat_span

        # Per-label width estimate (Japanese full-width vs ASCII narrower)
        label_w_deg = _estimate_label_w_deg(city_name, 18, pts_per_lon)
        label_h_deg = 22 / pts_per_lat  # ~22pt vertical extent incl. padding

        # An earlier episode: per-city manual override (skip auto-placement)
        if city_name in city_offsets_override:
            ov = city_offsets_override[city_name]
            ov_x, ov_y = float(ov[0]), float(ov[1])
            ov_ha = ov[2] if len(ov) >= 3 else "left"
            label_lon_final = lon + ov_x / pts_per_lon
            label_lat_final = lat + ov_y / pts_per_lat
            placed_labels.append((label_lon_final, label_lat_final))
            placed_label_bboxes.append(
                _label_bbox(label_lon_final, label_lat_final, label_w_deg, label_h_deg, ov_ha)
            )
            _city_artist = ax.annotate(
                city_name,
                xy=(lon, lat),
                xytext=(ov_x, ov_y),
                textcoords="offset points",
                fontsize=18,
                fontweight="bold",
                color=white_hex,
                ha=ov_ha,
                zorder=6,
                **font_props,
            )
            city_label_artists.append(_city_artist)
            continue  # skip auto-candidate loop below

        best = candidates[0]
        best_min_dist = -1
        best_bbox = None
        for xo, yo, ha_c in candidates:
            label_lon = lon + xo / pts_per_lon
            label_lat = lat + yo / pts_per_lat
            bbox = _label_bbox(label_lon, label_lat, label_w_deg, label_h_deg, ha_c)

            # Bounds check — label bbox must fit inside the map frame
            if bbox[0] < lon_range[0] or bbox[2] > lon_range[1]:
                continue
            if bbox[1] < lat_range[0] or bbox[3] > lat_range[1]:
                continue
            # Skip candidates that overlap the legend rectangle
            if _in_legend(label_lon, label_lat):
                continue
            # Hard reject: overlap with any already-placed label's bbox
            if any(_bboxes_overlap(bbox, pb) for pb in placed_label_bboxes):
                continue
            # Check distance to all previously placed label centers
            min_d = float("inf")
            for pl_lon, pl_lat in placed_labels:
                d = ((label_lon - pl_lon) ** 2 + (label_lat - pl_lat) ** 2) ** 0.5
                min_d = min(min_d, d)
            # Also check distance to other city dots
            for other_name, (other_lon, other_lat) in city_list:
                if other_name == city_name:
                    continue
                d = ((label_lon - other_lon) ** 2 + (label_lat - other_lat) ** 2) ** 0.5
                min_d = min(min_d, d)
            if min_d > best_min_dist:
                best_min_dist = min_d
                best = (xo, yo, ha_c)
                best_bbox = bbox

        x_off, y_off, ha = best
        label_lon_final = lon + x_off / pts_per_lon
        label_lat_final = lat + y_off / pts_per_lat
        placed_labels.append((label_lon_final, label_lat_final))
        if best_bbox is not None:
            placed_label_bboxes.append(best_bbox)
        else:
            # No candidate passed all constraints — still record bbox for
            # the fallback placement to limit future collisions.
            placed_label_bboxes.append(
                _label_bbox(label_lon_final, label_lat_final, label_w_deg, label_h_deg, ha)
            )

        _city_artist = ax.annotate(
            city_name,
            xy=(lon, lat),
            xytext=(x_off, y_off),
            textcoords="offset points",
            fontsize=18,
            fontweight="bold",
            color=white_hex,
            ha=ha,
            zorder=6,
            **font_props,
        )
        city_label_artists.append(_city_artist)

    # Draw route labels with collision avoidance against city labels and other route labels
    # Estimate label size in data coordinates
    pts_per_lon = fig.get_size_inches()[0] * fig.dpi / lon_span
    pts_per_lat = fig.get_size_inches()[1] * fig.dpi / lat_span
    label_h_data = 20 / pts_per_lat  # approx label height in data coords
    placed_route_labels = []
    placed_route_label_bboxes = []  # C: bbox-aware overlap check for route labels
    route_label_artists = []  # track artists for collision check
    # auto-fix Stage 1: route_label upper exclusion zone (default 5%, raise to 18% to avoid title)
    _route_label_top_padding = visual.get("_route_label_top_padding", 0.05)

    def _bezier_point(sx, sy, cx, cy, ex, ey, t):
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t**2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t**2 * ey
        return bx, by

    def _try_candidate(
        test_x,
        test_y,
        rl_w_data,
        rl_h_data,
        lat_range,
        lat_span,
        _route_label_top_padding,
        placed_label_bboxes,
        placed_route_label_bboxes,
        placed_labels,
        city_list,
        placed_route_labels,
    ):
        """Return (bbox, min_dist) if candidate position is acceptable, else (None, -1)."""
        if (
            test_y < lat_range[0] + lat_span * 0.05
            or test_y > lat_range[1] - lat_span * _route_label_top_padding
        ):
            return None, -1
        cand_bbox = (
            test_x - rl_w_data / 2,
            test_y - rl_h_data / 2,
            test_x + rl_w_data / 2,
            test_y + rl_h_data / 2,
        )
        if any(_bboxes_overlap(cand_bbox, pb) for pb in placed_label_bboxes):
            return None, -1
        if any(_bboxes_overlap(cand_bbox, pb) for pb in placed_route_label_bboxes):
            return None, -1
        if _in_legend(test_x, test_y):
            return None, -1
        min_d = float("inf")
        for pl_lon, pl_lat in placed_labels:
            d = ((test_x - pl_lon) ** 2 + (test_y - pl_lat) ** 2) ** 0.5
            min_d = min(min_d, d)
        for _, (clon, clat) in city_list:
            d = ((test_x - clon) ** 2 + (test_y - clat) ** 2) ** 0.5
            min_d = min(min_d, d)
        for rl_x, rl_y in placed_route_labels:
            d = ((test_x - rl_x) ** 2 + (test_y - rl_y) ** 2) ** 0.5
            min_d = min(min_d, d)
        return cand_bbox, min_d

    leader_lines = []  # A: (start_x, start_y, end_x, end_y, color) for displaced labels

    for rl in route_labels:
        lt = rl["text"]
        lc = rl["color"]
        sx_r, sy_r = rl["sx"], rl["sy"]
        cx_r, cy_r = rl["cx"], rl["cy"]
        ex_r, ey_r = rl["ex"], rl["ey"]
        direction = rl["direction"]

        # hybrid: estimate route label bbox for overlap detection.
        # Add 20% safety margin to width to account for boxstyle round padding
        # and font rendering variance (avoids false-pass on borderline overlaps).
        rl_w_data = _estimate_label_w_deg(lt, 16, pts_per_lon) * 1.20
        rl_h_data = label_h_data * 1.8  # boxstyle round padding + safety margin

        # Curve midpoint (anchor for leader line if label gets displaced)
        anchor_x, anchor_y = _bezier_point(sx_r, sy_r, cx_r, cy_r, ex_r, ey_r, 0.5)

        best_pos = None
        best_min_dist = -1
        best_bbox_route = None
        used_displacement = False

        # Manual override: scene_def label_offset (data coords, [x, y]) — skip auto placement
        manual_offset = rl.get("label_offset")
        if (
            manual_offset is not None
            and isinstance(manual_offset, (list, tuple))
            and len(manual_offset) == 2
        ):
            best_pos = (anchor_x + manual_offset[0], anchor_y + manual_offset[1])
            best_bbox_route = (
                best_pos[0] - rl_w_data / 2,
                best_pos[1] - rl_h_data / 2,
                best_pos[0] + rl_w_data / 2,
                best_pos[1] + rl_h_data / 2,
            )
            best_min_dist = 999  # bypass collision-based selection below
            displacement = (manual_offset[0] ** 2 + manual_offset[1] ** 2) ** 0.5
            used_displacement = displacement > label_h_data * 1.5

        # Phase B: try along-curve placements first (preserves visual correspondence)
        t_candidates = [0.5, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75]
        perp_offsets = [
            lat_span * 0.04 * direction,
            lat_span * 0.04 * (-direction),
            lat_span * 0.08 * direction,
            lat_span * 0.08 * (-direction),
        ]
        for t_val in t_candidates:
            bx_t, by_t = _bezier_point(sx_r, sy_r, cx_r, cy_r, ex_r, ey_r, t_val)
            for perp_off in perp_offsets:
                test_x = bx_t
                test_y = by_t + perp_off
                cand_bbox, min_d = _try_candidate(
                    test_x,
                    test_y,
                    rl_w_data,
                    rl_h_data,
                    lat_range,
                    lat_span,
                    _route_label_top_padding,
                    placed_label_bboxes,
                    placed_route_label_bboxes,
                    placed_labels,
                    city_list,
                    placed_route_labels,
                )
                if cand_bbox is None:
                    continue
                if min_d > best_min_dist:
                    best_min_dist = min_d
                    best_pos = (test_x, test_y)
                    best_bbox_route = cand_bbox

        # Phase C (displacement fallback): if Phase B found nothing acceptable,
        # widen search to displaced positions with bigger offsets, and mark for leader line.
        if best_min_dist < 0:
            v_offsets = [
                0,
                label_h_data * 2,
                -label_h_data * 2,
                label_h_data * 4,
                -label_h_data * 4,
                label_h_data * 6,
                -label_h_data * 6,
                label_h_data * 8,
                -label_h_data * 8,
            ]
            h_offsets = [0, rl_w_data * 0.4, -rl_w_data * 0.4]
            for dx in h_offsets:
                for dy in v_offsets:
                    test_x = anchor_x + dx
                    test_y = anchor_y + dy
                    cand_bbox, min_d = _try_candidate(
                        test_x,
                        test_y,
                        rl_w_data,
                        rl_h_data,
                        lat_range,
                        lat_span,
                        _route_label_top_padding,
                        placed_label_bboxes,
                        placed_route_label_bboxes,
                        placed_labels,
                        city_list,
                        placed_route_labels,
                    )
                    if cand_bbox is None:
                        continue
                    if min_d > best_min_dist:
                        best_min_dist = min_d
                        best_pos = (test_x, test_y)
                        best_bbox_route = cand_bbox
                        used_displacement = True

        # Final fallback: forced position below top exclusion zone
        if best_min_dist < 0 or best_pos is None:
            forced_y = lat_range[1] - lat_span * (_route_label_top_padding + 0.02)
            best_pos = (anchor_x, forced_y)
            best_bbox_route = (
                best_pos[0] - rl_w_data / 2,
                forced_y - rl_h_data / 2,
                best_pos[0] + rl_w_data / 2,
                forced_y + rl_h_data / 2,
            )
            used_displacement = True

        # A: if label is displaced from its curve, queue a leader line
        # (will be drawn AFTER all labels placed so it appears below them).
        displacement = ((best_pos[0] - anchor_x) ** 2 + (best_pos[1] - anchor_y) ** 2) ** 0.5
        if used_displacement and displacement > label_h_data * 1.5:
            leader_lines.append((anchor_x, anchor_y, best_pos[0], best_pos[1], lc))

        placed_route_labels.append(best_pos)
        if best_bbox_route is not None:
            placed_route_label_bboxes.append(best_bbox_route)
        _route_label_artist = ax.text(
            best_pos[0],
            best_pos[1],
            lt,
            fontsize=16,
            color=lc,
            ha="center",
            va="center",
            alpha=0.95,
            zorder=6,
            fontweight="bold",
            **font_props,
            bbox=dict(
                boxstyle="round,pad=0.4", facecolor=bg_hex, alpha=0.8, edgecolor=lc, linewidth=0.5
            ),
        )
        route_label_artists.append(_route_label_artist)

    # ある回 B: 経路ラベル artist を自分の曲線に結び直す。この loop は route_labels を
    # 1 件につき必ず 1 artist 追加する (途中の continue は候補位置の内側 loop のもの)
    # ので index が一致する。
    for _rl, _rl_artist in zip(route_labels, route_label_artists, strict=True):
        _ci = _rl.get("curve_idx", -1)
        if 0 <= _ci < len(route_curves):
            route_curves[_ci]["owner"] = _rl_artist

    # A: draw queued leader lines (curve anchor → displaced label).
    # zorder=5 so they sit below route labels (6) but above arrows (3).
    for ax_x, ay, lx_end, ly_end, lc_line in leader_lines:
        ax.plot(
            [ax_x, lx_end],
            [ay, ly_end],
            color=lc_line,
            linewidth=0.7,
            alpha=0.55,
            linestyle="--",
            zorder=5,
        )

    # Title (inside plot area, top center)
    title_artist = None  # track for collision check
    title_fontsize = visual.get("_title_fontsize", 28)  # auto-fix Stage 3 may override
    if title:
        title_y = lat_range[1] - lat_span * 0.06
        title_artist = ax.text(
            (lon_range[0] + lon_range[1]) / 2,
            title_y,
            title,
            fontsize=title_fontsize,
            color=gold_hex,
            ha="center",
            va="top",
            fontweight="bold",
            zorder=7,
            **font_props,
        )

    # Legend — use custom labels from visual spec if provided,
    # otherwise fall back to default person-journey labels.
    _DEFAULT_LEGEND_LABELS = {
        "origin": "生誕",
        "education": "留学",
        "career": "研究",
        "wandering": "遍歴",
        "exile": "亡命",
        "final": "最期の地",
    }
    _LEGEND_LABELS = visual.get("legend_labels", _DEFAULT_LEGEND_LABELS)
    legend_items = []
    seen_labels = set()
    for cat in ["origin", "education", "career", "wandering", "exile", "final"]:
        if cat in legend_categories:
            lbl = _LEGEND_LABELS.get(cat, cat)
            if lbl not in seen_labels:
                legend_items.append(mpatches.Patch(color=_ROUTE_CATEGORY_COLORS[cat], label=lbl))
                seen_labels.add(lbl)

    # Colour separation: a legend can only be read if its colours are actually
    # distinguishable from each other and from the background. Checked against the
    # categories THIS scene uses, so unrelated near-neighbours in the palette do
    # not warn on a scene that never draws them together.
    for _prob in check_route_palette_separation(categories=sorted(legend_categories)):
        print(f"    [WARN] route_map legend color: {_prob['summary']}")

    legend_artist = None  # track for collision check
    if legend_items:
        legend_prop = FontProperties(fname=font_path, size=18) if font_path else {"size": 18}
        legend_artist = ax.legend(
            handles=legend_items,
            loc=legend_loc,
            bbox_to_anchor=legend_bbox,
            fontsize=18,
            facecolor=bg_hex,
            edgecolor=line_color,
            labelcolor=white_hex,
            prop=legend_prop,
            borderpad=0.8,
            handlelength=1.5,
        )
        legend_artist.get_frame().set_alpha(0.85)

    # Hide axes
    ax.spines[:].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Reserve bottom 220/1080 (≈20.4%) for subtitle overlay.
    # Axis content is constrained to the top ~79.6% of the figure, ensuring
    # city markers/labels never collide with subtitles rendered on top.
    # NOTE: bbox_inches="tight" would crop the reserved margin away,
    # so we use the full figsize instead.
    SUBTITLE_SAFE_FRAC = 220 / 1080  # ≈ 0.2037
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=SUBTITLE_SAFE_FRAC)

    # Layer 3: collision check (runs whether or not preflight ran).
    # Reports printed as WARN here; preflight is responsible for STOP/auto-fix.
    collision_reports = _check_route_map_collisions(
        fig,
        title_artist,
        route_label_artists,
        legend_artist,
        city_label_artists,
        ax=ax,
        city_dots=cities,
        route_curves=route_curves,
        # misreading: the shot's crop decides what is actually visible, so the
        # clipping check needs to know which effect will be applied.
        effect=effect,
    )
    for rep in collision_reports:
        _tag = "WARN" if rep.get("severity", "error") == "error" else "ADVISORY"
        print(f"    [{_tag}] route_map collision: {rep['summary']}")
        print(f"           suggest: {rep['suggestion']}")

    if preflight_only:
        plt.close(fig)
        return collision_reports

    # Save as temp PNG then apply Ken Burns
    temp_png = output_path.replace(".mp4", "_map.png")
    fig.savefig(temp_png, dpi=200, facecolor=bg_hex)
    plt.close()

    try:
        generate_ken_burns(
            temp_png, output_path, duration, effect=effect, width=width, height=height, fps=fps
        )
    finally:
        if os.path.exists(temp_png):
            os.remove(temp_png)
    return collision_reports


def _apply_route_map_auto_fix_stage(
    visual: dict, stage: int, reports: list | None = None, attempt: int = 0
) -> tuple[dict, str]:
    """ auto-fix: mutate visual for the given stage. Returns (new_visual, description).

    `attempt` lets a stage be retried from the SAME base with a different move
    (stage 4 rotates the legend one further corner per attempt) -- necessary now
    that the caller discards non-improving candidates, so a retried stage would
    otherwise recompute the identical mutation.
    `reports` are the collisions measured on `visual`; stage 5 needs them because
    it moves the specific labels they name.
    """
    import copy

    new_visual = copy.deepcopy(visual)
    if stage == 1:
        # Stage 1 (label avoidance): widen route_label top exclusion zone so labels
        # avoid the band where the title sits.
        new_visual["_route_label_top_padding"] = 0.18
        return new_visual, "route_label top exclusion 5%->18% (labels avoid title band)"
    if stage == 2:
        # Stage 2 (bounds expansion): grow bounds.lat[1] upward by 20% of current span.
        cities = new_visual.get("cities", {})
        bounds = new_visual.get("bounds")
        if not bounds and cities:
            lons = [coord[0] for coord in cities.values()]
            lats = [coord[1] for coord in cities.values()]
            lon_min, lon_max = min(lons), max(lons)
            lat_min, lat_max = min(lats), max(lats)
            # Materialise the SAME frame the auto path computes, on BOTH axes.
            # Writing only "lat" (as this stage used to) leaves the renderer to
            # resolve `bounds.get("lon", _DEFAULT_BOUNDS["lon"])` = the hardcoded
            # world default [-85, 45], silently reframing the map the auto-fix was
            # only supposed to nudge vertically. An earlier episode shipped exactly that way and
            # its `_route_map_auto_fix_log` shows this stage wrote it.
            map_scale = max(lon_max - lon_min, lat_max - lat_min)
            lon_pad = _auto_bounds_pad(lon_max - lon_min, map_scale, _PAD_FLOOR_LON, _PAD_MIN_LON)
            lat_pad = _auto_bounds_pad(lat_max - lat_min, map_scale, _PAD_FLOOR_LAT, _PAD_MIN_LAT)
            bounds = {
                "lon": [lon_min - lon_pad, lon_max + lon_pad],
                "lat": [lat_min - lat_pad, lat_max + lat_pad],
            }
            new_visual["bounds"] = bounds
        if bounds and "lat" in bounds:
            lat_min, lat_max = bounds["lat"]
            span = lat_max - lat_min
            new_visual["bounds"]["lat"] = [lat_min, lat_max + span * 0.20]
            return new_visual, (
                f"bounds.lat[1] expanded {lat_max:.1f}->{lat_max + span * 0.20:.1f} (+20% of span)"
            )
        return new_visual, "bounds expansion skipped (no lat info)"
    if stage == 3:
        # Stage 3 (fontsize reduction): shrink title fontsize 28 -> 22.
        new_visual["_title_fontsize"] = 22
        return new_visual, "title fontsize 28->22"
    if stage == 4:
        # Stage 4 (legend relocation): cycle legend_loc through corners to avoid
        # route_label / city overlap. Each invocation rotates one position:
        # upper right -> lower right -> lower left -> upper left.
        rotation = ["upper right", "lower right", "lower left", "upper left"]
        anchors = {
            "upper right": [0.92, 0.98],
            "lower right": [0.92, 0.30],
            "lower left": [0.08, 0.30],
            "upper left": [0.08, 0.98],
        }
        cur_loc = new_visual.get("legend_loc", "upper right")
        try:
            next_loc = rotation[(rotation.index(cur_loc) + 1 + attempt) % 4]
        except ValueError:
            next_loc = rotation[(1 + attempt) % 4]  # unknown current → start from lower right
        new_visual["legend_loc"] = next_loc
        new_visual["legend_bbox_to_anchor"] = anchors[next_loc]
        return new_visual, f"legend_loc {cur_loc!r}->{next_loc!r}"
    if stage == 5:
        # Stage 5: move the city labels the reports NAME, using
        # the displacement measured at detection time. Stages 1-4 can only widen a
        # margin, stretch the bounds, shrink the title or move the legend -- none of
        # them touches a city label, which is what 6 of the 7 real collisions in the
        # repo are about and what every suggestion string tells the human to edit.
        # Writing a city_offsets entry pins that label (auto-placement is skipped for
        # it), so we start from the offset auto-placement had chosen.
        pushes: dict = {}
        for rep in reports or []:
            fix = (rep or {}).get("city_fix")
            if not fix or not fix.get("city"):
                continue
            px, py = fix["push_pts"]
            prev = pushes.get(fix["city"])
            # One city can collide with two things; opposite pushes would cancel to
            # a no-op, so keep the single largest move and let the re-check judge it.
            if prev is None or (px * px + py * py) > (prev[0] ** 2 + prev[1] ** 2):
                pushes[fix["city"]] = (px, py, fix)
        if not pushes:
            return new_visual, "no city label named by the reports (stage 5 skipped)"
        offsets = dict(new_visual.get("city_offsets") or {})
        moved = []
        for city, (px, py, fix) in pushes.items():
            cur = offsets.get(city)
            if cur and len(cur) >= 2:
                base_x, base_y = float(cur[0]), float(cur[1])
                ha = cur[2] if len(cur) >= 3 else fix["city_ha"]
            else:
                base_x, base_y = fix["city_offset_pts"]
                ha = fix["city_ha"]
            offsets[city] = [round(base_x + px, 1), round(base_y + py, 1), ha]
            moved.append(f"{city}({px:+.0f},{py:+.0f})")
        new_visual["city_offsets"] = offsets
        return new_visual, "city_offsets nudge " + " ".join(moved)
    return new_visual, f"unknown stage {stage}"


def route_map_preflight(
    scene_def_path: str,
    allow: bool = False,
    auto_fix: bool = False,
    advisory_out: list | None = None,
) -> dict:
    """ Layer 2: pre-render collision check for all route_map visuals.

    Loads scene_definition.json, iterates scenes whose visual.type == "route_map",
    calls generate_route_map(..., preflight_only=True) on each, and collects
    collision reports.

    With auto_fix=True, attempts a 5-stage repair sequence per affected scene:
      Stage 1: widen route_label top exclusion zone to avoid title band
      Stage 2: expand bounds.lat[1] upward by 20% of span
      Stage 3: reduce title fontsize 28 -> 22
      Stage 4: rotate legend_loc through the four corners (up to 3 tries)
      Stage 5: nudge the city labels the reports name, via city_offsets
    The search is a greedy hill-climb: each candidate is re-checked and adopted
    ONLY if it strictly reduces the collision count, otherwise it is discarded and
    the next stage starts from the best state so far. Whatever improvement is
    found -- full or partial -- is persisted to scene_definition.json and logged
    under the top-level `_route_map_auto_fix_log` block; residual collisions are
    still returned as unresolved.

    A candidate that clears collisions is VETOED anyway if it makes a city label
    read as a different city (`_check_label_ownership`). If every collision-clearing
    candidate is vetoed, the scene is left unfixed and reported unresolved: a
    persisted frame that captions the wrong city is worse than a build that stops
    on a collision, because the collision is visible to the pipeline and the
    mislabelled city is only visible to a human watching the render.

    Args:
        scene_def_path: path to scene_definition.json
        allow: if True, return reports without raising (caller decides STOP)
        auto_fix: if True, mutate scene_def visual params and persist on success
        advisory_out: if given, every non-blocking finding (an earlier episode label ownership /
            line-through-label) is appended as {"scene_id", "report"}. The return
            value stays blocking-only so existing callers keep their semantics,
            but the pipeline needs the count for its advisory roll-up -- an
            advisory that only ever reaches stdout is one a reader scanning the
            'Pipeline Complete' tail will miss (an earlier episode lesson).

    Returns:
        dict {scene_id: [collision_report, ...]} for unresolved BLOCKING collisions.
        Empty dict means all clean (or all auto-fixed); advisories never appear here.
    """
    if not os.path.exists(scene_def_path):
        print(f"[route-map preflight] scene_definition.json not found: {scene_def_path}")
        return {}

    with open(scene_def_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    # scene_definition.json structure: sd["sections"][i]["scenes"][j]
    # Collect (section_idx, scene_idx, scene) for every route_map scene.
    route_scenes: list = []
    for sec_idx, section in enumerate(scene_def.get("sections", [])):
        for sc_idx, sc in enumerate(section.get("scenes", [])):
            v = sc.get("visual")
            if isinstance(v, dict) and v.get("type") == "route_map":
                route_scenes.append((sec_idx, sc_idx, sc))
    if not route_scenes:
        return {}

    print(f"\n[route-map preflight] checking {len(route_scenes)} route_map scene(s)...")

    unresolved: dict = {}
    fix_log: list[dict] = []
    # **検査できなかった scene は「衝突なし」ではない。** 例外を握って continue する
    # だけだと、この STOP ゲートは 1 枚も検査せずに素通りできてしまう (2026-08-06 の
    # 再検証で、preflight の実レンダが ImportError を投げても build がそのまま進む
    # ことを確認)。ある回の Gate 2 と同じ扱いにする -- 名指しで数えて表に出す。
    unevaluated: list[tuple[str, str]] = []

    for sec_idx, sc_idx, scene in route_scenes:
        scene_id = scene.get("scene_id") or scene.get("id") or f"scene_{sec_idx}_{sc_idx}"
        visual = scene["visual"]
        try:
            reports = generate_route_map(visual, "", 0.0, preflight_only=True)
        except Exception as e:
            detail = f"{type(e).__name__}: {e}"
            print(f"  {scene_id}: preflight render failed: {detail}")
            unevaluated.append((scene_id, detail))
            continue

        if not reports:
            print(f"  {scene_id}: clean")
            continue

        _blocking = [r for r in reports if r.get("severity", "error") == "error"]
        _advisory = [r for r in reports if r.get("severity", "error") != "error"]
        print(
            f"  {scene_id}: {len(_blocking)} collision(s), "
            f"{len(_advisory)} advisory finding(s) detected"
        )
        for rep in _blocking:
            print(f"    - {rep['summary']}")
            print(f"      suggest: {rep['suggestion']}")
        for rep in _advisory:
            print(f"    - [advisory] {rep['summary']}")
            print(f"      suggest: {rep['suggestion']}")

        if not auto_fix or not _blocking:
            # Advisory findings do NOT stop the build. They fire on
            # 10 / 21 of the 37 episodes that own a route_map, and spot-checking
            # the renders shows they are real but long-tolerated defects -- making
            # them blocking would halt a rebuild of half the shipped inventory.
            #
            # They also do not TRIGGER the auto-fix on their own. The five repair
            # stages move margins, latitude, title size, legend corner and city
            # offsets -- blunt levers aimed at bbox overlap. Letting an advisory
            # start that search would rewrite scene_definition.json for the 21
            # episodes that are currently "clean" by the blocking definition, to
            # chase a metric those stages were never designed to move.
            if _blocking:
                unresolved[scene_id] = _blocking
            if advisory_out is not None:
                advisory_out.extend({"scene_id": scene_id, "report": r} for r in _advisory)
            continue

        # auto-fix: greedy hill-climb. A candidate is adopted ONLY if it strictly
        # reduces the collision count; otherwise it is discarded and the next stage
        # starts from the best state so far.
        #
        # The original loop adopted every mutation unconditionally, so a stage that
        # made things worse was kept and the remaining stages searched from the
        # damaged state. Measured over the 7 colliding scenes in the repo: an earlier episode
        # went 1 -> 5 collisions at stage 2 and burned three more stages there, and
        # 3 of 7 scenes were made strictly worse at some point. Rejecting
        # non-improving stages does not merely avoid that damage -- it takes the
        # auto-fix from 2/7 to 4/7 resolved, because an earlier episode (city vs legend)
        # are fixed by the legend rotation ALONE and the old loop only ever reached
        # stage 4 on top of stages 1-3, by which point the map had been reframed.
        # "Adopt if not worse" (<=) was measured too and it re-breaks those two:
        # strict improvement is the rule that works.
        def _score(reps):
            """(blocking, advisory) counts. The auto-fix OBJECTIVE is the FIRST only.

            The second is printed, never optimised. Two richer objectives were
            implemented and measured against the 7 auto-fixable scenes, and both
            were dropped:

              1. "Clear a collision AND add no new advisory" -- 7/7 -> 5/7.
                 004_ramanujan (3 collisions) and 030_takagi (1) lose their fix.
              2. Lexicographic (fewer collisions, then fewer advisories). Adopting
                 a stage purely for an advisory tie-break moves `best_visual`, and
                 the remaining stages then search from somewhere else:
                 004_ramanujan went 3 -> 3.

            Both failed for the same reason: they steer on an advisory COUNT, which
            lumps "a line crosses a label" (ugly) together with "this label now
            names the wrong city" (wrong). `_ownership_veto` is not an objective
            -- it is a veto on one specific, measurable harm, and it costs nothing
            on the 7 scenes precisely because it is that narrow.
            """
            b = sum(1 for r in reps if r.get("severity", "error") == "error")
            return b, len(reps) - b

        best_visual, best_reports = visual, reports
        accepted_stages: list[str] = []
        vetoed_stages: list[str] = []
        exhausted: set = set()
        for stage, attempt in ((1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1)):
            if stage in exhausted:
                continue
            # Stage 5 nudges the city labels the reports NAME, so it must be fed the
            # blocking collisions only. Handing it the advisory findings as well
            # (ownership reports also carry a `city_fix` lever) silently changes which
            # cities it moves: measured, that alone took the auto-fix from 7/7 to 5/7
            # on the repo's colliding scenes -- 004_ramanujan and 030_takagi stopped
            # resolving. The new checks are meant to observe this search, not steer it.
            _repair_input = [r for r in best_reports if r.get("severity", "error") == "error"]
            candidate, descr = _apply_route_map_auto_fix_stage(
                best_visual, stage, _repair_input, attempt
            )
            if candidate == best_visual:
                continue  # stage had nothing to change
            try:
                stage_reports = generate_route_map(candidate, "", 0.0, preflight_only=True) or []
            except Exception as e:
                # A candidate that cannot render is a rejected candidate, not a
                # silent pass-through of the previous reports.
                print(f"    stage {stage} render failed, discarded: {type(e).__name__}: {e}")
                continue
            _cand_b, _cand_a = _score(stage_reports)
            _best_b, _best_a = _score(best_reports)
            # Blocking collisions ONLY -- byte-for-byte the rule an earlier episode calibrated.
            _improved = _cand_b < _best_b
            # ...but a collision cleared by making a label name the wrong city is
            # not a fix. Veto BEFORE adoption so `best_visual` never holds, and
            # never gets persisted from, a misleading layout.
            _newly_ambiguous = _ownership_veto(stage_reports, best_reports) if _improved else []
            if _improved and _newly_ambiguous:
                _misread = ", ".join(
                    f"{c} reads as {o} (ownership {b:.2f}->{r:.2f})"
                    if b != float("inf")
                    else f"{c} reads as {o} (ownership ->{r:.2f})"
                    for c, r, b, o in _newly_ambiguous
                )
                print(
                    f"    stage {stage} ({descr}): clears {_best_b}->{_cand_b} collision(s) "
                    f"but {_misread} -- REJECTED (a frame that names the wrong city "
                    f"is worse than an unresolved collision)"
                )
                vetoed_stages.append(f"stage{stage}: {descr} -> {_misread}")
                if stage == 5:
                    exhausted.add(5)
                continue
            if not _improved:
                print(
                    f"    stage {stage} ({descr}): {_cand_b} collision(s) / "
                    f"{_cand_a} advisory - no improvement, discarded"
                )
                if stage == 5:
                    # Stage 5 is driven by best_reports; unchanged input would
                    # recompute the identical nudge.
                    exhausted.add(5)
                continue
            print(
                f"    stage {stage} ({descr}): {_best_b}/{_best_a} -> "
                f"{_cand_b}/{_cand_a} (collision/advisory), adopted"
            )
            best_visual, best_reports = candidate, stage_reports
            accepted_stages.append(f"stage{stage}: {descr}")
            if _cand_b == 0:
                print(f"    RESOLVED for {scene_id}")
                break

        # Persist any improvement, even a partial one: reverting a 3 -> 1 back to 3
        # throws away work the human would otherwise redo by hand. Residual
        # collisions are still reported as unresolved so the build stops.
        if accepted_stages or best_visual is not visual:
            scene_def["sections"][sec_idx]["scenes"][sc_idx]["visual"] = best_visual
            fix_log.append(
                {
                    "scene_id": scene_id,
                    "stages_applied": accepted_stages,
                    # Why the search stopped where it did. Without this, a partial
                    # fix looks like "the stages ran out" when in fact a working
                    # candidate was refused on purpose.
                    "stages_vetoed_label_ownership": vetoed_stages,
                    "original_reports": [r["summary"] for r in reports],
                    "residual_reports": [r["summary"] for r in best_reports],
                }
            )
        _residual_blocking = [r for r in best_reports if r.get("severity", "error") == "error"]
        _residual_advisory = [r for r in best_reports if r.get("severity", "error") != "error"]
        if _residual_blocking:
            if vetoed_stages:
                # Say DECLINED, not "could not clear". The auto-fix had a candidate
                # that reached 0 collisions and refused it; a reader who is told
                # "could not clear" goes looking for a missing repair stage.
                print(
                    f"    auto-fix DECLINED to fix {scene_id}: "
                    f"{len(_residual_blocking)} collision(s) remain because every "
                    f"candidate that cleared them made a label read as another city "
                    f"({len(vetoed_stages)} stage(s) vetoed). Fix by hand: widen "
                    f"bounds, or set visual.city_offsets so the labels separate "
                    f"without crowding another city's dot."
                )
            else:
                print(
                    f"    auto-fix could not clear {scene_id}: "
                    f"{_score(reports)[0]} -> {len(_residual_blocking)} collision(s) remain"
                )
            unresolved[scene_id] = _residual_blocking
        if advisory_out is not None:
            advisory_out.extend({"scene_id": scene_id, "report": r} for r in _residual_advisory)
        if _residual_advisory:
            # Not a build stopper, but say it out loud: "auto-fixed and persisted"
            # was exactly the line that made an earlier episode look finished while the label
            # sat on the wrong dot.
            print(
                f"    {scene_id}: {len(_residual_advisory)} advisory finding(s) remain "
                f"(label ownership / line through label) -- review the render"
            )

    # Persist auto-fix changes (if any)
    if fix_log:
        existing_log = scene_def.get("_route_map_auto_fix_log", [])
        existing_log.extend(fix_log)
        scene_def["_route_map_auto_fix_log"] = existing_log
        with open(scene_def_path, "w", encoding="utf-8") as f:
            json.dump(scene_def, f, ensure_ascii=False, indent=2)
        print(f"[route-map preflight] {len(fix_log)} scene(s) auto-fixed and persisted")

    # 検査できなかった scene を advisory へ載せる。呼び出し側 (pipeline) は
    # `advisory_out` の件数を最終サマリの roll-up に積むので、ここに載せないと
    # 「この scene は見ていない」という事実がどこにも残らない。
    if unevaluated:
        print(
            f"\n[route-map preflight] {len(unevaluated)} scene(s) を検査できませんでした "
            f"(衝突が無いのではなく、**見ていません**):"
        )
        for scene_id, detail in unevaluated:
            print(f"  - {scene_id}: {detail}")
        print("  レンダが通らない原因を直してから、この scene の地図を目で確認してください。")
        if advisory_out is not None:
            advisory_out.extend(
                {
                    "scene_id": scene_id,
                    "report": {
                        "type": "preflight_unevaluated",
                        "severity": "warning",
                        "summary": f"preflight を実行できませんでした ({detail})",
                    },
                }
                for scene_id, detail in unevaluated
            )

    if advisory_out:
        _n_own = sum(1 for a in advisory_out if a["report"]["type"] == "city_label_ownership")
        _n_uneval = sum(1 for a in advisory_out if a["report"]["type"] == "preflight_unevaluated")
        _n_line = len(advisory_out) - _n_own - _n_uneval
        _parts = [f"{_n_own} label ownership", f"{_n_line} line-through-label"]
        if _n_uneval:
            _parts.append(f"{_n_uneval} 未検査")
        print(
            f"[route-map preflight] {len(advisory_out)} advisory finding(s): "
            + ", ".join(_parts)
            + ". These do not stop the build -- look at the rendered map."
        )

    if unresolved and not allow:
        print(f"\n[route-map preflight] FAIL: {len(unresolved)} scene(s) still have collisions.")
        print("  Re-run with --auto-fix-route-collisions or --allow-route-collision,")
        print("  or edit scene_definition.json manually following the suggestions above.")

    return unresolved
