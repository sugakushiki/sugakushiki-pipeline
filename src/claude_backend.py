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
import re
import tempfile
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


# ---------------------------------------------------------------------------
# ある回: Claude の利用上限 (usage limit)
#
# ある回の Gate 2 でセッション上限に当たり、画像 QA が「全 scene 失敗」で abort した。
# の probe は 401 (失効) しか見ないので、上限の応答は「QA が壊れた」ように見え、
# 切り分けに一往復かかった。上限の応答には再開時刻が書いてある
# ("You've hit your session limit · resets 9:30pm (Asia/Tokyo)") ので、
#   1. 応答を分類して「利用上限。resets HH:MM」と名指しする (classify_usage_limit)
#   2. どの呼び出し経路 (call_claude / 6 本の `claude -p --output-format text` wrapper) で
#      当たっても project root に sentinel (_claude_usage_limit.json) を書く
#   3. pipeline は子プロセスが返るたびに sentinel を見て、その場で止める
#      (残りの Claude 依存ステップを回して時間を捨てない。再開は --steps で続きから)
# 判定は失敗経路 (is_error / 非ゼロ終了 / 空出力) に限る。成功応答の本文に「rate limit」
# のような語が出ても sentinel を書かない (偽の abort を避ける)。
# ---------------------------------------------------------------------------

_LIMIT_MARKERS = (
    "hit your session limit",
    "hit your weekly limit",
    "hit your limit",
    "usage limit reached",
    "usage limit",
    "limit reached",
    "rate limit",
    "too many requests",
)
_RESET_RE = re.compile(
    r"resets?\s+(?:at\s+)?([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?(?:\s*\([^)]{1,40}\))?)",
    re.IGNORECASE,
)
USAGE_LIMIT_SENTINEL = "_claude_usage_limit.json"


class ClaudeUsageLimitError(RuntimeError):
    """Claude の利用上限に当たった (再開時刻は .resets)。"""

    def __init__(self, message: str, resets: str | None = None, context: str | None = None):
        super().__init__(message)
        self.resets = resets
        self.context = context


def classify_usage_limit(text: str | None) -> dict | None:
    """利用上限の応答なら {"resets", "snippet"} を返す。違えば None。純関数。"""
    raw = text or ""
    low = raw.lower()
    if not any(m in low for m in _LIMIT_MARKERS):
        return None
    m = _RESET_RE.search(raw)
    return {"resets": m.group(1).strip() if m else None, "snippet": raw.strip()[:200]}


def usage_limit_message(info: dict | None) -> str:
    resets = (info or {}).get("resets")
    tail = f" (resets {resets})" if resets else ""
    return f"Claude の利用上限に当たりました{tail}。上限が戻ってから同じコマンドを --steps で続きから再開してください"


def _sentinel_path(project_root=None) -> Path:
    root = Path(project_root) if project_root else find_project_root()
    return Path(root) / USAGE_LIMIT_SENTINEL


def note_usage_limit(context: str, info: dict, project_root=None) -> Path:
    """sentinel を書く (pipeline が読んで止まる)。"""
    path = _sentinel_path(project_root)
    payload = {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "context": context,
        "resets": (info or {}).get("resets"),
        "snippet": (info or {}).get("snippet", ""),
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:  # 書けなくても呼び出し側の例外は立つ
        print(f"  [!] usage-limit sentinel を書けませんでした: {e}")
    return path


def read_usage_limit(project_root=None) -> dict | None:
    path = _sentinel_path(project_root)
    if not path.exists():
        return None
    try:
        # utf-8-sig: 手で置いた sentinel (PowerShell の Set-Content は BOM 付き) も読める
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"context": "?", "resets": None, "snippet": "(sentinel unreadable)"}


def clear_usage_limit(project_root=None) -> None:
    path = _sentinel_path(project_root)
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        print(f"  [!] usage-limit sentinel を消せませんでした: {e}")


def note_usage_limit_from_files(
    output_path, error_path, context: str, exit_code: int = 1, project_root=None
) -> dict | None:
    """`claude -p --output-format text > out 2> err` 型の wrapper 用。

    失敗経路 (非ゼロ終了、または短い出力) のときだけ out/err を読んで分類し、
    上限なら sentinel を書いて名指しする。成功した長い応答は見ない (偽陽性回避)。
    """
    texts = []
    for pth in (output_path, error_path):
        try:
            if pth and os.path.exists(pth):
                texts.append(open(pth, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
    combined = "\n".join(texts)
    if exit_code == 0 and len(combined.strip()) > 300:
        return None
    info = classify_usage_limit(combined)
    if not info:
        return None
    note_usage_limit(context, info, project_root)
    print(f"  [!] [USAGE-LIMIT] {usage_limit_message(info)} ({context})")
    return info


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
      "usage_limit"-- non-healthy AND output says the usage/session limit was hit
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
    _lim = classify_usage_limit(out + " " + (stderr or ""))
    if _lim:
        return False, "usage_limit", f"{usage_limit_message(_lim)}: {snippet}"
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

        # ある回: 利用上限は失敗経路 (is_error / 本文なし) でだけ判定し、sentinel を書いて
        # 専用の例外で上げる (呼び出し側の graceful degrade に埋もれても pipeline が止まれる)
        _lim_text = ""
        if result_event and result_event.get("is_error"):
            _lim_text = str(result_event.get("result", ""))
        if not full_text:
            _lim_text += " " + raw_text[:2000]
        _lim = classify_usage_limit(_lim_text) if _lim_text.strip() else None
        if _lim:
            note_usage_limit(f"call_claude:{prefix}", _lim, root)
            raise ClaudeUsageLimitError(
                f"{usage_limit_message(_lim)}: {_lim['snippet']}",
                resets=_lim.get("resets"),
                context=prefix,
            )

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


# ---------------------------------------------------------------------------
# JSON extraction from LLM responses
#
# Every QA agent answers with one JSON object inside a ```json fence. Two
# failure shapes were observed in real transcripts and are handled here, in
# order of least intervention:
#
#   1. Self-restart: Claude writes a broken block, says "starting fresh" and
#      writes a second, complete block. A non-greedy regex grabbed the first
#      (broken) block. Fix: enumerate ALL ```json blocks, try the LAST first.
#      (script_generator.extract_json learned this first; ported here so the
#      QA path has the same robustness.)
#   2. Stray inner quotes: a long free-text string value (a formatted
#      reference list with "Title" quoting) where the model escapes most inner
#      quotes as \" but leaves a few raw. json.loads fails mid-string with
#      "Expecting ',' delimiter". Seen twice in a row on the SourceManager
#      agent: two ~7000-char responses, both COMPLETE (stop_reason=end_turn,
#      one text block) -- not truncation. Fix: repair_json_text() re-escapes a
#      quote that cannot be a terminator, judged by what follows it.
#
# Raw control characters (newline / tab) inside strings are the third common
# LLM defect: strict=False accepts them and the repair pass escapes them.
#
# On total failure the ValueError names the first parse error's position and
# surrounding text. "length=6997" alone was undiagnosable and the raw response
# had to be dug out of the nested CLI's transcript after the fact.
# ---------------------------------------------------------------------------

_JSON_VALUE_START = '"{[-0123456789tfn'
_JSON_WS = " \t\r\n"


def _quote_is_terminator(text: str, j: int) -> bool:
    """Decide whether the '"' just before index j closes a JSON string.

    A real closing quote is followed (after whitespace) by ':' (it was a key),
    '}' / ']' (last member), end of text, or ',' plus the start of the next
    member. A following '"' is ambiguous (missing comma vs. prose) and is
    deliberately treated as a terminator so a structural defect still fails
    loudly instead of being merged into one string. Anything else -- a letter,
    '(', '、', '所' ... -- means the quote sits inside prose and must be escaped.
    """
    n = len(text)
    while j < n and text[j] in _JSON_WS:
        j += 1
    if j >= n:
        return True
    c = text[j]
    if c in ':}]"':
        return True
    if c == ",":
        k = j + 1
        while k < n and text[k] in _JSON_WS:
            k += 1
        return k >= n or text[k] in _JSON_VALUE_START
    return False


def repair_json_text(text: str) -> str:
    """Escape stray inner double quotes and raw control characters inside JSON strings.

    Walks the text tracking string state. Outside strings nothing is touched.
    Inside a string an unescaped '"' that cannot be a terminator (see
    _quote_is_terminator) becomes '\\"', and raw newline / tab become '\\n' /
    '\\t'. Existing escape pairs are copied verbatim, so well-formed JSON passes
    through unchanged (asserted by).

    Limitation: an inner quote followed by ', "' / '"' / '}' looks like a
    terminator and is left alone. The candidate then either still fails to parse
    (the caller raises as before) or parses with that quote closing the string
    early -- e.g. {"a": "foo "bar", "b": "c"} becomes {"a": "foo \"bar", "b": "c"},
    the trailing inner quote dropped (probed in an earlier episode re-verification). Members
    are never silently merged into one string, so a structural defect (missing
    comma) still fails loudly.
    """
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        ch = text[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "\\":
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == '"':
            if _quote_is_terminator(text, i + 1):
                in_str = False
                out.append(ch)
            else:
                out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            pass
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _json_candidates(text: str) -> list:
    """Substrings that might be the JSON object, most likely first, de-duplicated."""
    cands = []

    # 1. every ```json block, LAST first (a later self-restart supersedes)
    fences = [m.start() for m in re.finditer(r"```", text)]
    blocks = []
    for m in re.finditer(r"```json", text):
        body_start = m.end()
        nxt = next((p for p in fences if p > body_start), None)
        body = text[body_start : nxt if nxt is not None else len(text)].strip()
        if body:
            blocks.append(body)
    cands.extend(reversed(blocks))

    # 2. generic fenced blocks holding an object
    for m in re.finditer(r"```[\w-]*\s*(\{.*?\})\s*```", text, re.DOTALL):
        cands.append(m.group(1).strip())

    # 3. outermost { ... } of the whole text: covers un-fenced output and a
    #    fence that a stray ``` inside a string value cut short
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        cands.append(text[first : last + 1])

    seen, unique = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _parse_json_object(body: str) -> tuple:
    """(obj or None, first error). Tries strict, lenient (control chars), then repaired."""
    first_error = None
    attempts = ((body, True), (body, False))
    for stage in range(3):
        if stage < 2:
            txt, strict = attempts[stage]
        else:
            txt, strict = repair_json_text(body), False
        try:
            obj = json.loads(txt, strict=strict)
        except json.JSONDecodeError as e:
            if first_error is None:
                first_error = e
            continue
        if isinstance(obj, dict):
            return obj, first_error
        if first_error is None:
            first_error = ValueError(f"top-level JSON is {type(obj).__name__}, not an object")
    return None, first_error


def _describe_error(body: str, err: Exception) -> str:
    if isinstance(err, json.JSONDecodeError):
        ctx = body[max(0, err.pos - 80) : err.pos + 80]
        return f"{err.msg} at char {err.pos} (line {err.lineno} col {err.colno}); context: {ctx!r}"
    return str(err)


def extract_json_from_response(text: str) -> dict:
    """Claude Code レスポンスから JSON オブジェクトを抽出する。

    候補は ```json ブロック (複数あれば後のものを優先) → 汎用 ``` ブロック →
    最初の { から最後の } の順。各候補を strict → 制御文字許容 →
    repair_json_text() で修復、の順に parse する。全滅なら最初の候補の parse
    エラー位置と前後の文脈を含む ValueError を投げる。
    """
    text = text.replace("\r\n", "\n")
    candidates = _json_candidates(text)
    first_desc = None
    for body in candidates:
        obj, err = _parse_json_object(body)
        if obj is not None:
            return obj
        if first_desc is None and err is not None:
            first_desc = _describe_error(body, err)
    detail = f"; first error: {first_desc}" if first_desc else "; no JSON object found"
    raise ValueError(
        f"Could not extract valid JSON from response "
        f"(length={len(text)}, candidates={len(candidates)}{detail})"
    )


def try_extract_json(text: str | None) -> dict | None:
    """extract_json_from_response の「失敗したら None」版 (, 2026-09-19)。

    qa_image_checker / qa_thumbnail_vision / manim_vision_qa が各自に持っていた `_extract_json`
    (最初の ```json ブロックだけを見る、修復なし) の置き換え。こちらは複数ブロックの後方優先・
    制御文字許容・repair_json_text まで通るので、旧実装で拾えたものは全部拾う。
    """
    if not text:
        return None
    try:
        return extract_json_from_response(text)
    except ValueError:
        return None


def call_claude_text(
    prompt: str,
    *,
    context: str,
    prefix: str = "txt",
    allowed_tools: str | None = "Read,Bash",
    debug: bool = False,
) -> str | None:
    """`claude -p --output-format text` の共通 wrapper (, 2026-09-19)。

    qa_image_checker / qa_thumbnail_vision / manim_vision_qa / image_generator (vision) /
    wikimedia_fetcher (外見) / check_image_signatures の 6 本が同じ 50 行 (temp ファイル経由の
    os.system、利用上限 sentinel、後片付け) を各自に持っていた。違いは temp ファイルの接頭辞と
    `--allowedTools Read,Bash` の有無だけで、後者は CLAUDE.md が「v2.1.63 以降必須」と書くのに
    3 本が付けていなかった。ここに寄せる。

    Windows では subprocess を使わない (日本語クラッシュ)。os.system + temp ファイル方式。
    失敗 (非ゼロ終了 / 出力なし / 例外) は None。利用上限は note_usage_limit_from_files が
    sentinel に書き、pipeline が次の子プロセス境界で止まる。
    """
    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, f"_tmp_{prefix}_prompt.txt")
    output_path = os.path.join(tmp_dir, f"_tmp_{prefix}_output.txt")
    error_path = os.path.join(tmp_dir, f"_tmp_{prefix}_error.txt")
    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(prompt)
        for p in (output_path, error_path):
            if os.path.exists(p):
                os.remove(p)
        tools = f"--allowedTools {allowed_tools} " if allowed_tools else ""
        cmd = (
            f'type "{prompt_path}" | claude -p --output-format text {tools}'
            f'> "{output_path}" 2> "{error_path}"'
        )
        if debug:
            print(f"    [DEBUG] Prompt: {len(prompt)} chars")
            print(f"    [DEBUG] Command: {cmd[:120]}...")
        exit_code = os.system(cmd)
        try:
            note_usage_limit_from_files(output_path, error_path, context, exit_code)
        except Exception as _e:  # noqa: BLE001 - never let the guard break the caller
            print(f"    [!] usage-limit guard skipped: {_e}")
        if exit_code != 0:
            if debug and os.path.exists(error_path):
                with open(error_path, encoding="utf-8", errors="replace") as f:
                    print(f"    [DEBUG] stderr: {f.read().strip()[:200]}")
            return None
        if not os.path.exists(output_path):
            return None
        with open(output_path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except Exception as e:  # noqa: BLE001 - caller degrades gracefully on None
        if debug:
            print(f"    [DEBUG] call_claude_text error: {e}")
        return None
    finally:
        for p in (prompt_path, output_path, error_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
