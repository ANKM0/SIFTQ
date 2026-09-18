"""Tests for the `.aqua/` discovery symlinks and their setup script (Issue #462).

aqua only discovers `aqua.yaml` / `.aqua/aqua.yaml` / `aqua/aqua.yaml` from the
current directory upward. The repository keeps its config in `.config/`, so
`.aqua/aqua.yaml` and the local registry must be symlinks into `.config/` for
proxied commands such as `opencode` to resolve without `AQUA_CONFIG`.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETUP_TASKFILE = REPOSITORY_ROOT / "taskfile" / "setup.yml"
CODEX_RULES = REPOSITORY_ROOT / ".codex" / "rules" / "shared.rules"
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.setup_aqua_symlinks import LINKS, link_state, main, set_link


def _seed_sources(root: Path) -> None:
    for target in LINKS.values():
        source = (root / ".aqua" / target).resolve()
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("packages: []\n", encoding="utf-8")


def test_repository_links_point_into_config() -> None:
    for link, target in LINKS.items():
        path = REPOSITORY_ROOT / link
        assert path.is_symlink(), f"{link} is not a symlink"
        assert path.readlink().as_posix() == target
        assert path.resolve().is_file(), f"{link} target does not exist"


def test_setup_task_runs_the_link_script() -> None:
    tasks = yaml.safe_load(SETUP_TASKFILE.read_text(encoding="utf-8"))["tasks"]
    task = tasks.get("setup:aqua-links")
    assert task is not None, "setup:aqua-links is not defined"
    commands = "\n".join(str(cmd) for cmd in task.get("cmds", []))
    assert "uv run python scripts/setup_aqua_symlinks.py" in commands


def test_setup_task_is_allowed_in_codex_rules() -> None:
    rules = CODEX_RULES.read_text(encoding="utf-8")
    assert (
        'prefix_rule(pattern=["task", "-t", ".config/Taskfile.yml", "setup:aqua-links"], decision="allow")'
        in rules
    )


def test_set_link_is_idempotent(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    for link, target in LINKS.items():
        assert link_state(tmp_path, link, target) == "missing"

    set_link(tmp_path, *next(iter(LINKS.items())))
    set_link(tmp_path, *next(iter(LINKS.items())))

    link, target = next(iter(LINKS.items()))
    assert link_state(tmp_path, link, target) == "ok"


def test_main_check_fails_when_links_are_missing(tmp_path: Path, capsys) -> None:
    _seed_sources(tmp_path)

    assert main(["--root", str(tmp_path), "--check"]) == 1
    assert "missing" in capsys.readouterr().err


def test_main_creates_links_then_check_passes(tmp_path: Path, capsys) -> None:
    _seed_sources(tmp_path)

    assert main(["--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--check"]) == 0
    for link, target in LINKS.items():
        assert (tmp_path / link).is_symlink()
        assert link_state(tmp_path, link, target) == "ok"


def test_main_refuses_to_overwrite_a_regular_file(tmp_path: Path, capsys) -> None:
    _seed_sources(tmp_path)
    conflict = tmp_path / next(iter(LINKS))
    conflict.parent.mkdir(parents=True, exist_ok=True)
    conflict.write_text("keep me\n", encoding="utf-8")

    assert main(["--root", str(tmp_path)]) == 1
    assert "not the expected symlink" in capsys.readouterr().err
    assert conflict.read_text(encoding="utf-8") == "keep me\n"


def test_main_fails_when_source_is_absent(tmp_path: Path, capsys) -> None:
    assert main(["--root", str(tmp_path)]) == 1
    assert "does not exist" in capsys.readouterr().err
