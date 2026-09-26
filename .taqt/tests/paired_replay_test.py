import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop_eval.replay import (
    _default_worktree,
    _resolve_checks,
    _task_command,
    free_port,
    load_replay_spec,
    preview_command,
    run_preview,
    run_replay,
    summarize_records,
)


def test_summarize_records_computes_closure_and_escaped_rates() -> None:
    records = [
        {"arm": "A", "status": "done", "escaped": False},
        {"arm": "A", "status": "done", "escaped": True},
        {"arm": "A", "status": "human", "escaped": False},
        {"arm": "A", "status": "failed", "escaped": False},
        {"arm": "B", "status": "done", "escaped": False},
        {"arm": "B", "status": "done", "escaped": False},
    ]

    summary = summarize_records(records)

    assert summary["arms"]["A"] == {
        "total": 4,
        "done": 2,
        "human": 1,
        "failed": 1,
        "escaped": 1,
        "human_causes": {
            "routing": 1,
            "verification": 0,
            "review": 0,
            "spec_product": 0,
            "permission": 0,
            "model_infra": 0,
        },
        "tokens": {
            "input": 0,
            "output": 0,
            "reasoning": 0,
            "cache_read": 0,
            "cache_write": 0,
            "total": 0,
        },
        "cost": 0.0,
        "closure_rate": 0.5,
        "escaped_rate": 0.25,
        "human_rate": 0.25,
    }
    assert summary["arms"]["B"]["closure_rate"] == 1.0
    assert summary["arms"]["B"]["escaped_rate"] == 0.0
    assert summary["arms"]["B"]["human_rate"] == 0.0
    assert summary["arms"]["B"]["human_causes"] == {
        "routing": 0,
        "verification": 0,
        "review": 0,
        "spec_product": 0,
        "permission": 0,
        "model_infra": 0,
    }


def test_summarize_records_counts_human_causes_per_arm() -> None:
    records = [
        {"arm": "A", "status": "human", "escaped": False, "human_cause": "verification"},
        {"arm": "A", "status": "human", "escaped": False, "human_cause": "verification"},
        {"arm": "A", "status": "human", "escaped": False, "human_cause": "permission"},
        {"arm": "B", "status": "human", "escaped": False, "human_cause": "routing"},
        {"arm": "B", "status": "done", "escaped": False},
    ]

    summary = summarize_records(records)

    assert summary["arms"]["A"]["human_causes"]["verification"] == 2
    assert summary["arms"]["A"]["human_causes"]["permission"] == 1
    assert summary["arms"]["B"]["human_causes"]["routing"] == 1


def test_run_replay_runs_each_arm_without_github(tmp_path: Path) -> None:
    calls: list[str] = []

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        calls.append(Path(kwargs["loop_path"]).name)
        return {"status": "done"}

    def check_runner(command: str, cwd: Path, **_kwargs: object) -> int:
        return 1 if command == "fail" else 0

    result = run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml", "B": tmp_path / "b.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=["fail"],
        run_loop_fn=run_loop_fn,
        check_runner=check_runner,
    )

    assert calls == ["a.yaml", "b.yaml"]
    assert result["records"] == [
        {"arm": "A", "status": "done", "escaped": True},
        {"arm": "B", "status": "done", "escaped": True},
    ]
    assert result["summary"]["arms"]["A"]["escaped_rate"] == 1.0


def test_run_replay_skips_checks_when_not_done(tmp_path: Path) -> None:
    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        return {"status": "human"}

    def check_runner(command: str, cwd: Path, **_kwargs: object) -> int:
        raise AssertionError("checks must not run when the loop did not finish")

    result = run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=["task ci:test:unit"],
        run_loop_fn=run_loop_fn,
        check_runner=check_runner,
    )

    assert result["records"] == [{"arm": "A", "status": "human", "escaped": False}]


def test_run_replay_records_human_cause_from_state(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").write_text(
        json.dumps({"status": "human", "last_feedback": "verification_fix"}),
        encoding="utf-8",
    )

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        return {"status": "human", "run_dir": str(run_dir)}

    result = run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        run_loop_fn=run_loop_fn,
    )

    assert result["records"][0]["human_cause"] == "verification"
    assert result["summary"]["arms"]["A"]["human_causes"]["verification"] == 1


def test_load_replay_spec_reads_arms_and_checks(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "name: ISSUE-1\narms:\n  A: .taqt/loops/main_loop.yaml\n  B: eval/baselines/loop/main_loop_minimal.yaml\nchecks:\n  - task ci:test:unit\n",
        encoding="utf-8",
    )

    payload = load_replay_spec(spec)

    assert payload["name"] == "ISSUE-1"
    assert payload["arms"]["B"] == "eval/baselines/loop/main_loop_minimal.yaml"
    assert payload["checks"] == ["task ci:test:unit"]


def test_run_replay_executes_a_real_command_adapter_loop(tmp_path: Path) -> None:
    loop_path = tmp_path / "loop.yaml"
    loop_path.write_text(
        "version: 1\n"
        "id: replay-fixture\n"
        "agents:\n"
        "  implement:\n"
        "    role: implementation\n"
        "    command: 'true'\n"
        "steps:\n"
        "  - id: implement\n"
        "    kind: llm\n"
        "    agent: implement\n"
        "    next: done\n"
        "  - id: done\n"
        "    kind: terminal\n",
        encoding="utf-8",
    )
    task_path = tmp_path / "task.yaml"
    task_path.write_text(
        "id: ISSUE-1\n"
        "status: pending\n"
        "source:\n"
        "  type: github_issue\n"
        "  repo: owner/repo\n"
        "  issue_number: 1\n",
        encoding="utf-8",
    )

    result = run_replay(
        task_path=task_path,
        arms={"A": loop_path},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=["true"],
    )

    assert result["records"][0]["status"] == "done"
    assert result["summary"]["arms"]["A"]["closure_rate"] == 1.0


@pytest.mark.parametrize(
    "body",
    [
        "name: ISSUE-1\n",
        "name: ISSUE-1\narms: {}\n",
        "name: ISSUE-1\narms:\n  A: ''\n",
        "name: ISSUE-1\narms:\n  A: main_loop.yaml\nchecks: not-a-list\n",
    ],
)
def test_load_replay_spec_rejects_invalid_specs(tmp_path: Path, body: str) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(body, encoding="utf-8")

    with pytest.raises(ValueError):
        load_replay_spec(spec)


def test_task_command_prefers_config_then_root(tmp_path: Path) -> None:
    assert _task_command(tmp_path) == "task -t .config/Taskfile.yml"

    (tmp_path / "Taskfile.yml").write_text("version: '3'\n", encoding="utf-8")
    assert _task_command(tmp_path) == "task -t Taskfile.yml"

    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "Taskfile.yml").write_text("version: '3'\n", encoding="utf-8")
    assert _task_command(tmp_path) == "task -t .config/Taskfile.yml"
    assert _resolve_checks(["{taskfile} ci:test:unit"], tmp_path) == [
        "task -t .config/Taskfile.yml ci:test:unit"
    ]


def test_missing_tasks_detects_base_without_interface() -> None:
    from loop_eval.preflight import missing_tasks

    repo = Path(__file__).resolve().parents[2]

    assert "ci:test:unit" in missing_tasks("a4279946", repo)
    assert missing_tasks("21e97b54", repo) == []


def test_load_replay_spec_reads_base_commit_and_repetitions(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "name: ISSUE-1\narms:\n  A: a.yaml\nchecks: []\nbase_commit: abc123\nrepetitions: 3\n",
        encoding="utf-8",
    )

    payload = load_replay_spec(spec)

    assert payload["base_commit"] == "abc123"
    assert payload["repetitions"] == 3


@pytest.mark.parametrize(
    "body",
    [
        "name: ISSUE-1\narms:\n  A: a.yaml\nbase_commit: ''\n",
        "name: ISSUE-1\narms:\n  A: a.yaml\nrepetitions: 0\n",
        "name: ISSUE-1\narms:\n  A: a.yaml\nrepetitions: two\n",
    ],
)
def test_load_replay_spec_rejects_invalid_base_commit_and_repetitions(
    tmp_path: Path, body: str
) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(body, encoding="utf-8")

    with pytest.raises(ValueError):
        load_replay_spec(spec)


def test_run_replay_isolates_workspace_per_arm_and_repetition(tmp_path: Path) -> None:
    from contextlib import contextmanager

    seen: list[tuple[str, int, str]] = []

    @contextmanager
    def factory(arm: str, rep: int, base_commit: str, repo: Path):
        isolated = tmp_path / f"ws-{arm}-{rep}"
        isolated.mkdir(exist_ok=True)
        seen.append((arm, rep, base_commit))
        yield isolated

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        return {"status": "done"}

    result = run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml", "B": tmp_path / "b.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=[],
        base_commit="abc123",
        repetitions=2,
        repo=tmp_path,
        worktree_factory=factory,
        run_loop_fn=run_loop_fn,
    )

    assert seen == [("A", 0, "abc123"), ("A", 1, "abc123"), ("B", 0, "abc123"), ("B", 1, "abc123")]
    assert len(result["records"]) == 4
    assert [record["rep"] for record in result["records"]] == [0, 1, 0, 1]


def test_run_replay_passes_per_workspace_tmp_root_to_loop(tmp_path: Path) -> None:
    seen: list[dict[str, object]] = []

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        environment = kwargs["child_environment"]
        assert isinstance(environment, dict)
        seen.append(environment)
        return {"status": "done"}

    run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=[],
        run_loop_fn=run_loop_fn,
    )

    tmp_root = (tmp_path / ".tmp").resolve()
    assert seen == [
        {"TMP_ROOT": str(tmp_root), "UV_PROJECT_ENVIRONMENT": str(tmp_root / ".venv")}
    ]


def test_run_replay_passes_isolation_environment_to_checks(tmp_path: Path) -> None:
    seen: list[object] = []

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        return {"status": "done"}

    def check_runner(command: str, cwd: Path, *, env: object = None) -> int:
        seen.append(env)
        return 0

    run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=["true"],
        run_loop_fn=run_loop_fn,
        check_runner=check_runner,
    )

    tmp_root = (tmp_path / ".tmp").resolve()
    assert seen == [{"TMP_ROOT": str(tmp_root), "UV_PROJECT_ENVIRONMENT": str(tmp_root / ".venv")}]


def test_run_replay_reports_kept_workspaces_when_requested(tmp_path: Path) -> None:
    from contextlib import contextmanager

    @contextmanager
    def factory(arm: str, rep: int, base_commit: str, repo: Path):
        isolated = tmp_path / f"ws-{arm}-{rep}"
        isolated.mkdir(exist_ok=True)
        yield isolated

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        return {"status": "done"}

    result = run_replay(
        task_path=tmp_path / "task.yaml",
        arms={"A": tmp_path / "a.yaml"},
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
        checks=[],
        base_commit="abc123",
        repo=tmp_path,
        worktree_factory=factory,
        run_loop_fn=run_loop_fn,
        keep_worktrees=True,
    )

    assert result["kept_workspaces"] == [str(tmp_path / "ws-A-0")]


def test_default_worktree_keep_controls_removal(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)

    with _default_worktree("A", 0, "HEAD", repo, Path("ws")) as removed:
        assert removed.is_dir()
    assert not removed.exists()

    with _default_worktree("A", 0, "HEAD", repo, Path("ws"), keep=True) as kept:
        assert kept.is_dir()
    assert kept.is_dir()


def test_free_port_is_bindable() -> None:
    port = free_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_run_preview_prints_url_and_serves_the_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(
        command: list[str], *, cwd: Path, **kwargs: object
    ) -> subprocess.CompletedProcess[object]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(args=command, returncode=0)

    exit_code = run_preview(tmp_path, port=4321, runner=fake_runner)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "http://127.0.0.1:4321" in captured.out
    assert calls == [(preview_command(4321), tmp_path)]
    assert "preview:mock" in calls[0][0]


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "file.txt").write_text("content", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo
