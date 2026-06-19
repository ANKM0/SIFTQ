---
name: siftq-issue-creator
description: Create or draft SIFTQ GitHub issues (feature, bug, or research) with AC/DoD templates and sympohy-compatible labels.
---

# SIFTQ Issue Creator

Use this skill when asked to create or draft a GitHub issue for `ANKM0/SIFTQ`.

## 1) Issue creation workflow

1. Select the template type:
   - Feature change
   - Bug
   - Research
2. Generate title, background, scope, AC, DoD, and verification notes.
3. Fill in placeholders in the selected template.
4. Confirm labels and run `gh issue create`.

## 2) Label rule (this repository)

For issues intended to run through sympohy automation:

- Add `sympohy:pending`
- Add `sympohy:phase:triage`

Do not add the following manually:

- `sympohy:blocked`
- `sympohy:done`

These are set by workflow automation.

If repository has additional project labels, include them as optional context labels.

## 3) Required output format

Return these exact fields:

- `title`
- `labels` list
- complete issue body text
- exact `gh issue create` command

## 4) References

- [issue templates](references/issue-templates.md)
- [label policy](references/issue-label-policy.md)
