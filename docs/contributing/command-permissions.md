---
codd:
  node_id: design:command-permissions
  type: design
  status: draft
  depends_on:
    - id: req:yoriwake-system
      relation: depends_on
      semantic: governance
---

# Command Permissions

Yoriwake defines repository-local command permission rules for LLM-assisted
work in `.codex/rules/yoriwake.rules`.

## Policy

- Allow safe read, investigation, validation, GitHub issue/PR, and normal
  branch publishing commands used by Yoriwake workflows.
- Forbid secret access, destructive file operations, destructive Git commands,
  and broad privilege changes.
- Require human approval for commands that are not explicitly covered by the
  allow or forbidden rules.

## Allowed Areas

- Read-only shell and file metadata inspection.
- Read-only Git inspection.
- Normal issue branch creation, commit, and upstream push.
- GitHub issue, pull request, run, repository, and authentication status
  inspection.
- Local validation through aqua, uv, and CoDD.

## Forbidden Areas

- Reading environment files, local GitHub credentials, or SSH material.
- Destructive file deletion patterns.
- Force pushing, hard resets, workspace restores, and Git clean operations.
- `sudo`, recursive chmod, and recursive chown.

## Rule File

The rule file uses `prefix_rule` entries:

```text
prefix_rule(pattern=["gh", "pr", "view"], decision="allow")
prefix_rule(pattern=["git", "reset", "--hard"], decision="forbidden")
```

Undefined commands must remain case-by-case so the assistant does not gain
unbounded command access by accident.
