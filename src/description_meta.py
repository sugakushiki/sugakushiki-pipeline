"""description_meta.py - description.intro staleness detection.

`scene_definition.json` の `description.intro` は script_generator が LLM で
episode_config の導入系フィールド (theme / hook / modern_connection /
description.intro_guidance) から生成する。生成後にこれらの config フィールドを
編集しても intro は自動同期されず、credits_generator が古い intro をそのまま
description.txt (公開 YouTube 概要欄) に焼き込む。

既存の 2 チェックはこの config -> intro drift を捕まえない:
  - credits_generator.description_drift : description.txt を scene_def から
    再生成して比較。config 起因の stale は description.txt と scene_def が
    「同じ古い intro」で揃うため素通り (両方 stale なので diff ゼロ)。
  - qa_checker._detect_description_drift : intro <-> narration の 6-gram
    coverage。config は見ない。

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
        のまま = stale。
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
