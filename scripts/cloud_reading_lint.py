#!/usr/bin/env python3
"""cloud_reading_lint.py - Cloud TTS (Chirp3-HD) narration の読み誤り温床を静的 WARN。

Cloud TTS (`tts.engine=cloud`) エピソードには VOICEVOX の audio_query (kana 実測)
が無いため、reading_guard.py のような合成前 kana 照合ができない。本 lint は
scene_definition.json の narration / narration_speech_cloud を **合成前に静的走査**し、
Chirp3-HD が誤読・不自然化しやすい 4 カテゴリを advisory WARN する。ある回
(コワレフスカヤ) で user が 1 つずつ耳で指摘した読み問題を、出荷前に自動検出
するのが狙い。STT QA (scripts/stt_qa.py) は合成後 wav を検証する事後ガードだが、
本 lint はテキスト段階で温床を洗い出す事前ガードで、両者は補完的。

検出カテゴリ (いずれも advisory=WARN、既定 exit 0、--strict で WARN 時 exit 1):

  (1) 多読み漢字が読み未固定: 文脈依存で誤読しやすい漢字が narration にあり、
      対応する narration_speech_cloud の同 index 文に「正しい読みのひらがな」が
      無い (= 漢字のまま = Chirp 自動読みに委ねている) 場合。読みを固定していれば
      発火しないので、修正済み ep では出ない。辞書 _POLYPHONE で拡張。
  (2) 同音誤解語: 音が別語と衝突する語 (大数学者=だいすうがくしゃ -> 代数学者 と
      同音)。narration/字幕にあれば言い換えを促す。辞書 _HOMOPHONE で拡張。
  (3) 難語/専門硬語: 視聴者に難しい硬い語 (里程標)。blocklist _HARD_WORDS で拡張。
  (4) Chirp が不自然な間を入れやすい構文: 用言 + 「とは」 / 長い主語 + 「は、」。
      正規表現で近似検出。

narration は sd["sections"][i]["scenes"][j]["narration"] (list of str)。
narration_speech_cloud も同構造 (任意)。字幕マーカー "|" は除去して判定する。

Usage:
    python scripts/cloud_reading_lint.py examples/moriarty/scene_definition.json
    python scripts/cloud_reading_lint.py examples/moriarty/scene_definition.json --strict
    (--strict: WARN があれば exit 1。既定は advisory で exit 0)
"""

import argparse
import collections
import difflib
import json
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# cloud_tts._READING_OVERRIDES holds ambiguous kanji whose reading is force-fixed at
# synthesis via SSML <phoneme> (二乗->にじょう, 数論家->すうろんか, ...). Those need no
# narration_speech_cloud kana, so the polyphone scan must skip them or it raises a
# false "多読み未固定" WARN every build. Load defensively.
try:
    _src_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    )
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    from cloud_tts import _READING_OVERRIDES as _SSML_FORCED
except Exception:
    _SSML_FORCED = {}

# (1b) 数の位「京」(=けい, 10^16): 数字直後の 京 は単位。Chirp が きょう(都市) 誤読しうる
#。数字非前置の 東京/京都 は対象外、後続 都/城/浜/阪/畿 も除外。
_KEI_UNIT_RE = re.compile(r"[0-9０-９一二三四五六七八九十百千万億兆]\s*京(?![都城浜阪畿])")

# (1c) 単独「数」(かず/すう 多読み): 前後を漢字/カタカナ/長音/々 で挟まれない裸の 数。
# 素数/数列/因数/数学/十数/リュカ数/メルセンヌ数 等の複合語は前後文字で自動除外。
# 後続「え」も除外 = 動詞「数える(かぞえ)」で名詞の 数 ではない。
_STANDALONE_NUM_RE = re.compile(r"(?<![一-鿿ァ-ヶー々])数(?![一-鿿々え])")


# ----------------------------------------------------------------------------
# (1) 多読み漢字辞書: {surface: (correct_yomi_hiragana, [misread_notes], fix_note)}
#
# surface = narration に出る「文脈まで含んだ具体表層」。具体化することで別読みが
# 正しい文脈 (踏み入れ=いれ、私たち=わたし 等) を巻き込まず FP を避ける。
# correct_yomi = narration_speech_cloud の同 index 文にこのひらがな列があれば
# 「読み固定済み」とみなし WARN しない。無ければ Chirp 自動読み任せ = WARN。
# ある回 実績 + memory 由来の既知誤読を初期値に。測ってから足すこと。
# ----------------------------------------------------------------------------
_POLYPHONE = {
    # 入 (はいる/いれる): 入学文脈の可能形「入れ(ません)」は はいれ。イレ 誤読。
    # 「踏み入れ」「手に入れ」は いれ で正しいので surface に含めず、
    # possible-form の "に入れ" (…に入れる/入れない) を狙う。
    "に入れま": (
        "はいれ",
        ["入=いれ と読み はいれない/はいれません を イレ 化"],
        "大学に入れ->はいれ で固定",
    ),
    "に入れる": ("はいれ", ["入=いれ の可能形を イレル 化"], "はいれる で固定"),
    # 愛 (あい/めでる): 「愛では」「愛のない」は あい。「愛で」は動詞 めでる 化しやすい。
    "愛では": ("あい", ["愛で+は を 動詞めでる+は と解析し メデ 化"], "あいで(は) で固定"),
    "愛は": ("あい", ["愛=あい。語頭 愛+は を メデ 化しうる"], "あいは で固定"),
    # 友 (とも/ゆう): 「の友」は とも。ユウ 誤読。
    "の友": ("とも", ["友=とも。ユウ と音読み誤読"], "のとも で固定 (読点も可)"),
    # 私 (わたし/わたくし/し): 「私講師」は し(=しこうし)。ワタクシ 誤読。
    #   note: 「私たち」(わたし) は surface に含めないので巻き込まない。
    "私講師": ("しこうし", ["私=し。ワタクシコウシ と誤読"], "しこうし で固定"),
    "私塾": ("しじゅく", ["私=し。ワタクシジュク と誤読"], "しじゅく で固定"),
    # 正 (せい/しょう/ただ): 「正教授」は せい。ショウ 誤読。
    "正教授": ("せいきょうじゅ", ["正=せい。ショウキョウジュ と誤読"], "せいきょうじゅ で固定"),
    # 通 (とおる/かよう/つう): 「を通って」は とおる。カヨッテ/ツウジテ 誤読。
    "を通って": ("とおって", ["通=とおる。カヨッテ/ツウジテ 誤読"], "をとおって で固定"),
    "を通り": ("とおり", ["通=とおる。カヨリ/ツウリ 誤読"], "をとおり で固定"),
    # --- memory 由来の既知多読み (VOICEVOX で確立、Cloud でも温床) ---
    # 二乗 (にじょう): ニノリ/フタジョウ 誤読。Chirp は SSML phoneme でも固定可だが
    #   narration_speech_cloud の にじょう 明示があれば安全。
    "二乗": (
        "にじょう",
        ["二乗=にじょう。ニノリ/フタジョウ 誤読"],
        "にじょう で固定 (or SSML phoneme)",
    ),
    "対数": ("たいすう", ["対数=たいすう。ツイスウ 誤読はまれだが硬語で温床"], "たいすう で固定"),
    # 物 (ぶつ/もの): 自然物=しぜんぶつ を シゼンモノ 化 (物=もの)。
    "自然物": ("しぜんぶつ", ["物=ぶつ。シゼンモノ 誤読"], "しぜんぶつ で固定"),
    # 下 (した/もと): 「の下で」は もと。シタ 誤読。
    #   note: 「門下」(もんか) は Chirp が既定で正読するので含めない (FP 回避)。
    "の下で": ("もと", ["下=もと。シタ 誤読 (…のもとで)"], "のもとで で固定"),
    # 里 (り): 里程/一里 は り。サト 誤読。
    "里程": (
        "りてい",
        ["里=り。サトホド/サトテイ 誤読"],
        "りてい で固定 (難語自体は別途言い換え検討)",
    ),
    # 後世 (こうせい): のちせい/ごせ 誤読。
    "後世": ("こうせい", ["後世=こうせい。ノチセイ/ゴセ 誤読"], "こうせい で固定"),
    # 一行 (いちぎょう/いっこう): 文脈依存。数式/文章の 1 行は いちぎょう。
    "一行": (
        "いちぎょう",
        ["一行=いちぎょう(文字列の1行)/いっこう(集団) の多読み"],
        "文脈に応じ いちぎょう or いっこう を明示",
    ),
    # -
    # 数 (かず/すう): 「数で解けない」= かず。Chirp が すう と非決定 (closing_03=スウ /
    #   closing_04=カズ に同表記で割れた実測)。「数学/関数/整数」は含まない specific surface。
    "数で解け": (
        "かず",
        ["数=かず。スウデトケナイ 誤読"],
        "かずで解け で固定 (平仮名直書き)",
    ),
    # 球 (きゅう/たま): 数学の球(sphere)は きゅう。Chirp が たま 誤読。
    #   地球/野球(きゅう)は「球の…」に一致しないので巻き込まない。
    "球の切断": ("きゅう", ["球=きゅう。タマ 誤読"], "きゅうの切断 で固定"),
    "球の体積": ("きゅう", ["球=きゅう。タマ 誤読温床"], "きゅうの体積 で固定"),
    "球の表面": ("きゅう", ["球=きゅう。タマ 誤読温床"], "きゅうの表面 で固定"),
    # 型 (かた/かたち/けい): 数学の型(form/type)は かた。Chirp が かたち 化。
    #   血液型(がた)/模型(けい)は「別の型」「あらゆる型」に一致しないので除外。
    "別の型": ("かた", ["型=かた。カタチ 誤読"], "べつのかた で固定"),
    "あらゆる型": ("かた", ["型=かた。カタチ 誤読温床"], "あらゆるかた で固定"),
    # NOTE(不採用): 三次方程式(さんじ)は Chirp が既定で正読するのが通常で、稀な三乗(さんじょう)
    #   誤読は再ロールで解消する。surface「三次方程式」→さんじ を入れると全 scene で FP 多発
    #   (かな固定しないのが慣行) のため多読み辞書には入れない。耳/STT spot-check で確認する。
    # -
    # 表 (ひょう/おもて): 対数表/一つの表/表を引く は ひょう(table)。Chirp が おもて(surface)化
    #。表面=ひょうめん/代表=だいひょう 等の複合語や
    #   コインの表(=おもて) を巻き込まない具体表層に限る。
    "対数の表": ("ひょう", ["表=ひょう(table)。オモテ 誤読"], "対数のひょう で固定"),
    "つの表": (
        "ひょう",
        ["一つ/二つの表=ひょう。オモテ 誤読"],
        "つのひょう で固定",
    ),
    "表を引": ("ひょう", ["表を引く=ひょうをひく。オモテ 誤読"], "ひょうを引 で固定"),
    # 底 (てい/そこ): 対数/指数の底(base)は てい。Chirp が そこ(bottom)化
    #。海の底/底なし(=そこ) を巻き込まない base 文脈に限る。
    "も底も": (
        "てい",
        ["底=てい(base)。ソコ 誤読"],
        "もていも で固定",
    ),
    "を底と": ("てい", ["X を底とする=ていとする。ソコ 誤読"], "をていと で固定"),
    # -
    # 第九巻 (だいきゅうかん): 九=く/きゅう。Chirp が だいくかん 化。第九=だいく(ベートーヴェン) に引かれる。書物の巻は きゅう。
    "第九巻": (
        "だいきゅうかん",
        ["九=きゅう。ダイクカン 誤読"],
        "だいきゅうかん で固定",
    ),
    # 第七巻 (だいななかん): 七=しち/なな の多読み。書物の巻は なな が明瞭。
    "第七巻": ("だいななかん", ["七=なな/しち の多読み"], "だいななかん で固定"),
    # 何ひとつ (なにひとつ): 何=なに/なん。Chirp が 何 を脱落させ「とひとつ」化。
    "何ひとつ": (
        "なにひとつ",
        ["何=なに。トヒトツ 誤読"],
        "なにひとつ で固定",
    ),
    # 実を結 (実=み/じつ): 「実を結ぶ」idiom は み。ジツ 誤読温床。
    #   yomi="みを" = 固定形「みを結ぶ」に含まれる。果実=かじつ/事実=じじつ 等の複合語は
    #   surface「実を結」に一致しないので巻き込まない。
    "実を結": ("みを", ["実=み。ジツヲムスブ 誤読"], "みを結 で固定"),
    # NOTE(不採用): ある回 で「天文→てんもん」を追加したが、再検証で出荷済み 5 ep
    #   (045/048/049/051/052、計 24 箇所) に FP 発火。確定した 天文→てんぶん 誤読は無く、
    #   Chirp は 天文 を安定して てんもん と読む。三次方程式(さんじ)と同じ「通常正読・FP 多発・
    #   稀な誤読は per-occurrence/再ロールで解消」ケースなので _POLYPHONE には入れない。
}

# ----------------------------------------------------------------------------
# (2) 同音誤解語: {surface: (別語, 言い換え案)}
# ----------------------------------------------------------------------------
_HOMOPHONE = {
    "大数学者": (
        "代数学者 (だいすうがくしゃ)",
        "偉大な数学者 / 大数学者 (だい すうがくしゃ) と分割",
    ),
}

# ----------------------------------------------------------------------------
# (3) 難語/専門硬語 blocklist: {surface: 言い換え案}
# ----------------------------------------------------------------------------
_HARD_WORDS = {
    "里程標": "道しるべ / 節目",
}

# ----------------------------------------------------------------------------
# (7) 発音リスク語 -> 言い換え。読み固定 (_POLYPHONE / SSML <phoneme>) では
# 直らない問題 — 特に **acoustic voicing (か->が 等の濁り)** — は、語そのものを言い換えて
# 回避するのが確実。読み制御は「読み」を固定するが「音の出し方」は変えないため
# (cloud_tts SSML は prosody-neutral)、濁り癖は残りうる。ここは「言い換え戦略」の
# 蓄積辞書: user が耳で見つけた Chirp の発音問題を 1 行足すたび、以後の全 ep で執筆時に
# 言い換えが促され再発が予防される (検出の天井問題を、予防で回避する)。
# 表層は _POLYPHONE と同じく **具体的** にして安全な用法を巻き込まない。
# 値 = (問題の種類, [安全な言い換え候補...], 由来/note)。既定は提案のみ (字幕表示と
# 語感を変えるので人間が承認して narration/speech/cloud を同期置換する)。
# ----------------------------------------------------------------------------
_REPHRASE_RISK = {
    "毎日通い": (
        "か→が 濁り (acoustic voicing)",
        ["毎日足を運び", "毎日通って"],
        "Chirp が「まいにち通い」の か を濁らせ「まいにちがよい」化。"
        "読みは かよい で正しく SSML では直らないので言い換えで回避",
    ),
}

# ----------------------------------------------------------------------------
# (4) 不自然な間を入れやすい構文の正規表現
# ----------------------------------------------------------------------------
# 用言 (動詞終止/連体形) + とは。ひらがな (=活用語尾) 直後の「とは」を近似検出
# (例「解けるとは」「わかるとは」)。除外:
#   * 名詞 + とは (「幾何とは」) = 主題提示で自然 -> 直前 1 文字がひらがな (=活用語尾)
#     の時だけ拾う (lookbehind [ぁ-ん])。
#   * 「ことは」(名詞化 こと + topic 助詞は) = 「入ることは/得ることは/解けることは」等
#     で極めて頻出の自然構文。「と」の直前が「こ」の場合を除外 (最大の FP 源。
#     lookbehind は「と」の直前に効かせる: (?<=[ぁ-ん])(?<!こ)と)。
#   * 「とは言え/とはいえ/とはいうものの」= 接続表現で自然 -> 直後が 言/い/ず/ぜ を除外。
_VERB_TOWA_RE = re.compile(r"(?<=[ぁ-ん])(?<!こ)とは(?![ずぜ言い])")
# 長い主語 + は、: 名詞句 (漢字/カタカナ/ひらがな/長音/中点) が概ね 8 文字超 続いた
# 直後の「は、」(topic 助詞 + 読点)。Chirp が主語末で長い間を空けやすい。
_LONG_SUBJECT_HA_RE = re.compile(r"([一-鿿ぁ-んァ-ヶーー・]{8,})は、")


def _clean(line: str) -> str:
    """字幕分割マーカー '|' を除去。"""
    return line.replace("|", "")


def _iter_scenes(scene_def: dict):
    """(scene_id, index, narration_line, cloud_line) を yield。cloud は無ければ空文字。"""
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "?")
            narration = scene.get("narration", []) or []
            cloud = scene.get("narration_speech_cloud") or []
            for i, narr in enumerate(narration):
                if not isinstance(narr, str):
                    continue
                narr_c = _clean(narr)
                cloud_c = _clean(cloud[i]) if i < len(cloud) and isinstance(cloud[i], str) else ""
                yield sid, i, narr_c, cloud_c


def _scan_polyphone(sid, idx, narr, cloud):
    """(1) 多読み漢字が narration にあり cloud で読み未固定なら WARN。"""
    out = []
    # cloud が空 (narration_speech_cloud 未設定) の場合は narration 自身を読み源とみなす。
    read_src = cloud if cloud else narr
    for surface, (yomi, notes, fix) in _POLYPHONE.items():
        if surface not in narr:
            continue
        if yomi in read_src:
            continue  # 読み固定済み = OK
        if any(k in surface for k in _SSML_FORCED):
            continue  # cloud_tts._READING_OVERRIDES で SSML 合成時固定済み = OK (二乗 等)
        out.append(
            {
                "type": "polyphone",
                "scene_id": sid,
                "index": idx,
                "surface": surface,
                "detail": narr,
                "note": (
                    f"多読み「{surface}」の読み「{yomi}」が narration_speech_cloud に無い "
                    f"(Chirp 自動読み任せ)。誤読リスク: {'; '.join(notes)}。対処: {fix}"
                ),
            }
        )
    return out


def _scan_kei_unit(sid, idx, narr, cloud):
    """(1b) 数の位「京」(=けい) が数字直後にあり cloud で けい 未固定なら WARN。"""
    read_src = cloud if cloud else narr
    if not _KEI_UNIT_RE.search(narr) or "けい" in read_src:
        return []
    return [
        {
            "type": "kei_unit",
            "scene_id": sid,
            "index": idx,
            "surface": "京 (位=けい)",
            "detail": narr,
            "note": (
                "数の位「京」(=けい、10^16) が数字直後にあり cloud で読み未固定。"
                "Chirp が きょう(都市) と誤読しうる。"
                "けい で固定推奨 (例: 1844けい)"
            ),
        }
    ]


def _scan_standalone_num(sid, idx, narr, cloud):
    """(1c) 単独の「数」(かず/すう 多読み) が cloud で読み未固定なら WARN。

    複合語 (素数/数列/因数/数学/十数/リュカ数/メルセンヌ数 等) は _STANDALONE_NUM_RE の
    前後 lookaround (漢字/カタカナ/長音/々) で自動除外。かず/すう どちらの明示も無い
    (= Chirp 自動読み任せ) 場合のみ WARN。かず(具体的な数)か すう(抽象概念) は文脈依存
    なので特定読みは強制せず「per-context で明示せよ」と促す。"""
    if not _STANDALONE_NUM_RE.search(narr):
        return []
    read_src = cloud if cloud else narr
    if "かず" in read_src or "すう" in read_src:
        return []  # 何らかの読み明示あり = OK
    return [
        {
            "type": "standalone_num",
            "scene_id": sid,
            "index": idx,
            "surface": "数 (かず/すう)",
            "detail": narr,
            "note": (
                "単独の「数」は かず/すう の多読みで Chirp が非決定 "
                "。文脈に応じ "
                "かず(具体的な数) か すう(抽象概念) を narration_speech_cloud に平仮名明示推奨"
            ),
        }
    ]


def _scan_homophone(sid, idx, narr, cloud):
    """(2) 同音誤解語が narration/cloud にあれば言い換えを促す。"""
    out = []
    for text, tag in (("narration", narr), ("cloud", cloud)):
        for surface, (collide, rephrase) in _HOMOPHONE.items():
            if surface in tag:
                out.append(
                    {
                        "type": "homophone",
                        "scene_id": sid,
                        "index": idx,
                        "surface": surface,
                        "detail": tag,
                        "note": f"「{surface}」は {collide} と同音で誤解を招く ({text})。言い換え: {rephrase}",
                    }
                )
    return out


def _scan_hard_words(sid, idx, narr, cloud):
    """(3) 難語 blocklist に該当すれば平易化を促す。"""
    out = []
    for text, tag in (("narration", narr), ("cloud", cloud)):
        for surface, rephrase in _HARD_WORDS.items():
            if surface in tag:
                out.append(
                    {
                        "type": "hard",
                        "scene_id": sid,
                        "index": idx,
                        "surface": surface,
                        "detail": tag,
                        "note": f"難語「{surface}」({text})。視聴者向けに平易化: {rephrase}",
                    }
                )
    return out


def _scan_pause_syntax(sid, idx, narr, cloud):
    """(4) Chirp が不自然な間を入れやすい構文 (用言+とは / 長主語+は、)。"""
    out = []
    # narration_speech_cloud があればそれ (実際に合成されるテキスト)、無ければ narration。
    target = cloud if cloud else narr
    for m in _VERB_TOWA_RE.finditer(target):
        ctx = target[max(0, m.start() - 6) : m.end() + 2]
        out.append(
            {
                "type": "pause_towa",
                "scene_id": sid,
                "index": idx,
                "surface": ctx,
                "detail": target,
                "note": (
                    f"用言 + 「とは」(…{ctx}…)。Chirp が「とは」前で不自然な間を入れやすい。"
                    "「というのは」化 or 文分割を検討"
                ),
            }
        )
    for m in _LONG_SUBJECT_HA_RE.finditer(target):
        subj = m.group(1)
        out.append(
            {
                "type": "pause_long_subject",
                "scene_id": sid,
                "index": idx,
                "surface": subj + "は、",
                "detail": target,
                "note": (
                    f"長い主語 (約{len(subj)}文字) + 「は、」。主語末で間が入りやすい。"
                    "主語を短縮するか文を分割"
                ),
            }
        )
    return out


def _scan_blanket_wa(sid, idx, narr, cloud):
    """(5) narration_speech_cloud の一括 は→わ 変換を検出。

    script_generator は cloud を出さず gen_cloud_readings が **native は** で生成する
    (コンマ孤立助詞のみ わ 化)。しかし legacy/手書きの scene_def に「全ての は を わ
    にした」cloud が残ると gen_cloud は既存を保存し素通りする。
    narration が は を 2 つ以上持つのに cloud が は 0・わ 複数なら一括変換の疑いで WARN
    (native cloh は語中 では/には を は のまま残すので は 0 は異常)。
    """
    if not cloud:
        return []
    h_narr = narr.count("は")
    h_cloud = cloud.count("は")
    w_cloud = cloud.count("わ")
    if h_narr >= 2 and h_cloud == 0 and w_cloud >= h_narr:
        return [
            {
                "type": "blanket_wa",
                "scene_id": sid,
                "index": idx,
                "surface": "は→わ",
                "detail": cloud,
                "note": (
                    f"narration は は×{h_narr} なのに cloud は は×0・わ×{w_cloud} = "
                    "一括 は→わ 変換の疑い。native は へ戻す (gen_cloud_readings --force で "
                    "再生成、コンマ孤立助詞のみ わ)。語中 は の わ 化はアクセント崩れ+"
                    "「わ、」境界の余分音挿入 (phantom) を招く"
                ),
            }
        ]
    return []


_BRACKET_CHARS = "《》「」『』（）()"


def _strip_brackets(s: str) -> str:
    return "".join(ch for ch in s if ch not in _BRACKET_CHARS)


def _scan_inline_particle_wa(sid, idx, narr, cloud):
    """(6) narration_speech_cloud のインライン助詞 は→わ 過剰変換を検出。

    script_generator が topic/subject 助詞 は を わ 表記に変換すると、Chirp3-HD は わ を
    独立モーラとして読み、境目に微小な間が入って不自然になる。gen_cloud_readings は本来 native は を残す設計 (コンマ孤立
    助詞のみ わ 化)。ゆえに cloud の わ が「元の narration では は だった助詞」なら過剰変換。

    narration (は=ground truth) と cloud を《》「」除去で文字整列し、は→わ の 1 文字置換
    (=過剰変換された助詞) を数える。`_scan_blanket_wa` (全 は→わ=cloud に は が 0) の
    **部分変換版** で、は が一部残っていても検出する。難点: コンマ孤立助詞由来の正当な わ も
    稀に混じりうる (advisory なので人間が確認)。にわ/でわ/のわ/とわ や 語幹内の 終わ/変わ/
    わずか 等の本物の わ は narration 側も わ なので置換にならず誤検出しない。
    """
    if not cloud:
        return []
    n = _strip_brackets(narr)
    c = _strip_brackets(cloud)
    subs = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, n, c, autojunk=False).get_opcodes():
        if tag == "replace":
            for k in range(min(i2 - i1, j2 - j1)):
                if n[i1 + k] == "は" and c[j1 + k] == "わ":
                    subs += 1
    if subs == 0:
        return []
    return [
        {
            "type": "inline_particle_wa",
            "scene_id": sid,
            "index": idx,
            "surface": f"は→わ ×{subs}",
            "detail": cloud,
            "note": (
                f"インライン助詞 は→わ 過剰変換 ×{subs} (narration は→cloud わ)。"
                "Chirp3-HD は独立 わ の境目に微小な間を入れ不自然化 (A/B 実測 約25%長)。"
                "native は へ戻す (gen_cloud_readings は本来非変換)。"
                "※ コンマ孤立助詞由来の わ は正当"
            ),
        }
    ]


def _scan_rephrase_risk(sid, idx, narr, cloud):
    """(7) 発音リスク語を検出し、安全な言い換えを提案。

    _POLYPHONE (読み固定) / SSML で直らない Chirp の発音問題 (特に濁り か->が) を、
    語を言い換えて回避する。narration (=字幕表示。言い換えると表示も変わる) を走査。
    提案のみ (人間が承認して narration/narration_speech/narration_speech_cloud を同期置換)。
    """
    out = []
    for surface, (problem, alts, note) in _REPHRASE_RISK.items():
        if surface in narr:
            out.append(
                {
                    "type": "rephrase_risk",
                    "scene_id": sid,
                    "index": idx,
                    "surface": surface,
                    "detail": narr,
                    "note": (
                        f"発音リスク「{surface}」({problem})。読み固定では直りにくいので"
                        f"言い換え推奨: {' / '.join(alts)}。{note}"
                    ),
                }
            )
    return out


# Raw formula tokens surviving into the CLOUD reading (the synthesis text) that Chirp
# mis-voices: letter+apostrophe (f'), '=' touching a letter (L=T-V), a superscript ^
# after a letter (x^2), or a standalone Lagrange point L1..L5. gen_cloud.
# spell_formula_tokens auto-fixes the common forms; this flags any that survived
# (hand-tuned/legacy cloud, or a form not yet in the dictionary) BEFORE synthesis.
_RAW_FORMULA_RE = re.compile(
    r"[A-Za-z]'|=[A-Za-z]|[A-Za-z]=|\bL[1-5](?![0-9A-Za-z])|[A-Za-zα-ωΑ-Ω]\^"
)
# Case particle + 読点 (を、に、へ、が) which Chirp lengthens the pre-comma vowel on.
# Capturing so per-particle repetition can be counted. Excludes は (topic-marker, the
# _LONG_SUBJECT_HA_RE domain) and enumeration particles も/と/で (「AもBもCも」 is a
# natural list, not the 「図を、…そのものを、」からー図をー elongation).
_PARTICLE_COMMA_RE = re.compile(r"([をにへが])、")
# Digits (ASCII + full-width) masked to detect intentional parallel enumerations whose
# only difference is numbers (four-square examples), which are NOT reword duplicates.
_DIGIT_MASK_RE = re.compile(r"[0-9０-９]")


def _scan_raw_formula(sid, idx, narr, cloud):
    """(1d) 生の数式トークン (L=T-V, f'(x), Lₙ, x^2) が cloud=合成テキストに残存すると
    Chirp が誤読 (ある回 f'(x)->エフゴエックス, 生 L=T-V)。narration (字幕表示) の記号は
    許容 -- 合成テキスト (narration_speech_cloud) のみ対象。gen_cloud.spell_formula_tokens
    が主要形を自動スペルアウトするので、通常は 0。取りこぼしの backstop。"""
    if not cloud:
        return []
    m = _RAW_FORMULA_RE.search(cloud)
    if not m:
        return []
    return [
        {
            "type": "raw_formula",
            "scene_id": sid,
            "index": idx,
            "surface": m.group(0),
            "detail": cloud,
            "note": (
                "cloud=合成テキストに生の数式トークンが残存 -> Chirp 誤読リスク "
                "(ある回 f'(x)->エフゴエックス)。narration_speech_cloud にカナ読みを明示 "
                "(例: エル・イコール・ティー・マイナス・ブイ / エフ・プライム・エックス)"
            ),
        }
    ]


_BARE_FRACTION_RE = re.compile(r"([0-9０-９]+)\s*[/／∕]\s*([0-9０-９]+)")


def _scan_bare_fraction(sid, idx, narr, cloud):
    """(1e) 合成テキスト (narration_speech_cloud) に生の分数 "N/M" が残ると Chirp が
    分数として読むか非決定。分数は「M分のN」等でスペルアウトして読みを固定する。
    narration (字幕表示) の N/M は許容 -- cloud のみ対象。gen_cloud はスラッシュ分数を
    自動スペルアウトしないので backstop。advisory。

    分子/分母のどちらかが 3 桁以上のときだけ WARN する: 22/7・1/2 等の短い分数は Chirp が
    分数として安定して読む。
    棒読みが観測されたのは 355/113 のような桁数の多い分数で、その閾値に calibrate。"""
    if not cloud:
        return []
    for m in _BARE_FRACTION_RE.finditer(cloud):
        num, den = m.group(1), m.group(2)
        if len(num) < 3 and len(den) < 3:
            continue  # short fraction: Chirp reads it as a fraction reliably
        return [
            {
                "type": "bare_fraction",
                "scene_id": sid,
                "index": idx,
                "surface": m.group(0),
                "detail": cloud,
                "note": (
                    "cloud=合成テキストに桁数の多い生の分数 N/M が残存 -> Chirp が分数か"
                    "非決定読み。narration_speech_cloud で "
                    "「M分のN」にスペルアウトして固定 "
                    "(例: 355/113 -> ひゃくじゅうさんぶんのさんびゃくごじゅうご)"
                ),
            }
        ]
    return []


def _scan_comma_elongation(sid, idx, narr, cloud):
    """(7) 1文に読点が多く助詞+読点が連続すると Chirp が読点前の母音を伸ばし不自然。
    合成テキスト (cloud 優先) の読点>=3 かつ 助詞+読点>=2 で advisory。"""
    read = cloud if cloud else narr
    if not read:
        return []
    n_comma = read.count("、")
    # The elongation is the SAME particle+読点 repeated (を、…を、)
    # 「図を、…幾何学そのものを、」からー図をー そのものをー。A list of varied noun+読点
    # (person_08 「サルデーニャ王、…ルイ16世、…ナポレオンと、」) is a natural enumeration,
    # not this, so count per-particle repetition rather than raw 助詞+読点 total.
    parts = collections.Counter(m.group(1) for m in _PARTICLE_COMMA_RE.finditer(read))
    max_rep = max(parts.values(), default=0)
    if n_comma >= 3 and max_rep >= 2:
        return [
            {
                "type": "comma_elong",
                "scene_id": sid,
                "index": idx,
                "surface": f"読点{n_comma}/同一助詞+読点{max_rep}",
                "detail": read,
                "note": (
                    "1文に読点/助詞+読点が多く Chirp が読点前で母音を伸ばす risk "
                    "。読点を減らす/「まで」等で助詞+読点の連続を崩す"
                ),
            }
        ]
    return []


def _dup_bigrams(s: str) -> set:
    s = _clean(s).replace("、", "").replace("。", "")
    return {s[i : i + 2] for i in range(len(s) - 1)}


def _scan_adjacent_dup(sid, narration):
    """(8) 隣接する narration 要素がほぼ言い直しの重複 (文字bigram overlap係数>=0.5、数字のみ
    差の並列テンプレは除外)。
    ある回「一流の数学者に師事することなく…独学で高等数学を身につけて」と
    [5]「一流の師につくことなく…独力で高等数学を身につけて」。scene 単位 (per-element
    scan では隣接比較できない)。advisory -- 片方を削除/差別化する。"""
    out = []
    for i in range(len(narration) - 1):
        a, b = narration[i], narration[i + 1]
        if not isinstance(a, str) or not isinstance(b, str):
            continue
        ga, gb = _dup_bigrams(a), _dup_bigrams(b)
        if len(ga) < 5 or len(gb) < 5:
            continue
        inter = len(ga & gb)
        # overlap coefficient (∩ / min) -- catches a reworded near-subset even when the
        # two lengths differ. ある回=0.57 vs normal adjacent <=0.11.
        overlap = inter / min(len(ga), len(gb))
        if inter < 5 or overlap < 0.5:
            continue
        # Exclude intentional parallel enumerations that differ only in numbers:
        # once digits are masked they collapse to the same template, so a near-identical
        # digit-masked overlap means a deliberate list, not a reword.
        ma, mb = _dup_bigrams(_DIGIT_MASK_RE.sub("#", a)), _dup_bigrams(_DIGIT_MASK_RE.sub("#", b))
        if ma and mb and len(ma & mb) / min(len(ma), len(mb)) >= 0.9:
            continue
        out.append(
            {
                "type": "adjacent_dup",
                "scene_id": sid,
                "index": i,
                "surface": f"[{i}]≈[{i + 1}] (overlap {overlap:.2f})",
                "detail": f"{_clean(a)[:28]} / {_clean(b)[:28]}",
                "note": (
                    "隣接 narration がほぼ言い直しの重複。"
                    "片方を削除するか内容を差別化する"
                ),
            }
        )
    return out


def run_lint(scene_path: str) -> list:
    """scene_definition.json を走査して WARN dict のリストを返す。"""
    with open(scene_path, encoding="utf-8") as f:
        scene_def = json.load(f)

    warnings = []
    for sid, idx, narr, cloud in _iter_scenes(scene_def):
        warnings.extend(_scan_polyphone(sid, idx, narr, cloud))
        warnings.extend(_scan_kei_unit(sid, idx, narr, cloud))
        warnings.extend(_scan_standalone_num(sid, idx, narr, cloud))
        warnings.extend(_scan_homophone(sid, idx, narr, cloud))
        warnings.extend(_scan_hard_words(sid, idx, narr, cloud))
        warnings.extend(_scan_pause_syntax(sid, idx, narr, cloud))
        warnings.extend(_scan_blanket_wa(sid, idx, narr, cloud))
        warnings.extend(_scan_inline_particle_wa(sid, idx, narr, cloud))
        warnings.extend(_scan_rephrase_risk(sid, idx, narr, cloud))
        warnings.extend(_scan_raw_formula(sid, idx, narr, cloud))
        warnings.extend(_scan_bare_fraction(sid, idx, narr, cloud))
        warnings.extend(_scan_comma_elongation(sid, idx, narr, cloud))
    # scene 単位 (隣接要素比較) の scan
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            warnings.extend(
                _scan_adjacent_dup(scene.get("scene_id", "?"), scene.get("narration", []) or [])
            )
    return warnings


_CATEGORY_TAG = {
    "polyphone": "多読み未固定",
    "kei_unit": "位(京=けい)",
    "standalone_num": "多読み(数=かず/すう)",
    "homophone": "同音誤解",
    "hard": "難語",
    "pause_towa": "間(とは)",
    "pause_long_subject": "間(長主語)",
    "blanket_wa": "一括は→わ",
    "inline_particle_wa": "助詞は→わ過剰変換",
    "rephrase_risk": "発音リスク(言い換え推奨)",
    "raw_formula": "生記号(L=T-V/f'(x)等)",
    "bare_fraction": "生分数(N/M)",
    "comma_elong": "コンマ伸ばし",
    "adjacent_dup": "隣接文重複",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cloud TTS (Chirp3-HD) narration の読み誤り温床 静的 lint"
    )
    parser.add_argument("scene_definition", help="scene_definition.json のパス")
    parser.add_argument(
        "--strict", action="store_true", help="WARN があれば exit 1 (既定は exit 0)"
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  Cloud Reading Lint (Chirp3-HD 読み誤り温床 pre-build check)")
    print("=" * 64)

    if not os.path.exists(args.scene_definition):
        print(f"  [ERROR] not found: {args.scene_definition}")
        return 2

    warnings = run_lint(args.scene_definition)

    if not warnings:
        print("\n  RESULT: PASS (読み誤りの温床は検出されませんでした)")
        return 0

    counts = {}
    for w in warnings:
        counts[w["type"]] = counts.get(w["type"], 0) + 1
    summary = " / ".join(f"{_CATEGORY_TAG.get(k, k)} {v}" for k, v in sorted(counts.items()))
    print(f"\n  [WARN] {len(warnings)} 件検出 ({summary}):")
    for w in warnings:
        tag = _CATEGORY_TAG.get(w["type"], w["type"])
        print(f"    - [{tag}] {w['scene_id']}[{w['index']}] 「{w['surface']}」")
        print(f"        {w['note']}")
    print("\n  対処: (1)多読みは narration_speech_cloud にひらがなで読み固定 or SSML phoneme、")
    print("        (2)同音誤解語は言い換え、(3)難語は平易化、(4)間の構文は文分割/言い換え。")
    print(f"\n  RESULT: {'FAIL' if args.strict else 'WARN'} ({len(warnings)} 件)")
    if warnings:
        try:
            _src = os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
            )
            if _src not in sys.path:
                sys.path.insert(0, _src)
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("cloud_reading_lint", len(warnings))
        except Exception:
            pass
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
