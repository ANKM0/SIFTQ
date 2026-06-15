import { INITIAL_AREAS, type AreaId } from "../domain/area";
import {
  areaLabelSettingsWithDefaults,
  getDefaultAreaLabelSettings,
  normalizeAreaLabelSettings,
  type AreaLabelSettings
} from "../domain/settings";
import { type SettingsRepository } from "../ports/settingsRepository";

export type SqliteValue = string | number | bigint | boolean | null;
export type SqliteRow = Readonly<Record<string, SqliteValue | undefined>>;

export type SqliteConnection = {
  execute(sql: string, params?: readonly SqliteValue[]): Promise<void>;
  select<Row extends SqliteRow>(
    sql: string,
    params?: readonly SqliteValue[]
  ): Promise<Row[]>;
  transaction?<Result>(operation: () => Promise<Result>): Promise<Result>;
};

type AreaLabelRow = SqliteRow & {
  readonly area_id: string;
  readonly label: string;
};

const AREA_ID_CHECK_VALUES = INITIAL_AREAS.map((area) => `'${area.id}'`).join(", ");
const CREATE_AREA_LABEL_SETTINGS_TABLE = `
CREATE TABLE IF NOT EXISTS area_label_settings (
  area_id TEXT PRIMARY KEY NOT NULL CHECK (area_id IN (${AREA_ID_CHECK_VALUES})),
  label TEXT NOT NULL CHECK (length(trim(label)) > 0)
)`;

export class SqliteSettingsRepository implements SettingsRepository {
  private isSchemaReady = false;

  constructor(private readonly connection: SqliteConnection) {}

  async loadAreaLabels(): Promise<AreaLabelSettings> {
    await this.ensureSchema();

    const rows = await this.connection.select<AreaLabelRow>(
      "SELECT area_id, label FROM area_label_settings"
    );
    const storedLabels: Partial<Record<AreaId, string>> = {};

    for (const row of rows) {
      if (isKnownAreaId(row.area_id)) {
        storedLabels[row.area_id] = row.label;
      }
    }

    return areaLabelSettingsWithDefaults(storedLabels);
  }

  async saveAreaLabels(labels: AreaLabelSettings): Promise<void> {
    const normalizedLabels = normalizeAreaLabelSettings(labels);

    await this.ensureSchema();
    await this.runTransaction(async () => {
      for (const area of INITIAL_AREAS) {
        await this.connection.execute(
          `INSERT INTO area_label_settings (area_id, label)
           VALUES (?, ?)
           ON CONFLICT(area_id) DO UPDATE SET label = excluded.label`,
          [area.id, normalizedLabels[area.id]]
        );
      }
    });
  }

  async restoreDefaultAreaLabels(): Promise<AreaLabelSettings> {
    const defaultLabels = getDefaultAreaLabelSettings();

    await this.saveAreaLabels(defaultLabels);

    return defaultLabels;
  }

  private async ensureSchema(): Promise<void> {
    if (this.isSchemaReady) {
      return;
    }

    await this.connection.execute(CREATE_AREA_LABEL_SETTINGS_TABLE);
    this.isSchemaReady = true;
  }

  private async runTransaction<Result>(
    operation: () => Promise<Result>
  ): Promise<Result> {
    if (this.connection.transaction !== undefined) {
      return this.connection.transaction(operation);
    }

    await this.connection.execute("BEGIN IMMEDIATE");

    try {
      const result = await operation();
      await this.connection.execute("COMMIT");

      return result;
    } catch (error) {
      await this.connection.execute("ROLLBACK");
      throw error;
    }
  }
}

function isKnownAreaId(areaId: string): areaId is AreaId {
  return INITIAL_AREAS.some((area) => area.id === areaId);
}
