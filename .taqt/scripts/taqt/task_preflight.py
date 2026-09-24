from pathlib import Path
from typing import Any

from .self_improvement import request_self_improvement
from .task_store import (
    decomposition_errors,
    readiness_errors,
    save_task,
    triage_task,
)


def preflight_task(
    task_path: Path,
    task: dict[str, Any],
    *,
    workspace: Path,
    runs_root: Path,
    execute: bool = True,
) -> list[str]:
    """Return readiness/decomposition errors for a task.

    Triage and self-improvement side effects run only when ``execute`` is set.
    """
    errors = readiness_errors(task, workspace=workspace)
    if errors:
        if execute:
            reason = "; ".join(errors)
            triage_task(task_path, task, reason)
            request_self_improvement(
                task_path=task_path,
                task=task,
                reason=reason,
                event="readiness_failed",
                runs_root=runs_root,
                workspace=workspace,
            )
            save_task(task_path, task)
        return errors

    errors = decomposition_errors(task, workspace=workspace)
    if errors:
        if execute and task.get("phase") != "decomposed":
            triage_task(task_path, task, "; ".join(errors))
        return errors

    return []
