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
- **`description.intro_guidance` で「この一文を入れる」と決めた要素は `description.intro_required_phrases` にも書く** (ある回: guidance が求めた R(5,5) の一文が生成 intro に無く、user の再確認まで誰も気づかなかった。staleness 検査 も intro-semantic も「要求が満たされたか」は見ない)。credits step が intro 本文と照合して無ければ WARN する (narration の `required_phrases` と同じ型)。`description.notes` も同様に scene_definition 側へコピーされ credits はそちらを読むので、config だけ直したら scene_definition も直す (食い違えば credits が WARN)
- **導入系フィールド（`theme` / `hook` / `modern_connection` / `description.intro_guidance`）を後から編集したら `scene_definition.json` の `description.intro` も見直す**。intro は自動同期されないので、放置すると古い導入文が公開概要欄に焼かれる（`check_description_staleness.py` が検出。据え置くと決めたなら `--accept` で再刻印）

## `pronunciation_high_risk` は読み辞書であって禁止リストではない

**「この語は使わない」と `pronunciation_high_risk` に書いても台本生成には一切効かない。** あの欄は TTS の読みを記録する場所で、script_generator は禁止語として扱わない。

ある回は `"一行 → 使わない(いちぎょう と いっこう が割れる)"` と書いてあったのに LLM が「論敵の一行の誤り」と書き、Chirp が いっこう と読み、**user が通し視聴で耳で見つけた**。

- 避けたい語は **`forbidden_phrases`** に入れる (smoke 18 が user-facing への漏れを照合する)
- 読みを固定したいだけなら `pronunciation_high_risk` に読みを書く
- 両方が必要なこともある (語を出したくないが、出てしまったときに備えて読みも記録する)
- smoke test **section 18d** が「避けると書いたのに `forbidden_phrases` に無い語」を WARN する

## 年齢は「月が特定できる出来事」にだけ付ける

**月が分からない出来事に「N歳」を書かない。** 満年齢は誕生日の前後で 1 違う。

ある回は 3 か所間違えたまま音声まで焼いた (生 1842年12月17日):

- 「1870年8月の逮捕時に 28 歳」→ **満 27 歳**
- 「1868年、リーが 26 歳のとき」→ 1868 年の大半は **満 25 歳**。しかも典拠に月が無い
- 「1872年…30 歳のことです」→ 学位は 7 月なので **満 29 歳**

**LLM の QA が挙げたのは 1 件だけ**だった。生年から全件を手で照合して残り 2 件が出た。
config の `hook` / `key_topics` に書いた年齢がそのまま narration に流れるので、**config を
書く時点で誕生日と突き合わせる**こと。月が特定できないなら「大学を出て三年後」のように
年齢を使わない書き方にする。

**自動検査は作らないこと。** 2026-08-19 に「narration の N歳 を生年から算術照合する」検査を
実装して 67 話で較正したが、**ERROR 18 / WARN 133 のほぼ全部が偽陽性**だった。原因は
**「N歳」が主題人物を指すとは限らない**こと (カントール回の息子 13 歳、ゲーデル回の恩師
ハーン 54 歳、ラプラス回のナポレオン 16 歳、バナッハ回の母 25 歳…)。主題の生年で他人の
年齢を照合しているので当然合わない。`check_route_places` の地名辞書照合が真1/偽4 で
不採用になったのと同じ型で、**この精度の検査は「また誤発火」を学習させて lint 全体の
信用を壊す**。ここは上の一文を人が守る。

## `description.notes` は「本編に入れられなかった限定」だけ

**判定は一つ。「本編を最後まで見た人が、それでもなお知らないことか」。** 満たさないなら書かない。

この欄は ある回で「本編で言うと文が重くなるが、言わないと定理を過大に述べたことになる限定」の
置き場所として作られた。手本は ある回 (『一番良い答えは必ず角に来る』→ 正確には『最適解の
**少なくともひとつ**が角にある』) と ある回 (『独立でなくても大数の法則は成り立つ』の正確な意味・
収束の成立条件・2万文字は詩の約1/8)。どちらも本編の主張を名指しして限定している。

**放っておくと膨らむ。** 裏を取るほど書きたくなり、書けば書くほど誠実に見えるからである。実測で
ある回が 11 項目 1562 字、ある回が 8 項目 1160 字、**ある回は 10 項目 1490 字でそのうち 9 項目が
本編の再掲か調査ログだった**。2026-08-19 に 4 話から計 13 項目 (約 2800 字) を削除した。

崩れ方は必ずこの 2 型のどちらかになる:

- **型1「資料が割れる」系**: 「スーシンの没日は MacTutor と Wikipedia で異なる」— **本編はどちらの
  日付も言っていない**。言っていない主張に限定は要らない。これは調査ログであって視聴者向けの
  情報ではない。**置き場所は `verified_facts` の `source`** (そこには取得日つきで残る)
- **型2 再掲**: 本編が既に語っていることを概要欄でもう一度書く。書く前に **narration を grep する**
  こと。ある回は 10 項目中 6 項目がこれだった

**注が 1 件しか残らないのは script の失敗ではなく成功である** — 限定を本編に入れ込めたから注に
書くことが残らなかった。残らなかったものを埋めて水増ししない。

**決定論検査は置いていない。** 「本編に既出の語の割合」で自動判定を試したが、ある回で残すべき
1 項目 (ピカール–ヴェシオ) を「手順」と誤判定し、ある回の残すべき項目も既出率 100% と出た。
`check_route_places` の地名辞書照合が真1/偽4 で不採用になったのと同じ理由で、**語が在るかと
「その限定が必要か」は別問題**。ここは人が上の一文で判断する。

## `cloud_reading_overrides` — その回だけの固有名の読み

engine=cloud の回で、**その回にしか出ない固有名 (地名・人名・書名)** の読みを SSML
`<phoneme alphabet="yomigana">` で固定する `{表層: よみ(かな)}` の辞書。
グローバルの force 辞書 (`cloud_tts._READING_OVERRIDES`) に入れるほど汎用でない語の置き場。

```json
"cloud_reading_overrides": { "場合": "ばあい", "干支": "えと" }
```

- **グローバル辞書が優先**される (較正済みの読みを ep 側に壊させない)
- 上書き語を**含む文だけ**が SSML になる。含まない文はバイト単位で不変 = キャッシュも副作用も動かない
- 値は**かなだけ** (が検査)

**どちらの層を使うかは語の性質で決まり、机上では決められない**:

| 手段 | 効く語 | 壊れる語 |
|---|---|---|
| `narration_speech_cloud` に**かなを直書き** | **固有名・術語** (秦九韶 / 序 / 都 / 臨安) | 短い機能語 —「ばあい」は**「ば・あい」と割れ**、「えと」は**「えーっと」**になる |
| **SSML `<phoneme>`** (この辞書) | 短い機能語、多くの術語 | **固有名で honor されないことがあり、しかも非決定** (同じ「秦九韶」が scene によって バダ急症 / シンキョウショウ に割れた) |

**ある回から自動化**: `cloud_reading_overrides` の表層が **3 文字以上**なら `gen_cloud_readings` が cloud 文にかなで直書きし (術語・固有名の経路)、2 文字以下だけ SSML に残す。手で書いた `narration_speech_cloud` は保存されるので、既存の cloud に漢字が残っている語は従来どおり SSML。

**どちらも不安定な語 (には) は、語そのものを使わない書き換えが唯一の解**。
**必ず 1 文だけ合成して STT で確かめてから決める** (15 秒。フルビルド 50 分を回してから
「まだ直っていない」と報告しないため)。詳細過去の運用知見。

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

## `cloud_direct_kana` — 短い語をかな直書きにする opt-in

`cloud_reading_overrides` の語のうち **2 文字以下は既定で SSML** に残る (場合/干支 は直書きすると
「ば・あい」「えーっと」と割れる)。ところが 弦 (1 文字) と 一片 (2 文字) は SSML が honor されず
(ケン/キリ、いっぱた)、cloud 文にかなを直書きして直った。語ごとに `cloud_direct_kana: ["弦", "一片"]`
と挙げると、`gen_cloud_readings` が長さに関係なく直書きにする。ただし 1〜2 文字の語は**漢字に挟まれた位置には当てない** (正弦 / 弦楽器 は残り SSML のまま。再検証で「正げん」になった) ので、複合語の読みを変えたければ複合語自体を overrides に書く。**挙げる語は overrides にも要る**
(無ければ config_validator が WARN)。1 文字キーは SSML の表層一致で複合語 (角→三角級数、表→表せる)
まで変えるので、1 文字語は必ずこちらへ。

**後から足しても既存の cloud 文には効かない**: `gen_cloud_readings` は既に
`narration_speech_cloud` がある scene を温存する (手で直した読みを守るため) ので、生成後に
`cloud_direct_kana` や 3 文字以上の overrides を足しても、その scene の cloud は変わらない = no-op。
audio ステップの `[GEN-CLOUD][WARN] 既存の narration_speech_cloud を温存した N scene に…` が
scene と語を名指しするので、`python scripts/gen_cloud_readings.py <scene_def> --force` で全 scene を
作り直すか (手で直した読みも消える)、当該 scene の cloud だけ手で直す。
