"""Generate `narration_speech_cloud` for a cloud-TTS episode's scene_definition.json.

Why: script_generator does NOT emit narration_speech_cloud, so cloud episodes fall
back to narration_speech (VOICEVOX kana) at synthesis time -- which reads flat, and
(worse) the fallback wavs become a silent source of stale audio. This produces a
proper cloud reading up front, so the audio step never falls back.

Rule (calibrated from an earlier episode):
  - prose sentence  -> narration[i] with | markers removed (Cloud reads kanji well)
  - symbol sentence -> narration_speech[i] (the VOICEVOX spell-out already turns
    x^2=x etc. into エックスのにじょうはエックス; engine-neutral, correct for Cloud),
    spaces stripped
  - 『』 -> 、 (a short, non-exaggerated pause around quoted terms); ─ — ― ->、;
    doubled punctuation collapsed. cloud_tts.strip_for_cloud drops leftover markers.

NOT done here (deliberately): particle は->わ / へ->え. Reliable particle detection
needs a morphological analyzer; a naive replace corrupts word-internal は/へ. Cloud
Chirp3-HD reads particles natively; the rare misread is caught by stt_qa + the ear
and hand-fixed in narration_speech_cloud. See internal notes.

By default only scenes that LACK narration_speech_cloud are filled (existing,
hand-tuned readings are preserved). Pass --force to regenerate every scene.

Usage: python scripts/gen_cloud_readings.py episodes/XXX/scene_definition.json [--force]
"""

import argparse
import json
import re
import sys

# Latin letters + formula operators that Cloud cannot voice from raw text; such a
# sentence uses the VOICEVOX spell-out (narration_speech) instead of the display text.
_SYMBOL_RE = re.compile(r"[A-Za-z\^=²³×÷−√∝≠+*]")

# A は/へ that is comma-isolated -- preceded by 、 and followed by 、 。 or the string
# end -- is unambiguously the topic/direction particle: a word-internal は/へ (では,
# には, はじめて, へや, ...) is never a lone token flanked by punctuation. The 『』->、
# conversion in _cleanup creates exactly this isolation (『noun』は -> noun、は) and
# Cloud then mis-reads the lone particle as "ha"/"he" instead of "wa"/"e". So reattach it to the
# preceding word and spell the reading: drop the leading comma, は->わ / へ->え,
# keep any trailing punctuation. Safe without a morphological analyzer because the
# trigger is the lone-token signature, never a particle embedded in a word.
_ISOLATED_HA = re.compile(r"、は(?=[、。]|$)")
_ISOLATED_HE = re.compile(r"、へ(?=[、。]|$)")

# The myriad unit 京 (=けい, 10^16) DIRECTLY after a number, and NOT part of a place
# name, is unambiguously the numeric unit. Chirp3-HD otherwise voices a bare 京 as
# きょう (the city), so a large number like "800京" reads "800 Tokyo". Spell it けい at
# generation time so the reading is fixed before any synthesis.
# Char class + place-name exclusion mirror cloud_reading_lint._KEI_UNIT_RE (calibrated
# FP-zero on 5 shipped cloud eps): the negative lookahead keeps "第3京浜"(第三京浜道路)
# and "3京都" from becoming "3けい浜/けい都". An auto-rewrite must be at least as
# conservative as the detector that already flags this.
_MYRIAD_KEI = re.compile(r"(?<=[0-9０-９一二三四五六七八九十百千万億兆])京(?![都城浜阪畿])")

# Formula tokens Cloud voices wrong from raw text. Normally the symbol line uses the
# narration_speech (VOICEVOX) spell-out, but a scene whose narration_speech is
# absent/deleted falls back to raw narration and leaks "L=T-V" / "f'(x)" into the cloud
# reading -- Chirp then voices f'(x) as "エフゴエックス" and L=T-V as a raw jumble. Spell the common, unambiguous formula tokens here so the reading is correct
# even without narration_speech. Applied longest-first, AFTER the narration_speech
# fallback; idempotent on already-spelled text (a spelled reading holds no raw token),
# so it is a pure safety net -- prose never contains these tokens. cloud_reading_lint
# ._scan_raw_formula flags anything this dictionary does not yet cover.
_FORMULA_READINGS = [
    ("L=T-V", "エル・イコール・ティー・マイナス・ブイ"),
    ("f''(x)", "エフ・ダブルプライム・エックス"),
    ("f'(x)", "エフ・プライム・エックス"),
]
# Lagrange points L1..L5 as standalone tokens (not L10/L4a). Chirp voices bare "L4" as
# エルフォー or garbles it; spell エルよん/エルご to match math_07's established reading.
_LPOINT_RE = re.compile(r"L([1-5])(?![0-9A-Za-z])")
_LPOINT_KANA = {"1": "いち", "2": "に", "3": "さん", "4": "よん", "5": "ご"}


def spell_formula_tokens(text: str) -> str:
    """Spell out common formula tokens (L=T-V, f'(x), f''(x), L1..L5) that Cloud
    otherwise mis-voices. Safety net for scenes lacking a narration_speech spell-out;
    idempotent (spelled text holds no raw token) and prose-safe (tokens never occur in
    prose). Also usable to retrofit already-generated readings without a re-gen."""
    for tok, yomi in _FORMULA_READINGS:
        text = text.replace(tok, yomi)
    text = _LPOINT_RE.sub(lambda m: "エル" + _LPOINT_KANA[m.group(1)], text)
    return text


def fix_isolated_particles(text: str) -> str:
    """Rewrite comma-isolated topic/direction particles は/へ to わ/え (reattached).

    See _ISOLATED_HA/_HE for why the comma-isolation signature is a safe, analyzer-
    free way to tell a lone particle from a word-internal は/へ. Idempotent; also
    used to retrofit already-generated readings (no re-generation needed)."""
    text = _ISOLATED_HA.sub("わ", text)
    text = _ISOLATED_HE.sub("え", text)
    return text


def _cleanup(text: str) -> str:
    """『』 -> subtle pause; 「」《》 -> removed (read inline); dashes -> pause; collapse
    doubled punctuation; de-isolate comma-stranded は/へ particles (else Cloud reads
    them ha/he); and spell digit-preceded 京 as けい (else the myriad unit reads きょう)."""
    text = text.replace("|", "").replace("『", "、").replace("』", "、")
    # misreading: strip 「」 (emphasis quotes around terms like 「対数」). Chirp3-HD inserts an
    # unnatural pause at each 「/」 (speed_qa DASH warnings); the term reads smoothly
    # inline without them. narration keeps them for subtitle display; only cloud drops them.
    # misreading: 《》 (double angle brackets around 《証明》《隠れた前提》 etc.) join this -- Chirp
    # voices them NON-deterministically (heard as "ま"/"うぇ" at some 《, silent at others;
    # user-caught in person_05 「、《この者」->「ま、」 and closing_02 「《選べるもの》」->「うぇ」).
    text = text.replace("「", "").replace("」", "").replace("《", "").replace("》", "")
    text = re.sub(r"[─―—]{1,}", "、", text)
    # Dash -> 、 keeps the spaces that hugged the dash (narration "A ── は" -> "A 、 は"),
    # which strands the following particle: the comma-isolated は/へ regex needs an
    # adjacent、, so "、 は" (spaced) is missed and Cloud voices the lone は as "ha"
    #. Collapse whitespace hugging
    # any 、 before de-isolation so the reattach fires and the phantom pause is removed.
    text = re.sub(r"[ \t　]*、[ \t　]*", "、", text)
    text = text.replace("、。", "。").replace("。、", "。")
    text = re.sub(r"、{2,}", "、", text)
    text = fix_isolated_particles(text)
    text = _MYRIAD_KEI.sub("けい", text)
    text = re.sub(r"^[、\s]+", "", text)
    return text.strip()


def build_cloud_reading(narration: list, narration_speech: list | None) -> list:
    """Return the narration_speech_cloud array for one scene."""
    out = []
    for i, line in enumerate(narration):
        if _SYMBOL_RE.search(line) and narration_speech and i < len(narration_speech):
            base = narration_speech[i].replace(" ", "").replace("　", "")
        else:
            base = line
        # Spell formula tokens (L=T-V/f'(x)/Lₙ) so raw symbols never leak into the cloud
        # reading when narration_speech is absent. No-op otherwise.
        out.append(spell_formula_tokens(_cleanup(base)))
    return out


def generate(scene_path: str, force: bool = False) -> tuple[int, int]:
    """Fill narration_speech_cloud in-place. Returns (generated, preserved).

    A scene missing cloud is generated from narration (native は; symbol sentences
    use the narration_speech spell-out). An existing cloud is preserved so a
    hand-tuned reading survives re-builds; ``--force`` regenerates every scene.

    The LLM does NOT emit narration_speech_cloud -- script_generator strips any it
    produces (strip_llm_cloud_readings) so that the blanket は->わ over-conversion
    it tends to apply never reaches synthesis. Thus at pipeline time the only
    existing clouds this preserves are genuine hand-tuned ones.
    """
    with open(scene_path, encoding="utf-8") as f:
        sd = json.load(f)
    gen = skip = 0
    for sec in sd.get("sections", []):
        for sc in sec.get("scenes", []):
            narration = sc.get("narration")
            if not narration:
                continue
            if sc.get("narration_speech_cloud") and not force:
                skip += 1
                continue  # preserve existing (hand-tuned) reading
            sc["narration_speech_cloud"] = build_cloud_reading(
                narration, sc.get("narration_speech")
            )
            gen += 1
    if gen:
        with open(scene_path, "w", encoding="utf-8") as f:
            json.dump(sd, f, ensure_ascii=False, indent=2)
    return gen, skip


def main() -> int:
    p = argparse.ArgumentParser(description="Generate narration_speech_cloud for cloud episodes.")
    p.add_argument("scene_json", help="Path to scene_definition.json")
    p.add_argument(
        "--force",
        action="store_true",
        help="Regenerate all scenes (default: only scenes missing narration_speech_cloud)",
    )
    args = p.parse_args()
    gen, skip = generate(args.scene_json, args.force)
    print(f"[GEN-CLOUD] generated {gen} scene(s), preserved {skip} existing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
