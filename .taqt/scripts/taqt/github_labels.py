import json
import subprocess


ENABLED_LABEL = "taqt:enabled"


def fetch_issue_labels(repo: str, issue_number: int) -> set[str] | None:
    completed = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "labels"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    labels = payload.get("labels") if isinstance(payload, dict) else None
    if not isinstance(labels, list):
        return None
    return {
        str(label["name"])
        for label in labels
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    }


def enabled_error(task: dict[str, object]) -> str | None:
    source = task.get("source")
    if not isinstance(source, dict):
        return "task source is missing"
    repo = source.get("repo")
    issue_number = source.get("issue_number")
    if not isinstance(repo, str) or not isinstance(issue_number, int):
        return "task source does not identify a GitHub issue"
    labels = fetch_issue_labels(repo, issue_number)
    if labels is None:
        return f"could not verify {repo}#{issue_number} labels; refusing to run"
    if ENABLED_LABEL not in labels:
        return f"{repo}#{issue_number} does not have {ENABLED_LABEL}; refusing to run"
    return None
