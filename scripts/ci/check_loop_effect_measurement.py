import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loop_change_paths import is_loop_change_path

EVIDENCE_PREFIX = "eval/results/loop/"


def evaluate(changed: list[str]) -> str | None:
    loop_changes = [path for path in changed if is_loop_change_path(path)]
    evidence = [path for path in changed if path.startswith(EVIDENCE_PREFIX)]
    if loop_changes and not evidence:
        return ", ".join(loop_changes)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-loop-effect-measurement")
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args(argv)

    completed = subprocess.run(
        ["git", "diff", "--name-only", args.base, args.head],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    missing = evaluate([line for line in completed.stdout.splitlines() if line])
    if missing:
        print(
            "::warning title=loop effect measurement::"
            f"loop paths changed without evidence in {EVIDENCE_PREFIX}: {missing}"
        )
    else:
        print("loop effect measurement: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
