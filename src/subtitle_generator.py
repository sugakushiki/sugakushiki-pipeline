"""
subtitle_generator.py - Generate SRT and drawtext filter_script from timing.json

Usage:
    python subtitle_generator.py timing.json --output-dir examples/moriarty
    python subtitle_generator.py timing.json --output-dir examples/moriarty --scene-json scene_definition.json
    python subtitle_generator.py timing.json --output-dir examples/moriarty --scene-level

Input:  timing.json (from audio_generator.py)
        scene_definition.json (optional, for visual-type-aware subtitle margins)
Output: {output_dir}/subtitles.srt          - Standard SRT file
        {output_dir}/subtitles_drawtext.txt  - FFmpeg drawtext filter_script

Subtitle margin adjustment:
    When --scene-json is provided, subtitle Y-position is adjusted per scene:
    - ken_burns / text_overlay: 160px from bottom (default)
    - manim:                    240px from bottom (avoid Manim label overlap)
    - route_map:                220px from bottom (avoid map legend overlap)

The drawtext filter_script is used by video_assembler.py for subtitle rendering.
SRT is generated for reference and potential future use (e.g., YouTube upload).
"""

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import requests

# ---------------------------------------------------------------------------
# Drawtext settings (confirmed in Weekend 2)
# ---------------------------------------------------------------------------
FONT_FILE = "_font.ttc"  # Local copy of BIZ-UDMinchoM.ttc (Windows workaround)
FONT_SIZE = 42
BOTTOM_MARGIN = 160  # pixels from bottom (default for ken_burns, text_overlay)
BOTTOM_MARGIN_MANIM = 240  # pixels from bottom for manim scenes (avoid label overlap)
BOTTOM_MARGIN_ROUTE = 220  # pixels from bottom for route_map scenes (avoid legend overlap)
FONT_COLOR = "white"
BORDER_WIDTH = 3  # text border for readability
BORDER_COLOR = "black"
VIDEO_HEIGHT_VAR = "h"  # FFmpeg variable for video height


MAX_CHARS = 25  # Max characters per subtitle line


def build_visual_type_map(scene_def: dict) -> dict[str, str]:
    """Build scene_id → visual type mapping from scene_definition.json.

    Returns e.g. {"intro_01": "ken_burns", "math_03": "manim", ...}
    """
    vtype_map = {}
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            vtype = scene.get("visual", {}).get("type", "")
            if sid:
                vtype_map[sid] = vtype
    return vtype_map


def get_bottom_margin(visual_type: str) -> int:
    """Return appropriate bottom margin for subtitle based on visual type.

    Manim scenes have labels at the bottom → push subtitles higher.
    Route map scenes have legend at the bottom → push subtitles higher.
    """
    if visual_type == "manim":
        return BOTTOM_MARGIN_MANIM
    elif visual_type == "route_map":
        return BOTTOM_MARGIN_ROUTE
    else:
        return BOTTOM_MARGIN


# ---------------------------------------------------------------------------
# Date numeral → Arabic for subtitle display (structural, all episodes).
# Narration source stays in kanji (spoken-style); audio reads narration_speech
# so it is unaffected. Subtitles render 年/月/日 dates in Arabic for readability
# and consistency with on-screen Manim year labels (1609 等). user request,
# ある回 Kepler.
# ---------------------------------------------------------------------------
_KANJI_POS = {
    "〇": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
}
_KANJI_D = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _trad_kanji_to_int(s: str) -> int:
    """Traditional kanji numeral (1-31, may contain 十) -> int."""
    if s == "十":
        return 10
    if "十" in s:
        a, b = s.split("十")
        return (_KANJI_D[a] if a else 1) * 10 + (_KANJI_D[b] if b else 0)
    return _KANJI_D[s]


def dates_to_arabic(text: str) -> str:
    """Convert kanji DATE numerals (year/month/day) to Arabic for subtitles.

    - Years: 3-4 positional digit-kanji + 年 (一六〇九年 -> 1609年, 四一五年 -> 415年,
      紀元前二六二年 -> 紀元前262年). ある回 強化: {4} -> {3,4} で古代の3桁年号と
      BC 年号 (紀元前/前 接頭の3桁) も変換 (従来は4桁のみで 415年/262年 を取りこぼした)。
      Durations like 二千年/五十七年 use 千/十 and are NOT matched; 2桁以下も非対象
      (「二三年」=数年 等の口語 duration の誤変換を避ける)。
      Note: VOICEVOX は漢数字年号も正しく読む (四一五年→ヨンヒャクジュウゴネン) ため、
      これは字幕表示専用の変換であり音声 (narration_speech) には影響しない。
    - Months: 1-12 + 月 (十二月 -> 12月); ヶ月 (十四ヶ月) is excluded.
    - Days: 1-31 + 日 (二十七日 -> 27日). 近日点/遠日点 are safe because 日 there
      is preceded by 近/遠 (not a digit kanji), so they never match.
    Idempotent (Arabic input passes through). Audio uses narration_speech and is
    unaffected by this display-only conversion.
    """
    text = re.sub(
        r"([一二三四五六七八九〇]{3,4})年",
        lambda m: "".join(_KANJI_POS[c] for c in m.group(1)) + "年",
        text,
    )
    text = re.sub(
        r"(?<!ヶ)(十[一二]?|[一二三四五六七八九])月",
        lambda m: str(_trad_kanji_to_int(m.group(1))) + "月",
        text,
    )
    text = re.sub(
        r"(?<!ヶ)((?:[二三]?十[一二三四五六七八九]?)|[一二三四五六七八九])日",
        lambda m: str(_trad_kanji_to_int(m.group(1))) + "日",
        text,
    )
    return text


def split_segments(text: str) -> list[str]:
    """Split narration text at | markers into subtitle segments."""
    text = dates_to_arabic(text)
    raw = [seg.strip() for seg in text.split("|") if seg.strip()]
    fixed = _fix_bad_breaks(raw)
    final = []
    for seg in fixed:
        if len(seg) > MAX_CHARS:
            final.extend(_auto_split(seg))
        else:
            final.append(seg)
    return final


def _fix_bad_breaks(segments: list[str]) -> list[str]:
    """Fix segments that start with closing brackets or other bad patterns.

    Rules:
    - If a segment starts with 」）】）, merge it back to the previous segment
    - If a segment is only 1-2 chars (e.g. orphaned punctuation), merge it
    """
    if len(segments) <= 1:
        return segments

    result = [segments[0]]
    for seg in segments[1:]:
        should_merge = False

        # Starts with closing bracket/quote
        if seg and seg[0] in "」）】）》』":
            should_merge = True

        # Very short orphaned segment (1-2 chars)
        if len(seg) <= 2:
            should_merge = True

        if should_merge and result:
            result[-1] = result[-1] + seg
        else:
            result.append(seg)

    return result


def _auto_split(text: str) -> list[str]:
    """Split a long subtitle segment (>MAX_CHARS) at natural break points.

    Priority (higher score wins near the middle):
    1. After 、 。 」 ） (Japanese punctuation) — score 100
    2. After ASCII , . ; : followed by space (Latin punctuation) — score 90
    3. After particles: は が を に で と の も へ — score 50
    4. Space preceded by an ASCII alphanumeric char (Latin word boundary) — score 30
    5. Midpoint fallback

    Never split inside 「...」 pairs.

    Latin scoring (priorities 2, 4) prevents French/English quotes from
    being bisected mid-word (e.g. "je le vois, mais je ne le crois pas").
    """
    if len(text) <= MAX_CHARS:
        return [text]

    best_pos = -1
    best_score = -1
    target = len(text) // 2  # prefer splits near the middle

    # Find 「」 ranges to avoid splitting inside quotes
    quote_ranges = []
    depth = 0
    quote_start = -1
    for i, ch in enumerate(text):
        if ch == "「":
            if depth == 0:
                quote_start = i
            depth += 1
        elif ch == "」":
            depth -= 1
            if depth == 0 and quote_start >= 0:
                quote_ranges.append((quote_start, i))
                quote_start = -1

    def in_quotes(pos):
        return any(s <= pos <= e for s, e in quote_ranges)

    # Score each potential split point (split AFTER position i)
    for i in range(2, len(text) - 2):
        if in_quotes(i):
            continue

        ch = text[i]
        score = 0

        # Priority 1: after Japanese punctuation
        if ch in "、。」）":
            score = 100
        # Priority 2: space preceded by ASCII punctuation
        # (natural break in Latin quotes: "..., " / "... . ")
        elif ch == " " and i > 0 and text[i - 1] in ",.;:":
            score = 90
        # Priority 3: after common particles (check char + next char context)
        elif ch in "はがをにでとのもへ":
            # Simple heuristic: these are likely particles if preceded by
            # kanji/katakana/hiragana and not part of a word
            score = 50
        # Priority 4: Latin word boundary — space preceded by ASCII alnum
        # (not Japanese; avoids bisecting "je ne le crois" at "ne le")
        elif ch == " " and i > 0 and text[i - 1].isascii() and text[i - 1].isalnum():
            score = 30

        if score > 0:
            # Prefer splits closer to the middle
            distance_penalty = abs(i - target)
            final_score = score * 1000 - distance_penalty

            if final_score > best_score:
                best_score = final_score
                best_pos = i

    if best_pos > 0:
        left = text[: best_pos + 1].strip()
        right = text[best_pos + 1 :].strip()
        # Recurse if still too long
        result = []
        result.extend(_auto_split(left) if len(left) > MAX_CHARS else [left])
        result.extend(_auto_split(right) if len(right) > MAX_CHARS else [right])
        return [s for s in result if s]

    # Fallback: split at midpoint
    mid = len(text) // 2
    return [text[:mid].strip(), text[mid:].strip()]


# ---------------------------------------------------------------------------
# Per-segment subtitle timing via VOICEVOX mora/pause durations
#
# Character count is a poor proxy for spoken time: brackets 『』「」（）are
# silent, the middle dot ・ injects a ~0.5s pause, year/number strings run
# ~2.6 morae per character and kanji ~1.5-1.8. Splitting a sentence's measured
# duration across its | segments by raw character count therefore drifts the
# subtitle ahead of (or behind) the audio — worst at year-leading sentences
# (measured up to ~0.7s). Weighting each segment by the duration VOICEVOX
# actually speaks it removes that drift. Falls back to character count when
# VOICEVOX is unreachable so the step never hard-fails.
# ---------------------------------------------------------------------------
VOICEVOX_SPEAKER_ID = 13  # 青山龍星ノーマル (matches audio_generator.SPEAKER_ID)
_SPOKEN_DUR_CACHE: dict[str, float] = {}


def voicevox_spoken_duration(text: str, voicevox_url: str) -> float | None:
    """Spoken duration in seconds (excluding edge silence) of `text`, measured
    from VOICEVOX /audio_query mora + pause lengths. Returns None on any
    failure. Cached per text."""
    if text in _SPOKEN_DUR_CACHE:
        return _SPOKEN_DUR_CACHE[text]
    try:
        resp = requests.post(
            f"{voicevox_url}/audio_query",
            params={"text": text, "speaker": VOICEVOX_SPEAKER_ID},
            timeout=10,
        )
        resp.raise_for_status()
        query = resp.json()
    except (requests.RequestException, ValueError):
        return None
    dur = 0.0
    for phrase in query.get("accent_phrases", []):
        for mora in phrase.get("moras", []):
            dur += (mora.get("consonant_length") or 0.0) + (mora.get("vowel_length") or 0.0)
        pause = phrase.get("pause_mora")
        if pause:
            dur += pause.get("vowel_length") or 0.0
    _SPOKEN_DUR_CACHE[text] = dur
    return dur


# Calibrated from VOICEVOX measurements (speaker 13): per-character "mora
# weight" approximating spoken duration. Char count alone drifts because of
# these; the weights below were chosen to match measured morae/pauses.
_SILENT_CHARS = set("「」『』（）()【】［］〔〕《》〈〉　 ")
_SMALL_KANA = set("ぁぃぅぇぉゃゅょゎ" + "ァィゥェォャュョヮ")  # fold into preceding mora

# Standalone Latin letters used as math variables are spoken as their full
# katakana letter-name (x = エックス ≈ 4 morae, w = ダブリュー ≈ 4), not one
# character-time. Character count therefore badly under-counts formula cards
# (the Boole x²=x / 1−x hook, S/N, W log2, ...). Applied ONLY to a single letter
# flanked by non-letters; a letter inside a word (French/English quotes such as
# "je ne le crois pas") keeps ~1 mora/char so quote cards are not inflated.
_LATIN_VAR_MORAE = {
    "a": 2.0, "b": 2.0, "c": 2.0, "d": 2.0, "e": 2.0, "f": 2.0, "g": 2.0,
    "h": 3.0, "i": 2.0, "j": 2.0, "k": 2.0, "l": 2.0, "m": 2.0, "n": 2.0,
    "o": 2.0, "p": 2.0, "q": 3.0, "r": 3.0, "s": 2.0, "t": 2.0, "u": 2.0,
    "v": 2.0, "w": 4.0, "x": 4.0, "y": 2.0, "z": 3.0,
}  # fmt: skip
# Greek letters are always read as their names (π=パイ 2, ε=イプシロン 4,
# δ=デルタ 3, Σ=シグマ 3, ...) and never occur in prose, so weighting is safe.
_GREEK_MORAE = {
    "α": 4.0, "β": 3.0, "γ": 3.0, "δ": 3.0, "ε": 4.0, "ζ": 2.0, "η": 2.0,
    "θ": 3.0, "ι": 3.0, "κ": 2.0, "λ": 3.0, "μ": 2.0, "ν": 2.0, "ξ": 3.0,
    "ο": 2.0, "π": 2.0, "ρ": 2.0, "σ": 3.0, "ς": 3.0, "τ": 2.0, "υ": 3.0,
    "φ": 2.0, "χ": 2.0, "ψ": 3.0, "ω": 3.0,
    "Α": 4.0, "Β": 3.0, "Γ": 3.0, "Δ": 3.0, "Θ": 3.0, "Λ": 3.0, "Ξ": 3.0,
    "Π": 2.0, "Σ": 3.0, "Φ": 2.0, "Ψ": 3.0, "Ω": 3.0,
}  # fmt: skip
# Math operators read as multi-mora words. Deliberately EXCLUDES '=' / '＝':
# in this corpus those are overwhelmingly foreign-name separators
# (ジャン=バティスト, ブール＝ラ＝レーヌ) rather than イコール, so weighting them
# as equals would over-count name cards. Also excludes '^' '/' ASCII '-' '<' '>'
# (context-dependent). The tokens kept below only ever appear in genuine
# formulas, where character count under-counts them.
_MATH_OP_MORAE = {
    "−": 2.0,  # U+2212 MINUS SIGN -> ひく / マイナス (ASCII '-' left alone: ambiguous)
    "+": 3.0,  # プラス
    "＋": 3.0,  # U+FF0B fullwidth plus -> プラス
    "×": 3.0,  # かける
    "÷": 2.0,  # わる
    "√": 3.0,  # ルート
    "%": 5.0,  # パーセント
}  # fmt: skip


def _estimate_morae(seg: str) -> float:
    """Estimate spoken-duration units (~morae) of a subtitle segment, calibrated
    from VOICEVOX. Handles the drift sources character count misjudges:
    silent brackets (0), middle dot ・ (~0.5s pause ~= 4),、(~1.5)。(~2.5),
    digit runs (~2.6/char, years), kanji (~1.7), small kana (0), and math tokens
    that read as multi-mora words: standalone Latin variables (x=エックス≈4),
    Greek letters (π/ε/δ...), and operators (−/+/√/%). This matters most for
    Cloud episodes, whose subtitle timing relies on this estimate rather than a
    VOICEVOX measurement of the display text."""
    w = 0.0
    n = len(seg)
    for i, ch in enumerate(seg):
        if ch in _SILENT_CHARS:
            continue
        if ch == "・":
            w += 4.0
        elif ch == "、":
            w += 1.5
        elif ch in "。.．!！?？":
            w += 2.5
        elif ch in _MATH_OP_MORAE:
            w += _MATH_OP_MORAE[ch]
        elif ch.isdigit():
            w += 2.6
        elif ch in _SMALL_KANA:
            w += 0.0
        elif ch in "ーっッ":
            w += 1.0
        elif ("぀" <= ch <= "ゟ") or ("゠" <= ch <= "ヿ"):
            w += 1.0  # kana
        elif "㐀" <= ch <= "鿿":
            w += 1.7  # kanji
        elif ch in _GREEK_MORAE:
            w += _GREEK_MORAE[ch]  # Greek math symbol read as its name
        elif ch.isascii() and ch.isalpha():
            # Standalone Latin letter = math variable (read エックス/ダブリュー...);
            # a letter adjacent to another Latin letter is part of a word (~1 mora).
            prev_alpha = i > 0 and seg[i - 1].isascii() and seg[i - 1].isalpha()
            next_alpha = i + 1 < n and seg[i + 1].isascii() and seg[i + 1].isalpha()
            w += 1.0 if (prev_alpha or next_alpha) else _LATIN_VAR_MORAE.get(ch.lower(), 2.5)
        else:
            w += 1.0  # other
    return max(w, 0.5)


def segment_weights(segments: list[str], voicevox_url: str | None = None) -> list[float]:
    """Weight for splitting a sentence's duration across its segments.

    Default: a calibrated local mora estimate (instant, no network) that fixes
    the year / middle-dot / bracket / kanji drift. If ``voicevox_url`` is given,
    use the exact VOICEVOX-measured spoken duration instead (accurate but
    ~2s/segment, so opt-in only); falls back to the local estimate on failure."""
    if voicevox_url:
        durations = []
        ok = True
        for seg in segments:
            d = voicevox_spoken_duration(seg, voicevox_url)
            if d is None or d <= 0.0:
                ok = False
                break
            durations.append(d)
        if ok:
            return durations
    return [_estimate_morae(s) for s in segments]


def prefetch_durations(segments: list[str], voicevox_url: str, workers: int = 12) -> None:
    """Warm the spoken-duration cache for many segments concurrently.

    VOICEVOX /audio_query is ~2s serial but parallelises well (~0.13s effective
    at 16 workers), turning a ~10-min episode into ~1 min. Failures are left
    uncached so segment_weights falls back to the local estimate for them."""
    todo = [s for s in dict.fromkeys(segments) if s not in _SPOKEN_DUR_CACHE]
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(lambda s: voicevox_spoken_duration(s, voicevox_url), todo))


def distribute_time(
    sentence_start: float,
    sentence_end: float,
    segments: list[str],
    weights: list[float] | None = None,
) -> list[dict]:
    """Distribute sentence time across segments proportionally by `weights`
    (measured spoken duration when provided, else character count).

    Returns list of {text, start, end} for each segment.
    """
    if not segments:
        return []
    if weights is None:
        weights = [float(len(s)) for s in segments]
    total_weight = sum(weights)
    if total_weight <= 0:
        weights = [1.0] * len(segments)
        total_weight = float(len(segments))

    duration = sentence_end - sentence_start
    result = []
    current = sentence_start

    for i, seg in enumerate(segments):
        if i == len(segments) - 1:
            # Last segment gets remaining time (avoid float rounding gaps)
            seg_end = sentence_end
        else:
            seg_end = current + duration * (weights[i] / total_weight)

        result.append(
            {
                "text": seg,
                "start": round(current, 3),
                "end": round(seg_end, 3),
            }
        )
        current = seg_end

    return result


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter.

    In drawtext, these characters need escaping: : \\ ; %.
    The single quote (') is NOT escaped but *converted* to the typographically
    identical U+2019 (’): the shell-style `'\\''` escape works on a command line
    but NOT inside an ffmpeg ``-filter_script`` file (which is parsed with no
    shell), where it breaks the quoting so the drawtext options (fontsize,
    enable=between(...), ...) leak into the frame as literal burnt-in text. This
    bit ある回 ("df = f'(X)dX ...") -- the filter string was rendered
    persistently over the back half of the video. Converting to U+2019 (mirrors
    the '%' -> '％' strategy below) sidesteps the escaping entirely and renders a
    correct apostrophe/prime for derivatives.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")
    # Semicolons in filter_script context
    text = text.replace(";", "\\;")
    # FFmpeg drawtext cannot handle literal '%' (interprets as format specifier
    # and drops the line with "Stray %" warning). Replace with full-width '％'
    # which renders visually identical in Japanese subtitles.
    text = text.replace("%", "\uff05")
    return text


def validate_drawtext_lines(lines: list[str]) -> list[str]:
    """Return drawtext lines whose ``text='...'`` quoting is broken.

    A raw ASCII apostrophe (') left inside a text value breaks the ffmpeg
    ``-filter_script`` quoting: the value closes early and the drawtext options
    (fontsize=..., enable=between(...)) leak into the frame as persistent
    burnt-in text (ある回 "f'(X)dX ...", visible over the whole back half
    of the video). escape_drawtext converts every ASCII ' to U+2019, so any ASCII
    ' surviving inside a text value means the escaping failed. Deterministic
    backstop that guards the whole special-character class, not just the
    apostrophe already fixed at the source.
    """
    bad = []
    for ln in lines:
        m = re.search(r":text='(.*?)':fontsize=", ln)
        if m and "'" in m.group(1):
            bad.append(ln)
    return bad


def generate_entries(
    timing_data: dict, scene_level: bool = False, voicevox_url: str | None = None
) -> list[dict]:
    """Generate subtitle entries from timing data.

    Args:
        timing_data: Parsed timing.json
        scene_level: If True, use scene-local timestamps.
                     If False, use global timestamps (for full-video SRT).
        voicevox_url: If set, split each sentence's duration across its | segments
                     by VOICEVOX-measured spoken duration (handles years, ・,
                     brackets, kanji). If None or unreachable, falls back to
                     character-count splitting per sentence.

    Returns:
        List of {index, start, end, text} entries.
    """
    entries = []

    # Warm the VOICEVOX duration cache for every multi-segment sentence in one
    # parallel batch (per-segment serial querying would be ~10x slower).
    if voicevox_url:
        all_segments = []
        for scene in timing_data["scenes"].values():
            for sentence in scene["sentences"]:
                segs = split_segments(sentence["text"])
                if len(segs) > 1:
                    all_segments.extend(segs)
        prefetch_durations(all_segments, voicevox_url)

    # Iterate scenes in order
    for scene_id, scene in timing_data["scenes"].items():
        global_start = scene.get("global_start", 0.0)

        for sentence in scene["sentences"]:
            raw_text = sentence["text"]  # Contains | markers
            sent_start = sentence["start"]
            sent_end = sentence["end"]

            if not scene_level:
                # Convert to global timestamps
                sent_start += global_start
                sent_end += global_start

            segments = split_segments(raw_text)

            if len(segments) <= 1:
                # No | markers or single segment: one subtitle entry
                clean = raw_text.replace("|", "").strip()
                if clean:
                    entries.append(
                        {
                            "start": sent_start,
                            "end": sent_end,
                            "text": clean,
                            "scene_id": scene_id,
                        }
                    )
            else:
                # Multiple segments: distribute time by measured spoken duration
                weights = segment_weights(segments, voicevox_url)
                distributed = distribute_time(sent_start, sent_end, segments, weights)
                for seg in distributed:
                    seg["scene_id"] = scene_id
                    entries.append(seg)

    # Assign sequential index
    for i, entry in enumerate(entries):
        entry["index"] = i + 1

    return entries


def write_srt(entries: list[dict], output_path: str):
    """Write standard SRT file."""
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n")
            f.write("\n")


def build_era_map(scene_def: dict) -> dict[str, str]:
    """Build scene_id → era/date caption string from scene_definition.json.

    Each scene may carry an ``era_caption`` field (e.g. "1785年" or
    "確率論｜1774年"). Used to burn a persistent top-right date caption per
    scene so the viewer keeps temporal orientation as the person/theme
    pillars jump between years.
    """
    era_map: dict[str, str] = {}
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "")
            cap = scene.get("era_caption")
            if sid and cap:
                era_map[sid] = str(cap)
    return era_map


def write_drawtext_filter_script(
    entries: list[dict],
    output_path: str,
    visual_type_map: dict[str, str] = None,
    era_map: dict[str, str] = None,
):
    """Write FFmpeg drawtext filter_script file.

    Each entry becomes a drawtext line with enable='between(t,start,end)'.
    Uses local font copy (_font.ttc) to avoid Windows path issues.

    Bottom margin is adjusted per scene's visual type:
    - manim scenes:    240px (avoid overlap with Manim labels)
    - route_map scenes: 220px (avoid overlap with map legend)
    - other scenes:    160px (default)

    The filter_script is used with:
        ffmpeg -i input.mp4 -filter_script:v subtitles_drawtext.txt output.mp4

    Note: All drawtext entries are joined with comma (,) as a single
    filter chain, which FFmpeg processes as simultaneous filters
    (only the enabled one shows at any time).
    """
    if visual_type_map is None:
        visual_type_map = {}

    lines = []
    for entry in entries:
        escaped_text = escape_drawtext(entry["text"])
        start = entry["start"]
        end = entry["end"]

        # Determine bottom margin based on visual type of this scene
        scene_id = entry.get("scene_id", "")
        vtype = visual_type_map.get(scene_id, "")
        margin = get_bottom_margin(vtype)

        # drawtext filter with enable condition
        dt = (
            f"drawtext=fontfile={FONT_FILE}"
            f":text='{escaped_text}'"
            f":fontsize={FONT_SIZE}"
            f":fontcolor={FONT_COLOR}"
            f":borderw={BORDER_WIDTH}"
            f":bordercolor={BORDER_COLOR}"
            f":x=(w-text_w)/2"
            f":y={VIDEO_HEIGHT_VAR}-{margin}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
        )
        lines.append(dt)

    # Per-scene era/date caption: a small persistent label in the TOP-RIGHT
    # corner, shown for the whole scene span, so the viewer always knows
    # "when" they are (the person/theme pillars jump across years).
    if era_map:
        ranges: dict[str, tuple[float, float]] = {}
        for entry in entries:
            sid = entry.get("scene_id", "")
            if not sid:
                continue
            s, e = entry["start"], entry["end"]
            if sid in ranges:
                ranges[sid] = (min(ranges[sid][0], s), max(ranges[sid][1], e))
            else:
                ranges[sid] = (s, e)
        for sid, (s, e) in ranges.items():
            label = era_map.get(sid)
            if not label:
                continue
            escaped_label = escape_drawtext(label)
            dt = (
                f"drawtext=fontfile={FONT_FILE}"
                f":text='{escaped_label}'"
                f":fontsize=30"
                f":fontcolor=0xE2B714"  # ACCENT_GOLD
                f":borderw={BORDER_WIDTH}"
                f":bordercolor={BORDER_COLOR}"
                f":x=w-text_w-45"
                f":y=42"
                f":enable='between(t,{s:.3f},{e:.3f})'"
            )
            lines.append(dt)

    bad = validate_drawtext_lines(lines)
    if bad:
        print(
            f"  [WARN] drawtext filter lint: {len(bad)} 行で text='...' のクォートが壊れています "
            "(生の ASCII ' → フィルタ options が焼き込み漏れ)。escape_drawtext が ' を U+2019 に "
            "変換するはず -- assemble 前に要調査:"
        )
        for b in bad[:3]:
            print(f"    {b[:90]}")

    with open(output_path, "w", encoding="utf-8") as f:
        # filter_script format: one filter chain
        f.write(",\n".join(lines))
        f.write("\n")


def timing_signature(timing_data: dict) -> str:
    """Deterministic digest of per-scene durations the subtitles were baked from.

    Guard-B2: the narration_hash sidecar only detects narration TEXT
    edits. It does NOT detect timing-only changes -- when a reading fix
    (narration_speech_cloud) or speed normalization (cloud_speed_qa --apply)
    re-synthesizes audio, the narration text stays byte-identical but the scene
    durations (timing.json) shift, so subtitles.srt timestamps go stale while
    the text hash still matches (字幕/音声 desync undetected). Storing this
    signature lets the assemble preflight + G2 compare the timing the subtitles
    were baked against vs the current timing.json. MUST stay identical to pipeline._timing_signature.
    """
    import hashlib

    scenes = timing_data.get("scenes", {}) if isinstance(timing_data, dict) else {}
    parts = [f"{sid}:{round(sc.get('duration', 0) or 0, 3)}" for sid, sc in sorted(scenes.items())]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description="Generate subtitles from timing.json")
    parser.add_argument("timing_json", help="Path to timing.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument(
        "--scene-json",
        default=None,
        help="Path to scene_definition.json (for visual-type-aware subtitle margins)",
    )
    parser.add_argument(
        "--scene-level",
        action="store_true",
        help="Use scene-local timestamps instead of global",
    )
    parser.add_argument(
        "--no-voicevox-timing",
        action="store_true",
        help="Disable VOICEVOX spoken-duration subtitle timing and use the "
        "calibrated local mora estimate instead (no network). Default: VOICEVOX "
        "timing (exact for years/numbers/・/symbols, parallelised to ~1 min).",
    )
    parser.add_argument(
        "--voicevox-url",
        default="http://localhost:50021",
        help="VOICEVOX URL for subtitle segment timing (default: localhost:50021)",
    )
    args = parser.parse_args()

    # Load timing data
    with open(args.timing_json, encoding="utf-8") as f:
        timing_data = json.load(f)

    # Load scene definition for visual type mapping + era captions (optional)
    visual_type_map = {}
    era_map = {}
    if args.scene_json and os.path.exists(args.scene_json):
        with open(args.scene_json, encoding="utf-8") as f:
            scene_def = json.load(f)
        visual_type_map = build_visual_type_map(scene_def)
        era_map = build_era_map(scene_def)
        if era_map:
            print(f"  Era captions: {len(era_map)} scene(s) tagged")
        manim_count = sum(1 for v in visual_type_map.values() if v == "manim")
        route_count = sum(1 for v in visual_type_map.values() if v == "route_map")
        if manim_count or route_count:
            print(
                f"  Margin adjust: {manim_count} manim (→{BOTTOM_MARGIN_MANIM}px),"
                f" {route_count} route_map (→{BOTTOM_MARGIN_ROUTE}px)"
            )

    os.makedirs(args.output_dir, exist_ok=True)

    # Subtitle segment timing. Default: exact VOICEVOX spoken duration (correct
    # for year/number place-value, ・, brackets, symbols; parallel-prefetched to
    # ~1 min). --no-voicevox-timing falls back to the calibrated local mora
    # estimate (no network, approximate). VOICEVOX unreachable -> auto-fallback.
    voicevox_url = None if args.no_voicevox_timing else args.voicevox_url
    if voicevox_url and voicevox_spoken_duration("テスト", voicevox_url) is None:
        print(
            f"  [WARN] VOICEVOX unreachable at {voicevox_url}; "
            "subtitle timing falls back to local mora estimate"
        )
        voicevox_url = None
    print(
        "  Subtitle timing: "
        + (
            "VOICEVOX spoken-duration (parallel)"
            if voicevox_url
            else "local mora-estimate (fallback)"
        )
    )

    # Generate subtitle entries
    entries = generate_entries(timing_data, scene_level=args.scene_level, voicevox_url=voicevox_url)

    # Write SRT
    srt_path = os.path.join(args.output_dir, "subtitles.srt")
    write_srt(entries, srt_path)

    # Write drawtext filter_script (with visual-type-aware margins)
    drawtext_path = os.path.join(args.output_dir, "subtitles_drawtext.txt")
    write_drawtext_filter_script(entries, drawtext_path, visual_type_map, era_map)

    # G2: write sidecar metadata with narration hash for
    # subtitle/audio sync verification. pipeline verify_outputs compares the
    # embedded hash with current scene_def narration to detect stale
    # subtitles.srt (when --steps audio,visuals,assemble,bgm skips subtitles
    # step but scene_def narration was edited → 字幕/音声 齟齬).
    if args.scene_json and os.path.exists(args.scene_json):
        try:
            import datetime as _dt2
            import hashlib

            with open(args.scene_json, encoding="utf-8") as _f:
                _scene_def_for_hash = json.load(_f)
            # Concatenate all narration lines for hash (canonical, deterministic)
            _narration_blob = []
            for _sec in _scene_def_for_hash.get("sections", []):
                for _sc in _sec.get("scenes", []):
                    for _n in _sc.get("narration", []):
                        _narration_blob.append(_n)
            _narration_text = "\n".join(_narration_blob)
            _hash = hashlib.sha256(_narration_text.encode("utf-8")).hexdigest()[:16]
            _meta = {
                "narration_hash": _hash,
                "narration_lines": len(_narration_blob),
                # Guard-B2: timing the subtitles were baked from, so the
                # assemble preflight can catch timing-only staleness (reading /
                # speed-norm changed durations while narration text is unchanged).
                "timing_hash": timing_signature(timing_data),
                "timing_total_duration": round(timing_data.get("total_duration", 0) or 0, 3),
                "generated_at": _dt2.datetime.now().isoformat(timespec="seconds"),
                "scene_json": os.path.abspath(args.scene_json),
            }
            _meta_path = os.path.join(args.output_dir, "_subtitles_meta.json")
            with open(_meta_path, "w", encoding="utf-8") as _f:
                json.dump(_meta, _f, ensure_ascii=False, indent=2)
        except Exception as _e:
            print(f"  [WARN] _subtitles_meta.json write failed: {_e}")

    # Summary
    total_duration = timing_data.get("total_duration", 0)
    print("Subtitle generation complete")
    print(f"  Entries:     {len(entries)}")
    print(f"  Duration:    {total_duration:.1f}s ({total_duration / 60:.1f} min)")
    print(f"  SRT:         {srt_path}")
    print(f"  Drawtext:    {drawtext_path}")

    # Validation
    warnings = 0
    for entry in entries:
        if entry["end"] <= entry["start"]:
            print(
                f"  [WARN] Entry {entry['index']}: end <= start ({entry['start']:.3f}-{entry['end']:.3f})"
            )
            warnings += 1
        if len(entry["text"]) > MAX_CHARS:
            print(
                f"  [WARN] Entry {entry['index']}: {len(entry['text'])} chars > {MAX_CHARS}: {entry['text']}"
            )
            warnings += 1

    if warnings == 0:
        print("  Validation:  All OK")
    else:
        print(f"  Validation:  {warnings} warnings")


if __name__ == "__main__":
    main()
