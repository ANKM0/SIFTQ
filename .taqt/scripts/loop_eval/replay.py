import argparse
import contextlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

import yaml

from loop.runner import run_loop
from loop.state import load_events

from .defect_injection import subprocess_runner

RunLoopFn = Callable[..., dict[str, Any]]
CommandRunner = Callable[[str, Path], int]
WorktreeFactory = Callable[[str, int, str, Path], "contextlib.AbstractContextManager[Path]"]

DEFAULT_REPLAY_ROOT = Path("eval/gold/loop-tasks")
DEFAULT_WORKTREE_ROOT = Path("tmp/replay-worktrees")
EMPTY_TOKENS = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0, "total": 0}


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
    base_commit = payload.get("base_commit")
    if base_commit is not None and (not isinstance(base_commit, str) or not base_commit):
        raise ValueError(f"{path} base_commit must be a non-empty string when present")
    repetitions = payload.get("repetitions", 1)
    if not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError(f"{path} repetitions must be a positive integer")
    return {
        "name": name,
        "arms": arms,
        "checks": checks,
        "base_commit": base_commit,
        "repetitions": repetitions,
    }


def run_replay(
    *,
    task_path: Path,
    arms: dict[str, str | Path],
    workspace: Path,
    runs_root: Path,
    checks: Sequence[str] = (),
    base_commit: str | None = None,
    repetitions: int = 1,
    repo: Path | None = None,
    worktree_root: Path = DEFAULT_WORKTREE_ROOT,
    run_loop_fn: RunLoopFn = run_loop,
    check_runner: CommandRunner = subprocess_runner,
    worktree_factory: WorktreeFactory | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for arm, loop_path in arms.items():
        for rep in range(repetitions):
            with _workspace_for(
                arm,
                rep,
                base_commit=base_commit,
                repo=repo,
                workspace=workspace,
                worktree_root=worktree_root,
                factory=worktree_factory,
            ) as run_workspace:
                result = run_loop_fn(
                    loop_path=Path(loop_path),
                    task_path=task_path,
                    workspace=run_workspace,
                    runs_root=runs_root,
                )
                status = str(result.get("status"))
                escaped = False
                if status == "done" and checks:
                    escaped = _checks_failed(checks, cwd=run_workspace, runner=check_runner)
                record: dict[str, Any] = {"arm": arm, "status": status, "escaped": escaped}
                if repetitions > 1:
                    record["rep"] = rep
                run_dir = result.get("run_dir")
                if run_dir:
                    record["usage"] = _run_usage(Path(run_dir))
                records.append(record)
    return {"records": records, "summary": summarize_records(records)}


@contextlib.contextmanager
def _workspace_for(
    arm: str,
    rep: int,
    *,
    base_commit: str | None,
    repo: Path | None,
    workspace: Path,
    worktree_root: Path,
    factory: WorktreeFactory | None,
) -> Iterator[Path]:
    if base_commit is None or repo is None:
        yield workspace
        return
    if factory is not None:
        with factory(arm, rep, base_commit, repo) as isolated:
            yield isolated
        return
    with _default_worktree(arm, rep, base_commit, repo, worktree_root) as isolated:
        yield isolated


@contextlib.contextmanager
def _default_worktree(
    arm: str, rep: int, base_commit: str, repo: Path, worktree_root: Path
) -> Iterator[Path]:
    safe_arm = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in arm)
    path = (repo / worktree_root / f"{safe_arm}-{rep}").resolve()
    subprocess.run(
        ["git", "worktree", "add", "--detach", "--force", str(path), base_commit],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield path
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(path)],
            cwd=repo,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


def _run_usage(run_dir: Path) -> dict[str, Any]:
    tokens = dict(EMPTY_TOKENS)
    cost = 0.0
    for event in load_events(run_dir):
        response = event.get("response")
        usage = response.get("usage") if isinstance(response, dict) else None
        if not isinstance(usage, dict):
            continue
        usage_tokens = usage.get("tokens")
        if isinstance(usage_tokens, dict):
            for key in tokens:
                tokens[key] += int(usage_tokens.get(key) or 0)
        value = usage.get("cost")
        if isinstance(value, (int, float)):
            cost += float(value)
    return {"tokens": tokens, "cost": round(cost, 6)}


def summarize_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    per_arm: dict[str, dict[str, Any]] = {}
    for record in records:
        arm = str(record["arm"])
        stats = per_arm.setdefault(
            arm,
            {
                "total": 0,
                "done": 0,
                "human": 0,
                "failed": 0,
                "escaped": 0,
                "tokens": dict(EMPTY_TOKENS),
                "cost": 0.0,
            },
        )
        stats["total"] += 1
        status = str(record["status"])
        if status in stats:
            stats[status] += 1
        if record.get("escaped"):
            stats["escaped"] += 1
        usage = record.get("usage")
        if isinstance(usage, dict):
            usage_tokens = usage.get("tokens")
            if isinstance(usage_tokens, dict):
                for key in stats["tokens"]:
                    stats["tokens"][key] += int(usage_tokens.get(key) or 0)
            value = usage.get("cost")
            if isinstance(value, (int, float)):
                stats["cost"] = round(stats["cost"] + float(value), 6)
    for stats in per_arm.values():
        total = stats["total"]
        stats["closure_rate"] = round(stats["done"] / total, 4) if total else 0.0
        stats["escaped_rate"] = round(stats["escaped"] / total, 4) if total else 0.0
        stats["human_rate"] = round(stats["human"] / total, 4) if total else 0.0
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
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--worktree-root", type=Path, default=DEFAULT_WORKTREE_ROOT)
    args = parser.parse_args(argv)

    spec = load_replay_spec(args.spec)
    repo = args.repo or args.workspace
    repetitions = args.repetitions or spec["repetitions"]
    result = run_replay(
        task_path=args.task,
        arms=spec["arms"],
        workspace=args.workspace,
        runs_root=args.runs_root,
        checks=spec["checks"],
        base_commit=spec["base_commit"],
        repetitions=repetitions,
        repo=repo if spec["base_commit"] else None,
        worktree_root=args.worktree_root,
    )
    result["name"] = spec["name"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
