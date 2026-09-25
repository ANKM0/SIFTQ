import subprocess
from pathlib import Path
from typing import Sequence

REQUIRED_TASKS = (
    "ci:lint",
    "ci:lint:python",
    "ci:typecheck",
    "ci:test:unit",
    "setup:frontend:ci",
)


def missing_tasks(
    base_commit: str,
    repo: Path,
    required: Sequence[str] = REQUIRED_TASKS,
) -> list[str]:
    return [task for task in required if not _base_has_task(base_commit, task, repo)]


def _base_has_task(base_commit: str, task: str, repo: Path) -> bool:
    completed = subprocess.run(
        ["git", "grep", "-q", task, base_commit, "--", "*.yml"],
        cwd=repo,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0
