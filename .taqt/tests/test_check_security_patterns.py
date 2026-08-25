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


security = load_module("check_security_patterns")


def test_detects_dangerously_set_inner_html() -> None:
    text = 'const view = <div dangerouslySetInnerHTML={{ __html: input }} />;'
    violations = security.find_violations(text, "src/view.tsx", set())
    assert violations == [
        "src/view.tsx:1: dangerouslySetInnerHTML (const view = <div dangerouslySetInnerHTML={{ __html: input }} />;)"
    ]


def test_respects_allowlist() -> None:
    text = 'const view = <div dangerouslySetInnerHTML={{ __html: input }} />;'
    violations = security.find_violations(
        text,
        "src/view.tsx",
        {("src/view.tsx", "dangerouslySetInnerHTML")},
    )
    assert violations == []


def test_clean_code_has_no_violations() -> None:
    violations = security.find_violations(
        'const view = <div>{value}</div>;',
        "src/view.tsx",
        set(),
    )
    assert violations == []
