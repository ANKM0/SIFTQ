import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dependency_cruiser_is_declared() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert "dependency-cruiser" in package["devDependencies"]


def test_dependency_cruiser_config_defines_direction_rules() -> None:
    config = (ROOT / ".dependency-cruiser.cjs").read_text(encoding="utf-8")
    assert "no-circular" in config
    assert "src-not-to-tests" in config
    assert "domain-no-upward-dependency" in config
    assert "repository-no-presentation-dependency" in config
