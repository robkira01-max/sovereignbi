import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 1,
  reporter: [["html", { outputFolder: "../docs/playwright-report" }], ["list"]],
  use: {
    baseURL: process.env.SOVEREIGN_BASE_URL || "http://localhost:8000",
    trace: "on-first-retry",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 5"] },
    },
  ],
  webServer: {
    command: "cd .. && make run",
    url: "http://localhost:8000/health",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
