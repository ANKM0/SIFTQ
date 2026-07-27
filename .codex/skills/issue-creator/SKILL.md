---
name: siftq-issue-creator
description: Create or draft SIFTQ GitHub issues (feature, bug, or research) with AC/DoD templates and optional taqt activation labels.
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

Do not make a newly created issue a taqt automation target by default.

Add taqt labels only when the user explicitly asks for taqt automation, or when
the issue is already intended to be picked up by a taqt watcher.

For explicit taqt targets:

- Add `taqt:pending`
- Add `taqt:phase:triage`

Do not add the following manually:

- `taqt:blocked`
- `taqt:running`
- `taqt:done`

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
