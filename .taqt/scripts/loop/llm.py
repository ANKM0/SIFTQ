import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .guard import validate_commands


def run_agent(
    *,
    loop_definition: dict[str, Any],
    task: dict[str, Any],
    step: dict[str, Any],
    context: dict[str, Any],
    cwd: Path,
    child_environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    agents = loop_definition.get("agents") if isinstance(loop_definition.get("agents"), dict) else {}
    agent_id = step.get("agent")
    agent = agents.get(agent_id, {}) if isinstance(agent_id, str) else {}
    adapter = step.get("adapter") or agent.get("adapter") or os.environ.get("LOOP_LLM_ADAPTER")
    command = step.get("command") or agent.get("command") or os.environ.get("LOOP_LLM_COMMAND")
    timeout_seconds = int(step.get("timeout_seconds") or agent.get("timeout_seconds") or 1800)

    payload = {
        "task": task,
        "step": step,
        "agent": agent,
        "context": context,
        "prompt": _build_prompt(task=task, step=step, agent=agent, context=context),
    }
    if adapter == "opencode" and not command:
        return _run_opencode(
            payload=payload,
            agent_id=agent_id,
            agent=agent,
            step=step,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            child_environment=child_environment,
        )

    if not command:
        return {
            "status": "success",
            "mode": "dry_run",
            "agent": agent_id,
            "message": "No LLM command configured; dry-run agent response emitted.",
        }

    validate_commands([str(command)])
    completed = subprocess.run(
        str(command),
        input=json.dumps(payload, ensure_ascii=False),
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    parsed = _parse_stdout(completed.stdout)
    response = {
        "status": "success" if completed.returncode == 0 else "failure",
        "mode": "command",
        "agent": agent_id,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_json": bool(parsed),
    }
    if parsed:
        response.update(parsed)
        if completed.returncode != 0:
            response["status"] = "failure"
    return response


def _run_opencode(
    *,
    payload: dict[str, Any],
    agent_id: object,
    agent: dict[str, Any],
    step: dict[str, Any],
    cwd: Path,
    timeout_seconds: int,
    child_environment: Mapping[str, str] | None,
) -> dict[str, Any]:
    workspace = cwd.resolve()
    model = step.get("model") or agent.get("model") or os.environ.get("LOOP_OPENCODE_MODEL")
    if not model or "/" not in str(model):
        return {
            "status": "failure",
            "mode": "opencode",
            "agent": agent_id,
            "feedback": "unknown",
            "stderr": f"opencode adapter requires a full model id (provider/model); got: {model!r}",
        }
    command = [
        "opencode",
        "run",
        "-m",
        str(model),
        "--format",
        "json",
        "--dir",
        str(workspace),
        "--auto",
    ]
    variant = (
        step.get("reasoning_effort")
        or agent.get("reasoning_effort")
        or os.environ.get("LOOP_OPENCODE_VARIANT")
    )
    if variant:
        command.extend(["--variant", str(variant)])
    extra_args = os.environ.get("LOOP_OPENCODE_EXTRA_ARGS")
    if extra_args:
        command.extend(shlex.split(extra_args))
    command.extend(["--", str(payload["prompt"])])

    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **(child_environment or {})},
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return {
            "status": "failure",
            "mode": "opencode",
            "agent": agent_id,
            "command": shlex.join(command[:-1]),
            "feedback": "unknown",
            "stderr": "opencode executable was not found",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failure",
            "mode": "opencode",
            "agent": agent_id,
            "command": shlex.join(command[:-1]),
            "feedback": "timeout",
            "stderr": f"opencode timed out after {timeout_seconds}s",
        }

    parsed = _parse_opencode_stdout(completed.stdout)
    response = {
        "status": "success" if completed.returncode == 0 else "failure",
        "mode": "opencode",
        "agent": agent_id,
        "command": shlex.join(command[:-1]),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_json": bool(parsed),
        "usage": _sum_opencode_usage(completed.stdout),
    }
    if parsed:
        response.update(parsed)
        if completed.returncode != 0:
            response["status"] = "failure"
    if response["status"] != "success":
        response["feedback"] = response.get("feedback") or (
            "model_limit"
            if is_opencode_fallback_error(completed.stdout, completed.stderr)
            else "unknown"
        )
    return response


def is_opencode_fallback_error(stdout: str, stderr: str) -> bool:
    text = f"{stdout}\n{stderr}".lower()
    return any(
        token in text
        for token in (
            "usage limit",
            "usage_limit_reached",
            "rate_limit_reached",
            "rate limited",
            "too many requests",
            "429",
            "quota",
            "overloaded",
        )
    )


def _sum_opencode_usage(stdout: str) -> dict[str, Any]:
    totals = {
        "input": 0,
        "output": 0,
        "reasoning": 0,
        "cache_read": 0,
        "cache_write": 0,
        "total": 0,
    }
    cost = 0.0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        tokens = part.get("tokens")
        if isinstance(tokens, dict):
            totals["total"] += int(tokens.get("total") or 0)
            totals["input"] += int(tokens.get("input") or 0)
            totals["output"] += int(tokens.get("output") or 0)
            totals["reasoning"] += int(tokens.get("reasoning") or 0)
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            totals["cache_read"] += int(cache.get("read") or 0)
            totals["cache_write"] += int(cache.get("write") or 0)
        value = part.get("cost")
        if isinstance(value, (int, float)):
            cost += float(value)
    return {"tokens": totals, "cost": round(cost, 6)}


def _parse_opencode_stdout(stdout: str) -> dict[str, Any]:
    texts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
    return _parse_stdout("\n".join(texts))


IMPLEMENTATION_ROLES = {"implementation", "implementation_fixer"}

VERIFICATION_PRINCIPLES = (
    "Before declaring the step done, prove the change against the real artifact "
    "(run the feature, read the actual value, inspect the diff) per the "
    "`principle-prove-it-works` skill.",
    "When fixing, reproduce first and fix the root cause per the "
    "`principle-fix-root-causes` skill.",
    "Write tests for observable behavior, not implementation details, per the "
    "`principle-test-behavior-not-implementation` skill.",
)


def _verification_principles(role: str, *, readonly: bool) -> list[str]:
    if readonly or role in IMPLEMENTATION_ROLES:
        return list(VERIFICATION_PRINCIPLES)
    return []


def _build_prompt(
    *,
    task: dict[str, Any],
    step: dict[str, Any],
    agent: dict[str, Any],
    context: dict[str, Any],
) -> str:
    role = agent.get("role") or step.get("agent") or "agent"
    readonly = bool(agent.get("readonly"))
    review_contract = (
        "Return exactly one JSON object with status=success and verdict set to exactly one of "
        "approve, changes_requested, or human_required. Do not modify files."
        if readonly
        else "Return JSON with at least a status field. Use status=success when the step is complete."
    )
    lines = [
        f"Role: {role}",
        f"Task: {task.get('id')}",
        f"Step: {step.get('id')}",
        "",
        "Use the repository files and task context to complete this step.",
        "Make the minimal scoped code or test changes required for this step.",
        review_contract,
        "Use status=failure and feedback when the loop should route to another step.",
    ]
    lines.extend(_verification_principles(str(role), readonly=readonly))
    lines.extend(["", json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True)])
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_stdout(stdout: str) -> dict[str, Any]:
    payload = _extract_json_object(stdout.strip())
    if payload is None:
        return {}
    status = payload.get("status")
    if status is not None and status not in {"success", "failure"}:
        payload["status"] = "failure"
        payload["feedback"] = payload.get("feedback") or "unknown"
    return payload
