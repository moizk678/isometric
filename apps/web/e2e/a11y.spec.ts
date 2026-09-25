import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { expectImageLoaded, newProxyContext, uploadThroughProxy, type UploadedDocument } from './support/app';

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

async function expectNoAxeViolations(page: Page): Promise<void> {
  // nextjs-portal is the Next.js dev-server overlay; it does not ship in production builds.
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).exclude('nextjs-portal').analyze();
  const summary = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    nodes: violation.nodes.map((node) => ({ target: node.target.join(' '), summary: node.failureSummary })),
  }));
  expect(summary, JSON.stringify(summary, null, 2)).toEqual([]);
}

let document: UploadedDocument;

test.beforeAll(async () => {
  const api = await newProxyContext(test.info().project.use.baseURL);
  document = await uploadThroughProxy(api, `e2e-a11y-${Date.now()}.png`);
  await api.dispose();
});

for (const viewport of [
  { name: 'desktop', size: { width: 1440, height: 900 } },
  { name: 'phone', size: { width: 390, height: 844 } },
]) {
  test.describe(`axe on ${viewport.name}`, () => {
    test.use({ viewport: viewport.size });

    test('documents list', async ({ page }) => {
      await page.goto('/documents');
      await expect(page.getByRole('link', { name: new RegExp(document.filename) })).toBeVisible();
      await expectNoAxeViolations(page);
    });

    test('upload', async ({ page }) => {
      await page.goto('/upload');
      await expect(page.getByRole('button', { name: 'Choose files' })).toBeVisible();
      await expectNoAxeViolations(page);
    });

    test('workbench with a selected object', async ({ page }) => {
      const annotation = document.objects.find((object) => object.type === 'annotation')!;
      await page.goto(`/documents/${document.documentId}?object=${annotation.id}`);
      await expect(page.getByRole('heading', { level: 1, name: document.filename })).toBeVisible();
      await expectImageLoaded(page.getByRole('img', { name: 'Original drawing, orientation corrected' }));
      await expectNoAxeViolations(page);
    });
  });
}
