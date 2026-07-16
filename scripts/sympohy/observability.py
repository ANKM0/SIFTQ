from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile
from typing import Literal, Mapping, Sequence


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
_PROPOSAL_TARGETS = ("prompt", "hook", "stage_gate", "docs", "skill", "test", "config")
_LOW_RISK_APPLICATOR_TARGETS = frozenset({"docs", "prompt", "test", "config"})
_FAILURE_KINDS = frozenset(
    {
        "hook",
        "codex",
        "command",
        "review",
        "merge",
        "browser",
        "recovery",
        "policy",
        "data",
        "unknown",
    }
)
_SUCCESS_STATUSES = frozenset({"success", "pass", "passed", "observed", "done"})
_FAILURE_STATUSES = frozenset(
    {"failed", "failure", "retry", "block", "blocked", "interrupted"}
)


@dataclass(frozen=True)
class ReplayResult:
    source_path: Path
    db_path: Path
    event_count: int
    run_count: int


@dataclass(frozen=True)
class FailureObservation:
    kind: str
    signature: str
    resolution_key: str
    terminal: bool
    event: ObservationEvent


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

    def analyze_failures(
        self,
        *,
        issue: int | None = None,
        run_id: str | None = None,
    ) -> dict[str, object]:
        events = self._analysis_events(issue=issue, run_id=run_id)
        events_by_run: dict[str, list[ObservationEvent]] = defaultdict(list)
        for event in events:
            events_by_run[event.run_id].append(event)

        kind_counts: Counter[str] = Counter()
        phase_dwell: dict[str | None, dict[str, object]] = {}
        resolved_failures: list[dict[str, object]] = []
        blocked_failures: list[dict[str, object]] = []
        recurring_patterns: Counter[str] = Counter()
        recurring_pattern_runs: dict[str, set[str]] = defaultdict(set)

        for run_events in events_by_run.values():
            self._accumulate_phase_dwell(phase_dwell, run_events)
            chains = _derive_failure_chains(run_events)
            for chain in chains:
                for failure in chain["failures"]:
                    kind_counts[str(failure["kind"])] += 1
                pattern = str(chain["pattern"])
                recurring_patterns[pattern] += 1
                recurring_pattern_runs[pattern].add(str(chain["run_id"]))
                summary = {
                    "issue": chain["issue"],
                    "run_id": chain["run_id"],
                    "phase": chain["phase"],
                    "status": chain["status"],
                    "failure_count": chain["failure_count"],
                    "failure_kinds": chain["failure_kinds"],
                    "failure_signatures": chain["failure_signatures"],
                    "started_at": chain["started_at"],
                    "ended_at": chain["ended_at"],
                    "test_failures": _chain_test_failures(chain),
                    "event_chain": chain["event_chain"],
                }
                if chain["status"] == "resolved":
                    resolved_failures.append(summary)
                elif chain["status"] == "blocked":
                    blocked_failures.append(summary)

        return {
            "failure_kind_counts": [
                {"kind": kind, "count": count}
                for kind, count in sorted(
                    kind_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "phase_dwell": [
                {
                    "phase": phase,
                    "run_count": int(data["run_count"]),
                    "event_count": int(data["event_count"]),
                    "total_duration_seconds": round(float(data["total_duration_seconds"]), 6),
                    "max_duration_seconds": round(float(data["max_duration_seconds"]), 6),
                }
                for phase, data in sorted(
                    phase_dwell.items(),
                    key=lambda item: (item[0] is None, "" if item[0] is None else str(item[0])),
                )
            ],
            "resolved_failures": resolved_failures,
            "blocked_failures": blocked_failures,
            "recurring_event_chain_patterns": [
                {
                    "pattern": pattern,
                    "count": count,
                    "run_ids": sorted(recurring_pattern_runs[pattern]),
                }
                for pattern, count in sorted(
                    recurring_patterns.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        }

    def propose_improvements(
        self,
        *,
        issue: int | None = None,
        run_id: str | None = None,
    ) -> dict[str, object]:
        analysis = self.analyze_failures(issue=issue, run_id=run_id)
        event_chain_summaries = [
            _summarize_failure_chain(chain, chain_status="resolved")
            for chain in analysis["resolved_failures"]
        ] + [
            _summarize_failure_chain(chain, chain_status="blocked")
            for chain in analysis["blocked_failures"]
        ]

        candidates = _propose_improvement_candidates(
            analysis=analysis,
            event_chain_summaries=event_chain_summaries,
        )

        return {
            "schema_version": 1,
            "issue": issue,
            "run_id": run_id,
            "analysis": analysis,
            "event_chain_summaries": event_chain_summaries,
            "candidates": candidates,
        }

    def apply_improvements(
        self,
        *,
        issue: int | None = None,
        run_id: str | None = None,
    ) -> dict[str, object]:
        proposal = self.propose_improvements(issue=issue, run_id=run_id)
        candidates = proposal.get("candidates", [])
        candidate_list = (
            list(candidates)
            if isinstance(candidates, Sequence)
            and not isinstance(candidates, (str, bytes, bytearray))
            else []
        )
        auto_apply_candidates = [
            dict(candidate)
            for candidate in candidate_list
            if isinstance(candidate, Mapping)
            and _is_auto_apply_candidate(candidate)
        ]
        manual_review_candidates = [
            dict(candidate)
            for candidate in candidate_list
            if isinstance(candidate, Mapping)
            and not _is_auto_apply_candidate(candidate)
        ]
        return {
            "schema_version": 1,
            "issue": issue,
            "run_id": run_id,
            "stop_after": "verified_draft_pr",
            "requires_human_review": True,
            "prohibited_actions": [
                "dangerous_auto_apply",
                "broad_code_changes",
                "auto_merge",
            ],
            "policy": {
                "allowed_categories": sorted(_LOW_RISK_APPLICATOR_TARGETS),
                "manual_review_categories": ["hook", "skill", "stage_gate"],
                "lightweight_config_only": True,
            },
            "summary": {
                "candidate_count": len(candidate_list),
                "auto_apply_count": len(auto_apply_candidates),
                "manual_review_count": len(manual_review_candidates),
            },
            "auto_apply_candidates": auto_apply_candidates,
            "manual_review_candidates": manual_review_candidates,
        }

    def _analysis_events(
        self,
        *,
        issue: int | None,
        run_id: str | None,
    ) -> list[ObservationEvent]:
        where, params = _event_filters(
            issue=issue,
            run_id=run_id,
            phase=None,
            event_type=None,
            status=None,
            text=None,
        )
        cursor = self._connection.execute(
            f"""
            SELECT issue, run_id, event_id, phase, event_type, status, attempt,
                   duration, summary, metadata_json, timestamp, line_number
            FROM events
            {where}
            ORDER BY issue, run_id, event_index, event_id, line_number
            """,
            params,
        )
        return [
            ObservationEvent(
                issue=int(row["issue"]),
                run_id=str(row["run_id"]),
                event_id=str(row["event_id"]),
                phase=row["phase"],
                event_type=str(row["event_type"]),
                status=str(row["status"]),
                attempt=row["attempt"],
                duration=row["duration"],
                summary=str(row["summary"]),
                metadata=json.loads(row["metadata_json"]),
                timestamp=str(row["timestamp"]),
                line_number=int(row["line_number"]),
            )
            for row in cursor.fetchall()
        ]

    def _accumulate_phase_dwell(
        self,
        phase_dwell: dict[str | None, dict[str, object]],
        run_events: Sequence[ObservationEvent],
    ) -> None:
        per_phase: dict[str | None, list[ObservationEvent]] = defaultdict(list)
        for event in run_events:
            per_phase[event.phase].append(event)
        for phase, events in per_phase.items():
            timestamps = [_parse_timestamp(event.timestamp) for event in events]
            duration = (
                (timestamps[-1] - timestamps[0]).total_seconds()
                if len(timestamps) > 1
                else 0.0
            )
            bucket = phase_dwell.setdefault(
                phase,
                {
                    "run_count": 0,
                    "event_count": 0,
                    "total_duration_seconds": 0.0,
                    "max_duration_seconds": 0.0,
                },
            )
            bucket["run_count"] = int(bucket["run_count"]) + 1
            bucket["event_count"] = int(bucket["event_count"]) + len(events)
            bucket["total_duration_seconds"] = (
                float(bucket["total_duration_seconds"]) + duration
            )
            bucket["max_duration_seconds"] = max(
                float(bucket["max_duration_seconds"]),
                duration,
            )


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


def _summarize_failure_chain(
    chain: Mapping[str, object],
    *,
    chain_status: str,
) -> dict[str, object]:
    event_chain = chain.get("event_chain", [])
    events = event_chain if isinstance(event_chain, Sequence) else []
    truncated = [
        {
            "event_id": str(event.get("event_id", "")),
            "event_type": str(event.get("event_type", "")),
            "status": str(event.get("status", "")),
            "phase": event.get("phase"),
            "summary": str(event.get("summary", "")),
        }
        for event in events[:3]
        if isinstance(event, Mapping)
    ]
    return {
        "issue": chain.get("issue"),
        "run_id": chain.get("run_id"),
        "phase": chain.get("phase"),
        "status": chain_status,
        "failure_count": chain.get("failure_count"),
        "failure_kinds": list(chain.get("failure_kinds", [])),
        "failure_signatures": list(chain.get("failure_signatures", [])),
        "started_at": chain.get("started_at"),
        "ended_at": chain.get("ended_at"),
        "test_failures": list(chain.get("test_failures", [])),
        "events": truncated,
    }


def _propose_improvement_candidates(
    *,
    analysis: Mapping[str, object],
    event_chain_summaries: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    blocked = [
        chain for chain in event_chain_summaries if str(chain.get("status")) == "blocked"
    ]
    resolved = [
        chain for chain in event_chain_summaries if str(chain.get("status")) == "resolved"
    ]
    recurring = analysis.get("recurring_event_chain_patterns", [])
    recurring_patterns = recurring if isinstance(recurring, Sequence) else []

    policy_review_blocks = [
        chain
        for chain in blocked
        if "policy:stage_gate:review" in chain.get("failure_signatures", [])
    ]
    if policy_review_blocks:
        _append_candidate(
            candidates,
            seen_ids,
            category="docs",
            dedupe_key="policy-review-docs",
            title="Clarify review-stage acceptance criteria",
            summary="Recurring review stage-gate blocks indicate missing traceability or acceptance coverage before review.",
            impact="high",
            confidence="high",
            risk="low",
            required_validation=[
                "task ci:markdown",
                "task pytest tests/sympohy/sympohy_observability_test.py",
            ],
            evidence_chains=policy_review_blocks,
        )
        _append_candidate(
            candidates,
            seen_ids,
            category="skill",
            dedupe_key="policy-review-skill",
            title="Strengthen implementation skill guidance before review",
            summary="The implementation workflow should steer agents to verify AC/DoD and PR metadata before entering review.",
            impact="medium",
            confidence="medium",
            risk="low",
            required_validation=[
                "task ci:markdown",
                "task pytest tests/sympohy/sympohy_observability_test.py",
            ],
            evidence_chains=policy_review_blocks,
        )
        _append_candidate(
            candidates,
            seen_ids,
            category="stage_gate",
            dedupe_key="policy-review-stage-gate",
            title="Tighten review stage-gate messaging",
            summary="Review blocks should surface the exact missing acceptance or traceability fields earlier and more explicitly.",
            impact="medium",
            confidence="medium",
            risk="low",
            required_validation=[
                "task pytest tests/sympohy/sympohy_stage_gate_test.py",
                "task pytest tests/sympohy/sympohy_observability_test.py",
            ],
            evidence_chains=policy_review_blocks,
        )

    codex_or_data_failures = [
        chain
        for chain in blocked + resolved
        if any(
            kind in {"codex", "data"} for kind in _as_str_list(chain.get("failure_kinds"))
        )
    ]
    if codex_or_data_failures:
        _append_candidate(
            candidates,
            seen_ids,
            category="prompt",
            dedupe_key="codex-prompt",
            title="Harden prompts for parseable structured output",
            summary="Codex or parse-status failures suggest the prompt contract is underspecified for machine-readable responses.",
            impact="high",
            confidence="medium",
            risk="low",
            required_validation=[
                "task pytest tests/sympohy/sympohy_observability_test.py",
                "task ci:test",
            ],
            evidence_chains=codex_or_data_failures,
        )

    command_or_hook_test_failures = [
        chain
        for chain in blocked + resolved
        if chain.get("test_failures")
        and any(
            kind in {"command", "hook"} for kind in _as_str_list(chain.get("failure_kinds"))
        )
    ]
    if command_or_hook_test_failures:
        _append_candidate(
            candidates,
            seen_ids,
            category="test",
            dedupe_key="test-fixtures",
            title="Add regression fixtures for repeated command or hook failures",
            summary="Observed command or hook failures already contain structured failing tests, so replay fixtures can lock the regression contract.",
            impact="high",
            confidence="high",
            risk="low",
            required_validation=[
                "task pytest tests/sympohy/sympohy_observability_test.py",
                "task ci:test",
            ],
            evidence_chains=command_or_hook_test_failures,
        )

    recurring_retry_patterns = [
        pattern
        for pattern in recurring_patterns
        if isinstance(pattern, Mapping)
        and int(pattern.get("count", 0) or 0) > 1
        and not str(pattern.get("pattern", "")).startswith("policy:stage_gate:")
    ]
    if recurring_retry_patterns:
        matching = [
            chain
            for chain in blocked + resolved
            if str(chain.get("failure_signatures", [""])[0] if chain.get("failure_signatures") else "")
            in {str(pattern.get("pattern", "")) for pattern in recurring_retry_patterns}
        ]
        _append_candidate(
            candidates,
            seen_ids,
            category="config",
            dedupe_key="recurring-config",
            title="Review retry and hook configuration for recurring failure chains",
            summary="The same failure chain is repeating across runs, which points to configuration or retry policy that is not absorbing a known transient path.",
            impact="medium",
            confidence="medium",
            risk="low",
            required_validation=[
                "task pytest tests/sympohy/sympohy_config_test.py",
                "task pytest tests/sympohy/sympohy_observability_test.py",
            ],
            evidence_chains=matching,
        )

    browser_failures = [
        chain
        for chain in blocked + resolved
        if "browser" in _as_str_list(chain.get("failure_kinds"))
    ]
    if browser_failures:
        _append_candidate(
            candidates,
            seen_ids,
            category="hook",
            dedupe_key="browser-hook",
            title="Add lightweight browser checks to hooks or verifiers",
            summary="Browser observation failures indicate the verification hooks should catch UI console or page errors earlier.",
            impact="medium",
            confidence="medium",
            risk="low",
            required_validation=[
                "task ci:test",
                "task pytest tests/sympohy/sympohy_observability_test.py",
            ],
            evidence_chains=browser_failures,
        )

    return sorted(
        candidates,
        key=lambda item: (
            -_impact_rank(str(item["impact"])),
            -_confidence_rank(str(item["confidence"])),
            _PROPOSAL_TARGETS.index(str(item["category"]))
            if str(item["category"]) in _PROPOSAL_TARGETS
            else len(_PROPOSAL_TARGETS),
            str(item["id"]),
        ),
    )


def _append_candidate(
    candidates: list[dict[str, object]],
    seen_ids: set[str],
    *,
    category: str,
    dedupe_key: str,
    title: str,
    summary: str,
    impact: str,
    confidence: str,
    risk: str,
    required_validation: Sequence[str],
    evidence_chains: Sequence[Mapping[str, object]],
) -> None:
    candidate_id = f"{category}:{dedupe_key}"
    if candidate_id in seen_ids:
        return
    seen_ids.add(candidate_id)
    run_ids = sorted(
        {
            str(chain.get("run_id"))
            for chain in evidence_chains
            if str(chain.get("run_id", "")).strip()
        }
    )
    patterns = sorted(
        {
            signature
            for chain in evidence_chains
            for signature in _as_str_list(chain.get("failure_signatures"))
        }
    )
    phases = sorted(
        {
            str(chain.get("phase"))
            for chain in evidence_chains
            if str(chain.get("phase", "")).strip()
        }
    )
    test_failures = _collect_test_failures(evidence_chains)
    candidates.append(
        {
            "id": candidate_id,
            "category": category,
            "title": title,
            "summary": summary,
            "impact": impact,
            "confidence": confidence,
            "risk": risk,
            "required_validation": list(required_validation),
            "application": _candidate_application_policy(
                category=category,
                title=title,
                summary=summary,
                required_validation=required_validation,
            ),
            "evidence": {
                "run_ids": run_ids,
                "failure_patterns": patterns,
                "phases": phases,
                "chain_count": len(evidence_chains),
                "test_failures": test_failures,
            },
        }
    )


def _collect_test_failures(
    chains: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    seen: set[str] = set()
    for chain in chains:
        failures = chain.get("test_failures")
        if not isinstance(failures, Sequence) or isinstance(
            failures, (str, bytes, bytearray)
        ):
            continue
        for failure in failures:
            if not isinstance(failure, Mapping):
                continue
            normalized = {
                "runner": str(failure.get("runner", "")).strip(),
                "name": str(failure.get("name", "")).strip(),
                "file": str(failure.get("file", "")).strip(),
                "line": failure.get("line"),
                "summary": str(failure.get("summary", "")).strip(),
            }
            key = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            collected.append(normalized)
    return collected


def _candidate_application_policy(
    *,
    category: str,
    title: str,
    summary: str,
    required_validation: Sequence[str],
) -> dict[str, object]:
    if category in {"docs", "prompt", "test"}:
        return {
            "automation_eligibility": "eligible",
            "scope": "low_risk",
            "reason": (
                f"{category} changes are in the bounded low-risk applicator scope "
                "and must stop at a verified draft PR."
            ),
            "stop_after": "verified_draft_pr",
            "requires_human_review": True,
        }
    if category == "config" and _is_lightweight_config_candidate(
        title=title,
        summary=summary,
        required_validation=required_validation,
    ):
        return {
            "automation_eligibility": "eligible",
            "scope": "low_risk",
            "reason": (
                "This config proposal is limited to lightweight sympohy retry or "
                "hook settings and must stop at a verified draft PR."
            ),
            "stop_after": "verified_draft_pr",
            "requires_human_review": True,
        }
    return {
        "automation_eligibility": "manual_only",
        "scope": "needs_human_review",
        "reason": (
            "This proposal is outside the bounded low-risk applicator scope and "
            "must not be auto-applied without human review."
        ),
        "stop_after": "manual_review",
        "requires_human_review": True,
    }


def _is_lightweight_config_candidate(
    *,
    title: str,
    summary: str,
    required_validation: Sequence[str],
) -> bool:
    normalized_text = " ".join((title, summary)).lower()
    if not any(token in normalized_text for token in ("config", "retry", "hook")):
        return False
    return any(
        "sympohy_config_test.py" in str(command) for command in required_validation
    )


def _is_auto_apply_candidate(candidate: Mapping[str, object]) -> bool:
    application = candidate.get("application")
    if not isinstance(application, Mapping):
        return False
    return str(application.get("automation_eligibility")) == "eligible"


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item) for item in value]


def _impact_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def _confidence_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


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


def _derive_failure_chains(events: Sequence[ObservationEvent]) -> list[dict[str, object]]:
    chains: list[dict[str, object]] = []
    active: dict[str, object] | None = None
    active_keys: set[str] = set()
    for event in events:
        observation = _classify_failure_event(event)
        if observation is not None:
            if active is None:
                active = _new_failure_chain(event)
                active_keys = set()
            active_keys.add(observation.resolution_key)
            active["failures"].append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "status": event.status,
                    "phase": event.phase,
                    "kind": observation.kind,
                    "signature": observation.signature,
                    "timestamp": event.timestamp,
                    "summary": event.summary,
                }
            )
            active["event_chain"].append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "status": event.status,
                    "phase": event.phase,
                    "kind": observation.kind,
                    "signature": observation.signature,
                    "summary": event.summary,
                    "test_failures": _event_test_failures(event),
                }
            )
            if observation.terminal:
                active["status"] = "blocked"
                active["ended_at"] = event.timestamp
                _finalize_failure_chain(chains, active)
                active = None
                active_keys = set()
            continue
        if active is None:
            continue
        resolution_key = _resolution_key(event)
        if resolution_key is not None and resolution_key in active_keys and _is_success_event(event):
            active["status"] = "resolved"
            active["ended_at"] = event.timestamp
            active["event_chain"].append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "status": event.status,
                    "phase": event.phase,
                    "summary": event.summary,
                    "resolution_key": resolution_key,
                    "test_failures": _event_test_failures(event),
                }
            )
            _finalize_failure_chain(chains, active)
            active = None
            active_keys = set()
    if active is not None:
        active["status"] = "blocked"
        active["ended_at"] = str(active["started_at"])
        _finalize_failure_chain(chains, active)
    return chains


def _new_failure_chain(event: ObservationEvent) -> dict[str, object]:
    return {
        "issue": event.issue,
        "run_id": event.run_id,
        "phase": event.phase,
        "started_at": event.timestamp,
        "ended_at": event.timestamp,
        "status": "open",
        "failures": [],
        "event_chain": [],
    }


def _finalize_failure_chain(
    chains: list[dict[str, object]],
    chain: dict[str, object],
) -> None:
    failures = list(chain["failures"])
    chain["failure_count"] = len(failures)
    chain["failure_kinds"] = [str(item["kind"]) for item in failures]
    chain["failure_signatures"] = [str(item["signature"]) for item in failures]
    chain["pattern"] = " -> ".join(chain["failure_signatures"])
    chains.append(chain)


def _chain_test_failures(chain: Mapping[str, object]) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in chain.get("event_chain", []):
        if not isinstance(item, Mapping):
            continue
        failures = item.get("test_failures")
        if not isinstance(failures, Sequence) or isinstance(
            failures, (str, bytes, bytearray)
        ):
            continue
        for failure in failures:
            if not isinstance(failure, Mapping):
                continue
            normalized = {
                "runner": str(failure.get("runner", "")).strip(),
                "name": str(failure.get("name", "")).strip(),
                "file": str(failure.get("file", "")).strip(),
                "line": failure.get("line"),
                "summary": str(failure.get("summary", "")).strip(),
            }
            key = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            collected.append(normalized)
    return collected


def _classify_failure_event(event: ObservationEvent) -> FailureObservation | None:
    if event.status not in _FAILURE_STATUSES and not _is_failure_browser_event(event):
        return None
    kind = _failure_kind(event)
    if kind not in _FAILURE_KINDS:
        kind = "unknown"
    signature = _failure_signature(event=event, kind=kind)
    resolution_key = _resolution_key(event) or signature
    terminal = _is_terminal_failure(event)
    return FailureObservation(
        kind=kind,
        signature=signature,
        resolution_key=resolution_key,
        terminal=terminal,
        event=event,
    )


def _failure_kind(event: ObservationEvent) -> str:
    if event.event_type == "hook":
        return "hook"
    if event.event_type == "codex":
        parse_status = str(event.metadata.get("parse_status", "")).strip().lower()
        if parse_status and parse_status not in {"parsed", "success"}:
            return "data"
        return "codex"
    if event.event_type == "command":
        command = str(event.metadata.get("command", "")).strip().lower()
        if "gh pr merge" in command or "gh pr ready" in command:
            return "merge"
        return "command"
    if event.event_type == "review":
        return "review"
    if event.event_type == "stage_gate":
        return "policy"
    if event.event_type == "browser_observation":
        return "browser"
    if event.event_type == "recovery":
        return "recovery"
    return "unknown"


def _failure_signature(*, event: ObservationEvent, kind: str) -> str:
    if kind in {"hook", "command"}:
        command = str(event.metadata.get("command", "")).strip() or event.summary
        return f"{kind}:{command}"
    if kind == "codex":
        role = str(event.metadata.get("role", "")).strip() or "unknown"
        parse_status = str(event.metadata.get("parse_status", "")).strip() or "unknown"
        return f"codex:{role}:{parse_status}"
    if kind == "review":
        reviewer = str(event.metadata.get("reviewer_role", "")).strip() or "unknown"
        return f"review:{reviewer}"
    if kind == "merge":
        return "merge:gh-pr"
    if kind == "browser":
        console_errors = int(event.metadata.get("console_error_count", 0) or 0)
        page_errors = int(event.metadata.get("page_error_count", 0) or 0)
        return f"browser:console={console_errors}:page={page_errors}"
    if kind == "recovery":
        name = str(event.metadata.get("event", "")).strip() or event.summary
        return f"recovery:{name}"
    if kind == "policy":
        stage = str(event.metadata.get("stage", "")).strip() or event.phase or "unknown"
        return f"policy:stage_gate:{stage}"
    if kind == "data":
        role = str(event.metadata.get("role", "")).strip() or "unknown"
        parse_status = str(event.metadata.get("parse_status", "")).strip() or "unknown"
        return f"data:codex:{role}:{parse_status}"
    return f"unknown:{event.event_type}"


def _resolution_key(event: ObservationEvent) -> str | None:
    kind = _failure_kind(event)
    if kind in {"hook", "command"}:
        command = str(event.metadata.get("command", "")).strip()
        return f"{kind}:{command}" if command else None
    if kind in {"codex", "data"}:
        role = str(event.metadata.get("role", "")).strip()
        return f"codex:{role}" if role else None
    if kind == "review":
        reviewer = str(event.metadata.get("reviewer_role", "")).strip()
        return f"review:{reviewer}" if reviewer else "review:unknown"
    if kind == "policy":
        stage = str(event.metadata.get("stage", "")).strip() or event.phase or ""
        return f"policy:{stage}" if stage else None
    if kind == "recovery":
        name = str(event.metadata.get("event", "")).strip()
        return f"recovery:{name}" if name else None
    if kind == "browser":
        return "browser:observation"
    return f"{kind}:{event.event_type}"


def _is_success_event(event: ObservationEvent) -> bool:
    if event.status in _SUCCESS_STATUSES:
        return True
    return event.event_type == "browser_observation" and not _is_failure_browser_event(event)


def _is_terminal_failure(event: ObservationEvent) -> bool:
    if event.status in {"block", "blocked", "interrupted"}:
        return True
    recovery_event = str(event.metadata.get("event", "")).strip()
    return recovery_event.endswith("_blocked")


def _is_failure_browser_event(event: ObservationEvent) -> bool:
    if event.event_type != "browser_observation":
        return False
    return any(
        int(event.metadata.get(key, 0) or 0) > 0
        for key in ("console_error_count", "page_error_count")
    )


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event_test_failures(event: ObservationEvent) -> list[dict[str, object]]:
    failures = event.metadata.get("test_failures")
    if not isinstance(failures, Sequence) or isinstance(
        failures, (str, bytes, bytearray)
    ):
        return []
    normalized: list[dict[str, object]] = []
    for failure in failures:
        if not isinstance(failure, Mapping):
            continue
        normalized.append(
            {
                "runner": str(failure.get("runner", "")).strip(),
                "name": str(failure.get("name", "")).strip(),
                "file": str(failure.get("file", "")).strip(),
                "line": failure.get("line"),
                "summary": str(failure.get("summary", "")).strip(),
            }
        )
    return normalized
