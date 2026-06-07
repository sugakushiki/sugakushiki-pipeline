"""
math_render.py - matplotlib mathtext を使った数式レンダリング共有ユーティリティ

BIZ UDMincho が ℵ・ℕ・ℝ・添字(₀)・特殊数学記号を豆腐化する問題への対策。
matplotlib 内蔵フォント（Computer Modern）で LaTeX サブセットを描画する。
LaTeX本体のインストールは不要。

使い分け:
    - `$...$` で囲む、または `\\` を含む文字列 → mathtext で画像化
    - それ以外（ASCII / 確実に表示できる Unicode） → 呼び出し側で PIL 描画

Consumers:
    - thumbnail_generator.py (math_symbol)
    - visual_generator.py    (text_overlay の main / sub、全体がTeXのとき)
"""

from PIL import Image


def uses_tex(text: str) -> bool:
    """文字列を mathtext で描画すべきか判定。

    判定基準: 文字列全体が `$...$` で囲まれていること（厳密モード）。
    `\\aleph_0 < 2^{\\aleph_0}$` のような部分的な LaTeX 片や、日本語と
    インラインで混在する場合はここでは False を返し、呼び出し側で通常の
    PIL 描画を使う。インライン混在対応は将来拡張（テキスト分割が必要）。
    """
    if not text:
        return False
    s = text.strip()
    return len(s) >= 2 and s.startswith("$") and s.endswith("$")


def render_mathtext_png(
    tex: str, fontsize: int = 100, color_hex: str = "#e2b714", dpi: int = 100
) -> Image.Image:
    """matplotlib mathtext で LaTeX 数式を透過PNGに変換する。

    Args:
        tex: 数式文字列。`$` で囲んでも囲まなくても良い（自動で補う）。
        fontsize: フォントサイズ（pt）。
        color_hex: "#rrggbb" 形式のカラー。
        dpi: レンダリングDPI。

    Returns:
        透過背景の RGBA Image（数式周辺でタイトにクロップ済み）。
    """
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tex_str = tex.strip()
    if not (tex_str.startswith("$") and tex_str.endswith("$")):
        tex_str = "$" + tex_str.strip("$") + "$"

    plt.rcParams["mathtext.fontset"] = "cm"

    fig = plt.figure()
    fig.patch.set_alpha(0)
    fig.text(0, 0, tex_str, fontsize=fontsize, color=color_hex)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def scale_image_alpha(img: Image.Image, max_alpha: int) -> Image.Image:
    """RGBA画像のアルファを max_alpha（0-255）まで減衰させる。

    アンチエイリアス（半透明ピクセル）は比率保持。
    """
    r, g, b, a = img.split()
    scale = max_alpha / 255.0
    a = a.point(lambda v: int(v * scale))
    return Image.merge("RGBA", (r, g, b, a))
