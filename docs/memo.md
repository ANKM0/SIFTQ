---
codd:
  node_id: design:agents-design-memo
  type: design
  status: draft
  depends_on:
    - id: req:yoriwake-system
      relation: depends_on
      semantic: governance
---

# Agents Design Memo

## Direction

Use role-specific agents rather than modeling this only as skills.

Target roles:

- `coordinator-agent`
- `issue-designer-agent`
- `implementation-agent`
- `review-agent`

The coordinator owns the workflow and final responsibility. Other agents should
not independently create branches, commit, push, create pull requests, or close
issues unless the coordinator explicitly delegates that action.

## Role Responsibilities

### coordinator-agent

The coordinator is the orchestrator for issue work.

Responsibilities:

- Accept an issue URL or issue number.
- Read the issue body, including AC and DoD.
- Update `main` and create the issue branch.
- Ask the issue designer to clarify scope, AC, DoD, and split points.
- Ask the implementation agent to make scoped code, test, or docs changes.
- Ask the review agent to evaluate the diff, AC, DoD, and verification result.
- Run the implementation-review-fix loop until no non-low review findings
  remain.
- Run required verification commands.
- Commit with the repository commit message format.
- Push the branch.
- Create a draft pull request targeting `main`.
- Summarize the branch, commit, checks, and pull request URL.

### issue-designer-agent

The issue designer owns issue creation and issue shape.

Responsibilities:

- Clarify background, summary, scope, AC, and DoD.
- Decide whether the work should be split into multiple issues.
- Identify whether the work affects code, tests, docs, agents, hooks, GitHub
  workflows, or CoDD-managed documentation.
- Define expected files or areas when that helps implementation.
- Create or update GitHub issues when requested.

### implementation-agent

The implementation agent owns scoped changes.

Responsibilities:

- Implement only the approved scope.
- Follow existing repository patterns.
- Update code, tests, docs, agents, or configuration as required by the issue.
- Avoid unrelated refactors.
- Fix all critical, high, and medium review findings unless the coordinator
  explicitly marks a finding as out of scope or blocked.
- Do not fix low findings unless they are trivial and clearly in scope.
- Run focused checks when useful before handing work back to the coordinator.
- Report changed files, verification commands, and any blockers.

### review-agent

The review agent owns pre-PR review and acceptance judgment.

Responsibilities:

- Check whether AC is satisfied.
- Check whether DoD is satisfied.
- Perform adversarial review by looking for reasons the change should not
  merge.
- Classify findings as `critical`, `high`, `medium`, or `low`.
- Review the diff for unrelated changes or missing tests.
- Check CoDD frontmatter, reverse links, and validation impact when docs are
  changed.
- Check whether the PR body should include `Closes #<issue>`.
- Report remaining risks or gaps before the coordinator creates the PR.

## Implementation Review Loop

The coordinator must run an implementation-review-fix loop before committing and
creating a pull request.

Loop:

1. Ask the implementation agent to implement the approved plan.
2. Ask the review agent to perform adversarial review.
3. Require the review agent to classify every finding by severity.
4. Ask the implementation agent to fix all `critical`, `high`, and `medium`
   findings.
5. Repeat review after fixes.
6. Continue until no `critical`, `high`, or `medium` findings remain.
7. Treat `low` findings as optional follow-up unless they are trivial and
   clearly in scope.

Severity:

- `critical`: data loss, security issue, broken core workflow, or checks that
  cannot run.
- `high`: AC or DoD is not satisfied, major behavior regression, or required
  validation is missing.
- `medium`: likely bug, incomplete edge case, missing test for changed behavior,
  or CoDD inconsistency.
- `low`: style, naming, minor documentation polish, or optional cleanup.

Escalate to the user instead of continuing automatically when:

- The same non-low finding remains after repeated fixes.
- The fix would expand the issue scope.
- The review reveals ambiguous product, design, or governance requirements.
- Required checks fail for unclear or environment-specific reasons.

## Issue Closing

Do not create a dedicated close agent for now.

Issue close should normally happen through pull request merge automation, using
`Closes #<issue>` in the PR body when the review agent confirms the issue can be
closed.

Agents should judge whether an issue is ready to close, but should not directly
close issues by default.

## Repository Layout Idea

Possible layout:

```text
.agents/
  agents/
    coordinator.md
    issue-designer.md
    implementation.md
    review.md
  workflows/
    issue-execution.md
```

Alternative:

```text
.agents/
  roles/
    coordinator.md
    issue-designer.md
    implementation.md
    review.md
```

The first option is clearer if these are treated as agents. The second option is
clearer if they are treated as role specifications used by a workflow.

## CoDD Relationship

`.agents/` should remain execution-oriented and outside the CoDD scan surface.

CoDD-managed design and governance documents should live under `docs/`, for
example:

```text
docs/contributing/agent-roles.md
docs/contributing/issue-execution.md
```

Those docs should use CoDD frontmatter and be linked from
`docs/requirements/system-requirements.md`.

## Hooks Relationship

Hooks are safety nets, not replacements for agents.

Good hook use cases:

- pre-commit formatting or lightweight validation
- pre-push `uv run codd validate`
- CI verification with CoDD commands

Bad hook use cases:

- reading AC or DoD
- deciding issue scope
- planning implementation
- editing code
- judging whether the issue is complete
- creating pull requests

Those are agent responsibilities.

## Initial Implementation Scope

For the first implementation issue, create the role definitions and workflow
documentation, but keep direct automation conservative.

Suggested files:

```text
.agents/agents/coordinator.md
.agents/agents/issue-designer.md
.agents/agents/implementation.md
.agents/agents/review.md
docs/contributing/agent-roles.md
docs/contributing/issue-execution.md
```

Keep GitHub issue close behavior manual or PR-merge-driven. Use draft PRs by
default.
