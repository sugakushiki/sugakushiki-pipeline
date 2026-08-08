# QA 運用

> pipeline 実行時の QA フラグと運用ルールを集約する。
> 関連:
> - [`docs/architecture.md`](../architecture.md) §4: QA を 3 層 (合成前の予防 / 合成後の検出 / 出荷物の検証) で捉えた全体像
> - [`QA_PIPELINE.md`](QA_PIPELINE.md): QA 5 エージェントのプロンプト設計詳細
> - [`QA_INTEGRATION_GUIDE.md`](QA_INTEGRATION_GUIDE.md): QA 結果の手動修正ガイド
> - [`cloud_tts_qa.md`](cloud_tts_qa.md): Cloud TTS 回の読み・速度 QA の層別チェックリスト
> - [`STYLE_GUIDE.md`](STYLE_GUIDE.md): QA が参照するスタイル基準
>
> 本ファイルは「実行時の運用とフラグ」、関連 docs は「設計詳細・修正手順」を扱う。

---

## アプローチ

**QA レポートは人間が読んで判断する。自動修正はしない。**

- **アプローチ A (デフォルト)**: QA レポート → 人間が手動修正
- `--qa-retry` (LLM に書き直させる) は critical が多い時だけの opt-in
- severity 判定: 数学的厳密性に関わるものは warning 以上

### 止まるか進むかは「判定が決定論的か」で決まる

- **非決定的な判定は advisory** — STT の書き起こし、Vision の意味判定、速度の実測値。
  誤検出に引きずられて正しい出力を壊すほうが損失が大きいので、警告だけ出して進む
- **決定論的な構造ガードは中断** — スキーマ、必須 params、bbox 衝突、白帯の画素比、
  timing 署名。誤検出がほぼ無く、見逃すと後段で修正できない
- **LLM QA Gate は例外的に中断する** — 非決定的だが、捕まえるのが*内容の誤り*で、
  出荷後に気付いても動画を作り直すしかないため。`--qa-allow-warn` /
  `--fact-check-allow-warn` で「設計判断として受け入れる」場合に通せる

---

## 中断するガードと escape

内容に関わるガードで pipeline が止まるのは以下。**escape を付けるのは
「その指摘を理解した上で意図的に進める」場合だけ**にする。

| ガード | 止まる条件 | escape |
|---|---|---|
| `config_validator` | スキーマ / 値域エラー | なし (config を修正する) |
| 事前事実チェック | CRITICAL | なし (config を修正する) |
| 事前事実チェック | WARNING | `--fact-check-allow-warn` |
| QA Gate 1 (script) | critical | なし (narration を修正する) |
| QA Gate 1 (script) | warning | `--qa-allow-warn` |
| QA Gate 2 (画像↔narration) | critical | なし (画像を再生成する) |
| 再利用テンプレの必須 params 欠落 | `timeline_recap` 等で params が空 | `--allow-empty-template-params` |
| route_map 衝突 preflight | title / label / legend の bbox 重なり・枠外はみ出し | `--allow-route-collision` / `--auto-fix-route-collisions` / `--skip-route-preflight` |
| レンダ動画の白帯 | 外周の白帯が 8% 以上 | `--allow-video-borders` |
| stale visual (assemble 直前) | visual mp4 の尺が timing.json と不一致 | `--allow-stale-visuals` |
| stale subtitle (assemble 直前) | narration hash / timing hash が subtitles.srt と不一致 | `--allow-stale-subtitles` |

環境系の preflight (Python モジュール / Claude CLI 認証 / VOICEVOX サーバ /
Cloud TTS キー) も欠けていれば即座に止まる。escape は Claude CLI 認証の
`--skip-auth-probe` だけで、他は用意していない。

> **Claude CLI 認証はビルド途中でも失効する**。長時間ビルドの最中に OAuth
> セッションが切れると、以降の `claude -p` を使う QA (LLM QA agents / 画像・Manim の
> Vision QA / 概要欄の意味レビュー) が**一斉に沈黙する** — 各呼び出し元が
> graceful degrade する設計なので、ビルドは "green" のまま終わってしまう。
> このため認証 ping は起動時 preflight だけでなく、**Vision QA の直前**
> (ビルド開始から ~40 分 = 失効しやすい時刻) にもう一度走る。失効していれば
> 該当 QA を skip した上で、最終サマリに「N 件の QA を skip した。再認証して
> 再実行すること」を出す。判定は positive signal (healthy な ping は `pong` を
> 返す) で行い、401 の文言マッチには依存しない。
> **恒久策は運用側**: 長時間ビルドの前に `claude setup-token` (1 年 OAuth) を
> 設定して失効の頻度そのものを下げる。

> **空 params と stale の escape は特に慎重に**。前者は他エピソードのデータを
> 黙って描画し (テンプレの self-test 既定値が出る)、後者は音声と映像・字幕が
> ずれたまま完成する。どちらも出来上がった動画を見るまで気付きにくい。

---

## フラグ一覧

### QA Gate

| フラグ | 既定 | 内容 |
|---|---|---|
| `--qa` | **ON** | script 生成後に QA を実行 (全エージェント) |
| `--skip-qa` | off | QA を全て skip (Gate 1 + Gate 2) |
| `--skip-qa-script-only` | off | Gate 1 だけ skip。Gate 2 は走る。narration 不変で asset だけ変えた部分再ビルド向け |
| `--skip-qa-image-narration` | off | Gate 2 (画像↔narration 整合) だけ skip |
| `--qa-quick` | off | Sonnet エージェントのみの簡易 QA |
| `--qa-agents` | 全件 | 実行するエージェントを指定 (カンマ区切り、例 `fact,style`) |
| `--qa-allow-warn` | off | WARN でも続行 (critical は止まる) |
| `--qa-retry` | off | 指摘があれば script を再生成して比較 |
| `--qa-max-diff` | 0.2 | `--qa-retry` が許容する差分率の上限 |

Gate 2 は image step **後**に走り、5 つの観点で判定する:
主要人物の有無 / 人物の性別 / 人物の人数 / 活動・小道具 (ステレオタイプ) / 細部。
レポートは `episodes/<id>/qa_report_images.json`。

### 事前事実チェック

`episode_config.json` の内容を script 生成**前**に検証する。C (Claude 知識) +
D (算術サニティ) + E (Wikidata 照合) + F (references の書誌 review) の 4 層。

| フラグ | 既定 | 内容 |
|---|---|---|
| `--skip-fact-check` | off | 事前事実チェック自体を skip |
| `--fact-check-allow-warn` | off | WARNING で止まらず続行 (CRITICAL は止まる) |
| `--use-gemini-fact` | off | Gemini Grounding (web 検索あり) で照合する |
| `--skip-reference-check` | off | F 層 (references 書誌 review) だけ skip |

- レポート: `episodes/<id>/pre_script_fact_check_report.json`
- Claude の結果はキャッシュ: `_pre_script_fact_cache.json`

**F 層だけは advisory で、他の 3 層と混ざらない。** `references` は書籍・論文の
自由記述引用なので、誤りの中身は著者・書名・出版年・出版社・訳者の attribution に
出る。決定論 API (Google Books / Open Library) での照合は実測で偽陽性を潰せなかった
— 実在する書籍が未収録で 0 件になる、復刻版の年で年比較が外れる、ISBN がほとんど
付いていない。そこで版・翻訳・掲載誌を推論できる LLM に寄せ、代わりに次の制約を
掛けている:

- 高確信のものだけを挙げ、確信が無ければ PASS する
- **正しい値を断定しない** (`correction` は書かない)。人間の web 照合を促すに留める
- 掲載誌・非英語・古い一次資料を「存在しない」と断じない
- URL だけの reference は対象外 (URL の到達性検証に委ねる)
- 結果は `report["reference_advisory"]` に隔離し、ブロック判定源の
  `report["issues"]` には**混ぜない** → warning でもビルドは止まらない

指摘は**必ず一次資料で web 照合してから**反映する。鵜呑みにしない。

### 読み・音声

| フラグ | 既定 | 内容 |
|---|---|---|
| `--check-pronunciation` | `--qa` で自動 ON | 合成前に Claude で VOICEVOX の読みを確認 (**voicevox 専用**) |
| `--skip-pronunciation-check` | off | `--qa` が有効でも読み確認を skip |
| `--skip-reading-guard` | off | 合成前の誤読 guard を skip (**voicevox 専用**、advisory) |
| `--normalize-cloud-speed` | off | Cloud 合成後に文単位の発話速度を median へ atempo 正規化 (**cloud 専用**) |

- **`--normalize-cloud-speed` は検出ではなく修正の opt-in**。検出 (`speed_qa_report.txt`)
  は常時走る。取り消しは `cloud_speed_qa.py --restore`
- Cloud 回の読み検証 (`cloud_reading_lint` / `stt_qa`) は skip フラグを持たず常時 advisory
- **`--pronunciation-dry-run` は pipeline のフラグではない** — `audio_generator.py`
  を単体実行するときのフラグで、修正提案だけ表示して `scene_definition.json` を
  変更しない。pipeline 経由では使えない

### 画像・映像のガード

| フラグ | 既定 | 内容 |
|---|---|---|
| `--skip-portrait-lint` | off | 肖像と source_prompt の特徴矛盾 lint を skip (advisory) |
| `--allow-video-borders` | off | レンダ動画の白帯 8% 以上でも中断しない |
| `--skip-route-preflight` | off | route_map 衝突 preflight を skip (レンダ中の WARN は残る) |
| `--skip-route-place-check` | off | ナレーションの地名が route_map に在るかの advisory review を skip (Claude・cache 付き・ビルドは止めない) |
| `--allow-route-collision` | off | 衝突を検出しても中断しない (advisory 化) |
| `--auto-fix-route-collisions` | off | 4 段の自動修復を試す (ラベル退避 → bounds 拡張 → title 縮小 → legend 再配置)。`scene_definition.json` を書き換え、`_route_map_auto_fix_log` に記録する |
| `--allow-empty-template-params` | off | 再利用テンプレの params が空でも続行 |

### アセンブリ直前の stale 検出

| フラグ | 既定 | 内容 |
|---|---|---|
| `--allow-stale-visuals` | off | visual mp4 が現在の timing より古くても assemble する |
| `--allow-stale-subtitles` | off | subtitles.srt が現在の narration / timing より古くても assemble する |

**読みや速度を変更したら `--steps` に `subtitles` を含める。** narration の文面が
変わらなくても、読みの修正や速度正規化で音声尺が変われば字幕のタイムスタンプは
古くなる。この場合 text hash は一致するので、timing 署名の側で検出される。

### 概要欄 (description) のガード

`scene_definition.json` の `description.intro` は公開 YouTube 概要欄の【導入】に
そのまま焼き込まれる。script 生成時に LLM が書いた文がそのまま残るため、**後から
入力を直しても intro だけが取り残される**方向の drift が 2 つある。どちらも
advisory で、`credits` step (焼く当のステップ) と完了後の出力検証の両方で照合する。

| 種別 | 何を見るか | 判定 | フラグ |
|---|---|---|---|
| config → intro (staleness) | episode_config の導入系フィールドを編集したのに intro が生成時のまま | 決定論 (署名 + hash) | escape なし (`--accept` で明示的に受け入れる) |
| narration → intro (意味一致) | 本編にある数学的前提条件・限定詞を intro が落として不正確化 | Claude (advisory) | `--skip-intro-check` |

**config → intro** は署名方式で見る。生成時に `_description_meta.json` へ
「導入系 config フィールド (`theme` / `hook` / `modern_connection` /
`description.intro_guidance` の 4 つ) の署名」と「intro テキストの hash」を刻印し、
照合時は **config 署名が変化 AND intro テキストが刻印時から不変**の両方が成立した
ときだけ WARN する。intro を手で直せば hash が変わって自動的に黙るので、手動同期の
あとに WARN が居座らない。intro は短い要約・`intro_guidance` は長い手書き指示なので
**内容の類似度では分離できない** (同期済みの回でも ratio が 0.05〜0.5 に散らばる)。
署名方式が唯一の道だった。対象フィールドを 4 つに絞ってあるのは、`references` や
`bgm` の編集で誤発火させないため。sidecar が無い回 (出荷済み) は no-op。

```bash
python scripts/check_description_staleness.py episodes/XXX
```

config を直したが intro は意図して据え置く、という判断をしたときは `--accept` で
再刻印して WARN を解消する。

**narration → intro** は Claude の advisory review。既存の 6-gram 表層チェック
(`qa_checker._detect_description_drift`) は言い換えで表層が変わると意味 drift を
取りこぼすので、そこを埋める層になる。要約による省略それ自体は問題にしない
(人名・年号・背景を落とすのは正常)。挙げるのは**本編が持っている限定詞を落とした
結果、記述が数学的に誤りになる**ものだけ。でっち上げ防止の接地として、指摘には
`narration_evidence` = その限定詞を含む本編該当文の引用を必須にしてある (本編に
実在しない限定詞は報告できない)。結果は intro + narration の hash でキャッシュされ、
内容が変わるまで Claude を呼ばない。

```bash
python scripts/check_intro_semantic.py episodes/XXX
```

`credits` step が Claude を呼んでキャッシュし、完了後の出力検証はキャッシュを
読むだけ (安い)。**修正するかどうかは人間が本編と照合して決める。**

### 環境・認証

| フラグ | 既定 | 内容 |
|---|---|---|
| `--skip-auth-probe` | off | Claude CLI 認証 ping (起動 preflight + Vision QA 直前の再確認) を skip。オフライン / Claude を使わない mechanical な再ビルド向け |
| `--no-keep-awake` | off | ビルド中の system sleep 抑止を無効化 (Windows のみ有効、他 OS では no-op) |

`--no-keep-awake` を外した既定では、pipeline 起動時に system sleep を抑止し
終了時に解除する。長時間ビルドが OS のスリープでプロセスごと落ちるのを防ぐ。

### ビルド完了後

`output_final.mp4` が存在する run の最後に、構造検査 11 件 (`scripts/post_build_verify.py`)
が自動で走り、警告数は最終サマリの advisory roll-up に載る。あわせてレビュー用の
`temp_videos/<ep>_output_final.mp4` へのコピーも pipeline が行う。

この 2 つは ある時点 から**存在はしていた**が pipeline から呼ばれておらず、実行の強制は
memory の「必ず実行」という記述だけだった。ある回でその穴を踏み、**修正前の動画を
レビューしてもらってレビュー 1 周を無駄にした**ので配線した。

| フラグ | 既定 | 内容 |
|---|---|---|
| `--skip-post-build-verify` | off | ビルド後の構造検査 11 件を skip |
| `--no-temp-video-copy` | off | `temp_videos/` へのコピーをしない |
| `--no-review-reel` | off | のレビューリール + 未変更区間の同一性証明を skip (ビルド前の baseline 採取も止まる) |
| `--allow-full-resynthesis` | off | 「既存キャッシュがあるのに半数以上を再合成する」という予告が出ても止まらない |

### 1 シーンだけ直す経路 (`--rebuild-scene`) の検査

2026-08-06 まで、`--rebuild-scene` は full build が走らせる**検査 16 系統を 1 つも
通っていなかった**。`pitfalls.md` には route_map preflight の 1 件だけが「将来課題」
として載っていて、**その 1 行があることで棚卸ししたつもりになっていた**。

現在は **11 の共有ヘルパー**を両経路から呼ぶ (下表の後半 4 つは、1 回目の配線で**画像と字幕の側を取りこぼしていた**ぶん):

| ヘルパー | 中身 | 部分再ビルドでの絞り込み |
|---|---|---|
| `_run_audio_pre_checks` | reading_guard / gen_cloud_readings / cloud_reading_lint | 絞らない (静的走査で速い) |
| `_run_audio_post_checks` | stt_qa / cloud_speed_qa | STT は `--scenes <再ビルドした scene>`。速度は episode 全体の中央値と比べる検査なので絞らない。`--apply` (正規化) は**回さない** |
| `_run_pre_visuals_checks` | / 画面年号 / ナレーションと画面の不一致 / timeline 凡例 / route 凡例 / 地名カバレッジ | 絞らない (LLM 部分は content-hash cache が効く) |
| `_run_route_map_preflight` | Layer 2 (STOP ゲート + auto-fix) | 絞らない |
| `_run_post_visual_lints` | 白帯 / manim_vision_qa / manim_text_collision_qa | Vision QA は `--scenes` (Claude vision は scene 数に比例)。白帯と bbox 衝突は決定論で速い (実測 13.8 秒 / 17 scene) ので絞らない |
| `_run_pre_assemble_guards` | / Guard-B / Guard-B2 / Guard-B3 | audio も subtitles も回すので Guard-B/B3 は自動的に skip、 だけが効く |
| `_run_output_verification` | verify_outputs / temp_videos コピー / post_build_verify / レビューリール | 絞らない |
| `_run_font_coverage_check` | フォントが持たない漢字 (焼き込み字幕の豆腐化) | 絞らない。**字幕は必ず全編焼き直す**ので全編見る |
| `_run_pre_images_checks` | ある回主題肖像の use_reference gap | ken_burns のときだけ。絞らない (config 由来の決定論 lint) |
| `_run_post_images_border_lint` | の source 側 (生成画像の白縁) | ken_burns のときだけ。絞らない (PIL の画素実測で速い) |
| `_run_image_qa_gate2` | QA Gate 2 (画像 vs narration の整合、Claude vision) | ken_burns のときだけ。`--scenes <再ビルドした scene>` (13 枚へ vision を投げない) |

**下 4 つは 1 回目の配線で落としていた。** 音声と visual の側だけを共有化して
「塞いだ」と報告したが、同じ AST 測定をやり直すと画像と字幕の側が残っていた ──
ken_burns の部分再ビルドは**画像を作り直す**し、字幕は**必ず全編焼き直す**のに、
画像 QA も白縁も肖像参照 gap もフォント検査も走っていなかった。CLAUDE.md の
「画像を再生成したら qa_image_checker を回す。勝手に QA を skip しない」という
明文のルールを、この経路だけが破っていたことになる。
**塞いだと言う前に、穴を見つけたときと同じ測り方でもう一度測る。**

あわせて preflight の step 集合を実態に合わせた。以前は手書きの短縮版
`["assemble", "credits", "bgm"]` で、**必ず音声を合成するのに VOICEVOX 疎通も
Cloud API キーの存在確認も起動時に見ていなかった** (どちらも `"audio" in steps` ゲート)。

### 合成の波及規模を合成前に出す (合成予告ゲート)

ある回で、1 語だけ直したつもりの `--steps audio,...` が **94 文すべてを再合成**した。
Cloud TTS (Chirp3-HD) は非決定的なので**テキストが同じでも尺が変わり**、全 23 scene の
尺がずれて visual 23 本の再 render (24 分) まで波及し、合計 57 分になった。

`audio_generator.plan_synthesis()` が合成前に**同じキー計算を素通し**して hits/misses を
数える (副作用なし)。pipeline は毎回その数を出し、**既存キャッシュがあるのに半数以上を
再合成する**ときだけ確認を挟む。初回ビルド (cache 空) と `--force-regen-audio` は
意図が明示されているので対象外。

較正 — 出荷 63 ep 実測で発火 1 件:

| ep | 全文 | 再合成 | キャッシュ |
|---|---|---|---|
| 048_khayyam | 69 | **41 (59%)** | 29 件 (40 文が未登録) |
| 050_conway | 80 | 28 | 80 |
| 049_lucas / 047_kovalevskaya | 93 / 79 | 19 / 17 | 全登録 |
| その他の cloud ep (044/045/051-063 ほか) | — | 0 | 全一致 |

**キーの導出は 1 実装しかない** (`resolve_scene_speech`)。予告と実際の合成で別々に
導出すると、片方だけ直したときに**予告が静かに嘘をつく**。


### 字幕の本文が編集前のまま焼かれる (Guard-B3)

**字幕の本文は `timing.json` の `sentences[].text` から作られる** (`subtitle_generator`:
`raw_text = sentence["text"]`)。narration から直接ではない。timing.json を書くのは
**audio ステップ**なので:

    narration を直す -> `--steps subtitles,assemble,bgm` を回す
      -> 字幕は再生成されるが、中身は**編集前のまま**

しかも `_subtitles_meta.json` には**編集後の** narration hash が刻まれるため、
**Guard-B / B2 はどちらも「問題なし」と答える**。実ビルドで確認した desync。

Guard-B3 は narration と timing の本文を直接突き合わせる。**ゲートは Guard-B とは別**で、
`audio` を steps に含まないときに見る — 同じゲート (`subtitles` を回さないとき) に乗せると、
事故が起きる当のシナリオで一度も走らない (最初の実装はこれを踏んだ)。

**本文を直したら audio から回すこと。** 較正: 出荷 63 ep で発火 1 件、それは真陽性
(`044_oka_kiyoshi/math_05` の narration は「立ちふさがります」だが出荷字幕は
「立ちはだかります」)。逃げ道は `--allow-stale-subtitles`。

### レビューリールと「触っていない所は変わっていない」の証明

在庫を 1 箇所直すたびに 17 分を通しで見直す負担が、**直せば直る欠陥を「触らない」に倒して
いた**。増分キャッシュ が下げたのは計算コストだけで、人間のレビューコストは
そのままだったため、ボトルネックはこちらに移っていた。

pipeline は **2 箇所**でこれを扱う。

1. **起動直後**: 現行 `output_final.mp4` からフレームハッシュを採り、キャッシュ・timing・
   字幕・narration のハッシュと合わせて `_review_baseline.json` に書く。ビルドが動画を
   上書きしてしまうので、**ここで採らないと後から証明できない**。
2. **末尾**: 差分を取り、変更シーンだけを ±2 秒の文脈付きで繋いだ
   `temp_videos/<ep>_review_reel.mp4` を出し、**未変更シーンについては**フレーム・字幕・
   位置が同一であることを `review_reel_report.txt` に書く。

リールだけでは足りない、というのが ある時点 の user 議論の結論だった。変更シーンだけ見せる
ことは、見せなかった部分について暗黙に「変わっていない」と主張しているのに、その主張に
裏付けが無かったため。**未変更のはずのシーンに差異が出たらリールには映らない**ので、
report のその節を先に読むこと。

全シーンが変わった回とリールが 7 分を超える回はリールを作らず「通しで見るほうが速い」と
明示する (2 分で済むと誤解させない)。

**check 10 (章タイムスタンプを timing.json から再計算して値で照合)** と
**check 11 (全画像の下隅を 1 枚に並べた目視用シート)** は ある回で新設した。
検査の最後に出る `[ACTION]` 行 (Manim フレームとシートのパス) は必ず開くこと。

### 観測性

| フラグ | 既定 | 内容 |
|---|---|---|
| `--log-file PATH` | 無効 | 構造化 JSONL イベントを PATH に書く (stdout のテキストはそのまま) |

1 行 1 JSON オブジェクト。フィールドは `ts` / `step` / `level` / `episode_id` /
`scene_id` / `msg` / `metadata`、severity は critical / warning / info の 3 階層。
既定は無効なので、既存ビルドの出力はバイト単位で変わらない。

---

## 部分再ビルド時の注意

`--qa` は既定 ON なので、**内容を変えない mechanical な部分再ビルド**
(`--steps assemble,bgm` 等) では `--skip-qa --skip-pronunciation-check` を併用しないと
QA Gate 1 が長時間ブロックする。

ただし **QA 指摘を内容修正した後**の再ビルドは別で、asset を作り直す前に
standalone で `python src/qa_checker.py <scene_def> --gate script` を通してから
skip する。安い script 検証を、高い asset 生成の前に挟む。

---

## QA 再検証 hook

`qa_report_*.json` を Read した瞬間に QA 再検証 hook が PreToolUse で再検証リマインダを差し込む。QA レポートは severity / citation /
confidence が構造化されているぶん一見権威的に見えるため、**指摘を伝える前に
一次資料で裏取りする**運用を機械的に促す。


---

## QA エージェント関連の落とし穴

[`pitfalls.md`](pitfalls.md) の「QA エージェント / Vision QA」節を参照:

- ContentReviewer の尺超過 false positive
- QA agent の非決定性 (run 間で判定が揺れる)
- Vision LLM 単発実行の保守性
