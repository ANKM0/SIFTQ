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
