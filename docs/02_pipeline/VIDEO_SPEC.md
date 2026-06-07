# VIDEO_SPEC.md — 動画フォーマット仕様 (SSOT)

<!-- lint_video_spec.py: canonical duration mention starts below -->

**通常回の尺: 10〜19 分** (canonical)

> **このファイルが動画フォーマット仕様の SSOT (Single Source of Truth)** です。
> 他のドキュメント はこのファイルを参照する形に統一されています。仕様変更時は本ファイルを更新後、`scripts/lint_video_spec.py` を実行して全 doc の一致を確認してください。
>
> 背景: 過去のセッションで「10〜15 分 → 10〜19 分」更新時、5 docs に分散記載されていたため STYLE_GUIDE.md が sanitize 漏れ。

## 通常回

| 項目 | 値 |
|---|---|
| 尺 | **10〜19 分** (回ごとにテーマに応じて調整、`target_duration_minutes` で指定) |
| 解像度 | 1920×1080 (1080p) |
| フレームレート | 30 fps |
| 動画コーデック | H.264 (libx264, profile High, level 4.0, yuv420p) |
| 音声コーデック | AAC-LC (mono, 24 kHz, ~100 kbps) |
| コンテナ | MP4 (`-movflags +faststart`) |

## ショート

| 項目 | 値 |
|---|---|
| 尺 | 60 秒以内 (YouTube Shorts 仕様) |
| 解像度 | 1080×1920 (縦長 9:16) |
| フレームレート | 30 fps |

## BGM (通常回 default)

| パラメータ | デフォルト値 | episode_config.json での上書き key |
|---|---|---|
| BGM ファイル | `bgm/angels_dream.mp3` | `bgm.file` |
| 音量 | -20 dB | `bgm.volume_db` |
| 冒頭ポーズ | 1.0 s | `bgm.intro_pause` |
| 末尾余韻 (endcard) | **10.0 s** (YouTube endcard 用) | `bgm.outro_hold` |
| BGM fade-in | 2.0 s | `bgm.bgm_fadein` |
| BGM fade-out | 3.0 s | `bgm.outro_fade` |

注意: default を変更する場合、既存ビルド済みエピソードの `output_final.mp4` と config (`outro_hold`) のドリフトが発生しうる。公開済みエピソードは `episode_config.json` で `outro_hold` を明示しておくと rebuild 時も意図した尺が維持される。

## 字幕

| 項目 | 値 |
|---|---|
| フォント | BIZ UDMincho |
| 字幕マージン (下端) | 240 px (Manim Y 座標 ≥ -2.0 で字幕衝突回避) |
| 1 セグメント最大文字数 | 25 字 (subtitle_generator の auto_split) |
| 分割マーカー | `\|` (narration 内、意味的に自然な位置に手動配置) |

## ナレーション

| 項目 | 値 |
|---|---|
| TTS エンジン | VOICEVOX 0.25.1 (localhost:50021) |
| 文体 | ですます調 |
| 想定読み速度 | 290 字 / 分 |
| 字数ターゲット | `target_duration_minutes` から動的計算 |

## 関連

- ナレーション読み仮名: [`src/voicevox_dict.json`](../../src/voicevox_dict.json)
- 既知の誤読パターン: [`src/audio_generator.py`](../../src/audio_generator.py) の `_MISREADING_CATEGORIES`
- パイプラインアーキテクチャ: [`docs/architecture.md`](../architecture.md)
- BGM mixer: [`src/bgm_mixer.py`](../../src/bgm_mixer.py)
