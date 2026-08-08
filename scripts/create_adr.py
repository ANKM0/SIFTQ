#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


ADR_DIR = Path("docs/adr")
TEMPLATE = Path(".agents/templates/adr.md")


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / ADR_DIR).is_dir():
            return path
    raise RuntimeError("repository root not found")


def next_number(root: Path) -> int:
    numbers = []
    for path in (root / ADR_DIR).glob("[0-9][0-9][0-9][0-9]-*.md"):
        numbers.append(int(path.name[:4]))
    return max(numbers, default=0) + 1


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "adr"


def render_template(root: Path, number: int, title: str) -> str:
    body = (root / TEMPLATE).read_text(encoding="utf-8")
    body = body.replace("<number>", f"{number:04d}")
    body = body.replace("<title>", title)
    body = body.replace("<Title>", title)
    return body


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create a SIFTQ ADR from the template.")
    p.add_argument("--title", required=True)
    p.add_argument("--slug", help="File slug. Defaults to title slug.")
    p.add_argument("--number", type=int, help="ADR number. Defaults to next number.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--write", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    root = repository_root()
    number = args.number or next_number(root)
    slug = args.slug or slugify(args.title)
    path = root / ADR_DIR / f"{number:04d}-{slug}.md"
    body = render_template(root, number, args.title)

    print(f"path: {path.relative_to(root)}")
    print("body:")
    print(body, end="" if body.endswith("\n") else "\n")

    if args.write:
        path.write_text(body if body.endswith("\n") else f"{body}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
