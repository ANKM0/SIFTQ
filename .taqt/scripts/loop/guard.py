import hashlib
import subprocess
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


def workspace_snapshot(cwd: Path) -> dict[str, dict[str, str]]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return {}

    snapshot: dict[str, dict[str, str]] = {}
    for line in completed.stdout.splitlines():
        if not line:
            continue
        raw_path = line[3:] if len(line) > 3 else line
        if " -> " in raw_path:
            raw_path = raw_path.rsplit(" -> ", 1)[1]
        path = Path(raw_path)
        absolute = cwd / path
        snapshot[path.as_posix()] = {
            "status": line[:2],
            "digest": _digest_path(absolute),
        }
    return snapshot


def changed_paths(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> list[Path]:
    changed: list[Path] = []
    for path, metadata in after.items():
        if before.get(path) != metadata:
            changed.append(Path(path))
    return sorted(changed, key=lambda value: value.as_posix())


def validate_agent_changes(agent: dict[str, Any], paths: Iterable[Path]) -> None:
    for path in paths:
        validate_write_path(agent, path)


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


def _digest_path(path: Path) -> str:
    if not path.exists() or path.is_dir():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
