"""
audio_generator.py - VOICEVOX batch audio generation with timing output

Usage:
    python audio_generator.py scene_definition.json --output-dir episodes/001_erdos
    python audio_generator.py scene_definition.json --output-dir episodes/001_erdos --dry-run

Input:  scene_definition.json
Output: {output_dir}/audio/*.wav + {output_dir}/timing.json

Requires: VOICEVOX running at http://localhost:50021 (unless --dry-run)

narration_speech support:
    If a scene contains 'narration_speech' (same length as 'narration'),
    it is used for VOICEVOX synthesis instead of 'narration'. This allows
    math symbols in subtitles (via 'narration') while sending readable
    Japanese to VOICEVOX (via 'narration_speech').
    Example: narration="x²−2=0", narration_speech="xの2乗マイナス2イコール0"
"""

import argparse
import json
import os
import re
import sys
import time
import wave

# ---------------------------------------------------------------------------
# VOICEVOX settings (from STYLE_GUIDE.md)
# ---------------------------------------------------------------------------
SPEAKER_ID = 13  # 青山龍星ノーマル
SPEED_SCALE = 0.87
PAUSE_LENGTH_SCALE = 1.3
PITCH_SCALE = -0.02

SILENCE_BETWEEN_SENTENCES = 0.8  # seconds
VOICEVOX_URL = "http://localhost:50021"

# User dictionary for math-specific pronunciations
# Path is relative to this script's location
DICT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voicevox_dict.json")

# WAV format constants (VOICEVOX output: 24kHz, 16-bit, mono)
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit
CHANNELS = 1


# ---------------------------------------------------------------------------
# narration_speech auto-generation (rule-based symbol → reading conversion)
# ---------------------------------------------------------------------------

# Characters that are safe for VOICEVOX (no conversion needed)
_SAFE_RANGES = (
    (0x0020, 0x007E),  # ASCII printable
    (0x3000, 0x303F),  # CJK symbols & punctuation (。、「」etc)
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xFF00, 0xFFEF),  # Fullwidth forms
)

# Additional safe characters not covered by ranges above
_SAFE_CHARS = set("──…・ー々〜")

# Symbol → reading replacement rules (order matters for multi-char patterns)
# Processed in order: longer/more specific patterns first
SYMBOL_RULES = [
    # Multi-char patterns (context-dependent)
    ("−√", "マイナスルート"),  # −√2 → マイナスルート2
    ("+√", "プラスルート"),  # +√2 → プラスルート2
    # Single symbol replacements
    ("²", "の2乗"),
    ("³", "の3乗"),
    ("⁴", "の4乗"),
    ("⁵", "の5乗"),
    ("√", "ルート"),
    ("−", "マイナス"),  # U+2212 (minus sign)
    ("π", "パイ"),
    ("∞", "無限大"),
    ("Σ", "シグマ"),
    ("∈", "属する"),
    ("⊂", "部分集合"),
    ("≠", "ノットイコール"),
    ("≤", "以下"),
    ("≥", "以上"),
    ("≈", "ニアリーイコール"),
    ("±", "プラスマイナス"),
    ("×", "かける"),
    ("÷", "わる"),
    ("⇔", "同値"),
    ("⟺", "同値"),
    ("→", "ならば"),
    ("←", "の逆"),
    ("=", "イコール"),  # ASCII = : only applied to lines already flagged by other symbols
]


def _is_safe_char(c: str) -> bool:
    """Check if a character is safe for VOICEVOX (no conversion needed)."""
    if c in _SAFE_CHARS:
        return True
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in _SAFE_RANGES)


def has_speech_unfriendly_chars(text: str) -> list[str]:
    """Detect characters in text that VOICEVOX cannot pronounce.

    Returns list of problematic characters found (empty if all safe).
    """
    problems = []
    seen = set()
    clean = text.replace("|", "")
    for c in clean:
        if c not in seen and not _is_safe_char(c):
            problems.append(c)
            seen.add(c)
    return problems


# Digit → kana mapping for fraction reading (1-20 covers nearly all math fractions in narration)
# moriarty 例エピソードで顕在化「2分の1 → にふんのいち (時間の分と混同)」を構造的予防
_DIGIT_KANA: dict[str, str] = {
    "1": "いち", "2": "に", "3": "さん", "4": "よん", "5": "ご",
    "6": "ろく", "7": "なな", "8": "はち", "9": "きゅう", "10": "じゅう",
    "11": "じゅういち", "12": "じゅうに", "13": "じゅうさん", "14": "じゅうよん",
    "15": "じゅうご", "16": "じゅうろく", "17": "じゅうなな", "18": "じゅうはち",
    "19": "じゅうきゅう", "20": "にじゅう",
}

# Fraction pattern: N分のM (Japanese fraction notation, denominator-first)
# e.g., "2分の1" → "にぶんのいち" (= 1/2). Default VOICEVOX reads as "にふんのいち" (時間の分).
_FRACTION_RE = re.compile(r"(\d+)\s*分の\s*(\d+)")


def _convert_fractions(text: str) -> str:
    """Convert N分のM patterns to kana fraction reading.

    e.g., "アルファが2分の1" → "アルファがにぶんのいち"
    Both digits convert via _DIGIT_KANA (limited to 1-20 for safety; falls back to digits + ぶんの).
    """
    def repl(match: "re.Match[str]") -> str:
        denom = match.group(1)
        numer = match.group(2)
        denom_kana = _DIGIT_KANA.get(denom, denom)
        numer_kana = _DIGIT_KANA.get(numer, numer)
        return f"{denom_kana}ぶんの{numer_kana}"
    return _FRACTION_RE.sub(repl, text)


def generate_speech_text(text: str) -> str:
    """Convert narration text to VOICEVOX-friendly reading using rule-based replacement.

    Strips | markers, converts N分のM fractions to kana, then applies SYMBOL_RULES in order.
    """
    result = text.replace("|", "")
    result = _convert_fractions(result)  # 「N分のM」→ kana fraction
    for pattern, reading in SYMBOL_RULES:
        result = result.replace(pattern, reading)
    return result


# ---------------------------------------------------------------------------
# Pronunciation check (VOICEVOX audio_query + Claude verification)
# ---------------------------------------------------------------------------


def get_kana_from_query(query_response: dict) -> str:
    """audio_queryレスポンスからカナ読みを再構成する。

    accent_phrases[].moras[].text を連結。
    pause_mora（無音）はスペースに変換。
    """
    kana_parts = []
    for phrase in query_response.get("accent_phrases", []):
        mora_text = "".join(m["text"] for m in phrase.get("moras", []))
        kana_parts.append(mora_text)
        if phrase.get("pause_mora"):
            kana_parts.append(" ")
    return "".join(kana_parts)


def query_pronunciation(text: str, voicevox_url: str) -> tuple:
    """audio_queryのみ実行し、クエリレスポンスとカナ読みを返す。"""
    import requests

    resp = requests.post(
        f"{voicevox_url}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=30,
    )
    resp.raise_for_status()
    query = resp.json()
    kana = get_kana_from_query(query)
    return query, kana


def write_kana_preview(entries: list, output_dir: str) -> str:
    """Day 16 強化 D: VOICEVOX 予測カナを合成前レビュー用に artifact 化。

    ある回 で VOICEVOX 誤読 9 件が user の最終動画視聴で初発覚し、各ラウンド
    ~50-70 分の再ビルドを要した。pronunciation_check が既に全行のカナを
    query 済 (entries) なので、それを `kana_preview.txt` に書き出すだけで
    追加コストゼロで「合成前にテキスト scan で誤読を発見」できるようにする
    (fail fast / user trust)。[!latin] は英字含み行 (NaN→なえぬ 型の高リスク、
    今回実際に発生したクラス) を scan 優先としてマーク。

    Returns: 書き出したパス。
    """
    import re as _re

    path = os.path.join(output_dir, "kana_preview.txt")
    latin = _re.compile(r"[A-Za-z]")
    flagged = 0
    lines = [
        "# kana preview - VOICEVOX 予測カナ",
        "# 各行: [scene_id][i] 読み上げテキスト / → 予測カナ",
        "# [!latin] = 英字含み (NaN→なえぬ 型の高リスク、優先 scan)",
        "# 誤読を見つけたら global 辞書 (audio_generator._MISREADING_CATEGORIES)"
        " か narration_speech で修正してから本ビルド",
        "",
    ]
    for e in entries:
        mark = " [!latin]" if latin.search(e.get("text", "")) else ""
        if mark:
            flagged += 1
        lines.append(f"[{e['scene_id']}][{e['index']}]{mark} {e['text']}")
        lines.append(f"   → {e['kana']}")
        lines.append("")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(
            f"  [KANA-PREVIEW] {len(entries)} 行を {path} に出力 "
            f"(英字含み {flagged} 行 [!latin])。本ビルド前にカナを scan 推奨"
        )
    except OSError as exc:
        print(f"  [WARN] kana_preview.txt 書き込み失敗: {exc}")
    return path


PRONUNCIATION_CHECK_PROMPT = """あなたはVOICEVOXナレーションの読み確認アシスタントです。
以下は数学ドキュメンタリーのナレーション行と、VOICEVOXが予定しているカナ読みです。

各行について、カナ読みが文脈上不適切な箇所がないか確認してください。

## よくある誤読パターン（必ずチェック）
- 値 → ネ（誤）→ あたい（正：数学的な値）
- 球 → タマ（誤）→ きゅう（正：幾何学の球体）
- 角形 → カクガタ/カッケエ（誤）→ かくけい（正：多角形。促音や長音化も誤り）
- 多角形 → タカッケイ/タカクガタ（誤）→ たかくけい（正：促音なし）
- 分の → プンノ/フンノ（誤）→ ぶんの（正：分数の「ぶん」）
- 辺 → アタリ（誤）→ へん（正：多角形の辺）
- 港町 → ミナトチョウ（誤）→ みなとまち（正）
- 根 → ネ（誤）→ こん（正：平方根）
- 解 → トク/カイ の文脈判断
- 数 → カズ/スウ の文脈判断

## 意味依存読み（同一漢字でも文脈で読みが変わる。複合語・比喩は要注意）
- 行った: 動作実施（「研究を行った」「証明を行った」「分析を行った」）→ おこなった ／ 移動（「ペテルブルクへ行った」）→ いった
- 根を持つ/根がある: 比喩的起源（「現代の数学は〜に根を持つ」）→ ね（こんは数学的な「方程式の解」専用）。比喩用法が直前に graph/tree 等の文脈と紛らわしい時は narration_speech で「ね」を明示する
- 穴の数/点の数/個の数 等の「〜の数」: 具体的に数えるもの → かず（「あなのかず」「てんのかず」）／「数値・素数・自然数」等の数学概念名 → すう
- **値**: 単独「値」→ あたい（「πの値」「f(x)の値」）／**複合語末尾「観測値・絶対値・理論値・実測値・近似値・最大値・最小値・平均値・期待値・固有値・推定値・初期値・予測値」等は「ち」読み**（「ぜったいち」「かんそくち」「りろんち」）。**「観測あたい」「絶対あたい」のような kanji/kana 混合形は誤り** — narration が複合語「観測値」「絶対値」なら narration_speech は「かんそくち」「ぜったいち」のように完全ひらがな化する
- **分数「N分のM」**: 「にぶんのいち」「さんぶんのに」のような **N(denominator)ぶんのM(numerator)** 読み。VOICEVOX デフォルトで「にふんのいち」(時間「分」と混同) になるため narration_speech では完全ひらがな化必須
- **「否」**: 単独「答えは否です」「P は否である」のような修辞・命題形は **「いな」**読み（「ひ」読みは熟語専用: 「否定」「賛否」「否決」）
- 後: 時間（「○年後」「後に」）→ ご・のち ／ 空間（「後ろ」）→ うしろ
- 中: 範囲（「ヨーロッパ中」「世界中」）→ じゅう ／ 位置（「水中」「空中」）→ ちゅう

## 漢字の複数読みに注意（文脈で判断すること）
- 開（ひらく/かい）、閉（とじる/へい）→ 「開と閉」は「かいとへい」
- 表（おもて/ひょう）、裏（うら）→ コインの文脈なら「おもて」
- 今日（きょう/こんにち）→ 「今日の〜」で現代を意味する場合は「こんにち」
- 英字略語（AND→アンド、OR→オア、AI→エーアイ、WiFi→ワイファイ、5G→ファイブジー等）が正しくカタカナ読みされているか
- 文脈に応じた読みの正確性を最優先で検証すること

{high_risk_section}

## 重要なルール
- corrected_speechは**元のテキストに最小限の修正を加えた日本語**にすること
- 誤読される漢字だけをひらがなに置き換え、それ以外は元のまま残す
- 全文カタカナにしてはいけない
- **漢字熟語の一部だけをひらがな化する hybrid 表記は禁止**。
  - NG 例: 「半年後」を「半ねんご」と直す → VOICEVOX は「はん」+「ねんご」と読んで「はんねんご」誤読再発
  - OK 例: 「半年後」→「はんとしご」(熟語全体をひらがな化)
  - OK 例: 「半年後」→「半年後」のまま (漢字維持、VOICEVOX user dict 補正に委ねる)
  - 原則: 熟語単位で全ひらがな化するか、漢字維持のどちらか。**漢字 + 部分ひらがなの混合は VOICEVOX が単独漢字を別読みするため誤読を再生産する**

例:
- 元テキスト: 「円周率の値を挟み込む」
- VOICEVOX読み: 「エンシュウリツノネオハサミコム」（値→ネが誤読）
- corrected_speech: 「円周率のあたいを挟み込む」（値→あたい のみ修正）

例:
- 元テキスト: 「球の体積は」
- VOICEVOX読み: 「タマノタイセキワ」（球→タマが誤読）
- corrected_speech: 「きゅうの体積は」（球→きゅう のみ修正）

例:
- 元テキスト: 「正96角形を使い」
- VOICEVOX読み: 「セエキュウジュウロクカクガタオツカイ」（角形→カクガタが誤読）
- corrected_speech: 「正96かくけいを使い」（角形→かくけい のみ修正）

データ:
{entries_json}

修正が必要な行のみ、以下のJSON配列で返してください。
JSONのみ出力し、他のテキストは含めないでください。
[
  {{
    "scene_id": "...",
    "index": 0,
    "corrected_speech": "修正後の読み上げテキスト（行全体・最小限の修正のみ）",
    "reason": "修正理由（例: 値→ネをあたいに修正）"
  }}
]
修正不要なら空配列 [] を返してください。"""


def _load_high_risk_words(episode_dir: str) -> str:
    """episode_config.json の pronunciation_high_risk を読み込み、プロンプト用テキストを返す。"""
    config_path = os.path.join(episode_dir, "episode_config.json")
    if not os.path.exists(config_path):
        # episode_dir が audio/ 等のサブディレクトリの場合、親を探す
        parent = os.path.dirname(episode_dir)
        config_path = os.path.join(parent, "episode_config.json")
    if not os.path.exists(config_path):
        return ""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        items = config.get("pronunciation_high_risk", [])
        if not items:
            return ""
        lines = "\n".join(f"- {item}" for item in items)
        return f"## このエピソード固有の高リスク語（必ずチェック）\n{lines}"
    except Exception:
        return ""


_PRONCHECK_CACHE_VERSION = 1
_PRONCHECK_CACHE_FILE = "_proncheck_cache.json"


def _entry_cache_key(entry: dict) -> str:
    """Stable short hash for a pronunciation-check entry.

    Keyed on scene_id + index + speech text + VOICEVOX kana. Any change
    (e.g. user edits narration_speech) invalidates the entry's cache.
    """
    import hashlib

    payload = (
        f"{entry.get('scene_id', '')}|{entry.get('index', 0)}|"
        f"{entry.get('text', '')}|{entry.get('kana', '')}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _load_proncheck_cache(episode_dir: str) -> dict:
    path = os.path.join(episode_dir, _PRONCHECK_CACHE_FILE)
    if not os.path.exists(path):
        return {"_version": _PRONCHECK_CACHE_VERSION, "entries": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("_version") != _PRONCHECK_CACHE_VERSION:
            return {"_version": _PRONCHECK_CACHE_VERSION, "entries": {}}
        return data
    except Exception:
        return {"_version": _PRONCHECK_CACHE_VERSION, "entries": {}}


def _save_proncheck_cache(episode_dir: str, cache: dict) -> None:
    path = os.path.join(episode_dir, _PRONCHECK_CACHE_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def check_pronunciation_with_claude(entries: list, episode_dir: str) -> list:
    """Claude Sonnetにカナ読みチェックを依頼し、修正リストを返す。

    Per-entry cache (keyed on text + VOICEVOX kana) skips Claude entirely
    for already-checked lines. Only the entries whose text or kana has
    changed are sent to Claude. Dramatic speedup on partial rebuilds
    (single-line narration edit → seconds instead of 18 minutes).

    claude_backend.pyのcall_claude()を使用。
    """
    # claude_backend.py をインポート
    src_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, src_dir)
    from claude_backend import call_claude

    cache = _load_proncheck_cache(episode_dir)
    cache_entries = cache.setdefault("entries", {})

    # Partition entries into cached (skip Claude) / missing (send to Claude).
    cached_corrections: list = []
    missing_entries: list = []
    for entry in entries:
        key = _entry_cache_key(entry)
        prev = cache_entries.get(key)
        if prev is None:
            missing_entries.append(entry)
            continue
        if prev.get("needs_fix"):
            cached_corrections.append(
                {
                    "scene_id": entry["scene_id"],
                    "index": entry["index"],
                    "corrected_speech": prev.get("corrected_speech", ""),
                    "reason": f"(cached) {prev.get('reason', '')}",
                }
            )
        # else: prev.needs_fix == False → skip (no action needed)

    if not missing_entries:
        print(f"  [Cache] All {len(entries)} entries cached -- skipping Claude call")
        return cached_corrections

    if len(missing_entries) < len(entries):
        print(
            f"  [Cache] {len(entries) - len(missing_entries)} cached, "
            f"{len(missing_entries)} sent to Claude"
        )

    high_risk = _load_high_risk_words(episode_dir)
    prompt = PRONUNCIATION_CHECK_PROMPT.format(
        entries_json=json.dumps(missing_entries, ensure_ascii=False, indent=2),
        high_risk_section=high_risk,
    )

    try:
        result_text = call_claude(
            prompt=prompt,
            model="sonnet",
            debug=False,
            prefix="proncheck",
        )

        # JSON抽出（```json ... ``` フェンス除去）
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # [ で始まる部分を探す
        bracket_start = result_text.find("[")
        bracket_end = result_text.rfind("]")
        if bracket_start != -1 and bracket_end != -1:
            result_text = result_text[bracket_start : bracket_end + 1]

        new_corrections = json.loads(result_text)
        if not isinstance(new_corrections, list):
            new_corrections = []

    except Exception as e:
        print(f"  [WARN] Pronunciation check failed: {e}")
        return cached_corrections

    # B-45: normalize VOICEVOX-incompatible kana before persisting.
    # Claude occasionally returns u + 濁点 (multi-codepoint) for "vu"
    # which VOICEVOX splits into "u + i". Replace with single-char ヴ.
    for c in new_corrections:
        corrected = c.get("corrected_speech", "")
        normalized, changed = _normalize_voicevox_kana(corrected)
        if changed:
            print(
                f"  [B-45 normalize] {c.get('scene_id')}[{c.get('index')}]: "
                f"う゛/ゔ → ヴ (VOICEVOX compatibility)"
            )
            c["corrected_speech"] = normalized

    # Update cache: each missing entry gets either a fix record or a no-fix
    # marker, so future runs with identical text+kana bypass Claude.
    fix_by_position = {
        (c.get("scene_id"), c.get("index")): c
        for c in new_corrections
        if c.get("scene_id") is not None and c.get("index") is not None
    }
    for entry in missing_entries:
        key = _entry_cache_key(entry)
        pos = (entry["scene_id"], entry["index"])
        if pos in fix_by_position:
            fx = fix_by_position[pos]
            cache_entries[key] = {
                "needs_fix": True,
                "corrected_speech": fx.get("corrected_speech", ""),
                "reason": fx.get("reason", ""),
            }
        else:
            cache_entries[key] = {"needs_fix": False}

    _save_proncheck_cache(episode_dir, cache)
    return cached_corrections + new_corrections


# Known VOICEVOX misreadings: kanji → correct hiragana replacement.
# Applied BEFORE Claude check as a guaranteed safety net.
#
# Organized by category for maintainability. At import time the rules are
# flattened into KNOWN_MISREADINGS, sorted by target length (longest first)
# so that compound words always match before the standalone kanji they
# contain. Manual ordering within a category is irrelevant.
_MISREADING_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    # Chinese mathematics-history proper nouns / classical technical terms.
    # VOICEVOX misreads these (e.g. 劉徽→りゅうび). Seeded for ある回 (Liu Hui)
    # but recurs for future Chinese-math episodes (祖沖之 等). Global
    # accumulation per CLAUDE.md (not per-ep narration_speech rewrites).
    "chinese_math_history": [
        ("劉徽", "りゅうき"),
        ("九章算術注", "きゅうしょうさんじゅつちゅう"),
        ("九章算術", "きゅうしょうさんじゅつ"),
        ("割円術", "かつえんじゅつ"),
        ("海島算経", "かいとうさんけい"),
        ("青朱出入図", "せいしゅしゅつにゅうず"),
        ("出入相補", "しゅつにゅうそうほ"),
        ("勾股定理", "こうこていり"),
        ("勾股", "こうこ"),
        ("析理", "せきり"),
        ("牟合方蓋", "ぼうごうほうがい"),
        ("塹堵", "ざんと"),
        ("陽馬", "ようば"),
        ("鱉臑", "べつどう"),
        ("祖暅之", "そこうし"),
        ("祖暅", "そこう"),
        ("祖沖之", "そちゅうし"),
        ("却行", "きゃっこう"),
        # 魏 (Three Kingdoms Wei) → ぎ. VOICEVOX misreads bare 魏 as the
        # given-name reading たかし.
        ("魏", "ぎ"),
        # 三国 呉/蜀 (Three Kingdoms Wu/Shu) — user 確認で ご・しょく。
        ("呉", "ご"),
        ("蜀", "しょく"),
        # 楊輝 (Yang Hui, 13c Chinese mathematician). VOICEVOX misreads as
        # ようあきら (given-name reading of 輝). Day 20 ある回 Pascal で
        # パスカルの三角形先行例として登場、user 動画確認で顕在化。
        # audio_query empirical verify 済 (2026-05-25).
        ("楊輝", "ようき"),
    ],
    # Math technical terms where VOICEVOX picks the wrong kun/on reading.
    # Examples of the bug: 空集合→そらしゅうごう, 多角形→ただかけい,
    # 数値→すうね, 既約分数→すんでやくぶんすう.
    "math_terms": [
        ("空集合", "くうしゅうごう"),  # 過去のケース: そらしゅうごう 誤読
        # Compound 値 → ち rule (集積拡張、moriarty 例エピソードで顕在化)
        ("数値解析", "すうちかいせき"),
        ("三角関数値", "さんかくかんすうち"),
        ("近似値", "きんじち"),
        ("極限値", "きょくげんち"),  # 過去のケース: きょくげんあたい 誤読
        ("絶対値", "ぜったいち"),  # moriarty 例エピソードで顕在化
        ("観測値", "かんそくち"),  # moriarty 例エピソードで顕在化、過去の per-ep narration_speech 個別対応の集積化
        ("理論値", "りろんち"),  # moriarty 例エピソードで顕在化、過去の per-ep narration_speech 個別対応の集積化
        ("実測値", "じっそくち"),
        ("計算値", "けいさんち"),
        ("推定値", "すいていち"),
        ("予測値", "よそくち"),
        ("初期値", "しょきち"),
        ("最大値", "さいだいち"),
        ("最小値", "さいしょうち"),
        ("平均値", "へいきんち"),
        ("期待値", "きたいち"),
        ("中央値", "ちゅうおうち"),
        ("固有値", "こゆうち"),
        ("関数値", "かんすうち"),
        ("中間値", "ちゅうかんち"),
        ("境界値", "きょうかいち"),
        ("限界値", "げんかいち"),
        ("極値", "きょくち"),
        ("真値", "しんち"),
        ("許容値", "きょようち"),
        ("設計値", "せっけいち"),
        ("数値", "すうち"),
        # 否 (formal-logic / 修辞用法) → いな (moriarty 例エピソードで顕在化)
        ("「否」", "「いな」"),  # 引用括弧付き (修辞用法、強調)
        ("答えは否", "答えはいな"),
        ("否である", "いなである"),  # 「Pは否である」predicate form (cf. 偽である)
        # 多角形系 (既存)
        # 正N角形: 「角形→かくけい」が先に効くと「正六かくけい」へ落ち、
        # VOICEVOX が 正六/正三 を しょうろく/しょうぞう と誤読。longest-first で正N形を先取り。clean 形と、
        # Phase0 で 角形→かくけい 適用後に永続化された損傷形の両方を集積。
        ("正三角形", "せいさんかくけい"),
        ("正六角形", "せいろっかくけい"),
        ("正三かくけい", "せいさんかくけい"),
        ("正六かくけい", "せいろっかくけい"),
        ("多角形", "たかくけい"),
        ("角形", "かくけい"),
        # 辺 (幾何の「へん」) → VOICEVOX が訓読み「あたり」と誤読
        #。
        # 数学文脈の 辺 は一律 へん。longest-first で 辺の数→へんのかず 等は温存。
        # 一辺/三辺 は連濁の自然形を明示。
        ("一辺", "いっぺん"),
        ("三辺", "さんぺん"),
        # 斜辺: bare 辺→へん が 斜辺→斜へん に分割すると VOICEVOX が
        # 斜 を訓「はす」で ハスヘン 誤読。
        # longest-first で 辺→へん より先取り。clean形/永続ns形 両対応。
        ("斜辺", "しゃへん"),
        ("斜へん", "しゃへん"),
        # 右辺 / 左辺。
        # 「右辺」を VOICEVOX に直接渡せば「ウヘン」と正読されるが、
        # 既存 rule 辺→へん が「右辺→右へん」と書換、結果「右」が訓「ミギ」で
        # ミギヘン 誤読。longest-first で 右辺/左辺 を先取り、kana 化で確定。
        # VOICEVOX 実測 (2026-05-29): 右辺→ウヘン ✅ / 右へん→ミギヘン ❌ /
        # うへん→ウヘン ✅ / 左辺→サヘン ✅ / りょうへん→リョオヘン ✅
        # 永続化損傷形 (旧 NS で「右へん」「左へん」が書き戻されている場合) も対応。
        ("右辺", "うへん"),
        ("左辺", "さへん"),
        ("右へん", "うへん"),
        ("左へん", "さへん"),
        ("辺", "へん"),
        # 行 (おこなう=perform) を VOICEVOX が いく と誤読。bare 行 は 行く/一行/行列/却行 を
        # 壊すため不可。曖昧でない「独立に行」のみ限定 (独立に行く は
        # 事実上存在しない)。
        ("独立に行", "独立におこな"),
        # 帰せられる/帰せられて/帰せられている を VOICEVOX が訓「かえ」で
        # カエセラレル/カエセラレテ 誤読。再帰(さいき)/帰着(きちゃく)は正常
        # のため「帰せられ」prefix で広く captures、活用形を含む。
        # (ある回 user feedback: 「帰せられている → かえせられている」再発、
        # 既存「帰せられる」は活用形「帰せられて(いる)」を捉えていなかった)
        ("帰せられ", "きせられ"),
        # 立体名: VOICEVOX が 錐/体/柱 を誤読。longest-first で 四角錐→角錐 を保証。
        ("四角錐", "しかくすい"),
        ("四面体", "しめんたい"),
        # 正多面体 (プラトン立体): VOICEVOX が「N面体」の 体 を てい と誤読
        #。VOICEVOX 実測 (audio_query):
        #   正八面体 → セエハチメンテエ ❌ / 正十二面体 → セエジュウニメンテエ ❌
        #   正二十面体 → セエニジュウメンテエ ❌ / 面体 → メンテエ ❌
        # 「正」の直後のカナで VOICEVOX の解析が変わるため term ごとに full/bare:
        #   正四面体: bare(四面体→しめんたい)だと「正し」→ただし 誤読 → full せいしめんたい
        #   正二十面体: bare(二十面体→にじゅう)だと「正に」→まさに 誤読 → full せいにじゅうめんたい
        #   正八面体: full「せいはちめんたい」だと は→係助詞ワ で セイワチメンタイ ❌
        #             → bare(八面体→はちめんたい)で「正はちめんたい」→セエハチメンタイ ✅
        #   正十二面体: bare(十二面体→じゅうに)で「正じゅうにめんたい」→セエジュウニメンタイ ✅
        # 全て VOICEVOX audio_query で実測確認。
        # 正多面体/多面体 は default セエタメンタイ/タメンタイ 正のため対象外。
        ("正四面体", "せいしめんたい"),
        ("正二十面体", "せいにじゅうめんたい"),
        ("八面体", "はちめんたい"),
        ("十二面体", "じゅうにめんたい"),
        ("二十面体", "にじゅうめんたい"),
        # 金星 (Venus): VOICEVOX default は きんぼし/かなぼし (相撲・金星 の読み)。
        # 天文の金星は きんせい。
        # 他惑星 (水星すいせい/火星かせい/木星もくせい/土星どせい/地球ちきゅう) は default 正。
        ("金星", "きんせい"),
        ("角錐", "かくすい"),
        ("三角柱", "さんかくちゅう"),
        ("立方体", "りっぽうたい"),
        ("直方体", "ちょくほうたい"),
        ("円柱", "えんちゅう"),
        # 漢字分数「N分の一」: VOICEVOX が 分 を時間の ぷん/ふん と誤読
        #。_convert_fractions は
        # 漢字分数を変換しない。二分割(にぶんかつ)等の非分数は「分の」を
        # 含まないため非干渉。
        ("三分の一", "さんぶんのいち"),
        ("四分の一", "よんぶんのいち"),
        ("六分の一", "ろくぶんのいち"),
        # 微 (劉徽の語「微」= 無限小・形なきもの、名詞でび) を VOICEVOX が
        # かすか 等と誤読。微分積分(びぶん)は default 正のため非対象、限定形のみ。
        ("微となり", "びとなり"),
        ("微は", "びは"),
        # 微調整: VOICEVOX が 「ほろちょうせい」と誤読。
        # びちょうせい が正。VOICEVOX 実測 (query_pronunciation):
        #   微調整 → ホロチョオセエ ❌  /  びちょうせい → ビチョオセエ ✅
        # 「微+漢語」結合は ほろ 訓を優先するため熟語限定でカナ化。
        ("微調整", "びちょうせい"),
        ("細分", "さいぶん"),
        # 形を持たない: bare 形→かたち は 三角形/長方形/図形 を全壊させる
        # ため不可。限定句のみ。
        ("形を持たない", "かたちをもたない"),
        # 正方形 → せいほうけい。
        ("正方形", "せいほうけい"),
        # 一行: 文中の「一行」= 一行(いちぎょう)の記述/書き残した一行。
        # VOICEVOX default いっこう (一団) を回避。
        ("一行", "いちぎょう"),
        # 「史書は一行も」: 一行→いちぎょう(kana)化で直前の係助詞「は」が
        # VOICEVOX で ハ 誤読。VOICEVOX 実カナで
        # 「史書わいちぎょう」→シショワイチギョオ を確認。clean形/永続ns形
        # の両方を longest-first で先取り。
        ("史書は一行", "史書わいちぎょう"),
        ("史書はいちぎょう", "史書わいちぎょう"),
        # 「三角柱は陽馬」: 三角柱→さんかくちゅう / 陽馬→ようば の kana 化で
        # 間の係助詞「は」が VOICEVOX で ハ 誤読。
        # VOICEVOX 実カナで「さんかくちゅうわようば」→サンカクチュウワヨオバ
        # を確認。全 ns 走査で該当はこの1件のみ (他の は は全て ワ 正)。
        ("三角柱は陽馬", "さんかくちゅうわようば"),
        ("さんかくちゅうはようば", "さんかくちゅうわようば"),
        # 「べつどうは」/「しめんたいは」: 鱉臑→べつどう / 四面体→しめんたい の
        # kana 化後、続く係助詞 は が VOICEVOX で ハ 誤読。VOICEVOX 実測 (query_pronunciation):
        #   べつどうは → ベツドオハ ❌  /  べつどうわ → ベツドオワ ✅
        #   しめんたいは → シメンタイハ ❌  /  しめんたいわ → シメンタイワ ✅
        # 参考 (誤読しない=明示ルール不要): ようばは→ヨウバワ、これは→コレワ、
        # りゅうきは→リュウキワ、二個は→ニコワ は VOICEVOX が正しく ワ。
        ("べつどうは", "べつどうわ"),
        ("しめんたいは", "しめんたいわ"),
        # 「言い当てては」の は (て形+係助詞) を VOICEVOX が ハ と誤読
        #。VOICEVOX 実カナで「言い当ててわ」→
        # イイアテテワ を確認済。限定句のみ (bare は→わ は不可)。
        ("言い当てては", "言い当ててわ"),
        # 他にい (= ほかにいる、副詞「他に」+動詞「いる」) を VOICEVOX が
        # 「たにいる」(訓「た」誤読 + 一語結合) と誤読
        #。
        # 他国(たこく)/他言(たごん) は熟語のため非干渉、bare「他に+い」のみ。
        ("他にい", "ほかにい"),
        # 「結果は七度」の は (係助詞) を VOICEVOX が ハ と誤読
        #。
        # 「結果は」+ 数詞「七度」の境界で 7°12'/7.2° の文脈に入る瞬間に
        # ハ 誤読が起きる。VOICEVOX 実カナで「結果わななど」→ケッカワナナド を確認。
        # narration_speech 側も「結果わななど」と同期。
        ("結果は七度", "結果わ七度"),
        # 三丈 (古代の長さ単位 丈=じょう) を VOICEVOX が さんたけ と誤読
        #。
        ("三丈", "三じょう"),
        # 里 (距離単位 li) → り。VOICEVOX が さと (村) と誤読
        #。本題材の 里 は一律に距離単位。
        ("里", "り"),
        ("負の根", "ふのこん"),
        ("重根", "じゅうこん"),
        ("実根", "じっこん"),
        ("流率法", "りゅうりつほう"),
        ("高次元", "こうじげん"),
        ("球", "きゅう"),
        ("値", "あたい"),
        # 保型
        # 数学用語 automorphic function = 保型関数 の標準読みは「ほけい」
        ("保型関数論", "ほけいかんすうろん"),
        ("保型関数", "ほけいかんすう"),
        ("保型形式", "ほけいけいしき"),
        ("保型", "ほけい"),
        # 「N の数」型
        # 標準: 「N のかず」と読む
        ("頂点の数", "ちょうてんのかず"),
        ("辺の数", "へんのかず"),
        ("面の数", "めんのかず"),
        # Stability terms
        ("不安定多様体", "ふあんていたようたい"),
        ("安定多様体", "あんていたようたい"),
        ("不安定軌道", "ふあんていきどう"),
        ("安定軌道", "あんていきどう"),
        ("不安定性", "ふあんていせい"),
        ("安定性", "あんていせい"),
        ("不安定だ", "ふあんていだ"),
        ("安定だ", "あんていだ"),
        ("不安定的", "ふあんていてき"),
        ("安定的", "あんていてき"),
        ("不安定", "ふあんてい"),
        ("安定", "あんてい"),
        # 一般形 / 特殊形
        ("一般形", "いっぱんけい"),
        ("特殊形", "とくしゅけい"),
        # 完成形。
        # VOICEVOX 実測 (2026-05-29):
        #   完成形 → カンセイガタ ❌
        #   かんせいけい → カ'ン/セイケイ (2 accent phrase、分離音) ❌
        #   カンセエケエ → カ'ンセエケエ (1 phrase、連続音) ✅
        # ひらがな表記は形態素分割 (「かん」+「せいけい」) → カタカナ + 長音
        # で 1 phrase 化。既存「一般形/特殊形/標準形→けい」系列と同じ math 文脈
        # 形→けい だが、本 entry は連続音優先でカタカナ長音表記。
        ("完成形", "カンセエケエ"),
        # 正の数 / 負の数
        ("正の数", "せいのすう"),
        ("負の数", "ふのすう"),
        # NaN
        ("NaN", "なん"),
        # ある回 ヴァイエルシュトラスで顕在化
        # 量化子 (quantifier = ε-δ 論理の ∀ ∃) を VOICEVOX が
        # りょうかこ と誤読 (子→こ、し脱落)。標準読みは りょうかし。
        # pronunciation_high_risk にあったが Claude prompt-hint が
        # 永続化されず empirical 残存 → global 辞書へ昇格。
        ("量化子", "りょうかし"),
        # 標準形 (math: standard/normal form) を VOICEVOX が
        # ひょうじゅんがた と誤読 (形→がた)。一般形/特殊形と同じ
        # 数学の 形→けい 系列で global 集積。
        ("標準形", "ひょうじゅんけい"),
        # 数直線 (number line) を VOICEVOX が かずちょくせん と誤読
        # (数→かず)。数学標準の 数→すう に固定。「数直線上」
        # 「数直線の」等の派生は longest-prefix で吸収。
        ("数直線", "すうちょくせん"),
        # 私講師 (Privatdozent の和訳、一般大学講師職とは別の称号)
        # を VOICEVOX が わたしこうし と誤読 (私→わたし)。
        # 公式読みは ししこうし (PD 称号として確立)。
        # pronunciation_high_risk にあったが empirical 残存
        # → global 辞書昇格。
        ("私講師", "ししこうし"),
        # 今日の解析学 / 今日の数学 等 academic 文脈の「今日」は
        # こんにち (modern times) であって きょう (today) ではない。
        # bare「今日」は きょう が default で正のため、academic
        # follow-word のみ集積。ある回 で顕在化。
        ("今日の解析学", "こんにちのかいせきがく"),
        ("今日の数学", "こんにちのすうがく"),
        # 「教科書を開け」(open a textbook) は ひらけ。
        # bare 開け→あけ が default (open a door)、book context 限定。
        # ある回「大学の数学科の教科書を開けば」で顕在化。
        ("教科書を開け", "教科書をひらけ"),
        # 等方的 — VOICEVOX misreads as ひとしかたてき (kun-on mixed reading
        # of 等方). Day 20 ある回 パスカルの原理「等方的に伝わる」で
        # user 動画確認で顕在化。audio_query empirical verify 済 (2026-05-25)。
        ("等方的", "とうほうてき"),
        # 類体論 / 類体 (class field theory) — ある回 高木貞治で顕在化。
        # VOICEVOX 実測 (audio_query, 2026-05-28):
        #   類体論 → ルイカラダロン ❌  /  るいたいろん → ルイタイロン ✅
        # 「体」を「カラダ」と訓読みで誤読。longest-first で類体論を先取り。
        # bare「類体」も「ヒルベルト類体」(math_10)「○○類体」で誤読のためカナ化。
        ("類体論", "るいたいろん"),
        ("類体", "るいたい"),
        # 整数環 (ring of integers) — ある回 で顕在化。
        # VOICEVOX 実測: 整数環 → セイスウタマキ ❌  /  せいすうかん → セイスウカン ✅
        # 「環」を「たまき」(指輪) と訓読みで誤読。ring of integers (math)
        # は「かん」が標準。「ガウス整数環」「有理整数環」等で再発予想。
        ("整数環", "せいすうかん"),
    ],
    # Compound readings with tricky kun/on boundary (non-math).
    "compounds": [
        ("真か偽か", "しんかぎか"),
        ("南西端", "なんせいたん"),
        ("縁取られた", "ふちどられた"),
        ("小部屋", "こべや"),
        ("港町", "みなとまち"),
        ("年後", "ねんご"),
        # 半年系
        # longest first で "年後→ねんご" より優先される
        ("半年間", "はんとしかん"),
        ("半年後", "はんとしご"),
        ("半年前", "はんとしまえ"),
        ("半年", "はんとし"),
        # Sonnet が pronunciation_check で「半年→半ねん」と誤部分書換するパターンへの防御
        #
        ("半ねんご", "はんとしご"),
        ("半ねん", "はんとし"),
        # past findings + rendaku (連濁) 深い compounds (preventive)
        ("嫉妬深い", "しっとぶかい"),  # 過去のケース: しっとふかい 誤読
        ("興味深い", "きょうみぶかい"),  # 連濁、予防
        ("疑い深い", "うたがいぶかい"),  # 連濁、予防
        ("注意深い", "ちゅういぶかい"),  # 連濁、予防
        # Context-specific phrase locks (longer match beats 命/中 generic readings).
        ("父の命に", "ちちのめいに"),  # 過去のケース: ちちのいのちに 誤読
        ("ヨーロッパ中", "ヨーロッパじゅう"),  # 過去のケース: ヨーロッパちゅう 誤読
        # 過去のケース: 偽 in formal-logic predicate context defaults to にせ
        # (everyday reading) but should be ぎ. Catch via predicate forms
        # without affecting 偽物/偽証/偽善 (everyday compounds).
        ("真偽", "しんぎ"),  # 真偽 → しんぎ
        ("偽命題", "ぎめいだい"),
        ("偽である", "ぎである"),  # 「Pは偽である」predicate form
        ("偽となる", "ぎとなる"),
        ("偽ということ", "ぎということ"),  # 過去の formal-logic シーン: 「は偽ということ」誤読
        # ある回 ブラフマグプタで顕在化
        ("同じ書", "おなじしょ"),  # 過去のケース: どうじしょ 誤読 (書=しょ, 著書の意)
        ("はるか後", "はるかのち"),  # 過去のケース: はるかご 誤読 (後=のち, 後年の意)
        # 一枚物 — VOICEVOX misreads as いちまいぶつ (on-on instead of kun-on
        # for 物=もの). Day 20 ある回「一枚物の小論」で user 動画
        # 確認で顕在化。audio_query empirical verify 済 (2026-05-25)。
        ("一枚物", "いちまいもの"),
        # 本名 — VOICEVOX misreads as ほんな (kun-kun) instead of ほんみょう
        # ('real name', 標準読み, 広辞苑筆頭). Day 20 ある回「本名
        # アントワーヌ・ゴンボー」で user 動画確認で顕在化。当初「ほんめい」
        # と修正したが user 指摘で「ほんみょう」に再修正 (2026-05-26)。
        ("本名", "ほんみょう"),
        ("という語", "というご"),  # 過去のケース: というかたり 誤読 (語=ご, 単語の意)
        ("祖型", "そけい"),  # 過去のケース: そがた 誤読 (祖型=そけい, prototype の意)
        # 高木貞治 (Teiji Takagi, 数学者) — ある回 で顕在化。
        # VOICEVOX 実測 (audio_query, 2026-05-28):
        #   高木貞治 → タカギ・サダハル ❌  /  たかぎていじ → タカギテイジ ✅
        # default で「貞治」を「さだはる」(王貞治等の現代日本人男性名読み) と
        # 解釈。数学者高木貞治の正読みは「ていじ」。"高木貞治" exact match のみ
        # global 化 (bare 貞治 は別人物 王貞治/井上貞治/明智光秀幼名 等で
        # 「さだはる」が正のためカナ化しない)。
        ("高木貞治", "たかぎていじ"),
    ],
}


# VOICEVOX-incompatible kana patterns (B-45).
# Pronunciation_check (Claude) sometimes returns the combining-濁点 form
# "う゛" (U+3046 + U+309B spacing or U+3099 combining) which VOICEVOX reads
# as two phonemes "u + i" instead of "vu", producing 誤読 like ダウィト for
# ダヴィト. Normalize to single-char ヴ (U+30F4) before persisting.
_VOICEVOX_KANA_FIXES: list[tuple[str, str]] = [
    ("う゛", "ヴ"),  # う + spacing 濁点
    ("ゔ", "ヴ"),  # う + combining 濁点 (would NFC-compose to ゔ)
    ("ゔ", "ヴ"),    # standalone ゔ → ヴ (VOICEVOX-safe variant)
]


def _normalize_voicevox_kana(text: str) -> tuple[str, bool]:
    """Normalize kana patterns that VOICEVOX mis-reads (B-45).

    Returns (normalized_text, changed) where changed=True iff any
    substitution was applied.
    """
    if not text:
        return text, False
    changed = False
    for src, dst in _VOICEVOX_KANA_FIXES:
        if src in text:
            text = text.replace(src, dst)
            changed = True
    return text, changed


# Patterns for narration_speech drift detection (B-8)
_KANJI_RE = re.compile(r"[一-鿿]")
_DIGIT_SEQ_RE = re.compile(r"\d+")
# narration containing math/ASCII content is intentionally rewritten to kana
# in narration_speech by design (e.g. "x²" -> "xの2乗", "La Geometrie" ->
# "ラ・ジェオメトリ"). The "kanji extra in speech" check would FP on these
# (e.g. "乗" injected by kana correction), so such lines are skipped.
# Trade-off: misses ASCII-side edits like "B-12 -> B-13"; judged acceptable
# in 21-episode dry-run survey.
_FORMULA_OR_ASCII_RE = re.compile(
    r"[A-Za-z]"
    r"|[²³⁰¹⁴⁵⁶⁷⁸⁹⁻⁺]"
    r"|[√∞∫∑∏∂∇π·×÷≦≧≠≈≡∈∉⊂⊃∪∩∀∃≤≥]"
    r"|[\^*/<>=+\-,]"  # incl. comma (digit separators like "3,900")
)


def _check_narration_speech_drift(narration_clean: str, speech: str) -> list[str]:
    """Detect drift between narration[i] and narration_speech[i] (B-8).

    pronunciation_check leaves user-managed narration_speech untouched, so
    when narration is edited the speech may go stale (過去のケース "ittsai ->
    hotondo" incident, internal notes).

    Detects two patterns:
    1. kanji present in speech but absent from narration (speech retains
       old narration's wording — kana correction would not introduce new
       kanji), and
    2. digit-sequence mismatch when both sides contain digits (year /
       count edit not propagated to speech).

    Out of scope (BACKLOG): pure-kana speech (~0.7%), edits sharing all
    kanji, punctuation/particle-only edits. See sessionNN commit notes.

    Returns: list of reason strings; empty = no drift detected.
    """
    if not speech or not narration_clean or speech == narration_clean:
        return []
    # Pure-kana speech: drift undetectable here (BACKLOG follow-up)
    if not _KANJI_RE.search(speech):
        return []

    # Skip math/ASCII narration: kana correction inevitably introduces new
    # kanji (e.g. "乗") and reshuffles digits (e.g. "1/3" -> "3ぶんの1",
    # "II" -> "2", "3,900" -> "3900"), causing false positives in both
    # checks below. Validated in 21-episode dry-run.
    if _FORMULA_OR_ASCII_RE.search(narration_clean):
        return []

    # Date numerals are intentionally decoupled: subtitles
    # (narration display) render dates in Arabic via subtitle_generator.
    # dates_to_arabic, while narration_speech keeps kanji for VOICEVOX. Normalise
    # both sides so kanji date digits (一五八九 vs 1589) are not mis-flagged as drift.
    from subtitle_generator import dates_to_arabic

    narration_clean = dates_to_arabic(narration_clean)
    speech = dates_to_arabic(speech)
    if speech == narration_clean:
        return []

    reasons: list[str] = []

    # Check 1: kanji extra in speech
    speech_kanji = set(_KANJI_RE.findall(speech))
    nar_kanji = set(_KANJI_RE.findall(narration_clean))
    extra_in_speech = speech_kanji - nar_kanji
    if extra_in_speech:
        if not (speech_kanji & nar_kanji):
            reasons.append(
                f"all kanji in speech ({''.join(sorted(speech_kanji))}) absent from narration"
            )
        else:
            reasons.append(
                f"kanji in speech absent from narration: {''.join(sorted(extra_in_speech))}"
            )

    # Check 2: digit-sequence drift (year/count edit)
    # speech is allowed to be a subsequence of nar — kana correction often
    # drops digits when phrases like "正17角形" become "せいじゅうななかくけい".
    # WARN only when speech contains a digit not reachable in order from nar
    # (e.g. nar="1830年" / speech="1826ねん").
    nar_nums = _DIGIT_SEQ_RE.findall(narration_clean)
    sp_nums = _DIGIT_SEQ_RE.findall(speech)
    if nar_nums and sp_nums and nar_nums != sp_nums:
        if not _is_subseq(sp_nums, nar_nums):
            reasons.append(f"digit sequences differ: nar={nar_nums} speech={sp_nums}")

    # Check 3: kanji extra in narration ("speech missing").
    # Mirror of check 1. Triggered when narration was edited to ADD content
    # (extra phrase / new sentence) but narration_speech stayed at the old
    # shorter version — pronunciation_check does not overwrite user-managed
    # speech, so it goes stale. ある回 case: スタディア説明
    # ("スタディアとは古代の長さの単位で、およそ百六十メートル前後です") added
    # to narration but speech still had the old version → not read aloud.
    #
    # Twin guards to suppress false positives from kana correction:
    # (1) Missing-kanji count ≥ 3 (kana 補正は通常 1-2 文字単位なので、3 文字
    #     以上の差は narration 拡張の指標)。
    # (2) speech length < narration_clean length × 0.95 (kana 補正は通常
    #     speech を narration よりやや長くするため。speech が narration より
    #     5% 以上短い場合のみ "stale" suspect)。ある回 stale case では
    #     speech 73 文字 / narration 95 文字 = 0.77 → WARN 発火。
    #     一方 kana 補正のみの synced ケースでは speech が narration より
    #     長くなる傾向 → ratio ≥ 0.95 で suppress。
    extra_in_narration = nar_kanji - speech_kanji
    if (
        len(extra_in_narration) >= 3
        and len(speech) < len(narration_clean) * 0.95
    ):
        reasons.append(
            f"speech may be stale (kanji in narration absent from speech: "
            f"{''.join(sorted(extra_in_narration))[:10]}, "
            f"speech/nar length ratio {len(speech) / len(narration_clean):.2f})"
        )

    return reasons


def _is_subseq(small: list, big: list) -> bool:
    """Return True if `small` is a subsequence of `big` (order-preserving)."""
    it = iter(big)
    return all(x in it for x in small)


def _flatten_and_sort_misreadings(
    categories: dict[str, list[tuple[str, str]]],
) -> list[tuple[str, str]]:
    """Flatten category → ordered rule list with:
    1. Longer targets first (guarantees compound words match before kanji),
    2. Stable within same length (preserves category declaration order).
    """
    seen: dict[str, str] = {}
    ordered: list[tuple[str, str]] = []
    for cat_rules in categories.values():
        for target, reading in cat_rules:
            if target in seen:
                if seen[target] != reading:
                    raise ValueError(
                        f"conflicting KNOWN_MISREADINGS for {target!r}: "
                        f"{seen[target]!r} vs {reading!r}"
                    )
                continue
            seen[target] = reading
            ordered.append((target, reading))
    # Stable sort by target length DESC
    ordered.sort(key=lambda kv: len(kv[0]), reverse=True)
    return ordered


KNOWN_MISREADINGS: list[tuple[str, str]] = _flatten_and_sort_misreadings(_MISREADING_CATEGORIES)


def detect_stale_ns_from_old_rules(scene_def: dict) -> list:
    """Detect existing narration_speech entries that may contain stale kana
    from previous _MISREADING_CATEGORIES rule versions.

    Failure mode pattern:
    - Old rule "本名 → ほんめい" applied → NS "ほんめいアントワーヌ" written back
    - Rule updated to "本名 → ほんみょう"
    - On next build, apply_known_misreading_fixes scans NS for "本名" (kanji)
      but NS already has "ほんめい" (no kanji), so rule is NOT applied
    - "ほんめい" stays as audio output (silent regression)

    This function flags such suspects: narration contains kanji X, NS for the
    same index does NOT contain expected hiragana Y. WARN-only (user must
    manually edit NS).

    Returns: [{"scene_id", "index", "kanji", "expected_hiragana", "ns_excerpt"}, ...]
    """
    stale = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            narration = scene.get("narration", [])
            ns_list = scene.get("narration_speech")
            if ns_list is None:
                continue  # auto-flat: rule fix will run on current build, no stale risk
            for i, narr in enumerate(narration):
                if i >= len(ns_list):
                    continue
                ns = ns_list[i]
                if ns is None:
                    continue
                narr_flat = narr.replace("|", "")
                for kanji, hiragana in KNOWN_MISREADINGS:
                    # narration has the orig kanji
                    if kanji not in narr_flat:
                        continue
                    # ... but NS doesn't have the expected new hiragana
                    # AND NS doesn't have the orig kanji (which would mean
                    # rule will run on current build).
                    if hiragana not in ns and kanji not in ns:
                        stale.append(
                            {
                                "scene_id": scene.get("scene_id", "?"),
                                "index": i,
                                "kanji": kanji,
                                "expected_hiragana": hiragana,
                                "ns_excerpt": ns[:80],
                            }
                        )
                        break  # report once per line
    return stale


def apply_known_misreading_fixes(scene_def: dict, dry_run: bool = False) -> list:
    """既知の誤読パターンをルールベースで修正する。

    narration_speechが未設定の行も含めて全行チェックし、
    既知パターンが含まれる行にnarration_speechを設定する。

    Args:
        scene_def: scene_definition.json の dict
        dry_run: True なら scene_def を変更せず、検出のみ行う

    Returns: 修正された（またはdry_runでは検出された）行の diff リスト
        [{"scene_id": ..., "index": ..., "before": ..., "after": ..., "source": "rule"}, ...]
    """
    diffs = []

    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            narration = scene.get("narration", [])
            if not narration:
                continue

            for i, raw_text in enumerate(narration):
                # 現在の読み上げテキストを取得
                speech = scene.get("narration_speech")
                if speech and i < len(speech):
                    current = speech[i]
                else:
                    current = raw_text.replace("|", "")

                # 既知パターンを適用
                modified = current
                for kanji, hiragana in KNOWN_MISREADINGS:
                    if kanji in modified:
                        modified = modified.replace(kanji, hiragana)

                if modified != current:
                    sid = scene.get("scene_id", "?")
                    diffs.append(
                        {
                            "scene_id": sid,
                            "index": i,
                            "before": current,
                            "after": modified,
                            "source": "rule",
                        }
                    )

                    if not dry_run:
                        if scene.get("narration_speech") is None:
                            scene["narration_speech"] = [
                                line.replace("|", "") for line in narration
                            ]
                        scene["narration_speech"][i] = modified

                    tag = "[RULE?]" if dry_run else "[RULE]"
                    print(f"  {tag} {sid}[{i}]: {current[:50]}...")
                    print(f"       -> {modified[:50]}...")

    return diffs


def lint_narration_markers(scene_def: dict) -> int:
    """Narration | marker and narration_speech consistency lint.

    Checks:
    1. Long narration (>80 chars) with insufficient | markers
    2. narration vs narration_speech array length mismatch per scene

    Returns: number of warnings (non-blocking, no API calls)
    """
    warn_count = 0

    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            narration = scene.get("narration", [])
            narration_speech = scene.get("narration_speech")

            # Check: narration_speech length mismatch
            if narration_speech is not None:
                if len(narration_speech) != len(narration):
                    print(
                        f"  [LINT] {sid}: narration_speech length "
                        f"({len(narration_speech)}) != narration length "
                        f"({len(narration)})"
                    )
                    warn_count += 1

            # Check: long lines without enough | markers
            #        + narration_speech drift (B-8)
            for i, line in enumerate(narration):
                clean = line.replace("|", "")
                if len(clean) > 80:
                    pipes = line.count("|")
                    expected = len(clean) // 40  # ~1 marker per 40 chars
                    if pipes < expected:
                        print(
                            f"  [LINT] {sid}[{i}]: {len(clean)} chars "
                            f"with {pipes} | marker(s) "
                            f"(recommend {expected}+)"
                        )
                        warn_count += 1

                # B-8: narration_speech drift detection
                if narration_speech is not None and i < len(narration_speech):
                    speech = narration_speech[i]
                    reasons = _check_narration_speech_drift(clean, speech)
                    if reasons:
                        nar_disp = clean[:60] + ("..." if len(clean) > 60 else "")
                        sp_disp = speech[:60] + ("..." if len(speech) > 60 else "")
                        print(f"  [LINT] {sid}[{i}]: narration_speech may be stale")
                        print(f"     narration: {nar_disp}")
                        print(f"     speech:    {sp_disp}")
                        print(f"     reasons: {'; '.join(reasons)}")
                        warn_count += 1

                    # B-45: detect VOICEVOX-incompatible kana already on disk
                    _, voicevox_bad = _normalize_voicevox_kana(speech)
                    if voicevox_bad:
                        sp_disp = speech[:60] + ("..." if len(speech) > 60 else "")
                        print(
                            f"  [LINT] {sid}[{i}]: VOICEVOX-incompatible kana "
                            f"(う゛/ゔ) in narration_speech"
                        )
                        print(f"     speech: {sp_disp}")
                        print("     fix: replace う゛/ゔ with ヴ (single-char katakana)")
                        warn_count += 1

    return warn_count


def validate_narration_speech(scene_def: dict) -> None:
    """Validate narration_speech arrays -- fail-fast on empty entries.

    If a scene has narration_speech (not None), every entry must be a
    non-empty string. Empty strings cause VOICEVOX to return ~0.23 sec
    silent wav files, producing scenes where subtitles flash by in an
    instant (a past edit-mismatch bug).

    The fix at the source is to copy narration[i] into narration_speech[i]
    for indices that don't need pronunciation override, OR remove the
    narration_speech key entirely so VOICEVOX uses narration as-is.

    Raises:
        ValueError: if any narration_speech contains empty entries.
    """
    issues = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            ns = scene.get("narration_speech")
            if ns is None:
                continue  # No narration_speech → audio uses narration directly
            if not isinstance(ns, list):
                issues.append(f"{sid}: narration_speech is not a list")
                continue
            n = scene.get("narration", [])
            for i, s in enumerate(ns):
                if not s or not s.strip():
                    fallback = n[i][:60] if i < len(n) else "(no narration)"
                    issues.append(
                        f"{sid}[{i}]: narration_speech is empty. "
                        f"Copy narration[{i}]='{fallback}...' or remove "
                        f"narration_speech array entirely."
                    )
    if issues:
        msg = "narration_speech validation failed:\n" + "\n".join(f"  - {item}" for item in issues)
        raise ValueError(msg)


def _print_pronunciation_summary(diffs: list, dry_run: bool = False) -> None:
    """適用された（または dry_run で提案された）発音修正の一覧を表で表示する。"""
    if not diffs:
        return

    header = "Proposed pronunciation fixes (dry-run)" if dry_run else "Applied pronunciation fixes"
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {header} -- {len(diffs)} entries")
    print(f"{line}")

    # source ごとに集計
    by_source = {}
    for d in diffs:
        by_source.setdefault(d.get("source", "?"), []).append(d)
    for source, items in by_source.items():
        print(f"  [{source}] {len(items)} fix(es)")

    # 最大10件まで個別表示（以降は省略）
    for i, d in enumerate(diffs[:10]):
        sid = d.get("scene_id", "?")
        idx = d.get("index", 0)
        before = d.get("before", "")[:60]
        after = d.get("after", "")[:60]
        reason = d.get("reason", "") or d.get("source", "")
        print(f"  {i + 1:2d}. {sid}[{idx}]  ({reason})")
        print(f"      before: {before}")
        print(f"      after:  {after}")
    if len(diffs) > 10:
        print(f"  ... and {len(diffs) - 10} more (see log above for details)")
    print(f"{line}\n")


def pronunciation_check(
    scene_def: dict, voicevox_url: str, episode_dir: str, dry_run: bool = False
) -> int:
    """全ナレーション行のVOICEVOXカナ読みをClaudeで検証し、
    問題のある行にnarration_speechを設定する。

    Args:
        scene_def: scene_definition.json の dict
        voicevox_url: VOICEVOX API base URL
        episode_dir: エピソードディレクトリ（Claude CLI一時ファイル配置先）
        dry_run: True なら scene_def を変更せず、提案のみ出力する

    Returns: 修正された（dry_run なら提案された）行数
    """
    mode_label = " (dry-run)" if dry_run else ""
    print(f"\n[CHECK] Pronunciation check{mode_label} (Claude + VOICEVOX audio_query)...")

    all_diffs = []
    rule_diffs: list = []

    # Phase 0: ルールベース事前修正（dry_run の場合のみここで呼ぶ）
    # Day 15 構造強化: dry_run でない場合は main 関数の Phase 0 で既に適用済 (常時実行)。
    # ここでは dry_run の表示用にのみ呼ぶ。non-dry-run で再呼びすると idempotent だがログ重複。
    if dry_run:
        rule_diffs = apply_known_misreading_fixes(scene_def, dry_run=True)
        all_diffs.extend(rule_diffs)
        if rule_diffs:
            print(f"  [RULE] Would apply {len(rule_diffs)} rule-based fix(es)")

    # 1. 全行の読み上げテキストとカナを収集
    entries = []
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            scene_id = scene.get("scene_id", "")
            narration = scene.get("narration", [])
            narration_speech = scene.get("narration_speech")

            for i, raw_text in enumerate(narration):
                # 読み上げテキストを決定
                if narration_speech and i < len(narration_speech):
                    speech_text = narration_speech[i]
                else:
                    speech_text = raw_text.replace("|", "")

                # audio_queryでカナ取得
                _, kana = query_pronunciation(speech_text, voicevox_url)

                entries.append(
                    {
                        "scene_id": scene_id,
                        "index": i,
                        "text": speech_text,
                        "kana": kana,
                    }
                )

    if not entries:
        print("  No narration lines to check.")
        _print_pronunciation_summary(all_diffs, dry_run=dry_run)
        return len(all_diffs)

    print(f"  Queried {len(entries)} lines from VOICEVOX")

    # Day 16 強化 D: 予測カナを合成前レビュー用 artifact に出力 (追加コスト0)
    write_kana_preview(entries, episode_dir)

    # 2. Claude Sonnetに一括送信
    corrections = check_pronunciation_with_claude(entries, episode_dir)

    if not corrections:
        print("  [OK] No additional pronunciation issues found by Claude.")
        _print_pronunciation_summary(all_diffs, dry_run=dry_run)
        return len(all_diffs)

    # 3. 修正をscene_defに適用
    llm_applied = 0
    for fix in corrections:
        sid = fix.get("scene_id", "")
        idx = fix.get("index", 0)
        corrected = fix.get("corrected_speech", "")
        reason = fix.get("reason", "")

        if not corrected:
            continue

        # scene_defから該当シーンを探す
        for section in scene_def.get("sections", []):
            for scene in section.get("scenes", []):
                if scene.get("scene_id") != sid:
                    continue

                narration = scene.get("narration", [])
                if idx >= len(narration):
                    continue

                # 現在の narration_speech を取得（なければ narration から生成）
                speech = scene.get("narration_speech")
                if speech and idx < len(speech):
                    old_text = speech[idx]
                else:
                    old_text = narration[idx].replace("|", "")

                if old_text == corrected:
                    continue  # 変更なし

                all_diffs.append(
                    {
                        "scene_id": sid,
                        "index": idx,
                        "before": old_text,
                        "after": corrected,
                        "source": "claude",
                        "reason": reason,
                    }
                )
                llm_applied += 1

                if not dry_run:
                    if scene.get("narration_speech") is None:
                        scene["narration_speech"] = [line.replace("|", "") for line in narration]
                    scene["narration_speech"][idx] = corrected

                tag = "[FIX?]" if dry_run else "[FIX]"
                print(f"\n  {tag} {sid}[{idx}]: {reason}")
                print(f"     before: {old_text}")
                print(f"     after:  {corrected}")

    total = len(all_diffs)
    verb = "Would apply" if dry_run else "Applied"
    print(
        f"\n  {verb} {total} pronunciation fix(es) (rule={len(rule_diffs)}, claude={llm_applied})"
    )
    _print_pronunciation_summary(all_diffs, dry_run=dry_run)
    return total


def auto_generate_narration_speech(scene_def: dict) -> int:
    """Scan all scenes and auto-generate narration_speech where needed.

    For scenes that contain speech-unfriendly characters in narration
    but have no narration_speech, generates one using rule-based conversion
    and injects it into the scene dict.

    Returns number of scenes that were auto-generated.
    """
    generated_count = 0

    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            scene_id = scene.get("scene_id", "")
            narration = scene.get("narration", [])

            # Skip if narration_speech already provided
            if scene.get("narration_speech") is not None:
                continue

            # Check each narration line for problematic characters
            needs_speech = False
            for text in narration:
                if has_speech_unfriendly_chars(text):
                    needs_speech = True
                    break

            if not needs_speech:
                continue

            # Auto-generate narration_speech
            speech_lines = []
            for text in narration:
                if has_speech_unfriendly_chars(text):
                    speech = generate_speech_text(text)
                    speech_lines.append(speech)
                else:
                    # No problematic chars: use narration as-is (strip | markers)
                    speech_lines.append(text.replace("|", ""))

            scene["narration_speech"] = speech_lines
            generated_count += 1

            # Print what was generated for human verification
            print(f"\n  [AUTO] Auto-generated narration_speech for {scene_id}:")
            for i, (orig, speech) in enumerate(zip(narration, speech_lines, strict=True)):
                orig_clean = orig.replace("|", "")
                if orig_clean != speech:
                    print(f"     [{i}] display: {orig_clean}")
                    print(f"     [{i}] speech:  {speech}")

                # Residual check: warn if speech text still has unfriendly chars
                residual = has_speech_unfriendly_chars(speech)
                if residual:
                    chars_str = " ".join(f"U+{ord(c):04X}" for c in residual)
                    print(f"     [WARN]  [{i}] RESIDUAL: {chars_str}")
                    print("          -> Add rules to SYMBOL_RULES or fix manually")

    # Also check manually provided narration_speech for residual issues
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            speech = scene.get("narration_speech")
            if speech is None:
                continue
            scene_id = scene.get("scene_id", "")
            for i, line in enumerate(speech):
                residual = has_speech_unfriendly_chars(line)
                if residual:
                    chars_str = " ".join(f"U+{ord(c):04X}" for c in residual)
                    print(
                        f"\n  [WARN]  {scene_id}[{i}] narration_speech has unfriendly chars: {chars_str}"
                    )
                    print(f"       -> {line.encode('ascii', 'replace').decode('ascii')}")

    return generated_count


# ---------------------------------------------------------------------------
# VOICEVOX User Dictionary
# ---------------------------------------------------------------------------


def register_user_dict(voicevox_url: str, dict_file: str = DICT_FILE) -> int:
    """Register math-specific pronunciations in VOICEVOX user dictionary.

    Checks existing entries to avoid duplicates.
    Returns number of newly registered words.
    """
    import requests

    if not os.path.exists(dict_file):
        print(f"  Dictionary file not found: {dict_file}")
        return 0

    with open(dict_file, encoding="utf-8") as f:
        dict_data = json.load(f)

    words = dict_data.get("words", [])
    if not words:
        return 0

    # Get existing user dictionary entries
    try:
        resp = requests.get(f"{voicevox_url}/user_dict", timeout=10)
        resp.raise_for_status()
        existing = resp.json()  # {uuid: {surface, pronunciation, ...}}
    except Exception as e:
        print(f"  Warning: Could not read user dictionary: {e}")
        existing = {}

    # Build set of existing surfaces for dedup
    existing_surfaces = set()
    for entry in existing.values():
        existing_surfaces.add(entry.get("surface", ""))

    # Register missing words
    registered = 0
    for word in words:
        surface = word.get("surface")
        if not surface:
            continue  # Section marker (_section / _comment) — skip silently
        if surface in existing_surfaces:
            continue

        try:
            resp = requests.post(
                f"{voicevox_url}/user_dict_word",
                params={
                    "surface": surface,
                    "pronunciation": word["pronunciation"],
                    "accent_type": word.get("accent_type", 0),
                    "word_type": word.get("word_type", "COMMON_NOUN"),
                    "priority": word.get("priority", 5),
                },
                timeout=10,
            )
            resp.raise_for_status()
            registered += 1
        except Exception as e:
            print(f"  Warning: Failed to register '{surface}': {e}")

    return registered


def strip_subtitle_markers(text: str) -> str:
    """Remove | subtitle break markers from narration text."""
    return text.replace("|", "")


def get_wav_duration(filepath: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(filepath, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def generate_silence_wav(filepath: str, duration: float):
    """Generate a silent WAV file of given duration."""
    num_frames = int(SAMPLE_RATE * duration)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"\x00" * num_frames * SAMPLE_WIDTH)


def synthesize_voicevox(text: str, output_path: str, voicevox_url: str) -> float:
    """Send text to VOICEVOX and save WAV. Returns duration in seconds."""
    import requests

    # Step 1: audio_query
    resp = requests.post(
        f"{voicevox_url}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=30,
    )
    resp.raise_for_status()
    query = resp.json()

    # Apply tuned parameters
    query["speedScale"] = SPEED_SCALE
    query["pauseLengthScale"] = PAUSE_LENGTH_SCALE
    query["pitchScale"] = PITCH_SCALE

    # Step 2: synthesis
    resp = requests.post(
        f"{voicevox_url}/synthesis",
        params={"speaker": SPEAKER_ID},
        data=json.dumps(query),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    return get_wav_duration(output_path)


def estimate_duration(text: str) -> float:
    """Estimate speech duration for dry-run mode.

    Rough heuristic: ~6.5 chars/sec for Japanese at speed 0.87.
    """
    clean = strip_subtitle_markers(text)
    chars = len(clean)
    return max(chars / 6.5, 0.5)


def concatenate_wavs(wav_files: list, output_path: str):
    """Concatenate multiple WAV files into one.

    All input files must have the same format (rate, channels, sample width).
    """
    if not wav_files:
        return

    # Read params from first file
    with wave.open(wav_files[0], "rb") as wf:
        params = wf.getparams()

    with wave.open(output_path, "wb") as out:
        out.setparams(params)
        for filepath in wav_files:
            with wave.open(filepath, "rb") as wf:
                out.writeframes(wf.readframes(wf.getnframes()))


def process_scene(scene: dict, audio_dir: str, voicevox_url: str, dry_run: bool) -> dict:
    """Process a single scene: generate audio for all narration sentences.

    If scene contains 'narration_speech' (same length as 'narration'),
    uses it for VOICEVOX synthesis (math-friendly readings like
    "xの2乗マイナス2イコール0"). The original 'narration' text is
    preserved in timing.json for subtitle display.

    Returns timing info for this scene.
    """
    scene_id = scene["scene_id"]
    narration = scene["narration"]
    narration_speech = scene.get("narration_speech")  # Optional: VOICEVOX-readable text
    pause_after = scene.get("pause_after", 0.5)

    # Validate narration_speech length if provided
    if narration_speech is not None and len(narration_speech) != len(narration):
        print(
            f"  [WARN] {scene_id}: narration_speech length ({len(narration_speech)}) "
            f"!= narration length ({len(narration)}), ignoring narration_speech"
        )
        narration_speech = None

    sentences_timing = []
    segment_files = []  # ordered list of WAV files for concatenation
    current_time = 0.0

    for i, raw_text in enumerate(narration):
        sent_idx = f"{i + 1:03d}"
        sent_wav = os.path.join(audio_dir, f"{scene_id}_{sent_idx}.wav")

        # Determine speech text for VOICEVOX:
        # - narration_speech[i] if available (math-friendly reading)
        # - otherwise strip | markers from narration[i] (default)
        if narration_speech is not None:
            speech_text = strip_subtitle_markers(narration_speech[i])
        else:
            speech_text = strip_subtitle_markers(raw_text)

        # Generate or estimate audio
        if dry_run:
            duration = estimate_duration(speech_text)
            # Create a placeholder silence file in dry-run too
            generate_silence_wav(sent_wav, duration)
        else:
            duration = synthesize_voicevox(speech_text, sent_wav, voicevox_url)

        start = current_time
        end = current_time + duration

        sentences_timing.append(
            {
                "index": i,
                "text": raw_text,  # Keep | markers for subtitle_generator (display text)
                "text_clean": speech_text,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(duration, 3),
                "wav_file": f"{scene_id}_{sent_idx}.wav",
            }
        )

        segment_files.append(sent_wav)
        current_time = end

        # Add silence between sentences (except after last)
        if i < len(narration) - 1:
            silence_wav = os.path.join(audio_dir, f"{scene_id}_silence_{sent_idx}.wav")
            generate_silence_wav(silence_wav, SILENCE_BETWEEN_SENTENCES)
            segment_files.append(silence_wav)
            current_time += SILENCE_BETWEEN_SENTENCES

    # Concatenate all segments into scene-level WAV
    scene_wav = os.path.join(audio_dir, f"{scene_id}.wav")
    concatenate_wavs(segment_files, scene_wav)
    scene_duration = current_time

    # Add scene-end pause (silence after last sentence)
    # This is NOT included in the scene WAV but recorded for video_assembler
    total_with_pause = scene_duration + pause_after

    # Clean up silence files
    for f in segment_files:
        if "_silence_" in f and os.path.exists(f):
            os.remove(f)

    return {
        "scene_id": scene_id,
        "duration": round(scene_duration, 3),
        "pause_after": pause_after,
        "duration_with_pause": round(total_with_pause, 3),
        "sentences": sentences_timing,
        "wav_file": f"{scene_id}.wav",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate VOICEVOX audio from scene_definition.json"
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory (audio/ and timing.json will be created here)",
    )
    parser.add_argument(
        "--voicevox-url", default=VOICEVOX_URL, help=f"VOICEVOX API URL (default: {VOICEVOX_URL})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Estimate durations without VOICEVOX"
    )
    parser.add_argument(
        "--dict-file",
        default=None,
        help=f"Path to pronunciation dictionary JSON (default: {DICT_FILE})",
    )
    parser.add_argument(
        "--check-pronunciation",
        action="store_true",
        help="Check VOICEVOX pronunciation with Claude before synthesis",
    )
    parser.add_argument(
        "--pronunciation-dry-run",
        action="store_true",
        help="Report proposed pronunciation fixes without modifying "
        "scene_definition.json. Implies --check-pronunciation; "
        "exits after printing the summary without running synthesis.",
    )
    args = parser.parse_args()

    # --pronunciation-dry-run implies --check-pronunciation
    if args.pronunciation_dry_run:
        args.check_pronunciation = True

    # Load scene definition
    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)

    # Auto-generate narration_speech for scenes with math symbols
    n_auto = auto_generate_narration_speech(scene_def)
    if n_auto > 0:
        print(f"\n  Auto-generated narration_speech for {n_auto} scene(s)")
        print("  [WARN] Review the speech text above before publishing")

    # Validate narration_speech: empty entries cause silent audio (a past silent-failure bug)
    try:
        validate_narration_speech(scene_def)
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    # Create output directories
    audio_dir = os.path.join(args.output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # Subtitle marker lint (always runs, zero-cost, no API calls)
    n_lint = lint_narration_markers(scene_def)
    if n_lint > 0:
        print(f"\n  [LINT] {n_lint} subtitle marker warning(s) -- review above")
    else:
        print("  [LINT] Subtitle markers OK")

    # Phase 0: Rule-based misreading fix (always-on, no API calls)
    # Day 15 構造強化: --skip-pronunciation-check でも常に走るよう pronunciation_check の外に移動
    # 以前は pronunciation_check 内で呼ばれていたため、--skip-pronunciation-check 時に rule fix も
    # 丸ごと skip される設計問題があった
    if not args.dry_run:
        rule_diffs = apply_known_misreading_fixes(scene_def, dry_run=False)
        if rule_diffs:
            print(f"\n[RULE] Applied {len(rule_diffs)} rule-based misreading fix(es)")
            for d in rule_diffs[:20]:  # cap output
                print(f"  {d['scene_id']}[{d['index']}]: {d['before'][:60]}...")
                print(f"    -> {d['after'][:60]}...")
            if len(rule_diffs) > 20:
                print(f"  ... and {len(rule_diffs) - 20} more")
            with open(args.scene_json, "w", encoding="utf-8") as f:
                json.dump(scene_def, f, ensure_ascii=False, indent=2)
            print(f"  Saved {len(rule_diffs)} rule-based fix(es) to {args.scene_json}")

        # G3: Detect NS that may contain stale kana from old
        # rule versions. apply_known_misreading_fixes operates on existing NS,
        # so NS like "ほんめい" (from old "本名→ほんめい" rule) survives even
        # after rule update to "本名→ほんみょう" (no kanji in NS to match).
        # WARN-only; user must manually edit NS to include expected new kana.
        stale_ns = detect_stale_ns_from_old_rules(scene_def)
        if stale_ns:
            print(
                f"\n[NS-STALE] {len(stale_ns)} possible stale narration_speech entry(ies):"
            )
            print(
                "  NS may contain old kana from previous _MISREADING_CATEGORIES rule versions."
            )
            print(
                "  If rule was updated (e.g. 本名→ほんめい → 本名→ほんみょう), NS keeps the old kana"
            )
            print(
                "  because apply_known_misreading_fixes scans NS for kanji (which is no longer there)."
            )
            for s in stale_ns[:10]:
                print(
                    f"  {s['scene_id']}[{s['index']}]: rule expects '{s['kanji']}'"
                    f"→'{s['expected_hiragana']}'"
                )
                print(f"    NS: {s['ns_excerpt']}...")
            if len(stale_ns) > 10:
                print(f"  ... and {len(stale_ns) - 10} more")
            print(
                "  Action: manually edit scene_definition.json NS to include expected new kana, "
                "then re-run audio step."
            )

    # Check VOICEVOX connection (unless dry-run)
    if not args.dry_run:
        try:
            import requests

            resp = requests.get(f"{args.voicevox_url}/version", timeout=5)
            resp.raise_for_status()
            print(f"VOICEVOX connected: version {resp.text}")
        except Exception as e:
            print(f"ERROR: Cannot connect to VOICEVOX at {args.voicevox_url}")
            print(f"  {e}")
            print("  Start VOICEVOX or use --dry-run for testing.")
            sys.exit(1)

        # Register math-specific pronunciations
        dict_path = args.dict_file if args.dict_file else DICT_FILE
        n_registered = register_user_dict(args.voicevox_url, dict_path)
        if n_registered > 0:
            print(f"  Registered {n_registered} new dictionary entries")

        # Pronunciation check with Claude (before synthesis)
        if args.check_pronunciation:
            n_fixed = pronunciation_check(
                scene_def,
                args.voicevox_url,
                args.output_dir,
                dry_run=args.pronunciation_dry_run,
            )
            if n_fixed > 0 and not args.pronunciation_dry_run:
                # Save updated scene_def with pronunciation fixes
                with open(args.scene_json, "w", encoding="utf-8") as f:
                    json.dump(scene_def, f, ensure_ascii=False, indent=2)
                print(f"  Saved {n_fixed} pronunciation fix(es) to {args.scene_json}")
            if args.pronunciation_dry_run:
                print(
                    f"  [DRY-RUN] {n_fixed} fix(es) would be applied. "
                    f"No changes written to {args.scene_json}."
                )
                print("  Re-run without --pronunciation-dry-run to apply.")
                sys.exit(0)

    # Process all scenes
    timing_data = {
        "episode_id": scene_def.get("episode_id", "unknown"),
        "scenes": {},
        "total_duration": 0.0,
        "generation_mode": "dry-run" if args.dry_run else "voicevox",
    }

    total_sentences = 0
    total_duration = 0.0
    global_offset = 0.0  # cumulative offset for global timestamps

    for section in scene_def["sections"]:
        section_id = section["section_id"]
        print(f"\n=== Section: {section_id} ===")

        for scene in section["scenes"]:
            scene_id = scene["scene_id"]
            n_sentences = len(scene["narration"])
            total_sentences += n_sentences

            print(f"  {scene_id} ({n_sentences} sentences)...", end=" ", flush=True)
            start_time = time.time()

            scene_timing = process_scene(scene, audio_dir, args.voicevox_url, args.dry_run)

            # Add global offset
            scene_timing["global_start"] = round(global_offset, 3)
            scene_timing["global_end"] = round(global_offset + scene_timing["duration"], 3)
            global_offset += scene_timing["duration_with_pause"]

            timing_data["scenes"][scene_id] = scene_timing
            total_duration += scene_timing["duration_with_pause"]

            elapsed = time.time() - start_time
            print(f"{scene_timing['duration']:.1f}s audio ({elapsed:.1f}s elapsed)")

    timing_data["total_duration"] = round(total_duration, 3)
    timing_data["total_duration_minutes"] = round(total_duration / 60, 2)

    # Save timing.json
    timing_path = os.path.join(args.output_dir, "timing.json")
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing_data, f, ensure_ascii=False, indent=2)

    # Summary
    mode = "DRY-RUN (estimated)" if args.dry_run else "VOICEVOX"
    print(f"\n{'=' * 50}")
    print(f"Generation complete ({mode})")
    print(f"  Scenes:    {len(timing_data['scenes'])}")
    print(f"  Sentences: {total_sentences}")
    print(
        f"  Duration:  {timing_data['total_duration']:.1f}s ({timing_data['total_duration_minutes']:.1f} min)"
    )
    print(f"  Audio dir: {audio_dir}")
    print(f"  Timing:    {timing_path}")


# ===========================================================================
# Partial rebuild: single-scene audio regeneration
# ===========================================================================


def rebuild_single_scene_audio(
    scene_json_path: str, scene_id: str, output_dir: str, voicevox_url: str = VOICEVOX_URL
) -> bool:
    """Rebuild audio for a single scene and update timing.json.

    This function is called by pipeline.py's --rebuild-scene mode.
    It does NOT modify the existing full-build code path.

    Steps:
      1. Load scene_definition.json, find the target scene
      2. Run auto_generate_narration_speech (idempotent)
      3. Call process_scene() for the target scene only
      4. Load existing timing.json
      5. Replace the target scene's entry
      6. Recalculate global_start/global_end for ALL scenes
      7. Write updated timing.json

    Returns True on success.
    """
    # Load scene definition
    with open(scene_json_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    # Build ordered list of scene_ids and find the target scene
    scene_order = []
    target_scene = None
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            scene_order.append(scene["scene_id"])
            if scene["scene_id"] == scene_id:
                target_scene = scene

    if target_scene is None:
        print(f"[PARTIAL REBUILD] ERROR: Scene '{scene_id}' not found in scene_definition.json")
        return False

    # Auto-generate narration_speech if needed (idempotent, modifies scene_def in-place)
    auto_generate_narration_speech(scene_def)

    # Phase 0: Rule-based misreading fix.
    # The full pipeline applies this in main() but partial rebuild used to skip
    # it, so new scenes added via --rebuild-scene (or this function directly)
    # got raw narration_speech with no dict-based corrections. The ある回 case:
    # math_11b "辺" → mis-read as "あたり" because the 辺→へん rule never ran.
    # Fix applies the dict and saves the updated scene_def to disk so subsequent
    # runs see the corrected narration_speech.
    rule_diffs = apply_known_misreading_fixes(scene_def, dry_run=False)
    if rule_diffs:
        print(f"[PARTIAL REBUILD] Applied {len(rule_diffs)} rule-based misreading fix(es)")
        for d in rule_diffs[:10]:
            print(f"  {d['scene_id']}[{d['index']}]: {d['before'][:50]}...")
            print(f"    -> {d['after'][:50]}...")
        if len(rule_diffs) > 10:
            print(f"  ... and {len(rule_diffs) - 10} more")
        with open(scene_json_path, "w", encoding="utf-8") as f:
            json.dump(scene_def, f, ensure_ascii=False, indent=2)
        print(f"  Saved updates to {scene_json_path}")

    # Re-find target_scene after in-place modification
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            if scene["scene_id"] == scene_id:
                target_scene = scene
                break

    # Check VOICEVOX connection
    try:
        import requests

        resp = requests.get(f"{voicevox_url}/version", timeout=5)
        resp.raise_for_status()
        print(f"[PARTIAL REBUILD] VOICEVOX connected: version {resp.text}")
    except Exception as e:
        print(f"[PARTIAL REBUILD] ERROR: Cannot connect to VOICEVOX at {voicevox_url}: {e}")
        return False

    # Register dictionary
    n_registered = register_user_dict(voicevox_url, DICT_FILE)
    if n_registered > 0:
        print(f"[PARTIAL REBUILD] Registered {n_registered} new dictionary entries")

    # Generate audio for the single scene
    audio_dir = os.path.join(output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    print(f"[PARTIAL REBUILD] Generating audio for scene '{scene_id}'...")
    scene_timing = process_scene(target_scene, audio_dir, voicevox_url, dry_run=False)

    # Load existing timing.json
    timing_path = os.path.join(output_dir, "timing.json")
    if not os.path.exists(timing_path):
        print(f"[PARTIAL REBUILD] ERROR: timing.json not found: {timing_path}")
        return False

    with open(timing_path, encoding="utf-8") as f:
        timing_data = json.load(f)

    old_duration = timing_data["scenes"].get(scene_id, {}).get("duration", 0.0)
    new_duration = scene_timing["duration"]

    # Replace the target scene's entry in timing_data
    timing_data["scenes"][scene_id] = scene_timing

    # Recalculate global_start/global_end for ALL scenes in document order
    global_offset = 0.0
    total_duration = 0.0
    for sid in scene_order:
        if sid not in timing_data["scenes"]:
            continue
        entry = timing_data["scenes"][sid]
        entry["global_start"] = round(global_offset, 3)
        entry["global_end"] = round(global_offset + entry["duration"], 3)
        global_offset += entry.get("duration_with_pause", entry["duration"] + 0.5)
        total_duration = global_offset

    timing_data["total_duration"] = round(total_duration, 3)
    timing_data["total_duration_minutes"] = round(total_duration / 60, 2)

    # Sanity check: duration shift should be reasonable
    duration_shift = abs(new_duration - old_duration)
    if duration_shift > 10.0:
        print(
            f"[PARTIAL REBUILD] WARN: Duration shifted by {duration_shift:.1f}s "
            f"({old_duration:.1f}s → {new_duration:.1f}s)"
        )

    # Write updated timing.json
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing_data, f, ensure_ascii=False, indent=2)

    print(
        f"[PARTIAL REBUILD] Audio rebuilt: {scene_id} ({old_duration:.1f}s → {new_duration:.1f}s)"
    )
    print(
        f"[PARTIAL REBUILD] timing.json updated "
        f"(total: {timing_data['total_duration']:.1f}s / "
        f"{timing_data['total_duration_minutes']:.1f} min)"
    )
    return True


if __name__ == "__main__":
    main()
