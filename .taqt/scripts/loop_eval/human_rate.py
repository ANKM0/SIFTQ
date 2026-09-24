import argparse
import collections
import json
from pathlib import Path
from typing import Any

DEFAULT_RUNS_ROOT = Path(".taqt/runs")

TERMINAL_STATUSES = ("done", "human", "failed")

CAUSE_CATEGORIES = (
    "routing",
    "verification",
    "review",
    "spec_product",
    "permission",
    "model_infra",
)

_VERIFICATION_FEEDBACK = {"verification_fix", "verification_human"}
_REVIEW_FEEDBACK = {"review_human", "review_fix"}
_SPEC_PRODUCT_FEEDBACK = {"specification_feedback", "product_feedback"}
_MODEL_INFRA_FEEDBACK = {"model_limit", "timeout"}
_PERMISSION_MARKERS = (
    "write scope",
    "permission",
    "readonly",
    "read-only",
    "filesystem",
    "outside agent",
)


def classify_cause(state: dict[str, Any]) -> str:
    feedback = str(state.get("last_feedback") or "")
    reason = str(state.get("blocked_reason") or "")
    haystack = f"{feedback}\n{reason}".lower()
    if any(marker in haystack for marker in _PERMISSION_MARKERS):
        return "permission"
    if feedback in _VERIFICATION_FEEDBACK:
        return "verification"
    if feedback in _REVIEW_FEEDBACK:
        return "review"
    if feedback in _SPEC_PRODUCT_FEEDBACK:
        return "spec_product"
    if feedback in _MODEL_INFRA_FEEDBACK:
        return "model_infra"
    if state.get("status") == "failed":
        return "model_infra"
    return "routing"


def load_states(runs_root: Path = DEFAULT_RUNS_ROOT) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for path in sorted(runs_root.glob("*/*/state.json")):
        try:
            states.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return states


def _period(state: dict[str, Any]) -> str:
    updated = str(state.get("updated_at") or "")
    return updated[:7] if len(updated) >= 7 else "unknown"


def summarize(states: list[dict[str, Any]]) -> dict[str, Any]:
    terminal = [state for state in states if state.get("status") in TERMINAL_STATUSES]
    totals = collections.Counter(str(state.get("status")) for state in terminal)
    total = len(terminal)
    human_states = [state for state in terminal if state.get("status") == "human"]
    causes = collections.Counter(classify_cause(state) for state in human_states)
    monthly: dict[str, dict[str, Any]] = {}
    for state in terminal:
        period = _period(state)
        bucket = monthly.setdefault(
            period, {"total": 0, "done": 0, "human": 0, "failed": 0, "human_causes": {}}
        )
        status = str(state.get("status"))
        bucket["total"] += 1
        bucket[status] += 1
        if status == "human":
            cause = classify_cause(state)
            bucket["human_causes"][cause] = bucket["human_causes"].get(cause, 0) + 1

    def rate(count: int) -> float:
        return round(count / total, 4) if total else 0.0

    return {
        "total": total,
        "done": totals.get("done", 0),
        "human": totals.get("human", 0),
        "failed": totals.get("failed", 0),
        "closure_rate": rate(totals.get("done", 0)),
        "human_rate": rate(totals.get("human", 0)),
        "human_causes": {category: causes.get(category, 0) for category in CAUSE_CATEGORIES},
        "monthly": monthly,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop-eval-human-rate")
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    args = parser.parse_args(argv)

    result = summarize(load_states(args.runs_root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
