from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


BLOCKED_COMMAND_FRAGMENTS = (
    "rm -rf /",
    "rm -rf .",
    "git reset --hard",
    "git clean -fd",
    "git clean -fdx",
    "git push --force",
    "git push --force-with-lease",
)


def validate_commands(commands: Iterable[str]) -> None:
    for command in commands:
        compact = " ".join(command.split())
        for fragment in BLOCKED_COMMAND_FRAGMENTS:
            if fragment in compact:
                raise ValueError(f"blocked command: {command}")


def validate_write_path(agent: dict[str, Any], path: Path) -> None:
    if agent.get("readonly"):
        raise ValueError(f"readonly agent cannot write: {path}")
    patterns = agent.get("writes") or []
    if not patterns:
        return
    normalized = path.as_posix()
    for pattern in patterns:
        prefix = str(pattern).removesuffix("**")
        if normalized.startswith(prefix):
            return
    raise ValueError(f"path outside agent write scope: {path}")
