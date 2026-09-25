import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

const webDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(webDir, '../..');

const databaseUrl =
  process.env.E2E_DATABASE_URL ?? 'postgresql://isometric:isometric@localhost:5432/isometric_e2e';
const apiPort = process.env.E2E_API_PORT ?? '8000';
const webPort = process.env.E2E_WEB_PORT ?? '3000';
const apiOrigin = `http://127.0.0.1:${apiPort}`;
const baseURL = `http://localhost:${webPort}`;
// Reusing servers is opt-in so a dev API on the same port never serves the E2E run from another database.
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_SERVERS === '1';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/.results',
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['list'], ['html', { outputFolder: './e2e/.report', open: 'never' }]] : 'list',
  use: {
    baseURL,
    navigationTimeout: 60_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: [
    {
      command: './apps/web/e2e/serve-api',
      cwd: repoRoot,
      url: `${apiOrigin}/openapi.json`,
      env: {
        LOCAL_DATABASE_URL: databaseUrl,
        ARTIFACT_ROOT: path.join(repoRoot, '.private/e2e-artifacts'),
        PORT: apiPort,
      },
      reuseExistingServer,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'pipe',
    },
    {
      command: './scripts/run-web',
      cwd: repoRoot,
      url: `${baseURL}/upload`,
      env: {
        API_ORIGIN: apiOrigin,
        DEV_OWNER_ID: 'dev-owner',
        PORT: webPort,
        NEXT_TELEMETRY_DISABLED: '1',
      },
      reuseExistingServer,
      timeout: 180_000,
      stdout: 'ignore',
      stderr: 'pipe',
    },
  ],
});
