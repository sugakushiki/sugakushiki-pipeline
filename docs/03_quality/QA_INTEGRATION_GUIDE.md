# QA 結果の扱い方

> QA が出した指摘を、どう読み、どこまで信じ、どう反映するか。
> 関連:
> - [`qa.md`](qa.md): 実行時のフラグと、どのガードが build を止めるか
> - [`QA_PIPELINE.md`](QA_PIPELINE.md): 各エージェントのプロンプト設計
> - [`pitfalls.md`](pitfalls.md): 過去に QA を鵜呑みにして踏んだ失敗

---

## 大原則: QA の指摘は「候補」であって「判定」ではない

QA レポートは severity / confidence / citation が構造化されているため、
**一見すると裁定済みの結論に見える**。実際には LLM エージェントの出力であり、
誤検出も、もっともらしい誤った根拠も混ざる。

- **warning 以上の指摘は、1 件ずつ一次資料で裏取りしてから反映する**
- **却下する判断のときこそ裏取りする** — 「これは誤検出だろう」と表面的に
  判断して流すのが、最も事故が起きるパターン
- FactChecker / SourceManager / ContentReviewer は Claude なので、**読む側と
  同じバイアスを持ちうる**。「もっともらしいから正しい」は成立しない

`qa_report_*.json` を読むと QA 再検証 hook が再検証リマインダを差し込む。これはこの原則を機械的に思い出させるためのもの。

---

## レポートの構造

`episodes/<id>/qa_report_script.json`:

```
overall_status : PASS / WARN / FAIL
summary        : {total_issues, critical, warning, info}
agents_run     : 実行されたエージェント名
agents         : {エージェント名: {status, issues[], summary, _model, _duration_sec}}
```

`issues[]` の 1 件:

| フィールド | 意味 |
|---|---|
| `severity` | `critical` / `warning` / `info` |
| `scene_id` | 対象シーン (`math_03` 等) |
| `claim` | narration 側の該当記述 |
| `finding` | エージェントの指摘内容 |
| `suggestion` | 修正案 (無い場合は `null`) |
| `confidence` | エージェントの自己申告確信度 (0.0〜1.0) |

**`confidence` は精度の保証ではない**。低い値は「裏取りが要る」の合図として使えるが、
高い値が正しさを意味するわけではない。判断材料の 1 つとして読む。

---

## エージェントごとの得手不得手

| エージェント | 見るもの | 注意 |
|---|---|---|
| `fact` | 事実の正確性 | 年号・帰属の指摘は当たりも多いが、一次資料と食い違うことがある。必ず出典で確認 |
| `style` | 文体・トーン | `--auto-fix` の対象はここだけ |
| `source` | 参考文献の妥当性 | 実在しない書名を「確認した」形で挙げることがある |
| `content` | 構成・尺感 | 尺超過の false positive が出やすい。実尺は timing.json で確認 |
| `consistency` | 用語・トーンの一貫性 | エピソード内のみ。横断の表記揺れは `lint_cross_episode_terms.py` |
| `dearu_lint` | である調の混入 | **決定論的な正規表現**。LLM の StyleChecker が run 間で揺れて見逃すため併走させている。`『...』` 引用内は info、本文の終止は warning |

`dearu_lint` だけは LLM ではないので、指摘の有無は再現する。それ以外は
**同じ入力でも run ごとに結果が揺れる**ことを前提に読む。

---

## `--auto-fix` の適用範囲

`qa_checker.py --auto-fix` が触るのは、**きわめて限定された条件を全て満たす指摘だけ**:

- `style` エージェントの指摘であること
- severity が `info` より上 (warning / critical)
- `suggestion` が存在すること
- 置換元が 30 字未満、`suggestion` が 60 字未満
- 1 回の実行で最大 5 件

該当する指摘の `claim` を `suggestion` で単純置換する。適用内容は
`qa_auto_fixes.json` に記録される。

**事実・構成・出典の指摘は自動修正の対象外**。それらは人間が判断する。
auto-fix を使った場合も、置換結果は目視で確認する。

---

## 単体実行

pipeline を回さずに `qa_checker.py` だけを走らせる。内容修正の後、
高い asset 生成 (画像・音声) をやり直す**前**に script を再検証するのに使う。

```bash
python src/qa_checker.py episodes/<id>/scene_definition.json --gate script
```

| フラグ | 用途 |
|---|---|
| `--agents style` | エージェントを絞る (カンマ区切りで複数指定可) |
| `--quick` | Sonnet のエージェントのみ。全実行より大幅に速い |
| `--use-gemini-fact` | FactChecker を Gemini Grounding (web 検索あり) にする |
| `--auto-fix` | 上記の条件を満たす style 指摘を適用する |
| `--output PATH` | レポートの出力先を変える |
| `--debug` | プロンプトと応答を表示する |

実行前に所要時間の見積りが表示される。実測はエピソードの長さと
エージェント構成で変わるので、見積りは目安として扱う。

---

## 修正した後

1. **narration を編集したら `narration_speech` と `narration_speech_cloud` も同期する**
   — 読み替えテキストが古いまま残ると、音声だけが旧文面で合成される
2. **`description.intro` も確認する** — 数学的な前提条件や限定詞が narration 側
   だけ直って intro から落ちると、概要欄が不正確になる。
   `python scripts/check_intro_semantic.py <episode_dir>` で機械的にも見られる
   (advisory。`episode_config` 側を直した場合は
   `python scripts/check_description_staleness.py <episode_dir>`)
3. **大量修正・事実修正・横断修正のあとは standalone で再検証する** —
   `qa_checker.py --gate script` を通してから、asset 生成を含む再ビルドに進む
4. **読みや速度を変えたなら `--steps` に `subtitles` を含める** — narration の
   文面が同じでも音声尺が変われば字幕のタイムスタンプは古くなる

---

## pronunciation_check の集積運用構造

誤読対策は per-episode の個別書き換えではなく、**global な集積**で予防する設計になっている。
同じ誤読が次のエピソードで再発しないようにするため、修正はできるだけ下の層に入れる。

- **`_MISREADING_CATEGORIES` 辞書** (`audio_generator.py`) — math_terms / compounds
  等のカテゴリ別の誤読エントリ
- **`_convert_fractions()`** — `(\d+)分の(\d+)` を kana に自動変換
- **pronunciation_check のプロンプト** — 複合語・分数・否定・数式のルールを明示
- **`script_generator` の narration_speech 生成プロンプト** — 生成段階で同じルールを適用
- **`formula_display._sanitize_subtitle()`** — 字幕に生の LaTeX が残っていれば strip して WARN

文脈依存の誤読 (同じ漢字が文によって読み分かる語) は global 化できないので、
そこだけ `narration_speech` 側で個別に指定する。

詳細: [`STYLE_GUIDE.md`](STYLE_GUIDE.md) の数式音声化ルール、
[`pitfalls.md`](pitfalls.md) の VOICEVOX / 字幕の節。
Cloud TTS の読み・速度については [`cloud_tts_qa.md`](cloud_tts_qa.md)。
