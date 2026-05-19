---
name: branch-strategy
description: Follow the Yoriwake branch strategy for GitHub issue work. Use when creating, reviewing, naming, updating, pushing, or merging branches for Yoriwake changes.
---

# Branch Strategy

## Overview

Use this skill whenever Yoriwake work needs a Git branch. The repository uses
short-lived issue branches from `main`, reviewed through pull requests, then
merged back to `main` after checks pass.

## Required Flow

1. Start from an up-to-date `main`.
2. Create one branch per GitHub issue.
3. Commit focused changes on that issue branch.
4. Push the branch and open a pull request targeting `main`.
5. Merge into `main` only after review and required checks pass.
6. Delete the issue branch after merge unless follow-up work still depends on
   it.

## Branch Naming

Use:

```text
issue-<issue-number>-<short-kebab-description>
```

Examples:

```text
issue-11-branch-strategy-docs-skills
issue-8-commit-format-docs-skills
```

## Commands

```bash
git switch main
git pull --ff-only
git switch -c issue-<issue-number>-<short-kebab-description>
```

Push the branch with upstream tracking:

```bash
git push -u origin "$(git branch --show-current)"
```

## Rules

- Do not commit directly to `main` for issue work.
- Do not mix unrelated issues in one branch.
- Rebase or merge from `main` only when needed to resolve drift before review.
- Keep branch names lowercase and hyphenated.
- Use the commit message format in `.agents/skills/commit-message-format/`.
