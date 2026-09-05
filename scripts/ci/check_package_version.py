#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path


VERSION_RE = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / "package.json").is_file():
            return path
    raise RuntimeError("repository root not found")


def parse_version(value: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid release version: {value}")
    return tuple(int(part) for part in match.groups())


def package_version(root: Path) -> tuple[int, int, int]:
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    return parse_version(str(package["version"]))


def latest_release_version(root: Path) -> tuple[int, int, int] | None:
    tags = subprocess.check_output(
        ["git", "-C", str(root), "tag", "--list", "v[0-9]*"],
        text=True,
    ).splitlines()
    versions = [parse_version(tag) for tag in tags]
    return max(versions) if versions else None


def format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def main() -> int:
    root = repository_root()
    current = package_version(root)
    latest = latest_release_version(root)
    if latest is None:
        print(f"package.json version: {format_version(current)} (no release tags found)")
        return 0
    if current < latest:
        print(
            "package.json version is older than the latest release tag: "
            f"{format_version(current)} < {format_version(latest)}"
        )
        return 1
    print(
        "package.json version is not behind the latest release tag: "
        f"{format_version(current)} >= {format_version(latest)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
