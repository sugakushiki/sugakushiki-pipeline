# QA統合ガイド — pipeline.py + script_generator.py リファクタリング

**前提**: qa_checker.py, claude_backend.py, QA_PIPELINE.md が作成済み

---

## 1. ファイル配置

```batch
cd <project_root>/

REM 新規ファイル → src/ に配置
copy qa_checker.py src\qa_checker.py
copy claude_backend.py src\claude_backend.py

REM ドキュメント → docs/ に配置
copy QA_PIPELINE.md docs\QA_PIPELINE.md

REM .gitignore に追加
echo _tmp_qa_prompt.txt >> .gitignore
echo _tmp_qa_output.txt >> .gitignore
echo *.bak >> .gitignore
echo qa_auto_fixes.json >> .gitignore
```

---

## 2. pipeline.py への QA 統合

### 2-1. 変更箇所（argparse）

```python
# 既存の引数に追加
parser.add_argument(
    "--qa", action="store_true",
    help="スクリプト生成後にQAチェックを実行",
)
parser.add_argument(
    "--qa-quick", action="store_true",
    help="クイックQA（Sonnetエージェントのみ）",
)
parser.add_argument(
    "--qa-auto-fix", action="store_true",
    help="QAの結果に基づく自動修正を適用",
)
parser.add_argument(
    "--skip-qa", action="store_true",
    help="QAチェックをスキップ（--qa指定時の上書き）",
)
```

### 2-2. 変更箇所（scriptステップの後に挿入）

```python
# === QA Gate 1: Script QA ===
if (args.qa or args.qa_quick) and not args.skip_qa:
    if "script" in steps_to_run or scene_def_path.exists():
        print(f"\n{'='*60}")
        print("Gate 1: Script QA")
        print(f"{'='*60}")
        
        import subprocess as sp
        
        qa_cmd = [
            sys.executable, 
            str(src_dir / "qa_checker.py"),
            str(scene_def_path),
            "--gate", "script",
        ]
        
        if args.qa_quick:
            qa_cmd.append("--quick")
        
        if args.qa_auto_fix:
            qa_cmd.append("--auto-fix")
        
        # qa_checker は os.system() 経由で Claude Code を呼ぶので
        # subprocess ではなく os.system() で実行する方が安全
        qa_cmd_str = " ".join(f'"{c}"' for c in qa_cmd)
        qa_exit = os.system(qa_cmd_str)
        
        if qa_exit == 1:
            print("\n❌ QA FAILED. Fix critical issues before proceeding.")
            print("   レポート: " + str(episode_dir / "qa_report_script.json"))
            if not input("続行しますか？ (y/N): ").strip().lower() == "y":
                sys.exit(1)
        elif qa_exit == 2:
            print("\n💥 QA ERROR. Some agents failed.")
            print("   レポートを確認してください。")
```

### 2-3. 実行例

```batch
REM スクリプト生成 + クイックQA
python src/pipeline.py episodes/001_erdos/episode_config.json --steps script --qa-quick

REM フルパイプライン + フルQA + 自動修正
python src/pipeline.py episodes/001_erdos/episode_config.json --qa --qa-auto-fix

REM QAスキップ（急ぎの場合）
python src/pipeline.py episodes/001_erdos/episode_config.json --skip-qa
```

---

## 3. script_generator.py のリファクタリング

### 3-1. 目的

script_generator.py 内の Claude Code 呼び出しロジックを claude_backend.py に統一し、
コードの重複を解消する。

### 3-2. 変更概要

**Before** (script_generator.py 内):
```python
# ファイルI/O方式で Claude Code を呼び出す独自実装
prompt_file = project_root / "_tmp_prompt.txt"
output_file = project_root / "_tmp_claude_output.txt"
prompt_file.write_text(prompt, encoding="utf-8")
cmd = f'cd /d "{project_root}" && claude -p "..." --output-format text > "{output_file}" 2>&1'
os.system(cmd)
result = output_file.read_text(encoding="utf-8")
```

**After** (claude_backend.py を利用):
```python
from claude_backend import call_claude, extract_json_from_response

result_text = call_claude(
    prompt=full_prompt,
    model="opus",  # or "sonnet"
    debug=args.debug,
    project_root=str(project_root),
)
scene_definition = extract_json_from_response(result_text)
```

### 3-3. 具体的な変更手順

1. **import追加** (script_generator.py 冒頭):
```python
from claude_backend import call_claude, extract_json_from_response
```

2. **Claude Code 呼び出し部分を置き換え**:
   - `_tmp_prompt.txt` / `_tmp_claude_output.txt` の書き出し・読み込みロジックを削除
   - `call_claude()` 関数呼び出しに置き換え
   - ファイルパス名は `_tmp_qa_prompt.txt` (qa_checker) と衝突しないよう注意
     → claude_backend.py はプレフィックスで区別: script用は `_tmp_script_*`, QA用は `_tmp_qa_*`

3. **JSON抽出を共通化**:
   - `extract_json_from_response()` が claude_backend.py にあるので、
     script_generator.py 内の同様のロジックを削除

4. **モデルマッピングを共通化**:
   - `CLAUDE_MODEL_MAP` が claude_backend.py にあるので、
     script_generator.py 内の重複定義を削除

### 3-4. 注意点

- claude_backend.py の一時ファイル名は `_tmp_qa_*` になっている。
  script_generator.py 用にプレフィックスを分けたい場合は、
  `call_claude()` に `prefix` パラメータを追加するか、
  並行実行しないなら同じファイル名でも問題ない。

- リトライロジック（最大3回、文字数バリデーション）は script_generator.py 固有なので、
  リファクタリング後も script_generator.py 側に残す。

---

## 4. qa_checker.py 単体テスト手順

```batch
cd <project_root>/
venv\Scripts\activate

REM 1. クイックモード（Sonnetのみ、~25分）
python src/qa_checker.py episodes/001_erdos/scene_definition.json --quick

REM 2. 特定エージェントのみ（スタイルだけ、~8分）
python src/qa_checker.py episodes/001_erdos/scene_definition.json --agents style

REM 3. Gemini Grounding FactChecker（Web検索付き、~1分）
python src/qa_checker.py episodes/001_erdos/scene_definition.json --agents fact --use-gemini-fact

REM 4. フルQA + 自動修正（~75分）
python src/qa_checker.py episodes/001_erdos/scene_definition.json --auto-fix

REM 5. デバッグモード
python src/qa_checker.py episodes/001_erdos/scene_definition.json --agents style --debug
```

### 推奨テスト順序

1. まず `--agents style` でスタイルチェッカー単体を動作確認（~8分）
2. 次に `--agents fact --use-gemini-fact` でGemini Grounding版を確認（~1分）
3. `--quick` でSonnet 3エージェント一括（~25分）
4. 最後にフル実行（~75分）

---

## 5. ディレクトリ構造（QA追加後）

```
sugakushiki/
├── src/
│   ├── pipeline.py              ← QA統合追加
│   ├── script_generator.py      ← claude_backend.py 利用にリファクタ
│   ├── qa_checker.py            ★新規
│   ├── claude_backend.py        ★新規
│   ├── audio_generator.py
│   ├── subtitle_generator.py
│   ├── image_generator.py
│   ├── visual_generator.py
│   ├── video_assembler.py
│   └── manim_templates/
├── docs/
│   ├── QA_PIPELINE.md           ★新規
│   └── ... (既存)
├── episodes/
│   └── 001_erdos/
│       ├── scene_definition.json
│       ├── scene_definition.json.bak  ← auto-fix時のバックアップ
│       ├── qa_report_script.json      ← QAレポート
│       ├── qa_auto_fixes.json         ← 自動修正ログ
│       └── ... (既存)
```

---

## 6. Git commit案

```
P2-7: Multi-agent QA pipeline (Gate 1: Script QA)

New files:
- src/qa_checker.py: 5 agents (FactChecker, StyleChecker, SourceManager,
  ContentReviewer, ConsistencyChecker) with Opus/Sonnet backend selection
- src/claude_backend.py: Shared Claude Code -p utility (extracted from
  script_generator.py pattern, file I/O workaround for Windows)
- docs/QA_PIPELINE.md: Full 4-gate design document

Features:
- --quick mode (Sonnet agents only, ~25min)
- --auto-fix mode (safe style corrections applied to scene_definition.json)
- --use-gemini-fact (Gemini Grounding for web-search-enabled fact checking)
- --debug mode (show prompts and responses)
- JSON report output (qa_report_script.json)
- PASS/WARN/FAIL status with severity-based aggregation

Pipeline integration:
- pipeline.py: --qa and --qa-quick flags for post-script QA gate
```

---

## 7. Phase A 拡張: pronunciation_check 集積運用構造

audio_generator の pronunciation_check は誤読パターンの集積運用構造を持つ:

- **`_MISREADING_CATEGORIES` 辞書** (`audio_generator.py`): math_terms / compounds 等のカテゴリ別 misreading entries
- **`_convert_fractions()` regex 自動変換**: `(\d+)分の(\d+)` を kana 化 (1-20 範囲)
- **pronunciation_check Claude prompt**: 複合「値」/分数/否/数式ルール明示
- **`script_generator` narration_speech 生成 prompt**: 生成段階での同ルール適用
- **`formula_display._sanitize_subtitle()`**: 字幕の raw LaTeX strip + WARN

per-ep 個別対応 (narration_speech 個別書き換え) ではなく global 集積で誤読を予防する設計。詳細: `docs/03_quality/STYLE_GUIDE.md` の「数式音声化ルール」section、`docs/03_quality/pitfalls.md` の VOICEVOX section / 字幕 section。
