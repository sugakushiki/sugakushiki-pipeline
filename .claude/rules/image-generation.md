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
- 不適用: 人物がいるが主題者でない場合は `"is_subject": false` で対応 (no_human ではない)

## 参照が開く条件は prompt の人物判定 — 所有格と「人物なし」で塞いだ

参照写真を使うかどうかは `should_use_reference_photo(global, has_person, scene_use_reference)` で
決まり、**`has_person` は `detect_has_person(prompt)` = キーワードの部分一致**。ここに 2 つ穴があった。

1. **所有格を人物と数えていた。** ある回の prompt が
   `a mathematician's private homage …` の 1 語で門を開き、テラスの絵に**主題者が二重に描かれた**
   (巨大な顔の手前に、同じ人物が奥の席にも座っている)。画像 QA は構図の不一致は指摘したが
   二重像は名指ししなかった
2. **prompt が「人物なし」と明言していても真になっていた** (`no people` と書いてあるのに
   `hair` や `standing` の部分一致で真)

**測定 (出荷 76 話、ken_burns の prompt 1,076 件)**:

| | 件数 |
|---|---|
| `has_person` が真 | 794 (73%) |
| `no_human: true` の宣言 | **2 / 1,076** (逃げ道はあるが使われていない) |
| 危険 (参照あり回 + 参照を切っていない + 人物の絵でない) | 10 |
| 画像を目視した実害 | **0/3** (机の静物・無人の講堂・街の遠景)。実害は ある回の 1 件のみ |

**入れた修正は `detect_has_person` の中だけ**。所有格 (`'s`) で終わる一致を数えず、
`no people` / `no human` / `empty room` 等が書いてあれば偽を返す。判定は 794 → 744 件に。

- **`no_human` や `use_reference` を書き換えてはいけない。** 画像の fingerprint
  (`_prompt_fingerprint`) はその 2 つを見るので、**出荷済み 76 話の画像が再生成される**
- **単語境界 (``) 化は却下。** `Roman ` / `German` の中の `man ` で真になっていた prompt が
  **120 件** False に転び、その中に実際に人物が写る scene (教師が生徒に教える等) が含まれていた。
  部分一致は偶然とはいえ機能している
- 逆方向の誤り (肖像なのに参照を失う) は **ある時点 の safety net** が拾う ──
  「主題者の scene なのに参照が使われなかった」を WARN する経路が既にある。
  出荷 50 件の判定変更のうち、顔の手がかり (portrait / beard / face) を含むものは **0 件**だった
- の [6]

## 脇役人物シーン (is_subject フラグ) — ある回強化

主題者**以外**の人物を描くシーン (脇役・別人物。例: ライプニッツ回の Newton、ヒパティア回の父テオン person_02・弟子シネシオス person_04・歴史家ソクラテス・スコラスティコス person_07) に設定する。

- `visual block` に `"is_subject": false` を設定 (default true)
- 効果: `qa_image_checker.evaluate_consistency` (Gate 2 の主題者 cross-scene 一貫性チェック) の対象から除外する
- 背景: 従来は intro+person 全シーンを「主題者」前提で外見一貫性を評価していたため、別人物の脇役を「同一人物として不統一」と **false positive** で WARN していた
- 判定基準: source_prompt が主題者**以外の特定人物**を描く場合に false。人物のいない風景・静物は no_human または無印 (一貫性チェックは人物不在シーンを問題視しないため必須ではない)
- `use_reference` との違い: `use_reference: false` はリファレンス写真汚染の防止 (画像生成側)、`is_subject: false` は一貫性 QA 除外 (検証側)。主題者に写真がない古代回では全シーン use_reference:false になるため、脇役判別には is_subject が必須
- 後方互換: 無印は is_subject=true。主題者シーンが2枚未満になる場合、一貫性チェックは skip (比較対象なし)

## 主題者 text-only 生成の警告

主題者の参照写真が存在する (`use_reference` global 有効) のに、ある scene が **参照を使わず flash text-only で生成された** 場合に `[WARN] ... 主題者シーンだが参照写真を使わず text-only 生成` が出る。

- 背景: ある回で `has_person` の keyword miss / age 推定失敗 / guard 誤判定により、主題者の portrait scene が参照写真ではなく text-only で生成され「理想化された別人」になる症状が複数発生。guard を force-drop から advisory に demote して主因は解消したが、残存経路 (特に `detect_has_person` が人物描写語を取りこぼす case) を可視化する safety net
- 発火条件: scene が `use_reference=true` + `is_subject=true` + `no_human=false` なのに参照が使われなかった (`ref_active` False か age 推定失敗)
- 対処: その scene が**人物のいない環境/静物**なら `no_human=true`、**脇役の別人物**なら `is_subject=false` (+ 必要なら `use_reference=false`) を明示。**主題者本人**を描くべき scene なら `source_prompt` に人物描写 (顔・半身像等) を補って `has_person` を通す
- WARN-only (生成は続行)。環境 scene に `no_human` を付けていないと false-positive で出るが、その明示自体が望ましい hygiene

**この節が挙げてきた原因は scene 単位のものだけだった。実際に起きた大事故は 2 件とも
「global gate が閉じていて全肖像が text-only」型**で、1 枚ずつ調べても原因に辿り着けない。
肖像が軒並み別人に見えるときは、まず**参照が 1 枚でも生成に届いているか**を見る。

- **config に `birth_year` が無いと参照 gate が丸ごと OFF になる** (`global_use_reference` は
  「参照写真あり **+ birth_year** + flash backend」の AND)。年齢が計算できないので実写参照を
  使わない、という設計上の帰結だが、**config に 1 行足りないだけで全肖像が text-only**
  になる。古代の人物のように生年が本当に不明な場合との区別が付かないのが厄介で、
  `lint_portrait_reference.py` はこの取り違えを名指しするために在る
- **参照写真の拡張子が対応外だと、参照は二段階で消える**。Commons から来た `.gif` が
  `image_generator` の拡張子フィルタで弾かれ、しかも `refs` にも `skipped` にも入らないため
  **fail-loud backstop すら鳴らず**、全 10 枚が text-only で生成された。現在は
  `_transcode_refs_to_png()` が PNG へ変換する。**変換したら credits 側のファイル名も
  一緒に直すこと** — 片方だけ直すと `portrait_prompt_lint` が古い拡張子で弾き続ける
  (**1 つ直して通ったところで止めない**)

## 既存画像のスキップ仕様 / 自動再生成 (staleness 検出)

`image_generator` は既存画像を基本スキップするが、**生成入力の変更を fingerprint で検出して自動再生成**する (`_image_meta.json` に scene 毎の fingerprint を記録)。手動 png 削除は原則不要。

検出対象 (これらを編集すると次回ビルドで該当 scene が `[STALE]` 自動再生成):
- `source_prompt`
- `no_human` / `use_reference` フラグ
- `subject_appearance`

非対象 (narration/写真由来で user 直接編集の範囲外): age 推定・reference 写真選択。

後方互換: fingerprint 記録の無い旧資産や、appearance 追跡前の旧 meta (legacy fingerprint) は **stale 扱いにせず migration のみ** (deploy 時の一斉再生成・既存 curation 破壊を回避)。`.keep` 済み画像は `--force` 以外で常に保護。手動で確実に作り直したい場合は従来通り `--regen` / `--force` / png 削除も有効。

## ステレオタイプ・cliché 注意

`source_prompt` に時代物の cliché（smoking pipes / top hats / wigs / leather-bound volumes 等）を追加する前に web 検索で「その時代・その集団・その場面でこの描写が史実的か」を確認する。

「intellectual gathering = pipe smoking」のような stereotype は史実検証なしに加えてはいけない（過去に集団のパイプ喫煙が史実無しで Gemini に描かせた事例があった）。

### cliche scanner

`src/cliche_scanner.py` が `image_generator.py` の image step 入口で source_prompt の時代物 cliché を自動検出。Layer 1 (辞書ベース、always-on) と Layer 2 (LLM レビュー、`--cliche-llm-review` で opt-in) の 2 層構成。

辞書 `src/cliche_dictionary.json` のカテゴリ: period_accessory / smoking / atmosphere / pose / anachronism / academic_stereotype。

検出時の挙動: WARN のみ (生成は続行)。シーン単位で承認済み cliché を opt-out するには visual block に `"cliche_acks": ["smoking pipes", "top hat", ...]` を設定 (例: 史実検証済の場合は cliche_acks で承認)。

単独実行: `PYTHONPATH=src python -m cliche_scanner episodes/<ep>/scene_definition.json`

## 判読可能テキストと署名の生成時抑止

モデルが画像に描く**読めてしまう文字は常に誤り**である (narration と矛盾する日付・架空の人名・場違いな言語・崩れた紋章文字) うえ、下隅に画家風の偽署名を高頻度で入れる。**事後のぼかしは視聴者に見える** ので、生成時に抑止する:

- `image_generator` が全 source_prompt に **illegible-text/no-signature 節を生成時に自動付与** (fingerprint には入らないので出荷済み画像の一斉 STALE 再生成は起きない)。正当に文字が要るシーンは `visual` に `"allow_readable_text": true` で opt-out
- モデルは指示を無視することがあるため出口検査も残る: `scripts/check_image_signatures.py` (images step で自動、advisory) + post_build_verify のコーナーシート目視
- 誤テキストが出てしまったら**ぼかさず**、「文字は判読不能に」と明示して再生成する。**再生成したら署名を必ず再検査** (新しいロールには新しい署名が入る)

## 紙幣・通貨

法的に再現ルール対象になり得る。間接的（発表会見・報道風）な画像で表現。`source_prompt` に直接 banknote のクローズアップを指定しない。

## AI 生成画像の透かし除去

ChatGPT/Sora 系は BR ✦ スパークル透かしを必ず入れる。手動作成画像を受け取ったら標準的なトリミング+リサイズで除去する (下部 10-13% トリミング → 16:9 中央クロップ → 1920×1080 LANCZOS リサイズ)。`src/image_watermark_trim.py` を参照。

## image step のサイレント失敗対策

`pipeline.py` の images step 完了直後に `ken_burns シーン数 == images/*.png 数` を検証して fail-fast 済み。画像生成中のネット切断・API クォータ枯渇で空画像フォールバック (80-300 KB の極小 visual) が紛れる症状を防ぐ (過去のケースで発覚)。

## 年齢指定と本人性

肖像の年齢ずれ・別人化は、参照写真の有無ではなく **プロンプトの書き方と、参照写真からの年齢の隔たり** で決まる。ある回で person_02/04/06/07 の 4 枚に一斉に過齢化が出て、person_09/closing_03 が別人になった実例から:

- **年齢マーカーは `source_prompt` の先頭に、大文字＋否定形で置く。** 末尾に追記しても効かない。ある回は先頭に `This MUST be a TEENAGER of about NINETEEN ... NO grey hair, NO white beard` を置いて 70 代→19 歳に直ったが、同じ文言を person_03 の**末尾に追記したときは白髪の老人**が出た。既存の `in his early twenties` 程度の穏やかな記述は無視される。
- **「若い」と「顎髭」を同時に要求しない。** 参照写真の髭に引かれて年齢が上がる。19 歳シーンは髭の要求を外して解決した。
- **`use_reference` 未設定は既定 True** (`v.get("use_reference", True)`)。参照ゲートが開いていると全肖像が参照写真の年齢に引かれるので、未設定を「参照なし」と誤解しない (過去の運用知見④)。
- **参照写真の年齢から離れた年代を書く前に、その年代の実像を確認する。** 絵画でもよい。ある回は参照が 36 歳/45 歳の写真だけだったのに、晩年 (60-70 代) の外見を実像を見ずに「豊かな白髪と長い白髭」と想像で書き、白髭の家長風が生成された。実際の Max Liebermann 1912 年の肖像 (63 歳) は「頭頂の髪はまだ濃く、顎髭は短く刈り込まれた白髪まじり、痩せて面長」で正反対だった。**参照に使わないとしても実像は見る。**
- **サムネイルは参照年齢に最も近い肖像を選ぶと本人性が最良になる。** CTR ガイド (`episode-config.md` の「長寿の人物は中年〜晩年の権威的肖像」) と衝突する場合は本人性を優先する。

## 再生成は「改善」ではなく「振り直し」

`--regen` は前の絵を洗練するのではなく、新しくサイコロを振る。**直っている箇所を壊しうる**。ある回で person_03 は critical ではなかったのに、品質を上げようと再生成したら 20 代の 2 人が 60 代の 2 人に退行した。

- critical (別人・ナレーションとの矛盾・誤った焼き込み文字) は直す
- warning 止まりの細部 (隅の薄い署名風ノイズ、数歳の年齢ずれ) を追って回し続けない
- 再生成したら **必ず view して**、直したい点だけでなく**壊れていない点も保たれているか**を確認する

## 年齢推定 (`_estimate_scene_age`) の実装上の罠 — ある回で 4 つ直した

① `late 1940s France` の "40s" を「in his late 40s」と読んで **age=45** を返していた (`(?<!\d)` で修正。出荷済み含む 19 ep 31 肖像が年号の 10 年代から年齢を得ていた)
② 画像規約が推奨する**綴りの年齢マーカー** (`of about TWENTY-TWO`) を誰も解析していなかった (前置詞 of/is/looks を要求して実装。「only about ten mourners」= 人数は除外)
③ 年号引き算の上限が `< 200` で、現代の年号から **122〜189 歳**が出ていた (9 ep 12 scene) → `<= 110`
④ Vision QA リトライの年齢補正が**指摘の方向を見ず常に老けさせて**いた (「22歳のはずが中年に見える」で elderly を積み、5 回目で 70 歳)。**source_prompt の明示 band を最優先**する判定に



## `image_generator.py --output-dir` には episode dir を渡す

images dir を渡すと `images/images/` に生成され、参照写真が一つ上の階層に残るので**警告なく text-only 生成**になる (唯一の手がかりはログの `(flash)` 表示)。ある回で踏んだので `parser.error` で止まるようにした。

## 関連

- `docs/04_assets/image-generation.md`: 規約・フォールバック運用の概要
- `docs/04_assets/IMAGE_GUIDE.md`: プロンプト設計の詳細・実例集
- `docs/03_quality/pitfalls.md` の `画像生成` セクション

## 眼鏡を小道具として置かない

**机やページの上に置かれた眼鏡を prompt に書かない。** 生成モデルは眼鏡のフレームを
安定して描けない ── ある回 `math_06` (1938年の覚書) では、**片方のツルが空中で途切れ、
もう一方がレンズを横切って机の上に浮く**という、フレームとして成立しない絵になった。
掛けている眼鏡より、**置かれている眼鏡のほうが壊れやすい** (顔という支えが無く、
ツルの折れ角とヒンジを自力で決めることになるため)。

- 「知的な机上」の記号が欲しいなら、**万年筆・インク壺・文鎮・封筒・畳んだ新聞**など
  **単純な立体**に置き換える。眼鏡は情報を足さないのに失敗率だけ高い
- 人物が掛けている眼鏡は、参照写真に写っている場合のみ描く。
  参照が素顔なら描かない
- prompt には否定も明示する: `No eyeglasses or spectacles anywhere in the image.`
- **この欠陥は署名検出にも Vision QA にも引っかからない** (署名でもレイアウト衝突でもない)。
  出荷前の目視でしか見つからないので、生成画像を人が見るときに眼鏡があれば必ず拡大する
