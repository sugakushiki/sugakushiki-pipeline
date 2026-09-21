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
- 自動ルールは取りこぼす。STT 自体も取りこぼす (ある回の助詞「の」を
  取り逃した実績あり)。よって書き起こし全文を report に残し、人手レビュー併用を
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cloud_reading_lint as _crl  # noqa: E402

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
        # An earlier episode: unreliable in katakana-particle mode (Gemini renders は->ハ, を->ヲ,
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


# ---------------------------------------------------------------------------
# 名前末尾「ハ」の偽陽性抑止
#
# particle-ha-as-HA は「カタカナ直後のハ + 句読点/空白」を助詞位置と見なすが、
# 主題名が「ハ」で終わるエピソード (バナッハ) では名前そのものの末尾ハが
# 「バナッハ ノ」「バナッハ ガ」の形で系統的に誤発火する。
# STT は名前の綴りも揺らす (バラッハ / バナハ が実レポートに実在) ので、
# narration から「ハ」で終わるカタカナ語を抽出した辞書と **編集距離 1 まで** の
# 曖昧照合で抑止する。真陽性「名前+誤読助詞ハ」(バナッハハ、) は距離 2 になる
# ため発火が維持される (窓は len(name)-1 / len(name) のみ。len+1 窓を入れると
# この真陽性を巻き込むので入れない)。
# ---------------------------------------------------------------------------

# narration 中の「ハで終わる完結したカタカナ語」。後ろにカタカナが続く語中ハ
# (シュタインハウス の ハ) を辞書に入れない — 入れると「シュタイン + 助詞ハ」型の
# 真陽性を抑止してしまう。
_HA_FINAL_NAME_RE = re.compile(r"[ァ-ヶー]{2,}ハ(?![ァ-ヶー])")


def collect_ha_final_names(scene_def: dict) -> frozenset:
    """scene_def の narration / narration_speech_cloud から「ハ」で終わる
    カタカナ語 (バナッハ 等) を抽出する。無ければ空 = 挙動は従来と完全一致。"""
    names = set()
    for scene in _iter_scenes(scene_def):
        texts = list(scene.get("narration") or [])
        texts += [t for t in (scene.get("narration_speech_cloud") or []) if t]
        for t in texts:
            for m in _HA_FINAL_NAME_RE.finditer(t.replace("|", "")):
                names.add(m.group(0))
    return frozenset(names)


def _levenshtein(a: str, b: str) -> int:
    """短いカタカナ語専用の素朴な編集距離 (名前照合は高々 10 文字程度)。"""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _is_name_final_ha(transcript: str, ha_pos: int, ha_names) -> bool:
    """transcript[ha_pos] の「ハ」が、辞書中の名前 (バナッハ等) 自身の末尾か判定する。

    - token = ハ で終わる最大カタカナ連 (STT の空白分かち書きでも語単位で取れる)
    - 完全一致 (endswith) に加え、STT の綴り揺れ (バラッハ / バナハ) を
      suffix 窓 len(name)-1 / len(name) の編集距離 <= 1 で許容する。
    - 真陽性の「名前 + 誤読助詞ハ」(バナッハハ) は距離 2 になり抑止されない。
    """
    start = ha_pos
    while start > 0 and re.match(r"[ァ-ヶー]", transcript[start - 1]):
        start -= 1
    token = transcript[start : ha_pos + 1]
    for name in ha_names:
        if len(name) < 3:
            continue
        if token.endswith(name):
            return True
        # narration 側が「スティファンバナッハ」のような融合連の場合 (token の方が短い)
        if len(token) >= 3 and name.endswith(token):
            return True
        # 名前 + 助詞ハ (真陽性) は明示的に除外してから曖昧照合へ
        if token.endswith(name + "ハ"):
            continue
        for w in (len(name) - 1, len(name)):
            if w < 3 or w > len(token):
                continue
            if _levenshtein(token[-w:], name) <= 1:
                return True
    return False


def scan_stt_rules(transcript: str, ha_names=frozenset()) -> list:
    """_STT_RULES を 1 transcript に適用し (name, ctx, note) hits を返す。

    stt_qa (scene wav) と verify_shipped_audio (出荷 mp4) の**共有実装**。
    ある回で「corpus は import したのに katakana-mode guard だけ import し忘れ、
    決定打であるはずの shipped 検査の方が偽陽性に弱かった」型を、判定を 1 実装に
    まとめることで再発不能にする。katakana-mode guard も名前末尾ハ抑止
    もここに含まれる。
    """
    hits = []
    km = _is_katakana_mode(transcript)
    for rule in _STT_RULES:
        if rule.get("katakana_unreliable") and km:
            continue  # An earlier episode: skip particle-は=ハ in katakana-particle mode (FP)
        for m in rule["regex"].finditer(transcript):
            if (
                rule["name"] == "particle-ha-as-HA"
                and ha_names
                and _is_name_final_ha(transcript, m.end() - 1, ha_names)
            ):
                continue  # ある回: 名前 (バナッハ) 自身の末尾ハは助詞ではない
            s = max(0, m.start() - 6)
            e = min(len(transcript), m.end() + 6)
            hits.append((rule["name"], transcript[s:e], rule["note"]))
    return hits


# (2026-09-19): 誤読の表は cloud_reading_lint._STT_MISREAD_ROWS に移した (多読み表 _POLYPHONE の隣)。
# 同じ語が 2 つの表に別々に書かれる状態をやめ、ここは導出だけ。形は不変: (surface, 正読カタカナ, [誤読カタカナ], note)。
_READING_CHECKS = _crl.stt_misread_checks()


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


def _collect_reading_overrides(scene_def, scene_dir):
    """読みを固定している語をすべて集める: global force 辞書 + episode の上書き。

    どちらも「この語はこう読ませる」と決めた語なので、出荷 wav でそう読まれたかを
    確かめる対象は同じである。使われている scene も一緒に返す (narration_speech_cloud
    に表層が出る scene = SSML で読みが差される scene)。
    """
    readings: dict[str, str] = {}
    try:
        _src = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
        )
        if _src not in sys.path:
            sys.path.insert(0, _src)
        import cloud_tts

        readings.update(cloud_tts._READING_OVERRIDES)
    except Exception:
        pass
    # episode の上書きは cloud_reading_config が読む (5 か所の独自 json.load を 1 本化)。
    # global が優先 (較正済みの読みを ep 側に壊させない = cloud_tts と同じ順)
    try:
        from cloud_reading_config import load_cloud_reading_config

        readings = {**load_cloud_reading_config(scene_dir).overrides, **readings}
    except Exception as e:  # noqa: BLE001 - src が path に無い環境でも QA は続ける
        print(f"  [WARN] episode の cloud_reading_overrides を読めませんでした: {e}")
    usage: dict[str, list] = {}
    for scene in _iter_scenes(scene_def):
        sid = scene.get("scene_id", "?")
        # SSML は「合成器が送る文」に当たるので、その文 (cloud → speech → narration、
        # 長さ不一致は捨てる) で表層の有無を見る。以前は cloud 配列だけを見ていた。
        try:
            from speech_source import effective_speech_lines

            text = " ".join(effective_speech_lines(scene, "cloud")[0])
        except Exception:  # noqa: BLE001 - src が path に無い環境では従来どおり cloud 配列
            text = " ".join(scene.get("narration_speech_cloud") or [])
        if not text:
            continue
        for surface in readings:
            if surface in text:
                usage.setdefault(surface, []).append(sid)
    return readings, usage


def _to_katakana(s: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


# 読み照合専用の追加正規化。**実測で確認できた揺れだけ** を入れる (推測で足さない)。
#   ヲ/オ : 助詞「を」を Gemini は ヲ とも オ とも書く。期待読み「コンヲフクゲ」に対し
#           書き起こしが「コンオフクゲン」で前方一致が外れ、正しく読めている 根 を
#           「不一致」と報告した。
#   ー    : 長音記号の有無が揺れる (コーシ / コウシ)。両側から落として比べる。
#   ヅ/ヂ : 四つ仮名の表記揺れ。
# _norm_kana 自体は既存の誤読ルール照合と共有なので触らない (較正が変わる)。
_READING_EQUIV = str.maketrans({"ヲ": "オ", "ヅ": "ズ", "ヂ": "ジ", "ー": None})


def _norm_reading(s: str) -> str:
    return _norm_kana(s).translate(_READING_EQUIV)


# 数詞で始まる読み固定語 (二色 / 六人 / 四つ ...) は、Gemini の片仮名モードが **数詞を
# 算用数字で書く** ことがある。期待読み ニショク の前方一致は外れ、正しく読めている 二色 が
# 「不一致 -- 文単位の wav でも出ません」と報告された。先頭の数詞かなを算用数字に置き換えた
# 別形も probe に加える (置換は先頭 1 字の数詞だけ = 実測した揺れの範囲。推測で広げない)。
_NUM_KANJI = {
    "一": ("1", ("いち", "いっ")),
    "二": ("2", ("に",)),
    "三": ("3", ("さん",)),
    "四": ("4", ("よん", "よっ", "し")),
    "五": ("5", ("ご",)),
    "六": ("6", ("ろく", "ろっ")),
    "七": ("7", ("なな", "しち")),
    "八": ("8", ("はち", "はっ")),
    "九": ("9", ("きゅう", "く")),
    "十": ("10", ("じゅう", "じゅっ", "じっ")),
}


def _reading_probes(surface: str, reading: str) -> list[str]:
    """期待読みの前方一致 probe と、先頭数詞を算用数字にした別形 probe。"""
    want = _norm_reading(_to_katakana(str(reading)))
    probes = [want[: max(3, min(len(want), 6))]]
    head = str(surface)[:1]
    if head in _NUM_KANJI:
        digit, kanas = _NUM_KANJI[head]
        for k in kanas:
            if str(reading).startswith(k):
                alt = _norm_reading(_to_katakana(digit + str(reading)[len(k) :]))
                probes.append(alt[: max(3, min(len(alt), 6))])
                break
    return [p for p in probes if p]


def classify_override_coverage(overrides, usage, transcripts) -> dict:
    """読みを **固定した語** ごとに、出荷 wav で読みを確認できたかを分類する。

    scene 単位のカバレッジ (上の summarize_reading_coverage) は「その scene の
    書き起こしが かな か」しか見ない。だが実際に知りたいのは **「読みを指定した語が
    その指定どおりに読まれたか」** である。ある回では読み上書き 17 語のうち 9 語しか
    照合できておらず、**user が耳で見つけた 干支・根・一余り は全部その未照合側**に
    いた。レポートはそれを一言も言っていなかった (「0 WARN」とだけ出た)。

    「指摘ゼロ」と「未検査」を区別せよ の、語の粒度での適用である。

    引数:
      overrides   {表層: 読み(かな)}  — global force 辞書 + episode の上書きを統合したもの
      usage       {表層: [scene_id...]} — その語が narration_speech_cloud に出る scene
      transcripts {scene_id: 書き起こし}

    返り値: {"confirmed": [...], "mismatch": [(語, 読み, [scene...])], "unverified": [...]}
      - confirmed  : どこかの scene の書き起こしに指定どおりの読みが出た
      - mismatch   : かな書き起こしの scene があるのに、指定した読みがどこにも出ない
      - unverified : その語を含む scene が全部漢字書き起こしで、原理的に判定できない
    """
    confirmed, mismatch, unverified = [], [], []
    for surface, reading in sorted(overrides.items(), key=lambda kv: -len(kv[0])):
        # **今回書き起こした scene に限る**。--scenes で一部だけ回したとき、検査して
        # いない scene で使われている語まで「検証不可」に数えると、「未検査」と
        # 「検証できなかった」を混ぜることになる (この検査自体が無くそうとしている
        # 混同そのもの)。実測: --scenes person_02,math_03 で回すと 18 語中 16 語が
        # 対象外なのに「検証不可 18」と表示された。
        scenes = [s for s in (usage.get(surface) or []) if transcripts.get(s)]
        if not scenes:
            continue
        want = _norm_reading(_to_katakana(str(reading)))
        probes = _reading_probes(surface, reading)
        kanji = [c for c in surface if "一" <= c <= "鿿"]
        saw_kana_scene = False
        hit = False
        for sid in scenes:
            t = transcripts.get(sid) or ""
            if not t:
                continue
            nt = _norm_reading(t)
            if any(p in nt for p in probes):
                hit = True
                continue
            # **その語が漢字のまま書き起こされていたら「検証不可」であって不一致ではない。**
            # scene 単位のカタカナ率で判定していたときは、漢字かな混じりの scene
            # が「検証可能」と誤分類され、漢字で
            # 書かれた 根 を「読みが効いていない」と報告した -- 出荷 wav を STT に
            # かけ直すと コンヲフクゲン で **正しく読めていた** (2026-09-06 実測)。
            if kanji and any(c in t for c in kanji):
                continue
            if len(re.findall(r"[ァ-ヶ]", t)) > len(t) * 0.3:
                saw_kana_scene = True
        if hit:
            confirmed.append(surface)
        elif saw_kana_scene and len(want) >= 3:
            mismatch.append((surface, str(reading), scenes))
        else:
            # **2 モーラ以下の読みは「出ない」ことを根拠にできない**:
            # 筒 -> つつ が scene 全体の書き起こしで「シカクイッニ」と縮み、不一致として
            # 報告された。出荷 mp4 から当該文だけ切り出して 2 回かけ直すと どちらも
            # 「シカクイツツニ」で **音声は正常** だった。長い書き起こしほど STT は
            # 短い語を落とすので、短い読みは「確認できず」に倒す (未検証は未検証と言う)。
            unverified.append(surface)
    return {"confirmed": confirmed, "mismatch": mismatch, "unverified": unverified}


_SENTENCE_TAKES = 3  # 文単位 wav のかけ直し回数 (かなで返るまで)


def confirm_mismatches_with_sentence_wavs(result, scene_def, audio_dir, transcribe) -> dict:
    """不一致候補を **文単位の wav** で再確認して確定させる (ある回で必要と判明)。

    stt_qa が STT にかけるのは **scene 単位** の wav (30〜60 秒) だが、長い音声ほど
    Gemini は語を潰す。ある回では scene 単位の書き起こしが「場合」を バイ、「根」を
    漢字のまま返し、いずれも「読みが効いていない」と報告した。ところが **文単位の
    wav をかけ直すと 6/6 テイクで バアイ、コンヲフクゲン** で、音声は正しかった。

    つまり不一致は「読みが違う」ではなく「長い書き起こしで消えた」ことが多い。
    候補は全話で数件しか出ないので、その文だけ追加で 1 回かけ直す ── **決定打は
    出荷物で取る**、を自動化する。読みが出れば確認済みへ格上げし、出なければ
    不一致のまま残す (今度は文単位の証拠つき)。

    `transcribe(wav_path) -> str` を注入するのは、この関数を API 無しで試験するため。
    """
    if not result.get("mismatch"):
        return result
    scenes = {s.get("scene_id"): s for s in _iter_scenes(scene_def)}
    confirmed = list(result["confirmed"])
    unverified = list(result["unverified"])
    still, promoted, undetermined = [], [], []
    for surface, reading, sids in result["mismatch"]:
        probes = _reading_probes(surface, reading)
        hit = False
        kana_takes = 0  # 読みを判定できた (かなで返った) テイクの数
        for sid in sids:
            sc = scenes.get(sid)
            if not sc:
                continue
            for i, line in enumerate(sc.get("narration_speech_cloud") or []):
                if surface not in line:
                    continue
                wav = os.path.join(audio_dir, f"{sid}_{i + 1:03d}.wav")
                if not os.path.exists(wav):
                    continue
                # ある回: 1 テイクだけだと Gemini が **その語を漢字で** 返したとき (枢機卿 ->
                # 「枢機卿」) 読みは判定できないのに「文単位でも出ません」と不一致に倒れた
                # (かけ直すと スウキキョウ)。かなで返るまで最大 _SENTENCE_TAKES 回かけ直し、
                # 一度もかなで返らなければ「不一致」ではなく「検証不可」に分類する。
                for _take in range(_SENTENCE_TAKES):
                    try:
                        t = transcribe(wav)
                    except Exception:  # noqa: BLE001 - advisory: 確認できなければ据え置き
                        break
                    if any(p in _norm_reading(t) for p in probes):
                        hit = True
                        break
                    if surface not in t:
                        kana_takes += 1  # かな (または別の読み) で返った = 判定できた
                        break
                if hit:
                    break
            if hit:
                break
        if hit:
            confirmed.append(surface)
            promoted.append(surface)
        elif kana_takes == 0:
            undetermined.append(surface)
            unverified.append(surface)
        else:
            still.append((surface, reading, sids))
    return {
        "confirmed": confirmed,
        "mismatch": still,
        "unverified": unverified,
        "promoted": promoted,
        "undetermined": undetermined,
    }


def summarize_override_coverage(result) -> list[str]:
    """classify_override_coverage の結果を報告行にする (print はしない = テスト可能)。"""
    n = len(result["confirmed"]) + len(result["mismatch"]) + len(result["unverified"])
    if not n:
        return []
    lines = [
        f"  読み固定した語の検証: 確認 {len(result['confirmed'])} / "
        f"不一致 {len(result['mismatch'])} / 検証不可 {len(result['unverified'])}  (全 {n} 語)"
    ]
    for surface, reading, scenes in result["mismatch"]:
        lines.append(
            f"    [!] {surface} -> {reading} が書き起こしに出ません "
            f"(scene: {','.join(scenes)})。**文単位の wav でも出ませんでした** -- "
            f"audio/{scenes[0]}_NNN.wav を耳で確認してください "
            f"(scene 全体の書き起こしは語を潰すので、ここは文単位で再確認済み)"
        )
    if result["unverified"]:
        lines.append(
            "    [!] 次の語は書き起こしが漢字のため読みを確認できていません -- 耳で確認してください:"
        )
        lines.append("        " + "、".join(result["unverified"]))
    return lines


def summarize_reading_coverage(coverage, reading_seen) -> list[str]:
    """報告行を組み立てて返す (print はしない)。

    「0 WARN」は「読みが正しい」ではなく「照合できた範囲で既知の誤読が出なかった」に
    すぎない。漢字で書き起こされた scene は読みを原理的に判定できないので、どれだけ
    検証できたのかを必ず一緒に出す (ある回: 23 scene 中 16 が検証不可なのに「0 WARN」
    とだけ表示し、user が耳で 5 件見つけた)。

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
    particle-は=ハ 検出が全 topic は に誤発火する (ある回「有限ノリストハ、」を
    ハ 誤読と偽陽性化し、不要な「わ」固定 -> revert の無駄を生んだ)。
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


def _sentence_wav_says_correct(scene, sid, surface, correct, audio_dir, client) -> bool:
    """その語を含む **文単位** の wav をかけ直し、正しい読みが出るか見る。

    scene 単位 (30〜60 秒) の書き起こしは長いほど語を潰す。ある回では「場合」が
    scene 単位で バイ と書き起こされ誤読に見えたが、文単位では 6/6 テイクで バアイ
    だった。誤読を報告する前に、その一文だけで裏を取る (候補は稀なので費用は小さい)。

    確認できなければ False を返して従来どおり報告する (**取り下げは証拠があるときだけ**)。
    """
    lines = scene.get("narration_speech_cloud") or scene.get("narration") or []
    for i, line in enumerate(lines):
        if surface not in line.replace("|", ""):
            continue
        wav = os.path.join(audio_dir, f"{sid}_{i + 1:03d}.wav")
        if not os.path.exists(wav):
            continue
        try:
            t = _norm_kana(_transcribe(client, wav))
        except Exception:  # noqa: BLE001 - advisory: 確認できなければ報告を残す
            return False
        if correct in t:
            return True
    return False


def _iter_scenes(scene_def: dict):
    """実装は scene_def.iter_scenes (5 か所にあった同じ走査を 1 つに)。"""
    _src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    from scene_def import iter_scenes

    yield from iter_scenes(scene_def)


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

    # ある回: 主題名が「ハ」で終わる ep (バナッハ) で particle-ha が名前末尾に
    # 系統誤発火するのを防ぐため、narration から ハ 終わり語辞書を先に作る。
    ha_names = collect_ha_final_names(scene_def)

    warnings = []
    report_lines = []
    n_checked = 0
    n_missing = 0
    coverage = []  # (sid, label, kanji_ratio) — 読みを検証できた scene の割合を出すため
    transcripts = {}  # sid -> 書き起こし。**語単位** の読み検証カバレッジに使う
    # 読みを固定した語 (global force 辞書 + この ep の cloud_reading_overrides) と、
    # それが実際に出てくる scene。scene 単位のカバレッジでは「読みを指定した語が
    # 指定どおり読まれたか」が分からず、ある回は 17 語中 8 語が未照合のまま出荷寸前
    # まで進んだ (user が耳で拾った 干支・根・一余り は全部その未照合側だった)。
    override_readings, override_usage = _collect_reading_overrides(scene_def, scene_dir)
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
        transcripts[sid] = transcript

        # 判定は scan_stt_rules に一本化 (katakana-mode guard / 名前末尾ハ抑止を含む)
        scene_hits = scan_stt_rules(transcript, ha_names)

        # 多読み漢字の文脈依存誤読: narration に surface があり、STT に誤読カタカナ
        # が出て (かつ正しい読みが出ていない) なら WARN。narration は漢字で照合、
        # 誤読は空白除去したカタカナ列で照合する。
        narr_text = " ".join(scene.get("narration", []) or []).replace("|", "")
        t_norm = _norm_kana(transcript)
        for surface, correct, wrongs, note in _READING_CHECKS:
            if surface not in narr_text:
                continue
            hit = [w for w in wrongs if w in t_norm]
            # 正読が誤読の部分文字列 (主著: シュチョ ⊂ シュチョー) だと、誤読時にも
            # correct が t_norm に「見つかって」検出漏れする。誤読ヒット箇所を除いた
            # 残りで correct の有無を判定する。
            t_wo_hit = t_norm
            for w in hit:
                t_wo_hit = t_wo_hit.replace(w, "")
            if hit and correct not in t_wo_hit:
                # **scene 単位の書き起こしだけを根拠にしない** (2026-09-06)。
                # 30〜60 秒の wav では Gemini が語を潰し、正しく読めている語を誤読と
                # 報告する。
                # 該当文の wav でかけ直し、そこで正しい読みが出れば取り下げる。
                if _sentence_wav_says_correct(scene, sid, surface, correct, audio_dir, client):
                    reading_seen.setdefault(surface, {"ok": [], "ng": []})["ok"].append(sid)
                    print(
                        f"  [読み] {sid}: {surface} は scene 単位で誤読に見えましたが、"
                        f"文単位の wav では {correct} でした (取り下げ)"
                    )
                    continue
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

    # scene 単位に加えて **語単位**: 読みを固定した語が、指定どおり読まれたか。
    _ov_result = classify_override_coverage(override_readings, override_usage, transcripts)
    if _ov_result["mismatch"]:
        # scene 単位で出なかった語だけ、その文の wav でかけ直して確定させる
        # (候補は全話で数件。長い書き起こしの取りこぼしを実測で潰す)。
        _ov_result = confirm_mismatches_with_sentence_wavs(
            _ov_result, scene_def, audio_dir, lambda w: _transcribe(client, w)
        )
        if _ov_result.get("undetermined"):
            print(
                f"  [読み] 文単位の wav をかけ直しても {len(_ov_result['undetermined'])} 語は"
                f"漢字で書き起こされ判定できません (不一致ではなく検証不可に分類): "
                f"{'、'.join(_ov_result['undetermined'])}"
            )
        if _ov_result.get("promoted"):
            print(
                f"  [読み] scene 単位で出なかった {len(_ov_result['promoted'])} 語を "
                f"文単位の wav で確認しました: {'、'.join(_ov_result['promoted'])}"
            )
    for line in summarize_override_coverage(_ov_result):
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
