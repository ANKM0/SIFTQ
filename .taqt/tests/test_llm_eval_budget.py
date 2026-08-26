import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))


def load_module(name: str):
    path = ROOT / "scripts" / "ci" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget = load_module("llm_eval_budget")


def test_monthly_limit_reads_default_when_missing() -> None:
    path = Path("/tmp/nonexistent-limit.json")
    assert budget.monthly_limit(path) == budget.DEFAULT_LIMIT_USD


def test_spent_usd_returns_zero_when_file_missing() -> None:
    assert budget.spent_usd(Path("/tmp/nonexistent-spent.json")) == 0.0


def test_within_budget_boundary() -> None:
    assert budget.is_within_budget(50.0, 49.99) is True
    assert budget.is_within_budget(50.0, 50.0) is False
