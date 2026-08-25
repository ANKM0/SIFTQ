import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from checker import repository_root, source_files


@dataclass(frozen=True)
class Pattern:
    id: str
    regex: str


PATTERNS = [
    Pattern("dangerouslySetInnerHTML", r"dangerouslySetInnerHTML"),
    Pattern("eval", r"\beval\s*\("),
    Pattern("document.write", r"\bdocument\.write\s*\("),
    Pattern("window.open", r"\bwindow\.open\s*\("),
]

ALLOWLIST_PATH = "scripts/ci/security_allowlist.json"


def load_allowlist(root: Path) -> set[tuple[str, str]]:
    path = root / ALLOWLIST_PATH
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(entry["path"], entry["pattern"]) for entry in data}


def find_violations(
    text: str,
    relative_path: str,
    allowlist: set[tuple[str, str]],
) -> list[str]:
    violations: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            if re.search(pattern.regex, line) is None:
                continue
            if (relative_path, pattern.id) in allowlist:
                continue
            violations.append(
                f"{relative_path}:{index}: {pattern.id} ({line.strip()})"
            )
    return violations


def main() -> int:
    root = repository_root()
    allowlist = load_allowlist(root)
    failed = False
    for path in source_files(root, "src"):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for violation in find_violations(text, relative_path, allowlist):
            print(violation)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
