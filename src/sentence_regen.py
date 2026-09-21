"""sentence_regen.py - 決定論 lint を script 生成の中で回し、引っかかった文だけを再生成する。

これまで である調 / 比喩的な誇張 / forbidden_phrases の決定論 lint は **生成の後** (validate の
warning と QA Gate 1) にしか走らず、引っかかると人が scene_definition を手で直していた。
ある回は「数理生態学の最初の頁」を user が通し視聴で拾い、手で言い換えた。
lint 自体は 1 秒で答えが出るのだから、**台本を保存する前に**回して、違反した文だけを LLM に
書き直させれば、手直しの往復 (と再ビルド) が要らなくなる。

設計:
  - 対象は narration の **1 文単位** (scene_definition の narration 配列の要素)。全文の再生成は
    しない (再生成のたびに別の穴が開く。Cloud TTS のキャッシュも文単位)。
  - 走らせる lint は決定論のものだけ: である調 (`qa_checker.run_dearu_lint` の warning。『』内の
    info は対象外) / 比喩的な誇張 (`hyperbole_lint` の **metaphor** だけ。primacy は出典があれば
    書けるので warning のまま人が判断) / `forbidden_phrases` (空白無視)。
  - 書き直しは前後の文を文脈として渡し、事実・固有名・数値を変えないよう指示する。返ってきた文を
    同じ lint にかけ、通らなければもう一周 (max_rounds)。通らないまま終わった文は **元の文を残して**
    名指しする (validate の warning に載る = 従来の網はそのまま)。
  - `narration_speech` が同じ長さの配列で在れば同じ index を同期する (LLM が返せば
    それ、返さなければ narration から `|` を外したもの)。`narration_speech_cloud` は scene ごと
    捨てる (gen_cloud_readings が作り直す。生成直後は strip 済みなので通常は無い)。
  - LLM 呼び出しは `call_fn(prompt) -> str` を注入する (回帰テストは偽の関数で回す)。

呼び出し元: `script_generator.generate_script` (strip_llm_cloud_readings の後、validate の前)。
`--no-sentence-regen` で抑止。
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

NL = "\n"
MAX_ROUNDS = 2
# 書き直しの長さは元の文の ±この比率まで (短すぎ = 内容が落ちた、長すぎ = 事実を足した)
LEN_RATIO_MIN = 0.5
LEN_RATIO_MAX = 1.6

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)
_WS_RE = re.compile(r"[\s　]+")


def _strip_ws(s: str) -> str:
    return _WS_RE.sub("", s)


def _iter_scenes(scene_def: dict):
    """実装は scene_def.iter_scenes (5 か所にあった同じ走査を 1 つに)。"""
    from scene_def import iter_scenes  # 同じ src/ 内 (sys.path の細工は要らない)

    yield from iter_scenes(scene_def)


# 「」『』の中 (会話・引用) は である調でよい。qa_checker の
# dearu lint は 『』 しか除外しないので、ここでは両方を消してから掛ける (出荷 74 話の較正で
# 「いいえ、…」「私は本物の数学を…感じていた。」のような台詞 6 件が該当した)。
_QUOTE_RE = re.compile(r"「[^」]*」|『[^』]*』")
# scene の notes が「意図的」と書いている scene では である調を再生成の対象にしない
#。QA Gate 1 の
# warning は残るので人は見る。
_INTENT_NOTE_RE = re.compile(r"意図的|リフレイン|反復|体言止め|である調の例外|ですます調の例外")


def _dearu_reasons(text: str) -> list[str]:
    from qa_checker import run_dearu_lint

    stripped = _QUOTE_RE.sub("", text)
    mini = {"sections": [{"scenes": [{"scene_id": "s", "narration": [stripped]}]}]}
    out = []
    for issue in run_dearu_lint(mini).get("issues", []):
        claim = str(issue.get("claim", ""))
        # run_dearu_lint は description.intro drift と 年代倒錯 も同じ issues に混ぜる
        if issue.get("severity") != "warning" or "である調終止候補:" not in claim:
            continue
        excerpt = claim.split("である調終止候補:", 1)[-1].strip()
        out.append(f"である調の終止 {excerpt} → ですます調にする")
    return out


def lint_sentence(
    text: str,
    forbidden: list[str],
    allow: list[str] | None = None,
    scene_notes: str | None = None,
) -> list[str]:
    """1 文にかける決定論 lint。違反理由の list を返す (空なら合格)。"""
    from hyperbole_lint import scan_text

    reasons: list[str] = []
    plain = text.replace("|", "")
    if isinstance(scene_notes, list):
        scene_notes = " ".join(str(x) for x in scene_notes)
    if not (scene_notes and _INTENT_NOTE_RE.search(str(scene_notes))):
        reasons += _dearu_reasons(plain)
    for h in scan_text(plain, allow):
        if h["kind"] == "metaphor":
            reasons.append(
                f"比喩的な誇張「{h['match']}」({h['label']}) → 確かめられる言い方に言い換える"
            )
    flat = _strip_ws(plain)
    for p in forbidden:
        if p and _strip_ws(p) in flat:
            reasons.append(f"禁止表現「{p}」→ 別の言い方で同じ内容を伝える")
    return reasons


def find_offending_sentences(
    scene_def: dict, forbidden: list[str], allow: list[str] | None = None
) -> list[dict]:
    """scene_definition の全 narration 文を lint し、違反した文を列挙する。"""
    out = []
    for scene in _iter_scenes(scene_def):
        narr = scene.get("narration", [])
        if isinstance(narr, str):
            narr = [narr]
        for idx, raw in enumerate(narr):
            if not isinstance(raw, str) or not raw.strip():
                continue
            reasons = lint_sentence(raw, forbidden, allow, scene.get("notes"))
            if reasons:
                out.append(
                    {
                        "scene_id": scene.get("scene_id", "unknown"),
                        "index": idx,
                        "text": raw,
                        "reasons": reasons,
                    }
                )
    return out


def build_sentence_prompt(scene: dict, idx: int, reasons: list[str], forbidden: list[str]) -> str:
    """1 文の書き直しを頼む prompt。前後の文を文脈として渡す。"""
    narr = scene.get("narration", [])
    if isinstance(narr, str):
        narr = [narr]
    prev_t = narr[idx - 1] if idx > 0 else ""
    next_t = narr[idx + 1] if idx + 1 < len(narr) else ""
    target = narr[idx]
    lines = [
        "あなたは日本語 YouTube 数学史ドキュメンタリー「数学史記」の台本校閲者です。",
        "次のナレーションのうち【対象の文】だけを書き直してください。",
        "",
        f"【前の文】{prev_t.replace('|', '')}",
        f"【対象の文】{target}",
        f"【次の文】{next_t.replace('|', '')}",
        "",
        "【直すべき点】",
    ]
    lines += [f"- {r}" for r in reasons]
    lines += [
        "",
        "【条件】",
        "- ですます調で書く (「〜です」「〜ます」「〜ました」)。である調は使わない。",
        "- 事実・固有名・年号・数値は一切変えない。新しい事実や評価を足さない。",
        "- 比喩的な誇張 (〜の最初の頁 / 〜の父 / 幕を開けた / 世界を変えた / 金字塔 等) は書かない。",
        "- 長さは元の文と同程度 (±30%)。",
        "- 字幕の区切り記号「|」は元の文と同じ流儀で、意味の切れ目に 25 文字以内ごとに置く。",
    ]
    if forbidden:
        lines.append("- 次の表現は使わない: " + " / ".join(forbidden))
    lines += [
        "",
        "出力は JSON のみ (説明文は書かない):",
        '{"narration": "書き直した文 (| 入り)", "narration_speech": "読み上げ用 (| 無し。数式記号があれば読み下し)"}',
    ]
    if all(r.startswith("である調") for r in reasons):
        lines += [
            "",
            "ただし、その文が本人の言葉の引用・題名の一文のリフレイン・意図的な体言止めで、"
            "ですます調にすると壊れる場合に限り、書き直さずに次を返してください:",
            '{"keep": true, "reason": "残す理由 (20 字以内)"}',
        ]
    return NL.join(lines)


def parse_sentence_response(text: str) -> dict | None:
    """LLM の応答を {"narration", "narration_speech"} か {"keep": True, "reason"} に。取れなければ None。"""
    if not text:
        return None
    m = _JSON_OBJ_RE.search(text)
    if m:
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            if obj.get("keep") is True:
                return {"keep": True, "reason": str(obj.get("reason") or "").strip()[:60]}
            narr = obj.get("narration")
            if isinstance(narr, str) and narr.strip():
                sp = obj.get("narration_speech")
                return {
                    "narration": narr.strip(),
                    "narration_speech": sp.strip() if isinstance(sp, str) and sp.strip() else None,
                }
    # フォールバック: 1 行の生テキスト (JSON を書かないモデル向け)
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) == 1 and not lines[0].startswith("{"):
        return {"narration": lines[0].strip("「」"), "narration_speech": None}
    return None


def _acceptable(new: str, old: str, forbidden: list[str], allow: list[str] | None) -> list[str]:
    """書き直しを受け入れられない理由 (空なら受け入れる)。"""
    why: list[str] = []
    ratio = len(new.replace("|", "")) / max(1, len(old.replace("|", "")))
    if ratio < LEN_RATIO_MIN or ratio > LEN_RATIO_MAX:
        why.append(f"長さが元の {ratio:.2f} 倍")
    if _strip_ws(new) == _strip_ws(old):
        why.append("元の文と同じ")
    why += lint_sentence(new, forbidden, allow)
    return why


def regenerate_sentences(
    scene_def: dict,
    config: dict | None,
    call_fn: Callable[[str], str],
    max_rounds: int = MAX_ROUNDS,
    log: Callable[[str], None] = print,
) -> dict:
    """違反した文だけを書き直す。scene_def を **その場で** 更新し、report dict を返す。

    report: {"regenerated": [...], "unresolved": [...], "kept": [...], "rounds": int, "calls": int}
    各要素は {"scene_id", "index", "reasons", "before", "after"} (unresolved は after 無し、
    kept は LLM が引用/リフレインとして残した文で "llm_reason" 付き)。
    """
    config = config or {}
    forbidden = [p for p in (config.get("forbidden_phrases") or []) if isinstance(p, str) and p]
    allow = [a for a in (config.get("hyperbole_allow") or []) if isinstance(a, str) and a]
    scenes = {s.get("scene_id"): s for s in _iter_scenes(scene_def)}
    report: dict = {"regenerated": [], "unresolved": [], "kept": [], "rounds": 0, "calls": 0}
    pending = find_offending_sentences(scene_def, forbidden, allow)
    if not pending:
        # 沈黙と未実行を区別する (「走る」と「読まれる」は別): 0 件でも一行出す
        log(
            "  [SENTENCE-REGEN] 決定論 lint (である調/比喩的誇張/forbidden_phrases) に該当する文なし"
        )
        return report
    log(f"  [SENTENCE-REGEN] 決定論 lint に {len(pending)} 文が該当。文単位で書き直します")
    for round_no in range(1, max_rounds + 1):
        if not pending:
            break
        report["rounds"] = round_no
        still: list[dict] = []
        for item in pending:
            scene = scenes.get(item["scene_id"])
            if scene is None:
                still.append(item)
                continue
            idx = item["index"]
            old = scene["narration"][idx]
            prompt = build_sentence_prompt(scene, idx, item["reasons"], forbidden)
            try:
                resp = call_fn(prompt)
            except Exception as e:  # noqa: BLE001 - keep the original sentence, report it
                log(f"    [SENTENCE-REGEN] {item['scene_id']}[{idx}] 呼び出し失敗: {e}")
                item["reasons"] = item["reasons"] + [f"LLM 呼び出し失敗: {e}"]
                still.append(item)
                continue
            report["calls"] += 1
            parsed = parse_sentence_response(resp)
            if parsed is None:
                item["reasons"] = item["reasons"] + ["応答から文を取り出せなかった"]
                still.append(item)
                continue
            if parsed.get("keep"):
                if all(r.startswith("である調") for r in item["reasons"]):
                    # 引用・リフレインとして残す。人が見るために warning には載せる
                    report["kept"].append(
                        {
                            "scene_id": item["scene_id"],
                            "index": idx,
                            "reasons": item["reasons"],
                            "before": old,
                            "llm_reason": parsed.get("reason", ""),
                        }
                    )
                    log(
                        f"    [SENTENCE-REGEN] {item['scene_id']}[{idx}] LLM が意図的な文として残した"
                        f" ({parsed.get('reason', '')}): {old.replace('|', '')}"
                    )
                    continue
                item["reasons"] = item["reasons"] + ["keep は である調以外には認めない"]
                still.append(item)
                continue
            new, new_speech = parsed["narration"], parsed.get("narration_speech")
            why = _acceptable(new, old, forbidden, allow)
            if why:
                log(
                    f"    [SENTENCE-REGEN] {item['scene_id']}[{idx}] round {round_no}: 不採用 ({'; '.join(why)})"
                )
                item["reasons"] = why
                still.append(item)
                continue
            scene["narration"][idx] = new
            speech = scene.get("narration_speech")
            if isinstance(speech, list) and len(speech) == len(scene["narration"]):
                speech[idx] = new_speech or new.replace("|", "")
            if scene.pop("narration_speech_cloud", None) is not None:
                log(
                    f"    [SENTENCE-REGEN] {item['scene_id']}: narration_speech_cloud を捨てた (gen_cloud が作り直す)"
                )
            report["regenerated"].append(
                {
                    "scene_id": item["scene_id"],
                    "index": idx,
                    "reasons": item["reasons"],
                    "before": old,
                    "after": new,
                }
            )
            log(f"    [SENTENCE-REGEN] {item['scene_id']}[{idx}] 書き直し: {old.replace('|', '')}")
            log(f"                                     → {new.replace('|', '')}")
        pending = still
    for item in pending:
        report["unresolved"].append(
            {
                "scene_id": item["scene_id"],
                "index": item["index"],
                "reasons": item["reasons"],
                "before": item["text"],
            }
        )
        log(
            f"    [SENTENCE-REGEN] {item['scene_id']}[{item['index']}] は {max_rounds} 周で直らず、"
            f"元の文を残しました: {'; '.join(item['reasons'])}"
        )
    log(
        f"  [SENTENCE-REGEN] 書き直し {len(report['regenerated'])} 文 / 意図的として残した {len(report['kept'])} 文"
        f" / 未解決 {len(report['unresolved'])} 文 (LLM 呼び出し {report['calls']} 回)"
    )
    return report


def unresolved_warnings(report: dict) -> list[str]:
    """validate の warnings に混ぜる文字列 (未解決 + LLM が意図的として残した文)。"""
    out = [
        f"[SENTENCE-REGEN] {u['scene_id']}[{u['index']}] は決定論 lint に引っかかったまま "
        f"({'; '.join(u['reasons'])}): {u['before'].replace('|', '')[:40]}…"
        for u in report.get("unresolved", [])
    ]
    out += [
        f"[SENTENCE-REGEN] {k['scene_id']}[{k['index']}] は LLM が意図的な文として残した "
        f"({k.get('llm_reason') or '理由なし'}) -- 引用/リフレインなら scene notes に「意図的」と書く: "
        f"{k['before'].replace('|', '')[:40]}…"
        for k in report.get("kept", [])
    ]
    return out
