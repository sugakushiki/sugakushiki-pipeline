"""reading_guard.py - VOICEVOX 誤読 pre-build ガード。

全 effective audio (narration_speech があればそれ、無ければ narration の
flat 版) を VOICEVOX audio_query で kana 実測し、既知の誤読リスク語が
期待読みになっていない行を WARN する。

global 誤読辞書 (audio_generator.KNOWN_MISREADINGS) を適用した「実際に
合成されるテキスト」を測るので、辞書で対処済みの語は発火しない。発火
するのは「辞書にも narration_speech にも載っておらず、本番音声で誤読が
残る」箇所 = まさに今回 ある回 で user が耳で発見した類 (数=すう, 縁=えん)。

設計意図:
- 断片プローブでは文脈依存誤読 (数+カタカナ -> すう) を取りこぼす。全文
  実測 + 既知リスク辞書で網羅検出する。
- per-ep narration_speech に陥らず、汎用化できる語は global 辞書へ、
  文脈依存語は narration_speech へ、という振り分けの可視化に使う。

Usage:
    python scripts/reading_guard.py examples/moriarty/scene_definition.json
    python scripts/reading_guard.py examples/moriarty/scene_definition.json --strict
    (--strict: WARN があれば exit 1。既定は advisory で exit 0)
"""

import argparse
import json
import os
import re
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# (surface 表層形, expect 期待カナ, hint). surface が narration に出るのに
# 合成テキストの実測カナへ expect が現れなければ WARN。新しい誤読が出たら
# ここへ追加する (測ってから足すこと)。汎用化できる語は audio_generator.
# _MISREADING_CATEGORIES への追加も検討する。
KNOWN_READING_RISKS = [
    ("節線", "セッセン", "節線=せっせん (物理の節線。フシセン/フシ 誤読)"),
    ("三つの数", "カズ", "三つの数=みっつのかず (数=かず。直後がカタカナだと すう 化)"),
    ("板の縁", "フチ", "板の縁=いたのふち (縁=ふち。えん 誤読)"),
    ("公開鍵暗号", "カギ", "公開鍵暗号=こうかいかぎあんごう (鍵=かぎ。けん 誤読)"),
    ("何不自由", "ナニフジユウ", "何不自由=なにふじゆう"),
    ("何なのか", "ナンナ", "何なのか=なんなのか (なになのか 誤読)"),
    ("もの間", "アイダ", "〜もの間=ものあいだ (間=あいだ。かん 誤読)"),
    ("本名", "ホンミョウ", "本名=ほんみょう (ほんめい 誤読)"),
    # 多読み漢字: 文脈で読みが変わり VOICEVOX が訓/音を取り違える語。surface→expect。
    ("全問", "ゼンモン", "全問=ぜんもん (問=もん。全問で とい 化。三十問/一問は正)"),
    ("誓いの下", "モト", "誓いの下=ちかいのもと (下=もと。した 誤読)"),
    ("誓絶", "セイゼツ", "誓絶=せいぜつ (誓=せい。ちかい 誤読。誓約はセエヤク正)"),
    ("確信を抱", "イダ", "確信/夢/志を抱く=いだく (抱=いだく。だく 誤読)"),
    ("思いを抱", "イダ", "思い/希望を抱く=いだく (抱=いだく。だく 誤読)"),
    ("野望を抱", "イダ", "野望/野心を抱く=いだく (抱=いだく。だく 誤読)"),
    ("自然物", "ブツ", "自然物=しぜんぶつ"),
    # 割る (除算の動詞): VOICEVOX は終止形「割る」を「わりる」と誤読 (一段活用と誤解析)。
    # ある回 ガウスで既知だが global 辞書未登録で ある回「8割る5」再発。audio_generator
    # の math_terms に 割る→わる を集積済 (fix 適用後は ワル で PASS。本 entry は
    # fix 未適用/損傷形の検出バックストップ)。割り算/割った/割合 は非該当。
    ("割る", "ワル", "割る=わる (除算。終止形を わりる と誤読。割り算/割った は正)"),
    # 後世 (こうせい=後の時代/posterity): ある回「はるか後世」で「はるか後」rule の
    # greedy match により のち世→のちせい 再発 (真因は 後世/はるか後世 rule 欠落)。
    # audio_generator に 後世→こうせい / はるか後世→はるかこうせい を longest-first で
    # 集積済。本 entry は fix 未適用/損傷形の検出バックストップ。
    # 実測 (2026-06-22, VOICEVOX sp13): 後世(漢字)→コオセエ / こうせい(かな NS)→
    # コオセイ。両者を含む弁別子は「コオセ」。誤読形 のち世→ノチセエ / ごせ→ゴセ は
    # 「コオセ」非含有なので検出可 (コオセエ 限定だと かな NS=コオセイ で FP)。
    (
        "後世",
        "コオセ",
        "後世=こうせい (後の時代)。のちせい/ごせ 誤読。はるか後 rule の greedy match で再発",
    ),
    # 多読み漢字。surface→expect は
    # 文脈非依存で常に1つの読みの語のみ (= 誤検知ゼロ)。VOICEVOX 実測 (2026-06-27, sp13)。
    (
        "値打ち",
        "ネウチ",
        "値打ち=ねうち (単独「値→あたい」rule の誤発火で 値打ち→あたい打ち=アタイウチ 誤読。"
        "audio_generator に 値打ち/あたい打ち→ねうち 集積済。本 entry は損傷形/fix 未適用の検出 backstop)",
    ),
    (
        "幾分",
        "イクブン",
        "幾分=いくぶん (分=ぶん。VOICEVOX が いくふん=イクフン と誤読。文脈非依存で常に いくぶん)",
    ),
    (
        "ベルヌーイ家",
        "ウイケ",
        "ベルヌーイ家=ベルヌーイけ (家=け。VOICEVOX が ベルヌーイか=…ウイカ と誤読。"
        "expect は弁別子 ウイケ で FP 回避)",
    ),
]

_NON_KATA = re.compile(r"[^ァ-ヶー]")

# 助詞罠: narration_speech で漢語をひらがな化
# すると語中の「は/へ/を」を VOICEVOX が助詞 (わ/え/お) と読む。author が導入した
# 読み (NS にあって display に無いひらがな run) に限定し、カタカナ化との実測差分で確認。
_HIRA_RUN = re.compile(r"[ぁ-ん]{3,}")
# 「は/を」は助詞として頻出し FP が高いので、実証された誤読 class である「へ」に限定。
# (共変→きょうへん→キョオエン。語中の へん/へい 等が助詞 え に化ける)。
# 方向助詞「への」(知への闘い 等) は除外する。は/を 罠は稀で、手動 kana 実測で対応。
_TRAP_CHARS = set("へ")
# カタカナ固有名詞 (カバレッジ用): 中点込みの 3 文字以上のカタカナ列
_KATA_TERM = re.compile(r"[ァ-ヶー・]{3,}")

# 助詞「は」罠: 漢字/カタカナの直後の topic 助詞「は」が
# 直後のひらがなと結合して ハ と読まれることがある (本来 わ)。漢字/カタカナ前置 +
# ひらがな後続の「は」位置を候補とし、は→わ 置換の実測差分で誤読を確認する。
# 彼は=カレワ 等の正読は置換しても kana 同一なので発火しない (低 FP)。
# は が句読点/漢字の直前 (彼は、/ 彼は晩年) は結合が起きにくいので候補外。
_HA_TRAP_RE = re.compile(r"(?<=[一-鿿ァ-ヶー])は(?=[ぁ-ん])")
# 名詞の構成文字 (は 直前の語幹を後方に拾う)
_NOUN_CHAR = re.compile(r"[一-鿿ァ-ヶー々]")


def _ha_trap_positions(effective: str) -> list:
    """漢字/カタカナ前置 + ひらがな後続の topic 助詞「は」の index リスト。"""
    return [m.start() for m in _HA_TRAP_RE.finditer(effective)]


def _clean_kana(kana: str) -> str:
    """カタカナ + 長音記号以外 (空白・アクセント記号等) を除去して部分一致用に正規化。"""
    return _NON_KATA.sub("", kana)


def _hira_to_kata(s: str) -> str:
    """ひらがな -> カタカナ (長音符・記号はそのまま)。"""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ん" else c for c in s)


def _particle_trap_candidates(surface: str, effective: str) -> list:
    """effective(NS) 内の「author 導入のひらがな読み」で助詞罠リスクのある run を返す。

    判定: effective のひらがな run のうち (1) display(surface) に無い (= 漢字から
    変換された読み) かつ (2) は/へ/を が語末以外に出る もの。自然文の助詞
    (「ものではない」の は 等) は display にも在る or run 末尾なので除外され、FP を防ぐ。
    """
    if effective == surface:
        return []
    out = []
    for m in _HIRA_RUN.finditer(effective):
        run = m.group(0)
        if run in surface:
            continue  # display にも在る = 自然文 (助詞含む)、author 導入でない
        for j, ch in enumerate(run):
            if ch in _TRAP_CHARS and j != len(run) - 1:
                if run[j + 1] == "の":  # への = 方向助詞、除外
                    continue
                out.append(run)
                break
    return out


def _effective_pairs(scene_def: dict):
    """(scene_id, index, surface_text, effective_text) を yield。

    surface_text: narration[i] の flat 版 (表層の漢字を含む -> 語の存在判定用)
    effective_text: narration_speech[i] があればそれ、無ければ surface_text
                    (= VOICEVOX へ実際に送られるテキスト)
    """
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "?")
            narration = scene.get("narration", []) or []
            ns_list = scene.get("narration_speech")
            for i, narr in enumerate(narration):
                surface = narr.replace("|", "")
                if ns_list and i < len(ns_list) and ns_list[i]:
                    effective = ns_list[i]
                else:
                    effective = surface
                yield sid, i, surface, effective


# VOICEVOX の va/vu 合成のうち「kana 実測では露見しない」唯一の罠 =
# ひらがな ゔ (U+3094)。ゔぁ は kana 実測で「ヴァ」と出ても音は不自然。
# カタカナ ヴ (U+30F4) は除外する: ヴァ→バ と安定して倒れ、narration に ヴ があるのは意図した字幕表示。ここで ヴ まで
# 拾うと shipped 済みの正常 scene (Weierstrass 字幕) を全部 FP で叩く。
# effective(実際に合成されるテキスト) のみ走査。VOICEVOX 不要なので常に走る。
_VU_CHARS = ("ゔ",)


def scan_vu_synthesis_risk(scene_def: dict) -> list:
    """effective audio に ひらがな ゔ を含む行を WARN (kana 実測で露見しない合成劣化)。"""
    out = []
    for sid, idx, surface, effective in _effective_pairs(scene_def):
        found = [c for c in _VU_CHARS if c in effective]
        if not found:
            continue
        chars = "".join(found)
        from_ns = effective != surface  # NS で導入されたか (= narration には無い)
        where = "narration_speech" if from_ns else "narration(NS未設定)"
        out.append(
            {
                "type": "vu",
                "scene_id": sid,
                "index": idx,
                "surface": chars,
                "expect": "バ/定着カタカナ",
                "hint": (
                    f"合成テキスト({where})に ひらがな「{chars}」(va/vu)。VOICEVOX は"
                    "綺麗に合成しない (kana 実測では「ヴァ」と出るのに音は不自然)。バ 等の"
                    "定着カタカナに倒す (字幕 narration の カタカナ ヴ 表示は可・音は自然に バ)"
                ),
                "kana": "",
            }
        )
    return out


def run_guard(scene_path: str, voicevox_url: str) -> list:
    """誤読リスクを検出して WARN リストを返す。VOICEVOX 不通なら None。"""
    try:
        from audio_generator import apply_known_misreading_fixes, query_pronunciation
    except Exception as e:  # pragma: no cover
        print(f"  [SKIP] audio_generator を import できません: {e}")
        return None

    with open(scene_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    # global 辞書を適用 (辞書で対処済みの語を実測に反映する)
    try:
        apply_known_misreading_fixes(scene_def)
    except Exception as e:
        print(f"  [WARN] global 辞書適用に失敗 (続行): {e}")

    # VOICEVOX 疎通確認
    try:
        query_pronunciation("テスト", voicevox_url)
    except Exception as e:
        print(f"  [SKIP] VOICEVOX ({voicevox_url}) に接続できません: {e}")
        return None

    warnings = []
    measured = 0
    kata_terms = set()  # #4 カバレッジ用: narration 全体のカタカナ固有名詞
    for sid, idx, surface, effective in _effective_pairs(scene_def):
        for t in _KATA_TERM.findall(surface):
            kata_terms.add(t)
        # この行に出る誤読リスク語 / 助詞罠候補だけ measure (無ければ skip)
        hits = [(s, e, h) for (s, e, h) in KNOWN_READING_RISKS if s in surface]
        trap_cands = _particle_trap_candidates(surface, effective)
        ha_positions = _ha_trap_positions(effective)
        if not hits and not trap_cands and not ha_positions:
            continue
        try:
            _, kana = query_pronunciation(effective, voicevox_url)
        except Exception as e:
            print(f"  [WARN] {sid}[{idx}] audio_query 失敗: {e}")
            continue
        measured += 1
        clean = _clean_kana(kana)
        # (a) 既知誤読リスク辞書照合
        for surf, expect, hint in hits:
            if expect not in clean:
                warnings.append(
                    {
                        "type": "risk",
                        "scene_id": sid,
                        "index": idx,
                        "surface": surf,
                        "expect": expect,
                        "hint": hint,
                        "kana": clean,
                    }
                )
        # (b) #3 助詞罠: 候補 run をカタカナ化し実測差分で確認 (差が出れば trap)
        for run in trap_cands:
            kata = _hira_to_kata(run)
            try:
                _, kana2 = query_pronunciation(effective.replace(run, kata, 1), voicevox_url)
            except Exception:
                continue
            if _clean_kana(kana2) != clean:
                warnings.append(
                    {
                        "type": "trap",
                        "scene_id": sid,
                        "index": idx,
                        "surface": run,
                        "expect": kata,
                        "hint": f"ひらがな読み「{run}」が助詞誤読 (は/へ/を=わ/え/お)。カタカナ「{kata}」推奨",
                        "kana": clean,
                    }
                )
        # (c) は 助詞罠: 漢字/カタカナ前置の topic 助詞「は」が ハ と
        #     誤読されていないか「名詞アンカー」で判定。は 直前の名詞のカナ K に対し、
        #     base カナが K+ハ を含み K+ワ を含まなければ ハ 誤読 (本来 わ)。
        #     は->わ 全行置換は わ/は で再分割が変わり別箇所に diff (FP) が出るため不採用。
        for pos in ha_positions:
            j = pos
            while j > 0 and _NOUN_CHAR.match(effective[j - 1]):
                j -= 1
            noun = effective[j:pos]
            if not noun:
                continue
            try:
                _, kn = query_pronunciation(noun, voicevox_url)
            except Exception:
                continue
            K = _clean_kana(kn)
            if not K or (K + "ハ") not in clean or (K + "ワ") in clean:
                continue  # 正読(K+ワ) か 判定不能 → flag しない (保守的)
            ctx = effective[max(0, pos - 4) : pos + 2]
            warnings.append(
                {
                    "type": "trap",
                    "scene_id": sid,
                    "index": idx,
                    "surface": ctx,
                    "expect": "ワ",
                    "hint": f"topic 助詞「は」が ハ と誤読 (…{ctx}…)。読点を入れるか NS で わ 固定",
                    "kana": clean,
                }
            )
    print(f"  measured {measured} line(s) containing risk/trap terms")

    # #4 新規固有名詞カバレッジ: voicevox_dict.json 未登録のカタカナ語を提示
    # (reading_guard の PASS は既知リスク辞書照合のみ = 新規固有名詞は素通り。
    #  外国人名/地名の多い ep では下記を手動で実測確認すべき、という注意喚起)
    try:
        dict_path = os.path.join(_SRC, "voicevox_dict.json")
        with open(dict_path, encoding="utf-8") as f:
            words = json.load(f).get("words", [])
        registered = {(w.get("surface") or w.get("word") or "") for w in words}
    except Exception:
        registered = set()
    uncovered = sorted(t for t in kata_terms if t not in registered)
    if uncovered:
        shown = uncovered[:20]
        print(
            f"  [INFO] 辞書未登録のカタカナ固有名詞 {len(uncovered)} 件 "
            f"(PASS は既知リスクのみ照合 -> 新規 ep は手動実測推奨):"
        )
        print("    " + " / ".join(shown) + (" ..." if len(uncovered) > 20 else ""))
    return warnings


def main():
    parser = argparse.ArgumentParser(description="VOICEVOX 誤読 pre-build ガード")
    parser.add_argument("scene_definition", help="scene_definition.json のパス")
    parser.add_argument(
        "--voicevox-url", default="http://localhost:50021", help="VOICEVOX engine URL"
    )
    parser.add_argument(
        "--strict", action="store_true", help="WARN があれば exit 1 (既定は exit 0)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Reading Guard (VOICEVOX 誤読 pre-build check)")
    print("=" * 60)

    if not os.path.exists(args.scene_definition):
        print(f"  [ERROR] not found: {args.scene_definition}")
        sys.exit(2)

    # 静的 ゔ/ヴ scan は VOICEVOX 不要なので疎通の有無に関わらず常に実行する。
    with open(args.scene_definition, encoding="utf-8") as f:
        _sd_static = json.load(f)
    vu_warnings = scan_vu_synthesis_risk(_sd_static)

    guard_warnings = run_guard(args.scene_definition, args.voicevox_url)
    voicevox_skipped = guard_warnings is None
    if voicevox_skipped:
        print("  [NOTE] VOICEVOX 測定は SKIP (静的 ゔ/ヴ scan のみ実行)")

    warnings = list(vu_warnings) + (guard_warnings or [])

    if not warnings:
        if voicevox_skipped:
            print("\n  RESULT: PASS (静的 ゔ/ヴ scan のみ。VOICEVOX 誤読測定は未実行)")
        else:
            print("\n  RESULT: PASS (既知の誤読リスクは検出されませんでした)")
        sys.exit(0)

    n_vu = sum(1 for w in warnings if w.get("type") == "vu")
    n_trap = sum(1 for w in warnings if w.get("type") == "trap")
    n_risk = len(warnings) - n_vu - n_trap
    print(
        f"\n  [WARN] {len(warnings)} 件検出 "
        f"(誤読リスク {n_risk} / 助詞罠 {n_trap} / va・vu {n_vu}):"
    )
    for w in warnings:
        wtype = w.get("type")
        tag = {"trap": "助詞罠", "vu": "va/vu"}.get(wtype, "誤読")
        print(f"    - [{tag}] {w['scene_id']}[{w['index']}] 「{w['surface']}」")
        if wtype == "trap":
            print(f"        実測「{w['kana']}」-> {w['hint']}")
        elif wtype == "vu":
            print(f"        {w['hint']}")
        else:
            print(f"        実測カナに「{w['expect']}」が無い -> {w['hint']}")
        print("        narration_speech でカナ固定を推奨")
    print("\n  対処: narration_speech にカナで読みを固定 (文脈依存語)、")
    print("        または汎用語なら audio_generator._MISREADING_CATEGORIES に追加")
    print(f"\n  RESULT: {'FAIL' if args.strict else 'WARN'} ({len(warnings)} 件)")
    sys.exit(1 if args.strict else 0)


if __name__ == "__main__":
    main()
