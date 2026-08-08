#!/usr/bin/env python3
"""review_reel.py -- 変更シーンだけのレビューリール + 未変更区間の同一性証明.

## なぜ要るか

出荷済み在庫を 1 箇所直すと、確認のために 17 分の動画を通しで見直すことになる。
この負担が事実上の抑止力になり、**直せば直る欠陥が「触らない」に倒れる**。
増分キャッシュ は再ビルドの計算コストを数分に下げたが、人間のレビュー
コストは下げていない。ボトルネックはこちらに移っている。

ただし を user と詰めた結論は「リールだけでは足りない」だった。変更シーン
だけ見ても、**尺シフトや再エンコードが未変更部分に及んでいないか**の不安が残る
ためで、本ツールは 2 本立てにしてある:

  (a) 変更シーン (±pad 秒の文脈) だけを繋いだレビュー用 mp4
  (b) 未変更シーンが本当に変わっていないことの証明
      (フレームハッシュ + timing + 字幕の 3 点)

## 使い方

ビルド前 (pipeline が自動で実行する)::

    python scripts/review_reel.py episodes/XXX --snapshot

ビルド後 (pipeline が自動で実行する)::

    python scripts/review_reel.py episodes/XXX

`--snapshot` は現在の状態 (キャッシュ・timing・字幕・narration ハッシュ + 現行
output_final.mp4 のフレームハッシュ) を `_review_baseline.json` に書く。ビルド後の
実行はそれと現状を突き合わせ、変更シーンを特定してリールを切り出し、未変更シーンに
ついては証明を出す。

## 変更シーンの特定

`visuals/_visual_cache.json` (key + mp4 指紋) / `audio/_audio_cache.json` (text +
wav 指紋) / `timing.json` (尺) / `scene_definition.json` (narration) / `subtitles.srt`
の 5 経路の差分を取る。**mp4/wav の指紋も見る**ので `--force-regen-*` で内容キーが
同じまま再レンダした場合も変更として拾う。

## 未変更区間の証明

未変更と判定したシーンについて、baseline 時に現行動画から採った 1 シーン数枚の
フレーム (160x90 グレイスケールに落としたもの) のハッシュと、新しい動画の同じ
**シーン相対**位置のフレームを比較する。

- sha 一致            -> 同一 (再エンコードのゆらぎすら無い)
- dHash 距離 <= tol   -> 知覚的に同一 (エンコーダのノイズだけ)
- それ以上            -> 差異あり (未変更のはずのシーンが変わっている = 要調査)

FFmpeg は bit-deterministic ではないので sha 一致だけを合格条件にはできない。
一方 dHash だけだと「1 フレームずれ」を見逃すので、両方を出して区別する。

**dHash が見るのは絵の構造**なので、字幕 1 語の差し替えのような小さな変化は 160x90 の
縮小で消えて距離が伸びない。それはフレームの仕事ではなく、字幕ハッシュとキャッシュ
ハッシュの担当 (同一性の証明が 3 点なのはこのため)。フレームは「どのハッシュも予告
しなかった変化」を捕まえる最後の網として置いている。

## 直したものが動画に届いていない場合

キャッシュが「変わった」と言うのに `output_final.mp4` が baseline と 1 バイトも
変わっていないなら、**assemble / bgm を回していない** = 直したものが出荷物に入って
いない。この状態でリールを作ると**古い映像を「修正結果」として差し出す**ことになり、
ある回で修正前の動画をレビューさせてレビュー 1 周を無駄にしたのと同じ事故になる。
リールを作らず、何を回せばよいかを言う (`status="video_not_rebuilt"`)。

出力: `<episode_dir>/review_reel.mp4` (+ temp_videos へコピー) と
`<episode_dir>/review_reel_report.txt`。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASELINE_FILE = "_review_baseline.json"
REEL_FILE = "review_reel.mp4"
REPORT_FILE = "review_reel_report.txt"

DEFAULT_PAD = 2.0
# 変更が広範なら「リール」は通し視聴と変わらない。その場合はリールを作らず
# その事実を告げるほうが正しい (2 分で済むと誤解させない)。
DEFAULT_MAX_REEL_SEC = 420.0
DEFAULT_FRAMES_PER_SCENE = 3

# フレームハッシュ用の縮小サイズ。160x90 のグレイスケール = 14400 バイト。
# 実測 1 フレーム約 0.19 秒で採れるので 17 scene x 3 枚 = 約 10 秒。
FRAME_W, FRAME_H = 160, 90
# dHash は 9x8 に落として横隣接比較 -> 64 bit。
DHASH_W, DHASH_H = 9, 8
# 較正: 同じ時刻を 2 回採ると sha ごと一致 = 距離 0。
# 1 フレーム/3 フレームずらすと 0〜2 (最大 2)。同じ ep の別シーンとの比較は 32〜44。
# 再検証で**別エピソードの動画を当てて 51 フレーム**を測ると 18〜45 で、下限は 18
# だった (無地に近い題字カードは構造が乏しく距離が伸びない)。
# ずれとエンコーダのノイズ (最大 2) は通し、内容の変化 (実測下限 18) は落とす位置
# として 6 を採った。上下いずれにも 3 倍の余裕がある。
DEFAULT_DHASH_TOL = 6


# ---------------------------------------------------------------------------
# 低レベルユーティリティ
# ---------------------------------------------------------------------------


def _sha16(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def _load_json(path: str | Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _probe_duration(path: str) -> float | None:
    """ffprobe で動画尺を取得。読めなければ None。"""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                path,
            ],
            capture_output=True,
            timeout=60,
        )
        return float(proc.stdout.decode("utf-8", "replace").strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _file_fingerprint(path: str | Path) -> str:
    """'{len}:{sha256[:16]}'。visual/audio キャッシュの指紋と同じ形式。"""
    try:
        with open(path, "rb") as f:
            data = f.read()
        return f"{len(data)}:{hashlib.sha256(data).hexdigest()[:16]}"
    except OSError:
        return ""


def _extract_gray_frame(video: str, t: float) -> bytes | None:
    """動画の t 秒地点を FRAME_W x FRAME_H のグレイ raw で取り出す。

    stdout へ rawvideo を流すので中間ファイルを作らない (ffmpeg のログは stderr)。
    """
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-ss",
                f"{max(0.0, t):.3f}",
                "-i",
                video,
                "-frames:v",
                "1",
                "-vf",
                f"scale={FRAME_W}:{FRAME_H}",
                "-pix_fmt",
                "gray",
                "-f",
                "rawvideo",
                "-",
            ],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    data = proc.stdout
    return data if len(data) == FRAME_W * FRAME_H else None


def _dhash(frame: bytes) -> str:
    """FRAME_W x FRAME_H のグレイ raw から 64 bit の dHash を求める (hex 16 桁)。

    DHASH_W x DHASH_H へ箱平均で縮小し、横隣接ピクセルの大小で 1 bit ずつ。
    再エンコードの微小なノイズでは反転しないが、絵が変われば反転する。
    """
    cell_w = FRAME_W / DHASH_W
    cell_h = FRAME_H / DHASH_H
    small = []
    for gy in range(DHASH_H):
        y0, y1 = int(gy * cell_h), max(int(gy * cell_h) + 1, int((gy + 1) * cell_h))
        for gx in range(DHASH_W):
            x0, x1 = int(gx * cell_w), max(int(gx * cell_w) + 1, int((gx + 1) * cell_w))
            total = 0
            count = 0
            for y in range(y0, min(y1, FRAME_H)):
                row = y * FRAME_W
                for x in range(x0, min(x1, FRAME_W)):
                    total += frame[row + x]
                    count += 1
            small.append(total / count if count else 0.0)
    bits = 0
    n = 0
    for gy in range(DHASH_H):
        for gx in range(DHASH_W - 1):
            left = small[gy * DHASH_W + gx]
            right = small[gy * DHASH_W + gx + 1]
            bits = (bits << 1) | (1 if left > right else 0)
            n += 1
    return f"{bits:0{n // 4}x}"


def _hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except (TypeError, ValueError):
        return 64


def _sample_offsets(duration: float, n: int) -> list[float]:
    """シーン内のサンプル位置 (シーン相対秒)。端は 0.5 秒内側に寄せる。"""
    if duration <= 0:
        return []
    margin = min(0.5, duration / 4)
    lo, hi = margin, max(margin, duration - margin)
    if n <= 1 or hi - lo < 0.05:
        return [round((lo + hi) / 2, 3)]
    step = (hi - lo) / (n - 1)
    out = []
    for i in range(n):
        v = round(lo + step * i, 3)
        if v not in out:
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# エピソードの状態収集
# ---------------------------------------------------------------------------


def _scene_ids(scene_def: dict) -> list[str]:
    return [
        s.get("scene_id", "")
        for sec in scene_def.get("sections", [])
        for s in sec.get("scenes", [])
        if s.get("scene_id")
    ]


def _narration_hashes(scene_def: dict) -> dict:
    """scene_id -> narration + 読み指定 (VOICEVOX/Cloud 両方) のハッシュ。"""
    out = {}
    for sec in scene_def.get("sections", []):
        for sc in sec.get("scenes", []):
            sid = sc.get("scene_id")
            if not sid:
                continue
            payload = json.dumps(
                [
                    sc.get("narration", []),
                    sc.get("narration_speech", []),
                    sc.get("narration_speech_cloud", []),
                ],
                ensure_ascii=False,
                sort_keys=True,
            )
            out[sid] = _sha16(payload)
    return out


def _owner_scene(key: str, scene_ids: list[str]) -> str | None:
    """audio キャッシュのキー (`intro_01_003`) を所属 scene_id へ寄せる。

    scene_id 自体が末尾に連番を持つ (`intro_01`) ので単純な rsplit は危うい。
    既知の scene_id のうち最長一致を採る。
    """
    best = None
    for sid in scene_ids:
        if key == sid or key.startswith(sid + "_"):
            if best is None or len(sid) > len(best):
                best = sid
    return best


def _audio_hashes(audio_cache: dict, scene_ids: list[str]) -> dict:
    """scene_id -> その scene の全文 (text ハッシュ + wav 指紋) のハッシュ。"""
    per_scene: dict[str, list] = {}
    for key in sorted(audio_cache):
        sid = _owner_scene(key, scene_ids)
        if not sid:
            continue
        entry = audio_cache[key]
        if isinstance(entry, dict):
            per_scene.setdefault(sid, []).append((key, entry.get("text"), entry.get("wav")))
        else:
            per_scene.setdefault(sid, []).append((key, entry, None))
    return {
        sid: _sha16(json.dumps(rows, ensure_ascii=False, sort_keys=True))
        for sid, rows in per_scene.items()
    }


_SRT_TIME = re.compile(
    r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)",
)


def _parse_srt(path: str) -> list[tuple[float, float, str]]:
    """subtitles.srt を (start, end, text) に。時刻は timing.json と同じ基準。"""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return []
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = _SRT_TIME.search(block)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text_lines = [ln for ln in lines if not _SRT_TIME.search(ln) and not ln.strip().isdigit()]
        cues.append((start, end, "\n".join(text_lines)))
    return cues


def _subtitle_hashes(srt_path: str, timing: dict) -> dict:
    """scene_id -> その scene に載る字幕 (テキスト + シーン相対時刻) のハッシュ。

    絶対時刻ではなく **シーン相対**で持つ。上流の尺が動いて scene が後ろへずれても、
    そのシーンの字幕自体が変わっていなければ同一と判定したいため。
    """
    cues = _parse_srt(srt_path)
    if not cues:
        return {}
    scenes = timing.get("scenes", {})
    per_scene: dict[str, list] = {}
    for start, end, text in cues:
        for sid, sc in scenes.items():
            gs = float(sc.get("global_start", 0.0))
            ge = float(sc.get("global_end", gs))
            if gs - 0.001 <= start < ge + 0.001:
                per_scene.setdefault(sid, []).append(
                    (round(start - gs, 3), round(end - gs, 3), text)
                )
                break
    return {sid: _sha16(json.dumps(rows, ensure_ascii=False)) for sid, rows in per_scene.items()}


def collect_state(episode_dir: str | Path) -> dict:
    """フレーム以外のシーン状態をまとめて取る (差分判定の材料)。"""
    ep = Path(episode_dir)
    scene_def = _load_json(ep / "scene_definition.json", {})
    timing = _load_json(ep / "timing.json", {})
    visual_cache = _load_json(ep / "visuals" / "_visual_cache.json", {})
    audio_cache = _load_json(ep / "audio" / "_audio_cache.json", {})
    config = _load_json(ep / "episode_config.json", {})

    sids = _scene_ids(scene_def)
    narration = _narration_hashes(scene_def)
    audio = _audio_hashes(audio_cache, sids)
    subs = _subtitle_hashes(str(ep / "subtitles.srt"), timing)

    scenes = {}
    for sid in sids:
        tsc = timing.get("scenes", {}).get(sid, {})
        vc = visual_cache.get(sid) or {}
        scenes[sid] = {
            "narration": narration.get(sid),
            "audio": audio.get(sid),
            "subtitles": subs.get(sid),
            "visual_key": vc.get("key") if isinstance(vc, dict) else vc,
            "visual_mp4": vc.get("mp4") if isinstance(vc, dict) else None,
            "duration": round(float(tsc.get("duration", 0.0)), 3),
            "global_start": round(float(tsc.get("global_start", 0.0)), 3),
        }
    final = ep / "output_final.mp4"
    return {
        "episode_id": ep.name,
        "intro_pause": float((config.get("bgm") or {}).get("intro_pause", 1.0)),
        "video_fingerprint": _file_fingerprint(final) if final.exists() else "",
        "scene_order": sids,
        "scenes": scenes,
    }


def snapshot(
    episode_dir: str | Path,
    frames_per_scene: int = DEFAULT_FRAMES_PER_SCENE,
    video: str | None = None,
    verbose: bool = True,
) -> dict:
    """ビルド前の baseline を作って `_review_baseline.json` に書く。

    フレームハッシュは **現行の output_final.mp4** から採る。ビルドは動画を
    上書きするので、ここで採っておかないと「未変更区間が同一である」ことは
    あとから証明できない。
    """
    ep = Path(episode_dir)
    state = collect_state(ep)
    vid = video or str(ep / "output_final.mp4")
    intro = state["intro_pause"]
    frames_taken = 0
    if os.path.exists(vid) and frames_per_scene > 0:
        for sc in state["scenes"].values():
            offsets = _sample_offsets(sc["duration"], frames_per_scene)
            rows = []
            for rel in offsets:
                frame = _extract_gray_frame(vid, sc["global_start"] + intro + rel)
                if frame is None:
                    continue
                rows.append({"rel": rel, "sha": _sha16(frame), "dhash": _dhash(frame)})
                frames_taken += 1
            sc["frames"] = rows
    state["frames_source"] = os.path.basename(vid) if os.path.exists(vid) else ""
    out = ep / BASELINE_FILE
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError as e:
        if verbose:
            print(f"  [WARN] baseline を書けませんでした (続行): {e}")
        return state
    if verbose:
        print(
            f"  [review] baseline: {len(state['scenes'])} scene / {frames_taken} フレーム -> {out}"
        )
    return state


# ---------------------------------------------------------------------------
# 差分と証明
# ---------------------------------------------------------------------------

_FIELD_LABEL = {
    "narration": "narration",
    "audio": "音声",
    "subtitles": "字幕",
    "visual_key": "映像 (内容キー)",
    "visual_mp4": "映像 (再レンダ)",
    "duration": "尺",
}


def diff_state(base: dict, cur: dict) -> dict:
    """baseline と現状のシーン差分。変更理由は日本語ラベルで返す。"""
    b_scenes = base.get("scenes", {})
    c_scenes = cur.get("scenes", {})
    changed: dict[str, list[str]] = {}
    unchanged: list[str] = []
    for sid in cur.get("scene_order", []):
        c = c_scenes.get(sid, {})
        b = b_scenes.get(sid)
        if b is None:
            changed[sid] = ["新規シーン"]
            continue
        reasons = []
        for field, label in _FIELD_LABEL.items():
            bv, cv = b.get(field), c.get(field)
            # 両側とも無いなら比べる材料が無い (どちらの側にも変化の主張がない)。
            if bv is None and cv is None:
                continue
            # **片側だけ無いのは「変化なし」ではなく「比較できない」。**
            # 黙って skip すると、その経路の変化が丸ごと見えなくなる。実際に
            # 起きた: ある回は 2026-07-04 ビルドで visual キャッシュ より前だったため baseline の visual_key/visual_mp4 が None で、
            # **23 本の visual を 24 分かけて再 render したのに「変更シーンなし
            # (見るべきものなし)」と報告した**。2026-07-24 より前に作られた全 ep の
            # 初回再ビルドが同じ穴に落ちる。比較不能は変更側に倒す (見逃すより
            # 余計に見せるほうが安全)。
            if bv is None or cv is None:
                side = "baseline" if bv is None else "現在"
                reasons.append(f"{label} (比較不能: {side}に情報なし)")
                continue
            if bv != cv:
                reasons.append(label)
        if reasons:
            changed[sid] = reasons
        else:
            unchanged.append(sid)
    removed = [sid for sid in b_scenes if sid not in c_scenes]
    return {"changed": changed, "unchanged": unchanged, "removed": removed}


def prove_unchanged(
    episode_dir: str | Path,
    base: dict,
    cur: dict,
    unchanged: list[str],
    video: str | None = None,
    dhash_tol: int = DEFAULT_DHASH_TOL,
    verbose: bool = True,
) -> list[dict]:
    """未変更シーンが実際に同一であることをフレーム/timing/字幕で確かめる。"""
    ep = Path(episode_dir)
    vid = video or str(ep / "output_final.mp4")
    intro = float(cur.get("intro_pause", 1.0))
    rows = []
    for sid in unchanged:
        b = base["scenes"].get(sid, {})
        c = cur["scenes"].get(sid, {})
        row = {
            "scene_id": sid,
            "shift": round(c.get("global_start", 0.0) - b.get("global_start", 0.0), 3),
            "subtitles_same": b.get("subtitles") == c.get("subtitles"),
            "exact": 0,
            "near": 0,
            "differ": 0,
            "no_baseline_frames": not b.get("frames"),
            "worst": 0,
        }
        if os.path.exists(vid):
            for fr in b.get("frames") or []:
                frame = _extract_gray_frame(vid, c.get("global_start", 0.0) + intro + fr["rel"])
                if frame is None:
                    row["differ"] += 1
                    continue
                if _sha16(frame) == fr["sha"]:
                    row["exact"] += 1
                    continue
                d = _hamming(_dhash(frame), fr["dhash"])
                row["worst"] = max(row["worst"], d)
                if d <= dhash_tol:
                    row["near"] += 1
                else:
                    row["differ"] += 1
        rows.append(row)
        if verbose and (row["differ"] or not row["subtitles_same"]):
            print(
                f"  [!] {sid}: 未変更のはずが差異あり "
                f"(フレーム差 {row['differ']} / dHash 最大 {row['worst']} / "
                f"字幕 {'同一' if row['subtitles_same'] else '相違'})"
            )
    return rows


# ---------------------------------------------------------------------------
# リール生成
# ---------------------------------------------------------------------------


def plan_windows(
    changed: dict, cur: dict, pad: float = DEFAULT_PAD, video_duration: float | None = None
) -> list[dict]:
    """変更シーンを ±pad 秒の文脈付き窓にし、重なるものは 1 本にまとめる。"""
    intro = float(cur.get("intro_pause", 1.0))
    raw = []
    for sid in cur.get("scene_order", []):
        if sid not in changed:
            continue
        sc = cur["scenes"][sid]
        start = sc["global_start"] + intro - pad
        end = sc["global_start"] + intro + sc["duration"] + pad
        raw.append({"start": max(0.0, start), "end": end, "scenes": [sid]})
    merged: list[dict] = []
    for w in raw:
        if merged and w["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], w["end"])
            merged[-1]["scenes"].extend(w["scenes"])
        else:
            merged.append(dict(w))
    if video_duration:
        for w in merged:
            w["end"] = min(w["end"], video_duration)
    for w in merged:
        w["duration"] = round(w["end"] - w["start"], 3)
    return merged


def _label_filter(episode_dir: Path, text: str) -> str | None:
    """セグメント左上に貼る ASCII ラベルの drawtext。フォントが無ければ None。

    ラベルは ASCII だけにしてある (scene_id と理由コード)。日本語を焼くと
    drawtext のエスケープ事故 の面積が広がるため、
    日本語の理由は report 側に書く。
    """
    if not (episode_dir / "_font.ttc").exists():
        return None
    # '/' や ':' は drawtext のエスケープ対象なので、落とすのではなく最初から
    # 使わない (落とすと "1/2" が "12" に化けて別の意味になる)。
    safe = re.sub(r"[^A-Za-z0-9 _,+\-]", "", text)[:60]
    return (
        "drawtext=fontfile=_font.ttc"
        f":text='{safe}'"
        ":fontsize=34:fontcolor=white:borderw=3:bordercolor=black"
        ":box=1:boxcolor=black@0.45:boxborderw=10"
        ":x=40:y=40"
    )


def build_reel(
    episode_dir: str | Path,
    windows: list[dict],
    video: str | None = None,
    out_path: str | None = None,
    label: bool = True,
    verbose: bool = True,
) -> str | None:
    """窓を切り出して 1 本の mp4 に繋ぐ。作れなければ None。"""
    ep = Path(episode_dir)
    vid = video or str(ep / "output_final.mp4")
    out = out_path or str(ep / REEL_FILE)
    if not windows or not os.path.exists(vid):
        return None
    tmpdir = tempfile.mkdtemp(prefix="review_reel_")
    parts = []
    try:
        for i, w in enumerate(windows):
            seg = os.path.join(tmpdir, f"seg{i:02d}.mp4")
            vf = []
            if label:
                lf = _label_filter(ep, f"{i + 1} of {len(windows)} - " + ", ".join(w["scenes"]))
                if lf:
                    vf.append(lf)
            cmd = [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-ss",
                f"{w['start']:.3f}",
                "-t",
                f"{w['duration']:.3f}",
                "-i",
                vid,
            ]
            if vf:
                cmd += ["-vf", ",".join(vf)]
            cmd += [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                seg,
            ]
            # cwd=ep so drawtext's relative fontfile=_font.ttc resolves without
            # Windows path escaping (same trick video_assembler uses).
            proc = subprocess.run(cmd, capture_output=True, cwd=str(ep), timeout=1800)
            if not os.path.exists(seg) or os.path.getsize(seg) == 0:
                if verbose:
                    err = proc.stderr.decode("utf-8", "replace")[-400:]
                    print(f"  [WARN] セグメント {i} の切り出しに失敗: {err}")
                continue
            parts.append(seg)
        if not parts:
            return None
        listfile = os.path.join(tmpdir, "concat.txt")
        with open(listfile, "w", encoding="utf-8") as f:
            for p in parts:
                f.write(f"file '{p.replace(os.sep, '/')}'\n")
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                listfile,
                "-c",
                "copy",
                out,
            ],
            capture_output=True,
            timeout=1800,
        )
        return out if os.path.exists(out) and os.path.getsize(out) > 0 else None
    except (OSError, subprocess.SubprocessError) as e:
        if verbose:
            print(f"  [WARN] リール生成に失敗 (続行): {e}")
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# レポート
# ---------------------------------------------------------------------------


def format_report(
    episode_id: str,
    result: dict,
) -> str:
    """人が読むレポート本文。何が・なぜ変わり、残りが同一である根拠を書く。"""
    lines = [
        "=" * 60,
        f"  レビューリール / 未変更区間の同一性 -- {episode_id}",
        "=" * 60,
        "",
    ]
    changed = result["changed"]
    unchanged_rows = result["proof"]
    if not changed:
        lines.append("変更されたシーンはありません (見るべきものなし)。")
    else:
        lines.append(f"■ 変更シーン {len(changed)} 件")
        for sid, reasons in changed.items():
            lines.append(f"  - {sid}: {' / '.join(reasons)}")
    lines.append("")
    if result.get("status") == "video_not_rebuilt":
        lines.append(
            "[!!] 上の変更は **output_final.mp4 に入っていません** "
            "(動画が baseline と 1 バイトも変わっていない = assemble / bgm 未実行)。"
        )
        lines.append(
            "     この状態でリールを作ると古い映像を「修正結果」として見せることになるため、"
            "作りません。"
        )
        lines.append("     `--steps` に assemble,bgm を含めて再ビルドしてください。")
        lines.append("")
    if result.get("reel"):
        lines.append(
            f"■ リール: {result['reel']}  ({result['reel_seconds']:.0f} 秒 / "
            f"{len(result['windows'])} 区間)"
        )
    elif result.get("reel_skip_reason"):
        lines.append(f"■ リール: 生成せず -- {result['reel_skip_reason']}")
    lines.append("")
    lines.append(f"■ 未変更シーン {len(unchanged_rows)} 件の同一性")
    if not unchanged_rows:
        lines.append("  (未変更シーンなし)")
    for row in unchanged_rows:
        bits = []
        if row["no_baseline_frames"]:
            bits.append("baseline フレームなし")
        else:
            bits.append(
                f"フレーム 完全一致 {row['exact']} / 誤差内 {row['near']} / 差異 {row['differ']}"
            )
        bits.append("字幕 同一" if row["subtitles_same"] else "字幕 相違")
        if abs(row["shift"]) >= 0.001:
            bits.append(f"位置 {row['shift']:+.3f} 秒シフト")
        else:
            bits.append("位置 不変")
        mark = "!" if (row["differ"] or not row["subtitles_same"]) else "OK"
        lines.append(f"  [{mark}] {row['scene_id']}: {' / '.join(bits)}")
    lines.append("")
    suspects = [r for r in unchanged_rows if r["differ"] or not r["subtitles_same"]]
    if suspects:
        lines.append(
            f"[!] 未変更のはずのシーン {len(suspects)} 件に差異があります。"
            "リールに入っていないので通し視聴でしか気付けない類の変化です -- "
            "先にここを調べてください。"
        )
    shifted = [r for r in unchanged_rows if abs(r["shift"]) >= 0.001]
    if shifted:
        lines.append(
            f"[i] 未変更シーン {len(shifted)} 件が時間軸上で移動しています "
            "(上流の尺が変わったため)。中身は上記のとおり同一です。"
        )
    return "\n".join(lines)


def run(
    episode_dir: str | Path,
    pad: float = DEFAULT_PAD,
    max_reel_sec: float = DEFAULT_MAX_REEL_SEC,
    dhash_tol: int = DEFAULT_DHASH_TOL,
    video: str | None = None,
    copy_to_temp_videos: bool = True,
    verbose: bool = True,
) -> dict:
    """ビルド後の本体処理。差分 -> リール -> 証明 -> レポート。"""
    ep = Path(episode_dir).resolve()
    vid = video or str(ep / "output_final.mp4")
    baseline_path = ep / BASELINE_FILE
    result: dict = {
        "episode_id": ep.name,
        "changed": {},
        "windows": [],
        "proof": [],
        "reel": None,
        "reel_seconds": 0.0,
        "reel_skip_reason": None,
        "status": "ok",
    }
    if not baseline_path.exists():
        result["status"] = "no_baseline"
        result["reel_skip_reason"] = (
            "baseline がありません (このビルドは比較対象を持たない = 初回ビルド)"
        )
        if verbose:
            print(f"  [SKIP] {BASELINE_FILE} なし -- 比較対象がないためリールを作りません。")
        return result
    base = _load_json(baseline_path, {})
    cur = collect_state(ep)
    d = diff_state(base, cur)
    result["changed"] = d["changed"]
    result["removed"] = d["removed"]

    if not os.path.exists(vid):
        result["status"] = "no_video"
        result["reel_skip_reason"] = "output_final.mp4 がありません"
        if verbose:
            print("  [SKIP] output_final.mp4 がないためリールを作りません。")
        return result

    # 変更があると言いながら**動画が baseline のときと 1 バイトも変わっていない** =
    # 直したものが出荷物に届いていない (assemble / bgm を回していない)。
    # ここでリールを作ると、古い映像を切り出して「これが修正結果です」と差し出すことに
    # なる
    # が防ぐはずの事故そのもの。**作らずに、何を回せばよいかを言う。**
    result["video_rebuilt"] = True
    base_fp = base.get("video_fingerprint") or ""
    if d["changed"] and base_fp and base_fp == _file_fingerprint(vid):
        result["status"] = "video_not_rebuilt"
        result["video_rebuilt"] = False
        result["reel_skip_reason"] = (
            f"{len(d['changed'])} scene が変更されていますが、output_final.mp4 は "
            "baseline と同一のままです (assemble / bgm を回していないので、直したものが "
            "動画に入っていません)。--steps に assemble,bgm を含めて再ビルドしてください"
        )
        if verbose:
            print(f"  [!] {result['reel_skip_reason']}")
        result["proof"] = []
        report = format_report(ep.name, result)
        try:
            with open(ep / REPORT_FILE, "w", encoding="utf-8") as f:
                f.write(report + "\n")
            result["report"] = str(ep / REPORT_FILE)
        except OSError:
            pass
        if verbose:
            print(report)
        result["suspects"] = []
        return result

    total = len(cur.get("scene_order", []))
    if d["changed"]:
        vdur = _probe_duration(vid)
        windows = plan_windows(d["changed"], cur, pad=pad, video_duration=vdur)
        reel_sec = sum(w["duration"] for w in windows)
        result["windows"] = windows
        result["reel_seconds"] = reel_sec
        if len(d["changed"]) >= total:
            result["reel_skip_reason"] = (
                f"全 {total} scene が変更されています -- リールは通し視聴と同じです"
            )
        elif reel_sec > max_reel_sec:
            result["reel_skip_reason"] = (
                f"変更が広く、リールが {reel_sec / 60:.1f} 分になります "
                f"(上限 {max_reel_sec / 60:.1f} 分) -- 通しで見るほうが速いです"
            )
        else:
            result["reel"] = build_reel(ep, windows, video=vid, verbose=verbose)
    else:
        result["reel_skip_reason"] = "変更シーンなし (見るべきものなし)"

    result["proof"] = prove_unchanged(
        ep, base, cur, d["unchanged"], video=vid, dhash_tol=dhash_tol, verbose=verbose
    )

    report = format_report(ep.name, result)
    try:
        with open(ep / REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        result["report"] = str(ep / REPORT_FILE)
    except OSError as e:
        if verbose:
            print(f"  [WARN] レポートを書けませんでした: {e}")

    if result["reel"] and copy_to_temp_videos:
        try:
            tv = ep.parent.parent / "temp_videos"
            if tv.is_dir():
                dst = tv / f"{ep.name}_review_reel.mp4"
                shutil.copy2(result["reel"], dst)
                result["reel_copy"] = str(dst)
        except OSError as e:
            if verbose:
                print(f"  [WARN] temp_videos へのコピーに失敗: {e}")

    if verbose:
        print(report)
        if result.get("reel_copy"):
            print(f"\n  [review] リールを temp_videos へコピーしました: {result['reel_copy']}")
    result["suspects"] = [r for r in result["proof"] if r["differ"] or not r["subtitles_same"]]
    return result


def main() -> int:
    p = argparse.ArgumentParser(
        description="変更シーンだけのレビューリールと、未変更区間の同一性証明"
    )
    p.add_argument("episode_dir")
    p.add_argument(
        "--snapshot",
        action="store_true",
        help="ビルド前の baseline を作る (現状のキャッシュ/timing/字幕 + 現行動画のフレーム)",
    )
    p.add_argument("--video", default=None, help="既定: <ep>/output_final.mp4")
    p.add_argument("--pad", type=float, default=DEFAULT_PAD, help="変更シーン前後の文脈秒数")
    p.add_argument("--frames", type=int, default=DEFAULT_FRAMES_PER_SCENE)
    p.add_argument("--max-reel-sec", type=float, default=DEFAULT_MAX_REEL_SEC)
    p.add_argument("--dhash-tol", type=int, default=DEFAULT_DHASH_TOL)
    p.add_argument("--no-temp-video-copy", action="store_true")
    p.add_argument(
        "--strict",
        action="store_true",
        help="未変更のはずのシーンに差異があれば exit 1",
    )
    args = p.parse_args()

    ep = Path(args.episode_dir)
    if not ep.is_dir():
        print(f"ERROR: episode dir not found: {ep}")
        return 2
    if args.snapshot:
        snapshot(ep, frames_per_scene=args.frames, video=args.video)
        return 0
    res = run(
        ep,
        pad=args.pad,
        max_reel_sec=args.max_reel_sec,
        dhash_tol=args.dhash_tol,
        video=args.video,
        copy_to_temp_videos=not args.no_temp_video_copy,
    )
    if args.strict and res.get("suspects"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
