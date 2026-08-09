#!/usr/bin/env python3
import argparse
from pathlib import Path


DESIGN_DIR = Path("docs/design")
TEMPLATE = Path("docs/design/templates/design-doc.md")


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / DESIGN_DIR).is_dir():
            return path
    raise RuntimeError("repository root not found")


def render_template(root: Path, pr_number: int, title: str) -> str:
    body = (root / TEMPLATE).read_text(encoding="utf-8")
    body = body.replace("<number>", f"#{pr_number}")
    body = body.replace("<title>", title)
    body = body.replace("<Title>", title)
    return body


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create a SIFTQ Design Doc from the template.")
    p.add_argument("--title", required=True)
    p.add_argument("--pr", type=int, required=True, help="Pull request number.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--write", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.pr < 1:
        parser().error("--pr must be a positive integer")
    root = repository_root()
    path = root / DESIGN_DIR / f"#{args.pr}.md"
    body = render_template(root, args.pr, args.title)

    print(f"path: {path.relative_to(root)}")
    print("body:")
    print(body, end="" if body.endswith("\n") else "\n")

    if args.write:
        path.write_text(body if body.endswith("\n") else f"{body}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
