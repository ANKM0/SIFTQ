---
name: issue-implementation
description: Implement SIFTQ GitHub issues using repository-local workflow docs. Use when Codex is asked to implement, resume, validate, commit, push, or open a PR for a SIFTQ issue branch.
---

# Issue Implementation

## Overview

Use this skill for SIFTQ issue work. It keeps implementation agents pointed at
the canonical contributing docs instead of duplicating branch or commit rules in
skill text.

## Required References

Read the applicable source documents before making workflow decisions:

- `docs/contributing/branch-strategy.md` for branch naming, branch flow, push,
  and pull request target rules.
- `docs/contributing/commit-message-format.md` for commit message format.
- `docs/contributing/issue-execution.md` when working through a sympohy-managed
  issue or validating runner behavior.

If these documents and a request disagree, follow the user's latest explicit
instruction only after calling out the repository-rule mismatch.

## Workflow

1. Inspect the issue body and latest comments for scope, AC, DoD, and
   validation commands.
2. Check the local branch and worktree before editing. Preserve unrelated user
   changes.
3. Implement only the issue scope, keeping branch and commit decisions aligned
   with the contributing docs.
4. Run the issue-specific validation first, then the relevant repository checks.
5. Commit with the required issue-prefixed Conventional Commits format.
6. Push the issue branch and open a pull request targeting `main` when the
   branch is ready for review.

## Validation

Prefer validation commands named in the issue DoD. For issue branches that
change docs, skills, or sympohy behavior, also run `task ci` unless the issue or
user explicitly narrows validation.

When opening a pull request, include the validation commands and results in the
PR body and add the appropriate closing keyword for the issue.

## Repository Boundaries

- Keep branch strategy and commit message rule text in `docs/contributing/`.
- Do not recreate dedicated branch-strategy or commit-message-format skills.
- Update this skill only when implementation agents need different routing or
  workflow guidance.
