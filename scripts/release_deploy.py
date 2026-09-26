#!/usr/bin/env python3
import argparse
import json
import posixpath
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

VERSION_PATTERN = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
WORKER_PREFIXES = ("src/", "migrations/")
WRANGLER_CONFIGS = (".config/wrangler.jsonc", "wrangler.jsonc")


@dataclass(frozen=True)
class ReleasePlan:
    version: str | None
    ref: str
    base: str | None
    latest_tag: str | None
    next_patch: str | None
    next_minor: str | None
    prs: list[str]
    worker_change: bool
    migrations: list[str]
    mode: str


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


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


def pr_changed_paths(pr: str) -> list[str]:
    payload = json.loads(command("gh", "pr", "view", pr, "--json", "files"))
    return [str(entry["path"]) for entry in payload.get("files") or [] if entry.get("path")]


def pr_union_paths(prs: list[str]) -> list[str]:
    return list(dict.fromkeys(path for pr in prs for path in pr_changed_paths(pr)))


def latest_tag() -> str | None:
    try:
        tag = command("git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    except subprocess.CalledProcessError:
        return None
    return tag if VERSION_PATTERN.fullmatch(tag) else None


def next_versions(latest: str | None) -> tuple[str | None, str | None]:
    if latest is None:
        return None, None
    major, minor, patch = (int(part) for part in normalized_version(latest).split("."))
    return f"v{major}.{minor}.{patch + 1}", f"v{major}.{minor + 1}.0"


def parse_jsonc(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        stripped = re.sub(r"(?m)//.*$", "", stripped)
        return json.loads(stripped)


def effective_wrangler(path: str, payload: dict) -> dict:
    result = json.loads(json.dumps(payload))
    result.pop("$schema", None)
    base = posixpath.dirname(path)
    if "main" in result:
        result["main"] = posixpath.normpath(posixpath.join(base, result["main"]))
    for database in result.get("d1_databases") or []:
        if isinstance(database, dict) and "migrations_dir" in database:
            database["migrations_dir"] = posixpath.normpath(posixpath.join(base, database["migrations_dir"]))
    return result


def wrangler_config_at(ref: str) -> dict | None:
    for path in WRANGLER_CONFIGS:
        try:
            text = command("git", "show", f"{ref}:{path}")
        except subprocess.CalledProcessError:
            continue
        return effective_wrangler(path, parse_jsonc(text))
    return None


def worker_config_changed(base: str | None, ref: str) -> bool:
    if base is None:
        return False
    return wrangler_config_at(base) != wrangler_config_at(ref)


def build_plan(version: str | None, ref: str, base: str | None, prs: list[str] | None = None) -> ReleasePlan:
    prs = list(prs or [])
    resolved_ref = command("git", "rev-parse", f"{ref}^{{commit}}")
    paths = pr_union_paths(prs) if prs else changed_paths(base, resolved_ref)
    migrations = [path for path in paths if path.startswith("migrations/")]
    worker_change = (
        any(path.startswith(WORKER_PREFIXES) or path == "bun.lock" for path in paths)
        or worker_config_changed(base, resolved_ref)
        or (base is None and any(path in WRANGLER_CONFIGS for path in paths))
    )
    tag = latest_tag()
    next_patch, next_minor = next_versions(tag)
    return ReleasePlan(
        version=tag_name(version) if version else None,
        ref=resolved_ref,
        base=base,
        latest_tag=tag,
        next_patch=next_patch,
        next_minor=next_minor,
        prs=prs,
        worker_change=worker_change,
        migrations=migrations,
        mode="release+deploy" if worker_change else "release-only",
    )


def d1_database_name(path: Path = Path(".config/wrangler.jsonc")) -> str:
    payload = parse_jsonc(path.read_text(encoding="utf-8"))
    databases = payload.get("d1_databases") or []
    for entry in databases:
        if entry.get("binding") == "DB" and entry.get("database_name"):
            return str(entry["database_name"])
    for entry in databases:
        if entry.get("database_name"):
            return str(entry["database_name"])
    raise ValueError("D1 database_name not found in .config/wrangler.jsonc")


def require_execute(args: argparse.Namespace) -> None:
    if not args.execute:
        raise ValueError("This operation changes external or repository state; pass --execute.")


def require_clean() -> None:
    if command("git", "status", "--porcelain"):
        raise ValueError("worktree must be clean")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and execute releases and Worker deployments.")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--version")
    plan.add_argument("--ref", default="HEAD")
    plan.add_argument("--base")
    plan.add_argument("--pr", action="append", default=[])
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
            print(json.dumps(asdict(build_plan(args.version, args.ref, args.base, args.pr)), ensure_ascii=False, indent=2))
        elif args.operation == "release":
            require_execute(args)
            require_clean()
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
            subprocess.run(
                ["bun", "x", "wrangler", "d1", "migrations", "list", d1_database_name(Path(".config/wrangler.jsonc")), "--remote", "-c", ".config/wrangler.jsonc"],
                check=True,
            )
            subprocess.run(["bun", "x", "wrangler", "deploy", "-c", ".config/wrangler.jsonc"], check=True)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
