"""Generate `narration_speech_cloud` for a cloud-TTS episode's scene_definition.json.

Why: script_generator does NOT emit narration_speech_cloud, so cloud episodes fall
back to narration_speech (VOICEVOX kana) at synthesis time -- which reads flat, and
(worse) the fallback wavs become a silent source of stale audio. This produces a
proper cloud reading up front, so the audio step never falls back.

Rule (calibrated from an earlier episode):
  - prose sentence  -> narration[i] with | markers removed (Cloud reads kanji well)
  - symbol sentence -> narration_speech[i] (the VOICEVOX spell-out already turns
    x^2=x etc. into エックスのにじょうはエックス; engine-neutral, correct for Cloud),
    spaces stripped
  - 『』 -> 、 (a short, non-exaggerated pause around quoted terms); ─ — ― ->、;
    doubled punctuation collapsed. cloud_tts.strip_for_cloud drops leftover markers.

NOT done here (deliberately): particle は->わ / へ->え. Reliable particle detection
needs a morphological analyzer; a naive replace corrupts word-internal は/へ. Cloud
Chirp3-HD reads particles natively; the rare misread is caught by stt_qa + the ear
and hand-fixed in narration_speech_cloud. See internal notes.

By default only scenes that LACK narration_speech_cloud are filled (existing,
hand-tuned readings are preserved). Pass --force to regenerate every scene.

Usage: python scripts/gen_cloud_readings.py episodes/XXX/scene_definition.json [--force]
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import cloud_tts  # noqa: E402
from cloud_reading_config import load_cloud_reading_config  # noqa: E402

# Latin letters + formula operators that Cloud cannot voice from raw text; such a
# sentence uses the VOICEVOX spell-out (narration_speech) instead of the display text.
_SYMBOL_RE = re.compile(r"[A-Za-z\^=²³×÷−√∝≠+*]")

# A は/へ that is comma-isolated -- preceded by 、 and followed by 、 。 or the string
# end -- is unambiguously the topic/direction particle: a word-internal は/へ (では,
# には, はじめて, へや, ...) is never a lone token flanked by punctuation. The 『』->、
# conversion in _cleanup creates exactly this isolation (『noun』は -> noun、は) and
# Cloud then mis-reads the lone particle as "ha"/"he" instead of "wa"/"e". So reattach it to the
# preceding word and spell the reading: drop the leading comma, は->わ / へ->え,
# keep any trailing punctuation. Safe without a morphological analyzer because the
# trigger is the lone-token signature, never a particle embedded in a word.
_ISOLATED_HA = re.compile(r"、は(?=[、。]|$)")
_ISOLATED_HE = re.compile(r"、へ(?=[、。]|$)")

# The myriad unit 京 (=けい, 10^16) DIRECTLY after a number, and NOT part of a place
# name, is unambiguously the numeric unit. Chirp3-HD otherwise voices a bare 京 as
# きょう (the city), so a large number like "800京" reads "800 Tokyo". Spell it けい at
# generation time so the reading is fixed before any synthesis.
# Char class + place-name exclusion mirror cloud_reading_lint._KEI_UNIT_RE (calibrated
# FP-zero on 5 shipped cloud eps): the negative lookahead keeps "第3京浜"(第三京浜道路)
# and "3京都" from becoming "3けい浜/けい都". An auto-rewrite must be at least as
# conservative as the detector that already flags this.
_THOUSANDS_COMMA = re.compile(r"(?<=[0-9０-９])[,，](?=[0-9０-９]{3}(?![0-9０-９]))")
_NEN_BEFORE_DIGIT = re.compile(r"(?<![0-9０-９一二三四五六七八九十百千万])年(?=[0-9０-９])")
_MYRIAD_KEI = re.compile(r"(?<=[0-9０-９一二三四五六七八九十百千万億兆])京(?![都城浜阪畿])")

# 分数の「N十分の<数>」を じゅうぶんの に固定。**後続が数であることを必須**にするので
# 「三十分の休憩」(= 30 分) には当たらない。前が数字/漢数字なので「十分の理解」(じゅうぶん)
# のような副詞用法にも当たらない。出荷 69 話の narration を掃引した該当は
# 026 五十分の百五十七 / 027 五十分の一 x4 / 069 四十分の一 x2 の 7 件で、全て分数 (FP 0)。
# 026/027 は engine=voicevox なので今回の Chirp 誤読の対象外だが、cloud で再ビルドする
# ときのために生成時に固定しておく。
# 算用数字の分数「N 分の M」を かな にする。narration_speech は VOICEVOX 用に かな 化されているが、
# build_cloud_reading は記号を含む文でしか narration_speech を使わないので、cloud は
# 数字のまま合成に届いていた。分子・分母が両方数字のときだけ当たるので「30 分の休憩」
# (後ろが数字でない) には当たらない。
_DIGIT_FRACTION_RE = re.compile(r"([0-9０-９]{1,4})[ 　]*分の[ 　]*([0-9０-９]{1,4})")
_KANA_DIGITS = ["", "いち", "に", "さん", "よん", "ご", "ろく", "なな", "はち", "きゅう"]


def _int_to_kana(n: int) -> str:
    """1〜9999 の整数を読み下す (十・百・千の促音/連濁: いっせん・さんびゃく・ろっぴゃく…)。"""
    if n <= 0 or n >= 10000:
        return str(n)
    hundreds = {1: "ひゃく", 3: "さんびゃく", 6: "ろっぴゃく", 8: "はっぴゃく"}
    thousands = {1: "せん", 3: "さんぜん", 8: "はっせん"}
    out = []
    th, rest = divmod(n, 1000)
    if th:
        out.append(thousands.get(th, _KANA_DIGITS[th] + "せん"))
    hu, rest = divmod(rest, 100)
    if hu:
        out.append(hundreds.get(hu, _KANA_DIGITS[hu] + "ひゃく"))
    te, one = divmod(rest, 10)
    if te:
        out.append("じゅう" if te == 1 else _KANA_DIGITS[te] + "じゅう")
    if one:
        out.append(_KANA_DIGITS[one])
    return "".join(out)


def _digit_fraction_to_kana(text: str) -> str:
    """「16 分の 4」-> 「じゅうろくぶんのよん」。全角数字も受ける。"""

    def repl(m):
        den = int(m.group(1).translate(_ZEN2HAN))
        num = int(m.group(2).translate(_ZEN2HAN))
        return f"{_int_to_kana(den)}ぶんの{_int_to_kana(num)}"

    return _DIGIT_FRACTION_RE.sub(repl, text)


_ZEN2HAN = str.maketrans("０１２３４５６７８９", "0123456789")

_FRACTION_JUUBUN = re.compile(
    r"(?<=[0-9０-９一二三四五六七八九])十分の(?=[0-9０-９一二三四五六七八九十百千])"
)

# Formula tokens Cloud voices wrong from raw text. Normally the symbol line uses the
# narration_speech (VOICEVOX) spell-out, but a scene whose narration_speech is
# absent/deleted falls back to raw narration and leaks "L=T-V" / "f'(x)" into the cloud
# reading -- Chirp then voices f'(x) as "エフゴエックス" and L=T-V as a raw jumble. Spell the common, unambiguous formula tokens here so the reading is correct
# even without narration_speech. Applied longest-first, AFTER the narration_speech
# fallback; idempotent on already-spelled text (a spelled reading holds no raw token),
# so it is a pure safety net -- prose never contains these tokens. cloud_reading_lint
# ._scan_raw_formula flags anything this dictionary does not yet cover.
_FORMULA_READINGS = [
    ("L=T-V", "エル・イコール・ティー・マイナス・ブイ"),
    ("f''(x)", "エフ・ダブルプライム・エックス"),
    ("f'(x)", "エフ・プライム・エックス"),
]
# Lagrange points L1..L5 as standalone tokens (not L10/L4a). Chirp voices bare "L4" as
# エルフォー or garbles it; spell エルよん/エルご to match math_07's established reading.
_LPOINT_RE = re.compile(r"L([1-5])(?![0-9A-Za-z])")
_LPOINT_KANA = {"1": "いち", "2": "に", "3": "さん", "4": "よん", "5": "ご"}


def spell_formula_tokens(text: str) -> str:
    """Spell out common formula tokens (L=T-V, f'(x), f''(x), L1..L5) that Cloud
    otherwise mis-voices. Safety net for scenes lacking a narration_speech spell-out;
    idempotent (spelled text holds no raw token) and prose-safe (tokens never occur in
    prose). Also usable to retrofit already-generated readings without a re-gen."""
    for tok, yomi in _FORMULA_READINGS:
        text = text.replace(tok, yomi)
    text = _LPOINT_RE.sub(lambda m: "エル" + _LPOINT_KANA[m.group(1)], text)
    return text


def fix_isolated_particles(text: str) -> str:
    """Rewrite comma-isolated topic/direction particles は/へ to わ/え (reattached).

    See _ISOLATED_HA/_HE for why the comma-isolation signature is a safe, analyzer-
    free way to tell a lone particle from a word-internal は/へ. Idempotent; also
    used to retrofit already-generated readings (no re-generation needed)."""
    text = _ISOLATED_HA.sub("わ", text)
    text = _ISOLATED_HE.sub("え", text)
    return text


def _cleanup(text: str) -> str:
    """『』 -> subtle pause; 「」《》 -> removed (read inline); dashes -> pause; collapse
    doubled punctuation; de-isolate comma-stranded は/へ particles (else Cloud reads
    them ha/he); and spell digit-preceded 京 as けい (else the myriad unit reads きょう)."""
    # (2026-09-19): 括弧の扱い は cloud_tts.normalize_brackets と同じ表。合成直前の
    # strip_for_cloud も同じ関数を通るので、手書きの cloud 文と生成した cloud 文で扱いが揃う。
    text = cloud_tts.normalize_brackets(text.replace("|", ""))
    text = re.sub(r"[─―—]{1,}", "、", text)
    # Dash -> 、 keeps the spaces that hugged the dash (narration "A ── は" -> "A 、 は"),
    # which strands the following particle: the comma-isolated は/へ regex needs an
    # adjacent、, so "、 は" (spaced) is missed and Cloud voices the lone は as "ha"
    #. Collapse whitespace hugging
    # any 、 before de-isolation so the reattach fires and the phantom pause is removed.
    text = re.sub(r"[ \t　]*、[ \t　]*", "、", text)
    text = text.replace("、。", "。").replace("。、", "。")
    text = re.sub(r"、{2,}", "、", text)
    text = fix_isolated_particles(text)
    text = _MYRIAD_KEI.sub("けい", text)
    # ある回: 桁区切りのカンマは落とす (「1,200」を Chirp が いち、にひゃく と読んだ)。
    text = _THOUSANDS_COMMA.sub("", text)
    # ある回: 数字の前の「年」(年 10 万リーヴル = 年ごとに) を ねん に固定 (とし と読まれた)。
    # 数字の後ろの 年 (1747年) は正しく ねん と読むので触らない。
    text = _NEN_BEFORE_DIGIT.sub("ねん", text)
    text = _FRACTION_JUUBUN.sub("じゅうぶんの", text)
    text = _digit_fraction_to_kana(text)
    text = re.sub(r"^[、\s]+", "", text)
    return text.strip()


# ある回: 術語・固有名 (表層 3 文字以上) の読みは SSML でなく生成時にかなで直書きする。
# 合理力学 を `cloud_reading_overrides` (SSML <phoneme>) で固定したつもりが Chirp に無視され
# ゴーリキガク になり、lint は「config で固定済み」として黙った。ある回の実測どおり、固有名・
# 術語はかな直書きが効き、短い機能語 (場合/干支 = 2 文字以下) は直書きすると「ば・あい」と
# 割れるので SSML に残す。閾値はその実測から。
DIRECT_KANA_MIN_LEN = 3


def split_overrides_by_channel(
    overrides: dict | None, force_direct: set | list | None = None
) -> tuple[dict, dict]:
    """(かな直書きにする語, SSML に残す語)。値がかな以外なら両方から外す。

    ある回: `force_direct` (config の `cloud_direct_kana`) に挙げた語は長さに関係なく
    直書きにする。弦 (1 文字) と 一片 (2 文字) は SSML では割れ (ケン/キリ、いっぱた)、
    かな直書きで直った。2 文字以下は既定では SSML (場合/干支 は直書きすると割れる) なので、
    語ごとに opt-in する。
    """
    direct, ssml = {}, {}
    forced = {str(w) for w in (force_direct or [])}
    for k, v in (overrides or {}).items():
        k, v = str(k), str(v)
        if not k or not v or not re.fullmatch(r"[ぁ-ゖァ-ヺー]+", v):
            continue
        (direct if (len(k) >= DIRECT_KANA_MIN_LEN or k in forced) else ssml)[k] = v
    return direct, ssml


_KANJI = "\u4e00-\u9fff"


def compound_hits(text: str, key: str) -> list[str]:
    """`key` を含み、前後に漢字が続く語 (複合語) を text から拾う (弦 -> 正弦 / 弦楽器)。"""
    if not key or not text:
        return []
    pat = re.compile(rf"[{_KANJI}]*{re.escape(key)}[{_KANJI}]*")
    return sorted({m for m in pat.findall(text) if m != key})


def apply_direct_kana(text: str, direct: dict | None) -> str:
    """cloud 文の表層をかなに置換する (長い表層から)。

    ある回再検証: 1〜2 文字の語 (弦) を素朴に置換すると 正弦 が「正げん」になる (SSML の
    表層一致と同じ穴)。短い語は **前後に漢字が無い位置だけ** 置換する (張った弦 / 弦の は
    置換、正弦 / 弦楽器 は残す)。複合語の読みを変えたいなら、その複合語自体を overrides に
    書く (長い表層から先に置換される)。3 文字以上 (術語・固有名) は従来どおり全置換。
    """
    if not direct:
        return text
    for k in sorted(direct, key=len, reverse=True):
        if len(k) < DIRECT_KANA_MIN_LEN:
            text = re.sub(rf"(?<![{_KANJI}]){re.escape(k)}(?![{_KANJI}])", direct[k], text)
        else:
            text = text.replace(k, direct[k])
    return text


def build_cloud_reading(
    narration: list,
    narration_speech: list | None,
    overrides: dict | None = None,
    force_direct: set | list | None = None,
) -> list:
    """Return the narration_speech_cloud array for one scene."""
    direct, _ssml = split_overrides_by_channel(overrides, force_direct)
    out = []
    for i, line in enumerate(narration):
        if _SYMBOL_RE.search(line) and narration_speech and i < len(narration_speech):
            base = narration_speech[i].replace(" ", "").replace("　", "")
        else:
            base = line
        # Spell formula tokens (L=T-V/f'(x)/Lₙ) so raw symbols never leak into the cloud
        # reading when narration_speech is absent. No-op otherwise.
        out.append(apply_direct_kana(spell_formula_tokens(_cleanup(base)), direct))
    return out


def _load_direct_kana(scene_path: str) -> list:
    """config の `cloud_direct_kana` (長さに関係なくかな直書きにする語) を読む。
    読みは cloud_reading_config に 1 本化 (壊れた config は向こうが WARN)。"""
    return list(load_cloud_reading_config(scene_path).direct_kana)


def _load_episode_overrides(scene_path: str) -> dict:
    """config の `cloud_reading_overrides` を読む。cloud_reading_config に委譲。"""
    return dict(load_cloud_reading_config(scene_path).overrides)


def generate(scene_path: str, force: bool = False) -> tuple[int, int]:
    """Fill narration_speech_cloud in-place. Returns (generated, preserved).

    A scene missing cloud is generated from narration (native は; symbol sentences
    use the narration_speech spell-out). An existing cloud is preserved so a
    hand-tuned reading survives re-builds; ``--force`` regenerates every scene.

    The LLM does NOT emit narration_speech_cloud -- script_generator strips any it
    produces (strip_llm_cloud_readings) so that the blanket は->わ over-conversion
    it tends to apply never reaches synthesis. Thus at pipeline time the only
    existing clouds this preserves are genuine hand-tuned ones.
    """
    with open(scene_path, encoding="utf-8") as f:
        sd = json.load(f)
    overrides = _load_episode_overrides(scene_path)
    force_direct = _load_direct_kana(scene_path)
    # ある回: 短い直書き語が複合語の中にも現れるなら名指しする (そこは置換されず SSML に残る)
    all_text = "".join(
        n
        for sec in sd.get("sections", [])
        for sc in sec.get("scenes", [])
        for n in (sc.get("narration") or [])
    )
    direct_short, _ = split_overrides_by_channel(overrides, force_direct)
    for k in sorted(direct_short):
        if len(k) < DIRECT_KANA_MIN_LEN:
            hits = compound_hits(all_text, k)
            if hits:
                print(
                    f"[GEN-CLOUD][WARN] 直書き語「{k}」は複合語 {'/'.join(hits)} の中には当てません "
                    "(漢字に挟まれた位置は SSML のまま)。読みを固定したいなら複合語自体を "
                    "cloud_reading_overrides に書いてください"
                )
    gen = skip = 0
    stale_direct: list[tuple[str, list[str]]] = []
    for sec in sd.get("sections", []):
        for sc in sec.get("scenes", []):
            narration = sc.get("narration")
            if not narration:
                continue
            if sc.get("narration_speech_cloud") and not force:
                skip += 1
                # (2026-09-19): 温存した cloud 文に、direct_kana がまだ当たっていない語が
                # 漢字のまま残っていれば名指しする。config の cloud_direct_kana を後から足しても
                # 既存 cloud には効かない (= no-op) ことが、どこにも書かれていなかった。
                hit = sorted(
                    {
                        k
                        for line in sc["narration_speech_cloud"]
                        if isinstance(line, str)
                        for k in direct_short
                        if apply_direct_kana(line, {k: direct_short[k]}) != line
                    }
                )
                if hit:
                    stale_direct.append((sc.get("scene_id", "?"), hit))
                continue  # preserve existing (hand-tuned) reading
            sc["narration_speech_cloud"] = build_cloud_reading(
                narration, sc.get("narration_speech"), overrides, force_direct
            )
            gen += 1
    if stale_direct:
        print(
            f"[GEN-CLOUD][WARN] 既存の narration_speech_cloud を温存した {len(stale_direct)} scene に、"
            "cloud_direct_kana / 3 文字以上の overrides がまだ当たっていない語が漢字のまま残っています "
            "(config を後から変えても既存 cloud には効きません):"
        )
        for sid, words in stale_direct:
            print(f"    {sid}: {', '.join(words)}")
        print("    対処: `--force` で全 scene を再生成するか、当該 scene の cloud を手で直す")
    if gen:
        with open(scene_path, "w", encoding="utf-8") as f:
            json.dump(sd, f, ensure_ascii=False, indent=2)
    return gen, skip


def main() -> int:
    p = argparse.ArgumentParser(description="Generate narration_speech_cloud for cloud episodes.")
    p.add_argument("scene_json", help="Path to scene_definition.json")
    p.add_argument(
        "--force",
        action="store_true",
        help="Regenerate all scenes (default: only scenes missing narration_speech_cloud)",
    )
    args = p.parse_args()
    gen, skip = generate(args.scene_json, args.force)
    print(f"[GEN-CLOUD] generated {gen} scene(s), preserved {skip} existing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
