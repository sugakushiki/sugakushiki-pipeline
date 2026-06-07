"""B-14: cross-episode ターム整合性 lint (Wikidata Q-id ベース)。

全 episodes/*/scene_definition.json からカタカナ人名 + 数学概念を抽出し、
Wikidata SPARQL で Q-id 正準化。同じ Q-id が複数の表記で出現した場合に
warning を出力する。

X-1 (例: ニルス vs ニールスの表記揺れ) のような表記揺れを検出する。

使い方:
    python scripts/lint_cross_episode_terms.py
    python scripts/lint_cross_episode_terms.py --ep 020_abel  # 単一 ep のみ
    python scripts/lint_cross_episode_terms.py --no-cache    # キャッシュ無視

出力: docs/internal/cross_ep_lint_<YYYY-MM-DD>.md
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

# Phase 1.5 (Levenshtein 補完) の閾値
LEV_RATIO_THRESHOLD = 0.85  # SequenceMatcher.ratio()
LEV_MIN_LEN = 6  # min(len(t1), len(t2)) >= 6 (短い term での FP 抑制)

# Reuse B-17 Wikidata helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pre_script_fact_check import (  # noqa: E402
    _WIKIDATA_API,
    _WIKIDATA_UA,
    _wikidata_search_entity,
)

# Extraction regexes
# 「ニルス・ヘンリック・アーベル」「アル＝フワーリズミー」などの中点・等号区切り名
KATAKANA_NAME = re.compile(r"[ァ-ヴー]{2,}(?:[・＝][ァ-ヴー]{2,})+")
# 「フェルマーの最終定理」「カントールの定理」「ベルトランの仮説」など
THEOREM_PATTERN = re.compile(
    r"[一-龯ァ-ヴーぁ-んa-zA-Z0-9]{2,12}(?:の)?(?:定理|補題|公理|仮説|予想|法則|問題)"
)
# 「楕円関数」「集合論」「行列式」「複素平面」など、漢字 4 字以上の数学術語候補
KANJI_TERM = re.compile(r"[一-龯]{3,8}(?:論|論理|学|式|空間|関数|平面|集合|群|環|体|数|論)")

# Excluded terms (general words / non-mathematical) — 抽出ノイズ削減
EXCLUDE_TERMS = {
    "問題",
    "予想",
    "定理",
    "補題",
    "仮説",
    "公理",
    "法則",  # 単独語
    "数学者",
    "物理学者",
    "天文学者",
    "言語学者",
    "後の問題",
    "次の問題",
    "この問題",
    "ある問題",
}


def extract_text_from_scene_def(scene_def: dict) -> list[str]:
    """scene_definition.json からテキスト系フィールドを再帰的に集める。"""
    texts: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, str):
            texts.append(node)
        elif isinstance(node, list):
            for item in node:
                _walk(item)
        elif isinstance(node, dict):
            for k, v in node.items():
                # 抽出対象外のキー (ファイル名・ID 等は cross-ep 比較に意味がない)
                if k in {
                    "scene_id",
                    "section_id",
                    "id",
                    "type",
                    "template",
                    "voice",
                    "speaker",
                    "image_url",
                    "audio_path",
                    "duration",
                    "duration_seconds",
                    "fps",
                    "resolution",
                    "use_reference",
                    "no_human",
                    "qa_skip",
                    "skip",
                }:
                    continue
                _walk(v)

    # narration / narration_speech / visual の text 系 / chapter_subtitles / description
    _walk(scene_def.get("sections", []))
    desc = scene_def.get("description", {}) or {}
    if isinstance(desc, dict):
        for k in ("intro", "chapter_subtitles", "tags"):
            _walk(desc.get(k))
    return texts


def extract_candidates(texts: list[str]) -> dict[tuple[str, str], int]:
    """テキスト集合から (term, type) -> count の辞書を返す。"""
    candidates: dict[tuple[str, str], int] = defaultdict(int)
    for text in texts:
        if not text:
            continue
        # カタカナ人名 (中点・等号区切り)
        for m in KATAKANA_NAME.finditer(text):
            term = m.group(0)
            if len(term) < 4:
                continue
            candidates[(term, "person")] += 1
        # 「○○の定理」型
        for m in THEOREM_PATTERN.finditer(text):
            term = m.group(0)
            if term in EXCLUDE_TERMS:
                continue
            candidates[(term, "theorem")] += 1
    return dict(candidates)


def wikidata_resolve_qid(
    term: str,
    typ: str,
    cache: dict,
    timeout: int = 10,
) -> str | None:
    """Wikidata wbsearchentities で term -> Q-id を解決。キャッシュ付き。"""
    cache_key = f"{typ}:{term}"
    if cache_key in cache:
        return cache[cache_key]

    # 日本語 search
    qid = _search_wikidata_label(term, lang="ja", timeout=timeout)
    if not qid:
        # 英語 search にフォールバック (人名は英語で見つかる確率高)
        qid = _wikidata_search_entity(term, timeout=timeout)
    cache[cache_key] = qid
    time.sleep(1.0)  # rate limit
    return qid


def _search_wikidata_label(name: str, lang: str = "ja", timeout: int = 10) -> str | None:
    """日本語ラベルで Wikidata 検索 (wbsearchentities)。"""
    if not name:
        return None
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": lang,
        "format": "json",
        "type": "item",
        "limit": 3,
    }
    url = _WIKIDATA_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _WIKIDATA_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    candidates = data.get("search", [])
    return candidates[0]["id"] if candidates else None


def get_wikidata_labels(qid: str, timeout: int = 10) -> dict:
    """Q-id の labels (ja/en) と aliases を取得。表記揺れ集合の参照に使う。"""
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "labels|aliases",
        "languages": "ja|en",
        "format": "json",
    }
    url = _WIKIDATA_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _WIKIDATA_UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {"labels": {}, "aliases": []}
    entity = data.get("entities", {}).get(qid, {})
    labels = {lang: lbl["value"] for lang, lbl in entity.get("labels", {}).items()}
    aliases: list[str] = []
    for lang, alist in entity.get("aliases", {}).items():
        for a in alist:
            aliases.append(a["value"])
    return {"labels": labels, "aliases": aliases}


def main() -> int:
    ap = argparse.ArgumentParser(description="cross-episode ターム整合性 lint (Wikidata)")
    ap.add_argument("--ep", default=None, help="単一 ep のみ実行 (e.g. 020_abel)")
    ap.add_argument("--no-cache", action="store_true", help="キャッシュ無視で再 query")
    ap.add_argument(
        "--cache-path",
        default="scripts/_cross_ep_lint_cache.json",
        help="Wikidata 解決結果のキャッシュ JSON",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="レポート出力先 (デフォルト: docs/internal/cross_ep_lint_<YYYY-MM-DD>.md)",
    )
    ap.add_argument("--timeout", type=int, default=10, help="Wikidata API タイムアウト秒")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    output_path = args.output or f"docs/internal/cross_ep_lint_{today}.md"

    # Load cache
    cache: dict = {}
    if not args.no_cache and os.path.exists(args.cache_path):
        with open(args.cache_path, encoding="utf-8") as f:
            cache = json.load(f)

    # Step 1: collect all scene_definition.json
    sd_glob = "episodes/*/scene_definition.json"
    sd_paths = sorted(glob.glob(sd_glob))
    if args.ep:
        sd_paths = [p for p in sd_paths if args.ep in p]
    if not sd_paths:
        print(f"No scene_definition.json found ({sd_glob})", file=sys.stderr)
        return 1

    # Step 2: extract candidates per ep
    ep_candidates: dict[str, dict[tuple[str, str], int]] = {}
    print(f"[1/4] Extracting candidates from {len(sd_paths)} episode(s)...")
    for sd_path in sd_paths:
        ep_id = os.path.basename(os.path.dirname(sd_path))
        with open(sd_path, encoding="utf-8") as f:
            sd = json.load(f)
        texts = extract_text_from_scene_def(sd)
        cands = extract_candidates(texts)
        ep_candidates[ep_id] = cands
        print(f"  {ep_id}: {len(cands)} unique candidates from {len(texts)} text fields")

    # Step 3: aggregate unique terms across all eps and resolve to Q-id
    all_terms: set[tuple[str, str]] = set()
    for cands in ep_candidates.values():
        all_terms.update(cands.keys())
    print(f"[2/4] Resolving {len(all_terms)} unique terms via Wikidata (cached: {len(cache)})...")
    qid_map: dict[tuple[str, str], str | None] = {}
    for i, (term, typ) in enumerate(sorted(all_terms), start=1):
        qid = wikidata_resolve_qid(term, typ, cache, timeout=args.timeout)
        qid_map[(term, typ)] = qid
        if i % 10 == 0:
            print(f"  resolved {i}/{len(all_terms)} (cache size: {len(cache)})")

    # Save cache
    os.makedirs(os.path.dirname(args.cache_path), exist_ok=True)
    with open(args.cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"  cache saved to {args.cache_path} ({len(cache)} entries)")

    # Step 4: aggregate by Q-id and detect variants
    print("[3/4] Aggregating by Q-id and detecting variant collisions...")
    # qid -> {ep_id: set(variants)}
    qid_to_variants: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    qid_type: dict[str, str] = {}  # qid -> type (person/theorem)
    for ep_id, cands in ep_candidates.items():
        for (term, typ), count in cands.items():
            qid = qid_map.get((term, typ))
            if not qid:
                continue
            qid_to_variants[qid][ep_id].add(term)
            qid_type[qid] = typ

    # Detect: 同一 Q-id で 2 種以上の表記が出現
    drift_findings: list[dict] = []
    for qid, ep_vars in qid_to_variants.items():
        all_vars: set[str] = set()
        for v in ep_vars.values():
            all_vars.update(v)
        if len(all_vars) < 2:
            continue
        # ラベル/aliases を取得して「正準形」を提示
        wd_info = get_wikidata_labels(qid, timeout=args.timeout)
        time.sleep(0.5)
        drift_findings.append(
            {
                "qid": qid,
                "type": qid_type[qid],
                "labels": wd_info["labels"],
                "aliases": wd_info["aliases"],
                "variants": {ep: sorted(v) for ep, v in sorted(ep_vars.items())},
                "all_variants": sorted(all_vars),
            }
        )

    print(
        f"  found {len(drift_findings)} drift cases (out of {len(qid_to_variants)} resolved Q-ids)"
    )

    # Step 4.5: Phase 1.5 — Wikidata 解決失敗候補同士の Levenshtein 距離による補完検出
    # X-1 (ニルス/ニールス・ヘンリック・アーベル) のような表記揺れを Wikidata 解決失敗時に救済する
    print("[3.5/4] Levenshtein supplemental detection for Wikidata-unresolved terms...")
    ep_unresolved: dict[tuple[str, str], set[str]] = defaultdict(set)
    for ep_id, cands in ep_candidates.items():
        for term, typ in cands:
            if not qid_map.get((term, typ)):
                ep_unresolved[(term, typ)].add(ep_id)

    unres_list = sorted(ep_unresolved.keys())
    lev_findings: list[dict] = []
    for i, (t1, ty1) in enumerate(unres_list):
        for t2, ty2 in unres_list[i + 1 :]:
            if ty1 != ty2 or t1 == t2:
                continue
            if min(len(t1), len(t2)) < LEV_MIN_LEN:
                continue  # 短い term は FP リスク高、抽出 regex でカバー不要のもの
            ratio = SequenceMatcher(None, t1, t2).ratio()
            if ratio < LEV_RATIO_THRESHOLD:
                continue
            eps1, eps2 = ep_unresolved[(t1, ty1)], ep_unresolved[(t2, ty2)]
            cross_ep = bool(eps1 - eps2 or eps2 - eps1)  # 別 ep に跨る場合のみ採用
            lev_findings.append(
                {
                    "type": ty1,
                    "term1": t1,
                    "term2": t2,
                    "ratio": round(ratio, 3),
                    "eps1": sorted(eps1),
                    "eps2": sorted(eps2),
                    "cross_ep": cross_ep,
                }
            )
    print(
        f"  found {len(lev_findings)} Levenshtein candidates "
        f"({sum(1 for f in lev_findings if f['cross_ep'])} cross-ep)"
    )

    # Step 5: report
    print(f"[4/4] Writing report to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    lev_cross_ep = [f for f in lev_findings if f["cross_ep"]]
    lines = [
        "# Cross-episode ターム整合性 lint (B-14)",
        "",
        f"**実行日**: {today}",
        f"**対象 ep**: {len(ep_candidates)} episode ({', '.join(sorted(ep_candidates.keys()))})",
        f"**抽出候補総数**: {len(all_terms)}",
        f"**Wikidata 解決成功**: {sum(1 for q in qid_map.values() if q)}",
        f"**Wikidata Q-id 揺れ検出**: {len(drift_findings)} 件",
        f"**Levenshtein 補完 (Wikidata 未解決)**: {len(lev_findings)} 件 (うち cross-ep {len(lev_cross_ep)} 件)",
        "",
        "---",
        "",
        "## Wikidata Q-id ベース 揺れ一覧",
        "",
    ]
    if not drift_findings:
        lines.append("揺れなし。")
    else:
        for finding in sorted(drift_findings, key=lambda x: (x["type"], x["qid"])):
            qid = finding["qid"]
            ja = finding["labels"].get("ja", "(no ja label)")
            en = finding["labels"].get("en", "(no en label)")
            lines.append(f"### [{qid}](https://www.wikidata.org/wiki/{qid}) {ja} ({en})")
            lines.append("")
            lines.append(f"- **type**: {finding['type']}")
            lines.append(f"- **Wikidata 推奨表記 (ja)**: `{ja}`")
            if finding["aliases"]:
                lines.append(f"- **Wikidata aliases**: {', '.join(finding['aliases'][:10])}")
            lines.append(
                f"- **検出 variants**: {', '.join(repr(v) for v in finding['all_variants'])}"
            )
            lines.append("- **ep 別出現**:")
            for ep, vars_in_ep in finding["variants"].items():
                lines.append(f"  - `{ep}`: {', '.join(repr(v) for v in vars_in_ep)}")
            lines.append("")

    # Levenshtein 補完 section
    lines.extend(
        [
            "---",
            "",
            "## Levenshtein 補完候補 (Wikidata 未解決)",
            "",
            f"**閾値**: SequenceMatcher.ratio() ≥ {LEV_RATIO_THRESHOLD} かつ min_len ≥ {LEV_MIN_LEN}",
            "**目的**: Wikidata に登録されていない複合名 (例: 「ニルス・ヘンリック・アーベル」) の表記揺れを救済",
            "",
        ]
    )
    if not lev_findings:
        lines.append("候補なし。")
        lines.append("")
    else:
        # Cross-ep を優先表示
        sorted_lev = sorted(lev_findings, key=lambda x: (not x["cross_ep"], -x["ratio"]))
        for f in sorted_lev:
            cross_marker = " **[cross-ep]**" if f["cross_ep"] else " (same-ep only)"
            lines.append(
                f"### {f['type']}: `{f['term1']}` ↔ `{f['term2']}` (ratio={f['ratio']}){cross_marker}"
            )
            lines.append("")
            lines.append(f"- `{f['term1']}` 出現 ep: {', '.join(f['eps1'])}")
            lines.append(f"- `{f['term2']}` 出現 ep: {', '.join(f['eps2'])}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 注釈",
            "",
            "- 公開済み ep (公開済みエピソード) の音声は変更不可。scene_definition.json / description / YouTube 概要欄のテキストのみ修正可能",
            "- 未公開 ep (未公開エピソード) は再ビルドで修正可能、ただし baseline 影響注意",
            "- Wikidata Q-id 解決失敗 (= Wikidata 未登録) は Phase 1.5 (Levenshtein 補完) で救済",
            "- false positive 例: 同名異人 (ヤコブ・ベルヌーイとヤコブ II ベルヌーイ等) で Q-id 衝突する場合あり",
            f"- Levenshtein 閾値 (ratio ≥ {LEV_RATIO_THRESHOLD}, min_len ≥ {LEV_MIN_LEN}) は調整可能。短い表記 (例: 「カルダノ/カルダーノ」) は対象外、Phase 2 で抽出 regex 拡張により対応予定",
            "",
        ]
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report saved: {output_path}")
    print(f"Drift cases: {len(drift_findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
