"""description_meta.py - description.intro staleness detection.

`scene_definition.json` の `description.intro` は script_generator が LLM で
episode_config の導入系フィールド (theme / hook / modern_connection /
description.intro_guidance) から生成する。生成後にこれらの config フィールドを
編集しても intro は自動同期されず、credits_generator が古い intro をそのまま
description.txt (公開 YouTube 概要欄) に焼き込む (経緯: ある時点 で config を
「半世紀以上後→およそ60年後」に直したのに scene_def.description.intro は旧文
「半世紀後」のまま残り、手動修正 + credits 再実行で fix した事故)。

既存の 2 チェックはこの config -> intro drift を捕まえない:
  - credits_generator.description_drift : description.txt を scene_def から
    再生成して比較。config 起因の stale は description.txt と scene_def が
    「同じ古い intro」で揃うため素通り (両方 stale なので diff ゼロ)。
  - qa_checker._detect_description_drift : intro <-> narration の 6-gram
    coverage (方向)。config は見ない。

intro_guidance と intro の内容比較も不可能: intro_guidance は長い手書き
ガイダンス、intro は短い要約なので、同期済みの出荷 ep でも SequenceMatcher
ratio が 0.05-0.5 に散らばり、stale / in-sync を分離する閾値が存在しない
(全 57 ep 実測)。よって決定論検出は署名方式が唯一の道。

  検出方式 (Guard-B / _subtitles_meta.json の拡張):
    生成時に `_description_meta.json` へ
      intro_config_sig  = 導入系 config フィールドの署名
      intro_text_hash   = scene_def.description.intro テキストの hash
    を刻印し、照合時に **config 署名が変化 AND intro テキストが刻印時から不変**
    の両成立でのみ WARN する。
      - config を編集したのに intro が「刻印時のバイト列そのまま」= 旧生成文
        のまま = stale (の失敗そのもの)。
      - intro を手で直したら text hash が変わる -> 「同期済みとみなして」抑止。
        これにより手動 sync 後に WARN が居座る FP と re-stamp 運用を不要にする
        (naive な mtime / 署名だけの比較との決定的な違い)。

  後方互換: sidecar 無し (出荷済み全 ep) は no-op。フィールド範囲は references /
  bgm / tts / key_topics / math_content を **除外** し、導入の語りを形作る 4
  フィールドに限定 (body 編集での誤発火を防ぐ)。

刻印: script_generator が scene_definition.json 書き出し直後に write_meta()。
照合: pipeline.verify_outputs (advisory WARN) + scripts/check_description_staleness.py。
"""

import datetime
import hashlib
import json
import os
import re

META_FILENAME = "_description_meta.json"

# 導入 (description.intro) の語りを直接形作る config フィールド。
# ここに無い references / bgm / tts / key_topics / math_content の編集では
# WARN しない (intro の内容に効かない or body 側なので FP になる)。
# 表示ラベル -> config からの取り出し方 (top-level か description.* か)。
INTRO_CONFIG_FIELDS = ("theme", "hook", "modern_connection", "intro_guidance")


def _field_values(config: dict) -> dict:
    """導入系 config フィールドの生値 (str) を {label: value} で返す。"""
    desc = config.get("description", {}) or {}
    return {
        "theme": config.get("theme", "") or "",
        "hook": config.get("hook", "") or "",
        "modern_connection": config.get("modern_connection", "") or "",
        # intro_guidance は config["description"]["intro_guidance"] (手書きの
        # 導入意図。LLM には非渡しだが「intro はこう書け」という人間の意図の
        # 正準ソースなので、編集されたら intro の再同期が要る)。
        "intro_guidance": desc.get("intro_guidance", "") or "",
    }


def _field_hashes(config: dict) -> dict:
    """各導入フィールドの短縮 hash {label: 12-hex}。どのフィールドが変わったかを
    WARN で名指しするために per-field で保持する。前後空白のみの差分での FP を
    避けるため strip() する。"""
    out = {}
    for label, val in _field_values(config).items():
        out[label] = hashlib.sha256(str(val).strip().encode("utf-8")).hexdigest()[:12]
    return out


def intro_config_signature(config: dict) -> str:
    """導入系 config フィールド全体の決定論署名 (16-hex)。per-field hash を
    正準順で連結して hash するので _field_hashes と整合する。"""
    fh = _field_hashes(config)
    blob = "|".join(f"{k}={fh[k]}" for k in sorted(fh))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _intro_text(scene_def: dict) -> str:
    return (scene_def.get("description", {}) or {}).get("intro", "") or ""


def intro_text_hash(scene_def: dict) -> str:
    """scene_def.description.intro テキストの決定論 hash (16-hex)。"""
    return hashlib.sha256(_intro_text(scene_def).encode("utf-8")).hexdigest()[:16]


def build_meta(config: dict, scene_def: dict) -> dict:
    """sidecar に書く dict を組み立てる (I/O なし。テスト・再刻印から共有)。"""
    return {
        "intro_config_sig": intro_config_signature(config),
        "intro_config_fields": _field_hashes(config),
        "intro_text_hash": intro_text_hash(scene_def),
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def write_meta(episode_dir: str, config: dict, scene_def: dict) -> str | None:
    """`_description_meta.json` を書き出し path を返す。description.intro が空
    (guard 対象なし) なら何もせず None。script_generator の scene_def 書き出し
    直後に呼ばれる。"""
    if not _intro_text(scene_def).strip():
        return None
    path = os.path.join(episode_dir, META_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(build_meta(config, scene_def), f, ensure_ascii=False, indent=2)
    return path


def _changed_fields(embedded_fields: dict, config: dict) -> list[str]:
    """刻印時の per-field hash と現 config を突き合わせ、変化したフィールド名を
    返す。刻印が古く intro_config_fields を持たない場合は [] (名指し不能)。"""
    if not isinstance(embedded_fields, dict) or not embedded_fields:
        return []
    current = _field_hashes(config)
    return [k for k in INTRO_CONFIG_FIELDS if embedded_fields.get(k) != current.get(k)]


def check_staleness(episode_dir: str, config: dict, scene_def: dict) -> str | None:
    """description.intro が config に対して stale なら WARN 文字列を返す。
    健全 / 判定不能 / 後方互換 no-op なら None。

    トリガー: (config 署名が変化) AND (intro テキストが刻印時から不変)。
      - intro を手で直していれば text hash が変わり None (同期済みとみなす)。
      - config を変えていなければ署名一致で None。
    """
    meta_path = os.path.join(episode_dir, META_FILENAME)
    if not os.path.exists(meta_path):
        return None  # 後方互換: 出荷済み ep は sidecar 無し -> no-op
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    embedded_sig = meta.get("intro_config_sig")
    embedded_text = meta.get("intro_text_hash")
    if not embedded_sig or not embedded_text:
        return None  # 不完全な刻印 -> 判定不能

    # 条件 2: intro テキストが刻印時から不変か。手編集されていれば sync 済みと
    # みなして抑止 (FP 回避・re-stamp 不要の肝)。
    if intro_text_hash(scene_def) != embedded_text:
        return None

    # 条件 1: 導入系 config が変化したか。
    if intro_config_signature(config) == embedded_sig:
        return None  # in sync

    changed = _changed_fields(meta.get("intro_config_fields", {}), config)
    field_str = " / ".join(changed) if changed else "導入系 config フィールド"
    return (
        f"episode_config の {field_str} が script 生成後に編集されましたが、"
        "description.intro は刻印時のまま (旧生成テキスト) です -> stale の可能性。"
    )


# ---------------------------------------------------------------------------
# 数量ドリフト検出
#
# は config -> intro の drift を見る。だが ある回で踏んだのは **narration ->
# intro** の drift だった: narration の「何十万年」を原典に合わせて「何百万年」に
# 直したのに、`description.intro` は scene_definition に固定保存されていて
# `--steps credits` では再生成されないため、**音声と字幕は何百万年・概要欄だけ
# 何十万年** という食い違いのまま出るところだった (grep で偶然見つけた)。
#
# narration 全体のハッシュで見る案は退けた: ある回の narration 編集 4 件のうち
# 3 件は intro と無関係で、そのたび空振りする。 が FP 0 なのは対象を導入系の
# 4 フィールドに絞っているからで、narration 全体はその条件を満たさない。
#
# 代わりに **intro が名指しする数量トークン** が narration にあるかだけを見る。
# 較正 (出荷 68 話、漢数字↔算用数字を正規化した後): **1 話**で発火。それは
# 「intro にだけ年号がある」型で、今回の「同じ量について食い違う」型とは別。
# よって **advisory** であってゲートではない。
# ---------------------------------------------------------------------------

_QUANTITY_RE = re.compile(
    r"何[十百千]?[万億]?[年人倍通り]|[0-9]{3,4}年|[一二三四五六七八九十百千万]{2,}[年人問巻次個]"
)

_KANJI_DIGIT = {
    "〇": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
}


def _norm_numerals(text: str) -> str:
    """漢数字と算用数字の表記違いを吸収する。

    較正で分かった偽陽性はこれだけだった: 042_mandelbrot は intro「二千年」/
    narration「2000年」、046_boole はその逆。**同じ量を言っているのに表記が違うだけ**
    なので、正規化しないとこの 2 話が毎回鳴る。
    """
    t = text
    for k, v in _KANJI_DIGIT.items():
        t = t.replace(k, v)
    # 位取り語を落として桁だけ残す (2千年 -> 2000年 相当の粗い正規化)
    t = t.replace("千年", "000年").replace("百年", "00年")
    return t


def intro_quantity_drift(scene_def: dict) -> list:
    """intro が名指しする数量トークンのうち、narration に見当たらないものを返す。

    空リスト = ドリフトなし。**advisory 用**。較正 (2026-09-06、出荷 68 話): **1 話**。
    正規化を入れる前は 6 話出て、うち 5 話は「二千年 vs 2000年」の表記違いだった
    (漢数字↔算用数字を揃えると消える)。残る 1 件は「本編が言っていない年号を概要欄が
    足している」型で、今回の失敗 (intro と narration が同じ量について食い違う) とは
    別の話だが、どちらも人が見て判断すべきもの。**ゲートにはしない。**
    """
    intro = ((scene_def.get("description") or {}).get("intro")) or ""
    if not intro:
        return []
    narr = "".join(
        line.replace("|", "")
        for section in scene_def.get("sections", [])
        for scene in section.get("scenes", [])
        for line in (scene.get("narration") or [])
    )
    narr_n = _norm_numerals(re.sub(r"[\s\u3000]+", "", narr))  # ある回: 空白差で偽警告を出さない
    missing = []
    for tok in _QUANTITY_RE.findall(intro):
        if tok in narr:
            continue
        if _norm_numerals(re.sub(r"[\s\u3000]+", "", tok)) in narr_n:
            continue  # 表記違いだけ (二千年 vs 2000年)
        if tok not in missing:
            missing.append(tok)
    return missing
