"""
cloud_tts.py - Google Cloud Text-to-Speech (Chirp3-HD) synthesis backend.

This is the Cloud counterpart to VOICEVOX synthesis in audio_generator.py.
audio_generator imports this module for the `engine=cloud` path; to keep the
dependency one-directional (avoid a circular import) this module is standalone
and must NOT import audio_generator. It only needs `requests` + stdlib.

Design notes (see docs/03_quality/pitfalls.md "Cloud TTS"):
  - REST synthesis, LINEAR16 / 24kHz / mono -> the WAV can be concatenated with
    VOICEVOX-produced WAVs (same SAMPLE_RATE / width / channels).
  - Chirp3-HD accepts `speakingRate` but NOT `pitch` (sending pitch errors).
  - Reading control: Chirp3-HD DOES honor SSML <phoneme alphabet="yomigana"> on
    synchronous requests (verified 2026-07). build_synthesis_input wraps only the
    ambiguous-kanji words listed in _READING_OVERRIDES in a <phoneme> tag and
    sends SSML for those sentences; all other sentences are sent as unchanged
    plain text (identical cache key + audio, no side effect).
  - There is no `audio_query` equivalent, so the kana a VOICEVOX build can
    pre-verify is not available here. Post-hoc reading QA is done via STT
    (scripts/stt_qa.py). strip_for_cloud only removes subtitle markers +
    word-separation spaces; no VOICEVOX misreading dictionary is applied here.
"""

import base64
import os
import re
import wave

# ---------------------------------------------------------------------------
# Cloud TTS settings
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ja-JP"
DEFAULT_VOICE = "ja-JP-Chirp3-HD-Enceladus"
DEFAULT_RATE = 0.90  # speakingRate; matches the shipped an earlier episode build

# Must match audio_generator.SAMPLE_RATE so Cloud WAVs concatenate with silence
# gaps generated there. LINEAR16 -> 16-bit mono.
SAMPLE_RATE = 24000

_SYNTH_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_MAX_ATTEMPTS = 4
_TIMEOUT_SEC = 90


def load_tts_api_key(env_path: str = ".env") -> str:
    """Return the Google Cloud TTS API key.

    Resolution order: process environment GOOGLE_TTS_API_KEY, then the .env file.
    Raises RuntimeError (fail loud) if neither has it.
    """
    env_key = os.environ.get("GOOGLE_TTS_API_KEY")
    if env_key:
        return env_key.strip().strip('"').strip("'")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_TTS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "GOOGLE_TTS_API_KEY not found (checked environment and .env). "
        "Cloud TTS synthesis requires it."
    )


def strip_for_cloud(text: str) -> str:
    """Normalize narration text for Cloud synthesis.

    The ONLY transform safe to apply automatically on the Cloud path:
      - remove | subtitle break markers
      - remove VOICEVOX word-separation spaces (half- and full-width)
      - remove emphasis/quote brackets 「」『』《》:
        Chirp3-HD voices these NON-deterministically (heard as "ま"/"うぇ" at some
        《, silent at others). gen_cloud._cleanup already strips them on the
        generated path, but a HAND-WRITTEN narration_speech_cloud bypasses
        gen_cloud and would reach synthesis with the brackets intact. Stripping
        here (idempotent with gen_cloud) guarantees no bracket ever reaches TTS.
    No misreading/kana dictionary is applied here (Cloud reads BERT-contextual
    accent; VOICEVOX-specific normalization would corrupt it). Per-engine reading
    tweaks (particle は->わ, katakana for foreign names) are authored by hand in
    scene_definition.json `narration_speech_cloud`, not synthesized here.
    """
    text = text.replace("|", "").replace(" ", "").replace("　", "")
    for bracket in ("「", "」", "『", "』", "《", "》"):
        text = text.replace(bracket, "")
    return text


# ---------------------------------------------------------------------------
# Ambiguous-kanji reading overrides (SSML <phoneme> reading control)
# ---------------------------------------------------------------------------
# Chirp3-HD reads some context-INDEPENDENT kanji words non-deterministically or
# wrongly (二乗 -> じじょう instead of にじょう; 数論家 -> すうろんけ instead of すうろんか).
# An SSML <phoneme alphabet="yomigana"> tag forces the correct reading
# DETERMINISTICALLY while keeping the kanji in place, so surrounding prosody is
# unaffected (verified prosody-neutral on ja-JP-Chirp3-HD, 2026-07; SSML is honored
# on synchronous requests, which this REST path uses).
#
# Add a word here ONLY when its reading is the SAME in EVERY context. Context-
# dependent kanji (下=した/もと, 物=ぶつ/もの, 開けた=あけた/ひらけた, ...) must NOT go here --
# a blanket override would create a new misreading; those need per-occurrence handling.
#
# Accumulate entries as misreadings are caught by ear/STT.
_READING_OVERRIDES = {
    "二乗": "にじょう",  # 二乗 -> じじょう/じしょう
    "数論家": "すうろんか",  # 家 -> け 誤読 (すうろんけ) を Cloud が非決定ロール。数論家は常に すうろんか で文脈非依存
    # 対数 -> だいすう (対=だい 誤読) を Cloud が非決定的にロール (2026-07 実測、2ロールで
    # タイスウ/ダイスウ)。数学史で頻出・文脈非依存。VOICEVOX 資産の proactive seed 検証中に
    # 確定 (他の VOICEVOX 誤読 数値/絶対値/多角形/辺/後世/冪乗/素数/空集合 は Cloud で正読=不採用)。
    "対数": "たいすう",
    # セルジューク朝 -> Cloud が「朝」を あさ と誤読。複合語として常に ちょう なので登録可 (単体 朝 は文脈依存で不可)。
    "セルジューク朝": "せるじゅーくちょう",
}
_OVERRIDE_RE = (
    re.compile("|".join(re.escape(w) for w in sorted(_READING_OVERRIDES, key=len, reverse=True)))
    if _READING_OVERRIDES
    else None
)


def _xml_escape(s: str) -> str:
    """Escape the three characters that are significant in SSML text content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_synthesis_input(text: str) -> dict:
    """Return the Cloud TTS `input` object (`{"text": ...}` or `{"ssml": ...}`).

    If `text` contains NO override word, returns {"text": text} BYTE-FOR-BYTE
    unchanged -- so the sentence's cache key and synthesized audio are identical to
    the plain-text path (no re-synthesis, no side effect for every normal sentence).

    If it contains one or more override words, returns {"ssml": "<speak>...</speak>"}
    with EACH override word wrapped in a <phoneme alphabet="yomigana"> tag and only
    those words tagged (the rest stays normal kanji, preserving prosody). Non-word
    text is XML-escaped; a single left-to-right pass never re-scans an inserted tag.
    """
    if _OVERRIDE_RE is None or not _OVERRIDE_RE.search(text):
        return {"text": text}
    parts: list[str] = []
    last = 0
    for m in _OVERRIDE_RE.finditer(text):
        parts.append(_xml_escape(text[last : m.start()]))
        word = m.group(0)
        parts.append(
            f'<phoneme alphabet="yomigana" ph="{_READING_OVERRIDES[word]}">'
            f"{_xml_escape(word)}</phoneme>"
        )
        last = m.end()
    parts.append(_xml_escape(text[last:]))
    return {"ssml": "<speak>" + "".join(parts) + "</speak>"}


def _wav_duration(filepath: str) -> float:
    """Duration of a WAV file in seconds (standalone copy to avoid importing
    audio_generator; identical semantics to audio_generator.get_wav_duration)."""
    with wave.open(filepath, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def synthesize_cloud(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: float = DEFAULT_RATE,
    api_key: str | None = None,
) -> float:
    """Synthesize `text` to a WAV via Google Cloud TTS. Returns duration seconds.

    Input is built by build_synthesis_input: plain text by default, or SSML with
    <phoneme> reading overrides when the sentence contains an ambiguous-kanji word
    (see _READING_OVERRIDES). No pitch (Chirp3-HD errors on it). Retries transient
    failures up to _MAX_ATTEMPTS, then raises RuntimeError (fail loud -- a silent
    partial audio is far worse than a hard stop).
    """
    import time

    import requests

    if api_key is None:
        api_key = load_tts_api_key()

    body = {
        "input": build_synthesis_input(text),
        "voice": {"languageCode": LANGUAGE_CODE, "name": voice},
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": SAMPLE_RATE,
            "speakingRate": rate,
        },
    }
    url = f"{_SYNTH_URL}?key={api_key}"

    last_err = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = requests.post(url, json=body, timeout=_TIMEOUT_SEC)
            if resp.status_code == 200:
                audio = base64.b64decode(resp.json()["audioContent"])
                with open(output_path, "wb") as f:
                    f.write(audio)
                return _wav_duration(output_path)
            # Redact the key from any echoed URL in the error body.
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:  # noqa: BLE001 - retry any transient error, report last
            last_err = repr(e)
        time.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"Cloud TTS failed for {output_path!r} after {_MAX_ATTEMPTS} attempts: {last_err}"
    )


def config_signature(voice: str, rate: float) -> str:
    """Stable string of the Cloud params that affect a per-sentence wav.

    Folded into the per-sentence audio cache key (audio_generator) so a
    voice/rate change invalidates cached Cloud wavs. Combined with the synthesis
    text this ALSO gives Cloud a pseudo-deterministic cache: identical text +
    voice + rate reuses the previously-accepted take instead of re-rolling the
    non-deterministic Cloud output.
    """
    return f"cloud|{voice}|rate={rate}"
