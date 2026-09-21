#!/usr/bin/env python3
"""post_build_verify.py — post-build structural verification.

The number of checks is not written here on purpose; read it from CHECKS /
check_count(). Three different hand-typed counts (8, 10, "nine") were live in
this repository at once.

Runs a systematic verification checklist on a built episode directory so that
"build complete" is backed by evidence, not just a pipeline exit code of 0. It
surfaces the silent-failure classes that a green pipeline run can still hide:
fallback placeholders, stale subtitles/description, narration/speech drift, and
unreviewed Manim frames.

## Usage

    python scripts/post_build_verify.py episodes/<episode_id>

## Checks performed

1. **Manim fallback sidecar**: read visuals/_fallback_scenes.json → list any
   scenes that fell back to a text_overlay placeholder.

2. **Subtitle/narration hash sync**: compare the hash embedded in
   _subtitles_meta.json against the current scene_def narration → mismatch
   warning (subtitles regenerated out of step with audio).

3. **description.txt freshness**: mtime comparison against scene_def and
   episode_config → stale warning.

4. **narration vs narration_speech structural diff**: length-ratio heuristic
   (0.7 < ratio < 1.5) → flag a likely narration edit without a speech-side sync.

5. **Manim scene frame extraction**: ffmpeg extracts the last frame of every
   Manim scene to <episode_dir>/_qa_frames/post_build_<scene_id>.png for review.

6. **VOICEVOX proper-noun empirical verify**: query VOICEVOX for the subject
   plus frequently-misread proper nouns → report the kana readings produced.

7. **Subtitle char count**: flag lines longer than MAX_CHARS (default 25 jp).

8. **temp_videos sync**: warn if temp_videos/<ep_id>_output_final.mp4 (the review
   copy) is missing or stale relative to the freshly built output_final.mp4.

9. **output_final.mp4 health**: ffprobe the final mp4 → ERROR if the moov
   atom is missing or duration is unreadable (a killed bgm-step ffmpeg leaves a
   truncated, unplayable file that "exists" but is not a finished build).

10. **Chapter timestamps vs timing.json**: recompute the YouTube chapter marks
   from timing.json and compare them with the ones written into description.txt
   -> a partial rebuild that changed the timing but skipped the credits step
   leaves the old numbers behind (an earlier episode said 1:38 for a chapter now at 1:41).
   Check 3 cannot see this: it compares mtimes, and not against timing.json.

11. **Bottom-corner contact sheet**: tile the bottom corners of every generated
   image into one gamma-lifted sheet. Not a detector -- a looking aid. Image
   models paint a signature there, and two attempts at detecting it automatically
   both pointed at the wrong things; one episode shipped with 6 of 13 images
   signed because only 2 were checked by eye.

12. **subtitles_final.srt vs intro pause**: the bgm step prepends `intro_pause`
    seconds of video and audio, so `subtitles.srt` (assembled-video times) is early
    by that much on the final video. The bgm step now writes `subtitles_final.srt`
    (+intro_pause); this check verifies every cue is shifted by exactly that, and
    that the first speech onset in output_final.mp4 sits on the first cue.

13. **disk vs shipped**: timing.json の署名が字幕焼き込み時と一致するか、visuals / images が
    出荷物より新しくないか、文 wav が出荷物より新しいか (ある回再検証: audio ステップだけで
    62 文が再正規化され、出荷動画と disk がずれうる経路があった)。

This script does not replace human review; it forces a look at every artifact
before a build is reported as complete.

Output: stdout summary + <episode_dir>/_qa_frames/ holding the Manim frames.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROPER_NOUNS_TO_VERIFY = [
    # Curated watch-list of proper nouns that VOICEVOX has historically misread
    # (e.g. dropped-mora cases). Only the ones present in the episode are checked.
    "フェルマー",
    "メルセンヌ",
    "デザルグ",
    "ロベルヴァル",
    "セギエ",
    "シカール",
    "トリチェリ",
    "ハジェク",
    "コルモゴロフ",
    "ジロラモ・カルダーノ",
    "シュヴァリエ・ド・メレ",
    "フロラン・ペリエ",
    "エチエンヌ・パスカル",
    "クレルモン・フェラン",
    "ピュイ・ド・ドーム",
    "ポール・ロワイヤル",
    "ベルヌーイ",
    "ライプニッツ",
    "バベッジ",
    "ノイマン",
    "ピンガラ",
]


def check_manim_fallbacks(ep_dir: Path) -> dict:
    """Check visuals/_fallback_scenes.json (G1)."""
    sidecar = ep_dir / "visuals" / "_fallback_scenes.json"
    if not sidecar.exists():
        return {"status": "OK", "fallback_count": 0, "details": "no fallbacks"}
    try:
        with open(sidecar, encoding="utf-8") as f:
            data = json.load(f)
        if data:
            return {
                "status": "WARN",
                "fallback_count": len(data),
                "details": [f"{d['scene_id']}({d['reason']})" for d in data],
            }
        return {"status": "OK", "fallback_count": 0}
    except Exception as e:
        return {"status": "ERROR", "details": str(e)}


def check_subtitle_hash(ep_dir: Path) -> dict:
    """Subtitle/narration hash sync (G2)."""
    meta = ep_dir / "_subtitles_meta.json"
    scene_def = ep_dir / "scene_definition.json"
    if not meta.exists() or not scene_def.exists():
        return {"status": "SKIP", "reason": "meta or scene_def missing"}
    try:
        import hashlib

        with open(meta, encoding="utf-8") as f:
            embedded = json.load(f).get("narration_hash")
        with open(scene_def, encoding="utf-8") as f:
            sd = json.load(f)
        blob = []
        for sec in sd.get("sections", []):
            for sc in sec.get("scenes", []):
                for n in sc.get("narration", []):
                    blob.append(n)
        text = "\n".join(blob)
        current = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        if embedded != current:
            return {
                "status": "WARN",
                "embedded": embedded,
                "current": current,
                "msg": "subtitles.srt is stale relative to current scene_def",
            }
        return {"status": "OK"}
    except Exception as e:
        return {"status": "ERROR", "details": str(e)}


def check_description_freshness(ep_dir: Path) -> dict:
    """description.txt mtime vs source files (G6)."""
    desc = ep_dir / "description.txt"
    scene = ep_dir / "scene_definition.json"
    config = ep_dir / "episode_config.json"
    if not desc.exists():
        return {"status": "SKIP", "reason": "description.txt missing"}
    desc_mtime = desc.stat().st_mtime
    src_mtime = max(
        scene.stat().st_mtime if scene.exists() else 0,
        config.stat().st_mtime if config.exists() else 0,
    )
    if desc_mtime < src_mtime:
        import datetime

        return {
            "status": "WARN",
            "msg": f"STALE: desc {datetime.datetime.fromtimestamp(desc_mtime).isoformat(timespec='seconds')} < src {datetime.datetime.fromtimestamp(src_mtime).isoformat(timespec='seconds')}",
        }
    return {"status": "OK"}


def check_narration_ns_sync(ep_dir: Path) -> dict:
    """narration/NS edit-sync miss check.

    Two layers: a length-ratio heuristic (0.7 < ratio < 1.5), plus a
    synonym-replacement catch (kanji-set diff + digit-sequence diff, so a WARN
    fires even when length is unchanged). Reuses
    audio_generator._check_narration_speech_drift to re-scan at the post-build
    stage and surface WARNs that were buried in the build log.
    """
    scene = ep_dir / "scene_definition.json"
    if not scene.exists():
        return {"status": "SKIP"}
    with open(scene, encoding="utf-8") as f:
        sd = json.load(f)

    # Reuse audio_generator's structural drift check
    semantic_misses = []
    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from audio_generator import _check_narration_speech_drift  # type: ignore
    except Exception as e:
        _check_narration_speech_drift = None  # type: ignore
        semantic_misses.append(f"(semantic check unavailable: {e})")

    ratio_misses = []
    for sec in sd.get("sections", []):
        for sc in sec.get("scenes", []):
            n_list = sc.get("narration", [])
            ns_list = sc.get("narration_speech")
            if ns_list is None:
                continue
            for i, narr in enumerate(n_list):
                if i >= len(ns_list):
                    ratio_misses.append(f"{sc['scene_id']}[{i}]: NS missing")
                    continue
                ns = ns_list[i]
                if ns is None:
                    continue
                narr_flat = narr.replace("|", "")
                if not narr_flat:
                    continue
                ratio = len(ns) / len(narr_flat)
                if ratio < 0.7 or ratio > 1.5:
                    ratio_misses.append(
                        f"{sc['scene_id']}[{i}] ratio={ratio:.2f}: "
                        f"N={narr_flat[:40]}... / NS={ns[:40]}..."
                    )
                # semantic diff (synonym replacement catches)
                if _check_narration_speech_drift is not None:
                    reasons = _check_narration_speech_drift(narr_flat, ns)
                    for r in reasons:
                        semantic_misses.append(
                            f"{sc['scene_id']}[{i}]: {r} (N={narr_flat[:30]}.. / NS={ns[:30]}..)"
                        )

    all_misses = ratio_misses + semantic_misses
    if all_misses:
        return {
            "status": "WARN",
            "count": len(all_misses),
            "ratio_count": len(ratio_misses),
            "semantic_count": len(semantic_misses),
            "details": all_misses,
        }
    return {"status": "OK"}


def extract_manim_frames(ep_dir: Path, out_dir: Path) -> dict:
    """Extract last frame of all manim scenes for Read review."""
    scene = ep_dir / "scene_definition.json"
    if not scene.exists():
        return {"status": "SKIP"}
    with open(scene, encoding="utf-8") as f:
        sd = json.load(f)
    manim_scene_ids = []
    for sec in sd.get("sections", []):
        for sc in sec.get("scenes", []):
            if sc.get("visual", {}).get("type") == "manim":
                manim_scene_ids.append(sc.get("scene_id"))
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    failed = []
    for sid in manim_scene_ids:
        mp4 = ep_dir / "visuals" / f"{sid}.mp4"
        if not mp4.exists():
            failed.append(f"{sid}: mp4 missing")
            continue
        png = out_dir / f"post_build_{sid}.png"
        # Use -sseof -1 to seek 1 second before end of mp4 (= last static frame
        # after animation complete). Previously used `-ss 5` which captured
        # mid-animation frame (e.g. a line not yet drawn).
        result = subprocess.run(
            ["ffmpeg", "-sseof", "-1", "-i", str(mp4), "-frames:v", "1", "-y", str(png)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Shorten to a repo-relative path when we can, but never crash on a
            # directory outside the repo (a self-test may pass a temp dir, and
            # relative_to raises rather than returning the absolute path).
            try:
                shown = str(png.relative_to(REPO_ROOT))
            except ValueError:
                shown = str(png)
            extracted.append(shown)
        else:
            failed.append(f"{sid}: ffmpeg failed")
    return {
        "status": "OK" if not failed else "PARTIAL",
        "extracted": extracted,
        "failed": failed,
        "manim_count": len(manim_scene_ids),
    }


def _tts_engine(ep_dir: Path | None) -> str:
    """episode_config.tts.engine (既定 voicevox)。読めなければ voicevox 扱い。"""
    if ep_dir is None:
        return "voicevox"
    config = Path(ep_dir) / "episode_config.json"
    if not config.exists():
        return "voicevox"
    try:
        with open(config, encoding="utf-8") as f:
            return str((json.load(f).get("tts") or {}).get("engine") or "voicevox").lower()
    except Exception:
        return "voicevox"


def voicevox_is_up(timeout: float = 2.0) -> bool:
    """VOICEVOX (localhost:50021) が応答するか。1 回だけ叩く。"""
    try:
        import requests

        return requests.get("http://localhost:50021/version", timeout=timeout).status_code == 200
    except Exception:
        return False


def verify_voicevox_proper_nouns(subject: str, ep_dir: Path | None = None, *, probe=None) -> dict:
    """Query VOICEVOX for proper nouns, flag suspicious readings.

    (2026-09-19): engine=cloud の回では VOICEVOX は使っていないので SKIP。
    VOICEVOX が起動していなければ先に 1 回の probe で SKIP する ── 以前は 22 語それぞれが
    接続タイムアウト (実測 4 秒) を待って **合計 90 秒**かかり、しかも全語が error なのに
    suspicious が空だから **OK を返していた** (「指摘ゼロ」と「検査していない」の混同)。
    回帰スイートの 220 秒のうち 191 秒がこれだった。probe はテストから差し替えられる。
    """
    try:
        import requests
    except ImportError:
        return {"status": "SKIP", "reason": "requests not available"}

    engine = _tts_engine(ep_dir)
    if engine != "voicevox":
        return {"status": "SKIP", "reason": f"engine={engine} (VOICEVOX は使っていない)"}
    if not (probe or voicevox_is_up)():
        return {
            "status": "SKIP",
            "reason": "VOICEVOX が起動していない (localhost:50021 無応答)。固有名詞の読みは未検証",
        }

    results = {}
    suspicious = []
    errors = []
    for noun in [subject] + PROPER_NOUNS_TO_VERIFY:
        try:
            r = requests.post(
                f"http://localhost:50021/audio_query?text={noun}&speaker=13",
                timeout=5,
            )
            if r.status_code != 200:
                results[noun] = "(VOICEVOX HTTP error)"
                continue
            kanas = "".join(
                m.get("text", "")
                for p in r.json().get("accent_phrases", [])
                for m in p.get("moras", [])
            )
            results[noun] = kanas
            # Heuristic: if first char of noun is katakana but the kana reading
            # drops it (a dropped-mora misreading), flag.
            if noun and kanas and noun[0] != "・":
                # Compare first kana of input vs first kana of reading
                first_in = noun[0]
                first_out = kanas[0] if kanas else ""
                # Crude: if input is カナ but first output char is different and
                # input first char isn't in output at all, flag.
                if (
                    "゠" <= first_in <= "ヿ"  # カナ
                    and first_in != first_out
                    and first_in not in kanas[:3]
                ):
                    suspicious.append(f"{noun} → {kanas} (first char mismatch)")
        except Exception as e:
            results[noun] = f"(error: {e})"
            errors.append(noun)
    # 問い合わせに失敗した語は「読みが正しい」ことにしない。全部失敗なら検査していない。
    if errors and len(errors) == len(results):
        return {
            "status": "SKIP",
            "reason": f"全 {len(errors)} 語の問い合わせに失敗",
            "results": results,
        }
    return {
        "status": "WARN" if (suspicious or errors) else "OK",
        "results": results,
        "suspicious": suspicious,
        "unverified": errors,
    }


def check_temp_videos_sync(ep_dir: Path) -> dict:
    """Check temp_videos/<ep_id>_output_final.mp4 is in sync with latest build.

    Guards against the failure mode where output_final.mp4 is rebuilt but the
    copy under temp_videos/ (used for review) is left stale, so the reviewer
    keeps watching an old build.
    """
    output = ep_dir / "output_final.mp4"
    ep_id = ep_dir.name
    temp_path = REPO_ROOT / "temp_videos" / f"{ep_id}_output_final.mp4"
    if not output.exists():
        return {"status": "SKIP", "reason": "output_final.mp4 missing"}
    if not temp_path.exists():
        return {
            "status": "WARN",
            "msg": f"temp_videos copy missing: {temp_path}. Run: cp {output} {temp_path}",
        }
    output_mtime = output.stat().st_mtime
    temp_mtime = temp_path.stat().st_mtime
    if output_mtime > temp_mtime + 1:  # 1 sec tolerance
        import datetime as _dt

        return {
            "status": "WARN",
            "msg": (
                f"temp_videos copy STALE: "
                f"output={_dt.datetime.fromtimestamp(output_mtime).isoformat(timespec='seconds')} > "
                f"temp={_dt.datetime.fromtimestamp(temp_mtime).isoformat(timespec='seconds')}. "
                f"Run: cp {output} {temp_path}"
            ),
        }
    return {"status": "OK"}


def check_subtitle_char_count(ep_dir: Path, max_chars: int = 25) -> dict:
    """Subtitles entries > max_chars JP are flagged."""
    srt = ep_dir / "subtitles.srt"
    if not srt.exists():
        return {"status": "SKIP"}
    long_lines = []
    with open(srt, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip cue indices and timestamps
            if not line or line.isdigit() or "-->" in line:
                continue
            if len(line) > max_chars:
                long_lines.append(f"  [{len(line)} chars] {line}")
    if long_lines:
        return {
            "status": "WARN",
            "count": len(long_lines),
            "details": long_lines[:10],
        }
    return {"status": "OK"}


def check_output_final_health(ep_dir: Path) -> dict:
    """output_final.mp4 の moov/duration 健全性.

    pipeline は「output_final.mp4 が存在 = 完走」を前提とするが、bgm step の
    ffmpeg が途中で kill されると moov atom 欠落の部分書き込みファイルが残り、
    再生不可なのに「完成」と誤認される。ffprobe で moov/duration
    を確認し、読めなければ ERROR を返す (生成元 bgm_mixer / pipeline verify と
    合わせた 3 層 layered defense の最終層)。
    """
    output = ep_dir / "output_final.mp4"
    if not output.exists():
        return {"status": "SKIP", "reason": "output_final.mp4 missing"}
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(output)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as e:
        return {"status": "ERROR", "msg": f"ffprobe 実行不可: {e}"}
    if result.returncode != 0:
        return {
            "status": "ERROR",
            "msg": "moov atom 欠落 / 再生不可 (ffprobe failed)。bgm step を再実行してください。",
        }
    try:
        dur = float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return {
            "status": "ERROR",
            "msg": "duration 取得不可 (壊れた mp4)。bgm step を再実行してください。",
        }
    if dur <= 0:
        return {"status": "ERROR", "msg": f"duration 異常 ({dur})"}
    return {"status": "OK", "duration_sec": round(dur, 1)}


def check_chapter_timestamps(ep_dir: Path) -> dict:
    """Do the chapter timestamps written in description.txt still match timing.json?

    They are computed from timing.json by the credits step, and then nothing looks
    at them again. A partial rebuild that changes the timing but omits `credits`
    leaves the old numbers in place: on an earlier episode the description said 1:38 for a
    chapter that had moved to 1:41, and it was caught only because the credits
    step happened to be re-run by hand.

    Check 3 cannot see this - it compares description.txt's mtime against
    scene_definition.json and episode_config.json, not timing.json - and mtime is
    a poor proxy anyway (42 of 61 shipped episodes read as STALE under it, and
    merely rewriting a file with identical bytes trips it).

    This compares the VALUES, so it works on an archive too. Across the 61 shipped
    episodes 52 match exactly; of the 9 that do not, 8 differ by exactly one second
    on every chapter, which is the intro_pause of older builds rather than drift.
    """
    desc = ep_dir / "description.txt"
    scene = ep_dir / "scene_definition.json"
    timing = ep_dir / "timing.json"
    config = ep_dir / "episode_config.json"
    if not all(p.exists() for p in (desc, scene, timing, config)):
        return {
            "status": "SKIP",
            "reason": "description.txt / scene_def / timing.json のいずれかが無い",
        }
    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from credits_generator import calculate_chapters

        with open(scene, encoding="utf-8") as f:
            sd = json.load(f)
        with open(timing, encoding="utf-8") as f:
            tj = json.load(f)
        with open(config, encoding="utf-8") as f:
            cf = json.load(f)
        block = sd.get("description") or {}
        chapters = calculate_chapters(
            sd,
            tj,
            (cf.get("bgm") or {}).get("intro_pause", 1.0),
            block.get("chapter_subtitles"),
            block.get("chapter_overrides"),
        )
    except Exception as e:
        return {"status": "SKIP", "reason": f"章を再計算できない: {type(e).__name__}: {e}"}
    if not chapters:
        return {"status": "SKIP", "reason": "章が無い (3 section 未満 等)"}

    pat = re.compile(r"^(\d+:\d{2}(?::\d{2})?)\s+\S")
    written = [
        m.group(1)
        for m in (pat.match(ln.strip()) for ln in desc.read_text(encoding="utf-8").splitlines())
        if m
    ]
    expected = [c["timestamp"] for c in chapters]
    if written[: len(expected)] == expected:
        return {"status": "OK", "chapters": len(expected)}

    # Before blaming the description, ask whether timing.json still describes the
    # video. An earlier episode's does not: its scenes end at 14:34 while output_final.mp4 runs
    # 18:41, and the PUBLISHED chapters (verified against the live video) match the
    # video, not timing.json. Telling someone to re-run credits there would replace
    # correct published timestamps with wrong ones. Normal slack is intro_pause plus
    # the outro hold, ~13 s across the other 60 episodes; an earlier episode is off by 247 s.
    result = {
        "status": "WARN",
        "msg": "description.txt の章タイムスタンプが timing.json と合わない。credits step を回す",
        "timing_から計算": " ".join(expected),
        "description_の記載": " ".join(written[: len(expected)]),
    }
    video = ep_dir / "output_final.mp4"
    if video.exists():
        try:
            dur = float(
                subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "csv=p=0",
                        str(video),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                ).stdout.strip()
            )
            end = max(s.get("global_end", 0) for s in tj.get("scenes", {}).values())
            if dur - end > 60:
                result["msg"] = (
                    f"timing.json が動画を記述していない (scene 終端 {end:.0f} 秒 / "
                    f"動画 {dur:.0f} 秒)。credits を回すと概要欄のほうを壊す。"
                    "先に timing.json の出所を確かめること"
                )
        except (OSError, ValueError):
            pass
    return result


def _first_speech_onset(video: Path) -> float | None:
    """最終動画の声の立ち上がり (秒)。BGM を highpass で薄めて silencedetect の最初の silence_end。
    冒頭に無音が無ければ 0.0。ffmpeg が無い/失敗なら None (advisory なので黙って諦める)。"""
    try:
        out = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "info",
                "-i",
                str(video),
                "-t",
                "8",
                "-af",
                "highpass=f=300,silencedetect=n=-30dB:d=0.15",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        ).stderr
    except (OSError, subprocess.SubprocessError):
        return None
    starts = [float(m) for m in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(m) for m in re.findall(r"silence_end: ([0-9.]+)", out)]
    if starts and starts[0] < 0.05 and ends:
        return ends[0]
    return 0.0


def check_final_srt(ep_dir: Path) -> dict:
    """subtitles_final.srt は最終動画 (冒頭ポーズ入り) の時刻になっているか。

    subtitles.srt は output_assembled の時刻で、bgm ステップが intro_pause 秒の冒頭ポーズを
    入れるので最終動画に対しては早い。焼き込み字幕は映像ごとずれるので同期しているが、
    アップロード用の字幕ファイルは +intro_pause の subtitles_final.srt でなければならない。
    照合は 2 段: (a) 全キューが subtitles.srt + intro_pause に一致するか (決定論)、
    (b) 最終動画の声の立ち上がりが最初のキューの開始と 0.35 秒以内か (ffmpeg、advisory)。
    """
    src = ep_dir / "subtitles.srt"
    dst = ep_dir / "subtitles_final.srt"
    config = ep_dir / "episode_config.json"
    if not src.exists():
        return {"status": "SKIP", "reason": "subtitles.srt が無い"}
    intro_pause = 1.0
    if config.exists():
        try:
            with open(config, encoding="utf-8") as f:
                intro_pause = float(json.load(f).get("bgm", {}).get("intro_pause", 1.0))
        except (OSError, ValueError):
            pass
    if not dst.exists():
        return {
            "status": "WARN",
            "msg": "subtitles_final.srt が無い (bgm step を回す)。subtitles.srt は最終動画に対して "
            f"{intro_pause:.1f} 秒早いので、アップロード用には使えない",
        }
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from subtitle_generator import parse_srt_time

    def cues(path):
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "-->" in line:
                    a, b = (x.strip() for x in line.split("-->", 1))
                    out.append((parse_srt_time(a), parse_srt_time(b)))
        return out

    try:
        c_src, c_dst = cues(src), cues(dst)
    except ValueError as e:
        return {"status": "WARN", "msg": f"srt の時刻を読めない: {e}"}
    if len(c_src) != len(c_dst):
        return {
            "status": "WARN",
            "msg": f"キュー数が違う (subtitles.srt {len(c_src)} / final {len(c_dst)})。"
            "subtitles が更新された後に bgm を回していない",
        }
    bad = [
        i
        for i, ((a, b), (a2, b2)) in enumerate(zip(c_src, c_dst, strict=True), 1)
        if abs((a2 - a) - intro_pause) > 0.002 or abs((b2 - b) - intro_pause) > 0.002
    ]
    if bad:
        return {
            "status": "WARN",
            "msg": f"{len(bad)} cue(s) が subtitles.srt + {intro_pause:.1f}s と合わない (最初: #{bad[0]})。"
            "bgm step を回し直す",
        }
    result = {
        "status": "OK",
        "cues": len(c_dst),
        "offset": intro_pause,
        "first_cue": round(c_dst[0][0], 3) if c_dst else None,
    }
    final = ep_dir / "output_final.mp4"
    if final.exists() and c_dst:
        onset = _first_speech_onset(final)
        if onset is not None:
            result["speech_onset"] = round(onset, 3)
            if abs(onset - c_dst[0][0]) > 0.35:
                result["status"] = "WARN"
                result["msg"] = (
                    f"最終動画の声の立ち上がり {onset:.2f}s と最初のキュー {c_dst[0][0]:.2f}s が "
                    "0.35 秒以上ずれている (冒頭ポーズが config と違うか、bgm を回し直していない)"
                )
    return result


def check_disk_vs_shipped(ep_dir: Path) -> dict:
    """disk 上の素材が出荷物 (output_final.mp4) とずれていないか (ある回再検証で新設)。

    audio ステップを回すだけで 62 文が再正規化される経路があり、出荷済み動画と disk の
    音声・timing.json が食い違いうることが分かった (同じ係数に収束したので実害は無かった)。
    ここで見るのは 3 つ:
      (a) timing.json の署名 (Guard-B2) が字幕を焼いたときの `_subtitles_meta.json` と一致するか
          -- 不一致なら、音声を再合成/正規化した後に assemble していない = 焼き込み字幕と音がずれる
      (b) visuals/*.mp4 / images/*.png が出荷物より新しくないか -- 再レンダ/再生成が結合されていない
      (c) 文 wav が出荷物より新しいか -- (a) が一致なら音は同じ (係数が同じ) なので note のみ
    """
    final = ep_dir / "output_final.mp4"
    if not final.exists():
        return {"status": "SKIP", "reason": "output_final.mp4 が無い"}
    shipped_at = final.stat().st_mtime
    out: dict = {}
    issues: list[str] = []
    # (a) timing signature
    meta = ep_dir / "_subtitles_meta.json"
    timing = ep_dir / "timing.json"
    if meta.exists() and timing.exists():
        try:
            sys.path.insert(0, str(REPO_ROOT / "src"))
            from subtitle_generator import timing_signature

            with open(meta, encoding="utf-8") as f:
                embedded = json.load(f).get("timing_hash")
            with open(timing, encoding="utf-8") as f:
                current = timing_signature(json.load(f))
            if embedded and embedded != current:
                issues.append(
                    f"timing.json の署名 {current} が字幕焼き込み時 {embedded} と違う "
                    "(音声を再合成/正規化した後に subtitles/assemble を回していない)"
                )
            else:
                out["timing_signature"] = "match"
        except Exception as e:  # noqa: BLE001 - advisory
            out["timing_signature"] = f"unavailable ({e})"
    # (b) visuals / images newer than the shipped video
    for sub, pat, what in (("visuals", "*.mp4", "映像"), ("images", "*.png", "画像")):
        d = ep_dir / sub
        if not d.is_dir():
            continue
        newer = sorted(
            p.name
            for p in d.glob(pat)
            if not p.name.startswith("_") and p.stat().st_mtime > shipped_at + 1.0
        )
        if newer:
            issues.append(
                f"{what} {len(newer)} 本が出荷物より新しい (結合されていない): {', '.join(newer[:6])}"
            )
    # (c) sentence wavs newer than the shipped video
    audio = ep_dir / "audio"
    if audio.is_dir():
        newer_wav = [
            p.name
            for p in audio.glob("*_[0-9][0-9][0-9].wav")
            if p.stat().st_mtime > shipped_at + 1.0
        ]
        if newer_wav:
            out["note"] = f"文 wav {len(newer_wav)} 本が出荷物より新しい" + (
                " (timing 署名は一致 = 同じ係数の再適用。音は同じ)"
                if out.get("timing_signature") == "match"
                else ""
            )
    if issues:
        out["status"] = "WARN"
        out["issues"] = issues
        out["msg"] = (
            "disk が出荷物とずれている。subtitles 以降を回し直すか、出荷物を正として disk を戻す"
        )
        return out
    out["status"] = "OK"
    return out


def build_corner_sheet(ep_dir: Path, out_dir: Path) -> dict:
    """One page showing the bottom corners of every generated image.

    Not a check - a viewing aid, and deliberately so. Image models paint a
    signature into a corner now and then; on an earlier episode six of thirteen images carried
    one and only two were found, because the corners were looked at one image at
    a time and the sweep stopped early. One of the five missed was the endcard,
    which holds on screen for ten seconds.

    A detector was tried twice and rejected both times. Thresholding the local
    high-frequency energy proposed book spines and a desk lip, and the repair
    built on it pasted a desk into a field of grass. Ranking the corners by
    "thin structure on a flat surface" put only 2 of the 6 known signatures in
    the top 12 of 52 - it would send the eye to the wrong place. So nothing is
    decided here: every corner goes on one page, in a fixed order, with the
    shadows lifted so dark ink on dark wood is visible.

    Bottom corners only: all six on an earlier episode were painted along the bottom edge,
    which is where a painter signs. `--all-corners` widens it.
    """
    images = sorted((ep_dir / "images").glob("*.png"))
    # ある回: images/ に検査の作業ファイル (crop_bottomleft.png) が残っていてシートに写った。
    # scene_definition が隣にあれば scene_id 以外の png はシートから外し、名指しで返す
    # (シートの目的は出荷画像の下隅を見ることで、作業ファイルの隅ではない)。
    images, extras = split_scene_images(ep_dir, images)
    if not images:
        return {"status": "SKIP", "reason": "images/ に png が無い"}
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return {"status": "SKIP", "reason": "Pillow が無い"}

    cw, ch, cols = 460, 170, 4
    rows = (len(images) * 2 + cols - 1) // cols
    page = Image.new("RGB", (cols * cw, rows * (ch + 20)), (24, 24, 28))
    draw = ImageDraw.Draw(page)
    i = 0
    for p in images:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        # ASCII labels: PIL's built-in bitmap font has no CJK glyphs, so Japanese
        # here renders as tofu boxes and the sheet cannot be read.
        for side, x0 in (("bottom-left", 0), ("bottom-right", max(0, w - cw))):
            crop = im.crop((x0, max(0, h - ch), min(w, x0 + cw), h))
            crop = crop.point(lambda v: min(255, int((v / 255) ** 0.55 * 255)))
            cx, cy = (i % cols) * cw, (i // cols) * (ch + 20)
            page.paste(crop, (cx, cy + 20))
            draw.text((cx + 4, cy + 5), f"{p.stem} {side}", fill=(255, 220, 120))
            i += 1
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = out_dir / f"corners_{ep_dir.name}.png"
    page.save(sheet)
    result = {"status": "OK", "images": len(images), "sheet": str(sheet)}
    if extras:
        result["extras"] = [p.name for p in extras]
    return result


def shipped_image_stems(scene_def: dict) -> set:
    """出荷に使う png の stem: scene_id と、visual.source 等が参照するファイル名。

    較正 (出荷 71 話): scene_id 以外の png は 14 話にあり、大半は退避 (`*_bk`) や参照写真
    (`wiki_*`)、検査の作業ファイル (`corner_*`, `_crop_*`) だが、**010_gauss は
    `visual.source` で `gemini_map.png` のような名前の画像を出荷している**。scene_id だけで
    絞るとそれがシートから消えるので、参照されている名前も残す。
    """
    stems = set()
    for sec in scene_def.get("sections", []) or []:
        for sc in sec.get("scenes", []) or []:
            if sc.get("scene_id"):
                stems.add(sc["scene_id"])
            v = sc.get("visual") or {}
            for key in ("source", "image", "source_image", "background"):
                val = v.get(key)
                if isinstance(val, str) and val:
                    stems.add(Path(val).stem)
    return stems


def split_scene_images(ep_dir: Path, images: list) -> tuple[list, list]:
    """(出荷に使う png, それ以外の png)。scene_definition.json が無ければ全部出荷扱い。"""
    sd_path = ep_dir / "scene_definition.json"
    try:
        with open(sd_path, encoding="utf-8") as f:
            sd = json.load(f)
    except Exception:
        return list(images), []
    ids = shipped_image_stems(sd)
    if not ids:
        return list(images), []
    keep = [p for p in images if p.stem in ids]
    extras = [p for p in images if p.stem not in ids]
    return keep, extras


def format_actions(checks: list[tuple[str, dict]]) -> list[str]:
    """The "now go and look at these" lines, derived from the check results.

    Shared by the CLI and by the pipeline. When only the CLI printed them, the
    pipeline reported `[OK] 11. 画像の下隅シート` and no path -- the check ran and
    the one thing it exists to do, point the eye at the sheet, did not happen.
    """
    lines: list[str] = []
    frames = next((r.get("extracted") for _n, r in checks if r.get("extracted")), None)
    if frames:
        lines.append(
            f"[ACTION] Manim の最終フレーム {len(frames)} 枚を見てください "
            "(placeholder / レイアウト重なり / 文字の可読性):"
        )
        lines += [f"  Read {p}" for p in frames]
    sheet = next((r.get("sheet") for _n, r in checks if r.get("sheet")), None)
    if sheet:
        lines.append(
            "[ACTION] 生成画像の下隅を一枚にまとめました。署名の描き込みが無いか見てください "
            "(ある回は 13 枚中 6 枚にあり、2 枚しか見ずに出荷しかけました):"
        )
        lines.append(f"  Read {sheet}")
    extras = next((r.get("extras") for _n, r in checks if r.get("extras")), None)
    if extras:
        lines.append(
            "[ACTION] images/ に scene 以外の png があります (シートからは外しました。"
            "作業ファイルなら削除): " + ", ".join(extras)
        )
    return lines


# The checks, in report order. Single source of truth for BOTH what runs and how
# many there are: the count used to be typed by hand in four places and had drifted
# to three different values (8 in the README, 10 in this file's docstring and
# --help, "nine" in run_all's). An earlier episode fixed the one occurrence in the printed
# output and left the rest, which is how a number written down beside a list goes
# stale -- so nothing below writes the number down.
#
# Signature is uniform (ep_dir, out_dir, subject) even where a check ignores two
# of the three, so the table stays a table.
CHECKS: tuple[tuple[str, object], ...] = (
    ("Manim fallbacks (G1)", lambda ep, out, subj: check_manim_fallbacks(ep)),
    ("Subtitle/narration hash sync (G2)", lambda ep, out, subj: check_subtitle_hash(ep)),
    ("description.txt freshness (G6)", lambda ep, out, subj: check_description_freshness(ep)),
    ("narration vs NS structural diff", lambda ep, out, subj: check_narration_ns_sync(ep)),
    ("Manim scene frame extraction", lambda ep, out, subj: extract_manim_frames(ep, out)),
    ("VOICEVOX proper noun verify", lambda ep, out, subj: verify_voicevox_proper_nouns(subj, ep)),
    ("Subtitle char count (>25 jp)", lambda ep, out, subj: check_subtitle_char_count(ep)),
    ("temp_videos sync", lambda ep, out, subj: check_temp_videos_sync(ep)),
    ("output_final.mp4 health", lambda ep, out, subj: check_output_final_health(ep)),
    ("章タイムスタンプ vs timing.json", lambda ep, out, subj: check_chapter_timestamps(ep)),
    ("画像の下隅シート (目視用)", lambda ep, out, subj: build_corner_sheet(ep, out)),
    ("subtitles_final.srt vs 冒頭ポーズ", lambda ep, out, subj: check_final_srt(ep)),
    ("disk が出荷物とずれていないか", lambda ep, out, subj: check_disk_vs_shipped(ep)),
)


def check_count() -> int:
    """How many checks there are. Read this instead of typing a number."""
    return len(CHECKS)


def run_all(ep_dir: Path, out_dir: Path, subject: str) -> list[tuple[str, dict]]:
    """Every check, as [(name, result)]. Split out of main() so the pipeline can
    run them without shelling out and parsing printed text.

    This file was written on as a hard gate after a build shipped with
    eight defects, and enforcement was left to a note in memory saying to run it.
    It was not run on an earlier episode: the reviewer watched a stale copy of the video and
    re-reported four already-fixed defects, which check 8 would have caught in a
    second. A check nobody runs is not a check.
    """
    # Resolve first: extract_manim_frames reports paths via relative_to(REPO_ROOT),
    # which raises on a relative out_dir. The CLI and the pipeline both pass an
    # absolute one, so this only ever bit a caller that did not - but a verifier
    # that dies while verifying is the failure mode this file exists to prevent.
    ep_dir, out_dir = Path(ep_dir).resolve(), Path(out_dir).resolve()
    return [
        (f"{i}. {label}", fn(ep_dir, out_dir, subject)) for i, (label, fn) in enumerate(CHECKS, 1)
    ]


def main():
    parser = argparse.ArgumentParser(
        description=f"Post-build structural verification ({check_count()} checks)"
    )
    parser.add_argument("episode_dir", help="Path to episode directory")
    parser.add_argument(
        "--subject",
        default=None,
        help="Override subject name (default: from episode_config.mathematician_ja)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "Output dir for extracted manim frames "
            "(default: <episode_dir>/_qa_frames -- per-episode so another "
            "episode's run cannot overwrite the frames this one asks you to look at)"
        ),
    )
    args = parser.parse_args()

    ep_dir = Path(args.episode_dir).resolve()
    if not ep_dir.is_dir():
        print(f"[ERROR] not a directory: {ep_dir}")
        return 1
    # Per episode. A repo-wide directory with episode-agnostic file names lets any
    # other episode's verification silently replace the frames the [ACTION] line
    # names: an earlier episode opened post_build_math_02.png and found an earlier episode's simplex
    # picture, because an earlier episode regression test writes there on every smoke run.
    out_dir = Path(args.out_dir) if args.out_dir else ep_dir / "_qa_frames"

    # Resolve subject
    subject = args.subject
    if subject is None:
        config = ep_dir / "episode_config.json"
        if config.exists():
            with open(config, encoding="utf-8") as f:
                conf = json.load(f)
            subject = conf.get("mathematician_ja") or conf.get("mathematician") or "(unknown)"
        else:
            subject = "(unknown)"

    print(f"\n{'=' * 70}\n  Post-build Verify: {ep_dir.name}  (subject: {subject})\n{'=' * 70}")

    checks = run_all(ep_dir, out_dir, subject)

    warnings = 0
    for name, result in checks:
        status = result.get("status", "?")
        print(f"\n[{status}] {name}")
        if status in ("WARN", "ERROR", "PARTIAL"):
            warnings += 1
            for k, v in result.items():
                if k == "status":
                    continue
                if isinstance(v, list):
                    for item in v[:5]:
                        print(f"  - {item}")
                    if len(v) > 5:
                        print(f"  ... and {len(v) - 5} more")
                else:
                    print(f"  {k}: {v}")
        elif status == "OK":
            # 概略のみ
            for k, v in result.items():
                if k in ("status", "results"):
                    continue
                if isinstance(v, list) and not v:
                    continue
                print(f"  {k}: {v}")
        else:  # SKIP
            print(f"  reason: {result.get('reason', '')}")

    for line in format_actions(checks):
        print(("\n" if line.startswith("[ACTION]") else "") + line)

    print(f"\n{'=' * 70}\nSummary: {warnings} warning section(s)\n{'=' * 70}")

    if warnings > 0:
        print(
            "\n[!] Review all warnings above before reporting build complete to user.\n"
            "[!] Do NOT skip Read of the extracted frames before declaring the build complete."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
