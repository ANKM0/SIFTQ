#!/usr/bin/env python3
"""Reject Markdown prose that the vendored yomiyasu linter marks as errors.

Only `severity == "error"` findings fail the check. Warnings are summarized as a
score so the gate can land before the existing documents reach full strictness.
"""

import json
import subprocess
import sys
from pathlib import Path

from checker import repository_root


VENDOR_DIR = Path(".agents/skills/yomiyasu")
LINTER = VENDOR_DIR / "scripts" / "yomiyasu_lint.py"


def target_files(root: Path) -> list[Path]:
    """Git-managed Markdown files, excluding the vendored yomiyasu skill."""
    listed = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z", "*.md"],
        text=True,
    ).split("\0")
    vendored = (root / VENDOR_DIR).resolve()
    return sorted(
        root / name
        for name in listed
        if name and not (root / name).resolve().is_relative_to(vendored)
    )


def lint(root: Path, path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(root / LINTER), "--json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yomiyasu linter failed on {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def check_files(root: Path, paths: list[Path]) -> int:
    errors = 0
    warnings = 0
    score_total = 0
    for path in paths:
        report = lint(root, path)
        score_total += report.get("score", 0)
        display = path.relative_to(root) if path.is_relative_to(root) else path
        for finding in report.get("findings", []):
            if finding["severity"] != "error":
                warnings += 1
                continue
            print(f"{display}:{finding['line']}: {finding['message']}")
            print(f"  > {finding['snippet']}")
            errors += 1
    average = round(score_total / len(paths), 1) if paths else 0.0
    print(f"yomiyasu: {len(paths)} files, {warnings} warnings (average score {average})")
    return 1 if errors else 0


def main() -> int:
    root = repository_root()
    return check_files(root, target_files(root))


if __name__ == "__main__":
    sys.exit(main())
