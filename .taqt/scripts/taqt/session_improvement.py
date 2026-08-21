import argparse
import hashlib
import json
import re
import shlex
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"
CORRECTION_PATTERNS = (
    "違う",
    "訂正",
    "ではなく",
    "認識が違",
    "not correct",
    "actually",
    "that's wrong",
)
MARKER_PREFIX = "<!-- self-improvement:"


@dataclass(frozen=True)
class Evidence:
    kind: str
    pattern: str
    session_id: str
    task_id: str
    seen_at: datetime


@dataclass(frozen=True)
class Candidate:
    key: str
    kind: str
    pattern: str
    occurrences: int
    task_count: int
    first_seen: datetime
    last_seen: datetime

    @property
    def target(self) -> str:
        return "Taskfile" if self.kind == "command_failure" else "rule_or_skill"


def discover_worktrees(repository_root: Path) -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repository_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "could not list git worktrees")
    return tuple(
        Path(line.removeprefix("worktree ")).resolve()
        for line in completed.stdout.splitlines()
        if line.startswith("worktree ")
    )


def load_evidence(session_path: Path, worktrees: Iterable[Path]) -> list[Evidence]:
    records = _read_json_lines(session_path)
    metadata = next((record.get("payload", {}) for record in records if record.get("type") == "session_meta"), {})
    cwd = Path(str(metadata.get("cwd", ""))).resolve()
    if not any(_is_within(cwd, worktree) for worktree in worktrees):
        return []
    session_id = str(metadata.get("id") or session_path.stem)
    task_id = str((metadata.get("git") or {}).get("branch") or cwd)
    evidence: list[Evidence] = []
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        seen_at = _parse_timestamp(record.get("timestamp") or metadata.get("timestamp"))
        if seen_at is None:
            continue
        if record.get("type") == "event_msg" and payload.get("type") == "exec_command_end":
            if int(payload.get("exit_code") or 0) != 0:
                command = normalize_command(str(payload.get("command") or ""))
                if command:
                    evidence.append(Evidence("command_failure", command, session_id, task_id, seen_at))
        if record.get("type") == "event_msg" and payload.get("type") == "user_message":
            message = str(payload.get("message") or "")
            correction = correction_pattern(message)
            if correction:
                evidence.append(Evidence("user_correction", correction, session_id, task_id, seen_at))
    return evidence


def collect_candidates(
    session_root: Path,
    worktrees: Iterable[Path],
    *,
    now: datetime,
    min_occurrences: int = 3,
    min_tasks: int = 2,
    window_days: int = 30,
) -> list[Candidate]:
    cutoff = now - timedelta(days=window_days)
    grouped: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for session_path in session_root.rglob("*.jsonl"):
        for item in load_evidence(session_path, worktrees):
            if item.seen_at >= cutoff:
                grouped[(item.kind, item.pattern)].append(item)
    candidates = []
    for (kind, pattern), items in grouped.items():
        tasks = {item.task_id for item in items}
        if len(items) < min_occurrences or len(tasks) < min_tasks:
            continue
        candidates.append(
            Candidate(
                key=pattern_key(kind, pattern),
                kind=kind,
                pattern=pattern,
                occurrences=len(items),
                task_count=len(tasks),
                first_seen=min(item.seen_at for item in items),
                last_seen=max(item.seen_at for item in items),
            )
        )
    return sorted(candidates, key=lambda item: (item.kind, item.pattern))


def normalize_command(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return ""
    if tokens[0] == "task" and len(tokens) > 1 and re.fullmatch(r"[a-z0-9:-]+", tokens[1]):
        return f"task {tokens[1]}"
    return tokens[0]


def correction_pattern(message: str) -> str | None:
    normalized = re.sub(r"\s+", " ", message).strip().lower()
    for pattern in CORRECTION_PATTERNS:
        if pattern.lower() in normalized:
            return pattern.lower()
    return None


def pattern_key(kind: str, pattern: str) -> str:
    digest = hashlib.sha256(f"{kind}:{pattern}".encode()).hexdigest()[:12]
    return f"{kind}-{digest}"


def render_candidate(candidate: Candidate) -> str:
    return "\n".join(
        [
            f"## self-improvement: {candidate.key}",
            "",
            f"{MARKER_PREFIX}{candidate.key} -->",
            f"- kind: `{candidate.kind}`",
            f"- suggested target: `{candidate.target}`",
            f"- pattern: `{candidate.pattern}`",
            f"- occurrences: {candidate.occurrences}",
            f"- distinct tasks: {candidate.task_count}",
            f"- first seen: {candidate.first_seen.isoformat()}",
            f"- last seen: {candidate.last_seen.isoformat()}",
            "",
            "生ログ・コマンド出力・秘匿値は Issue に含めない。",
        ]
    )


def existing_issue_keys(repo: str) -> set[str]:
    completed = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "all", "--limit", "1000", "--json", "body"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "could not list GitHub issues")
    return issue_keys_from_payload(completed.stdout)


def issue_keys_from_payload(payload: str) -> set[str]:
    return set(re.findall(r"<!-- self-improvement:([^ ]+) -->", payload))


def create_issue(repo: str, candidate: Candidate) -> None:
    title = f"self-improvement: {candidate.target} を改善 ({candidate.key})"
    completed = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--label", "enhancement", "--body", render_candidate(candidate)],
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"could not create issue for {candidate.key}")


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-session-improvement")
    parser.add_argument("--repo", default="ANKM0/SIFTQ")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    candidates = collect_candidates(args.sessions_root, discover_worktrees(args.repository_root), now=now)
    if not candidates:
        print("No self-improvement candidates.")
        return 0
    existing = existing_issue_keys(args.repo) if args.execute else set()
    for candidate in candidates:
        if candidate.key in existing:
            print(f"existing: {candidate.key}")
            continue
        print(render_candidate(candidate))
        if args.execute:
            create_issue(args.repo, candidate)
            print(f"created: {candidate.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
