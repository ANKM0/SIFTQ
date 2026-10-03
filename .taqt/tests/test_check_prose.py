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


check_prose = load_module("check_prose")


def test_target_files_excludes_vendored_skill() -> None:
    relative = {path.relative_to(ROOT).as_posix() for path in check_prose.target_files(ROOT)}

    assert "AGENTS.md" in relative
    assert not any(name.startswith(".agents/skills/yomiyasu/") for name in relative)


def test_error_finding_fails(tmp_path: Path) -> None:
    path = tmp_path / "error.md"
    path.write_text("次に**「文書の立場」**を決めます。\n", encoding="utf-8")

    assert check_prose.check_files(ROOT, [path]) == 1


def test_warning_only_passes(tmp_path: Path) -> None:
    path = tmp_path / "warning.md"
    path.write_text("この機能の手触りを確認します。\n", encoding="utf-8")

    assert check_prose.check_files(ROOT, [path]) == 0
