"""intro_semantic_check.py - (F): narration -> description.intro の意味一致レビュー.

`scene_definition.json` の `description.intro` は YouTube 概要欄の【導入】に焼き込まれる
本編の短い要約 (引き) で、script_generator が LLM で生成する。生成後に narration を
編集しても intro は自動同期されないため、**本編が保持している数学的前提条件・限定詞を
intro が落とし、記述が不正確になる** drift が起こりうる。

既存 2 チェックはこの意味 drift を捕まえない:
  - qa_checker._detect_description_drift : intro <-> narration の 6-gram coverage。
    **言い換えで表層が変わると意味 drift を取りこぼす** (これが F を足す理由)。
  - description_meta.check_staleness : episode_config -> intro の決定論署名。
    narration -> intro の意味方向は見ない (別軸)。

方式:
  intro + narration 全文を Claude に渡し、**本編にある限定詞を intro が落として記述が
  不正確になっている箇所だけ**を高確信で報告させる。anti-hallucination の接地として
  `narration_evidence` に「その限定詞を含む本編の該当文の引用」を必須化する
  (本編に実在しない限定詞は報告できない = でっちあげ抑止)。

  ADVISORY 隔離: 呼び出し側は結果を report / 専用キーに置き、pipeline の blocking
  severity には混ぜない。人間が最終判断する (approach-A default)。correction は書かず
  「ここが疑わしい」の確認喚起に留める。

  graceful degrade: 空応答 / parse 失敗は status="UNAVAILABLE" (怖い偽 issue を出さない)。
  cache は intro + narration の hash に独立 (関係ないフィールド編集では再実行しない)。

刻印不要: intro と narration の現在値だけで判定するので、
出荷済み ep でも sidecar 無しでそのまま走る (後方互換の心配なし)。

Signal/noise (2026-07-25 に実 Opus で 27 shipped ep + planted 1 を calibrate):
  - 明白な FP = 0/27。25 ep はクリーン PASS。
  - recall: ある回 ゲーデルで本編にある『無矛盾な』欠落 (conf 0.95) を実発見。planted を検出しつつ同 ep の正版 ある回 は PASS = 1語違いのクリーン分離。
  - 加えて ある回 アーベルで『5次方程式の不可能性証明』の限定詞『代数的に(べき根で)/
    一般』欠落を borderline (conf 0.85) で surface。本編は正確形を述べつつ短縮ラベルも
    自ら使うので judgment call だが、 が名指しする『可解性の代数的に』クラスの正当な
    advisory (人間が最終判断)。 と同様、shipped の latent 精度問題を実発見した。
  anti-hallucination は保持: correction は書かず、narration_evidence の引用強制で
  本編に実在する限定詞のみに接地 (でっちあげ欠落を報告できない)。

照合: credits_generator.main (intro を概要欄に焼く当のステップ) + pipeline.verify_outputs
(最終 roll-up) + scripts/check_intro_semantic.py (standalone)。
"""

import hashlib
import os
import time

# 6-gram sibling が置かれている scene 走査ヘルパは qa_checker に無いので、
# ここでは自前で全 narration を平坦化する (依存を増やさない)。


def extract_narration(scene_def: dict) -> str:
    """全 scene の narration を「|」除去して連結した本文を返す。"""
    parts: list[str] = []
    sections = scene_def.get("sections", []) or []
    for section in sections:
        for scene in section.get("scenes", []) or []:
            narr = scene.get("narration", [])
            if isinstance(narr, str):
                narr = [narr]
            for line in narr or []:
                if isinstance(line, str):
                    parts.append(line.replace("|", ""))
    return " ".join(parts)


def intro_text(scene_def: dict) -> str:
    return (scene_def.get("description", {}) or {}).get("intro", "") or ""


def content_hash(scene_def: dict) -> str:
    """intro + narration の決定論 hash。どちらかが変われば cache 無効化。"""
    blob = intro_text(scene_def) + "\x1f" + extract_narration(scene_def)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_intro_semantic_prompt(scene_def: dict, subject: str = "") -> str:
    """narrow / advisory / anti-hallucination プロンプト.

    設計: 高確信の**限定詞欠落による不正確化**のみ報告する。
    要約による省略それ自体は問題にしない (詳細/人名/年号/背景の省略は正常)。
    correction は書かない (LLM は文言をでっちあげる)。確信なければ PASS。
    `narration_evidence` の引用を必須にして「本編に実在する限定詞」に接地する。
    """
    intro = intro_text(scene_def)
    narration = extract_narration(scene_def)
    subj = subject or "?"

    return f"""あなたは数学史動画「{subj}」の YouTube 概要欄 導入文 (description.intro) が、
本編ナレーションの数学的主張の**厳密さを損なわずに要約できているか**を検証する専門家です。

導入文は本編を短くまとめた「引き」なので、詳細・人名・年号・背景・比喩を省くのは
**まったく正常**です。あなたが探すのは唯一この一点だけ:

  **本編ナレーションが述べている数学的主張の「前提条件・限定詞」を、導入文が落とした
  ことで、導入文の記述が数学的に不正確 (誤り・誤解を招く) になっている箇所。**

該当しうる限定詞の例 (これに限らない):
  - 無矛盾性:「無矛盾な体系」の『無矛盾な』── 無矛盾でない体系は何でも証明でき、
    不完全性定理は成り立たない。落とすと主張が誤りになる。
  - 対象領域:「実数の無限」の『実数の』/「自然数の」── 領域が抜けると主張が空になる。
  - 手法・様式:「代数的に (べき根で) 解けない」の『代数的に』── 数値的には解けるので必須。
  - 関数・対象の性質:「連続な」「可微分な」「有界な」「正の」等。
  - 量化:「すべての」「ある」── 取り違えると別の命題になる。

# 検証対象
## 導入文 (description.intro)
{intro}

## 本編ナレーション (全文)
{narration}

# タスク
導入文の各文を本編と照合し、**上記のような限定詞が落ちて記述が不正確になっている**箇所
のみを、高い確信で報告してください。

# 重要な制約 (厳守)
- **要約による省略それ自体は問題ではありません。** 記述が依然として数学的に正しいなら
  報告しない。導入文が短いだけの省略 (詳細・人名・年号・固有名詞・背景・比喩) は報告しない。
- 導入文が本編とは別の**正しい**言い換えをしている場合は報告しない。
- **本編ナレーションに実在する限定詞についてのみ**報告してください。`narration_evidence`
  にその限定詞を含む本編の該当文を必ず引用すること。引用できないなら報告しない。
- **正しい文言を断定しないでください** (correction は書かない)。「この限定詞が抜けて
  不正確」という指摘と本編引用に留め、人間が最終判断する。
- 確信が持てなければ報告しない (precision 優先)。雑音を出すくらいなら PASS。

# 出力形式 (JSON のみ、JSON 以外のテキストは書かない)
```json
{{
  "status": "PASS" または "WARN",
  "issues": [
    {{
      "severity": "warning" または "info",
      "intro_quote": "導入文からの短い引用 (問題箇所)",
      "missing_qualifier": "落ちている限定詞 (例: 無矛盾な)",
      "narration_evidence": "本編でその限定詞を含む該当文の引用",
      "why_it_matters": "落とすと主張がどう不正確になるか (1文)",
      "confidence": 0.0-1.0
    }}
  ],
  "reviewed": true,
  "summary": "1-2文"
}}
```
- WARN = 高確信の欠落が1件以上。PASS = 報告なし。
- confidence < 0.7 の項目は原則 info。確証度の低いものは出さない。
- 出力は assistant の text ブロックに直接、ツールを使わず書いてください。
"""


def run_intro_semantic_check(
    scene_def: dict, episode_dir: str, subject: str = "", debug: bool = False
) -> dict:
    """ (F): advisory な narration -> intro 意味一致レビュー.

    Returns {status, issues, summary}. issues は ADVISORY -- severity は
    warning/info に cap し (critical にしない)、source-tag を付け、呼び出し側は
    blocking severity に混ぜない。空/parse 失敗は status="UNAVAILABLE" に degrade。
    intro が空 (guard 対象なし) なら PASS で即返す。
    """
    intro = intro_text(scene_def).strip()
    if not intro:
        return {"status": "PASS", "issues": [], "summary": "description.intro なし"}

    narration = extract_narration(scene_def).strip()
    if not narration:
        return {"status": "PASS", "issues": [], "summary": "narration なし (照合不能)"}

    from pre_script_fact_check import _load_cache, _save_cache, parse_fact_check_response

    cache_path = os.path.join(episode_dir, "_intro_semantic_cache.json")
    cache = _load_cache(cache_path)
    h = content_hash(scene_def)
    if cache.get("content_hash") == h and "report" in cache:
        print("  [intro-semantic] cache hit, skipping Claude call")
        report = cache["report"]
    else:
        print("  [intro-semantic] reviewing description.intro vs narration via Claude...")
        from claude_backend import call_claude

        prompt = build_intro_semantic_prompt(scene_def, subject)
        t0 = time.time()
        response = call_claude(
            prompt=prompt, model="opus", debug=debug, prefix="introsem", allowed_tools="Read"
        )
        elapsed = time.time() - t0
        print(f"  [intro-semantic] returned in {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        report = parse_fact_check_response(response)
        # Graceful degrade: parse_fact_check_response emits a synthetic critical
        # "internal" issue on empty/broken output. This review is advisory, so
        # treat that as UNAVAILABLE (do not surface a scary fake issue, do not
        # cache a failure) rather than a real finding.
        if any(i.get("field") == "internal" for i in report.get("issues", [])):
            print("  [intro-semantic] unavailable (empty/parse failure) -- advisory skipped")
            return {
                "status": "UNAVAILABLE",
                "issues": [],
                "summary": "intro semantic review unavailable (empty/parse failure)",
            }
        _save_cache(
            cache_path,
            {
                "content_hash": h,
                "report": report,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    # Advisory hardening: cap any critical to warning, tag source.
    for issue in report.get("issues", []):
        if issue.get("severity") == "critical":
            issue["severity"] = "warning"
        issue.setdefault("source", "claude_intro_semantic")
    return report


def read_cached_report(scene_def: dict, episode_dir: str) -> dict | None:
    """`_intro_semantic_cache.json` に現 intro+narration と一致する report があれば
    返す (Claude を呼ばない)。cache 無し / stale (内容が変わった) / 空 intro なら None。

    pipeline.verify_outputs の最終 roll-up 用: 高い Claude 呼び出しは credits step が
    済ませておき、verify は cache を読むだけにして安価に保つ。"""
    from pre_script_fact_check import _load_cache

    if not intro_text(scene_def).strip():
        return None
    cache = _load_cache(os.path.join(episode_dir, "_intro_semantic_cache.json"))
    if cache.get("content_hash") == content_hash(scene_def) and "report" in cache:
        return cache["report"]
    return None


def format_report(report: dict) -> str:
    """人が読む 1-block サマリ (standalone / pipeline WARN 用)。"""
    status = report.get("status", "?")
    issues = report.get("issues", [])
    if status == "UNAVAILABLE":
        return "  [intro-semantic] UNAVAILABLE (Claude 応答なし/parse 失敗) -- advisory skip"
    if not issues:
        return f"  [intro-semantic] {status}: 限定詞欠落なし ({report.get('summary', '')})"
    lines = [
        f"  [intro-semantic] {status}: {len(issues)} 件の限定詞欠落候補 (advisory, 要 human 確認)"
    ]
    for i in issues:
        mq = i.get("missing_qualifier", "?")
        iq = i.get("intro_quote", "")
        conf = i.get("confidence", "?")
        lines.append(f"    - 欠落『{mq}』(conf {conf}) intro:「{iq[:50]}」")
        why = i.get("why_it_matters", "")
        if why:
            lines.append(f"        理由: {why[:90]}")
    return "\n".join(lines)
