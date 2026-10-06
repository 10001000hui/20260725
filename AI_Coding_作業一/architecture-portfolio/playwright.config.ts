import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: process.env.TEST_REPORT_FILE || '../驗證資料/browser-results.json' }]],
  use: { baseURL: process.env.TEST_BASE_URL || 'http://127.0.0.1:3000', browserName: 'chromium', launchOptions: { executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox'] } },
});
