#!/usr/bin/env python3
"""portrait_prompt_lint.py — check portrait source_prompt vs reference photo.

When a portrait scene's source_prompt describes facial features that contradict
the episode's reference photo (e.g. "full beard" written into the prompt while
the reference is clean-shaven), the generated image drifts from the real person.
This standalone lint catches that mismatch before a build.

It:
    1. describes the episode's reference photo with Gemini Vision,
    2. extracts the person-description part of each ken_burns scene's
       source_prompt,
    3. asks the model whether the reference photo and the prompt description
       contradict each other,
    4. reports any mismatches.

## Usage

    python scripts/portrait_prompt_lint.py episodes/<episode_id>

    # A single scene only
    python scripts/portrait_prompt_lint.py episodes/<episode_id> --scene intro_03

    # JSON output (for CI integration)
    python scripts/portrait_prompt_lint.py episodes/<episode_id> --json

## Output

Per portrait scene:
    - reference photo path
    - facial-feature claims extracted from the prompt
    - vision check result (CONSISTENT / MISMATCH + detail)

## Design notes

- Not integrated into the auto pipeline (a Gemini Vision call per scene adds
  cost and time); run as an opt-in pre-build check.
- Episodes without a reference photo are skipped.
- Vision description uses Gemini Flash (low cost); the judgment uses the same model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows console は cp932、Japanese print の文字化け回避
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def load_scene_def(episode_dir: Path) -> dict:
    p = episode_dir / "scene_definition.json"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def find_reference_photos(episode_dir: Path) -> list[Path]:
    """`images/wiki_*.jpg` を全列挙 (solo_portrait filter 込み)."""
    images_dir = episode_dir / "images"
    if not images_dir.exists():
        return []
    credits_path = episode_dir / "wikimedia_credits.json"
    solo_filenames = None
    if credits_path.exists():
        try:
            with open(credits_path, encoding="utf-8") as f:
                credits = json.load(f)
            solo_filenames = {
                p["filename"] for p in credits.get("photos", []) if p.get("solo_portrait")
            }
        except (json.JSONDecodeError, KeyError):
            pass
    refs = []
    for f in sorted(images_dir.iterdir()):
        if f.name.startswith("wiki_") and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            if solo_filenames is None or f.name in solo_filenames:
                refs.append(f)
    return refs


def has_subject_portrait_scenes(scene_def: dict) -> bool:
    """True if the episode has >=1 subject portrait scene that relies on a reference.

    A subject portrait = a ken_burns scene with use_reference != false and
    is_subject != false (no_human scenes are excluded: they intentionally have no
    person, so a missing reference is not a defect for them). When such scenes exist
    but no usable reference photo is found, "no reference" is a DEFECT (portraits
    generated text-only -> drift from the real person), not a benign skip.
    """
    sections = scene_def.get("sections") or [{"scenes": scene_def.get("scenes", [])}]
    for sec in sections:
        for sc in sec.get("scenes", []):
            v = sc.get("visual", {})
            if v.get("type") != "ken_burns":
                continue
            if v.get("use_reference", True) is False:
                continue
            if v.get("is_subject", True) is False:
                continue
            if v.get("no_human", False) is True:
                continue
            return True
    return False


def describe_reference_vision(client, image_path: Path) -> str:
    """Gemini Flash Vision に reference 写真の人物特徴を describe させる."""
    from PIL import Image

    img = Image.open(image_path)
    prompt = (
        "この画像の人物について、AI 画像生成の比較用に以下の特徴を簡潔に "
        "(各項目 1-2 文、日本語) 述べてください:\n"
        "1. 顔の毛 (beard/mustache/clean-shaven/sideburns/側面の長い髪 等)\n"
        "2. 頭髪 (色・量・受け眉・balding 程度・髪型)\n"
        "3. 顔の骨格 (broad/narrow/squared/oval、頬の張り、目蓋の感じ)\n"
        "4. 推定年齢\n"
        "5. 服装 (formal coat/bow tie/casual 等)\n"
        "推測やキャラクター付けはせず、画像に見えるもののみを記述してください。"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[img, prompt],
    )
    return response.text.strip()


def check_prompt_vs_reference(client, image_path: Path, scene_id: str, source_prompt: str) -> dict:
    """Sonnet 互換 prompt で reference 写真と source_prompt の整合性判定."""
    from PIL import Image

    img = Image.open(image_path)
    check_prompt = f"""この reference 写真は historical figure の実写真です。
これから AI 画像生成で作る scene の source_prompt と比較して、人物の
facial features (顔の毛・頭髪・骨格・年齢) に矛盾があるか判定してください。

【scene id】 {scene_id}
【source_prompt (英文)】
{source_prompt}

判定基準:
- 顔の毛 (beard/mustache/sideburns) の有無が一致しているか
- 頭髪 (balding/full head/長さ/色) が一致しているか
- 年齢層が一致しているか (若年版なら「同じ骨格の younger version」記述があるか)
- 性別が一致しているか

注意:
- prompt が「同一人物の younger/older」を明示している場合、年齢差は許容
- prompt が「clean-shaven」「NO beard」のように明示否定している場合、reference と一致なら OK
- reference は実写真、prompt は historical reconstruction なので細部完全一致は不要、主要特徴の矛盾のみ flag

JSON のみで回答 (``` なし):
{{
  "status": "CONSISTENT" | "MISMATCH",
  "mismatches": ["矛盾点 1 (日本語)", "矛盾点 2"],
  "ref_features": "reference 写真の主要特徴サマリ (1 文)",
  "prompt_features": "source_prompt 内の人物描写サマリ (1 文)"
}}

mismatches は実際の矛盾のみ、許容差 (年齢差 etc.) は除外。"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[img, check_prompt],
    )
    text = response.text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(ln for ln in lines if not ln.startswith("```"))
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "status": "PARSE_ERROR",
            "mismatches": [f"JSON parse failed: {e}"],
            "ref_features": "",
            "prompt_features": "",
            "raw": text[:300],
        }


# Classify a mismatch string as IDENTITY (facial hair / head hair / bone / gender)
# vs AGE. IDENTITY = the source_prompt contradicts WHO the subject is = a shipped-defect risk. AGE
# (young/old version) is usually intentional age variation and far lower signal, so
# it must not drown out an identity mismatch. Unclassified -> identity (fail safe:
# never hide a possible identity contradiction).
_IDENTITY_KW = (
    "顔の毛",
    "ひげ",
    "髭",
    "口ひげ",
    "もみあげ",
    "beard",
    "mustache",
    "moustache",
    "sideburn",
    "clean-shaven",
    "頭髪",
    "髪",
    "hair",
    "禿",
    "balding",
    "骨格",
    "bone",
    "性別",
    "gender",
    "ハンドルバー",
)
_AGE_KW = ("年齢", "age", "elderly", "young", "歳", "老", "若")


def classify_mismatch(mm: str) -> str:
    """'identity' if the mismatch is about facial hair / head hair / bone / gender;
    'age' if it is only about age. Identity dominates when both appear."""
    low = mm.lower()
    if any(k in mm or k.lower() in low for k in _IDENTITY_KW):
        return "identity"
    if any(k in mm or k.lower() in low for k in _AGE_KW):
        return "age"
    return "identity"


def detect_has_person_prompt(prompt: str) -> bool:
    """簡易: prompt に person-indicating words が含まれるか."""

    keywords = [
        "Portrait of",
        "portrait of",
        "a young",
        "an elderly",
        "a middle-aged",
        "an old",
        "German man",
        "German woman",
        "Russian man",
        "Russian woman",
        "French mathematician",
        "Italian",
        "Greek scholar",
        " man,",
        " woman,",
        " man ",
        " woman ",
        " man.",
        " woman.",
    ]
    return any(k in prompt for k in keywords)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("episode_dir", help="Path to episodes/<id>/")
    ap.add_argument("--scene", help="Single scene_id to check (default: all portraits)")
    ap.add_argument("--json", action="store_true", help="Emit JSON report instead of text")
    args = ap.parse_args()

    episode_dir = Path(args.episode_dir).resolve()
    if not episode_dir.exists():
        print(f"ERROR: {episode_dir} not found")
        return 1

    scene_def = load_scene_def(episode_dir)
    ref_photos = find_reference_photos(episode_dir)
    if not ref_photos:
        # Only a benign SKIP if the episode genuinely uses no subject portrait.
        # If subject portraits DO exist, "no usable reference" is a DEFECT: the lint
        # can't run and those portraits were likely generated text-only (drift from
        # the real person) -- the exact an earlier episode regression. Fail loud (WARN), still
        # return without hard-failing.
        if has_subject_portrait_scenes(scene_def):
            banner = (
                f"[WARN] subject portraits exist but no usable reference photo in "
                f"{episode_dir}/images/wiki_*.* -> lint cannot run; 主題肖像は "
                f"text-only 生成の可能性大 (本人と乖離)。wikimedia_credits.json の "
                f"solo_portrait を確認してください "
                f"(ある回で solo 誤判定->全肖像 text-only 化した回帰)。"
            )
            print(f"\n{'=' * 60}")
            print(banner)
            print("NO_USABLE_REFERENCE: 1")  # parseable marker for the pipeline roll-up
            print(banner, file=sys.stderr)  # roll-up (stderr)
            try:
                import pipeline_log

                pipeline_log.emit_stderr_warn_summary("portrait_no_reference", 1)
            except Exception:
                pass
            return 0
        print(f"[SKIP] No reference photos in {episode_dir}/images/wiki_*.*")
        return 0

    # Load config for subject_en (to skip non-subject scenes)
    config_path = episode_dir / "episode_config.json"
    subject_en = ""
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        subject_en = config.get("subject_en") or config.get("mathematician", "")

    # Get client (reuses image_generator's helper)
    from image_generator import detect_non_subject_person, get_client

    client = get_client()

    # First, describe each reference photo (so users see what we use as anchor)
    print(f"\n=== Reference photos ({len(ref_photos)}) ===")
    print(f"Subject: {subject_en}")
    for rp in ref_photos:
        print(f"\n[{rp.name}]")
        desc = describe_reference_vision(client, rp)
        for line in desc.split("\n"):
            if line.strip():
                print(f"  {line}")

    # Per-scene check: for each ken_burns scene with use_reference=true and
    # subject-matching prompt, run the consistency check
    print("\n\n=== Per-scene lint ===")
    results = []
    sections = scene_def.get("sections") or [{"scenes": scene_def.get("scenes", [])}]
    primary_ref = ref_photos[0]  # use first ref as primary anchor
    for sec in sections:
        for sc in sec.get("scenes", []):
            sid = sc.get("scene_id")
            if args.scene and sid != args.scene:
                continue
            v = sc.get("visual", {})
            if v.get("type") != "ken_burns":
                continue
            sp = v.get("source_prompt", "")
            if not detect_has_person_prompt(sp):
                continue
            scene_use_ref = v.get("use_reference", True)
            if not scene_use_ref:
                continue  # already opted out
            # Skip non-subject scenes
            non_subj = detect_non_subject_person(sp, subject_en)
            if non_subj:
                print(f"\n[{sid}] SKIP (non-subject: {non_subj}, set use_reference=false)")
                continue
            print(f"\n[{sid}] checking against {primary_ref.name}...")
            result = check_prompt_vs_reference(client, primary_ref, sid, sp)
            result["scene_id"] = sid
            results.append(result)
            status = result.get("status", "?")
            print(f"  status: {status}")
            print(f"  ref:    {result.get('ref_features', '')[:120]}")
            print(f"  prompt: {result.get('prompt_features', '')[:120]}")
            cats = []
            for mm in result.get("mismatches", []):
                c = classify_mismatch(mm)
                cats.append((c, mm))
                print(f"  MISMATCH [{'IDENTITY' if c == 'identity' else 'AGE'}]: {mm}")
            result["_categorized"] = cats

    # Summary -- separate IDENTITY (facial hair / hair / bone / gender) from AGE.
    id_scenes = [r for r in results if any(c == "identity" for c, _ in r.get("_categorized", []))]
    age_scenes = [r for r in results if r.get("status") == "MISMATCH" and r not in id_scenes]
    n_identity, n_age = len(id_scenes), len(age_scenes)
    print(f"\n{'=' * 60}")
    print(
        f"Lint summary: {len(results)} scenes checked, "
        f"{n_identity} IDENTITY mismatch scene(s), {n_age} AGE-only mismatch scene(s)"
    )
    print(f"IDENTITY_MISMATCHES: {n_identity}")  # parseable marker for the pipeline roll-up
    if n_identity:
        print(
            "  [!] IDENTITY mismatch = source_prompt が reference と顔の毛/頭髪/骨格で矛盾 "
            "-- 本人の風貌が誤って伝わる恐れ。出荷前に必ず確認 (ある回 full beard vs 口ひげ)。"
        )
        for r in id_scenes:
            for c, mm in r.get("_categorized", []):
                if c == "identity":
                    print(f"      {r['scene_id']}: {mm}")

    if args.json:
        print(
            json.dumps(
                {
                    "results": results,
                    "identity_mismatches": n_identity,
                    "age_mismatches": n_age,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    # exit 2 = IDENTITY mismatch (real subject-fidelity defect), 1 = AGE-only
    # (usually intentional young/old version), 0 = clean.
    return 2 if n_identity else (1 if n_age else 0)


if __name__ == "__main__":
    sys.exit(main())
