import csv
import re
import sys

from pathlib import Path

from checker import repository_root


GLOSSARY_PATH = "scripts/ci/glossary.csv"


def load_terms(root: Path) -> list[tuple[str, str]]:
    path = root / GLOSSARY_PATH
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return [
            (row["preferred"], row["forbidden"])
            for row in csv.DictReader(file)
        ]


def find_violations(
    text: str,
    relative_path: str,
    terms: list[tuple[str, str]],
) -> list[str]:
    violations: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if "`" in line:
            continue
        for preferred, forbidden in terms:
            pattern = re.compile(rf"\b{re.escape(forbidden)}\b")
            if pattern.search(line):
                violations.append(
                    f"{relative_path}:{index}: {forbidden} -> {preferred} "
                    f"({line.strip()})"
                )
    return violations


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "docs").rglob("*.md")
        if ".git" not in path.parts and "graphify-out" not in path.parts
    )


def main() -> int:
    root = repository_root()
    terms = load_terms(root)
    failed = False
    for path in markdown_files(root):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for violation in find_violations(text, relative_path, terms):
            print(violation)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
