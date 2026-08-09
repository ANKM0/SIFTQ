# Loop Engineering

Loop engineering is the SIFTQ workflow for moving GitHub Issues through small, verifiable automation steps using taqt.

## Policy

- Use GitHub Issue AC/DoD as the source of implementation readiness.
- Do not start implementation when required issue sections are missing.
- Keep task slices close to five minutes of work when an issue contains multiple independent bullets.
- Run each task in its own git worktree when parallel execution is possible.
- Prefer the smallest meaningful validation first, then broader gates as needed.
- Route unclear requirements, product decisions, repeated failures, and max-attempt exits to human triage.
- Create a self-improvement request when a taqt event reveals a reusable operational lesson.

## Readiness Rules

- Feature: `## AC` and `## DoD` are required.
- Research: `## 調べたいこと` and `## 完了条件` are required.
- Bug: `## 概要` is required. Missing `## 再現手順` starts as a warning.

## Operating Notes

- `task taqt:create` creates or refreshes a local task from an issue.
- `task taqt:decompose` splits a ready task into small child tasks.
- `task taqt:worktree` creates the issue branch and worktree.
- `task taqt:run` runs the configured feedback loop.
- `task taqt:worker` runs multiple ready tasks with one worktree per task.
- `task taqt:sync` syncs task state back to GitHub.
- `task taqt:commit`, `task taqt:push`, and `task taqt:pr` route verified changes toward review.
- `task taqt:merge` merges the PR after checks and review criteria are satisfied.
- `task taqt:cleanup` removes worktrees and synchronizes parent/child task completion.
