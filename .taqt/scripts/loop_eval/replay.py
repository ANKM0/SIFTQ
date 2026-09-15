import argparse
import json
from pathlib import Path
from typing import Any, Callable, Sequence

import yaml

from loop.runner import run_loop

from .defect_injection import subprocess_runner

RunLoopFn = Callable[..., dict[str, Any]]
CommandRunner = Callable[[str, Path], int]

DEFAULT_REPLAY_ROOT = Path("eval/gold/loop-tasks")


def load_replay_spec(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{path} requires a name")
    arms = payload.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise ValueError(f"{path} requires a non-empty arms mapping")
    for arm, loop_path in arms.items():
        if not isinstance(arm, str) or not arm:
            raise ValueError(f"{path} arm names must be non-empty strings")
        if not isinstance(loop_path, str) or not loop_path:
            raise ValueError(f"{path} arm {arm} must reference a loop path")
    checks = payload.get("checks", [])
    if not isinstance(checks, list) or any(not isinstance(check, str) for check in checks):
        raise ValueError(f"{path} checks must be a list of strings")
    return {"name": name, "arms": arms, "checks": checks}


def run_replay(
    *,
    task_path: Path,
    arms: dict[str, str | Path],
    workspace: Path,
    runs_root: Path,
    checks: Sequence[str] = (),
    run_loop_fn: RunLoopFn = run_loop,
    check_runner: CommandRunner = subprocess_runner,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for arm, loop_path in arms.items():
        result = run_loop_fn(
            loop_path=Path(loop_path),
            task_path=task_path,
            workspace=workspace,
            runs_root=runs_root,
        )
        status = str(result.get("status"))
        escaped = False
        if status == "done" and checks:
            escaped = _checks_failed(checks, cwd=workspace, runner=check_runner)
        records.append({"arm": arm, "status": status, "escaped": escaped})
    return {"records": records, "summary": summarize_records(records)}


def summarize_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    per_arm: dict[str, dict[str, Any]] = {}
    for record in records:
        arm = str(record["arm"])
        stats = per_arm.setdefault(
            arm, {"total": 0, "done": 0, "human": 0, "failed": 0, "escaped": 0}
        )
        stats["total"] += 1
        status = str(record["status"])
        if status in stats:
            stats[status] += 1
        if record.get("escaped"):
            stats["escaped"] += 1
    for stats in per_arm.values():
        total = stats["total"]
        stats["closure_rate"] = round(stats["done"] / total, 4) if total else 0.0
        stats["escaped_rate"] = round(stats["escaped"] / total, 4) if total else 0.0
    return {"arms": per_arm}


def _checks_failed(commands: Sequence[str], *, cwd: Path, runner: CommandRunner) -> bool:
    return any(runner(command, cwd) != 0 for command in commands)


def _spec_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("*.yaml"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop-eval-paired-replay")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    args = parser.parse_args(argv)

    spec = load_replay_spec(args.spec)
    result = run_replay(
        task_path=args.task,
        arms=spec["arms"],
        workspace=args.workspace,
        runs_root=args.runs_root,
        checks=spec["checks"],
    )
    result["name"] = spec["name"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
