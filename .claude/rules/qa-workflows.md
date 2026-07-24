---
paths:
  - "**/qa_report*.json"
  - "**/scene_definition.json"
---

# QA レポート読み込み時 / scene_definition.json 編集時の規約

## QA レポート読み込み時

`qa_report_*.json` を Read した瞬間、`.claude/hooks/qa_report_reminder.py` が PreToolUse hook で再検証リマインダを system に差し込む（`settings.local.json` 登録時）。

QA 指摘を反映する前に、以下のフェーズを実施する:

1. **指摘の正しさを再検証**: web verify、コード確認、過去の `verified_facts` 確認
2. **修正の自然さを確認**: 修正後 narration / scene_definition が読み下しで自然か
3. **修正漏れの確認**: 同じ問題が他のシーンにないか

過去の運用知見として「**鵜呑み禁止**」が確立されている。

QA agent (FactChecker / ContentReviewer) は LLM 判定で run 間に揺れる (人物の登場人数や年号などが別 run で異なる結果を返すケースが過去に観測されている)。`common_errors_to_avoid` に明示してあれば QA 指摘を却下する判断基準にできる。

### verified_facts.source 直接参照による独立 verify

**QA SourceManager warning (出典確認推奨) を読んだ場合、`verified_facts.source` の identifier を WebFetch で少なくとも 1 件は独立 verify する。**

理由:
- verified_facts 新形式 `{fact, source}` の設計意図は「**QA が事実を指摘した時、source を直接参照して正誤判断できる**」(`docs/02_pipeline/EPISODE_CONFIG_TEMPLATE.md`)
- 過去の検証で「過去の運用知見の脚注的記述」を rely して却下する判断ミスがあり、後の WebFetch (Wikipedia) で裏付けなしと判明した事例があった
- 多層防御 (memory / hook / pre-script fact check / Vision check) を構築したが、SourceManager warning に対する **verified_facts.source 直接参照の自動化されていない gap** が残っていた

#### 独立 verify の手順

QA SourceManager warning が出ている各 unsourced_claim について:

1. **identifier の特定**: verified_facts の対応キーから `source` を取得し、含まれる identifier を抽出
   - arXiv 番号 (例: `arXiv:1302.5855`) → `https://arxiv.org/abs/1302.5855`
   - DOI (例: `10.xxxx/yyyy`) → `https://doi.org/10.xxxx/yyyy`
   - URL → 直接 fetch
   - ADS Bibcode (例: `1993JBAA..103...30S`) → `https://ui.adsabs.harvard.edu/abs/<bibcode>`
   - 書誌情報のみ (古い同人誌・紙書籍等) → 著者名 + タイトル + 発表年で web 検索、独立資料がなければ「primary verify 不可」と明示
2. **WebFetch で fetch**: identifier を URL 化して WebFetch、abstract/著者名/出版年/トピックの一致を確認
3. **結果の記録**: 検証 PASS なら却下、検証不一致なら narration を hedge 形 (「〜によれば」) に修正、検証不可なら user 判断を仰ぐ

#### 「鵜呑み禁止」の二重意味

- (a) **QA 指摘を鵜呑みにしない** (= 却下判断のための再検証)
- (b) **却下判断も鵜呑みにしない** (= 過去の運用知見を rely した却下時こそ verified_facts.source 直接 verify を実施)

`--qa-allow-warn` 使用時こそ各 warning を独立に検証する。「allow したから細かく見なくていい」モードに陥らない。

## scene_definition.json 編集時の narration_speech 同期義務

**`narration` を編集したら、対応する `narration_speech[i]` を必ず同 index で同期更新する。**

理由:
- pronunciation_check は既存 `narration_speech` を上書きしない仕様（user-managed として尊重）
- `narration` を編集しても `narration_speech[i]` が古いままだと VOICEVOX が古いテキストで音声生成
- 過去のケースで「一切→ほとんど」修正が音声に反映されず、長時間の再ビルドが必要になった

### 同期方法

- kana 補正があるなら kana 優先
- なければ `narration[i].replace('|', '')` の flat 版で OK
- 配列の一部 index だけ修正する場合、**修正しない index にも必ず `narration[i]` と同じ文字列をコピー** (空文字は VOICEVOX が極小無音 wav を返して短時間の字幕高速通過を起こす、過去のケースで発覚)

### Cloud TTS: `narration_speech_cloud` も同期対象 (2026-07-04〜)

`tts.engine=cloud` の ep は Cloud 用の任意フィールド **`narration_speech_cloud`** を持つ。sync surface が **2本** になったので、`narration` を編集したら **`narration_speech`(VOICEVOX) と `narration_speech_cloud`(Cloud) の両方**を同 index で同期する。

- `narration_speech_cloud` は VOICEVOX と別読み: **孤立助詞のみ** は→「わ」/へ→「え」(gen_cloud_readings が コンマ孤立の `、は`/`、へ` を自動変換。**語中の は を わ にしない** ── 全 は を わ にする blanket-わ は Chirp3-HD が独立わの境目に不自然な間を挿入する)、外国人名カタカナ化、全/半角スペース除去、**辞書非適用** (Cloud は verbatim 送信)。VOICEVOX の kana 補正をそのまま流用しない。
- **cloud の生成主体は gen_cloud_readings** (LLM ではない): script_generator は LLM が出力した `narration_speech_cloud` を strip し、gen_cloud が narration から native は で再生成する。手書きで既存 cloud を調整する場合のみ上記の孤立助詞ルールに従う (config に「LLM に narration_speech_cloud を用意させる」指示を書かない)。
- 未設定なら cloud は `narration_speech`→`narration` に fallback し「読み未検証」WARN。
- `validate_narration_speech()` は両フィールドの空要素を fail-fast、`lint_narration_markers()` は両フィールドの長さ不一致を WARN。
- Cloud 読みの検証は `scripts/stt_qa.py` (Gemini STT)。VOICEVOX の pronunciation_check/reading_guard は cloud には走らない。

### 自動検証

`audio_generator.py` の `lint_narration_markers()` が narration vs narration_speech の drift を WARN として検出 (speech 側の漢字欠落 + 数字列不一致を subseq 比較)。
ただし完全 kana speech・漢字共有編集・句読点編集は構造上検出不能。

## 関連 docs

- `docs/03_quality/qa.md`: QA 運用フラグ、QA 再検証 hook 詳細、severity 判定の運用
- `docs/03_quality/pitfalls.md` の `VOICEVOX / 発音 / narration_speech` および `QA エージェント / Vision QA` セクション
