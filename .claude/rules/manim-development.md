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

## 構造原則

- **1 ファイル 1 クラス**: `discover_manim_templates()` が 1 ファイル 1 クラスしか返さないので、複数 mode は `construct()` 内の mode 分岐で実装する（複数クラスに分けると最初のクラスだけ使われる、過去のケースで発覚）
- **末尾の `FadeOut` 禁止**: 全オブジェクト消失すると音声が Manim より長い場合に黒フレーム padding が起きる。最終フレームを保持し、シーン間トランジションは `video_assembler.py` の責務 (複数のテンプレートで対応済み)

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
