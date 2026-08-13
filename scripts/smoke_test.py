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
4. MathTex Japanese lint (learning): scan all manim_templates/*.py for
   `MathTex(...)` calls containing Japanese characters (U+3040..U+9FFF). LaTeX
   cannot render these without explicit usepackage CJK setup, so they cause
   "Unicode character not set up for use with LaTeX" errors at render time.
   CLAUDE.md規約: 日本語は Text(font=FONT), MathTex は ASCII/LaTeX マクロのみ.

Exit 0 on PASS, 1 on FAIL. Failures print actionable detail; successes are concise.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
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
        # SystemExit is caught separately because it does NOT derive from
        # Exception: a script whose sys.exit() runs at import time (no
        # __main__ guard) would otherwise terminate smoke_test itself. That
        # happened -- with exit code 0, so the run printed its header, finished
        # this section, and reported PASS while every later section was skipped.
        # A module that exits on import is an import failure; report it as one.
        except SystemExit as e:
            failures.append(
                f"{modname}: called sys.exit({e.code}) at import time "
                f'(missing `if __name__ == "__main__":` guard)'
            )
            continue
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

    # Pattern: MathTex(opening through matching close paren on same line OR
    # across up to ~10 lines (covers most multi-line MathTex calls).
    # Captures content between MathTex(and ).
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
            # Extract content between first MathTex(and matching )
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
    """strengthening: thumbnail.source_image の整合性チェック。

    thumbnail.source_image が指定された episode で、scene_definition.json が
    既に存在する場合、source_image が次のいずれかを満たすかチェック:
      (a) scene_def の scene_id ({scene_id}.png) と整合する、または
      (b) images/ に実ファイルとして存在する。
    どちらも満たさない場合のみ WARN (= thumbnail step で silent fallback)。

    過去のケース: config に 'person_07.png' を指定したが scene_def では
    person_01..04 のみで silent fallback (Vision auto-select) が起きた。本 lint で
    pre-pipeline で検出可能。

    (b) を許容する理由: thumbnail 専用に image-conditioning で生成した
    肖像 (例: thumb_portrait.png) は scene_id ではないが images/ に実在し、
    thumbnail_generator はこれを正しく採用する。generator の fallback 条件は
    `not os.path.exists(source_image_path)` (= ファイル存在) であって scene_id
    照合ではない。scene_id 限定で照合すると実在する専用肖像を false-positive で
    報告してしまうため、本チェックを generator の実条件 (ファイル存在) に揃える。

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
        # generator は source_image を「images/ にファイルが存在するか」で解決する
        # (thumbnail_generator.load_thumbnail_config の os.path.exists 分岐)。
        # scene_id 照合に加え、専用肖像 (thumb_portrait.png 等) が実在する場合も整合とみなす。
        image_on_disk = (episode_dir / "images" / source_image).exists()
        if scene_id not in scene_ids and not image_on_disk:
            warnings.append(
                f"{episode_dir.name}: thumbnail.source_image='{source_image}' "
                f"— scene_id '{scene_id}' not in scene_definition.json "
                f"and images/{source_image} not on disk "
                f"(silent fallback will occur at thumbnail step)"
            )
    return scanned, len(warnings), warnings


def check_manim_y_clearance() -> tuple[int, int, list[str]]:
    """strengthening: Manim template の Y 座標 lint。

    CLAUDE.md / manim-development.md 規約「Y 座標範囲 -2.0 〜 +3.3、
    字幕クリアランス y ≈ -2.2」に違反する `move_to([x, y, 0])` リテラルを検出。

    具体的には y < -2.0 (規約下限境界を超えた配置) を WARN として報告。
    過去のケース: three_body_problem.py poincare_section の annot y=-2.3、
    topology_basics.py 3manifold_intuition の conjecture y=-2.4 で字幕領域被り。

    Detects (regex):
      move_to([0, -2.3, 0])  ← FAIL (y < -2.0)
      move_to([0, -2.0, 0])  ← OK (規約境界、許容)

    Returns (scanned, fail, warnings).
    """
    import re

    # y < -2.0 リテラルにマッチ (規約下限 -2.0 未満 = 字幕帯に侵入)。
    # misreading: 旧パターンは -2.[1-9] 始まりで -2.01〜-2.09 (例: -2.05) を取りこぼし、
    # gp_ap の formula y=-2.05 が smoke を素通りし、出荷後にユーザーが字幕近接を目視した。
    # -2.0[1-9] を先頭に加えて境界直下も検出する。
    Y_VIOLATION_RE = re.compile(
        r"move_to\s*\(\s*\[[^\]]*?,\s*"
        r"(-2\.0[1-9]\d*|-2\.[1-9]\d*|-[3-9]\.\d+|-[3-9])\s*,\s*0\s*\]\s*\)"
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


def check_static_tail() -> tuple[int, int, list[str]]:
    """strengthening: Manim 「末尾静止」 anti-pattern lint。

    manim-development.md 規約: `used = 固定アニメ秒; self.wait(duration - used)` で
    残り全 slack を末尾の 1 回の静止 wait に流す設計は禁止。ナレーションが長い scene
    (40〜65秒) では 30〜60 秒の完全静止になる (ある回で 65秒中 61秒静止)。
    連続モーション (周期運動) / トレーサー / 段階リビール + 小さな coda に分配する。

    Detects (regex, `used` 変数を末尾 wait に直接流す形のみ — 分配済みの
    `self.wait(coda)` や `duration - reveal_t - N * hold` は誤検出しない):
      self.wait(max(1.0, duration - used))  ← WARN
      self.wait(duration - used)            ← WARN

    Returns (scanned, count, warnings).
    """
    import re

    TAIL_RE = re.compile(r"self\.wait\([^)\n]*duration\s*-\s*used\b")

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
            if TAIL_RE.search(line):
                warnings.append(
                    f"{fpath.name}:L{i}: 末尾静止 anti-pattern "
                    f"(全 slack を末尾 wait に流すと長時間静止)\n"
                    f"    {line.strip()[:100]}"
                )
    return scanned, len(warnings), warnings


# Pre-existing multi-class Manim templates (tech debt). CLAUDE.md's "1 file 1
# Scene class" rule was already violated by these before it was enforced here;
# they only render correctly when their FIRST mode is used, because
# visual_generator.discover_manim_templates() maps each file to its FIRST Scene
# subclass and renders that class for EVERY mode. Grandfathered to WARN so smoke
# stays green; NEW/edited templates must be single-class (they FAIL otherwise).
# To migrate one out of this set: collapse its classes into one Scene whose
# construct() branches on params["mode"], point every SCENES value at it, then
# drop it from this allowlist.
_MULTICLASS_LEGACY = {
    "asymptotic_formula",
    "continued_fraction",
    "equation_history",
    "partition_diagram",
    "permutation_group",
    "polygon_squeeze",
    "polynomial_roots",
    "series_convergence",
    "solvable_vs_unsolvable",
    "sphere_cylinder",
    "taxicab_number",
}


def _non_cp932_in_output_calls(text: str) -> set:
    """Characters the file would emit that cp932 cannot encode.

    Parses the source so a call spanning several lines is treated as one unit.
    Falls back to the old line-based scan if the file will not parse.

    argparse counts as an output call. It writes the parser's description and
    every flag's help to stdout on --help, so an em dash in one help string is
    enough to kill the tool -- and because `description=__doc__` is the usual
    spelling, the module docstring is on that path too. Scanning only
    print()/append() missed three published entry points whose --help died on a
    Windows console: the same "it only breaks on the path that matters" shape as
    the warning-path crashes this check was built for, except here the path is
    "the user did not know how to use the tool".
    """
    bad: set = set()

    def _scan(s: str) -> None:
        for ch in s:
            try:
                ch.encode("cp932")
            except UnicodeEncodeError:
                bad.add(ch)

    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            if "print(" in line or "append(" in line or "add_argument(" in line:
                _scan(line)
        return bad

    argparse_calls = ("ArgumentParser", "add_argument", "add_argument_group", "add_parser")
    module_doc = ast.get_docstring(tree) or ""

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = (
            fn.id
            if isinstance(fn, ast.Name)
            else (fn.attr if isinstance(fn, ast.Attribute) else "")
        )
        if name not in ("print", "append", *argparse_calls):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                _scan(sub.value)
            # description=__doc__ / epilog=__doc__ puts the module docstring on
            # the --help path, where the AST sees only a Name.
            elif isinstance(sub, ast.Name) and sub.id == "__doc__" and name in argparse_calls:
                _scan(module_doc)
    return bad


def check_console_encoding_guard() -> tuple[int, list[str]]:
    """Entry points that can print non-cp932 text must guard stdout encoding.

    On a Windows console the codepage is cp932, and printing a character it cannot
    encode raises UnicodeEncodeError -- the process dies mid-report. The characters
    are not exotic: em dashes in messages, ✅/❌ in measured-reading notes,
    superscripts and hiragana ゔ in the misreading dictionaries, rare kanji quoted
    back from a finding.

    What makes this class nasty is WHERE it lands. Every instance found sat on a
    warning or failure path, so the happy path exercised none of them: lint_video_spec
    crashed only when it detected a deprecated duration, i.e. only on the one
    regression it exists to catch, and had therefore never crashed at all.

    Checks entry points only (a `main()` or a `__main__` block). Library modules
    inherit the guard from whichever process imports them.
    """
    roots = [ROOT / "src", ROOT / "scripts"]
    violations: list[str] = []
    scanned = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            is_entry = "def main(" in text or '__name__ == "__main__"' in text
            if not is_entry:
                continue
            scanned += 1
            if 'reconfigure(encoding="utf-8"' in text:
                continue
            # Walk the CALL, not the line. The line-based scan missed anything
            # split across lines -- a print(on one line and its message on the
            # next was invisible, which is exactly how an em dash got into
            # stt_qa.py during an earlier episode work and crashed the warning path.
            bad = _non_cp932_in_output_calls(text)
            if bad:
                rel = path.relative_to(ROOT).as_posix()
                sample = "".join(sorted(bad)[:6])
                violations.append(f"{rel}: prints {sample!r} with no utf-8 stdout guard")
    return scanned, violations


def check_manim_single_class() -> tuple[int, list[str], list[str]]:
    """Enforce CLAUDE.md '1 file 1 Scene class' (an earlier episode regression).

    visual_generator.discover_manim_templates() maps each template FILE to its
    FIRST Scene subclass and renders that class for EVERY mode (mode is only read
    INSIDE construct() via _manim_params.json). A file defining 2+ Scene
    subclasses therefore silently renders the first class' content for all
    non-first modes -- SCENES pointing modes at distinct classes is ignored.
    an earlier episode nearly shipped with its bounds/milu/cross_section/sphere_volume payoff
    figures lost this way (all rendered as polygon_squeeze / bicylinder).

    Correct pattern: ONE Scene class + `if params["mode"] == ...` dispatch inside
    construct(); SCENES maps every mode to that single class.

    Returns (scanned, new_violations, legacy_violations). New violations FAIL the
    smoke test; legacy (grandfathered in _MULTICLASS_LEGACY) only WARN.
    """
    import ast

    new_v: list[str] = []
    legacy_v: list[str] = []
    scanned = 0
    for fpath in sorted(MANIM_TEMPLATES.glob("*.py")):
        if fpath.name in ("__init__.py", "style.py") or fpath.name.startswith("_"):
            continue
        scanned += 1
        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        scene_classes: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                bn = (
                    base.id
                    if isinstance(base, ast.Name)
                    else (base.attr if isinstance(base, ast.Attribute) else "")
                )
                if "Scene" in bn:
                    scene_classes.append(node.name)
                    break
        if len(scene_classes) >= 2:
            msg = (
                f"{fpath.name}: {len(scene_classes)} Scene classes {scene_classes} "
                f"-- only the first ({scene_classes[0]}) renders for ALL modes. "
                f"Use ONE Scene class + mode dispatch in construct()."
            )
            (legacy_v if fpath.stem in _MULTICLASS_LEGACY else new_v).append(msg)
    return scanned, new_v, legacy_v


def check_reusable_template_hardcode() -> tuple[int, int, list[str]]:
    """reused Manim templates that hardcode episode-specific person/year data.

    A 'generic' template holding ONE episode's data (timeline_recap once held
    Laplace's chronology + title) silently renders the wrong person when reused for
    another episode. This audit flags REUSED templates (>= 2 distinct subjects)
    that are NOT parameterized but carry biographical years / a foreign person's
    name. WARN-only (advisory, not counted toward overall_fail). Full detail +
    INFO-level review candidates: scripts/lint_template_hardcoded_claims.py.

    Returns (info_count, warn_count, warn_messages).
    """
    try:
        from lint_template_hardcoded_claims import run as _run_b52

        findings = _run_b52(str(EPISODES), str(MANIM_TEMPLATES))
    except Exception as e:
        return 0, 0, [f"(audit skipped: {e})"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    infos = [f for f in findings if f["severity"] == "INFO"]
    msgs = [
        f"{f['template']}: {f['reason']} "
        f"(years={f['hardcoded_years']}, names={list(f['hardcoded_names'])})"
        for f in warns
    ]
    return len(infos), len(warns), msgs


def check_tower_exponent_prose() -> tuple[int, int, list[str]]:
    """Ambiguous power-tower prose in narration (an earlier episode Gauss class).

    "2の2のk乗" represents the Fermat number F_k = 2^(2^k)+1 but reads as 2^(2k):
    a power tower written with ONE 乗 and no parentheses. The source data
    (episode_config verified_facts) was correct; the ambiguity entered when the
    formula became Japanese prose and was never shown on screen as a Manim formula.
    Advisory WARN (not counted toward overall_fail). Full detail + the
    fraction/genitive exclusion logic: scripts/lint_tower_exponent.py.

    Returns (0, finding_count, finding_messages).
    """
    try:
        from lint_tower_exponent import run as _run_tower

        findings = _run_tower(str(EPISODES))
    except Exception as e:
        return 0, 0, [f"(tower-exponent audit skipped: {e})"]
    msgs = [
        f'{f["episode"]} {f["scene_id"]} {f["field"]}[{f["index"]}]: "{f["snippet"]}"'
        for f in findings
    ]
    return 0, len(findings), msgs


def check_subtitle_timing_weighting() -> tuple[int, int, list[str]]:
    """強化: 字幕セグメントのタイミング配分が「文字数比」でなく「発話長(mora)比」で
    行われることの regression guard。

    ある回で字幕と音声が全体的にズレた根因は、distribute_time が | セグメントを
    文字数比で分割していたこと。年号「1665年」(5字だが約13拍) のように桁読み・記号を
    含むセグメントへ過小な時間しか割かれず、字幕が音声を先行した。修正後は VOICEVOX
    実測(既定) / local mora 推定(fallback) のいずれも桁数・記号を考慮した重みを返す。
    ここでは VOICEVOX 不要の local 推定で「同字数でも数字セグメントは仮名より重い」
    「distribute_time が重み比で配分する」ことを assert し、char-count への silent
    revert を検出する (offline, 決定論)。

    Returns (checks, fail, errors)。
    """
    errors: list[str] = []
    checks = 0
    try:
        import subtitle_generator as sg
    except Exception as e:  # noqa: BLE001
        return 0, 1, [f"subtitle_generator import 失敗: {type(e).__name__}: {e}"]

    # 1) 同字数(5字)でも数字セグメントは仮名より重い (桁読み考慮の生存)
    checks += 1
    try:
        w_year = sg._estimate_morae("1665年")
        w_kana = sg._estimate_morae("あいうえお")
        if not (w_year > w_kana):
            errors.append(
                f"字幕重み: 数字含み({w_year:.1f}) が同字数の仮名({w_kana:.1f}) を上回らない "
                "(桁読み考慮の消失 = 文字数比への revert 疑い)"
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"_estimate_morae: {type(e).__name__}: {e}")

    # 2) segment_weights は各セグメント長のリストを返し、文字数そのものではない
    checks += 1
    segs = ["1665年、", "大学は閉鎖されます。"]
    try:
        weights = sg.segment_weights(segs, voicevox_url=None)  # local推定(offline)
        if len(weights) != len(segs):
            errors.append(f"segment_weights 長さ不一致: {len(weights)} != {len(segs)}")
        elif weights == [float(len(s)) for s in segs]:
            errors.append("segment_weights が文字数そのもの = char-count 分割への revert")
    except TypeError as e:
        errors.append(f"segment_weights(voicevox_url=...) 署名が壊れた: {e}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"segment_weights: {type(e).__name__}: {e}")

    # 3) distribute_time が重み比で配分: 年号セグメントが文字数比の取り分を上回る
    checks += 1
    try:
        weights = sg.segment_weights(segs, voicevox_url=None)
        dist = sg.distribute_time(0.0, 10.0, segs, weights)
        if len(dist) != len(segs):
            errors.append("distribute_time が想定数のセグメントを返さない")
        else:
            year_dur = dist[0]["end"] - dist[0]["start"]
            char_share = 10.0 * (len(segs[0]) / sum(len(s) for s in segs))
            if not (year_dur > char_share):
                errors.append(
                    f"distribute_time: 年号セグメント {year_dur:.2f}s が文字数比 "
                    f"{char_share:.2f}s を上回らない (重み配分が効いていない)"
                )
    except Exception as e:  # noqa: BLE001
        errors.append(f"distribute_time: {type(e).__name__}: {e}")

    return checks, len(errors), errors


def check_bgm_part_format() -> tuple[int, int, list[str]]:
    """強化: bgm_mixer が *.part へ書く ffmpeg コマンドに明示 -f があることの guard。

    atomic-write は output を一旦 `output_path + ".part"` に書く。`.part` 拡張子
    からは ffmpeg が container を推定できず、新しめの build は 'Unable to choose an
    output format' で落ちる。ある回 build でこの regression が顕在化し、bgm step が
    全エピソードで失敗し得た (silent: assemble までは成功するので気づきにくい)。
    実 ffmpeg を呼ばず、cmd 構築に -f が残っていることを静的に検証する。

    Returns (checks, fail, errors)。
    """
    bgm = SRC / "bgm_mixer.py"
    try:
        text = bgm.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return 0, 1, [f"bgm_mixer.py 読み込み失敗: {e}"]

    errors: list[str] = []
    # .part atomic-write パターンが残っているか (無ければ拡張子推定可能に戻った
    # 可能性 → guard 対象外、レビューは別途)
    if '".part"' not in text:
        return 1, 0, []
    idx = text.find("write_target,")
    if idx == -1:
        return (
            1,
            1,
            ["bgm_mixer: write_target を出力に使う ffmpeg cmd が見つからない (構造変更?)"],
        )
    cmd_start = text.rfind("cmd = [", 0, idx)
    block = text[cmd_start:idx] if cmd_start != -1 else ""
    if '"-f"' not in block:
        errors.append(
            "bgm_mixer: *.part へ書く ffmpeg cmd に明示 -f が無い "
            "(`.part` から container 推定不可 → 'Unable to choose an output format'。"
            "cmd に '-f','mp4' を追加して回帰を防ぐ)"
        )
    return 1, len(errors), errors


def check_pipeline_step_selftest() -> tuple[int, int, list[str]]:
    """強化 C: pipeline step の制御フロー regression guard。

    ある時点 で audio_generator.pronunciation_check() の summary 行が
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

                # non-dry-run 経路 = ある時点 で crash したパス
                ag.pronunciation_check(_copy.deepcopy(sd), "http://localhost:0", td, dry_run=False)
                # dry-run 経路
                ag.pronunciation_check(_copy.deepcopy(sd), "http://localhost:0", td, dry_run=True)
        finally:
            ag.query_pronunciation = orig_qp
            ag.check_pronunciation_with_claude = orig_cc
    except Exception as e:  # noqa: BLE001 — smoke は全例外を可視化する
        errors.append(
            f"audio_generator.pronunciation_check: {type(e).__name__}: {e} "
            f"(type regression の再発)"
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
        # : description.intro も走査されること
        rd = qc.run_dearu_lint({"sections": [], "description": {"intro": "秘密はそこにあった。"}})
        assert any(
            i.get("scene_id") == "description.intro" and i["severity"] == "warning"
            for i in rd["issues"]
        ), "description.intro の である調 未検出"
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


def check_text_overlay_caret() -> tuple[int, int, list[str]]:
    """text_overlay の main/sub に生キャレット (x^3 等) があれば WARN。

    text_overlay は `$...$` で囲めば matplotlib mathtext で正しい上付きが出る
    (generate_text_overlay の TeX 分岐)。生の `^` は字面どおり表示され不格好かつ
    数学的に不完全 (ある回 'x^3' は三次方程式の一般形でない)。`^` を含み `$` で
    囲まれていない main/sub を検出する。Returns (scanned, warn, warnings)。

    **助言は 2 通りに分ける (2026-08-06)。** 以前はどの行にも「`$...$` で囲め」と
    書いていたが、`math_render.uses_tex` は**文字列全体が `$...$` のときだけ** True を
    返す (日本語インライン混在は明示的に対象外)。日本語混じりの行を囲んでも
    **描画は 1 ピクセルも変わらない**のに直したつもりになる。逃げ道の Unicode 上付きも
    使えない — 実測で BIZ UDMincho が持つのは `²` `³` だけで、`⁴ ᵏ ʳ ᵗ ⁽ ⁾` は
    **欠落=豆腐**になる。よって日本語混在の行は「数式だけ別フィールドに分ける」か
    「キャレット表記のまま」が現実解で、それをそのまま書く。
    """
    warnings: list[str] = []
    scanned = 0
    # 日本語 (かな・漢字) を含むか。含むなら全体 $...$ 化は不可能。
    _jp = re.compile(r"[぀-ヿ一-鿿]")
    for scene_def_path in sorted(EPISODES.glob("*/scene_definition.json")):
        try:
            with open(scene_def_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        for section in sd.get("sections", []):
            for scene in section.get("scenes", []):
                v = scene.get("visual", {})
                if v.get("type") != "text_overlay":
                    continue
                content = v.get("content", {})
                for key in ("main", "sub"):
                    txt = content.get(key, "") or ""
                    scanned += 1
                    if "^" in txt and "$" not in txt:
                        where = f"{scene_def_path.parent.name}/{scene.get('scene_id', '?')}.{key}"
                        if _jp.search(txt):
                            advice = (
                                "生キャレット。**日本語混在なので $...$ で囲んでも効きません** "
                                "(uses_tex は文字列全体一致のみ)。Unicode 上付きも "
                                "BIZ UDMincho は ² ³ しか持たず ⁴ ᵏ ʳ ᵗ は豆腐になる。"
                                "数式だけ別フィールドに分けるか、キャレット表記のままにする"
                            )
                        else:
                            advice = (
                                "生キャレット。$...$ で囲めば TeX 表示になる (純数式なので有効)"
                            )
                        warnings.append(f"{where}: '{txt[:40]}' — {advice}")
    return scanned, len(warnings), warnings


def check_quote_overlay_brackets() -> tuple[int, int, list[str]]:
    """text_overlay style=quote の content.main に鉤括弧「」があれば WARN。

    generate_text_overlay の quote スタイルは装飾用の「(左上)と」(本文末尾) を
    自分で描画する (visual_generator の quote ブロック)。なので content.main に
    リテラルの「」を入れると画面が二重「「…」」になり、さらに折り返しで閉じ「」が
    単独 2 行目に孤立する (ある回で顕在化、user が画面で発見)。content.main
    は括弧なしの本文だけにする。sub は出典で書名『』が正当に入るので対象外。
    Returns (scanned, warn, warnings)。
    """
    warnings: list[str] = []
    scanned = 0
    for scene_def_path in sorted(EPISODES.glob("*/scene_definition.json")):
        try:
            with open(scene_def_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        for section in sd.get("sections", []):
            for scene in section.get("scenes", []):
                v = scene.get("visual", {})
                if v.get("type") != "text_overlay" or v.get("style") != "quote":
                    continue
                main = (v.get("content", {}) or {}).get("main", "") or ""
                scanned += 1
                if "「" in main or "」" in main:
                    warnings.append(
                        f"{scene_def_path.parent.name}/{scene.get('scene_id', '?')}"
                        f".main: '{main[:40]}' — quote スタイルが装飾「」を自動描画。"
                        "リテラル「」を除去 (二重括弧+閉じ孤立の原因)"
                    )
    return scanned, len(warnings), warnings


def check_reference_years() -> tuple[int, int, list[str]]:
    """近代の出版社/誌名キーワードを持つ参考文献に4桁年が無ければ WARN。

    Hald '...' (Wiley) の刊行年欠落 を捕捉。所有格アポストロフィ
    (Fermat's 等) をタイトル引用と誤判定して website (年不要) を flag しないよう、
    判定は「近代の出版社/叢書/誌名キーワードを含むのに4桁年が無い」に限定する。
    Wikipedia/MacTutor 等の website や古典 (Plutarch/Brahmagupta) は publisher
    キーワードを持たないので除外される。Returns (scanned, warn, warnings)。
    """
    import re as _re

    year = _re.compile(r"(?:1[0-9]{3}|20[0-9]{2})")
    pub = _re.compile(
        r"(Press|Wiley|Springer|Dover|Princeton|Cambridge|Oxford|Routledge|Norton|"
        r"Penguin|Elsevier|Academic Press|MIT Press|Verlag|岩波|講談社|みすず|出版会|"
        r"University Press|Univ\. Press)"
    )
    warnings: list[str] = []
    scanned = 0
    for config_path in sorted(EPISODES.glob("*/episode_config.json")):
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        for ref in cfg.get("references", []) or []:
            if not isinstance(ref, str):
                continue
            scanned += 1
            # URL 付き (出版社カタログ/デジタル図書館等のウェブ参照) は年不要なので除外
            if pub.search(ref) and not year.search(ref) and "http" not in ref:
                warnings.append(f"{config_path.parent.name}: 年欠落 — {ref[:64]}")
    return scanned, len(warnings), warnings


def check_reference_duplicates() -> tuple[int, int, list[str]]:
    """同一 references 内で引用タイトル (書名/論文名) が正規化後に重複する
    参考文献を WARN。

    ある回で Falbo 'The Golden Ratio - A Contrary Viewpoint' (短縮) と
    'The Golden Ratio: A Contrary Viewpoint' (完全) が二重登録され、ダッシュ/コロンの
    表記差で exact 一致検出を逃れていた。著者 (引用符前のテキスト) + タイトル
    (引用符内) を [a-z0-9] に正規化したペアで照合する。著者を含めるのは、同名タイトルの
    別著作 (例 ある回 Weyl 'Emmy Noether' と Kimberling 'Emmy Noether' は別の追悼/紹介)
    を誤検出しないため。引用タイトルを持たない website 系 (Wikipedia/MacTutor) は対象外。
    episode_config と scene_def.credits の両 references を走査 (どちらが description.txt
    に使われても捕捉)。Returns (scanned, warn, warnings)。
    """
    import re as _re

    # 引用符 (ASCII ' " / 全角 ' ' " ") 開きは行頭/空白の後、閉じは空白/句読点/括弧の前。
    # 語中アポストロフィ (Fibonacci's) は直後が英字なので閉じ判定に該当せず誤切断しない。
    title_re = _re.compile(
        r"(?:^|\s)[‘“'\"]\s*(.+?)[’”'\"]"
        r"(?=[\s,.;:()—]|$)"
    )
    norm = _re.compile(r"[^a-z0-9]+")
    warnings: list[str] = []
    scanned = 0

    def _scan(refs: list, label: str, ep: str) -> None:
        nonlocal scanned
        seen: dict[str, str] = {}
        for ref in refs or []:
            if not isinstance(ref, str):
                continue
            scanned += 1
            m = title_re.search(ref)
            if not m:
                continue
            title_key = norm.sub("", m.group(1).lower())
            if len(title_key) < 8:
                continue
            author = norm.sub("", ref[: m.start()].lower())  # 引用符前 = 著者
            key = author + "|" + title_key
            if key in seen:
                warnings.append(
                    f"{ep} [{label}]: 重複タイトル '{m.group(1)[:48]}' "
                    "(2 件以上の references entry。表記差で重複登録の疑い)"
                )
            else:
                seen[key] = ref

    for config_path in sorted(EPISODES.glob("*/episode_config.json")):
        ep = config_path.parent.name
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            _scan(cfg.get("references", []), "config", ep)
        except Exception:
            pass
        sd_path = config_path.parent / "scene_definition.json"
        if sd_path.exists():
            try:
                with open(sd_path, encoding="utf-8") as f:
                    sd = json.load(f)
                _scan(sd.get("credits", {}).get("references", []), "scene_def", ep)
            except Exception:
                pass
    return scanned, len(warnings), warnings


def check_superlative_claims() -> tuple[int, int, list[str]]:
    """最上級/初出の主張 (人類初/世界初/史上初/人類で初めて) を抽出し advisory。

    'human's first calculation with complex numbers' のような primacy 主張は
    一次資料で厳密検証すべき (ヘロンが約1500年前に √(負) に遭遇していた)。narration を
    走査し、強い最上級主張を列挙して手動 verify を促す (bare 最初/初めて は頻出のため
    除外し overclaim になりやすい 人類/世界/史上 系に限定)。Returns (n, n, findings)。
    """
    import re as _re

    sup = _re.compile(r"(人類初|世界初|史上初|人類で初めて|世界で初めて|史上初めて)")
    findings: list[str] = []
    for scene_def_path in sorted(EPISODES.glob("*/scene_definition.json")):
        try:
            with open(scene_def_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        for section in sd.get("sections", []):
            for scene in section.get("scenes", []):
                for n in scene.get("narration", []) or []:
                    flat = n.replace("|", "")
                    if sup.search(flat):
                        findings.append(
                            f"{scene_def_path.parent.name}/"
                            f"{scene.get('scene_id', '?')}: {flat[:48]}"
                        )
    return len(findings), len(findings), findings


# 禁止表現の直後に来る否定。**その表現を否定している文は違反ではない**。
# forbidden_phrases に入るのは「誤った主張の表層」(例:「ブラウン運動を発見」) なので、
# 本編がそれを打ち消していれば、むしろ書くべきことを書いている。
# 「がありません」のような無関係な否定に釣られないよう、「では」「わけでは」を含む形と
# 動詞否定形に限定する (「疑いようがありません」は該当しない)。
_NEGATION_AFTER_FORBIDDEN = (
    "ではありません",
    "ではない",
    "ではなく",
    "ではなかった",
    "ではありませんでした",
    "わけではありません",
    "わけではない",
    "していません",
    "していない",
    "しませんでした",
    "しなかった",
    "とは限りません",
    "とは限らない",
)


def _forbidden_hit_is_negated(text: str, end: int) -> bool:
    """禁止表現の出現位置 end 以降、**同じ文の中に**否定があるか。

    句点までを見る。次の文まで見に行くと「〜を発見しました。それは誤りではありません」
    のような、主張はしているのに否定語が後続する文で取りこぼす。
    字幕分割マーカー `|` は文の途中なので落として繋ぐ。
    """
    tail = text[end:]
    stop = tail.find("。")
    clause = (tail if stop < 0 else tail[: stop + 1]).replace("|", "")
    return any(m in clause for m in _NEGATION_AFTER_FORBIDDEN)


def check_forbidden_phrases() -> tuple[int, int, list[str]]:
    """episode_config.json の forbidden_phrases が scene_def の user-facing
    テキストに混入していれば WARN。

    **否定文は違反にしない** (2026-08-06)。この検査の唯一の発火が 054_ito の
    「伊藤はブラウン運動を**発見したのではありません**」で、`forbidden_phrases` の
    「ブラウン運動を発見」に部分一致しただけの**偽陽性**だった。誤りを正しく否定して
    いる文が唯一の指摘、という状態は過去の運用知見が禁じた
    「自分の lint を退ける」習慣をこちらから育てることになる。

    error-debt (「割らずに」「割り算せず」等) は config の common_errors_to_avoid に
    散文で書かれるが、それが script 生成や chapter_subtitles / description.intro に
    表層として漏れても、既存 QA (narration 中心) は description ブロックを見ない
    (ある回: chapter「割らずに素数を見抜く」/ intro「見つけることなく」を user 指摘で
    手修正した反省)。config に `forbidden_phrases: [表層文字列]` を opt-in で列挙すると、
    narration / narration_speech / narration_speech_cloud / text_overlay content /
    description.intro / description.title / chapter_subtitles を横断走査して検出する。
    未設定 ep は no-op。advisory。"""
    warnings = 0
    details: list[str] = []
    scanned = 0
    for cfg_path in sorted(EPISODES.glob("*/episode_config.json")):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        forbidden = [p for p in (cfg.get("forbidden_phrases") or []) if p]
        if not forbidden:
            continue
        sd_path = cfg_path.parent / "scene_definition.json"
        if not sd_path.exists():
            continue
        try:
            with open(sd_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        scanned += 1
        texts: list[tuple[str, str]] = []
        for sec in sd.get("sections", []):
            for sc in sec.get("scenes", []):
                sid = sc.get("scene_id", "?")
                for key in ("narration", "narration_speech", "narration_speech_cloud"):
                    for i, t in enumerate(sc.get(key) or []):
                        if isinstance(t, str):
                            texts.append((f"{sid}.{key}[{i}]", t))
                v = sc.get("visual") or {}
                if v.get("type") == "text_overlay":
                    content = v.get("content") or {}
                    for k in ("main", "sub"):
                        if isinstance(content.get(k), str):
                            texts.append((f"{sid}.overlay.{k}", content[k]))
        desc = sd.get("description") or {}
        for k in ("intro", "title"):
            if isinstance(desc.get(k), str):
                texts.append((f"description.{k}", desc[k]))
        for k, val in (desc.get("chapter_subtitles") or {}).items():
            if isinstance(val, str):
                texts.append((f"description.chapter.{k}", val))
        ep = cfg_path.parent.name
        for loc, t in texts:
            for phrase in forbidden:
                pos = t.find(phrase)
                while pos >= 0:
                    if not _forbidden_hit_is_negated(t, pos + len(phrase)):
                        warnings += 1
                        details.append(f"{ep}/{loc}: 禁止表現「{phrase}」")
                        break  # 1 フィールド 1 語につき 1 件で足りる
                    pos = t.find(phrase, pos + len(phrase))
    return scanned, warnings, details


def check_description_markup() -> tuple[int, int, list[str]]:
    """description.txt に編集用のマークアップや内部メモが残っていれば WARN。

    概要欄は YouTube にそのまま貼られる。`**...**` は太字にならず**アスタリスクごと表示**
    される (YouTube の強調は `*` 一つ) ので、書いた本人以外には意味不明の記号になる。

    実害はマークアップそのものより、**それが混ざる経緯**にある ── ある回の参考文献には
    「**結婚の日付とブラックロック居住はこの記事には記載がない**」という、事実確認中に
    自分宛てに書いたメモが公開用の概要欄まで出ていた。強調記法は内部メモの目印になる。

    出荷済み 61 本で発火したのはこの 2 本だけなので、閾値も除外も要らない。advisory。
    """
    warnings = 0
    details: list[str] = []
    scanned = 0
    for path in sorted(EPISODES.glob("*/description.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        scanned += 1
        for hit in find_description_markup(text):
            warnings += 1
            details.append(f"{path.parent.name}: 強調記法 **{hit[:38]}**")
    return scanned, warnings, details


def find_description_markup(text: str) -> list[str]:
    """`**...**` の中身。純関数なので概要欄がディスクに無くても検査できる。"""
    return [m.group(1) for m in re.finditer(r"\*\*(.{1,60}?)\*\*", text, re.S)]


def missing_required_phrases(required: list[str], narration: list[str]) -> list[str]:
    """Which of `required` never appear in the narration. Pure, so it is testable
    without an episode on disk (the point of this check is that it RUNS)."""
    body = "\n".join(t for t in narration if isinstance(t, str))
    return [p for p in required if p and p not in body]


_AVOID_MARKERS = ("使わない", "使用しない", "使わず", "避ける", "書かない", "用いない")


def unenforced_avoid_words(cfg: dict) -> list[str]:
    """pronunciation_high_risk に「使わない」と書いた語のうち forbidden_phrases に無いもの。"""
    forbidden = "".join(cfg.get("forbidden_phrases") or [])
    out = []
    for entry in cfg.get("pronunciation_high_risk") or []:
        if not isinstance(entry, str) or not any(m in entry for m in _AVOID_MARKERS):
            continue
        word = entry.split("→")[0].split("->")[0].strip().strip("*「」 ")
        if word and word not in forbidden:
            out.append(word)
    return out


def check_avoid_words_enforced() -> tuple[int, int, list[str]]:
    """「この語は使わない」を pronunciation_high_risk に書いても台本生成には効かない。

    あの欄は TTS の読み辞書で、script_generator は禁止語として扱わない。ある回は
    『一行 → 使わない(いちぎょう と いっこう が割れる)』と書いてあったのに LLM が
    「論敵の一行の誤り」と書き、Chirp が いっこう と読み、user が耳で見つけた。
    避けたい語は forbidden_phrases に入れて初めて生成に効く (smoke 18 が照合する)。

    未設定 ep は no-op。advisory。
    """
    warnings = 0
    details: list[str] = []
    scanned = 0
    for cfg_path in sorted(EPISODES.glob("*/episode_config.json")):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        if not cfg.get("pronunciation_high_risk"):
            continue
        scanned += 1
        ep = cfg_path.parent.name
        for word in unenforced_avoid_words(cfg):
            warnings += 1
            details.append(
                f"{ep}: 「{word}」を pronunciation_high_risk で避けると書いたが "
                f"forbidden_phrases に無い (台本生成には効かない)"
            )
    return scanned, warnings, details


def check_required_phrases() -> tuple[int, int, list[str]]:
    """episode_config.json の required_phrases が narration に一つも出てこなければ WARN。

    forbidden_phrases の裏返し。企画で「この語は出す」と決めたのに書かれないまま完成する
    型を捕まえる (ある回: 双対性の説明で『ミニマックス』を一行だけ入れると決めたのに、
    どの scene にも書かれず、完成した動画を見た user の指摘で判明した。決めたことは
    計画メモにしか無く、それを照合する仕組みが無かった)。

    照合先は **narration のみ**。読み (narration_speech*) は表記が変わるし、概要欄や
    overlay に出ていても「本編で触れた」ことにはならない。未設定 ep は no-op。advisory。
    """
    warnings = 0
    details: list[str] = []
    scanned = 0
    for cfg_path in sorted(EPISODES.glob("*/episode_config.json")):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        required = [p for p in (cfg.get("required_phrases") or []) if p]
        if not required:
            continue
        sd_path = cfg_path.parent / "scene_definition.json"
        if not sd_path.exists():
            continue
        try:
            with open(sd_path, encoding="utf-8") as f:
                sd = json.load(f)
        except Exception:
            continue
        scanned += 1
        narration = [
            t
            for sec in sd.get("sections", [])
            for sc in sec.get("scenes", [])
            for t in (sc.get("narration") or [])
        ]
        ep = cfg_path.parent.name
        for phrase in missing_required_phrases(required, narration):
            warnings += 1
            details.append(f"{ep}: 必須語「{phrase}」が narration に無い")
    return scanned, warnings, details


def check_route_palette() -> list:
    """ある回: route_map の凡例色が互いに / 背景と識別できるか (決定論).

    凡例の色が「どの線がどの種類か」を伝える唯一の鍵なので、同時に使いうる 2 色が
    同じに見えたら凡例は何も説明しない。education (#7bc8f6) と career (#4cc9f0) は
    RGB 距離 47 で、暗い背景の細い線として区別不能だった。パレットを編集したとき
    ここで落ちる。
    """
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from visual_generator import check_route_palette_separation
    except Exception as e:  # pragma: no cover - import failure is reported, not swallowed
        return [f"palette check をロードできません: {type(e).__name__}: {e}"]
    return [p["summary"] for p in check_route_palette_separation()]


def check_misreading_context() -> list:
    """The 里 rule must stay context-dependent (VOICEVOX path).

    ("里", "り") is an unconditional substring rule, so it also rewrote 里親 to
    り親
    after a numeral. Nothing else pins that: revert it and every episode still
    builds, the audio just goes wrong again where only a listener would notice.

    Like section 23, this drives a **private-repo** regression test, and this
    smoke_test.py **is published**. Treating "the file is not here" as a failure
    made the published smoke test permanently red -- the same defect that was
    found and fixed one section further down, and not looked for here. **"absent"
    is a skip; "present but broken" is a failure.**
    """
    import subprocess

    checker = ROOT / "scripts" / "check_misreading_context_rules.py"
    if not checker.exists():
        print("  SKIP: check_misreading_context_rules.py が無い (回帰スイートは private repo 専用)")
        return []

    r = subprocess.run(
        [sys.executable, str(checker)],
        capture_output=True,
    )
    if r.returncode == 0:
        return []
    out = r.stdout.decode("utf-8", "replace")
    return [ln.strip() for ln in out.splitlines() if "[FAIL]" in ln] or [
        "check_misreading_context_rules.py failed"
    ]


def check_repo_health() -> list:
    """an earlier episode merge: work stranded in a worktree, and wholesale line-ending flips.

    Both were hit for real on 2026-08-05. Three of four parallel hardening
    sessions had committed; the fourth had not, and was reported as merged
    because `git branch --merged` listed its branch -- a branch nobody committed
    to still points at the base commit, so it is always an ancestor of HEAD.
    See src/repo_health.py for why these two live together.
    """
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from repo_health import format_report, run_all
    except Exception as e:  # pragma: no cover - import failure is reported, not swallowed
        return [f"repo health check をロードできません: {type(e).__name__}: {e}"]
    findings = run_all(str(ROOT))
    return [format_report(findings)] if findings else []


def template_mode_names(template: str) -> set | None:
    """A template's declared mode names, read from SCENES without importing it.

    Handles both spellings: a literal `SCENES = {"a": C, ...}` and the
    drift-proof `SCENES = dict.fromkeys(_MODES, C)`. Returns None when the file
    is missing or SCENES cannot be resolved, so callers can skip rather than
    invent a failure.
    """
    path = MANIM_TEMPLATES / f"{template}.py"
    if not path.exists():
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None
    modes_const = None
    scenes_node = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "SCENES":
                scenes_node = node.value
            elif target.id == "_MODES" and isinstance(node.value, ast.Tuple | ast.List):
                modes_const = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
    if scenes_node is None:
        return None
    if isinstance(scenes_node, ast.Dict):
        return {k.value for k in scenes_node.keys if isinstance(k, ast.Constant)}
    # dict.fromkeys(_MODES, Cls) -- the single-source-of-truth spelling.
    if isinstance(scenes_node, ast.Call) and modes_const:
        return modes_const
    return None


def check_manim_mode_exists() -> list:
    """`visual.params.mode` that is not a key of the template's SCENES.

    A mode name that does not exist does NOT fail: construct() falls through to
    its default branch and renders a DIFFERENT picture in silence. Nothing else
    catches it -- the check only fires when mode is MISSING, and
    manim_text_collision_qa used to fall back to the first SCENES key too.

    an earlier episode's generated script asked for 'riemann' / 'lebesgue' / 'default'; the
    scene whose narration says "the range is cut" would have shipped showing the
    domain cut instead. A retroactive scan then found the same defect already
    shipped in two published episodes -- 033_hamilton asks for 'multiply_by_i'
    where the template declares 'multiply_i' (one underscore).
    """
    problems = []
    for scene_json in sorted(EPISODES.glob("*/scene_definition.json")):
        ep = scene_json.parent.name
        try:
            with open(scene_json, encoding="utf-8") as f:
                sd = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for section in sd.get("sections", []):
            for scene in section.get("scenes", []):
                visual = scene.get("visual") or {}
                if visual.get("type") != "manim":
                    continue
                template = visual.get("template")
                mode = (visual.get("params") or {}).get("mode")
                if not template or not mode:
                    continue  # missing mode is's job
                modes = template_mode_names(template)
                if modes is None or mode in modes:
                    continue
                problems.append(
                    f"{ep}/{scene.get('scene_id')}: {template} mode={mode!r} は SCENES に無い "
                    f"(実在: {'/'.join(sorted(modes))}) -- 既定 mode の絵が黙って出る"
                )
    return problems


def check_reuse_template_required_params() -> list:
    """Reuse templates given SOME data keys but missing a required one.

    timeline_recap raises at render time when `milestones` is supplied without
    `title` (its fallback title names Laplace, so omitting it would put another
    person on screen). That guard works, but it only speaks after the visuals
    step
    declared in the template as a raise; read it back out and check the configs
    up front so the same mistake costs a second instead.
    """
    problems = []
    pattern = re.compile(r"'(\w+)' supplied but no '(\w+)'")
    requirements: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(MANIM_TEMPLATES.glob("*.py")):
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        pairs = pattern.findall(src)
        if pairs:
            requirements[path.stem] = pairs
    if not requirements:
        return problems
    for scene_json in sorted(EPISODES.glob("*/scene_definition.json")):
        ep = scene_json.parent.name
        try:
            with open(scene_json, encoding="utf-8") as f:
                sd = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for section in sd.get("sections", []):
            for scene in section.get("scenes", []):
                visual = scene.get("visual") or {}
                template = visual.get("template")
                if template not in requirements:
                    continue
                params = visual.get("params") or {}
                for have, need in requirements[template]:
                    if have in params and need not in params:
                        problems.append(
                            f"{ep}/{scene.get('scene_id')}: {template} は params.{have} が"
                            f"あるのに params.{need} が無い -- レンダ時に raise して"
                            f"placeholder になる"
                        )
    return problems


def _argparse_gaps(text: str) -> list[str]:
    """`args.<attr>` reads that no add_argument/set_defaults ever registers.

    Only the variable actually bound to a parse_args() result is followed, so a
    parameter that merely happens to be named `args` is not mistaken for a
    Namespace.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    ns_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr in ("parse_args", "parse_known_args")
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                ns_names.add(target.id)
            elif isinstance(target, ast.Tuple) and target.elts:
                # args, unknown = parser.parse_known_args()
                if isinstance(target.elts[0], ast.Name):
                    ns_names.add(target.elts[0].id)
    if not ns_names:
        return []

    registered: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr == "add_argument":
            explicit = next((kw.value.value for kw in node.keywords if kw.arg == "dest"), None)
            if isinstance(explicit, str):
                registered.add(explicit)
                continue
            longest = ""
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if not arg.value.startswith("-"):
                        registered.add(arg.value.replace("-", "_"))
                    elif len(arg.value) > len(longest):
                        longest = arg.value
            if longest:
                registered.add(longest.lstrip("-").replace("-", "_"))
        elif node.func.attr == "set_defaults":
            registered.update(kw.arg for kw in node.keywords if kw.arg)

    gaps: dict[str, int] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in ns_names
            and node.attr not in registered
        ):
            gaps.setdefault(node.attr, node.lineno)
    return [
        f"args.{attr} (line {lineno}) は add_argument に無い"
        for attr, lineno in sorted(gaps.items(), key=lambda kv: kv[1])
    ]


def check_argparse_registration() -> list:
    """CLI attributes read from a Namespace that was never given the flag.

    argparse raises AttributeError the first time such a read executes, and the
    read is usually near the top of main(), so the tool dies before it does
    anything -- but nothing static complains, because the source parses fine.

    The class is not hypothetical. The published copy of this pipeline lost three
    add_argument() calls to a sanitize rule, kept the args.<attr> reads that went
    with them, and crashed on every invocation for three weeks while every gate
    in the publish path reported PASS. This check runs from whichever tree it
    sits in, so it guards the published copy as well as this one.
    """
    problems = []
    for root in (ROOT / "src", ROOT / "scripts"):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = path.relative_to(ROOT).as_posix()
            problems.extend(f"{rel}: {gap}" for gap in _argparse_gaps(text))
    return problems


def _current_state_docs() -> list:
    """Docs that describe how the pipeline works NOW.

    Deliberately excludes the historical record -- the development log, session
    prompts, backlog archives and release checklists. Those legitimately name an
    older count, because that is what shipped at the time; rewriting them would be
    falsifying a log, and flagging them would train the reader to ignore this
    check.

    (The exclusion is expressed as an inclusion list of directories rather than by
    naming those files: a published script must not spell an internal file's name,
    because the sanitizer rewrites such a name to a placeholder and the published
    copy then points at something that does not exist.)
    """
    docs = [ROOT / "README.md", ROOT / "CLAUDE.md"]
    for sub in ("01_concept", "02_pipeline", "03_quality", "04_assets"):
        docs.extend(sorted((ROOT / "docs" / sub).glob("*.md")))
    arch = ROOT / "docs" / "architecture.md"
    if arch.exists():
        docs.append(arch)
    docs.extend(sorted((ROOT / ".claude" / "rules").glob("*.md")))
    skill = ROOT / ".claude" / "skills" / "qa-tools" / "SKILL.md"
    if skill.exists():
        docs.append(skill)
    return [d for d in docs if d.is_file()]


_PBV_COUNT_RE = re.compile(r"(?:構造検査|structural verif\w*)[^|\n]{0,24}?(\d+)\s*(?:件|checks?)")
_PBV_COUNT_RE2 = re.compile(r"(\d+)\s*(?:件|checks?)[^|\n]{0,24}?(?:構造検査|structural verif\w*)")

# Counts a doc states that can be recomputed from the code. Each entry is
# (何の数か, doc 側で数字を探す手がかり, 数える正規表現, 実体を返す関数).
#
# Keep this list growing rather than fixing a number in place: every count in
# prose is a copy that stops tracking its source the moment it is written, and
# the post_build_verify one had reached three different values in four places
# before anyone noticed.
_COUNTED_CLAIMS: list = [
    (
        "cloud_reading_lint の系統数",
        "cloud_reading_lint",
        re.compile(r"(\d+)\s*系統"),
        lambda: _module_collection_size("cloud_reading_lint", "_CATEGORY_TAG"),
    ),
]


def _module_collection_size(module: str, name: str) -> int:
    """len() of a module-level dict/list/tuple, read without importing the module.

    Parsed rather than imported so a heavy or side-effecting module cannot make a
    doc check expensive -- and so this still works in a tree where the module's
    own dependencies are not installed.
    """
    path = SCRIPTS / f"{module}.py"
    if not path.is_file():
        path = SRC / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == name for t in node.targets):
            continue
        value = node.value
        if isinstance(value, ast.Dict):
            return len(value.keys)
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return len(value.elts)
    raise LookupError(f"{module}.{name} が見つかりません")


def check_stated_counts() -> list:
    """Counts written into prose must equal what the code actually holds.

    post_build_verify was the case that started this: the count was hand-typed in
    four places and had drifted to three different values at once (8 in the
    README, 10 in the script's docstring and --help, "nine" in run_all's). An earlier episode
    learned the lesson, fixed the one occurrence in the printed output, and left
    the other three -- a number written beside a list goes stale the moment the
    list grows. cloud_reading_lint's "20 系統" was the same shape, against 17.

    Scoped to docs that describe the current system; see _current_state_docs.
    """
    problems = []

    try:
        sys.path.insert(0, str(SCRIPTS))
        import post_build_verify  # type: ignore

        expected = post_build_verify.check_count()
    except Exception as e:
        return [f"post_build_verify を読み込めず件数を照合できません: {e}"]

    docs = []
    for doc in _current_state_docs():
        try:
            docs.append((doc.relative_to(ROOT).as_posix(), doc.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue

    for label, hint, pattern, resolver in _COUNTED_CLAIMS:
        try:
            actual = resolver()
        except Exception as e:
            problems.append(f"{label} の実体を数えられません: {e}")
            continue
        for rel, text in docs:
            for lineno, line in enumerate(text.splitlines(), 1):
                if hint not in line:
                    continue
                for m in pattern.finditer(line):
                    if int(m.group(1)) != actual:
                        problems.append(
                            f"{rel}:{lineno}: {label} を {m.group(1)} と書いていますが実体は "
                            f"{actual} です"
                        )

    for rel, text in docs:
        for lineno, line in enumerate(text.splitlines(), 1):
            if "post_build_verify" not in line and "post-build verify" not in line.lower():
                continue
            for pattern in (_PBV_COUNT_RE, _PBV_COUNT_RE2):
                for m in pattern.finditer(line):
                    if int(m.group(1)) != expected:
                        problems.append(
                            f"{rel}:{lineno}: 検査数を {m.group(1)} と書いていますが実体は "
                            f"{expected} 件です ({m.group(0).strip()[:40]})"
                        )
    return problems


def _readme_tree_entries() -> set:
    """Filenames listed in README's repository-structure fence."""
    readme = ROOT / "README.md"
    if not readme.is_file():
        return set()
    text = readme.read_text(encoding="utf-8")
    # The language tag has to be part of the opener. Matching a bare "```\n"
    # pairs a ```mermaid block's CLOSING fence with the next opening one, and the
    # tree then falls in the gap between two matches instead of inside one.
    fences = re.findall(r"```[A-Za-z]*\n(.*?)```", text, re.S)
    tree = next((f for f in fences if "sugakushiki/" in f and "src/" in f), "")
    return set(re.findall(r"[\w.]+\.(?:py|json)", tree))


def _published_script_names() -> set:
    """Scripts the public repo gets, derived rather than listed.

    From WHITELIST_PATHS when the sync tool is present (this repo), and from the
    directory itself when it is not (the published tree, where everything present
    is by definition published). Parsed with ast rather than imported: reading a
    literal must not run the module.
    """
    sync = SCRIPTS / "sync_to_public.py"
    if not sync.is_file():
        return {p.name for p in SCRIPTS.glob("*.py")}
    try:
        tree = ast.parse(sync.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    for node in ast.walk(tree):
        target = getattr(node, "target", None)
        name = getattr(target, "id", None) if target is not None else None
        if name == "WHITELIST_PATHS" and isinstance(getattr(node, "value", None), ast.List):
            paths = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
            return {
                p.split("/")[-1] for p in paths if p.startswith("scripts/") and p.endswith(".py")
            }
    return set()


def check_readme_structure() -> list:
    """README's repository tree vs what actually ships.

    The tree had fallen eight files behind: four src/ modules and four scripts/,
    all of them the newest work (the review reel, the route_map legend and place
    reviews, the subtitle sentence aligner, the repo-health check). review_reel.py
    was not named anywhere in the README at all -- the same file that had already
    been missed once, by the WHITELIST.

    src/ is checked both ways because "src/**/*.py" publishes all of it. scripts/
    is an explicit allowlist, so the expected set comes from there.
    """
    listed = _readme_tree_entries()
    if not listed:
        return ["README のリポジトリ構造ブロックを読めません"]

    problems = []
    src_dir = ROOT / "src"
    if src_dir.is_dir():
        actual = {p.name for p in src_dir.glob("*.py")} | {p.name for p in src_dir.glob("*.json")}
        for name in sorted(actual - listed):
            problems.append(f"src/{name} が README の構造ツリーにありません")

    for name in sorted(_published_script_names() - listed):
        problems.append(f"scripts/{name} は公開されるのに README の構造ツリーにありません")

    for name in sorted(listed):
        if (src_dir / name).is_file() or (SCRIPTS / name).is_file():
            continue
        if any((ROOT / d).joinpath(name).is_file() for d in (".", "examples")):
            continue
        problems.append(f"README が {name} を挙げていますが src/ にも scripts/ にもありません")
    return problems


_INSTALLED_FONT_NAME = "BIZ-UDMinchoM.ttc"


def check_font_candidate_lists() -> list:
    """Every hand-written font-candidate list must name the installed font.

    Four modules each keep their own list of where BIZ UDMincho might be, and
    only three of them carried the name it actually installs under. The fourth,
    check_font_coverage, listed two spellings that exist nowhere plus the bundled
    _font.ttc -- so once that bundle was removed from the published copy for
    licensing, the published font_check step failed for every user, while the
    private checkout kept passing because the file was still sitting there.

    Deliberately not a "these lists must be identical" check: they legitimately
    differ (the thumbnail generator wants a Bold face; the visual generator
    prefers the episode-local copy first). What they cannot do is omit the one
    name the font is known to install under.
    """
    problems = []
    for path in sorted(SRC.glob("*.py")) + sorted(SCRIPTS.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            items = [
                e.value
                for e in node.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
            # Path literals only. A list of glob patterns ("BIZ*Mincho*.ttc") is
            # a fallback search, not a candidate list, and demanding an exact
            # filename of it makes the check fire on its own fix.
            items = [s for s in items if ("/" in s or "\\" in s)]
            if not any("Mincho" in s for s in items):
                continue
            if not any(_INSTALLED_FONT_NAME in s for s in items):
                problems.append(
                    f"{rel}:{node.lineno}: フォント候補に {_INSTALLED_FONT_NAME} が無い "
                    f"(実在しない名前だけを並べると、そのモジュールはフォントを見つけられません)"
                )
    return problems


def check_reference_markup() -> list:
    """Editing markup inside `references`, which is baked into the description.

    ある回 wrote `**フランス語の原文は読んでいない**` as an internal caveat, but
    references are user-facing: credits_generator copies them into
    description.txt under 【主要参考文献】, so the asterisks shipped. The ある回
    description check caught it only AFTER the description existed; catch it in
    the config, where the author can see why.
    """
    problems = []
    for config_json in sorted(EPISODES.glob("*/episode_config.json")):
        ep = config_json.parent.name
        try:
            with open(config_json, encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for i, ref in enumerate(cfg.get("references") or []):
            if not isinstance(ref, str):
                continue
            # `__` is deliberately NOT checked: numdam ids carry it
            # (BSMF_1905__33__261_1), and flagging every such URL would train the
            # reader to ignore this check.
            for mark, label in (("**", "強調記法 **"), ("`", "コード記法 `")):
                if mark in ref:
                    problems.append(f"{ep}/references[{i}]: {label} が概要欄にそのまま焼かれます")
    return problems


def check_regression_suite_manifest() -> list:
    """回帰テストらしいのに run_regression.py の glob から漏れているファイルを探す。

    2026-08-06: `scripts/test_*.py` 5 本が `.gitignore` の `test_*.py` に巻き込まれて
    追跡外に落ち、うち 2 本が**赤のまま 25 日間**気づかれなかった。名前が規約
    (`check_*.py`) から外れていたことが、誰も気づかなかった一因だった。

    ここで検査するのは**中身ではなく所在**。回帰テストを走らせるのは
 (session-wrapup) の役目で、smoke test は
    「suite から漏れているものが無いか」だけを 1 秒で見る。全部走らせると
 単体 191 秒が pre-pipeline ゲートに乗ってしまう。

    ここは **private repo 専用の検査**。回帰スイート (`scripts/check_*.py`) と
 はどちらも公開 WHITELIST に載せていないので、公開リポには
    そもそも存在しない。**この smoke_test.py は公開される**ため、runner が無いことを
    失敗にすると公開リポの smoke test が常時赤になる (2026-08-06 に一度そう書いて
    しまった)。**「無い」は skip、「有るのに壊れている」は失敗**と区別する。
    """
    runner = ROOT / "scripts" / "run_regression.py"
    if not runner.exists():
        # 公開リポにはスイート自体が無いので検査対象ゼロ。沈黙ではなく明示的な skip。
        print("  SKIP: run_regression.py が無い (回帰スイートは private repo 専用)")
        return []
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from run_regression import find_unwired
    except Exception as e:  # pragma: no cover - 有るのに壊れているのは握り潰さず報告する
        return [f"run_regression をロードできません: {type(e).__name__}: {e}"]
    return find_unwired(str(ROOT / "scripts"))


def main() -> int:
    # Findings quote the offending source text, which routinely contains characters
    # the Windows console codepage cannot encode (em dash, rare kanji, the CJK block
    # boundaries this file's own regexes name). Without this the smoke test dies
    # while reporting rather than reporting.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

    _section("7. Manim 末尾静止 lint")
    scanned, fail, warnings = check_static_tail()
    if fail:
        print(f"  WARN: {fail} 末尾静止 anti-pattern ({scanned} templates scanned)")
        for w in warnings:
            print(f"    {w}")
        # 長時間静止 = WARN (overall_fail にカウントせず、可視化のみ。
        # 連続モーション/トレーサー/段階リビール + coda に分配して解消する)
    else:
        print(f"  OK: {scanned} templates scanned, no static-tail anti-pattern")

    _section("8. Pipeline step self-test")
    tested, fail, errors = check_pipeline_step_selftest()
    if fail:
        print(f"  FAIL: {fail} step self-test error(s) ({tested} steps exercised)")
        for err in errors:
            print(f"    {err}")
        # 制御フロー regression = FAIL
        overall_fail += fail
    else:
        print(f"  OK: {tested} step path(s) exercised, no control-flow errors")

    _section("9. Reusable template hardcode")
    info_count, warn, warnings = check_reusable_template_hardcode()
    if warn:
        print(f"  WARN: {warn} reused template(s) hardcode ep-specific data (not parameterized)")
        for w in warnings:
            print(f"    {w}")
        # 汎用テンプレに ep 固有 hardcode = WARN (overall_fail にカウントせず可視化のみ。
        # timeline_recap のように visual.params 駆動へ移す)
    else:
        print(
            f"  OK: no non-parameterized reuse hazard "
            f"({info_count} INFO review candidate(s); "
            f"run scripts/lint_template_hardcoded_claims.py for detail)"
        )

    _section("10. Subtitle timing weighting (mora vs char-count)")
    checks, fail, errors = check_subtitle_timing_weighting()
    if fail:
        print(f"  FAIL: {fail} subtitle-timing issue(s) ({checks} checks)")
        for err in errors:
            print(f"    {err}")
        # 字幕タイミングが char-count へ revert = FAIL
        overall_fail += fail
    else:
        print(f"  OK: {checks} checks, subtitle timing uses spoken-duration weighting")

    _section("11. BGM .part container-format guard")
    checks, fail, errors = check_bgm_part_format()
    if fail:
        print(f"  FAIL: {fail} bgm format issue(s) ({checks} checks)")
        for err in errors:
            print(f"    {err}")
        # *.part に -f 無し = FAIL
        overall_fail += fail
    else:
        print(f"  OK: bgm_mixer forces -f for *.part write ({checks} check)")

    _section("12. Ambiguous power-tower prose (an earlier episode Gauss)")
    _, warn, warnings = check_tower_exponent_prose()
    if warn:
        print(f"  WARN: {warn} ambiguous power-tower prose finding(s) (advisory)")
        for w in warnings:
            print(f"    {w}")
        print(
            "    -> parenthesize (2の(2のk乗)乗), add an explicit 2nd 乗 in "
            "narration_speech, AND show the formula on screen"
        )
        # advisory only; does not block a build
    else:
        print("  OK: no ambiguous power-tower prose (A no B no C jou = A^(B^C))")

    _section("13. text_overlay 生キャレット")
    scanned, warn, warnings = check_text_overlay_caret()
    if warn:
        print(f"  WARN: {warn} 生キャレット ({scanned} text_overlay フィールド走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> main/sub を $...$ で囲み matplotlib mathtext で上付き表示 (ある回 x^3)")
    else:
        print(f"  OK: text_overlay に生キャレットなし ({scanned} フィールド)")

    _section("14. 参考文献の刊行年")
    scanned, warn, warnings = check_reference_years()
    if warn:
        print(f"  WARN: {warn} 文献に刊行年なし ({scanned} 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> 書籍/論文の参考文献に刊行年を補う (ある回 Hald。advisory)")
    else:
        print(f"  OK: 書籍/論文型の参考文献は刊行年あり ({scanned} 走査)")

    _section("15. 最上級/初出クレーム")
    n_sup, _, sup_findings = check_superlative_claims()
    if n_sup:
        print(f"  INFO: {n_sup} 件の primacy 主張 — 一次資料で厳密 verify 推奨 (advisory)")
        for fdg in sup_findings:
            print(f"    {fdg}")
        print(
            "    -> 人類初/世界初 は『遭遇の初出』(Heron 型) を取りこぼしやすい。"
            "『実際に〜した最初』等の精密化を検討 (ある回複素数)"
        )
    else:
        print("  OK: 人類初/世界初 系の primacy 主張なし")

    _section("16. 参考文献の重複")
    scanned, warn, warnings = check_reference_duplicates()
    if warn:
        print(f"  WARN: {warn} 件の重複タイトル ({scanned} 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> 表記差 (ダッシュ/コロン/巻号) で同一文献が二重登録。1 件に統合 (ある回 Falbo)")
    else:
        print(f"  OK: 引用タイトルの重複なし ({scanned} 走査)")

    _section("17. quote オーバーレイの二重括弧")
    scanned, warn, warnings = check_quote_overlay_brackets()
    if warn:
        print(f"  WARN: {warn} 件の quote main にリテラル「」 ({scanned} quote scene 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> content.main は括弧なし本文だけに。装飾「」は自動描画")
    else:
        print(f"  OK: quote オーバーレイに二重括弧なし ({scanned} quote scene)")

    _section("18. 禁止表現の user-facing 漏れ")
    scanned, warn, warnings = check_forbidden_phrases()
    if warn:
        print(f"  WARN: {warn} 件の禁止表現混入 ({scanned} ep with forbidden_phrases 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> config.forbidden_phrases の error-debt 表現が user-facing に漏れた。言い換え")
    else:
        print(f"  OK: 禁止表現の user-facing 漏れなし ({scanned} ep with forbidden_phrases)")

    _section("18b. 企画で決めた必須語が本編に無い")
    scanned, warn, warnings = check_required_phrases()
    if warn:
        print(f"  WARN: {warn} 件の必須語が未出現 ({scanned} ep with required_phrases 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> config.required_phrases で決めた語が narration に書かれていない")
    else:
        print(f"  OK: 必須語はすべて本編にある ({scanned} ep with required_phrases)")

    _section("18d. 『使わない』と書いた語が生成に効いていない")
    scanned, warn, warnings = check_avoid_words_enforced()
    if warn:
        print(f"  WARN: {warn} 件 ({scanned} ep with pronunciation_high_risk 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> pronunciation_high_risk は読み辞書。避けたい語は forbidden_phrases に入れる")
    else:
        print(f"  OK: 避ける指定はすべて forbidden_phrases にある ({scanned} ep)")

    _section("18c. 概要欄に編集用マークアップ/内部メモ")
    scanned, warn, warnings = check_description_markup()
    if warn:
        print(f"  WARN: {warn} 件の強調記法 ({scanned} 本の description.txt 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> YouTube は ** を太字にせず記号のまま出す。内部メモの混入も疑うこと")
    else:
        print(f"  OK: 概要欄に編集用マークアップなし ({scanned} 本)")

    _section("19. Manim 1ファイル1クラス (ある回 regression)")
    scanned, new_v, legacy_v = check_manim_single_class()
    if new_v:
        print(f"  FAIL: {len(new_v)} 新規 multi-class template(s) ({scanned} 走査)")
        for m in new_v:
            print(f"    {m}")
        # 非grandfather の複数 Sceneクラス = FAIL。visual_generator が先頭クラス
        # 固定 render するので非先頭モードが silent 誤レンダ。
        overall_fail += len(new_v)
    if legacy_v:
        print(
            f"  WARN: {len(legacy_v)} 既存 multi-class template(s) "
            f"(grandfathered tech debt; 再利用時に単一クラスへ移行)"
        )
        for m in legacy_v:
            print(f"    {m}")
    if not new_v and not legacy_v:
        print(f"  OK: {scanned} templates scanned, all single Scene class")

    _section("20. Console encoding guard (cp932 crash on the warning path)")
    scanned, enc_v = check_console_encoding_guard()
    if enc_v:
        print(f"  FAIL: {len(enc_v)} entry point(s) can crash while reporting ({scanned} 走査)")
        for m in enc_v:
            print(f"    {m}")
        print(
            '    対処: main() 冒頭で sys.stdout.reconfigure(encoding="utf-8") '
            "(ASCII 代替が使える文字なら置換でもよい)"
        )
        overall_fail += len(enc_v)
    else:
        print(f"  OK: {scanned} entry points scanned, none can crash on non-cp932 output")

    _section("21. route_map 凡例色の識別可能性")
    pal_v = check_route_palette()
    if pal_v:
        print(f"  FAIL: {len(pal_v)} 組の凡例色が識別できません")
        for m in pal_v:
            print(f"    {m}")
        print(
            "    対処: src/visual_generator.py の _ROUTE_CATEGORY_COLORS を離す "
            "(RGB 距離 >= 60)。凡例は絵柄を読み解く鍵なので、同じに見える 2 色は"
            "凡例を無意味にします"
        )
        overall_fail += len(pal_v)
    else:
        print("  OK: 全カテゴリ対と背景が RGB 距離 >= 60")

    _section("22b. 文脈依存の読み規則 (里)")
    mis_v = check_misreading_context()
    if mis_v:
        print(f"  FAIL: {len(mis_v)} 件")
        for m in mis_v:
            print(f"    {m}")
        print(
            "    対処: src/audio_generator.py の _MISREADING_REGEX_RULES を確認。"
            "無条件の (surface, reading) に戻すと語中の 1 文字漢字を誤爆します"
        )
        overall_fail += len(mis_v)
    else:
        print("  OK: 里 は数詞直後のみ変換 (里親/郷里/里子 は不変)")

    # Advisory, never counted into overall_fail: a session that is still running
    # legitimately has uncommitted work. The point is that the state is VISIBLE
    # before someone declares parallel work merged.
    _section("22. 取り残された作業 / 行末の反転 (ある回 merge)")
    health_v = check_repo_health()
    if health_v:
        for block in health_v:
            print(block)
    else:
        print("  OK: 未コミットの取り残しなし / 行末の反転なし")

    # 所在だけを見る 1 秒の検査。実行は session-wrapup の run_regression.py が担う。
    # ここで fail にするのは「テストが赤」ではなく「テストが suite の外にある」場合で、
    # 後者は放置すると赤に気づけなくなる (2026-08-06 に 25 日間の見逃しとして実際に発生)。
    _section("23. 回帰スイートからの漏れ (2026-08-06)")
    manifest_v = check_regression_suite_manifest()
    if manifest_v:
        print(f"  FAIL: {len(manifest_v)} 件が run_regression.py の探索から漏れています")
        for m in manifest_v:
            print(f"    {m}")
        print("    対処: scripts/check_<name>.py に改名する (glob 探索なので登録は不要)")
        overall_fail += len(manifest_v)
    else:
        print("  OK: 回帰テストは全て scripts/check_*.py 配下 (run_regression.py が拾える)")

    # 存在しない mode は render を止めない -- 既定の分岐に落ちて別の絵が黙って出る。
    # 遡及走査で出荷済み 2 本が既に該当していた (023 / 033) ので FAIL 扱いにする。
    _section("24. 実在しない Manim mode")
    mode_v = check_manim_mode_exists()
    if mode_v:
        print(f"  FAIL: {len(mode_v)} 件の mode が SCENES に存在しません")
        for m in mode_v:
            print(f"    {m}")
        print("    対処: scene_definition の params.mode をテンプレの SCENES のキーに直す")
        overall_fail += len(mode_v)
    else:
        print("  OK: 全 scene の params.mode が SCENES に存在する")

    _section("25. 再利用テンプレの必須 params 欠落")
    reuse_v = check_reuse_template_required_params()
    if reuse_v:
        print(f"  FAIL: {len(reuse_v)} 件がレンダ時に raise します")
        for m in reuse_v:
            print(f"    {m}")
        overall_fail += len(reuse_v)
    else:
        print("  OK: 再利用テンプレの必須 params は揃っている")

    _section("26. references の編集用マークアップ")
    refmk_v = check_reference_markup()
    if refmk_v:
        print(f"  FAIL: {len(refmk_v)} 件の references に強調記法が残っています")
        for m in refmk_v:
            print(f"    {m}")
        overall_fail += len(refmk_v)
    else:
        print("  OK: references に編集用マークアップなし")

    _section("27. argparse の登録漏れ (2026-08-13)")
    argp_v = check_argparse_registration()
    if argp_v:
        print(f"  FAIL: {len(argp_v)} 件が実行時に AttributeError になります")
        for m in argp_v:
            print(f"    {m}")
        overall_fail += len(argp_v)
    else:
        print("  OK: 参照される args 属性は全て add_argument に在る")

    _section("28. doc が書いた件数と実体の一致 (2026-08-13)")
    pbv_v = check_stated_counts()
    if pbv_v:
        print(f"  FAIL: {len(pbv_v)} 件の doc が実体と違う数を名乗っています")
        for m in pbv_v:
            print(f"    {m}")
        overall_fail += len(pbv_v)
    else:
        print("  OK: 検査数を名乗る doc は全て実体と一致")

    _section("29. README のリポジトリ構造 (2026-08-13)")
    tree_v = check_readme_structure()
    if tree_v:
        print(f"  FAIL: {len(tree_v)} 件が README の構造ツリーと実態で食い違います")
        for m in tree_v:
            print(f"    {m}")
        overall_fail += len(tree_v)
    else:
        print("  OK: README の構造ツリーは実態と一致")

    _section("30. フォント候補リストの乖離 (2026-08-13)")
    font_v = check_font_candidate_lists()
    if font_v:
        print(f"  FAIL: {len(font_v)} 件のリストが実在するフォント名を持っていません")
        for m in font_v:
            print(f"    {m}")
        overall_fail += len(font_v)
    else:
        print("  OK: 全てのフォント候補リストが実在名を含む")

    print("\n" + "=" * 60)
    if overall_fail:
        print(f"  FAIL  ({overall_fail} issue(s))")
        return 1
    print("  PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
