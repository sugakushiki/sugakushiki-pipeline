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
  (5) episode_config.pronunciation_high_risk が名指しした語が、narration_speech_cloud に
      元の表記のまま残っている (= 読み未固定)。あの欄は人間が手で作った危険語リストなのに
      cloud 合成では誰も読まないので、書いただけでは効かなかった (ある回の「根」)。

narration は sd["sections"][i]["scenes"][j]["narration"] (list of str)。
narration_speech_cloud も同構造 (任意)。字幕マーカー "|" は除去して判定する。
(5) だけは scene_definition.json の隣の episode_config.json も読む。

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
try:
    from speech_source import cloud_array_status  # 合成で捨てられる cloud 配列を見分ける
except Exception:  # noqa: BLE001

    def cloud_array_status(scene):  # type: ignore[misc]
        arr = scene.get("narration_speech_cloud")
        if arr is None:
            return "missing"
        return "ok" if len(arr) == len(scene.get("narration") or []) else "length_mismatch"


try:
    from cloud_reading_config import load_cloud_reading_config  # 読み設定の唯一の loader
except Exception:  # noqa: BLE001 - src が無い環境では episode 側の設定を空扱いにする

    def load_cloud_reading_config(_path):  # type: ignore[misc]
        from types import SimpleNamespace

        return SimpleNamespace(
            overrides={}, direct_kana=(), high_risk=[], forced_surfaces=frozenset()
        )


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
# ある回実績 + memory 由来の既知誤読を初期値に。測ってから足すこと。
# ----------------------------------------------------------------------------
_POLYPHONE = {
    # ── ある回 (user 耳で 3 語) ──
    # 十分 (じゅうぶん=enough / じゅっぷん=10 分): Chirp は「十分に多くの人を」を
    # じゅっぷん と読んだ。分数「五十分の一」「十分の一」は ぶん で別物 (EXCLUDE)。
    "十分": (
        ("じゅうぶん", "じゅっぷん"),
        ["十分=じゅうぶん (enough) を ジュップン (10 分) と読む"],
        "narration_speech_cloud に じゅうぶん (または じゅっぷん) を平仮名で明示",
    ),
    # 四つ (よっつ / よつ): 「そのうち四つは」を よつは と読んだ。四つ角=よつかど 等は EXCLUDE。
    "四つ": (
        ("よっつ", "よつ"),
        ["四つ=よっつ を ヨツ と読む"],
        "narration_speech_cloud に よっつ を平仮名で明示",
    ),
    # 正に (せいに=positive / まさに=exactly): 「確率が正になります」を まさに と読んだ。
    # 数学の「正になる」は せいに、副詞は まさに。どちらも実在するので固定せず明示を求める。
    "正に": (
        ("せいに", "まさに"),
        ["正に=せいに (符号が正) を マサニ と読む"],
        "narration_speech_cloud に せいに / まさに を平仮名で明示 (または「ゼロより大きく」に言い換え)",
    ),
    # ── ある回 (user 耳で 3 語。文単位 wav の STT で裏取り) ──
    # 天が (てん / あま): 「天が動くか」「天が動き」を アマ と読んだ (math_07 / math_08)。
    # 天体・天球・天文 は複合語で てん に安定するので surface は 天が に限る。
    "天が": (
        ("てんが", "あまが"),
        ["天が=てんが (天球) を アマガ と読む (ある回 STT 実測)"],
        "narration_speech_cloud に てんが を平仮名で明示",
    ),
    # 労に/労を (ろう): 「翻訳の労に対して」を ドク/トコ のように読んだ (person_07)。
    # 労う=ねぎらう は surface が違うので当たらない。
    "労に": (
        ("ろうに",),
        ["労=ろう を誤読 (ある回 STT=ドク)"],
        "労 を ろう と平仮名で明示",
    ),
    "労を": (("ろうを",), ["労=ろう を誤読 (ある回の型)"], "労 を ろう と平仮名で明示"),
    # 退け (しりぞけ / どけ): 「占星術を退け、」を トケ、「退けた」を ドケタ と読んだ
    # (closing_02 / math_08)。退ける=どける も実在するので固定せず明示を求める。
    # 退ける/退けた は 退け を含むので一つの surface で全活用に当たる。
    "退け": (
        ("しりぞけ", "どけ"),
        ["退け=しりぞけ を トケ / ドケ と読む (ある回・math_08 STT 実測)"],
        "narration_speech_cloud に しりぞけ を平仮名で明示、または cloud_reading_overrides で SSML 固定",
    ),
    # 入 (はいる/いれる): 入学文脈の可能形「入れ(ません)」は はいれ。イレ 誤読。
    # 「踏み入れ」「手に入れ」は いれ で正しいので surface に含めず、
    # possible-form の "に入れ" (…に入れる/入れない) を狙う。
    "に入れま": (
        "はいれ",
        ["入=いれ と読み はいれない/はいれません を イレ 化"],
        "大学に入れ->はいれ で固定",
    ),
    "に入れる": ("はいれ", ["入=いれ の可能形を イレル 化"], "はいれる で固定"),
    # その間 (そのあいだ/そのかん): ある回「その間の値も定義できます」を
    # そのかん と読んだ (user 耳)。どちらの読みも実在し (書き言葉の そのかん は
    # 「その期間」の意で正しい) 文脈依存なので force には入れず advisory に留める。
    # 全68話で 3 回 / 3 話。うち 1 件は「その間隔」= かんかく で **別語** なので
    # _POLYPHONE_EXCLUDE で外す (部分一致の罠)。
    "その間": (
        "そのあいだ",
        ["その間=そのあいだ(空間的な あいだ)/そのかん(時間的な 期間)"],
        "narration が空間の あいだ を指すなら そのあいだ と明記",
    ),
    # 馬上 (ばじょう): ある回で誤読 (出荷 wav STT が『杖で/バで』と聞き取り、user 耳)。
    "馬上": (
        "ばじょう",
        ["馬上=ばじょう。バ/ウマウエ 系の崩れ (ある回、user 耳)"],
        "ばじょうで で固定",
    ),
    # 羽 (わ/はね/う): 数詞+羽 の助数詞を ハ 化。
    # 出荷 66 ep の較正: 数詞+羽 は ある回の 1 件のみ (2026-08-17 実測)。1羽/一羽 の 2 表層に絞る (羽根/羽ばたき は不変)。
    "1羽": (
        "いちわ",
        ["羽=わ (助数詞)。1羽 を イチハ 化 (ある回、user 耳)"],
        "いちわ で固定",
    ),
    "一羽": (
        "いちわ",
        ["羽=わ (助数詞)。一羽 を イチハ 化しうる (ある回と同型)"],
        "いちわ で固定",
    ),
    # 下りる (おりる) / 下る (くだる): 送り仮名「下り」でも Chirp が クダリ 化。
    # 出荷 66 ep の較正: 「下り」は ある回の 1 件のみ (2026-08-17 実測)。否定形「下りず」だけ狙う (下り坂=くだり は表層が異なる)。
    "下りず": (
        "おりず",
        ["下り=おり。許可は下りず を クダリズ 化 (ある回、user 耳)"],
        "おりず で固定",
    ),
    # 乗 (じょう/のり): カタカナ変数直後の指数の乗を ノリ 化。
    # 二乗/累乗 は安定。出現の較正: cloud 回では 049 (ピー乗/エヌ乗) と 066 のみ (2026-08-18 掃引)。
    "ックス乗": (
        "じょう",
        ["乗=じょう (指数)。エックス乗 を ノリ 化 (ある回、user 耳)"],
        "えっくすじょう 等かなで固定",
    ),
    "ヌ乗": (
        "じょう",
        ["乗=じょう (指数)。エヌ乗 も同型 (ある回出荷 narration に出現)"],
        "えぬじょう 等かなで固定",
    ),
    "ピー乗": (
        "じょう",
        ["乗=じょう (指数)。ピー乗 も同型 (ある回出荷 narration に出現)"],
        "ぴーじょう 等かなで固定",
    ),
    # 主著 (しゅちょ): Chirp が しゅちょう (主張) 化。
    # 対照実験 (2026-08-18): 平仮名固定も phoneme 固定も長音側に揺れ、安定したのは言い換えのみ。
    "主著": (
        "しゅちょ",
        [
            "主著=しゅちょ が シュチョウ (主張) 化。かな固定/phoneme 固定でも揺れる (実験 2026-08-18)"
        ],
        "『主な著書』等へ言い換える (読み固定では安定しない)",
    ),
    # 志 (こころざし/し): 裸の志は シ 音読み化。志望/意志 等の複合語を巻き込まないよう「その志」だけ狙う。
    "その志": (
        "こころざし",
        ["志=こころざし。シ 音読み化 (ある回、user 耳 + 出荷 wav STT『そのしは』)"],
        "そのこころざし で固定",
    ),
    # 表 (ひょう/おもて): 裸の表は頻出しすぎるので「表全体」だけ狙う (天文表/発表/表紙 は安定)。
    "表全体": (
        "ひょうぜんたい",
        ["表=ひょう。オモテ 誤読 (ある回、user 耳)"],
        "ひょうぜんたい で固定",
    ),
    # 値 (あたい/ね): 形容詞直後の裸の値 (正しい値/正確な値/近い値) を ネ 化。
    # 出荷 65 ep の較正: い値 4 件 / な値 9 件、全て あたい が正の同型文脈 (2026-08-16 実測)。
    # 「の値」(25 件) は πの値/関数の値 等が頑健なので入れない。
    "い値": (
        "あたい",
        ["値=あたい。正しい値 を ネ 化 (ある回、user 耳 + 出荷 wav STT『正しい根』)"],
        "あたい で固定",
    ),
    "な値": ("あたい", ["値=あたい。正確な値 等を ネ 化しうる (ある回と同型)"], "あたい で固定"),
    # 命 (めい/いのち): 命令の意の「〜の命による/命を受け」は めい。イノチ 誤読。
    # 較正: 出荷 65 ep で 命による 1 件 + 命を受け 1 件 のみ。
    "命による": (
        "めい",
        ["命=めい (命令)。イノチ 誤読 (ある回、user 耳)"],
        "のめいによる で固定",
    ),
    "命によって": ("めい", ["命=めい (命令)。イノチ 誤読"], "のめいによって で固定"),
    "命により": ("めい", ["命=めい (命令)。イノチ 誤読"], "のめいにより で固定"),
    "命を受け": ("めい", ["命=めい (命令)。イノチ 誤読"], "めいをうけ で固定"),
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
    # 偽 (ぎ/にせ/いつわる): 述語の「偽」は ぎ。ある回で Chirp が ニセ と読み user が
    #   耳で拾った (出荷 wav の STT でも「コノホダイワ ニセ デシタ」を確認)。
    #   surface を述語形に限定するのは、「偽って」= いつわって と「真偽」= しんぎ を
    #   巻き込まないため。
    #   出荷 64 本での実測: 下記 5 surface で 6 件ヒット、いずれも ぎ が正しい。
    "偽でし": ("ぎ", ["偽=ぎ。ニセ 誤読 (ある回で出荷 wav の STT が確認)"], "ぎでした で固定"),
    "偽です": ("ぎ", ["偽=ぎ。ニセ 誤読"], "ぎです で固定"),
    "偽か": ("ぎ", ["偽=ぎ。真か偽か の述語。ニセ 誤読"], "ぎか で固定"),
    "偽が": ("ぎ", ["偽=ぎ。真と偽が の述語。ニセ 誤読"], "ぎが で固定"),
    "偽という": ("ぎ", ["偽=ぎ。ニセ 誤読"], "ぎという で固定"),
    # 床 (とこ/ゆか/しょう): 「の床」は とこ。ユカ 誤読。「病床」「臨床」は しょう で
    #   正しく読まれるので surface を「の床」に限定する (出荷 4 件中 3 件が複合語)。
    "の床": ("とこ", ["床=とこ。ユカ 誤読 (死の床/病の床)"], "のとこ で固定"),
    # 正義 (せいぎ): 「不正義」を Chirp が人名 まさよし と読んだ。
    "不正義": ("ふせいぎ", ["正義=せいぎ。マサヨシ と人名読み (ある回 user 耳)"], "ふせいぎ で固定"),
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
    # 環 (かん/わ): 代数の環 (可換環・多項式環・整数環) は かん。Chirp は「わ」と読む
    #   (実測: 「その足し算と掛け算の構造を環と呼びます」が STT で「構造はと呼びます」、
    #   「どんな環の上でも」が「どんなワの上でも」)。**環境/循環/一環を巻き込まない表層に限定**する
    #   ため、助詞・後続語まで含めた形で登録する (環境を/循環性 は下記のどれにも一致しない)。
    "環を": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんを で固定 (環境/循環は別語)"),
    "環は": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんは で固定"),
    "環から": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんから で固定"),
    "環の上": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんのうえ で固定"),
    "環と呼": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんとよ で固定"),
    "環における": ("かん", ["環=かん(代数の環)。ワ 誤読"], "かんにおける で固定"),
    # 包み込む (つつみこむ/くるみこむ): 包=つつむ が既定だが Chirp は くるみこむ と読む。
    "包み込": ("つつみこ", ["包=つつむ。クルミコ 誤読"], "つつみこ で固定"),
    # 後世 (こうせい): のちせい/ごせ 誤読。
    "後世": ("こうせい", ["後世=こうせい。ノチセイ/ゴセ 誤読"], "こうせい で固定"),
    # 一行 (いちぎょう/いっこう): 文脈依存。数式/文章の 1 行は いちぎょう。
    "一行": (
        "いちぎょう",
        ["一行=いちぎょう(文字列の1行)/いっこう(集団) の多読み"],
        "文脈に応じ いちぎょう or いっこう を明示",
    ),
    # 二点 (にてん): ある回で Chirp が同一文中の 2 回を にてん / ふたてん に割った
    # (user 耳検出)。数学文脈の「二点」は常に にてん で文脈非依存なので surface 一致で安全
    # (第二点/二点鎖線/十二点 も にてん)。
    "二点": (
        "にてん",
        ["二点=にてん。フタテン 誤読 (ある回、同一文で読みが割れた)"],
        "にてん で固定",
    ),
    # --- 耳検出、Cloud が非決定的に割れた多読み ---
    # 数 (かず/すう): 「数で解けない」= かず。Chirp が すう と非決定 (closing_03=スウ /
    #   closing_04=カズ に同表記で割れた実測)。「数学/関数/整数」は含まない specific surface。
    "数で解け": (
        "かず",
        ["数=かず。スウデトケナイ 誤読 (ある回、同一漢字表記で かず/すう に割れる)"],
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
    # --- 出荷 wav STT 検出、Cloud が誤読した多読み ---
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
        ["底=てい(base)。ソコ 誤読 (ある回指数も底も=ソコ)"],
        "もていも で固定",
    ),
    "を底と": ("てい", ["X を底とする=ていとする。ソコ 誤読"], "をていと で固定"),
    # --- 耳/STT 検出、Cloud が誤読した多読み ---
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
        ["何=なに。トヒトツ 誤読 (ある回、何 が脱落)"],
        "なにひとつ で固定",
    ),
    # 実を結 (実=み/じつ): 「実を結ぶ」idiom は み。ジツ 誤読温床。
    #   yomi="みを" = 固定形「みを結ぶ」に含まれる。果実=かじつ/事実=じじつ 等の複合語は
    #   surface「実を結」に一致しないので巻き込まない。
    "実を結": ("みを", ["実=み。ジツヲムスブ 誤読"], "みを結 で固定"),
    # NOTE(不採用): ある回で「天文→てんもん」を追加したが、再検証で出荷済み 5 ep
    #   (045/048/049/051/052、計 24 箇所) に FP 発火。確定した 天文→てんぶん 誤読は無く、
    #   Chirp は 天文 を安定して てんもん と読む。三次方程式(さんじ)と同じ「通常正読・FP 多発・
    #   稀な誤読は per-occurrence/再ロールで解消」ケースなので _POLYPHONE には入れない。
    # --- user が耳で検出。どれも辞書に無く、合成前に一件も警告できなかった ---
    # 黒板 (こくばん): Chirp が クロイタ と読む。**同一エピソード内で割れる** — ある回は
    #   closing_01 だけ コクバン で intro_01/intro_02 が クロイタ だった。文脈非依存で
    #   こくばん 以外に読みようがないので表層そのままで安全。
    #   出荷済み cloud 17 ep で発火 2 件、いずれも未固定の真陽性。
    "黒板": (
        "こくばん",
        ["黒板=こくばん。クロイタ 誤読 (ある回、user 耳)"],
        "こくばんで固定",
    ),
    # --- user が耳で 6 語。lint も STT も沈黙した ---
    # 縁 (ふち=edge / えん=relation): 円板の「縁」を エン と読んだ (math_03 で 6 回)。
    #   どちらも実在するので固定せず、かな明示を求める。
    "縁": (
        ("ふち", "えん"),
        ["縁=ふち (円板の縁) を エン と読む (ある回、user 耳)"],
        "narration_speech_cloud に ふち (または えん) を平仮名で明示",
    ),
    # 梳かす (とかす) / 梳く (すく): 「梳かせません」を スカセマセン と読んだ。
    #   活用「梳かし/梳かせ/梳かす」を「梳か」で当てる。「梳く」(すく) は含まない。
    "梳か": (
        "とか",
        ["梳かす=とかす を スカス と読む (ある回、user 耳)"],
        "とかし / とかせ で固定",
    ),
    # 私講師 は既存エントリ (上) にある。ある回では config の SSML override で「固定済み」と
    #   判定されて沈黙したが、Chirp は ワタシコウシ と読んだ (複合語は SSML が honor されない型)。
    #   **SSML で固定した語は lint が黙るので、かな直書きのほうが安全**。
    # 故郷 (こきょう / ふるさと): 「学問の故郷」で どちらでもない読みになった。
    "故郷": (
        ("こきょう", "ふるさと"),
        ["故郷=こきょう が崩れる (ある回、user 耳)"],
        "narration_speech_cloud に こきょう を平仮名で明示",
    ),
    # 角谷 (かくたに): 不動点定理の角谷静夫。カクドヤ と読んだ。
    "角谷": (
        "かくたに",
        ["角谷=かくたに を カクドヤ と読む (ある回、user 耳)"],
        "かくたに で固定",
    ),
    # ── ある回 (ヴォルテラ。user が通し視聴で 6 語を耳で拾った。lint も STT も沈黙) ──
    # 魚市場 (うおいちば / うおしじょう): どちらも実在するが、市場の魚売り場は うおいちば。
    "魚市場": (
        ("うおいちば", "うおしじょう"),
        ["魚市場 を ウオシジョウ と読む (ある回、user 耳)"],
        "narration_speech_cloud に うおいちば を平仮名で明示",
    ),
    # 食う者 (くうもの): クウシャ と読んだ (intro_02/person_07)。者=しゃ の複合語 (捕食者 等) は別。
    "食う者": (
        "くうもの",
        ["食う者=くうもの を クウシャ と読む (ある回、user 耳)"],
        "くうもの で固定",
    ),
    # 人街 (じんがい): ユダヤ人街 を ユダヤジンマチ と読んだ (person_01/closing_01)。
    "人街": (
        "じんがい",
        ["ユダヤ人街=ゆだやじんがい を ジンマチ と読む (ある回、user 耳)"],
        "じんがい で固定",
    ),
    # 二つの種 (しゅ=species / たね=seed): 「二つの種が出会う」を フタツノタネ と読んだ (math_02)。
    "つの種": (
        ("しゅ", "たね"),
        ["種=しゅ (species) を タネ と読む (ある回、user 耳)"],
        "narration_speech_cloud に しゅ を平仮名で明示 (種類/生物種 に言い換えてもよい)",
    ),
    # 獲る (とる / える): 「獲るのをやめたら」を エル と読んだ (math_06/closing_03)。獲物=えもの は別。
    "獲る": (
        ("とる", "える"),
        ["獲る=とる を エル と読む (ある回、user 耳)"],
        "narration_speech_cloud に とる を平仮名で明示",
    ),
    # 型 (かた / がた): 「同じ型の式」を オナジガタ と読んだ (closing_02)。「〜型」の連濁は語による。
    "同じ型": (
        ("おなじかた", "おなじがた"),
        ["同じ型=おなじかた を オナジガタ と読む (ある回、user 耳)"],
        "narration_speech_cloud に おなじかた を平仮名で明示",
    ),
    # 通 (かよう/とおる): 既存の「を通って/を通り」は とおる 側。こちらは かよう 側で、
    #   「学校に通った」= かよった を トオッタ と読む。
    #   **「筋の通った」は とおった が正しい**ので「の通った」は絶対に入れない (同一 ep に両方あった)。
    "に通った": ("かよ", ["通=かよう。トオッタ 誤読"], "にかよった で固定"),
    "に通って": ("かよ", ["通=かよう。トオッテ 誤読"], "にかよって で固定"),
    "に通い": ("かよ", ["通=かよう。トオリ 誤読"], "にかよい で固定"),
    # 行 (いく/おこなう/ぎょう): **裸の「行」は絶対に入れない** — 頻出しすぎて FP が爆発する。
    #   実際に踏んだのは「あっちへ行っていなさい」→ オコナッテ。
    #   助詞 へ/に が前置する「行って」は いく 以外に読みようがないのでここだけ狙う。
    "へ行って": ("いって", ["行=いく。オコナッテ 誤読"], "へいって で固定"),
    "に行って": ("いって", ["行=いく。オコナッテ 誤読"], "にいって で固定"),
    # 行の側 (ぎょう): 行列の「行」。イキ/オコナイ 誤読。「列」は れつ 一択なので入れない。
    "行の側": ("ぎょう", ["行=ぎょう (行列の行)。イキ/オコナイ 誤読"], "ぎょうの側 で固定"),
    # 塩水 (しおみず/えんすい): ある回の出荷 wav で エンスイ と読まれた (STT 実測)。
    #   語りの中では しおみず が自然。えんすい は技術文脈の読み。
    "塩水": (
        "しおみず",
        ["塩水=しおみず。エンスイ 誤読 (ある回、出荷 STT で実測)"],
        "しおみず で固定",
    ),
    # 以下は ある回で表層を読んで「危ない」と判断し先回りで固定したもの。
    #   出荷 STT は当該シーンを**漢字で書き起こした**ため読みを検証できなかった
    #   (書き起こしが漢字の scene では読みは原理的に判定できない)。
    "道路工夫": (
        "こうふ",
        ["工夫=こうふ (労働者)。クフウ 誤読 (ある回、user 耳)"],
        "どうろこうふ で固定",
    ),
    # NOTE(不採用): 裸の「工夫」と「工夫として」。くふう(=ingenuity) のほうが圧倒的に多く、
    #   「一つの工夫として」のような正当な用法を巻き込む。こうふ が要る場面は稀なので
    #   具体的な複合語 (道路工夫) だけに留める。
    # 期待値は「ずり」だけにする。全部かなで書くと **形態素の切れ目が消えて** Chirp が
    # 誤って区切る。正しい直し方は「曖昧な部分だけかな」= 校正ずり。
    # 「ずり」を期待すれば 校正ずり も こうせいずり も通る。
    "校正刷り": ("ずり", ["刷り=すり/ずり の連濁"], "校正ずり で固定 (全部かなにしない)"),
    "紙束": ("かみたば", ["紙束=かみたば。シソク 誤読"], "かみたば で固定"),
    "主計官": ("しゅけいかん", ["主計=しゅけい。シュケイ以外の音読み誤読"], "しゅけいかん で固定"),
    "出生証明": (
        "しゅっしょう",
        ["出生=しゅっしょう/しゅっせい の多読み"],
        "しゅっしょうしょうめいしょ で固定",
    ),
    "苦もなく": ("くもなく", ["苦=く。ニガ 誤読"], "くもなく で固定"),
    # --- user が耳検出。lint がどれも見ていなかった ---
    # 大家 (たいか/おおや): 「不等式の大家」= たいか。Chirp は オオヤ (家主) と読んだ。
    "の大家": ("たいか", ["大家=たいか。オオヤ(家主) 誤読"], "たいか で固定"),
    # 公に (おおやけに): 「公に放棄した」。Chirp は コウニ と音読みした。
    # 主人公に/公認 等は _POLYPHONE_EXCLUDE で除く。
    "公に": ("おおやけに", ["公に=おおやけに。コウニ 誤読"], "おおやけに で固定"),
    # 末 (すえ/まつ): 「考え抜いた末の」= すえ。Chirp は マツ と読んだ。
    # 月末/期末/末端 は「た末」に一致しないので巻き込まない。
    "た末の": ("すえ", ["末=すえ。マツ 誤読"], "すえ で固定"),
    "た末に": ("すえ", ["末=すえ。マツ 誤読温床 (ある回と同型)"], "すえ で固定"),
    # 対 (つい/たい): 「対ごとに独立」= ついごと。Chirp は タイゴト と読んだ。
    "対ごと": ("ついごと", ["対ごと=ついごと。タイゴト 誤読"], "ついごと で固定"),
    # 行ったり来たり (いったりきたり): Chirp は オコナッタリキタリ と読んだ。
    "行ったり来たり": (
        "いったりきたり",
        ["行ったり=いったり。オコナッタリ 誤読"],
        "いったりきたり で固定",
    ),
    # N手 (て): 手数を数える「一手先/二手先」。Chirp は ヒトテ/フタテ と読んだ。
    # 「二手に分かれる」は ふたて が正しいので、surface は先読みまで含めて narrow に。
    "一手先": ("いって", ["一手=いって。ヒトテ 誤読"], "いってさき で固定"),
    "二手先": ("にて", ["二手=にて。フタテ 誤読"], "にてさき で固定"),
    "八手": ("はちて", ["八手=はちて。ヤツデ(植物) 誤読"], "はちて で固定"),
}

# {surface: (この語が同じ文にあれば surface の一致を無視する, ...)}
# _POLYPHONE は部分一致なので、より長い語の一部として現れると別読みが正しい場合がある。
# 辞書のコメントに「〜は含めない」と書いてあっても、表層が部分文字列である限り一致する。
_POLYPHONE_EXCLUDE = {
    # 労に/労を は 苦労に・勤労に・労働に (くろう/きんろう/ろうどう) の部分一致を除く。
    # 出荷 72 話で「労に」は ある回の 1 文だけだが、部分文字列の罠は先に塞ぐ。
    "労に": ("苦労に", "勤労に", "労働に", "過労に", "心労に"),
    "労を": ("苦労を", "勤労を", "労働を", "過労を", "心労を"),
    # 「五十分の一」「十分の一」の 十分 は分数の ぶん (十分=じゅうぶん とは別物)。
    # 「三十分」「五十分」は時間の ぷん で、これも enough の 十分 ではない。
    "十分": (
        "十分の",
        "二十分",
        "三十分",
        "四十分",
        "五十分",
        "六十分",
        "七十分",
        "八十分",
        "九十分",
    ),
    # 四つ角=よつかど / 四つ葉=よつば / 四つ足=よつあし / 四つん這い は よつ が正しい。
    "四つ": ("四つ角", "四つ葉", "四つ足", "四つん這い", "四つ辻"),
    # 「手に入れる」「踏み入れる」「式に入れる (=代入する)」は いれる が正しい
    # (はいれる にすると誤り)。狙いは 大学に入れる=はいれる のほう。
    # 「式に入れ」は ある回 (反復法: 近似値を式に入れる) で毎ビルド発火した FP。
    "に入れる": ("手に入れ", "踏み入れ", "式に入れ"),
    "に入れま": ("手に入れ", "踏み入れ", "式に入れ"),
    # 「値段」「値札」「値域」の 値 は ね/域の一部で、あたい ではない。
    "い値": ("値段", "値札", "値域"),
    "な値": ("値段", "値札", "値域"),
    # 「その間隔」は かんかく で 間 単独ではない。
    "その間": ("その間隔", "その間柄"),
    # 「筋の通った」は とおった。「学校に通った」= かよった とは別語。
    "に通った": ("筋の通った", "筋が通った"),
    # 「主人公に」「公にする」以外の 公 の複合語は こう が正しい。
    "公に": ("主人公", "公認", "公開", "公式", "公理", "公算", "公務"),
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
    # ある回: user「日常でほとんど聞かない語で、伝わらない人が一定いる」
    "半可通": "半分しか分かっていない人 / 生かじりの人",
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
        "Chirp が「まいにち通い」の か を濁らせ「まいにちがよい」化 (ある回、user 耳)。"
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
            # narration と長さの違う cloud 配列は合成器が捨てる (narration_speech /
            # narration を喋る)。それを正として検査すると、音声と違う文を見て黙る。
            # 空として渡し、run_lint が別途 cloud_length_mismatch で名指しする。
            if cloud_array_status(scene) == "length_mismatch":
                cloud = []
            else:
                cloud = scene.get("narration_speech_cloud") or []
            for i, narr in enumerate(narration):
                if not isinstance(narr, str):
                    continue
                narr_c = _clean(narr)
                cloud_c = _clean(cloud[i]) if i < len(cloud) and isinstance(cloud[i], str) else ""
                yield sid, i, narr_c, cloud_c


def is_reading_pinned(surface, yomis, narr, cloud, *, ssml_global=None, ssml_episode=()):
    """ (2026-09-19): 語の読みが固定されている経路を返す。無ければ None。

    3 つの層を **1 か所で** 見る (それまで polyphone は 3 層を独自の順で、high_risk は
    かなの層しか見ておらず、`cloud_reading_overrides` で固定した語が `pronunciation_high_risk`
    にもあると偽警告になっていた):
      "kana"         : 読み (いずれか) が読み源 (cloud があれば cloud、無ければ narration) にある
                       = gen_cloud_readings の直書き / cloud_direct_kana / 手書きの結果
      "ssml_global"  : cloud_tts._READING_OVERRIDES の表層が surface を覆う (k in surface)、
                       または surface を含む override 表層が文にある (surface in k and k in narr)
      "ssml_episode" : episode_config.cloud_reading_overrides について同じ
    `cloud_direct_kana` は特別扱いしない ── 直書きが効いていれば "kana" で固定済み、効いて
    いなければ (の no-op) 未固定として名指しされるのが正しい。
    """
    read_src = cloud if cloud else narr
    yomis = yomis if isinstance(yomis, tuple | list) else (yomis,)
    if any(y and y in read_src for y in yomis):
        return "kana"

    def _covered(keys) -> bool:
        for k in keys or ():
            if not isinstance(k, str) or not k:
                continue
            if k in surface:
                return True
            if surface in k and k in (narr or ""):
                return True
        return False

    if _covered(ssml_global if ssml_global is not None else _SSML_FORCED):
        return "ssml_global"
    if _covered(ssml_episode):
        return "ssml_episode"
    return None


def _scan_polyphone(sid, idx, narr, cloud, episode_forced=()):
    """(1) 多読み漢字が narration にあり cloud で読み未固定なら WARN。

    `episode_forced` は episode_config.cloud_reading_overrides の表層 (SSML phoneme で
    合成時に固定される語)。ある回は 十分/四つ をそこで固定していたので、lint が
    「未固定」と言うと嘘になる (global の `_SSML_FORCED` と同じ扱い)。
    読み (yomi) は str か tuple。tuple は「文脈で割れる語」で、どれか一つが cloud に
    あれば固定済みとみなす (十分=じゅうぶん/じゅっぷん、正に=せいに/まさに)。
    """
    out = []
    # 読み源 (cloud があれば cloud、無ければ narration) の判定は is_reading_pinned の中。
    for surface, (yomi, notes, fix) in _POLYPHONE.items():
        if surface not in narr:
            continue
        # 表層は部分一致なので、より長い語の一部として現れたときは別読みが正しいことがある。
        # 例: 「に入れる」は 大学に入れる=はいれる を狙ったルールだが、「手に入れる」にも
        # 一致してしまい、提案どおり はいれ に直すと「てはいれる」という誤りになる
        #。辞書のコメントは除外する意図を
        # 書いていたが、表層一致だけでは実現できていなかった。
        if any(w in narr for w in _POLYPHONE_EXCLUDE.get(surface, ())):
            continue
        yomis = yomi if isinstance(yomi, tuple) else (yomi,)
        # かな / global SSML / episode SSML の 3 層を is_reading_pinned で 1 か所判定。
        if is_reading_pinned(surface, yomis, narr, cloud, ssml_episode=episode_forced):
            continue
        out.append(
            {
                "type": "polyphone",
                "scene_id": sid,
                "index": idx,
                "surface": surface,
                "detail": narr,
                "note": (
                    f"多読み「{surface}」の読み「{'/'.join(yomis)}」が narration_speech_cloud に無い "
                    f"(Chirp 自動読み任せ)。誤読リスク: {'; '.join(notes)}。対処: {fix}"
                ),
            }
        )
    return out


# (1d) 単独の字母「エー」: 変数名 a を cloud で「エー」と書くと Chirp が長音を引き延ばし、
# 「a、b、c」の a だけ不自然に遅くなる。「エイ」なら正常。
# 後続が句読点/空白/閉じ括弧/行末のときだけ = 「エーアイ」「エース」等の語は対象外。
_LETTER_LONG_VOWEL_RE = re.compile(r"(?<![ァ-ヶー])エー(?=[、。，．！？!?\s」』）)]|$)")


def _scan_letter_long_vowel(sid, idx, narr, cloud):
    """(1d) cloud の単独「エー」(字母 a) を WARN。「エイ」を推奨。"""
    if not cloud:
        return []
    if not _LETTER_LONG_VOWEL_RE.search(cloud):
        return []
    return [
        {
            "type": "letter_long_vowel",
            "scene_id": sid,
            "index": idx,
            "surface": "エー",
            "detail": cloud,
            "note": (
                "cloud の単独「エー」(字母 a) は Chirp が長音を引き延ばして不自然に遅くなる。"
                "対処: narration_speech_cloud で「エイ」と書く"
            ),
        }
    ]


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
                "Chirp が きょう(都市) と誤読しうる (ある回「1844京」-> キョウ)。"
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
                "(ある回/049: 同一表記が カズ/スウ に割れる実測)。文脈に応じ "
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
    """(5) narration_speech_cloud の一括 は→わ 変換を検出 (ある回 backstop)。

    script_generator は cloud を出さず gen_cloud_readings が **native は** で生成する
    (コンマ孤立助詞のみ わ 化)。しかし legacy/手書きの scene_def に「全ての は を わ
    にした」cloud が残ると gen_cloud は既存を保存し素通りする (ある回で顕在化: 語中
    は の わ 化がアクセント崩れ+「わ、」境界の余分音挿入=もはや/波動 の phantom を招く)。
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
    独立モーラとして読み、境目に微小な間が入って不自然になる (ある回 A/B 実測: わ 表記文は
    は 表記文より約 25% 長い)。gen_cloud_readings は本来 native は を残す設計 (コンマ孤立
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
    """(7) 発音リスク語を検出し、安全な言い換えを提案 (ある回「言い換え戦略」の仕組み)。

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
# ある回で最後の 2 つの選択肢を足した。narration_speech_cloud は「読み」の文なので、
# π / √ / ＝ が残っているのは常に取りこぼしである。出荷 wav の STT で確定した誤読:
#   π/4 -> 「パイ4」 / π/8 -> 「パイハチ」 (わる が落ちる)
#   エネストレーム＝掛谷の定理 -> 「エネストレームイコール掛谷の定理」
# 既存の _BARE_FRACTION_RE は N/M の両側が数字のときだけ見るので π/4 を取りこぼす。
_RAW_FORMULA_RE = re.compile(
    r"[A-Za-z]'|=[A-Za-z]|[A-Za-z]=|\bL[1-5](?![0-9A-Za-z])|[A-Za-zα-ωΑ-Ω]\^"
    r"|[πΠ√∛]|＝"
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
    分数として読むか非決定 (ある回: 22/7 は ななぶんのにじゅうに 正読だが 355/113 は
    「355 113」棒読み)。分数は「M分のN」等でスペルアウトして読みを固定する。
    narration (字幕表示) の N/M は許容 -- cloud のみ対象。gen_cloud はスラッシュ分数を
    自動スペルアウトしないので backstop。advisory。

    分子/分母のどちらかが 3 桁以上のときだけ WARN する: 22/7・1/2 等の短い分数は Chirp が
    分数として安定して読む (ある回出荷 wav STT で 22/7=ななぶんのにじゅうに を 2 度確認)。
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
                    "非決定読み (ある回 355/113 を「355 113」棒読み)。narration_speech_cloud で "
                    "「M分のN」にスペルアウトして固定 "
                    "(例: 355/113 -> ひゃくじゅうさんぶんのさんびゃくごじゅうご)"
                ),
            }
        ]
    return []


# ---- 裸の単独漢字 (複合語の一部でないもの) を取り出す共通判定 ------------------
# 多読み漢字の中には、表層一致 (_POLYPHONE) では扱えないものがある。1 文字の漢字を
# 表層に登録すると、その字を含む複合語すべてに一致してしまうからだ (角 → 内角/三角形/
# 角度、根 → 根本/平方根/屋根)。**辞書のコメントに「〜は含めない」と書いても、表層が
# 部分文字列である限り一致する** (_POLYPHONE_EXCLUDE と同じ教訓)。
# 代わりに前後の文字種で「複合語の一部でない裸の字」だけを取り出す:
#   前 = 漢字/片仮名/長音/数字なら複合語の後半 (内角・オイラー角・八分角 / 屋根・平方根)
#   後 = 漢字なら複合語の前半 (角度・角錐・角運動量 / 根本・根拠・根性)
_COMPOUND_PREV = re.compile(r"[一-鿿゠-ヿー0-9０-９]")
_COMPOUND_NEXT = re.compile(r"[一-鿿]")


def _iter_bare_kanji(text: str, kanji: str):
    """text 中で複合語の一部になっていない kanji の位置を yield する。"""
    for m in re.finditer(kanji, text):
        i = m.start()
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if prev and _COMPOUND_PREV.match(prev):
            continue
        if nxt and _COMPOUND_NEXT.match(nxt):
            continue
        yield i


_DIGIT_FRACTION_LINT_RE = re.compile(r"[0-9０-９]{2,}[ 　]*分の[ 　]*[0-9０-９]")


def _scan_digit_fraction(sid, idx, narr, cloud):
    """(1f) 合成テキストに算用数字 2 桁以上の分数「16 分の 4」が残ると Chirp が 分 を
    時間の ぷん で読む (ある回 user 耳: じゅうろっぷんのよん。1 桁は ぶん で通っていた)。
    gen_cloud_readings は生成時に かな 化するが、手書き・旧生成の cloud は数字のまま
    残るので backstop。advisory。"""
    if not cloud:
        return []
    out = []
    for m in _DIGIT_FRACTION_LINT_RE.finditer(cloud):
        out.append(
            {
                "type": "digit_fraction",
                "scene_id": sid,
                "index": idx,
                "surface": m.group(0),
                "detail": cloud,
                "note": (
                    "cloud=合成テキストに 2 桁以上の算用数字の分数が残存 -> Chirp が「分」を"
                    "時間の ぷん で読む (ある回: 16 分の 4 -> じゅうろっぷんのよん)。"
                    "narration_speech_cloud で じゅうろくぶんのよん のように かな 化 "
                    "(gen_cloud_readings は自動で行う)"
                ),
            }
        )
    return out


def _scan_bare_kaku(sid, idx, narr, cloud):
    """(1f) 単独の「角」は かく/かど の多読み。cloud に読みが無ければ WARN。

    ある回で「長さも角も」「角と比」「角も失われ」の 角 (=angle) を Chirp が かど と読んだ。
    かく (角度) と かど (曲がり角) は文脈依存なので読みを強制せず、明示を促すだけ。
    複合語 (内角/三角形/角錐/角度/オイラー角…) は `_iter_bare_kanji` が除外する。

    出荷 57 ep の narration に現れる 角 169 件を実走査して calibrate した。169 件のうち
    この条件を満たすのは 6 件だけで、すべて「読みが本当に曖昧な単独の角」だった
    (ある回角の三等分 / ある回二つの角 / ある回 / ある回波形の角=かど とも読める)。
    """
    if not narr:
        return []
    for i in _iter_bare_kanji(narr, "角"):
        if cloud and ("かく" in cloud or "かど" in cloud):
            continue
        return [
            {
                "type": "polyphone",
                "scene_id": sid,
                "index": idx,
                "surface": "角",
                "detail": narr[max(0, i - 14) : i + 14],
                "note": (
                    "多読み「角」の読みが narration_speech_cloud に無い (Chirp 任せ)。"
                    "誤読リスク: 角=かく(角度)/かど(曲がり角)。ある回で「長さも角も」が "
                    "カド と読まれた。文脈に応じ かく または かど を明示"
                ),
            }
        ]
    return []


def _scan_bare_kon(sid, idx, narr, cloud):
    """(1g) 単独の「根」は こん/ね の多読み。cloud に読みが無ければ WARN。

    ある回の「この方程式が持ちうる根は」を Chirp が **ね** と読んだ
    (出荷 wav を verify_shipped_audio で書き起こし「ホウテイシキ ガ モチウル ネ ワ」)。
    episode_config の pronunciation_high_risk には「根 → こん」「正の根 → せいのこん
    (ね と読ませない)」と書いてあり **危険は人間が把握して文字にしていた** のに、
    それを機械的に照合するものが何も無かった (その穴自体は `_scan_high_risk_unpinned`)。

    こん (方程式の根) と ね (植物の根・比喩の「根の部分」) は文脈依存なので読みは
    強制せず明示を促す。本チャンネルの題材では こん が圧倒的に多いが、ある回岡潔の
    「数学の根に置いた」= ね のような比喩用法も実在するので両方を許す。

    較正 (出荷 63 ep 全走査): narration に現れる 根 98 件のうち `_iter_bare_kanji` を
    通るのは 37 件。複合語 61 件 (平方根/立方根/三乗根/実根/重根/根本/根底/根幹/根拠/
    根付い/根尾川…) はすべて除外される。**素朴な置換で 根本 が「こん本」になった**
    のが ある回で実際に踏んだ罠で、この前後判定はそれを構造的に防ぐ。
    engine=cloud の 20 ep に限ると発火は 1 件のみ (ある回「その根に、」=
    こん/ね が本当に曖昧な未固定行)。ある回の 9 件は こん 固定済みなので黙る。
    """
    if not narr:
        return []
    for i in _iter_bare_kanji(narr, "根"):
        if cloud and ("こん" in cloud or "ね" in cloud):
            continue
        return [
            {
                "type": "polyphone",
                "scene_id": sid,
                "index": idx,
                "surface": "根",
                "detail": narr[max(0, i - 14) : i + 14],
                "note": (
                    "多読み「根」の読みが narration_speech_cloud に無い (Chirp 任せ)。"
                    "誤読リスク: 根=こん(方程式の根)/ね(植物の根)。ある回で「持ちうる根は」が "
                    "ネ と読まれた (出荷 wav STT)。文脈に応じ こん または ね を明示。"
                    "**置換するなら 根本(こんぽん)/平方根 等の複合語を壊さないこと**"
                ),
            }
        ]
    return []


# Kanji AND katakana both give the parser a morpheme boundary, so both count as
# "structure". Counting kanji alone flagged ある回「ブリッグスははるばるエディンバラの
# ネイピアを訪ねました」 (3 kanji but 15 katakana = plenty of structure, and no reported
# misreading). Calibrated over the 210 shipped cloud lines that contain a particle:
# the lowest legitimate line sits at 0.130, an earlier episode defect at 0.060.
_KANA_ONLY_MAX_STRUCTURE_RATIO = 0.10
_HIRAGANA_PARTICLE_RE = re.compile(r"[ぁ-ん](は|へ)[ぁ-ん]")
# Loanwords a writer reaches for when PARAPHRASING rather than respelling a reading.
# A cloud line is supposed to be the same words as the narration with the readings
# made explicit; if one of these appears in the cloud but not in the narration line,
# the subtitle and the audio are saying different words.
_PARAPHRASE_LOANWORDS = (
    "エピソード",
    "ストーリー",
    "アイデア",
    "イメージ",
    "ポイント",
    "ケース",
    "テーマ",
    "シーン",
    "ルール",
)


# 文語 (漢文書き下し) の一次資料引用。ある回の掛谷のノート引用
# 『予は側に在りて之を非常に興味ある質問なりと感じ、直ちに自ら一般的な問題を創作せり』は
# **一語だけでなく引用全体**が危なかった (側=かたわら を そば/がわ、予=よ を あらかじめ、
# 之=これ を ゆき 等)。既存の scanner は全て「この語が危ない」と語単位で見るので、
# **文体まるごとが現代語の読み規則から外れている**ことは誰も見ていなかった。
# 較正 (出荷 68 本): 標識 2 個以上の段落は ある回の 1 件のみ = 真陽性 1 / 偽陽性 0。
# 標識 1 個に緩めると 009_seki の人名「沢口一之が」が 之が に一致して偽陽性になるので 2 個。
_CLASSICAL_MARKS = (
    "予は",
    "之を",
    "之が",
    "なりと",
    "在りて",
    "ありて",
    "べからず",
    "ざるべ",
    "なりき",
)
_CLASSICAL_SERI_RE = re.compile(r"せり(?![ぁ-ん])")
_CLASSICAL_MIN_MARKS = 2
# 文語文の中で **現代語と違う読みをする一字漢字**。これが cloud に残っていたら未対処。
# 複合語の一部としても一致するが、発火は「文語標識 2 個以上の段落」に限られるので、
# 現代文の 内側 / 予定 / 之 を巻き込まない (出荷 68 本で実測 0 件)。
_CLASSICAL_KANJI = ("予", "側", "之", "於", "而", "曰", "猶", "已", "乃", "者")


def _scan_classical_quote(sid, idx, narr, cloud):
    """文語の引用が cloud で かな化されていなければ WARN。

    語単位の読み固定では足りない。文語は語彙も活用も現代語と違うので、Chirp は
    引用のほぼ全語を外す。**引用まるごとを かな で書く**のが唯一確実な対処なので、
    個別の語を辞書に足すのではなく「この文体が居る」ことを検出する。

    危ないのは **文語読みをする一字漢字** (予=よ / 側=かたわら / 之=これ) のほうで、
    同じ引用に混じる現代語の複合語 (非常/興味/質問/創作) は普通に読まれる。だから
    「漢字が全体として減ったか」では測れない ── ある回の実測は 21 字 -> 17 字 (0.81)
    で、**必要な処置は済んでいるのに漢字比では未対処に見えた**。危険な一字だけを見る。
    """
    if not narr:
        return []
    marks = [m for m in _CLASSICAL_MARKS if m in narr]
    n_marks = len(marks) + (1 if _CLASSICAL_SERI_RE.search(narr) else 0)
    if n_marks < _CLASSICAL_MIN_MARKS:
        return []
    risky = [c for c in _CLASSICAL_KANJI if c in narr]
    if not risky:
        return []
    # cloud で開かれていれば対処済み。cloud 未記入 (= Chirp に丸投げ) は未対処。
    if cloud and not any(c in cloud for c in risky):
        return []
    return [
        {
            "type": "classical_quote",
            "scene_id": sid,
            "index": idx,
            "surface": "/".join(marks[:4]) or "せり",
            "detail": narr[:60],
            "note": (
                "文語 (漢文書き下し) の引用が narration_speech_cloud で かな化されて "
                "いません。文語は語彙も活用も現代語と違うので Chirp は語単位でなく "
                "**引用のほぼ全語**を外します (ある回: 側=かたわら を誤読)。"
                "引用部分をまるごと平仮名で書いてください (字幕=narration は漢字のまま)"
            ),
        }
    ]


def _scan_itta(sid, idx, narr, cloud):
    """多読み「行った」(おこなった / いった) が cloud で未固定なら WARN。

    ある回「シローがアーベルとガロアの仕事について行った講義」が **いった** と
    読まれた (出荷 wav STT が「について言った講義」と書き起こした 2026-08-19)。cloud
    reading lint は当時この語を持っておらず、警告を一度も出していない。

    両方の読みが実在するので強制はしない。全67話の narration での 9 件を実測すると
    おこなった 5 (全体講演を行った / オイラーが行ったのは / リーマンが行ったのは x2 /
    巡礼を行った) 対 いった 3 (置換を続けて行ったとき / 線が行ったり来たり /
    先を行った考え)。文脈依存なので `_READING_OVERRIDES` には入れられない。
    """
    if not narr or "行った" not in narr:
        return []
    read_src = cloud if cloud else narr
    if "おこなった" in read_src or "いった" in read_src:
        return []
    i = narr.index("行った")
    return [
        {
            "type": "polyphone",
            "scene_id": sid,
            "index": idx,
            "surface": "行った",
            "detail": narr[max(0, i - 14) : i + 14],
            "note": (
                "多読み「行った」の読みが narration_speech_cloud に無い (Chirp 任せ)。"
                "誤読リスク: 行った=おこなった(実施した)/いった(移動した)。ある回で "
                "「仕事について行った講義」が イッタ と読まれた (出荷 wav STT)。"
                "文脈に応じ おこなった または いった を明示"
            ),
        }
    ]


def _scan_bare_kyuu(sid, idx, narr, cloud):
    """単独の「球」(きゅう / たま) が cloud で未固定なら WARN。

    ある回「直線と球を一対一に対応させ、接する球が…」が **たま** と読まれた
    (初回ビルドの STT が「直線と玉を」と書き起こし、user が通し視聴で指摘 2026-08-19)。

    `_iter_bare_kanji` を通すのは複合語を壊さないため。全67話の narration に 球 は 103 件
    あるが、地球/半球/球面/球体/野球 等は前後が漢字なので除外され、裸の 球 だけが残る。
    根 と同じ理由で読みは強制しない (数学では きゅう だが「玉」的な比喩も原理的にはありうる)。
    """
    if not narr:
        return []
    read_src = cloud if cloud else narr
    for i in _iter_bare_kanji(narr, "球"):
        if "きゅう" in read_src or "たま" in read_src:
            return []
        return [
            {
                "type": "polyphone",
                "scene_id": sid,
                "index": idx,
                "surface": "球",
                "detail": narr[max(0, i - 14) : i + 14],
                "note": (
                    "多読み「球」の読みが narration_speech_cloud に無い (Chirp 任せ)。"
                    "誤読リスク: 球=きゅう(数学の球)/たま。ある回で「直線と球を」が "
                    "タマ と読まれた (出荷 wav STT)。文脈に応じ きゅう を明示。"
                    "**置換するなら 地球/半球/球面 等の複合語を壊さないこと**"
                ),
            }
        ]
    return []


def _scan_kana_only_particle(sid, idx, narr, cloud):
    """(8) cloud 行が実質かなだけだと 助詞「は」が ha と読まれる。

    Chirp は形態素の切れ目で助詞を判定するので、漢字かな混じりの
    「彼は57と答えた」は wa になるが、全文平仮名の「かれはごじゅうななとこたえた」は
    ha になる。**STT では捕まえられない** (Gemini は転写時に助詞を は/ハ に正規化する)
    ので、合成前にテキストの形で止めるしかない。

    較正: 助詞を含む出荷済み cloud 210 行のうち最も平仮名寄りの行が 0.130、
    ある回の実 defect が 0.060。閾値 0.10 で誤検知ゼロ・実 defect 捕捉。
    """
    if not cloud:
        return []
    body = re.sub(r"[、。！？\s（）「」『』]", "", cloud)
    if not body:
        return []
    ratio = len(re.findall(r"[一-龥ァ-ヶー]", body)) / len(body)
    if ratio >= _KANA_ONLY_MAX_STRUCTURE_RATIO:
        return []
    m = _HIRAGANA_PARTICLE_RE.search(cloud)
    if not m:
        return []
    return [
        {
            "type": "kana_only_particle",
            "scene_id": sid,
            "index": idx,
            "surface": m.group(0),
            "detail": cloud[max(0, m.start() - 12) : m.start() + 14],
            "note": (
                f"cloud 行がほぼ平仮名だけ (漢字+カタカナ率 {ratio:.2f}) で助詞「{m.group(1)}」を含む。"
                "漢字の切れ目が無いと Chirp が助詞と解析できず ha/he と読む "
                "(ある回実測)。**STT では検出できない** ので合成前に直す。"
                "対処: 他の行と同じ漢字かな混じりに戻し、読みを固定したい語だけ平仮名にする"
            ),
        }
    ]


# ---- (10) episode_config.pronunciation_high_risk の読みが cloud で未固定 ----
# `pronunciation_high_risk` は **人間が手で作った危険語リスト**で、多くの回で「X → よみ」
# 形式で数十〜数百件書かれている。ところがこの欄は audio_generator が VOICEVOX 用の
# プロンプトヒントに流すだけで、**engine=cloud では誰も読まない**。ある回は
# 「根 → こん」「正の根 → **せいのこん**(ね と読ませない)」と書いてあったのに 根 が
# 漢字のまま合成テキストに残り、出荷 wav で ネ と読まれた。危険は把握され、文字にされ、
# そして照合されなかった。
#
# ここでの照合は素朴でよい: **その語が narration_speech_cloud に元の表記のまま
# 残っているなら、読みは固定されていない**。narration (=字幕) の漢字は正当なので見ない。
#
# ただし全エントリを対象にすると使い物にならない。出荷済み cloud 20 ep で実測すると
# **1101 件**発火した (「原論」「素数」「有理数」「対数」…= Chirp が普通に正読する硬語)。
# 毎ビルド 50 件の警告は「lint を無視する習慣」を育てるだけで、これは CLAUDE.md が
# 戒める失敗そのもの。そこで **書き手が競合する読みを名指しした語** に絞る:
#   * `**よみ**` と強調してある / 「〜と読ませない」「最重要」と書いてある
# これは単なる件数調整ではなく意味のある弁別で、「しおん と読ませない」「かど と読ませない」
# のように **誤読の候補まで書いた語** こそが多読みハザードだからだ (「原論 → げんろん」は
# 難語メモにすぎない)。この絞り込みで出荷済み cloud 20 ep の発火は **21 件** (約 1 件/ep)。
#
# さらに 3 つ除外する:
#   * 「使わない」「WATCH-READING」系 = 読みの固定指示ではない (smoke_test 18d の担当)
#   * 1 文字の表層 (角/数/根/解/量) = 複合語を巻き込む。実際 ある回の「角」は
#     三角法/三角形 に一致した。専用の `_scan_bare_kaku` / `_scan_bare_kon` /
#     `_scan_standalone_num` が前後の文字種で正しく扱う
#   * 漢字を含まない表層 (カタカナ人名・地名) = Chirp は素直に読むうえ全 ep で大量発火
_HIGH_RISK_NOT_A_READING = ("使わない", "使用しない", "避ける", "WATCH-READING")
_HIGH_RISK_EMPHASIS = ("と読ませない", "最重要")
_HIGH_RISK_EMPH_RE = re.compile(r"\*\*([^*]+)\*\*")
_KANJI_RE = re.compile(r"[一-鿿]")
_KANA_READING_RE = re.compile(r"[ぁ-んー・]+")


def parse_high_risk_entry(entry):
    """`pronunciation_high_risk` の 1 行を (surface, reading) に分解。対象外なら None。

    実データの形は自由文で、以下がすべて同じ欄に混在する:
        "根 → こん"
        "正の根 → **せいのこん**(ね と読ませない)"
        "種の計算 → **しゅのけいさん**(最重要。たね と読むと意味が壊れる。…)"
        "数 → WATCH-READING。かず/すう が文脈で割れる。…"
        "フランソワ・ヴィエト → ふらんそわゔぃえと"
    強調 (`**…**` / 「〜と読ませない」/「最重要」) のある行だけを返す。
    """
    if not isinstance(entry, str):
        return None
    normalized = entry.replace("->", "→")
    if "→" not in normalized:
        return None
    if any(marker in normalized for marker in _HIGH_RISK_NOT_A_READING):
        return None
    lhs, rhs = normalized.split("→", 1)
    surface = lhs.strip().strip("*「」 ")
    emphasized = _HIGH_RISK_EMPH_RE.search(rhs)
    if not emphasized and not any(m in rhs for m in _HIGH_RISK_EMPHASIS):
        return None
    reading = (emphasized.group(1) if emphasized else rhs).strip()
    # 注記 (括弧・句読点以降) を落として読みだけ残す
    reading = re.split(r"[(（。、]", reading)[0].strip().strip("*「」 ")
    if len(surface) < 2 or not _KANJI_RE.search(surface):
        return None
    if not reading or not _KANA_READING_RE.fullmatch(reading):
        return None
    return surface, reading


def load_episode_forced_readings(scene_path: str) -> frozenset:
    """scene_definition.json の隣の episode_config.json の cloud_reading_overrides の表層。

    そこに書いた語は cloud_tts が SSML <phoneme> で合成時に固定するので、
    narration_speech_cloud に平仮名が無くても「未固定」ではない (ある回: 十分/四つ)。
    config が無い/壊れている場合は空 (この lint を落とさない)。
    """
    # 読みは cloud_reading_config に 1 本化 (壊れた config は向こうが WARN、ここは空)
    return frozenset(load_cloud_reading_config(scene_path).forced_surfaces)


def load_high_risk_words(scene_path: str) -> list:
    """scene_definition.json の隣の episode_config.json から対象語を読む。

    config が無い/壊れている場合は空リスト (この lint を落とさない)。
    """
    out = []
    for entry in load_cloud_reading_config(scene_path).high_risk:
        parsed = parse_high_risk_entry(entry)
        if parsed:
            out.append(parsed)
    return out


_PARTICLE_HA_BEFORE_HA_RE = re.compile(r"[ぁ-ん]は(?=は)")


def _scan_particle_ha_before_ha(sid, idx, narr, cloud):
    """(9b) かなの並びの中の助詞「は」の直後が「は」で始まる語 → Chirp が ハ と読む。

    ある回: `端` を `はし` とかなで直した結果 `たばにははしが` となり、
    **助詞が ハ に壊れた** (出荷 wav の STT で 2 回とも ニハハシ。読点を打つと ニワハシ)。
    かな化は語の内部だけの操作ではなく、**隣接する助詞の区切りを変える**。

    (8) `kana_only_particle` は行全体のかな率で見るので、行の一部だけがかなの
    今回の形には沈黙する。ここは**局所**だけを見る。

    較正: 出荷済み cloud 2,910 行で 1 件のみ。助詞の前が漢字/カタカナなら形態素の
    切れ目が立つので対象外にしてある (前を平仮名に限らないと 153 件に膨らむ)。
    """
    if not cloud:
        return []
    m = _PARTICLE_HA_BEFORE_HA_RE.search(cloud)
    if not m:
        return []
    return [
        {
            "type": "particle_ha_before_ha",
            "scene_id": sid,
            "index": idx,
            "surface": cloud[m.start() : m.start() + 3],
            "detail": cloud[max(0, m.start() - 10) : m.start() + 12],
            "note": (
                "かなの並びの中で助詞「は」の直後が「は」で始まる語になっている。"
                "形態素の切れ目が立たず Chirp が助詞を ハ と読む (ある回で出荷まで漏れた)。"
                "対処: 助詞のあとに読点を打つ (「には、はしが」)。"
                "読点は尺を伸ばさず、`にわ` 表記のような語中変換の危険も無い"
            ),
        }
    ]


def _scan_high_risk_unpinned(sid, idx, narr, cloud, high_risk, episode_forced=()):
    """(10) config が名指しした危険語が cloud に元の表記のまま残っていれば WARN。

    固定済みの判定は polyphone と同じ `is_reading_pinned` (かな / global SSML /
    episode SSML)。以前はかなの層しか見ず、`cloud_reading_overrides` で固定した語が
    `pronunciation_high_risk` にも書いてあると偽警告になっていた。
    """
    if not cloud or not high_risk:
        return []
    out = []
    for surface, reading in high_risk:
        if surface in cloud and not is_reading_pinned(
            surface, (reading,), narr, cloud, ssml_episode=episode_forced
        ):
            out.append(
                {
                    "type": "high_risk_unpinned",
                    "scene_id": sid,
                    "index": idx,
                    "surface": surface,
                    "detail": cloud[
                        max(0, cloud.find(surface) - 12) : cloud.find(surface) + len(surface) + 12
                    ],
                    "note": (
                        f"episode_config.pronunciation_high_risk が「{surface}」の読みを "
                        f"{reading} と名指ししているのに、narration_speech_cloud には "
                        f"「{surface}」が元の表記のまま残っている (= Chirp 自動読み任せ)。"
                        f"この欄は cloud 合成では参照されないので、書いただけでは効かない。"
                        f"対処: narration (字幕) は漢字のまま、narration_speech_cloud の"
                        f"当該箇所だけ「{reading}」に置換する"
                    ),
                }
            )
    return out


def _scan_wording_divergence(sid, idx, narr, cloud):
    """(9) cloud が narration と違う「語」を喋る (字幕と音声の食い違い)。

    cloud は読みを明示するためのもので、語そのものを言い換える場所ではない。
    ある回は narration「逸話」に対し cloud「エピソード」と書いてしまい、
    字幕と音声が別の語になっていた。カタカナ全般を見ると「エックス」「オカキヨシ」
    「タヘンスウフクソカンスウロン」等の正当な読み下しに大量誤爆する (出荷実測) ので、
    **言い換えに使われやすい借用語**に限定する。出荷済み全話で誤検知ゼロ。
    """
    if not cloud or not narr:
        return []
    out = []
    for w in _PARAPHRASE_LOANWORDS:
        if w in cloud and w not in narr:
            out.append(
                {
                    "type": "wording_divergence",
                    "scene_id": sid,
                    "index": idx,
                    "surface": w,
                    "detail": cloud[max(0, cloud.find(w) - 12) : cloud.find(w) + len(w) + 10],
                    "note": (
                        f"cloud にだけ「{w}」がある (narration に無い)。読みの明示ではなく"
                        "語の言い換えになっており、字幕と音声が別の語を伝える。"
                        "narration と同じ語に戻す (読みを変えたいなら平仮名で書く)"
                    ),
                }
            )
    return out


# 合成時に SSML phoneme で読みが固定される語 (cloud_tts._READING_OVERRIDES)。
# import 失敗時は空 dict にして、この scanner だけ黙って no-op にする。
try:
    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    )
    from cloud_tts import _READING_OVERRIDES as _FORCE_READINGS
except Exception:
    _FORCE_READINGS = {}


def _scan_kana_over_force(sid, idx, narr, cloud):
    """(19) force 層がある語をわざわざ かなに開いて壊している。

    `cloud_tts._READING_OVERRIDES` に載っている語は、合成直前に SSML
    `<phoneme alphabet="yomigana">` で読みが固定される。**漢字のまま渡すのが正解**で、
    親切のつもりで `narration_speech_cloud` に かな を直書きすると force 層の対象から
    外れ、素の かな として読まれる。

    ある回は「一度離れてから」を `いちどはなれてから` と開いた結果、Chirp が
    **「いちど**あ**なれてから」** と読んだ。同じ回の `person_07` は漢字のまま
    「一度離れ、」で**正しく読まれており**、かな直書きだけが壊れたという対照が
    出荷 wav に残っている。かな は「は」が助詞に見えるなど別の曖昧さを持ち込むので、
    **force 層がある語では漢字が優れる**。

    判定は決定論: narration に override 対象の語があり、cloud 側ではその語が消えて
    読み (かな) に置き換わっていれば発火。
    """
    if not cloud or not narr:
        return []
    out = []
    for word, yomi in _FORCE_READINGS.items():
        # 壊れる機構は「かなに開いた結果 は が助詞に見えて弱まる」こと。
        # 出荷 69 話で素の一致は 16 件出るが、そのうち は/へ を含むのは ある回の
        # 「いちどはなれ」だけで、他 (ひせんけい/そうず/にじょう/じょしゅ…) は
        # user の耳でも正しく読まれている。**述語を機構に合わせて は を含む読みだけに
        # 絞る** -- 素の一致で警告すると、動いているものまで鳴らして lint 全体の
        # 信用を落とす。へ を含む「そうへいめん」も出荷 wav では正読だったので外した
        # (語中の へ は助詞に見えない)。較正後の出荷 69 話での発火は 0 件。
        if "は" not in yomi:
            continue
        if word in narr and word not in cloud and yomi in cloud:
            out.append(
                {
                    "type": "kana_over_force",
                    "scene_id": sid,
                    "index": idx,
                    "surface": f"{word} -> {yomi}",
                    "detail": cloud,
                    "note": (
                        f"「{word}」は合成時の force 層 (SSML phoneme) で読みが固定される。"
                        f"cloud で かな に開くと force の対象から外れ、素の かな として"
                        f"読まれて別の誤読を招く (ある回「一度離れて」-> いちどあなれて)。"
                        f"**漢字のまま**にする"
                    ),
                }
            )
    return out


def _scan_comma_elongation(sid, idx, narr, cloud):
    """(7) 1文に読点が多く助詞+読点が連続すると Chirp が読点前の母音を伸ばし不自然
    (ある回「力学から、図を、そして幾何学そのものを、」-> からー 図をー そのものをー)。
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
                    "(ある回からー図をー)。読点を減らす/「まで」等で助詞+読点の連続を崩す"
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
        # two lengths differ. An earlier episode=0.57 vs normal adjacent <=0.11.
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

    # episode_config が名指しした危険語 (隣の episode_config.json)。無ければ空。
    high_risk = load_high_risk_words(scene_path)
    # episode_config.cloud_reading_overrides (SSML で合成時固定) は多読み検査で固定済み扱い。
    episode_forced = load_episode_forced_readings(scene_path)

    warnings = []
    # cloud 配列の長さが narration と違う scene は、合成器がその配列を捨てて
    # narration_speech / narration を喋る。cloud に書いた読みは 1 つも効いていない。
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            if cloud_array_status(scene) == "length_mismatch":
                n_c = len(scene.get("narration_speech_cloud") or [])
                n_n = len(scene.get("narration") or [])
                warnings.append(
                    {
                        "type": "cloud_length_mismatch",
                        "scene_id": scene.get("scene_id", "?"),
                        "index": 0,
                        "surface": "",
                        "detail": f"narration_speech_cloud {n_c} 文 / narration {n_n} 文",
                        "note": (
                            "長さが違うので合成器はこの cloud 配列を捨て、narration_speech か narration を"
                            "喋る (cloud に書いた読みは効かない)。対処: 文の数を narration と揃える"
                        ),
                    }
                )
    for sid, idx, narr, cloud in _iter_scenes(scene_def):
        warnings.extend(_scan_polyphone(sid, idx, narr, cloud, episode_forced))
        warnings.extend(_scan_letter_long_vowel(sid, idx, narr, cloud))
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
        warnings.extend(_scan_digit_fraction(sid, idx, narr, cloud))
        warnings.extend(_scan_bare_kaku(sid, idx, narr, cloud))
        warnings.extend(_scan_bare_kon(sid, idx, narr, cloud))
        warnings.extend(_scan_itta(sid, idx, narr, cloud))
        warnings.extend(_scan_classical_quote(sid, idx, narr, cloud))
        warnings.extend(_scan_bare_kyuu(sid, idx, narr, cloud))
        warnings.extend(_scan_kana_over_force(sid, idx, narr, cloud))
        warnings.extend(_scan_comma_elongation(sid, idx, narr, cloud))
        warnings.extend(_scan_kana_only_particle(sid, idx, narr, cloud))
        warnings.extend(_scan_particle_ha_before_ha(sid, idx, narr, cloud))
        warnings.extend(_scan_wording_divergence(sid, idx, narr, cloud))
        warnings.extend(_scan_high_risk_unpinned(sid, idx, narr, cloud, high_risk, episode_forced))
    # scene 単位 (隣接要素比較) の scan
    for section in scene_def.get("sections", []):
        for scene in section.get("scenes", []):
            warnings.extend(
                _scan_adjacent_dup(scene.get("scene_id", "?"), scene.get("narration", []) or [])
            )
    return warnings


# ---- (11) 合成後 STT 用の誤読表 ----
# (surface, 正読カタカナ, [STT が書いた誤読カタカナ], note)。多読み表 _POLYPHONE (合成前 lint) と
# 同じ語が 15 件重なる。前は 2 ファイルに別々に書かれていて、読みが食い違っても誰も気づけなかった。
# ここに置き、stt_qa / verify_shipped_audio は stt_misread_checks() で導出する。
# 表に無い語の合成前 lint が無い (外から / 外国 等は文脈依存で静的には言えない) のは意図。
# narration の表層 -> (期待カタカナ, [誤読カタカナ...], note)。多読み漢字の
# 文脈依存誤読を、narration に surface があり STT に誤読カタカナが出た場合に
# WARN する。surface は誤読が起きる文脈に限定して
# FP を避ける (例: 「大学に入」= 入学 = はいる)。カタカナ照合は空白/句読点を
# 除去して行う (_norm_kana)。実測で FP を確認してから足すこと。
_STT_MISREAD_ROWS = [
    (
        "主著",
        "シュチョ",
        ["シュチョー", "シュチョウ", "シチョウ", "シチョー", "主張"],
        "主著=しゅちょ が『しゅちょう』(主張) 化した恐れ (ある回 scene wav『シチョウ』+ "
        "出荷 wav『主張』の 2 サンプルで確定)。今後のビルドは cloud_tts._READING_OVERRIDES "
        "の SSML phoneme で固定済。出荷済み分の再ビルドは user 判断",
    ),
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
    # --- user 耳 / 出荷 wav STT 検出。cloud_reading_lint の
    #     合成前 advisory を、実 wav でも backstop する層 (決定打=実 wav STT)。---
    (
        "第九巻",
        "ダイキュウカン",
        ["ダイクカン", "ダイクカ"],
        "第九巻=だいきゅうかん の 九 が『く』化した恐れ (ある回 STT『大区間』)。『だいきゅうかん』に固定",
    ),
    (
        "何ひとつ",
        "ナニヒトツ",
        ["トヒトツ"],
        "何ひとつ=なにひとつ の 何 が脱落し『とひとつ』化した恐れ。『なにひとつ』に固定",
    ),
    # --- user が耳で見つけた。**どれも辞書に無く、合成前も合成後も
    #     一件も警告できなかった**。同じ穴を次で開けないための backstop。---
    (
        "黒板",
        "コクバン",
        ["クロイタ"],
        "黒板=こくばん が『くろいた』化した恐れ (ある回、user 耳)。『こくばん』に固定",
    ),
    (
        "道路工夫",
        "コウフ",
        ["クフウ"],
        "工夫=こうふ(労働者) が『くふう』化した恐れ (ある回、user 耳)。『こうふ』に固定",
    ),
    (
        "へ行って",
        "イッテ",
        ["オコナッテ"],
        "行=いく が『おこなう』化した恐れ (ある回、user 耳)。『いって』に固定",
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
        "通=かよう が『とおる』化した恐れ (ある回、user 耳)。『かよった』に固定"
        " ※『筋の通った』は とおった が正しいので混同しないこと",
    ),
    (
        "塩水",
        "シオミズ",
        ["エンスイ"],
        "塩水=しおみず が『えんすい』化した恐れ (ある回、出荷 STT で実測)。『しおみず』に固定",
    ),
]


def stt_misread_checks() -> list:
    """stt_qa._READING_CHECKS の形 (surface, correct, wrongs, note) で返す。"""
    return [tuple(row) for row in _STT_MISREAD_ROWS]


_CATEGORY_TAG = {
    "polyphone": "多読み未固定",
    "letter_long_vowel": "字母の長音(エー→エイ)",
    "high_risk_unpinned": "config指定の読みが未固定",
    "kana_only_particle": "全文かな(助詞ha化)",
    "particle_ha_before_ha": "助詞はの直後がは(かな並び)",
    "wording_divergence": "字幕と音声で語が違う",
    "kei_unit": "位(京=けい)",
    "standalone_num": "多読み(数=かず/すう)",
    "homophone": "同音誤解",
    "hard": "難語",
    "pause_towa": "間(とは)",
    "pause_long_subject": "間(長主語)",
    "blanket_wa": "一括は→わ",
    "inline_particle_wa": "助詞は→わ過剰変換",
    "rephrase_risk": "発音リスク(言い換え推奨)",
    "raw_formula": "生記号(L=T-V/f'(x)/π/＝等)",
    "bare_fraction": "生分数(N/M)",
    "digit_fraction": "分数(算用数字2桁以上)",
    "comma_elong": "コンマ伸ばし",
    "adjacent_dup": "隣接文重複",
    "classical_quote": "文語引用",
    "cloud_length_mismatch": "cloud配列の長さ不一致(合成で捨てられる)",
    # (2026-09-19): emit されるのにタグが無かった 1 種。回帰 check_reading_tables が
    # 「emit される type == _CATEGORY_TAG のキー」を固定する (doc の系統数はここから数える)。
    "kana_over_force": "force語のかな直書き(SSMLと二重)",
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
    print("        (2)同音誤解語は言い換え、(3)難語は平易化、(4)間の構文は文分割/言い換え、")
    print("        (5)config指定の読みは narration_speech_cloud の当該箇所だけを平仮名に置換")
    print("           (字幕=narration は漢字のままでよい)。")
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
