"""route_place_check.py - ナレーションが語る地名が地図に描かれているかの意味レビュー (advisory).

ある回で user が「ナレーションはピレネーなのに地図に表示されていなくて分かりづらい」と
指摘した。**ナレーションが土地を語っているのに地図にその点が無いと、視聴者はどこの話なのか
分からないまま地図を見せられる**。

既存の route_map 検査は全て**レイアウト**の検査 で、
**内容** (語られたものが描かれているか) は誰も見ていない。逆向き (地図に出るが語られない) は
年号について `check_onscreen_years_traceable` が既にやっている。

## なぜ文字列一致でなく LLM か

決定論版を先に試した。全 40 route_map scene に対し、**全エピソードの都市名の和集合**を
辞書にして narration を走査すると 5 scene で発火したが、内訳は:

  - 007_noether「プリンストン高等研究所でも講義を行いました」-> **真** (実際に行った土地が地図に無い)
  - 013_turing「ロンドン数学会に投稿しました」               -> 偽 (団体名。本人はロンドンへ行っていない)
  - 053_dedekind「ベルリンやゲッティンゲンといった大きな大学の教授職に就く道もありました」-> 偽 (反実仮想)
  - 055_lagrange「オイラーがベルリンを去ってサンクトペテルブルクへ移ると」-> 偽 (他人の移動)
  - 060_grothendieck「ル・シャン**ボン**」に「ボン」が部分一致       -> 偽 (部分文字列)

真 1 / 偽 4。**地名が文字列として在るかどうかと、その人がそこに居たかどうかは別の問題**で、
前者しか見ない検査は原理的に後者を判定できない。さらに辞書方式は**辞書に無い地名を永久に
見逃す** — 起票の契機となったピレネーは、ある回が地図に足すまでどのエピソードにも無かった
ので、この検査が最も捕まえるべき当の事例を捕まえられない。よって references /
 F intro-semantic / ある回 route-legend と同型の **LLM advisory** にする。

## ADVISORY 隔離

- correction は書かせない。「語られたが地図に無い」の正解が「地図に足す」とは限らない
  (「ナレーションから地名を外す」「そもそも地図の対象外」もある) ので、人間が決める。
- `narration_evidence` にその地名を含む**本編の該当文の逐語引用**を必須化して接地する。
  本編に無い地名は報告できない。
- 空応答 / parse 失敗は status="UNAVAILABLE" (偽の issue を出さない)。ビルドは止めない。

cache は「その scene の cities + routes + narration」の hash に独立する
(`_route_place_cache.json`)。無関係な編集では Claude を呼ばない。

**必ず human が判断する (鵜呑み禁止)**。
"""

import hashlib
import json
import os
import time


def extract_route_place_scenes(scene_def: dict) -> list:
    """route_map シーンごとに「地図に在る地名」と「ナレーション本文」を取り出す。

    ナレーションが無いシーンは照合材料が無いので除外する。返り値が空なら対象なし。

    Returns:
        [{"scene_id", "title", "cities": [...], "routes": [...], "narration": "..."}]
    """
    out = []
    for section in scene_def.get("sections", []) or []:
        for scene in section.get("scenes", []) or []:
            visual = scene.get("visual") or {}
            if visual.get("type") != "route_map":
                continue
            narration = " ".join(scene.get("narration", []) or []).replace("|", "").strip()
            if not narration:
                continue
            routes = []
            for step in visual.get("route", []) or []:
                if not isinstance(step, dict):
                    continue
                routes.append(
                    {
                        "from": step.get("from", ""),
                        "to": step.get("to", ""),
                        "year": step.get("year", ""),
                        "label": (step.get("label") or "").strip(),
                    }
                )
            out.append(
                {
                    "scene_id": scene.get("scene_id") or scene.get("id") or "?",
                    "title": visual.get("title", ""),
                    "cities": list((visual.get("cities") or {}).keys()),
                    "routes": routes,
                    "narration": narration,
                }
            )
    return out


# プロンプトの版。**プロンプトを書き換えたらここを上げる**。cache キーは内容 hash なので、
# 版を持たないと「古いプロンプトで出した判定」が新しいプロンプトの結果として残り続ける
# (内容が変わるまで再実行されない)。上げると次のビルドで再レビューが走る (1 ep 約 33 秒)。
PROMPT_VERSION = "2026-08-06.1"


def content_hash(scene_def: dict) -> str:
    """地図の地名 + 経路 + ナレーション + プロンプト版の決定論 hash。"""
    blob = (
        PROMPT_VERSION
        + "\x00"
        + json.dumps(extract_route_place_scenes(scene_def), ensure_ascii=False, sort_keys=True)
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_route_place_prompt(scenes: list, subject: str = "") -> str:
    """narrow / advisory / anti-hallucination プロンプト."""
    subj = subject or "この人物"
    blocks = []
    for sc in scenes:
        lines = [
            f"## シーン {sc['scene_id']}"
            + (f" — 地図タイトル「{sc['title']}」" if sc["title"] else "")
        ]
        lines.append("- 地図に点として描かれている地名: " + "、".join(sc["cities"]))
        if sc["routes"]:
            lines.append("- 地図に描かれている経路:")
            for r in sc["routes"]:
                yr = f" {r['year']}年" if r["year"] else ""
                lbl = f"「{r['label']}」" if r["label"] else ""
                lines.append(f"    * {r['from']} → {r['to']}{yr} {lbl}")
        lines.append(f"- このシーンで読まれるナレーション:\n「{sc['narration']}」")
        blocks.append("\n".join(lines))
    body = "\n\n".join(blocks)

    return f"""あなたは数学史動画「{subj}」の地図 (route_map) を検証する編集者です。

このシーンでは、ナレーションが流れる間ずっと 1 枚の地図が画面に出ています。地図は
{subj}の足取りを点と線で描いたものです。**ナレーションが「{subj}がそこに居た土地」を
語っているのに、その点が地図に無いと、視聴者はいま聞いた場所を地図の上に見つけられません。**

あなたが探すのは唯一この一点だけ:

  **ナレーションが「{subj}が実際に居た/行った土地」として語っているのに、
    地図にその地名の点が無いもの。**

実例 (過去に起きた指摘): ナレーションが最後の隠棲地としてピレネーを語っていたのに、
地図にはその点が無く、視聴者から「どこの話か分からない」と指摘された。

# 検証対象
{body}

# タスク
各シーンについて、ナレーション中の地名を地図の地名と照合し、**上の条件に当てはまるものだけ**を
高い確信で報告してください。

# 報告してはいけないもの (厳守。ここを誤ると検査が雑音になります)
- **団体・作品・賞の名前に含まれる地名** (例:「ロンドン数学会に投稿した」のロンドン。
  本人がロンドンへ行った話ではない)。
- **反実仮想・一般論・比較のための言及** (例:「ベルリンやゲッティンゲンといった大学の
  教授職に就く道もありました」= 実際には行っていない)。
- **他人の移動** (例:「オイラーがサンクトペテルブルクへ移ると」= 主人公の足取りではない)。
- **国・地方・大陸など、点を打つには広すぎるもの** (例: フランス、ヨーロッパ、アメリカ)。
  ただし地図の縮尺から見て点として意味を持つ土地 (山地・村・郊外) は対象に含めます。
- **地図に別表記で載っているもの** (例: 地図の「ラセール(ピレネー)」はナレーションの
  「ピレネー」を含んでいる。載っているとみなす)。
- 比喩・慣用句としての地名。
- 確信が持てないもの。**雑音を出すくらいなら PASS**。

# その他の制約
- **どう直すべきかは書かないでください** (correction は書かない)。「語られたが地図に無い」の
  正解は「地図に点を足す」とは限らず (ナレーションから地名を外す / そもそも地図の対象外)、
  人間が決めます。指摘と根拠だけを出してください。
- `narration_evidence` には、**上に与えたナレーションの逐語引用のみ**を入れてください。
  与えられていない文については報告できません。

# 出力形式 (JSON のみ、JSON 以外のテキストは書かない)
```json
{{
  "status": "PASS" または "WARN",
  "issues": [
    {{
      "severity": "warning" または "info",
      "scene_id": "該当シーン",
      "place": "地図に無い地名",
      "narration_evidence": "その地名を含むナレーションの逐語引用 (1文)",
      "why_it_matters": "視聴者が何を見失うか (1文)",
      "confidence": 0.0-1.0
    }}
  ],
  "reviewed": true,
  "summary": "1-2文"
}}
```
- WARN = 高確信の欠落が 1 件以上。PASS = 報告なし。
- confidence < 0.7 の項目は原則 info。
- 出力は assistant の text ブロックに直接、ツールを使わず書いてください。
"""


def run_route_place_check(
    scene_def: dict, episode_dir: str, subject: str = "", debug: bool = False
) -> dict:
    """ナレーション地名 vs 地図地名の advisory レビュー。

    Returns {status, issues, summary}。issues は ADVISORY -- severity を warning/info に
    cap し source tag を付ける。呼び出し側は blocking severity に混ぜないこと。
    対象シーンが無ければ PASS で即返す (Claude を呼ばない)。
    """
    scenes = extract_route_place_scenes(scene_def)
    if not scenes:
        return {"status": "PASS", "issues": [], "summary": "地名照合対象の route_map なし"}

    from pre_script_fact_check import _load_cache, _save_cache, parse_fact_check_response

    cache_path = os.path.join(episode_dir, "_route_place_cache.json")
    cache = _load_cache(cache_path)
    h = content_hash(scene_def)
    if cache.get("content_hash") == h and "report" in cache:
        print("  [route-place] cache hit, skipping Claude call")
        report = cache["report"]
    else:
        print(f"  [route-place] reviewing {len(scenes)} route_map scene(s) via Claude...")
        from claude_backend import call_claude

        prompt = build_route_place_prompt(scenes, subject)
        t0 = time.time()
        response = call_claude(
            prompt=prompt, model="opus", debug=debug, prefix="routeplace", allowed_tools="Read"
        )
        elapsed = time.time() - t0
        print(f"  [route-place] returned in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        report = parse_fact_check_response(response)
        # Graceful degrade: parse_fact_check_response emits a synthetic critical
        # "internal" issue on empty/broken output. This review is advisory, so
        # treat that as UNAVAILABLE rather than surfacing a fake finding.
        if any(i.get("field") == "internal" for i in report.get("issues", [])):
            print("  [route-place] unavailable (empty/parse failure) -- advisory skipped")
            return {
                "status": "UNAVAILABLE",
                "issues": [],
                "summary": "route place review unavailable (empty/parse failure)",
            }
        _save_cache(
            cache_path,
            {
                "content_hash": h,
                "report": report,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    report = drop_ungrounded_issues(report, scenes)
    for issue in report.get("issues", []):
        if issue.get("severity") == "critical":
            issue["severity"] = "warning"
        issue.setdefault("source", "claude_route_place")
    return report


def drop_ungrounded_issues(report: dict, scenes: list) -> dict:
    """接地していない指摘を落とす (決定論の後段フィルタ)。

    残す条件は 2 つだけで、どちらも文字列として確かめられる:
      1. その地名が**そのシーンのナレーションに実在する** (幻覚の除去)。
      2. その地名が**地図の地名のどれにも含まれていない** (「ラセール(ピレネー)」に対する
         「ピレネー」のような別表記を「地図に無い」と報告させない)。

    プロンプトでも同じことを禁じているが、prompt は守られる保証がない。**地図に載って
    いるものを載っていないと報告する**のは、この検査への信頼を最も早く壊す誤りなので、
    LLM の遵守に任せず後段で落とす。
    """
    by_id = {sc["scene_id"]: sc for sc in scenes}
    kept = []
    for issue in report.get("issues", []) or []:
        place = (issue.get("place") or "").strip()
        sc = by_id.get(issue.get("scene_id"))
        if not place or sc is None:
            continue
        if place not in sc["narration"]:
            continue
        if any(place in city for city in sc["cities"]):
            continue
        kept.append(issue)
    out = dict(report)
    out["issues"] = kept
    if not kept and out.get("status") == "WARN":
        out["status"] = "PASS"
    return out


def read_cached_report(scene_def: dict, episode_dir: str) -> dict | None:
    """現在の地図/ナレーションと一致する cache があれば返す (Claude を呼ばない)。"""
    from pre_script_fact_check import _load_cache

    scenes = extract_route_place_scenes(scene_def)
    if not scenes:
        return None
    cache = _load_cache(os.path.join(episode_dir, "_route_place_cache.json"))
    if cache.get("content_hash") == content_hash(scene_def) and "report" in cache:
        return drop_ungrounded_issues(cache["report"], scenes)
    return None


def format_report(report: dict) -> str:
    """人が読む 1-block サマリ。"""
    status = report.get("status", "?")
    issues = report.get("issues", [])
    if status == "UNAVAILABLE":
        return "  [route-place] UNAVAILABLE (Claude 応答なし/parse 失敗) -- advisory skip"
    if not issues:
        return (
            f"  [route-place] {status}: 語られた地名は地図にあります ({report.get('summary', '')})"
        )
    lines = [f"  [route-place] {status}: {len(issues)} 件の地名欠落候補 (advisory, 要 human 確認)"]
    for i in issues:
        sid = i.get("scene_id", "?")
        place = i.get("place", "?")
        conf = i.get("confidence", "?")
        lines.append(f"    - {sid}「{place}」が地図にありません (conf {conf})")
        ev = i.get("narration_evidence", "")
        if ev:
            lines.append(f"        ナレーション: 「{ev[:70]}」")
        why = i.get("why_it_matters", "")
        if why:
            lines.append(f"        理由: {why[:90]}")
    return "\n".join(lines)
