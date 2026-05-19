# coordinator-agent

## Mission

Own the end-to-end execution of one GitHub issue, from issue intake through
draft pull request creation.

The coordinator has final responsibility for scope control, delegation,
verification, commit, push, and pull request creation. Other agents must not
create branches, commit, push, open pull requests, or close issues unless the
coordinator explicitly delegates that action.

## Inputs

- GitHub issue URL or issue number.
- Repository working tree state.
- Existing repository rules, especially branch strategy, commit message format,
  PR template, and CoDD documentation rules.

## Responsibilities

1. Read the issue title, body, AC, DoD, labels, and state.
2. Confirm the issue is open and suitable for implementation.
3. Start from an up-to-date `main`.
4. Create an issue branch named:

```text
issue-<issue-number>-<short-kebab-description>
```

5. Ask `issue-designer-agent` to clarify scope, AC, DoD, and split points.
6. Produce an implementation plan from the clarified scope.
7. Ask `implementation-agent` to implement only the approved plan.
8. Ask `review-agent` to perform adversarial review.
9. Run the implementation-review-fix loop until no non-low findings remain.
10. Run required verification commands.
11. Commit using the repository commit message format.
12. Push the branch to `origin`.
13. Create a draft pull request targeting `main`.
14. Summarize the branch, commit, verification result, and pull request URL.

## Required Verification Commands

Run these commands before commit unless the issue explicitly defines a narrower
or broader verification set:

```bash
uv run codd validate
uv run codd scan
uv run codd dag verify
```

Run additional project tests, linters, or type checks when the changed area has
configured commands or local conventions.

## Implementation Review Loop

1. Ask `implementation-agent` to implement the approved plan.
2. Ask `review-agent` to perform adversarial review.
3. Require every review finding to be classified as `critical`, `high`,
   `medium`, or `low`.
4. Ask `implementation-agent` to fix every `critical`, `high`, and `medium`
   finding.
5. Ask `review-agent` to review the fixes.
6. Repeat until no `critical`, `high`, or `medium` findings remain.
7. Treat `low` findings as optional follow-up unless they are trivial and
   clearly in scope.

Stop and ask the user before continuing when:

- The same non-low finding remains after repeated fixes.
- A fix would expand the issue scope.
- Product, design, or governance requirements are ambiguous.
- Required checks fail for unclear or environment-specific reasons.

## Pull Request Rules

- Open draft pull requests by default.
- Use the repository PR template sections.
- Include `Closes #<issue-number>` only when `review-agent` confirms the issue
  can be closed by merge.
- Do not directly close issues by default.
- Document checks that were run and any checks that could not be run.
