"""Pull `main` from a clean worktree and refresh graphify only when HEAD moves.

Implements ADR 0014: refuse to pull when the current branch is not main or the
worktree is dirty, pull with `git pull --ff-only`, and run `task graphify:update`
only when the pull succeeds and HEAD changed. A failed graphify update is
reported with a non-zero exit without rolling back the pull.
"""

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    return REPOSITORY_ROOT


def current_branch(root: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def status_porcelain(root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def guard_error(branch: str, status_output: str) -> str | None:
    if branch != "main":
        return (
            f"repo:pull-main requires the main branch, but the current branch "
            f"is {branch!r}. Switch with `git switch main` and rerun."
        )
    if status_output.strip():
        return (
            "repo:pull-main requires a clean worktree, but the worktree is "
            "dirty. Commit or stash your changes and rerun."
        )
    return None


def head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def pull_main(root: Path) -> int:
    return subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=root,
    ).returncode


def should_update_graphify(
    pull_code: int, head_before: str, head_after: str
) -> bool:
    return pull_code == 0 and head_before != head_after


def graphify_update(root: Path) -> int:
    return subprocess.run(
        ["task", "graphify:update"],
        cwd=root,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    del argv  # this slice accepts no arguments
    root = repository_root()
    error = guard_error(current_branch(root), status_porcelain(root))
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1
    head_before = head_sha(root)
    pull_code = pull_main(root)
    if pull_code != 0:
        return pull_code
    head_after = head_sha(root)
    if not should_update_graphify(pull_code, head_before, head_after):
        return 0
    graphify_code = graphify_update(root)
    if graphify_code != 0:
        print(
            "error: graphify update failed; main is already updated and will "
            f"not be rolled back. Fix graphify and rerun "
            "`task graphify:update`.",
            file=sys.stderr,
        )
    return graphify_code


if __name__ == "__main__":
    raise SystemExit(main())
