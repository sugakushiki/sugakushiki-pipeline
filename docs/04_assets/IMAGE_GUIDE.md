# 数学史記 画像生成プロンプト設計

---

## 1. 画像カテゴリと生成方針

動画内で必要な画像を3カテゴリに分類し、生成手段を使い分ける。

| カテゴリ | 内容 | 生成手段 | 理由 |
|---|---|---|---|
| A. 人物画像（写真あり） | 数学者の肖像（油絵風・年齢変換） | Wikimedia実写リファレンス → Gemini Flash | 人物の同一性を担保 |
| A'. 人物画像（写真なし） | 数学者の肖像（油絵風・時代考証あり） | Wikimedia PD肖像画リファレンス → Gemini Flash | 同一性は写真より弱いが及第点 |
| B. 場面・背景 | 時代の街並み、書斎、会議場など | Gemini Flash 直接生成 | 雰囲気の統一が重要 |
| C. 図解・タイムライン | 年表、概念図、データ可視化 | Manim / Pillow / matplotlib | 正確性が重要。AIより安定 |

**判断基準**：正確性が求められるもの → Manim/Pillow。雰囲気・情感が求められるもの → Gemini Flash。人物の同一性 → Wikimediaリファレンス必須。

### パイプラインでの処理フロー

```
episode_config.json
  │
  ├─ [4] wikimedia_fetcher.py
  │     Wikimedia Commonsから写真を取得・スコアリング
  │     → images/wiki_*.jpg（リファレンス用）
  │     → wikimedia_credits.json
  │
  └─ [5] image_generator.py
        wiki写真をリファレンスとして年齢変換生成（人物シーン）
        プロンプトのみで直接生成（場所・雰囲気シーン）
        → images/*.png
        Vision QA（Claude Sonnet）で品質評価 + リトライ
```

### Wikimediaリファレンスの注意点

- `_is_license_accepted()`: ライセンス文字列の正規化（spaces vs hyphens）でフィルタ漏れを防止
- `EXCLUDE_KEYWORDS`: 別人（配偶者、家族）の写真を除外するキーワードリスト
- `wikimedia_photo_urls`: episode_config.jsonに手動URLを指定するフォールバック。自動検索で正しい人物が出ない場合に使用

### フィクション人物の取り扱い (例: examples/moriarty/)

実在しない人物 (パブリックドメインの架空人物等) は Wikimedia リファレンスが存在しない、または同名異人がヒットする可能性があるため、以下の運用に切り替える:

- **`scene_definition.json` の visual block に `"use_reference": false` を明示**: Wikimedia auto-search でヒットした同名異人 (例: 架空の Professor James Moriarty 検索で米空軍 / 国務省の同名人物) がリファレンスとして渡されると画像生成が汚染されるため、参照を opt-out
- **Gemini Flash 直接生成のみ**: 人物画像も場面画と同じく Gemini Flash で source_prompt から直接生成 (リファレンス画像なし)
- **`wikimedia_credits.json` の空構造化**: 同名異人ヒット時は `{}` で commit して `description.txt` のクレジット欄混入を回避
- **同一性の制約**: リファレンスなしのため、同一フィクション人物が複数シーンで微妙に違う風貌になる (フィクションでは許容、実在人物では不可)

---

## 2. 画風の方向性

### 基本方針：「油絵風の知的な肖像」

チャンネルのトーン（知的ドキュメンタリー、NHKスペシャル的）に合わせ、以下の画風を基本とする。

| 要素 | 方針 |
|---|---|
| 画風 | 油絵（oil painting）/ アカデミック・リアリズム |
| 色調 | 暖色系の落ち着いたトーン。暗めの背景に人物が浮かぶ |
| 雰囲気 | 格調高い、知的、静謐 |
| 避けるもの | アニメ調、カートゥーン、写実的すぎるCG、明るすぎるポップな色使い |

### 画風キーワード集

プロンプトに含める画風指定の定型句：

```
# 基本セット（毎回使う）
oil painting style, academic realism, warm muted tones, dark background,
dignified atmosphere, museum quality

# 肖像画の場合に追加
portrait, three-quarter view, soft dramatic lighting, Rembrandt lighting

# 場面画の場合に追加
atmospheric, cinematic composition, depth of field, historical accuracy
```

### 避けるべきキーワード

```
# 避ける（チャンネルのトーンに合わない）
photorealistic, anime, cartoon, digital art, neon, vibrant colors,
fantasy, surreal, abstract
```

---

## 3. プロンプトテンプレート

### A. 人物肖像テンプレート（リファレンスベース）

リファレンス画像（Wikimedia実写/肖像画）を添付した上で、以下のプロンプトで年齢変換・油絵変換を行う：

```
Based on the reference image, create an oil painting portrait of this person
at age [年齢]. [時代・服装の描写].
oil painting style, academic realism, portrait, three-quarter view,
warm muted tones, dark background, soft dramatic lighting,
dignified atmosphere, museum quality.
Maintain the facial features and likeness from the reference image.
```

### B. 場面・背景テンプレート（直接生成）

```
[場所の描写] [時代の描写],
[具体的な要素], [雰囲気の描写],
oil painting style, atmospheric, cinematic composition,
warm muted tones, historical accuracy, depth of field
```

**例（1930年代ブダペスト）**：

```
Budapest cityscape in the 1930s, view of the Danube river and Chain Bridge,
historic buildings, autumn atmosphere, golden hour lighting,
oil painting style, atmospheric, cinematic composition,
warm muted tones, historical accuracy, depth of field
```

---

## 4. 画像生成API

### Gemini Flash（確定）

- Google AI Studio API経由
- コスト: 約¥4/枚、通常運用で月¥180〜240
- プロンプトは英語推奨
- リファレンス画像添付でスタイル変換が可能
- 安全フィルタに注意（戦争場面など）

### Vision QA

- Claude Sonnet via Claude Code CLI（Max契約内、追加コスト0）
- 約30秒/シーン
- 生成画像の品質・適合性を自動評価 + リトライ（最大4回）

---

## 5. 動画内での画像の使い方

### 表示パターン

| パターン | 説明 | 使用例 |
|---|---|---|
| Ken Burns効果 | ゆっくりズーム or パン | 最も一般的。肖像画・場面画をナレーションとともに表示 |
| text_overlay | テキストを重ねて表示 | 定義・引用・事実の強調 |
| formula_display | LaTeX数式を表示 | 数式中心のシーン（text_overlayのUnicode文字化け回避） |

### Ken Burns実装

Pillow + FFmpegパイプ方式（zoompanフィルタはサブピクセルジッターが発生するため不使用）。

---

## 6. 将来の拡張（メモ）

- 画像生成のバッチ処理：スクリプトのシーン指示から自動でプロンプトを生成し、APIで一括生成（実装済み）
- スタイル一貫性：LoRAやスタイルリファレンスを使えるAPIが出れば、チャンネル全体の画風統一が容易になる
- 動画内アニメーション：静止画にモーションを加えるAI（Runway, Pika等）の検討は将来課題
- Imagen 3/Flux等：リファレンス忠実度が高いモデルへの切り替え検討（人物同一性の改善）
