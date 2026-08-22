"""Tests for `.learnings/` remaining Git-tracked shared artifacts (Issue #174 slice 08).

`.learnings/LEARNINGS.md`, `.learnings/ERRORS.md`, and
`.learnings/FEATURE_REQUESTS.md` must stay Git-tracked and PR-reviewable shared
artifacts. They must appear in `git ls-files` and must not be ignored by
`.gitignore` (ADR 0017).
"""

import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

LEARNINGS_FILES = [
    ".learnings/LEARNINGS.md",
    ".learnings/ERRORS.md",
    ".learnings/FEATURE_REQUESTS.md",
]


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("path", LEARNINGS_FILES)
def test_learning_artifact_is_git_tracked(path: str) -> None:
    tracked = set(_git(["ls-files"]).stdout.splitlines())
    assert path in tracked, f"{path} is not Git-tracked"


@pytest.mark.parametrize("path", LEARNINGS_FILES)
def test_learning_artifact_is_not_ignored(path: str) -> None:
    result = _git(["check-ignore", path])
    assert result.returncode != 0, f"{path} is ignored by .gitignore"


def test_gitignore_has_no_learnings_entry() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".learnings/" not in gitignore
