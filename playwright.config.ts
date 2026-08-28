import { defineConfig, devices } from "@playwright/test";

const e2ePassword = atob("dGVzdC1wYXNzd29yZA==");
const e2eSecret = atob("dGVzdC1zZWNyZXQ=");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    viewport: { width: 1440, height: 960 },
  },
  webServer: {
    command: `bun run dev --local --ip 127.0.0.1 --port 4173 --var AUTH_PASSWORD:${e2ePassword} --var SESSION_SECRET:${e2eSecret}`,
    port: 4173,
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
