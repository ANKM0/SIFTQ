import argparse
import shutil
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / ".taqt" / "scripts"))

from taqt.deepseek import write_codex_profile_config as write_deepseek_codex_profile_config
from taqt.qwen import write_codex_profile_config as write_qwen_codex_profile_config
from taqt.profiles import (
    ACTIVE_FILE_NAME,
    load_profiles,
    resolve_codex_home,
    config_dir,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="switch-codex-profile")
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("profile")
    subparsers.add_parser("show")
    path_parser = subparsers.add_parser("path")
    path_parser.add_argument("profile")
    args = parser.parse_args(argv)

    loop_root = REPO_ROOT / ".taqt" / "loops"
    profiles = load_profiles(loop_root)
    if args.command == "show":
        print(f"active_profile: {_active_profile(loop_root)}")
        return 0

    profile = args.profile
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        print(f"unknown taqt profile: {profile}; available: {available}")
        return 2

    if args.command == "path":
        print(resolve_codex_home(profiles[profile], REPO_ROOT, profile=profile))
        return 0

    codex_home = resolve_codex_home(profiles[profile], REPO_ROOT, profile=profile)
    if profile == "deepseek":
        write_deepseek_codex_profile_config(codex_home / "config.toml", codex_home=codex_home)
    elif profile == "qwen":
        write_qwen_codex_profile_config(codex_home / "config.toml", codex_home=codex_home)
    else:
        if not _install_main_codex_config(codex_home):
            return 2

    _write_active_profile(loop_root, profile)

    print(f"active_profile: {profile}")
    return 0


def _active_profile(loop_root: Path) -> str:
    path = config_dir(loop_root) / ACTIVE_FILE_NAME
    if not path.exists():
        return "main"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        value = payload.get("active_profile")
        if isinstance(value, str) and value:
            return value
    return "main"


def _write_active_profile(loop_root: Path, profile: str) -> None:
    path = config_dir(loop_root) / ACTIVE_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"active_profile": profile}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _install_main_codex_config(codex_home: Path) -> bool:
    target = codex_home / "config.toml"
    source_dir = Path.home() / ".codex"
    main_template = source_dir / "config.main.toml"
    fallback = source_dir / "backup-deepseek" / "config.toml"
    if main_template.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(main_template, target)
        return True
    if fallback.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fallback, target)
        return True
    print(
        f"main Codex config template is missing; create {main_template} "
        "before switching to main.",
        file=sys.stderr,
    )
    return False


if __name__ == "__main__":
    raise SystemExit(main())
