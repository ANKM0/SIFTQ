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
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2")

    assert plan.mode == "release+deploy"
    assert plan.migrations == ["migrations/0003_add.sql"]


def test_build_plan_reports_latest_tag_and_candidates(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.17.9"
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan(None, "HEAD", None)

    assert plan.version is None
    assert plan.latest_tag == "v0.17.9"
    assert plan.next_patch == "v0.17.10"
    assert plan.next_minor == "v0.18.0"
    assert plan.prs == []


def test_build_plan_resolves_prs_and_unions_changed_files(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args == ("gh", "pr", "view", "12", "--json", "files"):
            return json.dumps({"files": [{"path": "src/index.tsx"}, {"path": "migrations/0003_add.sql"}]})
        if args == ("gh", "pr", "view", "13", "--json", "files"):
            return json.dumps({"files": [{"path": "src/index.tsx"}, {"path": "docs/readme.md"}]})
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", None, ["12", "13"])

    assert plan.prs == ["12", "13"]
    assert plan.migrations == ["migrations/0003_add.sql"]
    assert plan.mode == "release+deploy"


def test_build_plan_prefers_pr_files_over_base_diff(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args[:3] == ("git", "diff", "--name-only"):
            raise AssertionError("base diff must not classify when --pr is given")
        if args[:2] == ("git", "show"):
            raise subprocess.CalledProcessError(128, args)
        if args == ("gh", "pr", "view", "12", "--json", "files"):
            return json.dumps({"files": [{"path": "docs/readme.md"}]})
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2", ["12"])

    assert plan.mode == "release-only"


def test_build_plan_detects_cf_config_from_pr_without_base(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args == ("gh", "pr", "view", "12", "--json", "files"):
            return json.dumps({"files": [{"path": "cloudflare.config.ts"}]})
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", None, ["12"])

    assert plan.worker_change is True
    assert plan.mode == "release+deploy"


CF_CONFIG = (
    "import { bindings, defineConfig } from \"cf/config\";\n"
    "export default defineConfig({ worker: { name: \"app\", compatibilityDate: \"2025-06-01\", env: {\n"
    "  DB: bindings.d1({ name: \"siftq\", id: \"20ca1496-cadc-4b40-9265-1d59d55d5b82\" }),\n"
    "} } });\n"
)
CF_CONFIG_AFTER = CF_CONFIG.replace("2025-06-01", "2026-01-01")


def _cf_command(contents: dict[str, str]):
    def fake_command(*args: str) -> str:
        if args[:2] == ("git", "rev-parse"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args[:3] == ("git", "diff", "--name-only"):
            return "cloudflare.config.ts\nwrangler.config.ts"
        if args[:2] == ("git", "show"):
            key = args[2]
            if key in contents:
                return contents[key]
            raise subprocess.CalledProcessError(128, args)
        raise AssertionError(args)

    return fake_command


def test_build_plan_ignores_unchanged_cf_config(monkeypatch) -> None:
    monkeypatch.setattr(
        release_deploy,
        "command",
        _cf_command(
            {
                "v0.5.2:cloudflare.config.ts": CF_CONFIG,
                "commit:cloudflare.config.ts": CF_CONFIG,
            }
        ),
    )

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2")

    assert plan.worker_change is False
    assert plan.mode == "release-only"


def test_build_plan_detects_cf_config_change(monkeypatch) -> None:
    monkeypatch.setattr(
        release_deploy,
        "command",
        _cf_command(
            {
                "v0.5.2:cloudflare.config.ts": CF_CONFIG,
                "commit:cloudflare.config.ts": CF_CONFIG_AFTER,
            }
        ),
    )

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2")

    assert plan.worker_change is True
    assert plan.mode == "release+deploy"


def test_d1_database_id_reads_cloudflare_config(tmp_path) -> None:
    (tmp_path / "cloudflare.config.ts").write_text(CF_CONFIG, encoding="utf-8")

    assert release_deploy.d1_database_id(tmp_path / "cloudflare.config.ts") == "20ca1496-cadc-4b40-9265-1d59d55d5b82"


def test_d1_database_id_rejects_missing_id(tmp_path) -> None:
    (tmp_path / "cloudflare.config.ts").write_text("export default {};\n", encoding="utf-8")

    with pytest.raises(ValueError):
        release_deploy.d1_database_id(tmp_path / "cloudflare.config.ts")


def test_build_plan_uses_base_for_cf_config_comparison_with_pr(monkeypatch) -> None:
    def fake_command(*args: str) -> str:
        if args[:2] == ("git", "rev-parse"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args == ("gh", "pr", "view", "12", "--json", "files"):
            return json.dumps({"files": [{"path": "docs/readme.md"}]})
        if args[:2] == ("git", "show"):
            contents = {
                "v0.5.2:cloudflare.config.ts": CF_CONFIG,
                "commit:cloudflare.config.ts": CF_CONFIG_AFTER,
            }
            if args[2] not in contents:
                raise subprocess.CalledProcessError(128, args)
            return contents[args[2]]
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)

    plan = release_deploy.build_plan("v0.5.3", "HEAD", "v0.5.2", ["12"])

    assert plan.worker_change is True
    assert plan.mode == "release+deploy"


def test_plan_cli_accepts_repeated_pr_without_version(monkeypatch, capsys) -> None:
    def fake_command(*args: str) -> str:
        if args[:3] == ("git", "rev-parse", "HEAD^{commit}"):
            return "commit"
        if args[:2] == ("git", "describe"):
            return "v0.5.2"
        if args[:2] == ("gh", "pr"):
            return json.dumps({"files": [{"path": "src/index.tsx"}]})
        raise AssertionError(args)

    monkeypatch.setattr(release_deploy, "command", fake_command)
    monkeypatch.setattr(sys, "argv", ["release_deploy.py", "plan", "--ref", "HEAD", "--pr", "12", "--pr", "13"])

    assert release_deploy.main() == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["version"] is None
    assert payload["latest_tag"] == "v0.5.2"
    assert payload["next_patch"] == "v0.5.3"
    assert payload["prs"] == ["12", "13"]
    assert payload["worker_change"] is True


def _prepare_deploy(monkeypatch, tmp_path, *, migration_fails: bool = False) -> list[list[str]]:
    (tmp_path / "cloudflare.config.ts").write_text(CF_CONFIG, encoding="utf-8")
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp" / "cloudflare-secrets.env").write_text(
        "AUTH_PASSWORD=preview\nSESSION_SECRET=preview\n", encoding="utf-8"
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
        ["bun", "x", "cf", "d1", "migrations", "list", "20ca1496-cadc-4b40-9265-1d59d55d5b82", "--dir", "migrations"],
        ["bun", "x", "cf", "deploy", "--secrets-file", "tmp/cloudflare-secrets.env"],
    ]


def test_deploy_does_not_deploy_when_migration_check_fails(monkeypatch, tmp_path) -> None:
    calls = _prepare_deploy(monkeypatch, tmp_path, migration_fails=True)

    with pytest.raises(SystemExit):
        release_deploy.main()

    assert calls == [
        ["bun", "x", "cf", "d1", "migrations", "list", "20ca1496-cadc-4b40-9265-1d59d55d5b82", "--dir", "migrations"]
    ]


def test_deploy_requires_secrets_file(monkeypatch, tmp_path) -> None:
    (tmp_path / "cloudflare.config.ts").write_text(CF_CONFIG, encoding="utf-8")
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
    monkeypatch.setattr(sys, "argv", ["release_deploy.py", "deploy", "--tag", "v0.5.3", "--execute"])

    with pytest.raises(SystemExit):
        release_deploy.main()
