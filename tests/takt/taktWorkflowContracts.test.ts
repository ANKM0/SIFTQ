import { describe, expect, it } from "vitest";

import issueRefinementWorkflow from "../../.takt/workflows/issue-refinement.yaml?raw";
import implementationWorkflow from "../../.takt/workflows/siftq.yaml?raw";
import taskfile from "../../Taskfile.yml?raw";

describe("TAKT issue refinement workflow contract", () => {
  it("defines an independent issue refinement workflow that uses ai:impl-ready", () => {
    const givenWorkflow = issueRefinementWorkflow;

    const whenWorkflowContract = {
      declaresRefinementWorkflow: givenWorkflow.includes("name: issue-refinement"),
      marksImplementationReadiness: givenWorkflow.includes("ai:impl-ready"),
      targetsGitHubIssues: givenWorkflow.includes("GitHub Issue")
    };

    expect(whenWorkflowContract).toEqual({
      declaresRefinementWorkflow: true,
      marksImplementationReadiness: true,
      targetsGitHubIssues: true
    });
  });

  it("requires AC, DoD, and ADR readiness checks before label assignment", () => {
    const givenWorkflow = issueRefinementWorkflow;

    const whenReadinessChecks = [
      "AC",
      "DoD",
      "ADR",
      "ai:impl-ready"
    ].filter((requiredTerm) => givenWorkflow.includes(requiredTerm));

    expect(whenReadinessChecks).toEqual(["AC", "DoD", "ADR", "ai:impl-ready"]);
  });

  it("keeps unresolved questions, issue updates, and label evidence as explicit outcomes", () => {
    const givenWorkflow = issueRefinementWorkflow;

    const whenOutcomeContracts = {
      unresolvedQuestions: includesAny(givenWorkflow, [
        "ヒアリング項目",
        "unresolved questions",
        "open questions"
      ]),
      issueUpdate: includesAny(givenWorkflow, [
        "AC/DoD を更新",
        "update the GitHub Issue",
        "updated issue"
      ]),
      labelEvidence: includesAny(givenWorkflow, [
        "ラベル付与",
        "label evidence",
        "ai:impl-ready label"
      ])
    };

    expect(whenOutcomeContracts).toEqual({
      unresolvedQuestions: true,
      issueUpdate: true,
      labelEvidence: true
    });
  });
});

describe("TAKT implementation workflow readiness gate", () => {
  it("blocks implementation before planning when ai:impl-ready is missing", () => {
    const givenPlanStep = extractStepBlock(implementationWorkflow, "plan");

    const whenGateContract = {
      checksReadinessLabel: givenPlanStep.includes("ai:impl-ready"),
      blocksMissingReadiness: givenPlanStep.includes("Blocked"),
      blocksBeforeEdits: givenPlanStep.includes("edit: false")
    };

    expect(whenGateContract).toEqual({
      checksReadinessLabel: true,
      blocksMissingReadiness: true,
      blocksBeforeEdits: true
    });
  });

  it("blocks unclear acceptance, completion, and design prerequisites", () => {
    const givenPlanStep = extractStepBlock(implementationWorkflow, "plan");

    const whenBlockedPrerequisites = {
      acceptanceCriteria: givenPlanStep.includes("AC"),
      definitionOfDone: givenPlanStep.includes("DoD"),
      architectureDecision: givenPlanStep.includes("ADR"),
      designPremise: includesAny(givenPlanStep, ["設計前提", "design prerequisite"])
    };

    expect(whenBlockedPrerequisites).toEqual({
      acceptanceCriteria: true,
      definitionOfDone: true,
      architectureDecision: true,
      designPremise: true
    });
  });
});

describe("TAKT Taskfile workflow integration", () => {
  it("runs implementation issues through pipeline mode so commit messages use the configured template", () => {
    const givenImplementationTask = extractTaskBlock(taskfile, "ai:takt");

    const whenEntrypoint = {
      usesPipelineMode: givenImplementationTask.includes("--pipeline"),
      selectsImplementationWorkflow: givenImplementationTask.includes(
        "--workflow siftq"
      ),
      avoidsQueueAutoCommitPath: !givenImplementationTask.includes(
        "task ai:takt:add --"
      ),
      forwardsIssueArguments: givenImplementationTask.includes("{{.CLI_ARGS}}")
    };

    expect(whenEntrypoint).toEqual({
      usesPipelineMode: true,
      selectsImplementationWorkflow: true,
      avoidsQueueAutoCommitPath: true,
      forwardsIssueArguments: true
    });
  });

  it("validates both implementation and refinement workflows through doctor", () => {
    const givenDoctorTask = extractTaskBlock(taskfile, "ai:takt:doctor");

    const whenDoctorTargets = {
      validatesImplementationWorkflow: givenDoctorTask.includes("siftq"),
      validatesRefinementWorkflow: givenDoctorTask.includes("issue-refinement")
    };

    expect(whenDoctorTargets).toEqual({
      validatesImplementationWorkflow: true,
      validatesRefinementWorkflow: true
    });
  });

  it("provides a refinement entrypoint wired to the issue-refinement workflow", () => {
    const givenRefineTask = extractTaskBlock(taskfile, "ai:takt:refine");

    const whenRefineEntrypoint = {
      exists: givenRefineTask.length > 0,
      selectsRefinementWorkflowBeforeAdd: givenRefineTask.includes(
        "task ai:takt:cli -- --workflow issue-refinement add {{.CLI_ARGS}}"
      ),
      rejectsSubcommandWorkflowOption: !givenRefineTask.includes(
        "task ai:takt:add -- --workflow issue-refinement"
      ),
      forwardsIssueArguments: givenRefineTask.includes("{{.CLI_ARGS}}")
    };

    expect(whenRefineEntrypoint).toEqual({
      exists: true,
      selectsRefinementWorkflowBeforeAdd: true,
      rejectsSubcommandWorkflowOption: true,
      forwardsIssueArguments: true
    });
  });
});

function includesAny(source: string, terms: string[]): boolean {
  return terms.some((term) => source.includes(term));
}

function extractStepBlock(workflow: string, stepName: string): string {
  return extractYamlListBlock(workflow, `  - name: ${stepName}`);
}

function extractTaskBlock(source: string, taskName: string): string {
  const blockMatch = new RegExp(`^  ${escapeRegExp(taskName)}:\\n`, "m").exec(
    source
  );

  if (blockMatch === null) {
    return "";
  }

  const blockStart = blockMatch.index;
  const nextTaskStart = source
    .slice(blockStart + 1)
    .search(/\n {2}[^\s].*:\n/);

  if (nextTaskStart === -1) {
    return source.slice(blockStart);
  }

  return source.slice(blockStart, blockStart + nextTaskStart + 1);
}

function escapeRegExp(source: string): string {
  return source.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractYamlListBlock(source: string, marker: string): string {
  const blockStart = source.indexOf(marker);

  if (blockStart === -1) {
    return "";
  }

  const nextItemStart = source
    .slice(blockStart + marker.length)
    .search(/\n {2}- name: /);

  if (nextItemStart === -1) {
    return source.slice(blockStart);
  }

  return source.slice(blockStart, blockStart + marker.length + nextItemStart);
}
