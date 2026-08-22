"""Tests for the `task graphify:update` Task (Issue #174 slice 01).

The Task must update the graphify graph rooted at the executing worktree and,
when the graphify runtime is unavailable, fail with a clear error that includes
installation instructions instead of installing graphify implicitly.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CORE_TASKFILE = REPOSITORY_ROOT / "taskfile" / "core.yml"
CODEX_RULES = REPOSITORY_ROOT / ".codex" / "rules" / "siftq.rules"

GRAPHIFY_UPDATE_TASK = "graphify:update"
UV_INSTALL = "uv tool install graphifyy"
PIP_INSTALL = "python3 -m pip install graphifyy"


def _task_lines() -> list[str]:
    tasks = yaml.safe_load(CORE_TASKFILE.read_text(encoding="utf-8"))["tasks"]
    task = tasks.get(GRAPHIFY_UPDATE_TASK)
    assert task is not None, f"{GRAPHIFY_UPDATE_TASK} is not defined in {CORE_TASKFILE}"
    lines = [str(cmd) for cmd in task.get("cmds", [])]
    return [line for entry in lines for line in entry.splitlines()]


def test_graphify_update_invokes_graphify_on_worktree_root() -> None:
    lines = _task_lines()
    assert any("graphify" in line and "{{.ROOT_DIR}}" in line for line in lines)


def test_graphify_update_error_mentions_install_instructions() -> None:
    text = "\n".join(_task_lines())
    assert UV_INSTALL in text
    assert PIP_INSTALL in text


def test_graphify_update_is_allowed_in_codex_task_rules() -> None:
    rules = CODEX_RULES.read_text(encoding="utf-8")
    assert (
        f'prefix_rule(pattern=["task", "{GRAPHIFY_UPDATE_TASK}"], decision="allow")'
        in rules
    )


def test_graphify_update_fails_with_install_instructions_without_runtime() -> None:
    task_bin = shutil.which("task")
    if task_bin is None:
        pytest.skip("task binary is not available")

    path = os.pathsep.join([str(Path(task_bin).parent), "/usr/bin", "/bin"])
    if shutil.which("graphify", path=path) is not None:
        pytest.skip("graphify is resolvable on the restricted PATH")

    result = subprocess.run(
        ["task", GRAPHIFY_UPDATE_TASK],
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "PATH": path},
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert UV_INSTALL in output
    assert PIP_INSTALL in output
