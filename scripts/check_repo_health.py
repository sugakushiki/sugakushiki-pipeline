#!/usr/bin/env python3
"""CLI for the repository hygiene checks in src/repo_health.py.

Run this before declaring parallel work merged, or whenever a session ends:

    python scripts/check_repo_health.py            # advisory, exit 0
    python scripts/check_repo_health.py --strict   # exit 1 if anything is found

Also runs inside smoke_test.py (section 22) so it cannot rot unnoticed.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from repo_health import DEFAULT_TRUNK, format_report, run_all  # noqa: E402


def main() -> int:
    # Findings quote file paths that routinely contain kanji; the Windows console
    # codepage cannot encode them and would crash the reporter (smoke section 20).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".", help="main working tree (default: cwd)")
    ap.add_argument(
        "--trunk", default=DEFAULT_TRUNK, help=f"integration branch (default: {DEFAULT_TRUNK})"
    )
    ap.add_argument("--strict", action="store_true", help="exit 1 when findings exist")
    args = ap.parse_args()

    findings = run_all(args.repo_root, args.trunk)
    print(format_report(findings))
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
