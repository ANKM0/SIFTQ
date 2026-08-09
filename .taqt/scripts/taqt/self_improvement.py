import argparse
from pathlib import Path
from typing import Any

from loop.state import append_event, safe_id, utc_now

from .task_store import DEFAULT_TASK_ROOT, load_task, save_task


DEFAULT_RUNS_ROOT = Path(".taqt/runs")
DEFAULT_SKILL_PATH = Path(".agents/skills/self-improvement/SKILL.md")


def request_self_improvement(
    *,
    task_path: Path,
    task: dict[str, Any],
    reason: str,
    event: str,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    workspace: Path = Path("."),
    run_dir: Path | None = None,
) -> dict[str, Any]:
    request = build_request(
        task_path=task_path,
        task=task,
        reason=reason,
        event=event,
        workspace=workspace,
        run_dir=run_dir,
    )
    request_path = _request_path(task=task, event=event, runs_root=runs_root, run_dir=run_dir)
    request["request_path"] = str(request_path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(render_request(request), encoding="utf-8")
    task["self_improvement"] = request
    if run_dir is not None:
        append_event(run_dir, {"type": "self_improvement_requested", "request": request})
    return request


def build_request(
    *,
    task_path: Path,
    task: dict[str, Any],
    reason: str,
    event: str,
    workspace: Path = Path("."),
    run_dir: Path | None = None,
) -> dict[str, Any]:
    source = task.get("source") if isinstance(task.get("source"), dict) else {}
    skill_path = workspace / DEFAULT_SKILL_PATH
    return {
        "requested_at": utc_now(),
        "skill": "self-improvement",
        "skill_path": str(skill_path),
        "event": event,
        "reason": reason,
        "task_id": task.get("id"),
        "task_path": str(task_path),
        "status": task.get("status"),
        "phase": task.get("phase"),
        "blocked_reason": task.get("blocked_reason"),
        "repo": source.get("repo"),
        "issue_number": source.get("issue_number"),
        "run_path": str(run_dir) if run_dir is not None else None,
    }


def render_request(request: dict[str, Any]) -> str:
    lines = [
        "# taqt self-improvement request",
        "",
        f"- skill: `{request['skill']}`",
        f"- skill path: `{request['skill_path']}`",
        f"- event: `{request['event']}`",
        f"- reason: `{request['reason']}`",
        f"- task: `{request['task_id']}`",
        f"- task path: `{request['task_path']}`",
        f"- issue: `{request['repo']}#{request['issue_number']}`",
        f"- status: `{request['status']}`",
        f"- phase: `{request['phase']}`",
        f"- blocked reason: `{request['blocked_reason']}`",
        f"- run path: `{request['run_path']}`",
        "",
        "Use the self-improvement skill to decide whether this taqt event should be logged to `.learnings/`.",
        "Record only recurring, non-obvious, or operationally useful learnings.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-self-improvement")
    parser.add_argument("task")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--event", default="manual")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    task_path, task = load_task(args.task, args.task_root)
    request = build_request(
        task_path=task_path,
        task=task,
        reason=args.reason,
        event=args.event,
        workspace=args.workspace,
        run_dir=args.run_dir,
    )
    if not args.execute:
        print(render_request(request), end="")
        return 0

    request = request_self_improvement(
        task_path=task_path,
        task=task,
        reason=args.reason,
        event=args.event,
        runs_root=args.runs_root,
        workspace=args.workspace,
        run_dir=args.run_dir,
    )
    save_task(task_path, task)
    print(request["request_path"])
    return 0


def _request_path(
    *,
    task: dict[str, Any],
    event: str,
    runs_root: Path,
    run_dir: Path | None,
) -> Path:
    filename = f"{safe_id(event)}.md"
    if run_dir is not None:
        return run_dir / "artifacts" / "self-improvement.md"
    return runs_root / safe_id(str(task["id"])) / "self-improvement" / filename


if __name__ == "__main__":
    raise SystemExit(main())
