import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    viewport: { width: 1440, height: 960 }
  },
  webServer: {
    command: "pnpm vite --host 127.0.0.1 --port 4173",
    port: 4173,
    reuseExistingServer: !process.env["CI"]
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 960 }
      }
    }
  ]
});
