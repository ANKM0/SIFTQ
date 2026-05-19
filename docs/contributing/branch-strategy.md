---
codd:
  node_id: design:branch-strategy
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:branch-strategy-adr
      relation: depends_on
      semantic: decision
  depended_by:
    - id: design:issue-execution
      relation: depends_on
      semantic: workflow
---

# Branch Strategy

SIFTQ uses short-lived issue branches created from `main`. Completed work is
merged back into `main` through pull requests after review and required checks.

## Flow

1. Update `main`.
2. Create a branch for one GitHub issue.
3. Implement and commit focused changes on that branch.
4. Push the branch to `origin`.
5. Open a pull request targeting `main`.
6. Merge the pull request after review and checks pass.
7. Delete the branch after merge unless it is still needed for follow-up work.

## Branch Names

Use this format:

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

After committing:

```bash
git push -u origin "$(git branch --show-current)"
```

## Rules

- Do not commit directly to `main` for issue work.
- Keep one issue's work in one branch unless the issue is split intentionally.
- Keep branch names lowercase and hyphenated.
- Use the repository commit message format documented in
  `docs/contributing/commit-message-format.md`.

## Agent Skill

The repository-local Codex skill for this convention is
`.agents/skills/branch-strategy/SKILL.md`.
