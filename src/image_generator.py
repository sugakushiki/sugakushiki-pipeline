"""
image_generator.py - Generate images for ken_burns scenes via Gemini API

Usage:
    python image_generator.py scene_definition.json --output-dir examples/moriarty --list
    python image_generator.py scene_definition.json --output-dir examples/moriarty --generate
    python image_generator.py scene_definition.json --output-dir examples/moriarty --generate --scene intro_02
    python image_generator.py scene_definition.json --output-dir examples/moriarty --generate --backend imagen

Curation workflow:
    1. Run --generate to create all images
    2. Review images manually, mark good ones:
       python image_generator.py scene.json --output-dir ep/ --keep intro_01,person_03
    3. Re-run --generate --regen to regenerate only non-kept images
    4. View kept images: --list shows [LOCK] for kept images

    Kept images are listed in {images_dir}/.keep (one scene_id per line).
    --force overrides .keep protection.

Modes:
    --list      Show which images are needed and their prompts (no API call)
    --generate  Call Gemini API to generate missing images
    --keep      Mark scene_ids as curated (comma-separated)
    --unkeep    Remove scene_ids from curated list (comma-separated)
    --regen     Regenerate non-kept existing images (combine with --generate)

Image backends (switch via --backend flag or IMAGE_BACKEND env var):
    "flash"  - Gemini 2.5 Flash Image (generateContent API, FREE tier) [default]
    "imagen" - Imagen 4 (generateImages API, requires billing)

Requires:
    pip install google-genai Pillow python-dotenv
    GOOGLE_API_KEY in .env file or environment variable
    Get key: https://aistudio.google.com/apikey (no billing required for flash)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from io import BytesIO

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ASPECT_RATIO = "16:9"  # Widescreen for video

# Backend-specific settings
BACKENDS = {
    "flash": {
        "model": "gemini-2.5-flash-image",
        "description": "Gemini 2.5 Flash Image (free tier, generateContent API)",
    },
    "imagen": {
        "model": "imagen-4.0-generate-001",
        "description": "Imagen 4 (paid, generateImages API, $0.04/image)",
    },
}


def _load_dotenv():
    """Load .env file from script dir, project root, or main repo root (once).

    When running inside a git worktree, the project root differs from the
    main repository root.  This function walks up from src/ and also checks
    the main repo root so that a single .env in the real project directory
    is found regardless of the working-tree location.
    """
    if getattr(_load_dotenv, "_done", False):
        return
    try:
        from dotenv import load_dotenv

        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [script_dir, os.path.dirname(script_dir)]
        # If inside a git worktree, also check the main repository root
        git_file = os.path.join(os.path.dirname(script_dir), ".git")
        if os.path.isfile(git_file):
            with open(git_file, encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("gitdir:"):
                # e.g. "gitdir: ../../.git/worktrees/name"
                gitdir = content.split(":", 1)[1].strip()
                gitdir = os.path.normpath(os.path.join(os.path.dirname(script_dir), gitdir))
                # Walk up from gitdir to find the main .git directory
                main_git = gitdir
                while main_git and not os.path.isdir(os.path.join(main_git, "objects")):
                    main_git = os.path.dirname(main_git)
                if main_git:
                    main_root = os.path.dirname(main_git)
                    if main_root not in candidates:
                        candidates.append(main_root)
        for d in candidates:
            env_path = os.path.join(d, ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                break
    except ImportError:
        pass  # python-dotenv not installed, rely on environment
    _load_dotenv._done = True


def get_client():
    """Initialize Gemini API client."""
    _load_dotenv()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found.")
        print("Set it in .env file (project root) or as environment variable.")
        print("Get your key from https://aistudio.google.com/apikey")
        sys.exit(1)

    from google import genai

    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Curation (.keep file management)
# ---------------------------------------------------------------------------
KEEP_FILENAME = ".keep"


def _keep_path(images_dir: str) -> str:
    """Return path to .keep file."""
    return os.path.join(images_dir, KEEP_FILENAME)


def load_keep_list(images_dir: str) -> set[str]:
    """Load set of curated (kept) scene_ids from .keep file."""
    path = _keep_path(images_dir)
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


def save_keep_list(images_dir: str, kept: set[str]):
    """Save curated scene_ids to .keep file."""
    os.makedirs(images_dir, exist_ok=True)
    path = _keep_path(images_dir)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Curated images - these are protected from regeneration\n")
        f.write("# Remove a line or use --unkeep to allow regeneration\n")
        for scene_id in sorted(kept):
            f.write(f"{scene_id}\n")


def add_to_keep(images_dir: str, scene_ids: list[str]):
    """Add scene_ids to .keep list."""
    kept = load_keep_list(images_dir)
    added = []
    for sid in scene_ids:
        sid = sid.strip()
        if sid and sid not in kept:
            kept.add(sid)
            added.append(sid)
    save_keep_list(images_dir, kept)
    return added


def remove_from_keep(images_dir: str, scene_ids: list[str]):
    """Remove scene_ids from .keep list."""
    kept = load_keep_list(images_dir)
    removed = []
    for sid in scene_ids:
        sid = sid.strip()
        if sid in kept:
            kept.remove(sid)
            removed.append(sid)
    save_keep_list(images_dir, kept)
    return removed


# ---------------------------------------------------------------------------
# Scene definition parsing
# ---------------------------------------------------------------------------
# 強化 A: source_prompt staleness 検出。
# scene_definition.json の visual.source_prompt (+ no_human / use_reference)
# を変更しても既存 PNG があると image_generator がスキップしていた
#。生成時に有効 prompt の fingerprint を sidecar に保存し、
# 次回ビルドで不一致なら自動再生成する (memory
#過去の運用知見の reproducibility 原則)。
_IMAGE_META_FILE = "_image_meta.json"


def _image_meta_path(images_dir: str) -> str:
    return os.path.join(images_dir, _IMAGE_META_FILE)


def _load_image_meta(images_dir: str) -> dict:
    p = _image_meta_path(images_dir)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        # 壊れた meta は無視 (再生成判定が eff-off になるだけ、致命でない)
        return {}


def _save_image_meta(images_dir: str, meta: dict) -> None:
    try:
        with open(_image_meta_path(images_dir), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"  [WARN] _image_meta.json 書き込み失敗 (再生成判定が無効化): {e}")


def _prompt_fingerprint(task: dict, appearance: str = "") -> str:
    """画像生成に影響する user 制御入力の安定 hash。

    source_prompt + no_human + use_reference を対象 (これらが変われば
    生成画像が変わる)。age 推定や reference 選択は narration/写真由来で
    user 直接編集の範囲外なので fingerprint には含めない。

    強化: appearance (subject_appearance / 顔特徴記述) は use_reference
    シーンの生成 prompt に _build_reference_prompt で注入されるため、reference
    使用シーンでは fingerprint に含める。
    appearance を渡さない呼び出し ('') は legacy fingerprint (appearance 非対象)
    を返し、旧 meta の後方互換判定に使う (deploy 時の一斉再生成を回避)。
    """
    basis = (
        f"{task.get('prompt', '')}"
        f"|nh={task.get('no_human', False)}"
        f"|ur={task.get('use_reference', True)}"
    )
    if appearance and task.get("use_reference", True):
        basis += f"|ap={appearance}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def extract_image_tasks(scene_def: dict, images_dir: str) -> list:
    """Extract list of images that need to be generated.

    Returns list of dicts with:
        scene_id, section_id, source (filename), prompt, status, img_path, kept
    """
    kept_set = load_keep_list(images_dir)
    tasks = []
    for section in scene_def["sections"]:
        section_id = section.get("section_id", "")
        for scene in section["scenes"]:
            v = scene["visual"]
            if v["type"] != "ken_burns":
                continue

            source = v.get("source")
            prompt = v.get("source_prompt", "")

            if source:
                img_path = os.path.join(images_dir, source)
                if os.path.exists(img_path):
                    status = "exists"
                else:
                    status = "missing_file"
            else:
                source = f"{scene['scene_id']}.png"
                if os.path.exists(os.path.join(images_dir, source)):
                    status = "exists"
                elif prompt:
                    status = "needed"
                else:
                    status = "no_prompt"

            narration = " ".join(scene.get("narration", []))
            # Per-scene reference photo override (default: True)
            # Set "use_reference": false in visual block to skip reference
            # photos for scenes depicting other historical figures
            # (e.g. Leibniz in a Seki episode).
            use_reference = v.get("use_reference", True)

            # No-human declarative flag: explicit "no people"
            # scene declaration. When true, force use_reference=False and
            # append no-human prompt suffix at generation time.
            no_human = v.get("no_human", False)
            if not isinstance(no_human, bool):
                raise ValueError(
                    f"scene {scene['scene_id']}: visual.no_human must be bool, "
                    f"got {type(no_human).__name__}={no_human!r}"
                )
            if no_human:
                # Issue 3 (s94 fix): warn when explicit use_reference=true
                # conflicts with no_human=true. Silent override would confuse
                # users who set both flags expecting both to apply.
                if "use_reference" in v and v["use_reference"] is True:
                    print(
                        f"  [WARN] scene {scene['scene_id']}: explicit "
                        f"use_reference=true overridden by no_human=true"
                    )
                # Override: no_human implies no reference photo (a person
                # reference photo would contradict "no human in scene").
                use_reference = False

            # cliche scanner: visual.cliche_acks is an optional
            # list of cliche terms that the user has explicitly verified for
            # this scene — included in task dict for cliche_scanner opt-out.
            cliche_acks = v.get("cliche_acks", [])
            if not isinstance(cliche_acks, list) or not all(
                isinstance(a, str) for a in cliche_acks
            ):
                raise ValueError(
                    f"scene {scene['scene_id']}: visual.cliche_acks must be "
                    f"list[str], got {type(cliche_acks).__name__}={cliche_acks!r}"
                )

            tasks.append(
                {
                    "scene_id": scene["scene_id"],
                    "section_id": section_id,
                    "source": source,
                    "prompt": prompt,
                    "narration": narration,
                    "status": status,
                    "img_path": os.path.join(images_dir, source),
                    "kept": scene["scene_id"] in kept_set,
                    "use_reference": use_reference,
                    "no_human": no_human,
                    "is_subject": v.get("is_subject", True),
                    "cliche_acks": cliche_acks,
                }
            )

    return tasks


def list_tasks(tasks: list):
    """Display image generation task list."""
    print(f"\n{'=' * 60}")
    print(f"Image generation tasks ({len(tasks)} ken_burns scenes)")
    print(f"{'=' * 60}\n")

    for t in tasks:
        status = t["status"]
        has_prompt = bool(t["prompt"])
        kept = t.get("kept", False)

        if status == "exists" and kept:
            icon = "[LOCK]"
            note = " (curated, protected)"
        elif status == "exists":
            icon = "[OK]"
            note = ""
        elif status == "needed":
            icon = "[ ]"
            note = ""
        elif status == "missing_file" and has_prompt:
            icon = "[ ]"
            note = " (can regenerate)"
        elif status == "missing_file" and not has_prompt:
            icon = "[LIST]"
            note = " (copy from Phase 0)"
        elif status == "no_prompt":
            icon = "[NG]"
            note = " (no prompt defined)"
        else:
            icon = "?"
            note = ""

        print(f"  {icon} {t['scene_id']:15s}  {t['source']:30s}  [{status}]{note}")
        if status in ("needed", "missing_file") and has_prompt:
            p = t["prompt"][:80] + "..." if len(t["prompt"]) > 80 else t["prompt"]
            print(f"     prompt: {p}")
        print()

    gen_needed = sum(1 for t in tasks if t["status"] in ("needed", "missing_file") and t["prompt"])
    copy_needed = sum(1 for t in tasks if t["status"] == "missing_file" and not t["prompt"])
    existing = sum(1 for t in tasks if t["status"] == "exists")
    kept_count = sum(1 for t in tasks if t.get("kept", False))
    regen_candidates = sum(
        1 for t in tasks if t["status"] == "exists" and not t.get("kept", False) and t["prompt"]
    )
    print(
        f"  Summary: {existing} exist ({kept_count} curated), {gen_needed} to generate,"
        f" {copy_needed} to copy from Phase 0"
    )
    if regen_candidates:
        print(f"  Regen candidates: {regen_candidates} (existing, not curated, have prompt)")
        print("  Use --generate --regen to regenerate these.")
    if gen_needed:
        print(f"\n  Run with --generate to create {gen_needed} images via Gemini API.")


# ---------------------------------------------------------------------------
# Backend: Gemini 2.5 Flash Image (generateContent API - FREE)
# ---------------------------------------------------------------------------
def generate_image_flash(client, prompt: str, output_path: str, retries: int = 2) -> bool:
    """Generate image via Gemini 2.5 Flash Image (generateContent API).

    Free tier: ~1,500 requests/day, no billing required.
    Pricing if paid: ~$0.039/image.
    """
    from google.genai import types

    model = BACKENDS["flash"]["model"]

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=ASPECT_RATIO,
        ),
    )

    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            # Extract image from response parts
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        from PIL import Image

                        img = Image.open(BytesIO(part.inline_data.data))
                        img.save(output_path)
                        return True

            print(f"      No image in response (attempt {attempt + 1})")

        except Exception as e:
            err_str = str(e)
            print(f"      Error (attempt {attempt + 1}): {err_str[:200]}")

            if attempt < retries:
                wait = 2**attempt
                print(f"      Waiting {wait}s before retry...")
                time.sleep(wait)

    return False


# ---------------------------------------------------------------------------
# Backend: Imagen 4 (generateImages API - requires billing)
# ---------------------------------------------------------------------------
def detect_has_person(prompt: str) -> bool:
    """Heuristic: does the prompt describe a person? (Imagen backend only)"""
    person_keywords = [
        "man ",
        "woman ",
        "person ",
        "mathematician",
        "portrait",
        "elderly",
        "young ",
        "wearing",
        "expression",
        "hair",
        "hungarian",
        "standing",
        "sitting",
        "seated",
        "holding",
        "lawyer",
        "scholar",
        "friar",
        "philosopher",
        "nobleman",
        "magistrate",
        "judge",
        "priest",
        "monk",
    ]
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in person_keywords)


def should_use_reference_photo(
    global_use_reference: bool, has_person: bool, scene_use_reference: bool
) -> bool:
    """Decide whether a reference photo should be used for this scene.

    All three conditions must be True:
    - global_use_reference: module-level flag (ref photos exist + birth_year + flash backend)
    - has_person: the prompt describes a person
    - scene_use_reference: the scene's visual.use_reference is not explicitly False

    Extracted for unit testing; mirrors the gate in generate_all().
    """
    return bool(global_use_reference) and bool(has_person) and bool(scene_use_reference)


def detect_non_subject_person(prompt: str, subject_en: str) -> str | None:
    """強化 B: Detect if a scene's source_prompt mainly depicts a NON-subject person.

    ある回 で math_13 (Hermite) と closing_01 (Kovalevskaya) が Weierstrass の
    reference 写真を渡されて顔汚染した case の構造防御。

    heuristic:
        1. subject_en を構成する単語 (e.g. "Karl", "Weierstrass") のいずれかが
           prompt に登場すれば subject scene と判定 → None を返す
        2. それ以外で「Name Surname」型 (Capitalized + space + Capitalized) の
           proper noun pair が prompt にあれば、それが scene の主人物候補。
        3. または「Sofia/Charles/Bernard」等の単一 capitalized first name の後に
           "Russian woman" / "French mathematician" / "German" 等 description
           があれば single-name candidate

    Returns:
        非主題人物の name (検出時) or None (subject scene または検出不能)
    """
    if not prompt or not subject_en:
        return None

    import re as _re

    # subject の単語 (姓・名) が prompt に登場するか
    subject_words = [w for w in _re.split(r"\s+", subject_en.strip()) if len(w) >= 3]
    for w in subject_words:
        if _re.search(rf"\b{_re.escape(w)}\b", prompt):
            return None  # Subject is mentioned → subject scene

    # Subject not mentioned → look for other Capitalized name patterns.
    # Match "First Last" or "First Middle Last" style proper nouns.
    # Filter out common false positives (months, days, place names with caps).
    # NOTE: this list is intentionally broad to suppress false positives in
    # generic descriptive prose ("Young Victorian-era scholar", "The Strand
    # Magazine", "Royal Academy") — moriarty test exposed cases.
    EXCLUDE = {
        # Months/days
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        # Places (common cities/regions in 18-19c European math episodes)
        "Berlin",
        "Paris",
        "London",
        "Rome",
        "Athens",
        "Madrid",
        "Vienna",
        "Prussia",
        "Westphalia",
        "Stockholm",
        "Munich",
        "Bonn",
        "Munster",
        "Gottingen",
        "Heidelberg",
        "Strand",
        # Nationality/era adjectives that often appear as "<Adj> <NameWord>"
        "Prussian",
        "German",
        "French",
        "British",
        "English",
        "Russian",
        "Greek",
        "Italian",
        "Dutch",
        "Spanish",
        "Swiss",
        "Bohemian",
        "American",
        "European",
        "Asian",
        "African",
        "Indian",
        "Chinese",
        "Japanese",
        "Persian",
        "Arab",
        "Arabic",
        "Jewish",
        "Hindu",
        # Era / period descriptors
        "Victorian",
        "Edwardian",
        "Georgian",
        "Elizabethan",
        "Tudor",
        "Hellenistic",
        "Roman",
        "Medieval",
        "Renaissance",
        "Baroque",
        "Classical",
        "Modern",
        "Contemporary",
        "Ancient",
        # Age / size adjectives often capitalized at sentence start
        "Young",
        "Old",
        "Elderly",
        "Middle",
        "Aged",
        "Senior",
        "Junior",
        "Little",
        "Big",
        "Tall",
        "Short",
        "Heavy",
        "Slim",
        "Slender",
        # Articles/determiners that get capitalized sentence-initially
        "The",
        "An",
        "A",
        "His",
        "Her",
        "Their",
        "This",
        "That",
        "These",
        "Those",
        "Some",
        "Every",
        # Institution words
        "Europe",
        "Academy",
        "Royal",
        "Sciences",
        "Science",
        "University",
        "Theological",
        "Philosophical",
        "Mathematical",
        "Society",
        "Acta",
        "Cours",
        "Crelle",
        "College",
        "Institute",
        "Library",
        "Museum",
        "Cathedral",
        "Church",
        "Temple",
        "Palace",
        "Hall",
        "Studio",
        "Office",
        # Generic role words ("Portrait of"/"Image of" wrappers)
        "Portrait",
        "Image",
        "Photograph",
        "Drawing",
        "Painting",
        "Sketch",
        "Scene",
        "View",
        "Shot",
        "Composition",
    }
    # Extract all capitalized words and look for consecutive non-EXCLUDE pairs.
    # moriarty fix: "Young Charles Darwin" should NOT skip "Charles
    # Darwin" just because "Young Charles" hits EXCLUDE on the first word.
    # We iterate through all capitalized-word positions and find a pair where
    # BOTH words are non-EXCLUDE AND adjacent (separated by whitespace only).
    cap_words = [(m.start(), m.group()) for m in _re.finditer(r"\b[A-Z][a-z]+\b", prompt)]
    for i in range(len(cap_words) - 1):
        pos_a, word_a = cap_words[i]
        pos_b, word_b = cap_words[i + 1]
        # Adjacent means only whitespace between them (no comma, period, etc.)
        between = prompt[pos_a + len(word_a) : pos_b]
        if not _re.fullmatch(r"[ \t-]+", between):
            continue
        if word_a in EXCLUDE or word_b in EXCLUDE:
            continue
        if word_a in subject_words or word_b in subject_words:
            continue
        return f"{word_a} {word_b}"

    return None


def should_use_reference_photo_with_subject_guard(
    global_use_reference: bool,
    has_person: bool,
    scene_use_reference: bool,
    prompt: str,
    subject_en: str,
    scene_id: str = "",
) -> tuple[bool, str | None]:
    """強化 B: should_use_reference_photo + subject mismatch guard.

    Returns (use_reference_decision, warning_message_or_None).
    If the scene depicts a non-subject person (detect_non_subject_person hits),
    force use_reference=False and return a warning. This prevents the
    ある回 case where Hermite/Kovalevskaya scenes received Weierstrass photo.
    """
    base = should_use_reference_photo(global_use_reference, has_person, scene_use_reference)
    if not base:
        return False, None
    # fix: the auto-detection of a "non-subject person" fires on ANY pair of
    # adjacent capitalised words — including place/institution names (e.g. "Dunsink
    # Observatory") and merely-mentioned secondary people (e.g. "Zerah Colburn",
    # "Catherine Disney") in a scene that still DEPICTS the subject. Force-dropping
    # the reference there made most subject portraits fall back to text-only
    # generation (idealised, generic faces). The reference decision must instead be
    # driven by the EXPLICIT flags (visual.use_reference / is_subject); the fuzzy
    # detection is demoted to an advisory WARNING only.
    non_subj = detect_non_subject_person(prompt, subject_en)
    if non_subj:
        warn = (
            f"  [REF-GUARD] {scene_id}: prompt mentions '{non_subj}' (possible non-subject "
            f"person/place) while subject is '{subject_en}'. Reference is STILL USED "
            f"(scene likely depicts the subject). If this scene actually depicts a "
            f"non-subject, set visual.use_reference=false (or is_subject=false) explicitly."
        )
        return base, warn
    return base, None


def generate_image_imagen(
    client, prompt: str, output_path: str, retries: int = 2, has_person: bool = False
) -> bool:
    """Generate image via Imagen 4 (generateImages API).

    Requires Google Cloud billing. $0.04/image.
    New accounts get $300 free credit (90 days).
    """
    from google.genai import types

    model = BACKENDS["imagen"]["model"]

    config = types.GenerateImagesConfig(
        numberOfImages=1,
        aspectRatio=ASPECT_RATIO,
        outputMimeType="image/png",
        personGeneration="ALLOW_ADULT" if has_person else "DONT_ALLOW",
    )

    for attempt in range(retries + 1):
        try:
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=config,
            )

            if response.generated_images:
                img = response.generated_images[0]
                img.image.save(output_path)
                return True
            else:
                print(f"      No images returned (attempt {attempt + 1})")

        except Exception as e:
            err_str = str(e)
            print(f"      Error (attempt {attempt + 1}): {err_str[:200]}")

            # If safety filter, retry without person generation
            if "safety" in err_str.lower() and has_person and attempt == 0:
                print("      Retrying without person generation...")
                config = types.GenerateImagesConfig(
                    numberOfImages=1,
                    aspectRatio=ASPECT_RATIO,
                    outputMimeType="image/png",
                    personGeneration="DONT_ALLOW",
                )
                continue

            if attempt < retries:
                wait = 2**attempt
                print(f"      Waiting {wait}s before retry...")
                time.sleep(wait)

    return False


# ---------------------------------------------------------------------------
# Reference-based generation (age-aware, uses Wikimedia photo as base)
#
# Solves two problems simultaneously:
#   1. Cross-scene person consistency (same facial features throughout)
#   2. Age-appropriate appearance (young/middle-aged/elderly per scene)
#
# Uses Gemini Flash's image+text → image capability to transform a real
# photograph into an oil painting at a different age.
# ---------------------------------------------------------------------------

# Count of dirs where wiki_* references exist but NONE are usable as a solo
# portrait even after Vision (fail-loud backstop). Surfaced to the pipeline
# advisory roll-up from __main__ via pipeline_log.emit_stderr_warn_summary.
_REF_TEXTONLY_HITS = 0


def _vision_count_people(image_path: str) -> int | None:
    """Return how many distinct real human people have a visible face in the image.

    Uses Gemini Vision (gemini-2.5-flash), matching the call shape of
    scripts/portrait_prompt_lint.describe_reference_vision. Used ONLY to recover a
    text-heuristic-dropped photo that is actually a solo portrait.

    Graceful degrade: returns None on ANY error, and when google-genai is not
    installed or GOOGLE_API_KEY is missing (the caller treats None as "cannot
    confirm solo" -> not promoted). Never raises, so the images step can't crash.
    """
    try:
        _load_dotenv()
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        from google import genai
        from PIL import Image

        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)
        prompt = (
            "Look at this photograph and count the distinct real human people whose "
            "face is visible in it. Reply with ONLY a single integer "
            "(for example 0, 1, 2, ...) and nothing else."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt],
        )
        text = (response.text or "").strip()
        m = re.search(r"\d+", text)
        return int(m.group()) if m else None
    except Exception as e:
        print(
            f"  [PHOTO] Vision face-count failed for {os.path.basename(image_path)}: {str(e)[:120]}"
        )
        return None


def _set_solo_portrait_in_credits(credits_path: str, filename: str) -> None:
    """Persist solo_portrait=True for `filename` in wikimedia_credits.json.

    Called when Vision confirms a text-heuristic-dropped photo is actually a solo
    portrait, so the correction sticks (later runs skip the Vision call). Writes
    back with encoding='utf-8', ensure_ascii=False, indent=2.
    """
    if not credits_path or not os.path.exists(credits_path):
        return
    try:
        with open(credits_path, encoding="utf-8") as f:
            credits = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(
            f"  [PHOTO] Could not read {os.path.basename(credits_path)} to persist "
            f"solo_portrait: {e}"
        )
        return
    changed = False
    for p in credits.get("photos", []):
        if p.get("filename") == filename:
            p["solo_portrait"] = True
            changed = True
    if not changed:
        return
    try:
        with open(credits_path, "w", encoding="utf-8") as f:
            json.dump(credits, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"  [PHOTO] Could not write {os.path.basename(credits_path)}: {e}")


def _demote_group_photo_in_credits(credits_path: str, filename: str, n_people: int) -> None:
    """Persist solo_portrait=False + usage="unused" for a ref Vision found to be a
    GROUP photo. Mirror of _set_solo_portrait_in_credits (the promote path):
    is_solo_portrait() is a text heuristic that can mis-tag a group photo as solo
, which would then contaminate the identity
    reference. Persisting the demotion stops it being used AND being credited.
    """
    if not credits_path or not os.path.exists(credits_path):
        return
    try:
        with open(credits_path, encoding="utf-8") as f:
            credits = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    changed = False
    for p in credits.get("photos", []):
        if p.get("filename") == filename:
            p["solo_portrait"] = False
            p["usage"] = "unused"
            p["unused_reason"] = (
                f"Vision face-count = {n_people} (group photo mis-tagged solo; "
                "not a valid identity reference)"
            )
            changed = True
    if not changed:
        return
    try:
        with open(credits_path, "w", encoding="utf-8") as f:
            json.dump(credits, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"  [PHOTO] Could not write {os.path.basename(credits_path)}: {e}")


def _warn_refs_present_but_unusable() -> None:
    """Fail-loud backstop (Part B): wiki_* reference photos exist but none are usable
    as a solo portrait even after Vision -> subject portraits fall back to text-only
    generation and drift from the real person. Advisory only:
    emits a prominent WARN to stderr for the pipeline roll-up, never halts the build.
    """
    global _REF_TEXTONLY_HITS
    _REF_TEXTONLY_HITS += 1
    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    msg = (
        "  [WARN] 参照写真は存在するのに使える solo portrait が 0 件 "
        "-> 主題肖像が text-only 生成になり本人と乖離します。"
        "wikimedia_credits.json の solo_portrait を確認してください "
        "。"
    )
    print(msg, file=sys.stderr)
    try:
        sys.stderr.flush()
    except Exception:
        pass


def _find_reference_photos(images_dir: str) -> list[str]:
    """Find solo-portrait Wikimedia photos (wiki_*.jpg/png) for use as references.

    Only returns photos tagged as solo_portrait=True in wikimedia_credits.json.
    Group photos (multiple people) can't be used as identity anchors because
    the model can't determine which person is the subject.

    Falls back to all wiki_* files if credits JSON doesn't exist.
    """
    if not os.path.isdir(images_dir):
        return []

    # Try reading credits to filter by solo_portrait
    episode_dir = os.path.dirname(images_dir)
    credits_path = os.path.join(episode_dir, "wikimedia_credits.json")
    solo_filenames = None
    if os.path.exists(credits_path):
        try:
            with open(credits_path, encoding="utf-8") as f:
                credits = json.load(f)
            solo_filenames = {
                p["filename"] for p in credits.get("photos", []) if p.get("solo_portrait", False)
            }
        except (json.JSONDecodeError, KeyError):
            solo_filenames = None

    refs = []
    skipped = []
    for f in sorted(os.listdir(images_dir)):
        if f.startswith("wiki_") and f.lower().endswith((".jpg", ".jpeg", ".png")):
            if solo_filenames is not None:
                if f in solo_filenames:
                    refs.append(os.path.join(images_dir, f))
                else:
                    skipped.append(f)
            else:
                # No credits info → include all (backward compat)
                refs.append(os.path.join(images_dir, f))

    # misreading: Vision-validate the INCLUDED refs (symmetric to the promote path
    # below). is_solo_portrait() is a TEXT heuristic on the Wikimedia title/
    # description; a group photo whose text lacks group keywords is mis-tagged
    # solo=true and would be used as an identity reference, contaminating every
    # subject portrait. Demote refs Vision confirms are
    # groups (count >= 2); keep on None (no API key -> identical to the legacy
    # fast path) / 0 / 1 to avoid false demotion. Bounded: 1-3 refs, once per build.
    if refs:
        kept = []
        for rp in refs:
            n_people = _vision_count_people(rp)
            if n_people is not None and n_people >= 2:
                fname = os.path.basename(rp)
                skipped.append(fname)
                _demote_group_photo_in_credits(credits_path, fname, n_people)
                print(
                    f"  [PHOTO] Vision override: {fname} shows {n_people} people "
                    f"-> demoted (mis-tagged solo, NOT used as reference)"
                )
            else:
                kept.append(rp)
        refs = kept

    # Common case: references already usable -> return as-is.
    if refs:
        if skipped:
            print(
                f"  [PHOTO] Skipped {len(skipped)} group photo(s) as reference: "
                f"{', '.join(skipped)}"
            )
        return refs

    # refs is empty. If wiki_* files exist that the TEXT heuristic dropped, run a
    # Gemini Vision face-count to recover mis-tagged solo portraits. Group photos (Vision count >= 2) stay skipped.
    promoted = []
    for fname in skipped:
        n_people = _vision_count_people(os.path.join(images_dir, fname))
        if n_people == 1:
            refs.append(os.path.join(images_dir, fname))
            promoted.append(fname)
            _set_solo_portrait_in_credits(credits_path, fname)
            print(
                f"  [PHOTO] Vision override: {fname} shows 1 person "
                f"-> promoted to solo reference (credits updated)"
            )

    remaining_skipped = [f for f in skipped if f not in promoted]
    if remaining_skipped:
        print(
            f"  [PHOTO] Skipped {len(remaining_skipped)} group photo(s) as reference: "
            f"{', '.join(remaining_skipped)}"
        )

    # Fail-loud backstop: wiki_* references exist but none are usable even after
    # Vision (bad tags + no API key, or genuinely all group photos). WARN, no halt.
    if not refs and skipped:
        _warn_refs_present_but_unusable()

    return refs


def _mark_reference_photos_unused(images_dir: str) -> None:
    """Downgrade usage="reference" -> "unused" in wikimedia_credits.json.

    Called when reference photos were fetched but the GLOBAL reference gate is
    OFF (e.g. an ancient figure with no birth_year, so use_reference evaluates
    False and NO photo is passed to Gemini -> images are text-only/imaginative).
    credits_generator credits by usage label, so without this it would falsely
    credit un-used photos -- a wrong CC BY-SA festival photo mis-fetched for
    "Euclid of Alexandria" entered ある回's public description this way. Only
    touches usage=="reference" without a scene_id (scene-assigned photos, which
    ARE composited, are left intact). Idempotent.
    """
    episode_dir = os.path.dirname(images_dir)
    credits_path = os.path.join(episode_dir, "wikimedia_credits.json")
    if not os.path.exists(credits_path):
        return
    try:
        with open(credits_path, encoding="utf-8") as f:
            credits = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    changed = 0
    for ph in credits.get("photos", []):
        if ph.get("usage") == "reference" and not ph.get("scene_id"):
            ph["usage"] = "unused"
            ph["unused_reason"] = (
                "global reference gate off (no birth_year / non-flash backend): "
                "fetched but never passed to Gemini"
            )
            changed += 1
    if not changed:
        return
    try:
        with open(credits_path, "w", encoding="utf-8") as f:
            json.dump(credits, f, ensure_ascii=False, indent=1)
        print(
            f"  [PHOTO] {changed} fetched reference photo(s) marked unused "
            f"(global gate off; not credited in description)"
        )
    except OSError:
        pass


def _estimate_scene_age(narration: str, birth_year: int, source_prompt: str = "") -> int | None:
    """Estimate the subject's approximate age from narration text.

    Returns age as integer, or None if undeterminable.
    Uses same logic as wikimedia_fetcher._extract_scene_year but returns age directly.
    """
    # Strategy 1: Explicit year (YYYY年)
    # 修正: 1[89]XX|20XX → [12]XXX (1000-2999) に拡張。
    # 17世紀以前の数学者（フェルマー1607, 関孝和1642等）で1600年代の年号が
    # マッチしなかったバグを修正。
    year_matches = re.findall(r"(?<!\d)([12]\d{3})年", narration)
    if year_matches:
        age = int(year_matches[0]) - birth_year
        if 0 < age < 200:  # 妥当な年齢範囲のみ
            return age

    # Strategy 2: Direct age mention (N歳)
    age_matches = re.findall(r"(\d{1,3})歳", narration)
    if age_matches:
        age = int(age_matches[0])
        if 0 < age < 120:
            return age

    # Strategy 3: Explicit age directive in the source_prompt (e.g. "in his 50s").
    # This is scene- and subject-specific (the artist's directive for THIS portrait),
    # so it OUTRANKS the ambient narration era-keywords in Strategy 4 below. Those
    # keywords can false-match on OTHER people in the scene: ある回 ("戦後
    # ...一世代を育てました ... 学生寮 ...") matched 学生→age 20 for a 50s teaching
    # scene, overriding the prompt's clear "in his 50s" and producing a young solo
    # portrait under reference conditioning.
    if source_prompt:
        prompt_lower = source_prompt.lower()

        # 4a: Digit decades — "in his/her 70s", "in his/her late 70s"
        en_age = re.findall(
            r"(?:in (?:his|her|their) )?(?:early |late |mid[- ]?)?(\d{2})s", prompt_lower
        )
        if en_age:
            decade = int(en_age[0])
            return decade + 5  # midpoint of decade

        # 4b: Word decades — "in his mid-thirties", "in her early fifties"
        _WORD_DECADES = {
            "twenties": 20,
            "thirties": 30,
            "forties": 40,
            "fifties": 50,
            "sixties": 60,
            "seventies": 70,
            "eighties": 80,
            "nineties": 90,
        }
        for word, decade in _WORD_DECADES.items():
            if word in prompt_lower:
                if "early" in prompt_lower:
                    return decade + 2
                elif "late" in prompt_lower:
                    return decade + 8
                else:
                    return decade + 5  # mid or unspecified

        # 4c: "N years old", "N-year-old"
        en_age2 = re.findall(r"(\d{1,3})[- ]?years?[- ]?old", prompt_lower)
        if en_age2:
            age = int(en_age2[0])
            if 0 < age < 120:
                return age

        # 4d: "elderly" without specific age
        if "elderly" in prompt_lower:
            return 75

    # Strategy 4: Era keywords in the narration (lowest priority -- ambient and
    # greedy, so it only runs when the narration has no year / no 歳 and the
    # source_prompt gave no explicit age above).
    _ERA_AGES = {
        "幼少": 5,
        "幼い": 5,
        "子供": 8,
        "少年": 10,
        "青年": 20,
        "若い": 22,
        "学生": 20,
        "大学": 20,
        "中年": 45,
        "壮年": 50,
        "晩年": 75,
        "老年": 75,
        "最晩年": 80,
        "死去": 80,
        "亡くな": 80,
        "逝去": 80,
    }
    for keyword, age in _ERA_AGES.items():
        if keyword in narration:
            return age

    return None


def _build_reference_prompt(
    original_prompt: str, target_age: int, ref_photo_age: int | None, appearance: str = ""
) -> str:
    """Build a prompt for reference-based age transformation.

    Combines the original source_prompt with age transformation instructions.
    If appearance is provided, injects persistent facial feature descriptions
    to improve cross-scene identity consistency.
    """
    # source_prompt から性別を推定
    prompt_lower = original_prompt.lower()
    if any(w in prompt_lower for w in ("woman", "female", "she ", "her ", "girl")):
        gender = "woman"
    else:
        gender = "man"

    # 年齢帯の自然な外見記述
    if target_age <= 10:
        age_desc = f"a child of about {target_age} years old, youthful face, smooth skin"
    elif target_age <= 25:
        age_desc = (
            f"a young {gender} of about {target_age} years old, full dark hair, youthful features"
        )
    elif target_age <= 45:
        age_desc = f"a middle-aged {gender} of about {target_age} years old, some grey in hair"
    elif target_age <= 65:
        age_desc = (
            f"an older {gender} of about {target_age} years old, greying hair, weathered features"
        )
    else:
        age_desc = (
            f"an elderly {gender} of about {target_age} years old, white/grey hair, aged features"
        )

    # 固有の顔特徴（全シーン共通で注入）
    identity_desc = ""
    if appearance:
        identity_desc = (
            f"The subject has these CONSISTENT facial features across all ages: "
            f"{appearance}. These features must be preserved regardless of age. "
        )

    # 変換方向の説明
    if ref_photo_age and abs(target_age - ref_photo_age) <= 10:
        transform = "Paint this person at approximately the same age as in the photograph."
    elif ref_photo_age and target_age < ref_photo_age:
        transform = (
            f"De-age this person from ~{ref_photo_age} to ~{target_age} years old. "
            f"Keep the same bone structure, ethnicity, and distinctive facial features."
        )
    elif ref_photo_age and target_age > ref_photo_age:
        transform = (
            f"Age this person from ~{ref_photo_age} to ~{target_age} years old. "
            f"Keep the same bone structure, ethnicity, and distinctive facial features."
        )
    else:
        transform = (
            f"Depict this same person as {age_desc}. "
            f"Keep the same bone structure, ethnicity, and distinctive facial features."
        )

    prompt = (
        f"Using this photograph as a reference for the person's identity, "
        f"create an oil painting in academic realism style. "
        f"Render the face faithfully and true to life from the reference photograph; "
        f"do NOT beautify, glamorize, smooth, slim or idealize the face, and do not make the "
        f"person look younger, more handsome or more conventionally attractive than they really "
        f"were. Preserve their real, plain, characteristic features (hairline and any baldness, "
        f"side-whiskers/facial hair, lines, build and bearing). "
        f"{identity_desc}"
        f"{transform} "
        f"The subject should appear as {age_desc}. "
        f"{original_prompt}"
    )
    return prompt


def generate_image_with_reference(
    client, reference_path: str, prompt: str, output_path: str, retries: int = 2
) -> bool:
    """Generate image using a reference photo + text prompt via Gemini Flash.

    Uses generateContent with [image, text] input and IMAGE output modality.
    The reference photo provides person identity; the prompt controls age/style/setting.
    """
    from google.genai import types
    from PIL import Image

    model = BACKENDS["flash"]["model"]

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=ASPECT_RATIO,
        ),
    )

    try:
        ref_img = Image.open(reference_path)
    except Exception as e:
        print(f"      Failed to load reference: {e}")
        return False

    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[ref_img, prompt],
                config=config,
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        img = Image.open(BytesIO(part.inline_data.data))
                        img.save(output_path)
                        return True

            print(f"      No image in response (attempt {attempt + 1})")

        except Exception as e:
            err_str = str(e)
            print(f"      Error (attempt {attempt + 1}): {err_str[:200]}")

            if attempt < retries:
                wait = 2**attempt
                print(f"      Waiting {wait}s before retry...")
                time.sleep(wait)

    return False


def _select_best_reference(
    ref_photos: list[str], target_age: int | None, photo_ages: dict[str, int | None]
) -> str | None:
    """Select the best reference photo for a given target age.

    Prefers the photo whose age is closest to target_age.
    If target_age is unknown, returns the first photo.
    """
    if not ref_photos:
        return None
    if target_age is None or not photo_ages:
        return ref_photos[0]

    best = None
    best_dist = float("inf")
    for path in ref_photos:
        pa = photo_ages.get(path)
        if pa is not None:
            dist = abs(pa - target_age)
            if dist < best_dist:
                best_dist = dist
                best = path
    return best or ref_photos[0]


# ---------------------------------------------------------------------------
# Image quality evaluation (Claude Sonnet Vision via Claude Code CLI)
#
# 役割分担:
#   evaluate_image_quality() — 生成時インライン評価。Claude Code CLI経由でSonnet使用。
#       Max契約内で追加コストなし。時代・場所・雰囲気・構図の品質チェック＋リトライ駆動。
#       Claude Code未インストール時はGemini Flash Visionにフォールバック。
#   qa_image_checker.py — Gate 2スタンドアロン。Claude Sonnet Vision（要ANTHROPIC_API_KEY）。
#       個別シーン評価＋クロスシーン人物一貫性チェック。
# ---------------------------------------------------------------------------
def _call_claude_vision(image_path: str, prompt: str, debug: bool = False) -> str | None:
    """Call Claude Code CLI with an image file path and text prompt.

    Uses the same file-based I/O pattern as claude_backend.py.
    Claude Code reads the image file directly via its Read tool.
    Runs under Max subscription — no API key or additional cost.

    Returns response text, or None on failure.
    """
    import tempfile

    # Build combined prompt: instruct Claude to read the image, then evaluate
    abs_image_path = os.path.abspath(image_path)
    combined = (
        f"以下の画像ファイルを読んで評価してください。\n画像ファイル: {abs_image_path}\n\n{prompt}"
    )

    tmp_dir = tempfile.gettempdir()
    prompt_path = os.path.join(tmp_dir, "_tmp_vision_prompt.txt")
    output_path = os.path.join(tmp_dir, "_tmp_vision_output.txt")
    error_path = os.path.join(tmp_dir, "_tmp_vision_error.txt")

    try:
        with open(prompt_path, "w", encoding="utf-8-sig") as f:
            f.write(combined)

        for p in [output_path, error_path]:
            if os.path.exists(p):
                os.remove(p)

        cmd = (
            f'type "{prompt_path}" | claude -p --output-format text '
            f'> "{output_path}" 2> "{error_path}"'
        )

        if debug:
            print(f"    [DEBUG] Vision prompt: {len(combined)} chars")
            print(f"    [DEBUG] Image: {abs_image_path}")

        exit_code = os.system(cmd)

        if exit_code != 0:
            if debug and os.path.exists(error_path):
                with open(error_path, encoding="utf-8", errors="replace") as f:
                    print(f"    [DEBUG] stderr: {f.read().strip()[:200]}")
            return None

        if not os.path.exists(output_path):
            return None

        with open(output_path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()

    except Exception as e:
        if debug:
            print(f"    [DEBUG] _call_claude_vision error: {e}")
        return None
    finally:
        for p in [prompt_path, output_path, error_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


def evaluate_image_quality(
    client, image_path: str, prompt: str, narration: str, scene_id: str
) -> dict:
    """Evaluate a generated image using Claude Sonnet Vision (via Claude Code CLI).

    Primary: Claude Code CLI (`claude -p`) — Max subscription, no additional cost.
    Fallback: Gemini Flash Vision (if Claude Code is unavailable).

    Returns dict with keys: passed (bool), issues (list[str]), feedback (str)
    """
    eval_prompt = f"""【シーンID】{scene_id}
【ナレーション】{narration}
【生成プロンプト】{prompt}

評価基準:
1. 時代・場所がナレーションおよびプロンプトと一致しているか
2. 人物描写（年齢・民族・服装）がプロンプトと一致しているか
3. 人物の体格（痩せ型/標準/太め等）がプロンプトの記述と一致しているか。thin build/slender と指定されているのに太めに描かれている場合はFAIL
4. oil painting style / academic realism の雰囲気が出ているか
5. 構図指示（portrait/wide shot/medium shot等）が守られているか

注意: 「実在の人物に似ているか」は評価しないでください。人物の正確な外見はWikimedia写真で対応するため、ここではプロンプトの指示（年齢・民族・服装・体格等）との一致のみを評価します。

JSONのみ（```なし）で回答:
{{
  "passed": true | false,
  "issues": ["問題点1（日本語）", "問題点2"],
  "feedback": "プロンプト改善のための具体的なアドバイス（英語、1〜3文）",
  "positive": "良い点（日本語、1文）"
}}

passedはすべての基準を概ね満たす場合のみtrue。
issuesがない場合は[]。"""

    # ── Primary: Claude Code CLI ──────────────────────────────
    response_text = _call_claude_vision(image_path, eval_prompt)

    if response_text:
        try:
            text = response_text.strip()
            if "```" in text:
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                if m:
                    text = m.group(1)
            result = json.loads(text)
            return {
                "passed": result.get("passed", True),
                "issues": result.get("issues", []),
                "feedback": result.get("feedback", ""),
                "positive": result.get("positive", ""),
            }
        except (json.JSONDecodeError, Exception):
            # JSON解析失敗 → フォールバック
            pass

    # ── Fallback: Gemini Flash Vision ─────────────────────────
    return _evaluate_image_quality_gemini(client, image_path, prompt, narration, scene_id)


def _evaluate_image_quality_gemini(
    client, image_path: str, prompt: str, narration: str, scene_id: str
) -> dict:
    """Fallback: Evaluate using Gemini Flash Vision (original implementation)."""
    from PIL import Image

    try:
        img = Image.open(image_path)
        eval_prompt = f"""以下の画像を評価してください。

【シーンID】{scene_id}
【ナレーション】{narration}
【生成プロンプト】{prompt}

評価基準:
1. 時代・場所がナレーションおよびプロンプトと一致しているか
2. 人物描写（年齢・民族・服装）がプロンプトと一致しているか
3. 人物の体格（痩せ型/標準/太め等）がプロンプトの記述と一致しているか。thin build/slender と指定されているのに太めに描かれている場合はFAIL
4. oil painting style / academic realism の雰囲気が出ているか
5. 構図指示（portrait/wide shot/medium shot等）が守られているか

注意: 「実在の人物に似ているか」は評価しないでください。人物の正確な外見はWikimedia写真で対応するため、ここではプロンプトの指示（年齢・民族・服装・体格等）との一致のみを評価します。

JSONのみ（```なし）で回答:
{{
  "passed": true | false,
  "issues": ["問題点1（日本語）", "問題点2"],
  "feedback": "プロンプト改善のための具体的なアドバイス（英語、1〜3文）",
  "positive": "良い点（日本語、1文）"
}}

passedはすべての基準を概ね満たす場合のみtrue。
issuesがない場合は[]。"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, eval_prompt],
        )
        text = response.text.strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)
        result = json.loads(text)
        return {
            "passed": result.get("passed", True),
            "issues": result.get("issues", []),
            "feedback": result.get("feedback", ""),
            "positive": result.get("positive", ""),
        }
    except Exception as e:
        return {"passed": True, "issues": [], "feedback": "", "error": str(e)}


def _detect_prompt_gender(source_prompt: str) -> str:
    """Detect intended subject gender from the SOURCE prompt only.

    Must be called with the true, immutable source_prompt — never with an
    accumulated/strengthened prompt, otherwise feedback text containing
    "woman"/"female"/etc. can flip the detected gender.

    Returns "female" or "male" (defaults to "male" if unspecified).
    """
    p = source_prompt.lower()
    female_markers = (" woman", " female", " she ", " her ", " girl", "women")
    if any(m in p for m in female_markers):
        return "female"
    return "male"


def strengthen_prompt(
    current_prompt: str, feedback: str, issues: list, source_prompt: str = None
) -> str:
    """Strengthen the prompt based on evaluation feedback.

    Appends structured corrections to make regeneration more targeted.
    Does NOT call any API — pure string manipulation.

    Args:
        current_prompt: The prompt used in the just-failed attempt
            (may already contain corrections from earlier retries).
        feedback: Raw feedback text from Vision QA. NOT appended verbatim
            to avoid contaminating gender/identity detection on future
            iterations. Only used to extract structured corrections.
        issues: List of specific issue strings from Vision QA.
        source_prompt: The original, immutable source_prompt from
            scene_definition.json. Used for gender detection so that
            accumulated "woman"/"female" words in prior corrections
            cannot flip intended gender. If None, falls back to
            current_prompt (legacy behaviour).

    Returns:
        The strengthened prompt (current_prompt + structured corrections).
    """
    if not feedback and not issues:
        return current_prompt

    # Gender MUST be determined from the true source prompt, not from the
    # accumulated current_prompt which may contain feedback text like
    # "the image shows a woman" that flips detection on subsequent retries.
    gender_reference = source_prompt if source_prompt is not None else current_prompt
    intended_gender = _detect_prompt_gender(gender_reference)

    additions = []
    issues_joined = " ".join(issues)
    issues_lower = issues_joined.lower()

    # NOTE: raw feedback text is intentionally NOT appended to the prompt.
    # Prior behaviour was to append f"IMPORTANT CORRECTION: {feedback}"
    # which caused prompt pollution — QA feedback sentences containing
    # words like "woman"/"Japanese"/"modern" would be re-parsed on the
    # next retry and trigger opposite corrections. Structured rules below
    # are applied instead.

    if "現代" in issues_joined or "modern" in issues_lower:
        additions.append(
            "strictly historical setting, NO modern elements, NO contemporary clothing"
        )

    # Gender correction — always bind to source prompt's intended gender.
    gender_flagged = (
        "女性" in issues_joined
        or "female" in issues_lower
        or "woman" in issues_lower
        or "男性" in issues_joined
        or ("male" in issues_lower and "female" not in issues_lower)
        or ("man" in issues_lower and "woman" not in issues_lower)
    )
    if gender_flagged:
        if intended_gender == "female":
            additions.append("the subject must be female, a woman")
        else:
            additions.append("the subject must be male, a man")

    if "若" in issues_joined or "young" in issues_lower:
        additions.append("the subject is elderly, aged 60-85, with white or grey hair")
    if "アジア" in issues_joined or "asian" in issues_lower:
        additions.append("Eastern European appearance, NOT Asian features")
    if "油絵" in issues_joined or "painting style" in issues_lower:
        additions.append("must be rendered in oil painting style, NOT photorealistic")
    if "色" in issues_joined or "colorful" in issues_lower or "鮮やか" in issues_joined:
        additions.append(
            "muted, period-appropriate color palette, NOT oversaturated or vivid colors"
        )
    if "建物" in issues_joined or "building" in issues_lower or "背景" in issues_joined:
        additions.append("background must match the historical period, NO modern architecture")

    if not additions:
        return current_prompt

    # Deduplicate: if a correction is already present verbatim, skip it.
    unique_additions = [a for a in additions if a not in current_prompt]
    if not unique_additions:
        return current_prompt

    strengthened = current_prompt.rstrip(".")
    strengthened += ". " + " ".join(unique_additions)
    return strengthened


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------
def generate_all(
    scene_def: dict,
    images_dir: str,
    backend: str,
    target_scene: str = None,
    force: bool = False,
    regen: bool = False,
    qa_eval: bool = True,
    qa_max_retries: int = 2,
    birth_year: int = None,
    appearance: str = "",
    cliche_llm_review: bool = False,
    subject_en: str = "",
):
    """Generate all missing images.

    Args:
        regen:         If True, also regenerate existing non-kept images.
        force:         If True, regenerate ALL images including kept ones.
        qa_eval:       If True, evaluate each image after generation and retry
                       if quality check fails (uses Gemini Flash Vision, free).
        qa_max_retries: Max number of QA-driven regeneration attempts (default 2).
        birth_year:    Birth year of the subject. Enables reference-based
                       age-aware generation using Wikimedia photos as identity anchor.
        cliche_llm_review:. If True, run Layer 2 LLM-based cliche
                           review (Claude Sonnet) in addition to the always-on
                           Layer 1 dictionary scan.
    """
    os.makedirs(images_dir, exist_ok=True)
    tasks = extract_image_tasks(scene_def, images_dir)

    # 強化 A: source_prompt staleness 判定用 meta をロード。
    image_meta = _load_image_meta(images_dir)

    # cliche scanner: scan all source_prompts for unverified
    # period stereotypes BEFORE expensive image generation. WARN-only —
    # generation still proceeds. Layer 1 (dictionary) is always on; Layer 2
    # (LLM review) is opt-in via --cliche-llm-review.
    try:
        from cliche_scanner import scan_tasks as _cliche_scan_tasks

        cliche_report = _cliche_scan_tasks(tasks, llm_review=cliche_llm_review)
        if cliche_report.findings:
            print(
                f"\n[cliche_scanner] {cliche_report.scenes_with_findings}/"
                f"{cliche_report.scenes_scanned} scenes flagged "
                f"({cliche_report.layer1_hits} dict, "
                f"{cliche_report.layer2_hits} llm). Review below; if a flagged"
                f" term is historically verified for that scene, opt-out via "
                f"visual.cliche_acks in scene_definition.json."
            )
            for f in cliche_report.findings:
                print(f.format())
            print()
    except ImportError:
        print("  [WARN] cliche_scanner unavailable — skipping cliche scan")
    except Exception as e:
        print(f"  [WARN] cliche_scanner failed: {e}")

    # Filter tasks
    to_generate = []
    skipped_kept = 0
    for t in tasks:
        if target_scene and t["scene_id"] != target_scene:
            continue
        if t["status"] == "no_prompt":
            print(f"  [WARN] {t['scene_id']}: no prompt defined, skipping")
            continue

        # Respect .keep unless --force
        if t.get("kept", False) and not force:
            if t["status"] == "exists":
                skipped_kept += 1
                continue

        if t["status"] == "exists":
            if force:
                pass  # regenerate
            elif regen:
                pass  # regenerate non-kept (kept already filtered above)
            else:
                # 強化 A: source_prompt staleness 判定。
                # meta に記録があり fingerprint 不一致なら source_prompt 等が
                # 変更された → 自動再生成 (手動 png 削除を不要に)。
                # meta 記録が無い (旧資産/初回) 場合は従来通りスキップ
                # (全既存画像の一斉再生成という破壊的挙動を避ける)。
                #
                # 強化: subject_appearance 変更も検出対象に。current_fp は
                # appearance 込み、legacy_fp は appearance 非対象。stored が
                # legacy_fp と一致するなら appearance 追跡前の旧 meta なので
                # stale 扱いにせず次回 save で migration (deploy 時の一斉再生成を
                # 回避)。どちらとも不一致なら source_prompt か subject_appearance
                # が実際に変更された → 自動再生成。
                sid = t["scene_id"]
                stored = image_meta.get(sid)
                current_fp = _prompt_fingerprint(t, appearance)
                legacy_fp = _prompt_fingerprint(t)
                if stored is not None and stored != current_fp and stored != legacy_fp:
                    print(
                        f"  [STALE] {sid}: source_prompt/subject_appearance 変更検出 "
                        f"→ 自動再生成 (手動 png 削除不要)"
                    )
                    # fall through to regenerate
                else:
                    continue  # skip existing in normal mode (unchanged)

        if t["prompt"]:
            to_generate.append(t)

    if skipped_kept:
        print(f"  [LOCK] Skipping {skipped_kept} curated image(s) (use --force to override)")

    if not to_generate:
        print("No images to generate.")
        return

    client = get_client()

    # ── Reference photo detection ─────────────────────────────
    ref_photos = _find_reference_photos(images_dir)
    use_reference = bool(ref_photos) and birth_year and backend == "flash"

    # misreading: reference photos may be FETCHED (wikimedia_fetcher, labelled
    # usage="reference") yet the global gate is OFF -- e.g. an ancient figure
    # with no birth_year, so `use_reference` above is False and NO photo is ever
    # passed to Gemini (images are text-only/imaginative). Record that ACTUAL
    # usage in wikimedia_credits.json so credits_generator does not falsely
    # credit them: a wrong CC BY-SA festival photo (mis-fetched for "Euclid of
    # Alexandria") slipped into ある回's public description this way.
    if ref_photos and not use_reference:
        _mark_reference_photos_unused(images_dir)

    # 各リファレンス写真の推定年齢を計算
    ref_photo_ages = {}
    if use_reference:
        for rp in ref_photos:
            fname = os.path.basename(rp)
            year_matches = re.findall(r"(?<!\d)(1[89]\d{2}|20[0-3]\d)(?!\d)", fname)
            if year_matches:
                ref_photo_ages[rp] = max(int(y) for y in year_matches) - birth_year
        print(f"  [PHOTO] Reference photos found: {len(ref_photos)}")
        for rp in ref_photos:
            age = ref_photo_ages.get(rp)
            age_str = f" (age ~{age})" if age else ""
            print(f"     {os.path.basename(rp)}{age_str}")
        print()

    backend_info = BACKENDS[backend]
    eval_label = f" + Vision QA (max {qa_max_retries} retries)" if qa_eval else ""
    ref_label = " + reference-based" if use_reference else ""
    appear_label = " + appearance" if use_reference and appearance else ""
    print(f"\nBackend: {backend_info['description']}{ref_label}{appear_label}{eval_label}")
    print(f"Model:   {backend_info['model']}")
    if appearance:
        print(f"Appearance: {appearance[:80]}{'...' if len(appearance) > 80 else ''}")
    print(f"\nGenerating {len(to_generate)} images...\n")

    success = 0
    failed = 0
    qa_improved = 0  # QAリトライで改善されたシーン数
    ref_used = 0  # リファレンス使用回数

    for i, t in enumerate(to_generate):
        scene_id = t["scene_id"]
        current_prompt = t["prompt"]
        narration = t.get("narration", "")
        output_path = t["img_path"]

        # no_human flag: append explicit "no people in scene"
        # suffix so Gemini Flash's bias toward populating scenes with people
        # is suppressed. Used for object-only or unclear-protagonist scenes (group shots
        # where the subject is unidentifiable, or pure object/place scenes).
        is_no_human_scene = t.get("no_human", False)
        if is_no_human_scene:
            # Issue 2 (s94 fix): log application so users can verify which
            # scenes were treated as no-human at runtime.
            print(f"  [no_human] {scene_id}: appending no-people suffix")
            current_prompt = (
                current_prompt.rstrip()
                + " no human figure visible, still life composition, no people in scene."
            )

        # ── Determine generation method ───────────────────────
        # Issue 1 (s94 fix): force has_person=False when no_human=true.
        # Otherwise detect_has_person() can match "man " inside "human "
        # in the appended suffix and falsely report a person, which would
        # corrupt the imagen-backend has_person flag (the flash path is
        # already protected by use_reference being forced false).
        if is_no_human_scene:
            has_person = False
        else:
            has_person = detect_has_person(current_prompt)
        target_age = None
        ref_path = None

        # Per-scene override: scenes can opt out of reference photos.
        # Used when the scene depicts a different historical figure
        # (e.g. Leibniz in a Seki episode) where using the main subject's
        # reference photo would cause identity contamination.
        # Also forced false when no_human=true (set in enumerate_image_tasks).
        scene_use_reference = t.get("use_reference", True)

        # 強化 B: subject mismatch guard。
        # subject_en 指定時は scene の prompt と subject 名を照合、別人物
        # scene なら use_reference を強制 false。
        if subject_en:
            decided, warn_msg = should_use_reference_photo_with_subject_guard(
                use_reference,
                has_person,
                scene_use_reference,
                current_prompt,
                subject_en,
                scene_id,
            )
            if warn_msg:
                print(warn_msg)
            ref_active = decided
        else:
            ref_active = should_use_reference_photo(use_reference, has_person, scene_use_reference)

        if ref_active:
            target_age = _estimate_scene_age(narration, birth_year, current_prompt)
            if target_age is not None:
                ref_path = _select_best_reference(ref_photos, target_age, ref_photo_ages)

        if ref_path and target_age is not None:
            ref_age = ref_photo_ages.get(ref_path)
            label = f"ref→age {target_age}"
            # Build age-aware reference prompt
            current_prompt = _build_reference_prompt(
                current_prompt, target_age, ref_age, appearance=appearance
            )
        elif backend == "imagen":
            label = "person" if has_person else "scene"
        else:
            label = "flash"

        # 強化 (a): 主題者シーンが参照写真を使わず text-only 生成された
        # 場合に警告。subject reference が存在し (global use_reference)、scene が
        # 主題者の人物シーン (use_reference=true, is_subject=true, not no_human)
        # なのに参照が使われなかった (ref_active False か age 推定失敗) → has_person
        # keyword miss 等で「理想化された別人」が生成されるリスク。guard demote で
        # 主因は解消したが残存経路を可視化する safety net。誤検出時は is_subject=false / no_human=true を明示。
        ref_was_used = bool(ref_path and target_age is not None)
        if (
            use_reference
            and t.get("use_reference", True)
            and t.get("is_subject", True)
            and not is_no_human_scene
            and not ref_was_used
        ):
            if not has_person:
                cause = "has_person=False (人物描写語が source_prompt に無い)"
            elif target_age is None:
                cause = "age 推定不可 (narration/prompt から年齢を取れず)"
            else:
                cause = "ref 写真選択不可"
            print(
                f"  [WARN] {scene_id}: 主題者シーンだが参照写真を使わず "
                f"text-only 生成 ({cause}) -> 理想化リスク。"
                f"脇役/人物なし scene なら is_subject=false か no_human=true を"
                f"明示、主題者なら source_prompt に人物描写を補う"
            )

        print(f"  [{i + 1}/{len(to_generate)}] {scene_id} ({label})...")

        # ── 生成 → 評価 → リトライ ループ ──────────────────────
        final_ok = False
        for attempt in range(qa_max_retries + 1):
            attempt_label = f"attempt {attempt + 1}" if attempt > 0 else "initial"
            if attempt > 0:
                print(f"    [RETRY] QA retry ({attempt_label}): strengthening prompt...")

            # Choose generation method
            if ref_path and target_age is not None:
                ok = generate_image_with_reference(client, ref_path, current_prompt, output_path)
                if ok and attempt == 0:
                    ref_used += 1
            elif backend == "flash":
                ok = generate_image_flash(client, current_prompt, output_path)
            else:
                ok = generate_image_imagen(
                    client,
                    current_prompt,
                    output_path,
                    has_person=detect_has_person(current_prompt),
                )

            if not ok:
                print(f"    [NG] Generation failed ({attempt_label})")
                if ref_path and attempt == 0:
                    # Reference generation failed → fall back to normal flash
                    print("    [RETRY] Falling back to standard flash generation...")
                    ref_path = None
                    current_prompt = t["prompt"]  # Reset to original prompt
                if attempt < qa_max_retries:
                    time.sleep(2)
                continue  # 生成失敗はQA評価せず次のattemptへ

            size_kb = os.path.getsize(output_path) / 1024

            # QA評価スキップ（無効化または最終attempt）
            if not qa_eval or attempt == qa_max_retries:
                print(f"    [OK] Saved ({size_kb:.0f} KB)")
                final_ok = True
                break

            # ── Vision評価 ─────────────────────────────────────
            print("    [EVAL] Evaluating...", end=" ", flush=True)
            eval_result = evaluate_image_quality(
                client, output_path, current_prompt, narration, scene_id
            )

            if eval_result.get("error"):
                # 評価エラーは無視して続行
                print(f"[WARN] eval error ({eval_result['error'][:50]}), keeping image")
                final_ok = True
                break

            passed = eval_result.get("passed", True)
            issues = eval_result.get("issues", [])
            positive = eval_result.get("positive", "")

            if passed:
                print(f"[OK] passed ({size_kb:.0f} KB)")
                if positive:
                    try:
                        print(f"    [NOTE] {positive}")
                    except UnicodeEncodeError:
                        print(
                            f"    [NOTE] {positive.encode('ascii', errors='replace').decode('ascii')}"
                        )
                final_ok = True
                break
            else:
                print("[WARN] failed")
                for issue in issues:
                    try:
                        print(f"    [!] {issue}")
                    except UnicodeEncodeError:
                        print(f"    [!] {issue.encode('ascii', errors='replace').decode('ascii')}")
                if attempt < qa_max_retries:
                    # プロンプトを強化して次のattemptへ
                    # source_prompt=t["prompt"] で性別判定をブレさせない
                    current_prompt = strengthen_prompt(
                        current_prompt,
                        eval_result.get("feedback", ""),
                        issues,
                        source_prompt=t["prompt"],
                    )
                    qa_improved += 1
                    time.sleep(1)
                else:
                    # リトライ上限に達した場合は現在の画像を採用
                    print(f"    [WARN] Max retries reached, keeping best result ({size_kb:.0f} KB)")
                    final_ok = True

        if final_ok:
            success += 1
            # 強化 A: 生成成功時に有効 prompt の fingerprint を記録。
            # 次回ビルドで source_prompt 変更を検出して自動再生成する。
            # 強化: appearance 込みで記録 (subject_appearance 変更検出用、
            # 旧 meta を current_fp に migration)。
            image_meta[scene_id] = _prompt_fingerprint(t, appearance)
            _save_image_meta(images_dir, image_meta)
        else:
            failed += 1

        # Rate limiting between scenes
        if i < len(to_generate) - 1:
            time.sleep(1)

    print(f"\n{'=' * 40}")
    print(f"  Generated: {success}")
    if ref_used:
        print(f"  Reference-based: {ref_used} scene(s)")
    if qa_improved:
        print(f"  QA improved: {qa_improved} scene(s) retried")
    if failed:
        print(f"  Failed:    {failed}")
    print(f"  Output:    {images_dir}")

    _suggest_source_updates(scene_def, tasks, to_generate)


def _suggest_source_updates(scene_def: dict, tasks: list, generated: list):
    """Suggest source field updates for scenes that had auto-named images."""
    updates = []
    for t in generated:
        for section in scene_def["sections"]:
            for scene in section["scenes"]:
                if scene["scene_id"] == t["scene_id"]:
                    v = scene["visual"]
                    if not v.get("source") and os.path.exists(t["img_path"]):
                        updates.append((t["scene_id"], t["source"]))

    if updates:
        print("\n  [TIP] Add 'source' to scene_definition.json for auto-named images:")
        for scene_id, source in updates:
            print(f'     {scene_id}: "source": "{source}"')


def export_prompts(scene_def: dict, images_dir: str, output_file: str):
    """Export prompts to a text file for manual generation in Gemini chat."""
    tasks = extract_image_tasks(scene_def, images_dir)
    needed = [t for t in tasks if t["status"] in ("needed", "missing_file") and t["prompt"]]
    copy_needed = [t for t in tasks if t["status"] == "missing_file" and not t["prompt"]]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 画像生成プロンプト一覧\n")
        f.write("# Generated from scene_definition.json\n")
        f.write(f"# {len(needed)} images to generate\n\n")

        for t in needed:
            f.write(f"## {t['scene_id']} → {t['source']}\n\n")
            f.write(f"{t['prompt']}\n\n")
            f.write("---\n\n")

        if copy_needed:
            f.write("# --- Copy from Phase 0 (no prompt) ---\n\n")
            for t in copy_needed:
                f.write(f"# {t['scene_id']} → {t['source']}  (copy to images/ directory)\n")

    print(f"Exported {len(needed)} prompts to {output_file}")
    if copy_needed:
        unique_files = sorted(set(t["source"] for t in copy_needed))
        print(
            f"  Note: {len(unique_files)} image(s) need manual copy from Phase 0:"
            f" {', '.join(unique_files)}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generate images for ken_burns scenes via Gemini API"
    )
    parser.add_argument("scene_json", help="Path to scene_definition.json")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Episode output directory (images saved to {output_dir}/images/)",
    )
    parser.add_argument("--list", action="store_true", help="List image tasks without generating")
    parser.add_argument(
        "--generate", action="store_true", help="Generate missing images via Gemini API"
    )
    parser.add_argument("--scene", default=None, help="Generate only for this scene_id")
    parser.add_argument(
        "--force", action="store_true", help="Regenerate ALL images including curated ones"
    )
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate existing non-curated images (use with --generate)",
    )
    parser.add_argument(
        "--backend",
        default=None,
        choices=["flash", "imagen"],
        help="Image backend: flash (free) or imagen (paid)."
        " Default: flash. Override with IMAGE_BACKEND env var",
    )
    parser.add_argument(
        "--export-prompts",
        default=None,
        metavar="FILE",
        help="Export prompts to text file for manual generation",
    )
    parser.add_argument(
        "--no-qa-eval",
        action="store_true",
        help="Disable Vision QA evaluation after generation"
        " (faster, but no quality feedback or retry)",
    )
    parser.add_argument(
        "--qa-retries",
        type=int,
        default=4,
        help="Max QA-driven regeneration retries per scene (default: 4)",
    )
    parser.add_argument(
        "--keep",
        default=None,
        metavar="SCENE_IDS",
        help="Mark scene_ids as curated (comma-separated). Protected from --regen",
    )
    parser.add_argument(
        "--unkeep",
        default=None,
        metavar="SCENE_IDS",
        help="Remove scene_ids from curated list (comma-separated)",
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="CONFIG_JSON",
        help="Path to episode_config.json. Enables reference-based"
        " age-aware generation using Wikimedia photos."
        " (auto-detected if not specified)",
    )
    parser.add_argument(
        "--no-appearance",
        action="store_true",
        help="Disable subject_appearance injection into reference prompts (for A/B comparison)",
    )
    parser.add_argument(
        "--cliche-llm-review",
        action="store_true",
        help="Run Layer 2 LLM-based cliche review"
        " (Claude Sonnet) in addition to the always-on dictionary scan."
        " Default: off. Cost: 0 (Max subscription).",
    )
    args = parser.parse_args()

    # Load .env BEFORE reading env vars
    _load_dotenv()

    # Determine backend: CLI flag > env var > default
    backend = args.backend or os.environ.get("IMAGE_BACKEND", "flash")

    # Load scene definition
    with open(args.scene_json, encoding="utf-8") as f:
        scene_def = json.load(f)

    images_dir = os.path.join(args.output_dir, "images")

    # Extract birth_year from config if available
    birth_year = None
    config_path = args.config
    if not config_path:
        # Auto-detect: look for episode_config.json in output_dir
        auto_path = os.path.join(args.output_dir, "episode_config.json")
        if os.path.exists(auto_path):
            config_path = auto_path
    if config_path and os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        # Extract birth year
        if config.get("birth_year"):
            birth_year = int(config["birth_year"])
        elif isinstance(config.get("verified_facts"), dict):
            # support both legacy str and new {fact, source} dict.
            from config_validator import get_verified_fact_text

            birth_str = get_verified_fact_text(config["verified_facts"].get("birth", ""))
            if birth_str:
                m = re.search(r"(1[89]\d{2}|20[0-3]\d)", birth_str)
                if m:
                    birth_year = int(m.group(1))

    # Extract appearance description (for identity consistency)
    appearance = ""
    subject_en = ""
    if config_path and os.path.exists(config_path):
        if not args.no_appearance:
            appearance = config.get("subject_appearance", "")
        else:
            print("  [INFO] Appearance injection disabled (--no-appearance)")
        # 強化 B: subject_en for non-subject-person guard
        subject_en = config.get("subject_en") or config.get("mathematician", "")

    # Handle --keep / --unkeep commands
    if args.keep:
        scene_ids = [s.strip() for s in args.keep.split(",")]
        added = add_to_keep(images_dir, scene_ids)
        if added:
            print(f"[LOCK] Marked as curated: {', '.join(added)}")
        else:
            print("All specified scene_ids were already curated.")
        kept = load_keep_list(images_dir)
        print(f"   Total curated: {len(kept)} images")
        return

    if args.unkeep:
        scene_ids = [s.strip() for s in args.unkeep.split(",")]
        removed = remove_from_keep(images_dir, scene_ids)
        if removed:
            print(f"[UNLOCK] Removed from curated: {', '.join(removed)}")
        else:
            print("None of the specified scene_ids were curated.")
        kept = load_keep_list(images_dir)
        print(f"   Total curated: {len(kept)} images")
        return

    if args.export_prompts:
        export_prompts(scene_def, images_dir, args.export_prompts)
    elif args.generate:
        generate_all(
            scene_def,
            images_dir,
            backend,
            target_scene=args.scene,
            force=args.force,
            regen=args.regen,
            qa_eval=not args.no_qa_eval,
            qa_max_retries=args.qa_retries,
            birth_year=birth_year,
            appearance=appearance,
            cliche_llm_review=args.cliche_llm_review,
            subject_en=subject_en,
        )
    else:
        # Default: list mode
        tasks = extract_image_tasks(scene_def, images_dir)
        list_tasks(tasks)
        # Issue 3: also run cliche scan in --list mode so
        # users can verify source_prompt cliches without committing to a
        # full --generate (which costs API time + Vision QA retries).
        try:
            from cliche_scanner import scan_tasks as _cliche_scan_tasks

            cliche_report = _cliche_scan_tasks(tasks, llm_review=args.cliche_llm_review)
            if cliche_report.findings:
                print(
                    f"\n[cliche_scanner] {cliche_report.scenes_with_findings}/"
                    f"{cliche_report.scenes_scanned} scenes flagged "
                    f"({cliche_report.layer1_hits} dict, "
                    f"{cliche_report.layer2_hits} llm). "
                    f"Use visual.cliche_acks to opt-out verified terms."
                )
                for f in cliche_report.findings:
                    print(f.format())
        except ImportError:
            pass  # cliche_scanner unavailable — silent in list mode
        except Exception as e:
            print(f"\n  [WARN] cliche_scanner failed: {e}")


if __name__ == "__main__":
    main()
    # ③ advisory roll-up: surface the fail-loud "references exist but none usable"
    # backstop to the pipeline final summary via the X3 stderr channel (no-op unless
    # run under the pipeline with hits). Mirrors visual_generator's DEAD-AIR roll-up.
    if _REF_TEXTONLY_HITS:
        try:
            import pipeline_log

            pipeline_log.emit_stderr_warn_summary("images", _REF_TEXTONLY_HITS)
        except Exception:
            pass
