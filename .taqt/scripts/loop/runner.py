import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from .context import build_context
from .guard import changed_paths, validate_agent_changes, workspace_snapshot
from .llm import run_agent
from .observe import run_commands
from .policy import route_next_step
from .schema import load_document, validate_loop_definition, validate_task
from .state import (
    append_event,
    compact_successful_agent_response,
    create_run_dir,
    load_events,
    load_state,
    save_state,
)


TERMINAL_STEPS = {"done", "human", "failed"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop-runner")
    parser.add_argument("--loop", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--runs-root", type=Path, default=Path(".taqt/runs"))
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args(argv)

    result = run_loop(
        loop_path=args.loop,
        task_path=args.task,
        workspace=args.workspace,
        runs_root=args.runs_root,
        resume_dir=args.resume,
    )
    print(result["run_dir"])
    return 0 if result["status"] in {"done", "human"} else 1


def run_loop(
    *,
    loop_path: Path,
    task_path: Path,
    workspace: Path,
    runs_root: Path,
    resume_dir: Path | None = None,
    child_environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    loop_definition = load_document(loop_path)
    validate_loop_definition(loop_definition)
    task = load_document(task_path)
    validate_task(task)

    run_dir = resume_dir or create_run_dir(str(task["id"]), runs_root)
    if not resume_dir:
        shutil.copyfile(loop_path, run_dir / loop_path.name)
        shutil.copyfile(task_path, run_dir / "task.yaml")

    steps = {step["id"]: step for step in loop_definition["steps"]}
    state = load_state(run_dir) or {
        "task_id": task["id"],
        "loop_id": loop_definition["id"],
        "status": "running",
        "current_step": loop_definition["steps"][0]["id"],
        "iteration": 0,
        "last_feedback": None,
        "feedback_attempts": {},
    }
    if resume_dir and state.get("last_failed_step"):
        state["current_step"] = state["last_failed_step"]
        state["status"] = "running"
        state["loop_id"] = loop_definition["id"]
    limits = loop_definition.get("limits") if isinstance(loop_definition.get("limits"), dict) else {}
    max_iterations = int(limits.get("max_iterations", 12))
    max_fix_attempts = int(limits.get("max_fix_attempts", 3))

    while state["status"] == "running":
        if state["iteration"] >= max_iterations:
            state["status"] = "failed"
            state["blocked_reason"] = "max_iterations exceeded"
            append_event(run_dir, {"type": "blocked", "reason": state["blocked_reason"]})
            break

        step_id = state["current_step"]
        if step_id in TERMINAL_STEPS:
            state["status"] = step_id
            append_event(run_dir, {"type": "terminal", "step": step_id})
            break
        step = steps.get(step_id)
        if step is None:
            raise ValueError(f"unknown step: {step_id}")

        state["iteration"] += 1
        save_state(run_dir, state)
        append_event(run_dir, {"type": "step_started", "step": step_id, "kind": step["kind"]})

        next_step = _run_step(
            loop_definition=loop_definition,
            task=task,
            step=step,
            state=state,
            run_dir=run_dir,
            workspace=workspace,
            max_fix_attempts=max_fix_attempts,
            child_environment=child_environment,
        )
        state["current_step"] = next_step
        save_state(run_dir, state)

    save_state(run_dir, state)
    return {
        "status": state["status"],
        "phase": state.get("current_step"),
        "run_dir": str(run_dir),
    }


def _run_step(
    *,
    loop_definition: dict[str, Any],
    task: dict[str, Any],
    step: dict[str, Any],
    state: dict[str, Any],
    run_dir: Path,
    workspace: Path,
    max_fix_attempts: int,
    child_environment: Mapping[str, str] | None = None,
) -> str:
    kind = step["kind"]
    if kind == "commands":
        observation = run_commands(
            list(step.get("run") or []),
            cwd=workspace,
            timeout_seconds=int(step.get("timeout_seconds", 900)),
        )
        state["last_feedback"] = observation.get("feedback")
        append_event(run_dir, {"type": "observation", "step": step["id"], "observation": observation})
        return str(step.get("on_success" if observation["status"] == "success" else "on_failure"))

    if kind == "policy":
        next_step = route_next_step(step, state.get("last_feedback"))
        feedback = state.get("last_feedback") or "unknown"
        attempts = state.setdefault("feedback_attempts", {})
        attempts[feedback] = int(attempts.get(feedback, 0)) + 1
        if feedback != "unknown" and attempts[feedback] > max_fix_attempts:
            append_event(
                run_dir,
                {
                    "type": "decision",
                    "step": step["id"],
                    "feedback": feedback,
                    "next": "human",
                    "reason": "max_fix_attempts exceeded",
                },
            )
            return "human"
        append_event(
            run_dir,
            {
                "type": "decision",
                "step": step["id"],
                "feedback": feedback,
                "attempt": attempts[feedback],
                "next": next_step,
            },
        )
        return next_step

    if kind == "llm":
        agents = loop_definition.get("agents") if isinstance(loop_definition.get("agents"), dict) else {}
        agent_id = step.get("agent")
        agent = agents.get(agent_id, {}) if isinstance(agent_id, str) else {}
        before = workspace_snapshot(workspace)
        context = build_context(task=task, step=step, events=load_events(run_dir), workspace=workspace)
        response = run_agent(
            loop_definition=loop_definition,
            task=task,
            step=step,
            context=context,
            cwd=workspace,
            child_environment=child_environment,
        )
        after = workspace_snapshot(workspace)
        changed = changed_paths(before, after)
        response["changed_paths"] = [path.as_posix() for path in changed]
        try:
            validate_agent_changes(agent, changed)
        except ValueError as error:
            response["status"] = "failure"
            response["guard_error"] = str(error)
        if response["status"] == "success" and _is_design_step(step, agent_id, agent):
            try:
                artifact_path = _write_design_decision_artifact(
                    run_dir,
                    task=task,
                    step=step,
                    response=response,
                )
            except OSError as error:
                response["status"] = "failure"
                response["feedback"] = "implementation_feedback"
                response["artifact_error"] = str(error)
            else:
                response["artifact_path"] = artifact_path
                append_event(
                    run_dir,
                    {
                        "type": "design_artifact",
                        "step": step["id"],
                        "artifact_path": artifact_path,
                        "summary": _artifact_value(
                            response,
                            ("summary", "selected_option", "decision"),
                            "未記載",
                        ),
                        "status": "created",
                    },
                )
        next_step = str(step.get("next", step.get("on_pass", "done")))
        event_response = compact_successful_agent_response(response, next_step=next_step)
        append_event(
            run_dir,
            {"type": "agent_response", "step": step["id"], "response": event_response},
        )
        if response["status"] != "success":
            state["last_feedback"] = response.get("feedback") or "unknown"
            state["last_failed_step"] = step["id"]
            return str(step.get("on_failure", "human"))
        return next_step

    if kind == "terminal":
        return step["id"]

    raise ValueError(f"unsupported step kind: {kind}")


def _is_design_step(step: dict[str, Any], agent_id: object, agent: dict[str, Any]) -> bool:
    return (
        step.get("id") == "design"
        or agent_id == "design"
        or agent.get("role") == "design"
    )


def _write_design_decision_artifact(
    run_dir: Path,
    *,
    task: dict[str, Any],
    step: dict[str, Any],
    response: dict[str, Any],
) -> str:
    artifact = run_dir / "artifacts" / "design-decision.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    problem = _artifact_value(
        response,
        ("problem", "issue", "challenge"),
        "未記載",
    )
    constraints = _artifact_value(
        response,
        ("constraints", "constraint"),
        "未記載",
    )
    selected_option = _artifact_value(
        response,
        ("selected_option", "adopted_option", "decision", "summary"),
        "未記載",
    )
    rationale = _artifact_value(
        response,
        ("rationale", "reason", "decision_rationale"),
        "未記載",
    )
    rejected_options = _artifact_value(
        response,
        ("rejected_options", "rejected_option", "alternatives_rejected"),
        "未記載",
    )
    rejected_rationale = _artifact_value(
        response,
        ("rejected_rationale", "rejection_reason", "rejected_reasons"),
        "未記載",
    )
    impact_scope = _artifact_value(
        response,
        ("impact_scope", "impact", "scope"),
        "未記載",
    )
    validation_result = _artifact_value(
        response,
        ("validation_result", "validation", "verification", "tests"),
        "未記載",
    )
    open_items = _artifact_value(
        response,
        ("open_items", "unresolved", "open_questions"),
        "なし",
    )
    human_escalation = _artifact_value(
        response,
        ("human_escalation", "escalation", "escalate_to_human"),
        "なし",
    )
    content = "\n".join(
        [
            "# Design decision",
            "",
            f"- task: `{task.get('id')}`",
            f"- step: `{step.get('id')}`",
            "",
            "## 課題・制約",
            "",
            f"- 課題: {problem}",
            f"- 制約: {constraints}",
            "",
            "## 採用案と理由",
            "",
            f"- 採用案: {selected_option}",
            f"- 理由: {rationale}",
            "",
            "## 却下案と理由",
            "",
            f"- 却下案: {rejected_options}",
            f"- 理由: {rejected_rationale}",
            "",
            "## 影響範囲・検証結果",
            "",
            f"- 影響範囲: {impact_scope}",
            f"- 検証結果: {validation_result}",
            "",
            "## 未決事項または人間へのエスカレーション",
            "",
            f"- 未決事項: {open_items}",
            f"- 人間へのエスカレーション: {human_escalation}",
            "",
            "## Agent response",
            "",
            "```json",
            json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    artifact.write_text(content, encoding="utf-8")
    return "artifacts/design-decision.md"


def _artifact_value(
    response: dict[str, Any],
    keys: tuple[str, ...],
    default: str,
) -> str:
    for key in keys:
        value = response.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return default


if __name__ == "__main__":
    raise SystemExit(main())
