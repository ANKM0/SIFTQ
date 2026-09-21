---
name: adr-authoring
description: Create or update SIFTQ Architecture Decision Records using the repository ADR template and numbering conventions.
---

# ADR Authoring

Use this skill when creating or updating a SIFTQ ADR.

## Flow

1. Read `docs/contributing/adr.md`.
2. Decide title, slug, and one decision. Split out local decisions that do not need continued cross-cutting reference.
3. Break the decision into claims that could be wrong independently.
4. For each claim, record the evidence type, observation data, data-readiness condition, completion condition, status, limits, and reconsideration condition under supplemental information.
5. Require same-condition comparison for empirical claims about superiority, performance, cost, usability, or necessity. Record an unverified claim as provisional when comparison is not possible.
6. Draft purpose, background, constraints, decision, rejected options, and impact. Keep verification results and history under supplemental information.
7. Use `scripts/create_adr.py` for number, path, and template copy.
8. Update `docs/adr/README.md`.
9. Run the `adr-review` skill on the new or changed ADR and resolve its findings. For later evaluation of provisional claims, use the `adr-verification` skill. For new ADRs, run `task -t .config/Taskfile.yml ci:adr` for the deterministic check.

```bash
uv run python scripts/create_adr.py --title "..." --slug "..." --dry-run
```

## Writing Rules

- One ADR records one responsibility. Do not combine multiple responsibilities in one ADR.
- If decisions belong to different responsibilities, split them into separate ADRs.
- Keep it concise.
- Use concrete context.
- State the decision directly.
- Include only meaningful rejected options.
- Include the evidence type and verification scope for every claim.
- Define what data is observed, when it is sufficient to evaluate, and what completion condition means OK.
- Do not use one claim's verification result to justify another independent claim.
- Distinguish requirement compliance from superiority over alternatives.
- Mark claims that could not be verified as provisional and state when to revisit them.
- Keep the verification contract under supplemental information; manage unresolved verification points in the ADR README and store detailed results in experiment records without rewriting the decision.
- Keep implementation details out. Do not write identifiers, configuration values, processing order, code, commands, or source paths; leave them to code or design docs.
- To change an accepted ADR, do not rewrite its body. Add `> Status: Superseded by [ADR XXXX](...).` and record the new decision in a new ADR.
