import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop_eval.defect_injection import evaluate_mutants, load_mutant, run_arm, summarize


def test_summarize_reports_rates_and_mcnemar_discordance() -> None:
    records = [
        {"mutant": "m1", "arms": {"A": True, "B": True}},
        {"mutant": "m2", "arms": {"A": True, "B": False}},
        {"mutant": "m3", "arms": {"A": False, "B": True}},
        {"mutant": "m4", "arms": {"A": False, "B": False}},
    ]

    summary = summarize(records)

    assert summary["arms"]["A"] == {"caught": 2, "total": 4, "rate": 0.5}
    assert summary["arms"]["B"] == {"caught": 2, "total": 4, "rate": 0.5}
    assert summary["mcnemar"] == {
        "both_caught": 1,
        "a_caught_b_missed": 1,
        "a_missed_b_caught": 1,
    }


def test_run_arm_catches_first_failing_command() -> None:
    calls: list[str] = []

    def runner(command: str, cwd: Path) -> int:
        calls.append(command)
        return 1 if command == "b" else 0

    assert run_arm(["a", "b", "c"], cwd=Path("."), runner=runner) is True
    assert calls == ["a", "b"]


def test_evaluate_mutants_applies_and_reverts_each_mutant(tmp_path: Path) -> None:
    events: list[tuple[str, str]] = []

    def apply(patch: Path, repo: Path) -> None:
        events.append(("apply", patch.name))

    def revert(patch: Path, repo: Path) -> None:
        events.append(("revert", patch.name))

    def runner(command: str, cwd: Path) -> int:
        return 0

    mutants = [{"name": "m1", "patch_path": tmp_path / "m1.patch", "expected_catch": True}]

    result = evaluate_mutants(
        mutants,
        arms={"A": ["a"], "B": ["a", "b"]},
        repo=tmp_path,
        runner=runner,
        apply=apply,
        revert=revert,
    )

    assert events == [("apply", "m1.patch"), ("revert", "m1.patch")]
    assert result["records"][0]["arms"] == {"A": False, "B": False}


def test_load_mutant_reads_patch_and_expected(tmp_path: Path) -> None:
    (tmp_path / "m.patch").write_text("diff", encoding="utf-8")
    spec = tmp_path / "m.yaml"
    spec.write_text("name: m\npatch_file: m.patch\nexpected_catch: true\n", encoding="utf-8")

    mutant = load_mutant(spec)

    assert mutant["name"] == "m"
    assert mutant["patch_path"] == tmp_path / "m.patch"
    assert mutant["expected_catch"] is True


@pytest.mark.parametrize(
    "body",
    [
        "name: m\n",
        "name: m\npatch_file: missing.patch\nexpected_catch: true\n",
        "name: m\npatch_file: m.patch\n",
    ],
)
def test_load_mutant_rejects_incomplete_specs(tmp_path: Path, body: str) -> None:
    spec = tmp_path / "m.yaml"
    spec.write_text(body, encoding="utf-8")

    with pytest.raises(ValueError):
        load_mutant(spec)
