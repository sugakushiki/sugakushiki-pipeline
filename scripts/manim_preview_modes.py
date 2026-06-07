#!/usr/bin/env python3
"""manim_preview_modes.py — render every mode of a Manim template for review.

smoke_test's Y-clearance lint and MathTex-Japanese lint catch problems
deterministically (AST / regex), but text-vs-text and text-vs-graph layout
collisions only surface in an actual render. This script renders all modes of a
template (or only the templates changed in the current git diff) so they can be
eyeballed right after editing, before a full build.

## Usage

    # Single template, all modes, low quality (-ql) + final frame (-s)
    python scripts/manim_preview_modes.py src/manim_templates/<template>.py

    # Single mode only
    python scripts/manim_preview_modes.py src/manim_templates/<template>.py <mode>

    # All templates changed in the current git diff (default: -ql)
    python scripts/manim_preview_modes.py --diff

    # Custom output directory (default: _manim_preview/)
    python scripts/manim_preview_modes.py --diff --out /tmp/preview

    # Production quality (-qh, 1920x1080, 60fps). Use to pre-catch a mode that
    # renders fine at -ql but times out at -qh.
    python scripts/manim_preview_modes.py --diff --quality qh

## Output

One PNG per mode (Manim's -s flag = last-frame export) at
`_manim_preview/<template_stem>/<mode>.png`, for visual review.

## Quality option

| flag | resolution | fps | rough time | use |
|---|---|---|---|---|
| `-ql` (default) | 854x480 | 30 | 3-10s/mode | post-edit visual sanity check |
| `-qm` | 1280x720 | 30 | 10-30s/mode | intermediate quality |
| `-qh` | 1920x1080 | 60 | 30-300s/mode | production-equivalent; timeout pre-detection |

**Recommended workflow**: edit template → `--diff -ql` for a quick visual sanity
pass → re-confirm only the heavy templates (many cells, complex animation) with
`--diff --quality qh`.

## Relationship to smoke_test

Deliberately NOT integrated into smoke_test: a preview render is 10-20s per mode,
and all templates x modes would blow past smoke_test's 5-second budget. This is
an opt-in tool for the template-editing workflow.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "src" / "manim_templates"
DEFAULT_OUT = ROOT / "_manim_preview"


def discover_modes(template_path: Path) -> list[str]:
    """テンプレファイルから SCENES dict の keys (mode 名) を抽出。"""
    try:
        tree = ast.parse(template_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"  [SKIP] {template_path.name}: parse error {e}")
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "SCENES":
                    if isinstance(node.value, ast.Dict):
                        return [
                            k.value
                            for k in node.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        ]
    return []


def find_scene_class(template_path: Path) -> str | None:
    """ast で Scene サブクラスを探す (1 ファイル 1 クラスが規約)。"""
    tree = ast.parse(template_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in ("Scene", "ThreeDScene"):
                    return node.name
                if isinstance(base, ast.Attribute) and base.attr in ("Scene", "ThreeDScene"):
                    return node.name
    return None


def render_mode(
    template_path: Path,
    scene_class: str,
    mode: str,
    out_dir: Path,
    quality_flag: str = "ql",
    duration: float = 5.0,
) -> tuple[bool, str]:
    """単一 mode を Manim render (-s で last-frame PNG 出力)。

    Returns (success, message).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    tpl_stem = template_path.stem

    # Manim の -s flag は scene の最終 frame を 1 枚 PNG として出力
    # _manim_params.json を template と同じ dir に置く必要あり
    params = {"mode": mode, "duration": duration}
    params_path = template_path.parent / "_manim_params.json"
    try:
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False)

        # G5: per-mode media_dir to avoid Manim cache cross-mode
        # contamination. Previously all 3 modes shared `_media/`, causing Manim
        # to cache-hit between mode-switches and emit the same PNG for all modes
        # (verified: md5 identical for 3 outputs in pascals_triangle/). Per-mode
        # media_dir gives each mode its own scene cache key.
        media_dir = out_dir / tpl_stem / "_media" / mode
        cmd = [
            "manim",
            f"-{quality_flag}",
            "-s",  # save last frame as PNG
            "--media_dir",
            str(media_dir),
            template_path.name,
            scene_class,
        ]
        t0 = time.time()
        result = subprocess.run(
            cmd,
            cwd=str(template_path.parent),
            capture_output=True,
            text=True,
            timeout=180,
        )
        elapsed = time.time() - t0

        # Manim -s で生成された PNG を出力先に rename
        # default 出力: media_dir/images/<scene_class>/<scene_class>.png
        # G5 fix: per-mode media_dir で他 mode の PNG と混在しない
        png_files = sorted(
            media_dir.rglob("*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not png_files:
            return False, f"render OK but no PNG found ({elapsed:.1f}s)"
        # 最新 PNG を mode 別名にコピー
        target = out_dir / tpl_stem / f"{mode}.png"
        shutil.copy(png_files[0], target)
        return True, f"{target.relative_to(ROOT)} ({elapsed:.1f}s)"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (>180s)"
    except subprocess.CalledProcessError as e:
        return False, f"render failed: {e.stderr[-200:]}"
    finally:
        if params_path.exists():
            params_path.unlink()


def get_changed_templates(base_ref: str = "HEAD") -> list[Path]:
    """git diff で変更されたテンプレ一覧を取得。"""
    try:
        # 未 commit (working tree) + staged を両方
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "--", "src/manim_templates/"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        # 未 commit (untracked + modified)
        result2 = subprocess.run(
            ["git", "status", "--porcelain", "--", "src/manim_templates/"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        changed = set()
        for line in result.stdout.splitlines():
            changed.add(ROOT / line.strip())
        for line in result2.stdout.splitlines():
            # "?? src/manim_templates/foo.py" or " M src/manim_templates/bar.py"
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                changed.add(ROOT / parts[1])
        return [p for p in sorted(changed) if p.suffix == ".py" and p.exists()]
    except subprocess.CalledProcessError:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "template",
        nargs="?",
        help="Template path (e.g. src/manim_templates/foo.py). "
        "Omit with --diff to use git-changed templates.",
    )
    ap.add_argument("mode", nargs="?", help="Single mode name (default: all modes)")
    ap.add_argument("--diff", action="store_true", help="Use git diff to find changed templates")
    ap.add_argument(
        "--base", default="HEAD", help="git diff base ref (default: HEAD = working tree changes)"
    )
    ap.add_argument(
        "--quality",
        default="ql",
        choices=["ql", "qm", "qh"],
        help="Manim quality flag (default: ql = 480p15)",
    )
    ap.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Scene duration parameter passed to template (default: 5.0s)",
    )
    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Output dir for preview PNGs (default: {DEFAULT_OUT.relative_to(ROOT)})",
    )
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()

    # 対象 template 決定
    if args.diff:
        templates = get_changed_templates(args.base)
        if not templates:
            print(f"No changed templates found (base={args.base})")
            return 0
        print(f"Changed templates ({len(templates)}):")
        for t in templates:
            print(f"  {t.relative_to(ROOT)}")
        print()
    elif args.template:
        template_path = Path(args.template).resolve()
        if not template_path.exists():
            print(f"ERROR: {template_path} not found")
            return 1
        templates = [template_path]
    else:
        ap.print_help()
        return 1

    # 各 template の各 mode を render
    total_ok = 0
    total_fail = 0
    for tpl in templates:
        modes = discover_modes(tpl)
        scene_class = find_scene_class(tpl)
        if not scene_class:
            print(f"[SKIP] {tpl.name}: no Scene class found")
            continue
        if not modes:
            print(f"[SKIP] {tpl.name}: no SCENES dict found")
            continue
        if args.mode:
            if args.mode not in modes:
                print(f"[ERROR] {tpl.name}: mode '{args.mode}' not in {modes}")
                continue
            target_modes = [args.mode]
        else:
            target_modes = modes
        print(f"\n=== {tpl.name} ({scene_class}) -- {len(target_modes)} mode(s) ===")
        for mode in target_modes:
            print(f"  rendering: {mode} ...", end="", flush=True)
            ok, msg = render_mode(tpl, scene_class, mode, out_dir, args.quality, args.duration)
            if ok:
                print(f"  OK  {msg}")
                total_ok += 1
            else:
                print(f"  FAIL {msg}")
                total_fail += 1

    print(f"\n{'=' * 60}")
    print(f"Preview complete: {total_ok} OK, {total_fail} FAIL")
    print(f"Output: {out_dir.relative_to(ROOT)}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
