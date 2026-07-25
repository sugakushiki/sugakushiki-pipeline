# 画像生成

> CLAUDE.md から外出しした画像生成パイプラインの規約と運用を集約した doc。
> 関連:
> - `docs/04_assets/IMAGE_GUIDE.md`: 画像生成プロンプト設計の詳細・実例集
>
> 本ファイルは「規約・フォールバック運用」、関連 docs は「プロンプト設計の詳細」を扱う。

---

## パイプライン

- **人物（写真あり）**: Wikimedia 実写 → Gemini Flash で油絵風年齢変換
- **人物（写真なし）**: Wikimedia PD 肖像画 → 油絵変換（同一性は弱い）
- **場所・雰囲気**: Gemini Flash 直接生成

---

## 実写リファレンスが効く条件（最重要）

肖像が実写をもとに生成されるか、テキストだけから生成されるかは **2 段のゲート**で決まる。
どちらか一方でも閉じていると、**エラーも警告も出ないまま** text-only 生成に落ちる。
出来上がった顔が別人に見えて初めて分かる、という壊れ方をするので、先に確認する。

**① 回ぜんたいのゲート**（`episode_config.json`）— 3 つすべてが必要:

```
use_reference = bool(ref_photos) and birth_year and backend == "flash"
```

| 条件 | 欠けたときに起きること |
|---|---|
| 参照写真が取得できている | 参照する画像が無いので当然 text-only |
| **`birth_year` が書かれている** | **その回の肖像が全部 silent に text-only になる** |
| backend が Gemini Flash | 他 backend は image-conditioning に非対応 |

**`birth_year` を書き忘れる**のが一番多い閉じ方。年齢変換の入力としてだけでなく
**ゲートそのもの**なので、無いと `wikimedia_photo_urls` を丁寧に用意しても 1 枚も
Gemini に渡らない。`config_validator` の推奨フィールド WARN と、images step の直前に
走る `lint_portrait_reference`（advisory）が指摘する。

**② シーン単位のゲート**（`scene_definition.json` の visual block）— 2 つとも必要:

- `has_person` — `source_prompt` が人物を描写していると判定されること（自動判定）
- `use_reference` が明示的に `false` でないこと。**未設定は `true` 扱い**（`.get("use_reference", True)`）

未設定＝参照ありが既定、という点は読み違えやすい。`use_reference` を書いていない
シーンは「参照なし」ではなく「参照あり」なので、`lint_portrait_reference` も
**実効値**で判定する（フラグの字面ではなく `.get()` の既定値まで解決した値を見る。
リテラルで判定していた頃は未設定シーンを「参照なし」と誤検知して偽陽性を出していた）。

**若年シーンで参照を外す必要はない。** 68 歳の写真を参照して 11 歳のシーンを描かせても
generator は prompt の年齢語で適切に若年化する。過齢化が起きたケースは年齢の指定が
弱かったのが原因で、対処は `use_reference: false` ではなく
`This MUST be a small CHILD of about nine` のような**強い年齢明記**。

---

## Vision QA

- 検証エンジン: Claude Sonnet（Max 契約内コスト 0）
- 確認項目: 性別 / 年代 / 主題者の同一性 / ステレオタイプ / 細部
- リトライ時の挙動: 不変の `source_prompt` を使い、feedback の累積による性別反転を防止する（`strengthen_prompt` 仕様）

---

## cliche scanner

source_prompt の時代物 cliché を image step 入口で自動検出。事前事実チェック (pre-script fact check) と並ぶ予防的設計の二本柱で、過去にあった「集団のパイプ喫煙が史実無しで Gemini に描かれた」事故の構造的予防を担う。

- 実装: `src/cliche_scanner.py` (独立モジュール、`image_generator.py` の `generate_all()` から呼出)
- 辞書: `src/cliche_dictionary.json` (カテゴリ: period_accessory / smoking / atmosphere / pose / anachronism / academic_stereotype)
- **Layer 1 (always-on、deterministic)**: 辞書ベース word-boundary regex match、case-insensitive
- **Layer 2 (opt-in、Claude Sonnet)**: `--cliche-llm-review` で有効化、Anthropic Max 契約内コスト 0、unverified atmospheric stereotypes を判定
- 出力: WARN のみ (生成は続行、critical/fail-fast にしない)
- per-scene opt-out: visual block に `"cliche_acks": ["smoking pipes", "top hat", ...]` で承認済み cliché を opt-out (例: 史実検証済の場合)
- 単独実行: `PYTHONPATH=src python -m cliche_scanner episodes/<ep>/scene_definition.json [--llm-review]`

実機テストでは、史実的に正しい時代物要素 (top hat / gas lamp / cobblestone street などのビクトリア朝・19世紀後半・20世紀初頭の典型的小道具) が複数検出されるパターンが多く、cliche_acks で承認 opt-out する運用になる想定。

---

## no_human フラグ

`scene_definition.json` の visual block で人物排除シーンを宣言的に指定。

- 用途: 群像シーン (主題者が判別困難) や物・風景のみシーンで、source_prompt の手動書き換えなしに人物排除を実現
- スキーマ: `"no_human": true` (bool、optional、default false)
- 動作:
  - source_prompt 末尾に `"no human figure visible, still life composition, no people in scene."` を自動付加 (Gemini Flash の populate-with-people バイアス抑制)
  - `use_reference` を強制 false (人物リファレンス使用と矛盾するため)
- 検証: `image_generator.py` 起動時に bool 以外なら `ValueError` で fail-fast
- 既存エピソードへの影響: default false のため動作不変
- 不適用: 人物がいるが主題者でないシーンは `"use_reference": false` で対応 (no_human ではない)

---

## フォールバック運用

### `wikimedia_photo_urls`

自動検索で正しい人物が出ない場合の手動 URL 指定。

- **形式**: flat list `["url1", "url2", ...]`（dict 形式は不可、`KeyError: 0` を起こす — 過去のケースで発覚）
- **検証**: `wikimedia_fetcher.py` に dict 形式検出時の defensive check 追加済

### `use_reference: false`

主題者以外の人物（例: Leibniz 回での Newton）を ken_burns で扱う際、リファレンス汚染を防ぐ。visual block に明示する。

**主題者のシーンには付けない。** 上記「実写リファレンスが効く条件」のとおり未設定が
既定 `true` なので、主題者の肖像には何も書かないのが正しい。多人数シーンは
参照を効かせるより text-only のほうが安定する（眼鏡・髭などの識別的特徴は
`source_prompt` に明記して補う）。

### 紙幣・通貨

法的に再現ルール対象になり得るため、間接的（発表会見・報道風）な画像で表現。`source_prompt` に直接 banknote のクローズアップを指定しない。

---

## 既知の落とし穴

詳細は `docs/03_quality/pitfalls.md` 「画像生成 (Wikimedia / Gemini / 透かし)」セクション参照。主要なもの:

| カテゴリ | 概要 |
|---|---|
| 同名施設の写真混入 | `Leonhard Euler Telescope` 等。`wikimedia_credits.json` 確認後に手動削除 |
| AI 生成画像の透かし（BR ✦） | ChatGPT/Sora 系。トリミング+リサイズで除去（過去の運用知見の標準コード） |
| リファレンス画像が source_prompt の年齢指定を上書き | ken_burns で person シーンは肖像画ベース。人物以外のシーン or 手動差し替え |
| 画像が再生成されない | `image_generator` は既存スキップ仕様。`source_prompt` 変更時は該当ファイルを削除して再ビルド |
| Gemini Flash の点配置・形状指示が守られない | プロンプトに数値化した位置関係 + 禁止事項を明記。手動生成 + 透かし除去フォールバック |
| 性別反転（Vision QA リトライ） | feedback の累積を不変の `source_prompt` で吸収（`strengthen_prompt` 修正済） |
| 肖像が別人に見える | まず**参照写真が実際に渡っているか**を疑う（上記 2 段のゲート）。image-conditioning のほうが text-only より一貫して忠実なので、「似ていない」の多くはゲートが閉じている |
| 画像クレジットが絵画を「写真」と呼ぶ | 参照呼称は `death_year` の没年ヒューリスティックで決まる。未設定だと「肖像写真」側に倒れる。合わない回は `portrait_reference_kind` で明示 override |

---

## ステレオタイプ・cliché 注意

`source_prompt` に時代物の cliché を独断で追加する前に web 検索で「その時代・その集団・その場面でこの描写が史実的か」を確認する。

例: 「特定の知識人集団が集団でパイプ喫煙していた」のような描写は史実検証が必要。「intellectual gathering = pipe smoking」のような stereotype は避ける。

LLM ベースの cliché scanner は cliche scanner セクション (Layer 2) を参照。
