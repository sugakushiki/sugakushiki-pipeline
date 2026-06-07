"""
pipeline.py - Run the full video generation pipeline with a single command

Usage:
    python pipeline.py episodes/001_erdos/episode_config.json
    python pipeline.py episodes/001_erdos/episode_config.json --skip-script
    python pipeline.py episodes/001_erdos/episode_config.json --skip-manim --skip-images
    python pipeline.py episodes/001_erdos/episode_config.json --steps audio,subtitles,visuals,assemble

Partial rebuild (single scene):
    python pipeline.py episodes/006_shannon/episode_config.json --rebuild-scene math_02

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
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pipeline_log

# Ensure subprocesses use UTF-8 output (avoid cp932 crashes on Windows)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

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

# Output filenames (B-19 atomic rename: assemble -> intermediate, bgm -> final)
# Why: prior layout wrote output.mp4 from assemble, then overwrote into output_final.mp4
# from bgm. A failed bgm step left a stale output_final.mp4 from the previous run,
# which was indistinguishable from a fresh successful build. Splitting the names
# makes "output_final.mp4 exists" mean "the full pipeline finished".
OUTPUT_ASSEMBLED = "output_assembled.mp4"
OUTPUT_FINAL = "output_final.mp4"

# Required sections in description.txt (B-12 / D-3 post-pipeline verification)
_DESCRIPTION_REQUIRED_SECTIONS = [
    "【音声合成】",
    "【BGM】",
    "【映像素材】",
    "【画像クレジット】",
    "【主要参考文献】",
]


def verify_outputs(episode_dir: str, steps_run: list[str], scene_json: str) -> list[str]:
    """Post-pipeline output verification (B-12 / D-3).

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

    if "credits" in steps_run:
        # 【画像クレジット】is only expected when Wikimedia reference photos are
        # used. For use_reference=false episodes (Gemini-only images, credited
        # under 【映像素材】) the section is legitimately absent — don't WARN
        #.
        use_reference = True
        cfg_path = os.path.join(episode_dir, "episode_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    _cfg = json.load(f)
                use_reference = bool(
                    _cfg.get("image_style", {}).get("use_reference", True)
                )
            except Exception:
                pass
        required_sections = [
            s
            for s in _DESCRIPTION_REQUIRED_SECTIONS
            if not (s == "【画像クレジット】" and not use_reference)
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
    if os.path.exists(subtitles_path) and os.path.exists(subtitles_meta_path) and os.path.exists(scene_json):
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
                scene_reasons = ", ".join(
                    f"{fb.get('scene_id', '?')}({fb.get('reason', '?')})"
                    for fb in fallbacks
                )
                warnings.append(
                    f"  [visuals] {len(fallbacks)} Manim scene(s) fell back to "
                    f"text_overlay placeholder: {scene_reasons}. "
                    "Check src/manim_templates/ for timeout/render errors; "
                    "consider template optimization or MANIM_TIMEOUT increase."
                )
        except Exception:
            pass

    # G6: description.txt staleness check.
    # If credits step was skipped but scene_def/config has been edited since,
    # description.txt may contain stale chapter / BGM / references. Day 20
    # で `--steps audio,visuals,assemble,bgm` で credits skip した結果、
    # description.txt の chapter「骨」 (narrative では「業績」修正済) が古いまま
    # 残り user 指摘で発覚した failure mode の検出。
    desc_path = os.path.join(episode_dir, "description.txt")
    if os.path.exists(desc_path) and os.path.exists(scene_json):
        try:
            desc_mtime = os.path.getmtime(desc_path)
            scene_mtime = os.path.getmtime(scene_json)
            episode_config_path = os.path.join(episode_dir, "episode_config.json")
            config_mtime = (
                os.path.getmtime(episode_config_path)
                if os.path.exists(episode_config_path)
                else 0
            )
            newer_source_mtime = max(scene_mtime, config_mtime)
            if desc_mtime < newer_source_mtime:
                import datetime
                desc_dt = datetime.datetime.fromtimestamp(desc_mtime).isoformat(timespec="seconds")
                src_dt = datetime.datetime.fromtimestamp(newer_source_mtime).isoformat(timespec="seconds")
                warnings.append(
                    f"  [credits] description.txt is STALE (desc {desc_dt} < source {src_dt}). "
                    "Re-run with `--steps credits` to refresh chapter / BGM / references."
                )
        except OSError:
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


def _preflight_claude_cli(timeout_sec: int = 25) -> tuple[bool, str]:
    """Ping Claude CLI with a trivial prompt. Returns (ok, message).

    Cost: ~10-20s when healthy, 2-5s when 401. Trades a fixed startup cost
    for avoiding the expired-token-style 57-minute dead-end on an expired token.
    """
    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format",
                "text",
                "--allowedTools",
                "Read",
                "--model",
                "claude-opus-4-6",
                "reply exactly with the word pong",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False, f"Claude CLI ping timed out after {timeout_sec}s"
    except FileNotFoundError:
        return False, "Claude CLI ('claude' command) not found in PATH"

    combined = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        hint = (
            "authentication (401)"
            if "401" in combined or "authenticat" in combined.lower()
            else "non-zero exit"
        )
        return False, f"Claude CLI failed [{hint}]: {combined.strip()[:300]}"
    if "pong" not in (result.stdout or "").lower():
        return False, f"Claude CLI unexpected response: {(result.stdout or '').strip()[:200]}"
    return True, "OK"


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


def run_preflight_checks(steps: list[str]) -> None:
    """Run fail-fast environment checks; sys.exit(1) with clear guidance on failure."""
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

    # (2) Claude CLI auth — only if steps that call it will run
    claude_steps = {"script"}  # QA gate and pronunciation check also call Claude CLI
    needs_claude = bool(claude_steps & set(steps))
    if needs_claude:
        print("  [2/3] Claude CLI auth... ", end="", flush=True)
        ok, msg = _preflight_claude_cli()
        if not ok:
            print("FAIL")
            print(f"    {msg}")
            print()
            print("  Fix: Open Claude Code in VSCode/terminal and re-login if needed,")
            print("       or set ANTHROPIC_API_KEY in the environment.")
            print()
            pipeline_log.emit(
                pipeline_log.LEVEL_CRITICAL,
                "preflight",
                "claude cli auth failed",
                detail=msg,
            )
            pipeline_log.close()
            sys.exit(1)
        print(msg)
    else:
        print("  [2/3] Claude CLI auth... skipped (steps don't require it)")

    # (3) VOICEVOX — only if audio step will run
    if "audio" in steps:
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
    else:
        print("  [3/3] VOICEVOX server... skipped (audio step not selected)")

    pipeline_log.step_end(
        "preflight",
        exit_code=0,
        duration_ms=int((time.time() - preflight_start) * 1000),
    )
    print()


# ===========================================================================
# Partial rebuild: --rebuild-scene SCENE_ID
# ===========================================================================


def _run_partial_rebuild(
    scene_id: str,
    config_path: str,
    episode_dir: str,
    config: dict,
    src_dir: str,
    bgm_file: str,
    bgm_config: dict,
) -> None:
    """Rebuild a single scene and re-run assembly + credits + bgm.

    This is a completely separate code path from the full build.
    Called only when --rebuild-scene is specified.
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

    # --- Step 1: Audio regeneration for the target scene ---
    print("\n[PARTIAL REBUILD] Step 1/6: Audio regeneration")
    sys.path.insert(0, src_dir)
    from audio_generator import rebuild_single_scene_audio

    pipeline_log.step_start("audio (partial rebuild)", scene_id=scene_id)
    _audio_start = time.time()
    audio_ok = rebuild_single_scene_audio(scene_json, scene_id, episode_dir)
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

    # --- Step 2: Subtitle regeneration (full, since global timestamps changed) ---
    print("\n[PARTIAL REBUILD] Step 2/6: Subtitle regeneration (full)")
    cmd = [
        sys.executable,
        os.path.join(src_dir, "subtitle_generator.py"),
        timing_json,
        "--output-dir",
        episode_dir,
        "--scene-json",
        scene_json,
    ]
    run_step("subtitles (partial rebuild)", cmd)

    # --- Step 3: Image regeneration (only for ken_burns scenes) ---
    if vtype == "ken_burns":
        print("\n[PARTIAL REBUILD] Step 3/6: Image regeneration (ken_burns)")
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
    else:
        print(f"\n[PARTIAL REBUILD] Step 3/6: Image regeneration -- skipped ({vtype})")

    # --- Step 4: Visual regeneration for the target scene ---
    print("\n[PARTIAL REBUILD] Step 4/6: Visual regeneration")
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

    # --- Step 5: Video assembly (full, unavoidable) ---
    print("\n[PARTIAL REBUILD] Step 5/6: Video assembly (full)")
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

        drainer = threading.Thread(
            target=_drain_stderr,
            args=(proc.stderr, pipeline_log.merge_child_event, _on_raw),
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


def run_step(step_name: str, cmd: list[str], required: bool = True) -> bool:
    """Run a pipeline step as subprocess. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"  Step: {step_name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    pipeline_log.step_start(step_name, command=" ".join(cmd))
    start = time.time()
    exit_code = _run_subprocess_with_stderr_capture(cmd)
    elapsed = time.time() - start
    pipeline_log.step_end(
        step_name, exit_code=exit_code, duration_ms=int(elapsed * 1000)
    )

    if exit_code != 0:
        print(f"\n[FAIL] Step '{step_name}' failed (exit code {exit_code}, {elapsed:.1f}s)")
        if required:
            print("Pipeline aborted.")
            sys.exit(1)
        return False

    print(f"\n[OK] Step '{step_name}' complete ({elapsed:.1f}s)")
    return True


def main():
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
        "--skip-fact-check",
        action="store_true",
        help="B-17: skip pre-script episode_config fact check",
    )
    parser.add_argument(
        "--fact-check-allow-warn",
        action="store_true",
        help="B-17: continue on WARNING (CRITICAL still aborts)",
    )
    parser.add_argument(
        "--skip-qa-image-narration",
        action="store_true",
        help="B-18: skip narration-image consistency check (Gate 2). Default: enabled with --qa.",
    )
    parser.add_argument(
        "--skip-portrait-lint",
        action="store_true",
        help="Day 21 強化 H2: skip portrait_prompt_lint。default: enabled when use_reference scenes + wiki_*.jpg refs exist。WARN only、build halt しない。",
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
        help="B-11: skip route_map collision preflight (Layer 2). "
        "Layer 3 in-render WARN still runs.",
    )
    parser.add_argument(
        "--allow-route-collision",
        action="store_true",
        help="B-11: continue pipeline even if route_map collision is detected. "
        "Both preflight (Layer 2) and in-render (Layer 3) become advisory.",
    )
    parser.add_argument(
        "--auto-fix-route-collisions",
        action="store_true",
        help="B-11: opt-in 3-stage auto-fix of route_map collisions "
        "(label avoidance -> bounds expansion -> title fontsize). "
        "Mutates scene_definition.json with _route_map_auto_fix_log block.",
    )
    parser.add_argument("--skip-thumbnail", action="store_true", help="Skip thumbnail generation")
    parser.add_argument(
        "--rebuild-scene",
        default=None,
        metavar="SCENE_ID",
        help="Partial rebuild: regenerate a single scene and re-run assembly+bgm. "
        "Exclusive with --steps, --skip-* flags. "
        "B-11: route_map preflight is NOT run in partial rebuild; "
        "Layer 3 in-render WARN still fires.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help="D1+B-25 Phase 1: write structured JSON line events to PATH "
        "(in addition to stdout text). One JSON object per line with fields "
        "ts/step/level/episode_id/scene_id/msg/metadata. Severity levels: "
        "critical/warning/info. Default: disabled (no JSONL output, baseline parity).",
    )
    args = parser.parse_args()

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

    # ─── Structured JSONL logger init (D1+B-25 Phase 1, opt-in) ──────────
    # Initialized BEFORE preflight so startup failures (Claude CLI
    # 401 / system-Python module miss / VOICEVOX down) surface as critical
    # JSONL events rather than just stdout text.
    episode_id = os.path.basename(episode_dir.rstrip(os.sep)) or "unknown"
    log_file_path = Path(args.log_file) if args.log_file else None
    pipeline_log.init_logger(log_file_path, episode_id)

    # ─── Preflight: fail fast on venv / Claude auth / VOICEVOX issues ───
    # a past run lost 57min on expired Claude token + 30min on system-Python run.
    # Cheap upfront checks avoid these dead-ends.
    # --rebuild-scene only touches visuals/assemble/bgm → smaller check set.
    preflight_steps = ["assemble", "bgm"] if args.rebuild_scene else steps
    run_preflight_checks(preflight_steps)

    # Load config for BGM settings
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

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
        _run_partial_rebuild(
            scene_id=args.rebuild_scene,
            config_path=config_path,
            episode_dir=episode_dir,
            config=config,
            src_dir=src_dir,
            bgm_file=bgm_file,
            bgm_config=bgm_config,
        )
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

    # ─── B-17: Pre-script fact check (episode_config.json) ───────────────
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

            print("\n[B-17] Pre-script fact check on episode_config.json")
            _report = run_pre_script_fact_check(
                episode_config=config,
                episode_dir=episode_dir,
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
                    "[B-17] CRITICAL detected -- aborting before script "
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
                    "[B-17] WARNING detected -- aborting before script "
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
            print("[B-17] OK (no blocking issues)")
        except SystemExit:
            raise
        except Exception as _e:
            pipeline_log.emit(
                pipeline_log.LEVEL_WARNING,
                "lint_b17",
                "pre-script fact check skipped (exception)",
                error=f"{type(_e).__name__}: {_e}",
            )
            print(f"[B-17] pre-script fact check skipped due to error: {_e}")

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
    qa_requested = (
        (args.qa or args.qa_quick)
        and not args.skip_qa
        and not args.skip_qa_script_only
    )
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
        pipeline_log.step_end(
            "qa_script", exit_code=qa_exit, duration_ms=int(qa_elapsed * 1000)
        )

        if qa_exit == 1:
            print(f"\n[FAIL] QA FAILED ({qa_elapsed:.0f}s). Critical issues found.")
            print(f"   Report: {qa_report_path}")
            # Ask user whether to continue
            try:
                response = input("   Continue anyway? (y/N): ").strip().lower()
                if response != "y":
                    print("Pipeline aborted by user.")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                print("\nPipeline aborted.")
                sys.exit(1)
        elif qa_exit == 2:  # ERROR
            print(f"\n[ERROR] QA ERROR ({qa_elapsed:.0f}s). Some agents failed.")
            print(f"   Report: {qa_report_path}")
            print("   Continuing pipeline (QA errors are non-blocking)...")
        else:
            # Check report for warnings (WARN status returns exit code 0)
            qa_has_warnings = False
            if os.path.exists(qa_report_path):
                try:
                    with open(qa_report_path, encoding="utf-8") as f:
                        qa_data_check = json.load(f)
                    warn_count = qa_data_check.get("summary", {}).get("warning", 0)
                    if warn_count > 0:
                        qa_has_warnings = True
                except (json.JSONDecodeError, FileNotFoundError):
                    pass

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
        cmd = [
            sys.executable,
            os.path.join(src_dir, "audio_generator.py"),
            scene_json,
            "--output-dir",
            episode_dir,
        ]
        if args.dry_run_audio:
            cmd.append("--dry-run")
        run_pronunciation = (
            args.qa or args.qa_quick or args.check_pronunciation
        ) and not args.skip_pronunciation_check
        if run_pronunciation:
            cmd.append("--check-pronunciation")
        run_step("audio", cmd)

    # ─── Font coverage check (before subtitles) ─────────────────────────
    if "subtitles" in steps:
        font_check_script = os.path.join(src_dir, "check_font_coverage.py")
        if os.path.exists(font_check_script) and os.path.exists(scene_json):
            cmd = [sys.executable, font_check_script, scene_json]
            run_step("font_check", cmd, required=False)

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

        # ─── Day 21 強化 H2: portrait_prompt_lint pipeline 統合 ───────
        # Day 19 強化 C standalone (scripts/portrait_prompt_lint.py) を
        # images step 末尾で auto-gate。use_reference: true scene の
        # source_prompt と reference 写真 (wiki_*.jpg) の特徴矛盾を Gemini
        # Vision で catch。ある回「kimono」prompt vs 全 wiki refs
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
                        if _v.get("type") == "ken_burns" and _v.get(
                            "use_reference", True
                        ):
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
                    print("\n=== Step: portrait_prompt_lint ===")
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
                    # non-zero exit = MISMATCH detected (WARN-only, don't halt)
                    if _lint_result.returncode != 0:
                        print(
                            "  [WARN] portrait_prompt_lint detected MISMATCH(es). "
                            "Review above; reference photo features vs source_prompt may "
                            "diverge."
                        )
                else:
                    if not _wiki_exists:
                        print(
                            "  [SKIP] portrait_prompt_lint: no wiki_*.jpg reference "
                            "photos in episode (古代/近代以前 pattern)"
                        )
                    else:
                        print(
                            "  [SKIP] portrait_prompt_lint: no use_reference=true "
                            "ken_burns scenes"
                        )
            except Exception as _e:
                print(f"  [WARN] portrait_prompt_lint skipped (env/api issue): {_e}")

    # ─── QA Gate 2: Image Quality Check (B-18 narration consistency) ─────
    # Runs AFTER image generation so freshly-produced images are evaluated.
    # The prompt covers narration-image consistency (B-18: 主要人物の有無 /
    # 性別 / 人数 / 活動・小道具 / 細部) plus the original time-place /
    # subject / atmosphere checks.
    qa_img_narr_active = (
        (args.qa or args.qa_quick)
        and not args.skip_qa
        and not args.skip_qa_image_narration
        and "images" in steps
    )
    if qa_img_narr_active:
        qa_img_report = os.path.join(episode_dir, "qa_report_images.json")
        cmd = [
            sys.executable,
            os.path.join(src_dir, "qa_image_checker.py"),
            scene_json,
            "--output",
            qa_img_report,
        ]
        print(f"\n{'=' * 60}")
        print("  QA Gate 2: Image Quality Check (B-18)")
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
            try:
                response = input("   Continue anyway? (y/N): ").strip().lower()
                if response != "y":
                    print("Pipeline aborted by user.")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                sys.exit(1)

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

            # B-50: Thumbnail Vision QA — verify generated
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
            # G1: Clear stale _fallback_scenes.json from previous
            # build round so verify_outputs detects only the current build's
            # Manim fallbacks. Prevents false carry-over warnings.
            _fallback_sidecar = os.path.join(episode_dir, "visuals", "_fallback_scenes.json")
            if os.path.exists(_fallback_sidecar):
                try:
                    os.remove(_fallback_sidecar)
                except OSError:
                    pass

            # B-10: lint Manim factual-claim consistency (episode scope, γ).
            # Templates without LINT_FACTUAL_CLAIMS metadata are skipped.
            try:
                from qa_manim_consistency import lint_manim_factual_claims

                with open(scene_json, encoding="utf-8") as _f:
                    _scene_def_for_lint = json.load(_f)
                _manim_dir = os.path.join(src_dir, "manim_templates")
                print("\n[B-10] Manim factual-claim lint (episode scope):")
                _warns = lint_manim_factual_claims(_scene_def_for_lint, _manim_dir)
                print(f"[B-10] {_warns} warning(s)")
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
                print(f"[B-10] lint skipped: {_e}")

            # B-11 Layer 2: route_map collision preflight.
            # Detects title/route_label/legend bbox overlaps before any expensive
            # rendering, with optional 3-stage auto-fix.
            if not args.skip_route_preflight:
                try:
                    from visual_generator import route_map_preflight

                    _unresolved = route_map_preflight(
                        scene_json,
                        allow=args.allow_route_collision,
                        auto_fix=args.auto_fix_route_collisions,
                    )
                    if _unresolved and not args.allow_route_collision:
                        pipeline_log.emit(
                            pipeline_log.LEVEL_CRITICAL,
                            "lint_b11",
                            "route_map preflight aborted pipeline",
                            unresolved_count=len(_unresolved)
                            if hasattr(_unresolved, "__len__")
                            else None,
                        )
                        pipeline_log.close()
                        print(
                            "\n[B-11] route_map preflight aborted pipeline. "
                            "Fix collisions and re-run, or use "
                            "--allow-route-collision / --auto-fix-route-collisions / "
                            "--skip-route-preflight."
                        )
                        sys.exit(1)
                    pipeline_log.emit(
                        pipeline_log.LEVEL_WARNING if _unresolved else pipeline_log.LEVEL_INFO,
                        "lint_b11",
                        "route_map preflight complete",
                        unresolved_count=len(_unresolved)
                        if hasattr(_unresolved, "__len__")
                        else 0,
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
                    print(f"[B-11] route_map preflight skipped: {_e}")

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
            run_step("visuals", cmd)

    # ─── Step 6: Video assembly ──────────────────────────────────────────
    if "assemble" in steps:
        if not os.path.exists(timing_json):
            print("\n[WARN] timing.json not found. Skipping assembly.")
        else:
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

                run_step("bgm", cmd)

    # ─── Output verification (B-12 / D-3) ────────────────────────────────
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

    print(f"{'=' * 60}")

    # ─── pipeline_end event + logger close (D1+B-25 Phase 1) ─────────────
    _pipeline_end_level = (
        pipeline_log.LEVEL_WARNING if verify_warnings else pipeline_log.LEVEL_INFO
    )
    pipeline_log.emit(
        _pipeline_end_level,
        "pipeline",
        "pipeline end",
        duration_ms=int(total_elapsed * 1000),
        verify_warning_count=len(verify_warnings),
    )
    pipeline_log.close()


if __name__ == "__main__":
    main()
