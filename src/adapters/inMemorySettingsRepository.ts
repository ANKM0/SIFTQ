import {
  getDefaultAreaLabelSettings,
  normalizeAreaLabelSettings,
  type AreaLabelSettings
} from "../domain/settings";
import { type SettingsRepository } from "../ports/settingsRepository";

export class InMemorySettingsRepository implements SettingsRepository {
  private areaLabels: AreaLabelSettings;

  constructor(options: { areaLabels?: AreaLabelSettings } = {}) {
    this.areaLabels =
      options.areaLabels === undefined
        ? getDefaultAreaLabelSettings()
        : normalizeAreaLabelSettings(options.areaLabels);
  }

  async loadAreaLabels(): Promise<AreaLabelSettings> {
    return { ...this.areaLabels };
  }

  async saveAreaLabels(labels: AreaLabelSettings): Promise<void> {
    this.areaLabels = normalizeAreaLabelSettings(labels);
  }

  async restoreDefaultAreaLabels(): Promise<AreaLabelSettings> {
    this.areaLabels = getDefaultAreaLabelSettings();

    return this.loadAreaLabels();
  }
}
