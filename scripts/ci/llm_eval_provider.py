import argparse
import sys
import tomllib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / ".taqt" / "scripts"))


def resolve_codex_config(workspace: Path) -> dict:
    from taqt.profiles import load_profiles, resolve_codex_home, resolve_profile

    loop_root = workspace / ".taqt" / "loops"
    profile = resolve_profile(loop_root)
    profiles = load_profiles(loop_root)
    codex_home = resolve_codex_home(profiles[profile], workspace, profile=profile)
    config_path = codex_home / "config.toml"
    return tomllib.loads(config_path.read_text(encoding="utf-8"))


def chat_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def build_provider(config: dict) -> dict:
    model = str(config["model"])
    provider_name = str(config.get("model_provider", "openai"))
    provider_conf = (config.get("model_providers") or {}).get(provider_name) or {}
    base_url = provider_conf.get("base_url")

    if provider_name == "deepseek":
        provider = {"id": f"deepseek:chat:{model}", "config": {}}
        if isinstance(base_url, str) and base_url:
            provider["config"]["apiBaseUrl"] = chat_base_url(base_url)
        return provider

    if provider_name == "openrouter":
        provider = {"id": f"openrouter:chat:{model}", "config": {}}
        if isinstance(base_url, str) and base_url:
            provider["config"]["apiBaseUrl"] = base_url
        return provider

    if provider_name == "openai":
        provider = {"id": f"openai:chat:{model}", "config": {}}
        if isinstance(base_url, str) and base_url:
            provider["config"]["apiBaseUrl"] = base_url
        return provider

    raise ValueError(f"unsupported model_provider: {provider_name}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate promptfoo providers from Codex config.")
    parser.add_argument("--workspace", type=Path, default=REPO_ROOT, help="Repository workspace root.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "eval" / ".generated-providers.yaml",
        help="Output promptfoo providers file.",
    )
    args = parser.parse_args(argv)

    config = resolve_codex_config(args.workspace)
    provider = build_provider(config)
    payload = {"providers": [provider]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
