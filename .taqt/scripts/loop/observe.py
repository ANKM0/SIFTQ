from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

from .guard import validate_commands


def run_commands(
    commands: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    validate_commands(commands)
    results: list[dict[str, Any]] = []
    started = time.monotonic()

    for command in commands:
        command_started = time.monotonic()
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
        result = {
            "command": command,
            "exit_code": completed.returncode,
            "elapsed_seconds": round(time.monotonic() - command_started, 3),
            "stdout_tail": _tail(completed.stdout),
            "stderr_tail": _tail(completed.stderr),
        }
        results.append(result)
        if completed.returncode != 0:
            return {
                "status": "failure",
                "feedback": classify_failure(command, completed.stdout, completed.stderr),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "commands": results,
            }

    return {
        "status": "success",
        "feedback": None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "commands": results,
    }


def classify_failure(command: str, stdout: str, stderr: str) -> str:
    haystack = f"{command}\n{stdout}\n{stderr}".lower()
    if "specification" in haystack or "acceptance criteria" in haystack:
        return "specification_feedback"
    if "lint" in haystack or "typecheck" in haystack or "test" in haystack:
        return "implementation_feedback"
    if "design" in haystack or "architecture" in haystack:
        return "local_design_feedback"
    return "unknown"


def _tail(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]
