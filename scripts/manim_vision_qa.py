#!/usr/bin/env python3
"""manim_vision_qa.py - Vision QA for built Manim / route_map / timeline_recap visuals.

目的:
    ビルド済みの Manim 系 visual mp4 (type=="manim" / "route_map" / template in
    {timeline_recap, ...}) から**代表フレームを1枚 ffmpeg で抽出**し、Claude Sonnet
    Vision (Claude Code CLI 経由、Max 契約内でコスト0) に見せて「主張どおりに図が
    見えるか / 無意味な動き / 判別不能な形 / ラベル衝突」を判定して WARN する。

    既存の決定論 lint (Y座標範囲 / MathTex 日本語混入 / 末尾静止) では捕まらない
    **意味・美観**の欠陥を Vision で補う。ある回で user に指摘された症状:
      - 「独楽が独楽に見えない」   → (c) 図形が意図した対象に見えるか
      - 「謎に動く点」             → (b) 無意味な動き (静止画1枚では判定困難なら判定不可)
      - 「タイムラインの文字衝突」 → (d) ラベル同士 / ラベルと図形の重なり

    advisory (既定 exit 0、--strict で warn 検出時 exit 1)。Claude CLI 不在/失敗は
    graceful に SKIP (pipeline を止めない)。GOOGLE_API_KEY 等は不要 (Claude CLI 経路)。

Usage:
    python scripts/manim_vision_qa.py examples/moriarty/scene_definition.json
    python scripts/manim_vision_qa.py examples/moriarty/scene_definition.json --strict
    python scripts/manim_vision_qa.py examples/moriarty/scene_definition.json --visuals-dir <dir>
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

# Vision で検査対象にする visual タイプ / テンプレート。
# - type == "manim"      : 全ての Manim scene (独楽・数式アニメ等)
# - type == "route_map"  : matplotlib 版 route_map (都市ラベルの衝突・見切れ)
# - template in _TEMPLATE_ALLOW : type が manim 以外でもテンプレ名で拾う保険
#   (timeline_recap は type=="manim"+template で来るが、将来 type 直指定でも拾える)
_TEMPLATE_ALLOW = {"timeline_recap", "route_map"}


def _call_claude_cli(prompt: str, debug: bool = False) -> str | None:
    """Call Claude Code CLI with a text prompt (which may reference media file paths).

    qa_image_checker.py と同一の file-based I/O パターン (os.system + temp file)。
    Windows で subprocess.run/Popen は日本語クラッシュを起こすため使わない。Claude Code は Read tool でファイルを直接読む。
    Max subscription 配下で追加コストなし。

    Returns response text, or None on failure.
    """
    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, "_tmp_manim_vqa_prompt.txt")
    output_path = os.path.join(tmp_dir, "_tmp_manim_vqa_output.txt")
    error_path = os.path.join(tmp_dir, "_tmp_manim_vqa_error.txt")

    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(prompt)

        for p in [output_path, error_path]:
            if os.path.exists(p):
                os.remove(p)

        cmd = (
            f'type "{prompt_path}" | claude -p --output-format text '
            f'--allowedTools Read,Bash > "{output_path}" 2> "{error_path}"'
        )

        if debug:
            print(f"    [DEBUG] Prompt: {len(prompt)} chars")
            print(f"    [DEBUG] Command: {cmd[:120]}...")

        exit_code = os.system(cmd)

        if exit_code != 0:
            if debug and os.path.exists(error_path):
                with open(error_path, encoding="utf-8", errors="replace") as f:
                    print(f"    [DEBUG] stderr: {f.read().strip()[:200]}")
            return None

        if not os.path.exists(output_path):
            return None

        with open(output_path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()

    except Exception as e:
        if debug:
            print(f"    [DEBUG] _call_claude_cli error: {e}")
        return None
    finally:
        for p in [prompt_path, output_path, error_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from response text (handles ```json blocks)."""
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 末尾に散文が付く場合に備え、最初の JSON オブジェクトを貪欲でなく拾う
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _extract_frame(video_path: str, out_png: str, sseof: float = -3.0) -> bool:
    """終盤フレームを1枚 ffmpeg で PNG 抽出する。

    -sseof <負値> で末尾からのオフセットを指定 (段階 reveal は終盤に完成形が
    揃うので終盤が代表的)。動画が -sseof より短い場合は先頭からのフォールバック。
    subprocess.run は capture_output + text=False (バイト) で日本語パスの
    クラッシュを避ける。Windows でも安全。
    Returns True on success (PNG が生成された)。
    """
    for args in (
        ["-sseof", str(sseof), "-i", video_path, "-frames:v", "1", "-q:v", "2", "-y", out_png],
        # フォールバック: 短尺動画は末尾オフセットが効かないので先頭寄りを取る
        ["-i", video_path, "-frames:v", "1", "-q:v", "2", "-y", out_png],
    ):
        try:
            if os.path.exists(out_png):
                os.remove(out_png)
            proc = subprocess.run(  # noqa: S603 - ffmpeg 固定引数、shell=False
                ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if proc.returncode == 0 and os.path.exists(out_png) and os.path.getsize(out_png) > 0:
                return True
        except (OSError, ValueError):
            continue
    return False


def _summarize_narration(scene: dict, limit: int = 240) -> str:
    """narration を1本の文脈文字列に畳む (Vision に「何を描こうとしているか」を渡す)。"""
    narration = scene.get("narration", [])
    if isinstance(narration, list):
        flat = " ".join(str(n).replace("|", "") for n in narration)
    else:
        flat = str(narration)
    flat = flat.strip()
    if len(flat) > limit:
        flat = flat[:limit] + "…"
    return flat


def _visual_context(visual: dict) -> str:
    """visual の意図 (template/mode/title 等) を短い文脈文字列にする。"""
    parts = []
    vtype = visual.get("type", "")
    template = visual.get("template", "")
    if template:
        parts.append(f"template={template}")
    params = visual.get("params", {})
    mode = params.get("mode") if isinstance(params, dict) else None
    if mode:
        parts.append(f"mode={mode}")
    title = visual.get("title") or (params.get("title") if isinstance(params, dict) else None)
    if title:
        parts.append(f"title={title}")
    if vtype == "route_map":
        cities = visual.get("cities", {})
        if isinstance(cities, dict) and cities:
            parts.append(f"cities={list(cities.keys())}")
    return " / ".join(parts) if parts else "(context 情報なし)"


def _is_target(visual: dict) -> bool:
    """このシーンが Vision 検査対象か判定する。"""
    if not isinstance(visual, dict):
        return False
    vtype = visual.get("type", "")
    if vtype in ("manim", "route_map"):
        return True
    if visual.get("template") in _TEMPLATE_ALLOW:
        return True
    return False


def evaluate_single_visual(scene: dict, frame_path: str) -> dict:
    """1つの visual フレームを scene の意図に照らして Vision 評価する。"""
    scene_id = scene.get("scene_id", "unknown")
    visual = scene.get("visual", {})
    narration = _summarize_narration(scene)
    context = _visual_context(visual)
    abs_path = os.path.abspath(frame_path)

    prompt = f"""以下の画像ファイル (数学ドキュメンタリー動画の1シーンから抽出した代表フレーム) を Read して評価してください。
画像ファイル: {abs_path}

【シーンID】{scene_id}
【このシーンで説明しようとしている内容 (ナレーション要約)】
{narration}
【図の意図 (テンプレート/モード/タイトル等)】
{context}

この図は Manim や matplotlib で生成した数式・幾何・年表・地図などの図解です。写真ではありません。
以下の観点で評価し、JSONのみ (```なし) で日本語回答してください。FP (誤検出) を避け、
判断が難しい観点は verdict を下げず理由に「判定不可」と明記してください。

(a) 概念伝達 [concept]:
    この図は、ナレーションが説明しようとしている概念が視覚的に伝わるか。
    無関係・的外れ・空っぽ (ほぼ何も描かれていない) なら warn。

(b) 無意味な動き [motion]:
    無意味に動き回る点 / 無限ループ / 時間稼ぎのスイープ等、意味のない動きの兆候はないか。
    ただし**静止画1枚では動きは判定困難**なので、確証がなければ verdict は下げず
    reason に「静止画のため判定不可」と書くこと。軌跡が乱雑に画面を埋めている等、
    静止画から明らかに無意味と分かる場合のみ warn。

(c) 図形の同定 [shape]:
    図形が意図した対象に見えるか。例: 独楽 (top / spinning top) を描くはずなのに
    独楽に見えない、球のはずが平面に見える、擬球のはずがただの曲線、等。
    意図した対象と明らかに違って見えるなら warn。

(d) ラベル衝突 [label]:
    ラベル同士、またはラベルと図形/軸/他の文字が重なって読めない (衝突・見切れ・
    枠外はみ出し) 箇所はないか。年表の年号と説明文の重なり、地図の都市名の重なり等。
    明らかに重なって判読不能なら warn。

JSONフォーマット:
{{
  "verdict": "ok" | "warn",
  "issues": [
    {{
      "aspect": "concept" | "motion" | "shape" | "label",
      "message": "問題の説明 (日本語、1〜2文。何がどう見えるか具体的に)",
      "suggestion": "改善の提案 (日本語、1文)"
    }}
  ],
  "positive": "良い点 (日本語、1文)"
}}

warn は明らかに問題がある場合のみ。問題がなければ verdict="ok"、issues=[] とすること。
判定不可の観点は issues に入れず、その旨を positive か省略で表現してよい。"""

    try:
        text = _call_claude_cli(prompt)
        if text is None:
            return {
                "scene_id": scene_id,
                "status": "error",
                "error": "Claude CLI returned no output",
            }
        result = _extract_json(text)
        if result is None:
            return {
                "scene_id": scene_id,
                "status": "parse_error",
                "error": f"JSON parse failed: {text[:100]}",
            }
        return {"scene_id": scene_id, "status": "ok", "result": result}
    except Exception as e:
        return {"scene_id": scene_id, "status": "error", "error": str(e)}


def _collect_target_scenes(scene_def: dict) -> list[dict]:
    """scene_definition から Vision 検査対象シーンを収集する。"""
    targets = []
    for section in scene_def.get("sections", []):
        section_id = section.get("section_id")
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if _is_target(visual):
                s = dict(scene)
                s["section_id"] = section_id
                targets.append(s)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vision QA for built Manim / route_map / timeline_recap visuals"
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument("--visuals-dir", default=None, help="Override visuals directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="warn 検出時に exit 1 (既定は advisory で exit 0)",
    )
    parser.add_argument("--debug", action="store_true", help="Claude CLI stderr を表示")
    parser.add_argument(
        "--scenes",
        default=None,
        help="検査する scene_id をカンマ区切りで指定 (既定: 全 scene)。"
        "1 シーンだけ再レンダしたときに、そのシーンだけ Vision 検査するために使う "
        "(--rebuild-scene からはこの形で呼ばれる)",
    )
    args = parser.parse_args()

    scene_json_path = os.path.abspath(args.scene_json)
    if not os.path.exists(scene_json_path):
        print(f"ERROR: scene_definition.json not found: {scene_json_path}")
        return 2

    episode_dir = os.path.dirname(scene_json_path)
    visuals_dir = args.visuals_dir or os.path.join(episode_dir, "visuals")

    with open(scene_json_path, encoding="utf-8") as f:
        scene_def = json.load(f)
    episode_id = scene_def.get("episode_id", "unknown")

    target_scenes = _collect_target_scenes(scene_def)

    # --scenes: 1 シーンだけ再レンダしたときに全 scene へ Claude vision を投げると
    # 部分再ビルドの速さが失われる。指定があればそこだけに絞る。存在しない
    # scene_id を黙って 0 件にすると「検査した」と読めてしまうので名指しで警告する。
    if args.scenes:
        wanted = [s.strip() for s in args.scenes.split(",") if s.strip()]
        available = {s.get("scene_id") for s in target_scenes}
        unknown = [w for w in wanted if w not in available]
        target_scenes = [s for s in target_scenes if s.get("scene_id") in wanted]
        if unknown:
            print(
                f"[WARN] --scenes に Vision 対象でない scene_id: {', '.join(unknown)} "
                "(ken_burns 等は Vision QA の対象外)"
            )

    print(f"\n{'=' * 60}")
    print("  Manim Vision QA (advisory)")
    print(f"{'=' * 60}")
    print(f"  Episode:     {episode_id}")
    print(f"  Targets:     {len(target_scenes)} manim/route_map/timeline scenes")
    print(f"  Visuals dir: {visuals_dir}")
    print()

    # ── Claude CLI 可用性チェック (不在なら graceful SKIP) ──────────────
    if os.system("claude --version >nul 2>&1") != 0:
        print("[SKIP] Claude Code CLI not found - Vision QA skipped (advisory).")
        print("       Install Claude Code + Max subscription to enable.")
        return 0

    # ── ffmpeg 可用性チェック (不在なら graceful SKIP) ────────────────
    if os.system("ffmpeg -version >nul 2>&1") != 0:
        print("[SKIP] ffmpeg not found - cannot extract frames, Vision QA skipped (advisory).")
        return 0

    if not target_scenes:
        print("[OK] Vision 検査対象の visual なし。")
        return 0

    start_time = time.time()
    tmp_dir = tempfile.gettempdir()

    all_warns = []
    scene_results = {}
    missing = []
    extract_fail = []
    tmp_frames = []

    for i, scene in enumerate(target_scenes):
        scene_id = scene["scene_id"]
        video_path = os.path.join(visuals_dir, f"{scene_id}.mp4")
        print(f"  [{i + 1}/{len(target_scenes)}] {scene_id}...", end=" ", flush=True)

        if not os.path.exists(video_path):
            print("[SKIP] mp4 欠如 (再ビルド中?)")
            missing.append(scene_id)
            continue

        frame_path = os.path.join(tmp_dir, f"_manim_vqa_frame_{scene_id}.png")
        tmp_frames.append(frame_path)
        if not _extract_frame(video_path, frame_path):
            print("[SKIP] frame 抽出失敗")
            extract_fail.append(scene_id)
            continue

        t0 = time.time()
        eval_result = evaluate_single_visual(scene, frame_path)
        elapsed = time.time() - t0

        if eval_result["status"] == "ok":
            result = eval_result["result"]
            verdict = result.get("verdict", "ok")
            issues = result.get("issues", [])
            icon = "[OK]" if verdict == "ok" else "[WARN]"
            print(f"{icon} ({elapsed:.0f}s, {len(issues)} issues)")
            scene_results[scene_id] = result
            for issue in issues:
                all_warns.append(
                    {
                        "scene_id": scene_id,
                        "aspect": issue.get("aspect"),
                        "message": issue.get("message"),
                        "suggestion": issue.get("suggestion"),
                    }
                )
        else:
            print(f"[ERR] {eval_result.get('error', '')[:50]}")
            scene_results[scene_id] = {"error": eval_result.get("error")}

    # ── temp frame 後始末 ─────────────────────────────────────────────
    for p in tmp_frames:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass

    # ── silent-fail 検出: 全シーン error なら Claude CLI 破損の疑い ──────
    checked = [r for r in scene_results.values() if isinstance(r, dict)]
    errored = sum(1 for r in checked if "error" in r)
    all_errored = len(checked) > 0 and errored == len(checked)

    total_elapsed = time.time() - start_time

    # ── サマリー ──────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    if all_errored:
        print("  [ERROR] 全シーン評価失敗。Claude CLI 破損の疑い (Vision QA 無効)。")
        print(f"{'=' * 60}\n")
        # advisory なので pipeline を止めないが、strict では失敗を伝える
        return 1 if args.strict else 0

    print(f"  Manim Vision QA: {episode_id}")
    print(
        f"  Checked: {len(scene_results)}  Warns: {len(all_warns)}  "
        f"Missing mp4: {len(missing)}  Extract-fail: {len(extract_fail)}"
    )
    print(f"  Time: {total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")
    print(f"{'=' * 60}")

    for w in all_warns:
        aspect = w.get("aspect", "?")
        print(f"  [W:{aspect}] [{w['scene_id']}] {w.get('message', '')}")
        if w.get("suggestion"):
            print(f"      -> {w.get('suggestion')}")

    if not all_warns:
        print("  [OK] Vision で検出された意味/美観の問題なし (advisory)。")

    if missing:
        print(f"\n  [NOTE] mp4 欠如シーン (再ビルド中の可能性): {', '.join(missing)}")

    print(f"{'=' * 60}\n")

    if all_warns:
        try:
            _src = os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
            )
            if _src not in sys.path:
                sys.path.insert(0, _src)
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("manim_vision_qa", len(all_warns))
        except Exception:
            pass

    # advisory: 既定は exit 0。--strict のときのみ warn で exit 1。
    if args.strict and all_warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
