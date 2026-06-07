"""
blender_renderer.py — Blender headless rendering for 数学史記

Renders Blender Python scripts (templates) to MP4 video.
Uses Blender's --background mode with Eevee CPU rendering.

Usage by visual_generator.py:
    from blender_renderer import render_blender_template
    render_blender_template(template_path, params, output_path, duration, ...)
"""

import json
import os
import shutil
import subprocess

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

# Blender executable search paths
BLENDER_SEARCH_PATHS = [
    # Windows typical install locations (newest first)
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    # PATH
    "blender",
]


def find_blender() -> str | None:
    """Find Blender executable."""
    for path in BLENDER_SEARCH_PATHS:
        if path == "blender":
            # Check PATH
            if shutil.which("blender"):
                return "blender"
        elif os.path.isfile(path):
            return path
    return None


def render_blender_template(
    template_path: str,
    params: dict,
    output_path: str,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    blender_exe: str | None = None,
    timeout: int = 300,
) -> bool:
    """Render a Blender template script to MP4.

    Args:
        template_path: Path to Blender Python template script (.py)
        params: Parameters to pass to the template (written as JSON)
        output_path: Output MP4 path
        duration: Target duration in seconds
        width, height: Resolution
        fps: Frames per second
        blender_exe: Blender executable path (auto-detected if None)
        timeout: Render timeout in seconds

    Returns:
        True if rendering succeeded, False otherwise
    """
    if blender_exe is None:
        blender_exe = find_blender()
    if blender_exe is None:
        print("    [ERR] Blender not found. Install Blender and add to PATH.")
        return False

    if not os.path.isfile(template_path):
        print(f"    [ERR] Blender template not found: {template_path}")
        return False

    # Write params JSON to temp file alongside template
    params_with_meta = {
        **params,
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "output_path": os.path.abspath(output_path),
    }

    template_dir = os.path.dirname(os.path.abspath(template_path))
    params_path = os.path.join(template_dir, "_blender_params.json")

    try:
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params_with_meta, f, ensure_ascii=False, indent=2)

        # Build Blender command
        cmd = [
            blender_exe,
            "--background",  # No GUI
            "--python",
            os.path.abspath(template_path),
        ]

        print(f"    [BLENDER] Rendering: {os.path.basename(template_path)}")
        result = subprocess.run(
            cmd,
            cwd=template_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            stderr_lines = result.stderr.strip().split("\n")
            for line in stderr_lines[-5:]:
                print(f"    [BLENDER STDERR] {line}")
            print(f"    [ERR] Blender render failed (exit code {result.returncode})")
            return False

        if not os.path.isfile(output_path):
            # Check if template wrote to a different location
            print(f"    [ERR] Blender output not found: {output_path}")
            return False

        size_kb = os.path.getsize(output_path) / 1024
        print(f"    [BLENDER] Output: {size_kb:.0f}KB")
        return True

    except subprocess.TimeoutExpired:
        print(f"    [ERR] Blender render timed out ({timeout}s)")
        return False
    except Exception as e:
        print(f"    [ERR] Blender render error: {e}")
        return False
    finally:
        # Cleanup params file
        if os.path.exists(params_path):
            os.remove(params_path)


def discover_blender_templates(templates_dir: str) -> dict:
    """Discover available Blender templates.

    Scans templates_dir for .py files and returns a mapping of
    template_name -> template_file.

    Unlike Manim (which needs class discovery), Blender templates
    are standalone scripts, so we just map filename stem to path.

    Returns:
        dict[str, str]: {"gaussian_curvature": "gaussian_curvature.py", ...}
    """
    if not os.path.isdir(templates_dir):
        return {}

    templates = {}
    for fname in os.listdir(templates_dir):
        if fname.startswith("_") or not fname.endswith(".py"):
            continue
        name = fname[:-3]  # strip .py
        templates[name] = fname

    return templates
