import argparse
import contextlib
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

import yaml

from loop.runner import run_loop
from loop.state import load_events, load_state

from .defect_injection import subprocess_runner
from .human_rate import CAUSE_CATEGORIES, classify_cause
from .preflight import missing_tasks

RunLoopFn = Callable[..., dict[str, Any]]
CommandRunner = Callable[..., int]
WorktreeFactory = Callable[[str, int, str, Path], "contextlib.AbstractContextManager[Path]"]
PreviewRunner = Callable[..., subprocess.CompletedProcess[Any]]

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
    keep_worktrees: bool = False,
    run_loop_fn: RunLoopFn = run_loop,
    check_runner: CommandRunner = subprocess_runner,
    worktree_factory: WorktreeFactory | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    kept_workspaces: list[str] = []
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
                keep=keep_worktrees,
            ) as run_workspace:
                if keep_worktrees:
                    kept_workspaces.append(str(run_workspace))
                environment = _isolated_environment(run_workspace)
                result = run_loop_fn(
                    loop_path=Path(loop_path),
                    task_path=task_path,
                    workspace=run_workspace,
                    runs_root=runs_root,
                    child_environment=environment,
                )
                status = str(result.get("status"))
                escaped = False
                if status == "done" and checks:
                    escaped = _checks_failed(
                        _resolve_checks(checks, run_workspace),
                        cwd=run_workspace,
                        runner=check_runner,
                        env=environment,
                    )
                record: dict[str, Any] = {"arm": arm, "status": status, "escaped": escaped}
                if repetitions > 1:
                    record["rep"] = rep
                run_dir = result.get("run_dir")
                if run_dir:
                    record["usage"] = _run_usage(Path(run_dir))
                    if status == "human":
                        state = load_state(Path(run_dir))
                        if state is not None:
                            record["human_cause"] = classify_cause(state)
                records.append(record)
    result = {"records": records, "summary": summarize_records(records)}
    if keep_worktrees:
        result["kept_workspaces"] = kept_workspaces
    return result


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
    keep: bool = False,
) -> Iterator[Path]:
    if base_commit is None or repo is None:
        yield workspace
        return
    if factory is not None:
        with factory(arm, rep, base_commit, repo) as isolated:
            yield isolated
        return
    with _default_worktree(arm, rep, base_commit, repo, worktree_root, keep=keep) as isolated:
        yield isolated


@contextlib.contextmanager
def _default_worktree(
    arm: str, rep: int, base_commit: str, repo: Path, worktree_root: Path, *, keep: bool = False
) -> Iterator[Path]:
    safe_arm = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in arm)
    base_path = (repo / worktree_root / f"{safe_arm}-{rep}").resolve()
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    path = _add_worktree(base_path, base_commit, repo)
    try:
        yield path
    finally:
        if not keep:
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


def _add_worktree(base_path: Path, base_commit: str, repo: Path) -> Path:
    for attempt in range(3):
        candidate = base_path if attempt == 0 else base_path.with_name(f"{base_path.name}-{attempt}")
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)
        completed = subprocess.run(
            ["git", "worktree", "add", "--detach", "--force", str(candidate), base_commit],
            cwd=repo,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode == 0:
            return candidate
    raise RuntimeError(
        f"git worktree add failed for {base_commit} after retries: {completed.stderr.strip()}"
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
                "human_causes": {category: 0 for category in CAUSE_CATEGORIES},
                "tokens": dict(EMPTY_TOKENS),
                "cost": 0.0,
            },
        )
        stats["total"] += 1
        status = str(record["status"])
        if status in stats:
            stats[status] += 1
        if status == "human":
            cause = str(record.get("human_cause") or "routing")
            if cause in stats["human_causes"]:
                stats["human_causes"][cause] += 1
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


def _isolated_environment(workspace: Path) -> dict[str, str]:
    tmp_root = (workspace / ".tmp").resolve()
    return {"TMP_ROOT": str(tmp_root), "UV_PROJECT_ENVIRONMENT": str(tmp_root / ".venv")}


def _checks_failed(
    commands: Sequence[str],
    *,
    cwd: Path,
    runner: CommandRunner,
    env: dict[str, str] | None = None,
) -> bool:
    return any(runner(command, cwd, env=env) != 0 for command in commands)


def _task_command(workspace: Path) -> str:
    if (workspace / ".config" / "Taskfile.yml").is_file():
        return "task -t .config/Taskfile.yml"
    if (workspace / "Taskfile.yml").is_file():
        return "task -t Taskfile.yml"
    return "task -t .config/Taskfile.yml"


def _resolve_checks(checks: Sequence[str], workspace: Path) -> list[str]:
    task_command = _task_command(workspace)
    return [command.replace("{taskfile}", task_command) for command in checks]


def _spec_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("*.yaml"))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def preview_command(port: int) -> list[str]:
    return ["bun", "run", "preview:mock", "--local", "--ip", "127.0.0.1", "--port", str(port)]


def run_preview(
    workspace: Path,
    *,
    port: int | None = None,
    runner: PreviewRunner = subprocess.run,
) -> int:
    chosen = port or free_port()
    print(f"preview: http://127.0.0.1:{chosen} (password: preview)", flush=True)
    completed = runner(preview_command(chosen), cwd=workspace, text=True)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop-eval-paired-replay")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--task", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--worktree-root", type=Path, default=DEFAULT_WORKTREE_ROOT)
    parser.add_argument(
        "--keep-worktrees",
        action="store_true",
        help="Keep replay worktrees on disk and print their paths.",
    )
    subparsers = parser.add_subparsers(dest="command")
    preview_parser = subparsers.add_parser("preview", help="Serve a kept worktree with preview:mock.")
    preview_parser.add_argument("--workspace", type=Path, required=True)
    preview_parser.add_argument("--port", type=int)
    args = parser.parse_args(argv)

    if args.command == "preview":
        return run_preview(args.workspace, port=args.port)

    if args.spec is None or args.task is None:
        parser.error("--spec and --task are required")

    spec = load_replay_spec(args.spec)
    repo = args.repo or args.workspace
    repetitions = args.repetitions or spec["repetitions"]
    if spec["base_commit"]:
        missing = missing_tasks(spec["base_commit"], repo)
        if missing:
            print(
                f"::warning::gold {spec['name']} base lacks tasks: {', '.join(missing)}",
                file=sys.stderr,
            )
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
        keep_worktrees=args.keep_worktrees,
    )
    result["name"] = spec["name"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
