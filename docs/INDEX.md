# docs/INDEX.md — 数学史記 docs 全体目次

> 全 docs の入口。「困ったらまずここ」の確定先。
> 本 INDEX に未掲載のファイルは `Glob docs/**/*.md` で発見可能。

---

## 困ったらまずここ (用途別)

| 困りごと | 第一参照 | 補助参照 |
|---|---|---|
| アーキテクチャ全体把握 (4 図 / Mermaid) | [architecture.md](architecture.md) | -- |
| 新エピソードの企画・トーン設計 | [STYLE_GUIDE.md](03_quality/STYLE_GUIDE.md) | [pitfalls.md](03_quality/pitfalls.md) |
| `episode_config.json` を書く | [EPISODE_CONFIG_TEMPLATE.md](02_pipeline/EPISODE_CONFIG_TEMPLATE.md) | `.claude/rules/episode-config.md` (path-scoped で自動ロード) |
| Manim テンプレート作成・修正 | [SCENE_SPEC.md](02_pipeline/SCENE_SPEC.md) | `.claude/rules/manim-development.md` (path-scoped) / [pitfalls.md](03_quality/pitfalls.md) |
| 画像生成 (Wikimedia + Gemini Flash + Vision QA) | [IMAGE_GUIDE.md](04_assets/IMAGE_GUIDE.md) | [image-generation.md](04_assets/image-generation.md) / `.claude/rules/image-generation.md` (path-scoped) |
| QA 運用・指摘対応 | [qa.md](03_quality/qa.md) | `.claude/rules/qa-workflows.md` (path-scoped、QA 再検証 hook 連動) |
| Cloud TTS 回の読み・速度を詰める | [cloud_tts_qa.md](03_quality/cloud_tts_qa.md) | [qa.md](03_quality/qa.md) / [pitfalls.md](03_quality/pitfalls.md) の Cloud TTS 節 |
| パイプライン落とし穴を調べる | [pitfalls.md](03_quality/pitfalls.md) (カテゴリ別整理) | -- |

---

## ロード階層

3 階層で context をロードする設計:

1. **`CLAUDE.md` (リポ root)** — 毎セッション必須ロード。プロジェクトのコア規約とインデックス。
2. **`.claude/rules/*.md` (path-scoped、4 本)** — 編集対象ファイルに応じて自動ロード:
   - `episode-config.md` → `**/episode_config.json` 編集時
   - `manim-development.md` → `src/manim_templates/**/*.py` 編集時
   - `qa-workflows.md` → `**/qa_report*.json` / `**/scene_definition.json` 編集時 (QA 再検証 hook と連動)
   - `image-generation.md` → `src/*image*.py` / `episodes/*/visuals/**` 編集時
3. **`docs/**/*.md` (本ディレクトリ)** — 必要時に Read で個別参照。

詳細: `CLAUDE.md` 末尾「path-scoped rules」セクション。

---

## カテゴリ別キー docs

### docs/ 直下 — 全体俯瞰
- [architecture.md](architecture.md) — 4 Mermaid 図で pipeline / Manim / config / QA を俯瞰

### 01_concept/ — チャンネル根幹
- [CONCEPT.md](01_concept/CONCEPT.md) — チャンネルコンセプト
- [ROADMAP.md](01_concept/ROADMAP.md) — 中長期ロードマップ

### 02_pipeline/ — パイプライン仕様
- [EPISODE_CONFIG_TEMPLATE.md](02_pipeline/EPISODE_CONFIG_TEMPLATE.md) — `episode_config.json` のスキーマ詳細
- [SCENE_SPEC.md](02_pipeline/SCENE_SPEC.md) — Manim シーン仕様
- [VIDEO_SPEC.md](02_pipeline/VIDEO_SPEC.md) — 動画フォーマットの SSOT (尺・解像度・エンドカード等)
- [SYMPY_HELPER_DESIGN.md](02_pipeline/SYMPY_HELPER_DESIGN.md) — SymPy ヘルパーの設計

### 03_quality/ — 品質・QA・落とし穴
- [STYLE_GUIDE.md](03_quality/STYLE_GUIDE.md) — トーン・VOICEVOX・Manim・ビジュアル・出典ルール
- [pitfalls.md](03_quality/pitfalls.md) — 過去のバグをカテゴリ別に集約
- [qa.md](03_quality/qa.md) — QA フラグ詳細・再検証 hook 配線
- [cloud_tts_qa.md](03_quality/cloud_tts_qa.md) — Cloud TTS 回の読み制御・速度正規化・出荷前チェックリスト
- [QA_PIPELINE.md](03_quality/QA_PIPELINE.md) — QA エージェント設計詳細
- [QA_INTEGRATION_GUIDE.md](03_quality/QA_INTEGRATION_GUIDE.md) — QA 統合運用ガイド

### 04_assets/ — 画像・サムネイル
- [IMAGE_GUIDE.md](04_assets/IMAGE_GUIDE.md) — 画像生成プロンプト設計の詳細・実例集
- [image-generation.md](04_assets/image-generation.md) — 画像生成パイプライン規約

---

## 詳細列挙が必要な場合

本 INDEX に未掲載のファイル・将来追加されたファイルは:

- `Glob "docs/**/*.md"` で全列挙
- `Grep "keyword" --path docs/` で全文検索
- `git log -- docs/` で履歴・差分

---

## 関連入口 (docs/ 外)

- **`CLAUDE.md`** (リポ root) — プロジェクトコア規約、本 INDEX への入口
- **`.claude/rules/`** — path-scoped rules (上記「ロード階層」参照)
- **`README.md`** (リポ root) — 利用者向け導入・必須前提・クイックスタート
