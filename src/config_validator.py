"""
config_validator.py - Validate episode_config.json at pipeline startup

Validates required fields, types, value constraints, and warns about
recommended-but-optional fields.

Usage (standalone):
    python config_validator.py examples/moriarty/episode_config.json

Usage (from pipeline.py):
    from config_validator import validate_config
    errors, warnings = validate_config(config, config_path)

verified_facts schema (, 2026-05-05):
    legacy: {"birth": "1802-08-05 Kragerø, Norway", ...}
    new:    {"birth": {"fact": "1802-08-05 Kragerø, Norway",
                        "source": "MacTutor / Abel Prize biography"}, ...}

    Both forms are accepted. Use get_verified_fact_text() and
    get_verified_fact_source() helpers below for unified access.
"""

import json
import os
import re
import sys

# ── verified_facts helpers ────────────────────────────────────────────


def get_verified_fact_text(value) -> str:
    """Return the fact text, supporting both legacy scalar and new dict form.

    Legacy: value is a scalar (str / int / float / bool) -> returned as str.
    New:    value is {"fact": <scalar>, "source": "..."} -> returns str("fact").
    Anything else -> empty string.
    """
    if isinstance(value, dict):
        return str(value.get("fact", ""))
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return ""


def get_verified_fact_source(value) -> str:
    """Return the source attribution if present (new dict form only).

    Returns "" for legacy string values or if "source" is missing.
    """
    if isinstance(value, dict):
        return str(value.get("source", ""))
    return ""


# ── Required fields: missing or wrong type → ERROR ──────────────────────────

REQUIRED_FIELDS = {
    "episode_id": str,
    "mathematician": str,
    "mathematician_ja": str,
    "subject_en": str,
    "theme": str,
    "title_draft": str,
    "target_duration_minutes": (int, float),
    "hook": str,
    "key_topics": list,
    "modern_connection": str,
    "key_episodes": list,
    "references": list,
    "verified_facts": dict,
    "bgm": dict,
    "additional_instructions": str,
    "common_errors_to_avoid": list,
}

# ── Recommended fields: missing → WARNING ───────────────────────────────────

RECOMMENDED_FIELDS = {
    "subject_appearance": (str, "画像生成の体格チェックが機能しない"),
    "appearance": (dict, "年齢変換生成の精度が低下する"),
    "description": (dict, "credits_generatorのチャプター・タグ生成が弱くなる"),
    "pronunciation_high_risk": (list, "誤読チェックが汎用ルールのみになる"),
}


def validate_config(config: dict, config_path: str = "") -> tuple[list[str], list[str]]:
    """Validate an episode_config.json dict.

    Returns (errors, warnings) where each is a list of human-readable strings.
    errors = validation failures that should block the pipeline.
    warnings = recommendations that should be displayed but not block.
    """
    errors = []
    warnings = []

    # ── 1. Required fields + type check ─────────────────────────────────
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in config:
            errors.append(f"必須フィールド '{field}' が見つかりません")
            continue
        value = config[field]
        if not isinstance(value, expected_type):
            actual = type(value).__name__
            if isinstance(expected_type, tuple):
                expected_name = "/".join(t.__name__ for t in expected_type)
            else:
                expected_name = expected_type.__name__
            errors.append(f"'{field}' の型が不正です: 期待={expected_name}, 実際={actual}")

    # ── 2. Value constraints ────────────────────────────────────────────

    # episode_id format: NNN_name
    episode_id = config.get("episode_id", "")
    if isinstance(episode_id, str) and episode_id:
        if not re.match(r"^\d{3}_[a-z_]+$", episode_id):
            errors.append(
                f"'episode_id' の形式が不正です: '{episode_id}' (期待: NNN_name, 例: 006_shannon)"
            )

    # target_duration_minutes range
    # Regular episodes are 10-19 min (VIDEO_SPEC canonical). The ceiling here is
    # 22, not 19, to accommodate the documented long-form exception. The format discipline
    # for regular episodes is enforced by VIDEO_SPEC, not by this sanity bound.
    tdm = config.get("target_duration_minutes")
    if isinstance(tdm, (int, float)):
        if not (5 <= tdm <= 22):
            errors.append(f"'target_duration_minutes' が範囲外です: {tdm} (期待: 5〜22)")

    # optional per-episode 読み上げ速度 override (VOICEVOX speedScale)。
    # 既定 0.87 (audio_generator.SPEED_SCALE)。実用域を外れた値は誤設定の可能性が
    # 高い (極端だと聴取不能) ので advisory WARN。hard error にしないのは tuning 値だから。
    ss = config.get("speed_scale")
    if ss is not None:
        if not isinstance(ss, (int, float)):
            errors.append(f"'speed_scale' は数値である必要があります (実際: {type(ss).__name__})")
        elif not (0.5 <= ss <= 1.5):
            warnings.append(
                f"'speed_scale' が実用域外です: {ss} (推奨 0.5〜1.5、既定 0.87)。"
                "意図的でなければ確認してください"
            )

    # Optional TTS engine block (Cloud TTS support). Absent = VOICEVOX (default),
    # so validate only when present (.get(), backward-compatible with every
    # existing config). Shape: {"engine": "voicevox"|"cloud", "voice": str,
    # "rate": float}. engine/voice are hard errors (misconfig -> wrong backend);
    # rate is advisory (a tuning value) unless the type is wrong.
    tts = config.get("tts")
    if tts is not None:
        if not isinstance(tts, dict):
            errors.append(f"'tts' は dict である必要があります (実際: {type(tts).__name__})")
        else:
            engine = tts.get("engine")
            if engine is not None and engine not in ("voicevox", "cloud"):
                errors.append(
                    f"'tts.engine' が不正です: '{engine}' (期待: 'voicevox' または 'cloud')"
                )
            voice = tts.get("voice")
            if voice is not None and not isinstance(voice, str):
                errors.append(
                    f"'tts.voice' は文字列である必要があります (実際: {type(voice).__name__})"
                )
            rate = tts.get("rate")
            if rate is not None:
                if not isinstance(rate, (int, float)) or isinstance(rate, bool):
                    errors.append(
                        f"'tts.rate' は数値である必要があります (実際: {type(rate).__name__})"
                    )
                elif not (0.25 <= rate <= 4.0):
                    warnings.append(
                        f"'tts.rate' が Cloud TTS の実用域外です: {rate} "
                        "(speakingRate 有効域 0.25〜4.0、既定 0.90)。意図的でなければ確認してください"
                    )

    # verified_facts must be dict (NOT list) — past crash prevention
    vf = config.get("verified_facts")
    if isinstance(vf, list):
        errors.append(
            "'verified_facts' がlistです。dictに変換してください "
            "(過去にlist-vs-dictクラッシュが発生)"
        )

    # verified_facts schema check: each entry should be either a scalar
    # legacy form (str / int / float / bool — the historic format used in 21
    # existing eps) or the new dict form {"fact": <scalar>, "source": str}.
    # Aggregate counts to avoid spamming WARN per key.
    if isinstance(vf, dict):
        legacy_keys = []
        missing_source_keys = []
        invalid_keys = []
        scalar_types = (str, int, float, bool)
        for fkey, fval in vf.items():
            if fkey.startswith("_"):
                continue  # _note and other private keys are exempt
            if isinstance(fval, scalar_types):
                legacy_keys.append(fkey)
            elif isinstance(fval, dict):
                if "fact" not in fval or not isinstance(fval["fact"], scalar_types):
                    invalid_keys.append(fkey)
                elif "source" not in fval or not fval["source"]:
                    missing_source_keys.append(fkey)
            else:
                invalid_keys.append(fkey)
        if invalid_keys:
            errors.append(
                f"'verified_facts' に不正な形式の値があります: {invalid_keys[:5]}"
                f" (期待: scalar または {{'fact': scalar, 'source': str}})"
            )
        if legacy_keys:
            warnings.append(
                f"'verified_facts' に legacy scalar 形式が {len(legacy_keys)} 件あります "
                f"({legacy_keys[:3]}{'...' if len(legacy_keys) > 3 else ''}). "
                f"出典記録のため新形式 {{'fact': ..., 'source': '...'}} への移行を推奨"
            )
        if missing_source_keys:
            warnings.append(
                f"'verified_facts' の dict 形式値で 'source' が欠落: "
                f"{missing_source_keys[:3]}{'...' if len(missing_source_keys) > 3 else ''} "
                f"(出典 URL / 書籍ページを記載すると QA 議論時の参照コストが下がる)"
            )

    # key_topics non-empty
    kt = config.get("key_topics")
    if isinstance(kt, list) and len(kt) == 0:
        errors.append("'key_topics' が空です")

    # key_episodes non-empty
    ke = config.get("key_episodes")
    if isinstance(ke, list) and len(ke) == 0:
        errors.append("'key_episodes' が空です")

    # references non-empty
    refs = config.get("references")
    if isinstance(refs, list) and len(refs) == 0:
        errors.append("'references' が空です")

    # bgm.file should be non-empty string
    bgm = config.get("bgm")
    if isinstance(bgm, dict):
        bgm_file = bgm.get("file", "")
        if not bgm_file:
            warnings.append("'bgm.file' が未設定です (BGMなしでビルドされます)")

    # voicevox_dictionary_additions is a deprecated / dead field:
    # no code in src/ or scripts/ consumes it. Pronunciations must be registered
    # in src/voicevox_dict.json (the only DICT_FILE that register_user_dict reads).
    # Authoring readings here is a silent no-op.
    vda = config.get("voicevox_dictionary_additions")
    if vda:
        n = len(vda) if isinstance(vda, (list, dict)) else 1
        warnings.append(
            f"'voicevox_dictionary_additions' ({n} 件) は廃止フィールドで、どのコードからも"
            f"読まれません (no-op)。読み辞書は src/voicevox_dict.json に登録してください"
        )

    # wikimedia_photo_urls schema check:
    # Must be a flat list of URL strings. The dict form (e.g.
    # `{"person": [...]}`) crashes wikimedia_fetcher.py with KeyError: 0
    # because fallback_urls[i] is called assuming list semantics.
    # wikimedia_fetcher already has a defensive check + sys.exit(1) at
    # runtime, but failing earlier in preflight saves ~0.7s and provides
    # a clearer error path.
    wpu = config.get("wikimedia_photo_urls")
    if wpu is not None:
        if isinstance(wpu, dict):
            errors.append(
                f"'wikimedia_photo_urls' が dict 形式です (keys: {list(wpu.keys())[:5]}). "
                f"flat list 形式 ['url1', 'url2', ...] を使用してください "
                f"(過去の対応で発覚した KeyError: 0 を予防)"
            )
        elif not isinstance(wpu, list):
            errors.append(
                f"'wikimedia_photo_urls' の型が不正です: 期待=list, 実際={type(wpu).__name__}"
            )
        else:
            non_str = [i for i, u in enumerate(wpu) if not isinstance(u, str)]
            if non_str:
                errors.append(
                    f"'wikimedia_photo_urls' に非文字列要素があります (index: {non_str[:5]})"
                )
            non_url = [
                i
                for i, u in enumerate(wpu)
                if isinstance(u, str) and u and not u.startswith(("http://", "https://"))
            ]
            if non_url:
                warnings.append(
                    f"'wikimedia_photo_urls' に http(s):// で始まらない URL があります "
                    f"(index: {non_url[:5]})"
                )

    # chronology structure (if present)
    chronology = config.get("chronology")
    if chronology is not None:
        if not isinstance(chronology, list):
            errors.append(
                f"'chronology' の型が不正です: 期待=list, 実際={type(chronology).__name__}"
            )
        elif chronology:
            for i, entry in enumerate(chronology):
                if not isinstance(entry, dict):
                    errors.append(f"'chronology[{i}]' がdictではありません")
                elif "year" not in entry or "event" not in entry:
                    errors.append(f"'chronology[{i}]' に 'year' または 'event' キーがありません")

    # ── 3. title_draft format check ─────────────────────────────────────
    title = config.get("title_draft", "")
    if isinstance(title, str) and title:
        if "──" not in title:
            warnings.append(
                f"'title_draft' に全角ダッシュ（──）が含まれていません: "
                f"'{title}' (推奨形式: 「名前 ── サブタイトル」)"
            )

    # ── 4. Recommended fields → WARNING ─────────────────────────────────
    for field, (expected_type, reason) in RECOMMENDED_FIELDS.items():
        if field not in config:
            warnings.append(f"推奨フィールド '{field}' が未設定です ({reason})")
        elif not isinstance(config[field], expected_type):
            actual = type(config[field]).__name__
            warnings.append(
                f"'{field}' の型が想定と異なります: 期待={expected_type.__name__}, 実際={actual}"
            )

    # ── 実写参照 gate-off ガード ──────────────────────────────────
    # image_generator gates reference-based portrait conditioning on birth_year:
    #   use_reference = bool(ref_photos) and birth_year and backend == "flash"
    # birth_year comes from config["birth_year"] OR a year parsed out of
    # verified_facts["birth"]. If a real subject reference photo was supplied
    # (wikimedia_photo_urls non-empty) but NO birth_year is resolvable, the gate
    # is silently OFF and every subject portrait is generated TEXT-ONLY (the photo
    # is fetched but never passed to Gemini -- less faithful). An earlier episode shipped this
    # way until a user spotted it; the only signal was one buried log line. Cheap
    # early WARN so the whole reason for fetching a reference photo is not defeated.
    photo_urls = config.get("wikimedia_photo_urls")
    if isinstance(photo_urls, list) and len(photo_urls) > 0:
        birth_year_ok = bool(config.get("birth_year"))
        if not birth_year_ok and isinstance(config.get("verified_facts"), dict):
            birth_txt = get_verified_fact_text(config["verified_facts"].get("birth", ""))
            if re.search(r"(1[89]\d{2}|20[0-3]\d)", birth_txt):
                birth_year_ok = True
        if not birth_year_ok:
            warnings.append(
                "実写参照 (wikimedia_photo_urls) があるのに birth_year が解決できません "
                "→ 参照 gate OFF で主題肖像が全て text-only 生成されます (実写に紐づかず "
                "忠実度低下)。top-level 'birth_year': YYYY を追加するか "
                "verified_facts['birth'] に生年を含めてください (image_generator.py:1754)"
            )

    return errors, warnings


def print_validation_result(errors: list[str], warnings: list[str], config_path: str = "") -> bool:
    """Print validation results. Returns True if no errors."""
    label = os.path.basename(config_path) if config_path else "config"

    if not errors and not warnings:
        print(f"[VALIDATE] {label}: OK")
        return True

    if warnings:
        print(f"\n[VALIDATE] {label}: {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\n[VALIDATE] {label}: {len(errors)} error(s)")
        for e in errors:
            print(f"  ERROR: {e}")
        return False

    return True


# ── Standalone CLI ──────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("Usage: python config_validator.py <episode_config.json>")
        sys.exit(1)

    config_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(config_path):
        print(f"ERROR: File not found: {config_path}")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    errors, warnings = validate_config(config, config_path)
    ok = print_validation_result(errors, warnings, config_path)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
