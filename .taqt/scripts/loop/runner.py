from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from .context import build_context
from .llm import run_agent
from .observe import run_commands
from .policy import route_next_step
from .schema import load_document, validate_loop_definition, validate_task
from .state import append_event, create_run_dir, load_events, load_state, save_state


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
    }
    limits = loop_definition.get("limits") if isinstance(loop_definition.get("limits"), dict) else {}
    max_iterations = int(limits.get("max_iterations", 12))

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
        )
        state["current_step"] = next_step
        save_state(run_dir, state)

    save_state(run_dir, state)
    return {"status": state["status"], "run_dir": str(run_dir)}


def _run_step(
    *,
    loop_definition: dict[str, Any],
    task: dict[str, Any],
    step: dict[str, Any],
    state: dict[str, Any],
    run_dir: Path,
    workspace: Path,
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
        append_event(run_dir, {"type": "decision", "step": step["id"], "feedback": state.get("last_feedback"), "next": next_step})
        return next_step

    if kind == "llm":
        context = build_context(task=task, step=step, events=load_events(run_dir), workspace=workspace)
        response = run_agent(
            loop_definition=loop_definition,
            task=task,
            step=step,
            context=context,
            cwd=workspace,
        )
        append_event(run_dir, {"type": "agent_response", "step": step["id"], "response": response})
        if response["status"] != "success":
            state["last_feedback"] = "unknown"
            return str(step.get("on_failure", "human"))
        return str(step.get("next", step.get("on_pass", "done")))

    if kind == "terminal":
        return step["id"]

    raise ValueError(f"unsupported step kind: {kind}")


if __name__ == "__main__":
    raise SystemExit(main())
