#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys


HEADER_RE = re.compile(
    r"^#\d+ (feat|fix|docs|test|refactor|chore|ci|build|perf|style)"
    r"(\([a-z0-9-]+\))?!?: .+"
)


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def commit_range(args: list[str]) -> str:
    if len(args) == 2 and args[0] and args[1] and args[0] != "0000000000000000000000000000000000000000":
        return f"{args[0]}..{args[1]}"

    base = run_git(["merge-base", "origin/main", "HEAD"])
    return f"{base}..HEAD"


def main() -> int:
    rev_range = commit_range(sys.argv[1:])
    output = run_git(["log", "--no-merges", "--format=%H%x00%s", rev_range])
    if not output:
        return 0

    failed = False
    for line in output.splitlines():
        sha, subject = line.split("\0", 1)
        if not HEADER_RE.match(subject):
            print(f"{sha[:12]} invalid commit message: {subject}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
