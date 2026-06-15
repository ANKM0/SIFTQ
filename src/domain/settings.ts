import {
  DEFAULT_AREA_LABELS,
  INITIAL_AREAS,
  type Area,
  type AreaId,
  type AreaLabels
} from "./area";

export type AreaLabelSettings = AreaLabels;

export class SettingsValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SettingsValidationError";
  }
}

export function getDefaultAreaLabelSettings(): AreaLabelSettings {
  return { ...DEFAULT_AREA_LABELS };
}

export function normalizeAreaLabel(rawLabel: string): string {
  const label = rawLabel.trim();

  if (label.length === 0) {
    throw new SettingsValidationError("Area label must not be empty.");
  }

  return label;
}

export function normalizeAreaLabelSettings(
  rawLabels: Partial<Record<AreaId, string>>
): AreaLabelSettings {
  const labels: Partial<Record<AreaId, string>> = {};

  for (const area of INITIAL_AREAS) {
    const rawLabel = rawLabels[area.id];

    if (rawLabel === undefined) {
      throw new SettingsValidationError(`Area label is missing: ${area.id}.`);
    }

    labels[area.id] = normalizeAreaLabel(rawLabel);
  }

  return labels as AreaLabelSettings;
}

export function areaLabelSettingsWithDefaults(
  rawLabels: Partial<Record<AreaId, string>>
): AreaLabelSettings {
  const labels: Partial<Record<AreaId, string>> = {
    ...getDefaultAreaLabelSettings()
  };

  for (const area of INITIAL_AREAS) {
    const rawLabel = rawLabels[area.id];

    if (rawLabel !== undefined) {
      labels[area.id] = normalizeAreaLabel(rawLabel);
    }
  }

  return labels as AreaLabelSettings;
}

export function areasWithLabels(labels: AreaLabelSettings): readonly Area[] {
  const normalizedLabels = normalizeAreaLabelSettings(labels);

  return INITIAL_AREAS.map((area) => ({
    ...area,
    label: normalizedLabels[area.id]
  }));
}
