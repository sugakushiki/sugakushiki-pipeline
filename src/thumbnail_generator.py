"""
thumbnail_generator.py - サムネイル自動生成（3パターン）

Usage:
    python src/thumbnail_generator.py examples/moriarty/episode_config.json --output-dir examples/moriarty
    python src/thumbnail_generator.py examples/moriarty/episode_config.json --output-dir examples/moriarty --pattern A --phrase "2200年前のアルゴリズム"

Output:
    {output-dir}/thumbnails/
        thumbnail_A.png  (1280x720)
        thumbnail_B.png  (1280x720)
        thumbnail_C.png  (1280x720)
"""

import argparse
import glob
import json
import os
import random
import re as _thumb_re
import sys

from PIL import Image, ImageDraw, ImageFont

# ── カラーパレット ──────────────────────────────────────────────
BG_COLOR = "#1a1a2e"
GOLD = "#e2b714"
CYAN = "#4cc9f0"
PINK = "#f72585"
WHITE = "#ffffff"
BLACK = "#000000"
SHADOW_COLOR = "#000000"

# ── サイズ ──────────────────────────────────────────────────────
WIDTH = 1280
HEIGHT = 720

# ── フォント ────────────────────────────────────────────────────
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\BIZ-UDMinchoM.ttc",
    r"C:\Windows\Fonts\BIZUDMincho-Regular.ttf",
    r"C:\Windows\Fonts\BIZUDMincho-Bold.ttf",
    r"C:\Windows\Fonts\msmincho.ttc",
]


def find_font_path() -> str:
    """BIZ UDMinchoフォントのパスを検索。見つからなければNone。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """指定サイズのフォントを取得。"""
    path = find_font_path()
    if path:
        try:
            # .ttc の場合、index=0=Regular, index=1=Bold (if available)
            if path.endswith(".ttc") and bold:
                try:
                    return ImageFont.truetype(path, size, index=1)
                except Exception:
                    return ImageFont.truetype(path, size, index=0)
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"  Warning: Could not load font {path}: {e}")
    print("  Warning: BIZ UDMincho not found, using default font")
    return ImageFont.load_default()


# ── ユーティリティ ──────────────────────────────────────────────


def hex_to_rgb(hex_color: str) -> tuple:
    """#RRGGBB → (R, G, B)"""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    """#RRGGBB → (R, G, B, A)"""
    return hex_to_rgb(hex_color) + (alpha,)


def resize_and_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """画像をターゲットサイズにリサイズ＆中央クロップ。"""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # 横長 → 高さに合わせてリサイズ、左右クロップ
        new_h = target_h
        new_w = int(src_w * (target_h / src_h))
    else:
        # 縦長 → 幅に合わせてリサイズ、上下クロップ
        new_w = target_w
        new_h = int(src_h * (target_w / src_w))

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # 中央クロップ
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def draw_gradient_overlay(img: Image.Image, height_ratio: float = 0.40) -> Image.Image:
    """下部にグラデーション（黒→透明）オーバーレイを描画。"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    grad_start = int(HEIGHT * (1.0 - height_ratio))
    for y in range(grad_start, HEIGHT):
        progress = (y - grad_start) / (HEIGHT - grad_start)
        alpha = int(220 * progress)
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))

    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    shadow_offset: int = 3,
    shadow_color: tuple = None,
):
    """ドロップシャドウ付きテキスト描画。"""
    x, y = position
    sc = shadow_color or hex_to_rgb(SHADOW_COLOR)
    # Shadow
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=sc + (180,) if len(sc) == 3 else sc,
    )
    # Main text
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """テキストがmax_widthを超える場合に折り返す（日本語：文字単位）。"""
    if not text:
        return [""]

    # まず全体が収まるか確認
    bbox = font.getbbox(text)
    if bbox[2] - bbox[0] <= max_width:
        return [text]

    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ── 画像自動選定（scene_def フィルタ + Claude Vision） ─────────
#
# 選定アルゴリズム（v2）:
#   1. scene_definition.json から主題者を描く ken_burns シーンを抽出
#      - visual.use_reference が明示的に False のシーンは除外（非主題人物）
#      - source_prompt にシルエット/後ろ姿の記述があるシーンは除外
#      - source_prompt に人物記述キーワードが含まれるシーンのみ候補化
#   2. 画像ファイルが存在する候補に絞る
#   3. 候補が複数ならClaude Vision (Sonnet) で実画像を採点
#      - clarity (顔の明瞭さ) / composition (構図) / quality (品質) を各1-5点
#   4. 総合点最高の画像を採択
#
# 後方互換: scene_def=None の場合は旧来の person_*.png グロブ動作

# 「主題者の顔が写るシーン」を判定するための正規表現（単語境界ベース）
# 文字列内 "woman walking" が "man " にマッチするような誤検出を防ぐ
_THUMB_PERSON_PATTERNS = [
    _thumb_re.compile(r"\b(?:man|men|woman|women|person)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(
        r"\b(?:mathematician|scholar|lawyer|magistrate|judge|friar|philosopher|nobleman|gentleman|monk|priest)\b",
        _thumb_re.IGNORECASE,
    ),
    _thumb_re.compile(r"\bportrait\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\b(?:seated|sitting)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\b(?:his|her) (?:face|expression|eyes|hair|gaze)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\b(?:a |the |his |her )?\w+ figure\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(
        r"\bin (?:his|her) (?:early |late |mid[- ]?)?(?:twenties|thirties|forties|fifties|sixties|seventies|eighties|\d{2}s)\b",
        _thumb_re.IGNORECASE,
    ),
]

# ショットタイプによる人物主題判定
# サムネイル用途では「人物が主題のショット」のみ候補に含める
_THUMB_PERSON_SHOT_PATTERNS = [
    _thumb_re.compile(r"^\s*medium shot", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"^\s*close-?up (?:portrait|shot)", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"^\s*portrait\b", _thumb_re.IGNORECASE),
]

# 物体・風景主題のショット（サムネイル候補から除外）
_THUMB_NONPERSON_SHOT_PATTERNS = [
    _thumb_re.compile(r"^\s*wide establishing", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"^\s*overhead", _thumb_re.IGNORECASE),
    _thumb_re.compile(
        r"^\s*close-?up detail of (?:a |the )?(?:\w+ )?(?:book|manuscript|letter|document|register|edition|page|table|desk|study|scene)",
        _thumb_re.IGNORECASE,
    ),
    _thumb_re.compile(r"^\s*aerial", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"^\s*still life", _thumb_re.IGNORECASE),
]

# 「主題者の顔が見えない」シーンを除外する正規表現
_THUMB_EXCLUDE_PATTERNS = [
    _thumb_re.compile(
        r"silhouette of (?:a |the )?(?:man|woman|person|scholar|mathematician|figure|gentleman|\w+[- ]?figure)",
        _thumb_re.IGNORECASE,
    ),
    _thumb_re.compile(r"\b(?:his|her) silhouette\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\bfrom behind\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\bback of (?:a |the )?(?:man|woman|figure|person)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\bno (?:people|figures?|one)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\bempty (?:chair|seat|room|study)\b", _thumb_re.IGNORECASE),
    _thumb_re.compile(r"\bunoccupied\b", _thumb_re.IGNORECASE),
]


def _filter_subject_scenes(
    images_dir: str,
    scene_def: dict,
    subject_en: str | None = None,
) -> list[str]:
    """scene_definitionから主題者を描くken_burnsシーンの画像パスを返す。

    主題者優先のスコア順にソート:
      score 2: source_promptに subject_en が含まれる
      score 1: source_promptに his/the subject 等が含まれる
      score 0: 人物シーンだが主題者名は明記されていない
    """
    candidates = []
    subject_en_lower = (subject_en or "").lower().strip()

    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            vis = scene.get("visual", {})

            if vis.get("type") != "ken_burns":
                continue
            # 明示的に「別人物シーン」と指定されている → 除外
            if vis.get("use_reference") is False:
                continue

            img_path = os.path.join(images_dir, f"{sid}.png")
            if not os.path.exists(img_path):
                continue

            prompt = vis.get("source_prompt") or ""
            prompt_lower = prompt.lower()
            # 明示的に物体・風景ショットで始まる → 除外
            # ("Wide establishing shot", "Close-up detail of a [book/manuscript/...]" 等)
            if any(pat.search(prompt) for pat in _THUMB_NONPERSON_SHOT_PATTERNS):
                continue
            # 人物描写が含まれていない（物体・風景のみ）→ 除外
            if not any(pat.search(prompt) for pat in _THUMB_PERSON_PATTERNS):
                continue
            # 顔が見えないシーン（シルエット・後ろ姿・無人）→ 除外
            if any(pat.search(prompt) for pat in _THUMB_EXCLUDE_PATTERNS):
                continue
            # 「人物主題ショット」で始まるシーンはボーナス加点（後述のscoreに反映）
            has_person_shot_type = any(pat.search(prompt) for pat in _THUMB_PERSON_SHOT_PATTERNS)

            # 主題者マッチスコア（高いほど優先）
            #   3点: 主題者名が明記 + 人物主題ショット型で始まる
            #   2点: 主題者名が明記
            #   1点: his/the subject 等の代名詞
            #   0点: 人物描写はあるが主題者名なし
            #   +1加点: 人物主題ショット型で始まる（Medium shot / Portrait 等）
            if subject_en_lower and subject_en_lower in prompt_lower:
                score = 2
            elif _thumb_re.search(r"\bhis \w+", prompt_lower) or "the subject" in prompt_lower:
                score = 1
            else:
                score = 0
            if has_person_shot_type:
                score += 1

            candidates.append((img_path, score))

    # スコア降順、同点ならファイル名昇順
    candidates.sort(key=lambda x: (-x[1], x[0]))
    return [c[0] for c in candidates]


def _vision_score_candidates(
    candidate_paths: list[str],
    subject_label: str,
    max_vision_calls: int = 6,
) -> dict[str, int]:
    """Claude Vision で各画像を採点。{image_path: total_score} を返す。"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from image_generator import _call_claude_vision
    except ImportError:
        return {}

    import re as _re

    scores: dict[str, int] = {}
    for path in candidate_paths[:max_vision_calls]:
        name = os.path.basename(path)
        prompt = f"""この画像を YouTube サムネイル（1280x720）候補として評価してください。
主題者（サムネイルで描きたい人物）: {subject_label}

以下の3点を厳密に1〜5の整数で採点:
- clarity: 主題者の顔が明瞭に写っているか（正面〜斜め45度、目鼻立ちが分かる）。後ろ姿・シルエット・群衆は1点。
- composition: サムネイル映えする構図か（視線を引く表情、明暗のコントラスト、左右余白）。
- quality: 画像品質（油絵調のディテール、破綻や不自然さなし）。

JSONのみを返答（説明不要）:
{{"clarity": N, "composition": N, "quality": N}}"""

        result = _call_claude_vision(path, prompt)
        if not result:
            continue
        try:
            m = _re.search(r"\{[^{}]*\}", result)
            if not m:
                continue
            data = json.loads(m.group(0))
            c = int(data.get("clarity", 0))
            co = int(data.get("composition", 0))
            q = int(data.get("quality", 0))
            total = c + co + q
            scores[path] = total
            print(f"  [VISION] {name}: clarity={c} composition={co} quality={q} total={total}/15")
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    return scores


def select_best_thumbnail_image(
    images_dir: str,
    scene_def: dict | None = None,
    subject_name_ja: str | None = None,
    subject_en: str | None = None,
) -> str:
    """サムネイルに最適な画像を自動選定する。

    Args:
        images_dir: 画像ディレクトリ（*.png 配置場所）
        scene_def: scene_definition.json の dict。渡されると主題者フィルタが有効化。
        subject_name_ja: 日本語名（Vision評価プロンプト用）
        subject_en: 英語名（scene_def内プロンプトとの照合用）

    Returns:
        選定された画像のファイル名（例: "math_11.png"）

    選定優先順位:
        1. scene_def が渡されれば主題者シーンに絞り込み、Vision評価で最高スコア
        2. scene_def なし、または候補ゼロなら person_*.png グロブにフォールバック
        3. Vision 失敗時はファイル名ソート順で最初のもの
    """
    # Step 1: scene_def フィルタ
    candidates: list[str] = []
    if scene_def:
        candidates = _filter_subject_scenes(images_dir, scene_def, subject_en)
        if candidates:
            print(f"  [FILTER] Subject-focused candidates from scene_def: {len(candidates)}")

    # フォールバック: 従来の person_*.png グロブ
    if not candidates:
        candidates = sorted(glob.glob(os.path.join(images_dir, "person_*.png")))

    if not candidates:
        print("  Warning: No candidates found, using person_01.png")
        return "person_01.png"

    if len(candidates) == 1:
        selected = os.path.basename(candidates[0])
        print(f"  Only one candidate: {selected}")
        return selected

    # Step 2: Vision評価（実画像を見て採点）
    subject_label = subject_name_ja or subject_en or "主題の数学者"
    scores = _vision_score_candidates(candidates, subject_label)

    if scores:
        best = max(scores, key=scores.get)
        selected = os.path.basename(best)
        print(
            f"  Auto-selected: {selected} (vision score: {scores[best]}/15, from {len(candidates)} candidates)"
        )
        return selected

    # Step 3: Vision失敗時のフォールバック（scene_defフィルタの最上位）
    selected = os.path.basename(candidates[0])
    print(f"  Warning: Vision scoring failed, falling back to first candidate: {selected}")
    return selected


def validate_explicit_source_image(
    image_path: str,
    subject_label: str,
    threshold: int = 8,
) -> tuple[bool, int]:
    """明示指定された source_image を Vision 採点で妥当性チェック。

    既存 `_vision_score_candidates()` の Vision プロンプトは clarity を
    「後ろ姿・シルエット・群衆は1点」と判定するため、過去のケースのような
    「主役不在のグループシーンを source_image に指定」事故をスコアで検出可能。

    Args:
        image_path: 評価対象画像の絶対パス。
        subject_label: 主題者の表示名（Vision プロンプトに注入）。
        threshold: 合計スコア (0-15) の閾値。未満なら invalid 判定。

    Returns:
        (is_valid, total_score):
            is_valid: 閾値以上で True、未満で False、Vision 失敗時は True (skip)。
            total_score: 0-15、Vision 失敗時は -1。
    """
    scores = _vision_score_candidates([image_path], subject_label, max_vision_calls=1)
    if not scores or image_path not in scores:
        return True, -1  # Vision 失敗時は user 指定を尊重 (validation skip)
    total = scores[image_path]
    return total >= threshold, total


# ── パターン生成 ────────────────────────────────────────────────


def generate_pattern_a(source_img: Image.Image, name: str, phrase: str) -> Image.Image:
    """パターンA：全面人物＋下部テキスト帯"""
    # 人物画像を全面に配置
    canvas = resize_and_crop(source_img.copy(), WIDTH, HEIGHT)
    canvas = draw_gradient_overlay(canvas, height_ratio=0.45)

    draw = ImageDraw.Draw(canvas)

    # 名前（大きめ）
    name_font = get_font(88, bold=True)
    name_x = 60
    name_y = HEIGHT - 160

    draw_text_with_shadow(
        draw, (name_x, name_y), name, name_font, fill=hex_to_rgba(WHITE), shadow_offset=4
    )

    # フレーズ（金色、名前の下）
    phrase_font = get_font(38)
    phrase_lines = wrap_text(phrase, phrase_font, WIDTH - 120)
    phrase_y = name_y + 100
    for line in phrase_lines:
        draw_text_with_shadow(
            draw, (name_x, phrase_y), line, phrase_font, fill=hex_to_rgba(GOLD), shadow_offset=2
        )
        phrase_y += 48

    return canvas


def generate_pattern_b(source_img: Image.Image, name: str, phrase: str) -> Image.Image:
    """パターンB：左人物＋右テキスト"""
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), hex_to_rgba(BG_COLOR))

    # 左半分に人物画像
    left_w = WIDTH // 2 - 2  # 縦線の分
    left_img = resize_and_crop(source_img.copy(), left_w, HEIGHT)
    canvas.paste(left_img.convert("RGBA"), (0, 0))

    # 境界にアクセント縦線
    draw = ImageDraw.Draw(canvas)
    line_x = left_w
    draw.rectangle([line_x, 0, line_x + 4, HEIGHT], fill=hex_to_rgba(GOLD))

    # 右側テキストエリア
    right_x = left_w + 4
    right_center_x = right_x + (WIDTH - right_x) // 2
    text_area_w = WIDTH - right_x - 60

    # 名前（大きめ、右エリア中央）
    name_font = get_font(80, bold=True)
    name_bbox = name_font.getbbox(name)
    name_w = name_bbox[2] - name_bbox[0]
    name_x = right_center_x - name_w // 2
    name_y = HEIGHT // 2 - 100

    draw_text_with_shadow(
        draw, (name_x, name_y), name, name_font, fill=hex_to_rgba(WHITE), shadow_offset=3
    )

    # 名前の下に装飾線
    line_y = name_y + 100
    line_half = 80
    draw.rectangle(
        [right_center_x - line_half, line_y, right_center_x + line_half, line_y + 3],
        fill=hex_to_rgba(GOLD),
    )

    # フレーズ（水色）
    phrase_font = get_font(34)
    phrase_lines = wrap_text(phrase, phrase_font, text_area_w)
    phrase_y = line_y + 30
    for line in phrase_lines:
        line_bbox = phrase_font.getbbox(line)
        line_w = line_bbox[2] - line_bbox[0]
        line_x = right_center_x - line_w // 2
        draw_text_with_shadow(
            draw, (line_x, phrase_y), line, phrase_font, fill=hex_to_rgba(CYAN), shadow_offset=2
        )
        phrase_y += 44

    return canvas


def generate_pattern_c(
    source_img: Image.Image, name: str, phrase: str, math_symbol: str = None
) -> Image.Image:
    """パターンC：全面人物＋数式アクセント"""
    from math_render import render_mathtext_png, scale_image_alpha, uses_tex

    # ベースはパターンAと同じ
    canvas = resize_and_crop(source_img.copy(), WIDTH, HEIGHT)

    # 数式シンボルを半透明で散りばめる（テキスト領域と重ならない位置）
    # 構造強化: fontsize 縮小 + canvas 内 positions 計算 + alpha 引き上げ
    # 過去の bug: fontsize=100 で生成された 587×139 image を canvas 1280×720 に paste すると、
    # x=900+ の位置で 200-400px はみ出し → 4/6 の数式が画面外で消失。
    # alpha=30-50 の scale 後 mean alpha=4.47/255 (1.75% opacity) で残りも事実上不可視。
    if math_symbol:
        symbol_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        use_tex = uses_tex(math_symbol)

        if use_tex:
            symbol_img = render_mathtext_png(math_symbol, fontsize=60, color_hex=GOLD)
            sym_w, sym_h = symbol_img.size
        else:
            symbol_draw = ImageDraw.Draw(symbol_overlay)
            symbol_font = get_font(72)
            sym_w, sym_h = (300, 100)  # 概算 (text の場合)

        # Canvas 内に確実に収まる positions (sym_w + margin を考慮)
        max_x = max(20, WIDTH - sym_w - 20)
        max_y = max(20, HEIGHT - sym_h - 200)  # テキスト領域 (下 200px) は避ける

        # 強化 C: long math_symbol 用 adaptive positions。
        # 元の 6 positions は top-left + top-center + top-right の水平距離が
        # sym_w を上回る前提だが、long formula (sym_w > ~600px) では
        # top-center が両端と重なり、 "C ≈ 250,000Sta,000 stadia,000 stadia"
        # の garble を生む。
        # 閾値: sym_w > 水平 gap (max_x - 60) の 55% で adaptive モード起動、
        # top-center / bottom-center を mid-edge に振り替えて重複を避ける。
        horizontal_gap = max_x - 60
        if sym_w > horizontal_gap * 0.55:
            positions = [
                (60, 40),  # top-left
                (max_x, 50),  # top-right
                (60, max_y - 80),  # bottom-left
                (max_x, max_y - 60),  # bottom-right
                (60, max_y // 2),  # mid-left  (replaces top-center)
                (max_x, max_y // 2 + 20),  # mid-right (replaces bottom-center)
            ]
        else:
            positions = [
                (60, 40),
                (max_x, 50),
                (60, max_y - 80),
                (max_x, max_y - 60),
                (WIDTH // 2 - sym_w // 2, 30),
                (WIDTH // 2 - sym_w // 2, max_y),
            ]
        random.seed(42)  # 再現可能なランダム配置
        for x, y in positions:
            alpha = random.randint(110, 160)  # 視認可能レベル (43-63% opacity)
            if use_tex:
                faded = scale_image_alpha(symbol_img, alpha)
                symbol_overlay.paste(faded, (x, y), faded)
            else:
                color = hex_to_rgba(GOLD, alpha)
                symbol_draw.text((x, y), math_symbol, font=symbol_font, fill=color)

        canvas = Image.alpha_composite(canvas.convert("RGBA"), symbol_overlay)

    # グラデーション＋テキスト（パターンAと同じ）
    canvas = draw_gradient_overlay(canvas, height_ratio=0.45)
    draw = ImageDraw.Draw(canvas)

    # 名前
    name_font = get_font(88, bold=True)
    name_x = 60
    name_y = HEIGHT - 160
    draw_text_with_shadow(
        draw, (name_x, name_y), name, name_font, fill=hex_to_rgba(WHITE), shadow_offset=4
    )

    # フレーズ（ピンク for パターンC差別化）
    phrase_font = get_font(38)
    phrase_lines = wrap_text(phrase, phrase_font, WIDTH - 120)
    phrase_y = name_y + 100
    for line in phrase_lines:
        draw_text_with_shadow(
            draw, (name_x, phrase_y), line, phrase_font, fill=hex_to_rgba(PINK), shadow_offset=2
        )
        phrase_y += 48

    return canvas


# ── メイン ──────────────────────────────────────────────────────


def load_thumbnail_config(config_path: str, images_dir: str, args) -> dict:
    """episode_config.jsonからサムネイル設定を読み取り、CLIオーバーライドを適用。"""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    thumb = config.get("thumbnail", {})

    # 名前
    name = args.name if args.name else thumb.get("name", config.get("mathematician_ja", ""))

    # フレーズ
    if args.phrase:
        phrase = args.phrase
    elif thumb.get("phrase"):
        phrase = thumb["phrase"]
    else:
        # title_draftから「──」以降を取得
        title = config.get("title_draft", "")
        if "──" in title:
            phrase = title.split("──", 1)[1].strip()
        elif " " in title:
            phrase = title.split(" ", 1)[1].strip()
        else:
            phrase = title

    # 長さガード: 長すぎる phrase はサムネで折返し/見切れする。
    # title_draft 由来で自動取得すると、長文タイトルがそのまま phrase になりやすい。
    _PHRASE_MAX = 16
    if len(phrase) > _PHRASE_MAX:
        print(
            f"  [WARN] thumbnail phrase が長すぎます ({len(phrase)} 字 > {_PHRASE_MAX}): '{phrase}'"
        )
        print(
            "         サムネで折返し/見切れの恐れ。短い専用 phrase を "
            "episode_config.json thumbnail.phrase に設定推奨"
        )

    # scene_definition.json を一度だけロード（自動選定・fallback 両方で使用）
    scene_def = None
    episode_dir = os.path.dirname(images_dir.rstrip(os.sep))
    scene_def_path = os.path.join(episode_dir, "scene_definition.json")
    if os.path.exists(scene_def_path):
        try:
            with open(scene_def_path, encoding="utf-8") as f:
                scene_def = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: Failed to load scene_definition.json: {e}")
            scene_def = None

    def _auto_select() -> str:
        """scene_def フィルタ + Claude Vision 採点で人物画像を自動選定。"""
        return select_best_thumbnail_image(
            images_dir,
            scene_def=scene_def,
            subject_name_ja=config.get("mathematician_ja"),
            subject_en=config.get("subject_en") or config.get("mathematician"),
        )

    # 人物画像
    if args.source_image:
        source_image = args.source_image
    elif thumb.get("source_image"):
        source_image = thumb["source_image"]
        # 明示指定 source_image を Vision 採点で妥当性チェック。
        # 過去のケースで `person_03.png` (グループシーン、主役不在) を指定して
        # サムネイルが「主役不在」状態で生成された事故の予防。
        # 既存ファイルが見つかる場合のみチェック（不在なら経路 4 で recovery）。
        explicit_path = os.path.join(images_dir, source_image)
        if os.path.exists(explicit_path):
            subject_label = (
                config.get("mathematician_ja") or config.get("mathematician") or "主題の数学者"
            )
            threshold = thumb.get("source_validation_threshold", 8)
            is_valid, score = validate_explicit_source_image(
                explicit_path, subject_label, threshold=threshold
            )
            if not is_valid and score >= 0:
                print(
                    f"  Warning: Explicit source_image '{source_image}' has low Vision score "
                    f"({score}/15, threshold {threshold}). "
                    f"Likely a group shot or no clear subject portrait."
                )
                strict_mode = args.strict_source_validation or thumb.get(
                    "strict_source_validation", False
                )
                if strict_mode:
                    print(
                        "  [STRICT MODE] Falling back to auto-select via select_best_thumbnail_image()..."
                    )
                    source_image = _auto_select()
                else:
                    print(
                        "  [WARN-ONLY] Continuing with low-score image. "
                        "Consider --strict-source-validation or thumbnail.strict_source_validation=true to force fallback."
                    )
    else:
        # 自動選定: scene_definition.json と主題者名を渡して候補を絞り込み、
        # Claude Vision で実画像を評価して最適な1枚を選ぶ
        source_image = _auto_select()

    source_image_path = os.path.join(images_dir, source_image)
    fallback_resolved_name = None  # 構造強化: fallback で別画像が選ばれた場合に記録
    if not os.path.exists(source_image_path):
        # 指定 source_image が見つからない場合、blind glob ではなく
        # select_best_thumbnail_image() による Vision採点付き自動選定に落とす。
        # これにより zero-padding 不一致（person_2 vs person_02）などで
        # person_01.png（風景広角）が選ばれる事故を防ぐ。
        print(f"  Warning: Source image not found: {source_image_path}")
        print("  Falling back to vision-based auto-selection...")
        auto_pick = _auto_select()
        auto_pick_path = os.path.join(images_dir, auto_pick)
        if os.path.exists(auto_pick_path):
            source_image_path = auto_pick_path
            fallback_resolved_name = os.path.basename(source_image_path)
            print(f"  Auto-selected: {fallback_resolved_name}")
        else:
            # 最終手段: images/ 内の最初の person_*.png
            fallbacks = sorted(glob.glob(os.path.join(images_dir, "person_*.png")))
            if fallbacks:
                source_image_path = fallbacks[0]
                fallback_resolved_name = os.path.basename(source_image_path)
                print(f"  Last resort: {fallback_resolved_name}")
            else:
                print("  ERROR: No person images found")
                sys.exit(1)

    # 構造強化: fallback で別画像が選ばれた場合、config に書き戻して
    # silent fallback を明示状態に転換。次回ビルドで再現性確保。
    if fallback_resolved_name and config_path:
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            if "thumbnail" in cfg:
                old_value = cfg["thumbnail"].get("source_image")
                cfg["thumbnail"]["source_image"] = fallback_resolved_name
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                print(
                    f"  [FALLBACK->CONFIG] thumbnail.source_image: "
                    f"{old_value!r} -> {fallback_resolved_name!r} (saved to {config_path})"
                )
        except Exception as e:
            print(f"  [WARN] Failed to write back fallback to config: {e}")

    # 数式シンボル
    math_symbol = args.symbol if args.symbol else thumb.get("math_symbol", None)

    return {
        "name": name,
        "phrase": phrase,
        "source_image_path": source_image_path,
        "math_symbol": math_symbol,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate YouTube thumbnails (3 patterns)",
    )
    parser.add_argument("config_json", help="Path to episode_config.json")
    parser.add_argument("--output-dir", required=True, help="Episode output directory")
    parser.add_argument(
        "--pattern", default=None, choices=["A", "B", "C"], help="Generate only a specific pattern"
    )
    parser.add_argument("--phrase", default=None, help="Override phrase text")
    parser.add_argument("--name", default=None, help="Override name text")
    parser.add_argument(
        "--source-image", default=None, help="Override source image filename (in images/)"
    )
    parser.add_argument("--symbol", default=None, help="Override math_symbol")
    parser.add_argument(
        "--strict-source-validation",
        action="store_true",
        help="明示指定 source_image の Vision 採点が閾値未満の場合に "
        "auto-select に強制 fallback する。default は warning のみで採用続行。",
    )
    args = parser.parse_args()

    config_path = os.path.abspath(args.config_json)
    output_dir = os.path.abspath(args.output_dir)
    images_dir = os.path.join(output_dir, "images")
    thumbnails_dir = os.path.join(output_dir, "thumbnails")

    os.makedirs(thumbnails_dir, exist_ok=True)

    print("=" * 60)
    print("  Thumbnail Generator")
    print("=" * 60)

    # フォント確認
    font_path = find_font_path()
    if font_path:
        print(f"  Font: {os.path.basename(font_path)}")
    else:
        print("  Font: default (BIZ UDMincho not found)")

    # 設定読み込み
    thumb_config = load_thumbnail_config(config_path, images_dir, args)
    print(f"  Name:    {thumb_config['name']}")
    print(f"  Phrase:  {thumb_config['phrase']}")
    print(f"  Image:   {os.path.basename(thumb_config['source_image_path'])}")
    if thumb_config["math_symbol"]:
        print(f"  Symbol:  {thumb_config['math_symbol']}")

    # 人物画像読み込み
    source_img = Image.open(thumb_config["source_image_path"])
    print(f"  Source:  {source_img.size[0]}x{source_img.size[1]}px")

    name = thumb_config["name"]
    phrase = thumb_config["phrase"]
    math_symbol = thumb_config["math_symbol"]

    # パターン生成
    patterns = {}
    if args.pattern is None or args.pattern == "A":
        patterns["A"] = generate_pattern_a(source_img, name, phrase)
    if args.pattern is None or args.pattern == "B":
        patterns["B"] = generate_pattern_b(source_img, name, phrase)
    if args.pattern is None or args.pattern == "C":
        patterns["C"] = generate_pattern_c(source_img, name, phrase, math_symbol)

    # 保存
    print(f"\n  Output: {thumbnails_dir}")
    for label, img in patterns.items():
        out_path = os.path.join(thumbnails_dir, f"thumbnail_{label}.png")
        # RGBA → RGB (PNGでも透明度不要)
        img_rgb = Image.new("RGB", img.size, hex_to_rgb(BG_COLOR))
        img_rgb.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img_rgb.save(out_path, "PNG")
        size_kb = os.path.getsize(out_path) / 1024
        print(f"    thumbnail_{label}.png ({img.size[0]}x{img.size[1]}, {size_kb:.0f}KB)")

    print(f"\n  Generated {len(patterns)} thumbnail(s)")
    print("=" * 60)


if __name__ == "__main__":
    main()
