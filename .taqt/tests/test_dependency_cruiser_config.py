import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dependency_cruiser_is_declared() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert "dependency-cruiser" in package["devDependencies"]


def test_dependency_cruiser_config_defines_direction_rules() -> None:
    config = (ROOT / ".config/.dependency-cruiser.cjs").read_text(encoding="utf-8")
    assert "no-circular" in config
    assert "src-not-to-tests" in config
    assert "domain-no-upward-dependency" in config
    assert "repository-no-presentation-dependency" in config


def test_domain_rule_covers_presentation_and_adapters() -> None:
    config = (ROOT / ".config/.dependency-cruiser.cjs").read_text(encoding="utf-8")
    assert 'from: { path: "^src/task\\\\.ts$" }' in config
    assert 'to: { path: "^src/(index\\\\.tsx|components/|preview/|task-repository\\\\.ts$)" }' in config


def test_architecture_ci_runs_dependency_cruiser() -> None:
    ci = (ROOT / "taskfile/ci.yml").read_text(encoding="utf-8")
    assert "vp exec depcruise src --config .config/.dependency-cruiser.cjs" in ci
