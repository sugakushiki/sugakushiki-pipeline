"""kana_reading_diff.py - 文単位の「期待した読み」と「実際に読まれた読み」の差分。

これまでの読み検証は **「指定した読みが書き起こしに含まれるか」** しか見ていなかった。
だから (1) 読みを指定していない語の誤読は原理的に見えず、(2) 書き起こしが漢字で返ると
「検証不可」になり、(3) 別の読みで通っても黙る。ある回では 魚市場/食う者/人街/種/獲る/型 の
6 語が lint・出荷物 STT・文単位 STT の全層を抜けて user の耳に届いた。

ここでは語を指定せず、文ごとに二つのかなを突き合わせる:

  期待  : Gemini (テキスト) に narration_speech_cloud を「発音どおりカタカナで」書かせる
          (cloud 文は読みのかな直書きを含むので、固定した読みがそのまま期待になる)
  実際  : Gemini (STT) に文 wav を「**すべてカタカナだけ**で」書き起こさせる
          (漢字で返ったら最大 3 回かけ直す。ある回の実測ではこの指示で 21/21 文が かな で返った)

両者を正規化 (長音統一・空白除去) して difflib で並べ、食い違う区間を名指しする。
数字の読み (センハッピャク vs 千八百) や長音 (オウ/オー) は正規化で吸収し、それでも残る
2 文字以上の差だけを報告する。**advisory** (STT も期待側も揺れる) ── 名指しされた文を
耳で確かめる。結果は wav の md5 をキーに `audio/_kana_diff_cache.json` へ残し、再合成
していない文は二度と API を呼ばない。

較正 (ある回、読みを直した後の 117 文): 生の差分 60 文 → 同値表 + 2 テイク一致 + 固有名詞除外で
38 文 → 第 2 段の判定で 8 文 → 語単位の聞き直しで未確定 2 (のちに / 漁を)。既知の誤読 6 語
(トル/エル、シュ/タネ、カタ/ガタ …) は単体試験で拾える。**検出器ではなく耳確認の優先リスト**。
期待側の LLM も誤る (葬られ→ホメラレ、反対の側=がわ を誤読扱い) ので、確定は耳で。

CLI: python scripts/kana_reading_diff.py episodes/XXX/scene_definition.json [--scenes a,b] [--no-cache]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "src"))
from speech_source import effective_speech_lines  # noqa: E402

CACHE_FILE = "_kana_diff_cache.json"
MIN_SPAN = 1  # 1 かなの差でも報告する (獲る: トル/エル は 1 文字違い)。長音・促音は正規化で落とす
MAX_TAKES = 3

_STT_KANA_PROMPT = (
    "この日本語音声を、聞こえたとおりに**すべてカタカナだけ**で書き起こしてください。"
    "漢字・ひらがな・英字・数字は一切使わず、数も読みをカタカナで書くこと。"
    "長音は「ー」で表すこと。出力は書き起こし本文のみ。注釈・見出し・タイムスタンプは出力しない。"
)
_EXPECT_PROMPT = (
    "次の日本語の文を、ナレーターが読み上げたときの発音どおりに**すべてカタカナだけ**で"
    "書いてください。漢字・ひらがな・英字・数字は使わず、数字も読み (例: 1926年 → センキュウヒャクニジュウロクネン) "
    "で書くこと。助詞の「は」は「ワ」、「へ」は「エ」、「を」は「オ」と書くこと。長音は「ー」で表すこと。"
    "出力はカタカナの本文のみ。\n\n文: "
)

_HIRA2KATA = {chr(c): chr(c + 0x60) for c in range(0x3041, 0x3097)}
_LONG = {
    # 長音を「ー」に統一するための母音表 (カタカナ)
    "ア": "アカサタナハマヤラワガザダバパャ",
    "イ": "イキシチニヒミリギジヂビピ",
    "ウ": "ウクスツヌフムユルグズヅブプュ",
    "エ": "エケセテネヘメレゲゼデベペ",
    "オ": "オコソトノホモヨロゴゾドボポョ",
}
_VOWEL_OF = {}
for _v, _chars in _LONG.items():
    for _ch in _chars:
        _VOWEL_OF[_ch] = _v


def to_katakana(s: str) -> str:
    return "".join(_HIRA2KATA.get(ch, ch) for ch in s)


def normalize_kana(s: str) -> str:
    """比較用の正規化: カタカナ化、空白/句読点/記号除去、長音の統一 (オウ→オー、エイ→エー)、
    小書き ヲ→オ、ヂ→ジ、ヅ→ズ、ヴ→ブ。"""
    s = to_katakana(s or "")
    s = re.sub(r"[\s　、。,.!?！？「」『』()（）・:：;；\-–—]", "", s)
    s = s.replace("ヲ", "オ").replace("ヂ", "ジ").replace("ヅ", "ズ")
    for a, b in (("ヴァ", "バ"), ("ヴィ", "ビ"), ("ヴェ", "ベ"), ("ヴォ", "ボ"), ("ヴ", "ブ")):
        s = s.replace(a, b)
    out = []
    for ch in s:
        if out and ch in "ウオ" and _VOWEL_OF.get(out[-1]) == "オ":
            out.append("ー")  # オウ / オオ -> オー
        elif out and ch in "イエ" and _VOWEL_OF.get(out[-1]) == "エ":
            out.append("ー")  # エイ / エエ -> エー
        elif out and ch == "ウ" and _VOWEL_OF.get(out[-1]) == "ウ":
            out.append("ー")  # ウウ -> ウー
        elif out and ch == "ア" and _VOWEL_OF.get(out[-1]) == "ア":
            out.append("ー")
        elif out and ch == "イ" and _VOWEL_OF.get(out[-1]) == "イ":
            out.append("ー")
        else:
            out.append(ch)
    s = "".join(out)
    # 長音と促音は STT / 期待側の双方で揺れる (オウ/オー、ホッテ/ホウッテ) ので比較から外す。
    # 残った差は母音・子音の違い = 読みの違いそのもの (トル/エル、シュ/タネ、カタ/ガタ)。
    s = s.replace("ー", "").replace("ッ", "")
    return s


# 両側に対称に当てる同値表。助詞 (ハ/ワ、ヘ/エ、ヲ/オ) と、TTS も期待側も揺れる
# 正当な別読み (二人=ニニン/フタリ、翌年=ヨクネン/ヨクトシ、行き=ユキ/イキ)。較正 ではこれらが偽陽性の大半だった。両側を同じ形に潰すので、同値表の外の差だけが残る。
_EQUIV = [
    ("ハ", "ワ"),
    ("ヘ", "エ"),
    ("ヲ", "オ"),
    ("ヅ", "ズ"),
    ("ヂ", "ジ"),
    ("フタリ", "ニニン"),
    ("ヒトリ", "イチニン"),
    ("ヨクトシ", "ヨクネン"),
    ("フタサイ", "ニサイ"),
    ("ミッカ", "サンニチ"),
    ("イキ", "ユキ"),
    ("イク", "ユク"),
]


def canonical(s: str) -> str:
    """正規化のうえ、同値表で両側を同じ形に潰す (diff の前に必ず両側へ当てる)。"""
    s = normalize_kana(s)
    for a, b in _EQUIV:
        s = s.replace(a, b)
    return s


def has_kanji(s: str) -> bool:
    return bool(re.search(r"[一-鿿]", s or ""))


def diff_spans(expected: str, heard: str) -> list[dict]:
    """正規化済みの 2 本のかな列の食い違い区間 (2 文字以上) を返す。"""
    sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
    spans = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        e, h = expected[i1:i2], heard[j1:j2]
        if max(len(e), len(h)) < MIN_SPAN:
            continue
        ctx_e = expected[max(0, i1 - 6) : i2 + 6]
        ctx_h = heard[max(0, j1 - 6) : j2 + 6]
        spans.append(
            {"tag": tag, "expected": e, "heard": h, "ctx_expected": ctx_e, "ctx_heard": ctx_h}
        )
    return spans


# ---------------------------------------------------------------------------
# Gemini 呼び出し (stt_qa と同じクライアント/設定を使う)
# ---------------------------------------------------------------------------
def _client():
    import stt_qa

    key = stt_qa._load_gemini_key()
    if not key:
        return None
    from google import genai

    return genai.Client(api_key=key)


def stt_kana(client, wav_path: str) -> str:
    """文 wav を かな だけで書き起こす。漢字が混じれば最大 MAX_TAKES 回かけ直す。"""
    import stt_qa

    cfg = stt_qa._stt_config()
    last = ""
    for _ in range(MAX_TAKES):
        up = client.files.upload(file=wav_path)
        kw = {"model": "gemini-2.5-flash", "contents": [up, _STT_KANA_PROMPT]}
        if cfg is not None:
            kw["config"] = cfg
        resp = client.models.generate_content(**kw)
        last = stt_qa._strip_reasoning((resp.text or "").strip())
        if not has_kanji(last):
            return last
    return last


def expected_kana(client, text: str) -> str:
    import stt_qa

    cfg = stt_qa._stt_config()
    kw = {"model": "gemini-2.5-flash", "contents": [_EXPECT_PROMPT + text]}
    if cfg is not None:
        kw["config"] = cfg
    resp = client.models.generate_content(**kw)
    return (resp.text or "").strip()


_JUDGE_PROMPT = (
    "以下は日本語ナレーションの一文と、その音声をカタカナで書き起こしたもの (2 テイク) です。"
    "書き起こしを読み、ナレーション中の語が**本来の読みと違う読み方で読まれている**箇所があれば挙げてください。"
    "無視するもの: 固有名詞 (人名・地名・書名) の聞き取り違い、助詞 は/へ/を の表記、長音・促音・濁点の細かな差、"
    "数字の読み方の揺れ (二人/ににん 等)、書き起こしの脱落や余分な音 (誤読ではなく聞き取りの誤り)。"
    "**2 テイクの両方で同じ読みになっている語だけ**を挙げること。無ければ「なし」とだけ答える。"
    "出力形式: 1 行に 1 語、「語=本来の読み/聞こえた読み」。\n\n"
)


def judge_sentence(client, narration: str, cloud_text: str, heard: str, heard2: str) -> str:
    """差分が出た文について、ナレーション (漢字) と 2 テイクの書き起こしを見せて誤読候補の語を
    名指しさせる (第 2 段)。較正 では 39 文 → 6 語まで絞れたが、判定側も揺れる
    (『側=がわ』を誤読と言う、『市場=しじょう』は言わない) ので、優先順位づけに使い、確定には使わない。"""
    import stt_qa

    cfg = stt_qa._stt_config()
    prompt = (
        _JUDGE_PROMPT
        + f"ナレーション: {narration}\n読みの指定 (ある場合はかな): {cloud_text}\n"
        + f"書き起こし1: {heard}\n書き起こし2: {heard2}\n"
    )
    kw = {"model": "gemini-2.5-flash", "contents": [prompt]}
    if cfg is not None:
        kw["config"] = cfg
    resp = client.models.generate_content(**kw)
    return (resp.text or "").strip()


def _katakana_runs(text: str) -> list[str]:
    """narration 中のカタカナ語 (3 文字以上 = 人名・地名・書名) の正規化形。"""
    return [canonical(r) for r in re.findall(r"[ァ-ヶー]{3,}", text or "")]


def _md5(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _iter_sentences(scene_def: dict):
    """(scene_id, 1-based index, 合成に使われた文 (strip 前, | 抜き), narration)。

    「どの文が合成されたか」は speech_source が唯一の実装。以前ここは cloud[i] が
    空なら narration に落とし、narration_speech への fallback も長さ不一致の規則も
    再現していなかった (合成器と違う文を期待側に渡していた)。
    """
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id")
            narr = scene.get("narration") or []
            lines, _src = effective_speech_lines(scene, "cloud")
            for i, n in enumerate(narr):
                text = lines[i] if i < len(lines) else n
                yield sid, i + 1, (text or "").replace("|", ""), (n or "").replace("|", "")


def run(
    scene_def: dict,
    audio_dir: str,
    scenes: set[str] | None = None,
    use_cache: bool = True,
    client=None,
    log=print,
) -> dict:
    """全文 (または scenes) について期待/実際のかなを突き合わせる。

    返り値: {"checked": n, "flagged": [{"scene_id","index","narration","spans",...}], "unreadable": [...]}
    """
    client = client or _client()
    if client is None:
        log("  [kana-diff][SKIP] GOOGLE_API_KEY が無いので読み差分は取れません")
        return {"checked": 0, "flagged": [], "unreadable": [], "skipped": True}
    cache_path = os.path.join(audio_dir, CACHE_FILE)
    cache = {}
    if use_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
        except (OSError, ValueError):
            cache = {}
    checked = 0
    flagged, unreadable = [], []
    for sid, idx, text, narration in _iter_sentences(scene_def):
        if scenes and sid not in scenes:
            continue
        wav = os.path.join(audio_dir, f"{sid}_{idx:03d}.wav")
        if not os.path.exists(wav):
            continue
        key = f"{_md5(wav)}|{hashlib.md5(text.encode('utf-8')).hexdigest()[:8]}"
        entry = cache.get(key)
        if entry is None:
            try:
                heard_raw = stt_kana(client, wav)
                heard_raw2 = stt_kana(client, wav)  # 2 テイク: STT の偶発的な脱落を消す
                exp_raw = expected_kana(client, text)
            except Exception as exc:  # noqa: BLE001 - advisory: API の失敗で build を止めない
                log(f"  [kana-diff] {sid}_{idx:03d}: API error ({exc})")
                continue
            entry = {"heard": heard_raw, "heard2": heard_raw2, "expected": exp_raw}
            cache[key] = entry
        checked += 1
        heard_n = canonical(entry["heard"])
        heard2_n = canonical(entry.get("heard2") or entry["heard"])
        exp_n = canonical(entry["expected"])
        if has_kanji(entry["heard"]) or not heard_n:
            unreadable.append({"scene_id": sid, "index": idx, "narration": narration[:30]})
            continue
        # 2 テイクの両方に出る差だけを残す (誤読は一貫し、STT の脱落は偶発的)。
        s1 = diff_spans(exp_n, heard_n)
        s2 = diff_spans(exp_n, heard2_n)
        keys2 = {(sp["expected"], sp["ctx_expected"]) for sp in s2}
        spans = [sp for sp in s1 if (sp["expected"], sp["ctx_expected"]) in keys2]
        # 固有名詞 (narration のカタカナ語) の聞き取り違いは誤読ではないので外す。
        names = _katakana_runs(narration)
        spans = [
            sp for sp in spans if not any(sp["expected"] and sp["expected"] in nm for nm in names)
        ]
        if spans and "judge" not in entry:
            try:
                entry["judge"] = judge_sentence(
                    client, narration, text, entry["heard"], entry.get("heard2") or ""
                )
                cache[key] = entry
            except Exception as exc:  # noqa: BLE001 - advisory
                entry["judge"] = f"(judge error: {exc})"
        if spans:
            judge = (entry.get("judge") or "").strip()
            flagged.append(
                {
                    "scene_id": sid,
                    "index": idx,
                    "narration": narration,
                    "spans": spans,
                    "expected": entry["expected"],
                    "heard": entry["heard"],
                    "judge": "" if judge == "なし" else judge,
                }
            )
    if use_cache:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
    return {"checked": checked, "flagged": flagged, "unreadable": unreadable, "skipped": False}


def summarize(result: dict, log=print) -> int:
    """人が読む要約。返り値 = 要確認の文数。"""
    if result.get("skipped"):
        return 0
    log(
        f"  [kana-diff] 期待/実際の読み差分: {result['checked']} 文を照合、"
        f"要確認 {len(result['flagged'])} 文、かなで返らず判定不可 {len(result['unreadable'])} 文"
    )
    ordered = sorted(result["flagged"], key=lambda fl: 0 if fl.get("judge") else 1)
    n_judge = sum(1 for fl in ordered if fl.get("judge"))
    if n_judge:
        log(
            f"    第 2 段 (書き起こしを読ませた判定) が語を名指しした文 = {n_judge} 件。ここから耳で確かめる:"
        )
    for fl in ordered:
        mark = "★" if fl.get("judge") else "-"
        log(f"    {mark} {fl['scene_id']}_{fl['index']:03d}: {fl['narration'][:34]}")
        if fl.get("judge"):
            log(f"        判定: {fl['judge'].replace(chr(10), ' | ')[:120]}")
        for sp in fl["spans"][:4]:
            log(f"        期待 …{sp['ctx_expected']}…  /  実際 …{sp['ctx_heard']}…")
    for u in result["unreadable"]:
        log(
            f"    - {u['scene_id']}_{u['index']:03d}: かなで書き起こせず (耳で確認): {u['narration']}"
        )
    if result["flagged"]:
        log(
            "    -> 差分は STT の揺れ (長音・促音・数の読み) も含む advisory。名指しされた文の wav を耳で確かめ、"
            "誤読なら narration_speech_cloud にかなで固定する。"
        )
    return len(result["flagged"])


def main() -> int:
    p = argparse.ArgumentParser(description="期待した読みと実際の読みの差分 (Gemini)")
    p.add_argument("scene_json")
    p.add_argument("--audio-dir")
    p.add_argument("--scenes")
    p.add_argument("--no-cache", action="store_true")
    a = p.parse_args()
    with open(a.scene_json, encoding="utf-8") as f:
        sd = json.load(f)
    audio_dir = a.audio_dir or os.path.join(os.path.dirname(os.path.abspath(a.scene_json)), "audio")
    scenes = set(a.scenes.split(",")) if a.scenes else None
    res = run(sd, audio_dir, scenes, use_cache=not a.no_cache)
    n = summarize(res)
    if n:
        try:  # pipeline の最終サマリ (advisory roll-up) に件数を載せる
            sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "src"))
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("kana_reading_diff", n)
        except Exception:  # noqa: BLE001 - roll-up は付加情報。単体実行では無くてよい
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
