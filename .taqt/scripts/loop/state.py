import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUCCESS_LOG_TAIL_CHARS = 2_000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def create_run_dir(task_id: str, runs_root: Path) -> Path:
    run_dir = runs_root / safe_id(task_id) / new_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "artifacts").mkdir()
    return run_dir


def load_state(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "state.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    state = dict(state)
    state["updated_at"] = utc_now()
    (run_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_event(run_dir: Path, event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    payload.setdefault("created_at", utc_now())
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def compact_successful_agent_response(
    response: dict[str, Any], *, next_step: str
) -> dict[str, Any]:
    """Replace successful agent transcripts with bounded diagnostic metadata."""
    if response.get("status") != "success":
        return dict(response)

    compacted = {
        key: value for key, value in response.items() if key not in {"stdout", "stderr"}
    }
    compacted["log"] = {
        "format": "success-summary-v1",
        "next_step": next_step,
        "validation": "pending",
        "stdout": _summarize_log_text(response.get("stdout")),
        "stderr": _summarize_log_text(response.get("stderr")),
    }
    return compacted


def _summarize_log_text(value: object) -> dict[str, str | int]:
    text = value if isinstance(value, str) else ""
    return {
        "characters": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "tail": text[-SUCCESS_LOG_TAIL_CHARS:],
    }


def load_events(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "events.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
