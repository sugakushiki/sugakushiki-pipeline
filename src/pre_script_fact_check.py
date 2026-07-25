"""pre_script_fact_check.py - Verify factual claims in episode_config.json
before script generation.

Three-layer check:
- C: Claude Sonnet evaluates verified_facts / key_episodes / theme /
     key_topics for historical accuracy (knowledge-base check).
- D: Deterministic arithmetic sanity (birth/death years, age computation,
     event-year ordering) — no LLM, no API.
- E: Wikidata SPARQL cross-check for birth/death year against the
     authoritative entity (urllib only, no extra dependencies).

Output: pre_script_fact_check_report.json
Behaviour:
- default: any CRITICAL or WARNING aborts pipeline before script step
- --fact-check-allow-warn: only CRITICAL aborts (mirrors --qa-allow-warn)
- --skip-fact-check: bypass entirely

Cache: results keyed by episode_config hash; unchanged config skips Claude.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

# fix: Windows console is cp932 by default. When Sonnet's fact-check
# response contains characters outside cp932 (e.g. en-dash U+2013), the
# subsequent print() raises UnicodeEncodeError, which bubbles up and is
# caught at a higher layer with a `skipped due to error` message —
# the pipeline then bypasses CRITICAL/WARN handling silently. Forcing
# stdout/stderr to UTF-8 makes the lint output robust on cp932 consoles.
# (Same pattern as .claude/hooks/qa_report_reminder.py.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config_validator import get_verified_fact_source, get_verified_fact_text

# ---------------------------------------------------------------------------
# Prompt construction (C: Claude Sonnet check)
# ---------------------------------------------------------------------------


def _coerce_subject(episode_config: dict) -> tuple[str, str]:
    """Return (subject_en, subject_ja) tolerating dict / str shapes."""
    math_field = episode_config.get("mathematician", "不明")
    if isinstance(math_field, dict):
        subject_en = math_field.get("name", "不明")
    else:
        subject_en = str(math_field)
    subject_ja = episode_config.get("mathematician_ja", subject_en)
    return subject_en, subject_ja


def build_fact_check_prompt(episode_config: dict) -> str:
    """Compose the Sonnet prompt for verified_facts/key_episodes/theme."""
    subject_en, subject_ja = _coerce_subject(episode_config)

    verified_facts = episode_config.get("verified_facts", {})
    key_episodes = episode_config.get("key_episodes", [])
    theme = episode_config.get("theme", "")
    key_topics = episode_config.get("key_topics", [])

    vf_lines = []
    for k, v in verified_facts.items():
        if k.startswith("_"):
            continue  # _note etc. are documentation, not facts
        text = get_verified_fact_text(v)
        source = get_verified_fact_source(v)
        if source:
            vf_lines.append(f"  {k}: {text} (出典: {source})")
        else:
            vf_lines.append(f"  {k}: {text}")
    vf_block = "\n".join(vf_lines) if vf_lines else "  (空)"

    ke_lines = []
    for i, item in enumerate(key_episodes):
        ke_lines.append(f"  [{i}] {item}")
    ke_block = "\n".join(ke_lines) if ke_lines else "  (空)"

    kt_lines = []
    for i, item in enumerate(key_topics):
        kt_lines.append(f"  [{i}] {item}")
    kt_block = "\n".join(kt_lines) if kt_lines else "  (空)"

    return f"""あなたは数学史の事実検証の専門家です。
以下は episode_config.json (動画制作の設計資料) に記載された事実主張です。
この資料は次の script 生成プロセスの元になり、誤りがあると script に伝播します。
あなたの知識ベースに基づき、明らかな事実誤認を検出してください。

# 対象人物
{subject_en} ({subject_ja})

# verified_facts (構造化された確定事実)
{vf_block}

# key_episodes (時系列イベントリスト)
{ke_block}

# theme (物語の要約)
---
{theme}
---

# key_topics (主要トピック)
{kt_block}

# タスク

各事実主張について、あなたの知識ベースで検証可能な範囲で正確性を評価してください。

チェック項目:
1. 年号・日付 (生没年、論文発表年、事件年など)
2. 人名・地名の正確性 (スペル、読み、固有名詞)
3. 因果関係・人物関係 (誰が誰の弟子、誰がいつ命名、どの大学で学んだ)
4. 職業・役職 (大学教授、終身書記、ルター派牧師など)
5. 年齢計算の整合性 (享年・結婚時の親生死など)

# 出力形式

以下の JSON 形式でのみ出力してください。JSON 以外のテキストは含めないでください。

```json
{{
  "status": "PASS" または "WARN" または "FAIL",
  "issues": [
    {{
      "severity": "critical" または "warning" または "info",
      "field": "verified_facts.birth / key_episodes[3] / theme / key_topics[1] のような場所指定",
      "claim": "問題の主張 (原文から短く引用)",
      "finding": "検証結果の説明",
      "correction": "正しい情報 (なければ null)",
      "confidence": 0.0 から 1.0 の数値
    }}
  ],
  "verified_count": "検証した事実の総数",
  "summary": "全体の評価を1-2文で"
}}
```

判定基準:
- PASS: critical=0, warning=0
- WARN: critical=0, warning>=1
- FAIL: critical>=1

severity 判定ルール (厳守):
- **critical**: 年号 2 年以上ズレ / 人名・場所の明確な間違い / 存在しないエピソードの捏造 / 因果関係の逆転 / 享年と生没年の算術矛盾
- **warning**: 年号 1 年ズレ / 役職・職業の不正確 / confidence 0.5-0.7 の不確かな主張 / 解釈に争いのある事実
- **info**: 表現の曖昧さ ("約" "頃" で許容) / confidence < 0.5 で判断不能

確信が持てない場合は warning 寄り、知識ベースに含まれない場合は info で confidence を 0.3 以下にしてください。
事実が正確な場合は issues に含めないでください (問題のある主張のみ報告)。
出力は assistant の text ブロックに直接、Bash や他のツールを使わずに書いてください。
"""


# ---------------------------------------------------------------------------
# JSON response parsing
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_fact_check_response(response: str) -> dict:
    """Extract the JSON object from Claude's response. Returns parsed dict
    or a synthetic FAIL report if parsing breaks."""
    if not response:
        return {
            "status": "FAIL",
            "issues": [
                {
                    "severity": "critical",
                    "field": "internal",
                    "claim": "(no response)",
                    "finding": "Claude returned empty response",
                    "correction": None,
                    "confidence": 1.0,
                }
            ],
            "verified_count": 0,
            "summary": "Empty Claude response",
        }

    # robustness: Sonnet often prepends "<file> を読みます。" before
    # the ```json block, or returns a bare object with stray prose.
    # Try multiple extraction strategies before giving up.
    candidates: list[str] = []

    # Strategy 1: fenced ```json ... ``` block (current behavior)
    m = _JSON_BLOCK_RE.search(response)
    if m:
        candidates.append(m.group(1))

    # Strategy 2: first ```json fence onward, taking everything until matching close
    fence_start = response.find("```json")
    if fence_start >= 0:
        after_fence = response[fence_start + len("```json") :].lstrip()
        # Find matching close fence
        fence_end = after_fence.find("```")
        if fence_end > 0:
            candidates.append(after_fence[:fence_end].strip())

    # Strategy 3: balanced { ... } from first `{` to last `}` (catches bare JSON
    # with leading prose, e.g. "ファイルを読みます。{...}")
    first_brace = response.find("{")
    last_brace = response.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(response[first_brace : last_brace + 1].strip())

    # Strategy 4: whole response as last resort
    candidates.append(response.strip())

    last_err: Exception | None = None
    for payload in candidates:
        # Strip stray markdown fences if a bare object came back
        clean = payload
        if clean.startswith("```"):
            clean = clean.strip("`").lstrip("json").strip()
        try:
            return json.loads(clean)
        except Exception as e:
            last_err = e
            continue

    return {
        "status": "FAIL",
        "issues": [
            {
                "severity": "critical",
                "field": "internal",
                "claim": "(parse error)",
                "finding": f"Failed to parse Claude response as JSON after {len(candidates)} strategies: {last_err}",
                "correction": None,
                "confidence": 1.0,
            }
        ],
        "verified_count": 0,
        "summary": f"JSON parse error: {last_err}",
        "raw_response_head": response[:500],
    }


# ---------------------------------------------------------------------------
# D: Arithmetic sanity (deterministic, no LLM)
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"(1[5-9]\d{2}|20[0-3]\d)")
_AGE_KANJI_RE = re.compile(r"享年\s*(\d{1,3})|(\d{1,3})\s*歳")
_LIFESPAN_RE = re.compile(r"\d{4}\s*[-–]\s*\d{4}")


def _strip_lifespan(text: str) -> str:
    """Remove "YYYY-YYYY" / "YYYY–YYYY" lifespan ranges so that years cited
    inside them (other people's birth/death years) don't count as event
    years for the subject of this episode."""
    if not isinstance(text, str):
        return ""
    return _LIFESPAN_RE.sub("", text)


def _extract_first_year(text: str) -> int | None:
    if not isinstance(text, str):
        return None
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def _extract_age(text: str) -> int | None:
    if not isinstance(text, str):
        return None
    m = _AGE_KANJI_RE.search(text)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def _verified_facts_years(vf: dict) -> set[int]:
    """Every year that appears anywhere in verified_facts text.

    A key_episode year that matches one of these is an INTENTIONAL, vetted
    historical anchor -- e.g. Hilbert posing his tenth problem in 1900, 19
    years before Julia Robinson's 1919 birth -- rather than a typo, so Check 3
    should not flag it as "predates birth". Typo years (e.g. 1019 for 1919)
    won't appear in the hand-verified verified_facts block, so typo detection
    is preserved. This resolves the false positive for episodes whose subject
    works on a problem posed before they were born (Hilbert-problem solvers,
    Fermat-conjecture provers, etc.)."""
    years: set[int] = set()
    if not isinstance(vf, dict):
        return years
    for val in vf.values():
        text = get_verified_fact_text(val)
        if isinstance(text, str):
            years.update(int(y) for y in _YEAR_RE.findall(text))
    return years


def arithmetic_sanity_check(episode_config: dict) -> list[dict]:
    """D: deterministic checks that need no external knowledge.

    Returns list of issue dicts (same shape as Claude issues so the report
    can merge them).
    """
    issues: list[dict] = []
    vf = episode_config.get("verified_facts", {})

    birth_year = episode_config.get("birth_year")
    if not isinstance(birth_year, int):
        birth_year = _extract_first_year(get_verified_fact_text(vf.get("birth", "")))
    death_year = _extract_first_year(get_verified_fact_text(vf.get("death", "")))

    # Check 1: birth/death year ordering
    if birth_year and death_year and death_year < birth_year:
        issues.append(
            {
                "severity": "critical",
                "field": "verified_facts.birth/death",
                "claim": f"birth={birth_year}, death={death_year}",
                "finding": "death year precedes birth year",
                "correction": None,
                "confidence": 1.0,
                "source": "arithmetic",
            }
        )

    # Check 2: age vs (death - birth)
    if birth_year and death_year:
        computed_age = death_year - birth_year
        for fld_key in ("death", "death_age", "age"):
            stated = _extract_age(vf.get(fld_key, ""))
            if stated and abs(stated - computed_age) > 1:
                issues.append(
                    {
                        "severity": "critical",
                        "field": f"verified_facts.{fld_key}",
                        "claim": f"享年/歳 = {stated}",
                        "finding": (
                            f"computed age {computed_age} (= {death_year} - "
                            f"{birth_year}) differs from stated {stated}"
                        ),
                        "correction": f"享年 {computed_age}",
                        "confidence": 1.0,
                        "source": "arithmetic",
                    }
                )

    # Check 3: each key_episode year falls within [birth_year, death_year + 200]
    # Allow posthumous events (e.g. 1841 publication of Abel's 1826 paper).
    # Strip "YYYY-YYYY" lifespan ranges first -- those are biographical
    # parentheticals about other people, not events for this subject.
    # Skip key_episodes[0] (typically the birth narrative; may juxtapose
    # alternate calendars or contested birth-year theories).
    # Allow ±5yr slack vs birth_year to tolerate Julian/Gregorian dual
    # dating (e.g. Bernoulli: 1654 J / 1655 G).
    # Also allow any year that is an INTENTIONAL, vetted anchor in
    # verified_facts (e.g. Hilbert's 1900 problem, posed before the subject's
    # birth) -- typo years won't be in verified_facts, so detection is kept.
    if birth_year:
        anchor_years = _verified_facts_years(vf)
        for i, item in enumerate(episode_config.get("key_episodes", [])):
            if i == 0:
                continue
            text_clean = _strip_lifespan(item if isinstance(item, str) else "")
            year = _extract_first_year(text_clean)
            if year and year < birth_year - 5 and year not in anchor_years:
                issues.append(
                    {
                        "severity": "critical",
                        "field": f"key_episodes[{i}]",
                        "claim": f"year {year} appears before birth_year {birth_year}",
                        "finding": "event predates subject's birth (>5yr slack)",
                        "correction": None,
                        "confidence": 1.0,
                        "source": "arithmetic",
                    }
                )

    # Check 4: theme references year >100yr before birth_year
    # (catches obvious typos; lifespan ranges stripped to avoid FP)
    if birth_year:
        theme_clean = _strip_lifespan(episode_config.get("theme", ""))
        for m in _YEAR_RE.finditer(theme_clean):
            y = int(m.group(0))
            if y < birth_year - 100:
                issues.append(
                    {
                        "severity": "warning",
                        "field": "theme",
                        "claim": f"year {y} mentioned",
                        "finding": (
                            f"year {y} is more than 100 years before birth_year {birth_year}"
                        ),
                        "correction": None,
                        "confidence": 0.6,
                        "source": "arithmetic",
                    }
                )
                break  # one warning per theme is enough

    return issues


# ---------------------------------------------------------------------------
# E: Wikidata SPARQL cross-check (no extra deps, urllib only)
# ---------------------------------------------------------------------------

_WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
_WIKIDATA_UA = "sugakushiki-fact-check/1.0 (https://github.com/sugakushiki)"


def _wikidata_search_entity(
    name: str,
    birth_year: int | None = None,
    timeout: int = 10,
) -> str | None:
    """Search Wikidata entities by English name. If birth_year is given,
    pick the candidate whose birth date is closest (within 5 years) — this
    disambiguates same-name persons (e.g. Jakob Bernoulli 1655 vs Jakob II
    Bernoulli 1759). Returns Q-id or None.
    """
    if not name or name == "不明":
        return None
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 5,
    }
    url = _WIKIDATA_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _WIKIDATA_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    candidates = data.get("search", [])
    if not candidates:
        return None
    # No birth-year hint: return top hit
    if birth_year is None:
        return candidates[0]["id"]
    # With birth-year hint: fetch birth date for each candidate, pick best match
    best_id = None
    best_diff = None
    for cand in candidates:
        qid = cand["id"]
        facts = _wikidata_get_person_facts(qid, timeout=timeout)
        wd_b = _extract_year_from_iso(facts.get("birthDate", ""))
        if wd_b is None:
            continue
        diff = abs(wd_b - birth_year)
        if diff <= 5 and (best_diff is None or diff < best_diff):
            best_diff = diff
            best_id = qid
    # No candidate within 5 years: skip (don't return wrong entity)
    return best_id


def _wikidata_get_person_facts(qid: str, timeout: int = 15) -> dict:
    """Fetch birth/death year + place via SPARQL. Returns dict, possibly empty."""
    sparql = f"""SELECT ?birthDate ?deathDate ?birthPlaceLabel ?deathPlaceLabel
WHERE {{
  OPTIONAL {{ wd:{qid} wdt:P569 ?birthDate. }}
  OPTIONAL {{ wd:{qid} wdt:P570 ?deathDate. }}
  OPTIONAL {{ wd:{qid} wdt:P19 ?birthPlace. }}
  OPTIONAL {{ wd:{qid} wdt:P20 ?deathPlace. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 1"""
    url = (
        _WIKIDATA_SPARQL
        + "?"
        + urllib.parse.urlencode(
            {
                "query": sparql,
                "format": "json",
            }
        )
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _WIKIDATA_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {}
    bindings = data.get("results", {}).get("bindings", [])
    if not bindings:
        return {}
    b = bindings[0]
    out = {}
    for k in ("birthDate", "deathDate", "birthPlaceLabel", "deathPlaceLabel"):
        if k in b:
            out[k] = b[k]["value"]
    return out


def _extract_year_from_iso(iso_date: str) -> int | None:
    if not iso_date:
        return None
    m = re.match(r"-?(\d{4})", iso_date)
    return int(m.group(1)) if m else None


def wikidata_check(episode_config: dict, timeout: int = 15) -> list[dict]:
    """E: cross-check birth/death year against Wikidata entity.

    Network/API failures are reported as INFO (not CRITICAL) so the pipeline
    can still run offline. Mismatches >1yr trigger CRITICAL.
    """
    issues: list[dict] = []
    subject_en, _ = _coerce_subject(episode_config)

    # Use birth_year as disambiguation hint to avoid same-name confusion
    cfg_birth_for_hint = episode_config.get("birth_year")
    if not isinstance(cfg_birth_for_hint, int):
        cfg_birth_for_hint = _extract_first_year(
            get_verified_fact_text(episode_config.get("verified_facts", {}).get("birth", ""))
        )

    qid = _wikidata_search_entity(subject_en, birth_year=cfg_birth_for_hint, timeout=timeout)
    if not qid:
        issues.append(
            {
                "severity": "info",
                "field": "wikidata.entity",
                "claim": f"search '{subject_en}' (birth hint {cfg_birth_for_hint})",
                "finding": "no Wikidata entity within 5yr of birth_year (skipped)",
                "correction": None,
                "confidence": 0.5,
                "source": "wikidata",
            }
        )
        return issues

    facts = _wikidata_get_person_facts(qid, timeout=timeout)
    if not facts:
        issues.append(
            {
                "severity": "info",
                "field": "wikidata.facts",
                "claim": f"Q-id {qid}",
                "finding": "SPARQL returned no facts (network or empty entity)",
                "correction": None,
                "confidence": 0.5,
                "source": "wikidata",
            }
        )
        return issues

    vf = episode_config.get("verified_facts", {})

    # Birth year
    wd_birth = _extract_year_from_iso(facts.get("birthDate", ""))
    cfg_birth = episode_config.get("birth_year")
    if not isinstance(cfg_birth, int):
        cfg_birth = _extract_first_year(get_verified_fact_text(vf.get("birth", "")))
    if wd_birth and cfg_birth:
        if abs(wd_birth - cfg_birth) > 1:
            issues.append(
                {
                    "severity": "critical",
                    "field": "birth_year (vs Wikidata)",
                    "claim": f"config={cfg_birth}",
                    "finding": f"Wikidata says {wd_birth} (entity {qid})",
                    "correction": str(wd_birth),
                    "confidence": 0.9,
                    "source": "wikidata",
                }
            )
        else:
            issues.append(
                {
                    "severity": "info",
                    "field": "birth_year",
                    "claim": f"config={cfg_birth}",
                    "finding": f"Wikidata confirms {wd_birth} ({qid})",
                    "correction": None,
                    "confidence": 1.0,
                    "source": "wikidata",
                }
            )

    # Death year
    wd_death = _extract_year_from_iso(facts.get("deathDate", ""))
    cfg_death = _extract_first_year(get_verified_fact_text(vf.get("death", "")))
    if wd_death and cfg_death:
        if abs(wd_death - cfg_death) > 1:
            issues.append(
                {
                    "severity": "critical",
                    "field": "verified_facts.death (vs Wikidata)",
                    "claim": f"config death year={cfg_death}",
                    "finding": f"Wikidata says {wd_death} ({qid})",
                    "correction": str(wd_death),
                    "confidence": 0.9,
                    "source": "wikidata",
                }
            )

    return issues


# ---------------------------------------------------------------------------
# Cache (config hash → report)
# ---------------------------------------------------------------------------


def _config_hash(episode_config: dict) -> str:
    """Hash the fields actually checked, ignoring transient ones (bgm etc)."""
    relevant = {
        "mathematician": episode_config.get("mathematician"),
        "mathematician_ja": episode_config.get("mathematician_ja"),
        "birth_year": episode_config.get("birth_year"),
        "verified_facts": episode_config.get("verified_facts", {}),
        "key_episodes": episode_config.get("key_episodes", []),
        "theme": episode_config.get("theme", ""),
        "key_topics": episode_config.get("key_topics", []),
    }
    blob = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load_cache(cache_path: str) -> dict:
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache_path: str, data: dict) -> None:
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [WARN] failed to write cache {cache_path}: {e}")


# ---------------------------------------------------------------------------
# F: References bibliographic review -- ADVISORY only
#
# Empirically (2026-07-24) the deterministic API approach (a)/(b) cannot reach
# FP=0: Open Library returns 0 hits for the real Laugwitz book AND Shannon's
# journal articles (coverage gap -> "0 hits = fabricated" false-positives real
# works), and reprint/reissue years (Dupuy 'La vie d'Évariste Galois': config
# cites the correct 1896 original, API returns the 1992 reprint) make a year
# compare false-positive on correct citations. ISBN is absent from all 693
# references. So the FP-safe path is an LLM advisory review that can reason about
# editions / translations / journals (layer F).
#
# Signal/noise measured on 9 shipped episodes (~65 correct refs) + a torture set:
#   recall 4/4 on planted errors (wrong author / wrong year / fabricated title /
#   translation-year), 0 hallucinated FP on clearly-correct entries, and it found
#   2 REAL latent errors in shipped configs, both web-confirmed. Anti-hallucination
#   held: correction stays null, verify_hint points at primary sources.
#
# ADVISORY = these issues go under report["reference_advisory"], NEVER merged
# into report["issues"], so they cannot contribute to the pipeline's blocking
# severity count (the human web-verifies each flag; approach-A default).
# ---------------------------------------------------------------------------


def _reference_is_url_only(ref: str) -> bool:
    """True when a reference is essentially just a site/URL pointer (MacTutor /
    Wikipedia / Britannica). These are validated by credits_generator's URL
    checks, so the bibliographic review skips them. Heuristic: a URL is present
    AND the non-URL remainder carries no year (no author/title/publisher clause
    to attribute-check)."""
    r = ref.strip()
    if "http" not in r:
        return False
    non_url = re.sub(r"https?://\S+", "", r)
    return not re.search(r"(1[5-9]\d\d|20\d\d)", non_url)


def build_reference_check_prompt(episode_config: dict) -> str:
    """Narrow, advisory, anti-hallucination prompt for reviewing references.

    Design (calibrated 2026-07-24): flag ONLY high-confidence wrong attributions;
    do NOT assert corrections (LLMs fabricate bibliographic detail -- ask the
    human to web-verify instead); stay quiet when unsure (precision over recall);
    never declare a journal / non-English / old primary source "nonexistent"
    just because it is outside the model's knowledge (that is the API's failure
    mode we are avoiding)."""
    subject = episode_config.get("mathematician_ja") or episode_config.get("mathematician", "?")
    subject_en = episode_config.get("mathematician", "")
    refs = [r for r in episode_config.get("references", []) if isinstance(r, str)]
    book_refs = [r for r in refs if not _reference_is_url_only(r)]
    ref_lines = "\n".join(f"  [{i}] {r}" for i, r in enumerate(book_refs)) or "  (なし)"

    return f"""あなたは数学史の書誌 (参考文献) の正確性を検証する専門家です。
以下は動画「{subject} ({subject_en})」の episode_config.json の references です。
これらは YouTube 概要欄の【主要参考文献】に出るため、著者・書名・出版年・出版社・
訳者の attribution が誤っていると学術的信頼性を損ないます。

# 検証対象の references (URL のみの項目は除外済み)
{ref_lines}

# タスク
各 reference について、あなたの知識ベースで **高い確信をもって誤り** と判断できる
attribution のみを報告してください。特に次に注意:
1. 著者がその書名の著者か (別人の著作を誤帰属していないか)
2. 出版年 — とりわけ **原典 / 翻訳 / 復刻 (reprint) の年を取り違えていないか**
3. 出版社・叢書名・訳者の誤り
4. 実在しない書名・でっちあげの疑い

# 重要な制約 (厳守)
- **正しい値を断定しないでください**。あなたも版・訳・復刻の年を誤りやすい。
  「ここが疑わしい、人間が一次資料 (出版社ページ / WorldCat / 図書館目録) で
  確認すべき」という **確認喚起** として報告し、correction には推測を書かない
  (確証がなければ null)。
- **確信が持てない項目は報告しない** (precision 優先)。雑音を出すくらいなら PASS。
- ジャーナル論文・非英語文献・古い一次資料は、あなたの知識に無くても
  「存在しない」と判断しないでください (知識ベースの網羅性の限界)。

# 出力形式 (JSON のみ、JSON 以外のテキストは書かない)
```json
{{
  "status": "PASS" または "WARN",
  "issues": [
    {{
      "severity": "warning" または "info",
      "ref_index": 0,
      "ref_quote": "問題の reference から短く引用",
      "finding": "なぜ疑わしいか (年の取り違え/著者誤帰属/等)",
      "verify_hint": "人間が確認すべき一次情報源",
      "correction": null,
      "confidence": 0.0-1.0
    }}
  ],
  "reviewed_count": 検証した book reference 数,
  "summary": "1-2文"
}}
```
- WARN = 高確信の疑わしい項目が1件以上。PASS = 報告なし。
- confidence < 0.7 の項目は原則 info。確証度の低いものは出さない。
- 出力は assistant の text ブロックに直接、ツールを使わず書いてください。
"""


def _references_hash(episode_config: dict) -> str:
    """Hash the references list only, so the reference cache invalidates when a
    reference is edited but not when unrelated config fields change."""
    refs = [r for r in episode_config.get("references", []) if isinstance(r, str)]
    return hashlib.sha256(json.dumps(refs, ensure_ascii=False).encode("utf-8")).hexdigest()


def run_reference_check(episode_config: dict, episode_dir: str, debug: bool = False) -> dict:
    """ layer F: advisory bibliographic review of references via Claude.

    Returns {status, issues, reviewed_count, summary}. Issues are ADVISORY --
    severity is capped to warning/info (never critical), source-tagged, and the
    caller stores this under report["reference_advisory"] (NOT report["issues"]),
    so it never feeds the pipeline's blocking severity count. Graceful-degrades
    to status="UNAVAILABLE" on empty/parse failure."""
    book_refs = [
        r
        for r in episode_config.get("references", [])
        if isinstance(r, str) and not _reference_is_url_only(r)
    ]
    if not book_refs:
        return {
            "status": "PASS",
            "issues": [],
            "reviewed_count": 0,
            "summary": "書籍 reference なし",
        }

    cache_path = os.path.join(episode_dir, "_reference_check_cache.json")
    cache = _load_cache(cache_path)
    ref_hash = _references_hash(episode_config)
    if cache.get("reference_hash") == ref_hash and "reference_report" in cache:
        print("  [reference-check] cache hit, skipping Claude call")
        report = cache["reference_report"]
    else:
        print(f"  [reference-check] reviewing {len(book_refs)} book reference(s) via Claude...")
        from claude_backend import call_claude

        prompt = build_reference_check_prompt(episode_config)
        t0 = time.time()
        response = call_claude(
            prompt=prompt, model="opus", debug=debug, prefix="refcheck", allowed_tools="Read"
        )
        elapsed = time.time() - t0
        print(f"  [reference-check] returned in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        report = parse_fact_check_response(response)
        # Graceful degrade: parse_fact_check_response emits a synthetic critical
        # "internal" issue on empty/broken output. A reference review is advisory,
        # so treat that as UNAVAILABLE (do not surface a scary fake issue, do not
        # cache a failure) rather than a real finding.
        if any(i.get("field") == "internal" for i in report.get("issues", [])):
            print("  [reference-check] unavailable (empty/parse failure) -- advisory skipped")
            return {
                "status": "UNAVAILABLE",
                "issues": [],
                "reviewed_count": len(book_refs),
                "summary": "reference review unavailable (empty/parse failure)",
            }
        _save_cache(
            cache_path,
            {
                "reference_hash": ref_hash,
                "reference_report": report,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    # Advisory hardening: cap any critical to warning, tag source.
    for issue in report.get("issues", []):
        if issue.get("severity") == "critical":
            issue["severity"] = "warning"
        issue.setdefault("source", "claude_reference")
    report.setdefault("reviewed_count", len(book_refs))
    return report


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def run_pre_script_fact_check(
    episode_config: dict,
    episode_dir: str,
    use_claude: bool = True,
    use_arithmetic: bool = True,
    use_wikidata: bool = True,
    use_references: bool = True,
    debug: bool = False,
) -> dict:
    """Run all enabled layers and return a merged report dict."""
    report = {
        "subject": episode_config.get("mathematician_ja", episode_config.get("mathematician", "?")),
        "issues": [],
        "layer_summary": {},
    }

    # Layer D: arithmetic sanity
    if use_arithmetic:
        d_issues = arithmetic_sanity_check(episode_config)
        report["issues"].extend(d_issues)
        report["layer_summary"]["arithmetic"] = {
            "issues": len(d_issues),
            "critical": sum(1 for i in d_issues if i["severity"] == "critical"),
        }

    # Layer E: Wikidata SPARQL cross-check
    if use_wikidata:
        print("  [pre-script fact-check] querying Wikidata...")
        e_issues = wikidata_check(episode_config)
        report["issues"].extend(e_issues)
        report["layer_summary"]["wikidata"] = {
            "issues": len(e_issues),
            "critical": sum(1 for i in e_issues if i["severity"] == "critical"),
        }

    # Layer C: Claude Sonnet
    if use_claude:
        cache_path = os.path.join(episode_dir, "_pre_script_fact_cache.json")
        cache = _load_cache(cache_path)
        cfg_hash = _config_hash(episode_config)

        if cache.get("hash") == cfg_hash and "claude_report" in cache:
            print("  [pre-script fact-check] cache hit, skipping Claude call")
            c_report = cache["claude_report"]
        else:
            print("  [pre-script fact-check] calling Claude Sonnet...")
            from claude_backend import call_claude

            prompt = build_fact_check_prompt(episode_config)
            t0 = time.time()
            response = call_claude(
                prompt=prompt,
                model="opus",
                debug=debug,
                prefix="prefact",
                allowed_tools="Read",
            )
            elapsed = time.time() - t0
            print(
                f"  [pre-script fact-check] Sonnet returned in "
                f"{elapsed:.1f}s ({elapsed / 60:.1f} min)"
            )
            c_report = parse_fact_check_response(response)
            _save_cache(
                cache_path,
                {
                    "hash": cfg_hash,
                    "claude_report": c_report,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            )

        # Tag claude issues with source
        for issue in c_report.get("issues", []):
            issue.setdefault("source", "claude_sonnet")
        report["issues"].extend(c_report.get("issues", []))
        report["layer_summary"]["claude_sonnet"] = {
            "status": c_report.get("status"),
            "issues": len(c_report.get("issues", [])),
            "verified_count": c_report.get("verified_count"),
            "summary": c_report.get("summary"),
        }

    # Layer F: references bibliographic review -- ADVISORY.
    # Stored under report["reference_advisory"], deliberately NOT merged into
    # report["issues"], so reference flags never affect the blocking severity
    # roll-up below (the human web-verifies each flag; approach-A default).
    if use_references:
        print("  [pre-script fact-check] reviewing references (advisory)...")
        ref_report = run_reference_check(episode_config, episode_dir, debug=debug)
        report["reference_advisory"] = ref_report
        report["layer_summary"]["references"] = {
            "status": ref_report.get("status"),
            "issues": len(ref_report.get("issues", [])),
            "reviewed_count": ref_report.get("reviewed_count"),
            "summary": ref_report.get("summary"),
        }

    # Roll-up status
    sev_counts = {"critical": 0, "warning": 0, "info": 0}
    for issue in report["issues"]:
        sev_counts[issue.get("severity", "info")] = (
            sev_counts.get(issue.get("severity", "info"), 0) + 1
        )
    report["severity_counts"] = sev_counts
    if sev_counts["critical"] > 0:
        report["overall_status"] = "FAIL"
    elif sev_counts["warning"] > 0:
        report["overall_status"] = "WARN"
    else:
        report["overall_status"] = "PASS"
    return report


def print_pre_script_fact_check_report(report: dict) -> None:
    """Pretty-print the merged report to stdout (ASCII-safe)."""
    print(f"\n{'=' * 60}")
    print("  Pre-script Fact Check Report")
    print(f"  Subject: {report.get('subject', '?')}")
    print(f"  Overall: {report.get('overall_status', '?')}")
    print(f"{'=' * 60}")

    sev = report.get("severity_counts", {})
    print(
        f"  CRITICAL: {sev.get('critical', 0)}  "
        f"WARNING: {sev.get('warning', 0)}  "
        f"INFO: {sev.get('info', 0)}"
    )

    for layer, summary in report.get("layer_summary", {}).items():
        print(f"\n  Layer [{layer}]: {summary}")

    issues = report.get("issues", [])
    if issues:
        print("\n  Issues:")
        for _i, issue in enumerate(issues):
            sev_tag = issue.get("severity", "info").upper()
            field = issue.get("field", "?")
            src = issue.get("source", "?")
            print(f"  [{sev_tag}] ({src}) {field}")
            print(f"     claim:      {issue.get('claim', '')[:120]}")
            print(f"     finding:    {issue.get('finding', '')[:200]}")
            corr = issue.get("correction")
            if corr:
                print(f"     correction: {str(corr)[:200]}")
            conf = issue.get("confidence")
            if conf is not None:
                print(f"     confidence: {conf}")

    # references advisory (separate from the blocking issues above).
    ref_adv = report.get("reference_advisory")
    if ref_adv:
        ref_issues = ref_adv.get("issues", [])
        print(f"\n  References: {ref_adv.get('status', '?')}")
        if ref_issues:
            print("  ** 書誌 attribution の要確認 -- 一次資料で web verify のこと (鵜呑み禁止) **")
            for issue in ref_issues:
                sev_tag = issue.get("severity", "info").upper()
                print(f"  [{sev_tag}] references[{issue.get('ref_index', '?')}]")
                print(f"     quote:   {str(issue.get('ref_quote', ''))[:120]}")
                print(f"     finding: {str(issue.get('finding', ''))[:200]}")
                vh = issue.get("verify_hint")
                if vh:
                    print(f"     verify:  {str(vh)[:200]}")
                conf = issue.get("confidence")
                if conf is not None:
                    print(f"     confidence: {conf}")
        else:
            print(f"     {ref_adv.get('summary', '')[:160]}")
    print(f"{'=' * 60}\n")


def save_report(report: dict, episode_dir: str) -> str:
    path = os.path.join(episode_dir, "pre_script_fact_check_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main():
    parser = argparse.ArgumentParser(
        description=(
            "Pre-script fact check for episode_config.json. "
            "Layers: C=Claude Sonnet, D=arithmetic sanity. "
            "E=Wikidata is implemented in a separate phase."
        )
    )
    parser.add_argument("episode_config", help="path to episode_config.json")
    parser.add_argument(
        "--episode-dir", help="output dir for cache + report (default: dir of episode_config)"
    )
    parser.add_argument(
        "--allow-warn", action="store_true", help="exit 0 even if WARNING; only CRITICAL fails"
    )
    parser.add_argument("--no-claude", action="store_true", help="skip C layer (Claude Sonnet)")
    parser.add_argument(
        "--no-arithmetic", action="store_true", help="skip D layer (arithmetic sanity)"
    )
    parser.add_argument("--no-wikidata", action="store_true", help="skip E layer (Wikidata SPARQL)")
    parser.add_argument(
        "--no-references",
        action="store_true",
        help="skip F layer",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    with open(args.episode_config, encoding="utf-8") as f:
        episode_config = json.load(f)

    episode_dir = args.episode_dir or os.path.dirname(os.path.abspath(args.episode_config))

    report = run_pre_script_fact_check(
        episode_config,
        episode_dir,
        use_claude=not args.no_claude,
        use_arithmetic=not args.no_arithmetic,
        use_wikidata=not args.no_wikidata,
        use_references=not args.no_references,
        debug=args.debug,
    )
    print_pre_script_fact_check_report(report)
    path = save_report(report, episode_dir)
    print(f"  Report saved: {path}")

    sev = report.get("severity_counts", {})
    if sev.get("critical", 0) > 0:
        print("  -> CRITICAL detected, aborting")
        sys.exit(1)
    if sev.get("warning", 0) > 0 and not args.allow_warn:
        print("  -> WARNING detected, aborting (use --allow-warn to continue)")
        sys.exit(1)
    print("  -> OK")


if __name__ == "__main__":
    _main()
