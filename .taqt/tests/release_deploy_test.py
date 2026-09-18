import json
import subprocess
import sys

import pytest

from scripts import release_deploy


def test_normalized_version_accepts_optional_v() -> None:
    assert release_deploy.normalized_version("v0.5.3") == "0.5.3"
    assert release_deploy.tag_name("0.5.3") == "v0.5.3"


def test_normalized_version_rejects_incomplete_version() -> None:
    try:
        release_deploy.normalized_version("v0.5")
    except ValueError as error:
        assert "version must" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_build_plan_classifies_worker_and_migrations(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:3] == ("git", "diff", "--name-only"):
            return "src/index.tsx\nmigrations/0003_add.sql\ndocs/readme.md"
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2")

    assert plan.mode == "release+deploy"
    assert plan.migrations == ["migrations/0003_add.sql"]


def _prepare_deploy(monkeypatch, tmp_path, *, migration_fails: bool = False) -> list[list[str]]:
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "wrangler.jsonc").write_text(
        json.dumps(
            {
                "d1_databases": [
                    {"binding": "DB", "database_name": "siftq", "migrations_dir": "migrations"}
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    def fake_command(*args: str) -> str:
        if args == ("git", "status", "--porcelain"):
            return ""
        if args in {
            ("git", "rev-parse", "v0.5.3^{commit}"),
            ("git", "rev-parse", "HEAD"),
        }:
            return "commit"
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs):
        calls.append(args)
        if len(calls) == 1 and migration_fails:
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, stdout="No migrations to apply\n")

    monkeypatch.setattr(release_deploy.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["release_deploy.py", "deploy", "--tag", "v0.5.3", "--execute"])
    return calls


def test_deploy_checks_configured_d1_binding_before_worker(monkeypatch, tmp_path) -> None:
    calls = _prepare_deploy(monkeypatch, tmp_path)

    assert release_deploy.main() == 0
    assert calls == [
        ["bun", "x", "wrangler", "d1", "migrations", "list", "DB", "--remote", "-c", ".config/wrangler.jsonc"],
        ["bun", "x", "wrangler", "deploy", "-c", ".config/wrangler.jsonc"],
    ]


def test_deploy_does_not_deploy_when_migration_check_fails(monkeypatch, tmp_path) -> None:
    calls = _prepare_deploy(monkeypatch, tmp_path, migration_fails=True)

    with pytest.raises(SystemExit):
        release_deploy.main()

    assert calls == [
        ["bun", "x", "wrangler", "d1", "migrations", "list", "DB", "--remote", "-c", ".config/wrangler.jsonc"]
    ]
