import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))


def load_module(name: str):
    path = ROOT / "scripts" / "ci" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget = load_module("check_e2e_budget")


def test_is_within_budget() -> None:
    assert budget.is_within_budget(60000, 54000) is True
    assert budget.is_within_budget(60000, 60001) is False


def test_total_limit_defaults_without_file(tmp_path: Path) -> None:
    assert budget.total_limit_ms(tmp_path / "missing.json") == budget.DEFAULT_TOTAL_MS


def test_reads_limit_and_warn_flag(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({"total_ms": 1234, "warn_only": False}), encoding="utf-8")
    assert budget.total_limit_ms(path) == 1234
    assert budget.warn_only(path) is False


def test_report_total_ms_reads_summary(tmp_path: Path) -> None:
    report = {
        "stats": {"duration": 4321},
        "suites": [],
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert budget.report_total_ms(path) == 4321
