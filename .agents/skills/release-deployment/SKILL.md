---
name: release-deployment
description: Plan and execute SIFTQ GitHub releases and Cloudflare Workers deployments using the repository release tasks.
---

# Release and Deployment

Read [ADR 0034](../../../docs/adr/0034-separate-release-and-worker-deployment.md), [Release](../../../docs/contributing/release.md), and [deployment](../../../docs/contributing/deployment.md) before acting.

1. Use a clean dedicated worktree fixed at the candidate SHA.
2. Run `task -t .config/Taskfile.yml release:plan -- [--version vX.Y.Z] [--ref <sha>] [--base <previous-tag>] [--pr <N>]...` to classify the candidate. Without `--version` the plan still reports `latest_tag` / `next_patch` / `next_minor`. Repeat `--pr` to classify only those pull requests' changed files (the union); when `--base` is also given, classification uses the PR files while the wrangler comparison uses `--base`.
3. Immediately before tag push, remote migration, secrets, or Worker deployment, obtain explicit user authorization. Use `--execute` only after that authorization.
4. Use `task -t .config/Taskfile.yml release:create -- --version vX.Y.Z --ref HEAD --execute` to tag the checked-out release commit. For Worker changes, use `task -t .config/Taskfile.yml deploy:release -- --tag vX.Y.Z --execute` from that tag's worktree.
5. Record the target SHA, deployment decision, migration check, Worker version, and smoke result in GitHub Release Notes.

Do not deploy Release-only changes. Do not use a dirty worktree or tag a ref other than the checked-out release commit.
