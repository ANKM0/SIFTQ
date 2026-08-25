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


glossary = load_module("check_glossary")


def test_detects_forbidden_term_in_prose() -> None:
    terms = [("SIFTQ", "siftq")]
    assert glossary.find_violations(
        "プロジェクト名は siftq です。",
        "docs/example.md",
        terms,
    ) == ["docs/example.md:1: siftq -> SIFTQ (プロジェクト名は siftq です。)"]


def test_skips_code_spans() -> None:
    terms = [("SIFTQ", "siftq")]
    assert glossary.find_violations(
        "参照先は `.codex/rules/siftq.rules` です。",
        "docs/example.md",
        terms,
    ) == []
