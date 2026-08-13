"""
pipeline.py - Run the full video generation pipeline with a single command

Usage:
    python pipeline.py examples/moriarty/episode_config.json
    python pipeline.py examples/moriarty/episode_config.json --skip-script
    python pipeline.py examples/moriarty/episode_config.json --skip-manim --skip-images
    python pipeline.py examples/moriarty/episode_config.json --steps audio,subtitles,visuals,assemble

Partial rebuild (single scene):
    python pipeline.py examples/moriarty/episode_config.json --rebuild-scene math_02

Pipeline steps:
    1. script    - Generate scene_definition.json from episode_config (Gemini API)
    2. audio     - Generate narration audio (VOICEVOX)
    3. subtitles - Generate SRT + drawtext from timing.json
    4. images    - Generate missing images (Gemini API)
    4.5 thumbnail - Generate YouTube thumbnails (3 patterns)
    5. visuals   - Generate visual segments (Ken Burns, text, Manim)
    6. assemble  - Assemble final video (FFmpeg)
    7. credits   - Generate YouTube description text
    8. bgm       - Mix BGM + intro pause + outro fade → output_final.mp4

Output: {episode_dir}/output.mp4 (without BGM), output_final.mp4 (with BGM)
"""

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pipeline_log
import pipeline_progress

# Ensure subprocesses use UTF-8 output (avoid cp932 crashes on Windows)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _set_keep_awake(on: bool) -> None:
    """Prevent (on) / allow (off) system sleep for the lifetime of a build.

    Windows-only (SetThreadExecutionState). a multi-hour build run
    overnight was silently killed when the machine slept: progress
    was left status='running' with a now-dead pid, and the operator only found
    out by inspecting processes. Holding ES_SYSTEM_REQUIRED for the run
    prevents that. No-op on other platforms / if the call is unavailable.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        flags = (ES_CONTINUOUS | ES_SYSTEM_REQUIRED) if on else ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception:
        pass  # best-effort: never let power management break a build


ALL_STEPS = [
    "script",
    "audio",
    "subtitles",
    "photos",
    "images",
    "thumbnail",
    "visuals",
    "assemble",
    "credits",
    "bgm",
]

# steps that invoke the Claude CLI (directly or via a QA sub-step) and would
# fail SILENTLY if the logged-in OAuth session expired. The startup auth preflight
# runs whenever ANY of these is in the requested steps (not just "script"):
#   script  -> pre-script fact check + reference review + script gen + QA gate
#   images  -> image-narration Vision QA (qa_image_checker.py)
#   thumbnail-> thumbnail Vision QA (qa_thumbnail_vision.py)
#   visuals -> Manim Vision QA (manim_vision_qa.py)
#   credits -> intro-semantic review
# audio/subtitles/photos/assemble/bgm never call Claude (pure mechanical rebuilds
# of just those skip the probe).
CLAUDE_DEPENDENT_STEPS = frozenset({"script", "images", "thumbnail", "visuals", "credits"})

# Output filenames
# Why: prior layout wrote output.mp4 from assemble, then overwrote into output_final.mp4
# from bgm. A failed bgm step left a stale output_final.mp4 from the previous run,
# which was indistinguishable from a fresh successful build. Splitting the names
# makes "output_final.mp4 exists" mean "the full pipeline finished".
OUTPUT_ASSEMBLED = "output_assembled.mp4"
OUTPUT_FINAL = "output_final.mp4"

# Required sections in description.txt
_DESCRIPTION_REQUIRED_SECTIONS = [
    "【音声合成】",
    "【BGM】",
    "【映像素材】",
    "【画像クレジット】",
    "【主要参考文献】",
]


def _probe_mp4_duration(path: str) -> float | None:
    """ffprobe で mp4 の duration を取得。読めない (moov atom 欠落等) なら None。

    output_final.mp4 の破損 (部分書き込み / moov 欠落) を verify 段で検出。
    bgm_mixer 側の atomic write が主防御だが、partial rebuild / 外部中断に備え
    pipeline 側でも独立に健全性を確認する layered defense。
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def _visual_staleness_preflight(episode_dir: str, timing_json: str) -> list:
    """assemble 直前に visual mp4 の尺を timing.json の scene 尺と照合し、
    timing 刷新後に再 render されなかった stale visual を検出する。

    真因: 読み上げ速度変更で timing.json が刷新されたのに visuals の
    部分 render が一部 scene を旧尺のまま残し、assemble が新音声と旧尺 visual を
    黙って合成 -> 音声/字幕/映像が desync。視覚 (映像) と timing は別 artifact なので
    片方だけ更新されると静かにズレる。visual_generator は scene の narration 尺
    (timing scene['duration']) に合わせて render するので、両者が許容を超えてズレて
    いれば「その visual は別の timing で焼かれた = stale」と判定できる (fail fast)。

    Returns: [{scene_id, visual_dur, expected, drift, reason}] (空なら健全)。
    許容は max(1.0s, 3%) -- render 丸めは <0.5s、速度変更は ~10% ズレるので確実に弁別。
    """
    stale = []
    try:
        with open(timing_json, encoding="utf-8") as f:
            timing = json.load(f)
    except Exception as e:
        print(f"  timing.json を読めず staleness check skip: {e}")
        return stale
    visuals_dir = os.path.join(episode_dir, "visuals")
    for scene_id, sc in timing.get("scenes", {}).items():
        expected = sc.get("duration")
        if not isinstance(expected, (int, float)) or expected <= 0:
            continue
        vpath = os.path.join(visuals_dir, f"{scene_id}.mp4")
        if not os.path.exists(vpath):
            stale.append(
                {
                    "scene_id": scene_id,
                    "visual_dur": None,
                    "expected": expected,
                    "drift": None,
                    "reason": "visual mp4 が無い (未 render)",
                }
            )
            continue
        vdur = _probe_mp4_duration(vpath)
        if vdur is None:
            stale.append(
                {
                    "scene_id": scene_id,
                    "visual_dur": None,
                    "expected": expected,
                    "drift": None,
                    "reason": "visual mp4 を probe 不能 (破損?)",
                }
            )
            continue
        drift = abs(vdur - expected)
        tol = max(1.0, expected * 0.03)
        if drift > tol:
            stale.append(
                {
                    "scene_id": scene_id,
                    "visual_dur": round(vdur, 2),
                    "expected": round(expected, 2),
                    "drift": round(drift, 2),
                    "reason": f"尺ズレ {drift:.2f}s > 許容 {tol:.2f}s (旧 timing で render?)",
                }
            )
    return stale


def _timing_signature(timing_data: dict) -> str:
    """Deterministic digest of per-scene durations (Guard-B2, an earlier episode).

    MUST stay identical to subtitle_generator.timing_signature -- both sides
    hash the same per-scene durations so the assemble preflight can compare the
    timing the subtitles were baked from vs the current timing.json.
    """
    import hashlib

    scenes = timing_data.get("scenes", {}) if isinstance(timing_data, dict) else {}
    parts = [f"{sid}:{round(sc.get('duration', 0) or 0, 3)}" for sid, sc in sorted(scenes.items())]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _subtitle_staleness_check(episode_dir: str, scene_json: str) -> str | None:
    """Guard-B/B2: subtitles.srt が現在の narration **または timing** より古ければ
    mismatch 文字列を返す (健全 or 判定不能なら None)。post-build の G2 hash 検査を
    assemble 直前へ前倒しして fail-fast 化する。

    2 層で staleness を検出する:
      Guard-B: narration TEXT を編集したのに subtitles 未再生成 →
        narration_hash mismatch (ある回で subtitles を steps に入れ忘れ、
        assemble 完走後に G2 が検出 = 20分の無駄ビルド)。
      Guard-B2: narration TEXT は不変だが読み (narration_speech_cloud) 修正 /
        速度正規化 (cloud_speed_qa --apply) で音声尺 = timing.json が刷新され、
        subtitles.srt の timestamp だけ旧尺のまま残る → timing_hash mismatch。
        text hash は一致するので Guard-B では捕まらなかった desync クラス
        (ある回で読み修正の partial rebuild が字幕/音声を desync させ user 耳検出)。
    ハッシュ計算は subtitle_generator / G2 検査と同一。"""
    import hashlib

    meta_path = os.path.join(episode_dir, "_subtitles_meta.json")
    srt_path = os.path.join(episode_dir, "subtitles.srt")
    if not (os.path.exists(meta_path) and os.path.exists(srt_path) and os.path.exists(scene_json)):
        return None
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        embedded = meta.get("narration_hash")
        if not embedded:
            return None
        with open(scene_json, encoding="utf-8") as f:
            sd = json.load(f)
        blob = "\n".join(
            n
            for sec in sd.get("sections", [])
            for sc in sec.get("scenes", [])
            for n in sc.get("narration", [])
        )
        current = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
        if current != embedded:
            return f"narration text edited: embedded={embedded} vs current scene_def={current}"
        # Guard-B2: narration unchanged -> also verify the timing the subtitles
        # were baked from still matches the current timing.json (reading /
        # speed-norm changes durations while leaving narration text identical).
        embedded_timing = meta.get("timing_hash")
        timing_path = os.path.join(episode_dir, "timing.json")
        if embedded_timing and os.path.exists(timing_path):
            with open(timing_path, encoding="utf-8") as f:
                current_timing = _timing_signature(json.load(f))
            if current_timing != embedded_timing:
                return (
                    f"timing refreshed (durations changed, narration text unchanged): "
                    f"subtitles baked from timing={embedded_timing} vs current={current_timing}"
                )
        # NOTE: Guard-B3 (narration vs timing の本文) はここでは**呼ばない**。
        # この関数は「この run で subtitles を再生成しないとき」だけ呼ばれるが、
        # B3 が捕まえる desync は **subtitles を再生成しても直らない** (本文は
        # timing.json 由来で、それを書くのは audio ステップ)。同じゲートに乗せると
        # B3 が書かれた当のシナリオ `--steps subtitles,assemble,bgm` で一度も
        # 呼ばれない。main 側で `audio` の有無を見て `_subtitle_text_staleness_check`
        # を別に呼ぶ。
    except Exception:
        return None
    return None


def _subtitle_text_staleness_check(episode_dir: str, scene_json: str) -> str | None:
    """Guard-B3: 字幕の**本文**が narration の編集前のまま焼かれていないか。

    Guard-B/B2 を両方すり抜ける desync がある。**字幕の本文は timing.json の
    `sentences[].text` から来る** (`subtitle_generator`: `raw_text = sentence["text"]`)。
    timing.json を書くのは audio ステップなので、narration を直して
    `--steps subtitles,assemble,bgm` を回すと、字幕は**再生成されるが中身は編集前の
    まま**になる。しかも `_subtitles_meta.json` には**編集後の** narration hash が
    刻まれるため、Guard-B は満足して沈黙する = 古い字幕を「検査済み」として出荷する。

    実測 (ある回の複製で narration を 1 語だけ変えて実ビルド): 字幕ステップは 5.4 秒で
    完走し subtitles.srt を書き直したが、本文は編集前のままで、Guard-B/B2 はどちらも
    None を返した。

    **subtitles を回しても直らないので、Guard-B とは別のゲートで呼ぶこと** —
    直るのは audio を回したときだけ。
    """
    if not os.path.exists(scene_json):
        return None
    try:
        with open(scene_json, encoding="utf-8") as f:
            scene_def = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return _narration_vs_timing_mismatch(scene_def, episode_dir)


def _narration_vs_timing_mismatch(scene_def: dict, episode_dir: str) -> str | None:
    """字幕の元になる timing.json の本文が、現在の narration と食い違っていないか。

    字幕は timing.json の `sentences[].text` から作られる (narration から直接ではない)。
    timing.json を書くのは audio ステップなので、**narration を編集して audio を
    回さない限り、字幕は古い本文のまま**になる。両者を直接比較して最初の食い違いを返す。

    `|` は字幕分割マーカーで表示に影響しないため落として比較する (audio 側の
    正規化とズレて誤検出しないよう、比較は表示テキストの等価性だけを見る)。
    """
    timing_path = os.path.join(episode_dir, "timing.json")
    if not os.path.exists(timing_path):
        return None
    try:
        with open(timing_path, encoding="utf-8") as f:
            timing = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    scenes = timing.get("scenes", {})
    if not scenes:
        return None
    for sec in scene_def.get("sections", []):
        for sc in sec.get("scenes", []):
            sid = sc.get("scene_id")
            tsc = scenes.get(sid)
            if not sid or not tsc:
                continue
            narr = "".join(sc.get("narration") or []).replace("|", "").strip()
            baked = "".join(s.get("text", "") for s in tsc.get("sentences", []) or [])
            baked = baked.replace("|", "").strip()
            if narr and baked and narr != baked:
                return (
                    f"narration edited but timing.json still holds the OLD text for {sid} "
                    f"(subtitles are built from timing.json, so they would ship stale). "
                    f"Re-run the audio step: --steps audio,subtitles,assemble,bgm"
                )
    return None


def _output_final_summary(episode_dir: str) -> dict:
    """output_final.mp4 summary for the progress snapshot (path/size/valid)."""
    path = os.path.join(episode_dir, OUTPUT_FINAL)
    if not os.path.exists(path):
        return {"path": path, "exists": False}
    dur = _probe_mp4_duration(path)
    return {
        "path": path,
        "exists": True,
        "size_mb": round(os.path.getsize(path) / (1024 * 1024), 1),
        "duration_sec": round(dur, 1) if dur is not None else None,
        "valid": dur is not None and dur > 0,
    }


def verify_outputs(episode_dir: str, steps_run: list[str], scene_json: str) -> list[str]:
    """Post-pipeline output verification (/ D-3).

    Each step that completed should have left specific artifacts behind.
    A successful exit code is not enough — a past run had a step return 0 but
    silently skip writing wikimedia_credits.json, leaving description.txt
    without its image-credit section. This function catches that class of
    silent partial failure.

    Returns a list of warning strings (empty if all checks pass). Does not
    raise / exit — the caller decides how to surface them. Step-level fatal
    failures are caught earlier by run_step's required=True path.
    """
    warnings: list[str] = []

    single_file_checks = {
        "subtitles": ["subtitles.srt", "subtitles_drawtext.txt"],
        "thumbnail": [
            os.path.join("thumbnails", "thumbnail_A.png"),
            os.path.join("thumbnails", "thumbnail_B.png"),
            os.path.join("thumbnails", "thumbnail_C.png"),
        ],
        "assemble": [OUTPUT_ASSEMBLED],
        "credits": ["description.txt"],
        "bgm": [OUTPUT_FINAL],
    }

    for step, files in single_file_checks.items():
        if step not in steps_run:
            continue
        for fname in files:
            path = os.path.join(episode_dir, fname)
            if not os.path.exists(path):
                warnings.append(f"  [{step}] missing: {fname}")

    # output_final.mp4 の moov/duration 健全性検証。存在チェックだけでは
    # 部分書き込み (moov atom 欠落) の壊れた mp4 を「完成」と見逃す。
    if "bgm" in steps_run:
        final_path = os.path.join(episode_dir, OUTPUT_FINAL)
        if os.path.exists(final_path):
            dur = _probe_mp4_duration(final_path)
            if dur is None or dur <= 0:
                warnings.append(
                    f"  [bgm] {OUTPUT_FINAL} CORRUPT: moov atom 欠落 / duration 取得不可。"
                    "再生不可ファイルです。bgm step を再実行してください。"
                )

    # cloud 回が速度正規化されずに最終出力された場合の advisory。Chirp3-HD は
    # 文単位の実発話速度を揺らすため、直近の cloud 回 (045/046/047) は全て
    # cloud_speed_qa --apply で正規化してから出荷している。engine=cloud の最終ビルド
    # (bgm 完了 = output_final 生成) で _prenorm_backup/ が無ければ「未正規化のまま
    # 出荷しようとしている」として WARN。正規化は原本を _prenorm_backup/ に退避するので、
    # その有無が「掛けたか」の決定的シグナルになる。
    if "bgm" in steps_run:
        engine = "voicevox"
        cfg_path_tts = os.path.join(episode_dir, "episode_config.json")
        if os.path.exists(cfg_path_tts):
            try:
                with open(cfg_path_tts, encoding="utf-8") as f:
                    _cfg_tts = json.load(f)
                engine = _cfg_tts.get("tts", {}).get("engine", "voicevox")
            except Exception:
                pass
        if engine == "cloud" and not os.path.isdir(
            os.path.join(episode_dir, "audio", "_prenorm_backup")
        ):
            # "_prenorm_backup/ が無い" だけでは「掛け忘れ」と「そもそも
            # 不要」を区別できず、段差ゼロの回でも毎回 WARN が出て、そのたび人が
            # cloud_speed_qa を手で回して打ち消していた。cmd_detect が残す判定 sidecar
            # を読み、実測で段差があるときだけ WARN する。sidecar が無い (旧 ep /
            # audio step 未実行) ときは従来どおり WARN のまま = 後方互換。
            _verdict = None
            try:
                _vp = os.path.join(episode_dir, "_speed_qa_verdict.json")
                if os.path.exists(_vp):
                    with open(_vp, encoding="utf-8") as _f:
                        _verdict = json.load(_f)
            except Exception:
                _verdict = None
            _jumps = (_verdict or {}).get("adjacent_jumps")
            if _verdict is not None and isinstance(_jumps, int) and _jumps == 0:
                print(
                    "  [speed] 未正規化だが実測で隣接段差なし "
                    f"(median={_verdict.get('median')} stdev={_verdict.get('stdev')}) "
                    "-- 正規化は不要 (掛けると緩急が潰れる)"
                )
            else:
                _measured = (
                    f" 実測の段差 {_jumps} 件。" if isinstance(_jumps, int) and _jumps else ""
                )
                warnings.append(
                    "  [speed] cloud 回が未正規化のまま最終出力 (_prenorm_backup/ なし)。"
                    f"{_measured}"
                    "Chirp3-HD の文単位速度揺れは cloud_speed_qa --apply で均す "
                    "(045/046/047 は適用済)。`python scripts/cloud_speed_qa.py <scene_def>` で"
                    "隣接段差を確認し --apply を検討 (ある回掛け忘れの反省)"
                )

    if "credits" in steps_run:
        # 【画像クレジット】is only expected when Wikimedia reference photos are
        # used. For use_reference=false episodes (Gemini-only images, credited
        # under 【映像素材】) the section is legitimately absent — don't WARN
        #.
        engine = "voicevox"
        cfg_path = os.path.join(episode_dir, "episode_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    _cfg = json.load(f)
                engine = _cfg.get("tts", {}).get("engine", "voicevox")
            except Exception:
                pass
        # 【画像クレジット】is expected only when a fetched photo was ACTUALLY
        # credited (usage=="reference" or scene-assigned) -- mirror credits_
        # generator's emission, reading wikimedia_credits.json (the source of
        # truth) instead of guessing from config. Fixes two false-positives:
        #   (a) config key mismatch: the old check read image_style.use_reference
        #       but configs use image_strategy (no top-level bool) -> defaulted
        #       True -> section wrongly expected.
        #   (b) an earlier episode Euclid: ancient figure with no birth_year. image_generator
        #       gates reference use on birth_year (use_reference = ref_photos AND
        #       birth_year AND flash), so photos are fetched + labelled but NEVER
        #       passed to Gemini -> all usage="unused" -> section legitimately
        #       absent (images credited under 【映像素材】). Don't WARN.
        expect_image_credit = False
        wiki_path = os.path.join(episode_dir, "wikimedia_credits.json")
        if os.path.exists(wiki_path):
            try:
                with open(wiki_path, encoding="utf-8") as f:
                    _wc = json.load(f)
                expect_image_credit = any(
                    ph.get("usage") == "reference" or ph.get("scene_id")
                    for ph in _wc.get("photos", [])
                )
            except Exception:
                pass
        # 【音声合成】is only expected for VOICEVOX (attribution required). Cloud TTS
        # (Google Cloud Chirp3-HD) needs no attribution, so credits_generator omits
        # the section for engine=cloud (engine-aware, credits_generator.py) -- don't
        # WARN, else a false-positive fires on every cloud episode. See internal notes.
        required_sections = [
            s
            for s in _DESCRIPTION_REQUIRED_SECTIONS
            if not (s == "【画像クレジット】" and not expect_image_credit)
            and not (s == "【音声合成】" and engine == "cloud")
        ]
        desc_path = os.path.join(episode_dir, "description.txt")
        if os.path.exists(desc_path):
            try:
                with open(desc_path, encoding="utf-8") as f:
                    content = f.read()
                for section in required_sections:
                    if section not in content:
                        warnings.append(f"  [credits] description.txt missing section: {section}")
            except Exception as e:
                warnings.append(f"  [credits] description.txt unreadable: {e}")

    # G2: Subtitle/narration hash sync check.
    # subtitle_generator writes _subtitles_meta.json with hash of narration at
    # generation time. If scene_def narration has been edited since (e.g.
    # `--steps audio,visuals,assemble,bgm` skipped subtitles step but rebuilt
    # audio with edited narration), the embedded hash will mismatch current
    # scene_def, causing 字幕 (old) / 音声 (new) 齟齬 in output_final.mp4.
    subtitles_path = os.path.join(episode_dir, "subtitles.srt")
    subtitles_meta_path = os.path.join(episode_dir, "_subtitles_meta.json")
    if (
        os.path.exists(subtitles_path)
        and os.path.exists(subtitles_meta_path)
        and os.path.exists(scene_json)
    ):
        try:
            import hashlib as _hashlib

            with open(subtitles_meta_path, encoding="utf-8") as _f:
                _meta = json.load(_f)
            embedded_hash = _meta.get("narration_hash")
            if embedded_hash:
                # Self-contained scene_def parse (scene_def variable is parsed
                # later in this function; G2 check runs before that parse).
                with open(scene_json, encoding="utf-8") as _f2:
                    _scene_def_for_g2 = json.load(_f2)
                _narration_blob = []
                for _sec in _scene_def_for_g2.get("sections", []):
                    for _sc in _sec.get("scenes", []):
                        for _n in _sc.get("narration", []):
                            _narration_blob.append(_n)
                _text = "\n".join(_narration_blob)
                current_hash = _hashlib.sha256(_text.encode("utf-8")).hexdigest()[:16]
                if current_hash != embedded_hash:
                    warnings.append(
                        f"  [subtitles] subtitles.srt hash mismatch: "
                        f"embedded={embedded_hash} vs current scene_def={current_hash}. "
                        "narration was edited after last subtitles build → 字幕/音声 齟齬リスク。"
                        "Re-run with `--steps subtitles,assemble,bgm` to sync."
                    )
                else:
                    # Guard-B2: narration text matches, but did the timing
                    # the subtitles were baked from drift? Reading / speed-norm
                    # changes durations while leaving narration text identical,
                    # so the text hash passes yet subtitles.srt timestamps go
                    # stale (字幕/音声 desync the text-hash check cannot see).
                    _embedded_timing = _meta.get("timing_hash")
                    _timing_path_g2 = os.path.join(episode_dir, "timing.json")
                    if _embedded_timing and os.path.exists(_timing_path_g2):
                        with open(_timing_path_g2, encoding="utf-8") as _f3:
                            _cur_timing = _timing_signature(json.load(_f3))
                        if _cur_timing != _embedded_timing:
                            warnings.append(
                                f"  [subtitles] subtitles.srt timing stale: "
                                f"baked from timing={_embedded_timing} vs current="
                                f"{_cur_timing} (narration text unchanged). 読み/速度正規化で"
                                "音声尺が刷新され字幕タイムスタンプが旧尺のまま → 字幕/音声 desync。"
                                "Re-run with `--steps subtitles,assemble,bgm` to sync."
                            )
        except Exception:
            pass

    # G1: Manim fallback detection.
    # visual_generator が timeout / render error / template lookup fail で
    # text_overlay fallback に切り替わった場合、_fallback_scenes.json に
    # scene_id を記録する。silent fail (「[OK]」報告 + placeholder mp4) を
    # verify 段階で必ず WARN として user に届ける。
    fallback_sidecar = os.path.join(episode_dir, "visuals", "_fallback_scenes.json")
    if "visuals" in steps_run and os.path.exists(fallback_sidecar):
        try:
            with open(fallback_sidecar, encoding="utf-8") as f:
                fallbacks = json.load(f)
            if isinstance(fallbacks, list) and fallbacks:
                # Count SCENES, not entries: one scene can log twice (the render
                # failed, then the placeholder write failed too), and reporting
                # 19 for 13 scenes overstates it. An earlier episode showed both.
                scene_ids = []
                for fb in fallbacks:
                    sid = fb.get("scene_id", "?")
                    if sid not in scene_ids:
                        scene_ids.append(sid)
                scene_reasons = ", ".join(
                    f"{fb.get('scene_id', '?')}({fb.get('reason', '?')})" for fb in fallbacks
                )
                # The old advice named timeouts only, which is the wrong lead when
                # the log is full of ffmpeg errors or access violations.
                reasons = {str(fb.get("reason", "")) for fb in fallbacks}
                if any(r.startswith("timeout") for r in reasons):
                    hint = "timeout があります。template 簡素化か MANIM_TIMEOUT の引き上げを検討"
                elif any("ffmpeg_error" in r or "render_failed" in r for r in reasons):
                    hint = (
                        "ffmpeg / レンダのクラッシュです。テンプレートではなく環境側 "
                        "(ffmpeg・ディスク・メモリ) を疑い、直してから visuals を回し直す"
                    )
                else:
                    hint = "テンプレートの解決に失敗しています。template 名と SCENES を確認"
                severity = (
                    "**この状態で assemble すると placeholder が完成動画に入ります。**"
                    if len(scene_ids) >= 3
                    else ""
                )
                warnings.append(
                    f"  [visuals] {len(scene_ids)} scene(s) が text_overlay placeholder に "
                    f"fallback しました ({len(fallbacks)} 件の記録): {scene_reasons}. "
                    f"{severity}{hint}"
                )
        except Exception:
            pass

    # G6 + content drift: description.txt vs source.
    # PRIMARY = content drift: regenerate the description from source and compare,
    # catching stale title / chapter / timestamps / credits that mtime alone
    # misses. FALLBACK = mtime staleness
    # when the content check cannot run (missing timing/config, or generate error).
    desc_path = os.path.join(episode_dir, "description.txt")
    episode_config_path = os.path.join(episode_dir, "episode_config.json")
    if os.path.exists(desc_path) and os.path.exists(scene_json):
        drift = None
        try:
            from credits_generator import description_drift

            with open(episode_config_path, encoding="utf-8") as f:
                _cfg = json.load(f)
            with open(scene_json, encoding="utf-8") as f:
                _sd = json.load(f)
            _timing = {}
            _timing_path = os.path.join(episode_dir, "timing.json")
            if os.path.exists(_timing_path):
                with open(_timing_path, encoding="utf-8") as f:
                    _timing = json.load(f)
            _wiki = {}
            _wiki_path = os.path.join(episode_dir, "wikimedia_credits.json")
            if os.path.exists(_wiki_path):
                with open(_wiki_path, encoding="utf-8") as f:
                    _wiki = json.load(f)
            drift = description_drift(episode_dir, _cfg, _sd, _wiki, _timing)
        except Exception as e:  # noqa: BLE001 - verification helper, never fatal
            print(f"  [credits] drift check unavailable, using mtime: {e!r}")
            drift = None

        if drift:
            warnings.append(
                f"  [credits] description.txt DIVERGES from source ({drift}). "
                "Re-run with `--steps credits` to regenerate title / chapter / "
                "timestamps / credits from source."
            )
        elif drift is None:
            # content check unavailable -> fall back to mtime staleness
            try:
                desc_mtime = os.path.getmtime(desc_path)
                scene_mtime = os.path.getmtime(scene_json)
                config_mtime = (
                    os.path.getmtime(episode_config_path)
                    if os.path.exists(episode_config_path)
                    else 0
                )
                newer_source_mtime = max(scene_mtime, config_mtime)
                if desc_mtime < newer_source_mtime:
                    import datetime

                    desc_dt = datetime.datetime.fromtimestamp(desc_mtime).isoformat(
                        timespec="seconds"
                    )
                    src_dt = datetime.datetime.fromtimestamp(newer_source_mtime).isoformat(
                        timespec="seconds"
                    )
                    warnings.append(
                        f"  [credits] description.txt is STALE (desc {desc_dt} < source {src_dt}). "
                        "Re-run with `--steps credits` to refresh chapter / BGM / references."
                    )
            except OSError:
                pass

    # (Phase C): description.intro staleness vs episode_config.
    # _description_meta.json (stamped by script_generator) records the intro-
    # config signature + intro text hash at generation time. WARN only when the
    # config's intro-narrative fields (theme/hook/modern_connection/
    # intro_guidance) changed AND description.intro is still the byte-identical
    # generated text -> credits_generator would bake the stale intro into
    # description.txt (public 概要欄). Editing the intro by hand clears it (text
    # hash differs -> assumed synced). Backward compat: no sidecar -> no-op.
    # Complements the credits drift check above (which compares description.txt
    # vs scene_def and cannot see a config->intro drift where both are stale).
    if os.path.exists(scene_json) and os.path.exists(episode_config_path):
        try:
            from description_meta import check_staleness as _intro_check

            with open(episode_config_path, encoding="utf-8") as _f:
                _cfg_b42 = json.load(_f)
            with open(scene_json, encoding="utf-8") as _f:
                _sd_b42 = json.load(_f)
            _stale = _intro_check(episode_dir, _cfg_b42, _sd_b42)
            if _stale:
                warnings.append(
                    f"  [credits] description.intro STALE: {_stale} "
                    "scene_def.description.intro を config に合わせて更新し "
                    "`--steps credits` で description.txt を再生成してください。"
                )
        except Exception:  # noqa: BLE001 - verification helper, never fatal
            pass

    # (F): narration -> description.intro semantic review roll-up (ADVISORY).
    # The credits step runs the Claude call and caches it; here we only READ the
    # cached report (no Claude call, keeps verify cheap) and echo any dropped-
    # qualifier flags into the final advisory box the user always reads. Mirrors
    #'s "verify in several places, execute in one". No-op when no cache /
    # stale cache / intro empty / the check was skipped.
    if os.path.exists(scene_json):
        try:
            from intro_semantic_check import format_report, read_cached_report

            with open(scene_json, encoding="utf-8") as _f:
                _sd_b21 = json.load(_f)
            _isem = read_cached_report(_sd_b21, episode_dir)
            if _isem and _isem.get("issues"):
                warnings.append(
                    "  [credits] description.intro 限定詞欠落候補 (F, advisory):\n"
                    + format_report(_isem)
                )
        except Exception:  # noqa: BLE001 - verification helper, never fatal
            pass

    scene_def = None
    if os.path.exists(scene_json):
        try:
            with open(scene_json, encoding="utf-8") as f:
                scene_def = json.load(f)
        except Exception:
            pass

    if scene_def is not None:
        ken_burns_count = 0
        manim_count = 0
        narration_count = 0
        for sec in scene_def.get("sections", []):
            for sc in sec.get("scenes", []):
                vt = (sc.get("visual") or {}).get("type")
                if vt == "ken_burns":
                    ken_burns_count += 1
                elif vt == "manim":
                    manim_count += 1
                narration_count += len(sc.get("narration", []))

        if "audio" in steps_run and narration_count > 0:
            audio_dir = os.path.join(episode_dir, "audio")
            if os.path.isdir(audio_dir):
                wav_count = sum(1 for f in os.listdir(audio_dir) if f.endswith(".wav"))
                if wav_count < narration_count:
                    warnings.append(
                        f"  [audio] {wav_count} wav files vs {narration_count} narration lines (deficit {narration_count - wav_count})"
                    )
            else:
                warnings.append("  [audio] audio/ directory missing")

        if "visuals" in steps_run:
            expected_visuals = ken_burns_count + manim_count
            visuals_dir = os.path.join(episode_dir, "visuals")
            if expected_visuals > 0:
                if os.path.isdir(visuals_dir):
                    mp4_count = sum(1 for f in os.listdir(visuals_dir) if f.endswith(".mp4"))
                    if mp4_count < expected_visuals:
                        warnings.append(
                            f"  [visuals] {mp4_count} mp4 files vs {expected_visuals} expected (ken_burns {ken_burns_count} + manim {manim_count})"
                        )
                else:
                    warnings.append("  [visuals] visuals/ directory missing")

    return warnings


# ===========================================================================
# Preflight checks — fail fast before long operations
# ===========================================================================
# Motivation: a past run lost 57 minutes on a Claude CLI 401 auth error that only
# surfaced after the first attempt returned, and another ~30 minutes on a
# pipeline launched with system Python (matplotlib/google-genai/fontTools
# missing in subprocess children). These checks cost <30s but prevent hour-
# long dead-end runs.

_PREFLIGHT_REQUIRED_MODULES = [
    # Triggered by a past dead-end: visuals/images/font_check silently fell back when
    # pipeline was launched with system Python instead of the venv.
    ("matplotlib", "visual_generator.route_map / thumbnail / text_overlay"),
    ("google.genai", "image_generator (Gemini Flash)"),
    ("fontTools", "check_font_coverage"),
    ("PIL", "Ken Burns / thumbnail / various image ops"),
]


def _preflight_modules() -> list[str]:
    """Return list of missing-module diagnostic messages (empty if OK)."""
    missing = []
    for mod, used_by in _PREFLIGHT_REQUIRED_MODULES:
        try:
            __import__(mod)
        except ImportError:
            missing.append(f"{mod} (needed by: {used_by})")
    return missing


def _preflight_claude_cli(timeout_sec: int = 25) -> tuple[bool, str, str]:
    """Ping Claude CLI with a trivial prompt. Returns (ok, reason, message).

    delegates to claude_backend.probe_claude_cli (single source of truth
    for the ping + classification, unit-tested via classify_claude_ping). Cost
    ~8-20s healthy, faster on 401. Trades a fixed startup cost for avoiding the
    expired-token dead-end where the whole QA layer fails silently mid-build.
    """
    from claude_backend import probe_claude_cli

    return probe_claude_cli(timeout_sec)


def probe_claude_with_retry(prober=None, on_retry=None):
    """Ping Claude, retrying ONCE on a timeout. Returns (ok, reason, message).

    an earlier episode: one spurious 25s timeout aborted a 60-minute build at the preflight, and
    the CLI answered in 5.6s when re-run by hand seconds later. A timeout is transient
    by nature (cold start, network hiccup), so it earns a second chance.

    An `auth` verdict is deliberately NOT retried: an expired token does not heal, and
    retrying would only delay the fail-fast that exists to provide. Same for
    `not_found` (the binary is missing) and any other classification.

    `prober` is injectable so the retry policy itself is testable without a CLI.
    """
    probe = prober or _preflight_claude_cli
    ok, reason, msg = probe()
    if not ok and reason == "timeout":
        if on_retry:
            on_retry()
        ok, reason, msg = probe()
    return ok, reason, msg


def _preflight_voicevox(
    url: str = "http://localhost:50021", timeout_sec: int = 5
) -> tuple[bool, str]:
    """Verify VOICEVOX server is reachable."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url}/version", timeout=timeout_sec) as resp:
            if resp.status != 200:
                return False, f"VOICEVOX returned HTTP {resp.status}"
            version = (resp.read() or b"").decode("utf-8", errors="replace").strip()
            return True, f"OK ({version})"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, (
            f"VOICEVOX server not reachable at {url}. "
            f"Start the VOICEVOX GUI app (it binds port 50021). Details: {e}"
        )


def _env_or_dotenv(key: str) -> str | None:
    """Return `key` from process env, else from a top-level .env file (no deps).

    Used by the cloud-key preflight; a lone `KEY=value` line is enough.
    """
    v = os.environ.get(key)
    if v:
        return v.strip()
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith(key + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None


def run_preflight_checks(
    steps: list[str], engine: str = "voicevox", skip_auth_probe: bool = False
) -> None:
    """Run fail-fast environment checks; sys.exit(1) with clear guidance on failure.

    `engine` gates the VOICEVOX server check: engine="cloud" needs no local
    VOICEVOX (Cloud TTS is a remote REST API), so that check is skipped.
    `skip_auth_probe` skips the Claude CLI auth ping (offline / mechanical
    rebuild where a stale token is acceptable).
    """
    print("=" * 60)
    print("  Preflight Checks")
    print("=" * 60)

    pipeline_log.step_start("preflight", required_steps=steps)
    preflight_start = time.time()

    # (1) Python modules — always required
    print("  [1/3] Python modules... ", end="", flush=True)
    missing = _preflight_modules()
    if missing:
        print("FAIL")
        print()
        print("  Missing modules:")
        for m in missing:
            print(f"    - {m}")
        print()
        print(f"  Current Python: {sys.executable}")
        print()
        print("  Likely cause: pipeline launched without activating venv.")
        print("  Fix (Git Bash):")
        print("    source venv/Scripts/activate")
        print("  Fix (cmd/PowerShell):")
        print("    venv\\Scripts\\activate")
        print()
        pipeline_log.emit(
            pipeline_log.LEVEL_CRITICAL,
            "preflight",
            "python modules missing",
            missing=missing,
            python_executable=sys.executable,
        )
        pipeline_log.close()
        sys.exit(1)
    print("OK")

    # (2) Claude CLI auth — run whenever ANY Claude-dependent step will run
    # (not just "script"). A --steps qa/credits/visuals rebuild also calls Claude,
    # and previously skipped this probe -> its QA silently degraded on a dead token.
    needs_claude = bool(CLAUDE_DEPENDENT_STEPS & set(steps))
    if skip_auth_probe:
        print("  [2/3] Claude CLI auth... skipped (--skip-auth-probe)")
    elif needs_claude:
        print("  [2/3] Claude CLI auth... ", end="", flush=True)
        ok, reason, msg = probe_claude_with_retry(
            on_retry=lambda: print("timeout, retrying... ", end="", flush=True)
        )
        if not ok:
            print("FAIL")
            print(f"    {msg}")
            print()
            if reason == "auth":
                print("  OAuth セッションが失効している可能性が高いです。再認証してください:")
                print("    claude setup-token   (1年有効な OAuth トークンを発行)")
                print("  または ANTHROPIC_API_KEY を環境変数に設定。")
            elif reason == "not_found":
                print(
                    "  'claude' コマンドが PATH にありません。Claude Code CLI を確認してください。"
                )
            elif reason == "timeout":
                print("  応答なし (ネットワーク or CLI ハング)。再試行するか、Claude を使わない")
                print("  ステップだけなら --skip-auth-probe を付けてください。")
            else:
                print("  Claude CLI が異常応答。再認証 (claude setup-token) と CLI の動作を確認、")
                print("  または Claude を使わないビルドなら --skip-auth-probe を付けてください。")
            print()
            pipeline_log.emit(
                pipeline_log.LEVEL_CRITICAL,
                "preflight",
                "claude cli auth failed",
                reason=reason,
                detail=msg,
            )
            pipeline_log.close()
            sys.exit(1)
        print(msg)
    else:
        print("  [2/3] Claude CLI auth... skipped (steps don't require it)")

    # (3) VOICEVOX — only if audio step will run AND engine is voicevox.
    # Cloud TTS is a remote REST API (no local server) -> skip the check.
    if "audio" in steps and engine == "voicevox":
        print("  [3/3] VOICEVOX server... ", end="", flush=True)
        ok, msg = _preflight_voicevox()
        if not ok:
            print("FAIL")
            print(f"    {msg}")
            print()
            pipeline_log.emit(
                pipeline_log.LEVEL_CRITICAL,
                "preflight",
                "voicevox unreachable",
                detail=msg,
            )
            pipeline_log.close()
            sys.exit(1)
        print(msg)
    elif "audio" in steps and engine == "cloud":
        print("  [3/3] VOICEVOX server... skipped (engine=cloud, no local server)")
    else:
        print("  [3/3] VOICEVOX server... skipped (audio step not selected)")

    # (4) Cloud TTS/STT keys — only if the audio step runs with engine=cloud.
    # GOOGLE_TTS_API_KEY (synthesis) is REQUIRED; GOOGLE_API_KEY (Gemini STT read-QA)
    # is advisory (stt_qa degrades gracefully). ある回で両キーを取り違え、存在しない
    # 「API block」を追った反省 — 別物であることを preflight で明示する。
    if "audio" in steps and engine == "cloud":
        print("  [cloud] Cloud TTS/STT keys... ", end="", flush=True)
        tts_key = _env_or_dotenv("GOOGLE_TTS_API_KEY")
        stt_key = _env_or_dotenv("GOOGLE_API_KEY")
        if not tts_key:
            print("FAIL")
            print("    GOOGLE_TTS_API_KEY not found (env / .env). Cloud 音声合成に必須。")
            print("    Fix: .env に GOOGLE_TTS_API_KEY=... を設定")
            print("    (注意: Gemini/STT の GOOGLE_API_KEY とは別キー。取り違え注意)")
            pipeline_log.emit(pipeline_log.LEVEL_CRITICAL, "preflight", "cloud tts key missing")
            pipeline_log.close()
            sys.exit(1)
        if not stt_key:
            print("OK — GOOGLE_TTS_API_KEY あり (但し GOOGLE_API_KEY 無し=STT 読みQAはスキップ)")
        else:
            print("OK (GOOGLE_TTS_API_KEY 合成 + GOOGLE_API_KEY STT)")

    pipeline_log.step_end(
        "preflight",
        exit_code=0,
        duration_ms=int((time.time() - preflight_start) * 1000),
    )
    print()


# ===========================================================================
# Partial rebuild: --rebuild-scene SCENE_ID
# ===========================================================================


#: 予告ゲートが止める閾値。既存キャッシュがあるのに**半数以上**を再合成するなら、
#: 「1 か所直すつもり」ではありえないので確認を挟む。出荷 63 ep へ当てた実測では
#: 発火 1 件 (048_khayyam: 69 文中 41 文 / キャッシュは 29 件しかない) で、
#: 部分的な miss (047=17, 050=28, 049=19) は注意行にとどまり止めない。
FULL_RESYNTH_RATIO = 0.5


def _synthesis_forecast_gate(
    scene_json: str,
    episode_dir: str,
    src_dir: str,
    tts_engine: str,
    tts_voice: str | None,
    tts_rate: float | None,
    speed_scale: float,
    args,
) -> None:
    """合成の**前**に「何文を再合成するか」を出し、全文級なら確認を挟む。

    ある回 (2026-08-06): 1 文だけ直したつもりの再ビルドが 94 文すべてを再合成し、
    Cloud TTS は非決定的なので全 23 scene の尺が動き、visual 23 本の再 render
    (24 分) まで波及して合計 57 分になった。**この数は合成前に 1 秒で出せる**のに、
    誰も見ていなかった。予告は常に出し、止めるのは全文級のときだけ。

    初回ビルド (キャッシュ無し) と `--force-regen-audio` は意図が明示されている
    ので対象外。
    """
    if args.dry_run_audio or args.force_regen_audio:
        return
    try:
        sys.path.insert(0, src_dir)
        import audio_generator as _ag

        plan = _ag.plan_synthesis(
            scene_json,
            episode_dir,
            engine=tts_engine,
            tts_voice=tts_voice,
            tts_rate=tts_rate,
            speed_scale=speed_scale,
        )
    except Exception as _e:  # 予告が壊れてもビルドは止めない
        print(f"[合成予告] 見積もれませんでした (続行): {type(_e).__name__}: {_e}")
        return

    total, misses, cached = plan["total"], plan["misses"], plan["cache_entries"]
    if not total:
        return
    print(
        f"\n[合成予告] 全 {total} 文中 {misses} 文を再合成します "
        f"(キャッシュ一致 {plan['hits']} 文 / 既存キャッシュ {cached} 件、"
        f"影響 {len(plan['miss_scenes'])} scene)"
    )
    if cached == 0 or misses == 0:
        return

    if misses < total * FULL_RESYNTH_RATIO:
        return

    print(f"\n{'!' * 60}")
    print(f"  [合成予告] 既にビルド済みの ep で {misses}/{total} 文を再合成しようとしています。")
    if tts_engine == "cloud":
        print(
            "  Cloud TTS (Chirp3-HD) は非決定的なので、**テキストが同じでも尺が変わります**\n"
            "  -> 尺が変わった scene は visual の再 render が要り、ビルドが数十分伸びます。"
        )
    print(
        "  よくある原因: voice/rate/speed の変更、読みの一括修正、"
        "キャッシュキーの基が変わった古いビルド、audio/ の wav 差し替え。\n"
        "  1 シーンだけ直したいなら: "
        "python src/pipeline.py <config> --rebuild-scene <scene_id>"
    )
    print(f"{'!' * 60}")
    if args.allow_full_resynthesis:
        return
    if not _confirm_continue("意図した全文再合成なら --allow-full-resynthesis を付けて再実行。"):
        print("Pipeline aborted (合成予告ゲート)。")
        sys.exit(1)


def _run_pre_images_checks(
    episode_dir: str, scene_json: str, config_path: str, src_dir: str
) -> None:
    """画像を作る**前**の検査 (ある回: 主題肖像の use_reference gap)。

    `--rebuild-scene` の ken_burns 経路も画像を作り直すのに、この検査を通って
    いなかった (2026-08-06 の再検証で判明。最初の棚卸しでは音声・visual 側だけを
    共有化し、**画像と字幕の側を取りこぼしていた**)。
    """
    # misreading: subject-portrait use_reference gap check (before the paid Gemini run).
    # If a real reference photo exists (config.wikimedia_photo_urls) but a subject
    # portrait ken_burns scene has use_reference unset, it is generated text-only,
    # which idealizes distinctive features. advisory.
    try:
        _scripts_dir = os.path.join(src_dir, "..", "scripts")
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from lint_portrait_reference import run_lint as _portrait_ref_run

        _pr = _portrait_ref_run(scene_json, config_path)
        if _pr:
            print(
                f"\n  [WARN] 主題肖像が text-only 生成の恐れ {len(_pr)} 件 "
                "(参照 gate OFF = config に birth_year が無い可能性):"
            )
            for _w in _pr:
                print(f"    {_w['scene_id']}: config に birth_year を明記して gate を ON に")
            print(f"    詳細: python scripts/lint_portrait_reference.py {episode_dir}")
        else:
            print("  [OK] 主題肖像は参照写真を適切に条件付け (or 実写参照なし)")
    except Exception as _e:
        print(f"  [WARN] portrait-reference チェック skipped: {_e}")


def _run_post_images_border_lint(episode_dir: str, src_dir: str) -> None:
    """生成画像の白縁を実測する (の source 側)。両経路で共有する。"""
    # ─── ある回: 白縁検出 (安価な静的チェック、Vision QA とは別) ──────
    # Gemini が油絵に焼き込む白いキャンバス/額縁の縁は ken_burns の 15% ズーム
    # では消えきらず、最終動画で白帯になる。images
    # 直後に四辺の near-white strip を実測し、再描画/トリミングを促す (WARN-only)。
    try:
        _scripts_dir = os.path.join(src_dir, "..", "scripts")
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from lint_image_borders import run as _border_run

        _bw = _border_run(os.path.join(episode_dir, "images"))
        if _bw:
            print(f"\n  [WARN] 白縁検出 {len(_bw)} 枚 (動画で白帯になりうる):")
            for _b in _bw:
                _bd = ", ".join(f"{k}={v}px" for k, v in _b["borders"].items())
                print(f"    - {_b['image']}: {_bd}")
            print(
                "    対処: python scripts/lint_image_borders.py "
                f"{os.path.join(episode_dir, 'images')} --trim (+ visuals 再生成)"
            )
        else:
            print("  [OK] 白縁チェック: 検出なし")
    except Exception as _e:
        print(f"  [WARN] 白縁チェック skipped: {_e}")


def _run_image_qa_gate2(
    episode_dir: str, scene_json: str, src_dir: str, args, scenes: str | None = None
) -> None:
    """QA Gate 2: 生成画像と narration の整合を Claude vision で見る。

    `scenes` を渡すとその scene だけ検査する (13 枚へ vision を投げると部分再ビルドの
    速さが失われる)。CLAUDE.md の「画像を再生成したら qa_image_checker を回す。勝手に
    QA を skip しない」は `--rebuild-scene` にも当てはまるのに、この経路では走って
    いなかった。
    """
    # Runs AFTER image generation so freshly-produced images are evaluated.
    # The prompt covers narration-image consistency plus the original time-place /
    # subject / atmosphere checks.
    if not ((args.qa or args.qa_quick) and not args.skip_qa and not args.skip_qa_image_narration):
        return
    qa_img_report = os.path.join(episode_dir, "qa_report_images.json")
    cmd = [
        sys.executable,
        os.path.join(src_dir, "qa_image_checker.py"),
        scene_json,
        "--output",
        qa_img_report,
    ]
    if scenes:
        cmd += ["--scenes", scenes]
    print(f"\n{'=' * 60}")
    print("  QA Gate 2: Image Quality Check")
    print(f"{'=' * 60}")
    print(f"  Command: {' '.join(cmd)}\n")
    pipeline_log.step_start("qa_image", command=" ".join(cmd))
    _qa_image_start = time.time()
    qa_image_exit = _run_subprocess_with_stderr_capture(cmd)
    pipeline_log.step_end(
        "qa_image",
        exit_code=qa_image_exit,
        duration_ms=int((time.time() - _qa_image_start) * 1000),
    )
    if qa_image_exit == 1:
        print(f"\n[WARN] Image QA found critical issues. Check: {qa_img_report}")
        if not _confirm_continue(
            "Re-run with --skip-qa-image-narration to skip Gate 2, or --skip-qa to skip all QA."
        ):
            print("Pipeline aborted (image QA critical).")
            sys.exit(1)


def _run_font_coverage_check(scene_json: str, src_dir: str) -> None:
    """字幕を焼く前に、フォントが持たない漢字 (豆腐化) を検出する。

    部分再ビルドは字幕を**全編**再生成するのに、この検査を通っていなかった。
    """
    font_check_script = os.path.join(src_dir, "check_font_coverage.py")
    if os.path.exists(font_check_script) and os.path.exists(scene_json):
        run_step("font_check", [sys.executable, font_check_script, scene_json], required=False)


def _run_audio_pre_checks(scene_json: str, src_dir: str, tts_engine: str, args) -> None:
    """audio を合成する**前**に走る読み検査。full build と部分再ビルドで共有する。

    ここを共有にしたのは、`--rebuild-scene` がこれらを 1 つも通らなかったため
    (2026-08-06 の棚卸しで判明)。1 シーンだけ直す経路は **narration を編集した
    直後に走る**のが普通なので、読み検査が最も要る場面そのものだった。特に
    cloud_reading_lint の検査 (9) は `narration_speech_cloud` が古いまま
    (= 音声が編集前の語を喋り字幕だけ新しくなる) を捕まえる。
    """
    # VOICEVOX 誤読 pre-build guard (advisory WARN, never blocks).
    # 実際に合成されるテキストを kana 実測し、既知の誤読リスク語が読み固定
    # されていない行を WARN する。VOICEVOX 不通や dry-run audio では自動 skip。
    # VOICEVOX-only (audio_query kana 実測): Cloud は STT QA (audio 後) で代替。
    if tts_engine == "voicevox" and not args.skip_reading_guard and not args.dry_run_audio:
        guard_script = os.path.join(os.path.dirname(src_dir), "scripts", "reading_guard.py")
        if os.path.exists(guard_script):
            run_step(
                "reading_guard",
                [sys.executable, guard_script, scene_json],
                required=False,
            )

    # Cloud pre-step: ensure narration_speech_cloud exists BEFORE synthesis.
    # script_generator does not emit it, so without this the audio step falls
    # back to narration_speech (VOICEVOX kana) -- flat readings AND a silent
    # source of STALE audio (fallback wavs persist across text edits). Fill-if-
    # absent only: hand-tuned narration_speech_cloud is preserved. Advisory:
    # on failure the audio step still runs (with the old fallback).
    if tts_engine == "cloud" and not args.dry_run_audio:
        gen_script = os.path.join(os.path.dirname(src_dir), "scripts", "gen_cloud_readings.py")
        if os.path.exists(gen_script):
            run_step(
                "gen_cloud_readings (narration_speech_cloud)",
                [sys.executable, gen_script, scene_json],
                required=False,
            )

        # Cloud reading lint (P2/P3): 多読み漢字/同音誤解語/難語/不自然な間 を
        # narration + narration_speech_cloud で合成前に静的走査 (reading_guard の
        # Cloud 版)。ある回で user が1つずつ指摘した読み温床を出荷前に洗う。advisory。
        reading_lint = os.path.join(os.path.dirname(src_dir), "scripts", "cloud_reading_lint.py")
        if os.path.exists(reading_lint):
            run_step(
                "cloud_reading_lint (Chirp3-HD 読み誤り温床)",
                [sys.executable, reading_lint, scene_json],
                required=False,
            )


def _run_audio_post_checks(
    scene_json: str,
    episode_dir: str,
    timing_json: str,
    src_dir: str,
    tts_engine: str,
    args,
    scenes: str | None = None,
    allow_normalize: bool = True,
) -> None:
    """合成した wav を実測する検査 (Cloud のみ)。full build と部分再ビルドで共有する。

    `scenes` を渡すと STT はそのシーンだけを書き起こす (部分再ビルドで 20 シーン分の
    Gemini 呼び出しを避ける)。速度 QA は episode 全体の中央値と比べる検査なので
    **絞らない** -- 1 シーンだけ再合成すると、そのシーンだけ正規化が外れて前後と
    段差になる、というのがまさに見たい事象だから。

    `allow_normalize=False` は部分再ビルド用。`--apply` は episode 全体の wav を
    書き換えるので、visual を 1 本しか再 render していない状態で走らせると
    **他シーンの尺だけが動いて で止まる**。
    """
    if tts_engine != "cloud" or args.dry_run_audio:
        return

    speed_script = os.path.join(os.path.dirname(src_dir), "scripts", "cloud_speed_qa.py")
    audio_subdir = os.path.join(episode_dir, "audio")

    # fix (opt-in): atempo-normalize per-sentence articulation toward
    # the episode median (Chirp3-HD varies speech rate 24-31% between
    # adjacent sentences even in one session; per-sentence re-synth cannot
    # converge). Runs BEFORE stt_qa/detection so they verify the normalized
    # audio, and before subtitles/visuals so timing.json is final.
    if allow_normalize and args.normalize_cloud_speed and os.path.exists(speed_script):
        run_step(
            "cloud_speed_normalize (fix)",
            [
                sys.executable,
                speed_script,
                scene_json,
                "--audio-dir",
                audio_subdir,
                "--timing",
                timing_json,
                "--apply",
            ],
        )
    elif args.normalize_cloud_speed and not allow_normalize:
        print(
            "\n[cloud_speed_normalize] 部分再ビルドでは --apply を走らせません "
            "(episode 全体の wav を書き換えると、再 render していない scene の尺だけが"
            "動いて で止まります)。必要なら再ビルド後に単体で実行してください。"
        )

    # Cloud read verification via Gemini STT (advisory; VOICEVOX uses the
    # pre-build reading_guard instead).
    stt_script = os.path.join(os.path.dirname(src_dir), "scripts", "stt_qa.py")
    if os.path.exists(stt_script):
        stt_cmd = [sys.executable, stt_script, scene_json, "--audio-dir", audio_subdir]
        if scenes:
            stt_cmd += ["--scenes", scenes]
        run_step("stt_qa (Cloud read check)", stt_cmd, required=False)

    # detection (always-on advisory): surface abrupt articulation
    # jumps pre-publish (writes speed_qa_report.txt). Detection is free
    # regardless of the opt-in fix, so the problem is never invisible.
    if os.path.exists(speed_script):
        run_step(
            "speed_qa (Cloud speed check)",
            [sys.executable, speed_script, scene_json, "--audio-dir", audio_subdir],
            required=False,
        )


def _run_partial_rebuild(
    scene_id: str,
    config_path: str,
    episode_dir: str,
    config: dict,
    src_dir: str,
    bgm_file: str,
    bgm_config: dict,
    tts_engine: str = "voicevox",
    tts_voice: str | None = None,
    tts_rate: float | None = None,
    force_regen: bool = False,
    skip_intro_check: bool = False,
    args=None,
) -> None:
    """Rebuild a single scene and re-run assembly + credits + bgm.

    This is a completely separate code path from the full build.
    Called only when --rebuild-scene is specified.

    **`args` を受け取るのは検査を full build と共有するため** (2026-08-06)。
    それまでこの経路は full build が走らせる検査 16 系統を **1 つも通らず**、
    「在庫を 1 シーンだけ直す」という最も慎重にやりたい操作が、最も検査の薄い
    経路になっていた。`args=None` は後方互換 (検査を全部飛ばす) だが、pipeline
    からは常に渡す。
    """
    scene_json = os.path.join(episode_dir, "scene_definition.json")
    timing_json = os.path.join(episode_dir, "timing.json")

    # Validate prerequisites
    if not os.path.exists(scene_json):
        print(f"[PARTIAL REBUILD] ERROR: scene_definition.json not found: {scene_json}")
        sys.exit(1)
    if not os.path.exists(timing_json):
        print(f"[PARTIAL REBUILD] ERROR: timing.json not found: {timing_json}")
        sys.exit(1)

    # Load scene_definition.json and find the target scene
    with open(scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)

    target_scene = None
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            if scene.get("scene_id") == scene_id:
                target_scene = scene
                break
        if target_scene:
            break

    if target_scene is None:
        print(f"[PARTIAL REBUILD] ERROR: Scene '{scene_id}' not found in scene_definition.json")
        sys.exit(1)

    vtype = target_scene["visual"]["type"]

    print(f"\n{'=' * 60}")
    print("  PARTIAL REBUILD")
    print(f"{'=' * 60}")
    print(f"  Scene:       {scene_id}")
    print(f"  Visual type: {vtype}")
    print(f"  Episode dir: {episode_dir}")
    print(f"{'=' * 60}")

    rebuild_start = time.time()
    pipeline_log.emit(
        pipeline_log.LEVEL_INFO,
        "partial_rebuild",
        "partial rebuild start",
        scene_id=scene_id,
        visual_type=vtype,
    )

    # この経路が実際に回すステップ。stale ゲート (Guard-B/B3) と の
    # 「未実行ステップの advisory」表示が、full build と同じ語彙で判断できるようにする。
    steps_run = ["audio", "subtitles", "visuals", "assemble", "credits", "bgm"]
    if vtype == "ken_burns":
        steps_run.insert(2, "images")

    # --- Step 1: Audio regeneration for the target scene ---
    print("\n[PARTIAL REBUILD] Step 1/6: Audio regeneration")
    # 合成の前に読みを見る。1 シーンだけ直す操作は **narration を編集した直後**に
    # 走るのが普通なので、ここが読み検査の最も要る場面。cloud_reading_lint の
    # 検査 (9) は narration だけ直して narration_speech_cloud が古いまま
    # (音声は編集前の語を喋り、字幕だけ新しくなる) を捕まえる。
    if args is not None:
        _run_audio_pre_checks(scene_json, src_dir, tts_engine, args)
    sys.path.insert(0, src_dir)
    import audio_generator
    from audio_generator import rebuild_single_scene_audio

    # per-ep speed override on the in-process synth path (this path imports
    # the function directly instead of running audio_generator.py as a subprocess,
    # so the --speed-scale CLI does not apply; set the module global instead).
    # (VOICEVOX-only tuning; inert for engine=cloud.)
    audio_generator.SPEED_SCALE = config.get("speed_scale", 0.87)

    pipeline_log.step_start("audio (partial rebuild)", scene_id=scene_id)
    _audio_start = time.time()
    audio_ok = rebuild_single_scene_audio(
        scene_json,
        scene_id,
        episode_dir,
        engine=tts_engine,
        tts_voice=tts_voice,
        tts_rate=tts_rate,
        force_regen=force_regen,
    )
    pipeline_log.step_end(
        "audio (partial rebuild)",
        exit_code=0 if audio_ok else 1,
        duration_ms=int((time.time() - _audio_start) * 1000),
        scene_id=scene_id,
    )
    if not audio_ok:
        pipeline_log.close()
        print("[PARTIAL REBUILD] Audio regeneration failed. Aborting.")
        sys.exit(1)

    # 合成した wav を実測する (STT はこのシーンだけ / 速度は episode 全体と比べる)。
    if args is not None:
        _run_audio_post_checks(
            scene_json,
            episode_dir,
            timing_json,
            src_dir,
            tts_engine,
            args,
            scenes=scene_id,
            allow_normalize=False,
        )

    # --- Step 2: Subtitle regeneration (full, since global timestamps changed) ---
    print("\n[PARTIAL REBUILD] Step 2/6: Subtitle regeneration (full)")
    # 字幕は**全編**焼き直すので、フォントが持たない漢字の検査も full build と同じく通す。
    if args is not None:
        _run_font_coverage_check(scene_json, src_dir)
    cmd = [
        sys.executable,
        os.path.join(src_dir, "subtitle_generator.py"),
        timing_json,
        "--output-dir",
        episode_dir,
        "--scene-json",
        scene_json,
    ]
    # Engine-aware: Cloud episodes must not use VOICEVOX segment timing (it
    # measures the display text, not the Cloud-spoken text_clean). See the main
    # subtitles step for the full rationale.
    if tts_engine == "cloud":
        cmd.append("--no-voicevox-timing")
    run_step("subtitles (partial rebuild)", cmd)

    # --- Step 3: Image regeneration (only for ken_burns scenes) ---
    if vtype == "ken_burns":
        print("\n[PARTIAL REBUILD] Step 3/6: Image regeneration (ken_burns)")
        # 画像を作り直す以上、full build と同じ検査を通す。CLAUDE.md の
        # 「画像を再生成したら qa_image_checker を回す。勝手に QA を skip しない」は
        # この経路にも当てはまるのに、走っていなかった (2026-08-06 の再検証で判明)。
        if args is not None:
            _run_pre_images_checks(episode_dir, scene_json, config_path, src_dir)
        # Delete existing image to force regeneration
        images_dir = os.path.join(episode_dir, "images")
        for ext in (".png", ".jpg"):
            img_path = os.path.join(images_dir, f"{scene_id}{ext}")
            if os.path.exists(img_path):
                os.remove(img_path)
                print(f"[PARTIAL REBUILD] Deleted: {img_path}")
        cmd = [
            sys.executable,
            os.path.join(src_dir, "image_generator.py"),
            scene_json,
            "--output-dir",
            episode_dir,
            "--generate",
            "--scene",
            scene_id,
            "--config",
            config_path,
        ]
        run_step("images (partial rebuild)", cmd, required=False)
        if args is not None:
            _run_post_images_border_lint(episode_dir, src_dir)
            # Gate 2 はそのシーンだけに絞る (13 枚へ vision を投げない)。
            _run_image_qa_gate2(episode_dir, scene_json, src_dir, args, scenes=scene_id)
    else:
        print(f"\n[PARTIAL REBUILD] Step 3/6: Image regeneration -- skipped ({vtype})")

    # --- Step 4: Visual regeneration for the target scene ---
    print("\n[PARTIAL REBUILD] Step 4/6: Visual regeneration")
    # レンダ前の検査。route_map preflight (STOP ゲート) がここに無かったことは
    # pitfalls に「将来課題」として載っていたが、実際には pre-visuals 検査群ごと
    # 抜けていた -- 経路ラベルの衝突も、空 params による別 ep データの描画も、
    # 地名カバレッジも、部分再ビルドでは誰も見ていなかった。
    if args is not None:
        _run_pre_visuals_checks(episode_dir, scene_json, config, args, src_dir)
        _run_route_map_preflight(scene_json, args)

    from visual_generator import rebuild_single_scene_visual

    manim_dir = os.path.join(src_dir, "manim_templates")
    pipeline_log.step_start("visual (partial rebuild)", scene_id=scene_id)
    _visual_start = time.time()
    visual_ok = rebuild_single_scene_visual(
        scene_json,
        timing_json,
        scene_id,
        episode_dir,
        manim_templates_dir=manim_dir,
    )
    pipeline_log.step_end(
        "visual (partial rebuild)",
        exit_code=0 if visual_ok else 1,
        duration_ms=int((time.time() - _visual_start) * 1000),
        scene_id=scene_id,
    )
    if not visual_ok:
        pipeline_log.close()
        print("[PARTIAL REBUILD] Visual regeneration failed. Aborting.")
        sys.exit(1)

    # レンダ後の検査。Vision QA はこのシーンだけに絞る (全 scene へ投げると
    # 部分再ビルドの速さが失われる)。白帯と bbox 衝突は決定論で速いので絞らない。
    if args is not None:
        _run_post_visual_lints(episode_dir, scene_json, src_dir, args, scenes=scene_id)

    # --- Step 5: Video assembly (full, unavoidable) ---
    print("\n[PARTIAL REBUILD] Step 5/6: Video assembly (full)")
    # 1 シーンだけ再 render したのに、他の scene の尺が動いていないか。
    # audio も subtitles も回しているので Guard-B / B3 は自動的に skip される。
    if args is not None:
        _run_pre_assemble_guards(episode_dir, scene_json, timing_json, steps_run, args)
    cmd = [
        sys.executable,
        os.path.join(src_dir, "video_assembler.py"),
        scene_json,
        timing_json,
        "--output-dir",
        episode_dir,
        "--output-name",
        OUTPUT_ASSEMBLED,
    ]
    run_step("assemble (partial rebuild)", cmd)

    # --- Step 5.5: Credits ---
    print("\n[PARTIAL REBUILD] Step 5.5/6: Credits")
    cmd = [
        sys.executable,
        os.path.join(src_dir, "credits_generator.py"),
        config_path,
    ]
    # Default (1.0) must match bgm_mixer's default to keep chapters aligned.
    intro_pause = bgm_config.get("intro_pause", 1.0)
    if intro_pause > 0:
        cmd.extend(["--intro-pause", str(intro_pause)])
    if skip_intro_check:
        cmd.append("--skip-intro-check")
    run_step("credits (partial rebuild)", cmd, required=False)

    # --- Step 6: BGM mixing (full, unavoidable) ---
    output_assembled = os.path.join(episode_dir, OUTPUT_ASSEMBLED)
    output_final = os.path.join(episode_dir, OUTPUT_FINAL)
    if bgm_file and os.path.exists(bgm_file) and os.path.exists(output_assembled):
        print("\n[PARTIAL REBUILD] Step 6/6: BGM mixing")
        cmd = [
            sys.executable,
            os.path.join(src_dir, "bgm_mixer.py"),
            output_assembled,
            bgm_file,
            "--output",
            output_final,
            "--intro-pause",
            str(bgm_config.get("intro_pause", 1.0)),
            "--outro-hold",
            str(bgm_config.get("outro_hold", 10.0)),
            "--outro-fade",
            str(bgm_config.get("outro_fade", 3.0)),
            "--bgm-volume",
            str(bgm_config.get("volume_db", -20)),
            "--bgm-fadein",
            str(bgm_config.get("bgm_fadein", 2.0)),
        ]
        run_step("bgm (partial rebuild)", cmd)
    else:
        print(f"\n[PARTIAL REBUILD] Step 6/6: BGM — skipped (no BGM file or {OUTPUT_ASSEMBLED})")

    # --- 出力検査 + レビューコピー + post_build_verify + レビューリール ---
    # full build と同じ締めを通す。ここが無かったので、部分再ビルドで作った
    # 出荷物は構造検査 11 件を一度も受けず、temp_videos のコピーも古いままだった。
    verify_warnings: list[str] = []
    if args is not None:
        verify_warnings, _ = _run_output_verification(
            episode_dir, src_dir, config, args, steps_run, scene_json
        )

    # --- Summary ---
    total_elapsed = time.time() - rebuild_start

    print(f"\n{'=' * 60}")
    print("  PARTIAL REBUILD Complete")
    print(f"{'=' * 60}")
    print(f"  Scene:      {scene_id}")
    print(f"  Total time: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")

    if os.path.exists(output_final):
        size_mb = os.path.getsize(output_final) / (1024 * 1024)
        print(f"  Output:     {output_final} ({size_mb:.1f} MB)")
    elif os.path.exists(output_assembled):
        size_mb = os.path.getsize(output_assembled) / (1024 * 1024)
        print(f"  Output:     {output_assembled} ({size_mb:.1f} MB) [bgm pending]")

    # advisory の roll-up を部分再ビルドでも出す。 の教訓は「検出済みの警告が
    # サマリに集約されないと読まれない」で、それは full build に限らない。
    if verify_warnings:
        print(
            f"  [!] {len(verify_warnings)} verification warning(s) above "
            "-- review 'Output Verification' before publishing."
        )
    if _advisory_warn_counts:
        print(
            f"  [!] advisory warnings -- {_format_advisory_rollup()} "
            "(review each step's output above)"
        )
    _advisory_rollup_state["shown"] = True

    print(f"{'=' * 60}")

    pipeline_log.emit(
        pipeline_log.LEVEL_INFO,
        "partial_rebuild",
        "partial rebuild end",
        scene_id=scene_id,
        duration_ms=int(total_elapsed * 1000),
    )
    pipeline_log.close()


def _drain_stderr(stream, on_marker, on_raw) -> None:
    """Thread body: read child stderr line-by-line, dispatch by marker prefix.

    Runs on a daemon thread so it never blocks parent shutdown. Closing the
    stream (parent kill) raises a benign exception that terminates the loop.
    """
    try:
        for line in stream:
            event = pipeline_log.parse_marker_line(line)
            if event is not None:
                on_marker(event)
            else:
                on_raw(line)
    except (ValueError, OSError):
        # Stream closed underneath us (parent kill / Ctrl+C). Exit quietly.
        return


# Advisory-warning roll-up (③): child checks emit a per-step warning count via the
# X3 stderr channel (pipeline_log.emit_stderr_warn_summary); the parent tallies them
# here and surfaces the roll-up in the final summary so a mid-log advisory block
# (cloud_reading_lint / speed_qa / manim_vision_qa / dead-air) cannot be missed by a
# reader who scans only the 'Pipeline Complete' tail.
_advisory_warn_counts: dict[str, int] = {}

# the roll-up above is printed ONLY by the 'Pipeline Complete' box, so
# every gate that aborts (sys.exit(1)) used to discard advisories that earlier steps
# had already produced. An earlier episode shipped audio with a mis-read word that the pre-build
# cloud_reading_lint HAD flagged: the image-QA gate aborted before the summary, and the
# next (partial) build skipped the audio step, so the warning was never re-shown.
# `shown` is set by the normal summary; the atexit hook below fires only when the
# summary never ran, so successful builds keep byte-identical output.
_advisory_rollup_state: dict[str, bool] = {"shown": False}

# Steps whose advisory checks are re-run only when that step itself re-runs. Used to
# warn that a partial rebuild did NOT re-validate them.
_ADVISORY_STEPS: dict[str, str] = {
    "audio": "cloud_reading_lint / stt_qa / speed_qa",
    "images": "画像 Vision QA (Gate 2)",
    "visuals": "manim_vision_qa / manim_text_collision_qa / route-legend",
    "credits": "description staleness / intro-semantic",
}


def _format_advisory_rollup() -> str:
    return "  ".join(f"{k}={v}" for k, v in _advisory_warn_counts.items())


def _flush_advisory_rollup_on_abort() -> None:
    """Surface accumulated advisories when the run ended WITHOUT the final summary."""
    if _advisory_rollup_state["shown"] or not _advisory_warn_counts:
        return
    try:
        print(f"\n{'=' * 60}")
        print(f"  [!] 中断前に検出済みの advisory warnings -- {_format_advisory_rollup()}")
        print(
            "      内容は上のログに出ています。中断の原因を直して再開する前に必ず読んでください。"
        )
        print("      部分ビルド (--steps) で当該ステップを飛ばすと、この警告は再掲されません。")
        print(f"{'=' * 60}")
    except Exception:
        pass


atexit.register(_flush_advisory_rollup_on_abort)

# parent-side auth-probe warnings raised mid-build (a token that was valid at
# startup expired before a late Claude QA step). Surfaced prominently in the final
# summary so the "QA silently skipped" case is unmissable.
_auth_probe_warnings: list[str] = []


def _reprobe_claude_mid_build(context: str, resume_hint: str, skip: bool) -> bool:
    """ mid-build auth re-probe before a late Claude-dependent QA step.

    Returns True if Claude is reachable (proceed with the step), False if the
    token looks expired/unreachable. On failure it does NOT abort (these late QA
    steps are advisory / never-blocking, and the expensive assets are already
    built) -- instead it prints a LOUD notice, records a roll-up warning, and the
    caller SKIPS the step (running it would only yield a buried cascade of
    "Claude returned no output"). `skip` short-circuits to True (--skip-auth-probe).
    """
    if skip:
        return True
    ok, reason, msg = _preflight_claude_cli()
    if ok:
        return True
    banner = (
        f"Claude CLI auth 失効の可能性 ({reason}) -- {context} を skip します。\n"
        f"    {msg}\n"
        f"    再認証: claude setup-token  →  再開: {resume_hint}"
    )
    print(f"\n{'!' * 60}")
    print(f"  {banner}")
    print(f"{'!' * 60}\n")
    _auth_probe_warnings.append(f"{context}: {reason} ({resume_hint})")
    try:
        pipeline_log.emit(
            pipeline_log.LEVEL_WARNING,
            "auth_probe",
            "claude auth expired mid-build",
            reason=reason,
            context=context,
        )
    except Exception:
        pass
    return False


def _review_snapshot(episode_dir: str, src_dir: str, enabled: bool = True) -> None:
    """ビルド前に現行 output_final.mp4 のフレームハッシュ等を baseline に採る。

    ビルドは動画を上書きするので、**ここで採らないと「触っていない所は変わって
    いない」を後から証明できない**。証明が無いままリールだけ見せるのは、見せな
    かった部分について裏付けの無い主張をすることになる (の設計議論)。

    full build と `--rebuild-scene` の両方から呼ぶためのヘルパー。後者は
    full-build 経路へ入らず return するので、共有しないと**リールが最も要る
    「1 シーンだけ直す」場面で丸ごと抜ける**。
    """
    if not enabled or not os.path.exists(os.path.join(episode_dir, OUTPUT_FINAL)):
        return
    try:
        _sdir = os.path.join(os.path.dirname(src_dir), "scripts")
        if _sdir not in sys.path:
            sys.path.insert(0, _sdir)
        import review_reel as _rr

        _rr.snapshot(episode_dir)
    except Exception as e:  # a snapshot must never block a build
        print(f"  [!] レビュー用 baseline を作れませんでした: {type(e).__name__}: {e}")


def _review_reel_run(
    episode_dir: str, src_dir: str, enabled: bool = True, copy_to_temp_videos: bool = True
) -> None:
    """ビルド後に変更シーンのリールを出し、未変更区間の同一性を証明する。

    1 行の修正を確かめるために 17 分を見直す負担が、**直せば直る欠陥を「触らない」
    に倒していた**。リールはそれを変更シーンだけに縮め、証明はリールが映さない
    部分を受け持つ。`_review_snapshot` と同じ理由で full build と
    `--rebuild-scene` の両方から呼ぶ。
    """
    if not enabled:
        return
    try:
        _sdir = os.path.join(os.path.dirname(src_dir), "scripts")
        if _sdir not in sys.path:
            sys.path.insert(0, _sdir)
        import review_reel as _rr

        print(f"\n{'=' * 60}")
        print("  Review reel")
        print(f"{'=' * 60}")
        reel = _rr.run(episode_dir, copy_to_temp_videos=copy_to_temp_videos)
        warns = len(reel.get("suspects") or [])
        if reel.get("status") == "video_not_rebuilt":
            # Scenes changed but the shipped mp4 did not -- the fix never reached
            # the video. Counted so the summary roll-up shows it.
            warns += 1
        if warns:
            # Scenes nobody edited that nonetheless changed are exactly the ones the
            # reel does NOT show, so they have to reach the roll-up the reader scans.
            _advisory_warn_counts["review_reel"] = warns
    except Exception as e:  # never let the reviewer break a finished build
        print(f"\n  [!] レビューリールを生成できませんでした: {type(e).__name__}: {e}")


def _run_pre_visuals_checks(
    episode_dir: str, scene_json: str, config: dict, args, src_dir: str
) -> None:
    """visuals をレンダする**前**に走る検査群 (/ ある回-063 /)。

    main() の中に 230 行のべた書きで並んでいたものを関数にした。**構造そのものが事故を
    生んでいた**のが理由で、scene_definition の読み込みが の abort ゲート
    (`--allow-empty-template-params`) の内側にあったために、そのフラグを付けると
    無関係な advisory 6 件が道連れで黙っていた (2026-08-06 の再検証で発見)。1 つの
    関数に集めて各検査が自分のガードだけを持つ形にすると、同じ取り違えが起きにくい。

    副作用のみ (print / `_advisory_warn_counts` への計上 / 違反時の sys.exit)。
    振る舞いは抽出前と同一 -- 文は 1 つも書き換えていない (インデントのみ)。
    """
    # G1: Clear stale _fallback_scenes.json from previous
    # build round so verify_outputs detects only the current build's
    # Manim fallbacks. Prevents false carry-over warnings.
    _fallback_sidecar = os.path.join(episode_dir, "visuals", "_fallback_scenes.json")
    if os.path.exists(_fallback_sidecar):
        try:
            os.remove(_fallback_sidecar)
        except OSError:
            pass

    # lint Manim factual-claim consistency (episode scope, γ).
    # Templates without LINT_FACTUAL_CLAIMS metadata are skipped.
    try:
        from qa_manim_consistency import lint_manim_factual_claims

        with open(scene_json, encoding="utf-8") as _f:
            _scene_def_for_lint = json.load(_f)
        _manim_dir = os.path.join(src_dir, "manim_templates")
        print("\nManim factual-claim lint (episode scope):")
        _warns = lint_manim_factual_claims(_scene_def_for_lint, _manim_dir)
        print(f"{_warns} warning(s)")
        pipeline_log.emit(
            pipeline_log.LEVEL_WARNING if _warns else pipeline_log.LEVEL_INFO,
            "lint_b10",
            "manim factual-claim lint complete",
            warning_count=_warns,
        )
    except Exception as _e:
        pipeline_log.emit(
            pipeline_log.LEVEL_WARNING,
            "lint_b10",
            "manim lint skipped (exception)",
            error=f"{type(_e).__name__}: {_e}",
        )
        print(f"lint skipped: {_e}")

    # scene_definition はこの先の検査が全部使うので、ゲートの外で 1 回だけ読む。
    # **以前は の abort ゲート `--allow-empty-template-params` の内側で
    # 読んでいた**ため、そのフラグを付けると 尺不足 / 画面年号の追跡 /
    # ナレーションと画面の不一致 / timeline 凡例 / route_map 凡例ラベル /
    # route_map 地名カバレッジ の **6 つの advisory 検査が道連れで黙った**。
    # フラグの名前は「空 params を許す」であって「検査を止める」ではない。
    try:
        with open(scene_json, encoding="utf-8") as _f:
            _sd_b60 = json.load(_f)
    except Exception as _e:
        _sd_b60 = {}
        print(f"[visuals] scene_definition.json を読めませんでした: {_e}")

    # backstop: a data-driven reused template with EMPTY params
    # silently renders its self-test default -- another episode's data
    #. The template's own guard only catches PARTIAL
    # params. Assert the data param here, before the expensive visuals
    # render, and fail fast unless explicitly allowed.
    _tmpl_viol = []
    if not args.allow_empty_template_params:
        try:
            from qa_manim_consistency import check_reused_template_params

            _tmpl_viol = check_reused_template_params(_sd_b60)
        except Exception as _e:
            _tmpl_viol = []
            print(f"reused-template param check skipped: {_e}")

    # params present but the scene is too short to draw them
    #. Advisory: the content is correct, only the budget is wrong, so
    # this must not block a build the way's wrong-data case does.
    try:
        from qa_manim_consistency import check_template_duration_budget

        _timing_path = os.path.join(episode_dir, "timing.json")
        if os.path.exists(_timing_path):
            with open(_timing_path, encoding="utf-8") as _f:
                _timing_b78 = json.load(_f)
            _dur_viol = check_template_duration_budget(_sd_b60, _timing_b78)
        else:
            _dur_viol = []
    except Exception as _e:
        _dur_viol = []
        print(f"template duration-budget check skipped: {_e}")
    if _dur_viol:
        for _v in _dur_viol:
            print(
                f"  [WARN] {_v['scene_id']} ({_v['template']}): "
                f"{_v['items']} 件を描くのに {_v['duration']}s しかありません "
                f"(目安 {_v['required']}s 以上)。ナレーションを厚くするか "
                f"データを減らしてください。このままだと途中で切れます"
            )
        # Parent-side check: tally directly (emit_stderr_warn_summary is
        # the CHILD path -- the parent never demuxes its own stderr).
        _advisory_warn_counts["lint_b78_template_duration"] = len(_dur_viol)

    # misreading: on-screen years that come from the SCENE (route_map route[].year /
    # timeline_recap milestones) are invisible to the template-metadata lint
    # above, so an LLM-inferred year rode onto the map unchallenged.
    try:
        from qa_manim_consistency import check_onscreen_years_traceable

        _year_findings = check_onscreen_years_traceable(_sd_b60, config)
    except Exception as _e:
        _year_findings = []
        print(f"[an earlier episode] on-screen year traceability check skipped: {_e}")
    if _year_findings:
        for _v in _year_findings:
            print(
                f"  [YEAR][WARN] {_v['scene_id']} ({_v['kind']}): 画面に出る年号 "
                f"{'/'.join(_v['years'])} がナレーションにも verified_facts にも "
                f"ありません。出典を確認して config に記録するか、表示から外して"
                f"ください (LLM の推定値がそのまま焼かれる経路です)"
            )
        _advisory_warn_counts["lint_onscreen_years"] = len(_year_findings)

    # An earlier episode follow-up: a timeline colour that splits a track but has no
    # legend entry. The template drops dead legend entries and hides a
    # legend too small to distinguish anything, but it cannot invent the
    # NAME of a colour that is used -- that is an editorial call.
    # misreading: the narration names something the assigned MODE does not
    # draw (it said "四本の矢印" while the line chart was on screen).
    # Only the template knows what each mode puts up, so templates
    # declare it and this compares; templates without the declaration
    # are skipped.
    try:
        from qa_manim_consistency import check_narration_names_absent_visual

        _vis_viol = check_narration_names_absent_visual(_sd_b60, _manim_dir)
    except Exception as _e:
        _vis_viol = []
        print(f"[an earlier episode] narration/visual element check skipped: {_e}")
    if _vis_viol:
        for _v in _vis_viol:
            print(
                f"  [VISUAL][WARN] {_v['scene_id']}: ナレーションが "
                f"{'/'.join(_v['words'])} に触れていますが、"
                f"{_v['template']} の mode={_v['mode']} は描きません。"
                f"画面に合わせて書き直すか、mode を変えてください"
            )
        _advisory_warn_counts["lint_narration_visual"] = len(_vis_viol)

    try:
        from qa_manim_consistency import check_timeline_legend_coherence

        _leg_viol = check_timeline_legend_coherence(_sd_b60)
    except Exception as _e:
        _leg_viol = []
        print(f"[an earlier episode] timeline legend coherence check skipped: {_e}")
    if _leg_viol:
        for _v in _leg_viol:
            print(
                f"  [LEGEND][WARN] {_v['scene_id']}: {_v['track']} の色 "
                f"{'/'.join(_v['unnamed'])} が画面に出ますが凡例にありません。"
                f"色を分けるなら legend に名前を足し、意味がないなら"
                f"その track の色を揃えてください (見る側に手がかりがありません)"
            )
        _advisory_warn_counts["lint_timeline_legend"] = len(_leg_viol)

    # misreading: the route_map sibling of the check above. `legend_labels`
    # maps a category to ONE label, and nothing verified that the label
    # is true for every route in that category.
    # Route labels are short free-form Japanese, so this is an LLM
    # advisory review -- correction=null, never blocks the build.
    if not args.skip_route_legend_check:
        try:
            from route_legend_check import format_report, run_route_legend_check

            _rl_report = run_route_legend_check(
                _sd_b60,
                episode_dir,
                config.get("mathematician_ja") or config.get("mathematician", ""),
            )
            _rl_issues = _rl_report.get("issues", []) or []
            if _rl_issues:
                print(format_report(_rl_report))
                print(
                    "    -> 凡例ラベルは advisory。史実を確認して legend_labels か "
                    "route[].category を直してください (鵜呑み禁止)"
                )
                _advisory_warn_counts["lint_route_legend"] = len(_rl_issues)
        except Exception as _e:
            print(f"[an earlier episode] route_map legend coherence check skipped: {_e}")

    # the same map, checked from the other side. Every existing
    # route_map guard is about LAYOUT (collisions, clipping, ownership,
    # legend colours); none asks whether a place the narration names is
    # actually ON the map. An earlier episode talked about the Pyrenees over a map
    # that had no such point, and the viewer could not locate what they
    # had just heard. String matching cannot do this (a place named in
    # the text is not the same as a place the subject went to), so it is
    # an LLM advisory -- correction=null, never blocks the build.
    if not args.skip_route_place_check:
        try:
            from route_place_check import format_report as _rp_format
            from route_place_check import run_route_place_check

            _rp_report = run_route_place_check(
                _sd_b60,
                episode_dir,
                config.get("mathematician_ja") or config.get("mathematician", ""),
            )
            _rp_issues = _rp_report.get("issues", []) or []
            if _rp_issues:
                print(_rp_format(_rp_report))
                print(
                    "    -> 地名欠落は advisory。地図に点を足すか、ナレーションから"
                    "外すか、対象外かを人間が決めてください (鵜呑み禁止)"
                )
                _advisory_warn_counts["lint_route_place"] = len(_rp_issues)
        except Exception as _e:
            print(f"route_map place coverage check skipped: {_e}")

    if _tmpl_viol:
        for _v in _tmpl_viol:
            print(
                f"  {_v['scene_id']} ({_v['template']}): required "
                f"param '{_v['param']}' is missing/empty -> would render "
                f"the template's self-test default (another episode's "
                f"data). Populate visual.params.{_v['param']}."
            )
        pipeline_log.emit(
            pipeline_log.LEVEL_CRITICAL,
            "lint_b60_template_params",
            "reused-template param preflight aborted pipeline",
            violation_count=len(_tmpl_viol),
        )
        pipeline_log.close()
        print(
            "\nempty data-driven template params detected. "
            "Populate the data param (e.g. timeline_recap.milestones), "
            "or use --allow-empty-template-params for an intentional "
            "self-test render."
        )
        sys.exit(1)


def _run_route_map_preflight(scene_json: str, args) -> None:
    """ Layer 2: route_map の衝突 preflight (STOP ゲート)。両経路で共有する。

    `--rebuild-scene` からこれが呼ばれていなかったことは `pitfalls.md` に
    「将来課題」として 1 件だけ書かれていたが、実際には**部分再ビルドは検査を
    1 つも通っていなかった** (2026-08-06 の棚卸し)。route_map を 1 シーンだけ
    直すのは典型的な部分再ビルドなので、ここが抜けると衝突したまま焼ける。
    """
    if args.skip_route_preflight:
        return
    try:
        from visual_generator import route_map_preflight

        # misreading: label-ownership and line-through-label findings come
        # back here rather than in `_unresolved` -- they are advisory,
        # so they must reach the roll-up the reader actually scans
        # instead of scrolling past in the middle of the log.
        _route_advisories: list = []
        _unresolved = route_map_preflight(
            scene_json,
            allow=args.allow_route_collision,
            auto_fix=args.auto_fix_route_collisions,
            advisory_out=_route_advisories,
        )
        if _route_advisories:
            _advisory_warn_counts["route_map"] = len(_route_advisories)
        if _unresolved and not args.allow_route_collision:
            pipeline_log.emit(
                pipeline_log.LEVEL_CRITICAL,
                "lint_b11",
                "route_map preflight aborted pipeline",
                unresolved_count=len(_unresolved) if hasattr(_unresolved, "__len__") else None,
            )
            pipeline_log.close()
            print(
                "\nroute_map preflight aborted pipeline. "
                "Fix collisions and re-run, or use "
                "--allow-route-collision / --auto-fix-route-collisions / "
                "--skip-route-preflight."
            )
            sys.exit(1)
        pipeline_log.emit(
            pipeline_log.LEVEL_WARNING
            if (_unresolved or _route_advisories)
            else pipeline_log.LEVEL_INFO,
            "lint_b11",
            "route_map preflight complete",
            unresolved_count=len(_unresolved) if hasattr(_unresolved, "__len__") else 0,
            advisory_count=len(_route_advisories),
            allow=bool(args.allow_route_collision),
            auto_fix=bool(args.auto_fix_route_collisions),
        )
    except SystemExit:
        raise
    except Exception as _e:
        pipeline_log.emit(
            pipeline_log.LEVEL_WARNING,
            "lint_b11",
            "route_map preflight skipped (exception)",
            error=f"{type(_e).__name__}: {_e}",
        )
        print(f"route_map preflight skipped: {_e}")


def _run_post_visual_lints(
    episode_dir: str, scene_json: str, src_dir: str, args, scenes: str | None = None
) -> None:
    """visuals をレンダした**後**の検査 (白帯 / Vision QA / bbox 衝突)。

    `scenes` を渡すと Vision QA をそのシーンだけに絞る (Claude vision は scene 数に
    比例して課金・所要時間が伸びるので、1 シーンの再 render に 20 シーン分を投げない)。
    白帯と bbox 衝突は決定論で速い (実測 13.8 秒 / 17 scene) ので絞らない。
    """
    # ─── レンダ後の白帯チェック (納品物検査) ───
    # source 画像の白縁は ken_burns COVER 拡大でむしろ広がる。images step の白縁 lint は source のみ検査する
    # ため、レンダ動画フレームを直接測って assemble 前に捕捉する。
    try:
        # scripts/ を sys.path に通してから import する。source 白縁チェック
        # (images step) と対称。これが無いと、images step を経由しない部分
        # リビルド (--steps visuals 等) で scripts/ が path に無く、
        # `No module named 'lint_image_borders'` で silent skip していた
        # (images step が先に走る full run では相乗りで動いていた)。
        _scripts_dir = os.path.join(src_dir, "..", "scripts")
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from lint_image_borders import run_video as _vborder

        _vw = _vborder(os.path.join(episode_dir, "visuals"))
    except Exception as _e:
        _vw = []
        print(f"video border check skipped: {_e}")
    if _vw:
        severe = [v for v in _vw if v["max_pct"] >= 0.08]
        print(f"\n{'!' * 60}")
        print(f"  レンダ動画 {len(_vw)} 本に白帯 (ken_burns で消えない):")
        for v in _vw:
            bd = ", ".join(f"{k}={p * 100:.0f}%" for k, p in v["bands_pct"].items())
            print(f"    - {v['video']}: {bd}")
        print(
            "  対処: python scripts/lint_image_borders.py "
            f"{os.path.join(episode_dir, 'images')} --trim でクロップ -> visuals 再描画"
        )
        print(f"{'!' * 60}")
        if severe and not args.allow_video_borders:
            if not _confirm_continue(
                "白帯>=8% は ken_burns で消えません。source を --trim し visuals 再描画を推奨。"
            ):
                print("Pipeline aborted (video border).")
                sys.exit(1)

    # Manim Vision QA (P5): 各 Manim/route_map/timeline フレームを Claude
    # Sonnet vision で「概念が伝わるか/無意味な動き/判別不能な形/ラベル衝突」
    # 判定。決定論 lint (Y座標/MathTex/末尾静止) が捕まえない意味・美観の欠陥
    # を出荷前に検出。
    # advisory (Anthropic Max 内コスト0)。
    # the visuals step lands ~30-40 min into a build (after audio /
    # photos / image-gen / manim render), the canonical window for the
    # startup OAuth token to have expired. Re-probe right before this Claude
    # Vision QA so a dead token is surfaced loudly (and the step skipped)
    # instead of the Vision QA silently returning "no output" per scene.
    vqa_script = os.path.join(os.path.dirname(src_dir), "scripts", "manim_vision_qa.py")
    if os.path.exists(vqa_script):
        if _reprobe_claude_mid_build(
            "Manim Vision QA",
            "python src/pipeline.py <config> --steps visuals,credits --skip-script",
            skip=args.skip_auth_probe,
        ):
            vqa_cmd = [sys.executable, vqa_script, scene_json]
            if scenes:
                vqa_cmd += ["--scenes", scenes]
            run_step("manim_vision_qa (Vision: 意味/動き/衝突)", vqa_cmd, required=False)

    # misreading: deterministic text-collision preflight. manim_vision_qa (Sonnet
    # vision) MISSED the gp_ap/curve label proximity -- the user found those by
    # eye. This complements it: it re-runs each Manim mode's construct() with a
    # no-render mock, captures Text/MathTex bounding boxes, and flags stacks that
    # overlap a column and near-touch/overlap vertically. Deterministic; the
    # LaTeX cache-hits the just-rendered visuals so it is fast. advisory.
    collide_script = os.path.join(os.path.dirname(src_dir), "scripts", "manim_text_collision_qa.py")
    if os.path.exists(collide_script):
        run_step(
            "manim_text_collision_qa (決定論 bbox 衝突)",
            [sys.executable, collide_script, scene_json],
            required=False,
        )


def _run_pre_assemble_guards(
    episode_dir: str, scene_json: str, timing_json: str, steps: list[str], args
) -> None:
    """assemble の**前**に走る 3 つの stale ゲート (/ Guard-B,B2 / Guard-B3)。

    `steps` はこの実行で走った (走る) ステップ名。部分再ビルドは audio も
    subtitles も回すので Guard-B / B3 は自動的に skip され、 だけが効く
    (= 1 シーンだけ再 render したのに他の scene の尺が動いていないか)。
    """
    # stale-visual preflight。timing 刷新後に再 render されなかった
    # visual を尺照合で検出し、新音声 + 旧尺 visual の silent desync を fail
    # fast で止める。
    if not args.allow_stale_visuals:
        stale = _visual_staleness_preflight(episode_dir, timing_json)
        if stale:
            print("\nassemble preflight: visual と timing.json の尺が不一致です")
            for s in stale:
                vd = s["visual_dur"]
                vd_s = f"{vd}s" if vd is not None else "N/A"
                print(
                    f"  - {s['scene_id']}: visual={vd_s} / timing={s['expected']}s -- {s['reason']}"
                )
            print(
                "\n  timing 刷新後に visuals の再 render 漏れの可能性があります "
                "(音声/字幕と desync する納品事故)。\n"
                "  対処: `--steps visuals,assemble,...` で visuals を再 render して"
                "から assemble してください。\n"
                "  意図的に旧 visual で進める場合のみ `--allow-stale-visuals` を付与。"
            )
            sys.exit(1)

    # Guard-B: subtitle-stale preflight。narration 編集後に
    # subtitles を再生成せず assemble すると字幕(旧)/音声(新)が desync する
    #。この run で subtitles を再生成する (steps に
    # 含む) なら stale ではないので skip。
    if "subtitles" not in steps and not args.allow_stale_subtitles:
        sub_mismatch = _subtitle_staleness_check(episode_dir, scene_json)
        if sub_mismatch:
            print(
                "\n[Guard-B] assemble preflight: subtitles.srt が現在の narration/timing より古い"
            )
            print(f"  subtitles staleness: {sub_mismatch}")
            print(
                "  narration 編集 または 読み/速度正規化による音声尺の刷新後に "
                "subtitles を再生成していません (字幕/音声 desync で納品する事故)。\n"
                "  対処: `--steps subtitles,visuals,assemble,bgm` のように subtitles を"
                "含めて再実行。\n"
                "  意図的に旧字幕で進める場合のみ `--allow-stale-subtitles` を付与。"
            )
            sys.exit(1)

    # Guard-B3: 字幕の**本文**は timing.json 由来なので、subtitles を再生成
    # しても直らない。直るのは audio を回したときだけ。したがって上の
    # Guard-B/B2 とは**別のゲート**で見る -- 同じゲート ("subtitles" を
    # 回さないとき) に乗せると、この desync が起きる当のシナリオ
    # `--steps subtitles,assemble,bgm` で一度も走らない。
    if "audio" not in steps and not args.allow_stale_subtitles:
        text_mismatch = _subtitle_text_staleness_check(episode_dir, scene_json)
        if text_mismatch:
            print("\n[Guard-B3] assemble preflight: 字幕の本文が narration より古い")
            print(f"  {text_mismatch}")
            print(
                "  字幕の本文は timing.json の sentences[].text から作られ、"
                "timing.json を書くのは audio ステップです。\n"
                "  **subtitles だけ回しても編集前の本文のまま焼き直されます。**\n"
                "  対処: `--steps audio,subtitles,assemble,bgm` のように audio から再実行。\n"
                "  意図的に旧字幕で進める場合のみ `--allow-stale-subtitles` を付与。"
            )
            sys.exit(1)


def _run_output_verification(
    episode_dir: str, src_dir: str, config: dict, args, steps: list[str], scene_json: str
) -> tuple[list[str], int]:
    """出力検査 + レビュー用コピー + post_build_verify + レビューリール。

    ビルドの**終わり**にやることを 1 か所に集めた。full build にしか無かったため、
    `--rebuild-scene` で出荷物を作り直しても post_build_verify (構造検査 11 件) も
    verify_outputs も走らず、temp_videos のコピーも更新されなかった
    (= ある回で 1 レビュー周回を無駄にしたのと同じ事故が、部分再ビルドでは
    そのまま起きうる状態だった)。

    Returns (verify_outputs の警告, post_build_verify の警告数)。
    """
    verify_warnings = verify_outputs(episode_dir, steps, scene_json)
    print(f"\n{'=' * 60}")
    print("  Output Verification")
    print(f"{'=' * 60}")
    if not verify_warnings:
        print("  [OK] All expected outputs present for ran steps.")
    else:
        print(f"  [WARN] {len(verify_warnings)} verification issue(s):")
        for w in verify_warnings:
            print(w)

    # ─── Review copy + post-build structural verify ───────────────────────
    # The reviewer watches temp_videos/<ep>_output_final.mp4, not the file in the
    # episode directory. On an earlier episode the copy was not refreshed and the reviewer spent
    # a whole pass re-reporting four defects that the new build had already fixed.
    # Copying is the standing workflow, so the pipeline does it rather than leaving
    # it to be remembered; check 8 below still verifies the result.
    _final_ready = os.path.exists(os.path.join(episode_dir, OUTPUT_FINAL))
    if _final_ready and not args.no_temp_video_copy:
        try:
            _tv = os.path.join(os.path.dirname(src_dir), "temp_videos")
            if os.path.isdir(_tv):
                _dst = os.path.join(_tv, f"{os.path.basename(episode_dir)}_{OUTPUT_FINAL}")
                shutil.copy2(os.path.join(episode_dir, OUTPUT_FINAL), _dst)
                print(f"\n  [review] temp_videos へコピーしました: {_dst}")
        except OSError as e:
            print(f"\n  [!] temp_videos へのコピーに失敗: {e} -- 手でコピーしてください")

    post_build_warnings = 0
    if _final_ready and not args.skip_post_build_verify:
        try:
            # scripts/ is only put on sys.path inside particular step blocks, so a run
            # that skipped those would fail this import and degrade to a printed note --
            # the same silent-disable this block exists to prevent.
            _sdir = os.path.join(os.path.dirname(src_dir), "scripts")
            if _sdir not in sys.path:
                sys.path.insert(0, _sdir)
            import post_build_verify as _pbv

            _subject = config.get("mathematician_ja") or config.get("mathematician") or "(unknown)"
            # エピソード配下に置く。リポジトリ直下の共有ディレクトリに scene_id 名で
            # 書くと、別 ep の検証が [ACTION] の指す絵を黙って差し替える。
            _checks = _pbv.run_all(
                Path(episode_dir).resolve(),
                Path(episode_dir).resolve() / "_qa_frames",
                _subject,
            )
            print(f"\n{'=' * 60}")
            print(f"  Post-build Verify ({len(_checks)} checks)")
            print(f"{'=' * 60}")
            for _name, _res in _checks:
                _st = _res.get("status", "?")
                print(f"  [{_st}] {_name}")
                if _st in ("WARN", "ERROR", "PARTIAL"):
                    post_build_warnings += 1
                    for _k, _v in _res.items():
                        if _k != "status":
                            print(f"        {_k}: {_v}")
            # The "go and look at these" lines come from the same helper the CLI
            # uses. Printing only the statuses here left the corner sheet's path
            # unmentioned in exactly the run where it is produced.
            for _line in _pbv.format_actions(_checks):
                print(f"  {_line}")
            if post_build_warnings:
                _advisory_warn_counts["post_build_verify"] = post_build_warnings
        except Exception as e:  # never let the verifier break a finished build
            print(f"\n  [!] post_build_verify を実行できませんでした: {type(e).__name__}: {e}")

    if _final_ready:
        _review_reel_run(
            episode_dir,
            src_dir,
            enabled=not args.no_review_reel,
            copy_to_temp_videos=not args.no_temp_video_copy,
        )

    return verify_warnings, post_build_warnings


def _tally_advisory_warning(event: dict) -> None:
    """Record a child advisory warning count from an X3 stderr marker event."""
    try:
        if event.get("level") == pipeline_log.LEVEL_WARNING:
            wc = (event.get("metadata") or {}).get("warn_count")
            if isinstance(wc, int) and wc > 0:
                _advisory_warn_counts[event.get("step", "?")] = wc
    except Exception:
        pass


def _run_subprocess_with_stderr_capture(cmd: list[str]) -> int:
    """Run cmd with stdout pass-through and structured-stderr demux (X3).

    stdout is inherited (no parent capture) so child print output reaches the
    console exactly as before — this is what preserves baseline parity
    and keeps Manim/FFmpeg progress indicators intact.

    stderr is captured on a background daemon thread that demultiplexes:
    - Lines starting with the JSONL marker are merged into the central logger.
    - Other stderr lines (Python traceback, Manim error, FFmpeg warning) are
      re-emitted to console stderr unchanged.

    The thread design prevents a stderr buffer fill (deadlock) when stderr
    output is heavy enough to block child writes while parent waits. On
    Ctrl+C / KeyboardInterrupt the child is killed and the thread joined.

    Returns the child's exit code.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=None,  # inherit parent stdout — pass-through unchanged
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    drainer: threading.Thread | None = None
    if proc.stderr is not None:

        def _on_raw(line: str) -> None:
            sys.stderr.write(line)
            sys.stderr.flush()

        def _on_marker(event: dict) -> None:
            _tally_advisory_warning(event)
            pipeline_log.merge_child_event(event)

        drainer = threading.Thread(
            target=_drain_stderr,
            args=(proc.stderr, _on_marker, _on_raw),
            daemon=True,
        )
        drainer.start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        proc.wait()
        raise
    finally:
        # Ensure child cannot outlive parent on any error path.
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if drainer is not None:
            drainer.join(timeout=2.0)
    return proc.returncode


def _confirm_continue(noninteractive_hint: str) -> bool:
    """Ask whether to continue past a QA gate that flagged issues.

    In a non-interactive run (background task, CI, ``> log 2>&1`` with no TTY)
    ``input()`` gets EOF immediately, which previously looked like an opaque
    silent abort (: a backgrounded build died at the image-QA prompt with
    no explanation). When stdin is not a TTY we therefore DO NOT prompt: we
    print an actionable hint and abort deterministically (never auto-proceed
    past flagged issues without an explicit flag). Returns True to continue.
    """
    if not sys.stdin.isatty():
        print("   [non-interactive] stdin is not a TTY -- cannot prompt for confirmation.")
        print(f"   {noninteractive_hint}")
        return False
    try:
        return input("   Continue anyway? (y/N): ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        print("\n   Aborted.")
        return False


def run_step(step_name: str, cmd: list[str], required: bool = True) -> bool:
    """Run a pipeline step as subprocess. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"  Step: {step_name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    pipeline_log.step_start(step_name, command=" ".join(cmd))
    pipeline_progress.start_step(step_name)
    start = time.time()
    exit_code = _run_subprocess_with_stderr_capture(cmd)
    elapsed = time.time() - start
    pipeline_log.step_end(step_name, exit_code=exit_code, duration_ms=int(elapsed * 1000))
    pipeline_progress.end_step(step_name, exit_code, elapsed)

    if exit_code != 0:
        print(f"\n[FAIL] Step '{step_name}' failed (exit code {exit_code}, {elapsed:.1f}s)")
        if required:
            print("Pipeline aborted.")
            pipeline_progress.finish("failed")
            sys.exit(1)
        return False

    print(f"\n[OK] Step '{step_name}' complete ({elapsed:.1f}s)")
    return True


def _build_arg_parser() -> argparse.ArgumentParser:
    """CLI パーサを組み立てる。

    main() の中に置いたままだと **テストが本物の args を作れない**。回帰は手書きの
    ダミー namespace を使うことになり、フラグを 1 つ足すたびに黙って実物と乖離する
    (2026-08-06 の再検証で、部分再ビルドの検査を本物のヘルパーで通そうとしたら
    手書き args に `skip_route_legend_check` が無くて落ちた -- 検査は配線したのに、
    それを確かめるテストのほうが本物を再現できていなかった)。既定値ごと本物を作れる
    ようにして、回帰は `_build_arg_parser().parse_args([config])` を使う。
    """
    parser = argparse.ArgumentParser(
        description="Run the full sugakushiki video generation pipeline",
    )
    parser.add_argument("config_json", help="Path to episode_config.json")
    parser.add_argument(
        "--steps",
        default=None,
        help=f"Comma-separated list of steps to run (default: all). "
        f"Available: {','.join(ALL_STEPS)}",
    )
    parser.add_argument(
        "--skip-script",
        action="store_true",
        help="Skip script generation (use existing scene_definition.json)",
    )
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    parser.add_argument(
        "--allow-video-borders",
        action="store_true",
        help="レンダ動画の白帯>=8%%でも中断しない (既定は確認/中断)",
    )
    parser.add_argument(
        "--skip-manim", action="store_true", help="Use stubs instead of Manim rendering"
    )
    parser.add_argument(
        "--dry-run-audio", action="store_true", help="Estimate audio durations without VOICEVOX"
    )
    parser.add_argument(
        "--model", default="claude", help="Model for script generation (default: claude)"
    )
    parser.add_argument(
        "--no-subtitles", action="store_true", help="Skip subtitle overlay in final video"
    )
    parser.add_argument(
        "--qa",
        action="store_true",
        default=True,
        help="Run QA check after script generation (full: all agents, default: ON)",
    )
    parser.add_argument(
        "--qa-quick", action="store_true", help="Run quick QA (Sonnet agents only, ~25min)"
    )
    parser.add_argument(
        "--qa-retry",
        action="store_true",
        help="Re-generate script with QA feedback if issues found (comparison gate)",
    )
    parser.add_argument(
        "--qa-max-diff",
        type=float,
        default=0.20,
        help="Max allowed diff rate for QA retry (default: 0.20 = 20%%)",
    )
    parser.add_argument(
        "--qa-agents",
        default=None,
        help="Specific QA agents to run (comma-separated, e.g. fact,style)",
    )
    parser.add_argument(
        "--use-gemini-fact",
        action="store_true",
        help="Use Gemini Grounding for fact checking (web search enabled)",
    )
    parser.add_argument(
        "--skip-qa",
        action="store_true",
        help="Skip QA checks (script QA gate and standalone image QA)",
    )
    parser.add_argument(
        "--qa-allow-warn",
        action="store_true",
        help="Continue pipeline when QA reports WARN (warnings only). "
        "Critical issues still stop the pipeline.",
    )
    parser.add_argument("--skip-bgm", action="store_true", help="Skip BGM mixing step")
    parser.add_argument(
        "--bgm-file", default=None, help="BGM file path (overrides episode_config.json bgm.file)"
    )
    parser.add_argument(
        "--check-pronunciation",
        action="store_true",
        help="Check VOICEVOX pronunciation with Claude before synthesis (auto-enabled with --qa)",
    )
    parser.add_argument(
        "--skip-pronunciation-check",
        action="store_true",
        help="Skip pronunciation check even when --qa is active",
    )
    parser.add_argument(
        "--skip-reading-guard",
        action="store_true",
        help="skip VOICEVOX 誤読 pre-build guard (reading_guard.py). "
        "Default: enabled before audio step (advisory WARN, never blocks).",
    )
    parser.add_argument(
        "--force-regen-audio",
        action="store_true",
        help="re-synthesize every sentence, ignoring the per-sentence "
        "audio cache. Default: cache reuses unchanged wavs (NS-only edits "
        "re-synthesize just the changed sentences).",
    )
    parser.add_argument(
        "--allow-full-resynthesis",
        action="store_true",
        help="既存キャッシュがあるのに半数以上の文を再合成する、という予告が出ても "
        "止まらずに進む。Cloud は非決定的なので、再合成した文は尺が変わり "
        "visual の再 render まで波及する (ある回で 1 文の修正が 57 分になった)。",
    )
    parser.add_argument(
        "--force-regen-visuals",
        action="store_true",
        help=" Phase 2: re-render every scene, ignoring the per-scene "
        "visual cache. Default: the visuals step reuses unchanged scene mp4s "
        "and re-renders only scenes whose visual/params/template/source-image/"
        "duration changed (48min -> minutes on review iterations).",
    )
    parser.add_argument(
        "--normalize-cloud-speed",
        action="store_true",
        help="after Cloud TTS synthesis, atempo-normalize per-sentence "
        "articulation toward the episode median (Chirp3-HD varies speech rate "
        "24-31%% between adjacent sentences even in one session; per-sentence "
        "re-synth cannot converge). Off by default -- detection is always-on "
        "(advisory speed_qa_report.txt); this opt-in applies the fix. "
        "Cloud-only; inert for voicevox. Undo with cloud_speed_qa.py --restore.",
    )
    parser.add_argument(
        "--skip-fact-check",
        action="store_true",
        help="skip pre-script episode_config fact check",
    )
    parser.add_argument(
        "--fact-check-allow-warn",
        action="store_true",
        help="continue on WARNING (CRITICAL still aborts)",
    )
    parser.add_argument(
        "--skip-reference-check",
        action="store_true",
        help="skip references bibliographic review (advisory F layer, never blocks)",
    )
    parser.add_argument(
        "--skip-intro-check",
        action="store_true",
        help=" (F): skip narration->description.intro semantic review in the "
        "credits step (advisory, Claude, cached; never blocks)",
    )
    parser.add_argument(
        "--skip-route-legend-check",
        action="store_true",
        help="an earlier episode: skip the route_map legend-label coherence review in the visuals "
        "step (advisory, Claude, cached; never blocks)",
    )
    parser.add_argument(
        "--skip-route-place-check",
        action="store_true",
        help="skip the review of whether places named in the narration appear on "
        "the route_map (advisory, Claude, cached; never blocks)",
    )
    parser.add_argument(
        "--skip-auth-probe",
        action="store_true",
        help="skip the Claude CLI auth ping (startup preflight + mid-build "
        "re-probe). Use for offline / mechanical rebuilds where a stale token is ok.",
    )
    parser.add_argument(
        "--skip-post-build-verify",
        action="store_true",
        help="Skip the 9 post-build structural checks (scripts/post_build_verify.py) "
        "that run once output_final.mp4 exists.",
    )
    parser.add_argument(
        "--no-temp-video-copy",
        action="store_true",
        help="Do not copy output_final.mp4 into temp_videos/ (the review folder) "
        "when the build finishes.",
    )
    parser.add_argument(
        "--no-review-reel",
        action="store_true",
        help="skip the review reel (changed scenes only) and the proof that the "
        "unchanged sections are identical. Both the pre-build snapshot and the "
        "post-build comparison are disabled.",
    )
    parser.add_argument(
        "--skip-qa-image-narration",
        action="store_true",
        help="skip narration-image consistency check (Gate 2). Default: enabled with --qa.",
    )
    parser.add_argument(
        "--skip-portrait-lint",
        action="store_true",
        help="強化 H2: skip portrait_prompt_lint (Gemini Vision で reference 写真と source_prompt の特徴矛盾を catch、ある回 kimono mismatch 防御)。default: enabled when use_reference scenes + wiki_*.jpg refs exist。WARN only、build halt しない。",
    )
    parser.add_argument(
        "--skip-qa-script-only",
        action="store_true",
        help="Skip ONLY QA Gate 1 (script QA, ~15min). Useful for partial rebuilds "
        "where visuals/assets changed but narration did not. Gate 2 (image-narration "
        "consistency) still runs. Mutually inclusive with --skip-qa (which skips both).",
    )
    parser.add_argument(
        "--skip-route-preflight",
        action="store_true",
        help="skip route_map collision preflight (Layer 2). "
        "Layer 3 in-render WARN still runs.",
    )
    parser.add_argument(
        "--allow-route-collision",
        action="store_true",
        help="continue pipeline even if route_map collision is detected. "
        "Both preflight (Layer 2) and in-render (Layer 3) become advisory.",
    )
    parser.add_argument(
        "--auto-fix-route-collisions",
        action="store_true",
        help="opt-in 4-stage auto-fix of route_map collisions "
        "(label avoidance -> bounds expansion -> title fontsize -> legend relocation). "
        "Stages are cumulative and stop at the first one that resolves the collision. "
        "Mutates scene_definition.json with _route_map_auto_fix_log block.",
    )
    parser.add_argument(
        "--allow-empty-template-params",
        action="store_true",
        help="continue even if a data-driven reused template "
        "(e.g. timeline_recap) has empty params. WARNING: empty params make the "
        "template render its self-test default (another episode's data, e.g. "
        "Laplace's life events). Only use for an intentional self-test render.",
    )
    parser.add_argument("--skip-thumbnail", action="store_true", help="Skip thumbnail generation")
    parser.add_argument(
        "--allow-stale-visuals",
        action="store_true",
        help="skip the assemble stale-visual preflight (visual mp4 尺 vs "
        "timing.json). Use only when intentionally assembling with visuals that "
        "predate the current timing.",
    )
    parser.add_argument(
        "--allow-stale-subtitles",
        action="store_true",
        help="Guard-B: skip the assemble stale-subtitle preflight (narration hash vs "
        "subtitles.srt embedded hash). Use only when intentionally assembling with "
        "subtitles that predate the current narration.",
    )
    parser.add_argument(
        "--rebuild-scene",
        default=None,
        metavar="SCENE_ID",
        help="Partial rebuild: regenerate a single scene and re-run assembly+bgm. "
        "Exclusive with --steps, --skip-* flags. "
        "Runs the same guards as a full build (reading lint / STT / route_map "
        "preflight / stale-visual and stale-subtitle preflights / post_build_verify "
        "/ review reel); the expensive ones are narrowed to the rebuilt scene.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help="D1+ Phase 1: write structured JSON line events to PATH "
        "(in addition to stdout text). One JSON object per line with fields "
        "ts/step/level/episode_id/scene_id/msg/metadata. Severity levels: "
        "critical/warning/info. Default: disabled (no JSONL output, baseline parity).",
    )
    parser.add_argument(
        "--no-keep-awake",
        action="store_true",
        help="Do not keep the machine awake during the build (Windows). By "
        "default the pipeline prevents system sleep so a long/overnight build "
        "is not killed mid-run; this opts out.",
    )
    parser.add_argument(
        "--tts-engine",
        choices=["voicevox", "cloud"],
        default=None,
        help="TTS backend override. Default: episode_config.json 'tts.engine', "
        "else 'voicevox'. 'cloud' = Google Cloud TTS Chirp3-HD (needs "
        "GOOGLE_TTS_API_KEY; VOICEVOX GUI not required).",
    )
    parser.add_argument(
        "--tts-voice",
        default=None,
        help="Cloud TTS voice override (default: episode_config.json 'tts.voice', "
        "else ja-JP-Chirp3-HD-Enceladus). Ignored for voicevox.",
    )
    parser.add_argument(
        "--tts-rate",
        type=float,
        default=None,
        help="Cloud TTS speakingRate override (default: episode_config.json "
        "'tts.rate', else 0.90). Ignored for voicevox.",
    )
    return parser


def main():
    # Line-buffer stdout/stderr so a long run's log is monitorable in real time
    # even when redirected to a file. Without this, block-buffering makes the log
    # look frozen for minutes (observed when tailing pipeline_log during a build).
    #
    # encoding="utf-8" is the second half of the same call for a different reason:
    # this file prints em dashes, and modules imported into THIS process (
    # audio_generator, qa_retry) print characters the Windows console codepage
    # cannot represent at all. Without it those lines raise UnicodeEncodeError and
    # kill the run -- and they sit on warning paths, so the failure would land in
    # the middle of a long build rather than at startup. Subprocess steps need
    # their own guard; this one only covers what the parent prints.
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    parser = _build_arg_parser()
    args = parser.parse_args()

    # Keep the system awake for the (possibly multi-hour) build so it is not
    # killed by sleep mid-run; released automatically on exit. Override with
    # --no-keep-awake.
    if not args.no_keep_awake:
        _set_keep_awake(True)
        atexit.register(_set_keep_awake, False)

    # --rebuild-scene is exclusive with step-control flags
    if args.rebuild_scene:
        conflicting = []
        if args.steps:
            conflicting.append("--steps")
        if args.skip_script:
            conflicting.append("--skip-script")
        if args.skip_images:
            conflicting.append("--skip-images")
        if args.skip_bgm:
            conflicting.append("--skip-bgm")
        if args.skip_thumbnail:
            conflicting.append("--skip-thumbnail")
        if args.skip_manim:
            conflicting.append("--skip-manim")
        if conflicting:
            print(f"ERROR: --rebuild-scene cannot be combined with: {', '.join(conflicting)}")
            sys.exit(1)

    # Resolve paths
    config_path = os.path.abspath(args.config_json)
    episode_dir = os.path.dirname(config_path)
    scene_json = os.path.join(episode_dir, "scene_definition.json")
    timing_json = os.path.join(episode_dir, "timing.json")

    # Find src/ directory (relative to this script)
    src_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine which steps to run
    if args.steps:
        steps = [s.strip() for s in args.steps.split(",")]
        for s in steps:
            if s not in ALL_STEPS:
                print(f"ERROR: Unknown step '{s}'. Available: {', '.join(ALL_STEPS)}")
                sys.exit(1)
    else:
        steps = list(ALL_STEPS)
        if args.skip_script:
            steps.remove("script")
        if args.skip_images:
            steps.remove("images")

    # --skip-script overrides --steps (explicit intent to skip wins)
    if args.skip_script and "script" in steps:
        steps.remove("script")
    if args.skip_images and "images" in steps:
        steps.remove("images")
    if args.skip_bgm and "bgm" in steps:
        steps.remove("bgm")
    if args.skip_thumbnail and "thumbnail" in steps:
        steps.remove("thumbnail")

    # Verify config exists
    if not os.path.exists(config_path):
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)

    # ─── Structured JSONL logger init ──────────
    # Initialized BEFORE preflight so startup failures (Claude CLI
    # 401 / system-Python module miss / VOICEVOX down) surface as critical
    # JSONL events rather than just stdout text.
    episode_id = os.path.basename(episode_dir.rstrip(os.sep)) or "unknown"
    log_file_path = Path(args.log_file) if args.log_file else None
    pipeline_log.init_logger(log_file_path, episode_id)
    # Signal to subprocess children (advisory checks) that they run under the
    # pipeline, so their emit_stderr_warn_summary() fires for the final-summary
    # roll-up even when structured logging (--log-file) is disabled (the default).
    # Children inherit env; the parent's stderr demux + tally run regardless of
    # whether a JSONL logger was initialized.
    os.environ["PIPELINE_RUN"] = "1"

    # ─── machine-readable progress snapshot (always on) ────────────
    # Writes _pipeline_progress.json (overwritten each step boundary) so a
    # watcher can poll status/current_step/completion instead of guessing from
    # buffered stdout or wav/mp4 mtimes.
    pipeline_progress.init(episode_dir, episode_id, steps)

    # Load config early: the TTS engine affects preflight (Cloud needs no local
    # VOICEVOX server) and is threaded into the audio step + partial rebuild.
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    # Resolve TTS engine/voice/rate: CLI override > config 'tts' > defaults.
    # voice/rate stay None here when unset -> audio_generator fills Cloud defaults.
    tts_cfg = config.get("tts", {}) or {}
    tts_engine = args.tts_engine or tts_cfg.get("engine", "voicevox")
    tts_voice = args.tts_voice or tts_cfg.get("voice")
    tts_rate = args.tts_rate if args.tts_rate is not None else tts_cfg.get("rate")

    # ─── Preflight: fail fast on venv / Claude auth / VOICEVOX issues ───
    # a past run lost 57min on expired Claude token + 30min on system-Python run.
    # Cheap upfront checks avoid these dead-ends.
    # --rebuild-scene が実際に回すステップを**そのまま**渡す。以前は
    # ["assemble", "credits", "bgm"] という手書きの短縮版で、audio が抜けていた
    # ため **VOICEVOX サーバ疎通も Cloud API キーの存在確認も preflight で見て
    # いなかった** (どちらも `"audio" in steps` ゲート)。部分再ビルドは必ず音声を
    # 合成するので、落ちるならステップ 1 の奥ではなく起動時に落ちるべき。
    # "images" は ken_burns のときだけ走るが、preflight のどのゲートも見ていない
    # (Claude 疎通は visuals/credits で既に立つ) ので列挙しない。
    preflight_steps = (
        ["audio", "visuals", "assemble", "credits", "bgm"] if args.rebuild_scene else steps
    )
    run_preflight_checks(preflight_steps, engine=tts_engine, skip_auth_probe=args.skip_auth_probe)

    # ─── Validate config ─────────────────────────────────────────────────
    from config_validator import print_validation_result, validate_config

    val_errors, val_warnings = validate_config(config, config_path)
    val_ok = print_validation_result(val_errors, val_warnings, config_path)
    if not val_ok:
        print("\nPipeline aborted due to config validation errors.")
        print("Fix the errors above and re-run.")
        sys.exit(1)

    bgm_config = config.get("bgm", {})
    bgm_file = args.bgm_file or bgm_config.get("file", "")

    # per-episode 読み上げ速度。既定 0.87。global 定数を直接編集せず
    # episode_config.json の "speed_scale" で上書きし、audio step / partial
    # rebuild の両 audio 経路へ渡す (global 直編集の revert 忘れ hazard を排除)。
    speed_scale = config.get("speed_scale", 0.87)

    # BGM file path resolution: search multiple locations
    # Handles cases where config says "angels_dream.mp3" instead of "bgm/angels_dream.mp3"
    if bgm_file and not os.path.exists(bgm_file):
        project_root = os.path.dirname(src_dir)
        search_paths = [
            os.path.join(project_root, "bgm", os.path.basename(bgm_file)),
            os.path.join(project_root, bgm_file),
            os.path.join(episode_dir, bgm_file),
        ]
        for candidate in search_paths:
            if os.path.exists(candidate):
                bgm_file = candidate
                break

    # ─── Partial rebuild mode ────────────────────────────────────────────
    if args.rebuild_scene:
        # も通す。--rebuild-scene は「在庫を 1 シーンだけ直す」最短経路で、
        # **リールが最も要る場面そのもの**。この分岐は full-build 経路へ入らず
        # return するので、フックを 2 箇所へ明示的に置く必要がある。
        _review_snapshot(episode_dir, src_dir, enabled=not args.no_review_reel)
        _run_partial_rebuild(
            scene_id=args.rebuild_scene,
            config_path=config_path,
            episode_dir=episode_dir,
            config=config,
            src_dir=src_dir,
            bgm_file=bgm_file,
            bgm_config=bgm_config,
            tts_engine=tts_engine,
            tts_voice=tts_voice,
            tts_rate=tts_rate,
            force_regen=args.force_regen_audio,
            skip_intro_check=args.skip_intro_check,
            args=args,
        )
        # リールは `_run_output_verification` の中で回す (full build と同じ締め)。
        # ここで別に呼ぶと 2 度作ることになる。
        pipeline_progress.finish("complete", _output_final_summary(episode_dir))
        return  # Exit without entering the full-build path

    # Print plan
    print(f"\n{'=' * 60}")
    print("  数学史記 Pipeline")
    print(f"{'=' * 60}")
    print(f"  Config:      {config_path}")
    print(f"  Episode dir: {episode_dir}")
    print(f"  Steps:       {' → '.join(steps)}")
    if args.skip_manim:
        print("  Manim:       stubs (--skip-manim)")
    if args.dry_run_audio:
        print("  Audio:       dry-run (estimated)")
    if args.qa or args.qa_quick:
        qa_mode = "quick (Sonnet only)" if args.qa_quick else "full (all agents)"
        if args.skip_qa:
            qa_mode += " [SKIPPED]"
        print(f"  QA:          {qa_mode}")
        if args.qa_retry:
            print(f"  QA retry:    enabled (max diff: {args.qa_max_diff:.0%})")
        if args.use_gemini_fact:
            print("  Fact check:  Gemini Grounding (web search)")
    pron_active = (
        args.qa or args.qa_quick or args.check_pronunciation
    ) and not args.skip_pronunciation_check
    print(f"  Pronunciation: {'enabled' if pron_active else 'disabled'}")
    if "bgm" in steps:
        if bgm_file:
            print(f"  BGM:         {bgm_file} ({bgm_config.get('volume_db', -20)}dB)")
        else:
            print("  BGM:         not configured (will skip)")
    print(f"{'=' * 60}")

    pipeline_start = time.time()
    pipeline_log.emit(
        pipeline_log.LEVEL_INFO,
        "pipeline",
        "pipeline start",
        steps=steps,
        config_path=config_path,
        skip_qa=bool(args.skip_qa),
        skip_script=bool(args.skip_script),
        skip_images=bool(args.skip_images),
    )

    _review_snapshot(episode_dir, src_dir, enabled=not args.no_review_reel)

    # ─── Pre-script fact check (episode_config.json) ───────────────
    # C: Claude Sonnet knowledge-base check (verified_facts/key_episodes/theme)
    # D: arithmetic sanity (no LLM)
    # E: Wikidata cross-check (Phase 3, not yet wired)
    # default: any CRITICAL or WARNING aborts; --fact-check-allow-warn relaxes
    if "script" in steps and not args.skip_fact_check:
        try:
            from pre_script_fact_check import (
                print_pre_script_fact_check_report,
                run_pre_script_fact_check,
                save_report,
            )

            print("\nPre-script fact check on episode_config.json")
            _report = run_pre_script_fact_check(
                episode_config=config,
                episode_dir=episode_dir,
                use_references=not args.skip_reference_check,
            )
            print_pre_script_fact_check_report(_report)
            save_report(_report, episode_dir)
            _sev = _report.get("severity_counts", {})
            _crit = _sev.get("critical", 0)
            _warn = _sev.get("warning", 0)
            if _crit > 0:
                pipeline_log.emit(
                    pipeline_log.LEVEL_CRITICAL,
                    "lint_b17",
                    "pre-script fact check critical",
                    critical=_crit,
                    warning=_warn,
                )
                pipeline_log.close()
                print(
                    "CRITICAL detected -- aborting before script "
                    "step. Fix episode_config.json and re-run."
                )
                sys.exit(1)
            if _warn > 0 and not args.fact_check_allow_warn:
                pipeline_log.emit(
                    pipeline_log.LEVEL_WARNING,
                    "lint_b17",
                    "pre-script fact check warning (blocking)",
                    critical=_crit,
                    warning=_warn,
                )
                pipeline_log.close()
                print(
                    "WARNING detected -- aborting before script "
                    "step. Use --fact-check-allow-warn to continue."
                )
                sys.exit(1)
            if _warn > 0:
                pipeline_log.emit(
                    pipeline_log.LEVEL_WARNING,
                    "lint_b17",
                    "pre-script fact check warning (non-blocking)",
                    critical=_crit,
                    warning=_warn,
                )
            else:
                pipeline_log.emit(
                    pipeline_log.LEVEL_INFO,
                    "lint_b17",
                    "pre-script fact check ok",
                    critical=_crit,
                    warning=_warn,
                )
            print("OK (no blocking issues)")
        except SystemExit:
            raise
        except Exception as _e:
            pipeline_log.emit(
                pipeline_log.LEVEL_WARNING,
                "lint_b17",
                "pre-script fact check skipped (exception)",
                error=f"{type(_e).__name__}: {_e}",
            )
            print(f"pre-script fact check skipped due to error: {_e}")

    # ─── Step 1: Script generation ───────────────────────────────────────
    if "script" in steps:
        cmd = [
            sys.executable,
            os.path.join(src_dir, "script_generator.py"),
            config_path,
            "--output",
            scene_json,
            "--model",
            args.model,
            "--manim-templates",
            os.path.join(src_dir, "manim_templates"),
        ]
        run_step("script", cmd)
    else:
        if not os.path.exists(scene_json):
            print(f"ERROR: scene_definition.json not found: {scene_json}")
            print("Run without --skip-script or create it manually.")
            sys.exit(1)
        print(f"\n[SKIP] Skipping script generation (using existing {scene_json})")

    # ─── QA Gate 1: Script QA (optional) ─────────────────────────────────
    qa_requested = (args.qa or args.qa_quick) and not args.skip_qa and not args.skip_qa_script_only
    if qa_requested and os.path.exists(scene_json):
        print(f"\n{'=' * 60}")
        print("  QA Gate 1: Script Quality Check")
        print(f"{'=' * 60}")

        qa_cmd = [
            sys.executable,
            os.path.join(src_dir, "qa_checker.py"),
            scene_json,
            "--gate",
            "script",
        ]

        if args.qa_quick:
            qa_cmd.append("--quick")

        if args.qa_agents:
            qa_cmd.extend(["--agents", args.qa_agents])

        if args.use_gemini_fact:
            qa_cmd.append("--use-gemini-fact")

        qa_report_path = os.path.join(episode_dir, "qa_report_script.json")
        qa_cmd.extend(["--output", qa_report_path])

        print(f"  Command: {' '.join(qa_cmd)}\n")

        pipeline_log.step_start("qa_script", command=" ".join(qa_cmd))
        qa_start = time.time()
        qa_exit = _run_subprocess_with_stderr_capture(qa_cmd)
        qa_elapsed = time.time() - qa_start
        pipeline_log.step_end("qa_script", exit_code=qa_exit, duration_ms=int(qa_elapsed * 1000))

        if qa_exit == 1:
            print(f"\n[FAIL] QA FAILED ({qa_elapsed:.0f}s). Critical issues found.")
            print(f"   Report: {qa_report_path}")
            # Ask user whether to continue (non-interactive runs abort cleanly)
            if not _confirm_continue(
                "Fix scene_definition.json then re-run, or re-run with --skip-qa to bypass."
            ):
                print("Pipeline aborted (QA critical).")
                sys.exit(1)
        elif qa_exit == 2:  # ERROR
            print(f"\n[ERROR] QA ERROR ({qa_elapsed:.0f}s). Some agents failed.")
            print(f"   Report: {qa_report_path}")
            print("   Continuing pipeline (QA errors are non-blocking)...")
        else:
            # Check report for warnings (WARN status returns exit code 0)
            qa_has_warnings = False
            qa_fact_layer_present = True  # default True → old reports don't false-warn
            if os.path.exists(qa_report_path):
                try:
                    with open(qa_report_path, encoding="utf-8") as f:
                        qa_data_check = json.load(f)
                    warn_count = qa_data_check.get("summary", {}).get("warning", 0)
                    if warn_count > 0:
                        qa_has_warnings = True
                    # did the factual-verification layer actually run?
                    qa_fact_layer_present = qa_data_check.get("fact_layer_present", True)
                except (json.JSONDecodeError, FileNotFoundError):
                    pass

            # surface a fact-layer gap even on PASS. An earlier episode ran only
            # content/consistency (fact absent) and factual errors slipped through
            # silently. This makes the absence loud in the pipeline output.
            if not qa_fact_layer_present:
                print(f"\n{'!' * 60}")
                print("  [WARN] QA: 事実検証層 (FactChecker) が未実行です")
                print(f"{'!' * 60}")
                print("   この QA run は fact/fact_grounding を含みません。外部事実の正誤・")
                print("   cross-episode 矛盾は未検証です。--qa-agents に fact を含めて再実行する")
                print("   か、verified_facts / key_episodes を独立 verify してください。")
                print(f"   Report: {qa_report_path}")
                print(f"{'!' * 60}")

            if qa_has_warnings:
                print(f"\n[WARN] QA WARN ({qa_elapsed:.0f}s) -- {warn_count} warning(s) found.")
                print(f"   Report: {qa_report_path}")
                if args.qa_allow_warn:
                    print("   --qa-allow-warn set → continuing pipeline (WARN are advisory).")
                elif not args.qa_retry:
                    print("\n   Review the report, fix scene_definition.json, then re-run with:")
                    print(f"   python src/pipeline.py {args.config_json} --skip-script")
                    print("\n   To continue without fixing, re-run with --skip-qa")
                    print("   To continue accepting warnings, re-run with --qa-allow-warn")
                    sys.exit(1)
            else:
                print(f"\n[OK] QA passed ({qa_elapsed:.0f}s)")
                if os.path.exists(qa_report_path):
                    print(f"   Report: {qa_report_path}")

        # ─── QA Retry: Re-generate with feedback if issues found ─────
        if args.qa_retry and os.path.exists(qa_report_path):
            # Check if there are actionable issues (warning or critical)
            try:
                with open(qa_report_path, encoding="utf-8") as f:
                    qa_data = json.load(f)

                actionable = 0
                for agent_result in qa_data.get("agents", {}).values():
                    for issue in agent_result.get("issues", []):
                        if issue.get("severity") in ("warning", "critical"):
                            actionable += 1

                if actionable > 0:
                    print(f"\n  {actionable} actionable issues found → starting QA retry...")

                    # Import and run QA retry
                    sys.path.insert(0, src_dir)
                    from qa_retry import run_qa_retry

                    retry_result = run_qa_retry(
                        scene_json=scene_json,
                        config_json=config_path,
                        qa_report_path=qa_report_path,
                        src_dir=src_dir,
                        model=args.model,
                        quick=args.qa_quick,
                        use_gemini_fact=args.use_gemini_fact,
                        max_diff_rate=args.qa_max_diff,
                    )

                    if retry_result["action"] == "rejected":
                        print("\n  v2 rejected. v1 retained for manual review.")
                        print("  Pipeline continues with v1.")
                else:
                    print("\n  No actionable issues → QA retry skipped")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"\n  [WARN] Could not read QA report for retry: {e}")

    # ─── Step 2: Audio generation ────────────────────────────────────────
    if "audio" in steps:
        _synthesis_forecast_gate(
            scene_json,
            episode_dir,
            src_dir,
            tts_engine,
            tts_voice,
            tts_rate,
            speed_scale,
            args,
        )
        _run_audio_pre_checks(scene_json, src_dir, tts_engine, args)

        cmd = [
            sys.executable,
            os.path.join(src_dir, "audio_generator.py"),
            scene_json,
            "--output-dir",
            episode_dir,
            "--speed-scale",
            str(speed_scale),  # per-ep speedScale (config "speed_scale", default 0.87)
            "--tts-engine",
            tts_engine,
        ]
        if tts_engine == "cloud":
            if tts_voice:
                cmd += ["--tts-voice", tts_voice]
            if tts_rate is not None:
                cmd += ["--tts-rate", str(tts_rate)]
        if args.dry_run_audio:
            cmd.append("--dry-run")
        if args.force_regen_audio:
            cmd.append("--force-regen-audio")
        # pronunciation_check is VOICEVOX-only (uses audio_query + rewrites
        # narration_speech). Never pass it on the Cloud path.
        run_pronunciation = (
            tts_engine == "voicevox"
            and (args.qa or args.qa_quick or args.check_pronunciation)
            and not args.skip_pronunciation_check
        )
        if run_pronunciation:
            cmd.append("--check-pronunciation")
        run_step("audio", cmd)

        _run_audio_post_checks(scene_json, episode_dir, timing_json, src_dir, tts_engine, args)

    # ─── Font coverage check (before subtitles) ─────────────────────────
    if "subtitles" in steps:
        _run_font_coverage_check(scene_json, src_dir)

    # ─── Step 3: Subtitle generation ─────────────────────────────────────
    if "subtitles" in steps:
        if not os.path.exists(timing_json):
            print("\n[WARN] timing.json not found. Skipping subtitles.")
        else:
            cmd = [
                sys.executable,
                os.path.join(src_dir, "subtitle_generator.py"),
                timing_json,
                "--output-dir",
                episode_dir,
                "--scene-json",
                scene_json,
            ]
            # Engine-aware subtitle timing: VOICEVOX-measured per-segment
            # durations are only valid when VOICEVOX is the speaking engine. For
            # Cloud episodes the audio is Google Cloud TTS reading text_clean
            # (narration_speech_cloud), so querying VOICEVOX for the *display*
            # text drifts the split (and re-appears only when the local VOICEVOX
            # server happens to be up -> non-reproducible). Force the calibrated
            # local mora estimate instead.
            if tts_engine == "cloud":
                cmd.append("--no-voicevox-timing")
            run_step("subtitles", cmd)

    # ─── Step 3.5: Wikimedia photo fetch ─────────────────────────────────
    if "photos" in steps:
        cmd = [
            sys.executable,
            os.path.join(src_dir, "wikimedia_fetcher.py"),
            config_path,
            "--scene-json",
            scene_json,
            "--max-photos",
            "3",
        ]
        run_step("photos", cmd, required=False)

    # ─── Step 4: Image generation ────────────────────────────────────────
    if "images" in steps:
        _run_pre_images_checks(episode_dir, scene_json, config_path, src_dir)

        cmd = [
            sys.executable,
            os.path.join(src_dir, "image_generator.py"),
            scene_json,
            "--output-dir",
            episode_dir,
            "--generate",
            "--config",
            config_path,
        ]
        run_step("images", cmd, required=False)

        # Verify image count matches ken_burns scene count (a past silent-failure bug detection).
        # Silent partial failure of image generation (network drop, API quota)
        # used to produce only 4/18 images and pipeline continued, generating
        # tiny placeholder visuals for the missing 14 scenes. Fail-fast here.
        try:
            with open(scene_json, encoding="utf-8") as f:
                _scene_def = json.load(f)
            expected_ids = []
            for _sec in _scene_def.get("sections", []):
                for _sc in _sec.get("scenes", []):
                    if _sc.get("visual", {}).get("type") == "ken_burns":
                        expected_ids.append(_sc.get("scene_id"))
            images_dir = os.path.join(episode_dir, "images")
            existing = (
                set(
                    os.path.splitext(f)[0]
                    for f in os.listdir(images_dir)
                    if f.endswith(".png") and not f.startswith("wiki_")
                )
                if os.path.isdir(images_dir)
                else set()
            )
            missing = [sid for sid in expected_ids if sid not in existing]
            if missing:
                print(
                    f"\n[ERROR] Image generation incomplete: "
                    f"{len(missing)}/{len(expected_ids)} ken_burns scenes "
                    f"missing PNG. Missing: {', '.join(missing[:8])}"
                    f"{'...' if len(missing) > 8 else ''}"
                )
                print(
                    "  Pipeline halted to prevent silent fallback to "
                    "placeholder visuals (a past silent-failure bug). Re-run after "
                    "resolving image generation failure (network, "
                    "API quota, etc.)."
                )
                sys.exit(1)
            print(
                f"  [OK] Image count check: {len(expected_ids)} ken_burns scenes, all PNG present"
            )
        except SystemExit:
            raise
        except Exception as _e:
            print(f"\n[WARN] Image count verification skipped: {_e}")

        _run_post_images_border_lint(episode_dir, src_dir)

        # ─── 強化 H2: portrait_prompt_lint pipeline 統合 ───────
        # 強化 C standalone (scripts/portrait_prompt_lint.py) を
        # images step 末尾で auto-gate。use_reference: true scene の
        # source_prompt と reference 写真 (wiki_*.jpg) の特徴矛盾を Gemini
        # Vision で catch。an earlier episode「kimono」prompt vs 全 wiki refs
        # Western suit の mismatch を user 視聴前に検出する。
        #
        # 設計判断:
        # - WARN-only (build halt しない、exit code は無視)
        # - reference photo がない episode (古代人物) は自動 skip
        # - --skip-portrait-lint で opt-out 可能
        # - 失敗時 (Gemini env 未設定 / API timeout) は silent skip
        if not args.skip_portrait_lint:
            try:
                # quick check: any use_reference + wiki_*.jpg?
                _has_ref_scene = False
                for _sec in _scene_def.get("sections", []):
                    for _sc in _sec.get("scenes", []):
                        _v = _sc.get("visual", {})
                        if _v.get("type") == "ken_burns" and _v.get("use_reference", True):
                            _has_ref_scene = True
                            break
                    if _has_ref_scene:
                        break
                _wiki_exists = any(
                    f.startswith("wiki_") and f.lower().endswith((".jpg", ".jpeg", ".png"))
                    for f in (
                        os.listdir(os.path.join(episode_dir, "images"))
                        if os.path.isdir(os.path.join(episode_dir, "images"))
                        else []
                    )
                )
                if _has_ref_scene and _wiki_exists:
                    print("\n=== Step: portrait_prompt_lint (H2) ===")
                    _lint_cmd = [
                        sys.executable,
                        os.path.join(
                            os.path.dirname(src_dir), "scripts", "portrait_prompt_lint.py"
                        ),
                        episode_dir,
                    ]
                    _lint_result = subprocess.run(
                        _lint_cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    # surface output to pipeline log
                    if _lint_result.stdout:
                        print(_lint_result.stdout)
                    if _lint_result.stderr:
                        print(f"[portrait_lint stderr] {_lint_result.stderr[:500]}")
                    # exit 2 = IDENTITY mismatch (顔の毛/頭髪/骨格 -- reference と矛盾、
                    # 本人の風貌が誤って伝わる shipped-defect risk); 1 = AGE-only
                    # (若年/晩年版、通常は意図的)。identity は最終 advisory roll-up に
                    # 上げて見落とし防止。WARN-only、build halt しない。
                    if _lint_result.returncode == 2:
                        import re as _re

                        _m = _re.search(r"IDENTITY_MISMATCHES:\s*(\d+)", _lint_result.stdout or "")
                        _n_id = int(_m.group(1)) if _m else 1
                        print(
                            f"  [!] portrait_prompt_lint: IDENTITY mismatch x{_n_id} "
                            "(顔の毛/頭髪/骨格が reference と矛盾) -- 本人の風貌が誤って"
                            "伝わる。出荷前に必ず確認 (ある回 full beard vs 口ひげ)。"
                        )
                        try:
                            pipeline_log.emit_stderr_warn_summary(
                                "portrait_identity_mismatch", _n_id
                            )
                        except Exception:
                            pass
                    elif _lint_result.returncode == 1:
                        print(
                            "  [WARN] portrait_prompt_lint: 年齢帯のみの mismatch "
                            "(若年/晩年版、通常は意図的)。identity 矛盾なし。"
                        )
                else:
                    if not _wiki_exists:
                        print(
                            "  [SKIP] portrait_prompt_lint: no wiki_*.jpg reference "
                            "photos in episode (古代/近代以前 pattern)"
                        )
                    else:
                        print(
                            "  [SKIP] portrait_prompt_lint: no use_reference=true ken_burns scenes"
                        )
            except Exception as _e:
                print(f"  [WARN] portrait_prompt_lint skipped (env/api issue): {_e}")

    # ─── QA Gate 2: Image Quality Check ─────
    # Runs AFTER image generation so freshly-produced images are evaluated.
    # The prompt covers narration-image consistency plus the original time-place /
    # subject / atmosphere checks.
    if "images" in steps:
        _run_image_qa_gate2(episode_dir, scene_json, src_dir, args)

    # ─── Step 4.5: Thumbnail generation ──────────────────────────────────
    if "thumbnail" in steps:
        images_dir = os.path.join(episode_dir, "images")
        default_source = os.path.join(images_dir, "person_01.png")
        if os.path.exists(default_source) or config.get("thumbnail", {}).get("source_image"):
            cmd = [
                sys.executable,
                os.path.join(src_dir, "thumbnail_generator.py"),
                config_path,
                "--output-dir",
                episode_dir,
            ]
            run_step("thumbnail", cmd, required=False)

            # Thumbnail Vision QA — verify generated
            # thumbnails are single-person portraits (not group_scene /
            # landscape / abstract). Skippable with --skip-qa.
            thumbnails_dir = os.path.join(episode_dir, "thumbnails")
            if not args.skip_qa and os.path.isdir(thumbnails_dir):
                vision_qa_script = os.path.join(src_dir, "qa_thumbnail_vision.py")
                if os.path.exists(vision_qa_script):
                    vision_cmd = [
                        sys.executable,
                        vision_qa_script,
                        config_path,
                    ]
                    run_step("thumbnail_vision_qa", vision_cmd, required=False)
        else:
            print("\n[SKIP] Skipping thumbnail (no person image yet)")

    # ─── Step 5: Visual generation ───────────────────────────────────────
    if "visuals" in steps:
        if not os.path.exists(timing_json):
            print("\n[WARN] timing.json not found. Skipping visuals.")
        else:
            _run_pre_visuals_checks(episode_dir, scene_json, config, args, src_dir)
            _run_route_map_preflight(scene_json, args)

            cmd = [
                sys.executable,
                os.path.join(src_dir, "visual_generator.py"),
                scene_json,
                timing_json,
                "--output-dir",
                episode_dir,
                "--manim-templates",
                os.path.join(src_dir, "manim_templates"),
                "--blender-templates",
                os.path.join(src_dir, "blender_templates"),
            ]
            if args.skip_manim:
                cmd.append("--skip-manim")
            if args.force_regen_visuals:
                cmd.append("--force-regen-visuals")
            run_step("visuals", cmd)

            _run_post_visual_lints(episode_dir, scene_json, src_dir, args)

    # ─── Step 6: Video assembly ──────────────────────────────────────────
    if "assemble" in steps:
        if not os.path.exists(timing_json):
            print("\n[WARN] timing.json not found. Skipping assembly.")
        else:
            _run_pre_assemble_guards(episode_dir, scene_json, timing_json, steps, args)

            cmd = [
                sys.executable,
                os.path.join(src_dir, "video_assembler.py"),
                scene_json,
                timing_json,
                "--output-dir",
                episode_dir,
                "--output-name",
                OUTPUT_ASSEMBLED,
            ]
            if args.no_subtitles:
                cmd.append("--no-subtitles")
            run_step("assemble", cmd)

    # ─── Step 7: Credits / Description ───────────────────────────────────
    if "credits" in steps:
        cmd = [
            sys.executable,
            os.path.join(src_dir, "credits_generator.py"),
            config_path,
        ]
        # Pass intro-pause for chapter timestamp offset.
        # Default (1.0) must match bgm_mixer's default below, otherwise
        # YouTube chapters will be misaligned by the intro-pause duration.
        intro_pause = bgm_config.get("intro_pause", 1.0)
        if intro_pause > 0:
            cmd.extend(["--intro-pause", str(intro_pause)])
        if args.skip_intro_check:
            cmd.append("--skip-intro-check")
        run_step("credits", cmd, required=False)

    # ─── Step 8: BGM mixing ──────────────────────────────────────────────
    if "bgm" in steps:
        if not bgm_file:
            print("\n[SKIP] Skipping BGM (no bgm.file in episode_config.json)")
        elif not os.path.exists(bgm_file):
            print(f"\n[WARN] BGM file not found: {bgm_file}")
            print("   Skipping BGM mixing.")
        else:
            output_assembled = os.path.join(episode_dir, OUTPUT_ASSEMBLED)
            output_final = os.path.join(episode_dir, OUTPUT_FINAL)
            if not os.path.exists(output_assembled):
                print(f"\n[WARN] {OUTPUT_ASSEMBLED} not found. Skipping BGM mixing.")
            else:
                cmd = [
                    sys.executable,
                    os.path.join(src_dir, "bgm_mixer.py"),
                    output_assembled,
                    bgm_file,
                    "--output",
                    output_final,
                ]
                # Pass BGM parameters from config
                intro_pause = bgm_config.get("intro_pause", 1.0)
                outro_hold = bgm_config.get("outro_hold", 10.0)
                outro_fade = bgm_config.get("outro_fade", 3.0)
                volume_db = bgm_config.get("volume_db", -20)
                bgm_fadein = bgm_config.get("bgm_fadein", 2.0)

                cmd.extend(
                    [
                        "--intro-pause",
                        str(intro_pause),
                        "--outro-hold",
                        str(outro_hold),
                        "--outro-fade",
                        str(outro_fade),
                        "--bgm-volume",
                        str(volume_db),
                        "--bgm-fadein",
                        str(bgm_fadein),
                    ]
                )

                # Optional landscape endcard (replaces the last-frame freeze)
                endcard_image = bgm_config.get("endcard_image")
                if endcard_image:
                    endcard_path = (
                        endcard_image
                        if os.path.isabs(endcard_image)
                        else os.path.join(episode_dir, endcard_image)
                    )
                    if os.path.exists(endcard_path):
                        cmd.extend(["--endcard-image", endcard_path])
                    else:
                        print(
                            f"[WARN] endcard_image not found: {endcard_path}"
                            " — falling back to last-frame hold"
                        )

                run_step("bgm", cmd)

    # ─── Output verification ────────────────────────────────
    # post_build_verify の件数はヘルパー内で `_advisory_warn_counts` に積まれ、
    # 下の roll-up がそこから読む。ここでは受け取るだけ。
    verify_warnings, _ = _run_output_verification(
        episode_dir, src_dir, config, args, steps, scene_json
    )

    # ─── Summary ─────────────────────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start
    output_assembled = os.path.join(episode_dir, OUTPUT_ASSEMBLED)
    output_final = os.path.join(episode_dir, OUTPUT_FINAL)

    print(f"\n{'=' * 60}")
    print("  Pipeline Complete")
    print(f"{'=' * 60}")
    print(f"  Total time: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")

    # Show final output. output_final.mp4 only exists when bgm step finished;
    # if only assemble ran (or bgm was skipped), report the intermediate file.
    if os.path.exists(output_final):
        size_mb = os.path.getsize(output_final) / (1024 * 1024)
        print(f"  Output:     {output_final} ({size_mb:.1f} MB)")
    elif os.path.exists(output_assembled):
        size_mb = os.path.getsize(output_assembled) / (1024 * 1024)
        print(f"  Output:     {output_assembled} ({size_mb:.1f} MB) [bgm pending]")
    else:
        print("  Output:     not created (check step errors)")

    # Surface unresolved verify_outputs warnings inside the summary box so a reader
    # who scans only the tail cannot miss them (a description.txt stale-timestamp
    # WARN once fired in 'Output Verification' but was overlooked by reading only
    # 'Pipeline Complete'). The placeholder banner below still handles the CRITICAL
    # case; this line covers every verification warning (incl. description drift).
    if verify_warnings:
        print(
            f"  [!] {len(verify_warnings)} verification warning(s) above "
            "-- review 'Output Verification' before publishing."
        )

    if _advisory_warn_counts:
        print(
            f"  [!] advisory warnings -- {_format_advisory_rollup()} "
            "(review each step's output above)"
        )
    _advisory_rollup_state["shown"] = True

    # a partial rebuild does not re-run the advisory checks owned by the steps it
    # skipped, so their last verdict is stale. Name them rather than let the (clean)
    # summary imply everything was re-validated this run.
    _skipped_advisory = [s for s in _ADVISORY_STEPS if s not in steps]
    if _skipped_advisory:
        print(
            "  [i] 今回未実行のステップの advisory は再検証されていません: "
            + ", ".join(f"{s} ({_ADVISORY_STEPS[s]})" for s in _skipped_advisory)
        )

    # mid-build Claude auth expiry -> some Claude QA was SKIPPED (not run
    # silently). Surface prominently with resume guidance so it is unmissable.
    if _auth_probe_warnings:
        print(
            f"  [!!] Claude auth 失効で {len(_auth_probe_warnings)} 件の QA を skip しました "
            "-- 再認証 (claude setup-token) 後に該当ステップを再実行してください:"
        )
        for _w in _auth_probe_warnings:
            print(f"       - {_w}")

    print(f"{'=' * 60}")

    # Prominent placeholder/missing-animation banner so a Manim render
    # timeout/failure can NEVER silently ship in the final video (a past
    # near-miss: math_07 gimbal_lock shipped as a title-card placeholder and was
    # only caught by manual frame inspection). Reuses the gated G1 detection in
    # verify_outputs (only fires when the visuals step ran this invocation).
    placeholder_warn = next(
        (w for w in verify_warnings if "fell back to" in w and "placeholder" in w),
        None,
    )
    if placeholder_warn:
        print(f"\n{'!' * 60}")
        print("  [CRITICAL] PLACEHOLDER SCENE(S) IN THE FINAL VIDEO")
        print(f"{'!' * 60}")
        print(placeholder_warn.strip())
        print("  *** The video shows a plain title-card instead of the animation")
        print("  *** for the scene(s) above. Fix the Manim template (timeout/error),")
        print("  *** then re-run --steps visuals,assemble,bgm before publishing.")
        print(f"{'!' * 60}")

    # ─── pipeline_end event + logger close ─────────────
    _pipeline_end_level = pipeline_log.LEVEL_WARNING if verify_warnings else pipeline_log.LEVEL_INFO
    pipeline_log.emit(
        _pipeline_end_level,
        "pipeline",
        "pipeline end",
        duration_ms=int(total_elapsed * 1000),
        verify_warning_count=len(verify_warnings),
    )
    pipeline_log.close()

    # terminal progress snapshot so a watcher knows the build finished
    # (and whether output_final.mp4 is a valid, playable file).
    pipeline_progress.finish("complete", _output_final_summary(episode_dir))


if __name__ == "__main__":
    main()
