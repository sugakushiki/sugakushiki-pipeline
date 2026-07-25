# 数学史記 シーン定義仕様書（SCENE_SPEC）

**バージョン**: 1.0

---

## 1. 概要

シーン定義JSON（`scene_definition.json`）は、パイプライン全体の中心的なデータ構造である。スクリプトから動画までの各工程がこのJSONを入力として処理を行う。

### パイプラインにおける位置づけ

```
episode_config.json
  │
  ├─→ script_generator.py ─→ scene_definition.json  ← ★これの仕様
  │                               │
  │                    ┌──────────┼──────────┐
  │                    ▼          ▼          ▼
  │            audio_generator  visual_gen  subtitle_gen
  │                    │          │          │
  │                    ▼          ▼          ▼
  │                 audio/     visuals/   subtitles.srt
  │                    │          │          │
  │                    └──────────┼──────────┘
  │                               ▼
  └─────────────────────→ video_assembler.py ─→ output.mp4
```

### 設計原則

1. **ナレーション駆動**: 各シーンの尺はナレーション音声の長さで自動決定される
2. **宣言的**: 「何を見せるか」を記述し、「どう作るか」は各ジェネレーターが判断する
3. **段階的に拡張**: MVP では最小限のフィールドで動作し、段階的に拡張する

---

## 2. トップレベル構造

```json
{
  "episode_id": "001_erdos",
  "title": "エルデシュ ── 家を持たない数学者が数学を変えた",
  "version": "1.0",
  "metadata": {
    "target_duration_minutes": 10,
    "mathematician": "Paul Erdős",
    "theme": "放浪の数学者と共同研究の力"
  },
  "sections": [ ... ],
  "credits": {
    "voicevox": "VOICEVOX:青山龍星",
    "images": [
      "原写真: Kmhkmh, CC BY 3.0, Wikimedia Commons（画像を加工して使用）"
    ],
    "references": [
      "Paul Hoffman, \"The Man Who Loved Only Numbers\" (1998)",
      "MacTutor History of Mathematics Archive"
    ]
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `episode_id` | string | ✅ | エピソード識別子（ディレクトリ名にも使用） |
| `title` | string | ✅ | 動画タイトル |
| `version` | string | ✅ | 仕様バージョン |
| `metadata` | object | ✅ | エピソードのメタ情報 |
| `sections` | array | ✅ | セクション（パート）の配列 |
| `credits` | object | ✅ | クレジット情報（概要欄用） |

---

## 3. セクション（sections）

動画の4パート構造に対応する。

```json
{
  "sections": [
    {
      "section_id": "intro",
      "section_type": "intro",
      "label": "導入（フック）",
      "scenes": [ ... ]
    },
    {
      "section_id": "person",
      "section_type": "person",
      "label": "人物パート",
      "scenes": [ ... ]
    },
    {
      "section_id": "math",
      "section_type": "math",
      "label": "数学パート",
      "scenes": [ ... ]
    },
    {
      "section_id": "closing",
      "section_type": "closing",
      "label": "締め",
      "scenes": [ ... ]
    }
  ]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `section_id` | string | ✅ | セクション識別子 |
| `section_type` | enum | ✅ | `"intro"` / `"person"` / `"math"` / `"closing"` |
| `label` | string | ✅ | 日本語ラベル（デバッグ・ログ用） |
| `scenes` | array | ✅ | シーンの配列 |

---

## 4. シーン（scenes）— 核心のデータ構造

1つのシーンは「1つのビジュアル＋1つ以上のナレーション文」の組み合わせ。

```json
{
  "scene_id": "intro_01",
  "narration": [
    "1996年9月20日。",
    "ポーランド・ワルシャワで開かれた数学の国際会議。その会場で、一人の老数学者が静かに息を引き取った。"
  ],
  "visual": {
    "type": "ken_burns",
    "source": "banach_center.png",
    "effect": "zoom_in",
    "source_prompt": "Stefan Banach Center lecture hall in Warsaw, Poland, 1990s, oil painting style, atmospheric, warm muted tones"
  },
  "transition": "fade",
  "notes": "導入の掴み。静かに始まる。"
}
```

### 4.1 シーン共通フィールド

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `scene_id` | string | ✅ | シーン識別子（エピソード内でユニーク） |
| `narration` | array[string] | ✅ | ナレーション文の配列。VOICEVOXに個別に投げる。字幕分割は `\|` で指示 |
| `visual` | object | ✅ | ビジュアル指示（後述） |
| `transition` | string | - | 次シーンへの遷移。`"fade"` / `"cut"` / `"none"`。デフォルト: `"cut"` |
| `pause_after` | number | - | シーン後の無音時間（秒）。デフォルト: 0.5 |
| `notes` | string | - | 制作メモ（パイプラインでは無視） |

### 4.2 ナレーション配列の設計意図

```json
"narration": [
  "1996年9月20日　ポーランド、|ワルシャワで開かれた数学の国際会議で、|83歳の数学者が心臓発作を起こしました。"
]
```

- 配列の各要素はVOICEVOXへの個別リクエスト単位
- 短い文と長い文で自然なポーズが入る（pauseLengthScale: 1.3で制御）
- 文間の無音（デフォルト0.8秒）はaudio_generatorが挿入
- SRT字幕は各文の開始・終了タイムスタンプから自動生成

### 4.3 字幕分割マーカー `|`

ナレーション文中の `|` は**字幕の改行位置**を示す。

- **audio_generator**: `|` を除去してからVOICEVOXに渡す（音声には影響しない）
- **subtitle_generator**: `|` の位置で字幕テキストを改行する
- **基準**: 1行あたり最大25文字。25文字以内の文はマーカー不要
- **分割ルール**: 読点「、」、ダッシュ「──」、括弧の直後など、自然な区切りで分割する。単語の途中で切らない

---

## 5. ビジュアルタイプ（visual.type）

4つのビジュアルタイプ。

### 5.1 `ken_burns` — 静止画 + パン/ズーム

最も頻出するタイプ。画像を表示しながらゆっくり動かす。

```json
{
  "type": "ken_burns",
  "source": "erdos_portrait.png",
  "effect": "zoom_in",
  "source_prompt": "Elderly Hungarian mathematician in his 70s, thin white hair..."
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `type` | `"ken_burns"` | ✅ | |
| `source` | string | - | 画像ファイル名。未指定の場合 `source_prompt` から自動生成 |
| `effect` | enum | - | `"zoom_in"` / `"zoom_out"` / `"pan_left"` / `"pan_right"`。デフォルト: `"zoom_in"` |
| `source_prompt` | string | - | 画像生成AI用プロンプト（IMAGE_GUIDE準拠） |
| `use_reference` | bool | - | リファレンス写真を使うか。default: `true`。非主題人物のシーン (Leibniz 回での Newton 等) で `false` を設定して汚染防止 |
| `no_human` | bool | - | 人物排除シーンの宣言。default: `false`。`true` 時に source_prompt 末尾に `"no human figure visible, still life composition, no people in scene."` を自動付加 + `use_reference` を強制 false |
| `cliche_acks` | list[str] | - | 承認済み cliché 用語を opt-out (cliche scanner が WARN しなくなる)。例: `["smoking pipes", "top hat"]`。`src/cliche_dictionary.json` の term と一致する文字列を指定 |

**処理フロー**:
1. `source` があればその画像を使用
2. なければ `source_prompt` でGemini APIに画像生成を依頼
3. Pillow + FFmpegパイプ方式でKen Burns効果を適用（ジッターなし）

**no_human 適用例**:
- 机のみ (主題者の遺品・原稿のみ) などの物のみシーン
- 楽器のみ / 風景のみのシーン
- 群像シーンで主題者を表に出さない場合

### 5.2 `manim` — 数式アニメーション

Manimで生成するアニメーション。テンプレートIDまたはカスタムシーン名で指定。

```json
{
  "type": "manim",
  "template": "network_graph",
  "params": {
    "center_label": "Erdős",
    "nodes": ["Einstein", "Selberg", "Tao", "Alon"],
    "highlight_color": "#e2b714"
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `type` | `"manim"` | ✅ | |
| `template` | string | ✅ | テンプレートID（`manim_templates/` 内のクラス名に対応） |
| `params` | object | - | テンプレートに渡すパラメータ |
| `custom_scene` | string | - | テンプレート外のカスタムManimシーンファイルパス |

**実装済みテンプレートの例** (`src/manim_templates/`):

| テンプレートID | ファイル | クラス | mode/phase |
|---|---|---|---|
| `bertrand_postulate` | `bertrand_postulate.py` | `BertrandPostulate` | `visual` / `table` |
| `route_map` | `route_map.py` | `RouteMap` | - |
| `erdos_wander` | `erdos_wander.py` | `ErdosWander` | `abstract_dots` |
| `erdos_network` | `erdos_network.py` | `ErdosNetwork` | `step_by_step` / `colored` |
| `erdos_network_grow` | `erdos_network_grow.py` | `ErdosNetworkGrow` | `ripple` |
| `random_graph_coloring` | `random_graph_coloring.py` | `RandomGraphColoring` | `intro` / `demonstration` / `result` |

パラメータは `_manim_params.json` 経由で渡される（visual_generator.pyが自動書き出し・削除）。
上の表は**抜粋**であって全一覧ではない（実際のテンプレート数はこの表の桁違いに多い）。
現物は `src/manim_templates/` を直接見る — 各ファイルの docstring と `SCENES` dict が
mode と用途を説明している。

#### `params.mode` — 多モードテンプレートでは必須

1 つのテンプレートが `construct()` 内の `mode` 分岐で複数のバリアントを描き分ける。
`LINT_FACTUAL_CLAIMS` のキーが 2 つ以上あるテンプレートで `params.mode` を省くと、
**既定 mode が黙って描かれる**。ナレーションと食い違っても絵は出てくるので気付きにくい
（マンデルブロ集合を描かせるつもりが単一軌道だけ描かれた、という取りこぼしがあった）。
visuals step の前に走る lint が未指定を WARN する。

#### データ駆動テンプレートの `params` は省略しない

`timeline_recap` のように**データを外から受け取る**テンプレートは、`params` が空だと
モジュールの self-test 用の既定データ（別題材の年表）を描いてしまう。必須キーを欠いた
`params` は visuals step の前に検出して **abort** する（`--allow-empty-template-params`
で意図的に通せる）。

#### テンプレートを書く／直すときの制約

シーン定義側ではなくテンプレート側の規約。破ると **lint やレンダは通るのに画面が壊れる**
種類の失敗になるので、`src/manim_templates/` を触る前に確認する。

| 制約 | 破ったときに起きること |
|---|---|
| **1 ファイル 1 クラス** + `construct()` 内 mode 分岐 | 探索は AST で**最初の 1 クラス**しか拾わない。2 つ目以降は黙って無視される |
| `SCENES` dict + docstring + `LINT_FACTUAL_CLAIMS` | スクリプト生成 LLM が読む面。無いと存在しないテンプレート名を生成しうる |
| Y 座標は **−2.0 〜 +3.3** | 下端 240px は字幕帯。はみ出すと字幕と重なる |
| 末尾に `FadeOut` を入れない | 黒フレームが padding として残る |
| 尺配分は `style.pace(duration, weights, intro, coda)` を使う | `per = 本体尺 / 数値` と手書きすると、分母が `run_time` 係数の総和より小さいときアニメが割り当て尺を超過し、mp4 が音声尺に切り詰められて**結論部分が消える**。尺は一致してしまうので stale 検出では捕まらない |
| 日本語は `Text(font=FONT)`、`MathTex` に Unicode/日本語を入れない | 豆腐化・レンダエラー |

詳細チェックリストとカラーパレット: `.claude/rules/manim-development.md`（`src/manim_templates/**/*.py`
編集時に自動ロード）。図の意味・美観と bbox 衝突は描画後に `manim_vision_qa` /
`manim_text_collision_qa` が見る。

### 5.3 `text_overlay` — テキスト表示

テキストを画面に表示する。引用、キーフレーズ、数学的定義など。

```json
{
  "type": "text_overlay",
  "content": {
    "main": "エルデシュ数",
    "sub": "── ある数学者がエルデシュとの共著で何ステップ離れているかを示す指標"
  },
  "style": "definition"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `type` | `"text_overlay"` | ✅ | |
| `content` | object | ✅ | `main`（メインテキスト）、`sub`（サブテキスト、任意） |
| `style` | enum | - | `"definition"` / `"quote"` / `"title_card"` / `"fact"`。デフォルト: `"fact"` |
| `background` | string | - | 背景画像ファイル名（半透明オーバーレイ）。なければ `#1a1a2e` 単色 |

### 5.4 `pillow_chart` — Pillow/matplotlib生成図

データ可視化。タイムライン、棒グラフ、分布図など。

```json
{
  "type": "pillow_chart",
  "chart_type": "timeline",
  "data": {
    "events": [
      {"year": 1913, "label": "ブダペストに生まれる", "side": "top"},
      {"year": 1934, "label": "博士号取得", "side": "bottom"},
      {"year": 1996, "label": "ワルシャワで死去", "side": "top", "highlight": true}
    ]
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `type` | `"pillow_chart"` | ✅ | |
| `chart_type` | enum | ✅ | `"timeline"` / `"bar_chart"` / `"distribution"` |
| `data` | object | ✅ | チャートタイプ別のデータ構造 |
| `source` | string | - | 事前生成済みの画像ファイル名（指定時はdata不要） |

---

## 6. エルデシュ回のサンプル（導入パート）

エルデシュ回プロトタイプの導入部の仕様例。

```json
{
  "episode_id": "001_erdos",
  "title": "エルデシュ ── 家を持たない数学者が数学を変えた",
  "version": "1.0",
  "metadata": {
    "target_duration_minutes": 10,
    "mathematician": "Paul Erdős",
    "theme": "放浪の数学者と共同研究の力"
  },
  "sections": [
    {
      "section_id": "intro",
      "section_type": "intro",
      "label": "導入（フック）",
      "scenes": [
        {
          "scene_id": "intro_01",
          "narration": [
            "1996年9月20日。",
            "ポーランド・ワルシャワで開かれた数学の国際会議。その会場で、一人の老数学者が静かに息を引き取った。"
          ],
          "visual": {
            "type": "ken_burns",
            "source": "banach_center.png",
            "effect": "zoom_in",
            "source_prompt": "Stefan Banach Center lecture hall in Warsaw, Poland, 1990s, oil painting style, atmospheric, warm muted tones, academic conference setting"
          },
          "transition": "fade"
        },
        {
          "scene_id": "intro_02",
          "narration": [
            "エルデシュ・パール。ハンガリー生まれの数学者で、生涯に発表した論文は1,500本以上。",
            "これは数学の歴史の中で、群を抜いて最も多い。"
          ],
          "visual": {
            "type": "ken_burns",
            "source": "erdos_portrait.png",
            "effect": "zoom_in",
            "source_prompt": "Elderly Hungarian mathematician in his 70s, thin white hair, round glasses, oil painting style, academic realism, portrait, warm muted tones"
          },
          "transition": "fade"
        },
        {
          "scene_id": "intro_03",
          "narration": [
            "しかし、エルデシュが数学の世界に残したものは、論文の数だけではない。",
            "「エルデシュ数」という概念がある。ある数学者がエルデシュとの共著関係で何ステップ離れているかを示す指標で、数学界ではちょっとした名刺代わりになっている。"
          ],
          "visual": {
            "type": "text_overlay",
            "content": {
              "main": "エルデシュ数",
              "sub": "ある数学者がエルデシュとの共著関係で何ステップ離れているかを示す指標"
            },
            "style": "definition"
          },
          "transition": "fade"
        },
        {
          "scene_id": "intro_04",
          "narration": [
            "家を持たず、スーツケース一つで世界中の数学者を訪ね歩いた男。",
            "今日は、数学を「一人の天才の仕事」から「人と人のつながり」に変えた、エルデシュの物語を追いかけます。"
          ],
          "visual": {
            "type": "ken_burns",
            "source": "erdos_portrait.png",
            "effect": "zoom_out",
            "source_prompt": null
          },
          "transition": "fade"
        }
      ]
    }
  ],
  "credits": {
    "voicevox": "VOICEVOX:青山龍星",
    "images": [
      "原写真: Kmhkmh, CC BY 3.0, Wikimedia Commons（画像を加工して使用）"
    ],
    "references": [
      "Paul Hoffman, \"The Man Who Loved Only Numbers\" (1998)",
      "MacTutor History of Mathematics Archive",
      "The Erdős Number Project, Oakland University"
    ]
  }
}
```

---

## 7. 処理フロー（各モジュールの責務）

### audio_generator.py

**入力**: `scene_definition.json`  
**出力**: `audio/` ディレクトリ + `timing.json`

1. 全sectionの全sceneを走査
2. 各sceneの `narration` 配列の各文をVOICEVOXに投げる
3. 文ごとのWAVファイルを保存（`audio/intro_01_001.wav`, `audio/intro_01_002.wav`, ...）
4. 文間に無音（デフォルト0.8秒）を挿入して結合
5. シーンごとの結合WAVを保存（`audio/intro_01.wav`）
6. タイムスタンプ情報を `timing.json` に出力

**timing.json の構造**:

```json
{
  "scenes": {
    "intro_01": {
      "duration": 13.2,
      "sentences": [
        {"text": "1996年9月20日。", "start": 0.0, "end": 2.1},
        {"text": "ポーランド・ワルシャワで...", "start": 2.9, "end": 13.2}
      ]
    },
    "intro_02": {
      "duration": 14.5,
      "sentences": [
        {"text": "エルデシュ・パール。...", "start": 0.0, "end": 9.8},
        {"text": "これは数学の歴史の中で...", "start": 10.6, "end": 14.5}
      ]
    }
  },
  "total_duration": 49.0
}
```

### visual_generator.py

**入力**: `scene_definition.json` + `timing.json`  
**出力**: `visuals/` ディレクトリ（MP4セグメント）

1. 各sceneの `visual.type` に応じて処理を分岐
2. `timing.json` からシーンの尺を取得
3. 尺に合わせたビジュアルセグメントをMP4で出力（1920×1080, 30fps, H.264）

| type | 処理 |
|---|---|
| `ken_burns` | 画像取得 or 生成 → Pillow+FFmpegパイプでKen Burns効果（15%ズーム） → MP4 |
| `text_overlay` | Pillowでテキスト描画（style別配色） → 微小Ken Burns → MP4 |
| `manim` | `_manim_params.json` 書き出し → `manim render` → 尺調整（trim/pad） → MP4（`--skip-manim` でスタブ生成） |
| `pillow_chart` | matplotlib/Pillowで図を生成 → Ken Burns方式 → MP4 |

**text_overlayスタイル**:

| style | main色 | sub色 | 用途 |
|---|---|---|---|
| `definition` | 金（#e2b714） | 白 | 定義・用語 |
| `title_card` | 金（#e2b714） | 薄灰 | セクションタイトル |
| `fact` | 白 | 薄灰 | 事実・データ |
| `quote` | 白 | 薄灰 | 引用 |

### subtitle_generator.py

**入力**: `timing.json`  
**出力**: `subtitles.srt` + `subtitles_drawtext.txt`

1. 全シーンの全文に対し、`timing.json` のタイムスタンプを使ってSRTエントリを生成
2. ナレーション文中の `|` マーカーで字幕を分割し、文字数比例で時間を按分
3. `subtitles.srt`（標準SRT）と `subtitles_drawtext.txt`（FFmpeg drawtext filter_script）を同時生成

**drawtext確定パラメータ**（Weekend 2で検証済み）:

| 項目 | 値 |
|---|---|
| フォント | BIZ UDMincho（インストール済みのシステムフォントから `_font.ttc` としてビルド時にコピー） |
| フォントサイズ | 42 |
| 下端マージン | 100px |
| 文字色 | white、borderw=3、bordercolor=black |

### video_assembler.py

**入力**: `audio/` + `visuals/` + `subtitles.srt` + `scene_definition.json`  
**出力**: `output.mp4`

1. 全シーンのビジュアルセグメントをconcat
2. 全シーンの音声を結合
3. 字幕を重畳
4. 最終出力

---

## 8. ファイル命名規則

```
examples/moriarty/
├── scene_definition.json        # シーン定義（パイプラインの入力）
├── audio/
│   ├── intro_01.wav             # シーン別結合音声
│   ├── intro_01_001.wav         # 文別音声
│   ├── intro_01_002.wav
│   └── ...
├── visuals/
│   ├── intro_01.mp4             # シーン別ビジュアルセグメント
│   ├── intro_02.mp4
│   └── ...
├── images/
│   ├── banach_center.png        # 画像素材（手動 or AI生成）
│   ├── erdos_portrait.png
│   └── ...
├── timing.json                  # 音声タイムスタンプ
├── subtitles.srt                # 字幕（SRT形式）
├── subtitles_drawtext.txt       # 字幕（FFmpeg drawtext filter_script）
└── output.mp4                   # 最終出力
```

---

## 9. 拡張予定

| 機能 | フィールド案 |
|---|---|
| BGM | `scene.bgm`: `{ "track": "...", "volume": 0.1 }` |
| ショート切り出しマーク | `scene.short_candidate`: `true` |
| 効果音 | `scene.sfx`: `[{ "file": "...", "at": 2.5 }]` |
| エンドカード | `section_type: "endcard"` |
| サムネイル指示 | トップレベル `thumbnail` オブジェクト |
| 英語字幕 | `narration_en` 配列 |

---

## 10. バリデーションルール

パイプラインで実装するバリデーション:

1. `episode_id` がディレクトリ命名規則に合致すること（英数字 + アンダースコア）
2. `scene_id` がエピソード内でユニークであること
3. `narration` が空配列でないこと
4. `visual.type` が定義済みのタイプであること
5. `ken_burns` タイプで `source` も `source_prompt` もない場合はエラー
6. `manim` タイプで `template` も `custom_scene` もない場合はエラー
7. `section_type` が `"intro"` / `"person"` / `"math"` / `"closing"` のいずれかであること

---

## 11. route_map auto-fix の private fields

`--auto-fix-route-collisions` 起動時、route_map の衝突解消用に `scene_definition.json` の `visual` block と top-level に **`_` (アンダースコア) prefix の private fields** が persist される。**手動編集時は基本的に touch しない**こと (削除すると次回 preflight で再衝突する可能性)。

### visual block 内 (route_map scene のみ)

| フィールド | 型 | 用途 | デフォルト | Stage |
|---|---|---|---|---|
| `_route_label_top_padding` | float | route_label の上端除外帯 (lat_span 比) | 0.05 | Stage 1 で 0.18 に変更 |
| `_title_fontsize` | int | タイトルフォントサイズ (pt) | 28 | Stage 3 で 22 に変更 |

例:
```json
{
  "visual": {
    "type": "route_map",
    "title": "...",
    "bounds": {"lat": [50, 62], "lon": [...]},
    "_route_label_top_padding": 0.18,
    "_title_fontsize": 22
  }
}
```

`bounds.lat[1]` は Stage 2 で +20% 拡張される (private 化せず通常の bounds 値として書き込み)。`legend_loc` / `legend_bbox_to_anchor` は Stage 4 でローテーション (private 化せず通常値)。

### scene_def 直下 (top-level)

| フィールド | 型 | 用途 |
|---|---|---|
| `_route_map_auto_fix_log` | array of object | auto-fix の修正履歴 (透明性のため persist) |

各 entry の構造:
```json
{
  "scene_id": "person_05",
  "stages_applied": [
    "stage1: route_label top exclusion 5%->18% (labels avoid title band)",
    "stage2: bounds.lat[1] expanded 60.0->62.0 (+20% of span)"
  ],
  "original_reports": [
    "title overlaps route_label '1815 大聖堂学校入学' (255x7px)"
  ]
}
```

複数回 auto-fix を実行すると entry が末尾に append される (履歴保持)。

### 関連

- 実装: `src/visual_generator.py` の `_apply_route_map_auto_fix_stage()` / `route_map_preflight()`
- 仕様: route_map collision detection 設計 (preflight + in-render lint + auto-fix)
- pipeline 設定: `--auto-fix-route-collisions` (default OFF) / `--allow-route-collision` / `--skip-route-preflight`
