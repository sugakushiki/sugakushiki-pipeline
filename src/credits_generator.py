"""
credits_generator.py - Generate YouTube description text

Generates description.txt with:
  - Episode title + intro text (from scene_definition.json description block)
  - Channel tagline
  - Auto-calculated chapter timestamps with subtitles (from timing.json + description block)
  - Voice synthesis credit (VOICEVOX)
  - BGM credit (from episode_config.json)
  - Visual asset credits (auto-detected from scene types)
  - Wikimedia photo attribution
  - References
  - Hashtags (base tags + episode-specific from description block)

Data priority (LLM-generated > legacy fallback):
  - Intro text:          scene_def.description.intro > config.hook
  - Chapter subtitles:   scene_def.description.chapter_subtitles > section.chapter_title > section.label
  - Tags:                scene_def.description.tags > config.tags

Usage:
    python src/credits_generator.py episodes/001_erdos/episode_config.json
    python src/credits_generator.py episodes/001_erdos/episode_config.json --intro-pause 1.0

Output:
    episodes/001_erdos/description.txt

Sources:
    - episode_config.json    : title, hook (fallback), BGM, tags (fallback)
    - scene_definition.json  : credits, sections, visual types, description block
    - timing.json            : scene durations (for chapter timestamps)
    - wikimedia_credits.json : photo attribution (if exists)
"""

import argparse
import json
import os


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _extract_urls(text: str) -> list[str]:
    """Extract http/https URLs from text, balancing parentheses."""
    import re

    pattern = re.compile(r"https?://\S+")
    urls = set()
    for m in pattern.finditer(text):
        # Strip trailing punctuation EXCEPT ) — balance logic below handles parens
        url = m.group().rstrip(".,;:。、\"'）』」]>")
        # Balance half-width parens (Wikipedia URLs may contain unescaped parens)
        while url.endswith(")"):
            if url.count(")") > url.count("("):
                url = url[:-1]
            else:
                break
        if url:
            urls.add(url)
    return sorted(urls)


def _check_url(url: str, timeout: float = 5.0) -> tuple:
    """Check if URL returns 2xx/3xx. Returns (ok: bool, status_msg: str).

    Tries HEAD first, falls back to GET if HEAD is rejected (405/403).
    """
    import urllib.error
    import urllib.request

    headers = {"User-Agent": "Mozilla/5.0 (compatible; sugakushiki-build)"}
    last_err = "unknown"
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return True, f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (405, 403):
                last_err = f"HTTP {e.code} (HEAD blocked, retrying GET)"
                continue
            return False, f"HTTP {e.code}"
        except Exception as e:
            last_err = f"{type(e).__name__}"
            if method == "HEAD":
                continue
            return False, last_err
    return False, last_err


def validate_reference_urls(text: str, timeout: float = 5.0) -> list:
    """Validate all URLs in description text. Returns list of (url, error) for broken URLs.

    Network-bound; safe-fails on connection errors (returns them as broken).
    Does NOT raise — caller should treat results as warnings.
    """
    urls = _extract_urls(text)
    broken = []
    for url in urls:
        ok, msg = _check_url(url, timeout=timeout)
        if not ok:
            broken.append((url, msg))
    return broken


# ---------------------------------------------------------------------------
# Day 21 強化 H1: reference URL root-domain 検出 lint
#
# Day 21 ある回 で発覚した failure mode:
#   `https://www.iwanami.co.jp/` `https://www.japan-acad.go.jp/`
#   `https://www.city.motosu.lg.jp/` の 3 件 root URL が `validate_reference_urls()`
#   の HTTP 200 check を通って silent PASS。実際は Takagi 個別ページではなく
#   visitor が navigate しないと内容に到達できない。`岩波書店 解析概論・代数学講義・
#   初等整数論講義` という記述は publisher 誤り (代数学講義・初等整数論講義は共立出版、
#   verified_facts と矛盾) も併発。
#
# 対策: root URL (path が `/` か空) を WARN として検出。HTTP 200 PASS と
#   別軸の lint。post_build_verify 経由でも参照される (verify check 9)。
# ---------------------------------------------------------------------------


def _is_root_url(url: str) -> bool:
    """Return True if URL points to a domain root (no meaningful path).

    Examples flagged True:
      https://www.iwanami.co.jp/
      https://www.iwanami.co.jp
      http://example.com/

    Examples flagged False (deep URL or meaningful navigation):
      https://www.iwanami.co.jp/book/b265489.html
      https://en.wikipedia.org/wiki/Teiji_Takagi
      https://example.com/foo
      https://example.com/?id=42   (has query → not root)
      https://example.com/#section (has fragment → not root)
    """
    import urllib.parse as _up

    try:
        parsed = _up.urlparse(url)
    except Exception:
        return False
    # Day 21 強化 H1 (再 verify): URL 不完全形 (空文字 / scheme のみ "https://") を
    # root と誤判定しないため netloc を要求。_extract_urls regex 経由なら不要だが
    # 関数を public で使う caller に対する defensive guard。
    if not parsed.netloc:
        return False
    path = (parsed.path or "").strip()
    # Day 21 強化 H1 (refined): query/fragment 含む URL は root とみなさない
    # (path="/" でも ?q=foo や #section は意味のある navigation)
    has_query = bool(parsed.query)
    has_fragment = bool(parsed.fragment)
    if has_query or has_fragment:
        return False
    if path in ("", "/"):
        return True
    return False


def detect_root_urls(text: str) -> list[str]:
    """Find reference URLs that point to domain roots (no deep path).

    Returns list of root URLs (empty if all references are deep).

    NOTE: passes ALL URLs in text including 【音声合成】 / 【映像素材】 tool
    credits. Callers wanting only 【主要参考文献】 scope should use
    `detect_root_urls_in_references(references_list)`.
    """
    return [u for u in _extract_urls(text) if _is_root_url(u)]


def detect_root_urls_in_references(references: list[str]) -> list[str]:
    """Day 21 H1 (refined): scope root URL lint to references list only.

    Avoids false positive on tool homepages (VOICEVOX / Manim Community 等)
    which legitimately link to project home in 【音声合成】/【映像素材】
    credit sections. References are bibliographic and should always be
    deep URLs (specific article/book page).
    """
    out = []
    for ref in references:
        for u in _extract_urls(ref):
            if _is_root_url(u):
                out.append(u)
    return out


def format_timestamp(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS for YouTube chapters."""
    total = int(seconds)
    if total >= 3600:
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h}:{m:02d}:{s:02d}"
    else:
        m = total // 60
        s = total % 60
        return f"{m}:{s:02d}"


def calculate_chapters(
    scene_def: dict,
    timing: dict,
    intro_pause: float = 0.0,
    chapter_subtitles: dict = None,
    chapter_overrides: list[dict] | None = None,
) -> list[dict]:
    """Calculate chapter timestamps from timing.json and section structure.

    Args:
        chapter_subtitles: Optional dict mapping section_type (intro/person/math/closing)
                          to subtitle string. From scene_def["description"]["chapter_subtitles"].
        chapter_overrides: Day 21 強化 M1. Optional list of explicit chapters
                          [{"scene_id": "math_07", "label": "..."}, ...] or
                          [{"timestamp": "9:47", "label": "..."}, ...].
                          When provided, fully replaces auto-section-based chapters.
                          scene_id form is preferred (timing recomputes automatically).
                          timestamp form is verbatim (user owns sync with audio).
                          From scene_def["description"]["chapter_overrides"].

    Returns list of {"timestamp": "M:SS", "label": "..."} dicts.
    YouTube requires: first chapter at 0:00, minimum 3 chapters,
    minimum 10 seconds between chapters.
    """
    if not timing or "scenes" not in timing:
        return []

    sections = scene_def.get("sections", [])
    if len(sections) < 3:
        return []

    if chapter_subtitles is None:
        chapter_subtitles = {}

    scene_timings = timing.get("scenes", {})

    # Build cumulative offset for each scene
    # Scene order follows sections in scene_definition
    all_scene_ids = []
    for section in sections:
        for scene in section.get("scenes", []):
            all_scene_ids.append(scene.get("scene_id", ""))

    scene_start = {}  # scene_id -> start time in seconds (in final video)
    current_time = intro_pause  # account for BGM intro pause

    for scene_id in all_scene_ids:
        scene_start[scene_id] = current_time
        st = scene_timings.get(scene_id, {})
        duration = st.get("duration", 5.0)
        pause_after = st.get("pause_after", 0.5)
        current_time += duration + pause_after

    # ── Day 21 強化 M1: chapter_overrides 優先処理 ──────────
    # 用途: section-1:1 chapter で表現できない sub-section 分割。
    # scene_id form: 該当 scene の start を timing から auto-resolve。
    #   audio 再生成で scene 開始がずれても自動追随。
    # timestamp form: user が手書きで "M:SS" を指定 (legacy / 細かい時刻)。
    if chapter_overrides:
        ch_out = []
        for ent in chapter_overrides:
            if not isinstance(ent, dict):
                continue
            label = ent.get("label", "")
            sid = ent.get("scene_id")
            ts = ent.get("timestamp")
            if sid:
                if sid not in scene_start:
                    print(
                        f"[credits_generator] WARN: chapter_overrides scene_id "
                        f"{sid!r} not in timing; skipping override entry"
                    )
                    continue
                ts_val = format_timestamp(scene_start[sid])
            elif ts:
                ts_val = ts
            else:
                continue
            ch_out.append({"timestamp": ts_val, "label": label})
        # Day 21 強化 M1 (refined): 全 override が無効 / YouTube 最小 3 章未満の
        # 場合 auto-section に fallback。chapter_overrides が壊れて empty で
        # description silent 空 chapter block 出力する degradation を防ぐ。
        if len(ch_out) < 3:
            print(
                f"[credits_generator] WARN: chapter_overrides produced "
                f"{len(ch_out)} chapter(s) (< 3 required by YouTube); "
                f"falling back to auto-section chapters"
            )
            # fall through to auto-section logic below
        else:
            # Day 21 強化 M1 (再 verify): chronological order check
            # YouTube は chapter が time 順でないと reject する。out-of-order
            # 検出時は WARN のみ (auto-sort はしない、user の入力ミスを silent
            # masking しない方針)。
            def _ts_to_sec(ts: str) -> int:
                try:
                    parts = [int(x) for x in ts.split(":")]
                    if len(parts) == 2:
                        return parts[0] * 60 + parts[1]
                    elif len(parts) == 3:
                        return parts[0] * 3600 + parts[1] * 60 + parts[2]
                except (ValueError, AttributeError):
                    return -1
                return -1

            secs = [_ts_to_sec(c["timestamp"]) for c in ch_out]
            for i in range(1, len(secs)):
                if secs[i] <= secs[i - 1]:
                    print(
                        f"[credits_generator] WARN: chapter_overrides out of "
                        f"chronological order at index {i} "
                        f"({ch_out[i - 1]['timestamp']} -> {ch_out[i]['timestamp']}). "
                        f"YouTube requires strictly increasing timestamps."
                    )
                    break
            # Force first chapter to 0:00 per YouTube spec
            if ch_out[0]["timestamp"] != "0:00":
                ch_out[0]["timestamp"] = "0:00"
            return ch_out

    # Build chapters: one per section, using first scene's start time
    chapters = []
    for section in sections:
        scenes = section.get("scenes", [])
        if not scenes:
            continue
        first_scene_id = scenes[0].get("scene_id", "")
        timestamp_sec = scene_start.get(first_scene_id, 0.0)

        # Label priority: chapter_subtitles (from description block)
        #                > section.chapter_title (manual override)
        #                > section.label (cleanup parenthetical notes)
        section_type = section.get("section_type", "")
        label = chapter_subtitles.get(section_type, "")
        if not label:
            label = section.get("chapter_title", "")
        if not label:
            label = section.get("label", "")
            # Strip parenthetical notes like "（フック）"
            for ch in ["（", "("]:
                if ch in label:
                    label = label[: label.index(ch)].strip()

        chapters.append(
            {
                "timestamp": format_timestamp(timestamp_sec),
                "label": label,
            }
        )

    # First chapter must be 0:00
    if chapters and chapters[0]["timestamp"] != "0:00":
        chapters[0]["timestamp"] = "0:00"

    return chapters


def detect_visual_assets(scene_def: dict) -> list[str]:
    """Auto-detect visual asset types from scene definitions.

    Returns list of credit lines for 【映像素材】 section.
    """
    has_ai_images = False
    has_manim = False
    has_route_map = False

    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            vtype = visual.get("type", "")
            template = visual.get("template", "")

            if vtype == "ken_burns":
                has_ai_images = True
            elif vtype == "manim":
                has_manim = True
                if template == "route_map":
                    has_route_map = True
            elif vtype == "route_map":
                has_route_map = True

    credits = []
    if has_ai_images:
        credits.append("AI生成画像：Google Gemini")
    if has_manim:
        credits.append("数式アニメーション：Manim Community（https://www.manim.community/）")
    if has_route_map:
        credits.append("地図データ：Natural Earth（パブリックドメイン）")

    return credits


def generate_description(
    episode_dir: str,
    config: dict,
    scene_def: dict,
    wiki_credits: dict,
    timing: dict,
    intro_pause: float = 0.0,
) -> str:
    lines = []

    # ── タイトル + 紹介文 ─────────────────────────────────
    title = config.get("title_draft", "") or scene_def.get("title", "")
    desc_block = scene_def.get("description", {})

    if title:
        lines.append(title)
        lines.append("")

    # description.intro (LLM-generated) > config.hook (legacy fallback)
    intro_text = desc_block.get("intro", "") or config.get("hook", "")
    if intro_text:
        lines.append(intro_text)
        lines.append("")

    # チャンネル定型文
    lines.append("数学者の人生と業績を追うドキュメンタリーチャンネル「数学史記」。")
    lines.append("")

    # ── チャプター ────────────────────────────────────────
    chapter_subtitles = desc_block.get("chapter_subtitles", {})
    chapter_overrides = desc_block.get("chapter_overrides", []) or None
    chapters = calculate_chapters(
        scene_def, timing, intro_pause, chapter_subtitles, chapter_overrides
    )
    if chapters:
        for ch in chapters:
            lines.append(f"{ch['timestamp']} {ch['label']}")
        lines.append("")

    # ── 音声合成クレジット ────────────────────────────────
    credits = scene_def.get("credits", {})
    voicevox = credits.get("voicevox", "")
    if voicevox:
        lines.append("【音声合成】")
        lines.append(voicevox)
        lines.append("https://voicevox.hiroshiba.jp/")
        lines.append("")

    # ── BGMクレジット ─────────────────────────────────────
    bgm_config = config.get("bgm", {})
    bgm_credit = bgm_config.get("credit", "")
    if not bgm_credit:
        # credit フィールドがない場合、title/artist/source から組み立て
        bgm_title = bgm_config.get("title", "")
        bgm_artist = bgm_config.get("artist", "")
        bgm_source = bgm_config.get("source", "")
        if bgm_title and bgm_artist:
            bgm_credit = f"{bgm_title} - {bgm_artist}"
            if bgm_source:
                bgm_credit += f"（{bgm_source}）"
    if bgm_credit:
        lines.append("【BGM】")
        lines.append(bgm_credit)
        lines.append("")

    # ── 映像素材クレジット ────────────────────────────────
    visual_credits = detect_visual_assets(scene_def)
    if visual_credits:
        lines.append("【映像素材】")
        for vc in visual_credits:
            lines.append(vc)
        lines.append("")

    # ── 画像クレジット（Wikimedia）────────────────────────
    # Day 17 fix : only credit photos that were ACTUALLY ASSIGNED to
    # a scene. wikimedia_fetcher writes photos with scene_id=null when they
    # were downloaded but not assigned during assign_photos_to_scenes(), and
    # downstream image_generator never uses such photos as references.
    # Previously credits_generator output ALL entries unconditionally, which
    # produced misleading credits in ある回 (no scene assigned, but the 3
    # name-collision photos like 柳惠千 still credited).
    #
    # Day 21 強化 H3 : scene_id=null AND usage=="reference" のケース
    # を credit 対象に追加。近代人物 (高木・ヴァイエルシュトラス等) は
    # use_reference: true で wiki photo を Gemini reference として使うが
    # scene_id 直接割当はしない (= scene_id null + usage reference)。
    # 従来は credit silent skip → description【画像クレジット】section 欠落
    #。reference 用途 PD photo も
    # derivative use の attribution として credit に含める。
    #
    # Filter rules (a photo is INCLUDED if it has any usage credit):
    #   - photo.scene_id is set   → credited as scene-direct
    #   - photo.usage == "reference"   → credited as Gemini reference
    #   - everything else (scene_id null AND usage unused/skipped/missing) → skipped
    photos = wiki_credits.get("photos", [])
    kept_photos = []
    skipped = 0
    for photo in photos:
        usage = (photo.get("usage") or "").lower()
        scene_id = photo.get("scene_id")
        scene_assigned = scene_id not in (None, "", "null")
        is_reference = usage == "reference"
        if usage in ("unused", "skipped"):
            skipped += 1
            continue
        if not (scene_assigned or is_reference):
            skipped += 1
            continue
        kept_photos.append(photo)
    if skipped:
        print(
            f"[credits_generator] Skipped {skipped} wikimedia photo(s) "
            f"(scene_id null AND usage neither scene-direct nor reference)"
        )
    if kept_photos:
        lines.append("【画像クレジット】")
        # Day 21 強化 H3: split scene-direct vs reference photos for
        # transparency. reference photos are not displayed verbatim; they
        # served as Gemini reference for AI-generated portraits.
        direct_photos = [
            p for p in kept_photos if p.get("scene_id") not in (None, "", "null")
        ]
        ref_photos = [
            p for p in kept_photos
            if p.get("scene_id") in (None, "", "null")
            and (p.get("usage") or "").lower() == "reference"
        ]
        if ref_photos:
            lines.append(
                "本編およびサムネイルの肖像は、以下のパブリックドメイン写真を参照として"
                "AI（Google Gemini）で油絵風に生成しました。"
            )
            for photo in ref_photos:
                credit = photo.get("credit_text", "")
                if credit:
                    lines.append(f"- {credit}")
            if direct_photos:
                lines.append("")
                lines.append("以下の写真は本編で直接使用しました。")
        for photo in direct_photos:
            credit = photo.get("credit_text", "")
            url = photo.get("commons_url", "")
            license_url = photo.get("license_url", "")
            if credit:
                lines.append(credit)
            if license_url and license_url not in (credit or ""):
                lines.append(f"{license_url} via Wikimedia Commons")
            if url:
                lines.append(url)
        lines.append("")

    # ── 参考文献 ──────────────────────────────────────────
    # Priority: episode_config.references (human-curated, full bibliographic
    # detail) > scene_def.credits.references (LLM-simplified fallback).
    # Rationale: LLM often drops journal names, page ranges, publisher etc.
    references = config.get("references", [])
    if not references:
        references = credits.get("references", [])
    if references:
        lines.append("【主要参考文献】")
        for ref in references:
            lines.append(f"{ref}")
        lines.append("")

    # ── ハッシュタグ ──────────────────────────────────────
    # description.tags (LLM-generated) > config.tags (legacy fallback)
    episode_tags = desc_block.get("tags", []) or config.get("tags", [])
    # base_tags と重複する episode_tags を除外（"数学史" 等の二重ハッシュ防止、過去のケースで発覚）
    base_tag_set = {"数学", "数学史", "数学者", "ドキュメンタリー", "教育"}
    unique_episode_tags = [t for t in episode_tags if t not in base_tag_set]
    episode_tag_str = " ".join(f"#{t}" for t in unique_episode_tags) if unique_episode_tags else ""

    base_tags = "#数学 #数学史 #数学者 #ドキュメンタリー #教育"
    if episode_tag_str:
        lines.append(f"{base_tags} {episode_tag_str}")
    else:
        lines.append(base_tags)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate YouTube description text (description.txt)"
    )
    parser.add_argument("config_json", help="Path to episode_config.json")
    parser.add_argument(
        "--output", default=None, help="Output path (default: {episode_dir}/description.txt)"
    )
    parser.add_argument(
        "--intro-pause",
        type=float,
        default=None,
        help="Intro pause duration in seconds (for chapter offset). "
        "Defaults to bgm.intro_pause from config, or 0.0",
    )
    parser.add_argument(
        "--skip-url-check",
        action="store_true",
        help="Skip URL validation step (offline build, etc.)",
    )
    args = parser.parse_args()

    config_path = os.path.abspath(args.config_json)
    episode_dir = os.path.dirname(config_path)

    config = load_json(config_path)
    scene_def = load_json(os.path.join(episode_dir, "scene_definition.json"))
    wiki_credits = load_json(os.path.join(episode_dir, "wikimedia_credits.json"))
    timing = load_json(os.path.join(episode_dir, "timing.json"))

    # Determine intro_pause: CLI > config > default
    if args.intro_pause is not None:
        intro_pause = args.intro_pause
    else:
        intro_pause = config.get("bgm", {}).get("intro_pause", 0.0)

    output_path = args.output or os.path.join(episode_dir, "description.txt")

    text = generate_description(episode_dir, config, scene_def, wiki_credits, timing, intro_pause)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n[OK] description.txt generated: {output_path}")
    print(f"{'=' * 60}")
    # Print text safely (avoid cp932 encoding errors on Windows)
    try:
        print(text)
    except UnicodeEncodeError:
        import sys

        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    print(f"{'=' * 60}\n")

    # Summary
    desc_block = scene_def.get("description", {})
    chapter_subtitles = desc_block.get("chapter_subtitles", {})
    chapter_overrides = desc_block.get("chapter_overrides", []) or None
    chapters = calculate_chapters(
        scene_def, timing, intro_pause, chapter_subtitles, chapter_overrides
    )
    if chapters:
        print(f"  Chapters: {len(chapters)}")
    else:
        print("  Chapters: none (timing.json not found or < 3 sections)")
    print(f"  Intro pause: {intro_pause}s")

    # URL validation (warning only, never fails the pipeline)
    if not args.skip_url_check:
        urls = _extract_urls(text)
        if urls:
            print(f"  URL check: validating {len(urls)} URL(s)...", end=" ", flush=True)
            broken = validate_reference_urls(text)
            if broken:
                print(f"[WARN] {len(broken)} broken")
                for url, err in broken:
                    print(f"    {err}: {url}")
                print("    → 修正してから commit / 公開してください")
            else:
                print("[OK] all reachable")

            # Day 21 強化 H1: root URL lint (HTTP 200 通っても内容不一致を防ぐ)
            # Scope: 【主要参考文献】 のみ (tool homepage は credit 用途で許容)
            references_for_lint = config.get("references", []) or scene_def.get(
                "credits", {}
            ).get("references", []) or []
            root_urls = detect_root_urls_in_references(references_for_lint)
            if root_urls:
                print(
                    f"  Root URL check: [WARN] {len(root_urls)} bibliographic "
                    f"reference(s) point to domain root (no deep path)"
                )
                for url in root_urls:
                    print(f"    {url}")
                print(
                    "    → 個別ページの URL に置換してください "
                    ""
                )
            else:
                print("  Root URL check: [OK] all bibliographic references are deep URLs")


if __name__ == "__main__":
    main()
