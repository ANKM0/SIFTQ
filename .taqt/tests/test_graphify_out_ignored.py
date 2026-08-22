"""Tests for `graphify-out/` remaining untracked (Issue #174 slice 09).

`graphify-out/` is a per-worktree local artifact and must not be committed.
It must be ignored by `.gitignore`, match `git check-ignore`, and never appear
in `git ls-files`.
"""

import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

GRAPHIFY_OUT = "graphify-out/"


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


def test_gitignore_ignores_graphify_out() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert GRAPHIFY_OUT in gitignore


def test_graphify_out_matches_git_check_ignore() -> None:
    result = _git(["check-ignore", GRAPHIFY_OUT])
    assert result.returncode == 0, f"{GRAPHIFY_OUT} is not ignored by Git"


def test_graphify_out_is_not_git_tracked() -> None:
    tracked = _git(["ls-files"]).stdout.splitlines()
    assert not any(path.startswith(GRAPHIFY_OUT) for path in tracked), (
        "graphify-out/ files are Git-tracked"
    )
