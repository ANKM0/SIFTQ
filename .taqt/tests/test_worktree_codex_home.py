"""Tests for worktree-scoped Codex home resolution (Issue #174 slice 05).

Covers profile codex_home assignment, workspace-relative resolution with
override precedence and default fallback, task_run injecting the resolved
CODEX_HOME for both profiles, switch tasks writing into the worktree-scoped
CODEX_HOME, and the .gitignore entry for .taqt/codex-home/.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / ".taqt" / "scripts"))

from scripts.switch_codex_profile import main as switch_main
from taqt.profiles import resolve_codex_home
from taqt.task_run import main as task_run_main
from taqt.task_store import create_issue_task


@pytest.fixture(autouse=True)
def allow_enabled_label(monkeypatch) -> None:
    monkeypatch.setattr("taqt.task_run.enabled_error", lambda _task: None)


def test_profiles_assign_relative_worktree_codex_homes() -> None:
    profiles = yaml.safe_load(
        (REPOSITORY_ROOT / ".taqt" / "config" / "profiles.yaml").read_text(
            encoding="utf-8"
        )
    )["profiles"]

    assert profiles["main"]["codex_home"] == ".taqt/codex-home/main"
    assert profiles["deepseek"]["codex_home"] == ".taqt/codex-home/deepseek"


def test_resolve_codex_home_resolves_relative_path_against_workspace() -> None:
    workspace = Path("/repo")

    main_home = resolve_codex_home(
        {"codex_home": ".taqt/codex-home/main"},
        workspace,
        profile="main",
    )
    deepseek_home = resolve_codex_home(
        {"codex_home": ".taqt/codex-home/deepseek"},
        workspace,
        profile="deepseek",
    )

    assert main_home == Path("/repo/.taqt/codex-home/main")
    assert deepseek_home == Path("/repo/.taqt/codex-home/deepseek")


def test_resolve_codex_home_preserves_absolute_and_tilde_paths(
    tmp_path: Path, monkeypatch
) -> None:
    absolute = tmp_path / "absolute-home"
    monkeypatch.setenv("HOME", str(tmp_path))

    assert resolve_codex_home(
        {"codex_home": str(absolute)},
        tmp_path,
        profile="main",
    ) == absolute
    assert resolve_codex_home(
        {"codex_home": "~/.codex-deepseek"},
        tmp_path,
        profile="deepseek",
    ) == tmp_path / ".codex-deepseek"


def test_resolve_codex_home_prefers_cli_override() -> None:
    override = Path("/tmp/cli-home")

    assert (
        resolve_codex_home(
            {"codex_home": ".taqt/codex-home/main"},
            Path("/repo"),
            profile="main",
            override=override,
        )
        == override
    )


def test_resolve_codex_home_falls_back_to_profile_default(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert resolve_codex_home(
        {"loop": "development_feedback_loop_deepseek"},
        tmp_path,
        profile="deepseek",
    ) == tmp_path / ".codex-deepseek"


def test_codex_home_is_gitignored() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".taqt/codex-home/" in gitignore


def _write_profiles(tmp_path: Path, *, include_deepseek: bool) -> Path:
    loop_root = tmp_path / "loops"
    loop_root.mkdir()
    profiles = {
        "profiles": {
            "main": {
                "loop": "development_feedback_loop",
                "codex_home": ".taqt/codex-home/main",
            }
        }
    }
    if include_deepseek:
        profiles["profiles"]["deepseek"] = {
            "loop": "development_feedback_loop_deepseek",
            "codex_home": ".taqt/codex-home/deepseek",
            "env_key": "DEEPSEEK_API_KEY",
        }
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        yaml.safe_dump(profiles, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return loop_root


def _write_terminal_loop(loop_root: Path, name: str) -> None:
    (loop_root / f"{name}.yaml").write_text(
        """
version: 1
id: development_feedback_loop
steps:
  - id: done
    kind: terminal
""",
        encoding="utf-8",
    )


def _run_task_run(
    tmp_path: Path,
    loop_root: Path,
    *,
    profile: str,
    monkeypatch,
) -> tuple[int, dict[str, object]]:
    task_root = tmp_path / "tasks"
    runs_root = tmp_path / "runs"
    task_root.mkdir()
    task_path, _task = create_issue_task(
        repo="owner/repo",
        issue_number=174,
        loop="development_feedback_loop",
        task_root=task_root,
    )
    calls: list[dict[str, object]] = []

    def fake_run_loop(**kwargs):
        calls.append(kwargs)
        return {"status": "done", "run_dir": str(runs_root / "run")}

    monkeypatch.setattr("taqt.task_run.run_loop", fake_run_loop)
    exit_code = task_run_main(
        [
            str(task_path),
            "--loop-root",
            str(loop_root),
            "--runs-root",
            str(runs_root),
            "--workspace",
            str(tmp_path),
            "--skip-readiness-check",
            "--profile",
            profile,
        ]
    )
    return exit_code, calls[0]


def test_task_run_sets_worktree_codex_home_for_main_profile(
    tmp_path: Path, monkeypatch
) -> None:
    loop_root = _write_profiles(tmp_path, include_deepseek=False)
    _write_terminal_loop(loop_root, "development_feedback_loop")

    exit_code, call = _run_task_run(
        tmp_path, loop_root, profile="main", monkeypatch=monkeypatch
    )

    assert exit_code == 0
    assert call["child_environment"] == {
        "CODEX_HOME": str(tmp_path / ".taqt" / "codex-home" / "main"),
    }


def test_task_run_sets_worktree_codex_home_for_deepseek_profile(
    tmp_path: Path, monkeypatch
) -> None:
    loop_root = _write_profiles(tmp_path, include_deepseek=True)
    _write_terminal_loop(
        loop_root, "development_feedback_loop_deepseek"
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    exit_code, call = _run_task_run(
        tmp_path, loop_root, profile="deepseek", monkeypatch=monkeypatch
    )

    assert exit_code == 0
    assert call["child_environment"] == {
        "CODEX_HOME": str(tmp_path / ".taqt" / "codex-home" / "deepseek"),
        "DEEPSEEK_API_KEY": "secret",
    }


def _write_taqt_profiles(tmp_path: Path) -> None:
    """Write profiles.yaml under tmp_path/.taqt/config for switch-script tests."""
    config_dir = tmp_path / ".taqt" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "profiles.yaml").write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "main": {
                        "loop": "development_feedback_loop",
                        "codex_home": ".taqt/codex-home/main",
                    },
                    "deepseek": {
                        "loop": "development_feedback_loop_deepseek",
                        "codex_home": ".taqt/codex-home/deepseek",
                        "env_key": "DEEPSEEK_API_KEY",
                    },
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_switch_deepseek_writes_config_into_worktree_codex_home(
    tmp_path: Path, monkeypatch
) -> None:
    _write_taqt_profiles(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("scripts.switch_codex_profile.REPO_ROOT", tmp_path)

    exit_code = switch_main(["set", "deepseek"])

    assert exit_code == 0
    config = tmp_path / ".taqt" / "codex-home" / "deepseek" / "config.toml"
    assert config.exists()
    config_text = config.read_text(encoding="utf-8")
    assert 'model_provider = "deepseek"' in config_text
    assert 'env_key = "DEEPSEEK_API_KEY"' in config_text
    active = yaml.safe_load(
        (tmp_path / ".taqt" / "config" / "active.yaml").read_text(encoding="utf-8")
    )
    assert active == {"active_profile": "deepseek"}


def test_switch_main_copies_template_into_worktree_codex_home(
    tmp_path: Path, monkeypatch
) -> None:
    _write_taqt_profiles(tmp_path)
    # HOME is separate from REPO_ROOT so the test proves the template is
    # sourced from ~/.codex, not from a repository-local .codex directory.
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    template = home / ".codex" / "config.main.toml"
    template.parent.mkdir(parents=True)
    template.write_text('model_provider = "openai"\n', encoding="utf-8")
    monkeypatch.setattr("scripts.switch_codex_profile.REPO_ROOT", tmp_path)

    exit_code = switch_main(["set", "main"])

    assert exit_code == 0
    config = tmp_path / ".taqt" / "codex-home" / "main" / "config.toml"
    assert config.exists()
    assert config.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")
    active = yaml.safe_load(
        (tmp_path / ".taqt" / "config" / "active.yaml").read_text(encoding="utf-8")
    )
    assert active == {"active_profile": "main"}
