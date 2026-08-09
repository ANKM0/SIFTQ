---
name: issue-creator
description: Create or draft SIFTQ GitHub issues (feature, bug, or research) with AC/DoD templates and optional taqt activation labels.
---

# SIFTQ Issue Creator

Use this skill when asked to create or draft a GitHub issue for `ANKM0/SIFTQ`.

## 1) Issue creation workflow

1. Read `docs/contributing/issue.md`.
2. Select the template type:
   - Feature change
   - Bug
   - Research
3. Draft title, body, AC, DoD.
4. Confirm taqt target.
5. Review scope, AC/DoD, split need.
6. Use `scripts/create_issue.py` for template, body file, labels, and
   `gh issue create --body-file`.

Default dry-run:

```bash
uv run python scripts/create_issue.py \
  --type feature \
  --title "..." \
  --label area:docs \
  --dry-run
```

For drafted body, pass `--body-source <path>`.

Use `--execute` only after final user confirmation.

## 2) Label rule (this repository)

New issues are not taqt targets by default.

Ask before taqt unless explicitly requested.

For taqt, pass `--taqt`; script adds:

- `taqt:pending`
- `taqt:phase:triage`

Script rejects:

- `taqt:blocked`
- `taqt:running`
- `taqt:done`

Automation sets these.

Pass optional labels with repeated `--label`.

## 3) Required output format

Return these exact fields:

- `title`
- `labels` list
- complete issue body text
- exact `gh issue create` command

## 4) References

- [issue guide](../../../docs/contributing/issue.md)
- Canonical issue templates: `.github/ISSUE_TEMPLATE/*.md`
- [label policy](references/issue-label-policy.md)
