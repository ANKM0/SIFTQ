---
name: self-improvement
description: Record reusable lessons from agent work into .learnings and promote repeated lessons into durable repository rules.
---

# Self Improvement

## Overview

Use this skill when a development session creates reusable learning for future
agents or contributors. Record low-friction learning as repository Markdown
under `.learnings/`; promote repeated learning into durable rules only after it
proves useful across tasks.

## When To Record

Record a learning when any of these happen:

- The user corrects an agent assumption or implementation direction.
- A command fails and the cause plus fix are discovered.
- A repository-specific best practice is found during work.
- A requested workflow does not exist yet and should be considered later.
- Existing knowledge is stale, incomplete, or wrong.

Do not record secrets, credentials, private user data, or speculative notes that
cannot be reviewed as a normal repository diff.

## Where To Record

- General learnings: `.learnings/LEARNINGS.md`
- Command or workflow failures: `.learnings/ERRORS.md`
- Missing workflow or tool requests: `.learnings/FEATURE_REQUESTS.md`

If the learning clearly belongs to a narrower service or package, keep it near
that service only after a local `.learnings/` convention exists there. Otherwise
use the repository root `.learnings/`.

## Entry Format

Append a new entry with this shape:

```md
## LRN-YYYYMMDD-NNN: <type>

- Logged: YYYY-MM-DD
- Priority: low | medium | high
- Status: pending | promoted | rejected
- Area: <docs | taqt | frontend | ci | repo>

### Summary

<one sentence>

### Details

<what happened and why it matters>

### Suggested Action

<how future agents or contributors should apply it>
```

Use `ERR-YYYYMMDD-NNN` for `.learnings/ERRORS.md` and
`FR-YYYYMMDD-NNN` for `.learnings/FEATURE_REQUESTS.md`.

## Promotion Rule

Keep `.learnings/` as raw, reviewable learning. Promote a learning into a
durable rule when either condition is true:

- The same kind of learning appears at least three times.
- The learning applies across multiple issues, modules, or contributors.

Promotion targets include `.agents/skills/`, `.codex/rules/`, `docs/`, issue or
PR templates, and other repository governance files. After promotion, update the
learning entry status to `promoted` and cite the target file.

## Reporting Rule

When you add or modify `.learnings/`, mention it in your final response and in
the PR summary. Never silently create learning entries.
