from pathlib import Path
from typing import Any

import yaml


DEFAULT_PROFILE = "main"
PROFILES_FILE_NAME = "profiles.yaml"
ACTIVE_FILE_NAME = "active.yaml"


def config_dir(loop_root: Path) -> Path:
    return loop_root.parent / "config"


def load_profiles(loop_root: Path) -> dict[str, dict[str, Any]]:
    path = config_dir(loop_root) / PROFILES_FILE_NAME
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError(f"{path} requires a non-empty profiles mapping")

    normalized: dict[str, dict[str, Any]] = {}
    for name, profile in profiles.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path} contains an empty profile name")
        if not isinstance(profile, dict):
            raise ValueError(f"{path} profile {name} must be a mapping")
        if not isinstance(profile.get("loop"), str) or not profile["loop"]:
            raise ValueError(f"{path} profile {name} requires a loop")
        normalized[name] = profile
    return normalized


def load_active_profile(loop_root: Path) -> str | None:
    path = config_dir(loop_root) / ACTIVE_FILE_NAME
    if not path.exists():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    value = payload.get("active_profile")
    return value if isinstance(value, str) and value else None


def resolve_profile(loop_root: Path, requested: str | None = None) -> str:
    profiles = load_profiles(loop_root)
    profile = requested or load_active_profile(loop_root) or DEFAULT_PROFILE
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        raise ValueError(f"unknown taqt profile: {profile}; available: {available}")
    return profile
