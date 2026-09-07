import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from taqt.release_decision import (
    build_plan_command,
    decision_checklist,
    is_concrete,
)
from taqt.release_decision import (
    main as release_decision_main,
)
from taqt.task_auto import main as task_auto_main
from taqt.task_store import create_issue_task


def test_build_plan_command_is_read_only() -> None:
    command = build_plan_command(version="v0.5.3", ref="abc123", base="v0.5.2")
    assert command == [
        "task",
        "release:plan",
        "--",
        "--version",
        "v0.5.3",
        "--ref",
        "abc123",
        "--base",
        "v0.5.2",
    ]


def test_decision_checklist_forbids_unapproved_mutations() -> None:
    checklist = decision_checklist()
    assert "Release-only" in checklist
    assert "明示承認なしに実行しない" in checklist
    assert "Release Notes" in checklist


def test_is_concrete_rejects_placeholders() -> None:
    assert not is_concrete(version="vX.Y.Z", ref="<sha>", base="<tag>")
    assert is_concrete(version="v0.5.3", ref="abc123", base="v0.5.2")


def test_release_decision_execute_without_concrete_values_runs_nothing(capsys, monkeypatch) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("must not run subprocess with placeholders")

    monkeypatch.setattr("taqt.release_decision.subprocess.run", fail)
    assert release_decision_main(["ISSUE-368", "--execute"]) == 0
    output = capsys.readouterr().out
    assert "task release:plan" in output
    assert "Release-only" in output


def test_task_auto_dry_run_appends_release_decision_after_cleanup(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=68,
        loop="main_loop",
        task_root=tmp_path,
    )
    assert task_auto_main([str(task_path), "--workspace", str(tmp_path / "worktree")]) == 0
    output = capsys.readouterr().out
    assert "taqt.release-decision" in output
    assert output.index("taqt.merge") < output.index("taqt.cleanup") < output.index("taqt.release-decision")


def test_task_auto_release_decision_has_explicit_opt_out(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=69,
        loop="main_loop",
        task_root=tmp_path,
    )
    assert (
        task_auto_main([str(task_path), "--workspace", str(tmp_path), "--no-release-decision"]) == 0
    )
    assert "taqt.release-decision" not in capsys.readouterr().out
