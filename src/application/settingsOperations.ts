import {
  normalizeAreaLabelSettings,
  type AreaLabelSettings
} from "../domain/settings";
import { type SettingsRepository } from "../ports/settingsRepository";

export async function loadAreaLabels(
  repository: SettingsRepository
): Promise<AreaLabelSettings> {
  return repository.loadAreaLabels();
}

export async function saveAreaLabels(
  repository: SettingsRepository,
  labels: AreaLabelSettings
): Promise<AreaLabelSettings> {
  const normalizedLabels = normalizeAreaLabelSettings(labels);

  await repository.saveAreaLabels(normalizedLabels);

  return normalizedLabels;
}

export async function restoreDefaultAreaLabels(
  repository: SettingsRepository
): Promise<AreaLabelSettings> {
  return repository.restoreDefaultAreaLabels();
}
