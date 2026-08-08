"""Locate sentence boundaries inside one synthesized narration element.

Why this exists
---------------
A narration element (one entry of `scene["narration"]`) often holds two or three
sentences, and timing.json only records the element's start and end. Everything
inside was therefore estimated: subtitle cues were spread across the element by a
mora estimate, and the cloud speed check averaged the whole element into a single
articulation figure.

Both are wrong in the same way. Measured against 14 boundaries confirmed by
transcribing the audio either side of them, the estimate was off by 0.60 s on
average and 1.21 s at worst -- enough for a subtitle to change while the
previous sentence is still being spoken.

This module measures where the sentences actually end, so callers can anchor on
that instead of guessing.

How, and why not more simply
----------------------------
The obvious version - take the longest internal silences - does not work. Tried
on an earlier episode it produced 22 and 50 mora/s, physically impossible for speech, because
pauses for commas and breaths outnumber the sentence ends. Instead each boundary
is PREDICTED from the mora estimate and a silence is accepted only if it sits
within `TOL` of that prediction, scanning left to right so the boundaries cannot
come out of order (choosing each independently transposed 13 of 60 elements).

The prediction is made in SPEECH time, not wall-clock time, and that distinction
is the whole difference between this working and not working. See
`_predict_boundaries`.

The result is then sanity-checked: if any sentence would have to be spoken faster
or slower than a human can, the whole element is rejected and the caller keeps
its previous estimate. **Rejection is normal and must stay cheap** - a wrong
boundary is worse than no boundary, because it silently mistimes subtitles.

Callers should report coverage (how many elements resolved), not just results:
"0 problems" from a checker that could only see two thirds of the episode is the
failure mode this module was written to end.
"""

from __future__ import annotations

import os
import re
import subprocess

# ffmpeg silencedetect parameters. Kept identical to scripts/cloud_speed_qa.py so
# both tools segment the same audio the same way.
SIL_NOISE = "-35dB"
SIL_MIN = "0.18"

TOL = 1.1  # s: how far a real pause may sit from the predicted split
MIN_SIL = 0.20  # s: shorter gaps are breaths and commas, not sentence ends
EDGE = 0.20  # s: ignore silence at the very start/end of the element
RATE_LO, RATE_HI = 3.5, 12.0  # mora/s; outside this the segmentation is wrong

_SENT_END = re.compile(r"(?<=。)")


# Morae of the spoken digits and units. Not syllables: ひゃく is ひゃ+く = 2,
# きゅう is きゅ+う = 2, に and ご are 1.
_DIGIT_MORAE = {0: 2, 1: 2, 2: 1, 3: 2, 4: 2, 5: 1, 6: 2, 7: 2, 8: 2, 9: 2}
_SMALL_UNITS = ((1000, 2), (100, 2), (10, 2))  # せん ひゃく じゅう
_BIG_UNITS = ((10**16, 2), (10**12, 2), (10**8, 2), (10**4, 2))  # けい ちょう おく まん


def _morae_under_myriad(n: int) -> float:
    """Morae for 1..9999 spoken aloud. 一 is dropped before 十/百/千."""
    total = 0.0
    for value, unit in _SMALL_UNITS:
        d, n = divmod(n, value)
        if d:
            total += (0.0 if d == 1 else _DIGIT_MORAE[d]) + unit
    return total + (_DIGIT_MORAE[n] if n else 0.0)


def numeral_morae(digits: str) -> float:
    """Morae for a run of digits read as one Japanese number.

    Charging a flat rate per digit is wrong by about a factor of two either way:
    120 is ひゃくにじゅう (5 for three digits) while 39 is さんじゅうきゅう (6 for
    two) and 1947 is せんきゅうひゃくよんじゅうなな (12 for four). In a
    number-heavy sentence the error does not cancel, and on an earlier episode's math_04 it
    put the predicted sentence end 0.85 s late -- far enough that a pause inside
    the NEXT sentence won the boundary and the subtitle ran 1.1 s behind.
    """
    n = int(digits)
    if n == 0:
        return _DIGIT_MORAE[0]
    total = 0.0
    for value, unit in _BIG_UNITS:
        d, n = divmod(n, value)
        if d:
            total += _morae_under_myriad(d) + unit
    return total + (_morae_under_myriad(n) if n else 0.0)


def estimate_morae(text: str) -> float:
    """Rough spoken-mora count: kana=1, kanji~1.7, other=1, digits read as numbers."""
    text = re.sub(r"[。、!?.,\s]", "", text)
    total = 0.0
    for part in re.split(r"(\d+)", text):
        if not part:
            continue
        if part.isdigit():
            # Beyond 京 the reading is not a single number any more (phone numbers,
            # long IDs); fall back to the flat rate rather than invent a word.
            total += numeral_morae(part) if len(part) <= 20 else len(part) * 2
            continue
        for ch in part:
            o = ord(ch)
            if 0x30A0 <= o <= 0x30FF or 0x3040 <= o <= 0x309F:
                total += 1
            elif 0x4E00 <= o <= 0x9FFF:
                total += 1.7
            else:
                total += 1
    return total


def split_sentences(text: str) -> list[str]:
    """Split on the full stop, keeping it attached to the sentence it ends."""
    return [s for s in _SENT_END.split(text or "") if s.strip()]


def silence_spans(wav_path: str) -> tuple[float, list[tuple[float, float]]]:
    """(total_silence_seconds, [(start, end), ...]) from one silencedetect pass.

    ffmpeg writes its banner and any odd path bytes to stderr; decoding that with
    the Windows default codec raises UnicodeDecodeError inside subprocess's reader
    thread and the call silently returns nothing. Always decode explicitly.
    """
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-i",
                wav_path,
                "-af",
                f"silencedetect=noise={SIL_NOISE}:d={SIL_MIN}",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, ValueError):
        return 0.0, []
    err = r.stderr or ""
    total = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err))
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return total, list(zip(starts, ends, strict=False))


def audio_duration(wav_path: str) -> float | None:
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                wav_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout.strip()
        return float(out) if out else None
    except (OSError, ValueError):
        return None


def speech_time_edges(
    total: float, silence: list[tuple[float, float]], weights: list[float]
) -> list[float]:
    """Split `total` seconds by `weights`, measuring the shares in SPEECH time.

    Splitting a wall-clock span by weight assumes the silence inside it is spread
    in proportion to the words. It is not: it collects at the commas. A
    comma-heavy stretch therefore needs more wall time than its share of the
    words, and every cut after it lands early.

    On an earlier episode that displaced a sentence end by 1.2 s -- far enough that the real
    end fell outside `TOL`, a comma pause was accepted in its place, and the
    subtitle changed 1.8 s ahead of the voice. Against 14 boundaries confirmed by
    transcribing the audio either side of them, spending the shares against
    speech time and walking them back out through the measured silence took the
    mean error from 0.60 s to 0.08 s, 13 of the 14 landing exactly.

    The same correction applies within a sentence, where an earlier episode's median carries
    0.93 s of internal silence and 45% carry over a second.

    Returns `len(weights) - 1` internal cut points, in seconds from the start.
    """
    clipped = sorted((max(0.0, b), min(total, e)) for b, e in silence if e > 0 and b < total)
    speech = total - sum(e - b for b, e in clipped)
    cumulative, acc = [], 0.0
    for w in weights[:-1]:
        acc += w
        cumulative.append(acc)
    if sum(weights) <= 0:
        return [total * (i + 1) / len(weights) for i in range(len(weights) - 1)]
    if speech <= 0:  # all silence: nothing to place against, fall back to wall clock
        return [c / sum(weights) * total for c in cumulative]

    out = []
    for c in cumulative:
        want = c / sum(weights) * speech
        cursor = spoken = 0.0
        for b, e in clipped:
            if spoken + (b - cursor) >= want:
                break
            spoken += b - cursor
            cursor = e
        out.append(min(total, cursor + (want - spoken)))
    return out


def align(wav_path: str, text: str) -> dict:
    """Measure the sentence boundaries of one element.

    Returns a dict with:
      ok        - True when the boundaries are trustworthy
      reason    - why not, when ok is False (for coverage reporting)
      sentences - the split text
      bounds    - boundary times in seconds from the element's start
      spans     - [(start, end)] one per sentence
      rates     - mora/s per sentence (silence excluded)
      duration  - the element's length
      silence   - every measured silence, whether or not `ok`

    `duration` and `silence` are filled in whenever the wav can be read, so a
    caller that only wants to place cues inside a single-sentence element gets
    the measurement without a second pass over the audio.
    """
    sents = split_sentences(text)
    out = {
        "ok": False,
        "reason": "",
        "sentences": sents,
        "bounds": [],
        "spans": [],
        "rates": [],
        "duration": None,
        "silence": [],
    }
    single = len(sents) < 2
    if not wav_path or not os.path.exists(wav_path):
        out["reason"] = "single-sentence" if single else "no-audio"
        return out
    total = audio_duration(wav_path)
    if not total or total <= 0:
        out["reason"] = "single-sentence" if single else "no-duration"
        return out
    out["duration"] = total

    _sil_total, spans = silence_spans(wav_path)
    out["silence"] = spans
    if single:
        out["reason"] = "single-sentence"
        return out
    inner = [s for s in spans if s[0] > EDGE and s[1] < total - EDGE and (s[1] - s[0]) >= MIN_SIL]

    morae = [estimate_morae(s) for s in sents]
    if sum(morae) <= 0:
        out["reason"] = "no-morae"
        return out
    predicted = speech_time_edges(total, spans, morae)

    # Left to right, never stepping back: picking each boundary independently by
    # nearest-to-prediction transposed 13 of 60 elements on an earlier episode.
    bounds, last = [], 0.0
    for pred in predicted:
        cands = [
            s for s in inner if (s[0] + s[1]) / 2 > last and abs((s[0] + s[1]) / 2 - pred) <= TOL
        ]
        if not cands:
            out["reason"] = f"no-pause-near-{pred:.1f}s"
            return out
        best = min(cands, key=lambda s: abs((s[0] + s[1]) / 2 - pred))
        bounds.append((best[0] + best[1]) / 2)
        last = bounds[-1]

    edges = [0.0] + bounds + [total]
    rates = []
    for k, sent in enumerate(sents):
        seg = edges[k + 1] - edges[k]
        sil = sum(
            min(e, edges[k + 1]) - max(b, edges[k])
            for b, e in spans
            if e > edges[k] and b < edges[k + 1]
        )
        rates.append(estimate_morae(sent) / max(0.2, seg - sil))
    if any(r < RATE_LO or r > RATE_HI for r in rates):
        out["reason"] = f"implausible-rate-{min(rates):.1f}-{max(rates):.1f}"
        return out

    out.update(
        ok=True,
        reason="ok",
        bounds=bounds,
        spans=list(zip(edges[:-1], edges[1:], strict=False)),
        rates=rates,
    )
    return out
