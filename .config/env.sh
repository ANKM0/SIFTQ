# shellcheck shell=sh
# Canonical environment overrides for the tool configs under .config/.
# Task applies the same values through its top-level env: block.
# Source this before invoking tools directly:
#   . ./.config/env.sh
_config_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" && pwd)"
_repo_root="$(dirname -- "$_config_dir")"
export AQUA_CONFIG="$_config_dir/aqua.yaml"
export AQUA_POLICY_CONFIG="$_config_dir/aqua-policy.yaml"
export UV_PROJECT_ENVIRONMENT="$_repo_root/tmp/.venv"
export RUFF_CACHE_DIR="$_repo_root/tmp/.ruff_cache"
export UV_CACHE_DIR="$_repo_root/tmp/uv-cache"
export PLAYWRIGHT_BROWSERS_PATH="$_repo_root/tmp/playwright-browsers"
export PUPPETEER_CACHE_DIR="$_repo_root/tmp/puppeteer-cache"
