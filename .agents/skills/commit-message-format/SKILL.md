---
name: commit-message-format
description: Format Git commit messages for this repository with a GitHub issue number followed by a Conventional Commits header. Use when creating, reviewing, rewriting, or suggesting commit messages for SIFTQ changes.
---

# Commit Message Format

## Overview

Use this skill whenever a SIFTQ change needs a commit message. The required
format keeps each commit traceable to a GitHub issue while preserving
Conventional Commits semantics.

## Required Format

```text
#<issue-number> <type>[optional scope][!]: <summary>
```

Examples:

```text
#8 docs: document commit message format
#8 feat(codd): add graph verification command
#8 fix!: rename incompatible config key
```

## Rules

- Start with the GitHub issue number as `#<number>`.
- Add one space after the issue number.
- Use a Conventional Commits type such as `feat`, `fix`, `docs`, `test`,
  `refactor`, `chore`, `ci`, `build`, `perf`, or `style`.
- Add an optional scope in parentheses when it clarifies the touched area.
- Add `!` before the colon only for breaking changes.
- Write a concise imperative summary after `: `.
- Keep the first line focused on one logical change.
- Add a body only when the reason, tradeoff, or migration note is not clear
  from the summary.

## Workflow

1. Identify the issue number for the work before committing.
2. Choose the Conventional Commits type that matches the primary change.
3. Add a scope if the repository area is clear and useful.
4. Write the summary in imperative mood, without a trailing period.
5. Check the final header against the required format before running
   `git commit`.

## Common Choices

- Documentation-only change: `#8 docs: add commit message guide`
- Tooling or dependency maintenance: `#8 chore(deps): update uv lockfile`
- CI workflow change: `#8 ci: verify codd graph on pull requests`
- Bug fix: `#8 fix(codd): preserve scanned node ids`
