"""
script_generator.py - Generate scene_definition.json from episode_config.json via LLM API

Usage:
    python script_generator.py episode_config.json --output scene_definition.json
    python script_generator.py episode_config.json --output scene_definition.json --dry-run
    python script_generator.py episode_config.json --output scene_definition.json --model gemini-2.5-flash
    python script_generator.py episode_config.json --output scene_definition.json --model claude

Input:  episode_config.json (mathematician info, theme, key topics)
Output: scene_definition.json (full pipeline input per SCENE_SPEC)

Pipeline position:
    ★ script_generator.py → scene_definition.json
      ↓
    audio_generator.py → subtitle_generator.py → visual_generator.py → video_assembler.py

Supported models:
    --model claude             (default, Claude Opus via Claude Code, highest quality, ~30min)
    --model claude-opus        (same as claude)
    --model claude-sonnet      (Claude Sonnet 4.6 via Claude Code, fast, ~10min)
    --model gemini-2.5-flash   (Gemini Flash, free, ~1min, lower instruction following)
    --model gemini-2.5-pro     (Gemini Pro, free/low-cost)
"""

import argparse
import json
import os
import re
import sys
import time

# Shared Claude Code backend (also used by qa_checker.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_backend import (
    call_claude as _call_claude_backend,
)

# ─── Constants ───────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude"

# Character count targets (defaults for 10 min, recalculated in main())
CHAR_COUNT_MIN = 2600
CHAR_COUNT_MAX = 3200
MAX_RETRIES = 3

# Style guide essentials (embedded to avoid file dependency)
STYLE_GUIDE_PROMPT = """
## ナレーションのスタイルガイド

基調: サイモン・シン『フェルマーの最終定理』の語り口。抑制的で品があり、事実の積み重ねで感動を生む。
温度感:「賢い友人が居酒屋で熱く語っている」くらい。

ルール:
- 文体: ですます調で統一する（「〜です」「〜ます」「〜ました」「〜でしょう」）。である調（「〜である」「〜だった」「〜していた」「〜された」）は使わない。ただし会話の引用内は例外。堅すぎず、専門用語は文脈で理解できるように
- 感嘆符: スクリプト全体で2〜3回まで
- 禁止表現:「ヤバい」「すごすぎる」「衝撃」等の煽り語
- **narration での「今日」禁止** (VOICEVOX が「きょう」(today) と「こんにち」(modern times) を文脈で区別できず誤読頻発、ある回で繰り返し顕在化)。「現代」「今」「これから」「近代」など文脈に応じた言い換えを使う。許容: 「今日の」が「modern」の意味で必要な場合のみ「今日 (こんにち) の」のように読み補注を入れるか、narration_speech で「こんにちの」と書く
- 許容する強調:「ここが面白いのは」「注目すべきは」等の抑制的な表現
- 数学者の描写: 敬意はあるが神格化しない。失敗や人間的な弱さも等しく描く
- **person section は人物の物語として厚く書く** (経歴の列挙だけにせず): 性格・苦悩・家族・教育者像・同時代人との関係・困難など、verified_facts に基づく人物的側面を必ず含める。3 scenes 600 字程度では薄い、4-5 scenes 900-1200 字を target に。視聴者は数式より人物の物語に引き込まれる
- 数学の説明: 数式を「導出する」のではなく「意味を語る」スタンス
- 数値や引用は「〜と言われています」「〜によると」等で典拠を示唆する
""".strip()

SCENE_SPEC_PROMPT = """
## scene_definition.json の構造仕様

### トップレベル
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
  "credits": { ... }
}
```

### sections: 4つのパート
```json
"sections": [
  {"section_id": "intro", "section_type": "intro", "label": "導入（フック）", "scenes": [...]},
  {"section_id": "person", "section_type": "person", "label": "人物パート", "scenes": [...]},
  {"section_id": "math", "section_type": "math", "label": "数学パート", "scenes": [...]},
  {"section_id": "closing", "section_type": "closing", "label": "締め", "scenes": [...]}
]
```

### 各シーンの構造
```json
{
  "scene_id": "intro_01",
  "narration": [
    "1996年9月20日。",
    "ポーランド・ワルシャワで開かれた|数学の国際会議。"
  ],
  "visual": {
    "type": "ken_burns",
    "source_prompt": "Stefan Banach Center lecture hall..., oil painting style, academic realism, warm muted tones",
    "effect": "zoom_in"
  },
  "transition": "fade",
  "pause_after": 0.5,
  "notes": "導入の掴み"
}
```

### narration_speech（音声読み替え、任意フィールド）
ナレーションに数式記号（²、√、−、=、π など）が含まれる場合、VOICEVOXが正しく発音できない。
その場合、`narration_speech` を追加して、音声合成用の読み下しテキストを指定する。

```json
{
  "scene_id": "math_03",
  "narration": [
    "たとえば、|x²−2=0の2つの根、|+√2と−√2。",
    "この2つを入れ替えても、|元の方程式はそのまま成り立ちます。"
  ],
  "narration_speech": [
    "たとえば、xの2乗マイナス2イコール0の2つの根、プラスルート2とマイナスルート2。",
    "この2つを入れ替えても、元の方程式はそのまま成り立ちます。"
  ],
  ...
}
```

ルール:
- `narration_speech` は `narration` と同じ要素数の配列
- 数式記号がない文は `narration` と同じ内容でよい
- `|` マーカーは不要（音声には影響しない）
- 数式記号を含まないシーンには `narration_speech` を付けなくてよい（省略＝narrationをそのまま使用）
- 数式記号読み下し例: ² → 「の2乗」、√ → 「ルート」、− → 「マイナス」、= → 「イコール」、π → 「パイ」、∞ → 「無限大」、Σ → 「シグマ」、∈ → 「属する」

#### 日本語複合語の VOICEVOX 誤読対策（生成時に必ず適用）

VOICEVOX は文脈推定が弱く、以下のパターンは narration_speech で**完全ひらがな化**して回避する。
narration の表記はそのまま漢字でよい（視覚字幕表示用）が、narration_speech では**音声として正しい読み**を提供する。

- **複合語末尾の「値」→ 「ち」読み**: 観測値・絶対値・理論値・実測値・近似値・最大値・最小値・平均値・期待値・固有値・推定値・初期値・予測値・極値・関数値・中央値・中間値・境界値・限界値・真値・許容値・設計値 → 「かんそくち」「ぜったいち」「りろんち」等。**「観測あたい」「絶対あたい」のような kanji/kana 混合は絶対に書かない**。単独「値」（「πの値」「f(x)の値」）のみ「あたい」読み
- **分数「N分のM」**: 「2分の1」「3分の2」のような表現は narration_speech で「にぶんのいち」「さんぶんのに」と完全ひらがな化（VOICEVOX デフォルトで「にふんのいち」=時間の「分」に誤読される）
- **数式中の `A/B` の音声化**: 単純な分数は「BぶんのA」(denominator-first)、複雑な式は narration では文章で説明し具体的な式は visual のみで表示。例: `α(α-1)/2!` → 「2の階乗ぶんのアルファかけるアルファマイナス1」または narration から外す
- **修辞的「否」→「いな」読み**: 「答えは否です」「P は否である」のような単独「否」は「いな」と読む（「ひ」読みは熟語専用: 否定・賛否・否決）。narration_speech で「答えはいなです」と書く
- **VOICEVOX 誤読既知パターン**: 多角形→たかくけい、空集合→くうしゅうごう、流率法→りゅうりつほう、極限値→きょくげんち、今日→こんにち（「現代」の意味のとき）、等

### ビジュアルタイプ（visual.type）

1. **ken_burns**: 静止画＋パン/ズーム。人物肖像や場面描写に使用
   - effect: "zoom_in" / "zoom_out" / "pan_left" / "pan_right"
   - source_prompt: 画像生成AI用プロンプト（英語、oil painting style必須）。**人物が登場する場合は、必ずナレーションの時代に合った年齢と外見を含めること**（例: "a 21-year-old Hungarian man with dark hair" / "an elderly 83-year-old mathematician with white hair and weathered face"）

2. **text_overlay**: テキスト表示。定義、引用、キーフレーズに使用
   - content: {"main": "メインテキスト", "sub": "サブテキスト（任意）"}
   - style: "definition" / "quote" / "title_card" / "fact"

3. **manim**: 数式アニメーション。数学的内容の可視化に使用
   - template: テンプレートID
   - params: テンプレートパラメータ（任意）

4. **route_map**: 世界地図上の移動経路。数学者の旅路・移動の描写に使用
   - title: 地図のタイトル（日本語）
   - cities: {"都市名": [経度, 緯度], ...}
   - route: [{"from": "都市A", "to": "都市B", "year": "1934", "label": "説明", "category": "career"}, ...]
   - category（以下の6つから選ぶ。**招聘・就職・移籍はすべて career**、亡命と混同しない）:
     - "origin": 生誕地・出発点
     - "education": 留学・進学（学生時代の地理的移動）
     - "career": 研究職・宮廷数学者・大学教授等の職務赴任。**招聘・就職・移籍はすべて career**
     - "wandering": 放浪・遍歴（特定の職務でない移動）
     - "exile": **政治的迫害・国外追放・亡命のみ**（友好的招聘は exile ではなく career）
     - "final": 最期の地（その人物がそこで没した場合のみ）
   - bounds: {"lon": [-85, 45], "lat": [20, 65]}（任意、省略推奨＝都市座標から自動計算）
   - effect: "zoom_in" / "zoom_out"（任意、デフォルト zoom_in）

※ 上記4種以外のvisual.typeは使用禁止

### 字幕分割マーカー `|`
ナレーション文中の `|` は字幕の改行位置。1行25文字以内を目安に、読点やダッシュの直後で分割。
短い文（25文字以内）にはマーカー不要。

### pause_after
- 通常: 0.5（デフォルト）
- セクション間: 1.0〜1.5
- 最終シーン: 2.0

### scene_id の命名規則
- intro_01, intro_02, ...
- person_01, person_02, ...
- math_01, math_02, ...
- closing_01, closing_02, ...
""".strip()


GENERATION_RULES = """
## 生成ルール

### 全体構成
- 導入（intro）: 2〜4シーン。視聴者を引き込む意外な事実やエピソード。〜1分
- 人物パート（person）: 6〜12シーン。時代背景、生い立ち、転機。3〜4分
- 数学パート（math）: 5〜10シーン。代表的業績を直感的に解説。数式は最小限。3〜4分
- 締め（closing）: 1〜3シーン。数学史における位置づけ、現代との接続。〜1分

### ナレーション（★最重要：文字数に注意）
- 各シーンのナレーション配列は2〜5文。1文は20〜80文字程度
- 1シーンのナレーションは合計80〜250文字を目安にする
- 日本語ナレーションの実効速度は約4.5文字/秒（発話速度＋文間ポーズを含む）
- 10分動画には約2,700文字が必要
- **全シーン合計で2,600〜3,200文字になるように調整すること。これより少ないと動画が短すぎる**
- 人物パートと数学パートは特に各シーン120〜200文字程度にする。短い文の羅列ではなく、具体的なエピソードや説明を丁寧に書くこと

### ビジュアルの使い分け
- **visual.typeは ken_burns / text_overlay / manim / route_map の4種のみ使用可能。それ以外（pillow_chart等）は絶対に使わないこと**
- 人物の肖像や場面描写 → ken_burns
- 定義、重要な用語、引用 → text_overlay
- 数式、グラフ、数学的構造の説明 → manim
- 数学者の移動や旅路の地図表現 → route_map
- ken_burnsとtext_overlayを中心に。manimは数学パートで3〜5シーン程度
- route_mapは人物パートで0〜2シーン程度（移動・放浪を描く場面）

### route_map（地図ビジュアル）の使い方
route_mapは世界地図上に都市と移動経路を描画する。数学者の人生における移動を表現する場面で使用する。
- cities: 経路に登場する都市の座標（経度・緯度）を辞書で指定
- route: 移動経路を配列で指定。from/toは必ずcitiesに存在する都市名
- category: 経路の意味を示す（origin / education / career / wandering / exile / final の6種、上記§visual定義参照）。**招聘・就職・移籍は career**、亡命（exile）と混同しない
- bounds: 省略推奨（都市座標から自動計算される）。手動指定する場合はすべての都市と矢印が収まる範囲にすること
- 1つのroute_mapシーンに1〜5経路が適切。あまり多いと見づらい
- 都市の座標は実際の緯度・経度を正確に使用すること
- 都市名は日本語で記述すること（例: "ブダペスト", "プリンストン"）

### source_prompt（ken_burns用画像生成プロンプト）★画像品質に直結★
- 英語で記述。80〜150語程度で具体的に書くこと（短すぎるプロンプトは品質が低い）
- 必ず「oil painting style, academic realism, warm muted tones」を含める
- 禁止: photorealistic, anime, cartoon, digital art, neon, 3D render

**構図指示（必須）**: 以下のいずれかを含める
  - portrait composition（人物の上半身）
  - wide establishing shot（場所の全景）
  - medium shot with depth（中距離、奥行きあり）
  - overhead view / bird's eye（俯瞰）
  - close-up detail（手元、書類、黒板など）

**人物描写の必須要素**:
  - 時代（例: 1940s, postwar era, late 20th century）
  - 国籍・民族的特徴（例: Hungarian, Eastern European）
  - 年齢層（例: elderly man in his 70s, young researcher in his 20s）★ナレーションの時代と一致させること。幼少期のシーンに老人、青年期のシーンに高齢者を描かない★
  - 服装（例: rumpled tweed jacket, open-collar shirt, no tie）
  - 表情・動作（例: animated gesture while explaining, deep in thought）
  - 場所・背景（例: cluttered office, university corridor, conference hall）

**人物単独シーンの禁止表現** ★主役の単独肖像が意図のシーン（person_NN 等）で必ず守る★:
  - "other students/scholars/mathematicians/people visible in the background" のような **他の人物の存在を匂わせる表現を入れない**（過去のケースで Gemini Flash が背景人物を別肖像として膨らませ、結果としてコラージュ風の複数人物画像を生成した、ある回で発覚）
  - 背景は建築・室内装飾・自然光・書類や黒板など小道具に留める
  - 群像（議論シーン、講義、家族写真等）が **意図的に複数人物** を含む場合は scene_id や source_prompt 冒頭でその意図を明示する（例: "A heated debate between three mathematicians..."）

**use_reference / is_subject（参照写真の使用）** ★主題者の肖像忠実度に直結★:
  - `visual.use_reference` は **既定 true**（主題者の実在写真を参照として使い、実物の顔に忠実な肖像を生成する）。主題者（このエピソードの主役）が描かれるシーンでは **必ず true のままにする**
  - **`use_reference: false` を付けてよいのは「そのシーンの主たる／唯一の人物が主題者ではない別の歴史的人物」か「人物が主役でない場面」だけ**。脇役が *言及される* だけ、あるいは主題者と *一緒に写る* だけで false にしてはいけない（主題者がいるなら参照を使い、脇役は AI が別人として描く）。地名・施設名（例: "Dunsink Observatory"）は人物ではないので一切影響しない
  - 主題者以外の人物を主役として描くシーンには **`is_subject: false`** も併せて付ける（cross-scene 一貫性チェックの対象外にするため）
  - 例: person_NN が「若き主題者がコルバーンと暗算で競う」なら主題者が主役 → use_reference: true（コルバーンは AI が別人として描く）。「父テオンの肖像」のように脇役が主役なら use_reference: false かつ is_subject: false

**場面描写の必須要素**:
  - 具体的な地名や建物（例: Budapest, Cambridge, Princeton IAS building）
  - 時代の雰囲気（例: 1930s European academic atmosphere, Cold War era）
  - 照明（例: warm lamplight, soft natural light from tall windows, dim study room）
  - 背景の小道具（例: stacked papers, chalkboard with equations, coffee cups）
  - 季節・天候（例: autumn leaves, snowy street, bright summer day）

**悪いプロンプト例**: "A mathematician thinking, oil painting style, academic realism, warm muted tones"
  → 短すぎる。誰が・どこで・いつ・何をしているかが不明。生成画像は汎用的でつまらない

**良いプロンプト例**: "Elderly Hungarian mathematician in his 70s, thin white hair, wearing a rumpled open-collar shirt, animatedly explaining a proof to a young colleague in a cluttered university office filled with stacked papers and coffee cups, warm lamplight, Budapest 1990s atmosphere, portrait composition, oil painting style, academic realism, warm muted tones"
  → 具体的。人物・場所・時代・雰囲気・構図がすべて指定されている

### manim テンプレート ★利用可能なテンプレート名のみ使用すること★
scene_definition.jsonのtemplateには以下のテンプレートIDのみ指定可能:
{manim_template_list}
上記リストにないテンプレート名を使わないこと。
エピソードの内容に合うテンプレートがリストにない場合は、ken_burns か text_overlay で代替する。

### credits
- voicevox: "VOICEVOX:青山龍星" （固定）
- references: 参考文献をリスト（episode_configから引用）

### description（YouTube概要欄用）
YouTube概要欄に使うテキストを生成する。credits_generator.pyが読み取って description.txt に反映する。

```json
"description": {
  "intro": "2次方程式の解の公式は中学で習う。3次、4次にも公式がある。\nでは5次は？ 300年以上にわたり数学者が挑んだこの問いに、\n20歳の青年が全く新しい答えを出した。\n「解けるかどうかは、方程式の対称性で決まる」。\nエヴァリスト・ガロアの生涯と数学的業績を紹介します。",
  "chapter_subtitles": {
    "intro": "導入",
    "person": "革命と論文、そして決闘",
    "math": "根の対称性からガロア群へ",
    "closing": "20歳が遺した理論の行方"
  },
  "tags": ["ガロア", "ガロア理論", "群論", "方程式", "対称性"]
}
```

ルール:
- `intro`: 3〜5行で動画の内容を紹介する。最後の行は「〜の生涯と数学的業績を紹介します。」で終わる。フックとなるエピソードから始め、視聴者の興味を引く
- `chapter_subtitles`: 各セクション（intro/person/math/closing）のチャプタータイトル。短く印象的に（例：「革命と論文、そして決闘」）。introは「導入」固定
- `tags`: エピソード固有のタグ（5〜8個）。数学者名・テーマ・関連分野を含める
- `intro`の内容はナレーションと事実関係が一致すること（QAで確認される）
- `intro`は narration の **数学的厳密性に関わる前提条件・限定詞** (例: 不完全性定理の「無矛盾な」、対角線論法の「実数の」、可解性の「代数的に」、極限の「無限小に」等) を欠落させない。自然な書き換え (narration と description で語り口を変える) は OK だが、数学的核心要素 (前提条件・限定詞・必須語) は保持する。過去のケースで intro_02 narration の「十分に強い無矛盾な体系には...」が intro では「十分に強い体系には...」と「無矛盾な」が欠落し、数学的に misleading な記述 (矛盾した体系では何でも証明可能) になった事例の再発防止

### 重要
- 事実関係の正確性を最優先する
- 数学的に不確かなことは書かない。推測は「〜と言われている」等で明示する
- 数学パートの最後に「現代での応用」を30秒程度触れる
- JSONのすべてのキーは必ず文字列にすること（例: {"0": "value"} はOK、{0: "value"} はNG）
- ナレーション内の数値（選択肢の数、ビット数、確率値など）は、Manimテンプレートのdocstringに記載されたパラメータと必ず一致させること
- narration には Unicode 特殊文字（上付き ¹²³、下付き ₁₂₃、特殊記号 ≤≥≠ 等）を使用しないこと。数式記号は narration_speech で読み替え、narration 側は通常の ASCII 文字を使うこと（例: log₂ → log2、x² → x^2）
""".strip()


# ─── Manim template discovery ────────────────────────────────────────────


def discover_manim_templates(manim_templates_dir: str = None) -> list[str]:
    """Discover available Manim templates from directory.

    Returns list of template names (filename without .py).
    Extracts docstring first line as description.

    Returns e.g.:
        ["bertrand_postulate", "erdos_network", "random_graph_coloring", ...]
    """
    if not manim_templates_dir or not os.path.isdir(manim_templates_dir):
        return []

    exclude = {"style.py", "__init__.py"}
    templates = []

    for fname in sorted(os.listdir(manim_templates_dir)):
        if not fname.endswith(".py") or fname in exclude or fname.startswith("_"):
            continue
        templates.append(fname[:-3])  # remove .py

    return templates


def build_manim_template_list(manim_templates_dir: str = None) -> str:
    """Build the manim template list string for LLM prompt injection.

    Reads available templates and their docstrings to generate a list like:
        - "bertrand_postulate" : ベルトランの仮説の可視化
        - "erdos_network" : エルデシュ数ネットワーク図
    """
    if not manim_templates_dir or not os.path.isdir(manim_templates_dir):
        return "(利用可能なmanimテンプレートなし。ken_burns または text_overlay を使用すること)"

    import ast as _ast

    exclude = {"style.py", "__init__.py"}
    lines = []

    for fname in sorted(os.listdir(manim_templates_dir)):
        if not fname.endswith(".py") or fname in exclude or fname.startswith("_"):
            continue

        template_name = fname[:-3]
        filepath = os.path.join(manim_templates_dir, fname)

        # Extract docstring first line as description
        description = ""
        try:
            with open(filepath, encoding="utf-8") as f:
                tree = _ast.parse(f.read())
            docstring = _ast.get_docstring(tree)
            if docstring:
                # First non-empty line of module docstring
                for line in docstring.split("\n"):
                    line = line.strip()
                    if line:
                        description = line
                        break
        except Exception:
            pass

        if description:
            lines.append(f'- "{template_name}" : {description}')
        else:
            lines.append(f'- "{template_name}"')

    if not lines:
        return "(利用可能なmanimテンプレートなし。ken_burns または text_overlay を使用すること)"

    return "\n".join(lines)


# ─── API setup ───────────────────────────────────────────────────────────────


def _load_dotenv():
    """Load .env file from script dir, project root, or main repo root.

    When running inside a git worktree, the project root differs from the
    main repository root.  This function walks up from src/ and also checks
    the main repo root so that a single .env in the real project directory
    is found regardless of the working-tree location.
    """
    if getattr(_load_dotenv, "_done", False):
        return
    try:
        from dotenv import load_dotenv

        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [script_dir, os.path.dirname(script_dir)]
        # If inside a git worktree, also check the main repository root
        git_file = os.path.join(os.path.dirname(script_dir), ".git")
        if os.path.isfile(git_file):
            with open(git_file, encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("gitdir:"):
                gitdir = content.split(":", 1)[1].strip()
                gitdir = os.path.normpath(os.path.join(os.path.dirname(script_dir), gitdir))
                main_git = gitdir
                while main_git and not os.path.isdir(os.path.join(main_git, "objects")):
                    main_git = os.path.dirname(main_git)
                if main_git:
                    main_root = os.path.dirname(main_git)
                    if main_root not in candidates:
                        candidates.append(main_root)
        for d in candidates:
            env_path = os.path.join(d, ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                break
    except ImportError:
        pass
    _load_dotenv._done = True


def get_gemini_client():
    """Initialize Gemini API client."""
    _load_dotenv()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found.")
        print("Set it in .env file or as environment variable.")
        sys.exit(1)

    from google import genai

    return genai.Client(api_key=api_key)


# ─── LLM call backends ──────────────────────────────────────────────────────


def call_gemini(
    system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
) -> str:
    """Call Gemini API and return raw response text."""
    client = get_gemini_client()

    from google.genai import types

    gen_config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=gen_config,
    )

    return response.text or ""


def call_claude_code(
    system_prompt: str, user_prompt: str, model: str = "claude", debug: bool = False
) -> str:
    """Call Claude Code via -p flag using shared claude_backend module.

    Combines system + user prompt and delegates to claude_backend.call_claude().
    """
    combined_prompt = system_prompt + "\n\n---\n\n" + user_prompt

    # Resolve project root (parent of src/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    return _call_claude_backend(
        prompt=combined_prompt,
        model=model,
        debug=debug,
        project_root=project_dir,
        prefix="script",  # temp files: _tmp_script_prompt.txt / _tmp_script_output.txt
        allowed_tools="Read",  # No Bash: prevent Opus from trying workaround
        # via bash stdout (which the stream-json parser
        # can't capture). a past session.
    )


def is_claude_model(model: str) -> bool:
    """Check if the model string indicates Claude Code backend."""
    return model.lower().startswith("claude")


# CLAUDE_MODEL_MAP imported from claude_backend


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 30000,
    debug: bool = False,
) -> str:
    """Unified LLM call interface. Routes to appropriate backend."""
    if is_claude_model(model):
        return call_claude_code(system_prompt, user_prompt, model=model, debug=debug)
    else:
        return call_gemini(system_prompt, user_prompt, model, temperature, max_tokens)


# ─── Prompt building ─────────────────────────────────────────────────────────


def build_system_prompt(manim_templates_dir: str = None) -> str:
    """Build the system prompt with style guide, scene spec, and available templates."""
    template_list = build_manim_template_list(manim_templates_dir)
    rules = GENERATION_RULES.replace("{manim_template_list}", template_list)

    return f"""あなたは「数学史記」という日本語YouTubeチャンネルのスクリプトライターです。
数学者の人生と数学的業績を描くドキュメンタリー動画の台本を、JSON形式で生成してください。

{STYLE_GUIDE_PROMPT}

{SCENE_SPEC_PROMPT}

{rules}

出力は **scene_definition.json のJSON のみ** を返してください。
マークダウンのコードブロック（```json ... ```）で囲んでも構いませんが、JSON以外のテキストは含めないでください。

★重要: ナレーションの合計文字数が2,600〜3,200文字になるようにしてください。
各シーンのナレーションは具体的なエピソード、歴史的背景、数学的内容を丁寧に語ってください。
箇条書き的な短文の羅列ではなく、ドキュメンタリーのナレーションとして自然に聞こえる語り口にしてください。
"""


def build_user_prompt(config: dict) -> str:
    """Build the user prompt from episode config."""
    parts = []

    parts.append("以下のエピソード設定に基づいて、scene_definition.json を生成してください。\n")

    parts.append("## エピソード設定\n")
    parts.append(f"- episode_id: {config['episode_id']}")
    parts.append(f"- 数学者: {config['mathematician_ja']}（{config['mathematician']}）")
    parts.append(f"- テーマ: {config['theme']}")
    parts.append(f"- 目標尺: {config.get('target_duration_minutes', 10)}分")

    if config.get("title_draft"):
        parts.append(f"- タイトル案: {config['title_draft']}")

    target_min = config.get("target_duration_minutes", 10)
    target_chars = int(target_min * 60 * 4.5)
    parts.append(f"- 目標文字数: 約{target_chars}文字（{target_min}分 × 実効4.5文字/秒）")

    if config.get("hook"):
        parts.append(f"- フック（導入の掴み）: {config['hook']}")

    if config.get("key_topics"):
        parts.append(f"- 主要トピック: {', '.join(config['key_topics'])}")

    if config.get("modern_connection"):
        parts.append(f"- 現代との接続: {config['modern_connection']}")

    if config.get("key_episodes"):
        parts.append("\n## 重要なエピソード")
        for ep in config["key_episodes"]:
            parts.append(f"- {ep}")

    if config.get("math_content"):
        parts.append("\n## 数学的内容の指示")
        for mc in config["math_content"]:
            parts.append(f"- {mc}")

    if config.get("references"):
        parts.append("\n## 参考文献")
        for ref in config["references"]:
            parts.append(f"- {ref}")

    # 企画で決めた語彙の制約を**生成時に**渡す。
    #
    # `forbidden_phrases` と `required_phrases` は、これまで
    # **smoke test が事後に検出するだけ**で、src/ のどのモジュールも読んでいなかった。
    # つまり「この語は使わない」「この語は必ず出す」と config に書いても台本生成には
    # 一切届かず、出来上がったものを人が直す運用になっていた ── ある回は『ミニマックス』
    # を一行入れると決めたのにどの scene にも書かれず、完成した動画を見て初めて判明した。
    # 決めたことを生成側にも渡し、検出はその後の網として残す。
    forbidden = [p for p in (config.get("forbidden_phrases") or []) if isinstance(p, str) and p]
    if forbidden:
        parts.append("\n## 使ってはいけない表現")
        parts.append(
            "以下は事実誤認・誇張・読み違いを招くため、narration / narration_speech / "
            "text_overlay / description のいずれにも書かないでください "
            "(言い換えて同じ内容を伝えること):"
        )
        for p in forbidden:
            parts.append(f"- {p}")

    required = [p for p in (config.get("required_phrases") or []) if isinstance(p, str) and p]
    if required:
        parts.append("\n## 必ず本編に出す語")
        parts.append("以下は企画で「出す」と決めた語です。narration の中に最低 1 回入れてください:")
        for p in required:
            parts.append(f"- {p}")

    if config.get("additional_instructions"):
        parts.append("\n## 追加指示")
        parts.append(config["additional_instructions"])

    return "\n".join(parts)


def build_retry_prompt(user_prompt: str, current_chars: int, attempt: int) -> str:
    """Build a retry prompt with feedback on character count."""
    direction = "増やして" if current_chars < CHAR_COUNT_MIN else "減らして"
    target_mid = (CHAR_COUNT_MIN + CHAR_COUNT_MAX) // 2

    return f"""{user_prompt}

## ★再生成指示（{attempt}回目のリトライ）★
前回の生成結果はナレーション合計 {current_chars}文字 でした。
目標範囲は {CHAR_COUNT_MIN}〜{CHAR_COUNT_MAX}文字 です（目安: 約{target_mid}文字）。
文字数を{direction}ください。
- エピソードや説明の具体性を{"追加して厚みを出して" if current_chars < CHAR_COUNT_MIN else "整理して簡潔にして"}ください
- シーン数の増減ではなく、各シーンのナレーション量で調整してください
- JSON構造やvisualタイプは変更不要です"""


def build_qa_feedback_prompt(qa_report_path: str) -> str:
    """Build additional instructions from QA report for retry.

    Extracts actionable issues from qa_report_script.json and formats them
    as specific correction instructions for the LLM.

    Returns empty string if no actionable issues found.
    """
    try:
        with open(qa_report_path, encoding="utf-8") as f:
            report = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  WARNING: Could not read QA report: {e}")
        return ""

    instructions = []

    for agent_key, agent_result in report.get("agents", {}).items():
        # Skip fact_checker issues (require human judgment)
        if "fact" in agent_key:
            continue

        agent_result.get("agent_name", agent_key)
        issues = agent_result.get("issues", [])

        for issue in issues:
            severity = issue.get("severity", "info")
            if severity == "info":
                continue  # Only act on warning and critical

            scene_id = issue.get("scene_id", "")
            detail = issue.get("detail", issue.get("finding", ""))
            suggestion = issue.get("suggestion", "")

            if suggestion:
                loc = f"[{scene_id}] " if scene_id else ""
                instructions.append(f"- {loc}{detail}\n  → 修正案: {suggestion}")

        # ContentReviewer improvements
        improvements = agent_result.get("improvements", [])
        for imp in improvements:
            if imp.get("severity", "info") != "info":
                instructions.append(f"- {imp.get('detail', imp.get('suggestion', ''))}")

    if not instructions:
        return ""

    return (
        "\n\n## ★QAフィードバックに基づく修正指示★\n"
        "前回生成したスクリプトに対するQAチェックで以下の問題が見つかりました。\n"
        "これらを修正した上で、同じ構成・同じシーン数で再生成してください。\n"
        "**指摘されていないシーンのナレーションは極力変更しないでください。**\n\n"
        + "\n".join(instructions)
    )


# ─── JSON extraction ─────────────────────────────────────────────────────────


def _sanitize_json_keys(raw: str) -> str:
    """Fix JSON-non-compliant integer keys: {0: "val"} → {"0": "val"}."""
    return re.sub(r"(?<=[\{,])\s*(\d+)\s*:", r' "\1":', raw)


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response (handles markdown code blocks).

    強化 A: Claude が応答途中で「I'll output the complete JSON now,
    starting fresh」のように self-restart して複数 ```json ブロックを出力する
    ケースに対応。最初の (壊れた) ブロックを掴むのではなく、**ALL ```json
    ブロック を列挙し、parse 成功するものを後ろから採用** する。

    ある時点 で ある回で 3 回連続 build 失敗の根本原因がこれだった。Claude が
    長文 JSON の途中でトークン制約や思考のリセットで「starting fresh」と
    再開、scene_definition_raw_attempt2.txt に 2 つの ```json ブロックが存在
    (pos 0 の壊れた 634 字 + pos 644 の正常 34502 字)。non-greedy regex は
    pos 0 のブロックを取得して JSONDecodeError → 全 attempt fail。
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strategy 1: collect ALL ```json...``` blocks, try last-valid
    # first. Robust against Claude's self-restart mid-response.
    # Use a permissive regex: ```json then anything up to the next ``` OR
    # the next ```json (whichever comes first), then iterate.
    json_blocks: list[str] = []
    # Find positions of every ```json marker
    fence_positions = [m.start() for m in re.finditer(r"```json", text)]
    # Find positions of every closing ``` (any kind)
    all_fences = [m.start() for m in re.finditer(r"```", text)]
    for fence_start in fence_positions:
        body_start = fence_start + len("```json")
        # Next fence position strictly after body_start
        next_fence = next((p for p in all_fences if p > body_start), None)
        if next_fence is None:
            # Take everything to end of text
            body = text[body_start:].strip()
        else:
            body = text[body_start:next_fence].strip()
        if body:
            json_blocks.append(body)

    # Try each block from LAST to FIRST (Claude's later restart wins)
    for body in reversed(json_blocks):
        try:
            raw = _sanitize_json_keys(body)
            return json.loads(raw)
        except json.JSONDecodeError:
            continue

    # Strategy 2 (legacy): generic ``` fenced blocks (no "json" tag)
    patterns = [
        r"```\s*\n(.*?)\n\s*```",
        r"```\s*(.*?)```",
    ]
    for pattern in patterns:
        # Try ALL matches not just the first
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                raw = _sanitize_json_keys(match.group(1).strip())
                return json.loads(raw)
            except json.JSONDecodeError:
                continue

    # Strategy 3: parse the whole text as JSON
    try:
        raw = _sanitize_json_keys(text.strip())
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 4: outermost balanced { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            raw = _sanitize_json_keys(text[start : end + 1])
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response.\nFirst 500 chars:\n{text[:500]}")


# ─── Character count helper ──────────────────────────────────────────────────


def count_narration_chars(data: dict) -> int:
    """Count total narration characters (excluding | markers)."""
    total = 0
    for section in data.get("sections", []):
        for scene in section.get("scenes", []):
            for text in scene.get("narration", []):
                total += len(text.replace("|", ""))
    return total


# ─── timeline_recap schema normalization ─────────────────────
#
# The LLM is given only each Manim template's one-line docstring, not its param
# schema. For timeline_recap ("Two-track life/work timeline") it emits a natural
#     {name, birth_year, death_year, life_events:[{year,text}],
#      work_events:[{year,text}]}
# shape, but the template reads
#     {title, milestones:[[year,label,track,colour],...], legend}
# and, when `milestones` is absent, used to SILENTLY fall back to its Laplace
# self-test -- rendering Laplace's life events under another episode's title
#. The template now raises on that mismatch; here we
# rewrite the params upstream so real pipeline runs render the right person.


def _timeline_fmt_year(year) -> str:
    """Render a milestone year label, appending 年 unless already an era word."""
    s = str(year).strip()
    if not s:
        return s
    return s if s.endswith(("年", "世紀", "頃", "代")) else f"{s}年"


def _timeline_year_sort_key(year) -> int:
    """Leading (signed) integer of a year for chronological ordering."""
    m = re.search(r"-?\d+", str(year))
    return int(m.group()) if m else 9999


def _timeline_event_label(ev: dict) -> str:
    """Pull the display label from an event dict (LLM key naming varies)."""
    for k in ("text", "label", "event", "description", "title"):
        v = ev.get(k)
        if v:
            return str(v)
    return ""


def _milestones_in_list_form(milestones) -> bool:
    """True if `milestones` is already the template's schema.

    The template reads each milestone as [year, label, track, colour] (indexes
    m[0]..m[3]). "Already normalized" therefore means a non-empty list whose
    entries are ALL list/tuple rows -- NOT the LLM's per-milestone dict shape
    ({year, life, work}), which would break the template with KeyError: 0.
    Used for idempotency: such scenes are left untouched.
    """
    if not isinstance(milestones, list) or not milestones:
        return False
    # The row LENGTH is part of the schema, not just the row type. An earlier episode
    # emitted 2-element rows (["1876", "生まれる"]); those are lists, so a type-only
    # check called them "already normalized" and passed them through, and the
    # template's len(m) >= 4 guard then raised at RENDER time -- i.e. after a 60
    # minute build, shipping a text_overlay placeholder in place of the recap.
    # Requiring len >= 4 here makes short rows fall through to conversion instead.
    return all(isinstance(m, (list, tuple)) and len(m) >= 4 for m in milestones)


# timeline_recap's legend rows are keyed by COLOUR ("gold"/"cyan"/"white"/"pink"),
# but the LLM naturally writes a track-keyed dict ({"life": ..., "work": ...}).
_LEGEND_TRACK_COLOUR = {"life": "white", "work": "gold"}


def _normalize_timeline_legend(legend):
    """Convert a dict-form legend to the template's list of [colour, label] rows.

    The template does `for key, lbl in legend_data`, so a dict yields its KEYS and
    unpacking "life" into two names raises ValueError: too many values to unpack --
    at render time, i.e. a placeholder in the finished video.
    Track names are mapped to their colour ("life" below the axis in white, "work"
    above it in gold); a key the palette already knows is passed through. Returns
    None when `legend` is not a dict (nothing to convert).
    """
    if not isinstance(legend, dict) or not legend:
        return None
    # Track names are resolved FIRST so the output is canonical: "life" is also a
    # legacy palette key, and passing it through would leave two spellings of the
    # same colour in circulation.
    known = {"white", "gold", "cyan", "pink", "celestial", "probability"}
    rows = []
    for key, label in legend.items():
        k = str(key).strip()
        colour = _LEGEND_TRACK_COLOUR.get(k) or (k if k in known else "white")
        rows.append([colour, str(label)])
    return rows


def _pad_short_milestone_rows(milestones) -> list | None:
    """Pad [year, label] / [year, label, track] rows out to the template's 4 columns.

    The template reads m[0]..m[3] = [year, label, track, colour] and raises when a
    row is shorter. The LLM's most natural shape, however, is a plain
    [year, label] pair, which no other branch of the normalizer
    recognizes: it carries no life_events/work_events keys and no dict rows, so
    _life_work_to_milestones() returns None and the scene would reach the renderer
    unchanged -- placeholder in the finished video.

    An explicit third element is honoured as the track ("work" above the axis,
    "life" below); everything else defaults to the work track, matching the
    generic fallback in _milestone_dict_to_rows(). Returns None when `milestones`
    is not a list of short rows (so the caller falls through to the other
    branches).
    """
    if not isinstance(milestones, list) or not milestones:
        return None
    if not all(isinstance(m, (list, tuple)) and 2 <= len(m) < 4 for m in milestones):
        return None
    rows = []
    for m in milestones:
        track = str(m[2]).strip() if len(m) >= 3 and str(m[2]).strip() else "work"
        colour = "gold" if track == "work" else "white"
        rows.append([_timeline_fmt_year(m[0]), str(m[1]), track, colour])
    return rows


def _milestone_dict_to_rows(ev: dict) -> list:
    """Convert one per-milestone dict to (sort_key, row) tuples.

    The LLM sometimes emits milestones as dicts like
    {"year": 1815, "life": "...", "work": "..."} instead of the template's
    [year, label, track, colour] rows. A dict carrying BOTH a life and a work
    label splits into two rows (work above the axis in gold, life below in
    white), sorted with everything else by year. A dict with neither but a
    generic label (text/label/...) falls back to a single row, honouring an
    explicit track/colour when present. Empty labels are dropped.
    """
    y = ev.get("year", "")
    sk = _timeline_year_sort_key(y)
    yr = _timeline_fmt_year(y)
    rows: list[tuple[int, list]] = []
    work_label = str(ev.get("work") or "").strip()
    life_label = str(ev.get("life") or "").strip()
    if work_label:
        rows.append((sk, [yr, work_label, "work", "gold"]))
    if life_label:
        rows.append((sk, [yr, life_label, "life", "white"]))
    if not rows:
        # No life/work keys: fall back to a generic label, honouring an
        # explicit track/colour so we never silently drop the milestone.
        label = _timeline_event_label(ev)
        if label:
            track = str(ev.get("track") or "work").strip() or "work"
            colour = str(ev.get("colour") or ev.get("color") or "").strip()
            if not colour:
                colour = "white" if track == "life" else "gold"
            rows.append((sk, [yr, label, track, colour]))
    return rows


def _life_work_to_milestones(params: dict) -> dict | None:
    """Convert the LLM's timeline schemas to the template's milestones schema.

    Handles two natural LLM shapes the template does not read directly:

      1. {name, birth_year, death_year,
          life_events:[{year, text}], work_events:[{year, text}]}
      2. {title, milestones:[{year, life, work}, ...]}  <- per-milestone dicts
         (this second shape has a `milestones` key but its entries are dicts,
          so it still breaks the template with KeyError: 0

    Returns the rewritten params dict, or None when `params` carries no
    recognizable timeline data (so the caller leaves it untouched -- e.g. an
    empty dict or the {"mode": "laplace"} self-test).
    """
    life = params.get("life_events") or []
    work = params.get("work_events") or []
    birth = params.get("birth_year")
    death = params.get("death_year")

    # A `milestones` key whose entries are dicts is the LLM's per-milestone
    # shape (not the template's [year,label,track,colour] rows): treat it as
    # convertible data rather than passing the crash-inducing dicts through.
    raw_milestones = params.get("milestones")
    dict_milestones = (
        [m for m in raw_milestones if isinstance(m, dict)]
        if isinstance(raw_milestones, list)
        else []
    )

    if not (life or work or birth is not None or death is not None or dict_milestones):
        return None

    rows: list[tuple[int, list]] = []  # (sort_key, [year, label, track, colour])
    if birth is not None:
        rows.append(
            (_timeline_year_sort_key(birth), [_timeline_fmt_year(birth), "誕生", "life", "white"])
        )
    for ev in life:
        if isinstance(ev, dict):
            y = ev.get("year", "")
            rows.append(
                (
                    _timeline_year_sort_key(y),
                    [_timeline_fmt_year(y), _timeline_event_label(ev), "life", "white"],
                )
            )
    for ev in work:
        if isinstance(ev, dict):
            y = ev.get("year", "")
            rows.append(
                (
                    _timeline_year_sort_key(y),
                    [_timeline_fmt_year(y), _timeline_event_label(ev), "work", "gold"],
                )
            )
    if death is not None:
        rows.append(
            (_timeline_year_sort_key(death), [_timeline_fmt_year(death), "没", "life", "white"])
        )
    for ev in dict_milestones:
        rows.extend(_milestone_dict_to_rows(ev))

    rows.sort(key=lambda r: r[0])
    milestones = [r[1] for r in rows]

    name = str(params.get("name", "")).strip()
    title = params.get("title") or (f"{name}の歩んだ時間" if name else "歩んだ時間")

    out = {"title": title, "milestones": milestones, "legend": [["gold", "業績"]]}
    if "duration" in params:
        out["duration"] = params["duration"]
    return out


def normalize_timeline_recap_scenes(scene_def: dict) -> int:
    """Rewrite timeline_recap scenes' params to the template's milestones schema.

    Idempotent: scenes whose `milestones` are ALREADY the template's
    [year,label,track,colour] list rows are left untouched, as are scenes with
    no recognizable timeline data (the Laplace self-test). Crucially, a
    `milestones` key that is a list of per-milestone DICTS ({year, life, work})
    is NOT the template's schema -- it crashes the template with KeyError: 0
 -- so it is converted rather than passed through. A scene
    that selects timeline_recap but emits some OTHER unknown schema is left
    untouched -- the template's fail-loud shape guard then surfaces it via the
    pipeline placeholder banner rather than silently shipping wrong data.

    Returns the number of scenes rewritten (for logging).
    """
    rewritten = 0
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("type") != "manim" or visual.get("template") != "timeline_recap":
                continue
            params = visual.get("params")
            if not isinstance(params, dict):
                continue
            # The legend is normalized FIRST and independently of the milestones:
            # a scene can carry perfectly good 4-column milestones and still crash
            # the renderer on a dict-form legend, so this must
            # not sit behind the "already normalized" early-continue below.
            legend = _normalize_timeline_legend(params.get("legend"))
            if legend is not None:
                params["legend"] = legend
            # Already the template's list-of-rows schema? leave it. (A dict-form
            # `milestones` is NOT list form, so it falls through to conversion.)
            if _milestones_in_list_form(params.get("milestones")):
                if legend is not None:
                    rewritten += 1
                continue
            padded = _pad_short_milestone_rows(params.get("milestones"))
            if padded is not None:
                visual["params"] = {**params, "milestones": padded}
                rewritten += 1
                continue
            converted = _life_work_to_milestones(params)
            if converted is not None:
                if legend is not None:
                    converted["legend"] = legend
                visual["params"] = converted
                rewritten += 1
            elif legend is not None:
                rewritten += 1
    return rewritten


def strip_llm_cloud_readings(scene_def: dict) -> int:
    """Drop any narration_speech_cloud the LLM produced. Returns the count removed.

    By design the LLM does NOT own the Cloud reading: gen_cloud_readings.py builds
    narration_speech_cloud from narration at pipeline time (native は; comma-isolated
    particles only -> わ). But when episode_config additional_instructions tell the
    LLM to "narration_speech_cloud を用意 (助詞は→わ表記)", it over-applies the rule and
    rewrites word-internal は to わ as well (blanket-わ). Chirp3-HD then inserts a
    phantom pause at every lone わ (~25% longer by A/B) and the reading sounds unnatural.
    gen_cloud only FILLS scenes that lack a cloud, so an LLM-emitted blanket-わ survives
    all the way to synthesis.

    Stripping here -- the deterministic point where the LLM output is finalized --
    removes that whole failure class at the source: gen_cloud then regenerates every
    cloud from narration, so word-internal は stays は. narration_speech (the VOICEVOX
    kana spell-out, which gen_cloud reuses for symbol sentences) is left untouched.
    """
    stripped = 0
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            if scene.pop("narration_speech_cloud", None) is not None:
                stripped += 1
    return stripped


# ─── Validation ──────────────────────────────────────────────────────────────


def validate_scene_definition(data: dict) -> tuple[list[str], bool]:
    """Validate generated scene_definition.json.

    Returns:
        (warnings, retry_needed) - warnings list and whether retry is recommended
    """
    warnings = []
    retry_needed = False

    # Top-level fields
    for field in ["episode_id", "title", "version", "sections"]:
        if field not in data:
            warnings.append(f"Missing top-level field: {field}")

    if "sections" not in data:
        return warnings, True  # Broken structure, definitely retry

    # Description block validation (soft - warnings only, not retry)
    desc = data.get("description", {})
    if not desc:
        warnings.append(
            "Missing description block (intro/chapter_subtitles/tags for YouTube概要欄)"
        )
    else:
        if not desc.get("intro"):
            warnings.append("description.intro is empty")
        if not desc.get("chapter_subtitles"):
            warnings.append("description.chapter_subtitles is empty")
        if not desc.get("tags"):
            warnings.append("description.tags is empty")

    # Section validation
    valid_types = {"intro", "person", "math", "closing"}
    seen_scene_ids = set()
    total_chars = 0
    scene_count = 0

    for section in data["sections"]:
        section_type = section.get("section_type", "")
        if section_type not in valid_types:
            warnings.append(f"Invalid section_type: {section_type}")

        for scene in section.get("scenes", []):
            scene_count += 1
            scene_id = scene.get("scene_id", "")

            # Unique scene_id
            if scene_id in seen_scene_ids:
                warnings.append(f"Duplicate scene_id: {scene_id}")
            seen_scene_ids.add(scene_id)

            # Narration
            narration = scene.get("narration", [])
            if not narration:
                warnings.append(f"{scene_id}: Empty narration")

            for text in narration:
                clean = text.replace("|", "")
                total_chars += len(clean)

            # narration_speech validation (optional field)
            narration_speech = scene.get("narration_speech")
            if narration_speech is not None:
                if len(narration_speech) != len(narration):
                    warnings.append(
                        f"{scene_id}: narration_speech length ({len(narration_speech)}) "
                        f"!= narration length ({len(narration)})"
                    )

            # Visual
            visual = scene.get("visual", {})
            vtype = visual.get("type", "")
            if vtype not in ["ken_burns", "text_overlay", "manim", "route_map"]:
                warnings.append(f"{scene_id}: Invalid visual type: {vtype}")

            if (
                vtype == "ken_burns"
                and not visual.get("source")
                and not visual.get("source_prompt")
            ):
                warnings.append(f"{scene_id}: ken_burns has no source or source_prompt")

            if vtype == "manim" and not visual.get("template"):
                warnings.append(f"{scene_id}: manim has no template")

            if vtype == "text_overlay" and not visual.get("content"):
                warnings.append(f"{scene_id}: text_overlay has no content")

            if vtype == "route_map":
                if not visual.get("cities"):
                    warnings.append(f"{scene_id}: route_map has no cities")
                if not visual.get("route"):
                    warnings.append(f"{scene_id}: route_map has no route")

    # ── Character count check (ADVISORY, not a hard length target) ──
    # Length must follow content, not be forced into a window (user directive
    # 2026-07-11): do NOT retry to pad a tight script up to a MIN, nor trim good
    # content down to a MAX. Normal over/under vs the soft target is accepted.
    # Only a *pathological* shortfall (< 50% of the intended length) triggers a
    # retry -- a backstop against a broken/truncated generation, not against
    # content-driven length. See internal notes.
    char_mid = (CHAR_COUNT_MIN + CHAR_COUNT_MAX) / 2
    pathological_floor = int(char_mid * 0.5)
    if total_chars < pathological_floor:
        warnings.append(
            f"ERROR: CHAR COUNT PATHOLOGICALLY LOW: {total_chars} chars "
            f"(< {pathological_floor}, likely a broken/truncated generation) -- retrying"
        )
        retry_needed = True
    elif total_chars < CHAR_COUNT_MIN:
        warnings.append(
            f"ADVISORY: below the soft target ({total_chars} chars, soft range "
            f"{CHAR_COUNT_MIN}-{CHAR_COUNT_MAX}) -- accepted, length follows content"
        )
    elif total_chars > CHAR_COUNT_MAX:
        warnings.append(
            f"ADVISORY: above the soft target ({total_chars} chars, soft range "
            f"{CHAR_COUNT_MIN}-{CHAR_COUNT_MAX}) -- accepted, length follows content"
        )
    else:
        warnings.append(
            f"OK: Char count within soft target: {total_chars} chars "
            f"({CHAR_COUNT_MIN}-{CHAR_COUNT_MAX})"
        )

    # Duration estimate (4.5 chars/sec + 0.8s pause per sentence)
    num_sentences = sum(
        len(scene.get("narration", []))
        for section in data["sections"]
        for scene in section.get("scenes", [])
    )
    speech_sec = total_chars / 4.5
    pause_sec = num_sentences * 0.8
    est_duration_sec = speech_sec + pause_sec
    est_duration_min = est_duration_sec / 60

    target = data.get("metadata", {}).get("target_duration_minutes", 10)
    if est_duration_min < target * 0.6:
        warnings.append(
            f"Script too short: ~{est_duration_min:.1f}min (target: {target}min, {total_chars} chars)"
        )
    elif est_duration_min > target * 1.4:
        warnings.append(
            f"Script too long: ~{est_duration_min:.1f}min (target: {target}min, {total_chars} chars)"
        )

    return warnings, retry_needed


def print_summary(data: dict, warnings: list[str]):
    """Print summary of generated scene_definition."""
    print(f"\n{'=' * 60}")
    print("Script Generation Summary")
    print(f"{'=' * 60}")
    print(f"  Title:    {data.get('title', 'N/A')}")
    print(f"  Episode:  {data.get('episode_id', 'N/A')}")

    total_chars = 0
    total_scenes = 0
    section_stats = []

    for section in data.get("sections", []):
        section_id = section.get("section_id", "")
        scenes = section.get("scenes", [])
        chars = sum(len(t.replace("|", "")) for s in scenes for t in s.get("narration", []))
        total_chars += chars
        total_scenes += len(scenes)
        section_stats.append((section_id, len(scenes), chars))

    est_sec = total_chars / 4.5
    # Add pause estimate (0.8s per narration sentence)
    num_sentences = sum(
        len(s.get("narration", []))
        for sec in data.get("sections", [])
        for s in sec.get("scenes", [])
    )
    est_sec += num_sentences * 0.8
    est_min = est_sec / 60

    print(f"  Scenes:   {total_scenes}")
    print(f"  Chars:    {total_chars} ({num_sentences} sentences)")
    print(f"  Target:   {CHAR_COUNT_MIN}-{CHAR_COUNT_MAX} chars")
    print(f"  Est. dur: {est_sec:.0f}s ({est_min:.1f} min)  [4.5ch/s + 0.8s/sent pause]")
    print("\n  Section breakdown:")
    print(f"  {'Section':<12} {'Scenes':>6} {'Chars':>6} {'~Min':>6}")
    print(f"  {'-' * 12} {'-' * 6} {'-' * 6} {'-' * 6}")
    for sid, n, c in section_stats:
        sec_sentences = sum(
            len(s.get("narration", []))
            for sec in data.get("sections", [])
            if sec.get("section_id") == sid
            for s in sec.get("scenes", [])
        )
        sec_est = c / 4.5 + sec_sentences * 0.8
        print(f"  {sid:<12} {n:>6} {c:>6} {sec_est / 60:>5.1f}m")

    # Visual type distribution
    vtypes = {}
    for section in data.get("sections", []):
        for scene in section.get("scenes", []):
            vt = scene.get("visual", {}).get("type", "unknown")
            vtypes[vt] = vtypes.get(vt, 0) + 1
    print("\n  Visual types:")
    for vt, count in sorted(vtypes.items()):
        print(f"    {vt:<15} {count}")

    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("\n  OK: Validation passed")

    print(f"{'=' * 60}")


# ─── Generation with retry ───────────────────────────────────────────────────


def generate_script(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    output_path: str,
    max_retries: int = MAX_RETRIES,
    debug: bool = False,
) -> tuple[dict, list[str]]:
    """Generate scene_definition with automatic retry on character count failure.

    Returns:
        (scene_def, warnings) - the best result and its warnings
    """
    best_result = None
    best_warnings = None
    best_chars = 0
    target_mid = (CHAR_COUNT_MIN + CHAR_COUNT_MAX) // 2

    for attempt in range(1, max_retries + 1):
        print(f"\n{'─' * 40}")
        print(f"  Generation attempt {attempt}/{max_retries}")
        print(f"{'─' * 40}")

        # Build prompt (with retry feedback if not first attempt)
        if attempt == 1:
            current_user_prompt = user_prompt
        else:
            current_user_prompt = build_retry_prompt(user_prompt, best_chars, attempt)

        # Call LLM
        start_time = time.time()
        try:
            response_text = call_llm(
                system_prompt,
                current_user_prompt,
                model,
                temperature,
                max_tokens,
                debug=debug,
            )
        except RuntimeError as e:
            print(f"  WARNING: API error: {e}")
            if best_result is not None:
                print(f"  Using best previous result ({best_chars} chars)")
                break
            continue

        elapsed = time.time() - start_time
        print(f"  API call: {elapsed:.1f}s")

        if not response_text:
            print("  WARNING: Empty response from API")
            continue

        # Extract JSON
        try:
            scene_def = extract_json(response_text)
        except ValueError as e:
            print(f"  WARNING: JSON extraction failed: {e}")
            # Save raw response for debugging
            raw_path = output_path.replace(".json", f"_raw_attempt{attempt}.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"  Raw response saved to: {raw_path}")
            continue

        # follow-up: rewrite any timeline_recap scene from the LLM's natural
        # life/work schema to the `milestones` schema the template reads, before
        # validation / best-result tracking / save. Without this the template
        # silently fell back to its Laplace self-test.
        n_tl = normalize_timeline_recap_scenes(scene_def)
        if n_tl:
            print(f"  Normalized {n_tl} timeline_recap scene(s) -> milestones schema")

        # Cloud reading is gen_cloud_readings' job, not the LLM's: strip any
        # narration_speech_cloud the model emitted so its blanket は->わ over-
        # conversion never reaches synthesis (gen_cloud regenerates from narration
        # with native は). See strip_llm_cloud_readings for the full rationale.
        n_cloud = strip_llm_cloud_readings(scene_def)
        if n_cloud:
            print(f"  Stripped {n_cloud} LLM narration_speech_cloud (gen_cloud will regenerate)")

        # Validate
        warnings, retry_needed = validate_scene_definition(scene_def)
        current_chars = count_narration_chars(scene_def)

        print(f"  Chars: {current_chars} (target: {CHAR_COUNT_MIN}-{CHAR_COUNT_MAX})")

        # Track best result (closest to target midpoint)
        if best_result is None or abs(current_chars - target_mid) < abs(best_chars - target_mid):
            best_result = scene_def
            best_warnings = warnings
            best_chars = current_chars

        # Check if acceptable
        if not retry_needed:
            print("  OK: Character count within target range")
            break
        else:
            direction = "short" if current_chars < CHAR_COUNT_MIN else "long"
            print(f"  WARNING: Character count too {direction}, ", end="")
            if attempt < max_retries:
                print("retrying...")
            else:
                print(f"max retries reached, using best result ({best_chars} chars)")

    if best_result is None:
        print("ERROR: All generation attempts failed")
        sys.exit(1)

    return best_result, best_warnings


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate scene_definition.json from episode_config.json via LLM API",
    )
    parser.add_argument("config_json", help="Path to episode_config.json")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output path for scene_definition.json (default: same dir as config)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"claude/claude-sonnet/claude-opus or Gemini model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Generation temperature (default: 0.7, ignored for claude)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=30000,
        help="Max output tokens (default: 30000, ignored for claude)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Max retry attempts for char count (default: {MAX_RETRIES})",
    )
    parser.add_argument(
        "--manim-templates",
        default=None,
        help="Path to manim_templates dir (default: auto-detect from src/)",
    )
    parser.add_argument(
        "--qa-feedback",
        default=None,
        help="Path to QA report JSON. Injects QA issues into prompt for retry.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug info for Claude Code calls (temp file, command, real-time output)",
    )
    args = parser.parse_args()

    max_retries = args.max_retries

    if not is_claude_model(args.model):
        _load_dotenv()

    # Load episode config
    with open(args.config_json, encoding="utf-8") as f:
        config = json.load(f)

    # Recalculate character targets from target_duration_minutes
    # Rate: 290 chars/min (empirical: 初期エピソード average, matches default 2600-3200 for 10 min)
    global CHAR_COUNT_MIN, CHAR_COUNT_MAX
    target_minutes = config.get("target_duration_minutes", 10)
    char_mid = int(target_minutes * 290)
    CHAR_COUNT_MIN = (int(char_mid * 0.9) // 50) * 50  # round down to 50
    CHAR_COUNT_MAX = ((int(char_mid * 1.1) + 49) // 50) * 50  # round up to 50

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        config_dir = os.path.dirname(os.path.abspath(args.config_json))
        output_path = os.path.join(config_dir, "scene_definition.json")

    # Determine manim templates directory
    manim_templates_dir = args.manim_templates
    if not manim_templates_dir:
        # Auto-detect: look for manim_templates/ next to this script
        src_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(src_dir, "manim_templates")
        if os.path.isdir(candidate):
            manim_templates_dir = candidate

    if manim_templates_dir and os.path.isdir(manim_templates_dir):
        templates = discover_manim_templates(manim_templates_dir)
        print(f"  Manim templates: {len(templates)} found in {manim_templates_dir}")
    else:
        print("  Manim templates: none (dir not found)")

    # Build prompts
    system_prompt = build_system_prompt(manim_templates_dir)
    user_prompt = build_user_prompt(config)

    # Append QA feedback if provided (for retry with QA issues)
    if args.qa_feedback:
        qa_feedback = build_qa_feedback_prompt(args.qa_feedback)
        if qa_feedback:
            user_prompt += qa_feedback
            print(f"  QA feedback: injected from {args.qa_feedback}")
        else:
            print("  QA feedback: no actionable issues found")

    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(system_prompt)
        print("\n=== USER PROMPT ===")
        print(user_prompt)
        print("\n=== CONFIG ===")
        print(f"  Model:       {args.model}")
        print(f"  Backend:     {'Claude Code' if is_claude_model(args.model) else 'Gemini API'}")
        print(f"  Temperature: {args.temperature}")
        print(f"  Max tokens:  {args.max_tokens}")
        print(f"  Max retries: {max_retries}")
        print(f"  Output:      {output_path}")
        return

    # Generate with retry
    backend = (
        f"Claude Code ({args.model})" if is_claude_model(args.model) else f"Gemini ({args.model})"
    )
    print(
        f"Generating script for: {config.get('mathematician_ja', config.get('mathematician', 'unknown'))}"
    )
    print(f"  Model:       {args.model}")
    print(f"  Backend:     {backend}")
    print(f"  Target:      {config.get('target_duration_minutes', 10)} min")
    print(f"  Char target: {CHAR_COUNT_MIN}-{CHAR_COUNT_MAX}")
    print(f"  Max retries: {max_retries}")

    scene_def, warnings = generate_script(
        system_prompt,
        user_prompt,
        args.model,
        args.temperature,
        args.max_tokens,
        output_path,
        max_retries=max_retries,
        debug=args.debug,
    )

    # Save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scene_def, f, ensure_ascii=False, indent=2)
    print(f"\n  Output: {output_path}")

    # stamp _description_meta.json (intro-config signature + intro text
    # hash) right after writing scene_def, so the pipeline / standalone checker
    # can flag a stale description.intro once episode_config's intro-narrative
    # fields (theme / hook / modern_connection / intro_guidance) are edited
    # after generation. Advisory + never fatal. See src/description_meta.py.
    try:
        from description_meta import write_meta as _write_desc_meta

        _dmeta = _write_desc_meta(os.path.dirname(os.path.abspath(output_path)), config, scene_def)
        if _dmeta:
            print(f"  Description meta: {os.path.basename(_dmeta)}")
    except Exception as _e:  # noqa: BLE001 - advisory stamp, never fatal
        print(f"  [WARN] description meta stamp failed: {_e!r}")

    # Summary
    print_summary(scene_def, warnings)


if __name__ == "__main__":
    main()
