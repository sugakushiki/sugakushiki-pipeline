#!/usr/bin/env python
"""動画末尾に N 秒の endcard 区間（最後のフレーム静止 + BGM のみ）を追加する単発スクリプト。

使い方:
  python scripts/add_endcard_bgm.py examples/moriarty/output_final.mp4 \
      --bgm bgm/angels_dream.mp3 --output examples/moriarty/output_with_endcard.mp4

このスクリプトは scene_definition.json / description.txt / wikimedia_credits.json などの
副作用ファイルは一切触らない。動画ファイルのみを生成する。
"""

import argparse
import os
import subprocess
import sys


def get_duration(path: str) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        encoding="utf-8",
    ).strip()
    return float(out)


def main() -> int:
    p = argparse.ArgumentParser(description="動画末尾に endcard 区間 (最終フレーム + BGM) を追加")
    p.add_argument("video", help="入力動画 (output_final.mp4)")
    p.add_argument("--bgm", required=True, help="BGM ファイル (mp3)")
    p.add_argument("--output", required=True, help="出力ファイル")
    p.add_argument("--duration", type=float, default=10.0, help="endcard 秒数 (default: 10)")
    p.add_argument("--volume-db", type=float, default=-20.0, help="BGM 音量 dB (default: -20)")
    p.add_argument("--fade-in", type=float, default=1.0, help="BGM fade-in 秒数 (default: 1.0)")
    p.add_argument("--fade-out", type=float, default=2.0, help="BGM fade-out 秒数 (default: 2.0)")
    p.add_argument("--bgm-start", type=float, default=30.0, help="BGM 内の開始秒 (default: 30.0)")
    p.add_argument("--preset", default="fast", help="x264 preset (default: fast)")
    p.add_argument("--crf", type=int, default=18, help="x264 CRF (default: 18)")
    p.add_argument("--dry-run", action="store_true", help="ffmpeg コマンドのみ表示")
    args = p.parse_args()

    for f in (args.video, args.bgm):
        if not os.path.exists(f):
            print(f"[ERROR] not found: {f}", file=sys.stderr)
            return 2

    video_dur = get_duration(args.video)
    bgm_dur = get_duration(args.bgm)
    print(f"[INFO] input video: {args.video} ({video_dur:.2f}s)")
    print(f"[INFO] bgm: {args.bgm} ({bgm_dur:.2f}s)")
    print(f"[INFO] endcard duration: {args.duration:.1f}s")
    print(f"[INFO] bgm seek: {args.bgm_start:.1f}s, volume: {args.volume_db}dB")
    print(f"[INFO] output: {args.output}")

    fade_out_start = args.duration - args.fade_out

    filter_complex = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={args.duration}[v];"
        f"[1:a]asetpts=PTS-STARTPTS,volume={args.volume_db}dB,"
        f"afade=t=in:st=0:d={args.fade_in},"
        f"afade=t=out:st={fade_out_start}:d={args.fade_out}[bgm10];"
        f"[0:a][bgm10]concat=n=2:v=0:a=1[a]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        args.video,
        "-ss",
        str(args.bgm_start),
        "-t",
        str(args.duration),
        "-i",
        args.bgm,
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-c:a",
        "aac",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-b:a",
        "100k",
        "-movflags",
        "+faststart",
        args.output,
    ]

    print("[INFO] ffmpeg command:")
    print("  " + " ".join(cmd))

    if args.dry_run:
        return 0

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[ERROR] ffmpeg failed (code {result.returncode})", file=sys.stderr)
        return result.returncode

    out_dur = get_duration(args.output)
    expected = video_dur + args.duration
    delta = out_dur - expected
    print(f"[OK] output duration: {out_dur:.2f}s (expected ~{expected:.2f}s, delta {delta:+.2f}s)")
    if abs(delta) > 0.5:
        print("[WARN] duration delta exceeds 0.5s, check output", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
