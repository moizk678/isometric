import { randomUUID } from 'node:crypto';
import { expect, request as playwrightRequest, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { makeDrawingPng } from './png';

export type SceneObject = {
  id: string;
  type: string;
  interpretation: { evidence: { stage: string; artifactId: string }[] };
};

export type UploadedDocument = {
  documentId: string;
  jobId: string;
  revisionId: string;
  filename: string;
  objects: SceneObject[];
};

/** Uploads through the Next proxy (never FastAPI directly) and waits for the fixture job. */
export async function uploadThroughProxy(api: APIRequestContext, filename: string): Promise<UploadedDocument> {
  const created = await api.post('/api/v1/documents', {
    headers: { 'Idempotency-Key': randomUUID() },
    multipart: {
      file: { name: filename, mimeType: 'image/png', buffer: makeDrawingPng() },
      profile_id: 'piping_isometric',
      options_json: '{}',
    },
  });
  expect(created.status(), await created.text()).toBe(202);
  const { document_id: documentId, job_id: jobId } = (await created.json()) as { document_id: string; job_id: string };
  const revisionId = await waitForJobRevision(api, jobId);
  const objects = await sceneObjects(api, documentId, revisionId);
  return { documentId, jobId, revisionId, filename, objects };
}

export async function waitForJobRevision(api: APIRequestContext, jobId: string): Promise<string> {
  let revisionId: string | null = null;
  await expect
    .poll(
      async () => {
        const response = await api.get(`/api/v1/jobs/${jobId}`);
        const job = (await response.json()) as { state: string; result_revision_id: string | null };
        revisionId = job.result_revision_id;
        return job.state;
      },
      { timeout: 60_000, intervals: [250, 500, 1000] },
    )
    .toBe('succeeded');
  if (!revisionId) {
    throw new Error(`job ${jobId} succeeded without a result revision`);
  }
  return revisionId;
}

export async function sceneObjects(api: APIRequestContext, documentId: string, revisionId: string): Promise<SceneObject[]> {
  const response = await api.get(`/api/v1/documents/${documentId}/revisions/${revisionId}/scene`);
  expect(response.status()).toBe(200);
  const scene = (await response.json()) as { objects: SceneObject[] };
  return scene.objects;
}

export async function newProxyContext(baseURL: string | undefined): Promise<APIRequestContext> {
  return playwrightRequest.newContext({ baseURL });
}

export function objectOfType(objects: SceneObject[], type: string): SceneObject {
  const found = objects.find((object) => object.type === type);
  if (!found) {
    throw new Error(`fixture scene has no ${type} object`);
  }
  return found;
}

/** Presses Tab until `target` has focus, so the focus arrives by keyboard. */
export async function tabTo(page: Page, target: Locator, maxPresses = 60): Promise<void> {
  const handle = await target.elementHandle();
  if (!handle) {
    throw new Error('tab target is not attached');
  }
  for (let i = 0; i < maxPresses; i += 1) {
    await page.keyboard.press('Tab');
    if (await handle.evaluate((element) => element === document.activeElement)) {
      return;
    }
  }
  throw new Error(`target not reached after ${maxPresses} Tab presses`);
}

/** The element is focus-visible and draws a solid outline of at least 2 px. */
export async function expectVisibleFocus(target: Locator): Promise<void> {
  const style = await target.evaluate((element) => {
    const computed = getComputedStyle(element);
    return {
      focused: element === document.activeElement,
      focusVisible: element.matches(':focus-visible'),
      outlineStyle: computed.outlineStyle,
      outlineWidth: Number.parseFloat(computed.outlineWidth),
      outlineColor: computed.outlineColor,
    };
  });
  expect(style.focused, 'element should have focus').toBe(true);
  expect(style.focusVisible, 'element should match :focus-visible').toBe(true);
  expect(style.outlineStyle).not.toBe('none');
  expect(style.outlineWidth).toBeGreaterThanOrEqual(2);
  expect(style.outlineColor).not.toMatch(/rgba\(\d+, \d+, \d+, 0\)|transparent/);
}

export async function expectNoPageHorizontalScroll(page: Page): Promise<void> {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth, `document scrollWidth ${scrollWidth} exceeds clientWidth ${clientWidth}`).toBeLessThanOrEqual(clientWidth);
}

/** Headings and panel descriptions fit their own boxes, so no label is clipped or drawn under a neighbour. */
export async function expectTextFitsBoxes(page: Page): Promise<void> {
  const overflowing = await page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>('main h1, main h2, main h3, main header p'))
      .filter((element) => element.getClientRects().length > 0 && element.scrollWidth > element.clientWidth + 1)
      .map((element) => `${element.tagName.toLowerCase()} "${element.textContent?.trim()}" ${element.scrollWidth}>${element.clientWidth}`),
  );
  expect(overflowing, 'text overflows its box').toEqual([]);
}

/** Visible and not clipped off either horizontal edge of the viewport. */
export async function expectWithinViewportWidth(page: Page, target: Locator): Promise<void> {
  await expect(target).toBeVisible();
  const box = await target.boundingBox();
  const width = page.viewportSize()?.width ?? 0;
  expect(box, 'target has a layout box').not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(width + 0.5);
}

export async function expectImageLoaded(image: Locator): Promise<void> {
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 0)).toBe(true);
}
