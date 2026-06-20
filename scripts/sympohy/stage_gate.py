from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence


STAGE_STATUSES = {"pass", "retry", "block"}
ARTIFACT_STAGE_PREFIXES = {
    "requirements": "docs/requirements/",
    "design": "docs/design/",
    "wireframes": "docs/wireframes/",
    "adr": "docs/adr/",
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sympohy stage-gate")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args(argv)

    context = _read_context(args.input)
    result = evaluate_stage(
        args.stage,
        issue_number=args.issue,
        run_dir=args.run_dir,
        context=context,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"pass", "retry", "block"} else 2


def evaluate_stage(
    stage: str,
    *,
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
) -> dict[str, object]:
    normalized_stage = stage.strip().lower().replace("_", "-")
    if normalized_stage in {"request-elaboration", "triage"}:
        return _request_elaboration_gate(normalized_stage, issue_number, run_dir, context)
    if normalized_stage in ARTIFACT_STAGE_PREFIXES:
        return _artifact_gate(normalized_stage, issue_number, run_dir, context)
    if normalized_stage == "implementation":
        return _implementation_gate(issue_number, run_dir, context)
    if normalized_stage == "ci":
        return _boolean_gate(
            normalized_stage,
            issue_number,
            run_dir,
            context,
            key="ci_passed",
            retry_reason="CI failed; return to implementation loop.",
            return_to="implementation",
        )
    if normalized_stage == "review":
        return _boolean_gate(
            normalized_stage,
            issue_number,
            run_dir,
            context,
            key="review_approved",
            retry_reason="Review has critical/high/medium findings; return to implementation loop.",
            return_to="implementation",
        )
    if normalized_stage == "merge":
        return _merge_gate(issue_number, run_dir, context)
    return _result(
        "block",
        normalized_stage,
        issue_number,
        run_dir,
        reason=f"Unknown stage gate: {stage}",
    )


def _request_elaboration_gate(
    stage: str,
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
) -> dict[str, object]:
    if _non_empty_list(context.get("acceptance_criteria")) and _non_empty_list(
        context.get("definition_of_done")
    ):
        return _result(
            "pass",
            stage,
            issue_number,
            run_dir,
            reason="Issue has both AC and DoD.",
        )
    return _result(
        "block",
        stage,
        issue_number,
        run_dir,
        reason="Issue must include both AC and DoD before the loop can start.",
    )


def _artifact_gate(
    stage: str,
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
) -> dict[str, object]:
    decisions = context.get("artifact_decisions")
    if not isinstance(decisions, Mapping):
        return _result(
            "retry",
            stage,
            issue_number,
            run_dir,
            reason=f"{stage} artifact decision is missing.",
            return_to=stage,
        )
    decision = decisions.get(stage)
    if not isinstance(decision, Mapping):
        return _result(
            "retry",
            stage,
            issue_number,
            run_dir,
            reason=f"{stage} artifact decision is missing.",
            return_to=stage,
        )

    mode = str(decision.get("mode", "")).strip().lower().replace("-", "_")
    if mode == "not_needed":
        if str(decision.get("reason", "")).strip():
            return _result(
                "pass",
                stage,
                issue_number,
                run_dir,
                reason=f"{stage} is explicitly not needed.",
            )
        return _result(
            "retry",
            stage,
            issue_number,
            run_dir,
            reason=f"{stage} not_needed decision requires a reason.",
            return_to=stage,
        )
    if mode in {"new", "existing"}:
        path = str(decision.get("path", "")).strip()
        expected_prefix = ARTIFACT_STAGE_PREFIXES[stage]
        workspace = str(context.get("workspace", "")).strip()
        if path.startswith(expected_prefix) and _path_exists(workspace, path):
            return _result(
                "pass",
                stage,
                issue_number,
                run_dir,
                reason=f"{stage} artifact evidence is present.",
                artifacts=[path],
            )
        if path.startswith(expected_prefix):
            return _result(
                "retry",
                stage,
                issue_number,
                run_dir,
                reason=f"{stage} evidence path does not exist: {path}",
                return_to=stage,
            )
        return _result(
            "retry",
            stage,
            issue_number,
            run_dir,
            reason=f"{stage} evidence must reference {expected_prefix}...",
            return_to=stage,
        )
    return _result(
        "retry",
        stage,
        issue_number,
        run_dir,
        reason=f"{stage} decision mode must be new, existing, or not_needed.",
        return_to=stage,
    )


def _implementation_gate(
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
) -> dict[str, object]:
    if str(context.get("branch", "")).strip() and int(context.get("total_steps", 0)) > 0:
        return _result(
            "pass",
            "implementation",
            issue_number,
            run_dir,
            reason="Implementation plan and branch are present.",
        )
    return _result(
        "retry",
        "implementation",
        issue_number,
        run_dir,
        reason="Implementation requires a branch and at least one logical step.",
        return_to="implementation",
    )


def _merge_gate(
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
) -> dict[str, object]:
    missing = [
        label
        for label, key in (
            ("AC", "acceptance_criteria_satisfied"),
            ("DoD", "definition_of_done_satisfied"),
            ("CI", "ci_passed"),
            ("review", "review_approved"),
        )
        if not bool(context.get(key))
    ]
    if not missing:
        return _result(
            "pass",
            "merge",
            issue_number,
            run_dir,
            reason="AC, DoD, CI, and review evidence all passed.",
        )
    return _result(
        "retry",
        "merge",
        issue_number,
        run_dir,
        reason="Merge gate is missing passed evidence: " + ", ".join(missing),
        return_to="implementation",
    )


def _boolean_gate(
    stage: str,
    issue_number: int,
    run_dir: Path,
    context: Mapping[str, object],
    *,
    key: str,
    retry_reason: str,
    return_to: str,
) -> dict[str, object]:
    if bool(context.get(key)):
        return _result(
            "pass",
            stage,
            issue_number,
            run_dir,
            reason=f"{stage} evidence passed.",
        )
    return _result(
        "retry",
        stage,
        issue_number,
        run_dir,
        reason=retry_reason,
        return_to=return_to,
    )


def _result(
    status: str,
    stage: str,
    issue_number: int,
    run_dir: Path,
    *,
    reason: str,
    return_to: str | None = None,
    artifacts: Sequence[str] = (),
) -> dict[str, object]:
    if status not in STAGE_STATUSES:
        raise ValueError(f"unknown stage gate status: {status}")
    result: dict[str, object] = {
        "status": status,
        "stage": stage,
        "issue": issue_number,
        "run_dir": str(run_dir),
        "reason": reason,
        "artifacts": list(artifacts),
    }
    if return_to is not None:
        result["return_to"] = return_to
    return result


def _read_context(path: Path | None) -> Mapping[str, object]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("stage gate input must be a JSON object")
    context = payload.get("context", payload)
    if not isinstance(context, Mapping):
        raise ValueError("stage gate input context must be a JSON object")
    return context


def _non_empty_list(value: object) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


def _path_exists(workspace: str, relative_path: str) -> bool:
    if not workspace:
        return True
    if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        return False
    return (Path(workspace) / relative_path).exists()


if __name__ == "__main__":
    raise SystemExit(main())
