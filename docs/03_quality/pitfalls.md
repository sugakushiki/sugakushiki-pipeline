# よくある落とし穴 (Pitfalls Database)

> パイプラインで過去に発生したバグ・落とし穴のインシデント DB。
> 新エピソード制作時・コード修正時に「同じ罠を再発させない」ための索引。
> 新規エントリは末尾の「最近追加（未分類）」に積み、定期的に本表に整理する運用。

---

## Manim テンプレート関連

| 問題 | 原因 | 対策 |
|---|---|---|
| Manim内の日本語が文字化け | `MathTex()` に日本語を入れた | `Text(font=FONT)` を使う |
| 字幕が Manim要素と重なる | y座標が−2.0より下 | Manimシーンは字幕マージン240px、y ≥ −2.0 |
| Unicode数式が文字化け（S₃, ⟺等） | text_overlayでUnicode文字使用 | formula_displayテンプレート（LaTeX）を使う |
| Manimで全シーン同じアニメが出る | `discover_manim_templates()`が1ファイル1クラスしか返さない | **1ファイル1クラス + `construct()`内mode分岐**。複数クラスに分けると最初のクラスだけ使われる |
| Manim末尾で画面が黒になる | 末尾の `self.play(*[FadeOut(m) for m in self.mobjects], ...)` で全オブジェクト消失 → 音声がManimより長いとFFmpegが黒フレームでpadding | 末尾の `FadeOut` を削除し最終フレームを保持。全15箇所（equation_history / polygon_squeeze / permutation_group / polynomial_roots / solvable_vs_unsolvable / sphere_cylinder）を一括修正済み。シーン間トランジションは video_assembler の責務 |
| Manim 桁数表示と narration の不一致 | madhava_pi_series の partial_sums が「小数点以下の一致桁数」、narration が「有効数字」で表現が違う | Manim表示を「有効桁数」（整数部の `3` を含める）に統一。narration の「2桁」「3桁」は有効数字が自然（修正済み） |
| formula_display で意図しないフーリエ級数式が出る | scene_definition が `"formulas": [...]` + `"labels": [...]`（複数）を渡しているのに、formula_display.py が `params.get("formula", default)`（単数 key）のみ読み、見つからずデフォルトの `f(x) = Σ a_n cos(nx) + b_n sin(nx)`（フーリエ級数）にフォールバック。特定エピソードの該当シーン（連続の式 + 運動方程式の流体方程式シーン）で意図と無関係なフーリエ級数式が出ている状態で完成し、視聴フィードバックで発覚 | formula_display.py に `build_multi()` メソッド追加。`formulas` array が ≥2 件あれば縦並び FadeIn で順次表示。font_size 自動調整 + safe Y range scale。後方互換: 単一 "formula" もそのまま動く（対応セッションで修正済み） |
| Manim テンプレに表示される人名・年号が narration に出てこない | テンプレ内に「タルターリア 1535」「フェラーリ 1540」が cards_data でハードコードされていても、narration が「3次/4次方程式」とだけ言及して人名・年号を語らないと、視聴者には画面情報と音声情報の非対称が生じる。特定エピソードの該当シーン / 特定エピソードの該当シーン で発覚（equation_history テンプレ）。過去のケースでは narration が「16世紀」と一段抽象化し年号 1535/1540 を省略 | **解決済み**: `qa_manim_consistency.py` が pipeline visuals step 直前にテンプレの `LINT_FACTUAL_CLAIMS` metadata を読み、narration 全体に登場しない人名・年号を WARN として検出（episode scope γ 適用、複数テンプレートに metadata 追加済）。新規テンプレは `LINT_FACTUAL_CLAIMS` 必須（Manim チェックリスト項目 7 参照）。理想形 7 要素（双方向チェック・人物 ID・史実 DB・LLM 意味一致 等）は 段階導入計画として記録 |

---

## VOICEVOX / 発音 / narration_speech

| 問題 | 原因 | 対策 |
|---|---|---|
| VOICEVOX辞書が効かない | 文脈依存の読みに辞書は不向き | narration_speechフィールドで対応 |
| VOICEVOX誤読が動画完成後に発覚 | 値→ネ、重根→じゅうこう等、漢字の文脈依存読みをVOICEVOXが誤読 | pronunciation check（`--qa`時自動有効）+ KNOWN_MISREADINGS 13パターン + lint_narration_markers() |
| pronunciation checkの自動修正が逆効果 | 「真か偽か」を「まかぎか」に誤修正。自動修正結果を鵜呑みにした | KNOWN_MISREADINGSに正しい読みを登録（「真か偽か→しんかぎか」）。自動修正後の結果も人間が検証する |
| 近似値・数値・三角関数値が「あたい」と読まれる | KNOWN_MISREADINGS の汎用ルール `("値", "あたい")` が複合語にも誤適用され、Claudeによる自動修正で narration_speech が `近似あたい` 等に書き換えられた | 複合語ルール（数値解析→すうちかいせき、三角関数値→さんかくかんすうち、近似値→きんじち、数値→すうち）を汎用 `値` ルールより先に追加（修正済み） |
| KNOWN_MISREADINGS の追加が脆い（長さ順の手動メンテ） | フラットリストで「複合語を単一字ルールより先に置け」という手動コメントに依存 | カテゴリ別 dict + `_flatten_and_sort_misreadings()` で長さ順自動ソート＋重複検出（対応セッションで修正済み） |
| VOICEVOX 誤読: 極限値→きょくげんあたい、嫉妬深い→しっとふかい、年に300→としに300、ヨーロッパ中→ちゅう、後に→あとに、父の命→いのち | 「値」複合語（極限値）の未登録、連濁不適用（嫉妬深い→ぶかい）、漢字の文脈依存読み、narration_speech がない場合は narration がそのまま使われる | narration_speech で仮名明示が確実。KNOWN_MISREADINGS に極限値を追加する改修余地あり（連濁・曜日・年月漢字は個別 narration_speech で対処） |
| narration_speech 配列の一部が空文字 → 該当行が 0.23 秒の無音音声に | scene_definition.json で `narration_speech` を **特定 index だけ** 部分修正すると、他の index が `""` のまま残り、VOICEVOX が空文字を送られて極小無音 wav を返す。対応エピソード で person_05/person_09 が「字幕が一瞬で流れ去る」現象として発覚 | narration_speech 配列を編集する際は、修正しない index にも **必ず narration[i] と同じ文字列をコピー**（または narration_speech 配列ごと None / 削除）。`audio_generator.py` 起動時の検証で空文字があれば fail-fast（対応セッションで検証フェーズ追加） |
| narration_speech が古いまま残り音声に古いテキストが反映される | pronunciation_check は既存 `narration_speech` を上書きしない仕様（user-managed として尊重）。`narration` を編集しても `narration_speech[i]` が古いテキストのまま残り、VOICEVOX が古いテキストで音声生成。過去のケースで「一切→ほとんど」修正が音声に反映されず、ユーザー指摘で発覚（再ビルド 43.9 分必要） | `narration` 編集時に対応する `narration_speech[i]` を必ず同 index で同期更新する（kana 補正があるなら kana 優先、なければ `narration[i].replace('|', '')` の flat 版でOK）。過去の運用知見で運用ルール明文化。**解決済み**: `audio_generator.py` の `lint_narration_markers()` に narration vs narration_speech の drift 検出を追加（speech 側の漢字欠落 + 数字列不一致を WARN）。ただし完全 kana speech・漢字共有編集・句読点編集は構造上検出不能（将来課題） |
| VOICEVOX が「偽」を「にせ」と読む（形式論理 context） | math_05「Gの内容は偽ということになり」を VOICEVOX が「にせ」と everyday 読みで生成。math/logic context の predicate「は偽である」「は偽となる」では「ぎ」が正しいが、`偽物`/`偽証`/`偽善` の everyday compound と区別が必要。過去のケースで発覚 | `audio_generator.py` の `_MISREADING_CATEGORIES["compounds"]` に5項目追加: `真偽→しんぎ`/`偽命題→ぎめいだい`/`偽である→ぎである`/`偽となる→ぎとなる`/`偽ということ→ぎということ`。predicate form を限定で登録するため everyday compound（偽物/偽証/偽善）には影響しない（対応セッションで修正済み） |
| 複合語末尾「値」が「あたい」と誤読される (絶対値・観測値・理論値・期待値・最大値・最小値・平均値・固有値 等) | VOICEVOX 既定読みが単独「値」=あたい、複合語でも誤適用。moriarty 例エピソードで顕在化 | **構造解決済**: `audio_generator._MISREADING_CATEGORIES["math_terms"]` に複合「値」21 件を追加、pronunciation_check Claude prompt + script_generator narration_speech 生成 prompt にも「複合語末尾は ち 読み」ルール明示。新規 ep でも自動 catch (集積予防) |
| 「N分のM」が時間の「ふん」と混同されて「にふんのいち」と誤読 | VOICEVOX が「分」を時間単位で解釈、分数の文脈区別なし。moriarty 例エピソードで顕在化 | **構造解決済**: `audio_generator._convert_fractions()` で `(\d+)分の(\d+)` regex auto kana 変換 (denominator/numerator 1-20 範囲)。手動 narration_speech に頼らず自動適用 |
| 修辞的「否」が熟語の「ひ」と混同されて「ひ」と誤読 | 「答えは否」の修辞的単独用法と熟語 (否決・賛否・否定) の混在 | **構造解決済**: `_MISREADING_CATEGORIES.math_terms` に「否」を「いな」読みで 3 形式登録 (「答えは否」「P は否である」等)。熟語専用「ひ」読みは予測通り保持 |
| 数式 `A/B` の narration_speech に「A 割る B」が機械的に混入 | LLM が分数を発音化する際、「割る」を直訳的に挿入しがち | **構造解決済**: `script_generator` narration_speech 生成 prompt に「数式 A/B は denominator-first の `BぶんのA` 読み、複雑式は文章で説明し具体的式は visual で表示」ルールを明示。pronunciation_check Claude prompt にも同ルール |
| 「負」が「まけ」(動詞 負ける) と誤読 (math context の負数) | VOICEVOX default 読み「まけ」、「負の偶数」「負の数」など math context でも誤適用。ある時点 で発覚 | **構造解決済**: `voicevox_dict.json` に compound surface「負の」→「フノ」を追加。standalone「負」(動詞 負ける/背負う 形) と衝突しない compound 限定で global 適用。per-ep narration_speech 個別書き換えに頼らない Phase A 集積方式 |
| pronunciation_high_risk dict の typo が global 伝播 | ある時点 で「私講師→ししこうし」誤入力 (正: しこうし) → pronunciation_check Claude がそのまま採用 → 全 ep で誤読伝播のリスク | **将来対応**: dict entry の kanji 数 vs kana mora 数の sanity check、または LLM による定期 dict 監査。当面は dict 編集時に ear-test での確認を運用ルール化 |
| 動詞活用形を含む context で VOICEVOX 誤読 dict entry がマッチしない | ある回 で「帰せられる→きせられる」を `_MISREADING_CATEGORIES` に追加したが、ある回 「帰せられている」(活用形「て+いる」) には prefix unmatch で発動せず再発。「他にいた」「他にいる」も同パターン (動詞活用末尾の違いで dict miss) | **規約**: 動詞 + 活用形は **語幹マッチ default** で entry 登録。例:「帰せられる→きせられる」ではなく「帰せられ→きせられ」を登録すると `帰せられる/帰せられた/帰せられて/帰せられている` 全活用形を一発捕捉。動詞 + 「他にい」「微+漢語結合」のような語幹は最短マッチで集積する |
| narration を編集したが speech に古い内容が残って音声に反映されない | ある回 で intro_02 narration にスタディア単位説明 (約 30 文字) を **追加** したが narration_speech が古い (短い) 版のまま → 音声では読まれず QA Gate 1 も pass。既存 drift lint は「speech に余分な漢字 (= 過去の narration を保持)」方向のみ検出、「narration に追加されて speech に欠落」方向は未検出 | **構造解決済**: `audio_generator._check_narration_speech_drift()` に check 3 「kanji extra in narration ≥ 3 文字なら WARN (speech may be stale)」を追加。kana 補正による 1-2 文字差 (例: 微 → び) は tolerance、3 文字以上の差は narration expansion 後の speech 同期漏れと判定。過去の運用知見|

---

## Cloud TTS (engine=cloud) / 非決定性 / STT QA

`episode_config.json` の `tts.engine="cloud"` で Google Cloud TTS (Chirp3-HD) に切替。VOICEVOX とは別系統の落とし穴があるので分離。

| 問題 | 原因 | 対策 |
|---|---|---|
| Cloud audio を再生成したら尺が変わり visual が desync | **Cloud は非決定的**。同一テキストでも再合成ごとに読み・尺が ±1〜4s 揺れる | audio を再生成したら **必ず該当 visual も再 render**。良好シーンは温存する: per-sentence 音声 cache が engine+voice+rate+text を hash → text 不変なら cache hit で同一 wav 再利用 (擬似決定化)。敢えて別ロールを引くなら `--force-regen-audio` |
| VOICEVOX 誤読辞書が Cloud audio を壊す | `apply_known_misreading_fixes`/`_convert_fractions`/`("里","り")` 等は **VOICEVOX 専用正規化**。Cloud に適用すると郷里→サトリ等が再発 | **engine で完全分離済**: cloud は `narration_speech_cloud` を空白と括弧の strip だけ掛けて送る (読みの固定は SSML `<phoneme>` を**当該語を含む文にだけ**適用し、他の文はバイト不変)。辞書層は `engine=="voicevox"` ゲート。`auto_generate_narration_speech`/`pronunciation_check`/`register_user_dict`/VOICEVOX version check も全て voicevox 限定 (cloud は GUI 不要) |
| 助詞 は が『ハ』と読まれる / 長カタカナ名が崩れる | Chirp3-HD の BERT アクセントでも助詞 は→ハ 化・長い外国語カタカナ連結の劣化が起きる (audio_query が無く事前 kana 確認不可) | **コンマで孤立した は/へ だけ** を `gen_cloud_readings` が わ/え に変換する (孤立助詞が誤読の実体。ダッシュ由来の空白付き `、 は` も畳み込んで拾う)。外国人名はカタカナ化、長いカタカナ連結は分割/ひらがな境界で緩和 |
| **は を一律「わ」表記にすると逆効果** | 「助詞は わ で決定的固定」を全 は に広げると、独立した わ の境目で Chirp が微小な間を挿入し不自然化する (A/B 実測で わ 文は は 文より約 25% 長い)。真因は config の `additional_instructions` が LLM に『narration_speech_cloud を用意・助詞は→わ』と指示していたこと | `script_generator` が LLM 出力の `narration_speech_cloud` を **破棄**し、`gen_cloud_readings` が narration から native な は で全再生成する。`cloud_reading_lint` が全変換 (一括は→わ) と部分変換 (助詞は→わ過剰変換) の両方を WARN。**新規 config に『cloud 読みを LLM に用意させる』指示を書かない** |
| Cloud の誤読を事前検出できない | Cloud に VOICEVOX の `audio_query` (kana 実測) が無い → reading_guard 不適用 | 3 層で守る: ① 合成**前**の静的 lint (`scripts/cloud_reading_lint.py`) ② 合成**後**の Gemini STT 照合 (`scripts/stt_qa.py`、audio step 後に自動起動) ③ **出荷物**の STT (`scripts/verify_shipped_audio.py`、on-demand)。**どの層も単独では取りこぼす** → **必ず耳で spot-check** してから公開。`GOOGLE_API_KEY` 無しは graceful degrade |
| 文ごとに発話速度が揺れる | Chirp3-HD は文単位の実発話速度そのものを大きく揺らす (隣接文で 24〜31% 差)。`tts.rate` は全体基準で、文単位テンポは API 非制御 → **個別文の再合成では収束しない** | `scripts/cloud_speed_qa.py` が常時検出 (段差 >18% を WARN)。修正は opt-in の `--normalize-cloud-speed` / `--apply` で median へ atempo 部分圧縮。**2 回掛けると緩急が潰れる**ので多重適用ガードがある (かけ直すのは `--restore` 後) |
| narration 編集で Cloud 読みが古いまま | sync surface が2本 (`narration_speech` VOICEVOX + `narration_speech_cloud` Cloud) に増えた | narration 編集時は **両 NS を同期**。`narration_speech_cloud` 未設定なら cloud は narration_speech→narration に fallback し「読み未検証」WARN。`validate_narration_speech`/`lint_narration_markers` は両フィールドの空要素・長さ不一致を検証。過去の運用知見|
| ロールバックの手順 | Cloud が不評/障害時に VOICEVOX へ戻す | `tts.engine` を `voicevox` に戻す (or `--tts-engine voicevox`) → `--steps audio,subtitles,assemble,bgm` で再ビルド。尺が変わり visual が stale → が捕捉するので visuals も再 render。source (config + 両 NS の scene_def) は不変、build 成果物は derived として再生成 |
| pitch を Cloud に送るとエラー | Chirp3-HD は `pitch` 非対応 (`speakingRate` は有効) | Cloud には speakingRate (`tts.rate`、既定 0.90) のみ。`PITCH_SCALE`/`SPEED_SCALE`/`PAUSE_LENGTH_SCALE` は VOICEVOX 専用で cloud には送らない |

---

## 画像生成 (Wikimedia / Gemini / 透かし)

| 問題 | 原因 | 対策 |
|---|---|---|
| Wikimediaで別人の写真取得 | ライセンス正規化バグ + キーワード不足 | `_is_license_accepted()` + EXCLUDE_KEYWORDS |
| Ken Burnsがジッター | FFmpeg zoompan | Pillow+FFmpegパイプ方式 |
| 画像生成で女性が男性になる | `_build_reference_prompt`のage_descが"man"固定だった | source_promptからgenderを動的推定（修正済み） |
| リファレンス写真で別人が汚染 | 主題者以外の人物（例:Leibniz）にSekiの写真が使われる | visual blockに`"use_reference": false`を設定して非主題人物のリファレンスをopt-out |
| Vision QAリトライで性別が反転 | feedback内の"woman"等がプロンプトに蓄積し次回の性別判定を狂わせる | `strengthen_prompt`に`source_prompt=`を渡し、性別判定は常に不変のsource_promptで実施 |
| 画像が再生成されない | image_generatorは既存画像をスキップする仕様 | source_promptを変更した場合は該当画像ファイルを削除してから再ビルド |
| リファレンス画像が年齢指定を上書き | ken_burnsでpersonシーンはリファレンス肖像画ベースで生成されるため、source_promptの年齢指定が効かない | 人物以外のシーンに変更するか、手動で画像を差し替える |
| 通貨・紙幣の画像が法的に問題 | AI生成でも紙幣に見える画像は再現ルールの対象となりうる | 紙幣そのものではなく、発表会見・ニュース報道風の間接的な画像を使う。source_promptに直接banknoteのクローズアップを指定しない |
| 1600年代の年号で _estimate_scene_age が None を返す | 正規表現 `1[89]\d{2}|20[0-3]\d` が 1800年以降しか拾わなかった（17世紀以前の数学者は全シーンflashフォールバック） | `[12]\d{3}` に拡張 + 妥当性チェック（修正済み） |
| Gemini 画像生成で点の配置が守られない | 「point A upper-left, point B lower-right」指定でも両方上部に配置されるケースあり。3曲線のうちサイクロイドが真のサイクロイド形状にならず U字型やループになる | プロンプトに「B is lower than A by about half the height of the slate」など**数値化した垂直落差**、「drops VERY STEEPLY just after leaving point A」のような**サイクロイドの形状詳細**、「No Latin annotations」のような**禁止事項**を明記。必要ならブラウザの Gemini でユーザー手動生成 + トリミングでウォーターマーク除去 |
| Wikimedia 検索で「数学者名」を検索すると同名施設の写真がヒットする | 「Leonhard Euler」検索で **チリの天文台「Swiss 1.2-m Leonhard Euler Telescope」** のドーム/望遠鏡写真がトップに来る。リファレンス写真として AI 生成に渡されると顔の参考にならず、AI が描く人物が一切似ない原因になる | wikimedia_credits.json 取得後、ファイル名・タイトルに「telescope/observatory/dome」等の語が入っていたら警告するチェックを `image_generator.py` に追加検討。過去のケースでは手動で 4 枚（person_03/06、math_01/13）を再生成して差し替え |
| ChatGPT/Sora 生成画像に BR ✦ スパークル透かし | OpenAI 系列の画像生成サービスが必ず右下に 4 点星マークを入れる。動画素材としてそのまま使うとブランドロゴが映り込む。対応エピソード で手動作成 4 枚すべてに混入 | メモリ過去の運用知見の標準コードで下部 10-13% トリミング → 16:9 中央クロップ → 1920×1080 LANCZOS リサイズ。手動作成画像を受け取ったら必ず BR コーナーを目視確認 |
| Wikimedia Fetcher 同名施設の写真混入（再発） | 過去のケースで「Wikimedia 検索で『数学者名』を検索すると同名施設の写真がヒットする」を記録済みだが、対応エピソード でも `wikimedia_credits.json` に「Swiss 1.2-m Leonhard Euler Telescope」（チリの天文台ドーム + 望遠鏡）2件が混入し、description.txt の画像クレジット欄に出力された。AI reference photo として download されたが顔の参考にならず実質未使用 | wikimedia_fetcher.py の `EXCLUDE_KEYWORDS` に天文施設・船舶・公園等の同名語（telescope/observatory/dome/satellite/asteroid/crater/comet/ship 等）追加が将来課題。当面は description.txt 確認時に手動で wikimedia_credits.json から無関係 entry を削除して credits step 再実行（過去のケースでは Basel 風景1件のみ残し他2件削除） |
| `wikimedia_photo_urls` の dict 形式で `KeyError: 0` | 過去回（中期エピソードで）はすべて `wikimedia_photo_urls` を flat list `["https://..."]` で書いていたが、過去のケースで誤って `{"person": [...]}` の dict 形式で書いた。`wikimedia_fetcher.py:761` の `info.get("url", fallback_urls[i])` で int index を dict に渡し `KeyError: 0` 発生 → photos step 即座に失敗、ただし pipeline 続行で動画自体は完成（description.txt の Wikimedia photo クレジットが欠落） | `wikimedia_fetcher.py` に `isinstance(fallback_urls, dict)` 検出時に明確なエラーメッセージで `sys.exit(1)` する defensive check 追加済（対応セッション）。今後は flat list 形式を厳守 |
| source_prompt に独断で aesthetic detail を追加（裏取りなし） | 特定エピソードの該当シーン で私が source_prompt に「smoking pipes and gesturing animatedly」を追加 → Gemini Flash が忠実に「全員パイプ喫煙」画像を生成 → ユーザー指摘で「Vienna Circle が集団でパイプ喫煙していた史実なし」と判明。私のステレオタイプ追加が原因 | **構造解決済 (過去の対応で実装)**: `src/cliche_scanner.py` (Layer 1 辞書ベース always-on + Layer 2 LLM レビュー opt-in) が image step 入口で source_prompt の時代物 cliché (32 entries / 6 カテゴリ) を自動検出し WARN。Vienna Circle の喫煙が史実検証済の場合は visual block の `cliche_acks: ["smoking pipes"]` で per-scene opt-out 可能。詳細は `docs/04_assets/image-generation.md` の「cliche scanner」セクション参照 |

---

## サムネイル

| 問題 | 原因 | 対策 |
|---|---|---|
| サムネイル数式の円記号化／豆腐化 | BIZ UDMinchoが `\` を円記号(¥)で表示、ℵ・ℕ・ℝ・添字(₀)等を豆腐化（JIS X 0201互換） | thumbnail_generator.py は `$...$` で囲むと **matplotlib mathtext（Computer Modern）で描画** する（対応エピソードで導入）。TeXサブセット（`\aleph_0`、`2^{\aleph_0}`、`\pi`、`\frac{}{}`、ギリシャ文字など）が使える。例: `"math_symbol": "$\\aleph_0 < 2^{\\aleph_0}$"`。`$`なしの ASCII/Unicode 文字列は従来通り PIL で描画 |
| サムネイルに別人物（Pascal等）が選ばれる | `thumbnail_generator.py` が `person_*.png` 全体を候補にし、ファイル名だけでSonnetが推測していた | `scene_definition.json` を読み `use_reference != False` のken_burnsシーンに絞り、Claude Visionで実画像を採点（修正済み） |
| 「silhouette of Toulouse rooftops」が人物シルエットとして誤除外 | 単純な "silhouette" 文字列マッチで建物シルエットも拾っていた | "silhouette of a [person]" の形でのみ除外、建物は許容（修正済み） |
| サムネイルが風景画像になる（人物なし） | config の `source_image: "person_2.png"` と実ファイル `person_02.png`（ゼロ埋め2桁）が不一致 → fallback で `sorted(glob("person_*.png"))` の先頭 = `person_01.png`（風景広角）が選ばれる | `person_XX.png`（2桁ゼロ埋め）で指定、または `source_image` を省略して自動選定に任せる。fallback自体を `select_best_thumbnail_image()` に変更するのが理想（未修正） |
| サムネイルが風景画像になる（人物なし）※修正済み | config の `source_image` が実ファイルと不一致で fallback 発動時、`sorted(glob("person_*.png"))[0]` が `person_01.png`（風景広角）を返していた | `select_best_thumbnail_image()`（Vision採点付き）をfallbackに使用するよう修正済み。最終手段で person_01.png 使用 |
| サムネイル `source_image` が group scene を指して主役不在 | 過去のケースで `source_image: person_03.png`（ウィーン学団 7人の議論シーン）を指定 → サムネイルに7人並びでゲーデル特定不可 | **構造解決済 (過去の対応で実装)**: `validate_explicit_source_image()` が `config.thumbnail.source_image` 明示指定時に Vision 採点を実行、閾値 (default 8/15) 未満で warning 出力。`--strict-source-validation` CLI または `thumbnail.strict_source_validation: true` で強制 fallback (`select_best_thumbnail_image()` に切替)。新規 ep ビルド時に group shot 指定すれば自動的に warning が出る |

---

## 字幕 / drawtext

| 問題 | 原因 | 対策 |
|---|---|---|
| 字幕が不自然な位置で切れる | narrationの`|`が25文字以内で配置されておらず、subtitle_generatorのauto_split（MAX_CHARS=25）が機械的に分割 | **`|`を意味的に自然な位置に手動配置し25文字以内にする**。auto_splitに頼らない。問題は1文の長さではなく区切り位置の適切さ |
| 字幕に`%`が表示されない | FFmpeg drawtext filter_scriptが`%`を書式指定子として解釈し「Stray %」警告で行を削除する。`%%`も`\%`も効かない | subtitle_generator.pyで半角`%`→全角`％`(U+FF05)に置換済み。BIZ UDMinchoで正常描画 |
| 字幕が文字化け（□）になる | FFmpeg drawtext の `fontfile=_font.ttc` が相対パス。partial rebuildでcwdが worktree root 以外だと `_font.ttc` が見つからず、デフォルトフォント（CJK非対応）にサイレントfallback | video_assembler.py の merge_final で `cwd=output_dir` を指定 + 入出力パスを absolute 化（修正済み） |
| 仏語・英語引用の字幕が単語中央で分割される | subtitle_generator の auto_split が日本語の句読点・助詞のみ候補にし、ラテン文字は midpoint fallback に頼っていた | `,` `.` `;` `:` + 半角スペース、およびASCII単語境界をスコアリング対象に追加（対応セッションで修正済み） |
| 字幕に raw LaTeX が漏れる | scene_definition.json の visual block に formula_display が指定されたシーンで、subtitle 文字列に LaTeX 記法 (`\frac{}{}`、`$...$`) が含まれて drawtext で raw 表示されてしまう | **構造解決済**: `formula_display._sanitize_subtitle()` で LaTeX 記法を検出 → 該当部分を strip + WARN 出力。subtitle 生成前に確実に sanitize される |

---

## route_map

| 問題 | 原因 | 対策 |
|---|---|---|
| route_map で密集都市のラベル衝突 | 固定 `label_w_est = 5.0`（過大推定）、anchor 点距離のみで collision 判定 → ラテン/日本語の実幅を無視 | 文字種別の幅推定（日本語≈1em, ASCII≈0.55em）+ BBox 重なりによる hard reject（対応セッションで修正済み） |
| route_map の南端都市のラベルが字幕領域に侵入 | `plt.tight_layout` + `bbox_inches="tight"` で matplotlib がプロット領域を図全面に広げるため、下端220pxの字幕マージンに都市/ラベルが被る | `fig.subplots_adjust(bottom=220/1080)` でプロット領域から下端を構造除外。`bbox_inches="tight"` は subplots_adjust を打ち消すため削除。全エピソードの全route_mapに自動適用（対応セッションで修正済み） |
| route_map で都市が画面端に近いとラベルが見切れる | 既定 `bounds = lon[-85, 45], lat[20, 65]` でサンクトペテルブルク（lon=30.32）の右側の長いカナラベル「サンクトペテルブルク」が右端で切れた。特定エピソードの該当シーン（バーゼル→ペテルブルク）で発生 | scene_definition.json の visual block に `"bounds": {"lon": [-10, 50], "lat": [40, 65]}` のように **エピソード固有の絞り込み bounds** を明示指定。ヨーロッパ内移動なら西欧〜ロシア西部に絞ると地図が大きく見え、ラベルも収まる |
| route_map で title と route_label が画面上部で重なる | タイトルは `lat_range[1] - lat_span * 0.06`（画面上部）、route_label は bezier midpoint + offset で配置されるが、collision avoidance ロジック（既存）は city_label / route_label 間のみ対象、**title と legend は対象外**。特定エピソードの該当シーン で「アーベルの旅路 1815-1827」と「1815 大聖堂学校入学」が重なる事故が視聴で発覚 |  (過去の対応で実装) で多層防御を導入: Layer 2 preflight（pipeline 起動時 default ON、衝突検出時 STOP）+ Layer 3 in-render WARN + 4-stage opt-in auto-fix (`--auto-fix-route-collisions`)。escape: `--allow-route-collision` / `--skip-route-preflight` |
| route_label loop が「全 offset 拒否」時にタイトル重なり位置に戻る fallback bug | `for dy in offsets:` ループで全 candidate が境界外 / 既存ラベルとの距離不足で reject されると、`best_pos = (lx, ly)` 初期値に戻る。初期値が title 重なり領域にあると、Stage 1 (top exclusion 5%→18%) が実質無効化される | 対応セッションで修正: `best_min_dist == -1` 検知時に `forced_y = lat_range[1] - lat_span * (top_padding + 0.02)` への強制 fallback を追加。Stage 1 を確実に有効化 |
| `--rebuild-scene` で route_map preflight が走らない | `_run_partial_rebuild()` は別 code path で  Layer 2 を呼ばない（pipeline.py main フローのみ統合）。partial rebuild で route_map scene を再生成する時 preflight gate が効かない | Layer 3 in-render WARN は partial rebuild でも fire するため検出は可能（ただし STOP しない）。完全 fix が必要なら `_run_partial_rebuild` への統合が将来課題（段階追加候補） |

---

## description / credits / 参考文献

| 問題 | 原因 | 対策 |
|---|---|---|
| BGMクレジットが概要欄に出ない | credits_generatorが`bgm.credit`フィールドのみ参照 | title/artist/sourceからの自動組み立てに修正済み |
| チャプターが1秒ズレる | credits_generatorのintro-pauseデフォルト(0.0)がbgm_mixer(1.0)と不整合 | pipeline.pyで両方のデフォルトを1.0に統一済み |
| 参考文献にハルシネーション | LLM生成の書誌情報（著者名・書名・出版年）が不正確 | 事前事実チェックの書誌 review レイヤが advisory で拾う（決定論 API は実測で偽陽性を潰せなかった：実在書籍が未収録で 0 件になる／復刻年で年比較が外れる／ISBN がほとんど無い）。**指摘は必ず Web で裏取りしてから反映**する — 正しい値は書かせない設計 |
| 概要欄の導入文だけが古いまま公開される | `description.intro` は script 生成時の LLM 出力で、以後どこからも自動同期されない。`episode_config` を直しても、narration を直しても intro だけ取り残される | 2 方向を別々に見る: config → intro は署名方式の staleness 検出（`check_description_staleness.py`）、narration → intro は限定詞欠落の意味 review（`check_intro_semantic.py`）。どちらも credits step と完了後の検証に配線済み |
| 画像クレジットが絵画を「写真」と呼ぶ | 参照呼称は没年ヒューリスティック（写真技術以前なら「肖像画」）で決めているので、`death_year` 未設定や、参照が絵画と写真の混在の回では外れる | `death_year` を必ず書く。ヒューリスティックが合わない回は `portrait_reference_kind` で呼称を明示 override する。没年が新しいのに参照 credit が painting/lithograph 等を含む場合は advisory WARN が出る |
| 参考文献の雑誌名・出版社が description に出ない | credits_generator が scene_def.credits.references（LLM簡略版）を優先し、episode_config.references（手動完全版）を fallback にしていた | 優先度を逆転：episode_config.references が primary、scene_def が fallback（対応セッションで修正済み） |
| 参考文献 URL が broken | description.txt に書いた URL が 404 など broken だと視聴者が踏んだ時に体験を損ねる。対応エピソード で `abelprize.no/page/biography-niels-henrik-abel` が 404、ユーザー「参考文献も適切ですか？」をきっかけの verify で発覚 | `credits_generator.py` に URL 死活監視（`validate_reference_urls()`）を追加済（対応セッション）。HEAD/GET フォールバック、半角・全角括弧 strip、parens 内 URL 対応、`--skip-url-check` でオプトアウト可。warning のみで pipeline 失敗させない |

---

## pipeline / config

| 問題 | 原因 | 対策 |
|---|---|---|
| episode_config.jsonでクラッシュ | `verified_facts` がdictだった | リスト `[]` を使う |
| pipeline.py実行時の--qa付け忘れ | ~~QAはopt-inフラグ~~ → `--qa`はデフォルトON化済み（対応エピソード）。フラグ不要で常にQA実行。`--skip-qa`でopt-out | `--qa`の`default=True`化 + PreToolUse hook更新 |
| pipeline image step がサイレント部分失敗 | 画像生成中にネット切断や API クォータ枯渇で 18 枚必要なところ 4 枚で停止しても pipeline は致命エラーとして停止せず、空画像でフォールバックの 80-300 KB の極小 visual を生成して最終動画まで進む。過去のケースで発覚（最終動画の半分以上が黒/プレースホルダー） | `pipeline.py` の images step 完了直後に `ken_burns シーン数 == images/*.png 数` を検証して fail-fast（対応セッションで検証フェーズ追加） |
| atomic rename リネームの更新漏れ → undefined name | output.mp4 → output_assembled.mp4 / output_final.mp4 の atomic rename を導入した時、`_run_partial_rebuild()` summary 部分の変数名が `output_mp4` のまま残った dead branch が放置された。ruff lint で F821 として検出 | 対応セッションで `output_assembled` に修正。リネーム時は **同名 grep + ruff check F821** を必須に。今後は CI で ruff lint をかけるべき (将来課題) |
| requirements.txt から top-level 直接依存が長期欠落 | requirements.txt が `pip freeze` でなく manim 系のみ羅列されていて、sympy / matplotlib / python-dotenv / google-genai が **top-level 直接依存にも関わらず未列挙**。fresh venv で `pip install -r requirements.txt` を走らせると pipeline が動かない構造 BUG が長期放置 | `pip freeze` 全件を lock file 化、`requirements.in` (top-level) と分離。再生成手順を CLAUDE.md / ヘッダーに記載。fresh venv 実機検証 PASS |
| requirements*.txt のヘッダーコメントに em-dash 等の非 ASCII が混入で pip install が UnicodeDecodeError | Windows の pip 22.3 が requirements.txt を **cp932 で読もうとする** ため、UTF-8 で書いた em-dash (`—`、3 byte E2 80 94) の 3 byte 目 0x94 が cp932 の illegal byte で UnicodeDecodeError 即死。依存関係整理時に発覚 | requirements*.txt のヘッダーコメントは **ASCII のみ**で書く (em-dash → hyphen、日本語禁止)。CLAUDE.md の cp932 制約セクションに追記済み |
| 単一 asset 修正でフル再ビルド (~55-70 分) を回さず最小 step で済ませる | `--skip-script --skip-qa` でも audio (~13分) + visuals (~13分) + assemble (~16分) + bgm (~6分) が全部走る。ある時点 で closing_02 画像 1 枚 / description 1 行のためにフル再ビルドを複数回し時間浪費 | **修正対象 → 必要 step の対応表で `--steps` を最小化**: scene_def の **narration/narration_speech 変更** → audio から (`--skip-script --skip-qa`、~55分) ／ **manim params・text_overlay content・visual.source_prompt のみ変更 (narration 不変)** → `--steps visuals,assemble,bgm --skip-qa` (~35分、audio/timing 不変) ／ **画像 source_prompt 変更** → 該当 `images/{scene}.png` を手動削除後 `--steps images,visuals,assemble,bgm --skip-qa` (image staleness、A 強化で hash 自動化予定) ／ **episode_config.references・wikimedia_credits のみ変更** → `--steps credits --skip-qa` (~3秒、description.txt のみ再生成、動画再ビルド不要) ／ **音声・字幕も不変で BGM/endcard だけ** → `--steps bgm`。`python src/pipeline.py <config> --steps <csv> --skip-qa` 形式。timing.json は narration 不変なら有効なので audio スキップ可 |

---

## Claude CLI / API

| 問題 | 原因 | 対策 |
|---|---|---|
| Opus指定のつもりがSonnetで動いていた | `CLAUDE_MODEL_MAP["opus"] = None` で CLI の --model フラグが渡されず、CLI デフォルトの Sonnet に解決されていた（初期/中期エピソードでが全てSonnet） | `claude-opus-4-6` を明示指定（修正済み）。Opus は max_output_tokens=64K で 18分長尺にも余裕 |
| Claude応答の先頭が切れる（max_output_tokens到達） | Sonnet 32K / Opus 64K の上限を超えるとマルチターンに分割され、`--output-format text` は最後のassistantメッセージのみ返す | `--output-format stream-json --verbose` で全assistantイベントを連結（修正済み） |
| pronunciation_check の Claude 呼び出しが毎回18分 | narration 1行変更でもフル再送信 → 部分再ビルドが遅い | エントリ単位（scene_id+index+text+kana）の hash キャッシュ `_proncheck_cache.json` を追加。未変更エントリは Claude を skip（対応セッションで修正済み） |
| Claude CLI Opus が長文 JSON 生成で Bash workaround を試み内容を失う | Opus は max_output_tokens に達しそうと自己判断すると `Bash` ツールで JSON を出力しようとする。`stream-json` パーサは assistant text のみ連結するので Bash stdout は捕捉されない。対応エピソード で script_generator が attempt 1 で truncated JSON、attempt 2/3 即時失敗 | `claude_backend.call_claude` に `allowed_tools` パラメータ追加、script_generator / qa_checker から `allowed_tools="Read"` で呼び出して Bash 自体を禁止。プロンプトにも「Bash 等のツール禁止、assistant text に直接出力」を明記（対応セッションで修正済み） |
| **警告を出そうとした瞬間にクラッシュする (cp932)** | Windows コンソールの codepage は cp932。em dash・絵文字・✅❌・上付き文字・ひらがな ゔ・稀漢字を `print()` すると `UnicodeEncodeError` でプロセスが死ぬ。**問題はどこに潜むか**で、実例はすべて warning / FAIL 経路にあった → 正常系では一度も踏まれず、**肝心なときにだけ落ちる**。尺 lint は「非推奨の尺を検出した瞬間」= その lint が存在する理由そのものの経路で落ちており、一度もクラッシュしていなかった | エントリポイント (`main()`) の冒頭で `sys.stdout.reconfigure(encoding="utf-8")`。**ASCII 代替が使える文字なら置換が優先** (プロジェクト規約) だが、辞書データの ゔ / ² のように**文字そのものが情報**の場合は置換できないのでガードが要る。**subprocess で起動される step は親のガードが届かない**ので各自で設定する。smoke test section 20 が全エントリポイントを静的検査 |
| 長時間ビルドの途中で OAuth が失効し **QA が一斉にサイレント失敗** | `claude -p` を使う QA (LLM QA agents / 画像・Manim の Vision QA / 概要欄の意味 review) は呼び出し元がそれぞれ graceful degrade するので、認証が切れても例外にならず「全部 skip されたまま green で完走」する | 認証 ping を **起動時 preflight と Vision QA 直前の 2 回**打ち、失効していれば何を skip したかを最終サマリに出す。判定は positive signal (healthy な ping は `pong` を返す) で行い 401 の文言に依存しない。`--skip-auth-probe` で抑止。**恒久策は運用側** — 長時間ビルドの前に `claude setup-token` (1 年 OAuth) を設定する |
| Vision QA / claude CLI 系の subprocess 経路で `chcp 65001 >nul &&` prefix が silent fail | `pipeline.py` の `_run_subprocess_with_stderr_capture` (X3 stderr channel、対応 Day で導入) が子 python の stderr を非 TTY pipe にし、その子の `os.system("chcp 65001 >nul && type \| claude ...")` が exit 1 を返す。Vision QA Gate 2 が「Claude Code CLI returned no output」を 19/19 scenes で返し status PASS を偽装、画像品質の事実上の未検証で ある時点 まで露見せず。直接 `python src/qa_image_checker.py ...` 実行は動作。同パターンの `image_generator.py` の inline eval、`wikimedia_fetcher.py` の auto-appearance gen も同じく沈黙 fail | 3 ファイル (`qa_image_checker.py` / `image_generator.py` / `wikimedia_fetcher.py`) から `f"chcp 65001 >nul && "` prefix を削除（対応 Day で修正済み）。プロンプトファイルが `encoding="utf-8-sig"` BOM 付きで書かれており claude CLI の UTF-8 判定には十分、chcp 呼び出しは元々不要だった。修正後、subprocess.Popen 経由でも 19/19 scenes 全検証可能を確認 |

---

## 環境 / Windows / venv / worktree

| 問題 | 原因 | 対策 |
|---|---|---|
| subprocess.run() が動かない | Windows + Claude Code CLIの相性 | `os.system()` + tempファイル |
| print文でcp932クラッシュ | Windowsコンソール(cp932)で絵文字・特殊Unicode出力 | print内の絵文字はASCII代替（[OK], [WARN]等）を使う |
| worktreeでGemini APIキーが読めない | `_load_dotenv()` がworktree親ディレクトリまでしか探索せず、メインリポの`.env`を見つけられない | worktreeの`.git`ファイル（gitdir参照）を読んでメインリポルートまで遡る実装を追加済み |
| pipeline が長時間走った後で Claude CLI 401 / venv非活性 に気づく | 対応エピソード で 57分 + 30分 の dead-end を経験（前者はトークン期限切れ、後者は絶対パスなしの bash で venv を activate し忘れ） | `pipeline.py` 起動時 `run_preflight_checks()` が Python モジュール（matplotlib/google-genai/fontTools/PIL）、Claude CLI 認証（ping）、VOICEVOX 起動を `fail-fast` で検証（対応セッションで修正済み。Claude ping は steps が script を含む時のみ、VOICEVOX は audio を含む時のみ実行） |
| audio_generator pronunciation summary 出力で UnicodeEncodeError → scene_definition.json save 失敗 | `_print_pronunciation_summary` の print 文中に em dash `—` (U+2014) があり、Windows cp932 console でエンコードできず crash。複数の pronunciation fixes (rule + Claude) を計算した直後の summary print で abort → save 未実行で修正提案が失われる。過去のケースで発覚 | print 文の特殊 Unicode は ASCII 代替に統一（ルールの徹底）。`—` → `--`（対応セッション、3箇所修正済み） |
| Python hook / script の stdout 出力で UTF-8 日本語が Windows cp932 console で文字化け | hook の `print()` が UTF-8 文字列 (日本語・記号) を含む時、Windows console が cp932 で受け取り mojibake (例: `��|�[�g`) になる。過去のケースで `.claude/hooks/qa_report_reminder.py` の hook reminder で発覚。emoji / em-dash と違い日本語はクラッシュせず黙って化けるため発見が遅れる | main() 冒頭で `sys.stdout.reconfigure(encoding="utf-8")` + `sys.stdin.reconfigure(encoding="utf-8")` を呼び出す (Python 3.7+)。新 hook / 新 script で日本語や特殊文字を出力する場合はテンプレ化推奨 |
| worktree session が main repo の settings.local.json hook を見ない | main repo に hook を登録しても、worktree (`/.claude/worktrees/<name>/.claude/settings.local.json`) 内に独立の settings ファイルがあり、worktree session はそちらをロード。過去の hook 動作検証時に発覚 | worktree session でも独立に hook 登録が必要。`.claude/hooks/qa_report_reminder.py` 自体は repo にあるので path 指定だけで OK (絶対パス推奨)。session-wrapup 関連の注意事項あり |

---

## QA エージェント / Vision QA

| 問題 | 原因 | 対策 |
|---|---|---|
| QA ContentReviewer が尺超過 false positive を出す | 目標尺が prompt にハードコード「8-12分」→ 18分長尺回では必ず警告 | `episode_config.target_duration_minutes` を ContentReviewer プロンプトに注入（対応セッションで修正済み） |
| QA agent の非決定性（過去のケースで「5名 Acta 掲載→4名に修正」と「4名→5名に戻せ」が別回で発生） | FactChecker/ContentReviewer は LLM 判定で run 間に揺れる | 史実で自己判断。`common_errors_to_avoid` に明示してあれば QA 指摘を却下する判断基準になる。メモリ過去の運用知見の方針（鵜呑み禁止）を発動 |
| Gate 2 (qa_image_checker.py) が新規ビルドで未稼働 | pipeline.py で Gate 2 呼び出しが image step **前**に配置されており、新規ビルドでは未生成画像を評価しようとしてスキップ。複数の対応エピソードで `qa_report_images.json` が一度も生成されていなかった。対応セッションで発覚 | **解決済み**: pipeline.py の Gate 2 呼び出しを image step + 画像枚数検証の**後**に移動。`--qa` で default ON、`--skip-qa-image-narration` で opt-out。プロンプトは 5 sub-aspect (主要人物の有無 / 性別 / 人数 / 活動小道具 / 細部) + severity 基準で細分化。全エピソード dry-run + 個別エピソードの監査で TP 確認 |
| Vision LLM 単発実行で critical 検出が保守的 | qa_image_checker.py の severity 判定が単発 run で flip。特定エピソードの該当シーン が isolated 3 runs で 2/3 critical だが、全エピソード dry-run (single-run sweep) では 0 critical / 4 warning。同じ画像でも run ごとに「critical / warning / 細部 info」が変わる | severity escalation tuning は将来課題。当面は warning level で人間レビューに promote する運用。重要シーンは multi-run で確認を推奨 |

---

## 事実誤認 / 史実考証

| 問題 | 原因 | 対策 |
|---|---|---|
| 事実誤認: ニュートン王立造幣局での忙しさを「ロンドン大火事後」と誤る | 大火事は1666年、当時（1697年）から31年前で無関係 | 正しくは1696-99年の『通貨大改鋳事業（Great Recoinage）』。ニュートンは1696年4月から造幣局監事（Warden of the Mint）として新貨鋳造を指揮 |
| 事実誤認: オイラーの1726年論文を「博士論文」または「学位論文」と呼ぶ | 当時バーゼル大学には数学の博士号制度がなく、De Sono 自体も学位取得用ではなくバーゼル大学物理学教授職への応募論文だった。「学位論文」も厳密には不正確 | 「論文『音の伝播について』」または単に「論文」が正確。教授職応募の文脈を補うなら「教授職応募論文」。Euler は1723年に哲学修士、1726年に De Sono 提出、1727年ペテルブルク渡航（20歳）。日本語の定評ある伝記で「学位論文」表記が定着しているかは未検証 |
| 事実誤認: オイラーとヨハンの面談曜日（Saturday vs Sunday） | Boyer/Dunham 等の通俗伝記は Saturday、MacTutor/Euler自伝（独語 Sonntag）/Eneström 伝記研究は Sunday | 一次資料優先なら Sunday。QA agent が非決定的に Saturday を示唆することもある。論争回避なら「毎週末の午後」で中立化（対応セッションで採用） |
| 「両親」が結婚時の親生死を反映しない | 過去のケースで「ゲーデルの両親は終生この結婚を認めませんでした」と書いたが、父Rudolf 1929年没・結婚1938年で「両親」は不正確（結婚9年前に父死去）。IAS伝記の「parents disapproved」は1927年からの**交際**期間を指す表現 | 結婚・両親言及は「親の生没年 vs 結婚年」を確認してから書く。曖昧化したいなら「家族は」、長期交際を含むなら「交際を認めず」（父生存時を含むので両親OK）等で表現を選ぶ |
| 私の episode_config.json に最初から事実誤認（裏取りなし） | 対応エピソード で私が知識ベースから直接書いた verified_facts / key_episodes 5件が誤り（Hahn 55→54歳・Vienna脱出 1939/12→1940/01/15・Schlick犯人「不合格を恨んだ」→ Nelböck は1931年Schlick指導下で博士号取得済み・「不合格」は完全な事実誤認 等） → script に伝播 → script生成 23.8分 + QA 17.5分 のロス | episode_config.json の verified_facts / key_episodes を確定する前に、特に**年齢・年月日・職業・人物関係**は web verify する。**解決済み**: `pre_script_fact_check.py` が pipeline.py の script step 直前に C (Sonnet 知識ベース) + D (算術サニティ: 享年・event 年範囲) + E (Wikidata SPARQL 照合、birth_year hint で同名曖昧化) の3層検証を実行し、CRITICAL/WARNING で pipeline 停止。対応エピソード で内部不整合 3件を実検出 (建築家 vs 土木技師、1825年8月 vs 9月、ガロア応募テーマ) |

---

## コンテンツ設計

| 問題 | 原因 | 対策 |
|---|---|---|
| エンディングがtext_overlayだけで映像的に弱い | 最終シーンにken_burnsを使わなかった | **最終シーンはtext_overlayではなくken_burnsで締める**。原点に戻るイメージ（生誕地、学校等）が余韻を生む |
| 続編エピソードで「前回」「次回」など連続性語が紛れ込む | 同じ数学者の続編回 (同テーマの連続エピソード、解析篇→応用篇 等) で hook や本編に「前回扱った」「今回はその続き」等を入れると、視聴者が任意のエピソードから入った時に違和感。LLM は episode_config の theme/intro_guidance/additional_instructions に他エピソードへの cross-ref があるとそれに引きずられて narration を生成する | 各エピソードを単独完結で設計。「各回の独立性を重視」を運用ルール化 (前回・次回・続編・シリーズ・以前の動画 全般 NG)。episode_config.json と scene_definition.json から他エピソード参照を全削除し、common_errors_to_avoid に「連続性誘導NG」項目を明記 |

---

## 最近追加（未分類）

（ここに新規エントリを追加し、四半期程度で上記カテゴリに統合する）

### Day 19 追加

| Pitfall | 原因 | 対策 |
|---|---|---|
| Claude が JSON 出力途中で「I'll output the complete JSON now, starting fresh」と self-restart し 2 つ目の ```json ブロックを出力、`script_generator.extract_json` が最初の (壊れた) ブロックを掴んで JSONDecodeError → build 失敗 | 非貪欲 regex `\{.*?\}` が最初の ```json...``` 内の最初の `}` 風 closing で match、後続の valid ブロックを見ない。強化の 4-strategy parser は「最初に find した block を try」順序のまま | `extract_json` で **ALL ```json ブロックを列挙 → 最後の valid を採用**。`re.finditer(r"```json")` で全 fence position を取得し reversed 順に json.loads を試行。31 件 regression test で edge cases (single block / bare JSON / 日本語 prefix / 2 ブロック last valid / invalid raises) 全 PASS |
| 主題者以外の人物 scene (Hermite / Kovalevskaya 等) に主題者 reference photo が当たって顔汚染 | `wikimedia_credits.json` には主題者 (Karl Weierstrass) の写真のみで Hermite/Kovalevskaya 用の reference 不在。image_generator は scene が non-subject であることを自動検出せず、`use_reference: true` (default) のまま主題者写真を使用 | `image_generator.detect_non_subject_person(prompt, subject_en)` を新設 (capitalized word pair + EXCLUDE list で false positive 抑制)。`should_use_reference_photo_with_subject_guard` で自動 use_reference=false + 警告出力。moriarty 用 EXCLUDE (Strand / Victorian / Young / The 等) で false positive 抑制、ある回 用 true positive (Charles Hermite / Sofia Kovalevskaya) 維持を 13 件 unit test で確証 |
| Portrait prompt と reference 写真の特徴矛盾 | reference を実 verify せず想像で prompt を書いていた。Gemini は reference と矛盾する prompt を渡されると「画像 reference + テキスト description」のどちらに従うか不安定で variance 増大 | `scripts/portrait_prompt_lint.py` standalone (Gemini Vision で reference 写真を describe + source_prompt と矛盾検出、Gemini Flash で軽量)。Pre-build opt-in tool として template/portrait 編集時に手動実行。Pipeline 自動統合は cost (Vision call × N scenes) のため保留 |
| 同一文中の年号倒錯 (math_04「コーシーが1821年に始め、ボルツァーノが1817年に独立して着想していた」← 文法的には過去完了「ていた」で正しいが音声で誤解されやすい) | LLM ConsistencyChecker は「各年号は正しい / 各事実は独立に正しい」と判定 → 出現順 vs 数値順の不一致を見落とす。文法的には正しいので strict warning にはならない | `qa_checker._detect_temporal_ordering` deterministic regex。同一文 (句点区切り) 内の年号 (1[0-9]{3}|20[0-9]{2}) を抽出、出現順 ≠ 数値順なら flag。過去完了マーカー (「ていた」「していた」等) ありなら severity=info、なしなら warning。dearu_lint に統合され build 中自動実行 |
| Manim テンプレ新規 mode の文字衝突 (weierstrass_function.partial_sum_build の formula vs curve / epsilon_delta_continuity.bolzano_weierstrass の cluster_label vs a_star_label) は smoke_test の Y-clearance + MathTex 日本語 lint では catch できず、初回 build render するまで判明せず | smoke_test の section 3 は AST/regex で template discovery + SCENES dict + LINT_FACTUAL_CLAIMS の static check のみ。Manim render は実行しない (1 mode あたり 10-20 秒、全 81 templates × 多 modes = 20+ 分で smoke の 5 秒原則を破る) | `scripts/manim_preview_modes.py` standalone preview render script。`-ql -s` (低品質 + last-frame PNG) で 1 mode 約 24 秒。`--diff` で git 変更分のみ render してコスト抑制。template 編集ワークフローでの opt-in tool として manim-development.md に追記候補 |
| VOICEVOX が `ヴァ` + イ/ス で `ヴ → バ` degradation (ヴァイエルシュトラス → バイエルシュトラス、ヴェストファーレン → ベストファアレン)。`audio_query` の予測カナでは バ で返るので kana 化で迂回不可 (`ゔぁいえるしゅとらす` → 予測 `ヴァイエルシュトラス` だが合成音は `バ`) | VOICEVOX 内部 phoneme inventory に `v` 音素が limited、`ヴ + イ/ス` の組合せで合成段階で `b` に degrade。`ヴァ + ウ` などは通る (ヴァウチ正常) | **既存問題として user 許容** (バイエルシュトラスは日本語数学教科書の慣用読み)。global 辞書での kana 化 fix は無効と ある時点 で empirical 確認、修正対象外。新エピソードで主題者名に `ヴァ + イ/ス` を含む場合はこの degradation を予期して title/narration を設計 |

### Day 19 運用反省 (process pitfalls)

| Pitfall | 原因 | 対策 |
|---|---|---|
| Background pipeline 完了通知が delivery 不安定で、ETA 経過後に user から「まだですか?」と催促されるまで status check しなかった | harness の task-notification に依存しすぎ、長時間 task で notification miss/delay の可能性を考慮せず | ETA + 5 分後に自主的に status check する運用習慣を確立。長時間 task は ETA 経過を意識して proactive status report する |
| 「reference を実際に確認しないで想像で prompt を書く」基本動作怠り (Weierstrass を full beard と prompt に書いたが reference は clean-shaven) | Wikimedia 写真の URL を持っているのに WebFetch + Read で実 verify を最初から行わず、伝聞 (Wikipedia の text description) のみで判断 | **新規 episode の portrait prompt 作成時、wikimedia_photo_urls の actual image を WebFetch + Read で必ず先に view してから prompt を書く**。強化 C (`portrait_prompt_lint.py`) で構造防御化 |

### Day 22 追加

| Pitfall | 原因 | 対策 |
|---|---|---|
| route_map の **都市ラベル同士 / 都市ラベル×route ラベルの衝突** が既存 collision 検出を素通り | 既存 `_check_route_map_collisions` は title↔route_label / route_label↔route_label のみ対象で、`ax.annotate` で描く **都市ラベル (city_label_artists)** を collision 対象に含めていなかった。city_offsets で手動調整しても自動検出のセーフティネットがない | **強化 (1)**: `visual_generator._check_route_map_collisions(fig, title_artist, route_label_artists, legend, city_label_artists=None)` に city_label 引数追加。両 annotate site (city_offsets branch / auto branch) で `ax.annotate(...)` の戻り値を capture して list 化、city↔route_label / city↔city の bbox overlap を検出。**`_min_ov = 4` px 閾値** (dx≥4 かつ dy≥4 の両方) で 1px-tall sliver の false positive を抑制しつつ実衝突 (Ramanujan 32×14px / Seki 27×18px) は検出。回帰テストで閾値を実測チューニング |
| 日付字幕を Arabic 化 (`subtitle_generator.dates_to_arabic`) すると narration (Arabic) と narration_speech (漢数字) が構造的に乖離し、`_check_narration_speech_drift` / post_build_verify check4 が **毎回 false-positive WARN** を出す | 字幕は視認性のため Arabic、音声は VOICEVOX が漢数字を正しく読む (1601年→せんろっぴゃくいちねん) ため漢数字、という意図的 decoupling。だが drift 検出は両者を生のまま文字列比較していた | **強化 (2)**: `audio_generator._check_narration_speech_drift` で `_FORMULA_OR_ASCII_RE` check 後に `from subtitle_generator import dates_to_arabic` で narration/speech 双方を正規化してから比較。date-only diff は非検出化しつつ、実 drift (stale 「一切」残存等) は検出維持。test 4 ケース で確証。post_build_verify check4 も同 import 経路で同時解決 |
| 前写真時代エピソード (Kepler 1571-1630、Gemini 直接生成で use_reference=false) で description の **【画像クレジット】セクション欠落 WARN** が毎回出る | `pipeline.verify_outputs` の `_DESCRIPTION_REQUIRED_SECTIONS` が全エピソード一律で【画像クレジット】を必須化。Wikimedia 実写参照がない ep では画像クレジット自体が存在し得ないのに false WARN | **強化 (3)**: `verify_outputs` で `episode_dir/episode_config.json` の image_style.use_reference を読み、`required_sections = [s for s in _DESCRIPTION_REQUIRED_SECTIONS if not (s == "【画像クレジット】" and not use_reference)]` で条件除外。use_reference=true の ep では従来通り必須チェック維持 |
| VOICEVOX「金星」が「**きんぼし**」(相撲用語) と誤読 | 「金星」は天体「きんせい」と相撲「きんぼし」の同形異音語、VOICEVOX default が文脈なしで「きんぼし」を選択 | `audio_generator._MISREADING_CATEGORIES` math_terms に `金星→きんせい` を追加 (global 集積)。天体名は他にも同形異音リスクあり (sweep 推奨) |
| VOICEVOX 多面体名の係助詞同化 quirk: 「正八面体」full form → せいはちめんたい → 合成段階で「は」が**係助詞ワに同化**して「セイワチ」degradation | 「正八面体」の「八(はち)」の「は」を VOICEVOX が係助詞と誤認、連続音節最適化で「は→ワ」。一方 bare「八面体」→「正はちめんたい」と前置すると「せえはちめんたい」で正常 | **per-term で full/bare を実測選択**: 「八面体」は bare 形 (`八面体→はちめんたい`) を使い narration 側で「正」を別途付けない。逆に「正四面体」「正二十面体」は full form 必須 (bare だと「正し→ただし」「正に→まさに」の単独漢字誤読が出る)。VOICEVOX は audio_query で実測してから per-term 確定する (推測で dict 登録しない) |

> 構造強化 3 件は「学びを構造化する」cycle の継続。subtitle 日付 Arabic 化 (`dates_to_arabic`) は全エピソード自動適用の構造対応であり、ある回 固有の patch ではない。

### Day 23 追加

| Pitfall | 原因 | 対策 |
|---|---|---|
| **挙動を実測せず断定し、それを根拠に lint を作ってしまう** | VOICEVOX の読みを audio_query で実測せず推測で「誤読する」と断定。過去の運用知見にも誤 claim を一度書いた。実際は **VOICEVOX は漢数字年号も算用数字も同一に正しく読む** (四一五年→ヨンヒャクジュウゴネン = 415年) | **挙動 claim (誤読する/しない 等) は必ず audio_query 等で実測してから lint/修正/memory の根拠にする**。過去の運用知見(推測でなく実証) の audio 版。誤 lint (`qa_checker._detect_kanji_year_numerals`) は撤回、memory を訂正済み |
| 年号字幕が漢数字のまま残る | `subtitle_generator.dates_to_arabic` の年号 regex が `{4}` ちょうど4桁の positional 漢数字のみ変換し、**3桁年号 (四一五年) と BC (紀元前二六二年) を取りこぼし**ていた。年号は字幕表示の一貫性として算用数字が規約 (音声は漢数字でも正読のため decoupling) | **強化 (1)**: `dates_to_arabic` の年号 regex を `{3,4}` に拡張。3桁年号と BC も字幕 Arabic 化。2桁以下 (「二三年」=数年 口語 duration) と 十/百/千 を含む duration (千六百年・二十五年) は引き続き非対象。音声 (narration_speech) は不変 |
| 画像一貫性 QA が脇役を「主題者と別人=不統一」と false positive | `qa_image_checker.evaluate_consistency` が intro+person 全シーンを主題者前提で外見一貫性を評価。主題者に写真がない古代回 (全シーン use_reference:false) では脇役を判別する手段がなかった | **強化 (2)**: visual block に宣言フラグ `"is_subject": false` (default true)、`evaluate_consistency` の対象から除外。`no_human` / `use_reference` と並ぶ宣言フラグ。主題者シーンが2枚未満なら skip。`.claude/rules/image-generation.md` に規約追記 |
| VOICEVOX「陶片」が「**すえへん**」と誤読 | 「陶片」は「とうへん」だが VOICEVOX が陶を訓読み「すえ」で読む。pronunciation_check が拾えなかった (任意語彙の誤読は ground truth なしに検出困難) | per-ep は**言い換えで回避**: 「瓦や陶器の破片」(カワラ/トオキ/ハヘン と正読、audio_query 実測確認)。一般語彙の誤読検出強化 (独立読み器との照合等) は将来候補 |

> ある時点 の教訓: 「学びを構造化する」cycle で lint を足す前に、その lint の**前提となる挙動を実測**する。今回は実測を怠って誤 lint を作り、再検証で撤回 → 真因 (字幕表示規約 + dates_to_arabic の取りこぼし) に到達した。構造修正の前に根拠の実測。

### Day 24 追加

| Pitfall | 原因 | 対策 |
|---|---|---|
| **主題者 portrait が「理想化された別人」になる** | **複数経路の reference under-use**: (a) `should_use_reference_photo_with_subject_guard` の REF-GUARD が capitalized word-pair (地名 "Dunsink Observatory" / 脇役 "Zerah Colburn") を non-subject person と誤検出して reference を **force-drop**、(b) 私が config の additional_instructions に「脇役登場シーンは use_reference:false」と書き、script_generator が主題者シーンにも過剰適用、(c) `detect_has_person` の keyword miss で person scene が text-only に。結果、実写真が Gemini に渡らず text description のみで生成 → 顔が prompt の美化バイアスで理想化 | **4層構造修正**: (1) REF-GUARD を force-drop → **advisory に demote** (`return base, warn`、判断は explicit flag に委譲)、(2) `_build_reference_prompt` に**非美化指示**追加 (render faithfully / do NOT beautify・slim・idealize / preserve hairline・baldness・side-whiskers)、(3) `script_generator` に use_reference 運用ガイダンス追記 (主題者シーンは true 維持、脇役同席だけで false にしない、地名・施設名は人物でない)、(4) 主題者シーンが参照不使用で text-only 生成された時の **[WARN] safety net**。`generate_image_with_reference(contents=[ref_img, prompt])` の **image-conditioning は text-only より圧倒的に忠実** |
| **subject_appearance (顔特徴記述) を編集しても画像が再生成されない** silent gap (手動 `--regen` を強いられた) | `_prompt_fingerprint` が source_prompt + no_human + use_reference のみ hash し、`_build_reference_prompt` が注入する `appearance` を含めていなかった → fingerprint 不変 → ある時点 の staleness 自動再生成が発火せず | appearance を fingerprint に畳み込み (**use_reference シーンのみ**)。**legacy fingerprint で後方互換**: appearance 追跡前の旧 meta は migration のみ扱いで deploy 時の一斉再生成・既存 curation 破壊を回避。`--scene` 部分ビルド・生成失敗時の self-heal も維持。ユニット11件で確証。`image-generation.md` の「スキップ仕様」を自動再生成 に訂正 |
| **重い 3D primitive (Arrow3D) が 240s timeout → text_overlay placeholder に silent fallback** | `Arrow3D` の 3D cone mesh が 1080p で極端に重く、3本 + 連続 `Rotate` で 240s 超過。timeout fallback が `[OK]` 報告 + placeholder mp4 を出すため silent ship | (1) `Arrow3D` → `Line(ORIGIN, [x,y,z])` 代替で **240s → 15s**、(2) pipeline 完了時の **placeholder CRITICAL バナー** (既存 fallback 記録を `[CRITICAL]` で顕在化)、(3) render が timeout の **70% (168s) 超で near-timeout [WARN]**。`manim-development.md` に重い primitive 注意を追記 |
| Background pipeline のログが block-buffer されてリアルタイム進捗を監視できない | stdout が block-buffered で長時間 step の進捗が flush されず、status 確認のたびに stale | `pipeline.py` main() 冒頭で `sys.stdout/stderr.reconfigure(line_buffering=True)` (try/except 包み) |
| VOICEVOX「価値」→「**価あたい**」誤読 | **VOICEVOX native は「価値→かち」と正読** (「ニュースとしての価値」「科学の価値」を audio_query 実測 → カチ)。あたい は **global 規則 `("値","あたい")` (line 734) が「価値」の「値」に over-match した rule-induced 誤読**。VOICEVOX 由来でない | `audio_generator._MISREADING_CATEGORIES` math_terms に `価値→かち` を `値→あたい` より前に置き先回り guard (安全・必要)。**注意**: これは `値→あたい` の guard-accumulation anti-pattern (期待値/極限値/絶対値… と explicit guard を反応的に積む構造)。`値→あたい` を「単独 値 のみ match」に厳密化する根治は将来候補 (risky refactor)。006/024 は native では かち だが、`値→あたい` の build 時状態次第で 価あたい 出荷の可能性 → shipped-ep 別判断 |
| 「(頂点を) 通って」が「**かよって**」と読まれる — だが**安全な global 規則は作れない** | 通る(とおって=通過) と 通う(かよって=通学/通院) の **context-dependent homograph**。VOICEVOX は「ずつ通って」を文脈無関係に カヨッテ と読む (audio_query 実測: 「頂点を一度ずつ通って」「辺を一度ずつ通って」「二度ずつ通って治療」全て カヨッテ)。通過では とおって、通院/通学では かよって が正で、同一 substring が両義 | **当初 `ずつ通って→ずつとおって` を global 追加したが ある時点 中に撤回**: 「週に二度ずつ通って治療」(=かよって が正) を誤って とおって に壊すため。「を通って」は VOICEVOX が既に トオッテ と正読 (規則不要)。→ **path 文脈は per-ep narration_speech で対応**。**global 集積原則の精緻化: global 辞書は「文脈非依存で常に正しい誤読補正」のみ。homograph は per-ep**。019 は path 文脈 (辺→アタリ + 通って→カヨッテ の latent 誤読) だが既出荷・別判断 |

> ある時点 の運用反省 (1): 理想化された portrait を見て **「AI 画像生成の限界」と外部要因に帰責して調査を打ち切った**。user の「本当に限界ですか?」push back で再調査 → 真因は「reference を Gemini に渡せていない」自前パイプラインの bug だった。過去の運用知見の再演 (前回は「自分のコードは正しい」、今回は「AI の能力限界」と、いずれも調査を止める言い訳に外部/自明要因を使った)。**「限界」と言う前に、その限界に到達する経路が本当に動いているかをコードで確認する**。

> ある時点 の運用反省 (2): VOICEVOX 誤読の global 規則を **ambiguous case を実測せず追加し、「他 ep に誤読 residue がある」と grep の substring だけで断定**した。user の「文脈によってはかよっても正しい」で audio_query 実測 → (a)「ずつ通って」は通院文脈では かよって が正で global 規則は有害、(b)「価値」は VOICEVOX native では かち で誤読 residue は存在せず (あたい は別規則由来) と判明し、規則撤回 + 主張訂正。ある時点 の教訓「lint/規則を足す前に前提挙動を実測」の再演。**global 規則を足す前に、その規則が壊しうる反対文脈 (homograph の他読み) を必ず実測する。grep の substring 一致を『誤読』と断定しない**。

### Day 29 追加

| Pitfall | 原因 | 対策 |
|---|---|---|
| **指数タワー (A^(B^C)) を日本語プローズ化すると 乗 / 括弧が落ちて誤読される** (ある回: フェルマー数 2^(2^k)+1 を「2の2のk乗」と narration/字幕表示。乗が一つ足りず、視聴者には 2^(2k) と読める。実際 2^(2k)+1 は 2,5,17,**65**,257… で動画の 3,5,17,257,65537 と不一致) | (a) `episode_config.verified_facts.fermat_primes` は `2^(2^m)+1` と **正しかった**のに、script 化で外側の 乗 が脱落。(b) **画面に式 (Manim/text_overlay) を出していなかった**ため、曖昧な散文だけが唯一の情報源になり誤読を anchor できなかった。柱1の overlay は素数リスト + 作図条件のみで式そのものが不在だった | **3層**: (1) 字幕は **括弧**で曖昧性除去 →「2の(2のk乗)乗」、(2) narration_speech は **明示的に 2 つ目の 乗** を入れる →「2の、2のケー乗、じょう」(読点で pause)、(3) **text_overlay に式 `2^(2^k)+1` を表示**して視覚で固定。再発防止に `scripts/lint_tower_exponent.py` (smoke test section 12, advisory WARN) を追加: narration/narration_speech の「AのBのC乗」(3 短トークン・の 2 つ・乗 1 つ) を検出。分数 (`8分の1のxの2乗`)・根 (`二の三乗根`)・属格の の (`コサインのbのn乗`)・単一指数 (`aのpマイナス1乗`) は除外 (look-behind + 分/ぶん/根/階乗 文脈 + 末尾 2 つ目の乗 の look-ahead)。**全 37 ep を sweep して真のタワーは ある回 の 1 件のみ**だった |

> ある時点 の学び: 数式を「散文 + 音声」だけで伝えると、二段指数のように括弧が本質的な式は構造的に曖昧化する。**口頭・字幕で崩れやすい式 (タワー・入れ子・優先順位依存) は Manim / text_overlay で視覚化して anchor する**のが根治。元データ (verified_facts) が正しくても、プローズ変換段で情報が落ちる経路を lint で塞ぐ。公開済みエピソードのため動画自体は再レンダリングせず、(1) ソース修正 (記録整合 + 将来の再 build 用)、(2) 視聴者コメントへの訂正返信、で対応。

## Day 30 の落とし穴と構造化

| 落とし穴 | 原因 | 構造化した防御 |
|---|---|---|
| **`episode_config.voicevox_dictionary_additions` に読みを書いても無効 (no-op)** | このフィールドを読むコードが src/・scripts/ に存在しない (廃止済、`voicevox_dict.json` に統合)。ある回 で 49 語入れたが全て無視され固有名詞が VOICEVOX デフォルト読みに | `config_validator` に WARN 追加 (populated なら「廃止フィールド・no-op、src/voicevox_dict.json に登録せよ」)。smoke section 2 で表面化 |
| **narration_speech で漢語をひらがな化すると語中「へ/は/を」が助詞 (え/わ/お) 化** | VOICEVOX が「きょうへん」の へ を方向助詞と解釈し「キョオエン」。共変→きょうへん が裏目 | **読みカナはカタカナで書く** (キョウヘン)。`reading_guard` に へ助詞罠検出を追加 (author 導入のひらがな run のカタカナ化との実測差分、への は除外、FP ゼロ) |
| **reading_guard PASS が新規固有名詞で空振り** | `KNOWN_READING_RISKS` は過去回のハードコード。外国人名の多い回は「measured 0」で PASS だが都/棺/共変/七橋が全誤読 | `reading_guard` に辞書未登録カタカナ固有名詞のカバレッジ表示を追加 (PASS でも「N 件未照合 → 手動実測推奨」)。**新規 ep は PASS を信用せず全 effective audio を kana 実測** |
| **生成画像に焼き込まれた白縁が動画で白帯になる** | Gemini が油絵に白いキャンバス縁を描き込み、ken_burns 15% ズームでも消えない幅 (person_05、約100px) | `scripts/lint_image_borders.py` 新設 (四辺 near-white strip 実測、`--trim` で content box 自動クロップ)。pipeline images step 直後に WARN 配線 |
| **晩年 reference しか無いと若年/中年シーンも老人化** | use_reference 既定 ON で、プロンプトに「twenties」と書いても reference 写真 (晩年) が年齢を上書き (person_02 の20代三人組が全員老人) | 群像・若年・中年シーンは `use_reference: false` + プロンプトに年齢明示。理想は年齢別 reference。**images regen 後は Vision QA (`qa_image_checker`) で人数/年齢を assemble 前に検証** |
| **「時短のため --skip-qa」が逆に総時間を増やす** | 画像問題が動画段階まで漏れ、user レビューで都度発覚 → assemble+bgm を複数回やり直し (~20分の QA を惜しんで ~32分の再ビルドを数回) | **勝手に QA skip しない**。画像 regen を含む再ビルドでは Vision QA を回す。`--skip-qa` は内容不変の mechanical 再ビルド限定 |

> ある時点 の学び: 学びの大半を lint/check に構造化 (#1 config dead-field WARN / #2 白縁 lint / #3 へ助詞罠 / #4 固有名詞カバレッジ)。**「整合しているから」で検証を打ち切らない** — description「19世紀末」を一度本編一致で流したが、web 実証 (イグノラビムス論争は1872発・1880s-90s 拡大) で「広がった時期=世紀末」は妥当と確定。2箇所が一致していても両方不正確なら正しくならない。承認/却下とも一次資料で実証してから。

### Day 47 追加

| 問題 | 原因 | 対策 |
|---|---|---|
| **Cloud で f'(x)→「エフゴエックス」/ 生 L=T-V の誤読** | `gen_cloud.build_cloud_reading` は記号行で `narration_speech` (VOICEVOX スペルアウト) を読みに使う設計。narration 編集で `narration_speech_cloud` を削除して再生成させる際、**`narration_speech` も一緒に削除**すると記号のスペルアウト元が消え、生記号が cloud に漏れ Chirp が誤読 | `gen_cloud.spell_formula_tokens` (narration_speech 非依存の記号→読み辞書 L=T-V/f'(x)/f''(x)/Lₙ、生成時に常時適用・idempotent・prose-safe) + `cloud_reading_lint._scan_raw_formula` (cloud=合成テキストの生記号残存を backstop 検出)。**symbol scene の narration_speech_cloud は削除でなく変更分だけ手編集** |
| **narration 編集→再ビルドで字幕(旧)/音声(新) が desync** | `--steps` に subtitles を入れ忘れ (visuals,assemble のみ)→字幕.srt が旧 narration 由来。従来は assemble 完走後の G2 検査で検出=20分の無駄ビルド | `pipeline._subtitle_staleness_check` で assemble 直前に fail-fast。**narration 編集時は subtitles と visuals を両方 steps に含める** |
| **写真技術以前の人物に「肖像写真を参照」クレジット** | credits の参照肖像呼称が定型「肖像写真」 | `credits_generator._reference_kind` で `death_year<1840` なら「肖像画」に自動切替 (pre-photo WARN は backstop に降格) |
| **Wikimedia 空欄著者が「by Wikimedia Commons」に誤帰属** | `wikimedia_fetcher._format_credit` の `author or "Wikimedia Commons"` がリポジトリ名を著者に default | `author or "Unknown author"` に。CC-BY 作品は必ず実著者を持つのでこの default は無帰属 PD/CC0 のみに効く |
| **Cloud のコンマ伸ばし (力学から、図を、…を、→ からー図をー)** | 同一格助詞+読点の反復を Chirp が読点前母音で伸ばす | `cloud_reading_lint._scan_comma_elongation` (読点≥3 かつ同一格助詞〔をにへが〕+読点≥2、列挙リスト/も-list は非検出)。読点を減らす/「まで」等で連続を崩す |
| **隣接 narration がほぼ言い直しの重複** | 編集で隣の文を言い直しただけの重複 | `cloud_reading_lint._scan_adjacent_dup` (文字bigram overlap≥0.5、数字のみ差の並列テンプレ〔四平方の例 7=2²+…/31=5²+…〕は除外) |
| **並行セッションが main 作業 dir のブランチを stale へ切替え src 巻き戻し** | 並行タスク/セッション起動時に main dir の HEAD が古い `claude/*` へ checkout→追跡 src が巻き戻り、切替後に**新規起動**したビルドが preflight 失敗 (走行中 python は起動時メモリ展開済みで切替耐性) | 診断=reflog/worktree list/ps の claude 起動時刻。復旧=`git checkout <正ブランチ> -- src scripts` (surgical・未追跡成果物無傷)。過去の運用知見|

> ある時点 の学び: **音声修正は scene_def テキストでなく出荷 wav を STT で照合してから「反映済み」と言う** (`verify_shipped_audio.py`、f'(x)→「F プライム X」を実音声で確認)。**primacy/最上級の主張は狭く** (「最も有名な遺産」は L 点を最有名とする過剰主張=未定乗数法・解析力学の方が広く知られる)。**git 異常時は session-wrapup 自動フローをそのまま実行しない** (chimera 作業ツリーでは `checkout -- .` が未 commit の成果を消す→refactor/m1 から新 worktree で commit)。
