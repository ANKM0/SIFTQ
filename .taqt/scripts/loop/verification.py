import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


TASKFILE = "task -t .config/Taskfile.yml"
FAST_COMMANDS = (
    f"{TASKFILE} ci:lint",
    f"{TASKFILE} ci:lint:python",
    f"{TASKFILE} ci:typecheck",
    f"{TASKFILE} ci:test:unit",
)
E2E_COMMANDS = (f"{TASKFILE} ci:test:e2e",)
FRONTEND_DEPENDENCY_COMMAND = f"{TASKFILE} setup:frontend:ci"

DIFF_COMMAND = "git diff --check"
FRONTEND_DEPENDENCY_TASK = "setup:frontend:ci"
FULL_CHECKS = ("ci:lint", "ci:lint:python", "ci:typecheck", "ci:test:unit")
FRONTEND_CHECKS = ("ci:lint", "ci:typecheck", "ci:test:unit:changed")
E2E_TASK = "ci:test:e2e"


def _e2e_enabled() -> bool:
    value = os.environ.get("LOOP_VERIFICATION_SKIP_E2E", "").strip().lower()
    return value not in {"1", "true", "yes"}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _e2e_environment(base: Mapping[str, str] | None = None) -> dict[str, str]:
    return {**(base or {}), "E2E_PORT": str(_free_port()), "CI": "1"}


def _task_command(cwd: Path) -> str:
    if (cwd / ".config" / "Taskfile.yml").is_file():
        return "task -t .config/Taskfile.yml"
    if (cwd / "Taskfile.yml").is_file():
        return "task -t Taskfile.yml"
    return TASKFILE


def _is_documentation_path(path: str) -> bool:
    return path.startswith("docs/") or path.endswith(".md")


def _is_python_path(path: str) -> bool:
    return path.startswith(("scripts/", ".taqt/"))


def _is_frontend_path(path: str) -> bool:
    return path.startswith(("src/", "tests/")) or path in {"package.json", "bun.lock"}


def _is_e2e_path(path: str) -> bool:
    return path.startswith(("src/components/", "src/client/", "src/views/", "tests/e2e/"))


def _is_known_path(path: str) -> bool:
    return _is_documentation_path(path) or _is_python_path(path) or _is_frontend_path(path)


def _checks_for(paths: Sequence[str]) -> dict[str, Any]:
    if not paths or any(not _is_known_path(path) for path in paths):
        return {"setup": True, "checks": FULL_CHECKS, "e2e": True}

    frontend = any(_is_frontend_path(path) for path in paths)
    checks: list[str] = []
    if any(_is_documentation_path(path) for path in paths):
        checks.append("ci:markdown")
    if any(_is_python_path(path) for path in paths):
        checks.append("ci:lint:python")
    if frontend:
        checks.extend(FRONTEND_CHECKS)
    return {
        "setup": frontend,
        "checks": tuple(checks),
        "e2e": frontend and any(_is_e2e_path(path) for path in paths),
    }


def _has_failure(results: list[dict[str, Any]]) -> bool:
    return any(result["exit_code"] != 0 for result in results)


def run_verification(
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    task_command = _task_command(cwd)
    plan = _checks_for(_changed_paths(cwd))

    results = _run_phases([("diff_check", (DIFF_COMMAND,))], cwd=cwd, env=env)
    if _has_failure(results):
        return _failure_result(results, cwd=cwd)

    if plan["setup"]:
        results += _run_phases(
            [("frontend_dependencies", (f"{task_command} {FRONTEND_DEPENDENCY_TASK}",))],
            cwd=cwd,
            env=env,
        )
        if _has_failure(results):
            return _failure_result(results, cwd=cwd)

    checks = tuple(plan["checks"])
    if checks:
        parallel_command = " ".join((task_command, "--parallel", *checks))
        results += _run_phases([("fast_checks", (parallel_command,))], cwd=cwd, env=env)
        if _has_failure(results):
            return _failure_result(results, cwd=cwd)

    if plan["e2e"] and _e2e_enabled():
        results += _run_phases(
            [("e2e_checks", (f"{task_command} {E2E_TASK}",))],
            cwd=cwd,
            env=_e2e_environment(env),
        )
        if _has_failure(results):
            return _failure_result(results, cwd=cwd)

    return _result(status="pass", feedback=None, commands=results, cwd=cwd)


def _run_phases(
    phases: list[tuple[str, tuple[str, ...]]],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for phase, phase_commands in phases:
        for command in phase_commands:
            result = _run_command(command, cwd=cwd, env=env)
            result["phase"] = phase
            results.append(result)
    return results


def _failure_result(results: list[dict[str, Any]], *, cwd: Path) -> dict[str, Any]:
    failed = [result for result in results if result["exit_code"] != 0]
    timed_out = any(result.get("timed_out") for result in failed)
    return _result(
        status="human" if timed_out else "fix",
        feedback="verification_human" if timed_out else "verification_fix",
        commands=results,
        cwd=cwd,
        findings=[f"failed: {result['command']}" for result in failed],
    )


def validate_review(
    response: dict[str, Any], *, changed_paths: Sequence[str], cwd: Path
) -> dict[str, Any]:
    if changed_paths:
        return _result(
            status="human",
            feedback="review_human",
            commands=[],
            cwd=cwd,
            findings=["readonly review modified the workspace"],
        )
    if not response.get("parsed_json") or response.get("status") != "success":
        return _result(
            status="human",
            feedback="review_human",
            commands=[],
            cwd=cwd,
            findings=["review response was not a JSON object"],
        )
    verdict = response.get("verdict")
    if verdict == "approve":
        return _result(status="pass", feedback=None, commands=[], cwd=cwd)
    if verdict == "changes_requested":
        return _result(status="fix", feedback="review_fix", commands=[], cwd=cwd)
    if verdict == "human_required":
        return _result(status="human", feedback="review_human", commands=[], cwd=cwd)
    return _result(
        status="human",
        feedback="review_human",
        commands=[],
        cwd=cwd,
        findings=["review verdict is invalid"],
    )


def _changed_paths(cwd: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


def _run_command(
    command: str,
    *,
    cwd: Path,
    timeout_seconds: int = 900,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env={**os.environ, **env} if env else None,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "exit_code": None,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": _tail(error.stdout or ""),
            "stderr_tail": _tail(error.stderr or ""),
        }
    return {
        "command": command,
        "exit_code": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }


def _result(
    *,
    status: str,
    feedback: str | None,
    commands: list[dict[str, Any]],
    cwd: Path,
    findings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "feedback": feedback,
        "findings": findings or [],
        "commands": commands,
        "revision": _revision(cwd),
        "changed_paths": _changed_paths(cwd),
    }


def _revision(cwd: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _tail(text: str, *, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[-limit:]


def main() -> int:
    print(json.dumps(run_verification(cwd=Path(".")), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
