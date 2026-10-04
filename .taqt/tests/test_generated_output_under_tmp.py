"""Tests for ADR 0049/0065: generated artifacts live under `tmp/`.

Committed tool config stays in `.config/`; virtualenvs, caches, test output, and
local Wrangler state should be redirected into the git-ignored `tmp/` directory.
`graphify-out/` stays at the repository root because `graphify install` bakes the
literal path into its skills and hooks. `.wrangler/` stays at the repository
root because `cf dev` uses it for local state and does not accept `--persist-to`.
"""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_env_sh_redirects_venv_and_ruff_cache_under_tmp() -> None:
    env = (REPOSITORY_ROOT / ".config/env.sh").read_text(encoding="utf-8")
    assert 'export TMP_ROOT="${TMP_ROOT:-$_repo_root/tmp}"' in env
    assert 'UV_PROJECT_ENVIRONMENT="$TMP_ROOT/.venv"' in env
    assert 'RUFF_CACHE_DIR="$_repo_root/tmp/.ruff_cache"' in env


def test_taskfile_redirects_venv_and_ruff_cache_under_tmp() -> None:
    taskfile = (REPOSITORY_ROOT / ".config/Taskfile.yml").read_text(encoding="utf-8")
    assert "TMP_ROOT: '{{.TMP_ROOT | default (printf \"%s/../tmp\" .ROOT_DIR)}}'" in taskfile
    assert (
        "UV_PROJECT_ENVIRONMENT: '{{.TMP_ROOT | default (printf \"%s/../tmp\" .ROOT_DIR)}}/.venv'"
        in taskfile
    )
    assert 'RUFF_CACHE_DIR: "{{.ROOT_DIR}}/../tmp/.ruff_cache"' in taskfile


def test_pytest_cache_dir_is_under_tmp() -> None:
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'cache_dir = "tmp/.pytest_cache"' in pyproject


def test_playwright_output_dir_is_under_tmp() -> None:
    config = (REPOSITORY_ROOT / ".config/playwright.config.ts").read_text(encoding="utf-8")
    assert "tmp/test-results" in config


def test_local_dev_uses_cf_and_tool_fixed_wrangler_state() -> None:
    package = (REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8")
    assert '"dev": "cf dev"' in package
    assert "--persist-to" not in package
    assert ".config/.wrangler/state" not in package


def test_gitignore_keeps_graphify_out_and_drops_config_caches() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "graphify-out/" in gitignore
    assert ".wrangler/" in gitignore
    assert ".config/.venv/" not in gitignore
    assert ".config/.ruff_cache/" not in gitignore
