"""speech_source.py — 「その文は何を合成するか」の唯一の解決 (, 2026-09-19)。

正は `audio_generator.resolve_scene_speech` にあった規則:
  cloud   : narration_speech_cloud[i] → narration_speech[i] → narration[i]、最後に strip_for_cloud
  voicevox: narration_speech[i] → narration[i]、最後に | (字幕マーカー) を落とす
  **narration と長さの違う配列は捨てる** (その配列は合成に使われない)

同じ選択を cloud_speed_qa (`_pick_speech`)・kana_reading_diff (`_iter_sentences`)・
cloud_reading_lint (`_iter_scenes`)・stt_qa が各自に書いていて、長さ不一致の規則を再現して
いたのは speed_qa だけだった。lint が「合成では捨てられる cloud 配列」を正として検査すると、
音声は narration_speech を喋っているのに lint は cloud を見て黙る (または逆) ことになる。
ここに寄せて、全員が**合成器と同じ文**を見る。

使い方
------
    from speech_source import speech_texts, pick_speech_text, effective_speech_lines, cloud_array_status
    speech_texts(scene, "cloud")        # 合成テキスト (strip 済) のリスト = 合成器が送る文
    pick_speech_text(scene, i, "cloud") # 1 文
    effective_speech_lines(scene, "cloud") -> (strip 前の各文, 由来 "cloud"|"speech"|"narration")
    cloud_array_status(scene)           -> "ok" | "missing" | "length_mismatch"
"""

from __future__ import annotations

import cloud_tts


def strip_subtitle_markers(text: str) -> str:
    """字幕の分割マーカー | を落とす (VOICEVOX に送る文)。"""
    return text.replace("|", "")


def _array_status(scene: dict, key: str) -> str:
    arr = scene.get(key)
    if arr is None:
        return "missing"
    narration = scene.get("narration") or []
    if not isinstance(arr, list) or len(arr) != len(narration):
        return "length_mismatch"
    return "ok"


def cloud_array_status(scene: dict) -> str:
    """narration_speech_cloud の状態: ok / missing / length_mismatch (合成では捨てられる)。"""
    return _array_status(scene, "narration_speech_cloud")


def speech_array_status(scene: dict) -> str:
    """narration_speech の状態: ok / missing / length_mismatch。"""
    return _array_status(scene, "narration_speech")


def effective_speech_lines(scene: dict, engine: str = "cloud") -> tuple[list[str], str]:
    """(strip 前の各文, 由来)。由来 = "cloud" | "speech" | "narration"。

    長さが narration と違う配列は無いものとして扱う (resolve_scene_speech と同じ)。
    """
    narration = list(scene.get("narration") or [])
    speech = scene.get("narration_speech") if speech_array_status(scene) == "ok" else None
    cloud = scene.get("narration_speech_cloud") if cloud_array_status(scene) == "ok" else None
    if engine == "cloud" and cloud is not None:
        return [str(x) for x in cloud], "cloud"
    if speech is not None:
        return [str(x) for x in speech], "speech"
    return [str(x) for x in narration], "narration"


def speech_texts(scene: dict, engine: str = "cloud") -> list[str]:
    """合成器が実際に送る文 (strip 済)。"""
    lines, _ = effective_speech_lines(scene, engine)
    if engine == "cloud":
        return [cloud_tts.strip_for_cloud(x) for x in lines]
    return [strip_subtitle_markers(x) for x in lines]


def pick_speech_text(scene: dict, i: int, engine: str = "cloud") -> str:
    """i 文目の合成テキスト (strip 済)。"""
    texts = speech_texts(scene, engine)
    return texts[i] if 0 <= i < len(texts) else ""
