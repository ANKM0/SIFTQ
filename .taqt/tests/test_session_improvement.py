import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from taqt.session_improvement import (
    Candidate,
    collect_candidates,
    correction_pattern,
    issue_keys_from_payload,
    main,
    normalize_command,
)


def _write_session(path: Path, *, cwd: Path, branch: str, commands: list[int], corrections: int = 0) -> None:
    records = [
        {
            "timestamp": "2026-08-10T12:00:00Z",
            "type": "session_meta",
            "payload": {"id": path.stem, "cwd": str(cwd), "timestamp": "2026-08-10T12:00:00Z", "git": {"branch": branch}},
        }
    ]
    records.extend(
        {
            "timestamp": "2026-08-10T12:00:00Z",
            "type": "event_msg",
            "payload": {"type": "exec_command_end", "command": "task ci:test", "exit_code": code},
        }
        for code in commands
    )
    records.extend(
        {
            "timestamp": "2026-08-10T12:00:00Z",
            "type": "event_msg",
            "payload": {"type": "user_message", "message": "それは違う"},
        }
        for _ in range(corrections)
    )
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def test_collect_candidates_requires_recurrence_and_distinct_tasks(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    worktree_a = tmp_path / "repo"
    worktree_b = tmp_path / "repo-worktree"
    worktree_a.mkdir()
    worktree_b.mkdir()
    _write_session(sessions / "one.jsonl", cwd=worktree_a, branch="dev/#1_one", commands=[1, 1])
    _write_session(sessions / "two.jsonl", cwd=worktree_b, branch="dev/#2_two", commands=[1])
    _write_session(sessions / "outside.jsonl", cwd=tmp_path / "outside", branch="dev/#3_three", commands=[1, 1, 1])

    candidates = collect_candidates(
        sessions,
        [worktree_a, worktree_b],
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )

    assert len(candidates) == 1
    assert candidates[0].kind == "command_failure"
    assert candidates[0].occurrences == 3
    assert candidates[0].task_count == 2
    assert candidates[0].target == "Taskfile"


def test_collect_candidates_detects_correction_cues(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    worktree_a = tmp_path / "repo"
    worktree_b = tmp_path / "repo-worktree"
    worktree_a.mkdir()
    worktree_b.mkdir()
    _write_session(sessions / "one.jsonl", cwd=worktree_a, branch="dev/#1_one", commands=[], corrections=2)
    _write_session(sessions / "two.jsonl", cwd=worktree_b, branch="dev/#2_two", commands=[], corrections=1)

    candidates = collect_candidates(
        sessions,
        [worktree_a, worktree_b],
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )

    assert [(item.kind, item.target) for item in candidates] == [("user_correction", "rule_or_skill")]


def test_normalizers_remove_paths_and_detect_correction() -> None:
    assert normalize_command("task ci:test --token secret-value") == "task ci:test"
    assert normalize_command("curl -H 'Authorization: Bearer secret-value' https://example.test") == "curl"
    assert correction_pattern("Task は GitHub Issue ではなく Taskfile") == "ではなく"
    assert correction_pattern("問題ありません") is None


def test_issue_marker_prevents_duplicate_creation() -> None:
    payload = '[{"body":"<!-- self-improvement:command_failure-abc123 -->"}]'

    assert issue_keys_from_payload(payload) == {"command_failure-abc123"}


def test_execute_skips_existing_candidate_and_dry_run_does_not_query_github(tmp_path: Path, monkeypatch) -> None:
    candidate = Candidate(
        key="command_failure-abc123",
        kind="command_failure",
        pattern="task ci:test",
        occurrences=3,
        task_count=2,
        first_seen=datetime(2026, 8, 1, tzinfo=timezone.utc),
        last_seen=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )
    monkeypatch.setattr("taqt.session_improvement.discover_worktrees", lambda _root: ())
    monkeypatch.setattr("taqt.session_improvement.collect_candidates", lambda *_args, **_kwargs: [candidate])
    calls = []
    monkeypatch.setattr("taqt.session_improvement.existing_issue_keys", lambda _repo: {candidate.key})
    monkeypatch.setattr("taqt.session_improvement.create_issue", lambda *_args: calls.append("create"))

    assert main(["--repository-root", str(tmp_path), "--execute"]) == 0
    assert calls == []

    monkeypatch.setattr(
        "taqt.session_improvement.existing_issue_keys",
        lambda _repo: (_ for _ in ()).throw(AssertionError("dry run must not query GitHub")),
    )
    assert main(["--repository-root", str(tmp_path), "--dry-run"]) == 0
