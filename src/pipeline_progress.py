"""pipeline_progress.py - an always-fresh, machine-readable snapshot of
the running pipeline so a watcher can tell, reliably, what step is running and
whether the build finished.

Why this exists:
- stdout/Tee-Object logs buffer, so reading a mid-step line ("math_06") and
  concluding "順調" missed both a stuck step and a completed build.
- the background watcher's task-notification was unreliable in this environment.
- guessing from wav/mp4 mtimes is fragile.

Unlike pipeline_log (D-1) -- an append-only JSONL EVENT STREAM behind --log-file
-- this module writes ONE small JSON file (_pipeline_progress.json) that is
OVERWRITTEN at every step boundary and always represents the CURRENT state:
which step is running, which finished (with exit code + duration), and the
terminal status (complete / failed / interrupted) plus the output_final summary.

Design guarantees:
- atomic writes (temp + os.replace) + flush + fsync, so a poller never reads a
  half-written file and sees each update immediately.
- best-effort: a write failure never breaks the build.
- no-op until init() is called, so importing it is harmless.
- an atexit hook marks the run "interrupted" if it dies without finish() (Ctrl+C,
  crash, sys.exit from a preflight), so the file never lies "running" forever.

Poll example (PowerShell):
    Get-Content examples/moriarty/_pipeline_progress.json | ConvertFrom-Json |
        Select-Object status, current_step, updated_at
"""

import atexit
import json
import os
import time

PROGRESS_FILE = "_pipeline_progress.json"

_state: dict | None = None
_path: str | None = None
_finalized = False


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def init(episode_dir: str, episode_id: str, steps_planned: list) -> None:
    """Begin tracking. Creates _pipeline_progress.json in episode_dir."""
    global _state, _path, _finalized
    _path = os.path.join(episode_dir, PROGRESS_FILE)
    _finalized = False
    now = _now()
    _state = {
        "episode_id": episode_id,
        "pid": os.getpid(),
        "status": "running",
        "started_at": _iso(now),
        "started_ts": round(now, 1),
        "updated_at": _iso(now),
        "updated_ts": round(now, 1),
        "current_step": None,
        "steps_planned": list(steps_planned),
        "steps": [],
        "output_final": None,
    }
    _write()
    atexit.register(_atexit_finalize)


def start_step(name: str) -> None:
    if _state is None:
        return
    now = _now()
    _state["current_step"] = name
    _state["steps"].append(
        {
            "name": name,
            "status": "running",
            "started_at": _iso(now),
            "started_ts": round(now, 1),
            "ended_at": None,
            "exit_code": None,
            "duration_sec": None,
        }
    )
    _touch()


def end_step(name: str, exit_code: int, duration_sec: float) -> None:
    if _state is None:
        return
    now = _now()
    for entry in reversed(_state["steps"]):
        if entry["name"] == name and entry["status"] == "running":
            entry["status"] = "ok" if exit_code == 0 else "failed"
            entry["ended_at"] = _iso(now)
            entry["exit_code"] = exit_code
            entry["duration_sec"] = round(duration_sec, 1)
            break
    if _state["current_step"] == name:
        _state["current_step"] = None
    _touch()


def finish(status: str, output_final: dict | None = None) -> None:
    """Mark a terminal status: 'complete' / 'failed' / 'aborted'."""
    global _finalized
    if _state is None:
        return
    _state["status"] = status
    _state["current_step"] = None
    if output_final is not None:
        _state["output_final"] = output_final
    _finalized = True
    _touch()


def _atexit_finalize() -> None:
    # If the process is ending without an explicit finish(), the run died
    # mid-flight. Record that so the file never claims "running" forever.
    if _state is not None and not _finalized:
        _state["status"] = "interrupted"
        _touch()


def _touch() -> None:
    if _state is None:
        return
    now = _now()
    _state["updated_at"] = _iso(now)
    _state["updated_ts"] = round(now, 1)
    _write()


def _write() -> None:
    if _path is None or _state is None:
        return
    tmp = _path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _path)
    except OSError:
        # progress file is best-effort; never break the build over it
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
