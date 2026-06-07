# マルチエージェントQAパイプライン設計書

**ステータス**: Gate 1 (script QA) + Gate 2 (画像 narration 整合性、`qa_image_checker.py`) + Gate 3 (発音チェック、`audio_generator.pronunciation_check`) 実装済。Gate 4 (最終統合 QA) は完了後の出力検証 (`pipeline.py` 末尾) で代替。

---

## 1. 概要

パイプラインの各工程に品質チェックゲートを設置し、LLMエージェントが自動で品質評価を行う。
人間（Paul）のレビュー負担を最小化しつつ、事実誤り・スタイル逸脱・構成問題を早期に検出する。

### アーキテクチャ

```
episode_config.json
  │
  ├─→ script_generator.py ─→ scene_definition.json
  │                              │
  │                    ┌─────────┤ ★ Gate 1: スクリプトQA
  │                    │         │
  │                    │    qa_checker.py --gate script
  │                    │         │
  │                    │    ┌────┴────────────────────────┐
  │                    │    │ Agent 1: FactChecker (Opus)  │
  │                    │    │ Agent 2: StyleChecker (Son.) │
  │                    │    │ Agent 3: SourceManager (Son.) │
  │                    │    │ Agent 4: ContentReviewer (Op.)│
  │                    │    │ Agent 5: Consistency (Son.)   │
  │                    │    └────┬────────────────────────┘
  │                    │         │
  │                    │    qa_report_script.json
  │                    │         │
  │                    │    [PASS] → 次工程へ
  │                    │    [WARN] → レポート表示、続行
  │                    │    [FAIL] → パイプライン停止、修正を要求
  │                    │
  ├─→ image_generator.py ─→ images/
  │                              │
  │                    ┌─────────┤ ★ Gate 2: 画像QA（将来）
  │                    │         │
  ├─→ audio_generator.py ─→ audio/ + timing.json
  │                              │
  │                    ┌─────────┤ ★ Gate 3: 音声QA（将来）
  │                    │         │
  └─→ video_assembler.py ─→ output.mp4
                                 │
                       ┌─────────┤ ★ Gate 4: 最終QA（将来）
```

---

## 2. 運用フロー

```batch
cd <project_root>/
venv\Scripts\activate

REM 1. スクリプト生成 + QA
python src/pipeline.py episodes/001_erdos/episode_config.json --steps script --qa-quick

REM 2. qa_report_script.json を確認し、scene_definition.json を手動修正

REM 3. 残りを実行
python src/pipeline.py episodes/001_erdos/episode_config.json --skip-script
```

warning数件の手動修正は通常5分以内で完了する。
`--qa-retry` による自動再生成はdiff rateが高くなりすぎるため、critical多発時のみ使用。

---

## 3. Gate 1: スクリプトQA（★実装済み）

### 3-1. エージェント一覧

| # | エージェント | バックエンド | Quick | Full | 役割 |
|---|---|---|---|---|---|
| 1 | **FactChecker** | Opus | ❌ | ✅ | 事実の正確性検証。年号・人名・数値・エピソードの真偽判定 |
| 2 | **StyleChecker** | Sonnet | ✅ | ✅ | STYLE_GUIDE.md準拠チェック。トーン・禁止表現・感嘆符数 |
| 3 | **SourceManager** | Sonnet | ✅ | ✅ | 参考文献リスト生成。概要欄用テキスト出力 |
| 4 | **ContentReviewer** | Opus | ❌ | ✅ | 構成・尺感・わかりやすさ・視聴者引き込み力の評価 |
| 5 | **ConsistencyChecker** | Opus | ❌ | ✅ | エピソード内の用語統一、数学的表現の厳密性 |

### 3-2. 実行モード

| モード | エージェント | 時間 |
|--------|-------------|------|
| Quick (`--qa-quick`) | Sonnet×2 (style, source) | ~3分 |
| Full (`--qa`) | 上記 + Opus×3 (fact, content, consistency) | ~60分 |

### 3-3. 出力フォーマット

各エージェントの結果を統合した `qa_report_script.json` を生成:

```json
{
  "episode": "001_erdos",
  "gate": "script",
  "timestamp": "2026-03-01T10:30:00",
  "overall_status": "WARN",
  "summary": {
    "total_issues": 5,
    "critical": 1,
    "warning": 3,
    "info": 1
  },
  "agents": {
    "fact_checker": {
      "status": "WARN",
      "model": "opus",
      "duration_sec": 1523,
      "issues": [
        {
          "severity": "critical",
          "scene_id": "bio_03",
          "claim": "3歳にして3桁の掛け算を暗算でこなし",
          "finding": "Wikipedia/MacTutorでは「3歳」は負の数の発見。掛け算は4歳の記述もあり。",
          "suggestion": "「3、4歳の頃」に変更を推奨",
          "confidence": 0.7
        }
      ]
    },
    "style_checker": {
      "status": "PASS",
      "model": "sonnet",
      "duration_sec": 487,
      "issues": []
    },
    "source_manager": {
      "status": "PASS",
      "model": "sonnet",
      "duration_sec": 502,
      "output": {
        "references": ["Paul Hoffman, \"The Man Who Loved Only Numbers\" (1998)", "..."],
        "youtube_description_text": "【主要参考文献】\n- ..."
      }
    },
    "content_reviewer": {
      "status": "WARN",
      "model": "opus",
      "duration_sec": 1401,
      "issues": [
        {
          "severity": "warning",
          "category": "pacing",
          "detail": "数学パートの密度が高い。ベルトランの仮説とラムゼー理論を両方扱うと駆け足になる可能性。",
          "suggestion": "どちらかに絞り、もう一方は別エピソードで扱うことを推奨"
        }
      ]
    },
    "consistency_checker": {
      "status": "PASS",
      "model": "sonnet",
      "duration_sec": 491,
      "issues": []
    }
  }
}
```

### 3-4. 判定ロジック

| overall_status | 条件 | アクション |
|---|---|---|
| PASS | critical=0, warning≤2 | 自動で次工程へ |
| WARN | critical=0, warning≥3 または info多数 | レポート表示、人間が判断 |
| FAIL | critical≥1 | パイプライン停止、修正を要求 |

### 3-5. 各エージェントの詳細設計

#### Agent 1: FactChecker（Opus）

**入力**: scene_definition.json（ナレーション全文）
**タスク**: ナレーション中の検証可能な事実主張を抽出し、正確性を評価

**チェック項目**:
- 年号・日付（生年月日、死亡日、受賞年、事件の年など）
- 人名・地名の正確性（スペル、関係性）
- 数値データ（論文数、共著者数、エルデシュ数の統計など）
- エピソードの真偽（逸話が文献に基づいているか）
- 因果関係の正確性（「AがBの原因で」のような主張）

**出力**: 各主張に対して severity（critical/warning/info）、finding、suggestion、confidence（0-1）

**注意**: Claude Code `-p` はWeb検索不可。エージェントは自身の知識に基づいて評価する。confidence < 0.5 の場合は "要手動確認" としてフラグする。`--use-gemini-fact` でGemini Grounding（Web検索付き）に切り替え可能。

#### Agent 2: StyleChecker（Sonnet）

**入力**: scene_definition.json + STYLE_GUIDE.md
**タスク**: スタイルガイドとの適合性をチェック

**チェック項目**:
- 禁止表現の検出（「ヤバい」「すごすぎる」「衝撃」等）
- 感嘆符の数（1スクリプト2-3回まで）
- 文体の一貫性（敬語ベースだが堅すぎない）
- 数学者の描写トーン（敬意はあるが神格化しない）
- 数学の説明スタンス（「導出する」ではなく「意味を語る」）
- タイトル/フックの温度感（好奇心の喚起 ≠ 煽り）

**出力**: 逸脱箇所のリスト + 修正案

#### Agent 3: SourceManager（Sonnet）

**入力**: scene_definition.json + episode_config.json
**タスク**: ナレーション内容から参考文献リストを推定し、YouTube概要欄用テキストを生成

**出力**:
- 推定参考文献リスト（書籍・論文・Webサイト）
- YouTube概要欄用フォーマット済みテキスト
- ナレーション内で典拠が不明な主張のフラグ

**フォーマット**: STYLE_GUIDE セクション6準拠

#### Agent 4: ContentReviewer（Opus）

**入力**: scene_definition.json + episode_config.json
**タスク**: コンテンツとしての完成度を多角的に評価

**チェック項目**:
- 4パート構成（フック→人物→数学→締め）のバランス
- フックの強度（最初の30秒で視聴者を引き込めるか）
- 数学パートの密度（詰め込みすぎていないか）
- ナラティブアーク（感情の起伏が適切か）
- ターゲット層（数学好き + エンジニア）への訴求力
- 推定尺とのバランス

**出力**: 5段階評価（A-E）+ 改善提案

#### Agent 5: ConsistencyChecker（Opus）

**入力**: scene_definition.json + 既存エピソードのscene_definition.json（あれば）
**タスク**: 用語・トーンの一貫性チェック

**チェック項目（エピソード内）**:
- 同一人物の呼称統一（「エルデシュ」vs「パウル」の使い分けが一貫しているか）
- 同一概念の用語統一（「エルデシュ数」vs「エルデシュ・ナンバー」など）
- シーン間のトーン変動（急に感傷的になったりしないか）
- 時系列の矛盾（シーンAで1970年の話→シーンBで1960年の話 など）

**チェック項目（クロスエピソード）**:（Episode 002以降で有効化）
- 他エピソードで言及済みの人物の紹介が矛盾していないか
- チャンネル全体の用語辞書との整合性
- 同じエピソード/逸話の重複使用

---

## 4. Gate 2: 画像QA (`qa_image_checker.py` で実装)

### エージェント構想

| # | エージェント | バックエンド | 役割 |
|---|---|---|---|
| 1 | ImageQualityChecker | Gemini（Vision） | 生成画像の品質評価（不自然な人物、文字化け、時代考証） |
| 2 | ImageConsistency | Gemini（Vision） | エピソード内の画風一貫性チェック |

### 実装方針
- Gemini APIのVision機能を活用（画像入力が可能）
- IMAGE_GUIDE.mdの基準に基づいて評価
- 品質スコアが閾値以下の画像は再生成をトリガー

---

## 5. Gate 3: 音声QA (`audio_generator.pronunciation_check` で実装)

### エージェント構想

| # | エージェント | 実装方式 | 役割 |
|---|---|---|---|
| 1 | PronunciationChecker | ルールベース | VOICEVOX辞書未登録語の検出 |
| 2 | TimingValidator | ルールベース | 音声長とscene duration の乖離チェック |

### 実装方針
- LLM不要。ルールベースで実装可能
- audio_generator.pyの`--dry-run`結果と実音声長の比較
- 新出の漢字読みをvoicevox_dict.jsonと照合

---

## 6. Gate 4: 最終統合QA (`pipeline.py` 末尾の出力検証で代替)

### エージェント構想

| # | エージェント | バックエンド | 役割 |
|---|---|---|---|
| 1 | SyncValidator | ルールベース | 音声・映像・字幕の同期精度 |
| 2 | DurationChecker | ルールベース | 最終動画尺が8-12分の目標範囲内か |
| 3 | FinalReviewer | Opus | 完成動画のメタデータ + scene_definitionから総合品質レビュー |

### 実装方針
- Gate 4のFinalReviewerは動画を「見る」のではなく、メタデータ（尺、シーン構成、QA結果サマリー）を総合判断
- 音声・字幕の同期はFFprobeの出力を解析

---

## 7. 技術的制約とワークアラウンド

### Claude Code `-p` のWindows制約（再掲）

```
- stdinパイプ禁止 → ファイルI/Oで回避
- subprocess不可 → os.system()使用
- プロジェクト外ファイル不可 → プロジェクトルートに一時ファイル
```

### Web検索不可の影響

FactCheckerはClaude Code経由のため、リアルタイムWeb検索ができない。
対策:
1. エージェントの知識ベースに依存（Opusの知識は広範）
2. confidence値で不確実な主張をフラグ
3. `--use-gemini-fact` でGemini API（Grounding付き）による検索対応のファクトチェックが可能

### 共通ユーティリティ

script_generator.pyとqa_checker.pyで共通のClaude Code呼び出しロジックを
`src/claude_backend.py` に抽出済み。

---

## 8. コスト・時間の見積もり

### Gate 1 フルQA

| 構成 | 所要時間 | 使用量（Claude Max） |
|---|---|---|
| Opus × 3 (Fact + Content + Consistency) | ~45min | Max範囲内 |
| Sonnet × 2 (Style + Source) | ~3min | Max範囲内 |
| **合計** | **~50-60min** | **追加コストなし** |

### クイックモード

| 構成 | 所要時間 |
|---|---|
| Sonnet × 2 (Style + Source) | ~3min |

### 運用での実行頻度

- スクリプト生成ごとにクイックQA → 必ず実行
- フルQA → パイロット版・公開前のみ
- Episode 002以降 → ConsistencyCheckerのクロスエピソードチェックが有効化