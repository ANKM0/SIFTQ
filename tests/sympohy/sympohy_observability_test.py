from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from scripts.sympohy.observability import ObservationStore, rebuild_observation_store


class SympohyObservabilityTest(unittest.TestCase):
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

    def _sqlite_dump(self, path: Path) -> str:
        connection = sqlite3.connect(path)
        try:
            return "\n".join(connection.iterdump())
        finally:
            connection.close()

