import json
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.codex_profiles import initialize, validate


def test_initialize_creates_missing_profiles_without_overwriting_config(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text("model = \"gpt-5\"\n", encoding="utf-8")

    created = initialize(tmp_path)

    assert config.read_text(encoding="utf-8") == "model = \"gpt-5\"\n"
    assert tmp_path / "deepseek.config.toml" in created
    assert (tmp_path / "deepseek0731.config.toml").is_file()
    assert (tmp_path / "models" / "deepseek.json").is_file()
    assert (tmp_path / "models" / "deepseek0731.json").is_file()
    assert tmp_path / "luna-openrouter.config.toml" in created
    assert (tmp_path / "muse-spark-openrouter.config.toml").is_file()
    assert (tmp_path / "models" / "luna-openrouter.json").is_file()
    assert (tmp_path / "models" / "muse-spark-openrouter.json").is_file()


def test_initialize_does_not_create_main_config(tmp_path: Path) -> None:
    initialize(tmp_path)

    assert not (tmp_path / "config.toml").exists()


def test_validate_requires_profiles_catalogs_and_requested_api_keys(tmp_path: Path, monkeypatch) -> None:
    initialize(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    assert validate(tmp_path, require_env=True) == []


def test_catalog_has_required_codex_metadata(tmp_path: Path) -> None:
    initialize(tmp_path)
    catalog = (tmp_path / "models" / "deepseek0731.json").read_text(encoding="utf-8")

    assert '"shell_type": "shell_command"' in catalog
    assert '"model_messages"' in catalog


def test_openrouter_profiles_use_expected_models_and_namespace_tools(tmp_path: Path) -> None:
    initialize(tmp_path)

    luna = (tmp_path / "luna-openrouter.config.toml").read_text(encoding="utf-8")
    muse = (tmp_path / "muse-spark-openrouter.config.toml").read_text(encoding="utf-8")

    assert 'model = "openai/gpt-5.6-luna"' in luna
    assert 'model_provider = "openrouter"' in luna
    assert 'env_key = "OPENROUTER_API_KEY"' in luna
    assert 'namespace_tools = false' in luna
    assert 'model = "meta/muse-spark-1.3"' in muse
    assert 'model_provider = "openrouter"' in muse
    assert 'env_key = "OPENROUTER_API_KEY"' in muse
    assert 'namespace_tools = false' in muse


def test_openrouter_catalogs_declare_required_reasoning_levels(tmp_path: Path) -> None:
    initialize(tmp_path)

    def supported_efforts(path: Path) -> set[str]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            entry["effort"]
            for entry in payload["models"][0]["supported_reasoning_levels"]
        }

    assert "xhigh" in supported_efforts(tmp_path / "models" / "luna-openrouter.json")
    assert "high" in supported_efforts(tmp_path / "models" / "muse-spark-openrouter.json")


def test_taskfile_exposes_openrouter_codex_tasks() -> None:
    tasks = yaml.safe_load(
        (REPOSITORY_ROOT / "taskfile" / "codex.yml").read_text(encoding="utf-8")
    )["tasks"]

    assert tasks["codex:luna"]["cmds"] == ["codex --profile luna-openrouter {{.CLI_ARGS}}"]
    assert tasks["codex:muse-spark"]["cmds"] == [
        "codex --profile muse-spark-openrouter {{.CLI_ARGS}}"
    ]


def test_profiles_do_not_force_api_login(tmp_path: Path) -> None:
    initialize(tmp_path)

    assert "forced_login_method" not in (tmp_path / "deepseek0731.config.toml").read_text(
        encoding="utf-8"
    )


def test_validate_reports_missing_api_key(tmp_path: Path, monkeypatch) -> None:
    initialize(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert "environment variable is required: DEEPSEEK_API_KEY" in validate(
        tmp_path, require_env=True
    )
