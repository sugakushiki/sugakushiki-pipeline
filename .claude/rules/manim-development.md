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

8. **`LINT_VISUAL_ELEMENTS` metadata**: mode 別に「その mode が画面に出すもの」を宣言する。`qa_manim_consistency.check_narration_names_absent_visual()` が pipeline visuals step で読み、**ナレーションが画面にないものを名指ししていたら WARN** する。

   ```python
   LINT_VISUAL_ELEMENTS = {
       "two_state": ["矢印", "状態", "確率"],
       "converge":  ["縦軸", "横軸", "折れ線", "点", "破線"],
   }
   ```

   ある回は `converge` (折れ線) を出しながらナレーションが「二つの状態と、そのあいだの四本の矢印があります」と語り、**user が完成動画を見て「矢印が画面上になく理解が難しい」と指摘した**。矢印は同じテンプレの別 mode にある。params も座標も正しいので既存の決定論チェックは全部素通りし、Manim Vision QA も当該 scene は「0 issues」で通した (同 QA は別 scene の同型ミスは拾ったので、非決定的)。

   **画面に何があるかを知っているのはテンプレートだけ**なので、テンプレートに宣言させて narration と突き合わせる。宣言の無いテンプレは skip されるので既存 170 本は無影響。照合語は「絵を約束する語」だけ (矢印/等高線/折れ線/棒グラフ/縦軸/横軸/年表/ます目/格子/座標)。

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

### 尺配分は `style.pace()` を使う (手書きの割り算をしない)

`per = 本体尺 / 数値` と手書きしてはいけない。分母が `run_time` 係数の**総和**より小さいと
アニメの合計が割り当て尺を超過し、**mp4 が音声尺に合わせて切り詰められて結論部分が消える**。

```python
from style import pace

# 各 play/wait の run_time 重みを play 順に並べる。返り値は run_time の *リスト*
rt = pace(duration, [1.0, 0.8, 1.0, 1.2], intro=1.0, coda=3.0)
self.play(Create(axes), run_time=rt[0])
self.play(Write(label), run_time=rt[1])
```

分母は**常に重みの実際の総和**なので、アニメの合計は `duration - intro - coda` に
ぴったり収まる。

厄介なのは**壊れ方**で、尺が縮むのではなく**末尾が失われる**。切り詰め後の mp4 は
音声尺とぴったり一致するので、尺の突き合わせで見る stale 検出は素通りする。
検出できるのは実際に終盤フレームを見たときだけ (下記「検証」参照)。

### 末尾静止の anti-pattern

**`used = 固定アニメ秒; self.wait(max(1.0, duration - used))` で残り全部を末尾の 1 回の wait に流す設計は禁止**。ナレーションが長い scene (例: 40〜65秒) では固定アニメが 5〜13秒で終わり、**残り 30〜60秒が完全静止**になる。complex_rotation 等の既存テンプレも同じ設計で同症状を持つ (横展開リファクタ候補)。

修正パターン (slack を末尾に捨てず本編に分配する):
- **連続モーション**: 周期運動 (軌道・粒子) は `ValueTracker` + updater で **scene 全編** 動かす。`motion = duration - setup - coda` を計算し、`self.play(tracker.animate.set_value(...), run_time=motion, rate_func=linear)`。リビール (`FadeIn(label)`) は motion の play と並列に挟んで運動を止めない
- **トレーサー点**: 静的な図 (グラフ・釣鐘曲線) は曲線上を走る `Dot` を updater で往復させ、残り時間を `self.play(s.animate..., run_time=remaining)` で消費
- **段階リビール**: 要素が複数あるなら 1 つずつ (`for x in items: self.play(FadeIn(x))`) ナレーションに合わせて出す
- **余韻 (coda) は 2〜3秒に固定**。末尾の真の静止はこの範囲まで。`self.wait(coda)` のみ
- 検証: render 後に `ffprobe` で尺一致を確認し、**中間 (t=duration*0.5) と終盤 (t=duration*0.9) のフレームを抽出**して「全編モーションがあるか」を必ず目視 (最終フレームだけ見ると静止に気付けない)

### 段階リビールで「同じ位置のラベルを世代交代」させるときの 2 つの罠

同じ座標のラベルを何度も差し替える mode (自由度 3→9→29 のように**値だけが変わる**表示) は、フレームを見ないと壊れていることに気付けない失敗を 2 つ持つ。どちらも `smoke_test` の lint は通る。

**罠 1: `ReplacementTransform` のターゲットを取り違える。** ヘルパー関数でラベルを作っていると、次のように書いてしまう:

```python
self.play(ReplacementTransform(lab, make_label(v)))   # 画面に出るのは *この* 新オブジェクト
lab = make_label(v)                                    # NG: 別インスタンスを作り直している
```

`lab` が画面上のオブジェクトを指さなくなるので、次の transform は**画面外のオブジェクトを変形**し、前の世代が消えずに残る。全世代が同じ座標に積み上がって判読不能になる。ターゲットを名前に束ねて**それを持ち回す**:

```python
nxt = make_label(v)
self.play(ReplacementTransform(lab, nxt))
lab = nxt
```

**罠 2: 日本語テキストに長い `run_time` を与える。** `pace()` が返す 1 ステップは 3〜4 秒になることが多い。その run_time でテキストを `ReplacementTransform` すると**半端に崩れたグリフが数秒間表示**され、`FadeIn` でも数秒間ほぼ透明のままになる。`self.play(..., run_time=X)` は**子アニメ全部を X に引き伸ばす**ので、曲線の変形とラベルの出現を同じ play に混ぜると必ずこうなる。`AnimationGroup` で**アニメごとに run_time を持たせる** (テキストは 0.5 秒前後で入れて保持、長い時間は図形の変形だけに使う):

```python
self.play(
    AnimationGroup(
        ReplacementTransform(curve, nxt_curve, run_time=rt[i]),  # 図形は長く
        FadeIn(nxt_label, run_time=0.5),                          # 文字は即座に
        lag_ratio=0.0,
    )
)   # self.play() に run_time を渡さない (渡すと子の run_time が再スケールされる)
```

検証は **中間フレームを複数点**で抽出する (t=0.3/0.5/0.7/0.9 相当)。最終フレームだけ見ると罠 1 は「最終世代だけ正しく見える」ことがあり、罠 2 は最終フレームでは完全に不透明なので**どちらも最終フレームでは無症状に見える**。

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

ある回で earth_arc の `\text{弧長}` 混入 → preview render が LaTeX error で停止し render 時間を浪費した事例で確立。テンプレ編集の直後に smoke_test を打てば、render より前にこの種のミスを潰せる。

## 関連 pitfalls

`docs/03_quality/pitfalls.md` の `Manim テンプレート関連` セクションも参照。
