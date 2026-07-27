from __future__ import annotations

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

    if not command:
        return {
            "status": "success",
            "mode": "dry_run",
            "agent": agent_id,
            "message": "No LLM command configured; dry-run agent response emitted.",
        }

    payload = json.dumps({"task": task, "step": step, "context": context}, ensure_ascii=False)
    completed = subprocess.run(
        str(command),
        input=payload,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "status": "success" if completed.returncode == 0 else "failure",
        "mode": "command",
        "agent": agent_id,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
