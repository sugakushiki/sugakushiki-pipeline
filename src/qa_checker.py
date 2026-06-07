"""
qa_checker.py — マルチエージェント品質チェッカー

パイプラインの各工程にLLMエージェントによる品質チェックゲートを設置する。
Gate 1（スクリプトQA）を実装。Gate 2-4 は将来拡張。

使い方:
    # 全エージェント実行
    python src/qa_checker.py episodes/001_erdos/scene_definition.json --gate script

    # 特定エージェントのみ
    python src/qa_checker.py episodes/001_erdos/scene_definition.json --gate script --agents fact,style

    # クイックモード（Sonnetエージェントのみ）
    python src/qa_checker.py episodes/001_erdos/scene_definition.json --gate script --quick

    # デバッグ
    python src/qa_checker.py episodes/001_erdos/scene_definition.json --gate script --debug
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# claude_backend.py と同じディレクトリにある想定
sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_backend import call_claude, extract_json_from_response, find_project_root

# ============================================================
# Gemini API バックエンド（Grounding対応）
# ============================================================


def call_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    debug: bool = False,
    project_root: str = None,
) -> str:
    """
    Gemini API を直接呼び出す（Grounding = Web検索付き）。
    image_generator.py と同じ .env → GOOGLE_API_KEY パターン。
    """
    import urllib.error
    import urllib.request

    root = Path(project_root) if project_root else find_project_root()

    # .env から API キー読み込み
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        env_path = root / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GOOGLE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found in environment or .env")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )

    # Grounding（Google Search）を有効化
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    if debug:
        print(f"[DEBUG] Gemini model: {model}")
        print(f"[DEBUG] Prompt length: {len(prompt)} chars")

    start = time.time()
    print(f"  Gemini API ({model}, Grounding) を呼び出し中...")

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {e.code}: {body[:500]}") from e

    elapsed = time.time() - start
    print(f"  完了 ({elapsed:.1f}秒)")

    # レスポンスからテキスト抽出
    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {json.dumps(result)[:500]}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p["text"] for p in parts if "text" in p]

    return "\n".join(text_parts)


# ============================================================
# 自動修正機能
# ============================================================


def apply_auto_fixes(
    scene_definition: dict,
    qa_report: dict,
    max_fixes: int = 5,
) -> tuple:
    """
    QAレポートの issues から自動修正可能なものを scene_definition に適用する。

    Returns:
        (modified_scene_definition, applied_fixes_list)
    """
    import copy

    sd = copy.deepcopy(scene_definition)
    applied = []

    # シーンのnarrationをscene_idでインデックス化
    # (section_idx, scene_idx) のタプルでアクセスパスを保持
    scene_map = {}
    for si, section in enumerate(sd.get("sections", [])):
        for sci, scene in enumerate(section.get("scenes", [])):
            scene_map[scene.get("scene_id", "")] = (si, sci)

    # フラット構造のフォールバック
    if not scene_map:
        for i, scene in enumerate(sd.get("scenes", [])):
            scene_map[scene.get("scene_id", "")] = i

    for agent_key, agent_result in qa_report.get("agents", {}).items():
        issues = agent_result.get("issues", agent_result.get("improvements", []))

        for issue in issues:
            if len(applied) >= max_fixes:
                break

            severity = issue.get("severity", "info")
            suggestion = issue.get("suggestion")
            scene_id = issue.get("scene_id")

            # 自動修正対象: severity=warning以上、suggestion がある、scene_id が特定できる
            if not suggestion or severity == "info":
                continue

            # スタイル修正（禁止表現の置換など）
            if agent_key == "style" and scene_id and scene_id in scene_map:
                loc = scene_map[scene_id]

                # sections構造
                if isinstance(loc, tuple):
                    si, sci = loc
                    narr = sd["sections"][si]["scenes"][sci].get("narration", [])
                else:
                    narr = sd["scenes"][loc].get("narration", [])

                location = issue.get("location", "")

                if location and len(location) < 30 and len(suggestion) < 60:
                    # narrationが配列の場合、各要素を検索
                    if isinstance(narr, list):
                        for ni, line in enumerate(narr):
                            if location in line:
                                if isinstance(loc, tuple):
                                    sd["sections"][loc[0]]["scenes"][loc[1]]["narration"][ni] = (
                                        line.replace(location, suggestion, 1)
                                    )
                                else:
                                    sd["scenes"][loc]["narration"][ni] = line.replace(
                                        location, suggestion, 1
                                    )
                                applied.append(
                                    {
                                        "agent": agent_key,
                                        "scene_id": scene_id,
                                        "original": location,
                                        "replacement": suggestion,
                                        "reason": issue.get("detail", ""),
                                    }
                                )
                                break

            # ファクトチェック修正は自動適用しない（リスクが高い）
            # → レポートに「要手動確認」として残す

    return sd, applied


# ============================================================
# エージェント定義
# ============================================================

AGENTS = {
    "fact": {
        "name": "FactChecker",
        "model": "opus",
        "backend": "claude",  # "claude" or "gemini"
        "description": "事実の正確性検証",
    },
    "fact_grounding": {
        "name": "FactChecker (Gemini Grounding)",
        "model": "gemini-2.5-flash",
        "backend": "gemini",
        "description": "Web検索付き事実検証（Gemini Grounding）",
    },
    "style": {
        "name": "StyleChecker",
        "model": "sonnet",
        "backend": "claude",
        "description": "STYLE_GUIDE準拠チェック",
    },
    "source": {
        "name": "SourceManager",
        "model": "sonnet",
        "backend": "claude",
        "description": "参考文献リスト生成",
    },
    "content": {
        "name": "ContentReviewer",
        "model": "opus",
        "backend": "claude",
        "description": "構成・尺感・わかりやすさの評価",
    },
    "consistency": {
        "name": "ConsistencyChecker",
        "model": "opus",
        "backend": "claude",
        "description": "用語統一・トーン一貫性チェック",
    },
}

# クイックモードで実行するエージェント（Sonnetのみ）
QUICK_AGENTS = ["style", "source"]


# ============================================================
# プロンプト生成
# ============================================================


def _build_fact_checker_prompt(narration_text: str, episode_config: dict) -> str:
    """Agent 1: FactChecker プロンプト"""
    # mathematician can be string or dict
    math_field = episode_config.get("mathematician", "不明")
    if isinstance(math_field, dict):
        subject = math_field.get("name", "不明")
    else:
        subject = str(math_field)

    return f"""あなたは数学史の事実検証の専門家です。
以下のナレーション原稿に含まれる事実主張を検証してください。

# 対象人物
{subject}

# ナレーション原稿
---
{narration_text}
---

# タスク

ナレーション中の検証可能な事実主張をすべて抽出し、あなたの知識に基づいて正確性を評価してください。

チェック項目:
1. 年号・日付（生年月日、死亡日、受賞年、事件の年など）
2. 人名・地名の正確性
3. 数値データ（論文数、共著者数、統計値など）
4. エピソードの真偽（逸話が文献に基づいているか）
5. 因果関係の正確性

# 出力形式

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

```json
{{
  "status": "PASS" または "WARN" または "FAIL",
  "issues": [
    {{
      "severity": "critical" または "warning" または "info",
      "scene_id": "該当するscene_id（特定できない場合は null）",
      "claim": "検証対象の主張（原文から引用）",
      "finding": "検証結果の説明",
      "suggestion": "修正提案（問題がない場合は null）",
      "confidence": 0.0から1.0の数値（あなたの判断への確信度）
    }}
  ],
  "verified_facts_count": 検証した事実の総数,
  "summary": "全体の評価を1-2文で"
}}
```

判定基準:
- PASS: critical=0, warning≤1
- WARN: critical=0, warning≥2
- FAIL: critical≥1

## severity判定ルール（厳守）

- **critical**: 年号が2年以上ズレている / 人名の間違い / 因果関係の逆転 / 存在しないエピソードの捏造
- **warning**: 年号が1年ズレている / 数値データが10%以上異なる / エピソードの細部が不正確 / confidence 0.5-0.7の不確かな主張 / 同一事実の記述が複数箇所で矛盾している場合、どちらが正しいか（または両方誤りか）を明示すること
- **info**: 表現の曖昧さ（「約」「頃」で許容される範囲）/ confidence < 0.5で判断不能 / 検証不能だが問題なさそうな逸話

★重要: スクリプト内で同一事実が異なる形で記述されている場合（例:「スーツケースひとつ」と「スーツケース半分」）、一貫性の問題に加えて「文献上どちらが正しいか」を調査し、正しい記述を suggestion に含めてください。

上記ルールは必ず守ってください。迷った場合はwarning寄りに判定してください。
事実が正確な場合は issues に含めないでください（問題のある主張のみ報告）。"""


def _build_style_checker_prompt(narration_text: str, style_guide: str) -> str:
    """Agent 2: StyleChecker プロンプト"""
    return f"""あなたはYouTubeチャンネル「数学史記」のスタイル監修者です。
以下のナレーション原稿が、スタイルガイドに準拠しているかチェックしてください。

# スタイルガイド
---
{style_guide}
---

# ナレーション原稿
---
{narration_text}
---

# チェック項目

1. **禁止表現の検出**: 「ヤバい」「すごすぎる」「衝撃」等の煽り語が含まれていないか
2. **感嘆符の数**: 1スクリプトに2-3回まで（実際の数をカウント）
3. **文体の一貫性**: ですます調で統一されているか。である調（「〜である」「〜だった」「〜していた」「〜された」「〜なかった」「〜ている。」）が混在していないか。会話の引用内は例外
4. **数学者の描写トーン**: 敬意はあるが神格化していないか。失敗や人間的弱さも描いているか
5. **数学の説明スタンス**: 数式を「導出する」のではなく「意味を語る」スタンスになっているか
6. **温度感**: 「賢い友人が居酒屋で熱く語っている」くらいの温度感か
7. **サイモン・シン的語り口**: 抑制的で品があり、事実の積み重ねで感動を生むスタイルか

# 出力形式

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

```json
{{
  "status": "PASS" または "WARN" または "FAIL",
  "exclamation_count": 感嘆符の実数,
  "issues": [
    {{
      "severity": "critical" または "warning" または "info",
      "category": "prohibited_expression" / "exclamation" / "tone" / "math_description" / "deification" / "inconsistency",
      "location": "問題箇所の引用（短く）",
      "detail": "何が問題か",
      "suggestion": "修正案"
    }}
  ],
  "positive_notes": ["スタイルガイドに合致している良い点を1-3個"],
  "summary": "全体の評価を1-2文で"
}}
```

判定基準:
- PASS: critical=0, warning≤1
- WARN: critical=0, warning≥2
- FAIL: critical≥1（禁止表現が複数 or 全体的にトーンが逸脱）

## severity判定ルール（厳守）

- **critical**: 禁止表現リスト（「ヤバい」「すごすぎる」「衝撃」等）の使用 / 感嘆符が4個以上 / 全体的にYouTuber的な煽りトーン
- **warning**: 禁止表現に準ずる煽り語（「驚異的」「天才すぎる」「信じられない」等）の使用 / 3シーン以上連続で神格化トーンが弱さの描写なく続く / 文体の急変（敬語↔タメ口の混在）/ である調の混在（「〜だった」「〜された」「〜していた」等がですます調の中に出現）
- **info**: 「驚くほど」等の軽微な強調表現 / 神格化トーンが2シーン以内で直後にバランスが取れている / 温度感の微調整提案

禁止表現リストにない語でも、煽りの意図が明確な場合はwarningとしてください。"""


def _build_source_manager_prompt(narration_text: str, episode_config: dict) -> str:
    """Agent 3: SourceManager プロンプト"""
    # mathematician can be string or dict
    math_field = episode_config.get("mathematician", "不明")
    if isinstance(math_field, dict):
        subject = math_field.get("name", "不明")
    else:
        subject = str(math_field)

    return f"""あなたは学術参考文献の専門家です。
以下のナレーション原稿の内容から、参考文献リストを推定し、YouTube概要欄用のテキストを生成してください。

# 対象人物
{subject}

# ナレーション原稿
---
{narration_text}
---

# タスク

1. ナレーションで言及されている事実・エピソードの出典となりうる文献を推定
2. YouTube概要欄用のフォーマット済みテキストを生成
3. 典拠が不明な主張があればフラグ

# 参考文献の記載方針（STYLE_GUIDE準拠）

```
【主要参考文献】
- 著者名, "書名" (出版年)
- ウェブサイト名 (URL)

【データ出典】
- データ名：出典元

【映像素材】
- 地図データ：Natural Earth（パブリックドメイン）
- 音声合成：VOICEVOX:青山龍星
```

# 出力形式

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

```json
{{
  "status": "PASS",
  "references": {{
    "books": [
      {{"author": "著者名", "title": "書名", "year": "出版年", "relevance": "ナレーションとの関連"}}
    ],
    "websites": [
      {{"name": "サイト名", "url": "URL（推定）", "relevance": "関連"}}
    ],
    "data_sources": [
      {{"data": "データ名", "source": "出典元"}}
    ]
  }},
  "youtube_description_text": "概要欄用のフォーマット済みテキスト（改行含む）",
  "unsourced_claims": [
    {{
      "claim": "典拠不明な主張",
      "suggestion": "推定される出典 or 要調査",
      "severity": "critical" または "warning" または "info"
    }}
  ],
  "summary": "全体の評価を1-2文で"
}}
```

## severity判定ルール（厳守）

- **critical**: ナレーションの核となる主張（数学的業績、主要エピソード）に出典が全く推定できない
- **warning**: 具体的な数値・日付・引用を含む主張で、出典が単一の二次資料にしか見つからない / 伝記的逸話で一次資料の特定が困難
- **info**: 一般的に知られた事実で出典の明示が不要 / 推定出典に高い信頼性がある

判定基準:
- PASS: critical=0, warning≤2
- WARN: critical=0, warning≥3、またはunsourced_claimsが3件以上
- FAIL: critical≥1"""


def _build_content_reviewer_prompt(
    narration_text: str, scene_definition: dict, episode_config: dict = None
) -> str:
    """Agent 4: ContentReviewer プロンプト"""

    # シーン構成の概要を作る
    scenes_summary = []
    all_scenes = _get_all_scenes(scene_definition)
    for scene in all_scenes:
        sid = scene.get("scene_id", "?")
        vtype = scene.get("visual", {}).get("type", "?")
        narr = scene.get("narration", [])
        narr_len = sum(len(t) for t in narr) if isinstance(narr, list) else len(narr)
        scenes_summary.append(f"  {sid}: {vtype} ({narr_len}字)")
    scenes_text = "\n".join(scenes_summary)

    total_chars = _count_narration_chars(scene_definition)
    scene_count = len(all_scenes)

    # Target duration: read from episode_config (explicit) or scene_def metadata
    target_min = None
    if episode_config:
        target_min = episode_config.get("target_duration_minutes")
    if target_min is None:
        target_min = scene_definition.get("metadata", {}).get("target_duration_minutes")
    if target_min is None:
        target_min = 10  # legacy default for old episodes without the field

    # Allow ±15% tolerance around the configured target
    target_low = max(1, int(round(target_min * 0.85)))
    target_high = int(round(target_min * 1.15))
    target_chars_low = target_low * 290
    target_chars_high = target_high * 290

    return f"""あなたはYouTubeドキュメンタリーのコンテンツプロデューサーです。
以下のナレーション原稿を、コンテンツとしての完成度の観点から多角的に評価してください。

# チャンネル情報
- チャンネル名: 数学史記
- ジャンル: 数学の歴史ドキュメンタリー（日本語）
- ターゲット: 数学好き、エンジニア・データサイエンティスト
- 目標尺: {target_min}分（許容範囲 {target_low}〜{target_high}分 = 約{target_chars_low}〜{target_chars_high}字、290字/分換算）
- 参考トーン: サイモン・シン『フェルマーの最終定理』

# シーン構成（{scene_count}シーン、合計{total_chars}字）
{scenes_text}

# ナレーション原稿
---
{narration_text}
---

# 評価項目

以下の5軸で評価してください（各A-E、Aが最高）:

1. **フック（導入の引き込み力）**: 最初の30秒で視聴者が「続きを見たい」と思えるか
2. **ナラティブアーク**: 感情の起伏が適切か。平坦すぎないか、逆に起伏が激しすぎないか
3. **数学パートの密度**: 詰め込みすぎていないか。直感的に理解できるか
4. **ターゲット訴求力**: 数学好き・エンジニア層が「面白い」と感じるか
5. **リテンション（継続視聴）**: 途中で離脱されそうなポイントはないか

# 出力形式

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

```json
{{
  "status": "PASS" または "WARN" または "FAIL",
  "ratings": {{
    "hook": {{"grade": "A-E", "comment": "評価コメント"}},
    "narrative_arc": {{"grade": "A-E", "comment": "評価コメント"}},
    "math_density": {{"grade": "A-E", "comment": "評価コメント"}},
    "target_appeal": {{"grade": "A-E", "comment": "評価コメント"}},
    "retention": {{"grade": "A-E", "comment": "評価コメント"}}
  }},
  "overall_grade": "A-E",
  "strengths": ["良い点を2-3個"],
  "improvements": [
    {{
      "severity": "critical" または "warning" または "info",
      "category": "hook" / "narrative" / "math" / "pacing" / "retention",
      "detail": "具体的な改善提案",
      "scene_id": "該当シーン（あれば）"
    }}
  ],
  "estimated_viewer_retention_curve": "序盤/中盤/終盤の想定視聴維持率を簡潔に",
  "summary": "全体の評価を2-3文で"
}}
```

判定基準:
- PASS: overall_grade が A or B、critical=0
- WARN: overall_grade が C、または critical=0 で warning≥2
- FAIL: overall_grade が D or E、または critical≥1

## グレード基準（厳守）

- **A**: 公開可能な品質。このまま動画にして問題ない
- **B**: 軽微な改善で公開可能。1-2箇所の微調整で済む
- **C**: 構成や内容に改善の余地がある。パートの追加・削除が必要
- **D**: 大幅な書き直しが必要。構成が破綻している or 数学パートが理解不能
- **E**: 使用不可。テーマから逸脱している or 事実誤認が多すぎる

## improvements の severity判定ルール（厳守）

- **critical**: 視聴者が離脱する明確なポイントがある / 数学パートが専門家にしか理解できない / フックが機能していない（最初の30秒で興味を引けない）
- **warning**: ナラティブアークに弱い部分がある / ペーシングが一部不均一 / ターゲット層の一部にしか刺さらない
- **info**: 微調整でさらに良くなる提案 / 代替案の提示"""


def _build_consistency_checker_prompt(
    narration_text: str,
    scene_definition: dict,
    existing_episodes: list = None,
) -> str:
    """Agent 5: ConsistencyChecker プロンプト"""

    existing_context = ""
    if existing_episodes:
        existing_context = "\n# 既存エピソードの情報\n"
        for ep in existing_episodes:
            existing_context += f"\n## {ep['id']}\n{ep['summary']}\n"
    else:
        existing_context = "\n（これが最初のエピソードのため、クロスエピソードチェックは省略）\n"

    return f"""あなたはコンテンツの一貫性を検証する品質管理の専門家です。
以下のナレーション原稿のエピソード内一貫性と、既存エピソードとの整合性をチェックしてください。

# ナレーション原稿
---
{narration_text}
---
{existing_context}

# チェック項目

## エピソード内の一貫性
1. **人物呼称の統一**: 同一人物の呼び方が一貫しているか（例:「エルデシュ」と「パウル」の使い分け）
2. **用語の統一**: 同一概念に対して異なる用語を使っていないか
3. **トーンの変動**: シーン間で急にトーンが変わっていないか（突然感傷的になる等）
4. **時系列の整合性**: シーンの時系列が矛盾していないか

## クロスエピソード整合性（既存エピソードがある場合のみ）
5. 他エピソードで言及済みの人物の紹介に矛盾はないか
6. 用語辞書（エルデシュ数、ベルトランの仮説 等）の表記が統一されているか

# 出力形式

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

```json
{{
  "status": "PASS" または "WARN" または "FAIL",
  "terminology_map": {{
    "人物名": ["使用されている呼称のリスト"],
    "概念名": ["使用されている用語のリスト"]
  }},
  "issues": [
    {{
      "severity": "critical" または "warning" または "info",
      "category": "naming" / "terminology" / "tone" / "timeline" / "cross_episode",
      "detail": "問題の説明",
      "location": "該当箇所",
      "suggestion": "修正案"
    }}
  ],
  "timeline_check": "時系列が正しいかの簡潔な評価",
  "summary": "全体の評価を1-2文で"
}}
```

判定基準:
- PASS: critical=0, warning≤1
- WARN: critical=0, warning≥2
- FAIL: critical≥1（時系列矛盾 or 重大な用語不統一）

## severity判定ルール（厳守）

- **critical**: 時系列の矛盾（AがBより前に起きたと書いてあるが、日付が逆）/ 同一事実の数値が矛盾（「論文1500本」と「論文1475本」）
- **warning**: 同一の具体的な事物・状況に対して矛盾する記述がある（例:「スーツケースひとつ」と「スーツケース半分」/ 「3歳で」と「4歳で」同じ出来事を指す場合）/ 同一概念に2つ以上の異なる用語が混在（「共著者」と「協力者」を混用）/ 呼称が意図なく揺れている / 数学的に非同値な表現の混用（「509人を超える」は510人以上を意味し「509人以上」とは異なる — これは数学チャンネルとして看過できない）
- **info**: トーンの微小な変動で内容に影響しないもの

★重要ルール:
1. 同一の具体的事物に対する記述の食い違い（数量、呼称、状態）は、文脈上の自然さに関わらず必ず **warning以上** としてください。「意味的に近い」「文脈上許容される」という理由でinfoに格下げしないでください。
2. 呼称の揺れ（例: 幼少期のみファーストネーム使用）は、scene_definitionのnotesフィールド等に意図が明記されていない限り **warning** としてください。LLMが「意図的なスタイル選択だろう」と推測してinfoにしないでください。
3. 数学的表現の厳密性に注意してください。「超える」（strictly greater than）と「以上」（greater than or equal to）は異なります。数学史チャンネルとして数学的表現の不正確な混用は必ず **warning** です。
4. 一貫性の問題と事実の問題を区別してください。「スーツケースひとつ」vs「スーツケース半分」のような場合、一貫性の問題（統一されていない）に加えて「どちらが事実か」という問題もあります。factual accuracy に関わる場合はその旨を明記してください。"""


# ============================================================
# エージェント実行
# ============================================================


def extract_narration_text(scene_definition: dict) -> str:
    """scene_definition.json からナレーション全文を抽出

    構造: sections[] → scenes[] → narration[]（文字列の配列）
    """
    narrations = []

    for scene in _get_all_scenes(scene_definition):
        sid = scene.get("scene_id", "unknown")
        narr_list = scene.get("narration", [])
        if isinstance(narr_list, list) and narr_list:
            narr_text = "\n".join(narr_list)
            narrations.append(f"[{sid}]\n{narr_text}")
        elif isinstance(narr_list, str) and narr_list:
            narrations.append(f"[{sid}]\n{narr_list}")

    return "\n\n".join(narrations)


def _detect_description_drift(scene_definition: dict) -> list:
    """description.intro vs narration の 6-gram coverage 検査.

    description.intro は script step で config.description.intro_guidance から
    生成され、その後 narration を編集しても自動同期されない。ある回 で
    「古代の三大難問」が narration では「古代ギリシャの三大難問」に統一
    されたが description.intro が古いまま残った事例で発覚 (description.txt
    にもそのまま反映され YouTube 概要欄に出てしまう)。

    検出方法: description.intro 内の連続 CJK 部分文字列 (kanji + kana) から
    6-gram を抽出し、narration 全体テキストに存在しないものを drift 候補と
    して info-level で報告。意図的な言い換えなら無視可能、用語ゆれなら同期。
    """
    import re as _re

    desc = scene_definition.get("description", {}).get("intro", "")
    if not desc:
        return []

    narr_parts = []
    for scene in _get_all_scenes(scene_definition):
        for line in scene.get("narration", []) or []:
            if isinstance(line, str):
                narr_parts.append(line.replace("|", ""))
    narr_text = " ".join(narr_parts)

    cjk_re = _re.compile(r"[一-鿿ぁ-んァ-ヶー]+")
    issues = []
    reported = set()
    for chunk in cjk_re.findall(desc):
        if len(chunk) < 6:
            continue
        # 6-gram 単位で coverage 検査 (false positive を抑える長さ)
        for i in range(len(chunk) - 5):
            gram = chunk[i : i + 6]
            if gram in reported:
                continue
            if gram not in narr_text:
                reported.add(gram)
                issues.append(
                    {
                        "severity": "info",
                        "scene_id": "description.intro",
                        "claim": (
                            f"description.intro 6-gram '{gram}' が "
                            f"narration に存在しない (drift 候補)"
                        ),
                        "finding": (
                            "narration を編集した後 description.intro が古い"
                            "ままの可能性。意図的な言い換えなら無視、"
                            "用語ゆれなら同期推奨。"
                        ),
                        "suggestion": (
                            "scene_definition.description.intro を narration"
                            "の表現に合わせて更新 (credits step で "
                            "description.txt に反映される)"
                        ),
                    }
                )
                break  # 1 chunk あたり最初の miss のみ報告 (noise 抑制)
    return issues


def run_dearu_lint(scene_definition: dict) -> dict:
    """Deterministic である調 detector.

    LLM StyleChecker は run 間で揺れ、ある回 で である調 5 件中 2 件を見逃した
    (`した。`/`ない。` pattern が盲点)。は hard rule なので、非決定的 LLM の補完として正規表現で確実に候補を列挙する
    (layered defense)。`『...』` 引用内 は
    info、本文の である調終止は warning。最終判断は人間 (鵜呑み禁止)。

    Returns: agent-result 互換 dict (status / issues / summary / _agent)。
    """
    import re as _re

    # である調 文末終止形 (longest-first は不要、個別 search)。
    # 否定先読みで ですます系活用 (ました/でした/ません/です 等) を除外。
    patterns = [
        _re.compile(r"(?<![ま])する。"),
        _re.compile(r"(?<![ま])なる。"),
        _re.compile(r"(?<![ま])られる。"),
        _re.compile(r"(?<![ま])える。"),
        _re.compile(r"(?<![ま])うる。"),
        _re.compile(r"(?<![で])ある。"),
        _re.compile(r"(?<![ま])だ。"),
        _re.compile(r"である。"),
        _re.compile(r"(?<![まで])した。"),
        _re.compile(r"(?<![ま])った。"),
        _re.compile(r"(?<![ま])ない。"),
    ]

    issues = []
    for scene in _get_all_scenes(scene_definition):
        sid = scene.get("scene_id", "unknown")
        narr_list = scene.get("narration", [])
        if isinstance(narr_list, str):
            narr_list = [narr_list]
        for idx, raw in enumerate(narr_list):
            if not isinstance(raw, str):
                continue
            text = raw.replace("|", "")
            # 『...』 引用スパン (修辞的提示は許容 → info)
            quote_spans = [
                (m.start(), m.end()) for m in _re.finditer(r"『[^』]*』", text)
            ]
            seen = set()
            for pat in patterns:
                for m in pat.finditer(text):
                    pos = m.start()
                    if pos in seen:
                        continue
                    seen.add(pos)
                    in_quote = any(s <= pos < e for s, e in quote_spans)
                    ctx_s = max(0, pos - 18)
                    ctx_e = min(len(text), m.end() + 3)
                    excerpt = text[ctx_s:ctx_e]
                    issues.append(
                        {
                            "severity": "info" if in_quote else "warning",
                            "scene_id": sid,
                            "claim": f"{sid}[{idx}] である調終止候補: …{excerpt}",
                            "finding": (
                                "『』引用内の修辞的提示 (古代視点等)。意図的なら許容、"
                                "本文化するなら ですます化"
                                if in_quote
                                else "ですます調の中に である調終止が混在 (CLAUDE.md "
                                "スクリプト規約違反候補)。引用・体言止めの意図が "
                                "scene notes に無ければ ですます化"
                            ),
                            "suggestion": (
                                "文末を「〜です／〜ます／〜のです」等に統一。"
                                "意図的引用なら『』で囲み notes に明記"
                            ),
                        }
                    )

    warn = sum(1 for i in issues if i["severity"] == "warning")
    info = sum(1 for i in issues if i["severity"] == "info")
    if warn > 0:
        status = "WARN"
    else:
        status = "PASS"
    summary = (
        f"決定論 である調 検出: warning {warn} 件 / info {info} 件 "
        f"(『』引用内は info)。LLM StyleChecker の盲点補完。0 件なら ですます調統一。"
    )

    # Day 18 強化 D: description.intro drift lint も併走して issues に append。
    # 軽量 deterministic 6-gram coverage 検査で description.intro と narration の
    # 用語ゆれを検出。
    # info-level のみ、dearu_lint の status には影響しない。
    drift_issues = _detect_description_drift(scene_definition)
    info += len(drift_issues)
    issues.extend(drift_issues)
    if drift_issues:
        summary += f" / description.intro drift {len(drift_issues)} 件 (info)"

    # Day 19 強化 D: temporal ordering lint
    # 同一文中に年号が複数登場する場合、出現順と数値順の不一致を WARN として検出。
    # ある回「コーシーが1821年に始め、ボルツァーノが1817年に独立して着想していた」
    # のように年代倒錯した文 (1821 → 1817 順) は文法的には正しいが音声で誤解しやすい。
    # LLM ConsistencyChecker は「時系列いずれも一貫」と判定し見逃した盲点。
    temporal_issues = _detect_temporal_ordering(scene_definition)
    info += len(temporal_issues)
    issues.extend(temporal_issues)
    if temporal_issues:
        summary += f" / temporal-ordering {len(temporal_issues)} 件 (info)"

    return {
        "_agent": "dearu_lint",
        "_model": "deterministic-regex",
        "_duration_sec": 0.0,
        "status": status,
        "issues": issues,
        "summary": summary,
    }


def _detect_temporal_ordering(scene_definition: dict) -> list:
    """Day 19 強化 D: 同一文中の年号倒錯を検出。

    ある回 N[3]「コーシーが1821年に始め、ボルツァーノが1817年に独立して
    着想していた厳密化を、ヴァイエルシュトラスは…」型の文では、出現順 (1821 →
    1817) と数値順 (1817 < 1821) が逆。文法的には「着想していた」(過去完了) で
    時系列を保持するが、音声で聴くと先に「1821 で始めた」を聞いて Cauchy 先行と
    誤解されやすい。

    QA Gate 1 の LLM ConsistencyChecker は「時系列いずれも一貫」と判定 → 見逃し。
    Deterministic な regex で同一文中の年号出現順を抽出 → 数値順と比較。

    severity:
        info: 年号倒錯のみ検出 (誤解リスク提示、修正は人間判断)

    検出ロジック:
        1. 各 narration line を「、」「。」で分割せず単一文として扱う
        2. (西暦|紀元前) 数字 年 を抽出して appearance_order に並べる
        3. numeric_order と比較、一致しなければ WARN
        4. 「ていた」「ていました」過去完了形が直後にあれば severity 下げる
    """
    import re as _re

    # 西暦年号 (1000-2999) を抽出。「1817年」「1821年」等。
    # 紀元前 (前N世紀, 前N年, 紀元前N) はスキップ (BCE は数値が小さいほど後代で
    # 逆順、扱いが異なる)
    YEAR_PAT = _re.compile(r"(?<![\d一-鿿])(1[0-9]{3}|20[0-9]{2})年")

    # 過去完了マーカー (年代倒錯を緩和する文法手がかり)
    PAST_PERFECT_HINTS = [
        "ていた", "ていました", "ていたが", "ていたものの",
        "していた", "していました",
    ]

    issues = []
    for scene in _get_all_scenes(scene_definition):
        sid = scene.get("scene_id", "unknown")
        narr_list = scene.get("narration", [])
        if isinstance(narr_list, str):
            narr_list = [narr_list]
        for idx, raw in enumerate(narr_list):
            if not isinstance(raw, str):
                continue
            text = raw.replace("|", "")
            # 句点で分割、各句を独立に検査
            for sentence in _re.split(r"[。！？]", text):
                if not sentence.strip():
                    continue
                years_with_pos = [
                    (m.start(), int(m.group(1)))
                    for m in YEAR_PAT.finditer(sentence)
                ]
                if len(years_with_pos) < 2:
                    continue
                # 出現順 (= positions のまま) vs 数値順
                numeric_order = sorted(years_with_pos, key=lambda p: p[1])
                if numeric_order == years_with_pos:
                    continue  # 出現順 == 数値順、OK
                # 倒錯あり: 過去完了 hint で severity を下げる
                has_past_perfect = any(h in sentence for h in PAST_PERFECT_HINTS)
                severity = "info" if has_past_perfect else "warning"
                appearance = ", ".join(f"{y}年" for _, y in years_with_pos)
                expected = ", ".join(f"{y}年" for _, y in numeric_order)
                hint_note = (
                    " (「ていた」過去完了で時系列保持あり、音声で誤解リスクのみ)"
                    if has_past_perfect else ""
                )
                excerpt = sentence.strip()[:80]
                issues.append({
                    "severity": severity,
                    "scene_id": sid,
                    "claim": f"{sid}[{idx}] 年代倒錯: {excerpt}",
                    "finding": (
                        f"出現順 [{appearance}] が数値順 [{expected}] と"
                        f"一致しない{hint_note}。音声視聴で先発・後発の関係が"
                        f"逆に誤解される可能性"
                    ),
                    "suggestion": (
                        "出現順を数値順に揃える (例: 1817年 → 1821年 → ...)。"
                        "または「先んじて」「先に」等の時系列マーカーを追加"
                    ),
                })

    return issues


def _get_all_scenes(scene_definition: dict) -> list:
    """sections[].scenes[] または flat scenes[] からシーン一覧を取得"""
    scenes = []
    # Structure A: sections[].scenes[]
    for section in scene_definition.get("sections", []):
        scenes.extend(section.get("scenes", []))
    # Structure B: flat scenes[]
    if not scenes:
        scenes = scene_definition.get("scenes", [])
    return scenes


def _count_narration_chars(scene_definition: dict) -> int:
    """ナレーション合計文字数を計算"""
    total = 0
    for scene in _get_all_scenes(scene_definition):
        narr = scene.get("narration", [])
        if isinstance(narr, list):
            total += sum(len(t.replace("|", "")) for t in narr)
        elif isinstance(narr, str):
            total += len(narr.replace("|", ""))
    return total


def load_style_guide(project_root: Path) -> str:
    """STYLE_GUIDE.md を読み込む"""
    # 複数の候補パスを試す (docs 再編成で 03_quality/ 配下に移動済)
    candidates = [
        project_root / "docs" / "03_quality" / "STYLE_GUIDE.md",
        project_root / "docs" / "STYLE_GUIDE.md",
        project_root / "STYLE_GUIDE.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")

    # 明示パスが全滅でも docs/ 以下を再帰探索 (将来の再編成耐性)
    docs_dir = project_root / "docs"
    if docs_dir.is_dir():
        for found in sorted(docs_dir.rglob("STYLE_GUIDE.md")):
            return found.read_text(encoding="utf-8")

    print("  [WARN] STYLE_GUIDE.md が見つかりません。スキップします。")
    return "(STYLE_GUIDE.md not found)"


def load_episode_config(scene_def_path: Path) -> dict:
    """episode_config.json を読み込む"""
    episode_dir = scene_def_path.parent
    config_path = episode_dir / "episode_config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_existing_episodes(project_root: Path, current_episode_dir: str) -> list:
    """既存エピソードの情報を収集（クロスエピソードチェック用）"""
    episodes_dir = project_root / "episodes"
    if not episodes_dir.exists():
        return []

    existing = []
    for ep_dir in sorted(episodes_dir.iterdir()):
        if not ep_dir.is_dir():
            continue
        if ep_dir.name == Path(current_episode_dir).name:
            continue  # 自分自身はスキップ

        sd_path = ep_dir / "scene_definition.json"
        if sd_path.exists():
            with open(sd_path, encoding="utf-8") as f:
                sd = json.load(f)
            narr = extract_narration_text(sd)
            # 要約として最初の500字だけ
            existing.append(
                {
                    "id": ep_dir.name,
                    "summary": narr[:500] + ("..." if len(narr) > 500 else ""),
                }
            )

    return existing


def run_agent(
    agent_key: str,
    scene_definition: dict,
    scene_def_path: Path,
    project_root: Path,
    debug: bool = False,
) -> dict:
    """単一エージェントを実行"""
    agent_info = AGENTS[agent_key]
    print(f"\n{'─' * 50}")
    print(f"Agent: {agent_info['name']} ({agent_info['description']})")
    print(f"Model: {agent_info['model']}")
    print(f"{'─' * 50}")

    narration_text = extract_narration_text(scene_definition)
    episode_config = load_episode_config(scene_def_path)

    # エージェント別プロンプト生成
    if agent_key in ("fact", "fact_grounding"):
        prompt = _build_fact_checker_prompt(narration_text, episode_config)
    elif agent_key == "style":
        style_guide = load_style_guide(project_root)
        prompt = _build_style_checker_prompt(narration_text, style_guide)
    elif agent_key == "source":
        prompt = _build_source_manager_prompt(narration_text, episode_config)
    elif agent_key == "content":
        prompt = _build_content_reviewer_prompt(narration_text, scene_definition, episode_config)
    elif agent_key == "consistency":
        existing = load_existing_episodes(project_root, str(scene_def_path.parent))
        prompt = _build_consistency_checker_prompt(narration_text, scene_definition, existing)
    else:
        raise ValueError(f"Unknown agent: {agent_key}")

    # Claude Code 実行 or Gemini API
    start_time = time.time()
    try:
        backend = agent_info.get("backend", "claude")

        if backend == "gemini":
            response = call_gemini(
                prompt=prompt,
                model=agent_info["model"],
                debug=debug,
                project_root=str(project_root),
            )
        else:
            response = call_claude(
                prompt=prompt,
                model=agent_info["model"],
                debug=debug,
                project_root=str(project_root),
                prefix=f"qa_{agent_key}",
                allowed_tools="Read",  # No Bash: prevent Opus from trying
                # workaround via bash stdout which the
                # stream-json parser can't capture
                # (a past session).
            )

        result = extract_json_from_response(response)
        elapsed = time.time() - start_time

        # メタ情報追加
        result["_agent"] = agent_key
        result["_model"] = agent_info["model"]
        result["_duration_sec"] = round(elapsed, 1)

        # ステータス表示
        status = result.get("status", "UNKNOWN")
        issues = result.get("issues", result.get("improvements", []))
        issue_count = len(issues)

        status_icon = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}.get(status, "[?]")
        print(f"\n  {status_icon} {status} ({issue_count} issues, {elapsed:.0f}s)")

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n  [ERROR] {e}")
        return {
            "_agent": agent_key,
            "_model": agent_info["model"],
            "_duration_sec": round(elapsed, 1),
            "status": "ERROR",
            "error": str(e),
            "issues": [],
        }


# ============================================================
# レポート生成
# ============================================================


def aggregate_report(
    agent_results: dict,
    episode_id: str,
    gate: str,
) -> dict:
    """エージェント結果を統合レポートに集約"""

    total_issues = 0
    critical = 0
    warning = 0
    info = 0
    has_error = False

    for _key, result in agent_results.items():
        if result.get("status") == "ERROR":
            has_error = True
            continue

        issues = result.get("issues", result.get("improvements", []))
        for issue in issues:
            sev = issue.get("severity", "info")
            total_issues += 1
            if sev == "critical":
                critical += 1
            elif sev == "warning":
                warning += 1
            else:
                info += 1

    # 全体ステータス判定
    if has_error:
        overall = "ERROR"
    elif critical >= 1:
        overall = "FAIL"
    elif warning >= 3 or any(r.get("status") == "FAIL" for r in agent_results.values()):
        overall = "WARN"
    elif warning >= 1:
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "episode": episode_id,
        "gate": gate,
        "timestamp": datetime.now().isoformat(),
        "overall_status": overall,
        "summary": {
            "total_issues": total_issues,
            "critical": critical,
            "warning": warning,
            "info": info,
        },
        "agents": agent_results,
    }


def _safe(text: str) -> str:
    """cp932で表示できない文字を置換"""
    try:
        text.encode("cp932")
        return text
    except UnicodeEncodeError:
        return text.encode("cp932", errors="replace").decode("cp932")


def print_report(report: dict):
    """レポートをコンソールに表示"""

    status = report["overall_status"]
    status_icon = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]", "ERROR": "[ERROR]"}.get(
        status, "[?]"
    )

    print(f"\n{'=' * 60}")
    print(f"  QA Report: {report['episode']} / {report['gate']}")
    print(f"  Status: {status_icon} {status}")
    print(
        f"  Issues: {report['summary']['critical']} critical, "
        f"{report['summary']['warning']} warning, "
        f"{report['summary']['info']} info"
    )
    print(f"  Time: {report['timestamp']}")
    print(f"{'=' * 60}")

    for agent_key, result in report["agents"].items():
        agent_name = AGENTS.get(agent_key, {}).get("name", agent_key)
        agent_status = result.get("status", "?")
        duration = result.get("_duration_sec", 0)

        s_icon = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]", "ERROR": "[ERROR]"}.get(
            agent_status, "[?]"
        )
        print(f"\n  {s_icon} {agent_name} ({duration:.0f}s)")

        # サマリー表示
        summary = result.get("summary", "")
        if summary:
            print(f"     {_safe(summary)}")

        # issues表示
        issues = result.get("issues", result.get("improvements", []))
        for issue in issues:
            sev = issue.get("severity", "info")
            sev_mark = {"critical": "[C]", "warning": "[W]", "info": "[I]"}.get(sev, "[-]")
            detail = issue.get("detail", issue.get("finding", ""))
            print(f"     {sev_mark} [{sev}] {_safe(detail[:100])}")

            suggestion = issue.get("suggestion", "")
            if suggestion:
                print(f"        -> {_safe(suggestion[:100])}")

        # ContentReviewer の場合はレーティング表示
        ratings = result.get("ratings", {})
        if ratings:
            grades = [f"{k}:{v.get('grade', '?')}" for k, v in ratings.items()]
            print(f"     Ratings: {', '.join(grades)}")

        # SourceManager の場合は参考文献数表示
        refs = result.get("references", {})
        if refs:
            book_count = len(refs.get("books", []))
            web_count = len(refs.get("websites", []))
            print(f"     References: {book_count} books, {web_count} websites")

        # positive_notes（あれば）
        positives = result.get("positive_notes", result.get("strengths", []))
        if positives:
            print(f"     + {_safe(positives[0])}")

    # Notes (reminders for manual review)
    notes = report.get("notes", [])
    if notes:
        print(f"\n  {'─' * 50}")
        print("  Notes:")
        for note in notes:
            print(f"     {_safe(note)}")

    print(f"\n{'=' * 60}\n")


# ============================================================
# メイン
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="数学史記 マルチエージェントQAチェッカー")
    parser.add_argument(
        "scene_definition",
        help="scene_definition.json のパス",
    )
    parser.add_argument(
        "--gate",
        choices=["script"],  # 将来: "image", "audio", "final"
        default="script",
        help="実行するQAゲート (default: script)",
    )
    parser.add_argument(
        "--agents",
        type=str,
        default=None,
        help="実行するエージェント（カンマ区切り）例: fact,style,content",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="クイックモード（Sonnetエージェントのみ実行）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグ情報を表示",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="レポート出力先（デフォルト: エピソードディレクトリ内）",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="安全な修正を自動でscene_definition.jsonに適用（スタイル修正のみ）",
    )
    parser.add_argument(
        "--use-gemini-fact",
        action="store_true",
        help="FactCheckerにGemini Grounding（Web検索付き）を使用",
    )

    args = parser.parse_args()

    # scene_definition.json 読み込み
    sd_path = Path(args.scene_definition).resolve()
    if not sd_path.exists():
        print(f"ERROR: {sd_path} が見つかりません。")
        sys.exit(1)

    with open(sd_path, encoding="utf-8") as f:
        scene_definition = json.load(f)

    # プロジェクトルート検出
    project_root = find_project_root(str(sd_path.parent))
    print(f"Project root: {project_root}")

    # エピソードID
    episode_id = sd_path.parent.name  # e.g., "001_erdos"

    # 実行エージェントの決定
    if args.agents:
        agent_keys = [a.strip() for a in args.agents.split(",")]
        invalid = [a for a in agent_keys if a not in AGENTS]
        if invalid:
            print(f"ERROR: 不明なエージェント: {invalid}")
            print(f"有効なエージェント: {list(AGENTS.keys())}")
            sys.exit(1)
    elif args.quick:
        agent_keys = QUICK_AGENTS
        print("クイックモード: Sonnetエージェントのみ実行")
    else:
        agent_keys = list(AGENTS.keys())
        # fact_grounding はデフォルトでは含めない（明示的に指定 or --use-gemini-fact）
        agent_keys = [k for k in agent_keys if k != "fact_grounding"]

    # --use-gemini-fact: fact → fact_grounding に差し替え
    if args.use_gemini_fact:
        if "fact" in agent_keys:
            idx = agent_keys.index("fact")
            agent_keys[idx] = "fact_grounding"
            print("FactChecker: Gemini Grounding（Web検索付き）を使用")

    # 実行情報表示
    total_estimated = sum(25 if AGENTS[k]["model"] == "opus" else 8 for k in agent_keys)
    print(f"\nGate: {args.gate}")
    print(f"Episode: {episode_id}")
    print(f"Agents: {', '.join(agent_keys)} ({len(agent_keys)}個)")
    print(f"推定所要時間: ~{total_estimated}分")

    char_count = _count_narration_chars(scene_definition)
    scene_count = len(_get_all_scenes(scene_definition))
    print(f"Script: {char_count}字, {scene_count}シーン")

    # エージェント実行
    start_total = time.time()
    agent_results = {}

    for key in agent_keys:
        agent_results[key] = run_agent(
            agent_key=key,
            scene_definition=scene_definition,
            scene_def_path=sd_path,
            project_root=project_root,
            debug=args.debug,
        )

    # Day 16 強化 B: 決定論 である調 lint (LLM StyleChecker 盲点補完)。
    # script gate のみ (narration 対象)。Claude 不要・即時。
    if args.gate == "script":
        dl = run_dearu_lint(scene_definition)
        agent_results["dearu_lint"] = dl
        print(
            f"\n  [dearu_lint] {dl['status']} "
            f"({sum(1 for i in dl['issues'] if i['severity'] == 'warning')} warning / "
            f"{sum(1 for i in dl['issues'] if i['severity'] == 'info')} info)"
        )

    total_elapsed = time.time() - start_total

    # レポート集約
    report = aggregate_report(agent_results, episode_id, args.gate)
    report["total_duration_sec"] = round(total_elapsed, 1)

    # description.intro 整合性リマインダー
    report["notes"] = []
    desc_block = scene_definition.get("description", {})
    has_issues = report["summary"]["critical"] > 0 or report["summary"]["warning"] > 0
    if desc_block.get("intro") and has_issues:
        report["notes"].append(
            "WARNING: description.intro（YouTube概要欄の紹介文）にも同様の事実誤認がないか確認してください。"
            " ナレーションを修正した場合、description.intro の内容も整合性を保つ必要があります。"
        )

    # レポート保存（表示前に保存して、表示クラッシュでもレポートが残るようにする）
    output_path = args.output
    if not output_path:
        output_path = sd_path.parent / f"qa_report_{args.gate}.json"
    else:
        output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # レポート表示
    print_report(report)
    print(f"Total QA time: {total_elapsed:.0f}s ({total_elapsed / 60:.1f}min)")
    print(f"Report saved: {output_path}")

    # 自動修正モード
    if args.auto_fix:
        print(f"\n{'─' * 50}")
        print("自動修正モード")
        print(f"{'─' * 50}")

        modified_sd, fixes = apply_auto_fixes(scene_definition, report)

        if fixes:
            print(f"  {len(fixes)}件の自動修正を適用:")
            for fix in fixes:
                print(
                    f"    [{fix['agent']}] {fix['scene_id']}: "
                    f"'{fix['original'][:30]}' → '{fix['replacement'][:30]}'"
                )

            # バックアップ作成
            backup_path = sd_path.with_suffix(".json.bak")
            if not backup_path.exists():
                import shutil

                shutil.copy2(sd_path, backup_path)
                print(f"  バックアップ: {backup_path}")

            # 修正を書き込み
            with open(sd_path, "w", encoding="utf-8") as f:
                json.dump(modified_sd, f, ensure_ascii=False, indent=2)
            print(f"  修正済み: {sd_path}")

            # 修正ログを保存
            fix_log_path = sd_path.parent / "qa_auto_fixes.json"
            with open(fix_log_path, "w", encoding="utf-8") as f:
                json.dump(fixes, f, ensure_ascii=False, indent=2)
            print(f"  修正ログ: {fix_log_path}")
        else:
            print("  自動修正対象なし（全て手動確認が必要な項目です）")

    # 終了コード
    if report["overall_status"] == "FAIL":
        sys.exit(1)
    elif report["overall_status"] == "ERROR":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
