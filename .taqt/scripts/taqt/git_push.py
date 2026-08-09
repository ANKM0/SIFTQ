import argparse
import subprocess
from pathlib import Path

from .task_store import issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-push")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    branch = issue_branch(task)
    command = ["git", "push", "-u", args.remote, branch]
    print(" ".join(command))
    if not args.execute:
        return 0
    return subprocess.run(command, cwd=args.workspace, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
