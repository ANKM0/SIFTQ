import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ARCHITECTURE_FILES = (
    ROOT / "docs/adr/0006-adopt-lightweight-application-architecture.md",
    ROOT / "docs/contributing/architecture.md",
    ROOT / "docs/contributing/assets/app-architecture.mmd",
    ROOT / "docs/contributing/assets/app-architecture-layers.svg",
    ROOT / "docs/contributing/assets/app-architecture.svg",
)

CORE_ARCHITECTURE_FILES = ARCHITECTURE_FILES[:3] + ARCHITECTURE_FILES[4:]

POLICY_MARKERS = (
    ("domain", ("domain",)),
    ("structural types", ("構造体型", "structural types", "types")),
    ("pure functions", ("純粋関数", "pure functions")),
    ("Result", ("Result",)),
    ("adapter", ("adapter",)),
)

BOUNDARY_POLICY_MARKERS = (
    ("repository port", ("repository",)),
    ("minimal interface", ("interface",)),
    ("factory/object adapter", ("factory function", "factory functions", "factory + object")),
    ("object literal", ("object literal", "object literals", "factory + object")),
)

INTERFACE_FILES = {
    ROOT / "src/task-repository.ts",
    ROOT / "src/index.tsx",
    ROOT / "src/preview/MemoryTaskRepository.ts",
}


def test_architecture_documents_share_domain_policy() -> None:
    texts = {path: path.read_text(encoding="utf-8") for path in ARCHITECTURE_FILES}

    for policy, terms in POLICY_MARKERS:
        missing = [
            str(path.relative_to(ROOT))
            for path, text in texts.items()
            if not any(term in text for term in terms)
        ]
        assert missing == [], f"{policy} missing from: {', '.join(missing)}"


def test_core_architecture_documents_share_boundary_policy() -> None:
    texts = {path: path.read_text(encoding="utf-8") for path in CORE_ARCHITECTURE_FILES}

    for policy, terms in BOUNDARY_POLICY_MARKERS:
        missing = [
            str(path.relative_to(ROOT))
            for path, text in texts.items()
            if not any(term in text for term in terms)
        ]
        assert missing == [], f"{policy} missing from: {', '.join(missing)}"


def test_task_repository_interface_stays_at_the_side_effect_boundary() -> None:
    source_files = tuple(ROOT.joinpath("src").rglob("*.ts")) + tuple(ROOT.joinpath("src").rglob("*.tsx"))
    interface_declarations = {
        path
        for path in source_files
        if re.search(r"\binterface\s+TaskRepository\b", path.read_text(encoding="utf-8"))
    }
    usages = {
        path
        for path in source_files
        if "TaskRepository" in path.read_text(encoding="utf-8")
    }

    assert interface_declarations == {ROOT / "src/task-repository.ts"}
    assert usages == INTERFACE_FILES
    assert "TaskRepository" not in (ROOT / "src/task.ts").read_text(encoding="utf-8")
