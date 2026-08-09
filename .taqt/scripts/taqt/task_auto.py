import argparse
from pathlib import Path

from .task_cleanup import main as cleanup_main
from .git_commit import main as commit_main
from .git_push import main as push_main
from .github_merge import main as merge_main
from .github_pr import main as pr_main
from .task_run import main as run_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-auto")
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--loop-root", type=Path, default=Path(".taqt/loops"))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--worker-id", default="local")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base", default="main")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--merge-strategy", choices=["squash", "merge", "rebase"], default="squash")
    parser.add_argument("--delete-branch", action="store_true")
    parser.add_argument("--cleanup-worktree", action="store_true")
    parser.add_argument("--delete-local-branch", action="store_true")
    parser.add_argument("--delete-remote-branch", action="store_true")
    parser.add_argument("--skip-run", action="store_true")
    parser.add_argument("--skip-commit", action="store_true")
    parser.add_argument("--skip-push", action="store_true")
    parser.add_argument("--skip-pr", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    steps = _build_steps(args)
    if not args.execute:
        for step in steps:
            print(" ".join(step))
        return 0

    for step in steps:
        exit_code = _run_step(step)
        if exit_code != 0:
            return exit_code
    return 0


def _build_steps(args: argparse.Namespace) -> list[list[str]]:
    task = str(args.task)
    workspace = str(args.workspace)
    steps: list[list[str]] = []
    if not args.skip_run:
        steps.append(
            [
                "taqt.run",
                task,
                "--loop-root",
                str(args.loop_root),
                "--runs-root",
                str(args.runs_root),
                "--workspace",
                workspace,
                "--worker-id",
                str(args.worker_id),
            ]
        )
    if not args.skip_commit:
        steps.append(["taqt.commit", task, "--workspace", workspace])
    if not args.skip_push:
        steps.append(["taqt.push", task, "--workspace", workspace, "--remote", str(args.remote)])
    if not args.skip_pr:
        steps.append(["taqt.pr", task, "--workspace", workspace, "--base", str(args.base)])
    if args.merge:
        steps.append(
            [
                "taqt.merge",
                task,
                "--workspace",
                workspace,
                "--strategy",
                str(args.merge_strategy),
                *(["--delete-branch"] if args.delete_branch else []),
            ]
        )
    if args.cleanup_worktree:
        steps.append(
            [
                "taqt.cleanup",
                task,
                "--workspace",
                workspace,
                "--remote",
                str(args.remote),
                "--mark-done",
                "--sync-parent",
                *(["--delete-local-branch"] if args.delete_local_branch else []),
                *(["--delete-remote-branch"] if args.delete_remote_branch else []),
            ]
        )
    return steps


def _run_step(step: list[str]) -> int:
    name, *args = step
    args = [*args, "--execute"]
    if name == "taqt.run":
        args.remove("--execute")
        return run_main(args)
    if name == "taqt.commit":
        return commit_main(args)
    if name == "taqt.push":
        return push_main(args)
    if name == "taqt.pr":
        return pr_main(args)
    if name == "taqt.merge":
        return merge_main(args)
    if name == "taqt.cleanup":
        return cleanup_main(args)
    raise ValueError(f"unknown taqt auto step: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
