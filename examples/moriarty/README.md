# examples/moriarty/ — フィクションエピソード技術デモ

> **本動画はフィクションです。** 本ディレクトリはパイプラインが架空人物を題材としたエピソードでも動作することを示す技術デモであり、本チャンネル `@sugakushiki` で公開する予定はありません。

---

## 概要

シャーロック・ホームズの宿敵として Conan Doyle が描いた架空数学者 **Professor James Moriarty** を題材に、彼が扱ったとされる数学 — Newton の一般化二項定理 / Cauchy・Abel の収束理論 / Gauss-Newcomb の小惑星軌道計算 — を 19 世紀の実在の数学史から紹介する 7 分尺の例エピソード。

設計方針:
- **フィクション伝記 + 史実の数学を等比重** で並列構成
- Conan Doyle 原作 (*The Final Problem* 1893 / *The Valley of Fear* 1914-15) を出典に Moriarty 設定を引用
- 数学的内容 (Newton 1665 / Cauchy 1821 / Abel 1826 / Gauss 1801, 1809 / Newcomb 1858-1860) はすべて **実在の数学を正確に解説**
- Sherlockian 学術文献 (Anderson 1955 / Schaefer 1993 / Jenkins 2013-14) で解釈の根拠を明示

## エピソード構成

YouTube 概要欄チャプター (4 章、section 単位):

```
0:00  導入
0:42  コナン・ドイルが描いた数学者
2:58  二項定理から天体軌道計算へ
6:21  現代に生きる理論
```

シーン詳細 (7 シーン):

| シーン | 尺 (audio) | section | 内容 |
|---|---|---|---|
| intro_01 | 39.1s | intro | フィクション宣言 + Doyle「最後の事件」原文の引用 |
| person_01 | 57.9s | person | Baring-Gould 推定の生年、Anderson (1955) Sherlockian 解釈 |
| person_02 | 66.1s | person | *The Valley of Fear* 引用 + Schaefer (1993) Newcomb モデル説 |
| math_01 | 64.1s | math | Newton (1665) の一般化二項定理 (1+x)^α |
| math_02 | 67.9s | math | Cauchy (1821) / Abel (1826) の収束理論 |
| math_03 | 73.8s | math | Gauss (1801) ケレス軌道計算 + Newcomb 拡張、Jenkins (2013) gesture |
| closing_01 | 46.6s | closing | NASA NEO Surveillance への接続、結語 |

**合計**: 7 シーン / 約 7 分 8 秒 / 1974 字 (290 字/分 ターゲット)

**実出力**: `output_final.mp4`、**76.2 MB** / 約 7 分 8 秒、約 1.42 Mbps

## 同梱ファイル

| ファイル | 内容 |
|---|---|
| `episode_config.json` | エピソード設定 (verified_facts 新形式 `{fact, source}` で出典明記、Doyle / Schaefer / Jenkins / Newton / Cauchy / Gauss / Newcomb / Kirkwood の出典を含む) |
| `scene_definition.json` | スクリプト生成器が出力した構造化シーン定義 (narration / narration_speech / visual / chapter_subtitles) |
| `qa_report_script.json` | QA Gate 1 (5 エージェント: Fact / Style / Source / Content / Consistency) のレポート |
| `qa_report_images.json` | QA Gate 2 (画像-ナレーション Vision check) のレポート |
| `description.txt` | YouTube 概要欄テキスト (チャプター付き、出典明記) |
| `thumbnails/` | サムネイル 3 パターン (A / B / C) |

中間成果物 (audio/, images/, visuals/, output_final.mp4) は同梱されません。各自で再生成してください。

## 再現方法

```bash
# 1. 環境準備 (リポジトリルートの README.md 参照)
python -m venv venv && venv/Scripts/activate  # Windows
pip install -r requirements.txt
# VOICEVOX (localhost:50021) を起動

# 2. .env に API キーを設定
cp .env.example .env
# GOOGLE_API_KEY を埋める (Claude は claude login の CLI 認証を使うため API キー不要)

# 3. パイプライン実行
python src/pipeline.py examples/moriarty/episode_config.json \
  --fact-check-allow-warn --qa-allow-warn

# Notes:
#   --fact-check-allow-warn: 架空人物のため pre-script fact check が API content filter で
#                            ブロックされる場合がある。WARN として続行
#   --qa-allow-warn: SourceManager が Sherlockian 文献の独立 verify を求める warning を出すが、
#                    verified_facts.source に出典が明記されており許容
```

所要時間目安 (GPU なし環境): 約 60-90 min

## 数学コンテンツの出典

| 数学 | 出典 |
|---|---|
| 一般化二項定理 (1+x)^α | Newton, I. *De Analysi per Aequationes Numero Terminorum Infinitas* (1665, published 1711) |
| 二項級数の収束半径 \|x\|<1 | Cauchy, A.-L. *Cours d'analyse de l'École Royale Polytechnique* (1821) |
| 複素指数の二項級数収束 | Abel, N. H. *Crelle's Journal* 1, 311-339 (1826) |
| ケレス軌道計算 / 最小二乗法 | Gauss, C. F. *Theoria motus corporum coelestium* (1809) |
| 小惑星軌道の永年変化 | Newcomb, S. *Smithsonian Contributions to Knowledge* 12 (1860) |
| Kirkwood gap | Kirkwood, D. *Proc. AAAS* 15, 8-14 (1866) |

## Sherlockian 解釈の出典

| 解釈 | 出典 |
|---|---|
| 二項定理論文の Newton 一般化 + 収束論的拡張説 | Anderson, P. "A Treatise on the Binomial Theorem" *Baker Street Journal* 5(1), 13-18 (1955) |
| Newcomb モデル候補説 | Schaefer, B. E. *Journal of the British Astronomical Association* 103(1), 30-34 (1993) |
| *Dynamics of an Asteroid* のカオス理論萌芽説 | Jenkins, A. arXiv:1302.5855v2 (2014) |
| Moriarty 生年推定 (1846) | Baring-Gould, W. S. *The Annotated Sherlock Holmes* (Clarkson N. Potter, 1967) |

## 既知の課題 (本デモ版)

このデモエピソードのビルドで以下の課題が確認されました:

- **Manim 0.19.2 の partial_movie cache 破損**: `Manim render failed: islice ValueError` の表面エラーは Rich の traceback 表示のバグ。実際の根本原因は PyAV `InvalidDataError` で、`partial_movie_file_list.txt` の処理に失敗するケースがあった (math_01 で発生)。**`_manim_media/` キャッシュ削除 + 再 render** で復旧。本デモでは解消済 (math_01 visual は formula_display で正常 render)
- **`series_convergence` テンプレに `binomial` mode 未実装**: 二項級数の部分和収束を可視化する `binomial` mode は未実装で、math_02 で `mode: "binomial"` 指定が無効化された。本デモでは `formula_display` 単独で代替する設計時 fallback 案を採用、math_02 visual は formula_display で正常 render
- **Wikimedia 自動検索ヒットの想定外**: `Professor James Moriarty` の Wikimedia 検索で実在の同名異人 (Sean Moriarty / James Moriarty、米空軍 / 国務省) の写真がヒットし download された。`scene_definition.json` の visual block で `use_reference: false` を明示して画像生成への汚染を回避 (肖像は参照写真を用いず AI 生成)。これに合わせ `description.txt` の【画像クレジット】も Wikimedia 写真を記載しない (参照していないため)
- **`pre_script_fact_check` の content filter ブロック**: フィクション題材 (Sherlock Holmes / 暴力的描写) で API content filter が反応し fact check 自体がブロックされた。`--fact-check-allow-warn` で続行する運用が必要
- **`image_generator` の年代抽出ヒューリスティック**: narration に含まれる年号 (例: 1915) を `birth_year` から差し引いて目標年齢を推定する挙動があり、フィクション人物の場合に意図しない年齢 (今回 person_02 で 69 歳が初回算出された) になるケースを確認。本デモでは narration から直接的な年号言及を削除する workaround で対応

## ライセンス

- 本体コード・ドキュメント: MIT License — リポジトリルートの [`LICENSE`](../../LICENSE) 参照
- フォント (`_font.ttc` BIZ UDMincho): SIL Open Font License Version 1.1 — [`LICENSES/OFL.txt`](../../LICENSES/OFL.txt)
- Conan Doyle 原作 *The Final Problem* (1893) / *The Valley of Fear* (1914-15): パブリックドメイン
- Sherlockian 学術文献の引用: 学術引用フェアユース範囲

---

> 本エピソードは、パイプラインの汎用性デモ目的で制作されました。本チャンネルで公開する予定はなく、Moriarty 教授の業績設定はあくまで Conan Doyle の小説内のフィクションです。扱う数学的内容は実在の 19 世紀数学史を正確に紹介しています。
