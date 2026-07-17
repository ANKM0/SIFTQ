from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.sympohy.observability import (
    ObservationStore,
    _enforce_candidate_scope,
    rebuild_observation_store,
)


class SympohyObservabilityTest(unittest.TestCase):
    def test_replay_fixture_locks_schema_compatibility_and_rebuild_determinism(self) -> None:
        fixture_path = (
            Path(__file__).with_name("fixtures") / "observability_replay_issue_126.jsonl"
        )

        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            (log_dir / "events.jsonl").write_text(
                fixture_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            first = rebuild_observation_store(log_dir=log_dir)
            second_db = log_dir / "observations-copy.sqlite3"
            second = rebuild_observation_store(log_dir=log_dir, db_path=second_db)

            with ObservationStore(first.db_path) as store:
                analysis = store.analyze_failures(issue=126)
                proposal = store.propose_improvements(issue=126)
                application = store.apply_improvements(issue=126)
                runs = store.list_runs(issue=126)
                final_verifier_events = store.search_events(
                    issue=126,
                    phase="finalize",
                    event_type="codex",
                    limit=10,
                )
                recovery_events = store.search_events(
                    issue=126,
                    event_type="recovery",
                    limit=10,
                )
            first_dump = self._sqlite_dump(first.db_path)
            second_dump = self._sqlite_dump(second.db_path)

        self.assertEqual(first.event_count, 13)
        self.assertEqual(first.run_count, 6)
        self.assertEqual(second.event_count, 13)
        self.assertEqual(first_dump, second_dump)
        self.assertEqual(
            [run["run_id"] for run in runs],
            [
                "run-browser-1",
                "run-final-1",
                "run-final-2",
                "run-resume-1",
                "run-stale-1",
                "run-stale-2",
            ],
        )
        self.assertEqual(
            analysis["failure_kind_counts"],
            [
                {"kind": "recovery", "count": 2},
                {"kind": "browser", "count": 1},
                {"kind": "command", "count": 1},
                {"kind": "data", "count": 1},
                {"kind": "policy", "count": 1},
            ],
        )
        self.assertEqual(
            analysis["resolved_failures"][0]["failure_signatures"],
            ["command:task ci"],
        )
        self.assertEqual(
            sorted(
                chain["failure_signatures"][0]
                for chain in analysis["blocked_failures"]
            ),
            [
                "browser:console=2:page=1",
                "data:codex:final_verifier:invalid_json",
                "policy:stage_gate:review",
                "recovery:unsafe_recovery_blocked",
                "recovery:unsafe_recovery_blocked",
            ],
        )
        self.assertEqual(
            analysis["recurring_event_chain_patterns"][0],
            {
                "pattern": "recovery:unsafe_recovery_blocked",
                "count": 2,
                "run_ids": ["run-stale-1", "run-stale-2"],
            },
        )
        self.assertEqual(
            [bucket["phase"] for bucket in analysis["phase_dwell"]],
            ["finalize", "implement", "planning", "review"],
        )
        self.assertEqual(proposal["schema_version"], 1)
        self.assertEqual(proposal["issue"], 126)
        self.assertEqual(
            sorted(candidate["category"] for candidate in proposal["candidates"]),
            ["config", "docs", "hook", "prompt", "skill", "stage_gate", "test"],
        )
        self.assertEqual(application["schema_version"], 1)
        self.assertEqual(application["stop_after"], "verified_draft_pr")
        self.assertEqual(
            sorted(
                candidate["category"]
                for candidate in application["auto_apply_candidates"]
            ),
            ["config", "docs", "prompt", "test"],
        )
        self.assertEqual(
            sorted(
                candidate["category"]
                for candidate in application["manual_review_candidates"]
            ),
            ["hook", "skill", "stage_gate"],
        )
        self.assertEqual(
            [event["metadata"]["role"] for event in final_verifier_events],
            ["final_verifier", "final_verifier"],
        )
        self.assertEqual(
            [event["metadata"]["event"] for event in recovery_events],
            [
                "late_phase_recovery_resumed",
                "unsafe_recovery_blocked",
                "unsafe_recovery_blocked",
            ],
        )

    def test_rebuilds_deterministic_store_from_event_stream(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "run_id": "run-b",
                                "event_id": "run-b-000002",
                                "issue": 126,
                                "phase": "review",
                                "event_type": "review",
                                "status": "pass",
                                "attempt": 2,
                                "duration": 1.2,
                                "summary": "review passed",
                                "metadata": {"reviewer_role": "adversarial-review"},
                                "timestamp": "2026-07-16T10:00:02Z",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "run_id": "run-a",
                                "event_id": "run-a-000002",
                                "issue": 126,
                                "phase": "implement",
                                "event_type": "command",
                                "status": "success",
                                "attempt": 1,
                                "duration": 2.5,
                                "summary": "task ci passed",
                                "metadata": {"command": "task ci"},
                                "timestamp": "2026-07-16T10:00:01Z",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "run_id": "run-a",
                                "event_id": "run-a-000001",
                                "issue": 126,
                                "phase": "implement",
                                "event_type": "codex",
                                "status": "success",
                                "attempt": 1,
                                "duration": 3.0,
                                "summary": "implemented replay step",
                                "metadata": {"role": "implementation"},
                                "timestamp": "2026-07-16T10:00:00Z",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "run_id": "run-b",
                                "event_id": "run-b-000001",
                                "issue": 126,
                                "phase": "review",
                                "event_type": "stage_gate",
                                "status": "pass",
                                "attempt": None,
                                "duration": None,
                                "summary": "review stage gate passed",
                                "metadata": {"stage": "review"},
                                "timestamp": "2026-07-16T10:00:03Z",
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            first = rebuild_observation_store(log_dir=log_dir)
            second_db = log_dir / "observations-copy.sqlite3"
            second = rebuild_observation_store(log_dir=log_dir, db_path=second_db)

            with ObservationStore(first.db_path) as store:
                events = store.search_events(issue=126)
                runs = store.list_runs(issue=126)

            self.assertEqual(first.event_count, 4)
            self.assertEqual(first.run_count, 2)
            self.assertEqual(second.event_count, 4)
            self.assertEqual(
                [event["event_id"] for event in events],
                [
                    "run-a-000001",
                    "run-a-000002",
                    "run-b-000001",
                    "run-b-000002",
                ],
            )
            self.assertEqual(
                runs,
                [
                    {
                        "run_id": "run-a",
                        "issue": 126,
                        "event_count": 2,
                        "first_event_id": "run-a-000001",
                        "first_timestamp": "2026-07-16T10:00:00Z",
                        "last_event_id": "run-a-000002",
                        "last_timestamp": "2026-07-16T10:00:01Z",
                    },
                    {
                        "run_id": "run-b",
                        "issue": 126,
                        "event_count": 2,
                        "first_event_id": "run-b-000001",
                        "first_timestamp": "2026-07-16T10:00:03Z",
                        "last_event_id": "run-b-000002",
                        "last_timestamp": "2026-07-16T10:00:02Z",
                    },
                ],
            )

            self.assertEqual(self._sqlite_dump(first.db_path), self._sqlite_dump(second.db_path))

    def test_store_supports_search_and_aggregate_queries(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        self._event_json(
                            run_id="run-1",
                            event_id="run-1-000001",
                            event_type="codex",
                            status="success",
                            summary="implemented observation replay",
                            metadata={"role": "implementation"},
                        ),
                        self._event_json(
                            run_id="run-1",
                            event_id="run-1-000002",
                            event_type="command",
                            status="failure",
                            summary="task ci failed",
                            metadata={"failure_summary": "sqlite mismatch"},
                        ),
                        self._event_json(
                            run_id="run-1",
                            event_id="run-1-000003",
                            event_type="command",
                            status="success",
                            summary="task ci passed",
                            metadata={"command": "task ci"},
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                sqlite_events = store.search_events(text="sqlite")
                command_counts = store.aggregate_counts(group_by="event_type")
                status_counts = store.aggregate_counts(group_by="status", event_type="command")

        self.assertEqual(len(sqlite_events), 1)
        self.assertEqual(sqlite_events[0]["event_id"], "run-1-000002")
        self.assertEqual(
            command_counts,
            [
                {"value": "command", "count": 2},
                {"value": "codex", "count": 1},
            ],
        )
        self.assertEqual(
            status_counts,
            [
                {"value": "failure", "count": 1},
                {"value": "success", "count": 1},
            ],
        )

    def test_analyzer_classifies_resolved_and_blocked_failure_chains(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="implement",
                    event_type="command",
                    status="failure",
                    summary="task ci failed",
                    metadata={"command": "task ci", "failure_summary": "flake"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
                self._event(
                    run_id="run-1",
                    event_id="run-1-000002",
                    phase="implement",
                    event_type="command",
                    status="success",
                    summary="task ci passed",
                    metadata={"command": "task ci"},
                    timestamp="2026-07-16T10:00:08Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:01:00Z",
                ),
                self._event(
                    run_id="run-3",
                    event_id="run-3-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked again",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:02:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                analysis = store.analyze_failures(issue=126)

        self.assertEqual(
            analysis["failure_kind_counts"],
            [
                {"kind": "policy", "count": 2},
                {"kind": "command", "count": 1},
            ],
        )
        self.assertEqual(len(analysis["resolved_failures"]), 1)
        self.assertEqual(
            analysis["resolved_failures"][0]["failure_signatures"],
            ["command:task ci"],
        )
        self.assertEqual(len(analysis["blocked_failures"]), 2)
        self.assertTrue(
            all(
                item["failure_signatures"] == ["policy:stage_gate:review"]
                for item in analysis["blocked_failures"]
            )
        )
        self.assertEqual(
            analysis["recurring_event_chain_patterns"][0],
            {
                "pattern": "policy:stage_gate:review",
                "count": 2,
                "run_ids": ["run-2", "run-3"],
            },
        )

    def test_analyzer_keeps_structured_test_failures_in_failure_chains(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="hooks",
                    event_type="hook",
                    status="retry",
                    summary="hook failed: task ci",
                    metadata={
                        "command": "task ci",
                        "failure_summary": "FAILED tests/sympohy/test_runner.py::test_resume",
                        "test_failures": [
                            {
                                "runner": "pytest",
                                "name": "tests/sympohy/test_runner.py::test_resume",
                                "file": "tests/sympohy/test_runner.py",
                                "line": 27,
                                "summary": "AssertionError: expected retry",
                            },
                            {
                                "runner": "vitest",
                                "name": "App > renders failures",
                                "file": "tests/ui/App.test.tsx",
                                "line": 41,
                                "summary": "AssertionError: expected true to be false",
                            },
                        ],
                    },
                    timestamp="2026-07-16T10:00:00Z",
                ),
                self._event(
                    run_id="run-1",
                    event_id="run-1-000002",
                    phase="hooks",
                    event_type="hook",
                    status="success",
                    summary="hook passed: task ci",
                    metadata={"command": "task ci"},
                    timestamp="2026-07-16T10:00:08Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                analysis = store.analyze_failures(issue=126)

        self.assertEqual(len(analysis["resolved_failures"]), 1)
        self.assertEqual(
            analysis["resolved_failures"][0]["test_failures"],
            [
                {
                    "runner": "pytest",
                    "name": "tests/sympohy/test_runner.py::test_resume",
                    "file": "tests/sympohy/test_runner.py",
                    "line": 27,
                    "summary": "AssertionError: expected retry",
                },
                {
                    "runner": "vitest",
                    "name": "App > renders failures",
                    "file": "tests/ui/App.test.tsx",
                    "line": 41,
                    "summary": "AssertionError: expected true to be false",
                },
            ],
        )
        self.assertEqual(
            analysis["resolved_failures"][0]["event_chain"][0]["test_failures"],
            [
                {
                    "runner": "pytest",
                    "name": "tests/sympohy/test_runner.py::test_resume",
                    "file": "tests/sympohy/test_runner.py",
                    "line": 27,
                    "summary": "AssertionError: expected retry",
                },
                {
                    "runner": "vitest",
                    "name": "App > renders failures",
                    "file": "tests/ui/App.test.tsx",
                    "line": 41,
                    "summary": "AssertionError: expected true to be false",
                },
            ],
        )

    def test_analyzer_reports_phase_dwell_from_event_spans(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            self._event(
                                run_id="run-1",
                                event_id="run-1-000001",
                                phase="implement",
                                event_type="codex",
                                status="success",
                                summary="planning",
                                metadata={"role": "implementation"},
                                timestamp="2026-07-16T10:00:00Z",
                            ),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        json.dumps(
                            self._event(
                                run_id="run-1",
                                event_id="run-1-000002",
                                phase="implement",
                                event_type="command",
                                status="success",
                                summary="task ci passed",
                                metadata={"command": "task ci"},
                                timestamp="2026-07-16T10:00:06Z",
                            ),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        json.dumps(
                            self._event(
                                run_id="run-2",
                                event_id="run-2-000001",
                                phase="review",
                                event_type="review",
                                status="pass",
                                summary="review passed",
                                metadata={"reviewer_role": "adversarial-review"},
                                timestamp="2026-07-16T10:01:00Z",
                            ),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                analysis = store.analyze_failures(issue=126)

        self.assertEqual(
            analysis["phase_dwell"],
            [
                {
                    "phase": "implement",
                    "run_count": 1,
                    "event_count": 2,
                    "total_duration_seconds": 6.0,
                    "max_duration_seconds": 6.0,
                },
                {
                    "phase": "review",
                    "run_count": 1,
                    "event_count": 1,
                    "total_duration_seconds": 0.0,
                    "max_duration_seconds": 0.0,
                },
            ],
        )

    def test_proposer_emits_improvement_candidates_from_analysis_and_chain_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000001",
                    phase="hooks",
                    event_type="hook",
                    status="retry",
                    summary="hook failed: task ci",
                    metadata={
                        "command": "task ci",
                        "failure_summary": "FAILED tests/sympohy/test_runner.py::test_resume",
                        "test_failures": [
                            {
                                "runner": "pytest",
                                "name": "tests/sympohy/test_runner.py::test_resume",
                                "file": "tests/sympohy/test_runner.py",
                                "line": 27,
                                "summary": "AssertionError: expected retry",
                            }
                        ],
                    },
                    timestamp="2026-07-16T10:01:00Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000002",
                    phase="hooks",
                    event_type="hook",
                    status="success",
                    summary="hook passed: task ci",
                    metadata={"command": "task ci"},
                    timestamp="2026-07-16T10:01:08Z",
                ),
                self._event(
                    run_id="run-3",
                    event_id="run-3-000001",
                    phase="implement",
                    event_type="codex",
                    status="failure",
                    summary="codex response could not be parsed",
                    metadata={"role": "implementation", "parse_status": "invalid_json"},
                    timestamp="2026-07-16T10:02:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                proposal = store.propose_improvements(issue=126)

        self.assertEqual(proposal["schema_version"], 1)
        self.assertEqual(proposal["issue"], 126)
        self.assertIsNone(proposal["run_id"])
        self.assertEqual(len(proposal["event_chain_summaries"]), 3)
        self.assertEqual(
            sorted(candidate["category"] for candidate in proposal["candidates"]),
            ["docs", "prompt", "skill", "stage_gate", "test"],
        )

        candidates = {
            candidate["category"]: candidate for candidate in proposal["candidates"]
        }
        self.assertEqual(
            candidates["docs"]["required_validation"],
            [
                "task ci:markdown",
                "task pytest -- tests/sympohy/sympohy_observability_test.py",
            ],
        )
        self.assertEqual(
            candidates["prompt"]["evidence"]["failure_patterns"],
            ["data:codex:implementation:invalid_json"],
        )
        self.assertEqual(
            candidates["test"]["evidence"]["test_failures"],
            [
                {
                    "runner": "pytest",
                    "name": "tests/sympohy/test_runner.py::test_resume",
                    "file": "tests/sympohy/test_runner.py",
                    "line": 27,
                    "summary": "AssertionError: expected retry",
                }
            ],
        )
        self.assertEqual(
            proposal["event_chain_summaries"][0]["events"][0]["event_type"],
            "hook",
        )
        self.assertEqual(
            candidates["docs"]["application"]["automation_eligibility"],
            "eligible",
        )
        self.assertEqual(
            candidates["docs"]["application"]["stop_after"],
            "verified_draft_pr",
        )
        self.assertEqual(
            candidates["stage_gate"]["application"]["automation_eligibility"],
            "manual_only",
        )
        self.assertEqual(
            candidates["skill"]["application"]["automation_eligibility"],
            "manual_only",
        )

    def test_applicator_limits_auto_apply_to_low_risk_candidates_and_stops_at_draft_pr(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000001",
                    phase="hooks",
                    event_type="hook",
                    status="retry",
                    summary="hook failed: task ci",
                    metadata={
                        "command": "task ci",
                        "failure_summary": "FAILED tests/sympohy/test_runner.py::test_resume",
                        "test_failures": [
                            {
                                "runner": "pytest",
                                "name": "tests/sympohy/test_runner.py::test_resume",
                                "file": "tests/sympohy/test_runner.py",
                                "line": 27,
                                "summary": "AssertionError: expected retry",
                            }
                        ],
                    },
                    timestamp="2026-07-16T10:01:00Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000002",
                    phase="hooks",
                    event_type="hook",
                    status="success",
                    summary="hook passed: task ci",
                    metadata={"command": "task ci"},
                    timestamp="2026-07-16T10:01:08Z",
                ),
                self._event(
                    run_id="run-3",
                    event_id="run-3-000001",
                    phase="implement",
                    event_type="codex",
                    status="failure",
                    summary="codex response could not be parsed",
                    metadata={"role": "implementation", "parse_status": "invalid_json"},
                    timestamp="2026-07-16T10:02:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                application = store.apply_improvements(issue=126)

        self.assertEqual(application["schema_version"], 1)
        self.assertEqual(application["stop_after"], "verified_draft_pr")
        self.assertTrue(application["requires_human_review"])
        self.assertEqual(
            application["policy"]["allowed_categories"],
            ["config", "docs", "prompt", "test"],
        )
        self.assertIn("auto_merge", application["prohibited_actions"])
        self.assertEqual(
            sorted(
                candidate["category"]
                for candidate in application["auto_apply_candidates"]
            ),
            ["docs", "prompt", "test"],
        )
        self.assertEqual(
            sorted(
                candidate["category"]
                for candidate in application["manual_review_candidates"]
            ),
            ["skill", "stage_gate"],
        )

    def test_applicator_treats_lightweight_config_candidates_as_low_risk(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="hooks",
                    event_type="hook",
                    status="retry",
                    summary="hook failed: task ci",
                    metadata={"command": "task ci", "failure_summary": "flake"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
                self._event(
                    run_id="run-2",
                    event_id="run-2-000001",
                    phase="hooks",
                    event_type="hook",
                    status="retry",
                    summary="hook failed: task ci",
                    metadata={"command": "task ci", "failure_summary": "flake"},
                    timestamp="2026-07-16T10:01:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                application = store.apply_improvements(issue=126)

        config_candidates = [
            candidate
            for candidate in application["auto_apply_candidates"]
            if candidate["category"] == "config"
        ]
        self.assertEqual(len(config_candidates), 1)
        self.assertEqual(
            config_candidates[0]["application"]["automation_eligibility"],
            "eligible",
        )
        self.assertEqual(
            config_candidates[0]["application"]["stop_after"],
            "verified_draft_pr",
        )

    def test_applicator_executes_low_risk_candidates_runs_validation_and_verifies_draft_pr(self) -> None:
        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            log_dir = worktree / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            validation_calls: list[list[str]] = []
            push_call: dict[str, object] = {}
            git_calls: list[list[str]] = []
            statuses = iter(
                [
                    "",
                    "",
                    " M docs/contributing/issue-execution.md",
                    " M docs/contributing/issue-execution.md",
                ]
            )

            def check_call_with_heartbeat(
                command: list[str],
                *,
                cwd: Path,
                heartbeat: object | None = None,
            ) -> None:
                del heartbeat
                self.assertEqual(cwd, worktree)
                validation_calls.append(command)

            def codex_text(
                prompts: list[str],
                *,
                cwd: Path,
                log_path: Path,
                heartbeat: object | None = None,
                config: object | None = None,
                role: str = "default",
                state: object | None = None,
            ) -> str:
                del heartbeat, config, state
                self.assertEqual(cwd, worktree)
                self.assertEqual(role, "fix")
                self.assertTrue(log_path.name.endswith(".log"))
                self.assertIn("bounded self-improvement candidate", prompts[0])
                log_path.write_text("applied", encoding="utf-8")
                return ""

            def status(_cwd: Path) -> str:
                return next(statuses)

            def check_call(command: list[str], *, cwd: Path) -> None:
                self.assertEqual(cwd, worktree)
                git_calls.append(command)

            def push_branch_and_ensure_draft_pull_request(
                *,
                cwd: Path,
                branch: str,
                heartbeat: object | None = None,
                issue_number: int | None = None,
                base_branch: str | None = None,
            ) -> None:
                del heartbeat
                push_call.update(
                    {
                        "cwd": cwd,
                        "branch": branch,
                        "issue_number": issue_number,
                        "base_branch": base_branch,
                    }
                )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                with (
                    patch(
                        "scripts.sympohy.runner._check_call_with_heartbeat",
                        side_effect=check_call_with_heartbeat,
                    ),
                    patch(
                        "scripts.sympohy.runner._codex_text",
                        side_effect=codex_text,
                    ),
                    patch(
                        "scripts.sympohy.runner._current_branch",
                        return_value="issue-126-sympohy",
                    ),
                    patch(
                        "scripts.sympohy.runner._push_branch_and_ensure_draft_pull_request",
                        side_effect=push_branch_and_ensure_draft_pull_request,
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_has_changes",
                        return_value=True,
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        side_effect=status,
                    ),
                    patch(
                        "scripts.sympohy.observability.subprocess.check_call",
                        side_effect=check_call,
                    ),
                ):
                    application = store.apply_improvements(
                        issue=126,
                        execute=True,
                        cwd=worktree,
                        config=SimpleNamespace(base_branch="main"),
                    )

        self.assertEqual(
            [candidate["category"] for candidate in application["execution"]["applied_candidates"]],
            ["docs"],
        )
        self.assertEqual(
            validation_calls,
            [
                ["task", "ci:markdown"],
                ["task", "pytest", "--", "tests/sympohy/sympohy_observability_test.py"],
            ],
        )
        self.assertEqual(
            git_calls[0],
            ["git", "add", "-A", "--", "docs/contributing/issue-execution.md"],
        )
        self.assertEqual(git_calls[1][:2], ["git", "commit"])
        self.assertIn("apply self-improvement", git_calls[1][3])
        self.assertEqual(
            push_call,
            {
                "cwd": worktree,
                "branch": "issue-126-sympohy",
                "issue_number": 126,
                "base_branch": "main",
            },
        )
        self.assertEqual(
            application["execution"]["draft_pull_request"]["status"],
            "verified",
        )

    def test_applicator_rejects_out_of_scope_candidate_edits_before_validation(self) -> None:
        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            log_dir = worktree / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            statuses = iter(
                [
                    "",
                    "",
                    " M docs/contributing/issue-execution.md\n M scripts/sympohy/runner.py",
                    " M docs/contributing/issue-execution.md\n M scripts/sympohy/runner.py",
                ]
            )

            def codex_text(
                _prompts: list[str],
                *,
                cwd: Path,
                log_path: Path,
                heartbeat: object | None = None,
                config: object | None = None,
                role: str = "default",
                state: object | None = None,
            ) -> str:
                del heartbeat, config, role, state
                (cwd / "docs/contributing").mkdir(parents=True, exist_ok=True)
                (cwd / "scripts/sympohy").mkdir(parents=True, exist_ok=True)
                (cwd / "docs/contributing/issue-execution.md").write_text(
                    "docs change",
                    encoding="utf-8",
                )
                (cwd / "scripts/sympohy/runner.py").write_text(
                    "code change",
                    encoding="utf-8",
                )
                log_path.write_text("applied", encoding="utf-8")
                return ""

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                with (
                    patch(
                        "scripts.sympohy.runner._codex_text",
                        side_effect=codex_text,
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        side_effect=lambda _cwd: next(statuses),
                    ),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "observe-apply rejected out-of-scope changes .*scripts/sympohy/runner.py",
                    ):
                        store.apply_improvements(
                            issue=126,
                            execute=True,
                            cwd=worktree,
                            config=SimpleNamespace(base_branch="main"),
                        )

            self.assertFalse((worktree / "docs/contributing/issue-execution.md").exists())
            self.assertFalse((worktree / "scripts/sympohy/runner.py").exists())

    def test_applicator_rejects_out_of_scope_validation_side_effects(self) -> None:
        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            log_dir = worktree / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )
            statuses = iter(
                [
                    "",
                    "",
                    " M docs/contributing/issue-execution.md",
                    " M docs/contributing/issue-execution.md\n M scripts/sympohy/runner.py",
                    " M docs/contributing/issue-execution.md\n M scripts/sympohy/runner.py",
                ]
            )

            def codex_text(
                _prompts: list[str],
                *,
                cwd: Path,
                log_path: Path,
                heartbeat: object | None = None,
                config: object | None = None,
                role: str = "default",
                state: object | None = None,
            ) -> str:
                del heartbeat, config, role, state
                (cwd / "docs/contributing").mkdir(parents=True, exist_ok=True)
                (cwd / "docs/contributing/issue-execution.md").write_text(
                    "docs change",
                    encoding="utf-8",
                )
                log_path.write_text("applied", encoding="utf-8")
                return ""

            def validation(
                command: list[str],
                *,
                cwd: Path,
                heartbeat: object | None = None,
            ) -> None:
                del command, heartbeat
                (cwd / "scripts/sympohy").mkdir(parents=True, exist_ok=True)
                (cwd / "scripts/sympohy/runner.py").write_text(
                    "validation side effect",
                    encoding="utf-8",
                )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                with (
                    patch(
                        "scripts.sympohy.runner._codex_text",
                        side_effect=codex_text,
                    ),
                    patch(
                        "scripts.sympohy.runner._check_call_with_heartbeat",
                        side_effect=validation,
                    ),
                    patch(
                        "scripts.sympohy.runner._worktree_status",
                        side_effect=lambda _cwd: next(statuses),
                    ),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "observe-apply rejected out-of-scope validation changes .*scripts/sympohy/runner.py",
                    ):
                        store.apply_improvements(
                            issue=126,
                            execute=True,
                            cwd=worktree,
                            config=SimpleNamespace(base_branch="main"),
                        )

            self.assertFalse((worktree / "docs/contributing/issue-execution.md").exists())
            self.assertFalse((worktree / "scripts/sympohy/runner.py").exists())

    def test_prompt_auto_apply_scope_rejects_runner_changes(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "observe-apply rejected out-of-scope changes .*scripts/sympohy/runner.py",
        ):
            _enforce_candidate_scope(
                candidate={"id": "candidate-prompt", "category": "prompt"},
                changed_paths=["scripts/sympohy/runner.py"],
            )

    def test_apply_improvements_rejects_dirty_worktree(self) -> None:
        with TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            log_dir = worktree / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            events = [
                self._event(
                    run_id="run-1",
                    event_id="run-1-000001",
                    phase="review",
                    event_type="stage_gate",
                    status="block",
                    summary="review gate blocked",
                    metadata={"stage": "review", "failure_summary": "missing AC"},
                    timestamp="2026-07-16T10:00:00Z",
                ),
            ]
            (log_dir / "events.jsonl").write_text(
                "\n".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True)
                    for event in events
                )
                + "\n",
                encoding="utf-8",
            )

            with ObservationStore.rebuild(log_dir=log_dir)[0] as store:
                with patch(
                    "scripts.sympohy.runner._worktree_status",
                    return_value=" M docs/contributing/issue-execution.md\n",
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "observe-apply requires a clean worktree",
                    ):
                        store.apply_improvements(
                            issue=126,
                            execute=True,
                            cwd=worktree,
                            config=SimpleNamespace(base_branch="main"),
                        )

    def test_rebuild_rejects_invalid_event_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "runs" / "issue-126"
            log_dir.mkdir(parents=True)
            (log_dir / "events.jsonl").write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "event_id": "run-1-000001",
                        "issue": 126,
                        "phase": "implement",
                        "event_type": "command",
                        "status": "success",
                        "attempt": 1,
                        "duration": 1.0,
                        "summary": "bad metadata",
                        "metadata": ["not", "a", "mapping"],
                        "timestamp": "2026-07-16T10:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "invalid metadata"):
                rebuild_observation_store(log_dir=log_dir)

    def _event_json(
        self,
        *,
        run_id: str,
        event_id: str,
        event_type: str,
        status: str,
        summary: str,
        metadata: dict[str, object],
    ) -> str:
        return json.dumps(
            {
                "run_id": run_id,
                "event_id": event_id,
                "issue": 126,
                "phase": "implement",
                "event_type": event_type,
                "status": status,
                "attempt": 1,
                "duration": 1.0,
                "summary": summary,
                "metadata": metadata,
                "timestamp": "2026-07-16T10:00:00Z",
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _event(
        self,
        *,
        run_id: str,
        event_id: str,
        phase: str,
        event_type: str,
        status: str,
        summary: str,
        metadata: dict[str, object],
        timestamp: str,
    ) -> dict[str, object]:
        return {
            "run_id": run_id,
            "event_id": event_id,
            "issue": 126,
            "phase": phase,
            "event_type": event_type,
            "status": status,
            "attempt": 1,
            "duration": 1.0,
            "summary": summary,
            "metadata": metadata,
            "timestamp": timestamp,
        }

    def _sqlite_dump(self, path: Path) -> str:
        connection = sqlite3.connect(path)
        try:
            return "\n".join(connection.iterdump())
        finally:
            connection.close()
