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


checker = load_module("check_adr_implementation_details")


def test_detects_fenced_code_block() -> None:
    text = "# ADR 9999\n\n```ts\ntype Result = { ok: true };\n```\n"
    assert checker.find_violations(text, "docs/adr/9999-example.md") == [
        "docs/adr/9999-example.md:3: fenced code block is an implementation detail",
    ]


def test_detects_source_path_and_code_filename() -> None:
    text = "- 対象は `src/components/Layout.tsx` と `scripts/ci/check_docs.py` です。\n"
    assert checker.find_violations(text, "docs/adr/9999-example.md") == [
        "docs/adr/9999-example.md:1: source reference in inline code: `src/components/Layout.tsx`",
        "docs/adr/9999-example.md:1: source reference in inline code: `scripts/ci/check_docs.py`",
    ]


def test_allows_technology_names_in_inline_code() -> None:
    text = "- 保存先は `localStorage` とし、`sessionStorage` は採用しない。\n"
    assert checker.find_violations(text, "docs/adr/9999-example.md") == []


def test_adr_number_reads_leading_number() -> None:
    assert checker.adr_number(Path("0050-adopt-local-storage-task-edit-drafts.md")) == 50
    assert checker.adr_number(Path("README.md")) is None


def test_enforced_files_skip_grandfathered_adrs(tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "0042-old.md").write_text("old", encoding="utf-8")
    (adr_dir / "0050-new.md").write_text("new", encoding="utf-8")
    (adr_dir / "README.md").write_text("index", encoding="utf-8")

    assert [path.name for path in checker.enforced_adr_files(tmp_path)] == ["0050-new.md"]
