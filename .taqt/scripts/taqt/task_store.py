"""Compatibility facade for the taqt task store.

The implementation is split by responsibility:

- ``task_paths``: constants and section definitions
- ``task_repo``: task CRUD, issue metadata, branch naming
- ``task_readiness``: readiness checks and issue section parsing
- ``task_decomposition``: slice planning and slice task construction
- ``task_lifecycle``: triage / block / complete transitions
- ``task_recovery``: stale run recovery and parent completion
"""

from loop.schema import load_document, validate_task, write_document

from .task_decomposition import (
    build_slice_task,
    decompose_issue_body,
    decomposition_errors,
    slice_task_id,
)
from .task_lifecycle import block_task, complete_task, triage_task
from .task_paths import (
    DEFAULT_SLICE_MINUTES,
    DEFAULT_TASK_ROOT,
    DEFAULT_WORKTREE_ROOT,
    PRIORITY_ORDER,
)
from .task_readiness import readiness_errors, readiness_warnings
from .task_recovery import (
    complete_parent_if_children_done,
    is_stale_task,
    recover_stale_task,
)
from .task_repo import (
    branch_purpose,
    create_issue_task,
    issue_branch,
    issue_ref,
    list_tasks,
    load_task,
    next_pending_task,
    save_task,
    task_path,
    upsert_issue_task,
)

__all__ = [
    "DEFAULT_SLICE_MINUTES",
    "DEFAULT_TASK_ROOT",
    "DEFAULT_WORKTREE_ROOT",
    "PRIORITY_ORDER",
    "block_task",
    "branch_purpose",
    "build_slice_task",
    "complete_parent_if_children_done",
    "complete_task",
    "create_issue_task",
    "decompose_issue_body",
    "decomposition_errors",
    "is_stale_task",
    "issue_branch",
    "issue_ref",
    "list_tasks",
    "load_document",
    "load_task",
    "next_pending_task",
    "readiness_errors",
    "readiness_warnings",
    "recover_stale_task",
    "save_task",
    "slice_task_id",
    "task_path",
    "triage_task",
    "upsert_issue_task",
    "validate_task",
    "write_document",
]
