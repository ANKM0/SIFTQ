import { describe, expect, it } from "vitest";

import {
  loadAreaLabels,
  restoreDefaultAreaLabels,
  saveAreaLabels
} from "../../src/application/settingsOperations";
import { InMemorySettingsRepository } from "../../src/adapters/inMemorySettingsRepository";
import { getDefaultAreaLabelSettings } from "../../src/domain/settings";

describe("settings operations", () => {
  it("loads default area labels through the repository port", async () => {
    const repository = new InMemorySettingsRepository();

    await expect(loadAreaLabels(repository)).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });

  it("normalizes area labels before saving", async () => {
    const repository = new InMemorySettingsRepository();

    const savedLabels = await saveAreaLabels(repository, {
      do: "  Now  ",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Skipped",
      done: "Done"
    });

    expect(savedLabels).toEqual({
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Skipped",
      done: "Done"
    });
    await expect(loadAreaLabels(repository)).resolves.toEqual(savedLabels);
  });

  it("rejects empty area labels before mutating settings", async () => {
    const repository = new InMemorySettingsRepository();
    const originalLabels = await loadAreaLabels(repository);

    await expect(
      saveAreaLabels(repository, {
        ...originalLabels,
        do: "   "
      })
    ).rejects.toThrow("Area label must not be empty.");
    await expect(loadAreaLabels(repository)).resolves.toEqual(originalLabels);
  });

  it("restores default area labels", async () => {
    const repository = new InMemorySettingsRepository();

    await saveAreaLabels(repository, {
      do: "Now",
      schedule: "Later",
      delegate: "Assign",
      eliminate: "Drop",
      skipped: "Dismissed",
      done: "Finished"
    });

    await expect(restoreDefaultAreaLabels(repository)).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
    await expect(loadAreaLabels(repository)).resolves.toEqual(
      getDefaultAreaLabelSettings()
    );
  });
});
