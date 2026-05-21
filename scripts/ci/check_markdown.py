#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {".git", ".venv", ".codd", ".takt", "node_modules", "dist"}


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


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
