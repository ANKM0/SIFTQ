---
name: release-deployment
description: Plan and execute SIFTQ GitHub releases and Cloudflare Workers deployments using the repository release tasks.
---

# Release and Deployment

Read [ADR 0034](../../../docs/adr/0034-separate-release-and-worker-deployment.md), [Release](../../../docs/contributing/release.md), and [deployment](../../../docs/contributing/deployment.md) before acting.

1. Use a clean dedicated worktree fixed at the candidate SHA.
2. Run `task release:plan -- --version vX.Y.Z --ref <sha> --base <previous-tag>` to classify the candidate.
3. For a version change, run `task release:version -- --version vX.Y.Z --execute`, review and commit the result, then rerun the plan against the release commit.
4. Immediately before tag push, remote migration, secrets, or Worker deployment, obtain explicit user authorization. Use `--execute` only after that authorization.
5. Use `task release:create -- --version vX.Y.Z --ref HEAD --execute` to tag the checked-out release commit. For Worker changes, use `task deploy:release -- --tag vX.Y.Z --execute` from that tag's worktree.
6. Record the target SHA, deployment decision, migration check, Worker version, and smoke result in GitHub Release Notes.

Do not deploy Release-only changes. Do not use a dirty worktree or tag a ref other than the checked-out release commit.
