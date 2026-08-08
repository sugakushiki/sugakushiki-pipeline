"""stt_qa.py - Cloud TTS 読み検証ガード (Gemini STT ベース、advisory)。

VOICEVOX には audio_query による事前 kana 実測 (reading_guard.py) があるが、
Google Cloud TTS には kana を返す口が無いので発音を事前確認できない。その
代替として、合成済みの各シーン wav を Gemini STT で「実際に聞こえたとおり」
カタカナ書き起こしし、既知の Cloud 誤読パターンを照合して WARN する。

engine=cloud のビルドでのみ pipeline が呼ぶ (VOICEVOX ビルドは reading_guard)。

設計:
- advisory (既定 exit 0、--strict で WARN 時 exit 1)。reading_guard と同格。
- GOOGLE_API_KEY 無し / google-genai 未導入 は WARN で graceful degrade (build を
  止めない)。
- 自動ルールは取りこぼす。STT 自体も取りこぼす。よって書き起こし全文を report に残し、人手レビュー併用を
  前提にする (自動 WARN は「まず見るべき箇所」の提示)。

Usage:
    python scripts/stt_qa.py examples/moriarty/scene_definition.json
    python scripts/stt_qa.py examples/moriarty/scene_definition.json \
        --audio-dir examples/moriarty/audio --scenes math_03,math_04 --strict
"""

# Windows console は cp932。cp932 に無い文字 (em dash 等) を print すると
# UnicodeEncodeError でプロセスが死ぬ。ある回の再検証中に、追加した警告行の em dash で
# 実際にここが落ちた (しかも落ちるのは「検証できていない scene がある」という
# 警告経路だけ = 肝心なときだけ死ぬ)。出力の入口で一度だけ utf-8 に寄せておく。
import sys as _sys

if _sys.stdout.encoding and _sys.stdout.encoding.lower() != "utf-8":
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import json
import os
import re
import sys

# STT 書き起こし (カタカナ) に対する既知 Cloud 誤読ルール。
#   name  : ルール名
#   regex : STT カタカナ書き起こしに対する検出正規表現
#   note  : 意味と対処 (narration_speech_cloud を「わ」表記/カタカナ化 等)
# 追加時は実測で FP を確認してから足すこと (reading_guard の流儀)。
_STT_RULES = [
    {
        "name": "particle-ha-as-HA",
        # 直前がカタカナ (= 語に続く助詞位置) で、句読点/末尾直前の「ハ」。
        # 助詞「は」は「ワ」と発音されるべきなので、この位置の「ハ」は誤読候補。
        # 語中の「ハ」(ハルトークス等、後続が非句読点) は除外され FP を抑える。
        "regex": re.compile(r"[ァ-ヶー]ハ(?=[、。!?\s]|$)"),
        # misreading: unreliable in katakana-particle mode (Gemini renders は->ハ, を->ヲ,
        # です->デス as spelling, so EVERY topic は matches -> FP). Skipped there.
        "katakana_unreliable": True,
        "note": (
            "句末の助詞「は」が『ハ』と読まれている可能性 (正: ワ)。"
            "narration_speech_cloud で当該助詞を「わ」表記に変えて固定する。"
        ),
    },
    {
        "name": "particle-noha-as-NOHA",
        # 「のは」助詞連結が「ノハ」(正: ノワ)。closing/topic 文で頻出。
        "regex": re.compile(r"ノハ(?=[、。!?\s]|$)"),
        "katakana_unreliable": True,
        "note": (
            "『〜のは』の助詞「は」が『ノハ』と読まれている可能性 (正: ノワ)。"
            "narration_speech_cloud で「のわ」表記に固定する。"
        ),
    },
]


# narration の表層 -> (期待カタカナ, [誤読カタカナ...], note)。多読み漢字の
# 文脈依存誤読を、narration に surface があり STT に誤読カタカナが出た場合に
# WARN する。surface は誤読が起きる文脈に限定して
# FP を避ける (例: 「大学に入」= 入学 = はいる)。カタカナ照合は空白/句読点を
# 除去して行う (_norm_kana)。実測で FP を確認してから足すこと。
_READING_CHECKS = [
    (
        "大学に入",
        "ダイガクニハイレ",
        ["ダイガクニイレ"],
        "入=はいる(入学) が『いれ』化した恐れ。narration_speech_cloud で『はいれ』に固定",
    ),
    (
        "愛では",
        "アイデワ",
        ["メデワ", "メデ"],
        "愛=あい が動詞『愛でる(めで)』化した恐れ。『あいでは』に固定",
    ),
    ("の友", "ノトモ", ["ノユウ", "ノユー"], "友=とも(名詞) が『ゆう』化した恐れ。『とも』に固定"),
    (
        "私講師",
        "ノシコーシ",
        ["ワタクシコーシ", "ワタクシコウシ"],
        "私講師=しこうし の 私 が『わたくし』化した恐れ。『しこうし』に固定",
    ),
    (
        "正教授",
        "セイキョージュ",
        ["ショーキョージュ", "ショウキョージュ"],
        "正=せい が『しょう』化した恐れ。『せいきょうじゅ』に固定",
    ),
    (
        "を通って",
        "トオッテ",
        ["カヨッテ", "ツウジテ", "ツージテ"],
        "通=とおる が『かよう/つうじる』化した恐れ。『とおって』に固定",
    ),
    ("を通り", "トオリ", ["カヨイ"], "通=とおる が『かよう』化した恐れ。『とおり』に固定"),
    # 外 = そと/がい/はず の多読み (で surface)。読み自体は正しく出たが
    # 多読みの常連なので backstop。※ そ->ぞ の濁り(voicing)は STT が清音カタカナ(ソト)に
    # 書き起こすため、ここでは捕まらない = 耳 spot-check の領域。
    (
        "外から",
        "ソトカラ",
        ["ガイカラ", "ホカカラ"],
        "外=そと(外から) が がい/ほか 化した恐れ。『そとから』に固定",
    ),
    (
        "を外れ",
        "ハズレ",
        ["ガイレ", "ソトレ"],
        "外れ=はずれ が がい/そと 化した恐れ。『はずれ』に固定",
    ),
    (
        "外国",
        "ガイコク",
        ["ソトクニ", "ホカクニ", "ソトコク"],
        "外国=がいこく が そと/ほか 化した恐れ。『がいこく』に固定",
    ),
    # -
    #     合成前 advisory を、実 wav でも backstop する層 (決定打=実 wav STT)。---
    (
        "第九巻",
        "ダイキュウカン",
        ["ダイクカン", "ダイクカ"],
        "第九巻=だいきゅうかん の 九 が『く』化した恐れ。『だいきゅうかん』に固定",
    ),
    (
        "何ひとつ",
        "ナニヒトツ",
        ["トヒトツ"],
        "何ひとつ=なにひとつ の 何 が脱落し『とひとつ』化した恐れ。『なにひとつ』に固定",
    ),
    # -
    #     user が耳で見つけた**。同じ穴を次で開けないための backstop。---
    (
        "黒板",
        "コクバン",
        ["クロイタ"],
        "黒板=こくばん が『くろいた』化した恐れ。『こくばん』に固定",
    ),
    (
        "道路工夫",
        "コウフ",
        ["クフウ"],
        "工夫=こうふ(労働者) が『くふう』化した恐れ。『こうふ』に固定",
    ),
    (
        "へ行って",
        "イッテ",
        ["オコナッテ"],
        "行=いく が『おこなう』化した恐れ。『いって』に固定",
    ),
    (
        "に行って",
        "イッテ",
        ["オコナッテ"],
        "行=いく が『おこなう』化した恐れ。『いって』に固定",
    ),
    (
        "に通った",
        "カヨッタ",
        ["トオッタ"],
        "通=かよう が『とおる』化した恐れ。『かよった』に固定"
        " ※『筋の通った』は とおった が正しいので混同しないこと",
    ),
    (
        "塩水",
        "シオミズ",
        ["エンスイ"],
        "塩水=しおみず が『えんすい』化した恐れ。『しおみず』に固定",
    ),
]


def _norm_kana(s: str) -> str:
    """空白・句読点を除いたカタカナ列 (誤読照合用)。"""
    return re.sub(r"[\s　・、。!?！？]", "", s)


# 読みを検証できるのは、Gemini がそのシーンを *カタカナで* 書き起こしたときだけ。
# 漢字で書き起こされた行は「黒板」が コクバン なのか クロイタ なのか区別がつかない
# ので、その scene の読みは検証されていない。ある回では 23 scene 中 17 scene が
# 漢字書き起こしで、それでも stt_qa は「0 WARN」と表示していた (user が耳で 5 件検出)。
# 「指摘ゼロ」と「検査していない」を区別する。
_COVERAGE_FULL_MAX_KANJI = 0.05  # これ以下なら実質カタカナ書き起こし = 読み検証可
_COVERAGE_PARTIAL_MAX_KANJI = 0.20  # ここまでは混在 = 一部だけ検証可


def _reading_coverage(transcript: str) -> tuple[str, float]:
    """(判定ラベル, 漢字率) を返す。漢字率が高いほど読みは検証できていない。

    ある回実測で band はきれいに分離した (カタカナ書き起こし 0-8%、漢字書き起こし
    14-51%)。閾値はその谷に置いている。
    """
    body = re.sub(r"\s", "", transcript or "")
    if not body:
        return "empty", 0.0
    kanji = len(re.findall(r"[一-鿿]", body)) / len(body)
    if kanji <= _COVERAGE_FULL_MAX_KANJI:
        return "full", kanji
    if kanji <= _COVERAGE_PARTIAL_MAX_KANJI:
        return "partial", kanji
    return "none", kanji


def summarize_reading_coverage(coverage, reading_seen) -> list[str]:
    """報告行を組み立てて返す (print はしない)。

    「0 WARN」は「読みが正しい」ではなく「照合できた範囲で既知の誤読が出なかった」に
    すぎない。漢字で書き起こされた scene は読みを原理的に判定できないので、どれだけ
    検証できたのかを必ず一緒に出す。

    出力を関数に切り出してあるのは、**この経路自体をテストするため**。埋め込んだままだと
    分類関数だけ通しても出力が例外で落ちるか分からない (実際 em dash で落ちた)。
    """
    lines: list[str] = []
    if coverage:
        full = [s for s, lab, _ in coverage if lab == "full"]
        partial = [s for s, lab, _ in coverage if lab == "partial"]
        none = [s for s, lab, _ in coverage if lab in ("none", "empty")]
        lines.append(
            f"  読み検証カバレッジ: 検証可 {len(full)} / 一部 {len(partial)} / "
            f"検証不可 {len(none)}  (全 {len(coverage)} scene)"
        )
        if none:
            lines.append(
                "    [!] 次の scene は書き起こしが漢字のため読みを検証できていません"
                " -- 耳で確認してください:"
            )
            lines.append("        " + ", ".join(none))

    # 同じ語なのに scene によって読みが割れている型。片方だけ直っていると「1 件だけ WARN」に見えて全体の問題に気づけない。
    split = {s: v for s, v in (reading_seen or {}).items() if v["ok"] and v["ng"]}
    if split:
        lines.append("    [!] 同じ語の読みが scene 間で割れています (Chirp の非決定性):")
        for surface, v in split.items():
            lines.append(f"        {surface}: 正 {','.join(v['ok'])} / 誤 {','.join(v['ng'])}")
    return lines


def _is_katakana_mode(text: str) -> bool:
    """Gemini STT が助詞・活用をカタカナ化する「カタカナ助詞モード」か判定。

    このモードでは は->ハ, を->ヲ, です->デス, ます->マス が *綴り* として出るため、
    particle-は=ハ 検出が全 topic は に誤発火する。
    見分け: を の格助詞は通常ひらがな -> カタカナ「ヲ」があれば当モード。
            または カタカナ活用 デス/マス/デシタ/マシタ が複数。
    """
    if "ヲ" in text:
        return True
    kata_aux = text.count("デス") + text.count("マス") + text.count("デシタ") + text.count("マシタ")
    return kata_aux >= 2


def _load_gemini_key(env_path: str = ".env") -> str | None:
    """GOOGLE_API_KEY を環境変数 -> .env の順で解決。無ければ None。"""
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key.strip().strip('"').strip("'")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


_STT_PROMPT = (
    "この日本語音声を、実際に聞こえたとおりカタカナで正確に書き起こしてください。"
    "特に助詞「は」が『ハ』と『ワ』のどちらで発音されているか、"
    "固有名詞・専門用語の読み、不自然な区切りに注意してください。"
    "出力は書き起こし本文のみ。思考過程・注釈・タイムスタンプ・見出しは一切出力しないこと。"
)

# ---------------------------------------------------------------------------
# THINKING 漏れ対策: gemini-2.5-flash は thinking モデルで、上のプロンプトに反して
# 推論を答え本文に出す回がある (person_06 で ~100 行混入)。推論文中の「ハ」等が _READING
# corpus 照合を偽陽性化しうる。3 層で抑止する:
#   (1) thinking をオフ (thinking_budget=0)  -- 根本原因
#   (2) プロンプト強化 (上)                    -- 誘導
#   (3) 万一漏れた足場を _strip_reasoning で除去 -- backstop (本文は絶対に消さない設計)
# ---------------------------------------------------------------------------
_STT_CONFIG = None
_STT_CONFIG_TRIED = False


def _stt_config():
    """thinking を無効化した GenerateContentConfig を 1 度だけ構築 (キャッシュ)。SDK が
    ThinkingConfig 非対応なら None (graceful degrade -> プロンプト+strip で担保)。"""
    global _STT_CONFIG, _STT_CONFIG_TRIED
    if _STT_CONFIG_TRIED:
        return _STT_CONFIG
    _STT_CONFIG_TRIED = True
    try:
        from google.genai import types

        _STT_CONFIG = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    except Exception:
        _STT_CONFIG = None
    return _STT_CONFIG


# 足場行の判定 (いずれも数学史 narration には現れない構造 = 本文を巻き込まない):
_TS_PREFIX_RE = re.compile(
    r"^\s*\d{1,2}:\d{2}(?:\s*[-–—]\s*\d{1,2}:\d{2})?\s*"
)  # "0:00-0:04 " 前置
_ANNOT_LINE_RE = re.compile(r"^\s*[-*•]\s*[「『]")  # "- 「X」：説明" 注釈行
_META_LINE_RE = re.compile(
    r"^\s*(?:THINK|最終確認|再確認|再々確認|書き起こし(?:のみ|は|を)|音声を聞き取|一語ずつ)"
)


def _has_reasoning_leak(text: str) -> bool:
    """答え本文に推論足場が混入しているか (THINKING / タイムスタンプ行 / 注釈行)。"""
    if "THINK" in text.upper():
        return True
    lines = text.splitlines()
    return (
        sum(1 for ln in lines if _TS_PREFIX_RE.match(ln)) >= 2
        or sum(1 for ln in lines if _ANNOT_LINE_RE.match(ln)) >= 2
    )


def _strip_reasoning(text: str) -> str:
    """漏れた推論足場だけを除去する backstop。**書き起こし本文 (カタカナ/漢字) は絶対に
    消さない**: 除去対象は 先頭 THINKING ブロック / 注釈行 (箇条書き+「) / 特定メタ見出し /
    タイムスタンプ前置 のみで、いずれも narration には現れない構造。leak 未検出なら無変換で
    返す (通常の clean transcript は素通り)。除去し切って空になったら原文を返す (本文喪失回避)。"""
    if not text or not _has_reasoning_leak(text):
        return text
    lines = text.splitlines()
    # 先頭の THINKING 前置ブロック (THINK... 最初の空行まで) を落とす。
    if lines and re.match(r"^\s*THINK", lines[0], re.I):
        i = 1
        while i < len(lines) and lines[i].strip():
            i += 1
        lines = lines[i:]
    out = []
    for ln in lines:
        if _ANNOT_LINE_RE.match(ln) or _META_LINE_RE.match(ln):
            continue
        stripped = _TS_PREFIX_RE.sub("", ln).rstrip()
        if stripped:
            out.append(stripped)
    cleaned = "\n".join(out).strip()
    return cleaned if cleaned else text


def _transcribe(client, wav_path: str) -> str:
    """1 シーンの wav を Gemini STT でカタカナ書き起こし。thinking を無効化し、漏れた推論
    足場は _strip_reasoning で除去する。"""
    uploaded = client.files.upload(file=wav_path)
    kwargs = {"model": "gemini-2.5-flash", "contents": [uploaded, _STT_PROMPT]}
    cfg = _stt_config()
    if cfg is not None:
        kwargs["config"] = cfg
    try:
        resp = client.models.generate_content(**kwargs)
    except Exception:
        # thinking-disable config が API に拒否された等の場合は config 無しで再試行
        # (従来動作へ graceful degrade。プロンプト+strip は残る)。真のエラーは再送出。
        if "config" in kwargs:
            kwargs.pop("config")
            resp = client.models.generate_content(**kwargs)
        else:
            raise
    return _strip_reasoning((resp.text or "").strip())


def _iter_scenes(scene_def: dict):
    for section in scene_def.get("sections", []):
        yield from section.get("scenes", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Cloud TTS 読み検証 (Gemini STT、advisory)")
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument(
        "--audio-dir",
        default=None,
        help="Directory holding {scene_id}.wav (default: <scene_json dir>/audio)",
    )
    parser.add_argument(
        "--scenes",
        default=None,
        help="Comma-separated scene_ids to check (default: all)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path to write the full STT transcript report "
        "(default: <scene_json dir>/stt_qa_report.txt)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any WARN (default: advisory exit 0)",
    )
    args = parser.parse_args()

    scene_dir = os.path.dirname(os.path.abspath(args.scene_json))
    audio_dir = args.audio_dir or os.path.join(scene_dir, "audio")
    report_path = args.report or os.path.join(scene_dir, "stt_qa_report.txt")

    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)

    only = set(args.scenes.split(",")) if args.scenes else None

    # graceful degrade: key or SDK 無しは WARN で通過 (build を止めない)
    key = _load_gemini_key()
    if key is None:
        print("[STT-QA] SKIP: GOOGLE_API_KEY not found (STT read-check skipped).")
        print("  Cloud audio ships WITHOUT automated read verification -- review by ear.")
        return 0
    try:
        from google import genai
    except ImportError:
        print("[STT-QA] SKIP: google-genai not installed (STT read-check skipped).")
        return 0

    client = genai.Client(api_key=key)

    print("=" * 60)
    print("  STT QA (Cloud TTS read verification)")
    print("=" * 60)

    warnings = []
    report_lines = []
    n_checked = 0
    n_missing = 0
    coverage = []  # (sid, label, kanji_ratio) — 読みを検証できた scene の割合を出すため
    # surface -> {"ok": [sid...], "ng": [sid...]}。同じ語が scene 間で読みが割れる型を拾う。
    reading_seen = {}

    for scene in _iter_scenes(scene_def):
        sid = scene.get("scene_id", "?")
        if only is not None and sid not in only:
            continue
        wav = os.path.join(audio_dir, f"{sid}.wav")
        if not os.path.exists(wav):
            n_missing += 1
            print(f"  [SKIP] {sid}: wav not found ({wav})")
            continue

        try:
            transcript = _transcribe(client, wav)
        except Exception as e:  # noqa: BLE001 - STT failure is advisory, never fatal
            print(f"  [SKIP] {sid}: STT failed ({e!r})")
            continue

        n_checked += 1
        report_lines.append(f"===== {sid} =====\n{transcript}")

        scene_hits = []
        km = _is_katakana_mode(transcript)
        for rule in _STT_RULES:
            if rule.get("katakana_unreliable") and km:
                continue  # misreading: skip particle-は=ハ in katakana-particle mode (FP)
            for m in rule["regex"].finditer(transcript):
                s = max(0, m.start() - 6)
                e = min(len(transcript), m.end() + 6)
                ctx = transcript[s:e]
                scene_hits.append((rule["name"], ctx, rule["note"]))

        # 多読み漢字の文脈依存誤読: narration に surface があり、STT に誤読カタカナ
        # が出て (かつ正しい読みが出ていない) なら WARN。narration は漢字で照合、
        # 誤読は空白除去したカタカナ列で照合する。
        narr_text = " ".join(scene.get("narration", []) or []).replace("|", "")
        t_norm = _norm_kana(transcript)
        for surface, correct, wrongs, note in _READING_CHECKS:
            if surface not in narr_text:
                continue
            hit = [w for w in wrongs if w in t_norm]
            if hit and correct not in t_norm:
                scene_hits.append(
                    (f"misread:{surface}", f"STT={','.join(hit)} (expect {correct})", note)
                )
                reading_seen.setdefault(surface, {"ok": [], "ng": []})["ng"].append(sid)
            elif correct in t_norm:
                reading_seen.setdefault(surface, {"ok": [], "ng": []})["ok"].append(sid)

        label, kanji_ratio = _reading_coverage(transcript)
        coverage.append((sid, label, kanji_ratio))
        mark = {"full": "", "partial": "  [読み一部のみ検証可]", "none": "  [読み検証不可]"}.get(
            label, "  [書き起こし空]"
        )

        if scene_hits:
            print(f"  [WARN] {sid}: {len(scene_hits)} suspicious reading(s){mark}")
            for name, ctx, note in scene_hits:
                print(f"      - {name}: ...{ctx}...")
                print(f"        {note}")
                warnings.append((sid, name, ctx))
        else:
            print(f"  [OK]   {sid}{mark}")

    # 書き起こし全文を report に保存 (人手レビュー用)
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(report_lines))
        print(f"\n  Transcript report: {report_path}")
    except OSError as e:
        print(f"\n  [WARN] could not write report: {e}")

    print(f"\n  Checked {n_checked} scene(s), {len(warnings)} WARN, {n_missing} missing wav.")

    # 「0 WARN」は「読みが正しい」ではなく「照合できた範囲で既知の誤読が出なかった」に
    # すぎない。Gemini が漢字で書き起こした scene では読みが原理的に判定できないので、
    # どれだけ検証できたのかを必ず一緒に出す。
    for line in summarize_reading_coverage(coverage, reading_seen):
        print(line)

    print("  NOTE: STT can miss too -- always spot-check Cloud audio by ear before publishing.")

    if warnings:
        try:
            _src = os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
            )
            if _src not in sys.path:
                sys.path.insert(0, _src)
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("stt_qa", len(warnings))
        except Exception:
            pass

    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
