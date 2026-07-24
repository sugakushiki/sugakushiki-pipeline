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
    (40〜65秒) では 30〜60 秒の完全静止になる。
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


def check_manim_single_class() -> tuple[int, list[str], list[str]]:
    """Enforce CLAUDE.md '1 file 1 Scene class'.

    visual_generator.discover_manim_templates() maps each template FILE to its
    FIRST Scene subclass and renders that class for EVERY mode (mode is only read
    INSIDE construct() via _manim_params.json). A file defining 2+ Scene
    subclasses therefore silently renders the first class' content for all
    non-first modes -- SCENES pointing modes at distinct classes is ignored.
    ある回 nearly shipped with its bounds/milu/cross_section/sphere_volume payoff
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
        return 0, 0, [f""]
    warns = [f for f in findings if f["severity"] == "WARN"]
    infos = [f for f in findings if f["severity"] == "INFO"]
    msgs = [
        f"{f['template']}: {f['reason']} "
        f"(years={f['hardcoded_years']}, names={list(f['hardcoded_names'])})"
        for f in warns
    ]
    return len(infos), len(warns), msgs


def check_tower_exponent_prose() -> tuple[int, int, list[str]]:
    """Ambiguous power-tower prose in narration.

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

    ある回 で字幕と音声が全体的にズレた根因は、distribute_time が | セグメントを
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
            ["bgm_mixer: write_target を出力に使う ffmpeg cmd が見つからない"],
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
    数学的に不完全。`^` を含み `$` で
    囲まれていない main/sub を検出する。Returns (scanned, warn, warnings)。
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
                if v.get("type") != "text_overlay":
                    continue
                content = v.get("content", {})
                for key in ("main", "sub"):
                    txt = content.get(key, "") or ""
                    scanned += 1
                    if "^" in txt and "$" not in txt:
                        warnings.append(
                            f"{scene_def_path.parent.name}/{scene.get('scene_id', '?')}"
                            f".{key}: '{txt[:40]}' — 生キャレット。$...$ で囲み TeX 表示に"
                        )
    return scanned, len(warnings), warnings


def check_quote_overlay_brackets() -> tuple[int, int, list[str]]:
    """text_overlay style=quote の content.main に鉤括弧「」があれば WARN。

    generate_text_overlay の quote スタイルは装飾用の「(左上)と」(本文末尾) を
    自分で描画する (visual_generator の quote ブロック)。なので content.main に
    リテラルの「」を入れると画面が二重「「…」」になり、さらに折り返しで閉じ「」が
    単独 2 行目に孤立する。content.main
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

    ある回 で Falbo 'The Golden Ratio - A Contrary Viewpoint' (短縮) と
    'The Golden Ratio: A Contrary Viewpoint' (完全) が二重登録され、ダッシュ/コロンの
    表記差で exact 一致検出を逃れていた。著者 (引用符前のテキスト) + タイトル
    (引用符内) を [a-z0-9] に正規化したペアで照合する。著者を含めるのは、同名タイトルの
    別著作
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


def check_forbidden_phrases() -> tuple[int, int, list[str]]:
    """episode_config.json の forbidden_phrases が scene_def の user-facing
    テキストに混入していれば WARN。

    error-debt (「割らずに」「割り算せず」等) は config の common_errors_to_avoid に
    散文で書かれるが、それが script 生成や chapter_subtitles / description.intro に
    表層として漏れても、既存 QA (narration 中心) は description ブロックを見ない
。config に `forbidden_phrases: [表層文字列]` を opt-in で列挙すると、
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
                if phrase in t:
                    warnings += 1
                    details.append(f"{ep}/{loc}: 禁止表現「{phrase}」")
    return scanned, warnings, details


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

    _section("12. Ambiguous power-tower prose")
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
        print("    -> main/sub を $...$ で囲み matplotlib mathtext で上付き表示")
    else:
        print(f"  OK: text_overlay に生キャレットなし ({scanned} フィールド)")

    _section("14. 参考文献の刊行年")
    scanned, warn, warnings = check_reference_years()
    if warn:
        print(f"  WARN: {warn} 文献に刊行年なし ({scanned} 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> 書籍/論文の参考文献に刊行年を補う")
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
            "『実際に〜した最初』等の精密化を検討"
        )
    else:
        print("  OK: 人類初/世界初 系の primacy 主張なし")

    _section("16. 参考文献の重複")
    scanned, warn, warnings = check_reference_duplicates()
    if warn:
        print(f"  WARN: {warn} 件の重複タイトル ({scanned} 走査)")
        for w in warnings:
            print(f"    {w}")
        print("    -> 表記差 (ダッシュ/コロン/巻号) で同一文献が二重登録。1 件に統合")
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

    _section("19. Manim 1ファイル1クラス")
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

    print("\n" + "=" * 60)
    if overall_fail:
        print(f"  FAIL  ({overall_fail} issue(s))")
        return 1
    print("  PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
