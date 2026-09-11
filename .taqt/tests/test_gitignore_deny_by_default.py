"""Tests for `.gitignore` using deny-by-default matching (Issue #385)."""

import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
UNLISTED_PATH = "__issue_385_unlisted_path__"
UNLISTED_PATHS_WITH_ALLOWED_EXTENSIONS = (
    "__issue_385_unlisted__.py",
    "__issue_385_unlisted__.json",
    "__issue_385_unlisted_dir__/file.ts",
)
ALLOWLISTED_PATHS = (
    ".gitignore",
    "src/new-source.ts",
    "tests/new-test.ts",
    "scripts/new-script.py",
    "docs/new-doc.md",
    "migrations/0004_new.sql",
    "taskfile/new-task.yml",
    ".learnings/LEARNINGS.md",
    ".agents/skills/graphify/SKILL.md",
    ".codex/rules/shared.rules",
    ".taqt/config/profiles.yaml",
)
IGNORED_PATHS = (
    "graphify-out/",
    "tmp/example.json",
    ".taqt/runs/example.jsonl",
    ".taqt/worktrees/example/file.ts",
    ".taqt/config/active.yaml",
    ".dev.vars",
    ".env.local",
    "private.pem",
)


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_gitignore_starts_with_catch_all_pattern() -> None:
    lines = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines and lines[0] == "*"


def test_unlisted_path_is_ignored_by_gitignore() -> None:
    result = _git(["check-ignore", "--no-index", "-v", "--", UNLISTED_PATH])

    assert result.returncode == 0, f"{UNLISTED_PATH} is not ignored by .gitignore"
    assert result.stdout.startswith(".gitignore:1:*")


def test_unlisted_paths_with_allowed_extensions_are_ignored() -> None:
    for path in UNLISTED_PATHS_WITH_ALLOWED_EXTENSIONS:
        result = _git(["check-ignore", "--no-index", "-v", "--", path])

        assert result.returncode == 0, f"{path} is not ignored by .gitignore"
        assert ".gitignore:1:*" in result.stdout, f"{path} is not denied by default"


def test_allowlisted_paths_are_not_ignored() -> None:
    for path in ALLOWLISTED_PATHS:
        result = _git(["check-ignore", "--no-index", "-q", "--", path])
        assert result.returncode != 0, f"{path} is ignored by .gitignore"


def test_local_and_secret_paths_are_ignored() -> None:
    for path in IGNORED_PATHS:
        result = _git(["check-ignore", "--no-index", "-q", "--", path])
        assert result.returncode == 0, f"{path} is not ignored by .gitignore"
