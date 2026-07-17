---
codd:
  node_id: design:sympohy-llm-loop-observability-self-improvement-adr
  type: design
  status: proposed
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:sympohy-llm-loop-observability-self-improvement
      relation: depends_on
      semantic: decision
---

# ADR 0019: sympohy LLM Loop Observability and Self-Improvement Workflow

## Status

Proposed.

## Context

Issue #126 adds observability and self-improvement to the sympohy runner. The
runner already keeps `state.json` for resume and supports lifecycle recovery,
but the existing workflow does not define a durable audit stream, a replayable
analysis store, or a bounded path from observations to low-risk improvements.

The feature needs to answer three durable questions:

- What is the authoritative record for observed runner events?
- How do we rebuild searchable analytics without preserving large raw artifacts?
- How do we keep self-improvement constrained to low-risk, reviewable changes?

It also needs to fix the storage format boundary early. If the event stream
format stays undecided, later replay, schema compatibility, and migration work
will couple to temporary artifacts such as `recovery.log` or ad hoc JSON files.

Those choices affect storage shape, replay strategy, workflow boundaries, and
future observability features, so they belong in an ADR rather than only in a
feature design doc.

## Decision

sympohy adopts an append-only event stream as the primary audit record for LLM
loop observations.

`state.json` remains the latest resume state and heartbeat/recovery snapshot.
The event stream records the durable history for hook, command, Codex,
stage-gate, review, recovery, browser observation, developer instruction,
analysis, proposal, and application events.

The event stream format is line-delimited JSON (`events.jsonl`). Each line is a
single event object with its own `run_id` and `event_id`, so replay can rebuild
run-local ordering without treating `state.json` as historical storage.

A SQLite observation store is treated as a derived index that can be rebuilt
from the event stream. The store exists for search and aggregation, not as the
primary record.

The observation record stores lightweight summaries and structured metadata
only. It does not persist raw screenshots, Playwright traces, DOM dumps, or
raw developer instructions. Developer instructions are normalized to source
kind, path/ref, sha256, and summary.

The self-improvement path is bounded. The proposer may emit JSON candidates for
prompt, hook, stage gate, docs, skill, test, and config improvements, but the
applicator may only automate low-risk changes such as docs, prompt, and test
fixture updates. The workflow stops at a verified draft PR and does not
autonomously apply broad code changes or auto-merge them.

Failure taxonomy and failure signatures are recorded so the analyzer can
identify blocked causes, retryable failures, recovered failures, and recurring
event chains.

## Rejected Alternatives

- Use `state.json` as the only record: this would keep the implementation
  smaller, but it would collapse resume state, audit history, and analytics
  into one file and make replay-based analysis much harder.
- Use one large JSON array file for events: this would make append and crash
  recovery more fragile, and it would force whole-file rewrites for a storage
  shape that is naturally stream-oriented.
- Store raw browser and Codex artifacts permanently: this would maximize
  forensic detail, but it would create privacy and storage risk and would make
  the observation store harder to sanitize.
- Let the applicator edit arbitrary code automatically: this would make the
  system more autonomous, but it would bypass the low-risk boundary required
  for safe self-improvement.

## Consequences

- Observability becomes replayable and debuggable from a single append-only
  source of truth.
- The derived SQLite store can be dropped and rebuilt without losing the audit
  trail.
- The system keeps a clear boundary between resume state and historical
  analytics.
- Privacy and storage risk stay bounded because only lightweight summaries are
  retained.
- Self-improvement remains reviewable, but it requires extra implementation
  work for replay, taxonomy, and schema compatibility tests.
