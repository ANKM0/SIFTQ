import argparse
import json
import subprocess

from .task_store import load_task

STATUSES = ("pending", "running", "blocked", "done", "failed")
PHASES = ("spec", "test", "implement", "observe", "decide", "checker", "review", "human", "done", "failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-sync")
    parser.add_argument("task")
    parser.add_argument("--pr-url")
    parser.add_argument("--sync-labels", action="store_true")
    parser.add_argument("--label-prefix", default="taqt/status/")
    parser.add_argument("--phase-label-prefix", default="taqt/phase/")
    parser.add_argument("--close-done", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    _path, task = load_task(args.task)
    source = task["source"]
    issue_ref = f"{source['repo']}#{source['issue_number']}"
    body = (
        "taqt task update.\n\n"
        f"- task: `{task['id']}`\n"
        f"- status: `{task['status']}`\n"
        f"- phase: `{task['phase']}`\n"
        f"- run state: `{task.get('run', {}).get('state_path')}`\n"
    )
    if args.pr_url:
        body += f"- PR: {args.pr_url}\n"
    body += f"\n<!-- taqt:{task['id']} -->\n"
    commands = _label_commands(task, args.label_prefix, args.phase_label_prefix) if args.sync_labels else []
    if args.close_done and task["status"] == "done":
        commands.append(
            [
                "gh",
                "issue",
                "close",
                str(source["issue_number"]),
                "--repo",
                str(source["repo"]),
                "--comment",
                f"Completed by taqt task {task['id']}.",
            ]
        )
    if not args.execute:
        print(f"{issue_ref}:")
        print(body)
        for command in commands:
            print(" ".join(command))
        return 0
    for command in commands:
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return _upsert_comment(
        repo=str(source["repo"]),
        issue_number=int(source["issue_number"]),
        marker=f"<!-- taqt:{task['id']} -->",
        body=body,
    )


def _label_commands(task: dict[str, object], label_prefix: str, phase_label_prefix: str) -> list[list[str]]:
    source = task["source"]
    status = str(task["status"])
    phase = str(task.get("phase") or status)
    command = [
        "gh",
        "issue",
        "edit",
        str(source["issue_number"]),
        "--repo",
        str(source["repo"]),
        "--add-label",
        f"{label_prefix}{status}",
        "--add-label",
        f"{phase_label_prefix}{phase}",
    ]
    for candidate in STATUSES:
        if candidate != status:
            command.extend(["--remove-label", f"{label_prefix}{candidate}"])
    for candidate in PHASES:
        if candidate != phase:
            command.extend(["--remove-label", f"{phase_label_prefix}{candidate}"])
    return [command]


def _upsert_comment(*, repo: str, issue_number: int, marker: str, body: str) -> int:
    comments = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue_number}/comments"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if comments.returncode != 0:
        print(comments.stderr, end="")
        return comments.returncode
    comment_id = _find_comment_id(comments.stdout, marker)
    if comment_id is None:
        command = [
            "gh",
            "issue",
            "comment",
            str(issue_number),
            "--repo",
            repo,
            "--body",
            body,
        ]
    else:
        command = ["gh", "api", f"repos/{repo}/issues/comments/{comment_id}", "-X", "PATCH", "-f", f"body={body}"]
    return subprocess.run(command, check=False).returncode


def _find_comment_id(payload: str, marker: str) -> int | None:
    comments = json.loads(payload)
    if not isinstance(comments, list):
        return None
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body")
        if isinstance(body, str) and marker in body:
            comment_id = comment.get("id")
            return int(comment_id) if comment_id is not None else None
    return None


if __name__ == "__main__":
    raise SystemExit(main())
