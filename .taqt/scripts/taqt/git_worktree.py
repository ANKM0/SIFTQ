from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .task_store import issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-worktree")
    parser.add_argument("task")
    parser.add_argument("--base", default="main")
    parser.add_argument("--worktree-root", type=Path, default=Path(".taqt/worktrees"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    branch = issue_branch(task)
    worktree = args.worktree_root / task["id"]
    command = ["git", "worktree", "add", "-B", branch, str(worktree), args.base]
    print(" ".join(command))
    if not args.execute:
        return 0
    worktree.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
