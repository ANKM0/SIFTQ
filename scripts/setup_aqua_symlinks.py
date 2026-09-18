"""Maintain the `.aqua/` discovery symlinks for the `.config/` aqua files.

aqua resolves a proxied command from `AQUA_CONFIG`, a global config, or
`aqua.yaml` / `.aqua/aqua.yaml` / `aqua/aqua.yaml` found upward from the current
directory (ADR 0048). The repository keeps its aqua configuration in `.config/`,
which aqua does not search, so `.aqua/aqua.yaml` and the repository-local
registry are linked into `.aqua/`. Run with `--check` to verify without writing.
"""

import argparse
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINKS = {
    ".aqua/aqua.yaml": "../.config/aqua.yaml",
    ".aqua/aqua-code-mode-host-registry.yaml": (
        "../.config/aqua-code-mode-host-registry.yaml"
    ),
}


def repository_root() -> Path:
    return REPOSITORY_ROOT


def link_state(root: Path, link: str, target: str) -> str:
    path = root / link
    source = (path.parent / target).resolve()
    if path.is_symlink():
        if os.readlink(path) == target and source.is_file():
            return "ok"
        return "stale"
    if path.exists():
        return "conflict"
    if not source.is_file():
        return "missing-source"
    return "missing"


def set_link(root: Path, link: str, target: str) -> None:
    path = root / link
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.exists():
        path.unlink()
    path.symlink_to(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help="Repository root that contains `.config/` and `.aqua/`.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report missing or stale links without changing the filesystem.",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    failed = False
    for link, target in LINKS.items():
        state = link_state(root, link, target)
        if state == "ok":
            print(f"ok: {link} -> {target}")
            continue
        if state == "conflict":
            print(
                f"error: {link} exists and is not the expected symlink",
                file=sys.stderr,
            )
            failed = True
            continue
        if state == "missing-source":
            print(f"error: {link} target {target} does not exist", file=sys.stderr)
            failed = True
            continue
        if args.check:
            print(f"missing: {link} -> {target}", file=sys.stderr)
            failed = True
            continue
        set_link(root, link, target)
        print(f"created: {link} -> {target}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
