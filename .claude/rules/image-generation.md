---
paths:
  - "src/*image*.py"
  - "src/wikimedia_fetcher.py"
  - "episodes/*/visuals/**"
---

# 画像生成コード / visuals 編集時の規約

## 画像生成パイプライン

- **人物（写真あり）**: Wikimedia 実写 → Gemini Flash で油絵風年齢変換
- **人物（写真なし）**: Wikimedia PD 肖像画 → 油絵変換（同一性は弱い）
- **場所・雰囲気**: Gemini Flash 直接生成

## 性別判定の保護 (Vision QA リトライ時)

- `_build_reference_prompt` の age_desc は `source_prompt` から動的推定する（"man" 固定にしない、過去のケースで発覚した性別バグ）
- `strengthen_prompt` は不変の `source_prompt=` を引数で渡し、feedback の "woman" 等の累積を防ぐ
- リトライで性別が反転する症状の構造的解決済

## リファレンス汚染の防止

主題者以外の人物（Leibniz 回での Newton 等）に主題者のリファレンス写真が使われると AI 生成が破綻する。

- `visual block` に `"use_reference": false` を設定して非主題人物のリファレンスを opt-out
- `wikimedia_photo_urls` を手動で **flat list 形式** `["url"]` で指定（dict 形式は禁止、`KeyError: 0` を起こす）

## 人物排除シーン (no_human フラグ)

群像シーン (机のみで主役判別困難など) や物だけのシーンで、source_prompt 手動書き換えなしに「人物なし」を宣言的に指定する。

- `visual block` に `"no_human": true` を設定 (default false)
- 効果:
  - source_prompt 末尾に `"no human figure visible, still life composition, no people in scene."` を自動付加 (Gemini Flash の人物バイアス抑制)
  - `use_reference` を強制 false に (人物リファレンス使用と「人物なし」が矛盾するため)
- 適用例: 机のみ (主題者の遺品・原稿) / 楽器のみ / 風景のみ
- 不適用: 人物がいるが主題者でない場合は `"use_reference": false` で対応 (no_human ではない)

## 既存画像のスキップ仕様

`image_generator` は既存画像をスキップする。`source_prompt` を変更した場合は **該当画像ファイルを削除してから再ビルド**。

## ステレオタイプ・cliché 注意

`source_prompt` に時代物の cliché（smoking pipes / top hats / wigs / leather-bound volumes 等）を追加する前に web 検索で「その時代・その集団・その場面でこの描写が史実的か」を確認する。

「intellectual gathering = pipe smoking」のような stereotype は史実検証なしに加えてはいけない（過去に集団のパイプ喫煙が史実無しで Gemini に描かせた事例があった）。

### cliche scanner

`src/cliche_scanner.py` が `image_generator.py` の image step 入口で source_prompt の時代物 cliché を自動検出。Layer 1 (辞書ベース、always-on) と Layer 2 (LLM レビュー、`--cliche-llm-review` で opt-in) の 2 層構成。

辞書 `src/cliche_dictionary.json` のカテゴリ: period_accessory / smoking / atmosphere / pose / anachronism / academic_stereotype。

検出時の挙動: WARN のみ (生成は続行)。シーン単位で承認済み cliché を opt-out するには visual block に `"cliche_acks": ["smoking pipes", "top hat", ...]` を設定 (例: 史実検証済の場合は cliche_acks で承認)。

単独実行: `PYTHONPATH=src python -m cliche_scanner episodes/<ep>/scene_definition.json`

## 紙幣・通貨

法的に再現ルール対象になり得る。間接的（発表会見・報道風）な画像で表現。`source_prompt` に直接 banknote のクローズアップを指定しない。

## AI 生成画像の透かし除去

ChatGPT/Sora 系は BR ✦ スパークル透かしを必ず入れる。手動作成画像を受け取ったら標準的なトリミング+リサイズで除去する (下部 10-13% トリミング → 16:9 中央クロップ → 1920×1080 LANCZOS リサイズ)。`src/image_watermark_trim.py` を参照。

## image step のサイレント失敗対策

`pipeline.py` の images step 完了直後に `ken_burns シーン数 == images/*.png 数` を検証して fail-fast 済み。画像生成中のネット切断・API クォータ枯渇で空画像フォールバック (80-300 KB の極小 visual) が紛れる症状を防ぐ (過去のケースで発覚)。

## 関連

- `docs/04_assets/image-generation.md`: 規約・フォールバック運用の概要
- `docs/04_assets/IMAGE_GUIDE.md`: プロンプト設計の詳細・実例集
- `docs/03_quality/pitfalls.md` の `画像生成` セクション
