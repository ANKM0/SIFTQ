import argparse
import json
import sys
from pathlib import Path


DEFAULT_LIMIT_USD = 50.0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def monthly_limit(path: Path) -> float:
    if not path.exists():
        return DEFAULT_LIMIT_USD
    data = read_json(path)
    return float(data.get("monthly_limit_usd", DEFAULT_LIMIT_USD))


def spent_usd(path: Path) -> float:
    if not path.exists():
        return 0.0
    data = read_json(path)
    return float(data.get("spent_usd", 0.0))


def is_within_budget(limit: float, spent: float) -> bool:
    return spent < limit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the LLM eval monthly budget.")
    parser.add_argument("--limit-file", required=True, help="JSON file with monthly_limit_usd.")
    parser.add_argument("--spent-file", required=True, help="JSON file with spent_usd.")
    args = parser.parse_args(argv)

    limit = monthly_limit(Path(args.limit_file))
    spent = spent_usd(Path(args.spent_file))
    if not is_within_budget(limit, spent):
        print(f"LLM eval budget exceeded: spent=${spent:.2f} >= limit=${limit:.2f}", file=sys.stderr)
        return 1
    print(f"LLM eval budget ok: spent=${spent:.2f} < limit=${limit:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
