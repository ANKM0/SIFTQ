import json
import subprocess
import sys

from checker import repository_root


MAPPING_PATH = "scripts/ci/docs_mapping.json"


def load_rules(root) -> list[dict[str, str]]:
    path = root / MAPPING_PATH
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def find_violations(
    changed_files: list[str],
    rules: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []
    for rule in rules:
        pattern = rule["pattern"]
        required = rule["required"]
        if not any(path.startswith(pattern) for path in changed_files):
            continue
        if required not in changed_files:
            violations.append(f"{pattern} changes require {required}")
    return violations


def changed_files(root) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "main...HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    root = repository_root()
    rules = load_rules(root)
    violations = find_violations(changed_files(root), rules)
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
