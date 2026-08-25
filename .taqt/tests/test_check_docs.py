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


docs = load_module("check_docs")


def test_requires_mapped_document() -> None:
    rules = [{"pattern": "taskfile/", "required": "docs/memo.md"}]
    assert docs.find_violations(["taskfile/core.yml"], rules) == [
        "taskfile/ changes require docs/memo.md"
    ]


def test_mapped_document_is_allowed() -> None:
    rules = [{"pattern": "taskfile/", "required": "docs/memo.md"}]
    assert docs.find_violations(
        ["taskfile/core.yml", "docs/memo.md"],
        rules,
    ) == []


def test_unrelated_changes_are_ignored() -> None:
    rules = [{"pattern": "taskfile/", "required": "docs/memo.md"}]
    assert docs.find_violations(["src/task.ts"], rules) == []
