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
      - brackets via normalize_brackets (, the ONE table shared with
        gen_cloud._cleanup): 『』 -> a short pause (、), 「」《》 removed (an earlier episode:
        Chirp3-HD voices those NON-deterministically, heard as "ま"/"うぇ" at
        some 《, silent at others). The generated path already applied the same
        table, so this is idempotent there; a HAND-WRITTEN narration_speech_cloud
        bypasses gen_cloud and gets the identical treatment here.
    No misreading/kana dictionary is applied here (Cloud reads BERT-contextual
    accent; VOICEVOX-specific normalization would corrupt it). Per-engine reading
    tweaks (particle は->わ, katakana for foreign names) are authored by hand in
    scene_definition.json `narration_speech_cloud`, not synthesized here.
    """
    text = text.replace("|", "").replace(" ", "").replace("　", "")
    # (2026-09-19): 括弧の扱いは gen_cloud_readings._cleanup と同じ表 (normalize_brackets)。
    # それまで 『』 を gen は読点 (間) に、ここは削除にしていて、手書きの cloud 文だけ間が消えた。
    return normalize_brackets(text)


# 括弧・引用記号の扱い。
#   『』 -> 、 : 書名・強調の引用は軽い間として読ませる (生成側の設計)
#   「」《》 -> 削除: Chirp3-HD が非決定的に音声化する。narration (字幕) には残る
BRACKET_RULES: tuple[tuple[str, str], ...] = (
    ("『", "、"),
    ("』", "、"),
    ("「", ""),
    ("」", ""),
    ("《", ""),
    ("》", ""),
)


def normalize_brackets(text: str) -> str:
    """括弧を BRACKET_RULES で置換し、生じた重複句読点と先頭の読点を畳む。冪等。"""
    for src, dst in BRACKET_RULES:
        text = text.replace(src, dst)
    text = text.replace("、。", "。").replace("。、", "。")
    text = re.sub(r"、{2,}", "、", text)
    return re.sub(r"^[、\s]+", "", text)


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
    # 助手 -> じょし 誤読。
    # 助手 は常に じょしゅ で文脈非依存。全67話の narration で 11 回 / 8 話に出るが、
    # いずれも「〜の助手となり」型で読みは一つ。複合語 (助手席等) は本チャンネルに出現しない。
    "助手": "じょしゅ",
    # 大著 -> だいちょう 誤読。
    # 大著 は常に たいちょ で文脈非依存。全67話で 14 回 / 12 話。長音側へ倒れるのは
    # 主著 (しゅちょ -> しゅちょう) と同型の誤り方で、同じ長さの語頭子音違い。
    "大著": "たいちょ",
    # 最小 -> さいしょう を Chirp が **同じ回の中で非決定的に さいしょ へ倒す**。出荷 wav STT で intro_01/person_04 が さいしょ、person_05/math_03/math_11
    # は さいしょう と、**同一表層が一本の中で二通りに読まれた**。文脈非依存 (最小値/
    # 最小限/最小二乗法/最小化 いずれも さいしょう) なので force が正しい。全68話で
    # 25 回 / 12 話に出るが、さいしょ と読む用法は日本語に存在しない。
    "最小": "さいしょう",
    # 実解析 -> みかいせき 誤読。実 は じつ/み/さね と
    # 割れるが、数学語としての 実解析 は常に じつかいせき で文脈非依存
    # (実数=じっすう と同系。みかいせき という語は存在しない)。
    "実解析": "じつかいせき",
    # 場合 -> バイ 誤読。
    # 場合 は常に ばあい で文脈非依存 (その場合/場合分け いずれも同じ)。
    # **かなを直接埋めると Chirp が「ば・あい」と割って不自然に切れる** ので、
    # SSML phoneme で 1 トークンとして読ませるこの層が正しい。
    "場合": "ばあい",
    # 考証学 -> しょうがく / ごしょうがく 誤読。
    # 清代の学問名で常に こうしょうがく。文脈非依存。
    "考証学": "こうしょうがく",
    "二乗": "にじょう",  # 二乗 -> じじょう/じしょう
    "数論家": "すうろんか",  # 家 -> け 誤読 (すうろんけ) を Cloud が非決定ロール。数論家は常に すうろんか で文脈非依存
    # 対数 -> だいすう (対=だい 誤読) を Cloud が非決定的にロール (2026-07 実測、2ロールで
    # タイスウ/ダイスウ)。数学史で頻出・文脈非依存。VOICEVOX 資産の proactive seed 検証中に
    # 確定 (他の VOICEVOX 誤読 数値/絶対値/多角形/辺/後世/冪乗/素数/空集合 は Cloud で正読=不採用)。
    "対数": "たいすう",
    # セルジューク朝 -> Cloud が「朝」を あさ と誤読。複合語として常に ちょう なので登録可 (単体 朝 は文脈依存で不可)。
    "セルジューク朝": "せるじゅーくちょう",
    # 主著 -> しゅちょう 誤読。主著=しゅちょ は文脈非依存だが、**この override は完全には効かない**:
    # 対照実験 (2026-08-18、各 2 サンプル STT) で 平仮名しゅちょ=主張/主張、phoneme固定=視聴/史書 と
    # どちらも長音側に揺れた。唯一安定したのは言い換え『主な著書』(2/2 完全書き起こし)。
    # **第一の対策は narration の言い換え** (cloud_reading_lint が警告する)。この override は
    # 言い換えを逃した場合の backstop として残す (無いよりは寄る)。retro: 048/056 出荷分に誤読確定。
    "主著": "しゅちょ",
    # カタカナ変数 + 乗 -> のり 誤読。指数の 乗 は常に じょう で文脈非依存。cloud 回の出現は 049 (ピー乗/エヌ乗、出荷済)
    # と 066 のみ (全 ep 掃引 2026-08-18)。二乗→にじょう と同型で phoneme が効く見込みだが、
    # 066 は かな直書きで固定済み (この override は 049 再ビルドと将来 ep の backstop)。
    "エックス乗": "えっくすじょう",
    "エヌ乗": "えぬじょう",
    "ピー乗": "ぴーじょう",
    # 以下 4 件は ある回の通し視聴で user の耳が拾ったもの (2026-08-24)。いずれも文脈非依存。
    # 非線形 -> Chirp が「非」を落として「線形」に聞こえる。非線形 は常に ひせんけい で、非線形性/非線形項/非線形力学 も同じ。
    "非線形": "ひせんけい",
    # 相平面 -> あいへいめん。相 は そう/あい と割れるが、力学系の
    # 相平面/相空間/相図 は常に そう。相手 (あいて) のような和語複合は本チャンネルの
    # 数学文脈に出ない。
    "相平面": "そうへいめん",
    "相空間": "そうくうかん",
    # 相図 -> さいず。「サイズ」に聞こえるので誤解が大きい。
    "相図": "そうず",
    # 放っておけ -> はなっておけ。単体の 放って は はなって/ほうって で
    # 文脈依存だが、「放っておく/放っておけ」の句としては常に ほうって。
    "放っておけ": "ほうっておけ",
    "放っておく": "ほうっておく",
    # 一度離れ -> いちどばなれ と連濁。〜離れ (わかものばなれ 等) の
    # 接尾辞と誤解している。数詞 + 離れる は連濁しない。
    "一度離れ": "いちどはなれ",
}
# エピソード固有の読み (episode_config.json の `cloud_reading_overrides`)。
# グローバル辞書に入れるほど汎用でない固有名 (地名・人名・書名) をここで受ける。
# **かなを narration_speech_cloud に直接埋めない**ための口である ──
# 埋めると Chirp がトークンを割り、「場合」が「ば・あい」、「えと」が「えーっと」に
# なる。SSML は漢字のまま読みだけ差すので韻律が保たれる。
_EPISODE_OVERRIDES: dict[str, str] = {}
_ACTIVE_OVERRIDES: dict[str, str] = dict(_READING_OVERRIDES)
_OVERRIDE_RE = None


def _rebuild_override_re() -> None:
    """_ACTIVE_OVERRIDES を作り直し、長い語から一致する正規表現を組む。"""
    global _ACTIVE_OVERRIDES, _OVERRIDE_RE
    # グローバルが優先 (較正済みの語を episode 側で壊させない)
    merged = dict(_EPISODE_OVERRIDES)
    merged.update(_READING_OVERRIDES)
    _ACTIVE_OVERRIDES = merged
    _OVERRIDE_RE = (
        re.compile("|".join(re.escape(w) for w in sorted(merged, key=len, reverse=True)))
        if merged
        else None
    )


def set_episode_overrides(mapping: dict | None) -> int:
    """その回だけの読み上書きを設定する。返り値は有効になった語数。

    同じ表層がグローバル辞書にもあるときは**グローバルを優先**する
    (出荷済みの回で較正した読みを、あとから来た episode 側の値で壊さないため)。
    """
    global _EPISODE_OVERRIDES
    _EPISODE_OVERRIDES = {
        str(k): str(v)
        for k, v in (mapping or {}).items()
        if k and v and str(k) not in _READING_OVERRIDES
    }
    _rebuild_override_re()
    return len(_EPISODE_OVERRIDES)


_rebuild_override_re()


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
            f'<phoneme alphabet="yomigana" ph="{_ACTIVE_OVERRIDES[word]}">'
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
            if resp.status_code == 400 and is_too_long_error(resp.text):
                # ある回: 日付を含む 89 字の一文で Chirp が「文が長すぎる」を返し、audio ステップが
                # 2 分で落ちた (出荷 4,471 文の最長は 99 字で通っているので長さだけでは予測できない)。
                # リトライしても同じなので、読点で二つに分けて合成し、wav を繋いで返す。
                parts = split_long_sentence(text)
                if len(parts) >= 2:
                    print(
                        f"      [CLOUD][SPLIT] Chirp が「文が長すぎる」: {len(text)} 字を "
                        f"{len(parts)} つに分けて合成します (narration の分割を推奨): "
                        f"{text[:40]}..."
                    )
                    return _synthesize_split(parts, output_path, voice, rate, api_key)
        except Exception as e:  # noqa: BLE001 - retry any transient error, report last
            last_err = repr(e)
        time.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"Cloud TTS failed for {output_path!r} after {_MAX_ATTEMPTS} attempts: {last_err}"
    )


def is_too_long_error(body: str) -> bool:
    """Chirp3-HD の HTTP 400「This request contains sentences that are too long」か。"""
    return "too long" in (body or "")


def split_long_sentence(text: str, max_len: int = 60) -> list[str]:
    """一文を、中央に最も近い読点で二つに分ける (再帰的に max_len 以下まで)。

    読点が無ければ分けられないので [text] を返す (呼び出し側はそのまま失敗させる)。
    分けた前半は読点で終わったままにする (Chirp が文末として扱い、間が自然になる)。
    """
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    cuts = [m.end() for m in re.finditer("、", text)]
    cuts = [c for c in cuts if 8 <= c <= len(text) - 8]
    if not cuts:
        return [text]
    mid = len(text) / 2
    c = min(cuts, key=lambda k: abs(k - mid))
    left, right = text[:c].strip(), text[c:].strip()
    return split_long_sentence(left, max_len) + split_long_sentence(right, max_len)


def _synthesize_split(parts, output_path, voice, rate, api_key) -> float:
    """分割した各片を合成し、LINEAR16 (同 rate / mono) の wav として繋いで output_path に書く。"""
    import os
    import wave

    tmp_paths = []
    try:
        for i, part in enumerate(parts):
            tp = f"{output_path}.part{i}.wav"
            synthesize_cloud(part, tp, voice=voice, rate=rate, api_key=api_key)
            tmp_paths.append(tp)
        with wave.open(tmp_paths[0], "rb") as w0:
            params = w0.getparams()
        with wave.open(output_path, "wb") as out:
            out.setparams(params)
            for tp in tmp_paths:
                with wave.open(tp, "rb") as w:
                    assert w.getframerate() == params.framerate
                    assert w.getnchannels() == params.nchannels
                    out.writeframes(w.readframes(w.getnframes()))
    finally:
        for tp in tmp_paths:
            try:
                os.remove(tp)
            except OSError:
                pass
    return _wav_duration(output_path)


def config_signature(voice: str, rate: float) -> str:
    """Stable string of the Cloud params that affect a per-sentence wav.

    Folded into the per-sentence audio cache key (audio_generator) so a
    voice/rate change invalidates cached Cloud wavs. Combined with the synthesis
    text this ALSO gives Cloud a pseudo-deterministic cache: identical text +
    voice + rate reuses the previously-accepted take instead of re-rolling the
    non-deterministic Cloud output.
    """
    return f"cloud|{voice}|rate={rate}"
