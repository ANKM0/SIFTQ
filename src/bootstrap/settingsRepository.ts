import { InMemorySettingsRepository } from "../adapters/inMemorySettingsRepository";
import {
  SqliteSettingsRepository,
  type SqliteConnection
} from "../adapters/sqliteSettingsRepository";
import { type SettingsRepository } from "../ports/settingsRepository";

export type SettingsRepositoryHost = {
  readonly siftqSqliteSettingsConnection?: SqliteConnection;
};

export function createStartupSettingsRepository(
  host: SettingsRepositoryHost = globalThis as SettingsRepositoryHost
): SettingsRepository {
  if (host.siftqSqliteSettingsConnection === undefined) {
    return new InMemorySettingsRepository();
  }

  return new SqliteSettingsRepository(host.siftqSqliteSettingsConnection);
}
