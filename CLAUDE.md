# CLAUDE.md — 数学史記 プロジェクトルール

> Claude Code が毎セッション読むプロジェクトルール。本ファイルは規約のコアとインデックスを担う。
> 詳細な規約・ワークフロー・落とし穴集は `docs/` および `.claude/rules/` (path-scoped) に外出ししている。
> アーキテクチャ全体像は [`docs/architecture.md`](docs/architecture.md) (4 Mermaid 図)、利用者向けの導入は [`README.md`](README.md) を参照。

---

## プロジェクト概要

日本語 YouTube 数学史ドキュメンタリー動画制作パイプライン。
`episode_config.json` → 10 ステップ自動パイプライン → `output_final.mp4` (10〜19 分、詳細仕様: [docs/02_pipeline/VIDEO_SPEC.md](docs/02_pipeline/VIDEO_SPEC.md))。

## 環境

| 項目 | 値 |
|---|---|
| OS | Windows 11 想定 (Linux/Mac 動作未確認、GPU なし環境想定) |
| Python | 3.11.0 (venv 内は `python`、venv 外は `py`) |
| venv 有効化 | `venv\Scripts\activate` (Windows) / `source venv/bin/activate` (Unix) |
| Manim | v0.19.2 (`-qh` で 1080p) |
| VOICEVOX | 0.25.1 (localhost:50021、GUI アプリ起動必須) |
| FFmpeg | 2026-02 以降推奨 |
| フォント | BIZ UDMincho (日本語全般、OFL 1.1) |

## Windows 固有の制約

- **`subprocess` 禁止 (Claude CLI 経路)**: Claude Code CLI (`claude -p`) の呼び出しは `os.system()` + tempファイル方式。`subprocess.run()` / `subprocess.Popen()` は使わない (Windows での日本語クラッシュ回避)
- **`findstr` 非推奨**: 日本語テキストやパイプ演算子で不安定。ファイル渡しか `type` を使う
- **Claude Code CLI `-p` モード**: `--allowedTools Read,Bash` が必須 (v2.1.63 以降)
- **cp932 対応**: `print()` の絵文字・特殊 Unicode (em dash 等) は ASCII 代替に統一 (Windows console は cp932)。`requirements*.txt` のヘッダーコメントも非 ASCII 不可 (pip 22.3 が cp932 で読み込みクラッシュ)

## 品質チェックツール

| ツール | 用途 | コマンド |
|---|---|---|
| **smoke test** | pre-pipeline 静的健全性 (import / config_validator / Manim discovery、5 秒以内)。**ある回 拡張**: section 13 text_overlay 生キャレット / section 14 参考文献の刊行年欠落 / section 15 最上級 primacy 主張の一次資料 verify 促し。**ある回 拡張**: section 16 重複参考文献。**ある回 拡張**: section 17 quote オーバーレイの二重括弧 — `text_overlay` の `style:quote` は装飾用の「」を自動描画するので、`content.main` にリテラルの「」を入れると画面が二重「「…」」+折り返しで閉じ「」孤立になる。content.main は括弧なし本文だけに (sub は書名『』が正当なので対象外)。**ある回 拡張**: section 18 禁止表現の user-facing 漏れ — episode_config の **`forbidden_phrases`** (opt-in の表層文字列リスト) が scene_def の narration / narration_speech / narration_speech_cloud / text_overlay content / description.intro / title / chapter_subtitles に混入していれば WARN。error-debt (「割らずに」等) が script 生成や chapter_subtitles / description.intro に漏れても既存 QA (narration 中心) は **description ブロックを見ない** gap を塞ぐ。config 未設定 ep は no-op、`.get()` で後方互換。いずれも advisory。**ある回 拡張**: Y-clearance lint の正規表現に `-2\.0[1-9]` を追加 | `python scripts/smoke_test.py` |
| **reading guard** | VOICEVOX 誤読 pre-build 検出 (全 effective audio を global 辞書適用後に実測し既知誤読辞書照合、文脈依存誤読を検出。**narration_speech 編集後に実行推奨**)。**ある回 拡張**: ① へ助詞罠 (ひらがな読みの語中「へ」が助詞「え」化、共変→きょうへん→キョオエン) をカタカナ化との実測差分で検出 / ② 辞書未登録カタカナ固有名詞のカバレッジ表示 (PASS は既知リスクのみ照合 = 新規外国人名 ep は手動実測推奨)。**ある回 拡張**: ③ 多読み漢字 (下=した/もと, 抱=いだく/だく, 全N問, 誓絶) を surface→expect で照合 / ④ は助詞罠 (割合は→ワリアイハ) を**名詞アンカー** (は直前名詞カナ K に対し base が K+ハ で K+ワ 無し) で検出 (置換差分は再分割 FP のため不採用)。**ある回 拡張**: ⑤ regression sentinel 追加 — 割る=ワル (終止形を わりる 誤読、global 辞書 math_terms に集積済) / 後世=こうせい (はるか後 rule の greedy match で のち世→ノチセエ 再発、弁別子は実測ベースで「コオセ」= 漢字 コオセエ/かな こうせい→コオセイ 両対応・誤読形 ノチセエ/ゴセ 非含有)。両 sentinel は global fix 損傷時の backstop。**ある回 拡張**: ⑥ ひらがな ゔ (U+3094, va/vu) 合成劣化 sentinel — ゔぁ は kana 実測で「ヴァ」と出ても実音は不自然 (kana 非露見)。effective audio を**静的走査**し WARN (VOICEVOX 不要で常に走る)。カタカナ ヴ は ヴァ→バ 安定の ある回 許容慣行 (字幕ヴァ/音声バ) なので**除外**し shipped 正常 scene の FP を防ぐ。**ある回 拡張**: ⑦ 多読み漢字 物(ぶつ/もの) — 自然物=しぜんぶつ を VOICEVOX が シゼンモノ と誤読 (物=もの 化)、surface→expect「ブツ」で照合。なお closing_03「マンデルブロは無から」の topic は が ハ 化する助詞罠も同 guard が検出、漢字「無」は 無→ナ 誤読のため む 維持し「マンデルブロわむから」(わ 表記) で は→ワ と両立 | `python scripts/reading_guard.py episodes/XXX/scene_definition.json` |
| **STT QA (Cloud)** | Cloud TTS (`tts.engine=cloud`) 専用の読み検証。VOICEVOX の audio_query (kana 実測) が Cloud には無いため、合成済み各シーン wav を **Gemini STT** で書き起こし、既知 Cloud 誤読 (助詞 は=ハ `…ハ。`/`ノハ`) を照合し advisory WARN。engine=cloud のビルドで pipeline が audio step 後に自動起動 (VOICEVOX は代わりに reading_guard)。`GOOGLE_API_KEY` 無し/`google-genai` 未導入は graceful degrade。**STT も取りこぼす**ので耳 spot-check 併用。書き起こし全文を `stt_qa_report.txt` に残す。**ある回 拡張 (P1)**: 多読み漢字の文脈依存誤読を narration×STT で照合 (`_READING_CHECKS`: 入れ→イレ / 愛→メ(愛でる化) / 友→ユウ / 私→ワタクシ / 正→ショウ / 通→カヨ)。narration に surface があり STT に誤読カタカナが出れば WARN。詳細 [`docs/03_quality/cloud_tts_qa.md`](docs/03_quality/cloud_tts_qa.md)。**ある回 拡張**: ① **カタカナモード FP ガード** (`_is_katakana_mode`) — Gemini が助詞・活用をカタカナ化するモード (ヲ/デス/マス) では助詞 は もハ表記になり、は=ハ 検出が全 topic は に誤発火。格助詞 ヲ or デス/マス複数で当該モードを検出し particle-は 判定をその行で抑止 (正常ひらがな転写の実誤読は維持)。② `_READING_CHECKS` に **第九巻→ダイクカン / 何ひとつ→トヒトツ** (cloud_reading_lint の合成前 advisory を出荷 wav でも backstop=読み3層防御)。**ある回 拡張 (THINKING 漏れ抑止)**: `gemini-2.5-flash` は thinking モデルで、プロンプト「書き起こしのみ」に反し**推論を答え本文に出す回**がある (person_06 で ~100 行混入。推論文中の「ハ」等が corpus 照合を偽陽性化しうる)。`_transcribe`(verify_shipped_audio も共有)を 3 層で抑止: ① **thinking_budget=0** (`ThinkingConfig`、SDK 非対応は None graceful degrade、API 拒否時は config 無し再試行) ② プロンプトに「思考・注釈・タイムスタンプ・見出しは出力しない」 ③ `_strip_reasoning` backstop=先頭 THINKING ブロック/注釈行/メタ見出し/タイムスタンプ前置のみ除去し**本文は絶対に消さない** (leak 未検出なら無変換)。実 STT で person_06 が clean 化・leak-marker ゼロを確認。副作用ゼロ (advisory・出荷物不変) | `python scripts/stt_qa.py episodes/XXX/scene_definition.json` |
| **shipped-audio QA** | `stt_qa` が **scene wav (assemble 前)** を STT するのに対し、これは **`output_final.mp4`(速度正規化+連結+BGM 後=出荷物)** から各シーン音声を切り出し (timing.json global offset + bgm intro_pause) Gemini STT し、`stt_qa` と同じ既知誤読 corpus で照合する。ある回 session で決定打が繰り返し「**isolated wav でなく shipped 音声を STT**」だった (手作業 ~5回) のを自動化。**on-demand・advisory**(毎ビルド自動起動しない=STT コスト二重回避)。`GOOGLE_API_KEY` 無し/`google-genai` 未導入は graceful degrade。全文を `shipped_audio_qa_report.txt` に残す。**STT はばらつく**ので耳 spot-check 併用 | `python scripts/verify_shipped_audio.py episodes/XXX/scene_definition.json [--scenes id1,id2]` |
| **cloud reading lint** | Cloud TTS (`tts.engine=cloud`) 専用の**合成前**静的読み lint (`reading_guard` の Cloud 版)。narration + narration_speech_cloud を走査し ① 多読み漢字が読み未固定 ② 同音誤解語 (大数学者⇔代数学者) ③ 難語 (里程標→道しるべ) ④ 不自然な間 (用言+とは / 長主語+は) を WARN。engine=cloud で **script 後/audio 前**に pipeline 自動起動 (`gen_cloud_readings` 直後)。advisory。**ある回 拡張**: `_POLYPHONE` に文脈依存で Cloud が非決定読みする漢字を追加 — 数(かず/すう。「数で解け」= かず、closing_03 で スウ 誤読)/球(きゅう/たま。「球の切断/体積/表面」= きゅう、math_04 で タマ 誤読)/型(かた/かたち。「別の型/あらゆる型」= かた、math_01 で 形 誤読)。narration に surface があり cloud にひらがな読みが無ければ「平仮名固定推奨」WARN。**三次⇔三乗は不採用** (三次方程式は通常さんじで正読し全 scene FP 多発、稀な誤読は再ロールで解消)。⑤ **一括 は→わ 検出** — script_generator は cloud を出さず gen_cloud_readings が native は で生成する (コンマ孤立助詞のみ わ) が、legacy/手書きの scene_def に「全 は を わ にした」cloud が残ると gen_cloud は既存を保存し素通りする。narration が は×≥2 なのに cloud が は×0・わ複数なら WARN。**ある回 根治: script_generator が LLM の narration_speech_cloud を strip** (`strip_llm_cloud_readings`、extract_json 直後)=LLM が出力した cloud を破棄し gen_cloud が narration から native は で全再生成する。真因は config の additional_instructions が LLM に『narration_speech_cloud を用意・助詞は→わ表記』と明示指示→LLM が語中 は まで過剰変換=blanket-わ。strip は **LLM 出力が確定する決定論点で失敗クラスを source から断つ**（gen_cloud auto-heal 案は ⑤signature が単独/部分 は→わ を取りこぼす narrow さと、出荷済み ep を再ビルドで silent に触る難があり不採用。strip は fresh 生成時のみ動き narration から全再生成＝穴なし・出荷済み非破壊）。**根治の要点=config の additional_instructions に『LLM に narration_speech_cloud を用意させる』指示を書かない**。**ある回 拡張**: ⑥ **SSML-aware** — `_POLYPHONE` の多読みが `cloud_tts._READING_OVERRIDES` で SSML 合成時固定済み (二乗/数論家/対数 等) なら「未固定」WARN を抑止 (ある回 で 二乗×3 の空振り FP を解消。`any(k in surface for k in _SSML_FORCED)`)。⑦ **位「京」(=けい, 10^16)** — 数字直後の「京」が cloud で けい 未固定なら WARN。⑧ **単独「数」(かず/すう 多読み)** — 複合語 (素数/数列/因数/数学/十数/リュカ数/メルセンヌ数 等) 以外の裸の「数」が cloud で かず/すう どちらも未明示なら「文脈で平仮名明示推奨」WARN。⑦⑧は出荷済み cloud 5ep で FP ゼロに calibrate。**ある回 拡張**: ⑨ **多読み 表(ひょう/おもて)・底(てい/そこ)** — `対数の表`/`つの表`/`表を引`→ひょう、`も底も`/`を底と`→てい。**ある回 拡張**: ⑩ `_POLYPHONE` に **第九巻**(だいきゅうかん。九=く 誤読で出荷 STT「大区間」=だいくかん、第九=だいくに引かれる) / **第七巻**(だいななかん) / **何ひとつ**(なにひとつ。何 脱落で「とひとつ」化) / **実を結**(みを。「実を結ぶ」idiom の 実=み、ジツ 誤読温床)。事実(じじつ)/第一巻(いち=曖昧なし) を巻き込まない FP ガード検証・出荷6ep FP ゼロ。**ある回 拡張**: ⑪ **インライン助詞 は→わ 過剰変換** (`_scan_inline_particle_wa`) — script_generator が topic/subject 助詞 は を わ 表記化すると Chirp3-HD が独立 わ の境目に微小な間を挿入し不自然化 (A/Bテスト実測: わ文は は文より約25%長い)。既存 ⑤ `_scan_blanket_wa` は cloud の は が0の全変換のみ検出=部分変換(は一部残存)を取りこぼす。narration(は=正)と cloud を《》「」除去で difflib 整列し は→わ 単置換を数え WARN。修正は narration整列で わ→は 復元(わずか/変わる等の本物わは narration も わ で不変)。engine=cloud の audio step で自動走査。⑫ **発音リスク語→言い換え** (`_scan_rephrase_risk` + `_REPHRASE_RISK` 辞書) = **言い換え戦略の仕組み化**。読み固定 (SSML) で直らない問題 — 特に **acoustic voicing (か→が の濁り)** — は SSML が prosody-neutral (読みは固定するが音の出し方は変えない) ため残る。→ 検出でなく**予防**: narration の発音リスク語に**安全な言い換えを提案** WARN (③難語カテゴリの一般化、合成前・$0)。**運用**: user が耳で Chirp 発音問題を見つける→辞書に1行→以後全ep で執筆時に言い換えが促され**再発ゼロ化**。言い換えは字幕・語感を変えるので提案のみ・人間承認で3面同期置換。種= `毎日通い→足を運び`。**濁りの検出には原理的天井** (STT は清音に正規化。直接測れるのは DSP 有声判定のみで重い) ので予防+絞った耳確認が現実解。**ある回 拡張**: ⑬ **生分数 N/M lint** (`_scan_bare_fraction`) — cloud 合成テキストに生の分数「N/M」が残ると Chirp が分数として読むか**非決定**。**分子/分母どちらかが 3 桁以上**のときだけ WARN (22/7・1/2 等短い分数は Chirp が安定して分数読み=FP 回避、出荷 wav で 2 度確認し calibrate)。対処=narration_speech_cloud で「M分のN」スペルアウト (355/113→ひゃくじゅうさんぶんのさんびゃくごじゅうご)。narration 表示の N/M は許容 (cloud のみ対象)。 | `python scripts/cloud_reading_lint.py episodes/XXX/scene_definition.json` |
| **主題肖像 use_reference gap** | 実写参照 (`episode_config.wikimedia_photo_urls` 非空) がある ep で、主題の肖像 ken_burns scene が **text-only 生成される** 場合に WARN。pipeline の **images step 直前**に自動起動 (有料 Gemini の前)、advisory。rival (is_subject:false / use_reference:false) は除外。**ある回 修正 (gate-aware = 重要)**: 判定は **実効値** (`_effective_uses_reference`) で行う ── image_generator は `use_reference` **未設定 (None) を既定 True 扱い**し (`v.get("use_reference", True)`)、参照 gate ON (photos **and** birth_year) なら参照ベースで生成する。旧実装は `use_reference is not True` で **None を「参照なし」と誤検知**していた。修正後は WARN が出るのは **gate OFF (config に birth_year 無し→全肖像 silent text-only)** の時だけ (真因は birth_year 欠落。`config_validator` の「参照 gate OFF」ガードが本体で、本 lint は scene-level pointer)。対処=config に birth_year を明記して gate を ON にする。**不採用 (再検証で撤回)**: 「若年シーン+参照→過齢化」の inverse-gap lint を一度追加したが撤回 ── ある回 (明示 true, 10歳) も ある回 Conway person_01 (未設定, 11歳 on 68歳写真) も**適切に子供として生成**され、確定 TP ゼロ・正常な若年シーンを FP で叩くと判明。generator が prompt の年齢語で適切に若年化するので**若年+参照は過齢化の予兆にならない**。若年シーンの過齢化 は **age marker が弱かった**特殊ケースで、真の対処は use_reference:false でなく**強い年齢明記** (`This MUST be a small CHILD of about nine`) | `python scripts/lint_portrait_reference.py episodes/XXX` |
| **Manim Vision QA** | Manim/route_map/timeline の各フレームを **Claude Sonnet vision** で「概念が伝わるか/無意味な動き/判別不能な形 (独楽が独楽に見えるか)/ラベル衝突」判定。決定論 lint (Y座標/MathTex/末尾静止) が捕まえない**意味・美観**欠陥を検出。**visuals step 後**に pipeline 自動起動、advisory (Max 内コスト0)。`qa_image_checker` の Claude CLI 方式 (os.system+tempファイル、`--allowedTools Read,Bash`) 踏襲 | `python scripts/manim_vision_qa.py episodes/XXX/scene_definition.json` |
| **Manim 文字衝突 QA** | 各 Manim モードの construct() を **no-render mock** (play/wait を override して描画せず move_to/arrange/next_to だけ実行) で走らせ Text/MathTex の bbox を取得し、**横が重なり (x-overlap>0.12) かつ縦が重なり/接触 (gap<0.03) するペア**を検出。**manim_vision_qa (Sonnet 目視・非決定) が gp_ap/curve の ~0.05 重なりを「Warns 0」で見逃し user が目視した隙間**を、Y-lint (リテラル座標・字幕帯のみ) と Vision の中間の**決定論網**で埋める。データ駆動テンプレ (timeline_recap) は実 params を `_manim_params.json` に渡して実レイアウトを検査。**visuals step の manim_vision_qa 直後**に pipeline 自動起動、advisory。閾値 `X_OVERLAP_MIN=0.12`/`Y_GAP_MAX=0.03` は修正済み Napier 6モード + Conway 9シーンで FP ゼロに calibrate。**教訓: Manim の一律 Y シフトは詰まる→下段スタック全体を再スペースし合成前(smoke Y-lint)+合成後(vision+bbox 衝突)の多層で確認** | `python scripts/manim_text_collision_qa.py episodes/XXX/scene_definition.json` |
| **Cloud 発話速度 QA** | Cloud TTS (`tts.engine=cloud`) 専用の発話速度一貫性ガード。**Chirp3-HD は文ごとに実発話速度そのものを大きく揺らす**。`tts.rate` は全体基準にすぎず文単位テンポは API 非制御・非決定的なので**個別文の再合成では収束しない** (VOICEVOX は speedScale で一律決定的なのでこの問題なし)。**検出 (常時ON advisory)**: 各文 wav の実発話速度 (mora / 無音除く発話時間、ffmpeg silencedetect) を実測し隣接段差>18% を WARN、全文一覧を `speed_qa_report.txt` に残す。**さらに「間・区切り」異常も無音実測で同時検出**。**holistic な自然さ (抑揚) の自動判定は不採用**: Gemini 音声判定は 2倍速もチップマンク歪みも満点を付け弁別不能と較正で判明 (音声 LLM は TTS 自然さの絶対評価が苦手)。抑揚・微妙な誤発音は耳 spot-check で確定。engine=cloud のビルドで pipeline が audio step 後に自動起動 (stt_qa と同格)。**修正 (opt-in `--normalize-cloud-speed`)**: median へ ffmpeg atempo で部分圧縮 (strength=0.6、ピッチ保持、per-sentence wav in-place 上書き→cache 不変で再合成ゼロ、scene wav 再連結、timing.json 再構築)。ドラマ的に意図して遅い行 (artic<median*0.72) は保護。原本は `_prenorm_backup/` に退避し `--restore` で復元。timing 再構築は audio_generator の concat/silence/duration 一次関数を再利用し `--verify-timing` で arithmetic 一致 (max delta 0.0000s) を自己テスト済。**耳 spot-check 併用**。**ある回 拡張 (P4)**: ① **多重適用ガード** — `_prenorm_backup/` 既存時 `--apply` は**良性スキップ (exit 0、`--force` で強制)**。2回掛けは緩急を潰す。② **速度プロファイル照合** (detect) — median/stdev/min を承認済み ある回 基準と比較し 平坦化 (stdev<0.25)/過速 (median>7.7)/緩急なし (min>6.3) を WARN。**ある回 拡張**: ① **strength 自動チューニング** — `--apply` は既定で**段差 (>18%) を消す最小 strength を自動選択** (`_autotune`)。固定 strength=0.6 は ある回 の生 stdev~0.6 前提で、低分散回 を stdev 0.23 に過平坦化する。最小 strength 探索で stdev 0.35 を保ちつつ段差解消、かつ最遅の決め台詞を守るため FLOOR を自動引き上げ。`--strength FLOAT` で固定も可 (045/046/047 再現用)。② **未正規化ガード** — `pipeline.verify_outputs` が engine=cloud の最終ビルド (bgm) で `_prenorm_backup/` が無ければ「未正規化のまま出荷」と WARN。**ある回 拡張**: `--apply` の正規化 skip ガードを **stale 検出化** (`_backup_is_stale`: 完了時に `_prenorm_backup/.applied` marker を置き、backup 済み文の live wav が marker より新しければ「再合成された stale」と判断して再正規化。marker 無しの旧 backup も stale 扱い。`cmd_restore` は復元後に backup を削除)。中断ビルドが残した stale `_prenorm_backup` で force-regen 後の正規化がスキップ→**未正規化のまま出荷**する罠を根治 (手動 `rm -rf _prenorm_backup` 不要に)。**ある回 拡張 (SKIP 穴修正)**: `_backup_is_stale` の stale 判定を **backup 内の文だけでなく `audio_dir` の全 *.wav の mtime を marker と比較**するよう拡張。旧実装は前回 atempo された (=backup にある) 文の live wav しか見ず、**前回 within-band で atempo されず backup 非含の文を surgical 再合成すると stale 未検出→SKIP→未正規化で出荷**した。cmd_apply は marker を最後 (atempo+reconcat 後) に書くので触った全 wav は marker より古く、後の再合成のみ新しくなる=誤検出なし。 | `python scripts/cloud_speed_qa.py episodes/XXX/scene_definition.json` (検出) / `... --apply` (自動チューニング修正) |
| **ruff lint** | F+E+I+B+UP rule set (E501/E731/B008 ignore)。**現在 `src/ scripts/` は All checks passed (lint クリーン)** — 2026-06-26 に既存負債 134件を 0 に解消済 (F401/F841/B007/E741/B905/UP007/I001 等)。編集・新規コードはこのクリーン状態を維持する (フォーマット整形は別軸で下記参照) | `python -m ruff check src/ scripts/` |
| **ruff format** | black 互換フォーマッタ。**2026-06-26 に `src/ scripts/` 全 123 ファイルへ一括適用済 (3段階 commit、各段階で AST 等価=ast.dump 一致を検証し no-op を証明)。`ruff format --check` クリーン維持**。整形 commit は `.git-blame-ignore-revs` で blame からスキップ (ローカルは `git config blame.ignoreRevsFile .git-blame-ignore-revs`、GitHub は自動適用) | `python -m ruff format src/ scripts/` |
| **route_map preflight** | route_map 衝突検出 (pipeline 起動時に default ON、`--allow-route-collision` で escape、`--auto-fix-route-collisions` で 4-stage opt-in fix)。**ある回 拡張**: 各 route_map ラベルの実レンダ pixel bbox (`get_window_extent`) を `fig.bbox` (= `bbox_inches='tight'` 不使用なので保存 PNG 範囲) と照合し、枠外はみ出しを `*_clipped` collision report 化して同 preflight で STOP。auto 配置は候補段階で bounds skip 済だが**手動 `city_offsets` override / 全候補不可 fallback がその bounds チェックを通らずラベルが PNG 端で切れる gap** を塞ぐ。`_CLIP_TOL_PX=8px` は route_map 保有 shipped 28 ep 全走査で誤検知ゼロに calibrate (唯一の overflow=Cantor 6px≤閾値、合成 gross=390px と桁違い分離。ピクセル実測で check↔実 PNG 一致を確認) | (pipeline.py 内で自動起動) |
| **stale-visual preflight** | assemble step 直前に各 visual mp4 の実尺を timing.json の scene 尺と照合。許容 max(1.0s, 3%) 超の drift/欠落/破損があれば「旧 timing で焼かれた stale visual」として**中断** (fail fast)。`--allow-stale-visuals` で escape。timing 刷新 (速度変更等) 後に visuals 再 render を漏らし新音声+旧尺 visual を黙って合成する desync 事故 を防ぐ | (pipeline.py 内で assemble 前に自動起動) |
| **stale-subtitle preflight (Guard-B / B2)** | assemble step 直前に subtitles.srt が現在の narration/timing より古くないか照合し、古ければ**中断** (fail fast)。`--allow-stale-subtitles` で escape。**Guard-B** = narration TEXT を編集したのに subtitles 未再生成 → `_subtitles_meta.json` の narration_hash 不一致で検出。**Guard-B2 拡張** = narration TEXT は不変だが**読み (narration_speech_cloud) 修正・速度正規化 (cloud_speed_qa --apply) で音声尺 (timing.json) だけ刷新**されたケース。text hash は一致するので Guard-B を素通りし字幕タイムスタンプが旧尺のまま残る = 字幕/音声 desync。subtitle_generator が meta に timing 署名 (`timing_hash` = 全 scene duration の digest) を残し、preflight + post-build G2 が現 timing.json と照合。**教訓: 読み/速度を変えたら `--steps` に `subtitles` を必ず含める** (旧 meta に timing_hash 無い出荷済み ep は `.get()` で no-op=後方互換) | (pipeline.py 内で assemble 前に自動起動) |
| **多mode Manim mode-check** | scene_def の Manim scene が multi-mode テンプレ (LINT_FACTUAL_CLAIMS キー >1) を使うのに `visual.params.mode` 未指定なら WARN。default mode が narration と不一致になる silent ミスを検出。qa_manim_consistency に統合、visuals step 前に自動実行 | (pipeline.py visuals step で自動起動) |
| **再利用テンプレ空params abort** | データ駆動の再利用テンプレ (`timeline_recap`) が `visual.params` に必須キー (`milestones`) を欠く scene を visuals step 前に検出し **abort** (fail-fast)。空 params だと template は self-test default = 他 ep のデータ (timeline_recap→Laplace の人生イベント) を silent 描画する。template 自身の guard は partial params のみ raise し、完全空 `{}` は self-test と区別できず素通りしていた。`check_reused_template_params()` (qa_manim_consistency)、`--allow-empty-template-params` で escape。必須キー表 `_REQUIRED_TEMPLATE_PARAMS` に追加して拡張 | (pipeline.py visuals step で自動起動) |
| **build keep-awake** | pipeline 起動時に system sleep を抑止 (Windows `SetThreadExecutionState` で ES_SYSTEM_REQUIRED、atexit で解除)。長時間/深夜ビルドが OS スリープでプロセス全死する事故を防ぐ。`--no-keep-awake` で opt-out、非 Windows は no-op | (pipeline.py 起動時に自動) |
| **template hardcode 監査** | 再利用テンプレに ep 固有 hardcode (人名/年) 検出。≥2 主題で使う非 param 駆動テンプレを WARN (timeline_recap の Laplace データ混入型)。smoke test section 9 で advisory 自動実行 | `python scripts/lint_template_hardcoded_claims.py` |
| **タワー指数 lint** | 指数タワー `A^(B^C)` を曖昧プローズ化した「AのBのC乗」(乗1つ・括弧なし) を narration/narration_speech で検出 (ある回 ガウス 2^(2^k)+1 の誤読学び)。分数/根/属格の/単一指数は除外。smoke test section 12 で advisory 自動実行 | `python scripts/lint_tower_exponent.py` |
| **白縁 lint** | 生成画像に焼き込まれた白いキャンバス/額縁の縁を四辺の near-white strip 実測で検出。pipeline images step 直後に WARN、`--trim` で content box 自動クロップ。**ある回 拡張**: visuals step 直後に `run_video` で**レンダ動画フレームの外周白帯も % 実測** (source だけでなく納品物検査。ken_burns COVER 拡大で source 240px→動画 343px に広がる。band>=8% は `--allow-video-borders` 無しで中断)。眼視でなくピクセル実測 | `python scripts/lint_image_borders.py episodes/XXX/images` / `... episodes/XXX/visuals --video` |

依存物:
- `requirements.txt`: 完全 lock file (80 packages、`pip freeze` 出力 + コメント)
- `requirements.in`: top-level 直接依存 10 件 (manim / numpy / scipy / sympy / matplotlib / pillow / fonttools / requests / python-dotenv / google-genai)
- `requirements-dev.txt`: 開発用 (ruff)。production install は `pip install -r requirements.txt`、開発は `+ requirements-dev.txt`
- `.python-version`: 3.11.0 (pyenv 互換)
- 再生成: `pip install --upgrade -r requirements.in && pip freeze > requirements.txt`

## コーディング規約

### 全般
- 修正を提案する前に **実際のコードを読んで** 問題を確認する (推測で修正しない)
- 診断スクリプトやログ出力で **証拠を集めてから** 原因を特定する
- パイプラインレベルの構造的解決を優先。1 回限りのパッチは避ける
- 既存の関数・パターンを確認し、重複実装しない

### Python
- ファイル書き込みは `encoding='utf-8'` を明示
- パスは `os.path.join()` を使用 (バックスラッシュのハードコード不可)
- サイレントな `except: pass` 禁止 (最低限ログ出力)

### episode_config.json
- `verified_facts` は **dict 形式 `{}`** (list は `config_validator.py` でクラッシュ)
- `wikimedia_photo_urls` は **flat list 形式** `["url1", "url2"]` (dict 形式は `KeyError: 0`)
- 新フィールド追加時は `.get()` でデフォルト値を取って後方互換性確保
- 詳細: `.claude/rules/episode-config.md` (path-scoped、`episode_config.json` 編集時に自動ロード)

---

## Manim テンプレート

**1 ファイル 1 クラス + `construct()` 内 mode 分岐**。日本語は `Text(font=FONT)`、`MathTex` には Unicode/日本語を入れない。Y 座標は −2.0 〜 +3.3。`SCENES` dict + docstring + `LINT_FACTUAL_CLAIMS` metadata 必須。末尾に `FadeOut` を入れない (黒フレーム padding 防止)。**尺配分は `style.pace(duration, weights, intro, coda)` を使う** — `per = body / 数値` を手書きすると数値が run_time 係数和より小さいときアニメが `duration` を超過→mp4 が音声尺に切詰められ結論+coda が消失する。`pace` は per=budget/**sum(weights)** を保証し切詰めを構造的に防ぐ。

詳細チェックリスト + カラーパレット + アニメ規約: `.claude/rules/manim-development.md` (path-scoped、`src/manim_templates/**/*.py` 編集時に自動ロード)。

---

## スクリプト生成ルール

- 文体: **ですます調** (である調禁止)
- 文字数: **290 字/分** (`target_duration_minutes` から動的計算)
- 感嘆符: 1 スクリプトに 2〜3 回まで
- 禁止表現: 「ヤバい」「すごすぎる」「衝撃」等の煽り語
- **narration での「今日」禁止**: VOICEVOX が「きょう」(today) と「こんにち」(modern times) を文脈で区別できず誤読が繰り返し発生。「現代」「今」「これから」「近代」等に言い換え。modern の意味で「今日」が必要なら `narration_speech` に「こんにち」と明示
- 各エピソードは **単独完結** で書く (前回・次回・続編 NG)
- **person section は厚く**: 経歴の列挙だけにせず、性格・苦悩・人間味・個人エピソード (家族・教育者像・同時代人との関係・困難) を primary source で verify して含める。視聴者は数式より人物の物語に引き込まれる
- 事実確認: 歴史的主張は web verify してから narration に入れる (LLM の推論を鵜呑みにしない)
- 数式記号を含む narration には `narration_speech` で音声読み替え必須
- 数式音声化の誤読対策は global 集積で行う (audio_generator の誤読カテゴリ辞書 / `_convert_fractions()` / pronunciation_check Claude prompt / `formula_display._sanitize_subtitle()` の 4 層)。per-ep narration_speech 個別書き換えに陥らない
- **TTS エンジン**は `episode_config.json` の `tts.engine` で選択 (既定 `voicevox`、`cloud`=Google Cloud TTS Chirp3-HD)。上記の VOICEVOX 系誤読対策・辞書は **voicevox 専用**。cloud は scene_def の `narration_speech_cloud` (任意) で読みを調整 (助詞は「わ」表記/外国人名カタカナ化/空白除去) + **あいまい漢字は SSML `<phoneme alphabet="yomigana">` で読みを決定論固定**。読み制御は2層 — **force** = `cloud_tts._READING_OVERRIDES` (**文脈非依存語のみ**=二乗→にじょう/数論家→すうろんか/対数→たいすう/セルジューク朝。上書き語を含む文だけ SSML 化し他はバイト不変=副作用ゼロ、`build_synthesis_input`。**文脈依存語 (開けた=あけた/ひらけた, 数=かず/すう, 京=きょう/けい 等) は入れない** — ある回 で「開けた→あけた」強制が「道がひらけた」を破壊し regression、per-occurrence かな明記+出荷wav STT が正) / **detect** = `cloud_speed_qa._CONTEXT_DEPENDENT_WATCH` (文脈依存の多読み語=一行〔いちぎょう/いっこう〕は固定せず `WATCH-READING` advisory)。孤立助詞 は/へ は gen_cloud_readings でコンマ孤立を わ/え 化。**ある回 拡張**: 数字直後の「京」は gen_cloud `_cleanup` で **けい に固定** (`_MYRIAD_KEI` = `(?<=[0-9０-９])京`。10^16 の単位。東京/京都/京浜は数字前置でないので不変=文脈非依存で安全。上記 force に「京は入れない」とあるのは全「京」の強制の話で、**数字前置の京だけは曖昧性ゼロ**なので生成時固定が正。ある回「1844京」/ある回「800京」の きょう〔都市〕誤読が**出荷 wav STT でしか捕まらなかった**反省を合成前に前倒し)。**ある回 拡張**: gen_cloud `_cleanup` で **《》 も除去** (「」と同列。Chirp3-HD が二重山括弧を**非決定的に音声化** — person_05「、《この者」→「ま、」/closing_02「《選べるもの》」→「うぇ」、ただし同じ《》でも intro_04「隠れた前提」は無音=非決定)。narration 表示の《》は字幕用に維持、cloud のみ除去。合成直前の `cloud_tts.strip_for_cloud` にも「」『』《》除去を追加 (手書き cloud が gen_cloud を迂回しても括弧が TTS に届かない belt-and-suspenders、gen_cloud と冪等)。QA は Gemini STT (誤読はテキストでなく**出荷 wav** で検証) + cloud_speed_qa (speed/ISO-PARTICLE/WATCH-READING)。詳細過去の運用知見。**narration 編集時は `narration_speech` と `narration_speech_cloud` の両方を同期**。詳細: `docs/03_quality/pitfalls.md` "Cloud TTS" +過去の運用知見
- 字幕分割マーカー `|` は **意味的に自然な位置** で 25 文字以内に手動配置
- 詳細トーン規約: `docs/03_quality/STYLE_GUIDE.md`

---

## QA 運用

- **アプローチ A (デフォルト)**: QA レポート → 人間が手動修正 (鵜呑み禁止、過去の運用知見で繰り返し再発が確認されている)
- `--qa` は default ON、`--skip-qa` で opt-out
- 主要フラグ: `--qa-allow-warn` / `--skip-fact-check` (事前事実チェック) / `--skip-qa-image-narration` (画像-ナレーション QA) / `--skip-qa-script-only` (Gate 1 のみ skip、Gate 2 は走る)。**`--pronunciation-dry-run` は pipeline のフラグではない** (`audio_generator.py` 単体実行用。pipeline は転送しない)
- **QA 再検証 hook**: `qa_report_*.json` Read 時に `.claude/hooks/qa_report_reminder.py` が再検証リマインダを system に差し込む
- **build 完了後は最終サマリの `[!] advisory warnings` roll-up と「Output Verification」ブロックを必ず読む** (Pipeline Complete の tail だけ見ない)。engine=cloud の全 advisory check (cloud_reading_lint / stt_qa / cloud_speed_qa / manim_vision_qa / dead-air) の warning 件数が X3 stderr 経由で最終サマリに集約され、description 内容ドリフト等の verify_outputs WARN も同 box に echo される

詳細フラグ全リスト + hook 配線: `docs/03_quality/qa.md`。
`scene_definition.json` / `qa_report_*.json` 編集時の規約: `.claude/rules/qa-workflows.md` (path-scoped)。

---

## 画像生成

- 人物 (写真あり): Wikimedia 実写 → Gemini Flash で油絵風年齢変換
- 人物 (写真なし): Wikimedia PD 肖像画 → 油絵変換 (同一性は写真より弱い)
- 場所・雰囲気: Gemini Flash 直接生成
- Vision QA: Claude Sonnet (Anthropic Max 契約内コスト 0)
- 主題者以外には `"use_reference": false` (リファレンス汚染防止)
- `wikimedia_photo_urls` は flat list 形式 (dict は `KeyError: 0`)

詳細: `docs/04_assets/image-generation.md` および `docs/04_assets/IMAGE_GUIDE.md` (プロンプト設計詳細)。
画像生成コード / `episodes/*/visuals/` 編集時の規約: `.claude/rules/image-generation.md` (path-scoped)。

---

## よくある落とし穴

過去のバグ・落とし穴をカテゴリ別 (Manim / VOICEVOX / 画像生成 / サムネイル / 字幕 / route_map / description / pipeline / Claude CLI / 環境 / QA / 事実誤認 / コンテンツ設計) に整理:

→ **`docs/03_quality/pitfalls.md`** (新エピソード制作時・コード修正時の必読)

---

## 作業フロー

### 新エピソード制作
1. 企画・事実確認 (AI 補助で議論、一次資料で裏取り)
2. `episode_config.json` 作成 (`.claude/rules/episode-config.md` 規約参照)
3. Manim テンプレート作成 (`.claude/rules/manim-development.md` チェックリスト実行)
4. フルパイプライン実行: `python src/pipeline.py episodes/XXX/episode_config.json`
5. QA レポート確認 → 手動修正 (再検証フェーズ実施、QA 出力は鵜呑みにしない)
6. 大量/高リスク修正 (bulk 置換・事実/数値・クロス Ep) 後は `python src/qa_checker.py episodes/XXX/scene_definition.json --gate script` で **standalone 再検証 → クリーン後**に `--skip-script --skip-qa` で再ビルド (軽微な 1 箇所修正は再検証を省略可)。安い script 検証を、高い asset 生成 (VOICEVOX/Gemini) の前に挟む
7. 動画確認 → 微調整 → 公開

### パイプライン修正
1. 問題の再現確認 (ログ or 出力確認)
2. 該当コードを読む (推測しない)
3. 修正 → テスト → 影響範囲の確認

### 部分再ビルド時の注意
`--qa` は default ON。**mechanical な** partial rebuild (`--steps assemble,bgm` 等、内容を変えないコード検証) では `--skip-qa --skip-pronunciation-check` を併用しないと QA Gate 1 が長時間ブロックする (過去の運用知見)。
ただし **QA 指摘を内容修正した後**の再ビルドは別シナリオ: asset 再生成の前に上記 step 6 のとおり standalone `qa_checker --gate script` で再検証してから skip する。
**画像を再生成したら**、images 直後・visuals/assemble の前に `python src/qa_image_checker.py episodes/XXX/scene_definition.json` (Vision QA: 人数/年齢/性別/narration 整合、Max 内コスト0) を回す。skip して assemble まで進めると画像問題が動画段階まで漏れ、高い再 assemble を繰り返す。**勝手に QA を skip しない。**

---

## 参照ドキュメント

### アーキテクチャ全体像
- [`docs/architecture.md`](docs/architecture.md) — 4 Mermaid 図 (パイプラインフロー / Manim テンプレート構造 / episode_config スキーマ / QA + 観測性)
- [`README.md`](README.md) — 利用者向け導入・必須前提・クイックスタート

### 規約・スキーマ

| パス | 内容 |
|---|---|
| `docs/03_quality/STYLE_GUIDE.md` | トーン・VOICEVOX・Manim・ビジュアル・出典ルール |
| `docs/04_assets/IMAGE_GUIDE.md` | 画像生成プロンプト設計の詳細・実例集 |
| `docs/02_pipeline/EPISODE_CONFIG_TEMPLATE.md` | `episode_config.json` スキーマ詳細 |
| `docs/02_pipeline/SCENE_SPEC.md` | Manim シーン仕様 |
| `docs/02_pipeline/SYMPY_HELPER_DESIGN.md` | SymPy ヘルパーの設計 |
| `docs/03_quality/QA_PIPELINE.md` / `docs/03_quality/QA_INTEGRATION_GUIDE.md` | QA エージェント設計詳細 |
| `docs/03_quality/pitfalls.md` | 過去のバグ・落とし穴のカテゴリ別整理 |
| `docs/03_quality/qa.md` | QA フラグ詳細・hook 配線 |
| `docs/04_assets/image-generation.md` | 画像生成パイプライン規約 |

### path-scoped rules (`.claude/rules/`)

該当ファイル編集時に自動ロード:

| ルールファイル | 適用 paths |
|---|---|
| `episode-config.md` | `**/episode_config.json` |
| `manim-development.md` | `src/manim_templates/**/*.py` |
| `qa-workflows.md` | `**/qa_report*.json`, `**/scene_definition.json` |
| `image-generation.md` | `src/*image*.py`, `src/wikimedia_fetcher.py`, `episodes/*/visuals/**` |

### docs/INDEX
- [`docs/INDEX.md`](docs/INDEX.md) — docs 全体目次 (用途別 + 3 階層 + カテゴリ別)
