import json
import sys

from checker import repository_root, source_files


ALLOWLIST_PATH = "scripts/ci/requirements_allowlist.json"


def load_allowlist(root) -> set[str]:
    path = root / ALLOWLIST_PATH
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["path"] for entry in data}


def find_missing_tests(root, allowlist: set[str]) -> list[str]:
    missing: list[str] = []
    for path in source_files(root, "src"):
        relative_path = path.relative_to(root).as_posix()
        if relative_path in allowlist:
            continue
        candidates = [
            root / "tests" / f"{path.stem}.test.ts",
            root / "tests" / f"{path.stem}.test.tsx",
        ]
        if any(candidate.is_file() for candidate in candidates):
            continue
        missing.append(f"{relative_path}: missing test file")
    return missing


def main() -> int:
    root = repository_root()
    allowlist = load_allowlist(root)
    missing = find_missing_tests(root, allowlist)
    for violation in missing:
        print(violation)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
