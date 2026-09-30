"""Enforce Playwright E2E conventions that keep the suite fast and shardable.

Each rule is a ratchet: files listed in `e2e_conventions_allowlist.json` are
grandfathered so the gate stays green during migration. Remove entries as the
files are fixed; a stale-but-fixed entry stays valid because the rule no longer
matches.

Violations are printed as `path:line: rule` so they are greppable in CI.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checker import repository_root

ALLOWLIST_PATH = "scripts/ci/e2e_conventions_allowlist.json"
CONFIG_PATH = ".config/playwright.config.ts"

MAX_TESTS_PER_FILE = 20
MAX_LINES_PER_FILE = 400

SERIAL_RE = re.compile(r"describe\.configure\(\s*\{\s*mode:\s*[\"']serial[\"']")
NETWORKIDLE_RE = re.compile(r"\bnetworkidle\b")
UI_LOGIN_RE = re.compile(r"getByLabel\(\s*[\"']Password[\"']\s*\)")
TEST_RE = re.compile(r"^test\(", re.MULTILINE)
CONFIG_TRACE_RE = re.compile(r"trace:\s*[\"']on-first-retry[\"']")
CONFIG_RETRIES_ZERO_RE = re.compile(r"retries:\s*0\b")
CONFIG_FULLY_PARALLEL_RE = re.compile(r"fullyParallel:\s*true")
CONFIG_WORKERS_ONE_RE = re.compile(r"workers:\s*1\b")

ALLOWLIST_KEYS = ("serial", "networkidle", "ui_login", "large_files", "config")


def load_allowlist(root: Path) -> dict[str, list[str]]:
    path = root / ALLOWLIST_PATH
    if not path.is_file():
        return {key: [] for key in ALLOWLIST_KEYS}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return {key: list(data.get(key, [])) for key in ALLOWLIST_KEYS}


def _line_of(text: str, match: re.Match[str]) -> int:
    return text[: match.start()].count("\n") + 1


def find_spec_violations(
    text: str, relative_path: str, allowlist: dict[str, list[str]]
) -> list[str]:
    violations: list[str] = []

    if relative_path not in allowlist["networkidle"]:
        match = NETWORKIDLE_RE.search(text)
        if match:
            violations.append(
                f"{relative_path}:{_line_of(text, match)}: "
                "networkidle wait (use web-first assertions)"
            )

    if relative_path not in allowlist["ui_login"]:
        match = UI_LOGIN_RE.search(text)
        if match:
            violations.append(
                f"{relative_path}:{_line_of(text, match)}: "
                "UI password login (use the auth storageState fixture)"
            )

    if relative_path not in allowlist["serial"]:
        match = SERIAL_RE.search(text)
        if match:
            violations.append(
                f"{relative_path}:{_line_of(text, match)}: "
                "serial mode (isolate data and run in parallel)"
            )

    if relative_path not in allowlist["large_files"]:
        test_count = len(TEST_RE.findall(text))
        if test_count > MAX_TESTS_PER_FILE:
            violations.append(
                f"{relative_path}:1: {test_count} tests exceed the "
                f"{MAX_TESTS_PER_FILE}-test file limit (split by concern)"
            )
        line_count = text.count("\n") + 1
        if line_count > MAX_LINES_PER_FILE:
            violations.append(
                f"{relative_path}:1: {line_count} lines exceed the "
                f"{MAX_LINES_PER_FILE}-line file limit (split by concern)"
            )

    return violations


def find_config_violations(
    text: str, relative_path: str, allowlist: dict[str, list[str]]
) -> list[str]:
    if relative_path in allowlist["config"]:
        return []

    violations: list[str] = []
    if CONFIG_TRACE_RE.search(text) and CONFIG_RETRIES_ZERO_RE.search(text):
        violations.append(
            f"{relative_path}:1: trace on-first-retry with retries 0 never records "
            "(use retain-on-failure or set retries)"
        )
    if CONFIG_FULLY_PARALLEL_RE.search(text) and CONFIG_WORKERS_ONE_RE.search(text):
        violations.append(
            f"{relative_path}:1: fullyParallel true with workers 1 does not run in "
            "parallel (raise workers or drop fullyParallel)"
        )
    return violations


def main() -> int:
    root = repository_root()
    allowlist = load_allowlist(root)
    failed = False

    for path in sorted((root / "tests/e2e").glob("*.spec.ts")):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for violation in find_spec_violations(text, relative_path, allowlist):
            print(violation)
            failed = True

    config_path = root / CONFIG_PATH
    if config_path.is_file():
        text = config_path.read_text(encoding="utf-8")
        for violation in find_config_violations(text, CONFIG_PATH, allowlist):
            print(violation)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
