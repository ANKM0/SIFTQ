import json
import re
import sys

from checker import repository_root, source_files


SELECT_STAR_RE = re.compile(r"\bSELECT\s+\*", re.IGNORECASE)
ALL_CALL_RE = re.compile(r"\.all(?:<.*>)?\s*\(")
PREPARE_RE = re.compile(r"\.prepare\s*\(")
LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)

ALLOWLIST_PATH = "scripts/ci/db_query_allowlist.json"


def load_allowlist(root) -> set[tuple[str, str]]:
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
    lines = text.splitlines()
    violations: list[str] = []

    for index, line in enumerate(lines, start=1):
        if SELECT_STAR_RE.search(line):
            if (relative_path, "select_star") not in allowlist:
                violations.append(
                    f"{relative_path}:{index}: select_star ({line.strip()})"
                )

    for index, line in enumerate(lines, start=1):
        if ALL_CALL_RE.search(line) is None:
            continue
        block_start = max(0, index - 30)
        block = "\n".join(lines[block_start:index])
        prepare_match = PREPARE_RE.search(block)
        if prepare_match is None:
            continue
        query_block = block[prepare_match.start() :]
        if LIMIT_RE.search(query_block):
            continue
        if (relative_path, "unbounded_all") in allowlist:
            continue
        violations.append(
            f"{relative_path}:{index}: unbounded_all ({line.strip()})"
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
