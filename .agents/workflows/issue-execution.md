# Issue Execution Workflow

## Purpose

Use role-based agents to execute one GitHub issue from AC/DoD through draft pull
request creation.

## Roles

- `coordinator-agent`: orchestrates the workflow and owns final responsibility.
- `issue-designer-agent`: clarifies issue scope, AC, DoD, and split points.
- `implementation-agent`: implements approved changes.
- `review-agent`: performs adversarial review and acceptance judgment.

## Flow

1. Coordinator receives a GitHub issue URL or issue number.
2. Coordinator reads the issue title, body, AC, DoD, labels, and state.
3. Issue designer clarifies scope, AC, DoD, and expected changed areas.
4. Coordinator updates `main` and creates an issue branch using the repository
   branch strategy.
5. Coordinator creates a short implementation plan.
6. Implementation agent implements the approved plan.
7. Review agent performs adversarial review and classifies findings.
8. Coordinator repeats the implementation-review-fix loop until no non-low
   findings remain.
9. Coordinator runs required verification commands.
10. Coordinator performs a final status check.
11. Coordinator commits with the repository commit message format.
12. Coordinator pushes the branch.
13. Coordinator opens a draft pull request targeting `main`.
14. Coordinator summarizes the result.

## Implementation Review Loop

The review loop is mandatory before commit and pull request creation.

1. Implementation agent makes the approved changes.
2. Review agent classifies findings as `critical`, `high`, `medium`, or `low`.
3. Implementation agent fixes all `critical`, `high`, and `medium` findings
   unless the coordinator marks a finding out of scope or blocked.
4. Review agent reviews the fixes.
5. Coordinator repeats the loop until the review result is `PASS`.

`low` findings may be documented as follow-up unless they are trivial and
clearly in scope.

## Required Verification

Run these commands for repository workflow, docs, agents, and CoDD-related
changes:

```bash
uv run codd validate
uv run codd scan
uv run codd dag verify
```

Run additional tests, linters, or type checks when the changed area has
configured commands.

## Pull Request

Open a draft pull request targeting `main`.

The pull request body must include:

- Summary.
- Changes made.
- Out-of-scope items.
- Verification results.
- Impact.
- Review focus.

Include `Closes #<issue-number>` only when review confirms the issue can be
closed by merge.

## Hooks

Hooks are safety nets, not replacements for agents.

Good hook uses:

- formatting
- lightweight validation
- pre-push CoDD validation
- CI verification

Do not use hooks for AC/DoD interpretation, implementation planning, code
editing, acceptance judgment, or pull request creation.
