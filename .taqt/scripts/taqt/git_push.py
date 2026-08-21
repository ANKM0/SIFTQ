import argparse
import subprocess
from pathlib import Path

from .github_labels import enabled_error
from .task_store import block_task, issue_branch, load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-git-push")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    task_path, task = load_task(args.task)
    branch = issue_branch(task)
    command = ["git", "push", "-u", args.remote, branch]
    print(" ".join(command))
    if not args.execute:
        return 0
    label_error = enabled_error(task)
    if label_error:
        block_task(task_path, task, label_error)
        print(label_error)
        return 2
    return subprocess.run(command, cwd=args.workspace, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
