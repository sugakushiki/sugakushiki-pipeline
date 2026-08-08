---
paths:
  - "**/episode_config.json"
---

# episode_config.json — 編集時の規約

## 構造

- `verified_facts`: **dict 形式 `{}`** で書く（list は `config_validator.py` でクラッシュ。過去のケースで発覚した list-vs-dict 互換問題）
- `verified_facts` の値は **scalar (str/int/float/bool)** または **`{"fact": ..., "source": "..."}` dict**。新規エピソードは新形式 (出典付き) を推奨、legacy scalar は WARN のみ
- `wikimedia_photo_urls`: **flat list 形式** `["url1", "url2"]`（dict 形式は `KeyError: 0` を起こす、過去のケースで発覚）
- 新フィールド追加時は `.get()` でデフォルト値を取って後方互換性確保

## 起動時の検証

- `config_validator.py`: `verified_facts` の型を起動時に検証
- **事前事実チェック (`pre_script_fact_check.py`)**: `verified_facts` / `key_episodes` / `theme` / `key_topics` を script step 直前に Claude Sonnet 知識ベース + 算術サニティ + Wikidata SPARQL で検証。CRITICAL/WARNING で停止。`--skip-fact-check` / `--fact-check-allow-warn` で制御
- 同じ実行で `references` の書誌 attribution も review されるが、**こちらは advisory** で
  ブロック判定には混ざらない (`--skip-reference-check` で無効化)。指摘は Web で裏取りしてから直す

## 編集時の注意

- **年齢・年月日・職業・人物関係**は web verify してから書く（事前事実チェックで fail-fast されるが、自分で書く時点で誤認を避ける）
- `common_errors_to_avoid` に「連続性誘導 NG（前回・次回・続編 等）」「stereotype NG」を含める
- `references` の書誌情報は publication 前に Web 検索で著者名・書名・出版年を裏取り（`credits_generator.py` が URL 死活監視 `validate_reference_urls()`、事前事実チェックが書誌 attribution の advisory review を実施するが、**最終的な正確性の判断は人間**）
- `birth_year` / `death_year` は**書かないと黙って挙動が変わる**: 前者が無いと実写参照ゲートが閉じて全肖像が text-only 生成になり、後者が無いと画像クレジットの参照呼称が「肖像写真」側に倒れて絵画を写真と誤記する。呼称のヒューリスティックが合わない回（参照が絵画と写真の混在など）は `portrait_reference_kind` で明示 override する
- **導入系フィールド（`theme` / `hook` / `modern_connection` / `description.intro_guidance`）を後から編集したら `scene_definition.json` の `description.intro` も見直す**。intro は自動同期されないので、放置すると古い導入文が公開概要欄に焼かれる（`check_description_staleness.py` が検出。据え置くと決めたなら `--accept` で再刻印）

## `pronunciation_high_risk` は読み辞書であって禁止リストではない

**「この語は使わない」と `pronunciation_high_risk` に書いても台本生成には一切効かない。** あの欄は TTS の読みを記録する場所で、script_generator は禁止語として扱わない。

ある回は `"一行 → 使わない(いちぎょう と いっこう が割れる)"` と書いてあったのに LLM が「論敵の一行の誤り」と書き、Chirp が いっこう と読み、**user が通し視聴で耳で見つけた**。

- 避けたい語は **`forbidden_phrases`** に入れる (smoke 18 が user-facing への漏れを照合する)
- 読みを固定したいだけなら `pronunciation_high_risk` に読みを書く
- 両方が必要なこともある (語を出したくないが、出てしまったときに備えて読みも記録する)
- smoke test **section 18d** が「避けると書いたのに `forbidden_phrases` に無い語」を WARN する

## thumbnail.source_image 選定指針

`thumbnail.source_image` は scene_definition.json に存在する scene 名 (`person_NN.png` 等) を指定する。視聴者の YouTube クリック率に直結するため、**人物の業績ピーク時期** + **視覚的訴求** + **軸 (theme) の象徴**で選ぶ:

- **早世の人物** (主たる業績期に集中): ガロア (20 歳)、アーベル (26 歳)、リーマン (39 歳)、ラマヌジャン (32 歳)、ゲーデル (青年期の業績で表現も可)
  → 業績ピーク時期の scene を選択 (例: ガロア 1832 決闘前、アーベル 5次方程式の証明期)
- **長寿の人物** (長い業績期): ライプニッツ (70 歳)、ガウス (77 歳)、オイラー (76 歳)、デカルト (54 歳)
  → **威厳ある中年〜晩年期** (40-50 代の権威的肖像) を推奨。若年期は CTR が下がる傾向
- **業績で特定時期に特化**: ニュートン (青年期 Principia)、ゲーデル (24 歳不完全性定理)
  → 業績期の scene を選択
- **古代・近代以前** (実在の肖像が伝わらない): アルキメデス、ピタゴラス、マーダヴァ、エラトステネス
  → 軸を最も象徴する物体・場所の scene (例: アルキメデス王冠浮力、マーダヴァ ケーララ写経)
  → **代替候補**: intro_NN に「想像肖像」(use_reference: false で Gemini 直接生成された Hellenistic/古代風スカラー像) が生成されている場合は **portrait を CTR 優先で検討**する。ある回で当初 math_03 (Nile map atmospheric) を選択したが、軸「地球を測った男」を視聴者に直接伝える観点では intro_03 (Eratosthenes 図書館肖像) の方が認知性が高い。古代でも portrait 候補があれば map/landscape より先に検討する

選定時の確認: 視聴者が thumbnail で「人物・テーマを認識できる」場面か。若年期の独学少年や晩年の病床は narrative では強いが、CTR では弱い場合あり。最終判断は `verified_facts` の業績年代と `key_episodes` のピーク時期を見て決める。

## スキーマ詳細

詳細は `docs/02_pipeline/EPISODE_CONFIG_TEMPLATE.md` 参照。

## 関連

- `docs/03_quality/pitfalls.md` の `pipeline / config` および `事実誤認 / 史実考証` セクション
- `docs/03_quality/qa.md`: pre-script fact check のフラグ詳細
