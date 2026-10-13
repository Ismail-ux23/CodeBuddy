import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/browser",
  use: {
    baseURL: "http://127.0.0.1:3000",
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROME ? { channel: "chrome" } : {}),
  },
  webServer: {
    command: "npm run start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  reporter: "list",
});
