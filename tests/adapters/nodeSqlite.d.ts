declare module "node:sqlite" {
  type SqliteParameter = string | number | bigint | boolean | null;

  export class DatabaseSync {
    constructor(location: string);
    close(): void;
    exec(sql: string): void;
    prepare(sql: string): StatementSync;
  }

  export type StatementSync = {
    all(...params: readonly SqliteParameter[]): unknown[];
    run(...params: readonly SqliteParameter[]): unknown;
  };
}
