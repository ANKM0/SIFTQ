# Repository Policy

- Follow `docs/contributing/branch-strategy.md`.
- Follow `docs/contributing/commit-message-format.md`.
- Use `task ci` as the normal validation gate before PR handoff.
- Run `task codd:validate` for documentation or governance changes.
- Do not modify unrelated user work or untracked files.
- Do not add TAKT to SIFTQ application runtime dependencies.
- Use aqua-managed tooling entry points from `Taskfile.yml`.
