import json
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence


FAST_COMMANDS = (
    "task ci:lint",
    "task ci:lint:python",
    "task ci:typecheck",
    "task ci:test:unit",
)
FRONTEND_DEPENDENCY_COMMAND = "task setup:frontend:ci"


def run_verification(
    *,
    cwd: Path,
) -> dict[str, Any]:
    commands: list[tuple[str, tuple[str, ...]]] = [("diff_check", ("git diff --check",))]
    if _requires_frontend_dependencies(cwd):
        commands.append(("frontend_dependencies", (FRONTEND_DEPENDENCY_COMMAND,)))
        commands.extend(
            (
                ("fast_checks", FAST_COMMANDS),
            )
        )
    results: list[dict[str, Any]] = []
    for phase, phase_commands in commands:
        for command in phase_commands:
            result = _run_command(command, cwd=cwd)
            result["phase"] = phase
            results.append(result)
            if result["exit_code"] != 0:
                return _result(
                    status="human" if result.get("timed_out") else "fix",
                    feedback="verification_human" if result.get("timed_out") else "verification_fix",
                    commands=results,
                    cwd=cwd,
                )
    return _result(status="pass", feedback=None, commands=results, cwd=cwd)


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


def _requires_frontend_dependencies(cwd: Path) -> bool:
    return True


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


def _run_command(command: str, *, cwd: Path, timeout_seconds: int = 900) -> dict[str, Any]:
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
