from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(".sympohy/config.yaml")


@dataclass(frozen=True)
class SympohyConfig:
    max_workers: int
    base_branch: str
    worktree_root: Path
    run_log_root: Path
    stale_status_after_minutes: int
    hooks: tuple[str, ...]
    review_max_rounds: int
    retry_max_attempts: int
    final_verifier_fix_max_attempts: int


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SympohyConfig:
    if not path.exists():
        return default_config()

    values = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    stale_status_after_minutes = int(values.get("stale_status_after_minutes", "30"))
    if stale_status_after_minutes <= 0:
        raise ValueError("stale_status_after_minutes must be positive")

    final_verifier_fix_max_attempts = int(
        values.get("final_verifier_fix_max_attempts", "2")
    )
    if final_verifier_fix_max_attempts < 0:
        raise ValueError("final_verifier_fix_max_attempts must be non-negative")

    return SympohyConfig(
        max_workers=int(values.get("max_workers", "10")),
        base_branch=str(values.get("base_branch", "main")),
        worktree_root=Path(str(values.get("worktree_root", ".sympohy/worktrees"))),
        run_log_root=Path(str(values.get("run_log_root", ".sympohy/runs"))),
        stale_status_after_minutes=stale_status_after_minutes,
        hooks=tuple(values.get("hooks", ["task ci"])),
        review_max_rounds=int(values.get("review_max_rounds", "5")),
        retry_max_attempts=int(values.get("retry_max_attempts", "3")),
        final_verifier_fix_max_attempts=final_verifier_fix_max_attempts,
    )


def default_config() -> SympohyConfig:
    return SympohyConfig(
        max_workers=10,
        base_branch="main",
        worktree_root=Path(".sympohy/worktrees"),
        run_log_root=Path(".sympohy/runs"),
        stale_status_after_minutes=30,
        hooks=("task ci",),
        review_max_rounds=5,
        retry_max_attempts=3,
        final_verifier_fix_max_attempts=2,
    )


def _parse_simple_yaml(source: str) -> dict[str, object]:
    values: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in source.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list_key is not None:
            existing = values.setdefault(current_list_key, [])
            if not isinstance(existing, list):
                raise ValueError(f"{current_list_key} cannot be both scalar and list")
            existing.append(_clean_scalar(line[4:]))
            continue
        current_list_key = None
        if ":" not in line:
            raise ValueError(f"unsupported config line: {raw_line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            values[key] = []
            current_list_key = key
        else:
            values[key] = _clean_scalar(value)
    return values


def _clean_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'")
