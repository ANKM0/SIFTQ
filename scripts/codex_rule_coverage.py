#!/usr/bin/env python3
"""Report and verify how shared Codex rules cover remembered allow rules."""

import argparse
import ast
from collections import Counter
from pathlib import Path


def patterns(path: Path) -> list[tuple[str, ...]]:
    result: list[tuple[str, ...]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("prefix_rule(") or 'decision="allow"' not in line:
            continue
        source = line.split("pattern=", 1)[1].split(", decision=", 1)[0]
        value = ast.literal_eval(source)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            result.append(tuple(value))
    return result


def covers(prefixes: list[tuple[str, ...]], rule: tuple[str, ...]) -> bool:
    return any(rule[: len(prefix)] == prefix for prefix in prefixes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default", type=Path, default=Path.home() / ".codex/rules/default.rules")
    parser.add_argument("--shared", type=Path, default=Path(".codex/rules/siftq.rules"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--min-covered", type=int, default=90)
    args = parser.parse_args()
    if not args.default.is_file():
        print(f"default rules unavailable; skipping coverage report: {args.default}")
        return 0
    defaults, shared = patterns(args.default), patterns(args.shared)
    roots = Counter(rule[0] for rule in defaults if rule)
    covered = sum(covers(shared, rule) for rule in defaults)
    print(f"default allow rules: {len(defaults)}")
    print(f"shared coverage: {covered}/{len(defaults)}")
    print("roots: " + ", ".join(f"{key} {value}" for key, value in roots.most_common()))
    if args.check and covered < args.min_covered:
        print(f"shared coverage is below required minimum: {args.min_covered}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
