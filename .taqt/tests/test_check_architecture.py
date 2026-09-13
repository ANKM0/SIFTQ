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


def test_rejects_class_in_domain() -> None:
    text = "export class Task {}\n"
    assert architecture.find_violations(text, "src/task.ts", set()) == [
        "src/task.ts:1: domain class usage"
    ]


def test_rejects_domain_side_effect_apis() -> None:
    text = "const now = new Date();\nconst id = crypto.randomUUID();\nconst value = Math.random();\nconst response = fetch('/tasks');\n"
    assert architecture.find_violations(text, "src/task.ts", set()) == [
        "src/task.ts:1: domain side-effect API (Date)",
        "src/task.ts:2: domain side-effect API (crypto)",
        "src/task.ts:3: domain side-effect API (Math.random)",
        "src/task.ts:4: domain side-effect API (fetch)",
    ]


def test_rejects_domain_side_effect_import() -> None:
    text = 'import type { D1Database } from "@cloudflare/workers-types";\n'
    assert architecture.find_violations(text, "src/task.ts", set()) == [
        "src/task.ts:1: domain side-effect import (@cloudflare/workers-types)"
    ]


def test_allows_side_effect_apis_outside_domain() -> None:
    text = "const now = new Date();\nconst response = fetch('/tasks');\n"
    assert architecture.find_violations(text, "src/index.tsx", set()) == []
