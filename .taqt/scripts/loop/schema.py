import json
from pathlib import Path
from typing import Any

import yaml


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def write_document(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def validate_loop_definition(loop: dict[str, Any]) -> None:
    if loop.get("version") != 1:
        raise ValueError("loop.version must be 1")
    if not isinstance(loop.get("id"), str) or not loop["id"]:
        raise ValueError("loop.id is required")
    steps = loop.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("loop.steps must be a non-empty list")

    _validate_limits(loop.get("limits"))
    agents = _validate_agents(loop.get("agents"))
    seen: set[str] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step {index} must be a mapping")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ValueError(f"step {index} id is required")
        if step_id in seen:
            raise ValueError(f"duplicate step id: {step_id}")
        seen.add(step_id)
        kind = step.get("kind")
        if kind not in {"commands", "policy", "llm", "terminal"}:
            raise ValueError(f"step {step_id} has unsupported kind: {kind}")

    step_ids = set(seen)
    for step in steps:
        _validate_step_contract(step, step_ids, agents)
    if not _has_terminal_path(steps, step_ids):
        raise ValueError("loop must have a reachable terminal step")


def validate_task(task: dict[str, Any]) -> None:
    if not isinstance(task.get("id"), str) or not task["id"]:
        raise ValueError("task.id is required")
    source = task.get("source")
    if not isinstance(source, dict) or source.get("type") != "github_issue":
        raise ValueError("task.source.type must be github_issue")
    if not source.get("repo") or not source.get("issue_number"):
        raise ValueError("task.source.repo and source.issue_number are required")
    if task.get("status") not in {"pending", "running", "blocked", "done", "failed"}:
        raise ValueError("task.status is invalid")
    branch_summary = task.get("branch_summary")
    if branch_summary is not None and not isinstance(branch_summary, str):
        raise ValueError("task.branch_summary must be a string when present")


def _validate_limits(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError("loop.limits must be a mapping")
    for key in ("max_iterations", "max_fix_attempts"):
        if key in value and (not isinstance(value[key], int) or value[key] < 1):
            raise ValueError(f"loop.limits.{key} must be a positive integer")


def _validate_agents(value: Any) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, dict):
        raise ValueError("loop.agents must be a mapping")
    agent_ids: set[str] = set()
    for agent_id, agent in value.items():
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("agent id must be a non-empty string")
        if not isinstance(agent, dict):
            raise ValueError(f"agent {agent_id} must be a mapping")
        agent_ids.add(agent_id)
        if "readonly" in agent and not isinstance(agent["readonly"], bool):
            raise ValueError(f"agent {agent_id}.readonly must be a boolean")
        if "command" in agent and not isinstance(agent["command"], str):
            raise ValueError(f"agent {agent_id}.command must be a string")
        for key in ("adapter", "model", "profile", "sandbox", "approval"):
            if key in agent and not isinstance(agent[key], str):
                raise ValueError(f"agent {agent_id}.{key} must be a string")
        writes = agent.get("writes")
        if writes is not None and (
            not isinstance(writes, list)
            or any(not isinstance(pattern, str) or not pattern for pattern in writes)
        ):
            raise ValueError(f"agent {agent_id}.writes must be a list of strings")
    return agent_ids


def _validate_step_contract(step: dict[str, Any], step_ids: set[str], agents: set[str]) -> None:
    step_id = step["id"]
    kind = step["kind"]
    if kind == "commands":
        commands = step.get("run")
        if not isinstance(commands, list) or not commands:
            raise ValueError(f"commands step {step_id} requires a non-empty run list")
        if any(not isinstance(command, str) or not command for command in commands):
            raise ValueError(f"commands step {step_id}.run must contain strings")
        _validate_step_ref(step, "on_success", step_ids)
        _validate_step_ref(step, "on_failure", step_ids)
        return

    if kind == "policy":
        routes = step.get("routes")
        if not isinstance(routes, list) or not routes:
            raise ValueError(f"policy step {step_id} requires routes")
        for route in routes:
            if not isinstance(route, dict):
                raise ValueError(f"policy step {step_id} route must be a mapping")
            if not isinstance(route.get("when"), str) or not route["when"]:
                raise ValueError(f"policy step {step_id} route requires when")
            _validate_step_ref(route, "next", step_ids)
        return

    if kind == "llm":
        agent = step.get("agent")
        if agent is not None and (not isinstance(agent, str) or agent not in agents):
            raise ValueError(f"llm step {step_id} references unknown agent: {agent}")
        if "command" in step and not isinstance(step["command"], str):
            raise ValueError(f"llm step {step_id}.command must be a string")
        for key in ("adapter", "model", "profile", "sandbox", "approval"):
            if key in step and not isinstance(step[key], str):
                raise ValueError(f"llm step {step_id}.{key} must be a string")
        for key in ("next", "on_pass", "on_failure"):
            if key in step:
                _validate_step_ref(step, key, step_ids)
        return


def _validate_step_ref(payload: dict[str, Any], key: str, step_ids: set[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must reference a step")
    if value not in step_ids:
        raise ValueError(f"{key} references unknown step: {value}")


def _has_terminal_path(steps: list[dict[str, Any]], step_ids: set[str]) -> bool:
    by_id = {step["id"]: step for step in steps}
    seen: set[str] = set()
    stack = [steps[0]["id"]]
    while stack:
        step_id = stack.pop()
        if step_id in seen:
            continue
        seen.add(step_id)
        step = by_id[step_id]
        if step["kind"] == "terminal":
            return True
        for next_step in _next_steps(step):
            if next_step in step_ids:
                stack.append(next_step)
    return False


def _next_steps(step: dict[str, Any]) -> list[str]:
    kind = step["kind"]
    if kind == "commands":
        return [step["on_success"], step["on_failure"]]
    if kind == "policy":
        return [route["next"] for route in step["routes"] if isinstance(route, dict)]
    if kind == "llm":
        return [
            str(step[key])
            for key in ("next", "on_pass", "on_failure")
            if key in step
        ] or ["done"]
    return []
