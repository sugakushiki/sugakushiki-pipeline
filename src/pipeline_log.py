"""D1+B-25 Phase 1+1.5: Structured JSONL logging for pipeline events.

Schema (one JSON line per event):
    {
      "ts": "2026-05-05T12:34:56.789Z",   # ISO 8601 UTC, millisecond precision
      "step": "audio",                     # pipeline step name or sub-event
      "level": "info" | "warning" | "critical",
      "episode_id": "020_abel",            # episode dir basename
      "scene_id": null | "math_02",        # optional scene context
      "msg": "step end",
      "metadata": {                        # step-specific structured data
        "duration_ms": 12345,
        "exit_code": 0,
        ...
      }
    }

Identifier fields (episode_id, scene_id, step) are top-level for grep/jq
ergonomics (Q1-a: C). Step-specific measurements (duration_ms, exit_code,
free-form metadata) live in `metadata`.

Output is opt-in via pipeline.py's --log-file flag (Q1-b: C). Default
behavior preserves existing stdout text for baseline parity.

Channel design (X3, two-channel):
- stdout: human-readable raw text. Pass-through unchanged for baseline parity.
- stderr: structured JSONL events. Children prefix lines with _JSONL_MARKER
  via emit_stderr(); parent (pipeline.py run_step) captures stderr, parses
  marker lines into events (merged into the central logger), and re-emits
  non-marker lines to console as raw text. This lets us add structured
  emit at any child print site by adding one line (emit_stderr next to
  print) without touching stdout or replacing existing prints.

Phase 1 scope (parent path):
- pipeline.py run_step + QA Gate 1/2 + pipeline start/end events.
Phase 1.5 scope (parent inline lint + partial rebuild):
- B-10 (Manim factual claim) / B-11 (route_map collision) /
  B-17 (pre-script fact check)
- _run_partial_rebuild path (audio/visual inline + run_step subprocess steps)
- preflight events (V4: claude CLI / VOICEVOX / module miss)
Phase 2+ candidates (future, run after operational feedback):
- subprocess child emit_stderr wiring (script_generator / audio_generator
  / image_generator / visual_generator / video_assembler / credits_generator
  / bgm_mixer / qa_checker / qa_image_checker / pre_script_fact_check /
  thumbnail_generator / wikimedia_fetcher / subtitle_generator)
- B-14 / B-18 / B-20 (subprocess-based lint, wire via emit_stderr)

Environment variables (used by Phase 2 child emit_stderr; harmless if unset):
- PIPELINE_LOG_FILE: parent-resolved log file path (informational; child
  does not write directly, parent merges via stderr capture).
- PIPELINE_LOG_EPISODE_ID: episode id stamped on child-side events.
"""

from __future__ import annotations

import atexit
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

LEVEL_INFO = "info"
LEVEL_WARNING = "warning"
LEVEL_CRITICAL = "critical"
_VALID_LEVELS = {LEVEL_INFO, LEVEL_WARNING, LEVEL_CRITICAL}

# Marker prefix for JSONL lines on stderr (X3 channel). Chosen to be
# ASCII-only and unlikely to collide with any third-party stderr output.
_JSONL_MARKER = "__PIPELINE_LOG_JSONL__"

# Per-value truncation cap for metadata fields. Prevents accidental log
# bloat when a caller passes a large blob (scene_def dump, image bytes,
# stack trace) into metadata.
_METADATA_VALUE_CHAR_CAP = 1024

_logger: JsonlLogger | None = None
_atexit_registered = False


def _utc_iso_ms() -> str:
    """ISO 8601 UTC timestamp with millisecond precision and 'Z' suffix."""
    return (
        datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _truncate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Cap each metadata value's serialized form at _METADATA_VALUE_CHAR_CAP.

    Defensive guard: a caller passing a huge object (scene_def dump, image
    bytes, stack trace) would otherwise produce multi-MB JSONL lines that
    break tail/jq workflows. Values exceeding the cap are stringified and
    truncated with a "...[truncated]" suffix.
    """
    out: dict[str, Any] = {}
    for key, value in metadata.items():
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            serialized = str(value)
        if len(serialized) > _METADATA_VALUE_CHAR_CAP:
            out[key] = serialized[:_METADATA_VALUE_CHAR_CAP] + "...[truncated]"
        else:
            out[key] = value
    return out


def _ensure_stderr_utf8() -> None:
    """Reconfigure sys.stderr to UTF-8 so emit_stderr lines survive cp932 console.

    Windows console default codec is cp932; Japanese characters in metadata
    would otherwise raise UnicodeEncodeError or be replaced with "?". Run
    once per process (cheap, idempotent on Python 3.11).
    """
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        # Some streams (e.g. captured pytest stderr) don't support reconfigure.
        # Silent fall-through: emit_stderr's outer try/except still protects
        # against UnicodeEncodeError.
        pass


class JsonlLogger:
    """Append-only JSON line logger. Line-buffered for tail-able output."""

    def __init__(self, log_file: Path, episode_id: str):
        self.log_file = log_file
        self.episode_id = episode_id
        # Append mode: re-runs of the same episode coexist with prior runs
        # in the same file. Operators sort by ts when consuming.
        # buffering=1 forces line buffering so `tail -f` works.
        self._fh: TextIO = open(log_file, "a", encoding="utf-8", buffering=1)

    def emit(
        self,
        level: str,
        step: str,
        msg: str,
        scene_id: str | None = None,
        **metadata: Any,
    ) -> None:
        if level not in _VALID_LEVELS:
            level = LEVEL_INFO  # Defensive: unknown level downgraded, never crash.
        event = {
            "ts": _utc_iso_ms(),
            "step": step,
            "level": level,
            "episode_id": self.episode_id,
            "scene_id": scene_id,
            "msg": msg,
            "metadata": _truncate_metadata(metadata),
        }
        self._write_event(event)

    def emit_event(self, event: dict[str, Any]) -> None:
        """Write a pre-built event dict (used when parent merges child events).

        The event must already have ts/step/level/episode_id/scene_id/msg/
        metadata fields. Parent's episode_id is NOT overwritten — child-side
        episode_id is preserved (set from PIPELINE_LOG_EPISODE_ID env var).
        Metadata is truncated defensively even on the merge path so a
        misbehaving child can't blow up the central log.
        """
        if event.get("level") not in _VALID_LEVELS:
            event["level"] = LEVEL_INFO
        if isinstance(event.get("metadata"), dict):
            event["metadata"] = _truncate_metadata(event["metadata"])
        self._write_event(event)

    def _write_event(self, event: dict[str, Any]) -> None:
        try:
            self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            # A logger failure must never crash the pipeline. Surface to
            # stderr so the operator notices, then continue.
            print(
                f"[pipeline_log] emit failed: {type(e).__name__}: {e}",
                file=sys.stderr,
            )

    def step_start(self, step: str, scene_id: str | None = None, **metadata: Any) -> None:
        self.emit(LEVEL_INFO, step, "step start", scene_id=scene_id, **metadata)

    def step_end(
        self,
        step: str,
        exit_code: int,
        duration_ms: int,
        scene_id: str | None = None,
        **metadata: Any,
    ) -> None:
        # exit_code != 0 implies the step failed. Surface it as critical so
        # operators can grep `.level == "critical"` to find pipeline failures.
        level = LEVEL_INFO if exit_code == 0 else LEVEL_CRITICAL
        self.emit(
            level,
            step,
            "step end",
            scene_id=scene_id,
            duration_ms=duration_ms,
            exit_code=exit_code,
            **metadata,
        )

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


def init_logger(log_file: Path | None, episode_id: str) -> None:
    """Initialize the module-level singleton. No-op if log_file is None.

    Side effects:
    - Sets PIPELINE_LOG_FILE and PIPELINE_LOG_EPISODE_ID env vars so
      subprocess children inherit them and can use emit_stderr() consistently.
    - Registers an atexit handler (once) to flush+close the log file on
      unexpected exit (uncaught exception, os._exit elsewhere) so the last
      events aren't lost.
    """
    global _logger, _atexit_registered
    if log_file is None:
        _logger = None
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    _logger = JsonlLogger(log_file, episode_id)
    # Propagate to children via env vars (X3 channel design, Phase 2 wiring).
    os.environ["PIPELINE_LOG_FILE"] = str(log_file.resolve())
    os.environ["PIPELINE_LOG_EPISODE_ID"] = episode_id
    if not _atexit_registered:
        atexit.register(close)
        _atexit_registered = True


def get_logger() -> JsonlLogger | None:
    return _logger


def emit(level: str, step: str, msg: str, scene_id: str | None = None, **metadata: Any) -> None:
    """Module-level convenience: forwards to the active logger or no-ops."""
    if _logger is not None:
        _logger.emit(level, step, msg, scene_id=scene_id, **metadata)


def step_start(step: str, scene_id: str | None = None, **metadata: Any) -> None:
    if _logger is not None:
        _logger.step_start(step, scene_id=scene_id, **metadata)


def step_end(
    step: str,
    exit_code: int,
    duration_ms: int,
    scene_id: str | None = None,
    **metadata: Any,
) -> None:
    if _logger is not None:
        _logger.step_end(step, exit_code, duration_ms, scene_id=scene_id, **metadata)


def close() -> None:
    global _logger
    if _logger is not None:
        _logger.close()
        _logger = None


# ---------------------------------------------------------------------------
# X3 stderr channel (child-side emit + parent-side parser)
# ---------------------------------------------------------------------------

def emit_stderr(
    level: str,
    step: str,
    msg: str,
    scene_id: str | None = None,
    **metadata: Any,
) -> None:
    """Child-side emit: write a JSONL event to stderr with marker prefix.

    The parent's run_step wrapper detects the marker prefix and merges the
    event into the central logger. Non-marker stderr (Python tracebacks,
    Manim/FFmpeg errors) is passed through to the console as raw text.

    Stays usable when called from a context where the parent did not init
    a logger: in that case, env vars are unset and the line still goes to
    stderr — harmless on the console, ignored by parsers expecting a marker.

    Reconfigures sys.stderr to UTF-8 on first call to survive the cp932
    Windows console default (matters when metadata or msg contain Japanese).
    """
    _ensure_stderr_utf8()
    if level not in _VALID_LEVELS:
        level = LEVEL_INFO
    event = {
        "ts": _utc_iso_ms(),
        "step": step,
        "level": level,
        "episode_id": os.environ.get("PIPELINE_LOG_EPISODE_ID", "unknown"),
        "scene_id": scene_id,
        "msg": msg,
        "metadata": _truncate_metadata(metadata),
    }
    try:
        sys.stderr.write(_JSONL_MARKER + json.dumps(event, ensure_ascii=False) + "\n")
        sys.stderr.flush()
    except Exception:
        # A logger failure must never crash the child. Silent drop.
        pass


def parse_marker_line(line: str) -> dict[str, Any] | None:
    """Parser side: return event dict if line is a JSONL marker, else None.

    Used by parent's run_step to demultiplex child stderr into structured
    events (merged into central logger) vs raw text (re-emitted to console).
    """
    if not line.startswith(_JSONL_MARKER):
        return None
    try:
        return json.loads(line[len(_JSONL_MARKER) :].rstrip("\n"))
    except json.JSONDecodeError:
        return None


def merge_child_event(event: dict[str, Any]) -> None:
    """Parent helper: merge a child-emitted event into the active logger."""
    if _logger is not None:
        _logger.emit_event(event)
