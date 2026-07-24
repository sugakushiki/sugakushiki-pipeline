r"""
BGM Mixer - Episode動画にBGMを合成する
冒頭ポーズ（無音＋映像静止）+ BGMミックス + 末尾余韻（フェードアウト）

使い方:
  python src/bgm_mixer.py examples/moriarty/output.mp4 bgm/angels_dream.mp3

  # オプション指定
  python src/bgm_mixer.py examples/moriarty/output.mp4 bgm/angels_dream.mp3 ^
    --intro-pause 1.0 --outro-fade 3.0 --bgm-volume -20 --outro-hold 10.0

  # 出力先を指定
  python src/bgm_mixer.py examples/moriarty/output.mp4 bgm/angels_dream.mp3 ^
    -o examples/moriarty/output_final.mp4
"""

import argparse
import json
import os
import subprocess
import sys


def get_duration(filepath):
    """FFprobeで動画/音声の長さを取得（秒）"""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"Error: ffprobe failed for {filepath}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def probe_mp4(filepath):
    """ffprobe で mp4 の duration を取得。読めない (moov atom 欠落等) なら None。

    get_duration と違い sys.exit せず None を返すので、破損検出 に使う。
    """
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def get_video_props(filepath):
    """ffprobe で動画の (幅, 高さ, fps) を取得（endcard 合成用）。"""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-select_streams",
        "v:0",
        "-show_streams",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    data = json.loads(result.stdout)
    s = data["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    num, _, den = s.get("r_frame_rate", "30/1").partition("/")
    fps = (float(num) / float(den)) if den and float(den) else 30.0
    return w, h, fps


def main():
    parser = argparse.ArgumentParser(
        description="数学史記 BGMミキサー — 動画にBGM＋冒頭ポーズ＋末尾余韻を追加"
    )
    parser.add_argument("video", help="入力動画ファイル（output.mp4）")
    parser.add_argument("bgm", help="BGMファイル（MP3/WAV）")
    parser.add_argument("-o", "--output", help="出力ファイル名（デフォルト: *_final.mp4）")
    parser.add_argument(
        "--intro-pause", type=float, default=1.0, help="冒頭の無音ポーズ（秒）。デフォルト: 1.0"
    )
    parser.add_argument(
        "--outro-hold",
        type=float,
        default=10.0,
        help="末尾の余韻（映像の最終フレームを静止させる秒数）。デフォルト: 10.0（YouTube endcard 用）",
    )
    parser.add_argument(
        "--outro-fade",
        type=float,
        default=3.0,
        help="BGMフェードアウトの長さ（秒）。デフォルト: 3.0",
    )
    parser.add_argument(
        "--bgm-volume", type=float, default=-20, help="BGM音量（dB）。デフォルト: -20"
    )
    parser.add_argument(
        "--bgm-fadein", type=float, default=2.0, help="BGMフェードインの長さ（秒）。デフォルト: 2.0"
    )
    parser.add_argument(
        "--endcard-image",
        default=None,
        help="末尾余韻に最終フレーム静止の代わりに表示する画像（風景画等）。"
        "指定時は outro_hold 秒この画像を表示する（YouTube endcard 用）。",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="FFmpegコマンドを表示するだけで実行しない"
    )
    args = parser.parse_args()

    # ファイル存在チェック
    _check = [args.video, args.bgm]
    if args.endcard_image:
        _check.append(args.endcard_image)
    for f in _check:
        if not os.path.exists(f):
            print(f"Error: ファイルが見つかりません: {f}", file=sys.stderr)
            sys.exit(1)

    # 出力ファイル名
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.video)
        output_path = f"{base}_final{ext}"

    # 動画とBGMの長さを取得
    video_duration = get_duration(args.video)
    bgm_duration = get_duration(args.bgm)

    # 最終的な動画の長さ
    total_duration = args.intro_pause + video_duration + args.outro_hold

    print(f"入力動画: {args.video} ({video_duration:.1f}秒)")
    print(f"BGM: {args.bgm} ({bgm_duration:.1f}秒)")
    print(f"冒頭ポーズ: {args.intro_pause}秒")
    print(f"末尾余韻: {args.outro_hold}秒")
    print(f"合計: {total_duration:.1f}秒")
    print(f"BGM音量: {args.bgm_volume}dB")
    print(f"出力: {output_path}")
    print()

    # BGMフェードアウト開始位置（末尾から）
    bgm_fadeout_start = total_duration - args.outro_fade

    # FFmpegフィルタグラフ構築
    #
    # 映像:
    #   1. 冒頭ポーズ: 入力動画の最初のフレームを intro_pause 秒間表示
    #   2. 本編映像
    #   3. 末尾余韻: 最後のフレームを outro_hold 秒間表示
    #
    # 音声:
    #   1. 冒頭ポーズ: 無音
    #   2. 本編音声（ナレーション）
    #   3. 末尾余韻: 無音
    #   + BGM: ループ → 音量調整 → フェードイン/アウト → ミックス

    # --- 映像フィルタ ---
    # tpad: 冒頭に start 秒の静止フレーム、末尾に stop 秒の静止フレームを追加
    video_filter = f"tpad=start_duration={args.intro_pause}:start_mode=clone:stop_duration={args.outro_hold}:stop_mode=clone"

    # --- 音声フィルタ ---
    # [0:a] 本編音声に冒頭/末尾の無音を追加
    narration_filter = f"[0:a]adelay={int(args.intro_pause * 1000)}|{int(args.intro_pause * 1000)},apad=whole_dur={total_duration}[narr]"

    # [1:a] BGMをループ → 音量調整 → フェードイン/アウト → 長さカット
    bgm_filter = (
        f"[1:a]aloop=loop=-1:size={int(bgm_duration * 48000)}:start=0,"
        f"atrim=0:{total_duration},"
        f"volume={args.bgm_volume}dB,"
        f"afade=t=in:st=0:d={args.bgm_fadein},"
        f"afade=t=out:st={bgm_fadeout_start}:d={args.outro_fade}"
        f"[bgm]"
    )

    # ナレーションとBGMをミックス
    mix_filter = "[narr][bgm]amix=inputs=2:duration=longest:normalize=0[aout]"

    # フィルタグラフ全体（映像合成を endcard 有無で分岐）
    # endcard 画像あり: 本編(冒頭ポーズ付き) + 画像クリップ(outro_hold秒) を concat。
    #                   末尾は最終フレーム静止ではなく風景画になる。
    # endcard なし    : 従来どおり tpad の stop_mode=clone で最終フレームを静止。
    if args.endcard_image:
        vw, vh, vfps = get_video_props(args.video)
        v_main = (
            f"[0:v]tpad=start_duration={args.intro_pause}:start_mode=clone,"
            f"fps={vfps},format=yuv420p,setsar=1[vmain]"
        )
        v_end = (
            f"[2:v]scale={vw}:{vh}:force_original_aspect_ratio=decrease,"
            f"pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2,fps={vfps},format=yuv420p,setsar=1[vend]"
        )
        v_concat = "[vmain][vend]concat=n=2:v=1:a=0[vout]"
        filter_complex = f"{v_main};{v_end};{v_concat};{narration_filter};{bgm_filter};{mix_filter}"
    else:
        filter_complex = f"{narration_filter};{bgm_filter};{mix_filter}"

    # 一旦 *.part に書き、健全性検証後に output_path へ atomic rename する。
    # ffmpeg が途中で kill されても部分書き込みは .part に閉じ込められ、
    # 既存の output_final.mp4 (前回ビルド) は壊さない。
    write_target = output_path + ".part"

    # FFmpegコマンド
    cmd = ["ffmpeg", "-y", "-i", args.video, "-i", args.bgm]
    if args.endcard_image:
        # 末尾余韻ぶんの長さで画像をループ入力 (input #2)
        cmd += ["-loop", "1", "-t", str(args.outro_hold), "-i", args.endcard_image]
    cmd += ["-filter_complex", filter_complex]
    if not args.endcard_image:
        # endcard なしのときのみ tpad の -vf を使う (画像ありは concat 済み[vout])
        cmd += ["-vf", video_filter]
    cmd += [
        "-map",
        "[vout]" if args.endcard_image else "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        # write_target has a ".part" suffix, so ffmpeg cannot infer the
        # container from the extension. Force mp4 explicitly (newer ffmpeg
        # builds error out instead of guessing).
        "-f",
        "mp4",
        write_target,
    ]

    if args.dry_run:
        print("FFmpegコマンド:")
        # 表示用に整形
        cmd_str = cmd[0]
        i = 1
        while i < len(cmd):
            if cmd[i].startswith("-"):
                cmd_str += f" \\\n  {cmd[i]}"
                if i + 1 < len(cmd) and not cmd[i + 1].startswith("-"):
                    cmd_str += f' "{cmd[i + 1]}"'
                    i += 1
            else:
                cmd_str += f' "{cmd[i]}"'
            i += 1
        print(cmd_str)
        return

    print("BGMミックス中...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        print("\nError: FFmpegが失敗しました", file=sys.stderr)
        print(
            result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr, file=sys.stderr
        )
        # 中断で残った部分書き込みを掃除 (output_final は触らない)
        if os.path.exists(write_target):
            os.remove(write_target)
        sys.exit(1)

    # --- 出力の健全性検証 + atomic rename --------------------------
    # ffmpeg が途中で kill されると moov atom 欠落の壊れた mp4 が残り、
    # 「ファイルが存在 = 完成」という pipeline の前提を破る。
    # ffprobe で moov/duration を確認できたものだけを output へ rename する。
    if not os.path.exists(write_target):
        print("\nError: 出力ファイルが生成されませんでした", file=sys.stderr)
        sys.exit(1)

    output_duration = probe_mp4(write_target)
    if output_duration is None or output_duration <= 0:
        print(
            "\nError: 出力 mp4 の健全性検証に失敗 (moov atom 欠落 / duration 取得不可)。"
            "\n       壊れたファイルを破棄します。output_final は更新されません。",
            file=sys.stderr,
        )
        os.remove(write_target)
        sys.exit(1)

    # duration が想定から大きく乖離していれば WARN (構造は健全なので採用は続行)
    if abs(output_duration - total_duration) > 3.0:
        print(
            f"\n[WARN] 出力 duration {output_duration:.1f}秒 が想定 {total_duration:.1f}秒 と乖離 "
            "(>3秒)。フィルタ設定か入力長を確認してください。",
            file=sys.stderr,
        )

    # 健全性 OK -> atomic rename (同一ディレクトリなので os.replace は atomic)
    os.replace(write_target, output_path)

    output_size = os.path.getsize(output_path) / (1024 * 1024)
    print("\n完了!")
    print(f"  出力: {output_path}")
    print(f"  サイズ: {output_size:.1f}MB")
    print(f"  長さ: {output_duration:.1f}秒 ({output_duration / 60:.1f}分)")
    print(f"  冒頭ポーズ: {args.intro_pause}秒")
    print(f"  本編: {video_duration:.1f}秒")
    print(f"  末尾余韻: {args.outro_hold}秒")


if __name__ == "__main__":
    main()
