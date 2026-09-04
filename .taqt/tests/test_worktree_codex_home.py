"""Tests for shared Codex home usage in taqt runs (Issue #273)."""

import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / ".taqt" / "scripts"))

from taqt.profiles import resolve_codex_home
from taqt.task_run import main as task_run_main
from taqt.task_store import create_issue_task


@pytest.fixture(autouse=True)
def allow_enabled_label(monkeypatch) -> None:
    monkeypatch.setattr("taqt.task_run.enabled_error", lambda _task: None)


def test_profiles_have_no_worktree_codex_home_or_qwen_profile() -> None:
    profiles = yaml.safe_load(
        (REPOSITORY_ROOT / ".taqt" / "config" / "profiles.yaml").read_text(
            encoding="utf-8"
        )
    )["profiles"]

    assert set(profiles) == {"main", "deepseek", "burn"}
    assert all("codex_home" not in profile for profile in profiles.values())
    assert profiles["deepseek"]["env_keys"] == [
        "DEEPSEEK_API_KEY",
        "OPENCODE_API_KEY",
    ]
    assert profiles["burn"]["loop"] == "burn_loop"
    assert profiles["burn"]["env_keys"] == [
        "DEEPSEEK_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENCODE_API_KEY",
    ]


def test_sub_loop_selects_go_luna_for_reviewers_and_muse_for_implementers() -> None:
    loop = yaml.safe_load(
        (REPOSITORY_ROOT / ".taqt" / "loops" / "sub_loop.yaml").read_text(
            encoding="utf-8"
        )
    )
    agents = loop["agents"]

    assert agents["design"]["adapter"] == "opencode"
    assert agents["design"]["model"] == "opencode-go/gpt-5.6-luna"
    for agent_name in ("test", "checker"):
        assert agents[agent_name]["adapter"] == "opencode"
        assert agents[agent_name]["model"] == "opencode-go/gpt-5.6-luna"
    for agent_name in ("implement", "fix"):
        assert agents[agent_name]["adapter"] == "opencode"
        assert agents[agent_name]["model"] == "opencode/muse-spark-1.3-contributor-free"


def test_resolve_codex_home_uses_shared_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert resolve_codex_home({}, Path("/repo"), profile="deepseek") == tmp_path / ".codex"


def test_resolve_codex_home_preserves_explicit_override(tmp_path: Path) -> None:
    override = tmp_path / "isolated-codex"

    assert resolve_codex_home({}, tmp_path, profile="deepseek", override=override) == override


def test_task_run_inherits_shared_home_and_passes_deepseek_keys(
    tmp_path: Path, monkeypatch
) -> None:
    loop_root = tmp_path / "loops"
    loop_root.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "profiles.yaml").write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "deepseek": {
                        "loop": "sub_loop",
                        "env_keys": ["DEEPSEEK_API_KEY", "OPENCODE_API_KEY"],
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (loop_root / "sub_loop.yaml").write_text(
        "version: 1\nid: test\nsteps:\n  - id: done\n    kind: terminal\n",
        encoding="utf-8",
    )
    task_root = tmp_path / "tasks"
    task_root.mkdir()
    task_path, _ = create_issue_task(
        repo="owner/repo", issue_number=273, loop="test", task_root=task_root
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "taqt.task_run.run_loop",
        lambda **kwargs: calls.append(kwargs)
        or {"status": "done", "run_dir": str(tmp_path / "run")},
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("OPENCODE_API_KEY", "opencode-key")

    exit_code = task_run_main(
        [
            str(task_path),
            "--loop-root",
            str(loop_root),
            "--task-root",
            str(task_root),
            "--workspace",
            str(tmp_path),
            "--skip-readiness-check",
            "--profile",
            "deepseek",
        ]
    )

    assert exit_code == 0
    assert calls[0]["child_environment"] == {
        "DEEPSEEK_API_KEY": "deepseek-key",
        "OPENCODE_API_KEY": "opencode-key",
    }
