import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .guard import validate_commands


def run_agent(
    *,
    loop_definition: dict[str, Any],
    task: dict[str, Any],
    step: dict[str, Any],
    context: dict[str, Any],
    cwd: Path,
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
    if adapter == "codex" and not command:
        return _run_codex(payload=payload, agent_id=agent_id, agent=agent, step=step, cwd=cwd, timeout_seconds=timeout_seconds)

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
    }
    if parsed:
        response.update(parsed)
        if completed.returncode != 0:
            response["status"] = "failure"
    return response


def _run_codex(
    *,
    payload: dict[str, Any],
    agent_id: object,
    agent: dict[str, Any],
    step: dict[str, Any],
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    workspace = cwd.resolve()
    command = [
        "codex",
        "exec",
        "--cd",
        str(workspace),
        "--sandbox",
        str(step.get("sandbox") or agent.get("sandbox") or "workspace-write"),
    ]
    model = step.get("model") or agent.get("model") or os.environ.get("LOOP_CODEX_MODEL")
    if model:
        command.extend(["--model", str(model)])
    profile = step.get("profile") or agent.get("profile") or os.environ.get("LOOP_CODEX_PROFILE")
    if profile:
        command.extend(["--profile", str(profile)])
    extra_args = os.environ.get("LOOP_CODEX_EXTRA_ARGS")
    if extra_args:
        command.extend(shlex.split(extra_args))
    command.append("-")

    try:
        completed = subprocess.run(
            command,
            input=str(payload["prompt"]),
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return {
            "status": "failure",
            "mode": "codex",
            "agent": agent_id,
            "command": " ".join(command),
            "feedback": "unknown",
            "stderr": "codex executable was not found",
        }

    parsed = _parse_stdout(completed.stdout)
    response = {
        "status": "success" if completed.returncode == 0 else "failure",
        "mode": "codex",
        "agent": agent_id,
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if parsed:
        response.update(parsed)
        if completed.returncode != 0:
            response["status"] = "failure"
    if response["status"] != "success":
        response.setdefault("feedback", "unknown")
    return response


def _build_prompt(
    *,
    task: dict[str, Any],
    step: dict[str, Any],
    agent: dict[str, Any],
    context: dict[str, Any],
) -> str:
    role = agent.get("role") or step.get("agent") or "agent"
    return "\n".join(
        [
            f"Role: {role}",
            f"Task: {task.get('id')}",
            f"Step: {step.get('id')}",
            "",
            "Use the repository files and task context to complete this step.",
            "Make the minimal scoped code or test changes required for this step.",
            "Return JSON with at least a status field. Use status=success when the step is complete.",
            "Use status=failure and feedback when the loop should route to another step.",
            "",
            json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True),
        ]
    )


def _parse_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    status = payload.get("status")
    if status is not None and status not in {"success", "failure"}:
        payload["status"] = "failure"
        payload["feedback"] = payload.get("feedback") or "unknown"
    return payload
