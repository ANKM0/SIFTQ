import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "ci" / "loop_change_paths.py"
SPEC = importlib.util.spec_from_file_location("loop_change_paths", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
loop_change_paths = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop_change_paths)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".taqt/loops/main.yml", True),
        (".taqt/loops/nested/definition.yml", True),
        (".taqt/scripts/loop/verify.sh", True),
        (".taqt/loops-old/main.yml", False),
        (".taqt/scripts/loop_eval/result.json", False),
        ("src/task.ts", False),
    ],
)
def test_is_loop_change_path(path: str, expected: bool) -> None:
    assert loop_change_paths.is_loop_change_path(path) is expected
