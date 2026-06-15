# SIFTQ Issue Templates

Use these templates when drafting or creating SIFTQ GitHub issues. Remove
instructional placeholders before returning or submitting an issue.

## Feature Change

Use for implementation, documentation, workflow, tooling, or repository changes.

```markdown
## Background

<Why this change is needed, including current behavior, constraints, and related
context.>

## Summary

<What should change and what is intentionally out of scope.>

## AC

- [ ] <Reviewer-observable acceptance criterion.>
- [ ] <Another concrete acceptance criterion.>

## DoD

- [ ] <Required validation command, test, or inspection.>
- [ ] <Documentation, PR description, migration note, or follow-up requirement.>

## Additional Context

<Links, file paths, examples, risks, or follow-up issue ideas. Omit this section
when there is no useful context.>
```

## Research

Use for investigation work where the deliverable is a conclusion, comparison, or
recommendation rather than an implementation.

```markdown
## Background

<Why this research is needed and what decision or blocker it supports.>

## Questions

- <Question, option, or uncertainty to investigate.>
- <Another concrete research question.>

## Completion Criteria

- [ ] <The expected research artifact, decision record, summary, or recommendation.>
- [ ] <Validation, stakeholder review, or follow-up issue creation requirement.>
```

## Bug

Use for defects, regressions, failed workflows, broken UI behavior, or incorrect
automation behavior.

```markdown
## Summary

<What is broken, who is affected, and the observed impact.>

## Reproduction Steps

1. <First step to reproduce.>
2. <Second step to reproduce.>
3. <Observed result and expected result.>

## Cause(Optional)

<Known or suspected cause. Omit if unknown.>

## Proposed Fix(Optional)

<Suggested repair direction, validation command, or affected files. Omit if
unknown.>
```

## Template Selection Notes

- Choose Feature Change when the issue will be implemented by `sympohy`; include
  both `## AC` and `## DoD`.
- Choose Research when the next step is discovery and the issue should close on
  a written finding, ADR, design note, or follow-up issue set.
- Choose Bug when the request starts from observed incorrect behavior. If the
  fix is already clear and needs AC/DoD for automation, use Feature Change
  instead and include the bug details in Background.
