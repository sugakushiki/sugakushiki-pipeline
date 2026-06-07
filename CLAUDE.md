# CLAUDE.md — 数学史記 プロジェクトルール

> Claude Code が毎セッション読むプロジェクトルール。本ファイルは規約のコアとインデックスを担う。
> 詳細な規約・ワークフロー・落とし穴集は `docs/` および `.claude/rules/` (path-scoped) に外出ししている。
> アーキテクチャ全体像は [`docs/architecture.md`](docs/architecture.md) (4 Mermaid 図)、利用者向けの導入は [`README.md`](README.md) を参照。

---

## プロジェクト概要

日本語 YouTube 数学史ドキュメンタリー動画制作パイプライン。
`episode_config.json` → 9 ステップ自動パイプライン → `output_final.mp4` (10〜19 分、詳細仕様: [docs/02_pipeline/VIDEO_SPEC.md](docs/02_pipeline/VIDEO_SPEC.md))。

## 環境

| 項目 | 値 |
|---|---|
| OS | Windows 11 想定 (Linux/Mac 動作未確認、GPU なし環境想定) |
| Python | 3.11.0 (venv 内は `python`、venv 外は `py`) |
| venv 有効化 | `venv\Scripts\activate` (Windows) / `source venv/bin/activate` (Unix) |
| Manim | v0.19.2 (`-qh` で 1080p) |
| VOICEVOX | 0.25.1 (localhost:50021、GUI アプリ起動必須) |
| FFmpeg | 2026-02 以降推奨 |
| フォント | BIZ UDMincho (日本語全般、OFL 1.1) |

## Windows 固有の制約

- **`subprocess` 禁止 (Claude CLI 経路)**: Claude Code CLI (`claude -p`) の呼び出しは `os.system()` + tempファイル方式。`subprocess.run()` / `subprocess.Popen()` は使わない (Windows での日本語クラッシュ回避)
- **`findstr` 非推奨**: 日本語テキストやパイプ演算子で不安定。ファイル渡しか `type` を使う
- **Claude Code CLI `-p` モード**: `--allowedTools Read,Bash` が必須 (v2.1.63 以降)
- **cp932 対応**: `print()` の絵文字・特殊 Unicode (em dash 等) は ASCII 代替に統一 (Windows console は cp932)。`requirements*.txt` のヘッダーコメントも非 ASCII 不可 (pip 22.3 が cp932 で読み込みクラッシュ)

## 品質チェックツール

| ツール | 用途 | コマンド |
|---|---|---|
| **smoke test** | pre-pipeline 静的健全性 (import / config_validator / Manim discovery、5 秒以内) | `python scripts/smoke_test.py` |
| **ruff lint** | F+E+I+B+UP rule set (E501/E731/B008 ignore) | `python -m ruff check src/ scripts/` |
| **ruff format** | black 互換フォーマッタ (既存コードは段階適用) | `python -m ruff format src/ scripts/` |
| **route_map preflight** | route_map 衝突検出 (pipeline 起動時に default ON、`--allow-route-collision` で escape、`--auto-fix-route-collisions` で 4-stage opt-in fix) | (pipeline.py 内で自動起動) |

依存物:
- `requirements.txt`: 完全 lock file (80 packages、`pip freeze` 出力 + コメント)
- `requirements.in`: top-level 直接依存 10 件 (manim / numpy / scipy / sympy / matplotlib / pillow / fonttools / requests / python-dotenv / google-genai)
- `requirements-dev.txt`: 開発用 (ruff)。production install は `pip install -r requirements.txt`、開発は `+ requirements-dev.txt`
- `.python-version`: 3.11.0 (pyenv 互換)
- 再生成: `pip install --upgrade -r requirements.in && pip freeze > requirements.txt`

## コーディング規約

### 全般
- 修正を提案する前に **実際のコードを読んで** 問題を確認する (推測で修正しない)
- 診断スクリプトやログ出力で **証拠を集めてから** 原因を特定する
- パイプラインレベルの構造的解決を優先。1 回限りのパッチは避ける
- 既存の関数・パターンを確認し、重複実装しない

### Python
- ファイル書き込みは `encoding='utf-8'` を明示
- パスは `os.path.join()` を使用 (バックスラッシュのハードコード不可)
- サイレントな `except: pass` 禁止 (最低限ログ出力)

### episode_config.json
- `verified_facts` は **dict 形式 `{}`** (list は `config_validator.py` でクラッシュ)
- `wikimedia_photo_urls` は **flat list 形式** `["url1", "url2"]` (dict 形式は `KeyError: 0`)
- 新フィールド追加時は `.get()` でデフォルト値を取って後方互換性確保
- 詳細: `.claude/rules/episode-config.md` (path-scoped、`episode_config.json` 編集時に自動ロード)

---

## Manim テンプレート

**1 ファイル 1 クラス + `construct()` 内 mode 分岐**。日本語は `Text(font=FONT)`、`MathTex` には Unicode/日本語を入れない。Y 座標は −2.0 〜 +3.3。`SCENES` dict + docstring + `LINT_FACTUAL_CLAIMS` metadata 必須。末尾に `FadeOut` を入れない (黒フレーム padding 防止)。

詳細チェックリスト + カラーパレット + アニメ規約: `.claude/rules/manim-development.md` (path-scoped、`src/manim_templates/**/*.py` 編集時に自動ロード)。

---

## スクリプト生成ルール

- 文体: **ですます調** (である調禁止)
- 文字数: **290 字/分** (`target_duration_minutes` から動的計算)
- 感嘆符: 1 スクリプトに 2〜3 回まで
- 禁止表現: 「ヤバい」「すごすぎる」「衝撃」等の煽り語
- **narration での「今日」禁止**: VOICEVOX が「きょう」(today) と「こんにち」(modern times) を文脈で区別できず誤読が繰り返し発生。「現代」「今」「これから」「近代」等に言い換え。modern の意味で「今日」が必要なら `narration_speech` に「こんにち」と明示
- 各エピソードは **単独完結** で書く (前回・次回・続編 NG)
- **person section は厚く**: 経歴の列挙だけにせず、性格・苦悩・人間味・個人エピソード (家族・教育者像・同時代人との関係・困難) を primary source で verify して含める。視聴者は数式より人物の物語に引き込まれる
- 事実確認: 歴史的主張は web verify してから narration に入れる (LLM の推論を鵜呑みにしない)
- 数式記号を含む narration には `narration_speech` で音声読み替え必須
- 数式音声化の誤読対策は global 集積で行う (audio_generator の誤読カテゴリ辞書 / `_convert_fractions()` / pronunciation_check Claude prompt / `formula_display._sanitize_subtitle()` の 4 層)。per-ep narration_speech 個別書き換えに陥らない
- 字幕分割マーカー `|` は **意味的に自然な位置** で 25 文字以内に手動配置
- 詳細トーン規約: `docs/03_quality/STYLE_GUIDE.md`

---

## QA 運用

- **アプローチ A (デフォルト)**: QA レポート → 人間が手動修正 (鵜呑み禁止、過去の運用知見で繰り返し再発が確認されている)
- `--qa` は default ON、`--skip-qa` で opt-out
- 主要フラグ: `--qa-allow-warn` / `--skip-fact-check` (事前事実チェック) / `--skip-qa-image-narration` (画像-ナレーション QA) / `--pronunciation-dry-run`
- **QA 再検証 hook**: `qa_report_*.json` Read 時に `.claude/hooks/qa_report_reminder.py` が再検証リマインダを system に差し込む

詳細フラグ全リスト + hook 配線: `docs/03_quality/qa.md`。
`scene_definition.json` / `qa_report_*.json` 編集時の規約: `.claude/rules/qa-workflows.md` (path-scoped)。

---

## 画像生成

- 人物 (写真あり): Wikimedia 実写 → Gemini Flash で油絵風年齢変換
- 人物 (写真なし): Wikimedia PD 肖像画 → 油絵変換 (同一性は写真より弱い)
- 場所・雰囲気: Gemini Flash 直接生成
- Vision QA: Claude Sonnet (Anthropic Max 契約内コスト 0)
- 主題者以外には `"use_reference": false` (リファレンス汚染防止)
- `wikimedia_photo_urls` は flat list 形式 (dict は `KeyError: 0`)

詳細: `docs/04_assets/image-generation.md` および `docs/04_assets/IMAGE_GUIDE.md` (プロンプト設計詳細)。
画像生成コード / `episodes/*/visuals/` 編集時の規約: `.claude/rules/image-generation.md` (path-scoped)。

---

## よくある落とし穴

過去のバグ・落とし穴をカテゴリ別 (Manim / VOICEVOX / 画像生成 / サムネイル / 字幕 / route_map / description / pipeline / Claude CLI / 環境 / QA / 事実誤認 / コンテンツ設計) に整理:

→ **`docs/03_quality/pitfalls.md`** (新エピソード制作時・コード修正時の必読)

---

## 作業フロー

### 新エピソード制作
1. 企画・事実確認 (AI 補助で議論、一次資料で裏取り)
2. `episode_config.json` 作成 (`.claude/rules/episode-config.md` 規約参照)
3. Manim テンプレート作成 (`.claude/rules/manim-development.md` チェックリスト実行)
4. フルパイプライン実行: `python src/pipeline.py episodes/XXX/episode_config.json`
5. QA レポート確認 → 手動修正 (再検証フェーズ実施、QA 出力は鵜呑みにしない)
6. `--skip-script --skip-qa` で再ビルド
7. 動画確認 → 微調整 → 公開

### パイプライン修正
1. 問題の再現確認 (ログ or 出力確認)
2. 該当コードを読む (推測しない)
3. 修正 → テスト → 影響範囲の確認

### 部分再ビルド時の注意
`--qa` は default ON。partial rebuild では `--skip-qa --skip-pronunciation-check` を併用しないと QA Gate 1 が長時間ブロックする (過去の運用知見)。

---

## 参照ドキュメント

### アーキテクチャ全体像
- [`docs/architecture.md`](docs/architecture.md) — 4 Mermaid 図 (パイプラインフロー / Manim テンプレート構造 / episode_config スキーマ / QA + 観測性)
- [`README.md`](README.md) — 利用者向け導入・必須前提・クイックスタート

### 規約・スキーマ

| パス | 内容 |
|---|---|
| `docs/03_quality/STYLE_GUIDE.md` | トーン・VOICEVOX・Manim・ビジュアル・出典ルール |
| `docs/04_assets/IMAGE_GUIDE.md` | 画像生成プロンプト設計の詳細・実例集 |
| `docs/02_pipeline/EPISODE_CONFIG_TEMPLATE.md` | `episode_config.json` スキーマ詳細 |
| `docs/02_pipeline/SCENE_SPEC.md` | Manim シーン仕様 |
| `docs/02_pipeline/SYMPY_HELPER_DESIGN.md` | SymPy ヘルパーの設計 |
| `docs/03_quality/QA_PIPELINE.md` / `docs/03_quality/QA_INTEGRATION_GUIDE.md` | QA エージェント設計詳細 |
| `docs/03_quality/pitfalls.md` | 過去のバグ・落とし穴のカテゴリ別整理 |
| `docs/03_quality/qa.md` | QA フラグ詳細・hook 配線 |
| `docs/04_assets/image-generation.md` | 画像生成パイプライン規約 |

### path-scoped rules (`.claude/rules/`)

該当ファイル編集時に自動ロード:

| ルールファイル | 適用 paths |
|---|---|
| `episode-config.md` | `**/episode_config.json` |
| `manim-development.md` | `src/manim_templates/**/*.py` |
| `qa-workflows.md` | `**/qa_report*.json`, `**/scene_definition.json` |
| `image-generation.md` | `src/*image*.py`, `src/wikimedia_fetcher.py`, `episodes/*/visuals/**` |

### docs/INDEX
- [`docs/INDEX.md`](docs/INDEX.md) — docs 全体目次 (用途別 + 3 階層 + カテゴリ別)
