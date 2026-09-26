import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

from loop.verification import E2E_COMMANDS, FAST_COMMANDS, FRONTEND_DEPENDENCY_COMMAND


CommandRunner = Callable[[str, Path], int]

ARM_A = ("git diff --check", FRONTEND_DEPENDENCY_COMMAND, *FAST_COMMANDS)
ARM_B = (*ARM_A, *E2E_COMMANDS)
DEFAULT_ARMS = {"A": ARM_A, "B": ARM_B}
DEFAULT_MUTANT_ROOT = Path("eval/gold/loop-mutants")


def load_mutant(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{path} requires a name")
    patch_file = payload.get("patch_file")
    if not isinstance(patch_file, str) or not patch_file:
        raise ValueError(f"{path} requires patch_file")
    patch_path = path.parent / patch_file
    if not patch_path.is_file():
        raise ValueError(f"{path} patch_file not found: {patch_path}")
    expected_catch = payload.get("expected_catch")
    if not isinstance(expected_catch, bool):
        raise ValueError(f"{path} requires boolean expected_catch")
    return {"name": name, "patch_path": patch_path, "expected_catch": expected_catch}


def run_arm(commands: Sequence[str], *, cwd: Path, runner: CommandRunner) -> bool:
    for command in commands:
        if runner(command, cwd) != 0:
            return True
    return False


def summarize(
    records: Sequence[dict[str, Any]], *, arm_a: str = "A", arm_b: str = "B"
) -> dict[str, Any]:
    totals: dict[str, int] = {}
    caught: dict[str, int] = {}
    both_caught = a_caught_b_missed = a_missed_b_caught = 0
    for record in records:
        arms = record["arms"]
        for arm, hit in arms.items():
            totals[arm] = totals.get(arm, 0) + 1
            caught[arm] = caught.get(arm, 0) + (1 if hit else 0)
        hit_a = bool(arms.get(arm_a))
        hit_b = bool(arms.get(arm_b))
        if hit_a and hit_b:
            both_caught += 1
        elif hit_a and not hit_b:
            a_caught_b_missed += 1
        elif hit_b and not hit_a:
            a_missed_b_caught += 1
    rates = {
        arm: (caught[arm] / totals[arm] if totals[arm] else 0.0)
        for arm in totals
    }
    return {
        "arms": {
            arm: {"caught": caught[arm], "total": totals[arm], "rate": round(rates[arm], 4)}
            for arm in totals
        },
        "mcnemar": {
            "both_caught": both_caught,
            "a_caught_b_missed": a_caught_b_missed,
            "a_missed_b_caught": a_missed_b_caught,
        },
    }


def evaluate_mutants(
    mutants: Sequence[dict[str, Any]],
    *,
    arms: dict[str, Sequence[str]] = DEFAULT_ARMS,
    repo: Path,
    runner: CommandRunner,
    apply: Callable[[Path, Path], None],
    revert: Callable[[Path, Path], None],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for mutant in mutants:
        apply(mutant["patch_path"], repo)
        try:
            results = {
                arm: run_arm(commands, cwd=repo, runner=runner)
                for arm, commands in arms.items()
            }
        finally:
            revert(mutant["patch_path"], repo)
        records.append(
            {
                "mutant": mutant["name"],
                "expected_catch": mutant["expected_catch"],
                "arms": results,
            }
        )
    return {"records": records, "summary": summarize(records)}


def subprocess_runner(command: str, cwd: Path, *, env: Mapping[str, str] | None = None) -> int:
    completed = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, **env} if env else None,
    )
    return completed.returncode


def git_apply(patch: Path, repo: Path) -> None:
    subprocess.run(["git", "apply", str(patch)], cwd=repo, check=True)


def git_apply_reverse(patch: Path, repo: Path) -> None:
    subprocess.run(["git", "apply", "-R", str(patch)], cwd=repo, check=True)


def _mutant_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("*.yaml"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop-eval-defect-injection")
    parser.add_argument("--mutant-root", type=Path, default=DEFAULT_MUTANT_ROOT)
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    mutants = [load_mutant(path) for path in _mutant_paths(args.mutant_root)]
    if not mutants:
        print(json.dumps({"error": f"no mutants found in {args.mutant_root}"}, ensure_ascii=False))
        return 1
    result = evaluate_mutants(
        mutants,
        repo=args.repo,
        runner=subprocess_runner,
        apply=git_apply,
        revert=git_apply_reverse,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
