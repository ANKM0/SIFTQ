#!/usr/bin/env python3
import subprocess
from pathlib import Path


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / "package.json").is_file():
            return path
    raise RuntimeError("repository root not found")


ROOT = repository_root()


def markdown_files() -> list[Path]:
    """Repository-owned markdown files (tracked or untracked, not gitignored)."""
    tracked = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
        text=True,
    ).split("\0")
    untracked = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            "*.md",
        ],
        text=True,
    ).split("\0")
    return sorted({ROOT / name for name in tracked + untracked if name})


def main() -> int:
    failed = False
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            print(f"{path.relative_to(ROOT)}: missing trailing newline")
            failed = True
        for index, line in enumerate(text.splitlines(), start=1):
            if line.rstrip() != line:
                print(f"{path.relative_to(ROOT)}:{index}: trailing whitespace")
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
