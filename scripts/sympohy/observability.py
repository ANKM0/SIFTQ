from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile
from typing import Iterable, Literal, Mapping, Sequence


_REQUIRED_EVENT_KEYS = frozenset(
    {
        "run_id",
        "event_id",
        "issue",
        "phase",
        "event_type",
        "status",
        "attempt",
        "duration",
        "summary",
        "metadata",
        "timestamp",
    }
)
_COUNT_GROUP_FIELDS = frozenset({"event_type", "status", "phase", "run_id"})


@dataclass(frozen=True)
class ReplayResult:
    source_path: Path
    db_path: Path
    event_count: int
    run_count: int


@dataclass(frozen=True)
class ObservationEvent:
    issue: int
    run_id: str
    event_id: str
    phase: str | None
    event_type: str
    status: str
    attempt: int | None
    duration: float | int | None
    summary: str
    metadata: Mapping[str, object]
    timestamp: str
    line_number: int

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
        *,
        line_number: int,
    ) -> ObservationEvent:
        missing = sorted(_REQUIRED_EVENT_KEYS - set(payload.keys()))
        if missing:
            raise ValueError(
                f"event line {line_number} is missing required keys: {', '.join(missing)}"
            )
        run_id = payload["run_id"]
        event_id = payload["event_id"]
        issue = payload["issue"]
        event_type = payload["event_type"]
        status = payload["status"]
        summary = payload["summary"]
        timestamp = payload["timestamp"]
        metadata = payload["metadata"]
        phase = payload["phase"]
        attempt = payload["attempt"]
        duration = payload["duration"]
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError(f"event line {line_number} has invalid run_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError(f"event line {line_number} has invalid event_id")
        if not isinstance(issue, int):
            raise ValueError(f"event line {line_number} has invalid issue")
        if phase is not None and not isinstance(phase, str):
            raise ValueError(f"event line {line_number} has invalid phase")
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError(f"event line {line_number} has invalid event_type")
        if not isinstance(status, str) or not status.strip():
            raise ValueError(f"event line {line_number} has invalid status")
        if attempt is not None and not isinstance(attempt, int):
            raise ValueError(f"event line {line_number} has invalid attempt")
        if duration is not None and not isinstance(duration, int | float):
            raise ValueError(f"event line {line_number} has invalid duration")
        if not isinstance(summary, str):
            raise ValueError(f"event line {line_number} has invalid summary")
        if not isinstance(metadata, Mapping):
            raise ValueError(f"event line {line_number} has invalid metadata")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(f"event line {line_number} has invalid timestamp")
        return cls(
            issue=issue,
            run_id=run_id,
            event_id=event_id,
            phase=phase,
            event_type=event_type,
            status=status,
            attempt=attempt,
            duration=duration,
            summary=summary,
            metadata=dict(metadata),
            timestamp=timestamp,
            line_number=line_number,
        )


def load_event_stream(path: Path) -> list[ObservationEvent]:
    events: list[ObservationEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"event line {line_number} is not valid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError(f"event line {line_number} must be a JSON object")
        events.append(ObservationEvent.from_mapping(payload, line_number=line_number))
    return sorted(events, key=_event_sort_key)


def rebuild_observation_store(
    *,
    log_dir: Path,
    db_path: Path | None = None,
) -> ReplayResult:
    source_path = log_dir / "events.jsonl"
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    target_path = db_path or (log_dir / "observations.sqlite3")
    events = load_event_stream(source_path)
    _write_observation_store(events=events, db_path=target_path, source_path=source_path)
    return ReplayResult(
        source_path=source_path,
        db_path=target_path,
        event_count=len(events),
        run_count=len({event.run_id for event in events}),
    )


class ObservationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ObservationStore:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    @classmethod
    def rebuild(
        cls,
        *,
        log_dir: Path,
        db_path: Path | None = None,
    ) -> tuple[ObservationStore, ReplayResult]:
        result = rebuild_observation_store(log_dir=log_dir, db_path=db_path)
        return cls(result.db_path), result

    def search_events(
        self,
        *,
        issue: int | None = None,
        run_id: str | None = None,
        phase: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        text: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        where, params = _event_filters(
            issue=issue,
            run_id=run_id,
            phase=phase,
            event_type=event_type,
            status=status,
            text=text,
        )
        cursor = self._connection.execute(
            f"""
            SELECT issue, run_id, event_id, phase, event_type, status, attempt,
                   duration, summary, metadata_json, timestamp, line_number
            FROM events
            {where}
            ORDER BY issue, run_id, event_index, event_id, line_number
            LIMIT ?
            """,
            [*params, limit],
        )
        rows: list[dict[str, object]] = []
        for row in cursor.fetchall():
            rows.append(
                {
                    "issue": row["issue"],
                    "run_id": row["run_id"],
                    "event_id": row["event_id"],
                    "phase": row["phase"],
                    "event_type": row["event_type"],
                    "status": row["status"],
                    "attempt": row["attempt"],
                    "duration": row["duration"],
                    "summary": row["summary"],
                    "metadata": json.loads(row["metadata_json"]),
                    "timestamp": row["timestamp"],
                    "line_number": row["line_number"],
                }
            )
        return rows

    def aggregate_counts(
        self,
        *,
        group_by: Literal["event_type", "status", "phase", "run_id"],
        issue: int | None = None,
        run_id: str | None = None,
        phase: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        if group_by not in _COUNT_GROUP_FIELDS:
            raise ValueError(f"unsupported group_by: {group_by}")
        where, params = _event_filters(
            issue=issue,
            run_id=run_id,
            phase=phase,
            event_type=event_type,
            status=status,
            text=None,
        )
        cursor = self._connection.execute(
            f"""
            SELECT {group_by} AS value, COUNT(*) AS count
            FROM events
            {where}
            GROUP BY {group_by}
            ORDER BY count DESC, value ASC
            """,
            params,
        )
        return [{"value": row["value"], "count": row["count"]} for row in cursor.fetchall()]

    def list_runs(self, *, issue: int | None = None) -> list[dict[str, object]]:
        clauses: list[str] = []
        params: list[object] = []
        if issue is not None:
            clauses.append("issue = ?")
            params.append(issue)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cursor = self._connection.execute(
            f"""
            SELECT run_id, issue, event_count, first_event_id, first_timestamp,
                   last_event_id, last_timestamp
            FROM runs
            {where}
            ORDER BY issue, run_id
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def _event_filters(
    *,
    issue: int | None,
    run_id: str | None,
    phase: str | None,
    event_type: str | None,
    status: str | None,
    text: str | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    for column, value in (
        ("issue", issue),
        ("run_id", run_id),
        ("phase", phase),
        ("event_type", event_type),
        ("status", status),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)
    if text is not None and text.strip():
        clauses.append("(summary LIKE ? OR metadata_json LIKE ?)")
        pattern = f"%{text.strip()}%"
        params.extend((pattern, pattern))
    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def _write_observation_store(
    *,
    events: Sequence[ObservationEvent],
    db_path: Path,
    source_path: Path,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        prefix=f"{db_path.name}.",
        suffix=".tmp",
        dir=db_path.parent,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        connection = sqlite3.connect(tmp_path)
        try:
            _create_schema(connection)
            _insert_events(connection, events)
            connection.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES (?, ?), (?, ?)
                """,
                (
                    "source_path",
                    str(source_path),
                    "source_event_count",
                    str(len(events)),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        tmp_path.replace(db_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode = DELETE;
        PRAGMA synchronous = FULL;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            issue INTEGER NOT NULL,
            run_id TEXT NOT NULL,
            event_index INTEGER,
            phase TEXT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt INTEGER,
            duration REAL,
            summary TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            line_number INTEGER NOT NULL
        );

        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            issue INTEGER NOT NULL,
            event_count INTEGER NOT NULL,
            first_event_id TEXT NOT NULL,
            first_timestamp TEXT NOT NULL,
            last_event_id TEXT NOT NULL,
            last_timestamp TEXT NOT NULL
        );

        CREATE INDEX idx_events_issue_run ON events(issue, run_id);
        CREATE INDEX idx_events_phase ON events(phase);
        CREATE INDEX idx_events_type ON events(event_type);
        CREATE INDEX idx_events_status ON events(status);
        CREATE INDEX idx_events_summary ON events(summary);
        """
    )


def _insert_events(connection: sqlite3.Connection, events: Sequence[ObservationEvent]) -> None:
    if not events:
        return
    seen_event_ids: set[str] = set()
    run_summary: dict[str, dict[str, object]] = {}
    for event in events:
        if event.event_id in seen_event_ids:
            raise ValueError(f"duplicate event_id in event stream: {event.event_id}")
        seen_event_ids.add(event.event_id)
        event_index = _event_index(event.run_id, event.event_id)
        connection.execute(
            """
            INSERT INTO events(
                event_id, issue, run_id, event_index, phase, event_type, status,
                attempt, duration, summary, metadata_json, timestamp, line_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.issue,
                event.run_id,
                event_index,
                event.phase,
                event.event_type,
                event.status,
                event.attempt,
                None if event.duration is None else float(event.duration),
                event.summary,
                json.dumps(event.metadata, ensure_ascii=False, sort_keys=True),
                event.timestamp,
                event.line_number,
            ),
        )
        summary = run_summary.setdefault(
            event.run_id,
            {
                "issue": event.issue,
                "event_count": 0,
                "first_event_id": event.event_id,
                "first_timestamp": event.timestamp,
                "last_event_id": event.event_id,
                "last_timestamp": event.timestamp,
            },
        )
        summary["event_count"] = int(summary["event_count"]) + 1
        if _event_sort_key(event) < _event_sort_key_identity(
            run_id=event.run_id,
            issue=event.issue,
            event_id=str(summary["first_event_id"]),
            timestamp=str(summary["first_timestamp"]),
            line_number=0,
        ):
            summary["first_event_id"] = event.event_id
            summary["first_timestamp"] = event.timestamp
        summary["last_event_id"] = event.event_id
        summary["last_timestamp"] = event.timestamp
    connection.executemany(
        """
        INSERT INTO runs(
            run_id, issue, event_count, first_event_id, first_timestamp,
            last_event_id, last_timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                int(summary["issue"]),
                int(summary["event_count"]),
                str(summary["first_event_id"]),
                str(summary["first_timestamp"]),
                str(summary["last_event_id"]),
                str(summary["last_timestamp"]),
            )
            for run_id, summary in sorted(run_summary.items())
        ],
    )


def _event_sort_key(event: ObservationEvent) -> tuple[object, ...]:
    return _event_sort_key_identity(
        issue=event.issue,
        run_id=event.run_id,
        event_id=event.event_id,
        timestamp=event.timestamp,
        line_number=event.line_number,
    )


def _event_sort_key_identity(
    *,
    issue: int,
    run_id: str,
    event_id: str,
    timestamp: str,
    line_number: int,
) -> tuple[object, ...]:
    index = _event_index(run_id, event_id)
    return (
        issue,
        run_id,
        index is None,
        index if index is not None else 0,
        event_id,
        timestamp,
        line_number,
    )


def _event_index(run_id: str, event_id: str) -> int | None:
    prefix, _, suffix = event_id.rpartition("-")
    if prefix != run_id or not suffix.isdigit():
        return None
    return int(suffix)
