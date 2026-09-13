import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "ci" / "check_package_version.py"
SPEC = importlib.util.spec_from_file_location("check_package_version", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
check_package_version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_package_version)


def test_latest_release_version_uses_tags_reachable_from_head(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_check_output(command: list[str], *, text: bool) -> str:
        calls.append(command)
        assert text is True
        return "v0.12.0\n"

    monkeypatch.setattr(check_package_version.subprocess, "check_output", fake_check_output)

    assert check_package_version.latest_release_version(Path("/repo")) == (0, 12, 0)
    assert calls == [
        ["git", "-C", "/repo", "tag", "--merged", "HEAD", "--list", "v[0-9]*"]
    ]
