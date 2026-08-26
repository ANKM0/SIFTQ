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


provider = load_module("llm_eval_provider")


def test_chat_base_url_appends_v1_when_missing() -> None:
    assert provider.chat_base_url("https://api.deepseek.com/") == "https://api.deepseek.com/v1"


def test_chat_base_url_preserves_v1() -> None:
    assert provider.chat_base_url("https://api.deepseek.com/v1") == "https://api.deepseek.com/v1"


def test_build_provider_for_deepseek() -> None:
    config = {
        "model": "deepseek-v4-flash",
        "model_provider": "deepseek",
        "model_providers": {
            "deepseek": {
                "base_url": "https://api.deepseek.com/",
            }
        },
    }
    result = provider.build_provider(config)
    assert result == {
        "id": "deepseek:chat:deepseek-v4-flash",
        "config": {"apiBaseUrl": "https://api.deepseek.com/v1"},
    }


def test_build_provider_for_openai() -> None:
    config = {
        "model": "gpt-5-mini",
        "model_provider": "openai",
        "model_providers": {},
    }
    assert provider.build_provider(config) == {
        "id": "openai:chat:gpt-5-mini",
        "config": {},
    }


def test_build_provider_rejects_unknown_provider() -> None:
    config = {"model": "m", "model_provider": "unknown"}
    try:
        provider.build_provider(config)
    except ValueError as error:
        assert "unsupported model_provider" in str(error)
    else:
        raise AssertionError("expected ValueError")
