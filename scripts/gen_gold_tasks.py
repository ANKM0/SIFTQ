#!/usr/bin/env python3
"""Generate T3 gold specs from completed taqt tasks and merged fixes.

For each completed task's issue, find the first commit that references the issue
(the fix) and use its parent as the replay base commit. The task definition and a
replay spec are written under eval/gold/loop-tasks/.
"""
import argparse
import re
import subprocess
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TASKS_ROOT = REPOSITORY_ROOT / ".taqt" / "tasks"
GOLD_ROOT = REPOSITORY_ROOT / "eval" / "gold" / "loop-tasks"
GOLD_TASKS_ROOT = GOLD_ROOT / "tasks"
ARMS = {
    "A": ".taqt/loops/main_loop.yaml",
    "B": "eval/baselines/loop/main_loop_minimal.yaml",
}
CHECKS = (
    "task -t .config/Taskfile.yml ci:typecheck",
    "task -t .config/Taskfile.yml ci:test:unit",
)


def load_done_tasks() -> dict[int, dict]:
    by_issue: dict[int, dict] = {}
    for path in sorted(TASKS_ROOT.glob("*.yaml")):
        try:
            task = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(task, dict) or task.get("status") != "done":
            continue
        source = task.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("issue_number"), int):
            continue
        by_issue.setdefault(source["issue_number"], task)
    return by_issue


def fix_commits() -> dict[int, tuple[str, str]]:
    log = subprocess.run(
        ["git", "log", "--reverse", "--format=%H%x09%P%x09%s"],
        cwd=REPOSITORY_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.splitlines()
    found: dict[int, tuple[str, str]] = {}
    for line in log:
        sha, parents, subject = line.split("\t", 2)
        parent = parents.split()[0] if parents.split() else ""
        if not parent:
            continue
        for match in re.finditer(r"#(\d+)", subject):
            issue = int(match.group(1))
            found.setdefault(issue, (sha, parent))
    return found


def build_task(task: dict) -> dict:
    return {
        "id": task["id"],
        "source": task["source"],
        "status": "pending",
        "phase": "spec",
        "priority": task.get("priority", "normal"),
        "input": task.get("input", {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gen-gold-tasks")
    parser.add_argument("--limit", type=int, default=35)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    by_issue = load_done_tasks()
    fixes = fix_commits()
    GOLD_TASKS_ROOT.mkdir(parents=True, exist_ok=True)

    written = 0
    for issue in sorted(by_issue):
        if written >= args.limit:
            break
        fix = fixes.get(issue)
        if fix is None:
            continue
        _sha, base_commit = fix
        task = by_issue[issue]
        task_id = str(task["id"])
        spec = {
            "name": task_id,
            "arms": dict(ARMS),
            "checks": list(CHECKS),
            "base_commit": base_commit,
            "repetitions": 3,
        }
        spec_path = GOLD_ROOT / f"{task_id}.yaml"
        task_path = GOLD_TASKS_ROOT / f"{task_id}.yaml"
        print(f"{task_id}: base={base_commit[:8]} issue={issue}")
        if args.execute:
            spec_path.write_text(
                yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            task_path.write_text(
                yaml.safe_dump(build_task(task), allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        written += 1

    print(f"gold specs: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
