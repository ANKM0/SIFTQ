from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from .config import CODEX_MODEL_ROLES, DEFAULT_CONFIG_PATH, load_config
from .core import (
    extract_acceptance_set,
    merge_gate_allows_merge,
    next_retry_action,
    parse_review_json,
    transition_labels,
    validate_commit_subject,
)
from .github import REQUIRED_LABELS, migrate_legacy_tasks, sync_labels
from .observability import ObservationStore, rebuild_observation_store
from .runner import refine_issue, resume_issue, run_issue, watch
from .stage_gate import main as stage_gate_main
from .systemd import (
    install_systemd_units,
    print_systemd_status,
    start_systemd_service,
    stop_systemd_service,
)


ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sympohy")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("setup")
    subcommands.add_parser("doctor")
    subcommands.add_parser("labels-sync")
    subcommands.add_parser("watch")
    subcommands.add_parser("systemd-install")
    subcommands.add_parser("systemd-start")
    subcommands.add_parser("systemd-stop")
    subcommands.add_parser("systemd-status")

    stage_gate_parser = subcommands.add_parser("stage-gate")
    stage_gate_parser.add_argument("--stage", required=True)
    stage_gate_parser.add_argument("--issue", required=True, type=int)
    stage_gate_parser.add_argument("--run-dir", required=True)
    stage_gate_parser.add_argument("--input")

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

    observe_replay_parser = subcommands.add_parser("observe-replay")
    observe_replay_parser.add_argument("--run-dir", required=True)
    observe_replay_parser.add_argument("--db")

    observe_query_parser = subcommands.add_parser("observe-query")
    observe_query_parser.add_argument("--db", required=True)
    observe_query_parser.add_argument("--issue", type=int)
    observe_query_parser.add_argument("--run-id")
    observe_query_parser.add_argument("--phase")
    observe_query_parser.add_argument("--event-type")
    observe_query_parser.add_argument("--status")
    observe_query_parser.add_argument("--text")
    observe_query_parser.add_argument("--limit", type=int, default=100)

    observe_analyze_parser = subcommands.add_parser("observe-analyze")
    observe_analyze_parser.add_argument("--db", required=True)
    observe_analyze_parser.add_argument("--issue", type=int)
    observe_analyze_parser.add_argument("--run-id")

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
    if args.command == "observe-replay":
        result = rebuild_observation_store(
            log_dir=Path(args.run_dir),
            db_path=None if args.db is None else Path(args.db),
        )
        print(
            json.dumps(
                {
                    "source_path": str(result.source_path),
                    "db_path": str(result.db_path),
                    "event_count": result.event_count,
                    "run_count": result.run_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "observe-query":
        with ObservationStore(Path(args.db)) as store:
            print(
                json.dumps(
                    store.search_events(
                        issue=args.issue,
                        run_id=args.run_id,
                        phase=args.phase,
                        event_type=args.event_type,
                        status=args.status,
                        text=args.text,
                        limit=args.limit,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    if args.command == "observe-analyze":
        with ObservationStore(Path(args.db)) as store:
            print(
                json.dumps(
                    store.analyze_failures(
                        issue=args.issue,
                        run_id=args.run_id,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    if args.command == "systemd-install":
        return install_systemd_units(ROOT)
    if args.command == "systemd-start":
        return start_systemd_service()
    if args.command == "systemd-stop":
        return stop_systemd_service()
    if args.command == "systemd-status":
        return print_systemd_status()
    if args.command == "stage-gate":
        stage_gate_args = [
            "--stage",
            args.stage,
            "--issue",
            str(args.issue),
            "--run-dir",
            args.run_dir,
        ]
        if args.input is not None:
            stage_gate_args.extend(["--input", args.input])
        return stage_gate_main(stage_gate_args)
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
    retry_profile = _retry_profile(config)
    checks = {
        ".sympohy/config.yaml": config_path.exists(),
        "max_workers <= 10": config.max_workers <= 10,
        "stale_status_after_minutes > 0": config.stale_status_after_minutes > 0,
        "watch_poll_interval_seconds > 0": config.watch_poll_interval_seconds > 0,
        f"retry profile {retry_profile}": retry_profile
        in {"conservative", "compatibility", "custom"},
        "default hook task ci": "task ci" in config.hooks,
        "stage gate command configured": config.stage_gate_command
        == "task ai:sympohy:stage-gate",
        "codex model roles configured": all(
            role in config.codex_models for role in CODEX_MODEL_ROLES
        ),
        "stage gate task declared": "ai:sympohy:stage-gate:"
        in (ROOT / "Taskfile.yml").read_text(encoding="utf-8"),
        "systemd service template": (
            ROOT / ".sympohy/systemd/sympohy-watch.service"
        ).exists(),
        "systemd service install target": "WantedBy=default.target"
        in (ROOT / ".sympohy/systemd/sympohy-watch.service").read_text(
            encoding="utf-8"
        ),
        "commit hook rejects invalid subject": not validate_commit_subject(
            "sympohy: bad"
        ),
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


def _retry_profile(config: object) -> str:
    if (
        getattr(config, "max_workers") == 3
        and getattr(config, "review_max_rounds") == 3
        and getattr(config, "ci_retry_max_attempts") == 10
        and getattr(config, "final_verifier_fix_max_attempts") == 2
    ):
        return "conservative"
    if (
        getattr(config, "max_workers") == 10
        and getattr(config, "review_max_rounds") == 10
        and getattr(config, "ci_retry_max_attempts") == 50
        and getattr(config, "final_verifier_fix_max_attempts") == 2
    ):
        return "compatibility"
    return "custom"


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
