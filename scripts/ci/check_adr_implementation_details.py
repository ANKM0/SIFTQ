import re
import sys

from pathlib import Path

from checker import repository_root


ADR_DIR = "docs/adr"
ENFORCED_FROM = 50
FENCED_CODE = re.compile(r"^\s*```")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
SOURCE_DIRS = ("src/", "scripts/", "tests/", ".config/", ".taqt/", "migrations/", "docs/", "eval/", "tmp/")
CODE_SUFFIXES = (
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".sh",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
)


def adr_number(path: Path) -> int | None:
    match = re.match(r"(\d{4})-", path.name)
    return int(match.group(1)) if match else None


def enforced_adr_files(root: Path) -> list[Path]:
    directory = root / ADR_DIR
    if not directory.is_dir():
        return []
    return [
        path
        for path in sorted(directory.glob("*.md"))
        if (number := adr_number(path)) is not None and number >= ENFORCED_FROM
    ]


def find_violations(text: str, relative_path: str) -> list[str]:
    violations: list[str] = []
    in_fenced_code = False
    for index, line in enumerate(text.splitlines(), start=1):
        if FENCED_CODE.match(line):
            if not in_fenced_code:
                violations.append(f"{relative_path}:{index}: fenced code block is an implementation detail")
            in_fenced_code = not in_fenced_code
            continue
        for code in INLINE_CODE.findall(line):
            if is_source_reference(code):
                violations.append(f"{relative_path}:{index}: source reference in inline code: `{code}`")
    return violations


def is_source_reference(code: str) -> bool:
    token = code.strip()
    if not token:
        return False
    if token.endswith(CODE_SUFFIXES):
        return True
    return token.startswith(SOURCE_DIRS)


def main() -> int:
    root = repository_root()
    failed = False
    for path in enforced_adr_files(root):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for violation in find_violations(text, relative_path):
            print(violation)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
