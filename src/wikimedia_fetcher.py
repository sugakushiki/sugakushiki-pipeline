"""
wikimedia_fetcher.py - Fetch real photos from Wikimedia Commons

Searches Wikimedia Commons for CC-licensed photos of the episode's subject,
downloads up to 3 best candidates, and auto-assigns them to person/intro
ken_burns scenes in scene_definition.json.

Usage:
    python src/wikimedia_fetcher.py episodes/001_erdos/episode_config.json
    python src/wikimedia_fetcher.py episodes/001_erdos/episode_config.json --dry-run
    python src/wikimedia_fetcher.py episodes/001_erdos/episode_config.json --max-photos 5

Pipeline integration:
    Runs automatically between 'script' and 'images' steps when --qa or --qa-quick is used.
    Can also be run standalone to preview candidates before committing.

Output:
    - episodes/xxx/images/wiki_*.jpg  (downloaded photos)
    - episodes/xxx/wikimedia_credits.json  (attribution info for video credits)
    - scene_definition.json updated with source fields for assigned scenes

License filter:
    Only CC BY and CC BY-SA licenses are accepted (commercial use permitted).
    CC BY-NC, fair use, and unknown licenses are rejected.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
ACCEPTED_LICENSES = {
    "cc-by-1.0",
    "cc-by-2.0",
    "cc-by-2.5",
    "cc-by-3.0",
    "cc-by-4.0",
    "cc-by-sa-1.0",
    "cc-by-sa-2.0",
    "cc-by-sa-2.5",
    "cc-by-sa-3.0",
    "cc-by-sa-4.0",
    "cc0",
    "pd",
    "public domain",
    "public-domain",
}


def _is_license_accepted(raw_license: str) -> bool:
    """Check if a license string from Wikimedia API is acceptable.

    Handles format variations: Wikimedia returns "cc by 3.0" (spaces),
    "public domain", "Public Domain", "pd", etc.
    We normalize both the input and the accepted set to match reliably.
    """
    lic = raw_license.lower().strip()
    if not lic:
        return False
    # Check both original and hyphenated forms
    lic_hyphenated = lic.replace(" ", "-")
    return any(a in lic for a in ACCEPTED_LICENSES) or any(
        a in lic_hyphenated for a in ACCEPTED_LICENSES
    )


USER_AGENT = "sugakushiki-pipeline/1.0 (educational documentary; contact via GitHub)"

# 人物写真と判断するキーワード（ファイル名・説明に含まれる）
PORTRAIT_KEYWORDS = [
    "portrait",
    "photo",
    "photograph",
    "seminar",
    "lecture",
    "conference",
    "mathematician",
    "professor",
]
# 除外するキーワード（関係ない画像を弾く）
EXCLUDE_KEYWORDS = [
    "grave",
    "tomb",
    "cemetery",
    "street",
    "building",
    "theorem",
    "graph",
    "diagram",
    "formula",
    "equation",
    "prize",
    "award",
    "medal",
    "stamp",
    "coin",
    "plaque",
    "bust",
    "statue",
    "inequality",
    "signature",
    "autograph",
    "conjecture",
    "proof",
    "lemma",
    "constant",  # 数学用語（人物写真ではない）
    "wife",
    "spouse",
    "family",  # 家族写真（本人ではない）
    "birth place",
    "birthplace",
    "courtyard",  # 建物・場所
    "house",
    "museum",
    "school",  # 建物
    # 同名施設・天体（過去のケース で「Leonhard Euler Telescope」混入の再発防止）
    "telescope",
    "observatory",
    "dome",  # 天文施設
    "satellite",
    "asteroid",
    "crater",
    "comet",  # 同名天体
    # 対応セッションで追加（未対応分）
    "ship",
    "vessel",  # 船舶（数学者名を冠した船）
    "park",
    "garden",  # 公園・庭園
    "monument",
    "memorial",  # 記念碑
    "mountain",
    "peak",
    "hill",  # 山岳地形
]
# 写真として受け入れるファイル拡張子（SVG, PDF, OGG等を除外）
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif"}
# 複数人写真を示すキーワード（リファレンス用途から除外するためのフラグ）
GROUP_PHOTO_KEYWORDS = [
    "couple",
    "with",
    "group",
    "conference",
    "meeting",
    "class",
    "together",
    "team",
    "colleagues",
    "students",
]
# 対象セクション（実写で置き換えるシーン）
TARGET_SECTIONS = {"intro", "person"}


def is_solo_portrait(title: str, description: str) -> bool:
    """Heuristic: is this likely a solo portrait (single person)?

    Returns False if group photo keywords are found in title or description.
    Used to filter reference photos for age-transformation generation —
    group photos can't be used as identity anchors because the model
    can't determine which person is the subject.
    """
    combined = (title + " " + description).lower()
    for kw in GROUP_PHOTO_KEYWORDS:
        if kw in combined:
            return False
    return True


# ---------------------------------------------------------------------------
# Wikimedia Commons API helpers
# ---------------------------------------------------------------------------
def _api_get(params: dict) -> dict:
    """Call Wikimedia Commons API and return JSON response."""
    params["format"] = "json"
    params["formatversion"] = "2"
    url = WIKIMEDIA_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_commons(query: str, limit: int = 20) -> list[dict]:
    """Search Wikimedia Commons for image files matching query.

    Returns list of {title, pageid} dicts.
    """
    data = _api_get(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",  # File: namespace
            "srlimit": limit,
            "srprop": "title",
        }
    )
    results = data.get("query", {}).get("search", [])
    return [{"title": r["title"], "pageid": r["pageid"]} for r in results]


def search_category(category_name: str, limit: int = 50) -> list[dict]:
    """List files in a Wikimedia Commons category.

    This is the most reliable way to find photos of a specific person,
    as Wikimedia organizes photos into categories like 'Category:Paul Erdős'.

    Returns list of {title, pageid} dicts.
    """
    data = _api_get(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category_name}",
            "cmtype": "file",
            "cmlimit": limit,
        }
    )
    results = data.get("query", {}).get("categorymembers", [])
    return [{"title": r["title"], "pageid": r.get("pageid", 0)} for r in results]


def get_file_info(titles: list[str]) -> dict:
    """Get image URL and metadata for a list of File: titles.

    Returns dict keyed by title with {url, license, author, description, width, height}.
    """
    # API allows up to 50 titles per request
    chunks = [titles[i : i + 50] for i in range(0, len(titles), 50)]
    result = {}

    for chunk in chunks:
        data = _api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": "1920",  # リクエストする表示幅
            }
        )
        pages = data.get("query", {}).get("pages", [])
        if isinstance(pages, dict):
            pages = list(pages.values())

        for page in pages:
            title = page.get("title", "")
            imageinfo = page.get("imageinfo", [{}])
            if not imageinfo:
                continue
            info = imageinfo[0]
            meta = info.get("extmetadata", {})

            # ライセンス抽出
            license_short = (
                (
                    meta.get("LicenseShortName", {}).get("value", "")
                    or meta.get("License", {}).get("value", "")
                )
                .lower()
                .strip()
            )

            # 作者抽出（HTMLタグを除去）
            author_raw = meta.get("Artist", {}).get("value", "") or meta.get("Credit", {}).get(
                "value", ""
            )
            author = re.sub(r"<[^>]+>", "", author_raw).strip()
            # Normalize whitespace (collapse runs/newlines to single space)
            author = re.sub(r"\s+", " ", author).strip()
            # De-duplicate Wikimedia's common "Unknown author" x2 pattern
            # (outer <bdi> + inner <span> concat: "Unknown authorUnknown author")
            author = re.sub(
                r"(Unknown author)(\s*Unknown author)+", r"\1", author, flags=re.IGNORECASE
            )

            description = meta.get("ImageDescription", {}).get("value", "")
            description = re.sub(r"<[^>]+>", "", description).strip()

            result[title] = {
                "url": info.get("url", ""),
                "thumb_url": info.get("thumburl", info.get("url", "")),
                "license": license_short,
                "author": author,
                "description": description,
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "commons_page": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            }

    return result


# ---------------------------------------------------------------------------
# Candidate scoring and selection
# ---------------------------------------------------------------------------
def _parse_subject_names(subject_en: str) -> dict:
    """Parse subject name into components for matching.

    Returns dict with keys: full, first, last, last_ascii, first_lower, last_lower.
    """
    parts = subject_en.strip().split()
    if not parts:
        return {"full": "", "first": "", "last": "", "first_lower": "", "last_lower": ""}
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    # ASCII-folded version for matching (Erdős → Erdos)
    import unicodedata

    def _ascii_fold(s):
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

    return {
        "full": subject_en,
        "first": first,
        "last": last,
        "first_lower": first.lower(),
        "last_lower": last.lower(),
        "first_ascii": _ascii_fold(first).lower(),
        "last_ascii": _ascii_fold(last).lower(),
        "full_lower": subject_en.lower(),
    }


def score_candidate(
    title: str, info: dict, subject_names: dict = None, from_category: bool = False
) -> float:
    """Score a candidate image. Higher is better. Returns -1 to reject.

    Args:
        subject_names: parsed subject name from _parse_subject_names().
            Used to boost matching and reject wrong-person results.
        from_category: True if this file was found in the subject's Wikimedia
            category. Category membership implies relevance, so name-match
            gate is relaxed (but other filters still apply).
    """
    license_str = info.get("license", "").lower()

    # ライセンスフィルター（必須）
    if not _is_license_accepted(license_str):
        return -1.0

    # URLがない場合は除外
    if not info.get("url"):
        return -1.0

    # ファイル拡張子フィルター（写真のみ。SVG, PDF, OGG等を除外）
    title_ext = os.path.splitext(title.lower())[-1]
    if title_ext and title_ext not in PHOTO_EXTENSIONS:
        return -1.0

    score = 0.0
    title_lower = title.lower()
    desc_lower = info.get("description", "").lower()
    combined = title_lower + " " + desc_lower

    # 除外キーワードチェック
    for kw in EXCLUDE_KEYWORDS:
        if kw in title_lower or kw in desc_lower:
            return -1.0

    # ── Subject name matching（最重要）─────────────────────
    name_matched = False  # 人名マッチが成立したか
    if subject_names and subject_names["last_lower"]:
        last = subject_names["last_lower"]
        last_ascii = subject_names["last_ascii"]
        first = subject_names["first_lower"]
        first_ascii = subject_names["first_ascii"]

        # 姓がタイトル/説明に含まれるか（単語境界を考慮）
        # "erdő" が "erdős" にマッチしないよう、単語全体で比較
        def _word_match(needle: str, haystack: str) -> bool:
            """Check if needle appears as a whole word or hyphenated component."""
            pattern = rf"(?<![a-zà-ÿ]){re.escape(needle)}(?![a-zà-ÿ])"
            return bool(re.search(pattern, haystack, re.IGNORECASE))

        has_last = _word_match(last, combined) or _word_match(last_ascii, combined)
        has_first = _word_match(first, combined) or _word_match(first_ascii, combined)

        if has_last and has_first:
            # フルネームマッチ → 大幅ボーナス
            score += 5.0
            name_matched = True
        elif has_last and not has_first:
            # 姓のみ一致 → 「姓 別名」パターン（別人の写真）かチェック
            # 例: "Erdős Renée" → Erdős + Renée (≠Paul) → 別人
            # 例: "Ronald_graham_couple_with_erdos" → erdosは含むが別人パターンではない
            title_clean = re.sub(r"^File:", "", title, flags=re.IGNORECASE)

            # 姓の直後に別の大文字始まりの語がある（名前パターン）
            # ダッシュ（–, -）も区切りとして扱う
            # 注意: IGNORECASEを使わない。大文字始まりの語のみ人名候補とする。
            # これにより "Erdos budapest" (小文字b) は人名パターンと見なさず、
            # "Erdős Renée" (大文字R) は別人として正しく検出する。
            last_pattern = re.escape(last) + r"|" + re.escape(last_ascii)
            match_after = re.search(
                rf"(?i:(?:{last_pattern}))[\s\-–]+([A-ZÀ-Ÿ][a-zà-ÿ]+)", title_clean
            )
            match_before = re.search(
                rf"([A-ZÀ-Ÿ][a-zà-ÿ]+)[\s\-–]+(?i:(?:{last_pattern}))", title_clean
            )

            is_different_person = False
            for m in [match_after, match_before]:
                if m:
                    adjacent_name = m.group(1).lower()
                    if adjacent_name not in (
                        first,
                        first_ascii,
                        "file",
                        "with",
                        "and",
                        "the",
                        "von",
                        "de",
                        "van",
                    ):
                        is_different_person = True
                        break

            if is_different_person:
                return -1.0  # 明確に別人
            else:
                score += 2.0  # 姓のみだが別人パターンではない
                name_matched = True
        # 姓もない → ボーナスなし、name_matched=False のまま

    # ── 人名マッチ必須ゲート ──────────────────────────────
    # subject_namesが指定されているのに名前が一致しない写真は除外
    # （関係ない写真が解像度やアスペクト比だけで選ばれるのを防ぐ）
    # ただしカテゴリ経由の写真はカテゴリ所属自体が関連性の証拠なので免除
    if subject_names and subject_names["last_lower"] and not name_matched:
        if from_category:
            score += 1.0  # カテゴリ所属ボーナス（名前マッチより低い）
        else:
            return -1.0

    # 人物写真キーワードボーナス
    for kw in PORTRAIT_KEYWORDS:
        if kw in title_lower or kw in desc_lower:
            score += 1.0

    # アスペクト比（YouTube 16:9向け: 横長〜正方形が好ましい）
    w = info.get("width", 0)
    h = info.get("height", 0)
    if w > 0 and h > 0:
        ratio = h / w  # <1 = 横長, 1 = 正方形, >1 = 縦長
        if 0.5 <= ratio <= 0.75:  # 横長（16:9〜4:3相当）→ Ken Burnsに最適
            score += 2.0
        elif 0.75 < ratio <= 1.1:  # ほぼ正方形〜やや縦長
            score += 1.5
        elif 1.1 < ratio <= 1.5:  # 縦長ポートレート（クロップロスあるが許容）
            score += 0.5
        elif ratio > 1.5:  # 極端な縦長（大きなクロップロス）
            score -= 1.0

    # 解像度ボーナス（最低300px以上）
    if min(w, h) >= 800:
        score += 1.0
    elif min(w, h) >= 400:
        score += 0.5
    elif min(w, h) < 200:
        score -= 1.0

    return score


def select_best_photos(
    candidates: dict, max_photos: int = 3, subject_en: str = "", category_titles: set = None
) -> list[dict]:
    """Score and rank candidates, return top N."""
    subject_names = _parse_subject_names(subject_en) if subject_en else None
    scored = []
    for title, info in candidates.items():
        from_category = category_titles and title in category_titles
        s = score_candidate(title, info, subject_names, from_category=from_category)
        if s >= 0:
            scored.append((s, title, info))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "title": title,
            "score": s,
            "solo_portrait": is_solo_portrait(title, info.get("description", "")),
            **info,
        }
        for s, title, info in scored[:max_photos]
    ]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def download_photo(url: str, output_path: str) -> bool:
    """Download a photo from URL to output_path."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(output_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"      Download error: {e}")
        return False


# ---------------------------------------------------------------------------
# Scene assignment (era-aware matching)
# ---------------------------------------------------------------------------
def _extract_photo_year(title: str, description: str) -> int | None:
    """Extract the most likely year from photo title/description.

    Prefers year found in title; falls back to description.
    Only considers years in 1800-2030 range (relevant for mathematician photos).
    """
    for text in [title, description]:
        # \b fails with underscores (word char), so use lookaround for non-digits
        matches = re.findall(r"(?<!\d)(1[89]\d{2}|20[0-3]\d)(?!\d)", text)
        if matches:
            # If multiple years, prefer the later one (more likely to be photo date)
            return max(int(y) for y in matches)
    return None


def _extract_scene_year(narration_list: list[str], birth_year: int | None) -> int | None:
    """Extract the primary year/era from scene narration text.

    Strategies (in priority order):
    1. Explicit year: "1934年" → 1934
    2. Age mention: "19歳" + birth_year → birth_year + 19
    3. Era keywords: "晩年" → birth_year + 75, "幼少期" → birth_year + 5, etc.
    """
    text = " ".join(narration_list)

    # Strategy 1: Explicit year (YYYY年 pattern)
    year_matches = re.findall(r"(1[89]\d{2}|20[0-3]\d)年", text)
    if year_matches:
        # Return the first mentioned year (usually the primary temporal context)
        return int(year_matches[0])

    # Strategy 2: Age mention (N歳)
    if birth_year:
        age_matches = re.findall(r"(\d{1,3})歳", text)
        if age_matches:
            age = int(age_matches[0])
            if 0 < age < 120:
                return birth_year + age

    # Strategy 3: Era keywords
    if birth_year:
        _ERA_OFFSETS = {
            "幼少": 5,
            "幼い": 5,
            "子供": 8,
            "少年": 10,
            "青年": 20,
            "若い": 22,
            "学生": 20,
            "大学": 20,
            "中年": 45,
            "壮年": 50,
            "晩年": 75,
            "老年": 75,
            "最晩年": 80,
            "死去": 80,
            "亡くな": 80,
            "逝去": 80,
        }
        for keyword, offset in _ERA_OFFSETS.items():
            if keyword in text:
                return birth_year + offset

    return None


def _extract_birth_year(config: dict) -> int | None:
    """Extract birth year from episode_config.json.

    Checks: birth_year field → verified_facts.birth → key_episodes[0].
    """
    # Direct field
    if config.get("birth_year"):
        return int(config["birth_year"])

    # From verified_facts
    from config_validator import get_verified_fact_text

    vf = config.get("verified_facts", {})
    birth_str = get_verified_fact_text(vf.get("birth", ""))
    if birth_str:
        m = re.search(r"(1[89]\d{2}|20[0-3]\d)", birth_str)
        if m:
            return int(m.group(1))

    # From key_episodes (first entry often mentions birth)
    episodes = config.get("key_episodes", [])
    if episodes:
        m = re.search(r"(1[89]\d{2})年.*生まれ", episodes[0])
        if m:
            return int(m.group(1))

    return None


def find_target_scenes(scene_def: dict) -> list[dict]:
    """Find ken_burns scenes in intro/person sections without a real photo assigned.

    Returns list of scene dicts with section_id injected.
    """
    targets = []
    for section in scene_def.get("sections", []):
        section_id = section.get("section_id", "")
        if section_id not in TARGET_SECTIONS:
            continue
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "ken_burns":
                continue
            # すでにwiki_写真が割り当て済みならスキップ
            existing_source = visual.get("source", "")
            if existing_source.startswith("wiki_"):
                continue
            targets.append({**scene, "_section_id": section_id})
    return targets


def assign_photos_to_scenes(
    scene_def: dict, photos: list[dict], images_dir: str, birth_year: int | None = None
) -> tuple[dict, list[dict]]:
    """Assign downloaded photos to target scenes using era-aware matching.

    When birth_year is available, matches photos to scenes by temporal
    proximity (e.g. a 1992 photo goes to a scene about the subject at age 79,
    not a scene about their youth at age 19).

    Falls back to sequential assignment when year info is unavailable.

    Modifies scene_def in-place. Returns (updated_scene_def, assignment_log).
    """
    targets = find_target_scenes(scene_def)
    if not targets or not photos:
        return scene_def, []

    # ── 年代情報の抽出 ──────────────────────────────────────
    photo_years = []
    for photo in photos:
        py = _extract_photo_year(photo.get("title", ""), photo.get("description", ""))
        photo_years.append(py)

    scene_years = []
    for target in targets:
        sy = _extract_scene_year(target.get("narration", []), birth_year)
        scene_years.append(sy)

    # デバッグ出力
    has_year_info = any(py is not None for py in photo_years) and any(
        sy is not None for sy in scene_years
    )
    if has_year_info:
        print(f"    [DATE] Era-aware matching (birth_year={birth_year}):")
        for i, photo in enumerate(photos):
            yr = photo_years[i]
            age_str = f" (age ~{yr - birth_year})" if yr and birth_year else ""
            print(f"       Photo {i + 1}: {yr or '?'}{age_str}  ← {photo.get('title', '')[:50]}")
        for i, target in enumerate(targets):
            yr = scene_years[i]
            age_str = f" (age ~{yr - birth_year})" if yr and birth_year else ""
            print(f"       Scene {target['scene_id']}: {yr or '?'}{age_str}")

    # ── マッチング ────────────────────────────────────────────
    if has_year_info:
        assignments = _match_by_era(photos, photo_years, targets, scene_years, birth_year)
    else:
        # 年代情報なし → 従来の順番マッチング
        print("    [INFO] No era info available, using sequential assignment")
        assignments = []
        for i in range(min(len(photos), len(targets))):
            assignments.append((i, i))  # (photo_idx, scene_idx)

    # ── scene_definition.json の更新 ──────────────────────────
    result_log = []
    assigned_photo_indices = {pi for pi, si in assignments}
    for photo_idx, scene_idx in assignments:
        photo = photos[photo_idx]
        target_scene = targets[scene_idx]
        scene_id = target_scene["scene_id"]
        filename = photo["local_filename"]

        # scene_definition.json を更新
        for section in scene_def["sections"]:
            for scene in section["scenes"]:
                if scene["scene_id"] == scene_id:
                    scene["visual"]["source"] = filename
                    # source_promptは残す（AI生成フォールバック用）
                    break

        # マッチング理由の表示
        py = photo_years[photo_idx]
        sy = scene_years[scene_idx]
        if py and sy and birth_year:
            print(
                f"    [OK] {scene_id} <- {filename}  "
                f"(photo ~{py - birth_year}歳, scene ~{sy - birth_year}歳, "
                f"diff={abs(py - sy)}yr)"
            )
        else:
            print(f"    [OK] {scene_id} <- {filename} ({photo['license']})")

        result_log.append(
            {
                "scene_id": scene_id,
                "section": target_scene["_section_id"],
                "filename": filename,
                "wikimedia_title": photo["title"],
                "license": photo["license"],
                "author": photo["author"],
                "commons_url": photo["commons_page"],
                "solo_portrait": photo.get("solo_portrait", False),
            }
        )

    # 割り当てられなかった写真を表示（リファレンス用として保持）
    for i, photo in enumerate(photos):
        if i not in assigned_photo_indices:
            py = photo_years[i]
            age_str = f" (age ~{py - birth_year})" if py and birth_year else ""
            print(
                f"    [PHOTO] {photo['local_filename']}{age_str} -> 年齢差が大きいため直接割当なし（リファレンス用に保持）"
            )

    return scene_def, result_log


def _match_by_era(
    photos: list,
    photo_years: list,
    targets: list,
    scene_years: list,
    birth_year: int | None,
    max_age_diff: int = 20,
) -> list[tuple[int, int]]:
    """Greedy era-based matching: assign each photo to its best temporal match.

    Only assigns photos where the age difference is within max_age_diff years.
    Photos that don't match any scene within the threshold remain unassigned
    (available as reference images for AI generation, but not shown directly).

    Returns list of (photo_idx, scene_idx) pairs.
    """
    # 全ペアの年代距離を計算
    pairs = []
    for pi, py in enumerate(photo_years):
        for si, sy in enumerate(scene_years):
            if py is not None and sy is not None:
                dist = abs(py - sy)
            elif py is not None or sy is not None:
                dist = 1000  # 片方のみ年代あり → 低優先
            else:
                dist = 2000  # 両方なし → 最低優先
            pairs.append((dist, pi, si))

    pairs.sort(key=lambda x: x[0])

    # 貪欲法: 距離が近い順に割り当て（各写真・各シーンは1回のみ使用）
    used_photos = set()
    used_scenes = set()
    assignments = []

    for dist, pi, si in pairs:
        if pi in used_photos or si in used_scenes:
            continue
        # 年齢差が閾値を超える場合はスキップ（写真をシーンに直接割り当てない）
        if dist > max_age_diff:
            continue
        assignments.append((pi, si))
        used_photos.add(pi)
        used_scenes.add(si)
        # 全写真が割り当てられたら終了
        if len(used_photos) == len(photos):
            break

    # photo indexの順でソート（出力の安定性）
    assignments.sort(key=lambda x: x[0])
    return assignments


# ---------------------------------------------------------------------------
# Main fetch logic
# ---------------------------------------------------------------------------
def fetch_and_assign(
    episode_config_path: str,
    scene_json_path: str,
    max_photos: int = 3,
    dry_run: bool = False,
    appearance_backend: str = "sonnet",
) -> dict:
    """Main entry point: search, download, assign.

    Returns summary dict with counts and attribution info.
    """
    episode_dir = os.path.dirname(os.path.abspath(episode_config_path))
    images_dir = os.path.join(episode_dir, "images")
    credits_path = os.path.join(episode_dir, "wikimedia_credits.json")

    # Load episode config
    with open(episode_config_path, encoding="utf-8") as f:
        config = json.load(f)

    # Load scene definition
    with open(scene_json_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    # 検索クエリを構築（英語の人物名 + photographer/mathematician）
    subject_en = config.get("subject_en") or config.get("subject", "")
    if not subject_en:
        print("ERROR: episode_config.json に subject_en が必要です")
        sys.exit(1)

    # Day 17 fix : skip fetch when references will not be used.
    # Two ways to opt out:
    #   (A) Episode-level (preferred for subjects with no contemporary
    #       photo, e.g. 3rd-century 劉徽 / 7th-century Brahmagupta):
    #       episode_config["image_style"]["use_reference"] = false
    #   (B) Scene-level (all scenes EXPLICITLY set use_reference: false in
    #       their visual block) AND no wikimedia_photo_urls were pinned.
    # Why both: per-scene use_reference defaults to True in image_generator,
    # so an episode with "no portrait should be referenced" intent expressed
    # only in episode_config.portrait_reference TEXT would not trigger (B).
    # (A) gives the user a direct config-level switch.
    # Why this matters: previously the fetcher always ran for every episode,
    # downloading name-collision photos that never got assigned but ended up in description credits.
    pinned_urls = config.get("wikimedia_photo_urls", [])
    pinned_count = len(pinned_urls) if isinstance(pinned_urls, list) else 0
    ep_use_ref = config.get("image_style", {}).get("use_reference")
    skip_reason: str | None = None
    if pinned_count == 0 and ep_use_ref is False:
        skip_reason = "episode_config.image_style.use_reference=false"
    elif pinned_count == 0:
        uses_ref_true = 0
        uses_ref_false_explicit = 0
        for sect in scene_def.get("sections", []):
            for sc in sect.get("scenes", []):
                v = sc.get("visual", {}) or {}
                if "use_reference" not in v:
                    # unset == default True
                    uses_ref_true += 1
                elif v.get("use_reference") is True:
                    uses_ref_true += 1
                else:
                    uses_ref_false_explicit += 1
        if uses_ref_true == 0 and uses_ref_false_explicit > 0:
            skip_reason = (
                f"every scene explicitly sets use_reference=false "
                f"({uses_ref_false_explicit} scenes)"
            )
    if skip_reason:
        print(f"[wikimedia_fetcher] Skipping fetch: {skip_reason}. Writing empty credits.")
        empty_credits = {
            "episode_id": config.get("episode_id", "unknown"),
            "subject": subject_en,
            "fetched_at": None,
            "photos": [],
            "note": f"Search/download skipped: {skip_reason}.",
        }
        with open(credits_path, "w", encoding="utf-8") as f:
            json.dump(empty_credits, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "reason": skip_reason}

    search_query = f"{subject_en} mathematician"
    episode_id = config.get("episode_id", "unknown")
    birth_year = _extract_birth_year(config)

    print(f"\n{'=' * 60}")
    print("  Wikimedia Commons Photo Fetch")
    print(f"{'=' * 60}")
    print(f"  Subject:  {subject_en}")
    if birth_year:
        print(f"  Born:     {birth_year}")
    print(f"  Query:    {search_query}")
    print(f"  Max:      {max_photos} photos")
    if dry_run:
        print("  Mode:     DRY RUN (no download, no file changes)")
    print()

    # ── Fallback URL: episode_configで指定された写真を優先使用 ──
    # wikimedia_photo_urlsが指定されていれば検索をスキップし直接ダウンロード。
    # episode_config作成時にWikimedia Commonsで確認したURLを書いておくことで、
    # 自動検索のスコアリングに依存せず確実に正しい写真を使える。
    fallback_urls = config.get("wikimedia_photo_urls", [])
    if isinstance(fallback_urls, dict):
        print(
            f"ERROR: wikimedia_photo_urls must be a flat list of URL strings, "
            f"got dict with keys {list(fallback_urls.keys())}. "
            f"See episodes/010_gauss/episode_config.json for the correct format."
        )
        sys.exit(1)
    if fallback_urls:
        print(f"  Using {len(fallback_urls)} specified photo URL(s) (skipping search)")
        # URLからWikimediaタイトルを抽出してメタデータ取得
        fallback_titles = []
        for url in fallback_urls:
            # https://commons.wikimedia.org/wiki/File:Xxx.jpg → File:Xxx.jpg
            # https://upload.wikimedia.org/.../Xxx.jpg → Xxx.jpg を File:Xxx.jpg に
            if "File:" in url:
                title = "File:" + url.split("File:")[-1].split("?")[0]
                title = urllib.parse.unquote(title.replace("_", " "))
            else:
                # upload URL: extract filename from path
                fname = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
                title = f"File:{fname.replace('_', ' ')}"
            fallback_titles.append(title)

        print("  Fetching metadata...", end=" ", flush=True)
        try:
            candidates = get_file_info(fallback_titles)
        except Exception as e:
            print(f"[NG] Metadata fetch failed: {e}")
            return {"status": "error", "error": str(e)}
        print(f"OK ({len(candidates)} files)")

        # ダウンロード
        os.makedirs(images_dir, exist_ok=True)
        downloaded = []
        for i, title in enumerate(fallback_titles):
            info = candidates.get(title, {})
            dl_url = info.get("url", fallback_urls[i])
            ext = os.path.splitext(dl_url.split("?")[0])[-1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif"):
                ext = ".jpg"
            filename = f"wiki_{i + 1:02d}_{subject_en.lower().replace(' ', '_')}{ext}"
            output_path = os.path.join(images_dir, filename)

            print(f"    [{i + 1}/{len(fallback_titles)}] {filename}...", end=" ", flush=True)
            if os.path.exists(output_path):
                print("already exists, skipping")
            else:
                ok = download_photo(dl_url, output_path)
                if not ok:
                    print("[NG] Failed")
                    continue
                size_kb = os.path.getsize(output_path) / 1024
                print(f"[OK] ({size_kb:.0f} KB)")

            downloaded.append(
                {
                    "title": title,
                    "local_filename": filename,
                    "url": info.get("url", dl_url),
                    "license": info.get("license", ""),
                    "author": info.get("author", ""),
                    "description": info.get("description", ""),
                    "commons_page": info.get("commons_page", ""),
                    "width": info.get("width", 0),
                    "height": info.get("height", 0),
                    "solo_portrait": is_solo_portrait(title, info.get("description", "")),
                    "score": 99.0,  # fallback — always top priority
                }
            )
            time.sleep(0.5)

        if not downloaded:
            print("  All downloads failed.")
            return {"status": "download_failed", "downloaded": 0}

    else:
        # ── 自動検索（fallback URLなし）──────────────────────
        import unicodedata

        def _ascii_fold(s):
            return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

        subject_ascii = _ascii_fold(subject_en)
        last_name = subject_en.split()[-1] if " " in subject_en else subject_en
        last_ascii = _ascii_fold(last_name)

        print("  Searching Wikimedia Commons...")
        all_results = {}  # title → result dict（重複排除）
        category_titles = set()  # カテゴリ経由で見つかったタイトル（名前マッチ免除用）

        # ── カテゴリ検索（最も信頼性が高い）───────────────────
        category_queries = [subject_en]
        if subject_ascii != subject_en:
            category_queries.append(subject_ascii)
        for cat in category_queries:
            print(f'    Category: "{cat}"...', end=" ", flush=True)
            try:
                results = search_category(cat, limit=30)
                new_count = 0
                for r in results:
                    if r["title"] not in all_results:
                        all_results[r["title"]] = r
                        new_count += 1
                    category_titles.add(r["title"])
                print(f"{len(results)} files ({new_count} new)")
            except Exception as e:
                print(f"[NG] {e}")
            time.sleep(0.3)

        # ── テキスト検索（カテゴリで見つからなかった場合の補完）──
        text_queries = [
            f"{subject_en} mathematician",
            f"{subject_ascii} mathematician",
            f"{last_name} photo portrait",
        ]
        if last_ascii != last_name:
            text_queries.append(f"{last_ascii} photo portrait")

        for q in text_queries:
            print(f'    Query: "{q}"...', end=" ", flush=True)
            try:
                results = search_commons(q, limit=20)
                new_count = 0
                for r in results:
                    if r["title"] not in all_results:
                        all_results[r["title"]] = r
                        new_count += 1
                print(f"{len(results)} results ({new_count} new)")
            except Exception as e:
                print(f"[NG] failed: {e}")
            time.sleep(0.3)

        results = list(all_results.values())
        print(f"  Total unique: {len(results)} files")

        if not results:
            print("  No results found.")
            return {"status": "no_results", "downloaded": 0}

        # ── メタデータ取得 ─────────────────────────────────────
        titles = [r["title"] for r in results]
        print("  Fetching metadata...", end=" ", flush=True)
        try:
            candidates = get_file_info(titles)
        except Exception as e:
            print(f"[NG] Metadata fetch failed: {e}")
            return {"status": "error", "error": str(e)}
        print(f"OK ({len(candidates)} files)")

        # ── スコアリングと選択 ─────────────────────────────────
        best = select_best_photos(
            candidates, max_photos, subject_en=subject_en, category_titles=category_titles
        )
        print(f"\n  Selected {len(best)} candidates:")
        for photo in best:
            print(f"    [{photo['score']:.1f}] {photo['title']}")
            print(f"          License: {photo['license']}")
            print(f"          Author:  {photo['author'] or '(unknown)'}")
            print(f"          Size:    {photo['width']}×{photo['height']}")

        if not best:
            print("  No suitable photos found (license or quality filter).")
            return {"status": "no_suitable", "downloaded": 0}

        if dry_run:
            print(f"\n  [DRY RUN] Would download {len(best)} photos and assign to scenes.")
            return {"status": "dry_run", "candidates": best}

        # ── ダウンロード ───────────────────────────────────────
        os.makedirs(images_dir, exist_ok=True)
        print("\n  Downloading...")

        downloaded = []
        for i, photo in enumerate(best):
            ext = os.path.splitext(photo["url"].split("?")[0])[-1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif"):
                ext = ".jpg"
            filename = f"wiki_{i + 1:02d}_{subject_en.lower().replace(' ', '_')}{ext}"
            output_path = os.path.join(images_dir, filename)

            print(f"    [{i + 1}/{len(best)}] {filename}...", end=" ", flush=True)

            if os.path.exists(output_path):
                print("already exists, skipping")
                photo["local_filename"] = filename
                downloaded.append(photo)
                continue

            dl_url = photo.get("thumb_url") or photo["url"]
            ok = download_photo(dl_url, output_path)
            if ok:
                size_kb = os.path.getsize(output_path) / 1024
                print(f"[OK] ({size_kb:.0f} KB)")
                photo["local_filename"] = filename
                downloaded.append(photo)
            else:
                print("[NG] Failed")

            time.sleep(0.5)

        if not downloaded:
            print("  All downloads failed.")
            return {"status": "download_failed", "downloaded": 0}

    # ── 外見記述の自動生成 ─────────────────────────────────
    # ソロポートレートから顔の特徴を抽出し、episode_config.jsonに保存
    # image_generator.pyのリファレンスベース生成で全シーン共通の顔特徴として注入される
    if not config.get("subject_appearance"):
        solo_photos = [
            p
            for p in downloaded
            if p.get(
                "solo_portrait", is_solo_portrait(p.get("title", ""), p.get("description", ""))
            )
        ]
        if solo_photos:
            best_solo = os.path.join(images_dir, solo_photos[0]["local_filename"])
            print(
                f"\n  Generating appearance description from {solo_photos[0]['local_filename']}...",
                end=" ",
                flush=True,
            )
            appearance = _generate_appearance(best_solo, subject_en, backend=appearance_backend)
            if appearance:
                print("[OK]")
                print(f"    -> {appearance}")
                # episode_config.json に書き戻し
                config["subject_appearance"] = appearance
                with open(episode_config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print("    Saved to episode_config.json")
            else:
                print("[WARN] Failed (will use reference photo only)")
    else:
        print(f"\n  Appearance: {config['subject_appearance'][:60]}... (existing)")

    # ── 写真の用途 ──────────────────────────────────────────
    # wiki写真はリファレンス専用（AI画像生成の顔参照として使用）。
    # シーンへの直接割り当ては行わない。理由：
    #   - 実写とAI油絵の混在は視覚的に不自然
    #   - 全シーンをAI油絵で統一した方がドキュメンタリーとしての一貫性が高い
    print("\n  Photos stored as reference only (not assigned to scenes)")
    print("  → image_generator will use these for identity-consistent AI generation")
    assignments = []
    updated_scene_def = scene_def  # scene_definition.json は変更しない

    # ── scene_definition.json 保存 ─────────────────────────
    # 変更なしだが、他のステップとの一貫性のために保存
    with open(scene_json_path, "w", encoding="utf-8") as f:
        json.dump(updated_scene_def, f, ensure_ascii=False, indent=2)

    # ── クレジット保存 ─────────────────────────────────────
    # assigned: シーンに直接割り当てた写真（年齢が近い）
    # reference_only: リファレンス用に保持（年齢差が大きく直接割当しないが、
    #   AI画像生成のリファレンスとして使用。derivative workなのでCC BYクレジット必要）
    assigned_filenames = {a["filename"] for a in assignments}
    reference_photos = [p for p in downloaded if p["local_filename"] not in assigned_filenames]

    credits = {
        "episode_id": episode_id,
        "subject": subject_en,
        "fetched_at": datetime.now().isoformat(),
        "photos": [
            {
                "filename": a["filename"],
                "scene_id": a["scene_id"],
                "wikimedia_title": a["wikimedia_title"],
                "license": a["license"],
                "license_url": _license_url(a["license"]),
                "author": a["author"],
                "commons_url": a["commons_url"],
                "solo_portrait": a.get("solo_portrait", False),
                "usage": "direct",  # シーンに直接割当
                "credit_text": _format_credit(a),
            }
            for a in assignments
        ]
        + [
            {
                "filename": p["local_filename"],
                "scene_id": None,
                "wikimedia_title": p["title"],
                "license": p["license"],
                "license_url": _license_url(p["license"]),
                "author": p.get("author", ""),
                "commons_url": p.get("commons_page", ""),
                "solo_portrait": p.get(
                    "solo_portrait", is_solo_portrait(p.get("title", ""), p.get("description", ""))
                ),
                "usage": "reference",  # AI生成のリファレンスとして使用
                "credit_text": _format_credit(
                    {
                        "wikimedia_title": p["title"],
                        "author": p.get("author", ""),
                        "license": p["license"],
                    }
                ),
            }
            for p in reference_photos
        ],
    }
    with open(credits_path, "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=2)

    # ── サマリー ───────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Downloaded: {len(downloaded)} photos (reference only)")
    print(f"  Credits:    {credits_path}")
    print(f"{'=' * 60}\n")

    return {
        "status": "ok",
        "downloaded": len(downloaded),
        "assigned": len(assignments),
        "assignments": assignments,
    }


def _license_url(license_short: str) -> str:
    """Map a short license string (e.g. 'cc by 3.0') to its canonical URL."""
    lic = license_short.lower().replace("-", " ").replace("_", " ").strip()
    # Map common CC license variants to URLs
    _CC_URLS = {
        "cc by 1.0": "https://creativecommons.org/licenses/by/1.0/",
        "cc by 2.0": "https://creativecommons.org/licenses/by/2.0/",
        "cc by 2.5": "https://creativecommons.org/licenses/by/2.5/",
        "cc by 3.0": "https://creativecommons.org/licenses/by/3.0/",
        "cc by 4.0": "https://creativecommons.org/licenses/by/4.0/",
        "cc by sa 1.0": "https://creativecommons.org/licenses/by-sa/1.0/",
        "cc by sa 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
        "cc by sa 2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
        "cc by sa 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
        "cc by sa 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    }
    for key, url in _CC_URLS.items():
        if key in lic:
            return url
    if "public domain" in lic or lic == "pd":
        return "https://creativecommons.org/publicdomain/mark/1.0/"
    return ""


def _format_credit(assignment: dict) -> str:
    """Format attribution string for video credits (CC BY compliant)."""
    author = assignment["author"] or "Wikimedia Commons"
    license_short = assignment["license"].upper().replace("-", " ")
    license_url = _license_url(assignment["license"])
    title = assignment["wikimedia_title"].replace("File:", "")
    parts = [f"{title} by {author}, {license_short}"]
    if license_url:
        parts.append(f"({license_url})")
    parts.append("via Wikimedia Commons")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Appearance auto-generation (Claude Sonnet Vision via Claude Code CLI)
# ---------------------------------------------------------------------------
def _generate_appearance(image_path: str, subject_name: str, backend: str = "sonnet") -> str:
    """Generate a facial feature description from a solo portrait photo.

    Args:
        backend: "sonnet" (Claude Code CLI, Max subscription) or "gemini" (Gemini Flash Vision).

    Returns empty string on failure.
    """
    if backend == "gemini":
        return _generate_appearance_gemini(image_path, subject_name)

    # ── Primary: Claude Code CLI ──────────────────────────────
    import tempfile

    abs_image_path = os.path.abspath(image_path)
    prompt = (
        f"以下の画像ファイルを読んで分析してください。\n"
        f"画像ファイル: {abs_image_path}\n\n"
        f"This is a photograph of {subject_name}. "
        f"Describe ONLY the person's distinctive facial features that would remain "
        f"recognizable across different ages (from childhood to old age). "
        f"Focus on: bone structure, face shape, nose shape, lip shape, brow shape, "
        f"ear shape, eye shape, forehead width, chin shape, and overall build. "
        f"Do NOT describe age-dependent features like wrinkles, hair color, or skin condition. "
        f"Output ONLY a comma-separated list of features in English, no explanation. "
        f"Example: 'narrow face, prominent aquiline nose, thin lips, deep-set eyes, "
        f"broad forehead, large ears, angular jawline, lean build'"
    )

    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, "_tmp_appear_prompt.txt")
    output_path = os.path.join(tmp_dir, "_tmp_appear_output.txt")
    error_path = os.path.join(tmp_dir, "_tmp_appear_error.txt")

    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(prompt)

        for p in [output_path, error_path]:
            if os.path.exists(p):
                os.remove(p)

        cmd = (
            f'type "{prompt_path}" | claude -p --output-format text '
            f'> "{output_path}" 2> "{error_path}"'
        )

        exit_code = os.system(cmd)

        if exit_code == 0 and os.path.exists(output_path):
            with open(output_path, encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            # 簡易バリデーション（英語のカンマ区切りリストか）
            if text and "," in text and len(text) < 500 and not text.startswith("{"):
                text = text.split("\n")[0].rstrip(".")
                return text
    except Exception as e:
        print(f"(appearance gen error [Claude CLI]: {str(e)[:60]})")
    finally:
        for p in [prompt_path, output_path, error_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

    # ── Fallback: Gemini Flash Vision ─────────────────────────
    return _generate_appearance_gemini(image_path, subject_name)


def _generate_appearance_gemini(image_path: str, subject_name: str) -> str:
    """Fallback: Generate appearance using Gemini Flash Vision."""
    try:
        from google import genai
        from PIL import Image
    except ImportError:
        return ""

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv

            script_dir = os.path.dirname(os.path.abspath(__file__))
            for d in [script_dir, os.path.dirname(script_dir)]:
                env_path = os.path.join(d, ".env")
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
            api_key = os.environ.get("GOOGLE_API_KEY")
        except ImportError:
            pass
    if not api_key:
        return ""

    client = genai.Client(api_key=api_key)

    try:
        img = Image.open(image_path)
        prompt = (
            f"This is a photograph of {subject_name}. "
            f"Describe ONLY the person's distinctive facial features that would remain "
            f"recognizable across different ages (from childhood to old age). "
            f"Focus on: bone structure, face shape, nose shape, lip shape, brow shape, "
            f"ear shape, eye shape, forehead width, chin shape, and overall build. "
            f"Do NOT describe age-dependent features like wrinkles, hair color, or skin condition. "
            f"Output ONLY a comma-separated list of features in English, no explanation. "
            f"Example: 'narrow face, prominent aquiline nose, thin lips, deep-set eyes, "
            f"broad forehead, large ears, angular jawline, lean build'"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt],
        )
        text = (response.text or "").strip()

        if text and "," in text and len(text) < 500 and not text.startswith("{"):
            text = text.split("\n")[0].rstrip(".")
            return text
        return ""
    except Exception as e:
        print(f"(appearance gen error [Gemini]: {str(e)[:60]})")
        return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Fetch CC-licensed photos from Wikimedia Commons and assign to scenes"
    )
    parser.add_argument("config_json", help="Path to episode_config.json")
    parser.add_argument(
        "--scene-json", default=None, help="Path to scene_definition.json (default: auto-detect)"
    )
    parser.add_argument(
        "--max-photos", type=int, default=3, help="Max photos to download (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview candidates without downloading or modifying files",
    )
    parser.add_argument(
        "--appearance-backend",
        default="sonnet",
        choices=["sonnet", "gemini"],
        help="Backend for appearance generation: "
        "sonnet (Claude Code CLI, Max subscription, default) "
        "or gemini (Gemini Flash Vision, free tier)",
    )
    args = parser.parse_args()

    config_path = os.path.abspath(args.config_json)
    episode_dir = os.path.dirname(config_path)

    scene_json = args.scene_json or os.path.join(episode_dir, "scene_definition.json")
    if not os.path.exists(scene_json):
        print(f"ERROR: scene_definition.json not found: {scene_json}")
        print("Run script generation first.")
        sys.exit(1)

    result = fetch_and_assign(
        episode_config_path=config_path,
        scene_json_path=scene_json,
        max_photos=args.max_photos,
        dry_run=args.dry_run,
        appearance_backend=args.appearance_backend,
    )

    if result.get("status") == "error":
        sys.exit(2)


if __name__ == "__main__":
    main()
