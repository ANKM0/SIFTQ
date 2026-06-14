from __future__ import annotations

import os
from pathlib import Path
import subprocess


SERVICE_NAME = "sympohy-watch.service"
TIMER_NAME = "sympohy-watch.timer"
DEFAULT_SYSTEMD_PATH = "/usr/local/bin:/usr/bin:/bin"


def install_systemd_units(repo_root: Path) -> int:
    target = Path.home() / ".config/systemd/user"
    target.mkdir(parents=True, exist_ok=True)
    source = repo_root / ".sympohy/systemd"

    for name in (SERVICE_NAME, TIMER_NAME):
        text = (source / name).read_text(encoding="utf-8")
        text = text.replace("@@REPO_ROOT@@", str(repo_root))
        text = text.replace("@@PATH@@", _systemd_escape(_runtime_path()))
        (target / name).write_text(text, encoding="utf-8")

    subprocess.check_call(["systemctl", "--user", "daemon-reload"])
    subprocess.check_call(["systemctl", "--user", "enable", "--now", TIMER_NAME])
    return 0


def print_systemd_status() -> int:
    subprocess.call(["systemctl", "--user", "status", TIMER_NAME, "--no-pager"])
    subprocess.call(["systemctl", "--user", "status", SERVICE_NAME, "--no-pager"])
    subprocess.call(["journalctl", "--user", "-u", SERVICE_NAME, "-n", "50", "--no-pager"])
    return 0


def _runtime_path() -> str:
    return os.environ.get("PATH") or DEFAULT_SYSTEMD_PATH


def _systemd_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
