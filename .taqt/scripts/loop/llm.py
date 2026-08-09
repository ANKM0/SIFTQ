import json
import os
import subprocess
from pathlib import Path
from typing import Any


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
    command = step.get("command") or agent.get("command") or os.environ.get("LOOP_LLM_COMMAND")
    timeout_seconds = int(step.get("timeout_seconds") or agent.get("timeout_seconds") or 1800)

    if not command:
        return {
            "status": "success",
            "mode": "dry_run",
            "agent": agent_id,
            "message": "No LLM command configured; dry-run agent response emitted.",
        }

    payload = {
        "task": task,
        "step": step,
        "agent": agent,
        "context": context,
        "prompt": _build_prompt(task=task, step=step, agent=agent, context=context),
    }
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
