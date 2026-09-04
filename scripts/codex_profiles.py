#!/usr/bin/env python3
"""Create and validate shared Codex profiles without storing API keys."""

import argparse
import json
import os
import tomllib
from pathlib import Path

CODEX_HOME = Path.home() / ".codex"
MODEL_CATALOG_DIR = "models"


def _profile_config(
    *, model: str, provider: str, effort: str, catalog: Path, provider_block: list[str]
) -> str:
    lines = [
        f'model = "{model}"',
        f'model_provider = "{provider}"',
        'preferred_auth_method = "apikey"',
        f'model_reasoning_effort = "{effort}"',
        'model_auto_compact_token_limit = 120000',
        f'model_catalog_json = "{catalog}"',
        "",
        *provider_block,
        "",
    ]
    return "\n".join(lines)


def _model_catalog(
    *,
    slug: str,
    display_name: str,
    description: str,
    efforts: list[str],
    web_search_tool_type: str = "text",
    supports_search_tool: bool = True,
) -> dict[str, object]:
    return {
        "models": [
            {
                "slug": slug,
                "prefer_websockets": False,
                "support_verbosity": True,
                "default_verbosity": "low",
                "apply_patch_tool_type": "freeform",
                "web_search_tool_type": web_search_tool_type,
                "input_modalities": ["text"],
                "supports_image_detail_original": False,
                "truncation_policy": {"mode": "tokens", "limit": 10000},
                "supports_parallel_tool_calls": True,
                "tool_mode": None,
                "multi_agent_version": "v2",
                "use_responses_lite": False,
                "include_skills_usage_instructions": False,
                "context_window": 1048576,
                "max_context_window": 1048576,
                "effective_context_window_percent": 95,
                "auto_compact_token_limit": 120000,
                "reasoning_summary_format": "experimental",
                "default_reasoning_summary": "none",
                "display_name": display_name,
                "description": description,
                "default_reasoning_level": efforts[0],
                "supported_reasoning_levels": [
                    {"effort": effort, "description": f"{effort} reasoning effort"}
                    for effort in efforts
                ],
                "shell_type": "shell_command",
                "visibility": "list",
                "minimal_client_version": "0.144.0",
                "supported_in_api": True,
                "availability_nux": None,
                "upgrade": None,
                "priority": 1,
                "base_instructions": "You are a coding agent. Complete the assigned task.",
                "model_messages": {
                    "instructions_template": "You are a coding agent. Complete the assigned task."
                },
                "experimental_supported_tools": [],
                "supports_search_tool": supports_search_tool,
                "supports_reasoning_summaries": True,
            }
        ]
    }


def expected_files(codex_home: Path) -> dict[Path, str]:
    catalog_dir = codex_home / MODEL_CATALOG_DIR
    deepseek_catalog = catalog_dir / "deepseek.json"
    muse_free_catalog = catalog_dir / "muse-spark-opencode-free.json"
    return {
        codex_home / "deepseek.config.toml": _profile_config(
            model="deepseek-v4-pro",
            provider="deepseek",
            effort="high",
            catalog=deepseek_catalog,
            provider_block=[
                "[model_providers.deepseek]",
                'name = "DeepSeek"',
                'base_url = "https://api.deepseek.com/"',
                'wire_api = "responses"',
                'env_key = "DEEPSEEK_API_KEY"',
            ],
        ),
        codex_home / "muse-spark-opencode-free.config.toml": _profile_config(
            model="muse-spark-1.3-contributor-free",
            provider="opencode",
            effort="high",
            catalog=muse_free_catalog,
            provider_block=[
                "[model_providers.opencode]",
                'name = "OpenCode Zen"',
                'base_url = "https://opencode.ai/zen/v1"',
                'wire_api = "responses"',
                'env_key = "OPENCODE_API_KEY"',
                'namespace_tools = false',
            ],
        ),
        deepseek_catalog: json.dumps(
            _model_catalog(
                slug="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                description="DeepSeek V4 Pro for planning and review.",
                efforts=["low", "high", "max"],
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        muse_free_catalog: json.dumps(
            _model_catalog(
                slug="muse-spark-1.3-contributor-free",
                display_name="Muse Spark 1.3 Contributor Free",
                description="Muse Spark 1.3 Contributor Free via OpenCode Zen.",
                efforts=["high", "medium", "low"],
                supports_search_tool=False,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    }


def initialize(codex_home: Path) -> list[Path]:
    created: list[Path] = []
    for path, content in expected_files(codex_home).items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o600)
        created.append(path)
    return created


def validate(codex_home: Path, *, require_env: bool) -> list[str]:
    expected = expected_files(codex_home)
    errors: list[str] = []
    for path in expected:
        if not path.is_file():
            errors.append(f"missing: {path}")

    profile_expectations = {
        codex_home / "deepseek.config.toml": (
            "deepseek-v4-pro",
            "deepseek",
            "DEEPSEEK_API_KEY",
            codex_home / MODEL_CATALOG_DIR / "deepseek.json",
        ),
        codex_home / "muse-spark-opencode-free.config.toml": (
            "muse-spark-1.3-contributor-free",
            "opencode",
            "OPENCODE_API_KEY",
            codex_home / MODEL_CATALOG_DIR / "muse-spark-opencode-free.json",
        ),
    }
    namespace_tools_profiles = {codex_home / "muse-spark-opencode-free.config.toml"}
    for path, (model, provider, env_key, catalog_path) in profile_expectations.items():
        if not path.is_file():
            continue
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as error:
            errors.append(f"invalid TOML: {path}: {error}")
            continue
        if config.get("model") != model:
            errors.append(f"unexpected model in {path}: expected {model}")
        if config.get("model_provider") != provider:
            errors.append(f"unexpected provider in {path}: expected {provider}")
        provider_config = config.get("model_providers", {}).get(provider, {})
        if provider_config.get("env_key") != env_key:
            errors.append(f"unexpected env_key in {path}: expected {env_key}")
        if path in namespace_tools_profiles and provider_config.get("namespace_tools") is not False:
            errors.append(f"namespace_tools must be false in {path}")
        if config.get("model_catalog_json") != str(catalog_path):
            errors.append(f"unexpected model_catalog_json in {path}: expected {catalog_path}")
        if require_env and not os.environ.get(env_key):
            errors.append(f"environment variable is required: {env_key}")

    for model, _, _, catalog_path in profile_expectations.values():
        if not catalog_path.is_file():
            continue
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"invalid JSON: {catalog_path}: {error}")
            continue
        models = payload.get("models")
        if not isinstance(models, list) or not any(
            isinstance(entry, dict) and entry.get("slug") == model for entry in models
        ):
            errors.append(f"catalog does not define {model}: {catalog_path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-profiles")
    parser.add_argument("command", choices=("init", "check"))
    parser.add_argument("--codex-home", type=Path, default=CODEX_HOME)
    parser.add_argument("--require-env", action="store_true")
    args = parser.parse_args(argv)
    codex_home = args.codex_home.expanduser()

    if args.command == "init":
        for path in initialize(codex_home):
            print(f"created: {path}")
        return 0

    errors = validate(codex_home, require_env=args.require_env)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"valid: {codex_home}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
