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


db = load_module("check_db_queries")


def test_detects_select_star() -> None:
    text = 'await db.prepare("SELECT * FROM tasks").all();'
    violations = db.find_violations(text, "src/repository.ts", set())
    assert violations == [
        "src/repository.ts:1: select_star (await db.prepare(\"SELECT * FROM tasks\").all();)",
        "src/repository.ts:1: unbounded_all (await db.prepare(\"SELECT * FROM tasks\").all();)",
    ]


def test_detects_unbounded_all() -> None:
    text = (
        'const result = await this.db\n'
        '  .prepare(\n'
        '    "SELECT id FROM tasks WHERE owner_id = ? ORDER BY id",\n'
        "  )\n"
        "  .bind(OWNER_ID)\n"
        "  .all<Record<string, unknown>>();"
    )
    violations = db.find_violations(text, "src/repository.ts", set())
    assert violations == [
        "src/repository.ts:6: unbounded_all (.all<Record<string, unknown>>();)"
    ]


def test_all_with_limit_is_allowed() -> None:
    text = (
        'const result = await this.db\n'
        '  .prepare("SELECT id FROM tasks ORDER BY id LIMIT 10")\n'
        "  .all();"
    )
    violations = db.find_violations(text, "src/repository.ts", set())
    assert violations == []


def test_first_is_not_flagged() -> None:
    text = 'const row = await this.db.prepare("SELECT id FROM tasks").first();'
    violations = db.find_violations(text, "src/repository.ts", set())
    assert violations == []


def test_respects_allowlist() -> None:
    text = (
        'const result = await this.db\n'
        '  .prepare("SELECT id FROM tasks WHERE owner_id = ?")\n'
        "  .all();"
    )
    violations = db.find_violations(
        text,
        "src/repository.ts",
        {("src/repository.ts", "unbounded_all")},
    )
    assert violations == []
