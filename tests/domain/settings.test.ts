import { describe, expect, it } from "vitest";

import { INITIAL_AREAS } from "../../src/domain/area";
import {
  areasWithLabels,
  getDefaultAreaLabelSettings
} from "../../src/domain/settings";

describe("settings domain", () => {
  it("derives default area labels from the initial area definitions", () => {
    expect(getDefaultAreaLabelSettings()).toEqual(
      Object.fromEntries(INITIAL_AREAS.map((area) => [area.id, area.label]))
    );
  });

  it("applies label settings without changing stable area identity", () => {
    const areas = areasWithLabels({
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    });

    expect(areas).toEqual([
      { id: "do", label: "Now", kind: "matrix", role: "do" },
      { id: "schedule", label: "Later", kind: "matrix", role: "schedule" },
      { id: "delegate", label: "Assign", kind: "matrix", role: "delegate" },
      { id: "eliminate", label: "Drop", kind: "matrix", role: "eliminate" },
      { id: "skipped", label: "Dismissed", kind: "terminal", role: "skipped" },
      { id: "done", label: "Finished", kind: "terminal", role: "done" }
    ]);
  });
});
