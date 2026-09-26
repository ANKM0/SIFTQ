"""Producer/consumer contract between loop steps and policy routes (Issue #427).

A step that emits a feedback value must have a policy route for it. Without the
explicit route the feedback falls through to `unknown` and the run escalates to
human silently.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / ".taqt" / "scripts"))

from loop.runner import run_loop

TRANSITION_FEEDBACK = {
    ("verification", "on_fix"): "verification_fix",
    ("post_review", "on_fix"): "review_fix",
}


def _repo_loops() -> list[Path]:
    return sorted((REPOSITORY_ROOT / ".taqt" / "loops").glob("*.yaml"))


def _task_yaml() -> str:
    return """
id: ISSUE-427
source:
  type: github_issue
  repo: owner/repo
  issue_number: 427
status: pending
phase: spec
priority: normal
input: {}
run:
  id: null
  state_path: null
  events_path: null
worker:
  id: null
  heartbeat_at: null
blocked_reason: null
"""


@pytest.mark.parametrize("loop_path", _repo_loops(), ids=lambda path: path.name)
def test_policy_routes_cover_producer_feedback(loop_path: Path) -> None:
    loop = yaml.safe_load(loop_path.read_text(encoding="utf-8"))
    steps = {step["id"]: step for step in loop["steps"]}
    policy_ids = {step_id for step_id, step in steps.items() if step.get("kind") == "policy"}

    for step in loop["steps"]:
        for (kind, field), feedback in TRANSITION_FEEDBACK.items():
            if step.get("kind") != kind or field not in step:
                continue
            target = step[field]
            if target not in policy_ids:
                continue
            routes = {route["when"] for route in steps[target]["routes"]}
            assert feedback in routes, (
                f"{loop_path.name}: {step['id']}.{field} emits {feedback} "
                f"but policy {target} has no route for it"
            )


def test_verification_failure_routes_to_fix_then_completes(tmp_path: Path, monkeypatch) -> None:
    loop_path = REPOSITORY_ROOT / ".taqt" / "loops" / "main_loop.yaml"
    task_path = tmp_path / "task.yaml"
    task_path.write_text(_task_yaml(), encoding="utf-8")

    verification_results = [
        {"status": "fix", "feedback": "verification_fix", "commands": []},
        {"status": "pass", "feedback": None, "commands": []},
    ]
    monkeypatch.setattr("loop.runner.run_verification", lambda **_kwargs: verification_results.pop(0))

    calls: list[str] = []

    def fake_agent(**kwargs: object) -> dict[str, object]:
        calls.append(str(kwargs["step"]["id"]))
        return {"status": "success", "parsed_json": True}

    monkeypatch.setattr("loop.runner.run_agent", fake_agent)

    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=tmp_path / "runs",
    )

    assert result["status"] == "done"
    assert calls == ["implement", "fix"]
