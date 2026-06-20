from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(".sympohy/config.yaml")


@dataclass(frozen=True, init=False)
class SympohyConfig:
    max_workers: int
    base_branch: str
    worktree_root: Path
    run_log_root: Path
    stale_status_after_minutes: int
    hooks: tuple[str, ...]
    review_max_rounds: int
    ci_retry_max_attempts: int
    merge_gate_retry_max_attempts: int | None
    stage_gate_command: str | None

    def __init__(
        self,
        *,
        max_workers: int,
        base_branch: str,
        worktree_root: Path,
        run_log_root: Path,
        stale_status_after_minutes: int,
        hooks: tuple[str, ...],
        review_max_rounds: int,
        ci_retry_max_attempts: int | None = None,
        merge_gate_retry_max_attempts: int | None = None,
        stage_gate_command: str | None = "task ai:sympohy:stage-gate",
        retry_max_attempts: int | None = None,
        final_verifier_fix_max_attempts: int | None = None,
    ) -> None:
        ci_attempts = (
            ci_retry_max_attempts
            if ci_retry_max_attempts is not None
            else retry_max_attempts
        )
        if ci_attempts is None:
            ci_attempts = 50
        merge_attempts = (
            merge_gate_retry_max_attempts
            if merge_gate_retry_max_attempts is not None
            else final_verifier_fix_max_attempts
        )
        if stale_status_after_minutes <= 0:
            raise ValueError("stale_status_after_minutes must be positive")
        if review_max_rounds <= 0:
            raise ValueError("review_max_rounds must be positive")
        if ci_attempts <= 0:
            raise ValueError("ci_retry_max_attempts must be positive")
        if merge_attempts is not None and merge_attempts < 0:
            raise ValueError("merge_gate_retry_max_attempts must be non-negative")

        object.__setattr__(self, "max_workers", max_workers)
        object.__setattr__(self, "base_branch", base_branch)
        object.__setattr__(self, "worktree_root", worktree_root)
        object.__setattr__(self, "run_log_root", run_log_root)
        object.__setattr__(
            self, "stale_status_after_minutes", stale_status_after_minutes
        )
        object.__setattr__(self, "hooks", hooks)
        object.__setattr__(self, "review_max_rounds", review_max_rounds)
        object.__setattr__(self, "ci_retry_max_attempts", ci_attempts)
        object.__setattr__(
            self, "merge_gate_retry_max_attempts", merge_attempts
        )
        object.__setattr__(self, "stage_gate_command", stage_gate_command)

    @property
    def retry_max_attempts(self) -> int:
        return self.ci_retry_max_attempts

    @property
    def final_verifier_fix_max_attempts(self) -> int:
        return self.merge_gate_retry_max_attempts or 0


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SympohyConfig:
    if not path.exists():
        return default_config()

    values = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    stale_status_after_minutes = int(values.get("stale_status_after_minutes", "30"))
    ci_retry_max_attempts = int(
        values.get("ci_retry_max_attempts", values.get("retry_max_attempts", "50"))
    )
    merge_gate_retry_max_attempts = None
    if "merge_gate_retry_max_attempts" in values:
        merge_gate_retry_max_attempts = int(values["merge_gate_retry_max_attempts"])
    elif "final_verifier_fix_max_attempts" in values:
        merge_gate_retry_max_attempts = int(values["final_verifier_fix_max_attempts"])
    stage_gate_command_value = values.get(
        "stage_gate_command",
        "task ai:sympohy:stage-gate",
    )
    stage_gate_command = (
        str(stage_gate_command_value).strip() if stage_gate_command_value else None
    )

    return SympohyConfig(
        max_workers=int(values.get("max_workers", "10")),
        base_branch=str(values.get("base_branch", "main")),
        worktree_root=Path(str(values.get("worktree_root", ".sympohy/worktrees"))),
        run_log_root=Path(str(values.get("run_log_root", ".sympohy/runs"))),
        stale_status_after_minutes=stale_status_after_minutes,
        hooks=tuple(values.get("hooks", ["task ci"])),
        review_max_rounds=int(values.get("review_max_rounds", "10")),
        ci_retry_max_attempts=ci_retry_max_attempts,
        merge_gate_retry_max_attempts=merge_gate_retry_max_attempts,
        stage_gate_command=stage_gate_command,
    )


def default_config() -> SympohyConfig:
    return SympohyConfig(
        max_workers=10,
        base_branch="main",
        worktree_root=Path(".sympohy/worktrees"),
        run_log_root=Path(".sympohy/runs"),
        stale_status_after_minutes=30,
        hooks=("task ci",),
        review_max_rounds=10,
        ci_retry_max_attempts=50,
        merge_gate_retry_max_attempts=None,
        stage_gate_command="task ai:sympohy:stage-gate",
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
