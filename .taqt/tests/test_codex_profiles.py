import json
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.codex_profiles import initialize, validate


def test_initialize_creates_supported_profiles(tmp_path: Path) -> None:
    created = initialize(tmp_path)

    assert tmp_path / "deepseek.config.toml" in created
    assert tmp_path / "muse-spark-opencode-free.config.toml" in created
    assert not (tmp_path / "deepseek0731.config.toml").exists()
    assert not (tmp_path / "muse-spark-openrouter.config.toml").exists()


def test_validate_requires_supported_profiles_and_keys(tmp_path: Path, monkeypatch) -> None:
    initialize(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("OPENCODE_API_KEY", "opencode-key")

    assert validate(tmp_path, require_env=True) == []


def test_profiles_use_expected_endpoints(tmp_path: Path) -> None:
    initialize(tmp_path)

    muse_free = (tmp_path / "muse-spark-opencode-free.config.toml").read_text(encoding="utf-8")

    assert 'model = "muse-spark-1.3-contributor-free"' in muse_free
    assert 'base_url = "https://opencode.ai/zen/v1"' in muse_free

    catalog = json.loads(
        (tmp_path / "models" / "muse-spark-opencode-free.json").read_text(encoding="utf-8")
    )
    assert catalog["models"][0]["web_search_tool_type"] == "text"
    assert catalog["models"][0]["supports_search_tool"] is False


def test_catalogs_declare_required_reasoning_levels(tmp_path: Path) -> None:
    initialize(tmp_path)

    def efforts(path: Path) -> set[str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {entry["effort"] for entry in payload["models"][0]["supported_reasoning_levels"]}

    assert "high" in efforts(tmp_path / "models" / "deepseek.json")
    assert "high" in efforts(tmp_path / "models" / "muse-spark-opencode-free.json")


def test_taskfile_exposes_supported_codex_tasks() -> None:
    tasks = yaml.safe_load(
        (REPOSITORY_ROOT / "taskfile" / "codex.yml").read_text(encoding="utf-8")
    )["tasks"]

    assert tasks["codex:deepseek"]["cmds"] == ["codex --profile deepseek {{.CLI_ARGS}}"]
    assert "codex:luna" not in tasks
    assert tasks["codex:muse-spark:free"]["cmds"] == [
        "codex --profile muse-spark-opencode-free {{.CLI_ARGS}}"
    ]
