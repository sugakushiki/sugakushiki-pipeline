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
Cloud TTS キー) も欠けていれば即座に止まる。こちらは escape を用意していない。

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
D (算術サニティ) + E (Wikidata 照合) の 3 層。

| フラグ | 既定 | 内容 |
|---|---|---|
| `--skip-fact-check` | off | 事前事実チェック自体を skip |
| `--fact-check-allow-warn` | off | WARNING で止まらず続行 (CRITICAL は止まる) |
| `--use-gemini-fact` | off | Gemini Grounding (web 検索あり) で照合する |

- レポート: `episodes/<id>/pre_script_fact_check_report.json`
- Claude の結果はキャッシュ: `_pre_script_fact_cache.json`

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

`qa_report_*.json` を Read した瞬間に `.claude/hooks/qa_report_reminder.py` が
PreToolUse hook で再検証リマインダを差し込む。QA レポートは severity / citation /
confidence が構造化されているぶん一見権威的に見えるため、**指摘を伝える前に
一次資料で裏取りする**運用を機械的に促す。

- 設定: `settings.local.json` (gitignored) への登録が必要
- worktree セッションは main repo の `settings.local.json` を見ないので、
  worktree 側でも独立に登録する (hook 本体は repo にあるので絶対パス指定でよい)

---

## QA エージェント関連の落とし穴

[`pitfalls.md`](pitfalls.md) の「QA エージェント / Vision QA」節を参照:

- ContentReviewer の尺超過 false positive
- QA agent の非決定性 (run 間で判定が揺れる)
- Vision LLM 単発実行の保守性
