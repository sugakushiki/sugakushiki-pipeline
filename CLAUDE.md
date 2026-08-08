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
| フォント | BIZ UDMincho (日本語全般)。**同梱せず各自インストール** — Manim はフォント名で解決し、字幕焼き込み用の `_font.ttc` は `video_assembler.ensure_font_file()` がシステムフォントから複製する |

## Windows 固有の制約

- **`subprocess` 禁止 (Claude CLI 経路)**: Claude Code CLI (`claude -p`) の呼び出しは `os.system()` + tempファイル方式。`subprocess.run()` / `subprocess.Popen()` は使わない (Windows での日本語クラッシュ回避)
- **`findstr` 非推奨**: 日本語テキストやパイプ演算子で不安定。ファイル渡しか `type` を使う
- **Claude Code CLI `-p` モード**: `--allowedTools Read,Bash` が必須 (v2.1.63 以降)
- **cp932 対応**: `print()` の絵文字・特殊 Unicode (em dash 等) は ASCII 代替に統一 (Windows console は cp932)。`requirements*.txt` のヘッダーコメントも非 ASCII 不可 (pip 22.3 が cp932 で読み込みクラッシュ)

## 品質チェックツール



| ツール | 用途 | コマンド |
|---|---|---|
| **smoke test** | pre-pipeline 静的健全性 (import / config_validator / Manim discovery)。section 13-26 で禁止表現・重複参考文献・二重括弧・Y-clearance・コンソール encoding・**実在しない Manim mode**・再利用テンプレの必須 params・references のマークアップ 等を検査。**実測 約 219 秒** (2026-08-05。長く「数秒」と書かれていたが、その記述を根拠に検査の追加可否を判断すると誤る) | `python scripts/smoke_test.py` |
| **reading guard** | VOICEVOX 誤読の pre-build 検出。global 辞書適用後の実測 kana を既知誤読辞書と照合。**narration_speech 編集後に実行** | `python scripts/reading_guard.py episodes/XXX/scene_definition.json` |
| **STT QA (Cloud)** | engine=cloud の各 scene wav を Gemini STT で書き起こし既知誤読と照合。audio step 後に自動、advisory | `python scripts/stt_qa.py episodes/XXX/scene_definition.json` |
| **shipped-audio QA** | **出荷物** (`output_final.mp4`) から切り出して STT。読み検証の決定打。on-demand・advisory | `python scripts/verify_shipped_audio.py episodes/XXX/scene_definition.json [--scenes id1,id2]` |
| **cloud reading lint** | engine=cloud の**合成前**静的読み lint。多読み漢字・同音誤解・難語・間・助詞わ過剰変換・生分数・全文かな行・**config が名指しした読みの未固定**など 20 系統。script 後/audio 前に自動 | `python scripts/cloud_reading_lint.py episodes/XXX/scene_definition.json` |
| **主題肖像 use_reference gap** | 実写参照があるのに主題の肖像が text-only 生成される場合に WARN (真因は config の birth_year 欠落)。images step 前に自動 | `python scripts/lint_portrait_reference.py episodes/XXX` |
| **Manim Vision QA** | 各フレームを Claude Sonnet vision で「概念が伝わるか/判別できる形か/ラベル衝突」判定。visuals step 後に自動、advisory | `python scripts/manim_vision_qa.py episodes/XXX/scene_definition.json` |
| **Manim 文字衝突 QA** | no-render mock で bbox 衝突を決定論検出。**出荷済み在庫への遡及監査には使えない** (静的 mock はアニメの位置変化を評価できない) | `python scripts/manim_text_collision_qa.py episodes/XXX/scene_definition.json` |
| **Cloud 発話速度 QA** | Chirp3-HD の文ごとの実発話速度の段差 (>18%) と間の異常を実測。audio step 後に自動。**実測が段差なしを示すなら正規化しない** (緩急が潰れる) | `python scripts/cloud_speed_qa.py episodes/XXX/scene_definition.json` (検出) / `... --apply` (自動チューニング修正) |
| **ruff lint** | F+E+I+B+UP rule set (E501/E731/B008 ignore)。`src/ scripts/` は現在クリーン。**この状態を維持する** | `python -m ruff check src/ scripts/` |
| **ruff format** | black 互換。`--check` クリーン維持。整形 commit は `.git-blame-ignore-revs` で blame からスキップ | `python -m ruff format src/ scripts/` |
| **route_map preflight** | ラベル衝突・枠外見切れを検出し STOP (default ON)。`--auto-fix-route-collisions` は**改善したときだけ採用する greedy**＋都市 nudge。`city_offsets` を書くとその都市は auto 配置を外れる。**bbox が「0 件」でも絵は壊れる**ので、ラベルの所属 (d2/d1) と線がラベルを貫くかを advisory で併走 | (pipeline.py 内で自動起動) |
| **route_map 凡例ラベル review** | `legend_labels` のラベルが**そのカテゴリの全経路について真か**を Claude が review。経路ラベルは短い自由文なので文字列一致では判定できない。correction は書かず human 確認を促す | `python scripts/check_route_legend.py episodes/XXX [--strict] [--force]` (visuals step でも自動) |
| **route_map 地名カバレッジ review** | ナレーションが「その人が居た土地」として語っているのに**地図にその点が無い**ものを Claude が review。既存の route_map 検査は全て**配置**の検査で、**語られたものが描かれているか**は誰も見ていなかった。**辞書照合では駄目**: 全 ep の都市名を辞書にした決定論版は 40 scene で真 1 / 偽 4 (団体名「ロンドン数学会」・反実仮想・他人の移動・部分文字列「ル・シャンボン」の「ボン」)。地名が文字列として在るかと、その人がそこに居たかは別問題。correction は書かない (正解は「地図に足す」とは限らない) | `python scripts/check_route_places.py episodes/XXX [--strict] [--force]` (visuals step でも自動) |
| **route_map 凡例色の識別可能性** | 同時に使うカテゴリ色の RGB 距離 (と背景との距離) が 60 未満なら FAIL/WARN。**凡例は絵柄を読み解く鍵なので、同じに見える 2 色は凡例を無意味にする** (education/career が距離 47 で出荷 15 scene が該当していた) | smoke test section 21 (決定論) + render 時に使用カテゴリのみ WARN |
| **経路ラベルの所属 / Ken Burns 後の見切れ** | ① 経路ラベルが**自分の経路から離れすぎ** (>200px) か、**他の経路のほうが明確に近い** (自分>30px かつ 他<自分×0.6) かを測る。既存 3 検査は「箱が重なるか」「箱が枠内か」「線が箱を貫くか」だけで、**遠くに置かれた長い引出線は 3 つとも通過する** ② 見切れ検査は**静止図しか見ていない**。route_map は PNG を `generate_ken_burns` に通すので zoom_in の終端で**左右 125px・上下 70px が枠外**に出る。可視域は算術で確定するので決定論検査にできる。**較正**: 出荷 40 scene で 24 件 / 16 ep 発火。自分の経路までの距離は 0〜150px に 124 件、次が 372px という空白帯があり閾値 200 はその中に置いた | route_map preflight で自動 () |
| **取り残された作業 / 行末の反転** | ① worktree に未コミットの `src/ scripts/` があるか、trunk へ未マージの commit があるか。**`git branch --merged` は未コミットのブランチも「マージ済み」と表示する** (tip が base のまま=常に HEAD の祖先) ため、並行セッションの成果を 1 件取りこぼした。実測で 8 worktree が未コミットのパイプラインコードを保持、最古は trunk から 336 commit 遅れ ② ファイルの行末が index と食い違っていないか (Python のテキストモード書き込みが LF を CRLF に変え、2 行の修正が 110 行 diff になる)。**両方 advisory** | `python scripts/check_repo_health.py [--strict]` (smoke test section 22 でも自動) |
| **合成予告ゲート (2026-08-06)** | **合成の前に「全 N 文中 M 文を再合成する」を出す**。既存キャッシュがあるのに**半数以上**を再合成するなら確認を挟む (escape `--allow-full-resynthesis`、初回ビルドと `--force-regen-audio` は対象外)。ある回で 1 語の修正が全 94 文の再合成 → **Cloud TTS は非決定的なので同じテキストでも尺が変わり** → 全 23 scene の visual 再 render (24 分) → 合計 57 分になった。**この数は 1 秒で出せるのに誰も見ていなかった**。出荷 63 ep で発火 1 件 (048_khayyam 69 文中 41 文) | (audio step の前に自動。単体は `audio_generator.plan_synthesis()`) |
| **`--rebuild-scene` の検査 (2026-08-06)** | 部分再ビルドは **full build の検査 16 系統を 1 つも通っていなかった** (`pitfalls.md` には route_map preflight 1 件だけが「将来課題」として載っていた ── **既知の穴を 1 件書くと棚卸ししたつもりになる**)。**11 の共有ヘルパー**へ括り出して両経路から呼ぶ (最初の配線は音声と visual の側だけで、**画像と字幕の側 4 件を取りこぼしていた** ── ken_burns の再ビルドは画像を作り直し、字幕は必ず全編焼き直すのに、画像 QA も白縁も肖像参照 gap もフォント検査も無かった)。高コストな検査は再ビルドした scene に絞る (STT / Manim Vision QA / 画像 QA の `--scenes`)。preflight の step 集合も実態に合わせた (**必ず音声を合成するのに VOICEVOX 疎通も Cloud キーも見ていなかった**) | (`--rebuild-scene` で自動。) |
| **stale-visual preflight** | visual mp4 の実尺 vs timing.json。drift/欠落/破損で**中断**。`--allow-stale-visuals` で escape | (assemble 前に自動起動) |
| **stale-subtitle preflight (Guard-B / B2 / B3)** | narration hash (B) と timing 署名 (B2) で字幕の古さを検出し**中断**。**読み/速度を変えたら `--steps` に `subtitles` を必ず含める**。**B3 (2026-08-06)**: 字幕の本文は `timing.json` の `sentences[].text` 由来 (narration から直接ではない)。timing.json を書くのは audio ステップなので、**narration を直して `--steps subtitles,assemble,bgm` を回すと字幕は再生成されるのに中身は編集前のまま**になる。しかも `_subtitles_meta.json` には編集後の narration hash が刻まれるので **B/B2 は満足して沈黙する** (実ビルドで確認)。narration と timing の本文を直接突き合わせて捕まえる。**本文を直したら audio から回すこと**。較正: 出荷 63 ep で発火 1 件、それは真 (044_oka math_05 の narration は「立ちふさがります」だが出荷字幕は「立ちはだかります」) | (assemble 前に自動起動) |
| **description.intro staleness** | `config 署名が変化` AND `intro テキストが不変` の二条件でのみ WARN | `python scripts/check_description_staleness.py episodes/XXX [--accept]` (pipeline verify + credits step でも自動) |
| **references 書誌 review** | references の著者/書名/年/出版社を LLM が advisory review。**correction は書かず human の web verify を促す**。注記の中身は見ないので別途照合 | (script step で自動) / `python src/pre_script_fact_check.py episodes/XXX/episode_config.json --no-claude --no-arithmetic --no-wikidata` |
| **intro 意味一致 review** | narration→intro で数学的な限定詞が落ちていないかを Claude が review。`narration_evidence` の引用を必須化して接地 | `python scripts/check_intro_semantic.py episodes/XXX [--strict] [--force]` (credits step でも自動) |
| **多mode Manim mode-check** | multi-mode テンプレで `visual.params.mode` 未指定を WARN (default mode が narration と食い違う silent ミス) | (visuals step で自動起動) |
| **再利用テンプレ空params abort** | `timeline_recap` 等が必須キーを欠く scene を **abort**。空 params は他 ep のデータを silent 描画する | (visuals step で自動起動) |
| **再利用テンプレ尺不足 WARN** | params はあるが尺が足りない (予算 = max(6秒, 1.2秒 x 件数))。**timeline_recap の scene は尺と件数の対応を確認する** | (visuals step で自動起動) |
| **再利用テンプレの契約違反を script step で正規化** | milestones の 4 列化・legend の形式・色キーを補完。**契約違反はレンダ時にしか落ちない**ので前倒し。色は `_COLOR` の名前キー (hex は黙って全部白) | (script step の `normalize_timeline_recap_scenes()` で自動適用) |
| **timeline_recap の凡例・note 整合** | 凡例が絵柄を読み解く鍵になっているか。**色は track を分けるときだけ情報を持つ**。使われていない色は落とし、名前のない色は WARN | (visuals step で自動起動) |
| **画面に出る年号の追跡 lint** | params 由来の年号 (route の year / milestones) が narration にも config にも無ければ WARN。**偶然一致で見逃す**ので沈黙を検証の代わりにしない | (visuals step で自動起動) |
| **ナレーションと画面の不一致 lint** | narration が「その mode が描かないもの」を名指ししていたら WARN。テンプレの `LINT_VISUAL_ELEMENTS` 宣言と照合。**新規テンプレを書いたら宣言する** | (visuals step で自動起動) |
| **build keep-awake** | pipeline 起動時に system sleep を抑止。`--no-keep-awake` で opt-out、非 Windows は no-op | (pipeline.py 起動時に自動) |
| **template hardcode 監査** | 再利用テンプレの ep 固有 hardcode (人名/年) を WARN。smoke test section 9 で自動 | `python scripts/lint_template_hardcoded_claims.py` |
| **タワー指数 lint** | 指数タワー `A^(B^C)` の曖昧プローズ化「AのBのC乗」を検出。smoke test section 12 で自動 | `python scripts/lint_tower_exponent.py` |
| **白縁 lint** | 生成画像とレンダ動画フレームの外周白帯を**ピクセル実測**。images/visuals step 直後に WARN。`--trim` で自動クロップ | `python scripts/lint_image_borders.py episodes/XXX/images` / `... episodes/XXX/visuals --video` |
| **post-build verify** | ビルド後の構造検査 **11 件** (Manim fallback / 字幕同期 / 章タイムスタンプ vs timing.json / temp_videos 同期 / 画像の下隅シート 等)。**[ACTION] 行のパスを必ず開く** | `python scripts/post_build_verify.py episodes/XXX` (pipeline 末尾で自動起動) |
| **字幕の文境界実測** | `src/sentence_align.py`。モーラ比を**発話時間**に配分し実測無音を歩いて壁時計に戻す (数詞は読み下す)。平均誤差 0.013 秒 | (subtitles step で自動。`--audio-dir` は既定 ON) |
| **レビューリール + 未変更区間の同一性** | 1 箇所直すたびに 17 分を通しで見直す負担が**直せば直る欠陥を「触らない」に倒す**ため、変更シーンだけを ±2 秒の文脈付きで繋いだ mp4 を出す。ただし**リールだけでは足りない** (尺シフト・再エンコードが未変更部分に及んでいないか分からない) ので、未変更シーンについて**フレームハッシュ・timing・字幕**の 3 点で同一性を証明する。ビルド前に baseline を採る必要があるので pipeline の**先頭と末尾**の 2 箇所に配線。`--no-review-reel` で両方 OFF。**未変更のはずのシーンに差異が出たらリールには映らない**ので最初にそこを読む | `python scripts/review_reel.py episodes/XXX [--snapshot]` (pipeline が自動起動) |

依存物:
- `requirements.txt` (完全 lock) / `requirements.in` (top-level 直接依存) / `requirements-dev.txt` (開発用 ruff)。production install は `pip install -r requirements.txt`、開発は `+ requirements-dev.txt`
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
- **TTS エンジン**は `episode_config.json` の `tts.engine` で選択 (既定 `voicevox`、`cloud`=Google Cloud TTS Chirp3-HD)。上記の VOICEVOX 系誤読対策・辞書は **voicevox 専用**。cloud は scene_def の `narration_speech_cloud` (任意) で読みを調整 (助詞は「わ」表記/外国人名カタカナ化/空白除去) + **あいまい漢字は SSML `<phoneme alphabet="yomigana">` で読みを決定論固定**。読み制御は2層 — **force** = `cloud_tts._READING_OVERRIDES` (**文脈非依存語のみ**=二乗→にじょう/数論家→すうろんか/対数→たいすう/セルジューク朝。上書き語を含む文だけ SSML 化し他はバイト不変=副作用ゼロ、`build_synthesis_input`。**文脈依存語 (開けた=あけた/ひらけた, 数=かず/すう, 京=きょう/けい 等) は入れない** — ある回で「開けた→あけた」強制が「道がひらけた」を破壊し regression、per-occurrence かな明記+出荷wav STT が正) / **detect** = `cloud_speed_qa._CONTEXT_DEPENDENT_WATCH` (文脈依存の多読み語=一行〔いちぎょう/いっこう〕は固定せず `WATCH-READING` advisory)。孤立助詞 は/へ は gen_cloud_readings でコンマ孤立を わ/え 化。**ある回拡張**: 数字直後の「京」は gen_cloud `_cleanup` で **けい に固定** (`_MYRIAD_KEI` = `(?<=[0-9０-９])京`。10^16 の単位。東京/京都/京浜は数字前置でないので不変=文脈非依存で安全。上記 force に「京は入れない」とあるのは全「京」の強制の話で、**数字前置の京だけは曖昧性ゼロ**なので生成時固定が正。ある回「1844京」/ある回「800京」の きょう〔都市〕誤読が**出荷 wav STT でしか捕まらなかった**反省を合成前に前倒し)。**ある回拡張**: gen_cloud `_cleanup` で **《》 も除去** (「」と同列。Chirp3-HD が二重山括弧を**非決定的に音声化** — person_05「、《この者」→「ま、」/closing_02「《選べるもの》」→「うぇ」、ただし同じ《》でも intro_04「隠れた前提」は無音=非決定)。narration 表示の《》は字幕用に維持、cloud のみ除去。合成直前の `cloud_tts.strip_for_cloud` にも「」『』《》除去を追加 (手書き cloud が gen_cloud を迂回しても括弧が TTS に届かない belt-and-suspenders、gen_cloud と冪等)。QA は Gemini STT (誤読はテキストでなく**出荷 wav** で検証) + cloud_speed_qa (speed/ISO-PARTICLE/WATCH-READING)。詳細過去の運用知見。**narration 編集時は `narration_speech` と `narration_speech_cloud` の両方を同期**。詳細: `docs/03_quality/pitfalls.md` "Cloud TTS" +過去の運用知見
- 字幕分割マーカー `|` は **意味的に自然な位置** で 25 文字以内に手動配置
- **企画で「この語は出す」と決めたら `episode_config.json` の `required_phrases` に書く**。`forbidden_phrases` の裏返しで、smoke test section 18b が **narration に一度も現れない語**を名指しする。ある回は双対性の説明で『ミニマックス』を一行だけ入れると決めたのに**どの scene にも書かれず、完成した動画を見た user の指摘で判明**した ── 決めたことが計画メモにしかなく、照合する仕組みが無かった。照合先は **narration のみ** (読みは表記が変わる。概要欄や overlay に出ていても「本編で触れた」ことにはならない)。未設定 ep は no-op
- **ナレーションに入れられない数学的な限定は `episode_config.json` の `description.notes` に書く**。credits_generator が章タイムスタンプの直後に【注】ブロックとして概要欄に出す。ある回は本編の「一番良い答えは必ずその立体の角に来る」に対し、①正確には**最適解の少なくともひとつ**が角にある (等高線が辺と平行なら辺や面の上の角でない点も同値。ただし立体の内部ではない) ②実行可能な点が存在し領域が有界であるとき、を注記した。**本編で言うと文が重くなるが、言わないと定理を過大に述べたことになる**限定の置き場所。未設定 ep は何も出さない (既存 60 本の概要欄は不変)
- **`pronunciation_high_risk` は読み辞書であって禁止リストではない**。「この語は使わない」と書いても**台本生成には一切効かない** ── script_generator は禁止語として扱わない。ある回は『一行 → 使わない(いちぎょう と いっこう が割れる)』と書いてあったのに LLM が「論敵の一行の誤り」と書き、Chirp が いっこう と読み、**user が通し視聴で耳で見つけた**。避けたい語は **`forbidden_phrases`** に入れる。smoke test **section 18d** が「避けると書いたのに `forbidden_phrases` に無い語」を WARN する (54 話中 6 件発火)
- 詳細トーン規約: `docs/03_quality/STYLE_GUIDE.md`

---

## QA 運用

- **アプローチ A (デフォルト)**: QA レポート → 人間が手動修正 (鵜呑み禁止、過去の運用知見で繰り返し再発が確認されている)
- `--qa` は default ON、`--skip-qa` で opt-out
- 主要フラグ: `--qa-allow-warn` / `--skip-fact-check` (事前事実チェック) / `--skip-qa-image-narration` (画像-ナレーション QA) / `--skip-qa-script-only` (Gate 1 のみ skip、Gate 2 は走る)。**`--pronunciation-dry-run` は pipeline のフラグではない** (`audio_generator.py` 単体実行用。pipeline は転送しない)
- **QA 再検証 hook**: `qa_report_*.json` Read 時に再検証リマインダを system に差し込む
- **`--qa-quick` 禁止**: quick は Sonnet エージェントのみで全 agent の検証を満たさないので使わない。
- **build 完了後は最終サマリの `[!] advisory warnings` roll-up と「Output Verification」ブロックを必ず読む** (Pipeline Complete の tail だけ見ない)。engine=cloud の全 advisory check (cloud_reading_lint / stt_qa / cloud_speed_qa / manim_vision_qa / dead-air) の warning 件数が X3 stderr 経由で最終サマリに集約され、description 内容ドリフト等の verify_outputs WARN も同 box に echo される
- **中断ビルド・部分ビルドの advisory 死角**: 上記 roll-up は 'Pipeline Complete' でしか出力されないため、ゲートが `sys.exit(1)` すると**それまでに検出済みの警告が消えていた**。ある回は画像 QA ゲートで中断し、合成前 `cloud_reading_lint` が出していた「一行」多読み警告 26 件が失われ、続く部分ビルド (`--steps visuals,...`) が audio ステップを飛ばしたので再掲もされず、**誤読のまま音声を焼いた**。現在は `atexit` で中断時にも 1 回だけフラッシュし (正常完了時はフラグで抑止 = 既存出力不変)、`--steps` で飛ばしたステップについて「今回未実行のステップの advisory は再検証されていません」を最終サマリに出す。**中断したビルドと部分ビルドでは、走らなかったステップの advisory を個別に読み直すこと**
- **速度正規化 WARN は実測連動**: の「未正規化」警告は `_prenorm_backup/` の有無だけを見る一律チェックで、**段差ゼロの回でも毎回発火**していた (そのたび人が `cloud_speed_qa` を手で回して打ち消す運用)。現在は `cmd_detect` が `_speed_qa_verdict.json` (段差件数/median/stdev) を残し `verify_outputs` がそれを読むので、実測で段差ゼロなら WARN でなく「正規化は不要」と表示する。sidecar 無し (旧 ep / audio step 未実行) は従来どおり WARN = 後方互換。**実測が段差なしを示すなら正規化しない** (掛けると緩急が潰れる)
- **Claude CLI auth probe**: 長時間ビルド中に OAuth セッションが失効すると nested `claude -p` を使う全 QA が **一斉サイレント失敗**。pipeline は ① 起動 preflight (Claude 依存ステップ = script/images/thumbnail/visuals/credits のいずれかがあれば実行) で失効を **fail-fast**、② **manim_vision_qa 直前** (ビルド ~40分=トークン失効窓) で **mid-build 再 probe** し、失効なら該当 QA を skip + 最終サマリに「N 件の QA を skip、再認証して再実行」を surface (`_reprobe_claude_mid_build`)。判定は `claude_backend.classify_claude_ping` の **positive-signal** (healthy ping は `pong` を返す。401 文字列マッチに非依存)。`--skip-auth-probe` で抑止。**恒久策 = 長時間ビルド前に `claude setup-token` (1年 OAuth) を設定**して失効頻度を下げる。。**ある回追加**: 単発 25 秒 ping の**一過性タイムアウトで 60 分ビルドが preflight 落ち**した (直後に手で叩くと 5.6 秒で rc=0)。`reason == "timeout"` のときだけ 1 回リトライする (`probe_claude_with_retry`、prober 注入でテスト可能)。**`auth` (401) はリトライしない** — 失効したトークンは再試行で直らず、fail-fast の価値を損なうため
- **検査は記述でなくコードで強制する**: `post_build_verify.py` は ある時点 に 8 件の欠陥を出荷した反省から「hard gate」として新設されながら、**pipeline から一度も呼ばれておらず**、実行の強制は memory の『必ず実行』という記述だけだった。2 か月後の ある回で、その check 8 (temp_videos 同期) が捕まえるはずの事故がそのまま起きた ── **レビュー用のコピーを更新し忘れ、user は修正前の動画を見て、直っている 4 件を「なおっていない」と再指摘し、レビュー 1 周が無駄になった**。現在は pipeline 末尾で自動実行する。**新しい検査を足したら、同じ変更の中で pipeline か smoke_test に配線し、回帰テストに『呼ばれていること』を入れる** (部分文字列でなく AST。`run_all(` は `xrun_all(` にも含まれるので変異テストが素通りした)
- **「走る」と「読まれる」は別**: 上記を配線した直後、pipeline は `[OK] 11. 画像の下隅シート` とだけ出して**シートのパスを出さなかった** ([ACTION] を出す処理が CLI の `main()` 側にしか無かった)。見に行く場所を示すという検査の目的そのものが失われていた。見出しも「(9 checks)」と数字を焼き込んだままだった。**出力は共有ヘルパーに切り出して CLI と pipeline の両方から呼ぶ**
- **毎回やる運用は人間の記憶に置かない**: ビルド完了後の `temp_videos/` へのコピーは pipeline がやる (`--no-temp-video-copy` で無効化)。check 8 が結果を検証する (stale / 欠損の両方で発火することを実測済)
- **lint の警告を「STT の揺れ」「検証不可」で退けない**: `cloud_reading_lint` が**正教授**と**数**の 2 件を合成前に警告していたのに、前者は STT の書き起こしに「セキョウジュ」と出ているのを見て「STT は長音を落とすから揺れだろう」、後者は「その scene の書き起こしが漢字なので検証不可」と判断して先へ進み、**両方とも本物の誤読で user が耳で拾った**。過去の運用知見の「鵜呑みにしない」は**「反映する前に裏を取れ」であって「怪しければ退けてよい」ではない** ── 警告は既に一つの証拠なので、**否定する側に反証の義務がある**。「STT が揺れた」も「検証不可」も反証ではなく**検証していないという告白**にすぎない。読みは `narration_speech_cloud` に平仮名を書くだけでコストがほぼゼロ (字幕は漢字のまま) なので、**迷ったら直すほうを選ぶ**。**narration を書き直したら reading lint を回し直す**
- **参考文献は巻号だけでなく「注記の中身」を照合する**: `references` の `──` の後ろに書く注記 (その文献から何を得たか) は書誌情報とは**別の主張**で、 の reference review が見ているのは attribution (著者/書名/年/出版社) だけ。ある回は巻号ページを一次照合で通したあとに注記 5 件の誤りが出た — ① **同一著者・同一年の別論文と混同** (David Link は 2006 年に *Traces of the Mouth* 〔書くことの数学化〕と *Chains to the West* 〔西欧への伝播〕の 2 本を書いており、前者を挙げて後者の主題を注記していた。**巻号もページも実在するので書誌検査は素通りする**) ② **読んでいない文献を【主要参考文献】に並べた** (原典は開かず二次資料の引用で読んだ) ③ 引用範囲の誇張 (「全訳」が実際は二通の該当箇所) ④ 訳者の経緯 (独語訳→英訳を「4 名の英訳」と書いた) ⑤ 題名の綴り。**注記を書くときはその文献のどの記述を使ったか言えること**。言えないなら注記を書かない。**同じ著者が文献表に複数並んでいたら、主題がどちらのものか確かめる**。読んでいない文献は並べず、残すなら「〜を通して参照した」と経路を書く。修正は `episode_config.json` の `references` と `--steps credits` だけで済み**再エンコード不要**
- **QA の「指摘ゼロ」と「検査していない」を区別する**: 画像 QA (Gate 2) は Claude CLI が truncated JSON や無応答を返すと当該シーンを飛ばすのに、レポートは「13 scenes checked」と表示していた。ある回では**毎回 3〜5 シーンが未評価**で、critical を直した直後の画像すら検査されていなかった。現在は ① 失敗時に 1 回リトライ ② `scenes_evaluated`/`scenes_unevaluated` をレポートに記録 ③ サマリに `[!] N/13 scene(s) NOT evaluated` と**シーン名を明示**。実測でカバレッジ 8〜10/13 → 12/13。**未評価シーンは自分の目で確認する**

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
- **年齢推定 (`_estimate_scene_age`) の罠**と **`--output-dir` は episode dir を渡す** (誤ると警告なく text-only 生成) は `.claude/rules/image-generation.md` に詳述 (画像コード編集時に自動ロード)

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

**増分再ビルド**: audio (`audio/_audio_cache.json`) と visuals (`visuals/_visual_cache.json`) は content-hash キャッシュで未変更 scene を再利用し、partial rebuild を数分に短縮する (レビュー反復 48分→数分)。キャッシュが追跡するのは **narration/合成テキスト・visual.params・テンプレ.py + 依存 sibling + style.py・source 画像・scene 尺** の変更のみ。**レンダコード自体 (visual_generator.py の generate_* / audio 合成ロジック) やフォントを編集したら `--force-regen-visuals` / `--force-regen-audio` で強制再生成**しないと stale な wav/mp4 が黙って再利用される。詳細 memory過去の運用知見。

**1 シーンだけ直すなら `--rebuild-scene <scene_id>` (2026-08-06 に検査を配線済)**: `--steps audio,...` は**全文を再合成する**ので、Cloud 回では尺が動いて visual 再 render まで波及する。`--rebuild-scene` は full build と同じ検査を通り、高コストなものはそのシーンに絞る。**それでも `--steps` を使うときは、起動直後に出る「全 N 文中 M 文を再合成します」を読む**。

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
| `docs/03_quality/cloud_tts_qa.md` | Cloud TTS 回の読み制御 (SSML force / watch)・速度正規化・出荷前チェックリスト |
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
