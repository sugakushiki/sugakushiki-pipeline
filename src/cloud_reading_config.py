"""cloud_reading_config.py — episode_config.json の読み関連キーを読む唯一の loader (, 2026-09-19)。

読むキー:
  - `cloud_reading_overrides` : {表層: かな}。cloud_tts が SSML <phoneme> で合成時に固定する
                                (3 文字以上は gen_cloud_readings が cloud 文にかな直書き)
  - `cloud_direct_kana`       : [表層]。長さに関係なくかな直書きにする opt-in
  - `pronunciation_high_risk` : 人が手で書いた危険語リスト (自由文。VOICEVOX の prompt と
                                cloud_reading_lint の未固定検査が読む)

なぜ要るか
----------
2026-09-19 の棚卸しで、この 3 キーを **5 か所** (audio_generator / gen_cloud_readings ×2 /
stt_qa / cloud_reading_lint ×2) が各自に `json.load` していた。探すパスの規則も違っていた
(episode_dir とその親 / scene_definition.json の隣 / scene_dir) し、壊れた JSON の扱いも
WARN を出す所と黙る所があった。ここに寄せる: パスの解決を 1 つにし、壊れていれば **1 回だけ**
WARN を出して空を返す (lint やビルドをここで落とさない)。

使い方
------
    from cloud_reading_config import load_cloud_reading_config
    rc = load_cloud_reading_config(episode_dir_or_scene_json_path)
    rc.overrides   # dict[str, str]
    rc.direct_kana # tuple[str, ...]
    rc.high_risk   # list (生の entries)
    rc.path        # 読んだ episode_config.json のパス (無ければ None)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

_warned: set[str] = set()


@dataclass(frozen=True)
class CloudReadingConfig:
    overrides: dict = field(default_factory=dict)
    direct_kana: tuple = ()
    high_risk: list = field(default_factory=list)
    path: str | None = None

    @property
    def forced_surfaces(self) -> frozenset:
        """SSML で固定される表層 (cloud_reading_overrides のキー)。"""
        return frozenset(k for k in self.overrides if isinstance(k, str) and k)


EMPTY = CloudReadingConfig()


def resolve_episode_config_path(path: str | None) -> str | None:
    """episode_dir / scene_definition.json / episode_config.json / サブディレクトリ (audio/ 等) の
    どれを渡されても、対応する episode_config.json のパスを返す。無ければ None。"""
    if not path:
        return None
    p = os.path.abspath(path)
    if os.path.isfile(p):
        if os.path.basename(p) == "episode_config.json":
            return p
        p = os.path.dirname(p)
    for d in (p, os.path.dirname(p)):
        cand = os.path.join(d, "episode_config.json")
        if os.path.isfile(cand):
            return cand
    return None


def load_cloud_reading_config(path: str | None) -> CloudReadingConfig:
    """episode_config.json の読み関連キーを読む。無ければ EMPTY、壊れていれば WARN 1 回 + EMPTY。"""
    cfg_path = resolve_episode_config_path(path)
    if cfg_path is None:
        return EMPTY
    try:
        with open(cfg_path, encoding="utf-8") as f:
            config = json.load(f) or {}
    except Exception as e:  # noqa: BLE001 - 壊れた config でビルド/lint を落とさない (名指しはする)
        if cfg_path not in _warned:
            _warned.add(cfg_path)
            print(f"  [WARN] episode_config.json の読み設定を読めませんでした: {cfg_path}: {e}")
        return CloudReadingConfig(path=cfg_path)
    if not isinstance(config, dict):
        return CloudReadingConfig(path=cfg_path)
    ov_raw = config.get("cloud_reading_overrides") or {}
    overrides = (
        {str(k): str(v) for k, v in ov_raw.items() if k and v is not None}
        if isinstance(ov_raw, dict)
        else {}
    )
    dk_raw = config.get("cloud_direct_kana") or []
    direct_kana = (
        tuple(str(w) for w in dk_raw if isinstance(w, str) and w)
        if isinstance(dk_raw, list)
        else ()
    )
    hr_raw = config.get("pronunciation_high_risk") or []
    high_risk = list(hr_raw) if isinstance(hr_raw, list) else []
    return CloudReadingConfig(
        overrides=overrides, direct_kana=direct_kana, high_risk=high_risk, path=cfg_path
    )
