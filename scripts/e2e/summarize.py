"""Summarize a Playwright JSON report into E2E timing baselines.

`playwright test --reporter=json` emits a nested suite tree. This module reduces
it to total wall time, per-file duration, and pass/fail counts. The reduction is
pure so it can be tested (and reused by the budget ratchet) without running
Playwright.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator


def iter_tests(
    suite: dict[str, Any], file: str | None = None
) -> Iterator[tuple[str, dict[str, Any]]]:
    current = suite.get("file") or file or suite.get("title", "")
    for spec in suite.get("specs", []):
        for test in spec.get("tests", []):
            yield current, test
    for child in suite.get("suites", []):
        yield from iter_tests(child, current)


def _test_duration_ms(test: dict[str, Any]) -> int:
    return sum(int(result.get("duration", 0)) for result in test.get("results", []))


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    counts = {"passed": 0, "failed": 0, "flaky": 0, "skipped": 0}
    for suite in report.get("suites", []):
        for file, test in iter_tests(suite):
            entry = files.setdefault(
                file, {"file": file, "tests": 0, "duration_ms": 0, "failed": 0}
            )
            status = test.get("status", "unknown")
            entry["tests"] += 1
            entry["duration_ms"] += _test_duration_ms(test)
            if status == "expected":
                counts["passed"] += 1
            elif status == "unexpected":
                counts["failed"] += 1
                entry["failed"] += 1
            elif status == "flaky":
                counts["flaky"] += 1
            elif status == "skipped":
                counts["skipped"] += 1

    ordered = sorted(files.values(), key=lambda item: item["duration_ms"], reverse=True)
    stats = report.get("stats", {})
    total_ms = int(stats.get("duration", 0)) or sum(
        item["duration_ms"] for item in ordered
    )
    return {
        "total_ms": total_ms,
        "tests": {"total": sum(counts.values()), **counts},
        "files": ordered,
    }


def format_summary(summary: dict[str, Any]) -> str:
    counts = summary["tests"]
    lines = [
        f"E2E summary: {summary['total_ms'] / 1000:.1f}s total, {counts['total']} tests "
        f"(passed {counts['passed']}, failed {counts['failed']}, "
        f"flaky {counts['flaky']}, skipped {counts['skipped']})"
    ]
    for item in summary["files"]:
        share = item["duration_ms"] / summary["total_ms"] * 100 if summary["total_ms"] else 0
        lines.append(
            f"  {item['duration_ms'] / 1000:6.1f}s {share:5.1f}%  "
            f"{item['tests']:3d} tests  {item['file']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="summarize-e2e")
    parser.add_argument(
        "report",
        nargs="?",
        default="tmp/e2e/report.json",
        help="Path to the Playwright JSON report.",
    )
    parser.add_argument("--json", dest="json_out", help="Also write the summary here.")
    args = parser.parse_args(argv)

    path = Path(args.report)
    if not path.is_file():
        print(f"Playwright report not found: {path}", file=sys.stderr)
        return 1

    summary = summarize(json.loads(path.read_text(encoding="utf-8")))
    print(format_summary(summary))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
