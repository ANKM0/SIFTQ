---
codd:
  node_id: design:issue-execution
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
    - id: design:agent-roles
      relation: depends_on
      semantic: workflow
    - id: design:branch-strategy
      relation: depends_on
      semantic: workflow
    - id: design:commit-message-format
      relation: depends_on
      semantic: workflow
---

# Issue Execution

SIFTQ executes issue work through role-based agents. The workflow starts from
a GitHub issue with AC and DoD, then proceeds through planning, implementation,
adversarial review, verification, commit, push, and draft pull request creation.

## Workflow

1. Receive a GitHub issue URL or issue number.
2. Read the issue title, body, AC, DoD, labels, and state.
3. Follow the label-driven state machine.
4. Clarify scope, AC, DoD, and split points with `issue-designer-agent`.
5. Wait for human approval before implementation.
6. Update `main`.
7. Create a branch using the repository branch strategy.
8. Produce a short implementation plan.
9. Implement the approved scope with `implementation-agent`.
10. Review the implementation with `review-agent`.
11. Repeat the implementation-review-fix loop until no non-low findings remain.
12. Run required verification commands.
13. Commit with the repository commit message format.
14. Push the branch.
15. Open a draft pull request targeting `main`.

## Label State Machine

Use labels to trigger and gate issue execution:

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

Use `agent:blocked` when the agent cannot continue because scope is unclear,
checks fail for unclear reasons, permissions are missing, or repeated non-low
review findings remain unresolved.

`agent:design-ready` to `agent:approved` is a human review gate. Agents must not
approve their own design proposals.

Implementation must not start unless `agent:approved` is present.

## Label Triggers

- `agent:needs-design`: run the design phase and post or prepare a design
  proposal.
- `agent:approved`: run implementation through draft PR creation.
- `agent:blocked`: stop automated work until a human resolves the blocker.
- `agent:pr-created`: mark that a pull request has been created.

## Implementation Review Loop

The review loop is mandatory before commit and pull request creation.

1. `implementation-agent` implements the approved plan.
2. `review-agent` performs adversarial review.
3. `review-agent` classifies every finding as `critical`, `high`, `medium`, or
   `low`.
4. `implementation-agent` fixes all `critical`, `high`, and `medium` findings
   unless the coordinator marks a finding out of scope or blocked.
5. `review-agent` reviews the fixes.
6. The coordinator repeats the loop until no `critical`, `high`, or `medium`
   findings remain.

`low` findings may be documented as follow-up unless they are trivial and
clearly in scope.

Escalate to the user when a fix would expand scope, requirements are ambiguous,
or required checks fail for unclear or environment-specific reasons.

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

## Pull Requests

Open draft pull requests by default. The PR body should follow the repository PR
template and include:

- Summary.
- Changes made.
- Out-of-scope items.
- Verification results.
- Impact.
- Review focus.

Include `Closes #<issue>` only when `review-agent` confirms the issue can be
closed by merge. Do not directly close issues by default.

## Hooks

Hooks are safety nets, not replacements for agents.

Good hook uses:

- formatting
- lightweight validation
- pre-push CoDD validation
- CI verification

Hooks should not interpret AC or DoD, plan implementation, edit code, judge
acceptance, or create pull requests.

## Workflow File

The execution-oriented workflow lives at:

```text
.agents/workflows/issue-execution.md
```
