import argparse
import shutil
import time
from pathlib import Path
from typing import Any, Mapping

from .context import build_context
from .guard import changed_paths, validate_agent_changes, workspace_snapshot
from .llm import run_agent
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
from .verification import run_verification, validate_review


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
    max_provider_retries = int(limits.get("provider_retries", 3))

    while state["status"] == "running":
        step_id = state["current_step"]
        if step_id in TERMINAL_STEPS:
            state["status"] = step_id
            append_event(run_dir, {"type": "terminal", "step": step_id})
            break

        if state["iteration"] >= max_iterations:
            state["status"] = "failed"
            state["blocked_reason"] = "max_iterations exceeded"
            append_event(run_dir, {"type": "blocked", "reason": state["blocked_reason"]})
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
            max_provider_retries=max_provider_retries,
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
    max_provider_retries: int = 3,
    child_environment: Mapping[str, str] | None = None,
) -> str:
    kind = step["kind"]
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

    if kind == "verification":
        result = run_verification(cwd=workspace)
        state["last_feedback"] = result.get("feedback")
        state["last_verification"] = result
        append_event(run_dir, {"type": "verification", "step": step["id"], "result": result})
        if result["status"] == "fix":
            feedback = str(result.get("feedback") or "unknown")
            attempts = state.setdefault("feedback_attempts", {})
            attempts[feedback] = int(attempts.get(feedback, 0)) + 1
            if attempts[feedback] > max_fix_attempts:
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
        return str(step[f"on_{result['status']}"])

    if kind == "post_review":
        response = state.get("last_review_response")
        if not isinstance(response, dict):
            response = {}
        result = validate_review(
            response,
            changed_paths=response.get("changed_paths") if isinstance(response.get("changed_paths"), list) else [],
            cwd=workspace,
        )
        state["last_feedback"] = result.get("feedback")
        append_event(run_dir, {"type": "post_review", "step": step["id"], "result": result})
        return str(step[f"on_{result['status']}"])

    if kind == "llm":
        agents = loop_definition.get("agents") if isinstance(loop_definition.get("agents"), dict) else {}
        agent_id = step.get("agent")
        agent = agents.get(agent_id, {}) if isinstance(agent_id, str) else {}
        before = workspace_snapshot(workspace)
        context = build_context(task=task, step=step, events=load_events(run_dir), workspace=workspace)
        if state.get("last_verification"):
            context["last_verification"] = state["last_verification"]
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
        if agent.get("readonly"):
            state["last_review_response"] = response
        try:
            validate_agent_changes(agent, changed)
        except ValueError as error:
            response["status"] = "failure"
            response["guard_error"] = str(error)
            response["feedback"] = "scope_violation"
        next_step = str(step.get("next", step.get("on_pass", "done")))
        event_response = compact_successful_agent_response(response, next_step=next_step)
        append_event(
            run_dir,
            {"type": "agent_response", "step": step["id"], "response": event_response},
        )
        if agent.get("readonly"):
            return next_step
        if response["status"] != "success":
            feedback = str(response.get("feedback") or "unknown")
            state["last_feedback"] = feedback
            state["last_failed_step"] = step["id"]
            if feedback == "provider_error":
                provider_attempts = state.setdefault("provider_attempts", {})
                provider_attempts[step["id"]] = int(provider_attempts.get(step["id"], 0)) + 1
                if provider_attempts[step["id"]] <= max_provider_retries:
                    append_event(
                        run_dir,
                        {
                            "type": "provider_retry",
                            "step": step["id"],
                            "attempt": provider_attempts[step["id"]],
                            "reason": "provider_error",
                        },
                    )
                    time.sleep(min(30, 5 * provider_attempts[step["id"]]))
                    return step["id"]
                return "human"
            attempts = state.setdefault("feedback_attempts", {})
            attempts[feedback] = int(attempts.get(feedback, 0)) + 1
            if attempts[feedback] > max_fix_attempts:
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
            return str(step.get("on_failure", "human"))
        return next_step

    if kind == "terminal":
        return step["id"]

    raise ValueError(f"unsupported step kind: {kind}")


if __name__ == "__main__":
    raise SystemExit(main())
