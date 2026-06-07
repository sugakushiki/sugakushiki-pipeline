"""F1 smoke test - pre-pipeline static breakage detector.

Complements scripts/quick_baseline_check.py:
- quick_baseline_check.py: post-pipeline output verification (174 files match).
- smoke_test.py: pre-pipeline static health (catches breakage before any run).

Run:
    venv/Scripts/python.exe scripts/smoke_test.py

Checks (all read-only, no FFmpeg / VOICEVOX / Claude CLI calls, target <30s):
1. Imports: every src/*.py module imports cleanly (SyntaxError / ImportError /
   F821 dead branches surface here). Excludes src/blender_templates which need
   bpy/bmesh (Blender-internal modules, not in pip), and src/manim_templates
   which import `from style` resolved only in Manim's cwd-based runtime (those
   are validated via AST parse in step 3 instead).
2. Config validation: every episodes/*/episode_config.json passes
   src/config_validator.py validate_config().
3. Manim discovery: discover_manim_templates() returns >= MIN_TEMPLATES,
   each template parseable (class found via AST). Reports SCENES dict and
   LINT_FACTUAL_CLAIMS metadata coverage as info (not failure).
4. MathTex Japanese lint: scan all manim_templates/*.py for
   `MathTex(...)` calls containing Japanese characters (U+3040..U+9FFF). LaTeX
   cannot render these without explicit usepackage CJK setup, so they cause
   "Unicode character not set up for use with LaTeX" errors at render time.
   CLAUDE.md規約: 日本語は Text(font=FONT), MathTex は ASCII/LaTeX マクロのみ.

Exit 0 on PASS, 1 on FAIL. Failures print actionable detail; successes are concise.
"""

from __future__ import annotations

import importlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
EPISODES = ROOT / "episodes"
MANIM_TEMPLATES = SRC / "manim_templates"

# Modules that cannot import outside their runtime context
SKIP_IMPORT = {
    "src.blender_templates.gaussian_curvature",
    "src.blender_templates.gaussian_curvature_v2",
}

# Lower bound for template count (currently 53; alert if it drops below this)
MIN_TEMPLATES = 50

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# pipeline.py runs src/*.py as subprocess with src/ on path; mirror that
# here so absolute intra-src imports (e.g. `from config_validator import ...`)
# resolve during the smoke test.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _section(title: str) -> None:
    print(f"\n[{title}]")


def check_imports() -> tuple[int, int, list[str]]:
    """Import every src/*.py and scripts/*.py. Returns (ok, fail, errors).

    Excludes:
      - src/manim_templates/*: `from style import ...` resolves only in Manim's
        cwd-based runtime (validated via AST parse in check_manim_templates()).
      - src/blender_templates/*: bpy/bmesh are Blender-internal, not pip.
      - scripts/smoke_test.py itself (avoid recursion).
      - scripts/_*.py: leading-underscore convention for one-off helpers.
    """
    failures: list[str] = []
    ok = 0
    targets: list[tuple[Path, str]] = []
    for py in sorted(SRC.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel = py.relative_to(ROOT).with_suffix("")
        modname = ".".join(rel.parts)
        if modname in SKIP_IMPORT:
            continue
        if modname.startswith("src.manim_templates.") or modname.startswith(
            "src.blender_templates."
        ):
            continue
        targets.append((py, modname))
    for py in sorted((ROOT / "scripts").glob("*.py")):
        if py.name in ("__init__.py", "smoke_test.py"):
            continue
        if py.name.startswith("_"):
            continue
        rel = py.relative_to(ROOT).with_suffix("")
        modname = ".".join(rel.parts)
        targets.append((py, modname))

    for _py, modname in targets:
        try:
            importlib.import_module(modname)
        except Exception as e:
            tb = traceback.format_exc(limit=3)
            failures.append(f"{modname}: {type(e).__name__}: {e}\n{tb}")
            continue
        ok += 1
    return ok, len(failures), failures


def check_episode_configs() -> tuple[int, int, list[str]]:
    """Validate every episodes/*/episode_config.json."""
    from src import config_validator  # type: ignore

    failures: list[str] = []
    ok = 0
    configs = sorted(EPISODES.glob("*/episode_config.json"))
    for cfg_path in configs:
        try:
            with open(cfg_path, encoding="utf-8") as f:
                config = json.load(f)
            errors, _warnings = config_validator.validate_config(config, str(cfg_path))
            if errors:
                failures.append(f"{cfg_path.parent.name}: {len(errors)} error(s)")
                for err in errors[:3]:
                    failures.append(f"    - {err}")
                continue
        except Exception as e:
            failures.append(f"{cfg_path.parent.name}: {type(e).__name__}: {e}")
            continue
        ok += 1
    return ok, len(failures), failures


def check_manim_templates() -> tuple[int, int, list[str], dict[str, int]]:
    """Verify discover_manim_templates() works and templates are well-formed."""
    import ast

    from src import visual_generator  # type: ignore

    failures: list[str] = []
    info: dict[str, int] = {"with_scenes": 0, "with_lint_metadata": 0, "total": 0}

    templates = visual_generator.discover_manim_templates(str(MANIM_TEMPLATES))
    info["total"] = len(templates)

    if len(templates) < MIN_TEMPLATES:
        failures.append(
            f"discover_manim_templates returned {len(templates)} (expected >= {MIN_TEMPLATES})"
        )

    for tname, (fname, class_name) in templates.items():
        fpath = MANIM_TEMPLATES / fname
        if not fpath.exists():
            failures.append(f"{tname}: file missing ({fname})")
            continue
        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"))
        except SyntaxError as e:
            failures.append(f"{tname}: SyntaxError: {e}")
            continue

        has_scenes = False
        has_lint_meta = False
        class_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_found = True
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "SCENES":
                            has_scenes = True
                        elif target.id == "LINT_FACTUAL_CLAIMS":
                            has_lint_meta = True

        if not class_found:
            failures.append(f"{tname}: class {class_name} not found in {fname}")
        if has_scenes:
            info["with_scenes"] += 1
        if has_lint_meta:
            info["with_lint_metadata"] += 1

    return info["total"], len(failures), failures, info


def check_mathtex_japanese() -> tuple[int, int, list[str]]:
    """Lint: MathTex() calls must not contain Japanese characters (U+3040–U+9FFF).

    LaTeX (used by Manim for MathTex) cannot render Japanese without explicit
    \\usepackage{CJK} setup, producing "Unicode character not set up for use
    with LaTeX" errors at render time. CLAUDE.md規約: 日本語は Text(font=FONT)。

    Detects (regex on source, robust to multi-line MathTex calls):
      MathTex(r"\\text{各桁の重み:}\\; 2^3 = 8 ...")  ← FAIL
      Text("各桁の重み:", font=FONT, ...)              ← OK

    Returns (scanned, fail, warnings).
    """
    import re

    # Pattern: MathTex( opening through matching close paren on same line OR
    # across up to ~10 lines (covers most multi-line MathTex calls).
    # Captures content between MathTex( and ).
    JP_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿＀-￯]")
    MATHTEX_RE = re.compile(r"MathTex\s*\(", re.MULTILINE)

    warnings: list[str] = []
    scanned = 0
    for fpath in sorted(MANIM_TEMPLATES.glob("*.py")):
        if fpath.name == "__init__.py" or fpath.name == "style.py":
            continue
        scanned += 1
        try:
            src_text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = src_text.split("\n")
        for i, line in enumerate(lines):
            if not MATHTEX_RE.search(line):
                continue
            # Collect up to 10 lines starting from this line, until matching close paren
            depth = 0
            collected: list[str] = []
            for j in range(i, min(i + 10, len(lines))):
                collected.append(lines[j])
                for ch in lines[j]:
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                if depth == 0:
                    break
            block = "\n".join(collected)
            # Extract content between first MathTex( and matching )
            start = block.find("MathTex")
            if start < 0:
                continue
            paren_open = block.find("(", start)
            if paren_open < 0:
                continue
            content = block[paren_open + 1 :]
            # Find Japanese in the content (rough — false-positive on comments is acceptable)
            jp_match = JP_RE.search(content[:500])  # first 500 chars to skip later args
            if jp_match:
                # Get context (line and ~60 chars around match)
                m_pos = paren_open + 1 + jp_match.start()
                ctx_start = max(0, m_pos - 30)
                ctx_end = min(len(block), m_pos + 40)
                ctx = block[ctx_start:ctx_end].replace("\n", " ")
                warnings.append(
                    f"{fpath.name}:L{i + 1}: MathTex contains Japanese "
                    f"({jp_match.group()!r}) — use Text(font=FONT) instead\n"
                    f"    ...{ctx}..."
                )
    return scanned, len(warnings), warnings


def check_thumbnail_source_image() -> tuple[int, int, list[str]]:
    """Day 15 strengthening: thumbnail.source_image の整合性チェック。

    thumbnail.source_image が指定された episode で、scene_definition.json が
    既に存在する場合、source_image の basename が scene_def の scene_id と
    整合するかチェック。

    過去のケース : config に 'person_07.png' を指定したが scene_def では
    person_01..04 のみで silent fallback (Vision auto-select) が起きた。本 lint で
    pre-pipeline で検出可能。

    scene_definition.json が存在しない (= 未ビルド) 場合は skip (情報不足)。

    Returns (scanned, fail, warnings).
    """
    warnings: list[str] = []
    scanned = 0
    for config_path in sorted(EPISODES.glob("*/episode_config.json")):
        episode_dir = config_path.parent
        scene_def_path = episode_dir / "scene_definition.json"
        if not scene_def_path.exists():
            continue
        scanned += 1
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            with open(scene_def_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        source_image = cfg.get("thumbnail", {}).get("source_image", "")
        if not source_image:
            continue
        scene_id = source_image.replace(".png", "").replace(".jpg", "")
        scene_ids = {
            scene.get("scene_id", "")
            for section in sd.get("sections", [])
            for scene in section.get("scenes", [])
        }
        if scene_id not in scene_ids:
            warnings.append(
                f"{episode_dir.name}: thumbnail.source_image='{source_image}' "
                f"— scene_id '{scene_id}' not in scene_definition.json "
                f"(silent fallback will occur at thumbnail step)"
            )
    return scanned, len(warnings), warnings


def check_manim_y_clearance() -> tuple[int, int, list[str]]:
    """Day 15 strengthening: Manim template の Y 座標 lint。

    CLAUDE.md / manim-development.md 規約「Y 座標範囲 -2.0 〜 +3.3、
    字幕クリアランス y ≈ -2.2」に違反する `move_to([x, y, 0])` リテラルを検出。

    具体的には y < -2.0 (規約下限境界を超えた配置) を WARN として報告。
    過去のケース : three_body_problem.py poincare_section の annot y=-2.3、
    topology_basics.py 3manifold_intuition の conjecture y=-2.4 で字幕領域被り。

    Detects (regex):
      move_to([0, -2.3, 0])  ← FAIL (y < -2.0)
      move_to([0, -2.0, 0])  ← OK (規約境界、許容)

    Returns (scanned, fail, warnings).
    """
    import re

    # y in (-2.99..-2.1) または y <= -3.0 リテラルにマッチ
    Y_VIOLATION_RE = re.compile(
        r"move_to\s*\(\s*\[[^\]]*?,\s*(-2\.[1-9]\d*|-[3-9]\.\d+|-[3-9])\s*,\s*0\s*\]\s*\)"
    )

    warnings: list[str] = []
    scanned = 0
    for fpath in sorted(MANIM_TEMPLATES.glob("*.py")):
        if fpath.name in ("__init__.py", "style.py"):
            continue
        scanned += 1
        try:
            src_text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(src_text.split("\n"), start=1):
            m = Y_VIOLATION_RE.search(line)
            if m:
                warnings.append(
                    f"{fpath.name}:L{i}: y={m.group(1)} < -2.0 "
                    f"(字幕クリアランス -2.2 違反候補)\n"
                    f"    {line.strip()[:100]}"
                )
    return scanned, len(warnings), warnings


def check_pipeline_step_selftest() -> tuple[int, int, list[str]]:
    """Day 16 強化 C: pipeline step の制御フロー regression guard。

    Day 15 で audio_generator.pronunciation_check() の summary 行が
    non-dry-run 経路で `rule_diffs` 未定義参照 (UnboundLocalError) になる
    regression が混入し、ある回 build の audio step で初顕在 → ~73 分浪費。
    smoke の import チェックは実行パスを通らないため検出不能だった。

    ここでは合成 fixture + 外部 I/O monkeypatch で各 step の主要関数を
    実際に呼び、UnboundLocalError / NameError / TypeError 等の制御フロー
    由来エラーを VOICEVOX/Claude/Gemini 無しで <数秒 で検出する
    (fail fast、高コストビルド前)。

    Returns (steps_tested, fail, errors)。
    """
    import importlib
    import tempfile

    errors: list[str] = []
    tested = 0

    # 最小合成 scene_def (各関数が期待する構造)
    sd = {
        "episode_id": "smoke_selftest",
        "sections": [
            {
                "section_id": "intro",
                "scenes": [
                    {
                        "scene_id": "intro_01",
                        "narration": ["これはテストです。|二行目。", "正の数とNaN。"],
                        "narration_speech": ["これはテストです。二行目。", "せいのすうとなん。"],
                        "visual": {"type": "ken_burns", "source_prompt": "a test scene"},
                    }
                ],
            },
            {
                "section_id": "math",
                "scenes": [
                    {
                        "scene_id": "math_01",
                        "narration": ["結果はゼロになる。"],
                        "visual": {
                            "type": "manim",
                            "template": "formula_display",
                            "params": {"mode": "static", "formula": "x=1"},
                        },
                    }
                ],
            },
        ],
    }

    # --- audio_generator: pronunciation_check summary path ---
    tested += 1
    try:
        ag = importlib.import_module("audio_generator")
        orig_qp = ag.query_pronunciation
        orig_cc = ag.check_pronunciation_with_claude
        try:
            ag.query_pronunciation = lambda text, url: ({}, "ダミーカナ")
            ag.check_pronunciation_with_claude = lambda entries, ep: []
            with tempfile.TemporaryDirectory() as td:
                import copy as _copy

                # non-dry-run 経路 = Day 15 で crash したパス
                ag.pronunciation_check(_copy.deepcopy(sd), "http://localhost:0", td, dry_run=False)
                # dry-run 経路
                ag.pronunciation_check(_copy.deepcopy(sd), "http://localhost:0", td, dry_run=True)
        finally:
            ag.query_pronunciation = orig_qp
            ag.check_pronunciation_with_claude = orig_cc
    except Exception as e:  # noqa: BLE001 — smoke は全例外を可視化する
        errors.append(
            f"audio_generator.pronunciation_check: {type(e).__name__}: {e} "
            f""
        )

    # --- audio_generator: 純粋ヘルパ (外部 I/O 無し) ---
    tested += 1
    try:
        import copy as _copy

        ag = importlib.import_module("audio_generator")
        s2 = _copy.deepcopy(sd)
        ag.apply_known_misreading_fixes(s2, dry_run=True)
        ag.auto_generate_narration_speech(_copy.deepcopy(sd))
        ag.lint_narration_markers(_copy.deepcopy(sd))
        ag.validate_narration_speech(_copy.deepcopy(sd))
        with tempfile.TemporaryDirectory() as td:
            ag.write_kana_preview(
                [{"scene_id": "a", "index": 0, "text": "NaN", "kana": "ナエヌ"}], td
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"audio_generator helpers: {type(e).__name__}: {e}")

    # --- qa_checker: 決定論 である調 lint ---
    tested += 1
    try:
        import copy as _copy

        qc = importlib.import_module("qa_checker")
        r = qc.run_dearu_lint(_copy.deepcopy(sd))
        assert isinstance(r, dict) and "status" in r and "issues" in r, "result schema"
        # math_01 の「なる。」を warning 検出できること (検出器健全性)
        assert any(i["severity"] == "warning" for i in r["issues"]), "なる。未検出"
    except Exception as e:  # noqa: BLE001
        errors.append(f"qa_checker.run_dearu_lint: {type(e).__name__}: {e}")

    # --- image_generator: staleness fingerprint + meta ---
    tested += 1
    try:
        import copy as _copy

        ig = importlib.import_module("image_generator")
        with tempfile.TemporaryDirectory() as td:
            tasks = ig.extract_image_tasks(_copy.deepcopy(sd), td)
            fp1 = ig._prompt_fingerprint({"prompt": "p", "no_human": False, "use_reference": True})
            fp2 = ig._prompt_fingerprint({"prompt": "p2", "no_human": False, "use_reference": True})
            assert fp1 != fp2, "fingerprint が変化しない"
            ig._save_image_meta(td, {"intro_01": fp1})
            assert ig._load_image_meta(td).get("intro_01") == fp1, "meta roundtrip 失敗"
            _ = tasks  # extract が例外を出さないことの確認
    except Exception as e:  # noqa: BLE001
        errors.append(f"image_generator staleness: {type(e).__name__}: {e}")

    return tested, len(errors), errors


def main() -> int:
    print("=" * 60)
    print("  Smoke test (pre-pipeline static health)")
    print("=" * 60)

    overall_fail = 0

    _section("1. Imports")
    ok, fail, errors = check_imports()
    if fail:
        print(f"  FAIL: {fail} module(s) failed to import ({ok} OK)")
        for err in errors:
            print(f"    {err}")
        overall_fail += fail
    else:
        print(f"  OK: {ok} module(s) imported cleanly")

    _section("2. Episode configs")
    ok, fail, errors = check_episode_configs()
    if fail:
        print(f"  FAIL: {fail} config(s) invalid ({ok} OK)")
        for err in errors:
            print(f"    {err}")
        overall_fail += fail
    else:
        print(f"  OK: {ok} episode_config.json validated")

    _section("3. Manim templates")
    total, fail, errors, info = check_manim_templates()
    if fail:
        print(f"  FAIL: {fail} template issue(s) ({total} discovered)")
        for err in errors:
            print(f"    {err}")
        overall_fail += fail
    else:
        print(f"  OK: {total} templates discovered")
        print(
            f"    SCENES dict: {info['with_scenes']}/{total}"
            f"    LINT_FACTUAL_CLAIMS: {info['with_lint_metadata']}/{total}"
        )

    _section("4. MathTex Japanese lint")
    scanned, fail, warnings = check_mathtex_japanese()
    if fail:
        print(f"  FAIL: {fail} MathTex Japanese issue(s) ({scanned} files scanned)")
        for w in warnings:
            print(f"    {w}")
        overall_fail += fail
    else:
        print(f"  OK: {scanned} templates scanned, no Japanese in MathTex")

    _section("5. Thumbnail source_image consistency")
    scanned, fail, warnings = check_thumbnail_source_image()
    if fail:
        print(f"  WARN: {fail} mismatch(es) ({scanned} episodes with scene_def scanned)")
        for w in warnings:
            print(f"    {w}")
        # silent fallback 候補 = WARN (overall_fail にカウントせず、可視化のみ)
    else:
        print(f"  OK: {scanned} episodes, thumbnail.source_image consistent with scene_def")

    _section("6. Manim Y-clearance lint")
    scanned, fail, warnings = check_manim_y_clearance()
    if fail:
        print(f"  WARN: {fail} Y-clearance violation(s) ({scanned} templates scanned)")
        for w in warnings:
            print(f"    {w}")
        # 字幕領域被り = WARN (overall_fail にカウントせず、可視化のみ)
    else:
        print(f"  OK: {scanned} templates scanned, no Y<-2.0 violations")

    _section("7. Pipeline step self-test")
    tested, fail, errors = check_pipeline_step_selftest()
    if fail:
        print(f"  FAIL: {fail} step self-test error(s) ({tested} steps exercised)")
        for err in errors:
            print(f"    {err}")
        # 制御フロー regression = FAIL
        overall_fail += fail
    else:
        print(f"  OK: {tested} step path(s) exercised, no control-flow errors")

    print("\n" + "=" * 60)
    if overall_fail:
        print(f"  FAIL  ({overall_fail} issue(s))")
        return 1
    print("  PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
