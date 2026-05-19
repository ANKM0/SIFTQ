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
3. Coordinator follows the label-driven state machine.
4. Issue designer clarifies scope, AC, DoD, and expected changed areas when the
   issue has `agent:needs-design`.
5. Human review moves the issue from `agent:design-ready` to `agent:approved`.
6. Coordinator updates `main` and creates an issue branch using the repository
   branch strategy.
7. Coordinator creates a short implementation plan.
8. Implementation agent implements the approved plan.
9. Review agent performs adversarial review and classifies findings.
10. Coordinator repeats the implementation-review-fix loop until no non-low
   findings remain.
11. Coordinator runs required verification commands.
12. Coordinator performs a final status check.
13. Coordinator commits with the repository commit message format.
14. Coordinator pushes the branch.
15. Coordinator opens a draft pull request targeting `main`.
16. Coordinator summarizes the result.

## Label State Machine

Use labels to trigger and gate agent work:

```text
agent:needs-design
  -> issue-designer-agent creates a design proposal
  -> agent:design-ready
  -> human review
  -> agent:approved
  -> coordinator-agent starts implementation
  -> agent:running
  -> draft PR created
  -> agent:pr-created
```

Blocked work moves to:

```text
agent:blocked
```

The transition from `agent:design-ready` to `agent:approved` is human-owned.
Agents must not approve their own design proposals.

## Label Triggers

- `agent:needs-design`: run the design phase only.
- `agent:approved`: run implementation through draft PR creation.
- `agent:blocked`: stop automated work until a human resolves the blocker.
- `agent:pr-created`: no further automated work is required by this workflow.

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
task codd:validate
task codd:scan
task codd:dag
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
