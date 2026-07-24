"""
video_assembler.py - Assemble final video from visual segments, audio, and subtitles

Usage:
    python video_assembler.py scene_definition.json timing.json --output-dir examples/moriarty
    python video_assembler.py scene_definition.json timing.json --output-dir examples/moriarty --no-subtitles
    python video_assembler.py scene_definition.json timing.json --output-dir examples/moriarty --dry-run

Input:  scene_definition.json + timing.json + visuals/*.mp4 + audio/*.wav + subtitles_drawtext.txt
Output: {output_dir}/output.mp4

Pipeline position:
    audio_generator.py → audio/*.wav + timing.json
    subtitle_generator.py → subtitles_drawtext.txt
    image_generator.py → images/*.png
    visual_generator.py → visuals/*.mp4
    ★ video_assembler.py → output.mp4
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import wave

# ─── Constants ───────────────────────────────────────────────────────────────

WIDTH = 1920
HEIGHT = 1080
FPS = 30
FONT_FILE = "_font.ttc"  # Local copy of BIZ UDMincho (Windows path workaround)


# ─── FFmpeg subprocess timeouts ──────────────────────────────────────────────
# ある回: a stuck ffmpeg in the assemble step hung a background run >1h
# before a manual kill. Every ffmpeg/ffprobe call below is bounded so a stuck
# encode fails fast instead of hanging. Tiered by workload, env-overridable:
#   - ffprobe: metadata read (sub-second normally)
#   - per-scene: pad/freeze/black for one <=30s segment
#   - full-video: concat + final merge re-encode the whole 10-19 min episode,
#     which on CPU-only hardware legitimately takes minutes -> a generous ceiling
#     (1800s) that still catches the pathological >1h hang without false-positives
#     on a long, legitimate encode. Tune down via env if your hardware is fast.
# Windows note: ffmpeg/ffprobe are leaf processes, so run()'s kill-on-timeout
# (TerminateProcess) reaps them without a process-tree walk.


def _ffmpeg_timeout_s(env_var: str, default: int) -> int:
    """Read a positive-int timeout override from the environment, else default."""
    raw = os.environ.get(env_var)
    if raw:
        try:
            val = int(raw.strip())
            if val > 0:
                return val
        except ValueError:
            pass
    return default


_FFPROBE_TIMEOUT_S = _ffmpeg_timeout_s("SUGAKUSHIKI_FFPROBE_TIMEOUT_S", 60)
_FFMPEG_TIMEOUT_S = _ffmpeg_timeout_s("SUGAKUSHIKI_FFMPEG_TIMEOUT_S", 300)
_FFMPEG_FULL_TIMEOUT_S = _ffmpeg_timeout_s("SUGAKUSHIKI_FFMPEG_FULL_TIMEOUT_S", 1800)


class _FFmpegTimeout(RuntimeError):
    """An ffmpeg/ffprobe subprocess exceeded its timeout and was killed."""


def _run_ffmpeg(cmd, timeout, label, **kwargs):
    """subprocess.run(cmd) bounded by `timeout`.

    Returns the CompletedProcess, or raises _FFmpegTimeout (the process is
    killed) so callers fail fast instead of hanging on a stuck ffmpeg. ffmpeg/
    ffprobe are leaf processes, so run()'s kill-on-timeout reaps them cleanly
    on Windows.
    """
    kwargs.setdefault("capture_output", True)
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        raise _FFmpegTimeout(f"{label}: ffmpeg timed out after {timeout}s") from exc


# ─── Audio helpers ───────────────────────────────────────────────────────────


def get_wav_duration(filepath: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(filepath, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def generate_silence_wav(
    filepath: str,
    duration: float,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
):
    """Generate a silent WAV file."""
    n_frames = int(sample_rate * duration)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * (n_frames * channels * sample_width))


def concatenate_wavs(wav_files: list, output_path: str):
    """Concatenate multiple WAV files into one.

    All files must have the same format (channels, sample width, frame rate).
    """
    if not wav_files:
        return

    with wave.open(wav_files[0], "rb") as wf:
        params = wf.getparams()

    with wave.open(output_path, "wb") as out:
        out.setparams(params)
        for filepath in wav_files:
            with wave.open(filepath, "rb") as wf:
                out.writeframes(wf.readframes(wf.getnframes()))


# ─── Video helpers ───────────────────────────────────────────────────────────


def get_video_duration(filepath: str) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        filepath,
    ]
    try:
        result = _run_ffmpeg(
            cmd,
            _FFPROBE_TIMEOUT_S,
            "get_video_duration",
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except _FFmpegTimeout as exc:
        print(f"  [WARN] {exc}")
        return 0.0
    if result.returncode != 0:
        return 0.0
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0.0))


def pad_video_with_freeze(
    input_path: str,
    output_path: str,
    pad_duration: float,
    width: int = WIDTH,
    height: int = HEIGHT,
    fps: int = FPS,
):
    """Extend a video by freezing its last frame for pad_duration seconds.

    Uses tpad filter which is efficient and avoids re-encoding the whole video.
    Falls back to a simpler approach if tpad fails. Any ffmpeg timeout degrades
    to copying the input unchanged -- the freeze-pad is cosmetic and a stuck
    encode must not hang assembly.
    """
    if pad_duration <= 0.01:
        shutil.copy2(input_path, output_path)
        return
    try:
        _pad_video_with_freeze_impl(input_path, output_path, pad_duration, width, height, fps)
    except _FFmpegTimeout as exc:
        print(f"  [WARN] {exc} -> copying segment without freeze-pad")
        shutil.copy2(input_path, output_path)


def _pad_video_with_freeze_impl(input_path, output_path, pad_duration, width, height, fps):
    # Method: tpad filter (efficient, single pass)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        f"tpad=stop_mode=clone:stop_duration={pad_duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",  # no audio in visual segments
        output_path,
    ]
    result = _run_ffmpeg(
        cmd, _FFMPEG_TIMEOUT_S, "pad tpad", text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode == 0:
        return

    # Fallback: re-encode with concat approach
    # Extract last frame, make a still video, then concat
    temp_dir = os.path.dirname(output_path)
    last_frame = os.path.join(temp_dir, "_last_frame.png")
    freeze_vid = os.path.join(temp_dir, "_freeze.mp4")

    try:
        # Extract last frame
        duration = get_video_duration(input_path)
        seek_time = max(0, duration - 0.1)
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(seek_time),
                "-i",
                input_path,
                "-frames:v",
                "1",
                last_frame,
            ],
            _FFMPEG_TIMEOUT_S,
            "pad extract-frame",
        )

        # Make freeze video from last frame
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                last_frame,
                "-t",
                str(pad_duration),
                "-vf",
                f"scale={width}:{height}",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(fps),
                freeze_vid,
            ],
            _FFMPEG_TIMEOUT_S,
            "pad freeze",
        )

        # Concat original + freeze
        concat_list = os.path.join(temp_dir, "_concat_pad.txt")
        with open(concat_list, "w") as f:
            f.write(f"file '{os.path.abspath(input_path)}'\n")
            f.write(f"file '{os.path.abspath(freeze_vid)}'\n")

        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-an",
                output_path,
            ],
            _FFMPEG_TIMEOUT_S,
            "pad concat",
        )

    finally:
        for f in [last_frame, freeze_vid, concat_list]:
            if os.path.exists(f):
                os.remove(f)


def ensure_font_file(output_dir: str) -> str:
    """Copy BIZ UDMincho font to output_dir as _font.ttc (Windows path workaround).

    Returns the path to the font file.
    """
    font_path = os.path.join(output_dir, FONT_FILE)
    if os.path.exists(font_path):
        return font_path

    # Search for BIZ UDMincho
    candidates = [
        r"C:\Windows\Fonts\BIZ-UDMinchoM.ttc",
        r"C:\Windows\Fonts\BIZUDMincho-Regular.ttc",
        "/usr/share/fonts/truetype/bizud-mincho/BIZUDMincho-Regular.ttf",
    ]
    for src in candidates:
        if os.path.exists(src):
            shutil.copy2(src, font_path)
            return font_path

    return ""


# ─── Scene ordering ─────────────────────────────────────────────────────────


def get_scene_order(scene_def: dict) -> list[str]:
    """Extract ordered list of scene_ids from scene_definition.json."""
    scene_ids = []
    for section in scene_def["sections"]:
        for scene in section["scenes"]:
            scene_ids.append(scene["scene_id"])
    return scene_ids


# ─── Assembly pipeline ───────────────────────────────────────────────────────


def build_combined_audio(scene_ids: list[str], timing: dict, audio_dir: str, work_dir: str) -> str:
    """Concatenate per-scene WAVs with inter-scene pauses.

    Returns path to combined WAV file.
    """
    output_path = os.path.join(work_dir, "combined_audio.wav")
    segments = []

    for _i, scene_id in enumerate(scene_ids):
        scene_timing = timing["scenes"].get(scene_id, {})
        pause_after = scene_timing.get("pause_after", 0.5)

        # Scene audio
        scene_wav = os.path.join(audio_dir, f"{scene_id}.wav")
        if os.path.exists(scene_wav):
            segments.append(scene_wav)
        else:
            # Generate silence as placeholder
            dur = scene_timing.get("duration", 5.0)
            placeholder = os.path.join(work_dir, f"_placeholder_{scene_id}.wav")
            generate_silence_wav(placeholder, dur)
            segments.append(placeholder)

        # Inter-scene pause (include for ALL scenes including last for clean ending)
        if pause_after > 0.01:
            pause_wav = os.path.join(work_dir, f"_pause_{scene_id}.wav")
            generate_silence_wav(pause_wav, pause_after)
            segments.append(pause_wav)

    concatenate_wavs(segments, output_path)
    return output_path


def build_combined_video(
    scene_ids: list[str], timing: dict, visuals_dir: str, work_dir: str
) -> str:
    """Concatenate per-scene video segments with freeze-frame pauses.

    Each scene is padded with its pause_after duration (freeze last frame).
    Then all padded segments are concatenated.

    Returns path to combined video file.
    """
    padded_files = []

    for _i, scene_id in enumerate(scene_ids):
        scene_timing = timing["scenes"].get(scene_id, {})
        pause_after = scene_timing.get("pause_after", 0.5)

        visual_path = os.path.join(visuals_dir, f"{scene_id}.mp4")
        if not os.path.exists(visual_path):
            print(f"  [WARN] Missing: {visual_path}")
            # Generate black placeholder
            dur = scene_timing.get("duration", 5.0) + pause_after
            placeholder = os.path.join(work_dir, f"_black_{scene_id}.mp4")
            try:
                _run_ffmpeg(
                    [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c=#1a1a2e:s={WIDTH}x{HEIGHT}:d={dur:.3f}:r={FPS}",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-crf",
                        "23",
                        "-pix_fmt",
                        "yuv420p",
                        placeholder,
                    ],
                    _FFMPEG_TIMEOUT_S,
                    f"black placeholder {scene_id}",
                )
                padded_files.append(placeholder)
            except _FFmpegTimeout as exc:
                # Drop the segment rather than append a missing file (which would
                # break the concat below). The gap is surfaced by the print.
                print(f"  [ERROR] {exc} -> dropping segment {scene_id}")
            continue

        if pause_after > 0.01:
            padded_path = os.path.join(work_dir, f"_padded_{scene_id}.mp4")
            pad_video_with_freeze(visual_path, padded_path, pause_after)
            padded_files.append(padded_path)
        else:
            padded_files.append(visual_path)

    # Concatenate all segments
    output_path = os.path.join(work_dir, "combined_video.mp4")
    concat_list = os.path.join(work_dir, "_concat_list.txt")

    with open(concat_list, "w", encoding="utf-8") as f:
        for p in padded_files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        "-an",
        output_path,
    ]
    try:
        result = _run_ffmpeg(
            cmd,
            _FFMPEG_FULL_TIMEOUT_S,
            "concat",
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except _FFmpegTimeout as exc:
        print(f"  ERROR in concat: {exc}")
        sys.exit(1)
    if result.returncode != 0:
        print(f"  ERROR in concat: {result.stderr[:500]}")
        sys.exit(1)

    return output_path


def merge_final(
    video_path: str, audio_path: str, subtitle_path: str, output_path: str, output_dir: str
):
    """Merge combined video + audio, optionally overlaying subtitles.

    Uses a single FFmpeg command to minimize quality loss.

    The drawtext filter in subtitles_drawtext.txt uses ``fontfile=_font.ttc``
    (relative path). FFmpeg resolves this against its cwd, so we launch
    FFmpeg with ``cwd=output_dir`` and convert all other paths to absolute
    to survive the cwd change. Without this, running from a different cwd
    causes FFmpeg to silently fall back to a non-CJK font and Japanese
    subtitles render as tofu (□).
    """
    # Absolutize all paths so cwd=output_dir below does not break resolution.
    video_path_abs = os.path.abspath(video_path)
    audio_path_abs = os.path.abspath(audio_path)
    output_path_abs = os.path.abspath(output_path)
    output_dir_abs = os.path.abspath(output_dir)
    subtitle_path_abs = os.path.abspath(subtitle_path) if subtitle_path else None

    cmd = ["ffmpeg", "-y", "-i", video_path_abs, "-i", audio_path_abs]

    if subtitle_path_abs and os.path.exists(subtitle_path_abs):
        # Ensure font file exists in output_dir
        font_path = ensure_font_file(output_dir_abs)
        if not font_path:
            print("  [WARN] Font not found. Subtitles will use default font.")

        # Apply drawtext filter_script for subtitles
        cmd += [
            "-filter_script:v",
            subtitle_path_abs,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
        ]
    else:
        # No subtitles: copy video stream
        cmd += ["-c:v", "copy"]

    cmd += [
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        output_path_abs,
    ]

    # cwd=output_dir so drawtext's fontfile=_font.ttc (relative) resolves
    # to output_dir/_font.ttc regardless of the caller's cwd.
    try:
        result = _run_ffmpeg(
            cmd,
            _FFMPEG_FULL_TIMEOUT_S,
            "merge",
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=output_dir_abs,
        )
    except _FFmpegTimeout as exc:
        print(f"  ERROR in merge: {exc}")
        # Retry without subtitles: the no-subtitle path uses -c:v copy (no
        # re-encode), so it cannot hit the same drawtext-encode stall.
        if subtitle_path:
            print("  Retrying without subtitles...")
            merge_final(video_path, audio_path, None, output_path, output_dir)
        else:
            sys.exit(1)
        return
    if result.returncode != 0:
        print(f"  ERROR in merge: {result.stderr[:500]}")

        # Fallback: try without subtitles
        if subtitle_path:
            print("  Retrying without subtitles...")
            merge_final(video_path, audio_path, None, output_path, output_dir)
        else:
            sys.exit(1)


# ─── Dry-run / verification ─────────────────────────────────────────────────


def verify_inputs(
    scene_ids: list[str], timing: dict, visuals_dir: str, audio_dir: str, subtitle_path: str
) -> dict:
    """Check that all required input files exist.

    Returns a dict with counts and any missing files.
    """
    missing_visuals = []
    missing_audio = []
    total_duration = 0.0
    total_with_pause = 0.0

    for _i, scene_id in enumerate(scene_ids):
        scene_timing = timing["scenes"].get(scene_id, {})
        duration = scene_timing.get("duration", 0.0)
        pause_after = scene_timing.get("pause_after", 0.5)
        total_duration += duration
        total_with_pause += duration + pause_after

        visual = os.path.join(visuals_dir, f"{scene_id}.mp4")
        if not os.path.exists(visual):
            missing_visuals.append(scene_id)

        audio = os.path.join(audio_dir, f"{scene_id}.wav")
        if not os.path.exists(audio):
            missing_audio.append(scene_id)

    has_subtitles = subtitle_path and os.path.exists(subtitle_path)

    return {
        "scene_count": len(scene_ids),
        "total_duration": total_duration,
        "total_with_pause": total_with_pause,
        "missing_visuals": missing_visuals,
        "missing_audio": missing_audio,
        "has_subtitles": has_subtitles,
    }


def print_report(info: dict, scene_ids: list[str], timing: dict, visuals_dir: str, audio_dir: str):
    """Print assembly report."""
    print(f"\n{'=' * 60}")
    print("Video Assembly Report")
    print(f"{'=' * 60}")
    print(f"  Scenes:         {info['scene_count']}")
    print(
        f"  Narration:      {info['total_duration']:.1f}s ({info['total_duration'] / 60:.1f} min)"
    )
    print(
        f"  With pauses:    {info['total_with_pause']:.1f}s ({info['total_with_pause'] / 60:.1f} min)"
    )
    print(f"  Subtitles:      {'[OK]' if info['has_subtitles'] else '[NG] not found'}")

    if info["missing_visuals"]:
        print(f"\n  [WARN] Missing visuals ({len(info['missing_visuals'])}):")
        for sid in info["missing_visuals"]:
            print(f"    - visuals/{sid}.mp4")

    if info["missing_audio"]:
        print(f"\n  [WARN] Missing audio ({len(info['missing_audio'])}):")
        for sid in info["missing_audio"]:
            print(f"    - audio/{sid}.wav")

    # Per-scene breakdown
    print("\n  Scene breakdown:")
    print(f"  {'Scene':<15} {'Dur':>6} {'Pause':>6} {'Visual':>8} {'Audio':>8}")
    print(f"  {'-' * 15} {'-' * 6} {'-' * 6} {'-' * 8} {'-' * 8}")

    for scene_id in scene_ids:
        st = timing["scenes"].get(scene_id, {})
        dur = st.get("duration", 0.0)
        pause = st.get("pause_after", 0.0)

        v_path = os.path.join(visuals_dir, f"{scene_id}.mp4")
        a_path = os.path.join(audio_dir, f"{scene_id}.wav")
        v_status = "[OK]" if os.path.exists(v_path) else "[NG]"
        a_status = "[OK]" if os.path.exists(a_path) else "[NG]"

        print(f"  {scene_id:<15} {dur:>5.1f}s {pause:>5.1f}s {v_status:>8} {a_status:>8}")

    print(f"{'=' * 60}")


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Assemble final video from visual segments, audio, and subtitles",
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument("timing_json", help="Path to timing.json")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Episode output directory (contains audio/, visuals/, subtitles_drawtext.txt)",
    )
    parser.add_argument(
        "--output-name", default="output.mp4", help="Output filename (default: output.mp4)"
    )
    parser.add_argument("--no-subtitles", action="store_true", help="Skip subtitle overlay")
    parser.add_argument(
        "--dry-run", action="store_true", help="Verify inputs and print report without assembling"
    )
    args = parser.parse_args()

    # Load data
    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)
    with open(args.timing_json, encoding="utf-8") as f:
        timing = json.load(f)

    # Resolve paths
    output_dir = args.output_dir
    visuals_dir = os.path.join(output_dir, "visuals")
    audio_dir = os.path.join(output_dir, "audio")
    subtitle_path = (
        None if args.no_subtitles else os.path.join(output_dir, "subtitles_drawtext.txt")
    )
    output_path = os.path.join(output_dir, args.output_name)

    # Get scene order
    scene_ids = get_scene_order(scene_def)

    # Verify inputs
    info = verify_inputs(scene_ids, timing, visuals_dir, audio_dir, subtitle_path)
    print_report(info, scene_ids, timing, visuals_dir, audio_dir)

    if args.dry_run:
        if info["missing_visuals"] or info["missing_audio"]:
            print("\n[WARN] Some inputs are missing. Fix before assembling.")
        else:
            print("\n[OK] All inputs present. Ready to assemble.")
        return

    # Check for critical missing files
    if len(info["missing_visuals"]) == info["scene_count"]:
        print("\nERROR: No visual segments found. Run visual_generator.py first.")
        sys.exit(1)
    if len(info["missing_audio"]) == info["scene_count"]:
        print("\nERROR: No audio files found. Run audio_generator.py first.")
        sys.exit(1)

    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=30)
    except FileNotFoundError:
        print("ERROR: FFmpeg not found in PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: FFmpeg did not respond to -version within 30s")
        sys.exit(1)

    # Create work directory for temp files
    work_dir = os.path.join(output_dir, "_assembly_temp")
    os.makedirs(work_dir, exist_ok=True)

    try:
        start_time = time.time()

        # Step 1: Build combined audio
        print("\n[1/3] Building combined audio...")
        combined_audio = build_combined_audio(scene_ids, timing, audio_dir, work_dir)
        audio_duration = get_wav_duration(combined_audio)
        print(f"  → {audio_duration:.1f}s ({audio_duration / 60:.1f} min)")

        # Step 2: Build combined video
        print(f"\n[2/3] Building combined video ({len(scene_ids)} segments)...")
        combined_video = build_combined_video(scene_ids, timing, visuals_dir, work_dir)
        video_duration = get_video_duration(combined_video)
        print(f"  → {video_duration:.1f}s ({video_duration / 60:.1f} min)")

        # Duration check
        drift = abs(video_duration - audio_duration)
        if drift > 1.0:
            print(
                f"\n  [WARN] Duration mismatch: video={video_duration:.1f}s, audio={audio_duration:.1f}s (drift={drift:.1f}s)"
            )
            print("  Output will use the longer stream's duration.")

        # Step 3: Merge video + audio + subtitles
        print("\n[3/3] Merging final video...")
        sub_label = (
            "with subtitles"
            if (subtitle_path and os.path.exists(subtitle_path))
            else "no subtitles"
        )
        print(f"  ({sub_label})")
        merge_final(combined_video, combined_audio, subtitle_path, output_path, output_dir)

        elapsed = time.time() - start_time

        # Final report
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            final_duration = get_video_duration(output_path)
            print(f"\n{'=' * 60}")
            print("[OK] Assembly complete!")
            print(f"  Output:   {output_path}")
            print(f"  Duration: {final_duration:.1f}s ({final_duration / 60:.1f} min)")
            print(f"  Size:     {size_mb:.1f} MB")
            print(f"  Elapsed:  {elapsed:.1f}s")
            print(f"{'=' * 60}")
        else:
            print(f"\n[NG] Output file not created: {output_path}")
            sys.exit(1)

    finally:
        # Cleanup temp files
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
