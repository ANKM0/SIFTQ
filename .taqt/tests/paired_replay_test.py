import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop_eval.replay import load_replay_spec, run_replay, summarize_records


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
        "closure_rate": 0.5,
        "escaped_rate": 0.25,
    }
    assert summary["arms"]["B"]["closure_rate"] == 1.0
    assert summary["arms"]["B"]["escaped_rate"] == 0.0


def test_run_replay_runs_each_arm_without_github(tmp_path: Path) -> None:
    calls: list[str] = []

    def run_loop_fn(**kwargs: object) -> dict[str, object]:
        calls.append(Path(kwargs["loop_path"]).name)
        return {"status": "done"}

    def check_runner(command: str, cwd: Path) -> int:
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

    def check_runner(command: str, cwd: Path) -> int:
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


def test_load_replay_spec_reads_arms_and_checks(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "name: ISSUE-1\narms:\n  A: .taqt/loops/main_loop.yaml\n  B: eval/baselines/loop/main_loop_full_structure.yaml\nchecks:\n  - task ci:test:unit\n",
        encoding="utf-8",
    )

    payload = load_replay_spec(spec)

    assert payload["name"] == "ISSUE-1"
    assert payload["arms"]["B"] == "eval/baselines/loop/main_loop_full_structure.yaml"
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
