"""
least_squares_orbit.py — 最小二乗法とケレスの軌道予測 for 数学史記

1801年、ピアッツィの41日間の観測データからガウスがケレスの軌道を計算。
最小二乗法によるフィッティングと軌道予測を可視化。
SymPy連携でフィッティング計算を実行。

Modes:
    fitting - データ点への最小二乗フィッティングのアニメーション。
              ノイズ付きデータ点 → 直線フィット → 二次曲線フィットの段階表示。
              最小二乗法の基本原理を視覚化。
    orbit   - 観測データからケレスの軌道楕円を推定するプロセス。
              太陽を焦点とする楕円軌道上の観測弧（9度）→ 全軌道の推定。
              予測位置にケレスが再発見される劇的な瞬間。

Duration-aware: reads target duration from _manim_params.json.

Used by: Episode 010 (Gauss)
"""

import math

from manim import (
    DOWN,
    LEFT,
    UP,
    YELLOW,
    Arrow,
    Create,
    DashedLine,
    Dot,
    Ellipse,
    FadeIn,
    GrowArrow,
    Line,
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
    FONT,
    TEXT_DIM,
    TEXT_WHITE,
    load_params,
)

config.background_color = BG_COLOR


def _calc_wait_scale(duration, anim_time, default_wait_total):
    if default_wait_total <= 0:
        return 1.0
    target_waits = max(duration - anim_time, default_wait_total * 0.3)
    return max(0.3, min(target_waits / default_wait_total, 5.0))


class LeastSquaresOrbit(Scene):
    """Least squares fitting and Ceres orbit prediction."""

    def construct(self):
        self.camera.background_color = BG_COLOR
        params = load_params()
        mode = params.get("mode", "fitting")
        self._duration = params.get("duration", 18)

        if mode == "orbit":
            self._build_orbit()
        else:
            self._build_fitting()

    # ------------------------------------------------------------------
    # Mode A: fitting
    # ------------------------------------------------------------------
    def _build_fitting(self):
        duration = self._duration

        title = Text(
            "最小二乗法 ── データから真実を引き出す",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.8 + 0.8 + 1.2 + 1.2 + 0.8
        default_waits = 0.5 + 0.8 + 0.8 + 0.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        from manim import Axes

        axes = Axes(
            x_range=[-0.5, 6.5, 1],
            y_range=[-1, 8, 2],
            x_length=9,
            y_length=5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2},
            tips=False,
        )
        axes.move_to([0, -0.2, 0])
        self.play(Create(axes), run_time=0.8)
        self.wait(0.3 * ws)

        # Noisy data points (linear trend y = 1.2x + 0.5 with noise)
        import random

        random.seed(42)
        data_x = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
        data_y = [1.2 * x + 0.5 + random.gauss(0, 0.5) for x in data_x]

        dots = VGroup()
        for x, y in zip(data_x, data_y, strict=False):
            d = Dot(axes.c2p(x, y), color=ACCENT_CYAN, radius=0.07)
            dots.add(d)

        obs_label = Text(
            "観測データ（誤差を含む）",
            font=FONT,
            font_size=16,
            color=TEXT_DIM,
        )
        obs_label.move_to([5.5, 1.5, 0])

        self.play(FadeIn(dots), FadeIn(obs_label), run_time=0.8)
        self.wait(0.5 * ws)

        # Least squares fit line (compute manually)
        n = len(data_x)
        sx = sum(data_x)
        sy = sum(data_y)
        sxx = sum(x * x for x in data_x)
        sxy = sum(x * y for x, y in zip(data_x, data_y, strict=False))
        slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        intercept = (sy - slope * sx) / n

        fit_line = Line(
            axes.c2p(0, intercept),
            axes.c2p(6, slope * 6 + intercept),
            color=ACCENT_GOLD,
            stroke_width=3,
        )
        fit_label = MathTex(
            r"y = ax + b",
            font_size=26,
            color=ACCENT_GOLD,
        )
        fit_label.move_to(axes.c2p(5.5, slope * 5.5 + intercept) + [0.5, 0.4, 0])

        self.play(Create(fit_line), FadeIn(fit_label), run_time=1.2)
        self.wait(0.5 * ws)

        # Show residuals
        residuals = VGroup()
        for x, y in zip(data_x, data_y, strict=False):
            y_fit = slope * x + intercept
            res_line = DashedLine(
                axes.c2p(x, y),
                axes.c2p(x, y_fit),
                color=ACCENT_PINK,
                stroke_width=1.5,
                dash_length=0.08,
            )
            residuals.add(res_line)

        res_label = Text(
            "残差の二乗和を最小化",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        res_label.move_to([5.5, -0.5, 0])

        self.play(FadeIn(residuals), FadeIn(res_label), run_time=1.2)
        self.wait(0.5 * ws)

        # Formula - placed right of axes, below title, above fit_label
        formula = MathTex(
            r"\min \sum_{i=1}^{n} (y_i - f(x_i))^2",
            font_size=28,
            color=TEXT_WHITE,
        )
        formula.move_to([5.5, 0.3, 0])
        self.play(FadeIn(formula), run_time=0.8)
        self.wait(max(duration - anim_time - 1.0, 1.0))

    # ------------------------------------------------------------------
    # Mode B: orbit
    # ------------------------------------------------------------------
    def _build_orbit(self):
        duration = self._duration

        title = Text(
            "ケレスの軌道予測（1801年）",
            font=FONT,
            font_size=30,
            color=ACCENT_GOLD,
        )
        title.to_edge(UP, buff=0.35)
        self.play(FadeIn(title), run_time=0.8)

        anim_time = 0.8 + 0.6 + 0.8 + 1.5 + 1.5 + 0.8 + 0.8 + 0.8
        default_waits = 0.5 + 0.5 + 0.5 + 0.5 + 0.5 + 2.0
        ws = _calc_wait_scale(duration, anim_time, default_waits)

        # Sun at focus
        sun = Dot([0, 0.3, 0], color=YELLOW, radius=0.2)
        sun_label = Text("Sun", font=FONT, font_size=16, color=YELLOW)
        sun_label.next_to(sun, DOWN, buff=0.15)
        self.play(FadeIn(sun), FadeIn(sun_label), run_time=0.6)
        self.wait(0.3 * ws)

        # Elliptical orbit (approximation of Ceres orbit)
        # Semi-major axis ~2.77 AU, eccentricity ~0.076
        a = 3.0  # visual semi-major axis
        e = 0.08
        b = a * math.sqrt(1 - e * e)
        c = a * e  # focus offset

        # Dashed full orbit (to be revealed later)
        orbit_full = Ellipse(
            width=2 * a,
            height=2 * b,
            color=TEXT_DIM,
            stroke_width=1.5,
            stroke_opacity=0.3,
        )
        orbit_full.move_to([c, 0.3, 0])

        # Observation arc: 9 degrees of the orbit
        # Place observed arc around angle ~60 degrees from perihelion
        obs_start_angle = 50  # degrees
        obs_arc_length = 9  # degrees
        n_obs_points = 8

        obs_dots = VGroup()
        for i in range(n_obs_points):
            angle_deg = obs_start_angle + i * (obs_arc_length / (n_obs_points - 1))
            angle_rad = math.radians(angle_deg)
            x = c + a * math.cos(angle_rad)
            y = 0.3 + b * math.sin(angle_rad)
            d = Dot([x, y, 0], color=ACCENT_CYAN, radius=0.06)
            obs_dots.add(d)

        obs_label = Text(
            "41日間の観測（約9度の弧）",
            font=FONT,
            font_size=18,
            color=ACCENT_CYAN,
        )
        obs_label.move_to([3.5, 2.8, 0])

        self.play(FadeIn(obs_dots), FadeIn(obs_label), run_time=0.8)
        self.wait(0.3 * ws)

        # Gauss's calculation: reveal full orbit
        calc_label = Text(
            "ガウスの計算",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        calc_label.move_to([-4.0, 2.5, 0])
        arrow = Arrow(
            [-4.0, 2.2, 0],
            [-2.5, 1.5, 0],
            color=ACCENT_GOLD,
            stroke_width=2,
        )

        self.play(FadeIn(calc_label), GrowArrow(arrow), run_time=0.8)
        self.wait(0.3 * ws)

        # Reveal the predicted orbit
        orbit_predicted = Ellipse(
            width=2 * a,
            height=2 * b,
            color=ACCENT_GOLD,
            stroke_width=2.5,
        )
        orbit_predicted.move_to([c, 0.3, 0])

        self.play(Create(orbit_predicted), run_time=1.5)
        self.wait(0.3 * ws)

        # Predicted position (opposite side of orbit, ~230 degrees)
        predict_angle = math.radians(230)
        pred_x = c + a * math.cos(predict_angle)
        pred_y = 0.3 + b * math.sin(predict_angle)

        predict_dot = Dot([pred_x, pred_y, 0], color=ACCENT_PINK, radius=0.12)
        predict_label = Text(
            "予測位置",
            font=FONT,
            font_size=18,
            color=ACCENT_PINK,
        )
        predict_label.next_to(predict_dot, DOWN + LEFT, buff=0.15)

        self.play(FadeIn(predict_dot), FadeIn(predict_label), run_time=0.8)
        self.wait(0.3 * ws)

        # Discovery: Ceres found!
        found_label = Text(
            "1801年12月31日 再発見",
            font=FONT,
            font_size=22,
            color=ACCENT_GOLD,
        )
        found_label.move_to([0, -1.7, 0])

        found_box = Rectangle(
            width=5.5,
            height=0.65,
            color=ACCENT_GOLD,
            stroke_width=2,
            fill_opacity=0.1,
        )
        found_box.move_to(found_label)

        self.play(
            FadeIn(found_box),
            FadeIn(found_label),
            predict_dot.animate.set_color(ACCENT_GOLD),
            run_time=0.8,
        )
        self.wait(max(duration - anim_time - 1.0, 1.0))


# ---------------------------------------------------------------------------
# SCENES registry
# ---------------------------------------------------------------------------
# factual claims displayed in each mode.
LINT_FACTUAL_CLAIMS = {
    "fitting": {"people": [], "years": []},
    "orbit": {
        "people": [
            ["ガウス", "Gauss"],
            ["ケレス", "Ceres"],
        ],
        "years": ["1801"],
    },
}


SCENES = {
    "fitting": LeastSquaresOrbit,
    "orbit": LeastSquaresOrbit,
}
