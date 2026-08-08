"""Repository hygiene checks: work that is about to be lost, or quietly corrupted.

Two failure classes, both hit for real on 2026-08-05 while merging an earlier episode
pipeline hardening:

**A. Work stranded in a worktree.** Four parallel sessions produced hardening;
three had committed, the fourth had not. It was reported as "all four merged"
because `git branch --merged` listed its branch. That command answers "is this
branch's tip an ancestor of HEAD", and the tip of a branch nobody committed to is
still the base commit -- so a session that wrote code and never committed always
looks merged. The only honest answer comes from the worktree's own status.
Sweeping every worktree afterwards found **eight** holding uncommitted pipeline
code, some based three months behind trunk.

Staleness matters on its own: a worktree 300 commits behind has a `src/` without
the checks added since, so anything measured inside it is measured against code
that no longer exists. The session that triggered this was 304 commits behind and
was saved only by its shell happening to run in the main tree.

**B. A file's line endings flipped wholesale.** Editing a UTF-8 document with
Python's *text* mode on Windows rewrites every LF as CRLF, so a two-line edit
lands as a hundred-line diff. This repository deliberately does NOT normalise
line endings (measured 2026-08-05: .py is 260/261 LF, but .json is 313/345 and
.txt 148/156 CRLF, because the pipeline writes them on Windows), so a blanket
`.gitattributes` rule would renormalise 500+ files and fight every build. What
is safe to pin is pinned there; everything else is watched here.

Both checks are advisory: an in-progress session legitimately has uncommitted
work. They exist so the state is *visible* before someone declares a merge done.
"""

from __future__ import annotations

import os
import subprocess

# The long-lived integration branch (memory: project_trunk_branch -- origin/main
# is far behind and diffing against it produces a useless wall of changes).
DEFAULT_TRUNK = "refactor/m1-quality-improvements"

# What counts as "work that would be lost", split by tracked vs untracked rather
# than by directory.
#
# The first version of this scoped the whole scan to src/ and scripts/, reasoning
# that scratch elsewhere is deliberate. It reported zero while six worktrees held
# uncommitted edits -- among them a wrap-up session's changes to the repo's own
# top-level documentation. Those are not scratch.
#
# The distinction that actually holds:
#   - a MODIFIED TRACKED file, anywhere, is edited work -- somebody changed a
#     versioned file and did not commit it
#   - an UNTRACKED file is usually output: .bak snapshots, qa_report_*.json,
#     prototypes/, .claude/plans/. Worth reporting only under the pipeline dirs,
#     where a new file is more likely to be new code than an artefact.
PIPELINE_PATHS = ("src", "scripts")

# Untracked paths that are artefacts even inside the pipeline dirs.
_ARTEFACT_MARKERS = ("__pycache__", ".bak", ".pyc")

# A worktree this far behind trunk is measuring against code that has moved on.
STALE_COMMITS = 50


def _run_git(args: list[str], cwd: str | None = None) -> str:
    """Run git and return stdout, or "" if the command fails.

    Failures are expected here (a worktree directory can be deleted while git
    still lists it), so they degrade to "" rather than raising.

    That degradation is only safe where "" and "nothing found" mean the same
    thing. They do not for the trunk comparison -- a trunk that does not resolve
    makes every rev-list return "", which reads as "nothing unmerged" -- so
    scan_worktrees checks the trunk up front instead of inferring it from a
    blank. (This docstring used to promise `git_error` findings in the report;
    no such finding was ever emitted, so the failures it described were exactly
    as silent as it claimed they were not.)
    """
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout.decode("utf-8", errors="replace")


def _parse_worktree_list(porcelain: str) -> list[dict]:
    """Parse `git worktree list --porcelain` into [{path, head, branch}]."""
    entries, cur = [], {}
    for line in porcelain.splitlines():
        if line.startswith("worktree "):
            if cur:
                entries.append(cur)
            cur = {"path": line[len("worktree ") :], "head": "", "branch": ""}
        elif line.startswith("HEAD "):
            cur["head"] = line[len("HEAD ") :]
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch ") :].replace("refs/heads/", "")
    if cur:
        entries.append(cur)
    return entries


def _count_pipeline_changes(status_porcelain: str) -> tuple[int, int]:
    """Split `git status --porcelain` output into (modified tracked, new code).

    Returns two counts because they mean different things:

    - **modified tracked, any path** -- somebody edited a versioned file and did
      not commit it. Always work.
    - **untracked under src/ or scripts/** -- probably a new module. Untracked
      files elsewhere (.bak, qa_report_*.json, prototypes/, .claude/plans/) are
      output and are not counted; neither are __pycache__ and .pyc anywhere.
    """
    modified = new_code = 0
    for line in status_porcelain.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:].strip().strip('"')
        if not path or any(marker in path for marker in _ARTEFACT_MARKERS):
            continue
        if code.strip() == "??":
            if path.startswith(tuple(p + "/" for p in PIPELINE_PATHS)):
                new_code += 1
        else:
            modified += 1
    return modified, new_code


def scan_worktrees(
    repo_root: str = ".",
    trunk: str = DEFAULT_TRUNK,
    run_git=None,
) -> list[dict]:
    """Find worktrees holding work that is not in trunk.

    Args:
        repo_root: main working tree (its own entry is skipped)
        trunk: branch the work is meant to land on
        run_git: injected for tests -- called as run_git(args, cwd)

    Returns:
        [{"kind", "worktree", "branch", "uncommitted", "unmerged", "behind",
          "summary"}], one per worktree with something at risk.
    """
    git = run_git or _run_git
    findings = []

    entries = _parse_worktree_list(git(["worktree", "list", "--porcelain"], repo_root))
    root = os.path.normcase(os.path.abspath(repo_root))

    # DEFAULT_TRUNK names THIS repo's integration branch, so anyone who clones the
    # published copy and runs the tool compares against a branch they do not have.
    # git then fails, rev-list yields "", unmerged becomes 0, and a worktree whose
    # only risk is unpushed commits is dropped by the `not uncommitted and not
    # unmerged` guard below -- reported as an all-clear. Establish once whether the
    # comparison is even possible, and say so when it is not.
    trunk_ok = bool(git(["rev-parse", "--verify", "--quiet", f"{trunk}^{{commit}}"], repo_root))
    if not trunk_ok:
        findings.append(
            {
                "kind": "trunk_missing",
                "worktree": repo_root,
                "branch": trunk,
                "uncommitted": 0,
                "unmerged": 0,
                "behind": 0,
                "summary": f"trunk '{trunk}' がこのリポジトリで解決できません",
            }
        )

    for e in entries:
        path = e["path"]
        if os.path.normcase(os.path.abspath(path)) == root:
            continue

        # Status over the WHOLE tree, not just the pipeline dirs: the scoping
        # that used to live here is now inside _count_pipeline_changes, which
        # separates edited tracked files (anywhere) from new files (code dirs).
        modified, new_code = _count_pipeline_changes(git(["status", "--porcelain"], path))
        uncommitted = modified + new_code
        # Commits the worktree has that trunk does not. Distinct from
        # uncommitted work: this IS visible to `git branch --merged`, but it is
        # the same question ("is this landed?") and cheap to answer here.
        # Skipped entirely when the trunk does not resolve: asking would only turn
        # git's failure into a 0 that is indistinguishable from a real answer.
        unmerged_raw = (
            git(["rev-list", "--count", f"{trunk}..HEAD"], path).strip() if trunk_ok else ""
        )
        behind_raw = (
            git(["rev-list", "--count", f"HEAD..{trunk}"], path).strip() if trunk_ok else ""
        )
        unmerged = int(unmerged_raw) if unmerged_raw.isdigit() else 0
        behind = int(behind_raw) if behind_raw.isdigit() else 0

        # Uncommitted work is still measurable without a trunk, so it is still
        # reported. The unmerged half is not, and the trunk_missing finding above
        # is where that is said -- once, rather than by listing every worktree as
        # suspect, which would be a warning that fires on a healthy repo.
        if not uncommitted and not unmerged:
            continue

        bits = []
        if modified:
            bits.append(f"追跡ファイル {modified} 件が未コミット")
        if new_code:
            bits.append(f"{'/'.join(PIPELINE_PATHS)} に未追跡 {new_code} 件")
        if unmerged:
            bits.append(f"{unmerged} commit(s) not in {trunk}")
        stale = f"、HEAD は trunk から {behind} commit 遅れ" if behind >= STALE_COMMITS else ""

        findings.append(
            {
                "kind": "worktree",
                "worktree": os.path.basename(path.rstrip("/\\")),
                "path": path,
                "branch": e["branch"],
                "uncommitted": uncommitted,
                "modified": modified,
                "new_code": new_code,
                "unmerged": unmerged,
                "behind": behind,
                "summary": (f"{os.path.basename(path.rstrip('/'))}: {'; '.join(bits)}{stale}"),
            }
        )
    return findings


def check_eol_flips(repo_root: str = ".", run_git=None) -> list[dict]:
    """Find tracked files whose working-tree line endings differ from the index.

    `git ls-files --eol` prints `i/<index> w/<worktree> attr/<attrs> <path>`.
    With normalisation off, those two agree unless something rewrote the file
    with different line endings -- which is exactly the Python text-mode write
    that turned a 2-line documentation edit into a 110-line diff.
    """
    git = run_git or _run_git
    findings = []
    for line in git(["ls-files", "--eol"], repo_root).splitlines():
        # Format: "i/<eol>\tw/<eol>\tattr/<attrs>\t<path>", but the fields are
        # space-padded AND the attr field can itself contain spaces
        # ("attr/text eol=lf"), so the path must be taken after the last TAB --
        # splitting on whitespace puts half the attributes into the filename.
        head, sep, path = line.rpartition("\t")
        if not sep:
            continue
        fields = head.split()
        if len(fields) < 2:
            continue
        i_eol = fields[0].removeprefix("i/")
        w_eol = fields[1].removeprefix("w/")
        path = path.strip()
        if i_eol in ("lf", "crlf") and w_eol in ("lf", "crlf") and i_eol != w_eol:
            findings.append(
                {
                    "kind": "eol_flip",
                    "path": path,
                    "index": i_eol,
                    "worktree": w_eol,
                    "summary": (
                        f"{path}: 行末が index の {i_eol.upper()} に対し作業ツリーは "
                        f"{w_eol.upper()} -- 全行が変更として現れる"
                    ),
                }
            )
    return findings


def format_report(findings: list[dict]) -> str:
    """Render findings for a console. Empty list renders as the all-clear line."""
    if not findings:
        return "  OK: 未コミットの取り残しなし / 行末の反転なし"

    wt = [f for f in findings if f["kind"] == "worktree"]
    eol = [f for f in findings if f["kind"] == "eol_flip"]
    trunk_missing = [f for f in findings if f["kind"] == "trunk_missing"]
    lines = []
    # Rendered first, and deliberately not as a WARN among the others: it says the
    # worktree half of this report is not a result at all. A finding kind with no
    # branch here would be collected and then never printed, which is the same
    # silence the check was added to break.
    for f in trunk_missing:
        lines.append(f"  WARN: {f['summary']}")
        lines.append(
            "    -> 未マージ commit の判定は行えません。"
            "`--trunk <branch>` で統合ブランチを指定してください "
            "(既定値はこのパイプラインの開発リポジトリのものです)"
        )
    if wt:
        lines.append(f"  WARN: {len(wt)} worktree に trunk へ入っていない作業があります")
        for f in wt:
            lines.append(f"    {f['summary']}")
        lines.append(
            "    -> そのセッションが作業中なら正常。完了扱いにする前に、"
            "worktree で commit したか確認してください "
            "(`git branch --merged` は未コミットのブランチも「マージ済み」と表示します)"
        )
    if eol:
        lines.append(f"  WARN: {len(eol)} ファイルの行末が index と食い違っています")
        for f in eol:
            lines.append(f"    {f['summary']}")
        lines.append(
            "    -> 日本語ファイルを Python で書き換えるときは "
            'io.open(p, "rb") / "wb" のバイト単位で扱ってください '
            "(テキストモードは LF を CRLF に変換します)"
        )
    return "\n".join(lines)


def run_all(repo_root: str = ".", trunk: str = DEFAULT_TRUNK, run_git=None) -> list[dict]:
    """Both checks, in one list. This is what callers wire up."""
    return scan_worktrees(repo_root, trunk, run_git) + check_eol_flips(repo_root, run_git)
