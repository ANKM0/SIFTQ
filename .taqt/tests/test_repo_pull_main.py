"""Tests for the `task repo:pull-main` pull-and-graphify flow (Issue #174).

The repository script is the reproducible source of truth. Its guard decision
and graphify-update decision must be pure functions. The flow must reject
non-main branches and dirty worktrees before pull, refresh graphify only after
a successful pull that moves HEAD, and never roll back the pull when graphify
update fails.
"""

import sys
import subprocess
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CORE_TASKFILE = REPOSITORY_ROOT / "taskfile" / "core.yml"
CODEX_RULES = REPOSITORY_ROOT / ".codex" / "rules" / "siftq.rules"
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.repo_pull_main import (
    current_branch,
    guard_error,
    head_sha,
    main,
    pull_main,
    should_update_graphify,
    status_porcelain,
)


def test_repo_pull_main_task_uses_repository_script() -> None:
    tasks = yaml.safe_load(CORE_TASKFILE.read_text(encoding="utf-8"))["tasks"]
    task = tasks.get("repo:pull-main")
    assert task is not None, f"repo:pull-main is not defined in {CORE_TASKFILE}"

    commands = "\n".join(str(cmd) for cmd in task.get("cmds", []))
    assert "uv run python" in commands
    assert "scripts/repo_pull_main.py" in commands


def test_repo_pull_main_is_allowed_in_codex_task_rules() -> None:
    rules = CODEX_RULES.read_text(encoding="utf-8")
    assert 'prefix_rule(pattern=["task", "repo:pull-main"], decision="allow")' in rules


def test_guard_error_allows_main_and_clean_worktree() -> None:
    assert guard_error("main", "") is None


def test_should_update_graphify_only_after_successful_head_move() -> None:
    assert should_update_graphify(0, "before", "after") is True
    assert should_update_graphify(0, "same", "same") is False
    assert should_update_graphify(1, "before", "after") is False
    assert should_update_graphify(128, "before", "after") is False


def test_main_pulls_and_skips_graphify_when_head_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    pull_calls: list[str] = []
    graphify_calls: list[str] = []
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr("scripts.repo_pull_main.current_branch", lambda _root: "main")
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: "")
    monkeypatch.setattr(
        "scripts.repo_pull_main.head_sha", lambda _root: "same"
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 0,
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.graphify_update",
        lambda _root: graphify_calls.append("graphify") or 0,
    )

    assert main([]) == 0
    assert pull_calls == ["pull"]
    assert graphify_calls == []


def test_main_runs_graphify_update_after_pull_moves_head(
    tmp_path: Path, monkeypatch
) -> None:
    pull_calls: list[str] = []
    graphify_calls: list[str] = []
    head_values = iter(["before", "after"])
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr("scripts.repo_pull_main.current_branch", lambda _root: "main")
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: "")
    monkeypatch.setattr(
        "scripts.repo_pull_main.head_sha",
        lambda _root: next(head_values),
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 0,
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.graphify_update",
        lambda _root: graphify_calls.append("graphify") or 0,
    )

    assert main([]) == 0
    assert pull_calls == ["pull"]
    assert graphify_calls == ["graphify"]


def test_main_returns_graphify_failure_without_rolling_back_pull(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    pull_calls: list[str] = []
    graphify_calls: list[str] = []
    head_values = iter(["before", "after"])
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr("scripts.repo_pull_main.current_branch", lambda _root: "main")
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: "")
    monkeypatch.setattr(
        "scripts.repo_pull_main.head_sha",
        lambda _root: next(head_values),
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 0,
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.graphify_update",
        lambda _root: graphify_calls.append("graphify") or 3,
    )

    assert main([]) == 3
    assert pull_calls == ["pull"]
    assert graphify_calls == ["graphify"]
    assert "not be rolled back" in capsys.readouterr().err


def test_main_skips_graphify_update_when_pull_fails(
    tmp_path: Path, monkeypatch
) -> None:
    pull_calls: list[str] = []
    graphify_calls: list[str] = []
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr("scripts.repo_pull_main.current_branch", lambda _root: "main")
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: "")
    monkeypatch.setattr("scripts.repo_pull_main.head_sha", lambda _root: "before")
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 1,
    )
    monkeypatch.setattr(
        "scripts.repo_pull_main.graphify_update",
        lambda _root: graphify_calls.append("graphify") or 0,
    )

    assert main([]) == 1
    assert pull_calls == ["pull"]
    assert graphify_calls == []


def test_pull_main_runs_git_pull_ff_only(monkeypatch) -> None:
    recorded: dict = {}

    def fake_run(cmd, cwd, **kwargs):
        recorded["cmd"] = cmd
        recorded["cwd"] = cwd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("scripts.repo_pull_main.subprocess.run", fake_run)

    assert pull_main(Path("/repo")) == 0
    assert recorded["cmd"] == ["git", "pull", "--ff-only"]
    assert recorded["cwd"] == Path("/repo")


@pytest.mark.parametrize(
    ("helper", "expected_cmd", "stdout", "expected"),
    [
        (current_branch, ["git", "branch", "--show-current"], "main\n", "main"),
        (
            status_porcelain,
            ["git", "status", "--porcelain"],
            " M README.md\n",
            " M README.md\n",
        ),
        (head_sha, ["git", "rev-parse", "HEAD"], "abc123\n", "abc123"),
    ],
)
def test_git_query_helpers_run_exact_commands(
    monkeypatch, helper, expected_cmd, stdout, expected
) -> None:
    recorded: dict = {}

    def fake_run(cmd, cwd, **kwargs):
        recorded["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout)

    monkeypatch.setattr("scripts.repo_pull_main.subprocess.run", fake_run)

    assert helper(Path("/repo")) == expected
    assert recorded["cmd"] == expected_cmd


@pytest.mark.parametrize("branch", ["", "dev/#174_separate_codex_graphify_per_worktree", "MAIN"])
def test_guard_error_rejects_non_main_branch(branch: str) -> None:
    error = guard_error(branch, "")
    assert error is not None
    assert "main" in error


def test_guard_error_rejects_dirty_worktree() -> None:
    error = guard_error("main", " M README.md\n?? new-file.txt\n")
    assert error is not None
    assert "clean" in error


def test_main_fails_before_pull_when_branch_is_not_main(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    pull_calls: list[str] = []
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr(
        "scripts.repo_pull_main.current_branch",
        lambda _root: "dev/#174_separate_codex_graphify_per_worktree",
    )
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: "")
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 0,
    )

    assert main([]) == 1
    assert pull_calls == []
    assert "main" in capsys.readouterr().err


def test_main_fails_before_pull_when_worktree_is_dirty(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    pull_calls: list[str] = []
    monkeypatch.setattr("scripts.repo_pull_main.repository_root", lambda: tmp_path)
    monkeypatch.setattr("scripts.repo_pull_main.current_branch", lambda _root: "main")
    monkeypatch.setattr("scripts.repo_pull_main.status_porcelain", lambda _root: " M README.md\n")
    monkeypatch.setattr(
        "scripts.repo_pull_main.pull_main",
        lambda _root: pull_calls.append("pull") or 0,
    )

    assert main([]) == 1
    assert pull_calls == []
    assert "clean" in capsys.readouterr().err
