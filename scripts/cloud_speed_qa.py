"""cloud_speed_qa.py - Cloud TTS 発話速度の検出ガード + atempo 正規化 (opt-in fix)。

背景 (ある回の学び, internal notes):
  Google Cloud TTS (Chirp3-HD) は文ごとに **実発話速度そのもの** を大きく揺らす。
  実測で同一合成セッション内でも隣接文で 24-31% 差 (無音を除いた発話速度)。
  `tts.rate` は全体基準にすぎず、文単位の局所テンポは API で制御できない。しかも
  非決定的なので **個別文の再合成では収束しない** (サイコロの振り直し)。VOICEVOX は
  speedScale で一律決定的なのでこの問題は無い (このガードは engine=cloud 専用)。

対処は決定論的な後処理: 各文 wav の実発話速度 (mora / 無音を除く発話時間) を実測し、
エピソード全体の median に向けて ffmpeg atempo で部分圧縮する (ピッチ保持)。

モード:
  (default) detect  : 全文の発話速度を実測し、隣接文の急な段差を advisory WARN。
                      加えて「間・区切り」の異常も無音実測で検出 (run-on=文中の。で
                      間がほぼ無い / over-pause=不自然に長い無音 / dash=─『』残存)。
                      speed_qa_report.txt に一覧を残す。ファイルは一切変更しない。
                      engine=cloud のビルドで pipeline が audio 後に常時起動 (stt_qa と同格)。
  --apply           : atempo で正規化 (per-sentence wav を in-place 上書き、原本は
                      _prenorm_backup/ に退避)、scene wav を再連結、timing.json を
                      新しい尺で書き直す。pipeline は --normalize-cloud-speed 時のみ起動。
  --verify-timing   : atempo せず現行 wav から timing を再計算し、既存 timing.json と
                      差分を報告する自己テスト (arithmetic 一致の検証、破壊なし)。
  --restore         : _prenorm_backup/ から原本 wav を戻す (正規化の取り消し)。

設計原則 (internal notes):
  - detect は advisory (既定 exit 0、--strict で WARN 時 1)。build を止めない。
  - fix は opt-in (白縁 lint -> --trim と同じ思想)。音声の自動改変には人間の意思を挟む。
  - ドラマ的に意図して遅い行 (冒頭一言等、artic < median*FLOOR_FRAC) は正規化しない。
  - 原本を _prenorm_backup/ に退避し、常に復元可能 (--restore)。
  - concat/silence/duration は audio_generator の一次関数を再利用し合成パスと byte 整合。
"""

# Windows console は cp932。警告メッセージに含まれる em dash / 矢印などは cp932 で
# encode できず、**警告を出そうとした瞬間に** UnicodeEncodeError で死ぬ (正常系では
# 踏まれないので気づきにくい)。出力の入口で utf-8 に寄せる (smoke_test section 20)。
import sys as _sys

if _sys.stdout.encoding and _sys.stdout.encoding.lower() != "utf-8":
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import speech_source  # noqa: E402
from audio_generator import (  # noqa: E402
    SILENCE_BETWEEN_SENTENCES,
    _wav_fingerprint,  # single source of truth: must match the writer's algorithm
    concatenate_wavs,
    generate_silence_wav,
    get_wav_duration,
)

# --- tunables ---------------------------------------------------------------
STRENGTH = 0.60  # fraction of each sentence's deviation-from-median removed
FLOOR_FRAC = 0.72  # artic < median*FLOOR_FRAC -> intentional drama, left as-is
ATEMPO_MIN, ATEMPO_MAX = 0.80, 1.25  # atempo safety clamp (audio-quality band)
CHANGE_EPS = 0.02  # |atempo-1| below this -> treat as no-op (skip re-encode)
ADJACENT_WARN_PCT = 18.0  # detect: WARN when a non-drama adjacent jump exceeds this
# 直す目標は報告閾値より tight でなければならない。両者が同じ (どちらも 18%) だと
# auto-tune は「18% をぎりぎり下回る」強度を選び、13-18% の段差は *狙われず* かつ
# *報告もされない*。ある回はこの帯に 5 件を残したまま「段差 2 件」と報告し、user が
# 通し視聴で「速度変化がひどい」と指摘した。tune はこちらを目標にする。
NORMALIZE_TARGET_PCT = 12.0
SIL_NOISE, SIL_MIN = "-35dB", "0.18"  # ffmpeg silencedetect params
BACKUP_DIR = "_prenorm_backup"
# Episode-level speed PROFILE baselines (detect advisory). Calibrated on shipped
# An earlier episode (single --apply, natural pacing: stdev~0.40, median~7.4 @rate0.9, min~4.5).
# An earlier episode regression that motivated this: --apply run TWICE flattened stdev 0.60->0.26
# ->0.18 ("one-note and fast"). A too-low stdev / too-high median or floor now WARN.
PROFILE_MIN_STDEV = 0.25  # stdev below this -> over-flattened (norm applied too hard/twice)
PROFILE_MAX_MEDIAN = 7.7  # median mora/s above this -> too fast overall (lower tts.rate)
PROFILE_MAX_MIN = 6.3  # slowest sentence above this -> no slow beats left (pacing gone)
# Must match audio_generator.AUDIO_CACHE_FILE. --restore reverts wav CONTENT to the
# pre-norm original behind the audio cache's back; if the current text no longer
# matches that original, leaving the cache intact lets the audio step cache-hit and
# reuse a STALE wav.
# **2026-09-06**: --restore no longer DISCARDS those entries (that re-synthesized
# even sentences whose text never changed -> Cloud is non-deterministic -> new
# misreadings). It now re-points each new-format entry's wav fingerprint at the
# restored original and leaves its synthesis-text hash alone, so the audio step's
# own text comparison still catches an earlier episode. Legacy entries (no fingerprint) are
# still dropped. See _repoint_audio_cache_to_restored.
AUDIO_CACHE_FILE = "_audio_cache.json"
# Pause/phrasing anomaly thresholds.
RUN_ON_MAX_SILENCE = 0.35  # element with a mid-element 。 but < this internal silence -> run-on
OVER_PAUSE_GAP = 1.5  # a single internal silence gap > this -> awkward mid-sentence dead-air
_DASHQUOTE = re.compile(r"[—―─━–—『』「」]")  # dash/quote markers Cloud pauses on unreliably
# A comma-isolated topic/direction particle は/へ (、は、 / 、へ。 / ...) that Cloud
# reads "ha"/"he" instead of "wa"/"e". gen_cloud_readings
# now de-isolates these at generation (は->わ / へ->え); this static check catches any
# left in a hand-edited narration_speech_cloud. Same lone-token signature = safe.
_ISOLATED_PARTICLE = re.compile(r"、[はへ](?=[、。]|$)")
# Context-DEPENDENT multi-reading kanji that Cloud tends to misread but that CANNOT
# go in cloud_tts._READING_OVERRIDES (a blanket phoneme override would break the
# other legitimate reading). Detection-only: WARN when the kanji is still present in
# the cloud reading (i.e. not yet spelled out in narration_speech_cloud), so a human
# verifies the intended reading by ear or spells it. surface -> note. Cloud-side
# analog of reading_guard's VOICEVOX 多読み sentinels (下/抱/物). Accumulate as caught.
_CONTEXT_DEPENDENT_WATCH = {
    "一行": "Cloud は いっこう と読む (3/3 実測)。文/式の『一行=いちぎょう』なら "
    "narration_speech_cloud で『いちぎょう』と spell、または耳確認",
}
_WATCH_RE = (
    re.compile(
        "|".join(re.escape(w) for w in sorted(_CONTEXT_DEPENDENT_WATCH, key=len, reverse=True))
    )
    if _CONTEXT_DEPENDENT_WATCH
    else None
)


def _mora(text: str) -> float:
    """Rough spoken-mora count: kana=1, digit=2, kanji~1.7, other=1 (punct stripped)."""
    text = re.sub(r"[。、!?.,\s]", "", text)
    s = 0.0
    for ch in text:
        o = ord(ch)
        if 0x30A0 <= o <= 0x30FF or 0x3040 <= o <= 0x309F:
            s += 1
        elif ch.isdigit():
            s += 2
        elif 0x4E00 <= o <= 0x9FFF:
            s += 1.7
        else:
            s += 1
    return s


def _silence_analysis(wav_path: str) -> tuple:
    """(total_silence_seconds, [(start,end), ...]) via one ffmpeg silencedetect pass.

    total matches the previous _silence_seconds (sum of silence_duration) so the
    articulation metric is unchanged; intervals feed the pause/phrasing checks.
    """
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-i",
                wav_path,
                "-af",
                f"silencedetect=noise={SIL_NOISE}:d={SIL_MIN}",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError) as e:
        print(f"  [WARN] silencedetect failed for {os.path.basename(wav_path)}: {e}")
        return 0.0, []
    err = r.stderr
    total = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err))
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return total, list(zip(starts, ends, strict=False))


def _internal_kuten(text: str) -> int:
    """Count 。 that are NOT the element-final char (= a sentence break mid-element)."""
    text = text.rstrip()
    return text[:-1].count("。") if text.endswith("。") else text.count("。")


def _pick_speech(scene: dict, i: int, n: int) -> str:
    """合成器と同じ文を見る。実装は speech_source (ここは薄い呼び出し)。"""
    return speech_source.pick_speech_text(scene, i, "cloud")


def _iter_scenes(scene_def: dict):
    """実装は scene_def.iter_scenes (5 か所にあった同じ走査を 1 つに)。"""
    _src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    from scene_def import iter_scenes

    yield from iter_scenes(scene_def)


def _measure(scene_def: dict, audio_dir: str) -> list:
    """Per-sentence rows: {sid,i,path,dur,speech,mora,artic,text}. Missing wavs skipped."""
    rows = []
    for scene in _iter_scenes(scene_def):
        sid = scene["scene_id"]
        narr = scene.get("narration", [])
        n = len(narr)
        for i in range(n):
            path = os.path.join(audio_dir, f"{sid}_{i + 1:03d}.wav")
            if not os.path.exists(path):
                continue
            dur = get_wav_duration(path)
            total_sil, intervals = _silence_analysis(path)
            speech = max(dur - total_sil, 0.05)
            ftext = _pick_speech(scene, i, n)
            mora = _mora(ftext)
            # internal silences only (exclude leading/trailing edge silence)
            internal = [(s, e) for s, e in intervals if s > 0.08 and e < dur - 0.08]
            _iso = _ISOLATED_PARTICLE.search(ftext)
            _wm = _WATCH_RE.search(ftext) if _WATCH_RE else None
            rows.append(
                {
                    "sid": sid,
                    "i": i,
                    "path": path,
                    "dur": dur,
                    "speech": speech,
                    "mora": mora,
                    "artic": (mora / speech) if speech > 0 else 0.0,
                    "text": ftext[:22],
                    "ik": _internal_kuten(ftext),
                    "pause_total": sum(e - s for s, e in internal),
                    "pause_maxgap": max((e - s for s, e in internal), default=0.0),
                    "has_dash": bool(_DASHQUOTE.search(ftext)),
                    # full-text context of a comma-isolated は/へ particle, else ""
                    "iso": ftext[max(0, _iso.start() - 6) : _iso.start() + 4] if _iso else "",
                    # context-dependent multi-reading kanji still present (surface), else ""
                    "watch": _wm.group(0) if _wm else "",
                }
            )
    return rows


def _plan(rows: list):
    """Annotate rows with target atempo factor F. Returns (target, floor)."""
    arts = [r["artic"] for r in rows if r["artic"] > 0]
    target = statistics.median(arts) if arts else 0.0
    floor = target * FLOOR_FRAC
    for r in rows:
        a = r["artic"]
        if a <= 0 or a < floor:
            newr = a  # protected: intentional dramatic slow line (or unmeasurable)
        else:
            newr = target + (a - target) * (1 - STRENGTH)
        f = (newr / a) if a > 0 else 1.0
        f = max(ATEMPO_MIN, min(ATEMPO_MAX, f))
        r["F"] = f
        r["change"] = abs(f - 1.0) > CHANGE_EPS
    return target, floor


def _autotune(rows: list) -> tuple[float, float]:
    """Pick the GENTLEST normalization that still removes every >ADJACENT_WARN_PCT
    adjacent jump (minimize flattening subject to the no-jump constraint), and raise
    the drama FLOOR to protect the single slowest emphasis line the default floor
    would otherwise speed up. Sets globals STRENGTH/FLOOR_FRAC and returns them.

    Rationale: the fixed STRENGTH=0.60 is calibrated for an earlier episode's raw stdev
    ~0.60; on a lower-variance episode (an earlier episode raw 0.45) it over-flattens to stdev
    0.23 ("一本調子"). Searching for the minimal jump-killing strength kept stdev at
    0.35 (an earlier episode-like) while still fixing the +25% jumps, and raising FLOOR 0.72->
    ~0.83 preserved the punch line「答えは、幾何学です。」(artic 6.14).
    """
    global STRENGTH, FLOOR_FRAC
    arts = [r["artic"] for r in rows if r["artic"] > 0]
    if len(arts) < 2:
        return STRENGTH, FLOOR_FRAC
    med = statistics.median(arts)
    raw_min = min(arts)
    # Protect the slowest line only if it is a genuine slow-emphasis line
    # (meaningfully below median) that the DEFAULT floor leaves unprotected.
    floor_frac = FLOOR_FRAC
    if med > 0 and med * FLOOR_FRAC < raw_min < med * 0.85:
        floor_frac = min(0.86, (raw_min + 0.03) / med)
    # 探索範囲は 0.60 で打ち切られていたので、目標を tight にしても届かなかった。
    for s in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80, 0.85):
        STRENGTH, FLOOR_FRAC = s, floor_frac
        _plan(rows)
        jumps = _adjacent_jumps(rows, med * floor_frac, effective=True)
        if max((abs(j[5]) for j in jumps), default=0.0) < NORMALIZE_TARGET_PCT:
            return s, floor_frac
    STRENGTH, FLOOR_FRAC = 0.85, floor_frac
    _plan(rows)
    return STRENGTH, FLOOR_FRAC


def _adjacent_jumps(rows: list, floor: float, effective: bool = False):
    """Non-drama adjacent-sentence articulation jumps, %.

    effective=False: jumps in the CURRENT audio. True: jumps after applying F.
    """
    from collections import defaultdict

    by = defaultdict(list)
    for r in rows:
        a = r["artic"] * (r["F"] if effective else 1.0)
        by[r["sid"]].append((r["i"], a, r["artic"] < floor, r["text"]))
    out = []
    for sid, lst in by.items():
        lst.sort()
        for j in range(1, len(lst)):
            if lst[j][2] or lst[j - 1][2]:
                continue  # skip transitions touching a protected drama line
            a0, a1 = lst[j - 1][1], lst[j][1]
            if a0 <= 0:
                continue
            pct = (a1 - a0) / a0 * 100
            out.append((sid, lst[j - 1][0], lst[j][0], a0, a1, pct, lst[j][3]))
    return out


def _boundary_jumps(rows: list, floor: float, effective: bool = False):
    """Articulation jumps ACROSS scene boundaries.

    `_adjacent_jumps` groups by scene, so the last sentence of one scene and the
    first of the next are never compared -- yet that seam is audible: an earlier episode
    shipped closing_02 -> closing_03 at -25% while every within-scene jump passed.

    Calibrated on 21 shipped cloud episodes / 461 boundaries: |change| is 4.8% at
    the median, 13.0% at the 90th percentile and 16.4% at the 95th. Reusing the
    within-scene threshold (18%) therefore flags ~0.7 boundaries per episode, and
    the ones it flags are the 25-31% steps. A protected drama line on either side
    is skipped, same as within a scene.

    Returns (prev_sid, next_sid, a0, a1, pct, text_of_next).
    """
    # `rows` is already in document order (_measure walks _iter_scenes and then
    # sentence index). Do NOT sort by sid: alphabetically closing_* would come
    # first and every "boundary" would be fictional.
    out = []
    for j in range(1, len(rows)):
        prev, cur = rows[j - 1], rows[j]
        if prev["sid"] == cur["sid"]:
            continue
        if prev["artic"] < floor or cur["artic"] < floor:
            continue
        a0 = prev["artic"] * (prev["F"] if effective else 1.0)
        a1 = cur["artic"] * (cur["F"] if effective else 1.0)
        if a0 <= 0:
            continue
        out.append((prev["sid"], cur["sid"], a0, a1, (a1 - a0) / a0 * 100, cur["text"]))
    return out


def _pause_anomalies(rows: list) -> list:
    """Pause/phrasing anomalies (objective, silence-measured; complements speed).

    Targets the 'unnatural pausing' class ear-caught this session:
      RUN-ON     : element has a mid-element 。 (sentence break) but almost no
                   internal silence -> clauses run together ("...ますむから").
      OVER-PAUSE : an internal silence gap far longer than natural -> dead-air.
      DASH       : narration_speech_cloud still holds ─—『』 (Cloud pauses on them
                   unreliably; convert to。/、 for a dependable pause).
      ISO-PARTICLE: a comma-isolated topic/direction particle は/へ (、は、 / 、へ。)
                   that Cloud reads ha/he instead of wa/e (spell わ/え, reattach).
      WATCH-READING: a context-dependent multi-reading kanji (一行=いちぎょう/いっこう...)
                   still present in the cloud reading -> verify by ear / spell out.
    Returns (sid, i, type, detail, text) tuples.
    """
    out = []
    for r in rows:
        if r["ik"] >= 1 and r["pause_total"] < RUN_ON_MAX_SILENCE:
            out.append(
                (
                    r["sid"],
                    r["i"],
                    "RUN-ON",
                    f"文中の。で間がほぼ無い (内部無音 {r['pause_total']:.2f}s)",
                    r["text"],
                )
            )
        if r["pause_maxgap"] > OVER_PAUSE_GAP:
            out.append(
                (
                    r["sid"],
                    r["i"],
                    "OVER-PAUSE",
                    f"文中に不自然に長い無音 {r['pause_maxgap']:.2f}s",
                    r["text"],
                )
            )
        if r["has_dash"]:
            out.append(
                (
                    r["sid"],
                    r["i"],
                    "DASH",
                    "narration_speech_cloud に ─—『』 残存 (。/、へ変換推奨)",
                    r["text"],
                )
            )
        if r["iso"]:
            out.append(
                (
                    r["sid"],
                    r["i"],
                    "ISO-PARTICLE",
                    f"孤立した助詞 は/へ (…{r['iso']}…) -> ハ/ヘ 誤読リスク (わ/え へ)",
                    r["text"],
                )
            )
        if r["watch"]:
            out.append(
                (
                    r["sid"],
                    r["i"],
                    "WATCH-READING",
                    f"多読み語『{r['watch']}』: {_CONTEXT_DEPENDENT_WATCH[r['watch']]}",
                    r["text"],
                )
            )
    return out


def _profile_checks(median: float, stdev: float, amin: float) -> list:
    """Episode-level speed-profile checks vs baseline (an earlier episode shipped calibration).

    Returns (ok, label, detail) tuples. ok=True is an [OK], False is a [WARN].
    Complements the per-sentence adjacent-jump WARN with a whole-episode view: the
    an earlier episode double --apply flattened stdev without tripping any single adjacent jump.
    """
    out = []
    out.append(
        (
            stdev >= PROFILE_MIN_STDEV,
            f"stdev>={PROFILE_MIN_STDEV:.2f}",
            f"stdev={stdev:.2f}: 緩急が乏しく一本調子。正規化のかけ過ぎ/strength過大の恐れ "
            f"(承認済み ある回は stdev~0.40)",
        )
    )
    out.append(
        (
            median <= PROFILE_MAX_MEDIAN,
            f"median<={PROFILE_MAX_MEDIAN:.1f}",
            f"median={median:.2f} mora/s: 全体的に速い。tts.rate を下げる検討 "
            f"(参考: rate0.9~median7.4, rate0.85~median7.0)",
        )
    )
    out.append(
        (
            amin <= PROFILE_MAX_MIN,
            f"min<={PROFILE_MAX_MIN:.1f}",
            f"min={amin:.2f} mora/s: 遅い山場が無く間・緩急が消えている可能性 "
            f"(承認済み ある回は min~4.5)",
        )
    )
    return out


# --- timing rebuild (mirrors audio_generator.process_scene + main arithmetic) ---
def _rebuild_timing(scene_def: dict, audio_dir: str, timing: dict) -> dict:
    """Recompute all sentence/scene/global timings from the wavs on disk.

    Only numeric timing fields are touched; text/text_clean/wav_file/pause_after/
    generation_mode are preserved from the existing timing.json.
    """
    global_offset = 0.0
    total = 0.0
    for scene in _iter_scenes(scene_def):
        sid = scene["scene_id"]
        st = timing["scenes"].get(sid)
        if st is None:
            continue
        n = len(scene.get("narration", []))
        current = 0.0
        for i in range(n):
            path = os.path.join(audio_dir, f"{sid}_{i + 1:03d}.wav")
            dur = get_wav_duration(path)
            sent = st["sentences"][i]
            sent["start"] = round(current, 3)
            sent["end"] = round(current + dur, 3)
            sent["duration"] = round(dur, 3)
            current += dur
            if i < n - 1:
                current += SILENCE_BETWEEN_SENTENCES
        pause_after = st.get("pause_after", scene.get("pause_after", 0.5))
        st["duration"] = round(current, 3)
        st["duration_with_pause"] = round(current + pause_after, 3)
        st["global_start"] = round(global_offset, 3)
        st["global_end"] = round(global_offset + st["duration"], 3)
        global_offset += st["duration_with_pause"]
        total += st["duration_with_pause"]
    timing["total_duration"] = round(total, 3)
    timing["total_duration_minutes"] = round(total / 60, 2)
    return timing


def _reconcat_scene(scene: dict, audio_dir: str) -> None:
    """Re-concatenate {sid}.wav from its sentence wavs + 0.8s silence gaps."""
    sid = scene["scene_id"]
    n = len(scene.get("narration", []))
    segments = []
    silence_temps = []
    for i in range(n):
        segments.append(os.path.join(audio_dir, f"{sid}_{i + 1:03d}.wav"))
        if i < n - 1:
            sil = os.path.join(audio_dir, f"{sid}_silence_{i + 1:03d}.wav")
            generate_silence_wav(sil, SILENCE_BETWEEN_SENTENCES)
            segments.append(sil)
            silence_temps.append(sil)
    concatenate_wavs(segments, os.path.join(audio_dir, f"{sid}.wav"))
    for sil in silence_temps:
        if os.path.exists(sil):
            os.remove(sil)


def _atempo(src: str, factor: float) -> None:
    """Time-stretch src in place by `factor` (pitch-preserving), keeping wav format."""
    tmp = src + ".tmp.wav"
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src,
            "-filter:a",
            f"atempo={factor:.4f}",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            tmp,
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not os.path.exists(tmp):
        raise RuntimeError(f"atempo failed for {os.path.basename(src)}: {r.stderr[-200:]}")
    os.replace(tmp, src)


# --- commands ---------------------------------------------------------------
def cmd_detect(scene_def, audio_dir, report_path, strict) -> int:
    rows = _measure(scene_def, audio_dir)
    if not rows:
        print("[SPEED-QA] SKIP: no sentence wavs found.")
        return 0
    target, floor = _plan(rows)
    jumps = _adjacent_jumps(rows, floor)
    bjumps = _boundary_jumps(rows, floor)
    arts = [r["artic"] for r in rows]
    warn = [j for j in jumps if abs(j[5]) > ADJACENT_WARN_PCT]
    bwarn = [j for j in bjumps if abs(j[4]) > ADJACENT_WARN_PCT]
    pauses = _pause_anomalies(rows)
    stdev = statistics.pstdev(arts)
    amin, amax = min(arts), max(arts)
    profile = _profile_checks(target, stdev, amin)
    profile_warn = [pc for pc in profile if not pc[0]]

    print("=" * 60)
    print("  Cloud TTS speed QA (articulation consistency)")
    print("=" * 60)
    print(
        f"  N={len(rows)}  median={target:.2f} mora/s  stdev={stdev:.2f}"
        f"  min={amin:.2f} max={amax:.2f}"
    )

    lines = ["Cloud TTS articulation (mora / speech-time excl. silence), by scene:\n"]
    from collections import defaultdict

    by = defaultdict(list)
    for r in rows:
        by[r["sid"]].append(r)
    for sid, lst in by.items():
        lines.append(f"===== {sid} =====")
        for r in sorted(lst, key=lambda r: r["i"]):
            drama = " [drama-protected]" if r["artic"] < floor else ""
            lines.append(f'  [{r["i"] + 1}] {r["artic"]:.2f} mora/s{drama}  "{r["text"]}"')
    lines.append("\nNon-drama adjacent jumps (largest first):")
    for sid, i0, i1, a0, a1, pct, _txt in sorted(jumps, key=lambda j: -abs(j[5]))[:15]:
        flag = "  <-- WARN" if abs(pct) > ADJACENT_WARN_PCT else ""
        lines.append(f"  {sid}[{i0 + 1}->{i1 + 1}] {a0:.2f}->{a1:.2f}  {pct:+.0f}%{flag}")
    lines.append("\nSpeed profile (episode-level vs an earlier episode baseline):")
    lines.append(f"  median={target:.2f} mora/s  stdev={stdev:.2f}  min={amin:.2f}  max={amax:.2f}")
    for ok, label, detail in profile:
        lines.append(f"  [{'OK' if ok else 'WARN'}] {label}  ({detail})")
    lines.append("\nPause/phrasing anomalies:")
    if pauses:
        for sid, i, typ, detail, _txt in pauses:
            lines.append(f"  {sid}[{i + 1}] {typ}: {detail}")
    else:
        lines.append("  (none)")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  Report: {report_path}")
    except OSError as e:
        print(f"  [WARN] could not write report: {e}")

    if warn:
        n_fix = sum(1 for r in rows if r["change"])
        print(f"\n  [WARN] {len(warn)} abrupt speed change(s) > {ADJACENT_WARN_PCT:.0f}%:")
        for sid, i0, i1, _a0, _a1, pct, txt in sorted(warn, key=lambda j: -abs(j[5])):
            print(f'      {sid}[{i0 + 1}->{i1 + 1}] {pct:+.0f}%  "{txt}"')
        print(
            f"  Fix: re-run the build with --normalize-cloud-speed "
            f"(would atempo {n_fix} sentence(s))."
        )
    if bwarn:
        print(
            f"\n  [WARN] {len(bwarn)} abrupt speed change(s) ACROSS scene boundaries "
            f"> {ADJACENT_WARN_PCT:.0f}%:"
        )
        for s0, s1, _a0, _a1, pct, txt in sorted(bwarn, key=lambda j: -abs(j[4])):
            print(f'      {s0} -> {s1} {pct:+.0f}%  "{txt[:34]}"')
        print(
            "  シーンの切れ目は速度がリセットされて自然な場所ですが、この幅は聞こえます。"
            "--normalize-cloud-speed で均すか、境界の文を録り直してください。"
        )
    else:
        print("  [OK] no abrupt non-drama speed changes.")

    if pauses:
        print(f"\n  [WARN] {len(pauses)} pause/phrasing anomaly(ies):")
        for sid, i, typ, detail, txt in pauses:
            print(f'      {sid}[{i + 1}] {typ}: {detail}  "{txt}"')
    else:
        print("  [OK] no pause/phrasing anomalies.")

    if profile_warn:
        print(f"\n  [WARN] {len(profile_warn)} speed-profile deviation(s) vs an earlier episode baseline:")
        for _ok, label, detail in profile_warn:
            print(f"      {label}: {detail}")
    else:
        print("  [OK] speed profile within an earlier episode baseline (stdev/median/min).")
    print("  NOTE: measurement is heuristic -- spot-check by ear before publishing.")
    # leave a machine-readable verdict beside the report so
    # pipeline.verify_outputs can tell "never normalized" from "normalization not
    # needed". The bare `_prenorm_backup/` existence test warned on every cloud
    # episode, including ones this detector had just measured as step-free, so the
    # operator had to re-run the detector by hand each build to dismiss it.
    try:
        with open(
            os.path.join(os.path.dirname(report_path), "_speed_qa_verdict.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                {
                    "adjacent_jumps": len(warn),
                    "boundary_jumps": len(bwarn),
                    "threshold_pct": ADJACENT_WARN_PCT,
                    "median": round(target, 2),
                    "stdev": round(stdev, 2),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass

    _n_adv = len(warn) + len(bwarn) + len(pauses) + len(profile_warn)
    if _n_adv > 0:
        try:
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("cloud_speed_qa", _n_adv)
        except Exception:
            pass
    return 1 if ((warn or bwarn or pauses or profile_warn) and strict) else 0


_SENTENCE_WAV_RE = re.compile(r".+_\d{3}\.wav$")


def _backup_is_stale(audio_dir: str, backup: str) -> bool:
    """A _prenorm_backup/ is stale when the audio was (re)synthesized AFTER the last
    normalization -- e.g. --force-regen-audio, or a build stopped mid-normalize that
    left an orphan backup while a LATER build re-synthesized the wavs. cmd_apply touches
    a '.applied' marker when a normalization completes; if ANY wav in audio_dir is newer
    than that marker, the current audio is fresh (un-normalized) and MUST be re-normalized
    rather than skipped (an earlier episode: the skip-guard shipped un-normalized audio, stdev
    0.34->0.52). We scan ALL wavs, not only backed-up ones: an earlier episode surgically re-synth'd a
    sentence that had been WITHIN band at the prior apply (so it was never atempo'd/backed
    up); checking only the backup missed it and SKIPped, shipping it un-normalized. A
    backup with no marker predates this guard -> treat as stale (safe: re-normalize)."""
    marker = os.path.join(backup, ".applied")
    if not os.path.exists(marker):
        return True
    m = os.path.getmtime(marker)
    # Scan ALL wavs in audio_dir, not just the backed-up (previously-atempo'd) ones.
    # A surgical re-synth of a sentence that was WITHIN band at the last apply is not
    # in the backup, so scanning only the backup missed it -> SKIP -> shipped it
    # un-normalized. cmd_apply writes the marker
    # LAST (after atempo + re-concat), so every wav it touched is older than the marker;
    # only a re-synth AFTER this apply produces a wav newer than the marker.
    # ある回 (再検証で発覚): scene 単位の連結 wav (<sid>.wav) は audio ステップがキャッシュ命中でも
    # 毎回書き直すので、それを見ると「再合成された」と誤認して **一文も変えていないのに全体を
    # 掛け直す** (verify run で 62 文が再 atempo され、出荷済み動画と disk の音声がずれた)。
    # 見るのは文 wav (<sid>_NNN.wav) だけ。
    for name in os.listdir(audio_dir):
        if not _SENTENCE_WAV_RE.match(name):
            continue
        p = os.path.join(audio_dir, name)
        if os.path.isfile(p) and os.path.getmtime(p) > m + 1.0:
            return True
    return False


def _revert_untouched_from_backup(audio_dir: str, backup: str) -> int:
    """Put back the pre-normalization originals of sentences NOT re-synthesized since.

    A stale backup means "some audio changed after the last normalization". The old
    behaviour simply dropped the backup and normalized whatever was on disk -- but the
    sentences that did NOT change still hold the PREVIOUS atempo, so they get
    compressed toward the median a second time (an earlier episode: the only way to avoid it was to
    run --restore by hand before every partial rebuild).

    A blanket restore is not the answer either: a sentence re-synthesized from edited
    text must keep its NEW audio, and copying the backup over it would resurrect the
    old wording. So revert exactly the
    sentences whose live wav is older than the marker -- those are the ones still
    carrying the previous normalization -- and leave anything newer alone.

    **戻り値は {sent_key: 戻した wav のパス}** (2026-09-06 に件数から変更)。呼び出し側が
    キャッシュをその原本へ向け直せるようにするため ── ここは wav を **キャッシュの
    背後で** 差し替えるので、向け直さないと次の audio ステップが指紋の不一致を見て
    **テキストを一文字も変えていない文まで再合成する**。Cloud TTS は非決定的なので
    その再合成は新しいテイク = 新しい誤読の機会になる。`--restore` 側で同じ欠陥を
    直したときにこちらを見ておらず、後から実測で再現して気づいた。

    apply の後段 `_refresh_audio_cache_wav_fp` は **atempo をかけた文だけ** を更新するので、
    「戻したが今回は正規化されなかった」文 (係数が 1 に近い / ドラマ的に遅い) が
    取り残される。そこがこの欠陥の通り道だった。
    """
    marker = os.path.join(backup, ".applied")
    if not os.path.exists(marker):
        return {}  # legacy backup: cannot tell what is what, leave the audio as-is
    m = os.path.getmtime(marker)
    reverted = {}
    for base in os.listdir(backup):
        if not base.endswith(".wav"):
            continue
        live = os.path.join(audio_dir, base)
        if not os.path.isfile(live):
            continue
        if os.path.getmtime(live) > m + 1.0:
            continue  # re-synthesized after the last apply: already an original
        shutil.copy2(os.path.join(backup, base), live)
        reverted[base[:-4]] = live
    return reverted


PLAN_FILE = "plan.json"  # _prenorm_backup/plan.json: 初回正規化の target/strength/floor と係数


def _factor_for(artic: float, target: float, strength: float, floor_frac: float) -> float:
    """1 文の atempo 係数を、保存済みの target/strength/floor から決める (_plan と同じ式)。"""
    a = artic
    floor = target * floor_frac
    if a <= 0 or a < floor:
        newr = a
    else:
        newr = target + (a - target) * (1 - strength)
    f = (newr / a) if a > 0 else 1.0
    return max(ATEMPO_MIN, min(ATEMPO_MAX, f))


def _save_plan(backup: str, rows: list, target: float, strength: float, floor_frac: float) -> None:
    plan = {
        "target": target,
        "strength": strength,
        "floor_frac": floor_frac,
        "sentences": {
            os.path.basename(r["path"])[:-4]: {"F": r["F"], "artic": r["artic"]} for r in rows
        },
    }
    with open(os.path.join(backup, PLAN_FILE), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)


def _load_plan(backup: str) -> dict | None:
    path = os.path.join(backup, PLAN_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            plan = json.load(f)
        if not all(k in plan for k in ("target", "strength", "floor_frac", "sentences")):
            return None
        return plan
    except (OSError, ValueError):
        return None


def _apply_incremental(scene_def, audio_dir, timing_path, backup: str, plan: dict) -> int:
    """再合成された文**だけ**を、初回正規化の係数 (target/strength/floor) で均す。

    従来は stale backup を見ると、未編集の文を原本に戻して episode 全体を測り直し、
    autotune をやり直して全文に atempo を掛け直していた。target と strength が少し動くので
    **一文も編集していない 61 文の wav まで変わり**、visual cache が全 scene を再レンダ
    (24 分)、レビューリールは「全 scene 変更」で作れなかった (ある回: 1 文の修正で 61 分)。

    初回の target/strength/floor を `plan.json` に保存しておき、以後の再合成分はその
    係数で個別に均す。未編集の文は byte 単位で不変 = visual cache が効き、部分再ビルドは
    数分、未変更区間の同一性証明が成り立つ。段差が残れば後段の speed_qa が報告する
    (係数を固定した代償として許容。全体を均し直したいときは --restore してから --apply)。
    """
    marker = os.path.join(backup, ".applied")
    m = os.path.getmtime(marker) if os.path.exists(marker) else 0.0
    rows = _measure(scene_def, audio_dir)
    fresh = [r for r in rows if os.path.getmtime(r["path"]) > m + 1.0]
    target, strength, floor_frac = plan["target"], plan["strength"], plan["floor_frac"]
    print("=" * 60)
    print(
        f"  Cloud speed normalization (incremental): 再合成 {len(fresh)}/{len(rows)} 文を "
        f"初回の係数 (target={target:.2f} mora/s, strength={strength:.2f}, floor={floor_frac:.2f}) で均す。"
        "未編集の文には触らない。"
    )
    print("=" * 60)
    changed = []
    for r in fresh:
        r["F"] = _factor_for(r["artic"], target, strength, floor_frac)
        r["change"] = abs(r["F"] - 1.0) > CHANGE_EPS
        base = os.path.basename(r["path"])
        dst = os.path.join(backup, base)
        key = base[:-4]
        if r["change"]:
            shutil.copy2(r["path"], dst)  # 新しい原本で上書き (古いテイクを --restore が蘇らせない)
            _atempo(r["path"], r["F"])
            changed.append(r)
            arrow = "SLOW" if r["F"] < 1 else "FAST"
            print(
                f"  {base} {arrow} atempo={r['F']:.3f}  ({r['artic']:.2f}->{r['artic'] * r['F']:.2f} mora/s)"
            )
        else:
            if os.path.exists(dst):
                os.remove(
                    dst
                )  # 掛けなかった文の古い原本は残さない (--restore で古いテイクに戻さない)
            print(f"  {base} keep (atempo={r['F']:.3f}, within band)")
        plan["sentences"][key] = {"F": r["F"], "artic": r["artic"]}
    with open(os.path.join(backup, PLAN_FILE), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)

    if changed:
        _refresh_audio_cache_wav_fp(
            audio_dir, {os.path.basename(r["path"])[:-4]: r["path"] for r in changed}
        )
    # 再合成された scene は (atempo の有無に関わらず) 尺が変わっているので繋ぎ直す。
    fresh_sids = {r["sid"] for r in fresh}
    for scene in _iter_scenes(scene_def):
        if scene["scene_id"] in fresh_sids:
            _reconcat_scene(scene, audio_dir)
    with open(timing_path, encoding="utf-8") as f:
        timing = json.load(f)
    timing = _rebuild_timing(scene_def, audio_dir, timing)
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)
    print(
        f"\n  atempo {len(changed)} 文 / 再繋ぎ {len(fresh_sids)} scene; timing.json rebuilt "
        f"(total={timing['total_duration_minutes']:.2f} min)。未編集の {len(rows) - len(fresh)} 文は不変。"
    )
    try:
        open(marker, "w").close()
    except OSError:
        pass
    return 0


def cmd_apply(scene_def, audio_dir, timing_path, force=False, strength=None) -> int:
    # Double-normalization guard: an existing _prenorm_backup/ means a previous
    # --apply already normalized these wavs. Re-normalizing atempo-compresses toward
    # the median a SECOND time and crushes the intonation. Skip (benign, exit 0) unless --force so the
    # pipeline's --normalize-cloud-speed never stacks on a prior --apply -- a benign
    # skip keeps the build going with the already-normalized audio (real errors still
    # return non-zero). To genuinely re-normalize, --restore first, then --apply.
    # An earlier episode: BUT only skip when the backup is CURRENT. A stopped build / --force-regen
    # can leave a stale backup while the audio is freshly re-synthesized; skipping then
    # ships UN-normalized audio. _backup_is_stale detects that and re-normalizes.
    backup = os.path.join(audio_dir, BACKUP_DIR)
    if os.path.isdir(backup) and not force:
        if _backup_is_stale(audio_dir, backup):
            # ある回: 初回の係数が plan.json に残っていれば、再合成分だけを増分で均す
            # (未編集の文は不変 = visual cache が効く)。plan 無しの旧 backup は従来経路。
            plan = _load_plan(backup)
            if plan is not None and os.path.exists(os.path.join(backup, ".applied")):
                return _apply_incremental(scene_def, audio_dir, timing_path, backup, plan)
            reverted = _revert_untouched_from_backup(audio_dir, backup)
            # 戻した wav へキャッシュを向け直す。ここを飛ばすと、戻したのに今回は
            # 正規化されなかった文 (後段の _refresh_audio_cache_wav_fp は atempo を
            # かけた文しか更新しない) が指紋不一致のまま残り、**テキスト未編集なのに
            # 次の audio ステップで引き直される** (2026-09-06 に実測で再現して修正)。
            _repoint_audio_cache_to_restored(audio_dir, reverted)
            print(
                "[SPEED-NORM] stale backup を検出 (前回正規化後に音声が再合成された、"
                "または marker 無しの旧 backup)。作り直して現在の音声を正規化する。"
            )
            if reverted:
                print(
                    f"  再合成されていない {len(reverted)} 文を正規化前の原本に戻してから掛け直す "
                    "(二重の atempo で緩急が潰れるのを防ぐ)。再合成済みの文は新しい音声のまま。"
                )
            shutil.rmtree(backup, ignore_errors=True)
        else:
            print(
                f"[SPEED-NORM] SKIP: 既に正規化済み ({backup} が存在)。二重掛けは緩急を潰すため"
                "スキップした。\n  かけ直すには先に --restore で原本に戻すこと (強制は --force)。"
            )
            return 0

    global STRENGTH, FLOOR_FRAC
    rows = _measure(scene_def, audio_dir)
    if not rows:
        print("[SPEED-NORM] SKIP: no sentence wavs found.")
        return 0
    # Strength selection: auto-tune (default) picks the gentlest jump-killing
    # strength so a low-variance episode is not over-flattened. --strength FLOAT forces a fixed value.
    if strength is None:
        s_used, fl_used = _autotune(rows)
        tune = f"auto strength={s_used:.2f} floor={fl_used:.2f}"
    else:
        STRENGTH, FLOOR_FRAC = strength, FLOOR_FRAC
        tune = f"fixed strength={STRENGTH:.2f} floor={FLOOR_FRAC:.2f}"
    target, floor = _plan(rows)
    changed = [r for r in rows if r["change"]]
    if not changed:
        print("[SPEED-NORM] nothing to do (already within band).")
        return 0

    os.makedirs(backup, exist_ok=True)
    changed_sids = set()
    print("=" * 60)
    print(
        f"  Cloud speed normalization: atempo {len(changed)}/{len(rows)} sentences "
        f"(target={target:.2f} mora/s, {tune})"
    )
    print("=" * 60)
    for r in changed:
        base = os.path.basename(r["path"])
        dst = os.path.join(backup, base)
        if not os.path.exists(dst):
            shutil.copy2(r["path"], dst)  # keep the ORIGINAL only (idempotent re-runs)
        _atempo(r["path"], r["F"])
        changed_sids.add(r["sid"])
        arrow = "SLOW" if r["F"] < 1 else "FAST"
        print(
            f"  {base} {arrow} atempo={r['F']:.3f}  ({r['artic']:.2f}->"
            f"{r['artic'] * r['F']:.2f} mora/s)"
        )

    # The atempo overwrote each changed wav in place, so its cached fingerprint is
    # now stale. Bless the normalized wavs in the audio cache so a later audio step
    # reuses them instead of re-synthesizing (which would undo the normalization).
    _refresh_audio_cache_wav_fp(
        audio_dir, {os.path.basename(r["path"])[:-4]: r["path"] for r in changed}
    )

    # Re-concat only the scenes whose sentences changed; retime the whole episode
    # (global offsets cascade downstream from any duration change).
    for scene in _iter_scenes(scene_def):
        if scene["scene_id"] in changed_sids:
            _reconcat_scene(scene, audio_dir)
    with open(timing_path, encoding="utf-8") as f:
        timing = json.load(f)
    timing = _rebuild_timing(scene_def, audio_dir, timing)
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)
    print(
        f"\n  Re-concatenated {len(changed_sids)} scene wav(s); timing.json rebuilt "
        f"(total={timing['total_duration_minutes']:.2f} min)."
    )
    print(f"  Originals backed up in {backup} (undo with --restore).")
    # ある回: 初回の係数を残す。以後の再合成分は _apply_incremental がこの係数で均す。
    _save_plan(backup, rows, target, STRENGTH, FLOOR_FRAC)
    # An earlier episode: mark normalization completion. _backup_is_stale compares live wav mtimes
    # against this marker to detect audio re-synthesized after this point (stale backup).
    try:
        open(os.path.join(backup, ".applied"), "w").close()
    except OSError:
        pass
    return 0


def cmd_verify_timing(scene_def, audio_dir, timing_path) -> int:
    """Self-test: recompute timing from current wavs (no atempo), diff vs existing."""
    with open(timing_path, encoding="utf-8") as f:
        original = json.load(f)
    recomputed = _rebuild_timing(scene_def, audio_dir, json.loads(json.dumps(original)))
    max_delta = 0.0
    where = ""
    for scene in _iter_scenes(scene_def):
        sid = scene["scene_id"]
        o = original["scenes"].get(sid)
        r = recomputed["scenes"].get(sid)
        if not o or not r:
            continue
        for key in ("duration", "duration_with_pause", "global_start", "global_end"):
            d = abs(o.get(key, 0) - r.get(key, 0))
            if d > max_delta:
                max_delta, where = d, f"{sid}.{key}"
        for so, sr in zip(o["sentences"], r["sentences"], strict=False):
            for key in ("start", "end", "duration"):
                d = abs(so.get(key, 0) - sr.get(key, 0))
                if d > max_delta:
                    max_delta, where = d, f"{sid}.s{so.get('index')}.{key}"
    td = abs(original.get("total_duration", 0) - recomputed.get("total_duration", 0))
    max_delta = max(max_delta, td)
    print(
        f"[VERIFY-TIMING] max delta = {max_delta:.4f}s (at {where or 'total'}); "
        f"total_duration delta = {td:.4f}s"
    )
    if max_delta <= 0.002:
        print("  [OK] timing arithmetic reproduces audio_generator exactly.")
        return 0
    print("  [WARN] timing recompute diverges -- investigate before using --apply.")
    return 1


def _repoint_audio_cache_to_restored(audio_dir: str, key_to_wav: dict) -> None:
    """--restore で wav を pre-norm 原本に戻したあと、キャッシュをその原本に向け直す。

    **なぜ「捨てる」ではなく「向け直す」なのか** (2026-09-06):
    従来は復元した文のキャッシュ項目を丸ごと削除していた。安全側ではあるが、
    **テキストを一文字も変えていない文まで再合成させる**。Cloud TTS は非決定的
    なので、その再合成は新しいテイクを引く = **新しい誤読が入る機会**になる。
    ある回では 1 文の修正で 39 文が対象になり、実際に引き直した 1 文が「臨安」を
    「リンガン」と読むテイクを引いた (出荷前に STT で捕まえた)。

    **ある回のバグを復活させない理由**: ここでは `text` (合成テキストのハッシュ) に
    触らない。刻まれているのは *その wav を作ったときのテキスト* のハッシュであり、
    次の audio ステップは **現在のテキスト** から計算し直したハッシュと突き合わせる。

      - テキストが編集されていれば   -> ハッシュ不一致 -> 再合成 (ある回は防がれたまま)
      - テキストが変わっていなければ -> 一致 + 指紋一致 -> 原本を再利用 (引き直さない)

    `--apply` 側の `_refresh_audio_cache_wav_fp` と対称の操作である。

    **旧形式 (ハッシュ文字列だけの項目) は従来どおり破棄する** —— 指紋の欄が無い
    ので「wav が差し替わった」ことを次段が検出できず、向け直すと stale な wav を
    再利用させてしまう (それが ある回そのもの)。
    """
    path = os.path.join(audio_dir, AUDIO_CACHE_FILE)
    if not os.path.exists(path):
        return
    if not key_to_wav:
        return
    try:
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        if not isinstance(cache, dict):
            raise ValueError("unexpected audio-cache shape")
        repointed = dropped = 0
        for key, wav in key_to_wav.items():
            entry = cache.get(key)
            if entry is None:
                continue
            if isinstance(entry, dict):
                entry["wav"] = _wav_fingerprint(wav)
                repointed += 1
            else:  # legacy: bare hash string, no fingerprint -> must not be trusted
                cache.pop(key, None)
                dropped += 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        if repointed:
            print(
                f"[RESTORE] re-pointed {repointed} audio-cache entr"
                f"{'y' if repointed == 1 else 'ies'} at the restored wav "
                "(text unchanged -> reused, not re-synthesized)."
            )
        if dropped:
            print(
                f"[RESTORE] dropped {dropped} legacy cache entr"
                f"{'y' if dropped == 1 else 'ies'} (no fingerprint -> re-synthesize)."
            )
    except (OSError, ValueError, json.JSONDecodeError):
        # 判断できないときは丸ごと捨てる (cold cache は安全。全部合成し直すだけ)。
        try:
            os.remove(path)
            print("[RESTORE] audio cache unreadable; removed it entirely (safe cold cache).")
        except OSError:
            pass


def _refresh_audio_cache_wav_fp(audio_dir: str, key_to_wav: dict) -> None:
    """After --apply overwrites sentence wavs in place, the audio cache still holds
    the fingerprint of each PRE-norm wav. Left stale, the next audio step's reuse
    check would see a fingerprint mismatch and re-synthesize -- undoing the
    normalization. Refresh each affected NEW-format entry's wav fingerprint (its
    synthesis-text hash is unchanged) so the reuse check accepts the normalized
    wav. Legacy string entries carry no fingerprint (old behavior; nothing to do).
    Best-effort: any cache trouble never fails the normalization."""
    path = os.path.join(audio_dir, AUDIO_CACHE_FILE)
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        if not isinstance(cache, dict):
            return
        n = 0
        for key, wav in key_to_wav.items():
            entry = cache.get(key)
            if isinstance(entry, dict):  # new-format entry -> refresh its fingerprint
                entry["wav"] = _wav_fingerprint(wav)
                n += 1
        if n:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            print(
                f"[SPEED-NORM] refreshed {n} audio-cache wav fingerprint(s) "
                "(normalized wavs will be reused, not re-synthesized)."
            )
    except (OSError, json.JSONDecodeError) as e:
        print(
            f"  [WARN] audio-cache fingerprint refresh skipped ({e}); "
            "a later audio step may re-synthesize normalized sentences."
        )


def cmd_restore(audio_dir) -> int:
    backup = os.path.join(audio_dir, BACKUP_DIR)
    if not os.path.isdir(backup):
        print(f"[RESTORE] no backup dir at {backup}; nothing to restore.")
        return 0
    n = 0
    restored = {}
    for base in os.listdir(backup):
        if base.endswith(".wav"):
            dst = os.path.join(audio_dir, base)
            shutil.copy2(os.path.join(backup, base), dst)
            restored[base[:-4]] = dst  # sent_key = "<scene>_<NNN>" (filename minus .wav)
            n += 1
    # Point the audio cache at the restored originals instead of discarding it.
    # The stored synthesis-text hash is left untouched, so the next audio step still
    # re-synthesizes anything whose TEXT changed while reusing the accepted
    # take for everything untouched (no non-deterministic re-roll). Legacy entries
    # without a fingerprint are dropped as before. See the function's docstring.
    _repoint_audio_cache_to_restored(audio_dir, restored)
    print(f"[RESTORE] restored {n} original sentence wav(s) from {backup}.")
    # An earlier episode: consume the backup after restoring. Leaving it (with its '.applied' marker)
    # would make a later --apply see the restored (un-normalized, old-mtime) wavs as
    # "not stale" and skip -- shipping un-normalized audio. A fresh --apply recreates it.
    shutil.rmtree(backup, ignore_errors=True)
    print(
        "  Re-run the audio step (or --steps subtitles,visuals,assemble,bgm after a "
        "re-concat) to rebuild scene wavs + timing."
    )
    return n and 0


def main() -> int:
    p = argparse.ArgumentParser(description="Cloud TTS speed QA + atempo normalization")
    p.add_argument("scene_json", help="Path to scene_definition.json")
    p.add_argument(
        "--audio-dir",
        default=None,
        help="Directory with {scene_id}[_NNN].wav (default: <scene dir>/audio)",
    )
    p.add_argument(
        "--timing", default=None, help="Path to timing.json (default: <scene dir>/timing.json)"
    )
    p.add_argument(
        "--report",
        default=None,
        help="detect report path (default: <scene dir>/speed_qa_report.txt)",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="atempo-normalize (opt-in fix)")
    mode.add_argument(
        "--verify-timing",
        action="store_true",
        help="self-test: recompute timing from wavs, diff vs timing.json",
    )
    mode.add_argument(
        "--restore", action="store_true", help="restore original wavs from _prenorm_backup/"
    )
    p.add_argument("--strict", action="store_true", help="detect: exit 1 on WARN")
    p.add_argument(
        "--force",
        action="store_true",
        help="--apply: bypass the already-normalized guard (emergency escape)",
    )
    p.add_argument(
        "--strength",
        type=float,
        default=None,
        help="--apply: force a fixed atempo strength (0-1). Default: auto-tune "
        "(gentlest strength that removes all >18%% jumps; avoids over-flattening).",
    )
    args = p.parse_args()

    scene_dir = os.path.dirname(os.path.abspath(args.scene_json))
    audio_dir = args.audio_dir or os.path.join(scene_dir, "audio")
    timing_path = args.timing or os.path.join(scene_dir, "timing.json")
    report_path = args.report or os.path.join(scene_dir, "speed_qa_report.txt")

    if args.restore:
        return cmd_restore(audio_dir)
    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)
    if args.verify_timing:
        return cmd_verify_timing(scene_def, audio_dir, timing_path)
    if args.apply:
        if not os.path.exists(timing_path):
            print(f"[SPEED-NORM] ERROR: timing.json not found: {timing_path}")
            return 1
        rc = cmd_apply(scene_def, audio_dir, timing_path, force=args.force, strength=args.strength)
        if rc == 0:
            # ある回: --apply の後に判定 sidecar (_speed_qa_verdict.json) を更新しないと、
            # 手で正規化した回で古い段差数が残り、pipeline の自動再正規化 (backup あり AND
            # 段差あり) と verify_outputs が正規化前の判定を読む。掛けた直後に
            # 再測定して report と sidecar を正規化後の値にする。
            print("\n[SPEED-NORM] 正規化後の再測定 (speed_qa_report / verdict を更新):")
            cmd_detect(scene_def, audio_dir, report_path, False)
        return rc
    return cmd_detect(scene_def, audio_dir, report_path, args.strict)


if __name__ == "__main__":
    sys.exit(main())
