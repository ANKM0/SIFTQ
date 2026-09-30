"""Check the measured E2E duration against the budget ratchet.

The budget lives in `eval/e2e-budget.json` and is compared to the total from the
Playwright JSON report produced by `ci:test:e2e:measure`. The ratchet warns by
default (`warn_only`) so a one-off slow runner does not fail the nightly run
until the limit is proven stable.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checker import repository_root

DEFAULT_TOTAL_MS = 60000


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def total_limit_ms(path: Path) -> int:
    if not path.is_file():
        return DEFAULT_TOTAL_MS
    return int(read_json(path).get("total_ms", DEFAULT_TOTAL_MS))


def warn_only(path: Path) -> bool:
    if not path.is_file():
        return True
    return bool(read_json(path).get("warn_only", True))


def is_within_budget(limit: int, total: int) -> bool:
    return total <= limit


def report_total_ms(path: Path) -> int:
    module_path = repository_root() / "scripts" / "e2e" / "summarize.py"
    spec = importlib.util.spec_from_file_location("e2e_summarize", module_path)
    assert spec is not None and spec.loader is not None
    summarize = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summarize)
    return int(summarize.summarize(read_json(path)).get("total_ms", 0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-e2e-budget")
    parser.add_argument("--budget-file", default="eval/e2e-budget.json")
    parser.add_argument("--report-file", default="tmp/e2e/report.json")
    args = parser.parse_args(argv)

    report = Path(args.report_file)
    if not report.is_file():
        print(f"Playwright report not found: {report}", file=sys.stderr)
        return 1

    budget = Path(args.budget_file)
    limit = total_limit_ms(budget)
    total = report_total_ms(report)
    if is_within_budget(limit, total):
        print(f"E2E budget ok: {total}ms <= {limit}ms")
        return 0

    message = f"E2E budget exceeded: {total}ms > {limit}ms"
    if warn_only(budget):
        print(f"::warning title=E2E budget::{message}")
        return 0
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
