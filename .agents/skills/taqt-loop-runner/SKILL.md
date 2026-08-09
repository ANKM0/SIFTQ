---
name: taqt-loop-runner
description: Run SIFTQ taqt loop-engineering tasks from GitHub Issues through readiness, decomposition, worktree execution, PR, merge, cleanup, and self-improvement follow-up.
---

# taqt Loop Runner

Use this skill when running or supervising taqt tasks for SIFTQ issues.

## References

1. Read the issue body and comments. Do not start implementation unless the issue has the required readiness sections.
2. Read `.agents/skills/self-improvement/SKILL.md` before acting on taqt self-improvement requests.

## Operating Policy

- Use GitHub Issue AC/DoD as the source of implementation readiness.
- Do not start implementation when required issue sections are missing.
- Keep task slices close to five minutes of work when an issue contains multiple independent bullets.
- Run each task in its own git worktree when parallel execution is possible.
- Prefer the smallest meaningful validation first, then broader gates as needed.
- Route unclear requirements, product decisions, repeated failures, and max-attempt exits to human triage.
- Create a self-improvement request when a taqt event reveals a reusable operational lesson.

## Readiness

- Feature issues require `## AC` and `## DoD`.
- Research issues require `## 調べたいこと` and `## 完了条件`.
- Bug issues require `## 概要`; missing `## 再現手順` is a warning first.
- If readiness is missing, run no implementation. Keep the task in `pending`, set `phase: triage`, and report the exact missing section such as `missing issue section: AC`.
- Human confirmation should ask for the missing sections or decision, not for generic permission.

## Standard Flow

1. Create or refresh the task:

```bash
task taqt:create -- --repo ANKM0/SIFTQ --issue <number> --priority high --branch-summary <lower_snake_summary>
```

2. Check whether the issue must be split into five-minute slices:

```bash
task taqt:decompose -- .taqt/tasks/ISSUE-<number>.yaml --execute
```

3. Create a task worktree and branch:

```bash
task taqt:worktree -- .taqt/tasks/ISSUE-<number>.yaml --execute
```

4. Run the task from the worktree:

```bash
task taqt:run -- /absolute/path/to/.taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number>
```

5. Sync status to GitHub when useful:

```bash
task taqt:sync -- .taqt/tasks/ISSUE-<number>.yaml --execute
```

6. Commit, push, and open PR after a verified run:

```bash
task taqt:commit -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --execute
task taqt:push -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --execute
task taqt:pr -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --execute
```

7. Merge and cleanup when checks, AC, and DoD are satisfied:

```bash
task taqt:merge -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --execute
task taqt:cleanup -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --mark-done --sync-parent --delete-local-branch --force-worktree --execute
```

8. Use `task taqt:report -- <run-dir>` to summarize a run.

## Parallel Worker

Use the worker when multiple ready tasks can run independently:

```bash
task taqt:worker -- --jobs 2 --limit 2 --execute
```

Each task gets a separate worktree under `.taqt/worktrees/`. Do not run tasks in parallel when they touch the same high-conflict files unless the split explicitly allows it.

## Auto Route

Use `taqt:auto` only after the task is ready and the selected workspace is correct:

```bash
task taqt:auto -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --execute
```

For merge and cleanup routing:

```bash
task taqt:auto -- .taqt/tasks/ISSUE-<number>.yaml --workspace .taqt/worktrees/ISSUE-<number> --merge --cleanup-worktree --delete-local-branch --force-worktree --execute
```

## Human Escalation And Self-Improvement

- If taqt records `self_improvement` in the task, read the generated request file and then use `.agents/skills/self-improvement/SKILL.md`.
- Log to `.learnings/` only when the event is recurring, non-obvious, or useful for future automation.
- Useful self-improvement events include readiness false positives, repeated GitHub API failures, worktree cleanup failures, max iteration exits, and unclear human escalation reasons.
- Do not log routine product decisions or one-off missing AC/DoD unless the pattern recurs.
