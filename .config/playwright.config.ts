import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const repoRoot = fileURLToPath(new URL("..", import.meta.url));
const e2ePassword = atob("dGVzdC1wYXNzd29yZA==");
const e2eSecret = atob("dGVzdC1zZWNyZXQ=");
const e2ePort = Number(process.env["E2E_PORT"] ?? 4173);

export default defineConfig({
  testDir: "../tests/e2e",
  outputDir: path.join(repoRoot, "tmp/test-results"),
  fullyParallel: true,
  // E2E files share one local D1 database and Worker process.
  workers: 1,
  retries: 0,
  use: {
    baseURL: `http://127.0.0.1:${e2ePort}`,
    trace: "on-first-retry",
    viewport: { width: 1440, height: 960 },
  },
  webServer: {
    command: `bun run dev --local --ip 127.0.0.1 --port ${e2ePort} --var AUTH_PASSWORD:${e2ePassword} --var SESSION_SECRET:${e2eSecret}`,
    port: e2ePort,
    reuseExistingServer: !process.env["CI"],
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 960 },
      },
    },
  ],
});
