"""Quick baseline check — verify episode artifacts match recorded baseline.

Usage:
    python scripts/quick_baseline_check.py <episode_dir> <baseline_json>

Example:
    python scripts/quick_baseline_check.py episodes/020_abel docs/internal/baselines/ep020.json

Compares SHA256 hashes of episode artifacts (audio/, visuals/, key files) against
the recorded baseline. Reports PASS / FAIL with detailed diff for any mismatches.

Designed for fast layer-A verification during refactor commits.
For full structural / quality verification, use the dedicated verify_*.py scripts
.
"""

import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_category(episode_dir: Path, category: str, expected: dict) -> tuple[int, int, list]:
    """Check a category (audio / visuals / images / thumbnails / key_files).

    Returns (pass_count, fail_count, fail_details).
    """
    cat_dir = episode_dir / category if category != "key_files" else episode_dir
    pass_count = 0
    fail_count = 0
    failures = []

    for filename, expected_hash in expected.items():
        if category == "key_files":
            file_path = episode_dir / filename
            actual_hash = (
                expected_hash["sha256"] if isinstance(expected_hash, dict) else expected_hash
            )
        else:
            file_path = cat_dir / filename
            actual_hash = expected_hash

        if not file_path.exists():
            fail_count += 1
            failures.append(f"  [MISSING] {category}/{filename}")
            continue

        actual = sha256_file(file_path)
        # For key_files, expected_hash is a dict {sha256, size}
        expected_str = expected_hash["sha256"] if isinstance(expected_hash, dict) else expected_hash

        if actual == expected_str:
            pass_count += 1
        else:
            fail_count += 1
            failures.append(
                f"  [DIFF] {category}/{filename}\n"
                f"        expected: {expected_str[:32]}...\n"
                f"        actual:   {actual[:32]}..."
            )

    return pass_count, fail_count, failures


def main():
    if len(sys.argv) < 3:
        print("Usage: quick_baseline_check.py <episode_dir> <baseline_json>", file=sys.stderr)
        return 2

    episode_dir = Path(sys.argv[1])
    baseline_path = Path(sys.argv[2])

    if not episode_dir.exists():
        print(f"ERROR: episode dir not found: {episode_dir}", file=sys.stderr)
        return 2

    if not baseline_path.exists():
        print(f"ERROR: baseline json not found: {baseline_path}", file=sys.stderr)
        return 2

    with open(baseline_path, encoding="utf-8") as f:
        baseline = json.load(f)

    print("Quick baseline check")
    print(f"  Episode:  {episode_dir}")
    print(f"  Baseline: {baseline_path}")
    print()

    total_pass = 0
    total_fail = 0
    all_failures = []

    for category in ["key_files", "audio", "visuals", "images", "thumbnails"]:
        expected = baseline.get("hashes", {}).get(category, {})
        if not expected:
            print(f"  {category}: (no baseline data, skipped)")
            continue

        p, f, failures = check_category(episode_dir, category, expected)
        total_pass += p
        total_fail += f
        all_failures.extend(failures)
        status = "OK" if f == 0 else f"FAIL ({f} mismatch)"
        print(f"  {category}: {p}/{p + f} {status}")

    print()
    print("=" * 50)
    if total_fail == 0:
        print(f"PASS  ({total_pass} files match baseline)")
        return 0
    else:
        print(f"FAIL  ({total_fail} mismatch out of {total_pass + total_fail})")
        print()
        for failure in all_failures[:20]:
            print(failure)
        if len(all_failures) > 20:
            print(f"  ... and {len(all_failures) - 20} more")
        return 1


if __name__ == "__main__":
    sys.exit(main())
