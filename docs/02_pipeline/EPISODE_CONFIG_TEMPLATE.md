# episode_config.json テンプレートガイド

episode_config.json の各フィールドの説明とルール。
パイプライン起動時に `config_validator.py` で自動検証される。

## 必須フィールド

欠落または型不一致の場合、パイプラインはERRORで即終了する。

| フィールド | 型 | 説明 | 値の制約 |
|---|---|---|---|
| `episode_id` | string | `NNN_name` 形式（例: `006_shannon`） | `^\d{3}_[a-z_]+$` |
| `mathematician` | string | 英語名 | |
| `mathematician_ja` | string | 日本語名 | |
| `subject_en` | string | 画像検索用の英語名 | |
| `theme` | string | エピソードのテーマ | |
| `title_draft` | string | タイトル案。推奨形式: `名前 ── サブタイトル` | `──` 未含有でWARNING |
| `target_duration_minutes` | number | 目標尺（分） | 5〜22（通常10〜19、深掘り長尺は例外で22まで） |
| `speed_scale` | number | 読み上げ速度 (VOICEVOX speedScale) の per-ep override。 | optional。既定 0.87（`audio_generator.SPEED_SCALE`）。0.5〜1.5 域外は advisory WARN。global 定数を直接編集せずここで指定する |
| `tts` | object | TTS エンジン設定 `{engine, voice, rate}`。`engine`=`"voicevox"`(既定)/`"cloud"`(Google Cloud TTS Chirp3-HD)。`voice`(cloud のみ、既定 `ja-JP-Chirp3-HD-Enceladus`)、`rate`(cloud speakingRate、既定 0.90、0.25〜4.0 域外は advisory WARN) | optional。**未指定=voicevox で完全後方互換**。CLI `--tts-engine/--tts-voice/--tts-rate` で一時上書き可。cloud は VOICEVOX GUI 不要 (`GOOGLE_TTS_API_KEY` が要る)、読みは scene_def の `narration_speech_cloud` で調整、QA は Gemini STT (`scripts/stt_qa.py`)。ロールバックは `engine` を `voicevox` に戻して再ビルド |
| `hook` | string | フック（冒頭ナレーション案） | |
| `key_topics` | string[] | 主要トピック | 空配列不可 |
| `modern_connection` | string | 現代との接続 | |
| `key_episodes` | string[] | 主要エピソード | 空配列不可 |
| `references` | string[] | 参考文献リスト | 空配列不可 |
| `verified_facts` | **object** | 検証済み事実（キー: ラベル、値: scalar または `{fact, source}` dict） | **listは不可（過去にクラッシュ）**。値の新形式 `{"fact": ..., "source": "..."}` を推奨 |
| `bgm` | object | BGM設定 `{file, title, artist, source, volume_db, ...}` | `bgm.file` 未設定でWARNING |
| `additional_instructions` | string | スクリプト生成への追加指示 | |
| `common_errors_to_avoid` | string[] | ナレーション生成時に避けるべき事実誤認 | |

## 推奨フィールド

未設定の場合WARNINGが表示されるが、パイプラインは続行する。

| フィールド | 型 | 説明 | 未設定時の影響 |
|---|---|---|---|
| `subject_appearance` | string | 人物の外見描写（英語）。**体格（thin/medium/heavy等）を必ず含めること** | 画像生成の体格チェックが機能しない |
| `appearance` | object | 年代別外見 `{young, middle, old}` | 年齢変換生成の精度低下 |
| `description` | object | YouTube概要欄設定 `{intro_guidance, tags_guidance}` | credits_generatorのチャプター・タグ生成が弱くなる |
| `pronunciation_high_risk` | string[] | VOICEVOX誤読しやすい語のリスト | 誤読チェックが汎用ルールのみになる |

## その他のオプションフィールド

バリデーション対象外。存在すれば使用される。

| フィールド | 型 | 説明 |
|---|---|---|
| `birth_year` | number | 生年（Wikimedia写真の年代マッチングに使用）。**実写参照ゲートの必須条件**でもある — 未設定だと `use_reference` が常に False になり、写真を取得済みでも一切 Gemini に渡らず全肖像が text-only 生成になる（silent。`lint_portrait_reference` が WARN） |
| `death_year` | number | 没年。**画像クレジットの参照呼称**に使う（<1840 = 写真技術以前 → 「肖像画」、以降 → 「肖像写真」。Guard-C）。未設定は「肖像写真」に倒れるので、写真以前の人物では絵画を「写真」と誤記する（ある回ラプラスで発生） |
| `portrait_reference_kind` | string | 上記の没年ヒューリスティックの **override**（例 `"肖像"` / `"画像"`）。参照が絵画と写真の混在（ある回ハミルトン）や、そもそも肖像でない画像（ある回オイラー＝望遠鏡写真）で使う。未設定なら従来動作 |
| `math_content` | string[] | 数学パートの構成指示 |
| `chronology` | object[] | 年表 `[{year, event}]`。存在する場合、各要素に `year` と `event` キーが必須 |
| `image_strategy` | object | 画像生成戦略 |
| `thumbnail` | object | サムネイル設定 `{phrase, math_symbol}` |
| `available_manim_templates` | any | 利用可能なManimテンプレートのリスト |
| `wikimedia_photo_urls` | string[] | Wikimedia写真の手動URL指定（flat list 形式必須、dict 形式は `KeyError: 0` クラッシュ。自動検索のフォールバック） |

## 廃止予定フィールド

| フィールド | 状況 | 移行先 |
|---|---|---|
| `mathematician_native` | 一部の旧エピソードに存在するが未使用 | 削除可 |
| `tags` | 旧エピソードに残存 | `description.tags_guidance` |
| `voicevox_dictionary_additions` | 旧エピソードに残存 | `voicevox_dict.json` に統合済み |
| `credits` | 旧エピソードに残存 | `credits_generator.py` が自動生成 |

## pronunciation_high_risk の例

```json
"pronunciation_high_risk": [
  "開と閉 → 「かいとへい」",
  "表か裏か → 「おもてかうらか」",
  "今日 → 「こんにち」（現代の意味の場合）",
  "AND → 「アンド」",
  "中嶋章 → 「なかしまあきら」"
]
```

config作成時（企画段階）に高リスク項目を事前にリストアップすること。

## subject_appearance の例

```json
"subject_appearance": "thin face, thin build, slender frame throughout life, short dark hair in youth, white hair in old age, playful grin, American male"
```

体格情報は画像生成の Vision QA で自動チェックされる。

## フィクション題材の取り扱い (例: examples/moriarty/)

実在しない人物を題材にする場合の運用上の注意点:

- **`subject_en` の同名異人ヒット**: Wikimedia 自動検索で実在の同名異人写真がヒットする場合がある (例: 架空の Professor James Moriarty 検索で米空軍 / 国務省の同名人物がヒット)。`scene_definition.json` の visual block に `"use_reference": false` を明示することで参照汚染を回避
- **`wikimedia_credits.json` の空構造化**: 同名異人ヒット時は `{}` で commit して `description.txt` のクレジット混入を回避
- **`pre_script_fact_check` の content filter**: フィクション題材 (推理小説の犯罪要素等) で API content filter がブロックする場合は `--fact-check-allow-warn` で続行
- **`image_generator` 年代抽出のヒューリスティック**: narration 内の年号 (実在の出来事の参照等) から目標年齢を算出するため、フィクション人物に意図しない年齢が出る場合あり。narration から年号言及を削除する workaround で対応

## バリデーションルール一覧

`src/config_validator.py` で自動検証される全ルール。

### ERROR（パイプライン停止）

| ルール | 対象 |
|---|---|
| 必須フィールド欠落 | 上記16フィールド |
| 型不一致 | 各フィールドの期待型と実際の型 |
| `episode_id` 形式不正 | `^\d{3}_[a-z_]+$` にマッチしない |
| `target_duration_minutes` 範囲外 | 5未満または22超 |
| `verified_facts` がlist | dict以外の型（過去にAttributeErrorクラッシュ） |
| `key_topics` が空配列 | |
| `key_episodes` が空配列 | |
| `references` が空配列 | |
| `chronology` 構造不正 | 存在する場合、各要素に `year`/`event` キーが必要 |

### WARNING（表示のみ、続行）

| ルール | 対象 |
|---|---|
| `title_draft` に `──` なし | 推奨形式: `名前 ── サブタイトル` |
| `bgm.file` 未設定 | BGMなしでビルドされる |
| 推奨フィールド未設定 | `subject_appearance`, `appearance`, `description`, `pronunciation_high_risk` |
| `verified_facts` に legacy scalar | 出典記録のため新形式 `{fact, source}` への移行を推奨 |
| `verified_facts` の dict 形式値で `source` 欠落 | 出典 URL / 書籍ページの記載を推奨 |

## verified_facts の新形式

出典明記化のため、`verified_facts[key]` の値を以下のいずれかに:

```json
"verified_facts": {
  "birth": {"fact": "1802-08-05 Kragerø, Norway",
            "source": "MacTutor / Abel Prize biography"},
  "death": {"fact": "1829-04-06 Froland",
            "source": "https://mathshistory.st-andrews.ac.uk/Biographies/Abel/"},
  "age_at_death": 26,            // legacy scalar (str/int/float/bool) も後方互換
  "_note": "..."                 // _ で始まるキーは検証対象外 (documentation 用)
}
```

利点:
- QA が事実を指摘した時、`source` を直接参照して正誤判断できる
- 出典 URL を `source` に貼ることで再検証コストが下がる
- 旧 21 ep の legacy scalar 形式は WARN のみで動作、段階移行可能

consumer (pre_script_fact_check.py / wikimedia_fetcher.py / image_generator.py) は
`config_validator.get_verified_fact_text(value)` ヘルパーで両形式を透過的に扱う。
