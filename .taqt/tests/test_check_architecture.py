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


architecture = load_module("check_architecture")


def test_allows_relative_imports() -> None:
    text = 'import { createTask } from "./task";\n'
    assert architecture.find_violations(text, "src/index.tsx", set()) == []


def test_allows_known_external_imports() -> None:
    text = 'import { Hono } from "hono";\nimport type { D1Database } from "@cloudflare/workers-types";\n'
    assert architecture.find_violations(text, "src/index.tsx", set()) == []


def test_rejects_unexpected_external_import() -> None:
    text = 'import lodash from "lodash";\n'
    assert architecture.find_violations(text, "src/index.tsx", set()) == [
        "src/index.tsx:1: unexpected import (lodash)"
    ]


def test_rejects_tests_import() -> None:
    text = 'import { task } from "../tests/task.test";\n'
    assert architecture.find_violations(text, "src/index.tsx", set()) == [
        "src/index.tsx:1: tests import (../tests/task.test)"
    ]
