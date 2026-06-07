"""
subtitle_generator.py - Generate SRT and drawtext filter_script from timing.json

Usage:
    python subtitle_generator.py timing.json --output-dir episodes/001_erdos
    python subtitle_generator.py timing.json --output-dir episodes/001_erdos --scene-json scene_definition.json
    python subtitle_generator.py timing.json --output-dir episodes/001_erdos --scene-level

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
_KANJI_POS = {"〇": "0", "一": "1", "二": "2", "三": "3", "四": "4",
              "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
_KANJI_D = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}


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

    - Years: exactly 4 positional digit-kanji + 年 (一六〇九年 -> 1609年).
      Durations like 二千年/五十七年 use 千/十 and are NOT matched.
    - Months: 1-12 + 月 (十二月 -> 12月); ヶ月 (十四ヶ月) is excluded.
    - Days: 1-31 + 日 (二十七日 -> 27日). 近日点/遠日点 are safe because 日 there
      is preceded by 近/遠 (not a digit kanji), so they never match.
    Idempotent (Arabic input passes through). Audio uses narration_speech and is
    unaffected by this display-only conversion.
    """
    text = re.sub(
        r"([一二三四五六七八九〇]{4})年",
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


def distribute_time(sentence_start: float, sentence_end: float, segments: list[str]) -> list[dict]:
    """Distribute sentence time across segments proportionally by character count.

    Returns list of {text, start, end} for each segment.
    """
    total_chars = sum(len(s) for s in segments)
    if total_chars == 0:
        return []

    duration = sentence_end - sentence_start
    result = []
    current = sentence_start

    for i, seg in enumerate(segments):
        if i == len(segments) - 1:
            # Last segment gets remaining time (avoid float rounding gaps)
            seg_end = sentence_end
        else:
            seg_duration = duration * (len(seg) / total_chars)
            seg_end = current + seg_duration

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
    
    In drawtext, these characters need escaping: : ' \\ 
    In filter_script files, semicolons also need escaping.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "'\\''")
    # Semicolons in filter_script context
    text = text.replace(";", "\\;")
    # FFmpeg drawtext cannot handle literal '%' (interprets as format specifier
    # and drops the line with "Stray %" warning). Replace with full-width '％'
    # which renders visually identical in Japanese subtitles.
    text = text.replace("%", "\uff05")
    return text


def generate_entries(timing_data: dict, scene_level: bool = False) -> list[dict]:
    """Generate subtitle entries from timing data.

    Args:
        timing_data: Parsed timing.json
        scene_level: If True, use scene-local timestamps.
                     If False, use global timestamps (for full-video SRT).

    Returns:
        List of {index, start, end, text} entries.
    """
    entries = []

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
                # Multiple segments: distribute time
                distributed = distribute_time(sent_start, sent_end, segments)
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


def write_drawtext_filter_script(
    entries: list[dict], output_path: str, visual_type_map: dict[str, str] = None
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

    with open(output_path, "w", encoding="utf-8") as f:
        # filter_script format: one filter chain
        f.write(",\n".join(lines))
        f.write("\n")


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
    args = parser.parse_args()

    # Load timing data
    with open(args.timing_json, encoding="utf-8") as f:
        timing_data = json.load(f)

    # Load scene definition for visual type mapping (optional)
    visual_type_map = {}
    if args.scene_json and os.path.exists(args.scene_json):
        with open(args.scene_json, encoding="utf-8") as f:
            scene_def = json.load(f)
        visual_type_map = build_visual_type_map(scene_def)
        manim_count = sum(1 for v in visual_type_map.values() if v == "manim")
        route_count = sum(1 for v in visual_type_map.values() if v == "route_map")
        if manim_count or route_count:
            print(
                f"  Margin adjust: {manim_count} manim (→{BOTTOM_MARGIN_MANIM}px),"
                f" {route_count} route_map (→{BOTTOM_MARGIN_ROUTE}px)"
            )

    os.makedirs(args.output_dir, exist_ok=True)

    # Generate subtitle entries
    entries = generate_entries(timing_data, scene_level=args.scene_level)

    # Write SRT
    srt_path = os.path.join(args.output_dir, "subtitles.srt")
    write_srt(entries, srt_path)

    # Write drawtext filter_script (with visual-type-aware margins)
    drawtext_path = os.path.join(args.output_dir, "subtitles_drawtext.txt")
    write_drawtext_filter_script(entries, drawtext_path, visual_type_map)

    # G2: write sidecar metadata with narration hash for
    # subtitle/audio sync verification. pipeline verify_outputs compares the
    # embedded hash with current scene_def narration to detect stale
    # subtitles.srt (when --steps audio,visuals,assemble,bgm skips subtitles
    # step but scene_def narration was edited → 字幕/音声 齟齬).
    if args.scene_json and os.path.exists(args.scene_json):
        try:
            import hashlib
            import datetime as _dt2

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
