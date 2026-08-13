"""route_legend_check.py - route_map の凡例ラベルが、そのカテゴリの経路を実際に説明して
いるかの意味レビュー (advisory).

route_map の凡例は `legend_labels` でカテゴリ (origin/education/career/...) に **1 つの
ラベル**を割り当てるが、そのラベルが**そのカテゴリに属する全経路について真かどうかを
誰も検査していない**。カテゴリは色を決めるだけで、ラベルは書きっぱなしになる。

これは 3 度目の再発:
  - ある回: 生成された「留学」「研究」が実態と合わず「進学」「就職」に手修正。
  - ある回: career -> 「官職に就く」としたが、4 本の career 経路のうち 2 本は
    「ドーブテール家」(家庭教師として住み込み) と単なる転居で、どちらも官職ではない。
    生成時の初期ラベルは「留学」「研究」で、ヴィエトはそのどちらもしていない。

既存の route_map 検査 (衝突 / 見切れ) は **配置**しか見ないので、
「凡例が嘘をついている」型は原理的に捕まらない。

方式 (references / F intro-semantic と同型の ADVISORY):
  経路ラベルは短い日本語の自由文 (法学の学位 / ドーブテール家 / ブルターニュ政庁顧問官 /
  枢密顧問官) なので、文字列一致では「官職に就く」との整合を判定できない。Claude に
  カテゴリ単位で「このラベルはこの経路群を言い表せているか」を判定させる。

  ADVISORY 隔離: correction は書かせない (LLM は尤もらしい代替ラベルをでっちあげる)。
  「このラベルはこの経路を説明できていない」という指摘と、**該当経路ラベルの逐語引用**
  だけを出させ、人間が最終判断する。ビルドは止めない。

  anti-hallucination の接地: `route_labels_not_covered` に渡した経路ラベルの逐語引用を
  必須化する。実在しない経路については報告できない。

  graceful degrade: 空応答 / parse 失敗は status="UNAVAILABLE" (偽の issue を出さない)。

cache は「カテゴリ + 凡例ラベル + 経路ラベル」の hash に独立するので、無関係な
narration 編集では再実行しない (`_route_legend_cache.json`)。

Signal/noise (実 Opus で全 37 ケース = route_map を持つ 36 ep + ある回修正前 を較正):
  PASS 11 / WARN 26。**人間が実際に凡例ラベルを選んだ 4 ep での分離が決定的**:
    - 008_al_khwarizmi (12世紀 ラテン語訳)   -> PASS
    - 059_gosset (進学 / 就職 = 手修正済み)   -> PASS  ← 過去に手で直した版を正しく通す
    - 061_dantzig (生まれる/学びに行く/職に就く) -> PASS
    - 063_viete 修正前 (官職に就く)           -> WARN  ← 「法学の学位」「ドーブテール家」を名指し
  = 正しいラベル 3/3 を通し、既知欠陥 1/1 を、起票時に指摘された当の 2 経路で検出。

  残る 22 件は `legend_labels` を書かず**既定ラベルに落ちている 30 ep** 側に出る。これは
  検査の雑音ではなく、`_DEFAULT_LEGEND_LABELS` 自体が意味の強い語である事による**系統的な
  欠陥**の検出:
    - 「留学」= 外国で学ぶこと。国内進学 (ある回/024/028/030/042/050/053/060) は留学でない。
    - 「亡命」= 政治的逃避。ラマヌジャンの招聘渡英・関孝和の栄転・
      デカルトの自発的移住・フーリエの県知事任命 はいずれも逆の意味。
    - 「研究」= 学術的探究。ライプニッツの法学者就任/外交使節/図書館長・
      コーシーの技師・ヴァイエルシュトラスの中等教員 は研究職でない。
  これは ある回が手で直した (留学・研究 -> 進学・就職) のと同じ型が 19 ep に残っている、
  という発見。**既定ラベルを中立な語に変えるのが根治**だが、出荷済み 30 ep の絵を変える
  編集判断なのでここでは行わず、検査が指摘するに留める。

  発火率が高いのは検査が緩いからではない (上の 4 ep の分離を参照)。件数を減らす目的で
  scope を狭めない --過去の運用知見の方針。

**必ず human が史実と照合して最終判断する (鵜呑み禁止)**。
"""

import hashlib
import json
import os
import time

# 凡例に出うる既知カテゴリと、legend_labels 未指定時の既定ラベル。
# visual_generator の凡例構築と同じ並び・同じ既定値を持つ (import 循環を避けて複製)。
_DEFAULT_LEGEND_LABELS = {
    "origin": "生誕",
    "education": "留学",
    "career": "研究",
    "wandering": "遍歴",
    "exile": "亡命",
    "final": "最期の地",
}
_KNOWN_CATEGORIES = list(_DEFAULT_LEGEND_LABELS)


def extract_route_legend_groups(scene_def: dict) -> list:
    """route_map シーンごとに「カテゴリ -> (凡例ラベル, 経路ラベル群)」を取り出す。

    凡例に載らないもの (未知カテゴリ) と、比較材料が無いもの (経路ラベルが全て空) は
    除外する。返り値が空なら検査対象なし。

    Returns:
        [{"scene_id", "title", "groups": [{"category","legend_label","routes":[...]}]}]
    """
    out = []
    for section in scene_def.get("sections", []) or []:
        for scene in section.get("scenes", []) or []:
            visual = scene.get("visual") or {}
            if visual.get("type") != "route_map":
                continue
            routes = visual.get("route", []) or []
            labels = visual.get("legend_labels") or _DEFAULT_LEGEND_LABELS

            by_cat: dict = {}
            for step in routes:
                if not isinstance(step, dict):
                    continue
                cat = step.get("category", "wandering")
                # 未知カテゴリは凡例に載らない (=説明すべき凡例が無い) ので対象外。
                if cat not in _KNOWN_CATEGORIES:
                    continue
                label = (step.get("label") or "").strip()
                frm, to = step.get("from", ""), step.get("to", "")
                by_cat.setdefault(cat, []).append(
                    {"label": label, "from": frm, "to": to, "year": step.get("year", "")}
                )

            groups = []
            for cat, steps in by_cat.items():
                # 経路ラベルが 1 つも無ければ照合材料が無い。
                if not any(s["label"] for s in steps):
                    continue
                groups.append(
                    {
                        "category": cat,
                        "legend_label": labels.get(cat, _DEFAULT_LEGEND_LABELS.get(cat, cat)),
                        "routes": steps,
                    }
                )
            if groups:
                out.append(
                    {
                        "scene_id": scene.get("scene_id") or scene.get("id") or "?",
                        "title": visual.get("title", ""),
                        "groups": groups,
                    }
                )
    return out


# プロンプトの版。**プロンプトを書き換えたらここを上げる**。cache キーは内容 hash なので、
# 版を持たないと「古いプロンプトで出した判定」が新しいプロンプトの結果として残り続ける
# (内容が変わるまで再実行されない)。 の route_place_check と同じ扱い。
PROMPT_VERSION = "2026-08-06.1"


def content_hash(scene_def: dict) -> str:
    """カテゴリ + 凡例ラベル + 経路ラベル + プロンプト版の決定論 hash。"""
    blob = (
        PROMPT_VERSION
        + "\x00"
        + json.dumps(extract_route_legend_groups(scene_def), ensure_ascii=False, sort_keys=True)
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_route_legend_prompt(scene_groups: list, subject: str = "") -> str:
    """narrow / advisory / anti-hallucination プロンプト."""
    subj = subject or "?"
    blocks = []
    for sc in scene_groups:
        lines = [
            f"## シーン {sc['scene_id']}"
            + (f" — 地図タイトル「{sc['title']}」" if sc["title"] else "")
        ]
        for g in sc["groups"]:
            lines.append(f"- カテゴリ `{g['category']}` の凡例ラベル: 「{g['legend_label']}」")
            lines.append("  このカテゴリに属する経路:")
            for r in g["routes"]:
                lbl = r["label"] or "(ラベルなし)"
                yr = f" {r['year']}年" if r["year"] else ""
                lines.append(f"    * {r['from']} → {r['to']}{yr}: 「{lbl}」")
        blocks.append("\n".join(lines))
    body = "\n\n".join(blocks)

    return f"""あなたは数学史動画「{subj}」の地図 (route_map) の**凡例が正しいか**を検証する編集者です。

地図では、移動経路をカテゴリごとに色分けし、凡例がカテゴリごとに**1 つのラベル**を与えます。
凡例ラベルは、そのカテゴリに属する**すべての経路に当てはまっていなければなりません**。
1 本でも当てはまらない経路があると、視聴者はその線を誤って読みます。

あなたが探すのは唯一この一点だけ:

  **凡例ラベルが、そのカテゴリに属する経路の一部 (または全部) を言い表せていない箇所。**

実例 (過去に起きた誤り):
  - カテゴリ `career` に「官職に就く」というラベルを付けたが、属する経路の中に
    「家庭教師として住み込み」や単なる転居が含まれていた。どちらも官職ではないので、
    凡例が経路を説明できていない。
  - 「留学」「研究」というラベルを付けたが、その人物は留学も研究職就任もしていなかった。

# 検証対象
{body}

# タスク
各カテゴリについて、凡例ラベルとその経路群を照合し、**ラベルが当てはまらない経路がある**
ものだけを、高い確信で報告してください。

# 重要な制約 (厳守)
- ラベルは短い要約なので、**多少の一般化は正常です**。経路群の全体をおおむね言い表せて
  いるなら報告しない (例:「就職」が複数の異なる職を束ねるのは正常)。
- 報告するのは、**ラベルが明確に偽になる経路がある**場合だけです (官職でないものを
  「官職に就く」と呼ぶ、行っていない「留学」と呼ぶ、等)。
- **正しいラベルを断定しないでください** (correction は書かない)。「このラベルはこの経路を
  説明できていない」という指摘に留め、人間が史実を確認して決めます。
- `route_labels_not_covered` には、**上に与えた経路ラベルの逐語引用のみ**を入れてください。
  与えられていない経路については報告できません。
- 経路ラベルだけでは職種や事情が判断できない場合は報告しない (推測しない)。
- 確信が持てなければ報告しない (precision 優先)。雑音を出すくらいなら PASS。

# 出力形式 (JSON のみ、JSON 以外のテキストは書かない)
```json
{{
  "status": "PASS" または "WARN",
  "issues": [
    {{
      "severity": "warning" または "info",
      "scene_id": "該当シーン",
      "category": "該当カテゴリ (例: career)",
      "legend_label": "その凡例ラベル",
      "route_labels_not_covered": ["当てはまらない経路ラベルの逐語引用", "..."],
      "why_it_matters": "なぜそのラベルでは誤読されるか (1文)",
      "confidence": 0.0-1.0
    }}
  ],
  "reviewed": true,
  "summary": "1-2文"
}}
```
- WARN = 高確信の不整合が 1 件以上。PASS = 報告なし。
- confidence < 0.7 の項目は原則 info。
- 出力は assistant の text ブロックに直接、ツールを使わず書いてください。
"""


def run_route_legend_check(
    scene_def: dict, episode_dir: str, subject: str = "", debug: bool = False
) -> dict:
    """凡例ラベル整合の advisory レビュー。

    Returns {status, issues, summary}。issues は ADVISORY -- severity を warning/info に
    cap し source tag を付ける。呼び出し側は blocking severity に混ぜないこと。
    対象シーンが無ければ PASS で即返す (Claude を呼ばない)。
    """
    groups = extract_route_legend_groups(scene_def)
    if not groups:
        return {"status": "PASS", "issues": [], "summary": "凡例照合対象の route_map なし"}

    from pre_script_fact_check import _load_cache, _save_cache, parse_fact_check_response

    cache_path = os.path.join(episode_dir, "_route_legend_cache.json")
    cache = _load_cache(cache_path)
    h = content_hash(scene_def)
    if cache.get("content_hash") == h and "report" in cache:
        print("  [route-legend] cache hit, skipping Claude call")
        report = cache["report"]
    else:
        n_cat = sum(len(sc["groups"]) for sc in groups)
        print(f"  [route-legend] reviewing {n_cat} legend category/categories via Claude...")
        from claude_backend import call_claude

        prompt = build_route_legend_prompt(groups, subject)
        t0 = time.time()
        response = call_claude(
            prompt=prompt, model="opus", debug=debug, prefix="routelegend", allowed_tools="Read"
        )
        elapsed = time.time() - t0
        print(f"  [route-legend] returned in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        report = parse_fact_check_response(response)
        # Graceful degrade: parse_fact_check_response emits a synthetic critical
        # "internal" issue on empty/broken output. This review is advisory, so
        # treat that as UNAVAILABLE rather than surfacing a fake finding.
        if any(i.get("field") == "internal" for i in report.get("issues", [])):
            print("  [route-legend] unavailable (empty/parse failure) -- advisory skipped")
            return {
                "status": "UNAVAILABLE",
                "issues": [],
                "summary": "route legend review unavailable (empty/parse failure)",
            }
        _save_cache(
            cache_path,
            {
                "content_hash": h,
                "report": report,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    for issue in report.get("issues", []):
        if issue.get("severity") == "critical":
            issue["severity"] = "warning"
        issue.setdefault("source", "claude_route_legend")
    return report


def read_cached_report(scene_def: dict, episode_dir: str) -> dict | None:
    """現在の凡例/経路と一致する cache があれば返す (Claude を呼ばない)。

    pipeline の最終 roll-up 用: 高い Claude 呼び出しは visuals step が済ませておき、
    verify 側は cache を読むだけにして安価に保つ。
    """
    from pre_script_fact_check import _load_cache

    if not extract_route_legend_groups(scene_def):
        return None
    cache = _load_cache(os.path.join(episode_dir, "_route_legend_cache.json"))
    if cache.get("content_hash") == content_hash(scene_def) and "report" in cache:
        return cache["report"]
    return None


def format_report(report: dict) -> str:
    """人が読む 1-block サマリ。"""
    status = report.get("status", "?")
    issues = report.get("issues", [])
    if status == "UNAVAILABLE":
        return "  [route-legend] UNAVAILABLE (Claude 応答なし/parse 失敗) -- advisory skip"
    if not issues:
        return f"  [route-legend] {status}: 凡例ラベルの不整合なし ({report.get('summary', '')})"
    lines = [
        f"  [route-legend] {status}: {len(issues)} 件の凡例不整合候補 (advisory, 要 human 確認)"
    ]
    for i in issues:
        cat = i.get("category", "?")
        lbl = i.get("legend_label", "?")
        conf = i.get("confidence", "?")
        sid = i.get("scene_id", "?")
        lines.append(f"    - {sid} `{cat}`「{lbl}」(conf {conf})")
        for r in i.get("route_labels_not_covered", []) or []:
            lines.append(f"        当てはまらない経路: 「{r}」")
        why = i.get("why_it_matters", "")
        if why:
            lines.append(f"        理由: {why[:90]}")
    return "\n".join(lines)
