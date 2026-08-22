# Source this file from Yoriwake's interactive shell to route a bare
# `git pull` to `task repo:pull-main` only inside this repository's worktrees.
#
# Install:
#   source /home/develop/Yoriwake/scripts/yoriwake_git_pull.sh
# Uninstall:
#   unset -f git _yoriwake_git_worktree
# Bypass:
#   command git pull [args...]

_yoriwake_git_pull_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_yoriwake_git_worktree() {
    local top
    top="$(command git rev-parse --show-toplevel 2>/dev/null)" || return 1
    case "$top" in
        "$_yoriwake_git_pull_root"|"$_yoriwake_git_pull_root"/*) ;;
        *) return 1 ;;
    esac
    [ -f "$top/.taqt/config/profiles.yaml" ] && [ -f "$top/taskfile/core.yml" ]
}

git() {
    if [ "${1:-}" = "pull" ] && [ "$#" -eq 1 ] && _yoriwake_git_worktree; then
        local top
        top="$(command git rev-parse --show-toplevel 2>/dev/null)"
        (cd "$top" && command task repo:pull-main)
    else
        command git "$@"
    fi
}
