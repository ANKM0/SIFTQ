#!/usr/bin/env python3
import argparse
import re
import shlex
import subprocess
from pathlib import Path


REPO = "ANKM0/SIFTQ"
TEMPLATE_FILES = {
    "feature": "feature_change.md",
    "bug": "bug_report.md",
    "research": "research.md",
}
TAQT_LABELS = ("taqt:enabled",)
FORBIDDEN_LABELS = {"taqt:pending", "taqt:phase:triage", "taqt:blocked", "taqt:running", "taqt:done"}


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / ".github").is_dir():
            return path
    raise RuntimeError("repository root not found")


def split_labels(values: list[str]) -> list[str]:
    labels: list[str] = []
    for value in values:
        for label in value.split(","):
            stripped = label.strip()
            if stripped:
                labels.append(stripped)
    return labels


def build_labels(labels: list[str], taqt: bool) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for label in labels + (list(TAQT_LABELS) if taqt else []):
        if label in FORBIDDEN_LABELS:
            raise ValueError(f"forbidden label: {label}")
        if label not in seen:
            result.append(label)
            seen.add(label)
    return result


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip()).strip("-._")
    return slug[:80] or "issue"


def default_body_file(issue_type: str, title: str) -> Path:
    return Path("/tmp/siftq-issues") / f"{issue_type}-{slugify_title(title)}.md"


def read_template(root: Path, issue_type: str) -> str:
    template = root / ".github" / "ISSUE_TEMPLATE" / TEMPLATE_FILES[issue_type]
    return template.read_text(encoding="utf-8")


def read_body_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_body_file(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if body.endswith("\n") else f"{body}\n", encoding="utf-8")


def issue_create_args(title: str, body_file: Path, labels: list[str]) -> list[str]:
    args = [
        "gh",
        "issue",
        "create",
        "--repo",
        REPO,
        "--title",
        title,
        "--body-file",
        str(body_file),
    ]
    for label in labels:
        args.extend(["--label", label])
    return args


def shell_command(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="Create or dry-run SIFTQ GitHub issue body files and gh commands.",
    )
    argument_parser.add_argument(
        "--type",
        choices=sorted(TEMPLATE_FILES),
        required=True,
        help="Issue type whose canonical .github/ISSUE_TEMPLATE file is used.",
    )
    argument_parser.add_argument("--title", required=True, help="GitHub issue title.")
    argument_parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="Issue label. Can be repeated or comma-separated.",
    )
    argument_parser.add_argument(
        "--taqt",
        action="store_true",
        help="Add the taqt activation label: taqt:enabled.",
    )
    argument_parser.add_argument(
        "--body-file",
        type=Path,
        help="Output issue body file. Defaults to /tmp/siftq-issues/<type>-<title>.md.",
    )
    argument_parser.add_argument(
        "--body-source",
        type=Path,
        help="Complete drafted issue body to copy into --body-file instead of the raw template.",
    )
    mode = argument_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the body file and print the body plus gh command without creating the issue.",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Write the body file and run gh issue create.",
    )
    return argument_parser


def main() -> int:
    argument_parser = parser()
    args = argument_parser.parse_args()
    root = repository_root()
    template_body = read_template(root, args.type)
    body = read_body_source(args.body_source) if args.body_source else template_body
    try:
        labels = build_labels(split_labels(args.label), args.taqt)
    except ValueError as error:
        argument_parser.error(str(error))
    body_file = args.body_file or default_body_file(args.type, args.title)

    write_body_file(body_file, body)
    command_args = issue_create_args(args.title, body_file, labels)
    command = shell_command(command_args)

    print(f"title: {args.title}")
    print(f"type: {args.type}")
    print("labels:")
    for label in labels:
        print(f"- {label}")
    if not labels:
        print("- (none)")
    print(f"body_file: {body_file}")
    print("body:")
    print(body, end="" if body.endswith("\n") else "\n")
    print("command:")
    print(command)

    if args.execute:
        subprocess.run(command_args, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
