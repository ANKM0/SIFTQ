import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "ci" / "check_loop_effect_measurement.py"
SPEC = importlib.util.spec_from_file_location("check_loop_effect_measurement", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_evaluate_warns_when_loop_changes_lack_evidence() -> None:
    assert module.evaluate([".taqt/loops/main_loop.yaml"]) == ".taqt/loops/main_loop.yaml"
    assert module.evaluate([".taqt/scripts/loop/runner.py", "src/index.tsx"]) == (
        ".taqt/scripts/loop/runner.py"
    )


def test_evaluate_ok_when_evidence_present_or_no_loop_change() -> None:
    assert module.evaluate([".taqt/loops/main_loop.yaml", "eval/results/loop/t2.json"]) is None
    assert module.evaluate(["src/index.tsx", "docs/x.md"]) is None
