import argparse
import subprocess
from pathlib import Path
from typing import Any

from .task_store import DEFAULT_WORKTREE_ROOT, issue_branch, load_task


def build_worktree_command(
    task: dict[str, Any],
    *,
    base: str = "main",
    worktree_root: Path = DEFAULT_WORKTREE_ROOT,
) -> list[str]:
    branch = issue_branch(task)
    worktree = worktree_root / str(task["id"])
    return ["git", "worktree", "add", "-B", branch, str(worktree), base]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-worktree")
    parser.add_argument("task")
    parser.add_argument("--base", default="main")
    parser.add_argument("--worktree-root", type=Path, default=DEFAULT_WORKTREE_ROOT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    command = build_worktree_command(task, base=args.base, worktree_root=args.worktree_root)
    print(" ".join(command))
    if not args.execute:
        return 0
    worktree_root = args.worktree_root
    (worktree_root / str(task["id"])).parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
