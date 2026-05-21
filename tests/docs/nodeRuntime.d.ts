declare module "node:child_process" {
  export function execFileSync(
    command: string,
    args: readonly string[],
    options: {
      env?: Record<string, string | undefined>;
      stdio?: "pipe";
    }
  ): Uint8Array;
}

declare module "node:fs" {
  export function mkdirSync(
    path: string,
    options: { recursive: true }
  ): string | undefined;

  export function rmSync(
    path: string,
    options: { recursive: true; force: true }
  ): void;

  export function writeFileSync(path: string, data: string, encoding: "utf8"): void;
}

declare const process: {
  env: Record<string, string | undefined>;
};
