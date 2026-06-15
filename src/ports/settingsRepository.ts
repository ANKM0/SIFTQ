import { type AreaLabelSettings } from "../domain/settings";

export type SettingsRepository = {
  loadAreaLabels(): Promise<AreaLabelSettings>;
  saveAreaLabels(labels: AreaLabelSettings): Promise<void>;
  restoreDefaultAreaLabels(): Promise<AreaLabelSettings>;
};
