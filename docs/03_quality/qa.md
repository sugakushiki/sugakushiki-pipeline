# QA 運用

> CLAUDE.md から外出しした QA 運用 doc。pipeline 実行時の QA フラグと運用ルールを集約。
> 関連:
> - `docs/03_quality/QA_PIPELINE.md`: QA 5 エージェント全体のプロンプト設計詳細
> - `docs/03_quality/QA_INTEGRATION_GUIDE.md`: QA 結果の手動修正ガイド
> - `docs/03_quality/STYLE_GUIDE.md`: QA が参照するスタイル基準
>
> 本ファイルは「実行時の運用とフラグ」、関連 docs は「設計詳細・修正手順」を扱う。

---

## アプローチ

- **アプローチA（デフォルト）**: QA レポート → 人間が手動修正
- `--qa-retry` は critical 多数時のみ opt-in
- severity 判定: 数学的厳密性に関わるものは warning 以上

---

## フラグ群

### QA 全般

- **`--qa-allow-warn`**: WARN のときもパイプラインを止めずに続行する（CRITICAL は止める）。ContentReviewer の構成意図（ペーシング・text_overlay 配置）warnings など「設計判断として受け入れるもの」を通す時に使う

### Pronunciation

- **`--pronunciation-dry-run`**: 発音修正の提案だけを表示して `scene_definition.json` は変更しない。音声生成前に LLM＋ルールベース修正を監査したい時に使う（`--check-pronunciation` を暗黙的に ON）

### Pre-script Fact Check

- **`--skip-fact-check` / `--fact-check-allow-warn`**: pre-script fact check（C: Sonnet 知識ベース + D: 算術サニティ + E: Wikidata 照合）の制御。default は CRITICAL/WARNING で停止。
  - `--fact-check-allow-warn`: WARN を通す（`--qa-allow-warn` と同パターン）
  - `--skip-fact-check`: 全体 opt-out
  - レポート: `episodes/<id>/pre_script_fact_check_report.json`
  - Sonnet 結果はキャッシュ: `_pre_script_fact_cache.json`

### Image-Narration Consistency

- **`--skip-qa-image-narration`**: Gate 2 (`qa_image_checker.py`) による画像-narration 整合性チェックを skip。default は `--qa` で ON。
  - Gate 2 は image step **後**に走る
  - 5 sub-aspect で判定:
    - 4-1 主要人物の有無
    - 4-2 人物の性別
    - 4-3 人物の人数
    - 4-4 活動・小道具（ステレオタイプ）
    - 4-5 細部
  - レポート: `episodes/<id>/qa_report_images.json`

---

## QA 再検証 hook: QA 指摘の自動再検証リマインダ

`qa_report_*.json` を Read した瞬間に `.claude/hooks/qa_report_reminder.py` が PreToolUse hook で再検証リマインダを system に差し込む。

- 設定: `settings.local.json` (gitignored) に登録が必要
- 詳細:過去の運用知見+ hook script の docstring 参照
- worktree session は main repo の `settings.local.json` を見ないため、worktree でも独立に hook 登録が必要（hook script 本体は repo にあるので path 指定だけで OK、絶対パス推奨）

---

## QA エージェント関連の落とし穴

`docs/03_quality/pitfalls.md` 「QA エージェント / Vision QA」セクション参照:

- ContentReviewer の尺超過 false positive
- QA agent の非決定性（run 間で判定が揺れる）
- Gate 2 (qa_image_checker.py) の新規ビルド時未稼働問題（解決済）
- Vision LLM 単発実行の保守性（将来課題）
