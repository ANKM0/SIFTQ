import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from taqt import github_labels, github_sync, github_watch, task_create, task_run, task_worker


def _task() -> dict[str, object]:
    return {
        "id": "ISSUE-167",
        "source": {"repo": "ANKM0/SIFTQ", "issue_number": 167},
        "status": "pending",
        "phase": "spec",
        "loop": "development_feedback_loop",
        "run": {},
    }


def test_fetch_issue_labels_returns_none_when_github_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        github_labels.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failed"),
    )

    assert github_labels.fetch_issue_labels("ANKM0/SIFTQ", 167) is None


def test_enabled_error_requires_enabled_label(monkeypatch) -> None:
    monkeypatch.setattr(github_labels, "fetch_issue_labels", lambda *_args: {"enhancement"})

    assert "does not have taqt:enabled" in str(github_labels.enabled_error(_task()))


def test_task_create_fails_closed_without_enabled_label(monkeypatch) -> None:
    monkeypatch.setattr(task_create, "_fetch_issue", lambda *_args: {"labels": []})
    monkeypatch.setattr(task_create, "create_issue_task", lambda **_kwargs: (_ for _ in ()).throw(AssertionError()))

    assert task_create.main(["--repo", "ANKM0/SIFTQ", "--issue", "167", "--id", "ISSUE-167"]) == 2


def test_watch_always_filters_enabled_label(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps([]), "")

    monkeypatch.setattr(github_watch.subprocess, "run", run)

    assert github_watch.main(["--repo", "ANKM0/SIFTQ", "--task-root", str(tmp_path)]) == 0
    assert ["--label", "taqt:enabled"] == calls[0][-2:]


def test_worker_blocks_task_when_label_is_missing(monkeypatch, tmp_path: Path) -> None:
    task = _task()
    blocked: list[str] = []
    monkeypatch.setattr(task_worker, "_select_pending", lambda *_args, **_kwargs: [(tmp_path / "ISSUE-167.yaml", task)])
    monkeypatch.setattr(task_worker, "enabled_error", lambda _task: "label missing")
    monkeypatch.setattr(task_worker, "block_task", lambda _path, _task, reason: blocked.append(reason))

    assert task_worker.main(["--task-root", str(tmp_path), "--execute"]) == 2
    assert blocked == ["label missing"]


def test_run_blocks_before_loop_when_label_is_missing(monkeypatch, tmp_path: Path) -> None:
    task = _task()
    blocked: list[str] = []
    monkeypatch.setattr(task_run, "load_task", lambda *_args: (tmp_path / "ISSUE-167.yaml", task))
    monkeypatch.setattr(task_run, "enabled_error", lambda _task: "label missing")
    monkeypatch.setattr(task_run, "block_task", lambda _path, _task, reason: blocked.append(reason))
    monkeypatch.setattr(task_run, "run_loop", lambda **_kwargs: (_ for _ in ()).throw(AssertionError()))

    assert task_run.main(["ISSUE-167", "--skip-readiness-check"]) == 2
    assert blocked == ["label missing"]


def test_run_blocks_after_safe_step_when_label_is_removed(monkeypatch, tmp_path: Path) -> None:
    task = _task()
    checks = iter([None, "label removed"])
    blocked: list[str] = []
    monkeypatch.setattr(task_run, "load_task", lambda *_args: (tmp_path / "ISSUE-167.yaml", task))
    monkeypatch.setattr(task_run, "enabled_error", lambda _task: next(checks))
    monkeypatch.setattr(task_run, "save_task", lambda *_args: None)
    monkeypatch.setattr(task_run, "block_task", lambda _path, _task, reason: blocked.append(reason))
    monkeypatch.setattr(task_run, "run_loop", lambda **_kwargs: {"status": "done", "run_dir": str(tmp_path / "run")})

    assert task_run.main(["ISSUE-167", "--skip-readiness-check"]) == 2
    assert blocked == ["label removed"]


def test_github_sync_only_prints_a_progress_comment(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(github_sync, "load_task", lambda *_args: (tmp_path / "ISSUE-167.yaml", _task()))

    assert github_sync.main(["ISSUE-167"]) == 0
    output = capsys.readouterr().out
    assert "gh issue edit" not in output
    assert "taqt task update" in output
