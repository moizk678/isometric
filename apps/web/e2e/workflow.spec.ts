import { readFile } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';
import {
  expectImageLoaded,
  expectVisibleFocus,
  newProxyContext,
  objectOfType,
  sceneObjects,
  tabTo,
  uploadThroughProxy,
  type SceneObject,
} from './support/app';
import { makeDrawingPng } from './support/png';

async function expectEvidenceFor(page: Page, object: SceneObject): Promise<void> {
  const evidence = page.getByRole('list', { name: 'Evidence' });
  await expect(evidence).toBeVisible();
  for (const item of object.interpretation.evidence) {
    await expect(evidence).toContainText(item.stage);
    await expect(evidence).toContainText(item.artifactId);
  }
  await expect(page.getByText(object.id, { exact: true }).first()).toBeVisible();
}

test('upload a PNG, wait for the fixture job, select objects, and download the SVG', async ({ page }) => {
  const filename = `e2e-workflow-${Date.now()}.png`;

  await page.goto('/upload');
  await page.getByTestId('upload-file-input').setInputFiles({
    name: filename,
    mimeType: 'image/png',
    buffer: makeDrawingPng(),
  });
  await expect(page.getByTestId('upload-attachment-row')).toContainText(filename);
  await page.getByTestId('upload-start-button').click();

  await page.waitForURL(/\/jobs\/[0-9a-f-]{36}$/);
  await expect(page.getByText('Succeeded', { exact: true })).toBeVisible({ timeout: 60_000 });
  await page.getByRole('link', { name: 'Open document' }).click();

  await page.waitForURL(/\/documents\/[0-9a-f-]{36}/);
  const documentId = new URL(page.url()).pathname.split('/').pop()!;
  await expect(page.getByRole('heading', { level: 1, name: filename })).toBeVisible();

  const api = await newProxyContext(test.info().project.use.baseURL);
  const detail = (await (await api.get(`/api/v1/documents/${documentId}`)).json()) as { current_revision_id: string };
  const objects = await sceneObjects(api, documentId, detail.current_revision_id);
  await api.dispose();

  await test.step('both canvases render', async () => {
    await expectImageLoaded(page.getByRole('img', { name: 'Original drawing, orientation corrected' }));
    await expectImageLoaded(page.getByRole('img', { name: /^SVG export of revision/ }));
  });

  await test.step('select an object by keyboard', async () => {
    const pipe = objectOfType(objects, 'pipe_segment');
    const pipeIndex = objects.indexOf(pipe);
    const listbox = page.getByRole('listbox', { name: 'Scene objects' });
    await tabTo(page, listbox);
    await expectVisibleFocus(listbox);
    await page.keyboard.press('Home');
    for (let i = 0; i < pipeIndex; i += 1) {
      await page.keyboard.press('ArrowDown');
    }
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(new RegExp(`[?&]object=${pipe.id}`));
    await expect(listbox.getByRole('option', { selected: true })).toHaveAttribute('aria-label', /^Pipe segment/);
    await expect(page.getByRole('group', { name: 'Original drawing' })).toHaveAttribute('data-selected-object', pipe.id);
    await expect(page.getByRole('group', { name: 'SVG export' })).toHaveAttribute('data-selected-object', pipe.id);
    await expect(page.getByTestId('svg-highlight')).toHaveAttribute('data-highlight-object', pipe.id);
    await expectEvidenceFor(page, pipe);
    await expect(listbox).toBeFocused();
  });

  await test.step('select an object by clicking its hit target', async () => {
    const annotation = objectOfType(objects, 'annotation');
    const svgViewer = page.getByRole('group', { name: 'SVG export' });
    await svgViewer.focus();
    await page.keyboard.press('0');
    await svgViewer.getByTestId('svg-overlay').locator(`[data-object-id="${annotation.id}"]`).click();

    await expect(page).toHaveURL(new RegExp(`[?&]object=${annotation.id}`));
    await expect(svgViewer).toHaveAttribute('data-selected-object', annotation.id);
    await expect(page.getByRole('listbox', { name: 'Scene objects' }).getByRole('option', { selected: true })).toHaveAttribute(
      'aria-label',
      /^Annotation/,
    );
    await expectEvidenceFor(page, annotation);
  });

  await test.step('download the SVG export', async () => {
    const link = page.getByRole('link', { name: 'Download SVG' });
    const href = await link.getAttribute('href');
    expect(href).toMatch(new RegExp(`^/api/v1/documents/${documentId}/revisions/${detail.current_revision_id}/exports/svg$`));
    await expect(link).toHaveAttribute('download', filename.replace(/\.png$/, '.svg'));

    const response = await page.request.get(href!);
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('image/svg+xml');
    expect(await response.text()).toContain('<svg');

    const [download] = await Promise.all([page.waitForEvent('download'), link.click()]);
    expect(download.suggestedFilename()).toBe(filename.replace(/\.png$/, '.svg'));
    const saved = await readFile((await download.path())!, 'utf8');
    expect(saved).toContain('<svg');
  });
});

test('touch selects an object on a phone and opens its evidence in the review drawer', async ({ browser }) => {
  const baseURL = test.info().project.use.baseURL;
  const api = await newProxyContext(baseURL);
  const uploaded = await uploadThroughProxy(api, `e2e-touch-${Date.now()}.png`);
  await api.dispose();
  const annotation = objectOfType(uploaded.objects, 'annotation');

  const context = await browser.newContext({
    baseURL,
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  await page.goto(`/documents/${uploaded.documentId}`);

  const canvasSwitch = page.getByRole('tablist', { name: 'Canvas' });
  await expect(canvasSwitch).toBeVisible();
  const reviewButton = page.getByRole('button', { name: /^Review \(\d+\)$/ });
  for (const target of [
    canvasSwitch.getByRole('tab', { name: 'Original' }),
    canvasSwitch.getByRole('tab', { name: 'SVG' }),
    reviewButton,
    page.getByRole('link', { name: 'Download SVG' }),
  ]) {
    const box = await target.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44);
    expect(box!.width).toBeGreaterThanOrEqual(44);
  }

  await canvasSwitch.getByRole('tab', { name: 'SVG' }).tap();
  const svgViewer = page.getByRole('group', { name: 'SVG export' });
  await expectImageLoaded(page.getByRole('img', { name: /^SVG export of revision/ }));
  await svgViewer.getByTestId('svg-overlay').locator(`[data-object-id="${annotation.id}"]`).tap();
  await expect(page).toHaveURL(new RegExp(`[?&]object=${annotation.id}`));
  await expect(svgViewer).toHaveAttribute('data-selected-object', annotation.id);
  const zoom = await svgViewer.getAttribute('data-zoom');

  await reviewButton.tap();
  const drawer = page.getByRole('dialog', { name: 'Review' });
  await expect(drawer).toBeVisible();
  const evidence = drawer.getByRole('list', { name: 'Evidence' });
  for (const item of annotation.interpretation.evidence) {
    await expect(evidence).toContainText(item.stage);
    await expect(evidence).toContainText(item.artifactId);
  }
  await drawer.getByRole('button', { name: 'Close drawer' }).tap();
  await expect(drawer).toBeHidden();

  await canvasSwitch.getByRole('tab', { name: 'Original' }).tap();
  const sourceViewer = page.getByRole('group', { name: 'Original drawing' });
  await expect(sourceViewer).toHaveAttribute('data-selected-object', annotation.id);
  await expect(sourceViewer).toHaveAttribute('data-zoom', zoom!);

  await context.close();
});
