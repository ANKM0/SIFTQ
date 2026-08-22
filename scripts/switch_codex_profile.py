import argparse
import shutil
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / ".taqt" / "scripts"))

from taqt.deepseek import write_codex_profile_config
from taqt.profiles import ACTIVE_FILE_NAME, load_profiles, config_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="switch-codex-profile")
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("profile")
    subparsers.add_parser("show")
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

    if profile == "deepseek":
        _backup_codex_config()
        write_codex_profile_config(_codex_config_path())
    else:
        if not _install_main_codex_config():
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


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _backup_codex_config() -> None:
    target = _codex_config_path()
    backup = target.with_suffix(".toml.bak")
    if target.exists() and not backup.exists():
        shutil.copyfile(target, backup)


def _install_main_codex_config() -> bool:
    target = _codex_config_path()
    main_template = target.parent / "config.main.toml"
    fallback = target.parent / "backup-deepseek" / "config.toml"
    if main_template.exists():
        _backup_codex_config()
        shutil.copyfile(main_template, target)
        return True
    if fallback.exists():
        _backup_codex_config()
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
