#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

VERSION_PATTERN = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
WORKER_PATHS = ("src/", "migrations/", "wrangler.jsonc", "bun.lock")


@dataclass(frozen=True)
class ReleasePlan:
    version: str
    ref: str
    base: str | None
    worker_change: bool
    migrations: list[str]
    mode: str


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def normalized_version(value: str) -> str:
    match = VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("version must be vX.Y.Z or X.Y.Z")
    return ".".join(match.groups())


def tag_name(version: str) -> str:
    return f"v{normalized_version(version)}"


def changed_paths(base: str | None, ref: str) -> list[str]:
    if base is None:
        return []
    return [line for line in command("git", "diff", "--name-only", f"{base}..{ref}").splitlines() if line]


def build_plan(version: str, ref: str, base: str | None) -> ReleasePlan:
    resolved_ref = command("git", "rev-parse", f"{ref}^{{commit}}")
    paths = changed_paths(base, resolved_ref)
    migrations = [path for path in paths if path.startswith("migrations/")]
    worker_change = any(path.startswith(WORKER_PATHS[:2]) or path in WORKER_PATHS[2:] for path in paths)
    return ReleasePlan(tag_name(version), resolved_ref, base, worker_change, migrations, "release+deploy" if worker_change else "release-only")


def package_version(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["version"])


def update_package_version(path: Path, version: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = normalized_version(version)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_execute(args: argparse.Namespace) -> None:
    if not args.execute:
        raise ValueError("This operation changes external or repository state; pass --execute.")


def require_clean() -> None:
    if command("git", "status", "--porcelain"):
        raise ValueError("worktree must be clean")


def ensure_version_matches(version: str) -> None:
    actual = package_version(Path("package.json"))
    if actual != normalized_version(version):
        raise ValueError(f"package.json version is {actual}; expected {normalized_version(version)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and execute SIFTQ releases and Worker deployments.")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--version", required=True)
    plan.add_argument("--ref", default="HEAD")
    plan.add_argument("--base")
    version = subparsers.add_parser("version")
    version.add_argument("--version", required=True)
    version.add_argument("--execute", action="store_true")
    release = subparsers.add_parser("release")
    release.add_argument("--version", required=True)
    release.add_argument("--ref", default="HEAD")
    release.add_argument("--execute", action="store_true")
    deploy = subparsers.add_parser("deploy")
    deploy.add_argument("--tag", required=True)
    deploy.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.operation == "plan":
            print(json.dumps(asdict(build_plan(args.version, args.ref, args.base)), ensure_ascii=False, indent=2))
        elif args.operation == "version":
            require_execute(args)
            update_package_version(Path("package.json"), args.version)
            print(f"package.json version updated to {normalized_version(args.version)}")
        elif args.operation == "release":
            require_execute(args)
            require_clean()
            ensure_version_matches(args.version)
            ref = command("git", "rev-parse", f"{args.ref}^{{commit}}")
            if ref != command("git", "rev-parse", "HEAD"):
                raise ValueError("release ref must equal the checked-out HEAD in the dedicated worktree")
            tag = tag_name(args.version)
            if subprocess.run(
                ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                check=False,
                stdout=subprocess.DEVNULL,
            ).returncode == 0:
                raise ValueError(f"tag already exists: {tag}")
            subprocess.run(["git", "tag", "-a", tag, ref, "-m", tag], check=True)
            subprocess.run(["git", "push", "origin", f"refs/tags/{tag}"], check=True)
            print(f"pushed {tag} at {ref}")
        else:
            require_execute(args)
            require_clean()
            tagged = command("git", "rev-parse", f"{args.tag}^{{commit}}")
            if tagged != command("git", "rev-parse", "HEAD"):
                raise ValueError("checked-out HEAD must equal the deployment tag")
            subprocess.run(["bun", "x", "wrangler", "d1", "migrations", "list", "siftq", "--remote"], check=True)
            subprocess.run(["bun", "x", "wrangler", "deploy"], check=True)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
