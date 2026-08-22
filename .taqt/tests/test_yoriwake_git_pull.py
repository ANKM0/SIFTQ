"""Tests for the worktree-scoped `git pull` shell function (Issue #174 slices 06-07).

The shell function must route only a bare `git pull` to `task repo:pull-main`
and only when the current directory is inside the Yoriwake clone's SIFTQ
worktree. All other Git commands, argument-bearing pulls, `command git pull`,
and pulls outside the Yoriwake clone must fall through to the real `git`.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts" / "yoriwake_git_pull.sh"

GIT_SH = r"""#!/bin/sh
printf '%s\n' "$*" >> "${GIT_LOG:?}"
if [ "$1" = "rev-parse" ] && [ "$2" = "--show-toplevel" ]; then
    printf '%s\n' "$TOPLEVEL"
fi
exit 0
"""

TASK_SH = r"""#!/bin/sh
printf '%s\n' "$*" >> "${TASK_LOG:?}"
exit 0
"""


@pytest.fixture
def shell_env(tmp_path: Path):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available")

    root = tmp_path / "Yoriwake"
    worktree = root / ".taqt" / "worktrees" / "ISSUE-174"
    worktree.mkdir(parents=True)
    (root / ".taqt" / "config").mkdir(parents=True)
    (root / "taskfile").mkdir()
    (root / "scripts").mkdir()
    (root / ".taqt" / "config" / "profiles.yaml").write_text(
        "profiles: {}\n", encoding="utf-8"
    )
    (root / "taskfile" / "core.yml").write_text(
        'version: "3"\n', encoding="utf-8"
    )
    shutil.copyfile(SCRIPT, root / "scripts" / "yoriwake_git_pull.sh")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text(GIT_SH, encoding="utf-8")
    fake_git.chmod(0o755)
    fake_task = bin_dir / "task"
    fake_task.write_text(TASK_SH, encoding="utf-8")
    fake_task.chmod(0o755)

    return {
        "bash": bash,
        "bin_dir": bin_dir,
        "root": root,
        "script": root / "scripts" / "yoriwake_git_pull.sh",
        "tmp_path": tmp_path,
        "worktree": worktree,
    }


def _run(shell_env: dict, *, cwd: Path, command: str, toplevel: Path):
    git_log = shell_env["tmp_path"] / "git.log"
    task_log = shell_env["tmp_path"] / "task.log"
    git_log.write_text("", encoding="utf-8")
    task_log.write_text("", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{shell_env['bin_dir']}{os.pathsep}{env.get('PATH', '')}"
    env["GIT_LOG"] = str(git_log)
    env["TASK_LOG"] = str(task_log)
    env["TOPLEVEL"] = str(toplevel)

    result = subprocess.run(
        [
            shell_env["bash"],
            "-c",
            'source "$1"; shift; cd "$1"; shift; eval "$1"',
            "bash",
            str(shell_env["script"]),
            str(cwd),
            command,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return git_log.read_text(encoding="utf-8").splitlines(), task_log.read_text(
        encoding="utf-8"
    ).splitlines()


def test_bare_pull_inside_yoriwake_worktree_routes_to_task(
    shell_env,
) -> None:
    git_lines, task_lines = _run(
        shell_env,
        cwd=shell_env["worktree"],
        command="git pull",
        toplevel=shell_env["root"],
    )

    assert task_lines == ["repo:pull-main"]
    assert "pull" not in git_lines
    assert git_lines.count("rev-parse --show-toplevel") == 2


@pytest.mark.parametrize(
    "command",
    ["git status", "git commit", "git push", "git switch main", "git fetch"],
)
def test_other_git_commands_use_raw_git(shell_env, command: str) -> None:
    git_lines, task_lines = _run(
        shell_env,
        cwd=shell_env["worktree"],
        command=command,
        toplevel=shell_env["root"],
    )

    assert task_lines == []
    assert git_lines == [command.removeprefix("git ")]


def test_command_git_pull_bypasses_wrapper(shell_env) -> None:
    git_lines, task_lines = _run(
        shell_env,
        cwd=shell_env["worktree"],
        command="command git pull",
        toplevel=shell_env["root"],
    )

    assert task_lines == []
    assert git_lines == ["pull"]


def test_pull_outside_yoriwake_root_uses_raw_git(shell_env) -> None:
    outside = shell_env["tmp_path"] / "elsewhere"
    outside.mkdir()

    git_lines, task_lines = _run(
        shell_env,
        cwd=outside,
        command="git pull",
        toplevel=outside,
    )

    assert task_lines == []
    assert git_lines == ["rev-parse --show-toplevel", "pull"]


def test_pull_inside_root_without_repo_marker_uses_raw_git(shell_env) -> None:
    nested = shell_env["root"] / "nested"
    nested.mkdir()

    git_lines, task_lines = _run(
        shell_env,
        cwd=nested,
        command="git pull",
        toplevel=nested,
    )

    assert task_lines == []
    assert git_lines == ["rev-parse --show-toplevel", "pull"]


def test_pull_with_args_uses_raw_git(shell_env) -> None:
    git_lines, task_lines = _run(
        shell_env,
        cwd=shell_env["worktree"],
        command="git pull --ff-only",
        toplevel=shell_env["root"],
    )

    assert task_lines == []
    assert git_lines == ["pull --ff-only"]
