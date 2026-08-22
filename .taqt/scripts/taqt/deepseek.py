import json
import os
from pathlib import Path


FLASH_MODEL = "deepseek-v4-flash"
PRO_MODEL = "deepseek-v4-pro"
MODELS = (FLASH_MODEL, PRO_MODEL)


def default_codex_home() -> Path:
    configured = os.environ.get("TAQT_DEEPSEEK_CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex-deepseek"


def ensure_codex_home(codex_home: Path) -> Path:
    codex_home.mkdir(parents=True, exist_ok=True)
    try:
        codex_home.chmod(0o700)
    except OSError:
        pass

    models_path = codex_home / "models.json"
    _ensure_models_catalog(models_path)
    if models_path.exists():
        _restrict_file(models_path)

    config_path = codex_home / "config.toml"
    if not config_path.exists():
        config_path.write_text(_config_text(models_path), encoding="utf-8")
        _restrict_file(config_path)
    return config_path


def _config_text(models_path: Path) -> str:
    return "\n".join(
        [
            f'model = "{FLASH_MODEL}"',
            'model_provider = "deepseek"',
            'preferred_auth_method = "apikey"',
            'forced_login_method = "api"',
            'model_reasoning_effort = "high"',
            f'model_catalog_json = "{models_path.resolve()}"',
            "",
            "[model_providers.deepseek]",
            'name = "DeepSeek"',
            'base_url = "https://api.deepseek.com/"',
            'wire_api = "responses"',
            'env_key = "DEEPSEEK_API_KEY"',
            "",
        ]
    )


def write_codex_profile_config(target: Path, *, codex_home: Path | None = None) -> None:
    home = codex_home or default_codex_home()
    ensure_codex_home(home)
    models_path = home / "models.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_config_text(models_path), encoding="utf-8")
    _restrict_file(target)


def _ensure_models_catalog(models_path: Path) -> None:
    if models_path.exists():
        try:
            catalog = json.loads(models_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid DeepSeek model catalog: {models_path}") from error
        if not isinstance(catalog, dict) or not isinstance(catalog.get("models"), list):
            raise ValueError(f"invalid DeepSeek model catalog: {models_path}")
    else:
        catalog = {"models": []}

    entries = catalog["models"]
    slugs = {
        entry.get("slug")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("slug"), str)
    }
    changed = False
    missing = [model for model in MODELS if model not in slugs]
    if missing:
        entries.extend(_model_catalog(model) for model in missing)
        changed = True
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model = entry.get("slug")
        if model not in MODELS:
            continue
        defaults = _model_catalog(str(model))
        for key in ("base_instructions", "model_messages"):
            if key not in entry or (key == "model_messages" and not isinstance(entry[key], dict)):
                entry[key] = defaults[key]
                changed = True
        model_messages = entry.get("model_messages")
        if isinstance(model_messages, dict) and "instructions_template" not in model_messages:
            model_messages["instructions_template"] = defaults["model_messages"]["instructions_template"]
            changed = True
    if changed:
        models_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _model_catalog(model: str) -> dict[str, object]:
    is_pro = model == PRO_MODEL
    return {
        "slug": model,
        "prefer_websockets": False,
        "support_verbosity": True,
        "default_verbosity": "low",
        "apply_patch_tool_type": "freeform",
        "web_search_tool_type": "text",
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
        "auto_compact_token_limit": None,
        "reasoning_summary_format": "experimental",
        "default_reasoning_summary": "none",
        "display_name": "DeepSeek-V4-Pro" if is_pro else "DeepSeek-V4-Flash",
        "description": "DeepSeek V4 Pro for planning and review."
        if is_pro
        else "DeepSeek V4 Flash for taqt coding tasks.",
        "default_reasoning_level": "high",
        "supported_reasoning_levels": [
            {"effort": "low", "description": "Fast responses with lighter reasoning"},
            {"effort": "high", "description": "Extra high reasoning depth for complex problems"},
            {"effort": "max", "description": "Maximum reasoning depth for the hardest problems"},
        ],
        "shell_type": "shell_command",
        "visibility": "list",
        "minimal_client_version": "0.144.0",
        "supported_in_api": True,
        "availability_nux": None,
        "upgrade": None,
        "priority": 1,
        "base_instructions": "You are a coding agent. Complete the assigned task using the repository and return the requested JSON result.",
        "model_messages": {
            "instructions_template": "You are a coding agent. Complete the assigned task using the repository and return the requested JSON result.",
        },
        "experimental_supported_tools": [],
        "supports_search_tool": True,
        "supports_reasoning_summaries": True,
    }


def _restrict_file(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass
