"""
claude_backend.py — Claude Code `-p` 共通呼び出しユーティリティ

script_generator.py と qa_checker.py で共通利用。
Windows環境の制約（stdinパイプ不可）をファイルI/Oで回避する。

使い方:
    from claude_backend import call_claude

    result = call_claude(
        prompt="あなたの指示...",
        model="opus",        # "opus" or "sonnet"
        debug=False,
        project_root=None,   # 自動検出
    )
"""

import json
import os
import time
from pathlib import Path

# モデルマッピング
# 重要: None を渡すと --model フラグなしとなり、CLI のデフォルト（Sonnet）になる。
# Opus を使いたい場合は明示的に "claude-opus-4-6" を指定すること。
# Opus の max_output_tokens = 64000 (Sonnet の 32000 の2倍)
CLAUDE_MODEL_MAP = {
    "opus": "claude-opus-4-6",  # 明示指定（max_output=64K）
    "claude": "claude-opus-4-6",  # デフォルトをOpusに
    "claude-opus": "claude-opus-4-6",  # 同上
    "sonnet": "claude-sonnet-4-6",  # max_output=32K
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-sonnet-4.5": "claude-sonnet-4-5-20250929",
}


def find_project_root(start_path: str = None) -> Path:
    """プロジェクトルートを検出（.git or src/ の存在で判定）"""
    if start_path:
        p = Path(start_path)
    else:
        p = Path(__file__).resolve().parent  # src/

    # src/ 内にいる場合は一つ上がプロジェクトルート
    if p.name == "src":
        return p.parent

    # .git を探す
    current = p
    for _ in range(5):
        if (current / ".git").exists():
            return current
        if (current / "src").exists():
            return current
        current = current.parent

    return p


# ---------------------------------------------------------------------------
# Claude CLI auth probe (long-build OAuth-expiry early detection)
#
# On a long build the logged-in OAuth session can expire mid-run. Every
# subsequent `claude -p` call then fails, but each caller degrades gracefully
# (call_claude raises -> qa_checker / manim_vision_qa / intro_semantic return
# None/UNAVAILABLE), so the whole QA layer fails SILENTLY and the build still
# finishes "green". This probe pings the CLI so an expired token is caught
# fail-fast with an actionable "re-authenticate and resume" message instead of
# a buried cascade of per-scene "Claude returned no output" errors.
#
# Design: the OK/NOT-OK decision rests on a POSITIVE signal (a healthy ping
# echoes 'pong'), NOT on matching a specific 401 string -- so it stays robust
# even if the exact auth-failure text changes. When NOT OK, the output is
# classified (auth / timeout / not_found / unexpected) only to sharpen the
# message. classify_claude_ping is a pure function so it is unit-testable
# without reproducing a real token expiry.
# ---------------------------------------------------------------------------

# Auth-failure substrings (lowercased). Presence only sharpens the message; the
# ok decision is the positive 'pong' signal above, so a stray match here cannot
# cause a false OK. 'credit balance' is NOT auth (out-of-credit) -> excluded.
_AUTH_MARKERS = (
    "401",
    "403",
    "authenticat",  # authentication / authenticate
    "unauthor",  # unauthorized / unauthorised
    "invalid api key",
    "oauth",
    "not logged in",
    "please log in",
    "please run",  # "please run `claude login`" / setup-token
    "setup-token",
    "token expired",
    "token has expired",
    "session expired",
    "re-authenticate",
    "reauthenticate",
)


def classify_claude_ping(
    returncode,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
    not_found: bool = False,
    timeout_sec: int = 25,
) -> tuple[bool, str, str]:
    """Classify a `claude -p` ping outcome. Pure (no I/O) so it is unit-testable.

    Returns (ok, reason, message) where reason is one of:
      "ok"         -- healthy (ping echoed 'pong')
      "not_found"  -- 'claude' command not in PATH
      "timeout"    -- ping did not return within timeout_sec
      "auth"       -- non-healthy AND output carries an auth-failure signature
      "unexpected" -- non-healthy with no recognizable auth signature (CLI
                      malfunction / crash / model access / unknown)

    The ok decision is the POSITIVE 'pong' signal, not string-matching, so a
    changed 401 message can never yield a false OK.
    """
    if not_found:
        return False, "not_found", "Claude CLI ('claude' command) not found in PATH"
    if timed_out:
        return False, "timeout", f"Claude CLI ping timed out after {timeout_sec}s"

    out = stdout or ""
    combined = (out + " " + (stderr or "")).lower()

    # Positive signal: a healthy ping returns 0 and echoes 'pong'.
    if returncode == 0 and "pong" in out.lower():
        return True, "ok", "OK"

    snippet = combined.strip()[:300]
    if any(m in combined for m in _AUTH_MARKERS):
        return (
            False,
            "auth",
            f"Claude CLI authentication failed (token likely expired / not logged in): {snippet}",
        )
    if returncode not in (0, None):
        return False, "unexpected", f"Claude CLI non-zero exit ({returncode}): {snippet}"
    return False, "unexpected", f"Claude CLI unexpected response (no 'pong'): {snippet}"


def probe_claude_cli(
    timeout_sec: int = 25, model: str = "claude-opus-4-6"
) -> tuple[bool, str, str]:
    """Ping the Claude CLI with a trivial ASCII prompt; return (ok, reason, message).

    Uses subprocess (capture_output for returncode + stderr diagnostics). The
    Windows 'subprocess 禁止' rule targets Japanese-text crashes; this ASCII-only
    ping is unaffected. Cost ~8-20s healthy, faster on 401. Faithful to the real
    call path in the only dimension that matters for auth: it exercises the same
    logged-in `claude -p` session.
    """
    import subprocess

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format",
                "text",
                "--allowedTools",
                "Read",
                "--model",
                model,
                "reply exactly with the word pong",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return classify_claude_ping(None, "", "", timed_out=True, timeout_sec=timeout_sec)
    except FileNotFoundError:
        return classify_claude_ping(None, "", "", not_found=True, timeout_sec=timeout_sec)

    return classify_claude_ping(
        result.returncode, result.stdout, result.stderr, timeout_sec=timeout_sec
    )


def _parse_stream_json_output(raw_text: str, debug: bool = False) -> tuple:
    """
    Claude CLI の stream-json 出力を解析し、全 assistant テキストブロックを連結する。

    stream-json 形式は1行1イベント:
        {"type":"system","subtype":"init",...}
        {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}
        {"type":"user","message":{...tool_result...}}
        {"type":"assistant",...}  (複数ターン可能性あり)
        {"type":"result","is_error":false,"result":"...","stop_reason":"..."}

    Claude CLI が応答を複数ターンに分割した場合（32K/64K トークン上限近辺）、
    最終assistantメッセージだけでなく全ての assistant テキストを連結することで
    完全な応答を復元する。

    Returns:
        (full_text, result_event)
        full_text: 全assistantテキストブロックを連結した文字列
        result_event: result イベントの dict（存在すれば）、なければ None
    """
    assistant_texts = []
    result_event = None
    parse_errors = 0
    total_lines = 0
    skipped_blank = 0

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            skipped_blank += 1
            continue
        total_lines += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue

        event_type = obj.get("type")

        if event_type == "assistant":
            message = obj.get("message", {}) or {}
            content = message.get("content", []) or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "") or ""
                    if text:
                        assistant_texts.append(text)

        elif event_type == "result":
            result_event = obj

    full_text = "".join(assistant_texts)

    if debug:
        print(
            f"[DEBUG] stream-json parse: {total_lines} lines, "
            f"{parse_errors} parse errors, "
            f"{len(assistant_texts)} assistant text blocks, "
            f"full_text length = {len(full_text)}"
        )
        if result_event:
            print(
                f"[DEBUG] result: is_error={result_event.get('is_error')}, "
                f"stop_reason={result_event.get('stop_reason')}, "
                f"num_turns={result_event.get('num_turns')}"
            )

    return full_text, result_event


def call_claude(
    prompt: str,
    model: str = "opus",
    debug: bool = False,
    project_root: str = None,
    timeout_minutes: int = 40,
    prefix: str = "qa",
    allowed_tools: str = "Read,Bash",
) -> str:
    """
    Claude Code `-p` をファイルI/O経由で呼び出す。

    stream-json フォーマットで出力を受け取り、全 assistant テキストブロックを
    連結して返す。これにより Claude が max_output_tokens 上限で応答を複数ターンに
    分割した場合でも、完全な応答を復元できる。

    Args:
        prompt: プロンプト文字列
        model: "opus" (default) or "sonnet"
        debug: True でプロンプトとレスポンスを表示
        project_root: プロジェクトルートパス（None で自動検出）
        timeout_minutes: タイムアウト（分）
        prefix: 一時ファイルのプレフィックス（"qa", "script" 等）
        allowed_tools: Claude CLI に許可するツール（デフォルト "Read,Bash"）。
            長文 JSON 生成では "Read" のみに絞ると、Opus が Bash で回避
            しようとして内容を失う問題を防げる（過去のケースで判明）。

    Returns:
        Claude Code のテキスト出力（全assistantメッセージ連結済み）

    Raises:
        RuntimeError: Claude Code 実行失敗時、または result イベントが is_error
    """
    root = Path(project_root) if project_root else find_project_root()

    # 一時ファイルパス（プロジェクトルート内 = Claude Code の権限内）
    prompt_file = root / f"_tmp_{prefix}_prompt.txt"
    output_file = root / f"_tmp_{prefix}_output.txt"

    try:
        # 1. プロンプトをファイルに書き出し
        prompt_file.write_text(prompt, encoding="utf-8")

        if debug:
            print(f"\n{'=' * 60}")
            print(f"[DEBUG] Model: {model}")
            print(f"[DEBUG] Prompt length: {len(prompt)} chars")
            print(f"[DEBUG] Prompt file: {prompt_file}")
            print(f"{'=' * 60}\n")

        # 2. Claude Code コマンド組み立て
        model_flag = ""
        model_id = CLAUDE_MODEL_MAP.get(model)
        if model_id:
            model_flag = f' --model "{model_id}"'

        # ファイル読み取り指示をコマンドライン引数として渡す
        # ★重要: Opusはエージェント的に振る舞うため、明確に制約する
        cmd_prompt = (
            f"_tmp_{prefix}_prompt.txt を読んでください。"
            f"そのファイルの指示に従い、結果をテキストとして標準出力に出力してください。"
            f"絶対にファイルの作成・書き込みをしないでください。"
            f"Bashツールやその他のツールを使わず、必ず assistant の text ブロックに"
            f"直接出力してください。Claude CLI の stream-json は複数ターンに"
            f"分割された応答を自動連結するため、長さを心配せず通常のテキストとして"
            f"書き続けてください。"
            f"出力を分割せず、1回のレスポンスで完全なJSONを出力してください。"
            f"ファイル書き込み許可を求めないでください。"
        )

        # stream-json 形式で出力を受け取る（--verbose は stream-json 要件）
        # これにより複数ターン応答（max_output_tokens 上限分割）でも完全復元可能
        cmd = (
            f'cd /d "{root}" && '
            f'claude -p "{cmd_prompt}"{model_flag} '
            f"--allowedTools {allowed_tools} "
            f'--output-format stream-json --verbose > "{output_file}" 2>nul'
        )

        if debug:
            print(f"[DEBUG] Command: {cmd[:200]}...")

        # 3. 実行
        start_time = time.time()
        print(f"  Claude Code ({model}) を実行中...")

        os.system(cmd)

        elapsed = time.time() - start_time
        print(f"  完了 ({elapsed:.1f}秒 / {elapsed / 60:.1f}分)")

        # 4. 出力ファイル読み取り
        if not output_file.exists():
            raise RuntimeError(f"Claude Code output file not found: {output_file}")

        raw_text = output_file.read_text(encoding="utf-8")

        if not raw_text.strip():
            raise RuntimeError("Claude Code returned empty output")

        # 5. stream-json パースして全 assistant テキストを連結
        full_text, result_event = _parse_stream_json_output(raw_text, debug=debug)

        # 6. エラーチェック
        if result_event and result_event.get("is_error"):
            err_msg = result_event.get("result", "unknown error")
            raise RuntimeError(
                f"Claude Code returned error (stop_reason={result_event.get('stop_reason')}): {err_msg}"
            )

        # 7. フォールバック: assistant テキストが空なら result の result フィールドを使う
        if not full_text:
            if result_event and result_event.get("result"):
                full_text = result_event["result"]
                if debug:
                    print("[DEBUG] Falling back to result.result field")
            else:
                # デバッグ用に raw_text の先頭を残して詳細エラー
                head = raw_text[:500].replace("\n", " ")
                raise RuntimeError(
                    f"No assistant text blocks found in stream-json output. Raw head: {head!r}"
                )

        result = full_text.strip()

        if debug:
            print(f"\n[DEBUG] Response length: {len(result)} chars")
            print(f"[DEBUG] First 500 chars:\n{result[:500]}\n")

        return result

    finally:
        # 8. 一時ファイル削除
        for f in [prompt_file, output_file]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def extract_json_from_response(text: str) -> dict:
    """
    Claude Code レスポンスからJSONを抽出する。
    コードブロック内のJSON、または直接のJSONを検出。
    """
    import re

    # 改行コード正規化
    text = text.replace("\r\n", "\n")

    # パターン1: ```json ... ```
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(\{.*?\})\n\s*```",
        r"```json\s*(.*?)\s*```",
        r"```\s*(\{.*?\})\s*```",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    # パターン2: 直接JSON（最初の { から最後の } まで）
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response (length={len(text)})")
