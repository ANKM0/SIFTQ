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


requirements = load_module("check_requirements")


def test_missing_test_is_reported(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.ts").write_text("export const task = 1;\n")
    (tmp_path / "tests").mkdir()

    violations = requirements.find_missing_tests(tmp_path, set())
    assert violations == ["src/task.ts: missing test file"]


def test_existing_test_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.ts").write_text("export const task = 1;\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "task.test.ts").write_text("test('task', () => {});\n")

    assert requirements.find_missing_tests(tmp_path, set()) == []


def test_allowlist_skips_file(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.ts").write_text("export const task = 1;\n")

    violations = requirements.find_missing_tests(
        tmp_path,
        {"src/task.ts"},
    )
    assert violations == []
