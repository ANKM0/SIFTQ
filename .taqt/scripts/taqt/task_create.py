from __future__ import annotations

import argparse

from .task_store import create_issue_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-create")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--loop", default="development_feedback_loop")
    parser.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    parser.add_argument("--requirement")
    parser.add_argument("--id")
    args = parser.parse_args(argv)

    path, _task = create_issue_task(
        repo=args.repo,
        issue_number=args.issue,
        loop=args.loop,
        priority=args.priority,
        requirement=args.requirement,
        task_id=args.id,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
