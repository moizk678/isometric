import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import {
  expectImageLoaded,
  expectNoPageHorizontalScroll,
  expectTextFitsBoxes,
  expectVisibleFocus,
  expectWithinViewportWidth,
  newProxyContext,
  tabTo,
  uploadThroughProxy,
  type UploadedDocument,
} from './support/app';

const screenshotDir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'screenshots');

/** 200% zoom of a 1280 x 800 window is a 640 x 400 CSS-pixel viewport at device scale 2. */
const layouts = [
  { name: '1440', viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
  { name: '390', viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 },
  { name: '320', viewport: { width: 320, height: 568 }, deviceScaleFactor: 1 },
  { name: 'zoom-200', viewport: { width: 640, height: 400 }, deviceScaleFactor: 2 },
] as const;

const DESKTOP_SHELL_PX = 1024;
/** Below this viewport the workbench is narrower than 900 px, so it shows one canvas and a switch. */
const NARROW_WORKBENCH_VIEWPORT_PX = 900;

type Screen = {
  name: string;
  path: (document: UploadedDocument) => string;
  ready: (page: Page, document: UploadedDocument) => Promise<void>;
  primaryActions: (page: Page) => Locator[];
  focusTarget: (page: Page) => Locator;
};

const screens: Screen[] = [
  {
    name: 'documents',
    path: () => '/documents',
    ready: async (page, document) => {
      await expect(page.getByRole('link', { name: new RegExp(document.filename) })).toBeVisible();
    },
    primaryActions: (page) => [
      (page.viewportSize()?.width ?? 0) >= DESKTOP_SHELL_PX
        ? page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Upload' })
        : page.getByRole('button', { name: 'Open navigation' }),
    ],
    focusTarget: (page) => page.getByRole('main').getByRole('link').first(),
  },
  {
    name: 'upload',
    path: () => '/upload',
    ready: async (page) => {
      await expect(page.getByRole('button', { name: 'Choose files' })).toBeVisible();
    },
    primaryActions: (page) => [page.getByRole('button', { name: 'Choose files' })],
    focusTarget: (page) => page.getByRole('button', { name: 'Choose files' }),
  },
  {
    name: 'job',
    path: (document) => `/jobs/${document.jobId}`,
    ready: async (page) => {
      await expect(page.getByText('Succeeded', { exact: true })).toBeVisible();
    },
    primaryActions: (page) => [page.getByRole('link', { name: 'Open document' })],
    focusTarget: (page) => page.getByRole('link', { name: 'Open document' }),
  },
  {
    name: 'workbench',
    path: (document) => `/documents/${document.documentId}`,
    ready: async (page, document) => {
      await expect(page.getByRole('heading', { level: 1, name: document.filename })).toBeVisible();
      await expectImageLoaded(page.getByRole('img', { name: 'Original drawing, orientation corrected' }));
    },
    primaryActions: (page) =>
      (page.viewportSize()?.width ?? 0) < NARROW_WORKBENCH_VIEWPORT_PX
        ? [page.getByRole('tablist', { name: 'Canvas' }), page.getByRole('link', { name: /Download .*SVG/ })]
        : [page.getByRole('link', { name: /Download .*SVG/ })],
    focusTarget: (page) => page.getByRole('link', { name: /Download .*SVG/ }),
  },
];

let document: UploadedDocument;

test.beforeAll(async () => {
  const api = await newProxyContext(test.info().project.use.baseURL);
  document = await uploadThroughProxy(
    api,
    `e2e-north-wing-riser-isometric-drawing-level-03-revision-b-final-issue-for-review-${Date.now()}.png`,
  );
  await api.dispose();
});

for (const layout of layouts) {
  test.describe(`layout ${layout.name}`, () => {
    test.use({ viewport: layout.viewport, deviceScaleFactor: layout.deviceScaleFactor });

    for (const screen of screens) {
      test(`${screen.name} keeps primary actions and visible focus without horizontal scroll`, async ({ page }) => {
        await page.goto(screen.path(document));
        await screen.ready(page, document);

        await expectNoPageHorizontalScroll(page);
        await expectTextFitsBoxes(page);

        for (const action of screen.primaryActions(page)) {
          await action.scrollIntoViewIfNeeded();
          await expectWithinViewportWidth(page, action);
        }

        await page.evaluate(() => window.scrollTo(0, 0));
        const focusTarget = screen.focusTarget(page);
        await tabTo(page, focusTarget);
        await expectVisibleFocus(focusTarget);
        await expectNoPageHorizontalScroll(page);

        // Hide the Next.js dev-tools badge so the evidence shows only the product UI.
        await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
        await page.screenshot({
          path: path.join(screenshotDir, `${screen.name}-${layout.name}.png`),
          fullPage: true,
          animations: 'disabled',
        });
      });
    }
  });
}
