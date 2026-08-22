import argparse
import json
import subprocess

from .task_store import load_task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-github-sync")
    parser.add_argument("task")
    parser.add_argument("--pr-url")
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
    if not args.execute:
        print(f"{issue_ref}:")
        print(body)
        return 0
    return _upsert_comment(
        repo=str(source["repo"]),
        issue_number=int(source["issue_number"]),
        marker=f"<!-- taqt:{task['id']} -->",
        body=body,
    )


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
