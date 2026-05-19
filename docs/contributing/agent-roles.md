---
codd:
  node_id: design:agent-roles
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:issue-execution
      relation: depends_on
      semantic: workflow
---

# Agent Roles

SIFTQ uses role-based agents for issue execution. Agents define operational
responsibilities, while CoDD-managed documents define the repository governance
and workflow expectations.

## Roles

### coordinator-agent

The coordinator owns the full issue workflow and final responsibility.

Responsibilities:

- Read the issue URL or issue number.
- Read AC and DoD.
- Update `main` and create the issue branch.
- Delegate issue clarification to `issue-designer-agent`.
- Delegate scoped implementation to `implementation-agent`.
- Delegate adversarial review to `review-agent`.
- Enforce label-driven gates before design and implementation.
- Run the implementation-review-fix loop until no non-low findings remain.
- Run required verification commands.
- Commit, push, and open a draft pull request.

### issue-designer-agent

The issue designer owns issue shape and implementation readiness.

Responsibilities:

- Clarify background, summary, scope, AC, and DoD.
- Identify out-of-scope items.
- Decide whether the work should be split into multiple issues.
- Identify affected areas such as code, tests, docs, agents, hooks, GitHub
  workflows, or CoDD-managed documents.
- Create or update GitHub issues when requested.
- Produce a design proposal when `agent:needs-design` is applied.
- Mark or request `agent:design-ready` after the design proposal is ready.
- Never mark its own design as `agent:approved`.

### implementation-agent

The implementation agent owns scoped changes.

Responsibilities:

- Implement only the approved scope.
- Follow existing repository patterns.
- Update code, tests, docs, agents, or configuration as required.
- Avoid unrelated refactors.
- Fix all `critical`, `high`, and `medium` review findings unless the
  coordinator marks a finding out of scope or blocked.
- Treat `low` findings as optional unless they are trivial and clearly in scope.

### review-agent

The review agent owns pre-PR review and acceptance judgment.

Responsibilities:

- Check AC and DoD satisfaction.
- Perform adversarial review.
- Classify findings as `critical`, `high`, `medium`, or `low`.
- Check diff scope, tests, docs, CoDD frontmatter, and reverse links.
- Confirm whether the PR body should include `Closes #<issue>`.

## Severity

- `critical`: data loss, security issue, broken core workflow, or checks that
  cannot run.
- `high`: AC or DoD is not satisfied, major behavior regression, or required
  validation is missing.
- `medium`: likely bug, incomplete edge case, missing test for changed behavior,
  or CoDD inconsistency.
- `low`: style, naming, minor documentation polish, or optional cleanup.

## Boundaries

Only the coordinator should create branches, commit, push, open pull requests,
or close issues by default. Other agents can recommend those actions but should
not perform them unless the coordinator explicitly delegates the action.

The transition from `agent:design-ready` to `agent:approved` is human-owned.
Agents can propose designs, but they must not approve their own design proposals.

Issue close should normally happen through pull request merge automation. Use
`Closes #<issue>` only after review confirms the issue can be closed by merge.

## Labels

Use these labels to trigger and gate agent work:

- `agent:needs-design`: run the design phase.
- `agent:design-ready`: design proposal is ready for human review.
- `agent:approved`: human-approved design; implementation may start.
- `agent:running`: agent work is currently running.
- `agent:blocked`: agent work is blocked and needs human input.
- `agent:pr-created`: the agent created a pull request.

## Agent Files

Role definitions live under:

```text
.agents/agents/
```

These files are execution-oriented role specs and remain outside the CoDD scan
surface. CoDD-managed governance for these roles lives in this document.
