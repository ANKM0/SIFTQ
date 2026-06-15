from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from .config import DEFAULT_CONFIG_PATH, load_config
from .core import (
    extract_acceptance_set,
    merge_gate_allows_merge,
    next_retry_action,
    parse_review_json,
    transition_labels,
    validate_commit_subject,
)
from .github import REQUIRED_LABELS, migrate_legacy_tasks, sync_labels
from .runner import refine_issue, resume_issue, run_issue, watch
from .systemd import install_systemd_units, print_systemd_status


ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sympohy")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("setup")
    subcommands.add_parser("doctor")
    subcommands.add_parser("labels-sync")
    subcommands.add_parser("watch")
    subcommands.add_parser("systemd-install")
    subcommands.add_parser("systemd-status")

    migrate_parser = subcommands.add_parser("migrate")
    migrate_parser.add_argument("issue", nargs="?")
    migrate_parser.add_argument("--all", action="store_true")
    migrate_parser.add_argument("--dry-run", action="store_true")
    migrate_parser.add_argument("--limit", type=int, default=500)

    refine_parser = subcommands.add_parser("refine")
    refine_parser.add_argument("issue")

    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("issue")

    resume_parser = subcommands.add_parser("resume")
    resume_parser.add_argument("issue")

    contract_parser = subcommands.add_parser("contract")
    contract_parser.add_argument("name")
    contract_parser.add_argument("payload")

    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "setup":
        return setup()
    if args.command == "doctor":
        return doctor(config_path=DEFAULT_CONFIG_PATH)
    if args.command == "labels-sync":
        sync_labels()
        return 0
    if args.command == "migrate":
        if args.issue is None and not args.all:
            parser.error("migrate requires ISSUE or --all")
        if args.issue is not None and args.all:
            parser.error("migrate accepts ISSUE or --all, not both")
        result = migrate_legacy_tasks(
            args.issue,
            dry_run=args.dry_run,
            limit=args.limit,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "refine":
        code, output = refine_issue(args.issue)
        print(output)
        return code
    if args.command == "run":
        return run_issue(args.issue, config)
    if args.command == "resume":
        return resume_issue(args.issue, config)
    if args.command == "watch":
        return watch(config)
    if args.command == "systemd-install":
        return install_systemd_units(ROOT)
    if args.command == "systemd-status":
        return print_systemd_status()
    if args.command == "contract":
        return contract(args.name, args.payload)

    parser.error(f"unsupported command: {args.command}")
    return 2


def setup() -> int:
    checks = {
        "gh": shutil.which("gh") is not None,
        "git": shutil.which("git") is not None,
        "codex": shutil.which("codex") is not None,
        "task": shutil.which("task") is not None,
        ".codex/rules/siftq.rules": (ROOT / ".codex/rules/siftq.rules").exists(),
        ".agents/skills": (ROOT / ".agents/skills").exists(),
        ".sympohy/config.yaml": (ROOT / ".sympohy/config.yaml").exists(),
    }
    _print_checks(checks)
    return 0 if all(checks.values()) else 1


def doctor(*, config_path: Path) -> int:
    config = load_config(config_path)
    checks = {
        ".sympohy/config.yaml": config_path.exists(),
        "max_workers <= 10": config.max_workers <= 10,
        "stale_status_after_minutes > 0": config.stale_status_after_minutes > 0,
        "default hook task ci": "task ci" in config.hooks,
        "systemd service template": (ROOT / ".sympohy/systemd/sympohy-watch.service").exists(),
        "systemd timer template": (ROOT / ".sympohy/systemd/sympohy-watch.timer").exists(),
        "commit hook rejects invalid subject": not validate_commit_subject("sympohy: bad"),
        "commit hook accepts repository subject": validate_commit_subject(
            "#74 feat(sympohy): add issue runner"
        ),
        "required labels declared": set(REQUIRED_LABELS) >= {
            "sympohy:pending",
            "sympohy:running",
            "sympohy:blocked",
            "sympohy:done",
            "sympohy:phase:triage",
            "sympohy:phase:implement",
            "sympohy:phase:hooks",
            "sympohy:phase:review",
            "sympohy:phase:fix",
            "sympohy:phase:finalize",
        },
        "codex uses user config": _runner_source_does_not_contain("--ignore-user-config"),
        "codex uses repo rules": _runner_source_does_not_contain("--ignore-rules"),
    }
    _print_checks(checks)
    return 0 if all(checks.values()) else 1


def contract(name: str, payload_source: str) -> int:
    payload = json.loads(payload_source)
    if name == "extract":
        result = extract_acceptance_set(payload["body"], payload.get("comments", []))
        print(
            json.dumps(
                None
                if result is None
                else {
                    "source": result.source,
                    "acceptance_criteria": list(result.acceptance_criteria),
                    "definition_of_done": list(result.definition_of_done),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if name == "transition":
        print(
            json.dumps(
                transition_labels(
                    payload.get("labels", []),
                    status=payload.get("status"),
                    phase=payload.get("phase"),
                ),
                ensure_ascii=False,
            )
        )
        return 0
    if name == "review":
        result = parse_review_json(payload["review"])
        print(json.dumps({"approved": result.approved, "blocking": len(result.blocking_findings)}))
        return 0
    if name == "retry":
        print(next_retry_action(int(payload["attempts"]), int(payload.get("max_attempts", 3))))
        return 0
    if name == "merge-gate":
        review = parse_review_json(payload["review"])
        print(
            json.dumps(
                {
                    "allowed": merge_gate_allows_merge(
                        final_verifier=payload["final_verifier"],
                        github_checks_status=payload["github_checks_status"],
                        review_result=review,
                    )
                }
            )
        )
        return 0
    raise ValueError(f"unknown contract: {name}")


def _print_checks(checks: dict[str, bool]) -> None:
    for name, passed in checks.items():
        status = "ok" if passed else "missing"
        print(f"{status}\t{name}")


def _runner_source_does_not_contain(term: str) -> bool:
    return term not in (ROOT / "scripts/sympohy/runner.py").read_text(encoding="utf-8")
