import { expect, test, type Route } from '@playwright/test';
import { makeDrawingPng } from './support/png';

const failures: { name: string; fail: (route: Route) => Promise<void>; message: string | RegExp; requestId: string | null }[] = [
  {
    name: 'server error',
    fail: (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'internal_error', message: 'Simulated upload failure', request_id: 'e2e-simulated-500' }),
      }),
    message: 'Simulated upload failure',
    requestId: 'e2e-simulated-500',
  },
  {
    name: 'network abort',
    fail: (route) => route.abort('connectionreset'),
    message: 'Upload failed. Try again.',
    requestId: null,
  },
];

for (const failure of failures) {
  test(`upload ${failure.name} keeps the selected file and the same retry succeeds`, async ({ page }) => {
    const filename = `e2e-retry-${failure.name.replace(/\s+/g, '-')}-${Date.now()}.png`;
    const failedKeys: string[] = [];

    await page.route('**/api/v1/documents', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      failedKeys.push((await route.request().headerValue('idempotency-key')) ?? '');
      await failure.fail(route);
    });

    await page.goto('/upload');
    await page.getByTestId('upload-file-input').setInputFiles({
      name: filename,
      mimeType: 'image/png',
      buffer: makeDrawingPng(),
    });
    await page.getByTestId('upload-start-button').click();

    const attachment = page.getByTestId('upload-attachment-row');
    await expect(attachment).toContainText('Upload failed');
    await expect(attachment).toContainText(filename);
    await expect(page.getByRole('alert').filter({ hasText: failure.message })).toBeVisible();
    if (failure.requestId) {
      await expect(attachment).toContainText(`Request ID: ${failure.requestId}`);
    }
    const retry = page.getByRole('button', { name: 'Retry' });
    await expect(retry).toBeVisible();
    await expect(retry).toBeEnabled();
    expect(failedKeys).toHaveLength(1);

    await page.unroute('**/api/v1/documents');

    const retryRequest = page.waitForRequest(
      (request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/documents',
    );
    const retryResponse = page.waitForResponse(
      (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/documents',
    );
    await retry.click();
    expect(await (await retryRequest).headerValue('idempotency-key')).toBe(failedKeys[0]);
    expect((await retryResponse).status()).toBe(202);

    await page.waitForURL(/\/jobs\/[0-9a-f-]{36}$/);
    await expect(page.getByText('Succeeded', { exact: true })).toBeVisible({ timeout: 60_000 });
  });
}
