---
paths:
  - "src/manim_templates/**/*.py"
---

# Manim テンプレート — 作成・修正時の必須チェックリスト

**テンプレート作成・修正時、以下を必ず確認する（手動ではなくスクリプトで検証）：**

1. **日本語/Unicode in MathTex**: `MathTex()` 内に日本語・Unicode文字がないこと。日本語は `Text(font=FONT)` を使う
2. **Y座標範囲**: 全オブジェクトが y = −2.0 〜 +3.3 の範囲内（字幕クリアランス: y ≈ −2.2）
3. **字幕キャプション不可**: `styled_text` でキャプションを入れない。字幕はパイプライン Step 3 で別途生成
4. **`font=FONT` 指定**: 全ての `Text()` に `font=FONT` を付ける（`FONT = "BIZ UDMincho"`）
5. **`SCENES` dict + docstring**: テンプレートファイル末尾に `SCENES` 辞書、ファイル冒頭に docstring（テンプレート自動発見で使用）
6. **docstring にモードごとの固定パラメータを明記**: 数値不整合防止。例: `questions: 8 choices, depth 3, result = 3 bits`
7. **`LINT_FACTUAL_CLAIMS` metadata**: `SCENES` dict の直前に mode 別の人名・年号 dict を宣言。`Text()` / `cards_data` 等で **画面に表示される** 固有名のみ列挙する（docstring/コメントの年号は対象外）。表示する固有名がない mode は `{"people": [], "years": []}` で明示。`qa_manim_consistency.py` が pipeline visuals step 直前にこれを読み、narration 全体に登場しない人名・年号を WARN として検出する。形式：

   ```python
   LINT_FACTUAL_CLAIMS = {
       "<mode_key>": {
           "people": [
               ["タルターリア", "Tartaglia"],   # OR-list of aliases (Latin/kana)
               ["フェラーリ", "Ferrari"],
           ],
           "years": ["1535", "1540"],
       },
       "<other_mode>": {"people": [], "years": []},  # 明示的に空
   }
   ```

## カラーパレット

```python
BG_COLOR = "#1a1a2e"      # 背景（ダークネイビー）
GOLD = "#e2b714"           # 強調・タイトル
CYAN = "#4cc9f0"           # 数式・グラフ
PINK = "#f72585"           # 重要ポイント
```

## アニメーション

- **`FadeIn` を使用**。`Write` は描画タイミングがずれるため不可
- **duration-aware**: `duration` パラメータを受け取り、アニメーション時間を動的調整

### 末尾静止の anti-pattern

**`used = 固定アニメ秒; self.wait(max(1.0, duration - used))` で残り全部を末尾の 1 回の wait に流す設計は禁止**。ナレーションが長い scene (例: 40〜65秒) では固定アニメが 5〜13秒で終わり、**残り 30〜60秒が完全静止**になる。complex_rotation 等の既存テンプレも同じ設計で同症状を持つ (横展開リファクタ候補)。

修正パターン (slack を末尾に捨てず本編に分配する):
- **連続モーション**: 周期運動 (軌道・粒子) は `ValueTracker` + updater で **scene 全編** 動かす。`motion = duration - setup - coda` を計算し、`self.play(tracker.animate.set_value(...), run_time=motion, rate_func=linear)`。リビール (`FadeIn(label)`) は motion の play と並列に挟んで運動を止めない
- **トレーサー点**: 静的な図 (グラフ・釣鐘曲線) は曲線上を走る `Dot` を updater で往復させ、残り時間を `self.play(s.animate..., run_time=remaining)` で消費
- **段階リビール**: 要素が複数あるなら 1 つずつ (`for x in items: self.play(FadeIn(x))`) ナレーションに合わせて出す
- **余韻 (coda) は 2〜3秒に固定**。末尾の真の静止はこの範囲まで。`self.wait(coda)` のみ
- 検証: render 後に `ffprobe` で尺一致を確認し、**中間 (t=duration*0.5) と終盤 (t=duration*0.9) のフレームを抽出**して「全編モーションがあるか」を必ず目視 (最終フレームだけ見ると静止に気付けない)

### 幾何構成の向き・不等号は実フレームで検証

数式的に意味を持つ図 (測地線の弧・曲率・角度和・不等号) は、**コードが意図どおりの向きに描けているとは限らない**。ラベルや narration の主張 (「内角の和 < 180°」等) と実際の描画が一致しているか、**レンダ後のフレームを抽出して幾何的に確認する** (コードの目視だけで OK としない)。

ある回 `hyperbolic_geometry` の三角形は `ArcBetweenPoints(a, b, angle=±mag)` の**符号を1つ取り違え**、ポアンカレ円板の測地線を外側に膨らませて内角の和が 180°より**大きく** (球面的に) 見えていた — ラベルの「180°より小さい」と正反対。`angle` の符号は弧の膨らむ向き (a→b 進行方向の左/右) を決めるので、双曲弧のように**中心側へ凹ませたい**ときは向きを明示計算する (`sign = -1 if np.dot(left_normal, center - mid) > 0 else +1`)。曲率・向き・大小関係を主張する図は、render フレームで実測検証してから通す。

### レンダリング負荷 / timeout

Manim render は 1 scene あたり **240s timeout** (`visual_generator._MANIM_TIMEOUT_S`)。超過すると text_overlay placeholder に silent fallback する (pipeline の placeholder バナーで事後検出はされるが、完成動画に紛れるリスク)。

- 重い primitive (`Arrow3D` / `Cone` / `Sphere` の多用、長時間 `Rotate` を `rate_func=linear` で何 turn も回す等) は 1080p で容易に timeout に達する。3D 矢印は `Line(ORIGIN, [x,y,z])` で代替すると大幅に高速
- 成功しても render 時間が timeout の **70% (168s) 以上**だと `[WARN] ... timeout 近傍` が出る。僅かな負荷増 (FPS/解像度/尺変動・環境負荷) で placeholder 化しうるので、警告が出た scene は template を簡素化する

## 構造原則

- **1 ファイル 1 クラス**: `discover_manim_templates()` が 1 ファイル 1 クラスしか返さないので、複数 mode は `construct()` 内の mode 分岐で実装する（複数クラスに分けると最初のクラスだけ使われる、過去のケースで発覚）
- **末尾の `FadeOut` 禁止**: 全オブジェクト消失すると音声が Manim より長い場合に黒フレーム padding が起きる。最終フレームを保持し、シーン間トランジションは `video_assembler.py` の責務 (複数のテンプレートで対応済み)
- **再利用テンプレに ep 固有データを hardcode しない**: closing / recap / 汎用テンプレで人名・年表・タイトル等を `Text()` に直書きしない。`load_params()` + `params.get(key, fallback)` で `visual.params` から読む (例: `timeline_recap.py` の title/milestones/legend)。hardcode すると別 ep で再利用した時に前 ep のデータが表示される。`scripts/lint_template_hardcoded_claims.py` (smoke test section 9) が「≥2 主題で使う非 param 駆動テンプレの ep 固有 hardcode」を WARN する
- **データ駆動テンプレの partial params は silent fallback でなく fail-loud**: の `params.get(key, _DEFAULT)` は便利だが、**title だけ渡して milestones を渡し忘れた**ような部分指定で「前 ep のデフォルトデータ (Laplace) を別 ep のタイトル下に描画」する silent semantic bug を生む。`lint_template_hardcoded_claims.py` は Text() hardcode 専用で param-default fallback は検出できない。対策: **データキーを一部でも渡したのに必須キー (milestones 等) が無ければ `raise`** し、no-param 時のみ self-test fallback に落とす。raise → render 失敗 → pipeline の placeholder バナーで顕在化する (fail fast / no silent failures)。検証は実 Manim レンダで partial→raise / full→成功 を確認する (logic の机上確認でなく実描画)

## formula_display を使う場合

- `"formulas": [...]` (plural) は **2 element 以上** で渡すと `build_multi()` が呼ばれて全式が縦並びレンダリングされる。
- `"formulas": [...]` が **1 element のみ** の場合、`construct()` 内で自動的に singular `"formula"` に promote される。それ以前は build_static フォールバックで hardcoded Fourier 式が表示される silent bug があった。
- singular で確実に渡したい場合は `"formula": "..."` を直接書く方が明示的。

## 編集後ワークフロー

**Manim テンプレファイルの新規作成・編集後、preview render する前に必ず `python scripts/smoke_test.py` を実行する**。

理由: smoke_test の Manim Y-clearance lint + MathTex Japanese lint は AST/regex で deterministic に検出する layered defense だが、`MathTex(r"\text{弧長}")` のような nested Japanese 混入は render するまで気付きにくい (LaTeX `\text{}` の中に CJK が入って render で LaTeX error)。

ある回 で earth_arc の `\text{弧長}` 混入 → preview render が LaTeX error で停止し render 時間を浪費した事例で確立。テンプレ編集の直後に smoke_test を打てば、render より前にこの種のミスを潰せる。

## 関連 pitfalls

`docs/03_quality/pitfalls.md` の `Manim テンプレート関連` セクションも参照。
