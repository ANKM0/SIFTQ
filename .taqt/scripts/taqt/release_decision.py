import argparse
import re
import subprocess
from pathlib import Path

VERSION_PLACEHOLDER = "vX.Y.Z"
REF_PLACEHOLDER = "<sha>"
BASE_PLACEHOLDER = "<tag>"
VERSION_PATTERN = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def build_plan_command(*, version: str, ref: str, base: str, prs: list[str] | None = None) -> list[str]:
    command = ["task", "-t", ".config/Taskfile.yml", "release:plan", "--"]
    if version and version != VERSION_PLACEHOLDER:
        command += ["--version", version]
    if ref and ref != REF_PLACEHOLDER:
        command += ["--ref", ref]
    if base and base != BASE_PLACEHOLDER:
        command += ["--base", base]
    for pr in prs or []:
        command += ["--pr", pr]
    return command


def decision_checklist() -> str:
    return (
        "ADR 0034: Worker成果物・D1 migration・本番設定変更あり=Release+deploy、それ以外=Release-only。\n"
        "Release-onlyではWorkerをデプロイしない。\n"
        "タグpush・remote migration・Workerデプロイは明示承認なしに実行しない。\n"
        "判断結果（対象SHA・デプロイ有無・migration確認方針）をRelease Notes記録方針に沿って残す。"
    )


def latest_tag(workspace: Path) -> str | None:
    if not workspace.is_dir():
        return None
    completed = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    tag = completed.stdout.strip()
    return tag if VERSION_PATTERN.fullmatch(tag) else None


def next_versions(latest: str | None) -> tuple[str | None, str | None]:
    if latest is None:
        return None, None
    major, minor, patch = (int(part) for part in latest.lstrip("v").split("."))
    return f"v{major}.{minor}.{patch + 1}", f"v{major}.{minor + 1}.0"


def render_reminder(
    *,
    version: str,
    ref: str,
    base: str,
    prs: list[str],
    latest: str | None,
    next_patch: str | None,
    next_minor: str | None,
) -> str:
    command = " ".join(build_plan_command(version=version, ref=ref, base=base, prs=prs))
    versions = "\n".join(
        [
            f"Release version: {version}",
            f"Latest tag: {latest or 'unknown'}",
            f"Next patch: {next_patch or 'unknown'}",
            f"Next minor: {next_minor or 'unknown'}",
        ]
    )
    return f"{versions}\n{command}\n{decision_checklist()}"


def is_concrete(*, version: str, ref: str, base: str, prs: list[str] | None = None) -> bool:
    return (
        version not in (VERSION_PLACEHOLDER, "")
        and ref != REF_PLACEHOLDER
        and (base != BASE_PLACEHOLDER or bool(prs))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-release-decision")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--version", default=VERSION_PLACEHOLDER)
    parser.add_argument("--ref", default=REF_PLACEHOLDER)
    parser.add_argument("--base", default=BASE_PLACEHOLDER)
    parser.add_argument("--pr", action="append", default=[])
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    latest = latest_tag(args.workspace)
    next_patch, next_minor = next_versions(latest)
    print(
        render_reminder(
            version=args.version,
            ref=args.ref,
            base=args.base,
            prs=args.pr,
            latest=latest,
            next_patch=next_patch,
            next_minor=next_minor,
        )
    )
    if not args.execute or not is_concrete(version=args.version, ref=args.ref, base=args.base, prs=args.pr):
        return 0
    completed = subprocess.run(
        build_plan_command(version=args.version, ref=args.ref, base=args.base, prs=args.pr),
        cwd=args.workspace,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
