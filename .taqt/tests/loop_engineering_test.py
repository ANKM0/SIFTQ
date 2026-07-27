from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop.observe import run_commands
from loop.runner import run_loop
from loop.schema import load_document
from taqt.task_run import main as task_run_main
from taqt.task_store import create_issue_task, issue_branch
from taqt.git_worktree import main as git_worktree_main
from taqt.git_commit import main as git_commit_main
from taqt.git_push import main as git_push_main
from taqt.github_pr import main as github_pr_main


def test_create_issue_task_writes_taqt_yaml(tmp_path: Path) -> None:
    path, task = create_issue_task(
        repo="owner/repo",
        issue_number=123,
        loop="development_feedback_loop",
        requirement="docs/requirements/feature.md",
        task_root=tmp_path,
    )

    assert path == tmp_path / "ISSUE-123.yaml"
    assert task["source"]["type"] == "github_issue"
    assert task["source"]["issue_number"] == 123
    assert load_document(path)["input"]["requirement"] == "docs/requirements/feature.md"


def test_observe_classifies_failed_test_command(tmp_path: Path) -> None:
    result = run_commands(["python -c 'import sys; sys.exit(1)' # test"], cwd=tmp_path)

    assert result["status"] == "failure"
    assert result["feedback"] == "implementation_feedback"
    assert result["commands"][0]["exit_code"] == 1


def test_loop_runner_completes_command_loop(tmp_path: Path) -> None:
    loop_path = tmp_path / "loop.yaml"
    task_path = tmp_path / "task.yaml"
    runs_root = tmp_path / "runs"
    loop_path.write_text(
        """
version: 1
id: smoke
limits:
  max_iterations: 5
steps:
  - id: observe
    kind: commands
    run:
      - python -c 'print("ok")'
    on_success: done
    on_failure: decide
  - id: decide
    kind: policy
    routes:
      - when: unknown
        next: human
  - id: done
    kind: terminal
  - id: human
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path.write_text(
        """
id: ISSUE-1
source:
  type: github_issue
  repo: owner/repo
  issue_number: 1
status: pending
phase: spec
priority: normal
loop: smoke
input: {}
run:
  id: null
  state_path: null
  events_path: null
worker:
  id: null
  heartbeat_at: null
blocked_reason: null
""",
        encoding="utf-8",
    )

    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=runs_root,
    )

    assert result["status"] == "done"
    state = json.loads((Path(result["run_dir"]) / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "done"


def test_taqt_task_run_maps_human_terminal_to_blocked_task(tmp_path: Path) -> None:
    loop_root = tmp_path / "loops"
    task_root = tmp_path / "tasks"
    loop_root.mkdir()
    task_root.mkdir()
    (loop_root / "development_feedback_loop.yaml").write_text(
        """
version: 1
id: development_feedback_loop
steps:
  - id: human
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=9,
        loop="development_feedback_loop",
        task_root=task_root,
    )

    exit_code = task_run_main(
        [
            str(task_path),
            "--loop-root",
            str(loop_root),
            "--runs-root",
            str(tmp_path / "runs"),
            "--workspace",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    task = load_document(task_path)
    assert task["status"] == "blocked"
    assert task["phase"] == "human"
    assert task["blocked_reason"] == "human escalation required"


def test_git_and_pr_scripts_are_dry_run_by_default(tmp_path: Path, capsys) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=42,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    assert issue_branch(task) == "issue-42-development-feedback-loop"
    assert git_worktree_main([str(task_path), "--base", "main"]) == 0
    assert git_push_main([str(task_path), "--remote", "origin"]) == 0
    assert github_pr_main([str(task_path), "--base", "main", "--draft"]) == 0

    output = capsys.readouterr().out
    assert "git worktree add -B issue-42-development-feedback-loop" in output
    assert "git push -u origin issue-42-development-feedback-loop" in output
    assert "gh pr create" in output
    assert "--draft" in output


def test_git_commit_is_dry_run_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=43,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    class Completed:
        returncode = 0
        stdout = " M file.py\n"
        stderr = ""

    def fake_run(*_args, **_kwargs):
        return Completed()

    monkeypatch.setattr("taqt.git_commit.subprocess.run", fake_run)

    assert git_commit_main([str(task_path), "--workspace", str(tmp_path)]) == 0

    output = capsys.readouterr().out
    assert "git add -A" in output
    assert "git commit -m #43 feat(taqt): implement development feedback loop task" in output
