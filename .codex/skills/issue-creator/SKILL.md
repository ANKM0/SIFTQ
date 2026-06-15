---
name: issue-creator
description: Create SIFTQ GitHub issues from rough requests using the repository's Feature Change, Research, or Bug templates. Use when Codex needs to draft or create an issue for ANKM0/SIFTQ with complete AC/DoD, sympohy queue labels, and repository-local issue wording.
---

# Issue Creator

Use this skill to turn a rough SIFTQ request into a GitHub issue that is ready
for human review or `sympohy` execution.

## Workflow

1. Classify the request as one of:
   - Feature Change: implementation, documentation, workflow, or repository
     changes that need acceptance criteria and a definition of done.
   - Research: investigation, comparison, design exploration, or spike work.
   - Bug: a reported defect, regression, failing behavior, or broken workflow.
2. Read [issue templates](references/issue-templates.md) and choose the matching
   body template.
3. Read [issue label policy](references/issue-label-policy.md) before assigning
   labels.
4. Draft a concise title in Japanese when the surrounding issue context is
   Japanese. Keep command names, labels, paths, and issue references in their
   conventional form.
5. Fill every required section with concrete, testable content. Do not leave
   placeholder comments in the issue body.
6. For Feature Change issues, include both `## AC` and `## DoD` with checklist
   items. `sympohy` requires a complete AC/DoD set before implementation.
7. Add links to relevant files, docs, PRs, or prior issues when they materially
   constrain the work.
8. If creating the issue through GitHub, apply only the manual queue labels from
   the label policy. Do not apply automation-owned status labels.

## Output Format

When the user asks for a draft, return:

```text
Title: <issue title>
Labels: sympohy:pending, sympohy:phase:triage

<issue body>
```

When the user asks to create the issue, create it with `gh issue create` or the
available GitHub tool after confirming any missing facts that would change the
scope, labels, or acceptance criteria.

## Quality Bar

- Keep the issue independently actionable from its title and body.
- Make AC user- or reviewer-observable, not implementation task lists.
- Make DoD cover validation, documentation, PR notes, and any operational
  follow-up needed to close the issue.
- Prefer narrow issues. Split unrelated work into follow-up issue drafts rather
  than mixing multiple changes in one ticket.
- Preserve existing repository terminology: `SIFTQ`, `sympohy`, `AC`, `DoD`,
  `task ci`, and exact file paths.
