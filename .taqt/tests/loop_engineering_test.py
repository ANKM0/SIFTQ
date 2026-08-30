import json
import subprocess
import sys
from pathlib import Path

import yaml
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop.context import MAX_EVENT_CHARS, MAX_EVENT_STRING_CHARS, build_context
from loop.guard import validate_write_path
from loop.llm import run_agent
from loop.observe import run_commands
from loop.runner import _run_step, _write_design_decision_artifact, run_loop
from loop.schema import load_document, validate_loop_definition
from loop.state import SUCCESS_LOG_TAIL_CHARS, compact_successful_agent_response
from taqt.run_report import render_report
from taqt.task_run import main as task_run_main
from taqt.task_store import (
    create_issue_task,
    decomposition_errors,
    issue_branch,
    next_pending_task,
    readiness_errors,
    readiness_warnings,
    save_task,
    upsert_issue_task,
)
from taqt.task_auto import main as task_auto_main
from taqt.task_cleanup import main as task_cleanup_main
from taqt.task_decompose import main as task_decompose_main
from taqt.task_worker import main as task_worker_main
from taqt.git_worktree import main as git_worktree_main
from taqt.git_commit import main as git_commit_main
from taqt.git_push import main as git_push_main
from taqt.github_pr import main as github_pr_main
from taqt.github_merge import main as github_merge_main
from taqt.github_merge import find_pr
from taqt.github_sync import main as github_sync_main
from taqt.task_create import main as task_create_main
from taqt.deepseek import ensure_codex_home
from taqt.qwen import ensure_codex_home as ensure_qwen_codex_home
from taqt.profiles import load_profiles, resolve_profile


@pytest.fixture(autouse=True)
def allow_enabled_label(monkeypatch) -> None:
    for module in (
        "taqt.task_run",
        "taqt.task_worker",
        "taqt.task_auto",
        "taqt.git_commit",
        "taqt.git_push",
        "taqt.github_pr",
    ):
        monkeypatch.setattr(f"{module}.enabled_error", lambda _task: None)


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


def test_task_create_fetches_issue_metadata(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = json.dumps(
            {
                "title": "Add taqt skill",
                "body": "## AC\n- Works.\n\n## DoD\n- Verified.\n",
                "labels": [{"name": "enhancement"}, {"name": "taqt:enabled"}],
            }
        )
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr("taqt.task_create.subprocess.run", fake_run)

    assert task_create_main(
        [
            "--repo",
            "owner/repo",
            "--issue",
            "136",
            "--loop",
            "development_feedback_loop",
            "--task-root",
            str(tmp_path),
        ]
    ) == 0

    task = load_document(tmp_path / "ISSUE-136.yaml")
    assert task["branch_summary"] == "Add taqt skill"
    assert task["input"]["issue"]["body"].startswith("## AC")
    assert task["input"]["issue"]["labels"] == ["enhancement", "taqt:enabled"]
    assert calls[0][0][:3] == ["gh", "issue", "view"]


def test_task_create_uses_profile_loop_when_loop_omitted(tmp_path: Path, monkeypatch) -> None:
    loop_root = tmp_path / "loops"
    loop_root.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
  deepseek:
    loop: development_feedback_loop_deepseek
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "taqt.task_create._fetch_issue",
        lambda *_args: {
            "title": "Use DeepSeek profile",
            "body": "",
            "labels": ["taqt:enabled"],
        },
    )
    calls: list[dict[str, object]] = []

    def fake_create_issue_task(**kwargs):
        calls.append(kwargs)
        return (tmp_path / "ISSUE-136.yaml", {"id": "ISSUE-136"})

    monkeypatch.setattr("taqt.task_create.create_issue_task", fake_create_issue_task)

    exit_code = task_create_main(
        [
            "--repo",
            "owner/repo",
            "--issue",
            "136",
            "--id",
            "ISSUE-136",
            "--profile",
            "deepseek",
            "--loop-root",
            str(loop_root),
            "--task-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert calls[0]["loop"] == "development_feedback_loop_deepseek"


def test_issue_branch_uses_dev_issue_number_and_normalized_loop_purpose(tmp_path: Path) -> None:
    _path, task = create_issue_task(
        repo="owner/repo",
        issue_number=7,
        loop="Design Review!",
        task_root=tmp_path,
    )

    assert issue_branch(task) == "dev/#7_design_review"


def test_issue_branch_prefers_normalized_branch_summary(tmp_path: Path) -> None:
    path, task = create_issue_task(
        repo="owner/repo",
        issue_number=8,
        loop="development_feedback_loop",
        branch_summary="Add User Profile!",
        task_root=tmp_path,
    )

    assert issue_branch(task) == "dev/#8_add_user_profile"
    assert load_document(path)["branch_summary"] == "Add User Profile!"


def test_observe_classifies_failed_test_command(tmp_path: Path) -> None:
    result = run_commands(["python -c 'import sys; sys.exit(1)' # test"], cwd=tmp_path)

    assert result["status"] == "failure"
    assert result["feedback"] == "test_feedback"
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


def test_deepseek_codex_home_writes_provider_and_catalog_without_key(tmp_path: Path) -> None:
    config_path = ensure_codex_home(tmp_path / "deepseek-home")
    config = config_path.read_text(encoding="utf-8")
    catalog = json.loads((config_path.parent / "models.json").read_text(encoding="utf-8"))

    assert 'model = "qwen/qwen3.8-flash"' in config
    assert 'model_provider = "openrouter"' in config
    assert 'base_url = "https://openrouter.ai/api/v1"' in config
    assert 'env_key = "OPENROUTER_API_KEY"' in config
    assert 'base_url = "https://api.deepseek.com/"' in config
    assert 'wire_api = "responses"' in config
    assert 'env_key = "DEEPSEEK_API_KEY"' in config
    assert 'model_reasoning_effort = "low"' in config
    assert 'model_auto_compact_token_limit = 120000' in config
    assert "experimental_bearer_token" not in config
    assert "DEEPSEEK_API_KEY" not in json.dumps(catalog)
    assert {model["slug"] for model in catalog["models"]} == {
        "qwen/qwen3.8-flash",
        "deepseek-v4-pro",
    }
    assert all("base_instructions" in model for model in catalog["models"])
    assert all("instructions_template" in model["model_messages"] for model in catalog["models"])
    assert all(model["auto_compact_token_limit"] == 120000 for model in catalog["models"])
    assert all(model["default_reasoning_level"] == "low" for model in catalog["models"])


def test_deepseek_codex_home_migrates_legacy_flash_config_and_catalog(tmp_path: Path) -> None:
    codex_home = tmp_path / "deepseek-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        'model = "deepseek-v4-flash"\nmodel_provider = "deepseek"\n',
        encoding="utf-8",
    )
    (codex_home / "models.json").write_text(
        json.dumps({"models": [{"slug": "deepseek-v4-flash"}]}),
        encoding="utf-8",
    )

    config_path = ensure_codex_home(codex_home)
    config = config_path.read_text(encoding="utf-8")
    catalog = json.loads((codex_home / "models.json").read_text(encoding="utf-8"))

    assert 'model = "qwen/qwen3.8-flash"' in config
    assert 'model_provider = "openrouter"' in config
    assert {model["slug"] for model in catalog["models"]} == {
        "qwen/qwen3.8-flash",
        "deepseek-v4-pro",
    }


def test_qwen_codex_home_writes_provider_and_catalog_without_key(tmp_path: Path) -> None:
    config_path = ensure_qwen_codex_home(tmp_path / "qwen-home")
    config = config_path.read_text(encoding="utf-8")
    catalog = json.loads((config_path.parent / "models.json").read_text(encoding="utf-8"))

    assert 'model = "qwen/qwen3.8-flash"' in config
    assert 'base_url = "https://openrouter.ai/api/v1"' in config
    assert 'wire_api = "responses"' in config
    assert 'env_key = "OPENROUTER_API_KEY"' in config
    assert 'model_reasoning_effort = "low"' in config
    assert 'model_auto_compact_token_limit = 120000' in config
    assert "experimental_bearer_token" not in config
    assert "OPENROUTER_API_KEY" not in json.dumps(catalog)
    assert {model["slug"] for model in catalog["models"]} == {"qwen/qwen3.8-flash"}
    assert all("base_instructions" in model for model in catalog["models"])
    assert all("instructions_template" in model["model_messages"] for model in catalog["models"])
    assert all(model["auto_compact_token_limit"] == 120000 for model in catalog["models"])
    assert all(model["default_reasoning_level"] == "low" for model in catalog["models"])


def test_deepseek_loop_definition_uses_deepseek_for_all_agents() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    loop = load_document(repository_root / ".taqt/loops/development_feedback_loop_deepseek.yaml")

    validate_loop_definition(loop)
    assert loop["agents"]["design"]["model"] == "deepseek-v4-pro"
    assert loop["agents"]["implement"]["model"] == "qwen/qwen3.8-flash"
    assert loop["agents"]["checker"]["model"] == "qwen/qwen3.8-flash"
    assert "judge" not in loop["agents"]


def test_qwen_loop_definition_uses_qwen_for_all_agents() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    loop = load_document(repository_root / ".taqt/loops/development_feedback_loop_qwen.yaml")

    validate_loop_definition(loop)
    assert loop["agents"]["design"]["model"] == "qwen/qwen3.8-flash"
    assert loop["agents"]["implement"]["model"] == "qwen/qwen3.8-flash"
    assert loop["agents"]["checker"]["model"] == "qwen/qwen3.8-flash"
    assert "judge" not in loop["agents"]


def test_load_profiles_reads_loop_and_deepseek_settings(tmp_path: Path) -> None:
    loop_root = tmp_path / "loops"
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
  deepseek:
    loop: development_feedback_loop_deepseek
    codex_home: ~/.codex-deepseek
    env_key: DEEPSEEK_API_KEY
""",
        encoding="utf-8",
    )

    profiles = load_profiles(loop_root)

    assert profiles["main"]["loop"] == "development_feedback_loop"
    assert profiles["deepseek"]["loop"] == "development_feedback_loop_deepseek"
    assert profiles["deepseek"]["codex_home"] == "~/.codex-deepseek"


def test_resolve_profile_uses_active_profile(tmp_path: Path) -> None:
    loop_root = tmp_path / "loops"
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
  deepseek:
    loop: development_feedback_loop_deepseek
""",
        encoding="utf-8",
    )
    (tmp_path / "config" / "active.yaml").write_text(
        "active_profile: deepseek\n",
        encoding="utf-8",
    )

    assert resolve_profile(loop_root) == "deepseek"
    assert resolve_profile(loop_root, "main") == "main"


def test_resolve_profile_rejects_unknown_profile(tmp_path: Path) -> None:
    loop_root = tmp_path / "loops"
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        resolve_profile(loop_root, "deepseek")


def test_loop_runner_resumes_from_last_failed_llm_step(tmp_path: Path, monkeypatch) -> None:
    loop_path = tmp_path / "loop.yaml"
    task_path = tmp_path / "task.yaml"
    runs_root = tmp_path / "runs"
    loop_path.write_text(
        """
version: 1
id: resume-loop
agents:
  implement:
    role: implementation
steps:
  - id: implement
    kind: llm
    agent: implement
    next: done
    on_failure: human
  - id: done
    kind: terminal
  - id: human
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path.write_text(
        """
id: ISSUE-176
source:
  type: github_issue
  repo: owner/repo
  issue_number: 176
status: pending
phase: spec
priority: normal
loop: resume-loop
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
    responses = iter(
        [
            {"status": "failure", "feedback": "implementation_feedback"},
            {"status": "success"},
        ]
    )
    monkeypatch.setattr("loop.runner.run_agent", lambda **_kwargs: next(responses))

    first = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=runs_root,
    )
    first_state = json.loads((Path(first["run_dir"]) / "state.json").read_text(encoding="utf-8"))
    assert first["status"] == "human"
    assert first_state["last_failed_step"] == "implement"

    resumed = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=runs_root,
        resume_dir=Path(first["run_dir"]),
    )
    assert resumed["status"] == "done"


def test_loop_runner_writes_design_decision_artifact_after_success(tmp_path: Path) -> None:
    loop_path = tmp_path / "loop.yaml"
    task_path = tmp_path / "task.yaml"
    runs_root = tmp_path / "runs"
    loop_path.write_text(
        """
version: 1
id: design-artifact
agents:
  design:
    role: design
steps:
  - id: design
    kind: llm
    agent: design
    command: >-
      python -c 'import json; print(json.dumps({"status": "success", "summary": "Use the run artifact"}))'
    next: done
  - id: done
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path.write_text(
        """
id: ISSUE-166-01
source:
  type: github_issue
  repo: owner/repo
  issue_number: 166
status: pending
phase: spec
priority: high
loop: design-artifact
input: {}
""",
        encoding="utf-8",
    )

    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=runs_root,
    )

    artifact = Path(result["run_dir"]) / "artifacts" / "design-decision.md"
    assert result["status"] == "done"
    content = artifact.read_text(encoding="utf-8")
    assert content
    assert "Use the run artifact" in content
    assert "## 課題・制約" in content
    assert "## 採用案と理由" in content
    assert "## 却下案と理由" in content
    assert "## 影響範囲・検証結果" in content
    assert "## 未決事項または人間へのエスカレーション" in content

    events = [
        json.loads(line)
        for line in (artifact.parent.parent / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    artifact_event = next(event for event in events if event["type"] == "design_artifact")
    assert artifact_event["artifact_path"] == "artifacts/design-decision.md"
    assert artifact_event["summary"] == "Use the run artifact"
    assert artifact_event["status"] == "created"
    response_event = next(event for event in events if event["type"] == "agent_response")
    response = response_event["response"]
    assert "stdout" not in response
    assert response["log"]["next_step"] == "done"
    assert response["log"]["stdout"]["characters"] > 0


def test_loop_runner_does_not_record_created_event_when_artifact_write_fails(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    def fail_write(*args, **kwargs):
        raise OSError("artifact unavailable")

    monkeypatch.setattr("loop.runner._write_design_decision_artifact", fail_write)

    next_step = _run_step(
        loop_definition={"agents": {"design": {"role": "design"}}},
        task={"id": "ISSUE-166-03"},
        step={"id": "design", "kind": "llm", "agent": "design", "on_failure": "human"},
        state={},
        run_dir=run_dir,
        workspace=tmp_path,
        max_fix_attempts=3,
    )

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert next_step == "human"
    assert not any(event["type"] == "design_artifact" for event in events)
    response_event = next(event for event in events if event["type"] == "agent_response")
    assert response_event["response"]["status"] == "failure"
    assert response_event["response"]["artifact_error"] == "artifact unavailable"


def test_design_decision_artifact_renders_structured_response_fields(tmp_path: Path) -> None:
    _write_design_decision_artifact(
        tmp_path,
        task={"id": "ISSUE-166-02"},
        step={"id": "design"},
        response={
            "problem": "Missing decision structure",
            "constraints": "Keep the run self-contained",
            "selected_option": "Use Markdown sections",
            "rationale": "Readable in reports",
            "rejected_options": ["Only JSON"],
            "rejected_rationale": "Harder to review",
            "impact_scope": "Run artifacts",
            "validation_result": "Integration test",
            "open_items": "None",
            "human_escalation": "None",
        },
    )

    content = (tmp_path / "artifacts" / "design-decision.md").read_text(encoding="utf-8")
    assert "Missing decision structure" in content
    assert "Use Markdown sections" in content
    assert "Only JSON" in content
    assert "Integration test" in content
    assert "None" in content


def test_loop_schema_rejects_unknown_step_reference() -> None:
    try:
        validate_loop_definition(
            {
                "version": 1,
                "id": "bad",
                "steps": [
                    {
                        "id": "observe",
                        "kind": "commands",
                        "run": ["python -c 'print(1)'"],
                        "on_success": "missing",
                        "on_failure": "human",
                    },
                    {"id": "human", "kind": "terminal"},
                ],
            }
        )
    except ValueError as error:
        assert "unknown step" in str(error)
    else:
        raise AssertionError("expected schema validation failure")


def test_loop_schema_allows_model_and_reasoning_effort_for_agents_and_llm_steps(
    tmp_path: Path,
) -> None:
    loop_path = tmp_path / "loop.yaml"
    loop_path.write_text(
        """
version: 1
id: configured-agent
agents:
  implement:
    role: implementation
    adapter: codex
    model: gpt-5.6-luna
    reasoning_effort: xhigh
steps:
  - id: implement
    kind: llm
    agent: implement
    model: gpt-5.6-sol
    reasoning_effort: high
    next: done
  - id: done
    kind: terminal
""",
        encoding="utf-8",
    )

    loop = load_document(loop_path)
    validate_loop_definition(loop)

    assert loop["agents"]["implement"]["model"] == "gpt-5.6-luna"
    assert loop["agents"]["implement"]["reasoning_effort"] == "xhigh"
    assert loop["steps"][0]["model"] == "gpt-5.6-sol"
    assert loop["steps"][0]["reasoning_effort"] == "high"


def test_development_feedback_loop_uses_luna_workers_and_sol_checker() -> None:
    loop_path = Path(__file__).resolve().parents[1] / "loops" / "development_feedback_loop.yaml"

    agents = load_document(loop_path)["agents"]

    assert agents["design"]["model"] == "gpt-5.6-luna"
    assert agents["design"]["reasoning_effort"] == "xhigh"
    assert agents["test"]["model"] == "gpt-5.6-luna"
    assert agents["test"]["reasoning_effort"] == "xhigh"
    assert agents["implement"]["model"] == "gpt-5.6-luna"
    assert agents["implement"]["reasoning_effort"] == "max"
    assert agents["checker"]["model"] == "gpt-5.6-sol"
    assert agents["checker"]["reasoning_effort"] == "high"


def test_deepseek_loop_skips_decompose_orchestrate_and_judge() -> None:
    loop_path = Path(__file__).resolve().parents[1] / "loops" / "development_feedback_loop_deepseek.yaml"

    loop = load_document(loop_path)
    validate_loop_definition(loop)

    assert loop["id"] == "development_feedback_loop_deepseek"
    agents = loop["agents"]
    steps = loop["steps"]
    assert {"design", "test", "implement", "fix", "checker"} == set(agents)
    assert {"decompose", "orchestrate", "judge"}.isdisjoint(agents)
    assert {"decompose", "orchestrate", "judge"}.isdisjoint(step["id"] for step in steps)

    assert agents["design"]["model"] == "deepseek-v4-pro"
    assert agents["design"]["reasoning_effort"] == "high"
    assert agents["test"]["model"] == "qwen/qwen3.8-flash"
    assert agents["test"]["reasoning_effort"] == "low"
    assert agents["implement"]["model"] == "qwen/qwen3.8-flash"
    assert agents["implement"]["reasoning_effort"] == "low"
    assert agents["fix"]["model"] == "qwen/qwen3.8-flash"
    assert agents["fix"]["reasoning_effort"] == "low"
    assert agents["checker"]["model"] == "qwen/qwen3.8-flash"
    assert agents["checker"]["reasoning_effort"] == "low"

    step_ids = [step["id"] for step in steps]
    assert step_ids.index("design") < step_ids.index("test")
    assert step_ids.index("test") < step_ids.index("implement")
    assert step_ids.index("implement") < step_ids.index("observe")
    assert step_ids.index("checker") < step_ids.index("done")

    design = next(step for step in steps if step["id"] == "design")
    assert design["kind"] == "llm"
    assert design["next"] == "test"

    checker = next(step for step in steps if step["id"] == "checker")
    assert checker["kind"] == "llm"
    assert checker["next"] == "done"
    assert checker["on_failure"] == "fix"


def test_deepseek_loop_observe_and_decide_are_model_free() -> None:
    loop_path = Path(__file__).resolve().parents[1] / "loops" / "development_feedback_loop_deepseek.yaml"

    loop = load_document(loop_path)
    validate_loop_definition(loop)

    steps = {step["id"]: step for step in loop["steps"]}
    model_keys = {"agent", "model", "reasoning_effort"}

    observe = steps["observe"]
    assert observe["kind"] == "commands"
    assert "run" in observe and observe["run"]
    assert model_keys.isdisjoint(observe)

    decide = steps["decide"]
    assert decide["kind"] == "policy"
    assert "routes" in decide and decide["routes"]
    assert model_keys.isdisjoint(decide)


def test_loop_schema_rejects_invalid_reasoning_effort_for_agents_and_llm_steps() -> None:
    invalid_agent = {
        "version": 1,
        "id": "invalid-agent-effort",
        "agents": {
            "implement": {
                "adapter": "codex",
                "reasoning_effort": "fast",
            }
        },
        "steps": [{"id": "done", "kind": "terminal"}],
    }
    invalid_step = {
        "version": 1,
        "id": "invalid-step-effort",
        "steps": [
            {
                "id": "implement",
                "kind": "llm",
                "reasoning_effort": "fast",
                "next": "done",
            },
            {"id": "done", "kind": "terminal"},
        ],
    }
    invalid_agent_type = {
        "version": 1,
        "id": "invalid-agent-effort-type",
        "agents": {
            "implement": {
                "adapter": "codex",
                "reasoning_effort": 1,
            }
        },
        "steps": [{"id": "done", "kind": "terminal"}],
    }
    invalid_step_type = {
        "version": 1,
        "id": "invalid-step-effort-type",
        "steps": [
            {
                "id": "implement",
                "kind": "llm",
                "reasoning_effort": ["high"],
                "next": "done",
            },
            {"id": "done", "kind": "terminal"},
        ],
    }
    invalid_agent_null = {
        "version": 1,
        "id": "invalid-agent-effort-null",
        "agents": {"implement": {"adapter": "codex", "reasoning_effort": None}},
        "steps": [{"id": "done", "kind": "terminal"}],
    }
    invalid_step_null = {
        "version": 1,
        "id": "invalid-step-effort-null",
        "steps": [
            {"id": "implement", "kind": "llm", "reasoning_effort": None, "next": "done"},
            {"id": "done", "kind": "terminal"},
        ],
    }

    for loop, expected_message in (
        (invalid_agent, "reasoning_effort is invalid: fast"),
        (invalid_step, "reasoning_effort is invalid: fast"),
        (invalid_agent_type, "reasoning_effort must be a string"),
        (invalid_step_type, "reasoning_effort must be a string"),
        (invalid_agent_null, "reasoning_effort must be a string"),
        (invalid_step_null, "reasoning_effort must be a string"),
    ):
        try:
            validate_loop_definition(loop)
        except ValueError as error:
            assert expected_message in str(error)
        else:
            raise AssertionError("expected schema validation failure")


def test_context_truncates_large_agent_events(tmp_path: Path) -> None:
    context = build_context(
        task={"id": "ISSUE-1", "input": {}},
        step={"id": "test"},
        events=[
            {
                "type": "agent_response",
                "response": {"stderr": "x" * 2_000_000, "status": "failure"},
            }
        ],
        workspace=tmp_path,
    )

    event = context["recent_events"][0]
    assert event["response"]["status"] == "failure"
    assert len(event["response"]["stderr"]) == 2_001


def test_successful_agent_response_is_compacted_deterministically() -> None:
    response = {
        "status": "success",
        "stdout": "a" * (SUCCESS_LOG_TAIL_CHARS + 1),
        "stderr": "stderr output",
        "changed_paths": ["src/example.py"],
    }

    compacted = compact_successful_agent_response(response, next_step="observe")

    assert "stdout" not in compacted
    assert "stderr" not in compacted
    assert compacted["changed_paths"] == ["src/example.py"]
    assert compacted["log"]["next_step"] == "observe"
    assert compacted["log"]["validation"] == "pending"
    assert compacted["log"]["stdout"]["characters"] == SUCCESS_LOG_TAIL_CHARS + 1
    assert compacted["log"]["stdout"]["tail"] == "a" * SUCCESS_LOG_TAIL_CHARS
    assert len(compacted["log"]["stdout"]["sha256"]) == 64


def test_failed_agent_response_keeps_full_transcripts() -> None:
    response = {"status": "failure", "stdout": "output", "stderr": "failure details"}

    preserved = compact_successful_agent_response(response, next_step="human")

    assert preserved == response


def test_loop_guard_blocks_readonly_agent_workspace_changes(tmp_path: Path) -> None:
    loop_path = tmp_path / "loop.yaml"
    task_path = tmp_path / "task.yaml"
    runs_root = tmp_path / "runs"
    loop_path.write_text(
        """
version: 1
id: guarded
agents:
  checker:
    role: checker
    readonly: true
steps:
  - id: checker
    kind: llm
    agent: checker
    command: >-
      python -c 'from pathlib import Path; Path("changed.txt").write_text("x"); print("agent output")'
    on_failure: human
    next: done
  - id: done
    kind: terminal
  - id: human
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path.write_text(
        """
id: ISSUE-2
source:
  type: github_issue
  repo: owner/repo
  issue_number: 2
status: pending
phase: spec
priority: normal
loop: guarded
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
    subprocess_completed = subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert subprocess_completed.returncode == 0

    result = run_loop(
        loop_path=loop_path,
        task_path=task_path,
        workspace=tmp_path,
        runs_root=runs_root,
    )

    assert result["status"] == "human"
    events = [
        json.loads(line)
        for line in (Path(result["run_dir"]) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    response_event = next(event for event in events if event["type"] == "agent_response")
    response = response_event["response"]
    assert response["guard_error"] == "readonly agent cannot write: changed.txt"
    assert response["stdout"] == "agent output\n"


def test_loop_guard_allows_directory_itself_for_prefix_scope() -> None:
    validate_write_path({"writes": ["tests/"]}, Path("tests"))
    validate_write_path({"writes": ["tests/"]}, Path("tests/example_test.py"))


def test_codex_agent_adapter_invokes_codex_exec(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr("loop.llm.subprocess.run", fake_run)

    response = run_agent(
        loop_definition={
            "agents": {
                "implement": {
                    "role": "implementation",
                    "adapter": "codex",
                    "reasoning_effort": "high",
                }
            }
        },
        task={"id": "ISSUE-1"},
        step={"id": "implement", "agent": "implement"},
        context={"files": {}},
        cwd=tmp_path,
        child_environment={"DEEPSEEK_API_KEY": "secret", "CODEX_HOME": "/tmp/deepseek"},
    )

    assert response["status"] == "success"
    command, kwargs = calls[0]
    assert command[:2] == ["codex", "exec"]
    assert "--cd" in command
    assert command[command.index("--cd") + 1] == str(tmp_path.resolve())
    assert "--approve-for-me" in command
    assert "--sandbox" not in command
    assert command[command.index("-c") + 1] == "model_reasoning_effort=high"
    assert "--ask-for-approval" not in command
    assert kwargs["input"].startswith("Role: implementation")
    assert kwargs["env"]["DEEPSEEK_API_KEY"] == "secret"
    assert kwargs["env"]["CODEX_HOME"] == "/tmp/deepseek"


def test_codex_agent_adapter_resolves_reasoning_effort(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr("loop.llm.subprocess.run", fake_run)
    monkeypatch.setenv("LOOP_CODEX_REASONING_EFFORT", "low")

    cases = [
        ({"reasoning_effort": "high"}, {"reasoning_effort": "xhigh"}, "high"),
        ({}, {"reasoning_effort": "xhigh"}, "xhigh"),
        ({}, {}, "low"),
    ]
    for step_overrides, agent_overrides, expected_effort in cases:
        run_agent(
            loop_definition={
                "agents": {
                    "implement": {
                        "role": "implementation",
                        "adapter": "codex",
                        **agent_overrides,
                    }
                }
            },
            task={"id": "ISSUE-1"},
            step={"id": "implement", "agent": "implement", **step_overrides},
            context={},
            cwd=tmp_path,
        )
        command = calls[-1]
        assert command[command.index("-c") + 1] == f"model_reasoning_effort={expected_effort}"


def test_codex_agent_adapter_uses_codex_default_reasoning_effort_when_unspecified(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr("loop.llm.subprocess.run", fake_run)
    monkeypatch.delenv("LOOP_CODEX_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("LOOP_CODEX_EXTRA_ARGS", raising=False)

    response = run_agent(
        loop_definition={
            "agents": {
                "implement": {
                    "role": "implementation",
                    "adapter": "codex",
                }
            }
        },
        task={"id": "ISSUE-1"},
        step={"id": "implement", "agent": "implement"},
        context={},
        cwd=tmp_path,
    )

    assert response["status"] == "success"
    command = calls[0]
    assert "-c" not in command
    assert not any(argument.startswith("model_reasoning_effort=") for argument in command)
def test_build_context_compacts_large_events(tmp_path: Path) -> None:
    event = {
        "type": "agent_response",
        "step": "implement",
        "created_at": "2026-08-22T00:00:00Z",
        "message": "x" * (MAX_EVENT_STRING_CHARS + 1),
        "details": {str(index): "y" * MAX_EVENT_STRING_CHARS for index in range(7)},
    }

    context = build_context(task={}, step={}, events=[event], workspace=tmp_path)

    compacted = context["recent_events"][0]
    assert compacted["type"] == "agent_response"
    assert compacted["step"] == "implement"
    assert len(compacted["summary"]) <= MAX_EVENT_CHARS + 1
    assert compacted["summary"].endswith("…")


def test_policy_respects_max_fix_attempts(tmp_path: Path) -> None:
    loop_path = tmp_path / "loop.yaml"
    task_path = tmp_path / "task.yaml"
    runs_root = tmp_path / "runs"
    loop_path.write_text(
        """
version: 1
id: retry
limits:
  max_iterations: 10
  max_fix_attempts: 1
steps:
  - id: observe
    kind: commands
    run:
      - "python -c 'import sys; sys.exit(1)' # test"
    on_success: done
    on_failure: decide
  - id: decide
    kind: policy
    routes:
      - when: test_feedback
        next: observe
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
id: ISSUE-3
source:
  type: github_issue
  repo: owner/repo
  issue_number: 3
status: pending
phase: spec
priority: normal
loop: retry
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

    assert result["status"] == "human"
    state = json.loads((Path(result["run_dir"]) / "state.json").read_text(encoding="utf-8"))
    assert state["feedback_attempts"]["test_feedback"] == 2


def test_taqt_task_run_maps_human_terminal_to_blocked_task(tmp_path: Path) -> None:
    loop_root = tmp_path / "loops"
    task_root = tmp_path / "tasks"
    loop_root.mkdir()
    task_root.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
  deepseek:
    loop: development_feedback_loop_deepseek
    codex_home: ~/.codex-deepseek
    env_key: DEEPSEEK_API_KEY
""",
        encoding="utf-8",
    )
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
            "--skip-readiness-check",
        ]
    )

    assert exit_code == 0
    task = load_document(task_path)
    assert task["status"] == "blocked"
    assert task["phase"] == "human"
    assert task["blocked_reason"] == "human escalation required"
    assert task["self_improvement"]["event"] == "loop_human"
    assert task["self_improvement"]["run_path"]
    assert Path(task["self_improvement"]["request_path"]).is_file()


def test_taqt_task_run_deepseek_profile_injects_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    loop_root = tmp_path / "loops"
    task_root = tmp_path / "tasks"
    deepseek_home = tmp_path / "deepseek-home"
    runs_root = tmp_path / "runs"
    loop_root.mkdir()
    task_root.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        """
profiles:
  main:
    loop: development_feedback_loop
  deepseek:
    loop: development_feedback_loop_deepseek
    codex_home: ~/.codex-deepseek
    env_key: DEEPSEEK_API_KEY
""",
        encoding="utf-8",
    )
    (loop_root / "development_feedback_loop_deepseek.yaml").write_text(
        """
version: 1
id: development_feedback_loop_deepseek
steps:
  - id: done
    kind: terminal
""",
        encoding="utf-8",
    )
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=21,
        loop="development_feedback_loop",
        task_root=task_root,
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "qwen-secret")

    calls: list[dict[str, object]] = []

    def fake_run_loop(**kwargs):
        calls.append(kwargs)
        return {"status": "done", "run_dir": str(runs_root / "run")}

    monkeypatch.setattr("taqt.task_run.run_loop", fake_run_loop)

    exit_code = task_run_main(
        [
            str(task_path),
            "--loop-root",
            str(loop_root),
            "--runs-root",
            str(runs_root),
            "--workspace",
            str(tmp_path),
            "--skip-readiness-check",
            "--profile",
            "deepseek",
            "--codex-home",
            str(deepseek_home),
        ]
    )

    assert exit_code == 0
    assert calls[0]["loop_path"].name == "development_feedback_loop_deepseek.yaml"
    assert calls[0]["child_environment"]["DEEPSEEK_API_KEY"] == "secret"
    assert calls[0]["child_environment"]["OPENROUTER_API_KEY"] == "qwen-secret"
    assert calls[0]["child_environment"]["CODEX_HOME"] == str(deepseek_home)


def test_taqt_task_run_rejects_task_locked_by_another_worker(tmp_path: Path) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=14,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )
    task["status"] = "running"
    task["worker"] = {"id": "other", "heartbeat_at": "2026-01-01T00:00:00+00:00"}
    task_path.write_text(
        yaml.safe_dump(task, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    exit_code = task_run_main([str(task_path), "--task-root", str(tmp_path), "--worker-id", "local"])

    assert exit_code == 2


def test_taqt_task_run_rejects_mismatched_resume_dir(tmp_path: Path) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=15,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )
    task["run"]["id"] = "expected"
    task_path.write_text(
        yaml.safe_dump(task, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    resume_dir = tmp_path / "other"
    resume_dir.mkdir()
    (resume_dir / "state.json").write_text("{}", encoding="utf-8")

    exit_code = task_run_main([str(task_path), "--task-root", str(tmp_path), "--resume", str(resume_dir)])

    assert exit_code == 2


def test_next_pending_task_prefers_high_priority(tmp_path: Path) -> None:
    create_issue_task(
        repo="owner/repo",
        issue_number=10,
        loop="development_feedback_loop",
        priority="low",
        task_root=tmp_path,
    )
    high_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=11,
        loop="development_feedback_loop",
        priority="high",
        task_root=tmp_path,
    )

    selected = next_pending_task(tmp_path)

    assert selected is not None
    assert selected[0] == high_path


def test_upsert_issue_task_updates_issue_metadata(tmp_path: Path) -> None:
    path, task, created = upsert_issue_task(
        repo="owner/repo",
        issue_number=12,
        loop="development_feedback_loop",
        issue_title="Add profile",
        issue_body="Body",
        issue_labels=["taqt"],
        task_root=tmp_path,
    )

    assert created is True
    assert task["branch_summary"] == "Add profile"
    assert load_document(path)["input"]["issue"]["labels"] == ["taqt"]

    _path, updated, created = upsert_issue_task(
        repo="owner/repo",
        issue_number=12,
        loop="development_feedback_loop",
        issue_title="Add profile v2",
        issue_body="Body v2",
        issue_labels=["taqt", "ready"],
        task_root=tmp_path,
    )

    assert created is False
    assert updated["input"]["issue"]["body"] == "Body v2"


def test_readiness_errors_require_acceptance_criteria_and_dod(tmp_path: Path) -> None:
    _path, task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=13,
        loop="development_feedback_loop",
        issue_title="Add profile",
        issue_body="""
## Acceptance Criteria
- User can save a profile.

## Definition of Done
- Tests and docs are updated.
""",
        task_root=tmp_path,
    )

    assert readiness_errors(task, workspace=tmp_path) == []
    assert readiness_warnings(task, workspace=tmp_path) == []

    _path, incomplete, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=14,
        loop="development_feedback_loop",
        issue_title="Incomplete",
        issue_body="Need this soon.",
        task_root=tmp_path,
    )

    assert readiness_errors(incomplete, workspace=tmp_path) == [
        "missing issue section: AC",
        "missing issue section: DoD",
    ]


def test_readiness_errors_follow_research_template(tmp_path: Path) -> None:
    _path, task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=15,
        loop="development_feedback_loop",
        issue_title="Research",
        issue_body="""
## 調べたいこと
- Compare options.

## 完了条件
- Decision is documented.
""",
        task_root=tmp_path,
    )

    assert readiness_errors(task, workspace=tmp_path) == []

    _path, incomplete, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=16,
        loop="development_feedback_loop",
        issue_title="Research incomplete",
        issue_body="""
## 調べたいこと
- Compare options.
""",
        task_root=tmp_path,
    )

    assert readiness_errors(incomplete, workspace=tmp_path) == ["missing issue section: 完了条件"]


def test_readiness_warnings_follow_bug_template(tmp_path: Path) -> None:
    _path, task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=17,
        loop="development_feedback_loop",
        issue_title="Bug",
        issue_body="""
## 概要
Save fails.

## 再現手順
-
""",
        task_root=tmp_path,
    )

    assert readiness_errors(task, workspace=tmp_path) == []
    assert readiness_warnings(task, workspace=tmp_path) == ["missing issue section: 再現手順"]


def test_task_run_moves_task_missing_readiness_inputs_to_triage(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=18,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    exit_code = task_run_main(
        [
            str(task_path),
            "--task-root",
            str(tmp_path),
            "--workspace",
            str(tmp_path),
            "--runs-root",
            str(tmp_path / "runs"),
        ]
    )

    assert exit_code == 2
    task = load_document(task_path)
    assert task["status"] == "pending"
    assert task["phase"] == "triage"
    assert "missing issue section: AC" in task["blocked_reason"]
    assert task["self_improvement"]["event"] == "readiness_failed"
    assert task["self_improvement"]["issue_number"] == 18
    assert Path(task["self_improvement"]["request_path"]).is_file()
    assert "Self-improvement requested" in capsys.readouterr().out


def test_task_decompose_creates_five_minute_slice_tasks(tmp_path: Path, capsys) -> None:
    task_path, task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=19,
        loop="development_feedback_loop",
        issue_title="Large task",
        issue_body="""
## AC
- First behavior works.
- Second behavior works.

## DoD
- Verified.
""",
        task_root=tmp_path,
    )

    assert decomposition_errors(task, workspace=tmp_path) == [
        "task requires decomposition into 2 slices capped at 5 minutes"
    ]
    assert task_decompose_main([str(task_path), "--task-root", str(tmp_path), "--execute"]) == 0

    parent = load_document(task_path)
    first = load_document(tmp_path / "ISSUE-19-01.yaml")
    second = load_document(tmp_path / "ISSUE-19-02.yaml")
    assert parent["phase"] == "decomposed"
    assert [slice_item["task_id"] for slice_item in parent["plan"]["slices"]] == [
        "ISSUE-19-01",
        "ISSUE-19-02",
    ]
    assert first["slice"]["estimate_minutes"] == 5
    assert first["slice"]["title"] == "First behavior works."
    assert second["slice"]["title"] == "Second behavior works."
    assert readiness_errors(first, workspace=tmp_path) == []
    assert "decompose into 2 slices capped at 5 minutes" in capsys.readouterr().out


def test_task_run_requires_decomposition_for_large_ready_task(tmp_path: Path) -> None:
    task_path, _task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=20,
        loop="development_feedback_loop",
        issue_title="Large task",
        issue_body="""
## AC
- First behavior works.
- Second behavior works.

## DoD
- Verified.
""",
        task_root=tmp_path,
    )

    exit_code = task_run_main([str(task_path), "--task-root", str(tmp_path), "--workspace", str(tmp_path)])

    assert exit_code == 2
    task = load_document(task_path)
    assert task["status"] == "pending"
    assert task["phase"] == "triage"
    assert "requires decomposition into 2 slices" in task["blocked_reason"]


def test_git_and_pr_scripts_are_dry_run_by_default(tmp_path: Path, capsys) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=42,
        loop="development_feedback_loop",
        branch_summary="Add User",
        task_root=tmp_path,
    )

    assert issue_branch(task) == "dev/#42_add_user"
    task["branch"] = "issue-42-explicit-branch"
    assert issue_branch(task) == "issue-42-explicit-branch"
    task.pop("branch")
    assert git_worktree_main([str(task_path), "--base", "main"]) == 0
    assert git_push_main([str(task_path), "--remote", "origin"]) == 0
    assert github_pr_main([str(task_path), "--base", "main", "--draft"]) == 0

    output = capsys.readouterr().out
    assert "git worktree add -B dev/#42_add_user" in output
    assert "git push -u origin dev/#42_add_user" in output
    assert "gh pr create" in output
    assert "--draft" in output


def test_github_merge_is_dry_run_by_default(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=44,
        loop="development_feedback_loop",
        branch_summary="Merge Flow",
        task_root=tmp_path,
    )

    assert github_merge_main([str(task_path), "--strategy", "squash", "--delete-branch"]) == 0

    output = capsys.readouterr().out
    assert "gh pr checks dev/#44_merge_flow --repo owner/repo --required --watch" in output
    assert "gh pr merge dev/#44_merge_flow --repo owner/repo --squash --delete-branch" in output


def test_github_merge_finds_open_pr_by_head_branch(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = '[{"number": 134, "url": "https://example.test/pull/134", "isDraft": false}]'
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr("taqt.github_merge.subprocess.run", fake_run)

    pr = find_pr(repo="owner/repo", branch="issue-133-taqt-loop-engineering", cwd=tmp_path)

    assert pr == {"number": 134, "url": "https://example.test/pull/134", "isDraft": False}
    command, kwargs = calls[0]
    assert command[:3] == ["gh", "pr", "list"]
    assert "--head" in command
    assert "issue-133-taqt-loop-engineering" in command
    assert kwargs["cwd"] == tmp_path


def test_github_merge_falls_back_when_required_checks_are_not_configured(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=49,
        loop="development_feedback_loop",
        branch_summary="Merge Flow",
        task_root=tmp_path,
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='[{"number": 149, "url": "https://example.test/pull/149", "isDraft": false}]',
                stderr="",
            )
        if command[:3] == ["gh", "pr", "checks"] and "--required" in command:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr="no required checks reported on the 'dev/#49_merge_flow' branch\n",
            )
        return subprocess.CompletedProcess(command, 0, stdout="ci\tpass\n", stderr="")

    monkeypatch.setattr("taqt.github_merge.subprocess.run", fake_run)

    assert github_merge_main([str(task_path), "--workspace", str(tmp_path), "--execute"]) == 0

    commands = [call[0] for call in calls]
    assert commands[1][:4] == ["gh", "pr", "checks", "149"]
    assert "--required" in commands[1]
    assert commands[2][:4] == ["gh", "pr", "checks", "149"]
    assert "--required" not in commands[2]
    assert commands[3][:4] == ["gh", "pr", "merge", "149"]
    assert "falling back to all PR checks" in capsys.readouterr().out


def test_github_merge_keeps_blocking_on_other_required_check_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=50,
        loop="development_feedback_loop",
        branch_summary="Merge Flow",
        task_root=tmp_path,
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='[{"number": 150, "url": "https://example.test/pull/150", "isDraft": false}]',
                stderr="",
            )
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ci failed\n")

    monkeypatch.setattr("taqt.github_merge.subprocess.run", fake_run)

    assert github_merge_main([str(task_path), "--workspace", str(tmp_path), "--execute"]) == 1

    commands = [call[0] for call in calls]
    assert commands[1][:4] == ["gh", "pr", "checks", "150"]
    assert "--required" in commands[1]
    assert len(commands) == 2


def test_task_cleanup_dry_run_prints_worktree_and_branch_cleanup(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=48,
        loop="development_feedback_loop",
        branch_summary="Cleanup Flow",
        task_root=tmp_path,
    )

    assert task_cleanup_main(
        [
            str(task_path),
            "--task-root",
            str(tmp_path),
            "--workspace",
            str(tmp_path / "worktree"),
            "--delete-local-branch",
            "--delete-remote-branch",
            "--force-worktree",
            "--mark-done",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert f"git worktree remove --force {tmp_path / 'worktree'}" in output
    assert "git branch -D dev/#48_cleanup_flow" in output
    assert "git push origin --delete dev/#48_cleanup_flow" in output
    assert "mark done: ISSUE-48" in output


def test_task_cleanup_execute_marks_child_and_parent_done(tmp_path: Path, monkeypatch) -> None:
    parent_path, _parent, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=49,
        loop="development_feedback_loop",
        issue_title="Large task",
        issue_body="""
## AC
- First behavior works.
- Second behavior works.

## DoD
- Verified.
""",
        task_root=tmp_path,
    )
    assert task_decompose_main([str(parent_path), "--task-root", str(tmp_path), "--execute"]) == 0
    first_path = tmp_path / "ISSUE-49-01.yaml"
    second_path = tmp_path / "ISSUE-49-02.yaml"
    second = load_document(second_path)
    second["status"] = "done"
    second["phase"] = "done"
    save_task(second_path, second)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    class Completed:
        returncode = 0

    monkeypatch.setattr("taqt.task_cleanup.subprocess.run", lambda *_args, **_kwargs: Completed())

    assert task_cleanup_main(
        [
            str(first_path),
            "--task-root",
            str(tmp_path),
            "--workspace",
            str(worktree),
            "--mark-done",
            "--sync-parent",
            "--execute",
        ]
    ) == 0

    assert load_document(first_path)["status"] == "done"
    assert load_document(parent_path)["status"] == "done"


def test_task_cleanup_recovers_stale_running_task(tmp_path: Path) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=54,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )
    task["status"] = "running"
    task["phase"] = "implement"
    state_path = tmp_path / "runs" / "ISSUE-54" / "state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"status": "running", "current_step": "implement"}),
        encoding="utf-8",
    )
    task["run"] = {"id": "stale-run", "state_path": str(state_path), "events_path": None}
    task["worker"] = {
        "id": "stale-worker",
        "started_at": "2000-01-01T00:00:00+00:00",
        "heartbeat_at": "2000-01-01T00:00:00+00:00",
    }
    save_task(task_path, task)

    assert task_cleanup_main(
        [
            "--task-root",
            str(tmp_path),
            "--recover-stale",
            "--stale-minutes",
            "1",
            "--execute",
        ]
    ) == 0

    recovered = load_document(task_path)
    assert recovered["status"] == "pending"
    assert recovered["phase"] == "triage"
    assert "stale run recovered" in recovered["blocked_reason"]
    recovered_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert recovered_state["status"] == "failed"
    assert "stale run recovered" in recovered_state["blocked_reason"]


def test_task_auto_dry_run_includes_merge_route(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=45,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    assert task_auto_main([str(task_path), "--merge", "--workspace", str(tmp_path)]) == 0

    output = capsys.readouterr().out
    assert "taqt.run" in output
    assert "taqt.commit" in output
    assert "taqt.push" in output
    assert "taqt.pr" in output
    assert "taqt.merge" in output


def test_task_auto_dry_run_includes_cleanup_after_merge(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=55,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    assert task_auto_main(
        [
            str(task_path),
            "--merge",
            "--cleanup-worktree",
            "--delete-local-branch",
            "--force-worktree",
            "--workspace",
            str(tmp_path / "worktree"),
        ]
    ) == 0

    output = capsys.readouterr().out
    assert output.index("taqt.merge") < output.index("taqt.cleanup")
    assert "--mark-done" in output
    assert "--sync-parent" in output
    assert "--delete-local-branch" in output
    assert "--force-worktree" in output


def test_task_worker_dry_run_plans_one_worktree_per_ready_task(tmp_path: Path, capsys) -> None:
    for issue_number in (50, 51):
        upsert_issue_task(
            repo="owner/repo",
            issue_number=issue_number,
            loop="development_feedback_loop",
            issue_title=f"Task {issue_number}",
            issue_body="""
## Acceptance Criteria
- Works.

## Definition of Done
- Verified.
""",
            task_root=tmp_path,
        )

    assert task_worker_main(["--task-root", str(tmp_path), "--jobs", "2", "--merge"]) == 0

    output = capsys.readouterr().out
    assert output.count("git worktree add -B") == 2
    assert ".taqt/worktrees/ISSUE-50" in output
    assert ".taqt/worktrees/ISSUE-51" in output
    assert output.count("taqt.task_auto") == 2


def test_task_worker_plans_decomposed_child_tasks(tmp_path: Path, capsys) -> None:
    task_path, _task, _created = upsert_issue_task(
        repo="owner/repo",
        issue_number=53,
        loop="development_feedback_loop",
        issue_title="Large task",
        issue_body="""
## AC
- First behavior works.
- Second behavior works.

## DoD
- Verified.
""",
        task_root=tmp_path,
    )
    assert task_decompose_main([str(task_path), "--task-root", str(tmp_path), "--execute"]) == 0
    capsys.readouterr()

    assert task_worker_main(["--task-root", str(tmp_path), "--jobs", "2"]) == 0

    output = capsys.readouterr().out
    assert ".taqt/worktrees/ISSUE-53-01" in output
    assert ".taqt/worktrees/ISSUE-53-02" in output
    assert "ISSUE-53: not decomposed enough" not in output


def test_task_worker_blocks_not_ready_tasks_when_executing(tmp_path: Path, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=52,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )

    assert task_worker_main(["--task-root", str(tmp_path), "--execute"]) == 2

    task = load_document(task_path)
    assert task["status"] == "pending"
    assert task["phase"] == "triage"
    assert "missing issue section: DoD" in task["blocked_reason"]
    assert "not ready" in capsys.readouterr().out


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


def test_git_commit_execute_requires_verified_run(tmp_path: Path, monkeypatch, capsys) -> None:
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=46,
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

    assert git_commit_main([str(task_path), "--workspace", str(tmp_path), "--execute", "--allow-branch-mismatch"]) == 2

    assert "without a verified taqt run state" in capsys.readouterr().out


def test_github_sync_dry_run_prints_progress_comment_only(tmp_path: Path, capsys) -> None:
    task_path, task = create_issue_task(
        repo="owner/repo",
        issue_number=47,
        loop="development_feedback_loop",
        task_root=tmp_path,
    )
    task["status"] = "done"
    task["phase"] = "done"
    task_path.write_text(
        yaml.safe_dump(task, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    assert github_sync_main([str(task_path)]) == 0

    output = capsys.readouterr().out
    assert "taqt task update" in output
    assert "gh issue edit" not in output
    assert "gh issue close" not in output


def test_run_report_renders_recent_events() -> None:
    report = render_report(
        {
            "task_id": "ISSUE-1",
            "status": "human",
            "current_step": "human",
            "iteration": 2,
            "last_feedback": "implementation_feedback",
        },
        [
            {
                "type": "decision",
                "step": "decide",
                "feedback": "implementation_feedback",
                "next": "human",
            }
        ],
    )

    assert "# taqt run ISSUE-1" in report
    assert "implementation_feedback -> human" in report


def test_run_report_renders_design_artifact_reference() -> None:
    report = render_report(
        {
            "task_id": "ISSUE-166",
            "status": "done",
            "current_step": "done",
            "iteration": 1,
            "last_feedback": None,
        },
        [
            {
                "type": "design_artifact",
                "step": "design",
                "artifact_path": "artifacts/design-decision.md",
                "summary": "Use the run artifact",
                "status": "created",
            }
        ],
    )

    assert "[artifacts/design-decision.md](artifacts/design-decision.md)" in report
    assert "(created) / Use the run artifact" in report


def test_run_report_renders_success_log_summary() -> None:
    report = render_report(
        {
            "task_id": "ISSUE-260",
            "status": "done",
            "current_step": "done",
            "iteration": 1,
            "last_feedback": None,
        },
        [
            {
                "type": "agent_response",
                "step": "implement",
                "response": {
                    "status": "success",
                    "mode": "codex",
                    "changed_paths": ["src/example.py"],
                    "artifact_path": "artifacts/result.md",
                    "log": {
                        "format": "success-summary-v1",
                        "validation": "pending",
                        "next_step": "observe",
                        "stdout": {"characters": 120},
                        "stderr": {"characters": 340},
                    },
                },
            }
        ],
    )

    assert "changed: 1 — `src/example.py`" in report
    assert "artifact: `artifacts/result.md`" in report
    assert "validation: pending" in report
    assert "next: `observe`" in report
    assert "omitted: stdout 120 chars; stderr 340 chars" in report


def test_loop_policy_is_migrated_from_design_doc_to_adr() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    old_design_doc = repository_root / "docs/design/#134.md"
    adr_0002 = repository_root / "docs/adr/0002-separate-adr-and-design-docs.md"
    adr_0012 = repository_root / "docs/adr/0012-adopt-taqt-centered-loop-engineering-policy.md"
    adr_index = repository_root / "docs/adr/README.md"
    design_root = repository_root / "docs/design"
    design_script = repository_root / "scripts/create_design_doc.py"
    design_skill = repository_root / ".agents/skills/design-doc-authoring"
    loop_definition = repository_root / ".taqt/loops/development_feedback_loop.yaml"
    readme = repository_root / "README.md"
    future_readme = repository_root / "docs/future/README.md"
    wireframe = repository_root / "docs/wireframes/task-redesign.md"

    assert not old_design_doc.exists()
    assert "> Status: Superseded by [ADR 0012]" in adr_0002.read_text(encoding="utf-8")

    migrated_policy = adr_0012.read_text(encoding="utf-8")
    assert "GitHub Issue を要求" in migrated_policy
    assert "`state.json`、`events.jsonl`、artifact" in migrated_policy
    assert "script adapter" in migrated_policy

    assert "ADR 0002" in adr_index.read_text(encoding="utf-8")
    assert "Superseded by ADR 0012" in adr_index.read_text(encoding="utf-8")
    assert not design_root.exists()
    assert not design_script.exists()
    assert not design_skill.exists()
    assert "docs/design/" not in loop_definition.read_text(encoding="utf-8")
    adr_0011 = repository_root / "docs/adr/0011-resolve-loop-reasoning-effort-in-codex-adapter.md"
    adr_0011_text = adr_0011.read_text(encoding="utf-8")
    assert "Design Doc #165" not in adr_0011_text
    assert "https://github.com/ANKM0/SIFTQ/issues/165" in adr_0011_text
    readme_text = readme.read_text(encoding="utf-8")
    assert "docs/design/" not in readme_text
    assert ".taqt/runs/" in readme_text
    assert "docs/adr/0012-adopt-taqt-centered-loop-engineering-policy.md" in readme_text
    future_text = future_readme.read_text(encoding="utf-8")
    assert "docs/design/" not in future_text
    assert "docs/requirements/" in future_text
    assert "docs/adr/" in future_text
    assert "taqt run artifact" in future_text
    wireframe_text = wireframe.read_text(encoding="utf-8")
    assert "external design document" not in wireframe_text
    assert "requirements" in wireframe_text
