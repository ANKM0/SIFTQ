from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(".sympohy/config.yaml")
CODEX_MODEL_ROLES = (
    "default",
    "triage",
    "planning",
    "implementation",
    "fix",
    "review",
    "merge_readiness",
)
CODEX_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_FINAL_VERIFIER_FIX_MAX_ATTEMPTS = 2


@dataclass(frozen=True)
class CodexModelConfig:
    model: str
    reasoning_effort: str


DEFAULT_CODEX_MODELS = {
    "default": CodexModelConfig("gpt-5.5", "high"),
    "triage": CodexModelConfig("gpt-5.4-mini", "medium"),
    "planning": CodexModelConfig("gpt-5.5", "high"),
    "implementation": CodexModelConfig("gpt-5.5", "high"),
    "fix": CodexModelConfig("gpt-5.5", "high"),
    "review": CodexModelConfig("gpt-5.5", "xhigh"),
    "merge_readiness": CodexModelConfig("gpt-5.5", "xhigh"),
}


@dataclass(frozen=True, init=False)
class SympohyConfig:
    max_workers: int
    watch_poll_interval_seconds: int
    base_branch: str
    worktree_root: Path
    run_log_root: Path
    stale_status_after_minutes: int
    hooks: tuple[str, ...]
    review_max_rounds: int
    ci_retry_max_attempts: int
    final_verifier_fix_max_attempts: int
    stage_gate_command: str | None
    codex_models: dict[str, CodexModelConfig]

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
        stage_gate_command: str | None = "task ai:sympohy:stage-gate",
        retry_max_attempts: int | None = None,
        final_verifier_fix_max_attempts: int | None = None,
        watch_poll_interval_seconds: int = 60,
        codex_models: dict[str, CodexModelConfig] | None = None,
    ) -> None:
        ci_attempts = (
            ci_retry_max_attempts
            if ci_retry_max_attempts is not None
            else retry_max_attempts
        )
        if ci_attempts is None:
            ci_attempts = 50
        final_verifier_attempts = (
            DEFAULT_FINAL_VERIFIER_FIX_MAX_ATTEMPTS
            if final_verifier_fix_max_attempts is None
            else final_verifier_fix_max_attempts
        )
        if stale_status_after_minutes <= 0:
            raise ValueError("stale_status_after_minutes must be positive")
        if watch_poll_interval_seconds <= 0:
            raise ValueError("watch_poll_interval_seconds must be positive")
        if review_max_rounds <= 0:
            raise ValueError("review_max_rounds must be positive")
        if ci_attempts <= 0:
            raise ValueError("ci_retry_max_attempts must be positive")
        if final_verifier_attempts < 0:
            raise ValueError("final_verifier_fix_max_attempts must be non-negative")
        resolved_codex_models = _merge_codex_models(codex_models or {})

        object.__setattr__(self, "max_workers", max_workers)
        object.__setattr__(
            self, "watch_poll_interval_seconds", watch_poll_interval_seconds
        )
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
            self, "final_verifier_fix_max_attempts", final_verifier_attempts
        )
        object.__setattr__(self, "stage_gate_command", stage_gate_command)
        object.__setattr__(self, "codex_models", resolved_codex_models)

    @property
    def retry_max_attempts(self) -> int:
        return self.ci_retry_max_attempts

    def codex_model_for(self, role: str) -> CodexModelConfig:
        return self.codex_models.get(role, self.codex_models["default"])


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SympohyConfig:
    if not path.exists():
        return default_config()

    values = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    stale_status_after_minutes = int(values.get("stale_status_after_minutes", "30"))
    ci_retry_max_attempts = int(
        values.get("ci_retry_max_attempts", values.get("retry_max_attempts", "50"))
    )
    final_verifier_fix_max_attempts = int(
        values.get(
            "final_verifier_fix_max_attempts",
            str(DEFAULT_FINAL_VERIFIER_FIX_MAX_ATTEMPTS),
        )
    )
    stage_gate_command_value = values.get(
        "stage_gate_command",
        "task ai:sympohy:stage-gate",
    )
    stage_gate_command = (
        str(stage_gate_command_value).strip() if stage_gate_command_value else None
    )

    return SympohyConfig(
        max_workers=int(values.get("max_workers", "10")),
        watch_poll_interval_seconds=int(
            values.get("watch_poll_interval_seconds", "60")
        ),
        base_branch=str(values.get("base_branch", "main")),
        worktree_root=Path(str(values.get("worktree_root", ".sympohy/worktrees"))),
        run_log_root=Path(str(values.get("run_log_root", ".sympohy/runs"))),
        stale_status_after_minutes=stale_status_after_minutes,
        hooks=tuple(values.get("hooks", ["task ci"])),
        review_max_rounds=int(values.get("review_max_rounds", "10")),
        ci_retry_max_attempts=ci_retry_max_attempts,
        final_verifier_fix_max_attempts=final_verifier_fix_max_attempts,
        stage_gate_command=stage_gate_command,
        codex_models=_load_codex_models(values),
    )


def default_config() -> SympohyConfig:
    return SympohyConfig(
        max_workers=10,
        watch_poll_interval_seconds=60,
        base_branch="main",
        worktree_root=Path(".sympohy/worktrees"),
        run_log_root=Path(".sympohy/runs"),
        stale_status_after_minutes=30,
        hooks=("task ci",),
        review_max_rounds=10,
        ci_retry_max_attempts=50,
        final_verifier_fix_max_attempts=DEFAULT_FINAL_VERIFIER_FIX_MAX_ATTEMPTS,
        stage_gate_command="task ai:sympohy:stage-gate",
        codex_models=DEFAULT_CODEX_MODELS,
    )


def _load_codex_models(values: dict[str, object]) -> dict[str, CodexModelConfig]:
    role_values: dict[str, dict[str, str]] = {}
    for raw_key, raw_value in values.items():
        key = str(raw_key)
        if key.startswith("codex_model_"):
            role = key.removeprefix("codex_model_")
            field = "model"
        elif key.startswith("codex_reasoning_"):
            role = key.removeprefix("codex_reasoning_")
            field = "reasoning_effort"
        else:
            continue
        if role not in CODEX_MODEL_ROLES:
            raise ValueError(f"unsupported codex model role: {role}")
        role_values.setdefault(role, {})[field] = str(raw_value)

    loaded: dict[str, CodexModelConfig] = {}
    for role, fields in role_values.items():
        default = DEFAULT_CODEX_MODELS[role]
        reasoning_effort = fields.get("reasoning_effort", default.reasoning_effort)
        if reasoning_effort not in CODEX_REASONING_EFFORTS:
            raise ValueError(
                f"codex_reasoning_{role} must be one of "
                f"{', '.join(CODEX_REASONING_EFFORTS)}"
            )
        loaded[role] = CodexModelConfig(
            model=fields.get("model", default.model),
            reasoning_effort=reasoning_effort,
        )
    return _merge_codex_models(loaded)


def _merge_codex_models(
    overrides: dict[str, CodexModelConfig],
) -> dict[str, CodexModelConfig]:
    merged = dict(DEFAULT_CODEX_MODELS)
    for role in overrides:
        if role not in CODEX_MODEL_ROLES:
            raise ValueError(f"unsupported codex model role: {role}")
    merged.update(overrides)
    return merged


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
