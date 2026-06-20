---
name: adversarial-review
description: Stress-test SIFTQ code, docs, or pull request changes before approval. Use when the user asks for an adversarial review, code review, PR review, regression hunt, risk assessment, or a check for bugs, missing tests, missing docs, AC/DoD gaps, or unsafe merge behavior.
---

# Adversarial Review

## Overview

Use this skill to review SIFTQ changes from a skeptical, bug-focused stance.
Prioritize behavioral regressions, broken contracts, missing validation,
missing tests, documentation drift, and workflow safety issues.

## Workflow

1. Identify the review target: working tree diff, commit range, branch, PR, or
   issue-linked change.
2. Read the changed files and the closest tests before judging the change.
3. If the change is issue-driven, compare it with the latest AC/DoD and any
   requirements, design, wireframe, or ADR artifacts referenced by the issue.
4. Check repository workflow impact:
   - command permissions in `.codex/rules/siftq.rules`
   - Taskfile entrypoints and CI references
   - CoDD links and validation expectations
   - sympohy labels, phase transitions, hooks, and run-state behavior
5. Look for bugs first, then missing tests, then maintainability concerns.
6. Do not implement fixes unless the user explicitly asks for fixes.

## Findings Format

Lead with findings. Order by severity.

For each finding, include:

- severity: `blocker`, `high`, `medium`, or `low`
- file and line reference when available
- concrete impact
- why the current code or doc creates the risk
- the smallest useful fix direction

If there are no findings, say that clearly and list any remaining verification
gaps or residual risk.

## Review Heuristics

- Treat tests that only assert implementation details as weak unless they also
  protect user-visible behavior or repository workflow contracts.
- Treat missing negative cases as suspicious for parsers, validators, state
  machines, label migration, command execution, and GitHub automation.
- For frontend UI, check layout stability, accessibility basics, edge-case text
  length, and whether tests cover the main interaction.
- For docs, check whether CoDD frontmatter, dependencies, templates, and linked
  workflow docs stay coherent.
- For automation, check idempotency, retry behavior, stale state recovery,
  failure reporting, and whether commands respect Codex rules.
