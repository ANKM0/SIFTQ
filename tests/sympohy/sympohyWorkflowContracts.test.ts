import { describe, expect, it } from "vitest";

import ciWorkflow from "../../.github/workflows/ci.yml?raw";
import releaseWorkflow from "../../.github/workflows/release.yml?raw";
import config from "../../.sympohy/config.yaml?raw";
import taskfile from "../../Taskfile.yml?raw";
import cli from "../../scripts/sympohy/cli.py?raw";
import core from "../../scripts/sympohy/core.py?raw";
import runner from "../../scripts/sympohy/runner.py?raw";

const ciCdWorkflows = [ciWorkflow, releaseWorkflow].join("\n");

describe("sympohy Taskfile and CLI integration", () => {
  it("exposes setup, run, refine, doctor, watch, labels, and systemd entrypoints", () => {
    const requiredTasks = [
      "setup:sympohy",
      "ci:sympohy",
      "ai:sympohy",
      "ai:sympohy:refine",
      "ai:sympohy:doctor",
      "ai:sympohy:stage-gate",
      "ai:sympohy:labels:sync",
      "ai:sympohy:migrate",
      "ai:sympohy:watch",
      "ai:sympohy:systemd:install",
      "ai:sympohy:systemd:start",
      "ai:sympohy:systemd:stop",
      "ai:sympohy:systemd:status"
    ];

    expect(requiredTasks.every((taskName) => taskfile.includes(`  ${taskName}:`))).toBe(
      true
    );
    expect(cli).toContain("resume");
    expect(cli).toContain("migrate");
    expect(cli).toContain("stage-gate");
  });

  it("keeps sympohy outside application runtime dependencies", () => {
    expect(taskfile).toContain("uv run python -m scripts.sympohy");
  });

  it("validates sympohy project configuration in local and GitHub CI", () => {
    expect(taskfile).toContain("task: ci:sympohy");
    expect(taskfile).toContain("task: setup:sympohy");
    expect(taskfile).toContain("task: ai:sympohy:doctor");
    expect(ciWorkflow).toContain("UV_CACHE_DIR");
    expect(ciWorkflow).toContain("Check sympohy project configuration");
    expect(ciWorkflow).toContain("task ci:sympohy");
  });

  it("keeps CI/CD workflows free of legacy taqt runner assumptions", () => {
    expect(ciCdWorkflows).not.toMatch(/\btaqt\b/i);
    expect(ciCdWorkflows).not.toMatch(/\btakt\b/i);
    expect(ciCdWorkflows).not.toContain(".takt");
    expect(ciCdWorkflows).not.toContain("setup:takt");
    expect(ciCdWorkflows).not.toContain("ai:takt");
    expect(taskfile).not.toContain("setup:takt");
    expect(taskfile).not.toContain("ai:takt");
    expect(taskfile).not.toContain("pnpm dlx takt");
  });
});

describe("sympohy watcher contract", () => {
  it("uses sympohy status labels and stale-running inspection", () => {
    expect(core).toContain("sympohy:pending");
    expect(core).toContain("sympohy:running");
    expect(core).toContain("sympohy:blocked");
    expect(core).toContain("sympohy:done");
    expect(core).toContain("is_candidate_issue");
    expect(core).toContain("inspect_running_issue");
    expect(config).toContain("stale_status_after_minutes: 30");
    expect(config).toContain("watch_poll_interval_seconds: 60");
    expect(config).toContain("ci_retry_max_attempts: 10");
    expect(config).toContain("review_max_rounds: 3");
    expect(config).toContain("final_verifier_fix_max_attempts: 2");
    expect(config).not.toContain(["merge_gate", "retry_max_attempts"].join("_"));
    expect(config).toContain("stage_gate_command: task ai:sympohy:stage-gate");
    expect(core).toContain("DEFAULT_STALE_STATUS_AFTER_MINUTES");
    expect(core).toContain("\"dead pid\"");
    expect(runner).toContain("\"resume\"");
    expect(runner).toContain("resume_issue");
  });

  it("persists run state for stale-running inspection", () => {
    expect(runner).toContain("state.json");
    expect(runner).toContain("\"run_id\"");
    expect(runner).toContain("\"lock\"");
    expect(runner).toContain("\"phase\"");
    expect(runner).toContain("\"pid\"");
    expect(runner).toContain("\"heartbeat\"");
    expect(runner).toContain("\"worktree\"");
    expect(runner).toContain("\"branch\"");
    expect(runner).toContain("\"plan_reference\"");
    expect(runner).toContain("\"last_known_progress\"");
  });

  it("recovers implementation from saved plans and existing worktree state", () => {
    expect(runner).toContain("_load_existing_plan");
    expect(runner).toContain("_infer_implementation_recovery");
    expect(runner).toContain("recovered_existing_plan");
    expect(runner).toContain("worktree has uncommitted changes during resume");
    expect(runner).toContain("next_logical_step");
    expect(runner).toContain("resume_action");
    expect(runner).toContain("implement_next_step");
    expect(runner).toContain("push_pr");
    expect(runner).toContain("git\", \"log\", \"--format=%s\"");
    expect(runner).toContain("git\", \"status\", \"--porcelain\"");
  });

  it("limits parallel issue starts with conservative workers and uses independent worktrees", () => {
    expect(config).toContain("max_workers: 3");
    expect(runner).toContain("_watch_candidate_priority");
    expect(runner).toContain("watch_forever");
    expect(runner).toContain("_start_watch_workers");
    expect(runner).toContain("_reap_watch_workers");
    expect(runner).toContain("git\", \"worktree\", \"add");
  });
});

describe("sympohy automation contract", () => {
  it("models phase exclusivity, AC/DoD extraction, review JSON, retry, and merge gates", () => {
    expect(core).toContain("PHASES =");
    expect(core).toContain("extract_acceptance_set");
    expect(core).toContain("parse_review_json");
    expect(core).toContain("next_retry_action");
    expect(core).toContain("merge_gate_allows_merge");
    expect(core).toContain("stage_gate_status");
    expect(runner).toContain("_prepare_document_artifacts");
    expect(runner).toContain("artifact-decisions.json");
    expect(runner).toContain("\"requirements\", \"design\", \"wireframes\", \"adr\"");
    expect(runner).toContain("status set to pass or retry");
    expect(runner).toContain('"pass", "retry", or "block"');
  });

  it("does not disable normal Codex user config or repository rules", () => {
    expect(runner).toContain("\"codex\", \"exec\"");
    expect(runner).not.toContain("--ignore-user-config");
    expect(runner).not.toContain("--ignore-rules");
  });

  it("doctor checks config, labels, systemd templates, hooks, and commit subjects", () => {
    expect(cli).toContain("\"default hook task ci\"");
    expect(cli).toContain("\"stage gate command configured\"");
    expect(cli).toContain("\"codex model roles configured\"");
    expect(cli).toContain("\"stage gate task declared\"");
    expect(cli).toContain("\"stale_status_after_minutes > 0\"");
    expect(cli).toContain("\"watch_poll_interval_seconds > 0\"");
    expect(cli).toContain("\"required labels declared\"");
    expect(cli).toContain("\"systemd service template\"");
    expect(cli).toContain("\"systemd service install target\"");
    expect(cli).not.toContain("systemd timer template");
    expect(cli).toContain("validate_commit_subject");
  });

  it("migrates legacy task labels without taking over preserved issue metadata", () => {
    expect(core).toContain("migrate_task_labels");
    expect(core).toContain("LEGACY_TASK_LABEL_PREFIXES");
    expect(cli).toContain("migrate_legacy_tasks");
    expect(taskfile).toContain("delete legacy task labels");
    expect(taskfile).toContain("ai:sympohy:migrate");
  });
});
