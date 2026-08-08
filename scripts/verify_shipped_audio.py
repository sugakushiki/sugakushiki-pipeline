"""verify_shipped_audio.py - verify readings in the SHIPPED output_final.mp4.

stt_qa.py transcribes the per-scene wavs (audio/*.wav, pre-assemble). This tool
closes the loop by transcribing from the FINAL rendered video (post speed-
normalization + concat + bgm) -- what viewers actually hear. It extracts each
scene's audio window from output_final.mp4 (timing.json global offset + the bgm
intro_pause), STTs via Gemini, and runs the SAME known-misread corpus as stt_qa.

Motivation: the decisive reading check was repeatedly "STT the
SHIPPED audio, not the isolated wav / the scene-def text" -- done by hand ~5x.
This automates that discipline. advisory + on-demand (NOT wired into every build;
it doubles STT cost vs the scene-wav stt_qa). Graceful degrade without
GOOGLE_API_KEY / google-genai.

Usage:
  python scripts/verify_shipped_audio.py episodes/XXX/scene_definition.json
      [--video output_final.mp4] [--scenes id1,id2] [--report path]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Reuse the exact STT + reading-check corpus the scene-wav QA uses.
from stt_qa import (
    _READING_CHECKS,
    _STT_RULES,
    _is_katakana_mode,
    _load_gemini_key,
    _norm_kana,
    _transcribe,
)


def _extract(video: str, start: float, dur: float, out_wav: str) -> bool:
    """Extract [start, start+dur) from video to a mono 24k wav (STT-friendly)."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{dur:.3f}",
            "-i",
            video,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "24000",
            out_wav,
        ],
        capture_output=True,
    )
    return os.path.exists(out_wav) and os.path.getsize(out_wav) > 0


def _check_transcript(transcript: str, narr_text: str) -> list:
    """Run the stt_qa corpus on one transcript. Returns (name, ctx, note) hits."""
    hits = []
    # An earlier episode FP guard, same as stt_qa: when Gemini transcribes in katakana-particle
    # mode it spells every topic は as ハ regardless of what was actually spoken, so
    # the particle rules cannot discriminate there. This checker imported the corpus
    # but not the guard, which made the SHIPPED-audio check - the one CLAUDE.md calls
    # decisive - noisier than the scene-wav check it is meant to backstop.
    km = _is_katakana_mode(transcript)
    for rule in _STT_RULES:
        if rule.get("katakana_unreliable") and km:
            continue
        for m in rule["regex"].finditer(transcript):
            ctx = transcript[max(0, m.start() - 6) : m.end() + 6]
            hits.append((rule["name"], ctx, rule["note"]))
    t_norm = _norm_kana(transcript)
    for surface, correct, wrongs, note in _READING_CHECKS:
        if surface not in narr_text:
            continue
        hit = [w for w in wrongs if w in t_norm]
        if hit and correct not in t_norm:
            hits.append((f"misread:{surface}", f"STT={','.join(hit)} (expect {correct})", note))
    return hits


def main() -> int:
    p = argparse.ArgumentParser(
        description="Verify readings in the shipped output_final.mp4 (Gemini STT)"
    )
    p.add_argument("scene_definition")
    p.add_argument("--video", default=None, help="default: <ep>/output_final.mp4")
    p.add_argument("--scenes", default=None, help="comma-separated scene_ids (default all)")
    p.add_argument("--report", default=None)
    args = p.parse_args()

    ep_dir = os.path.dirname(os.path.abspath(args.scene_definition))
    video = args.video or os.path.join(ep_dir, "output_final.mp4")
    timing_path = os.path.join(ep_dir, "timing.json")
    report_path = args.report or os.path.join(ep_dir, "shipped_audio_qa_report.txt")

    print("=" * 60)
    print("  Shipped-audio reading QA (STT from output_final.mp4)")
    print("=" * 60)
    for pth in (args.scene_definition, video, timing_path):
        if not os.path.exists(pth):
            print(f"  [SKIP] not found: {pth}")
            return 0

    key = _load_gemini_key()
    if not key:
        print("  [SKIP] GOOGLE_API_KEY not found (shipped-audio STT skipped).")
        return 0
    try:
        from google import genai
    except ImportError:
        print("  [SKIP] google-genai not installed.")
        return 0
    client = genai.Client(api_key=key)

    with open(args.scene_definition, encoding="utf-8") as f:
        scene_def = json.load(f)
    with open(timing_path, encoding="utf-8") as f:
        timing = json.load(f)

    # bgm_mixer prepends intro_pause seconds, shifting the whole timeline.
    intro_pause = 1.0
    cfg = os.path.join(ep_dir, "episode_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                intro_pause = float(json.load(f).get("bgm", {}).get("intro_pause", 1.0))
        except Exception:
            pass

    want = set(args.scenes.split(",")) if args.scenes else None
    scenes_by_id = {
        s.get("scene_id"): s for sec in scene_def.get("sections", []) for s in sec.get("scenes", [])
    }

    warnings = []
    report_lines = []
    n = 0
    tmpd = tempfile.mkdtemp()
    for sid, sc in timing.get("scenes", {}).items():
        if want and sid not in want:
            continue
        gs = sc.get("global_start", 0.0)
        dur = sc.get("duration", 0.0)
        if dur <= 0:
            continue
        wav = os.path.join(tmpd, f"{sid}.wav")
        if not _extract(video, gs + intro_pause, dur, wav):
            print(f"  [MISS] {sid}: extract failed")
            continue
        n += 1
        try:
            transcript = _transcribe(client, wav)
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  [ERR]  {sid}: {e!r}")
            continue
        report_lines.append(f"===== {sid} ({gs + intro_pause:.1f}s) =====\n{transcript}")

        narr_text = " ".join((scenes_by_id.get(sid, {}) or {}).get("narration", []) or []).replace(
            "|", ""
        )
        hits = _check_transcript(transcript, narr_text)
        if hits:
            print(f"  [WARN] {sid}: {len(hits)} suspicious reading(s)")
            for name, ctx, note in hits:
                print(f"      - {name}: ...{ctx}...")
                print(f"        {note}")
                warnings.append((sid, name, ctx))
        else:
            print(f"  [OK]   {sid}")

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(report_lines))
        print(f"\n  Transcript report: {report_path}")
    except OSError as e:
        print(f"\n  [WARN] could not write report: {e}")

    print(f"\n  Checked {n} scene(s) from the SHIPPED video, {len(warnings)} WARN.")
    print("  NOTE: STT misses too (voicing/subtle) -- ear spot-check before publishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
