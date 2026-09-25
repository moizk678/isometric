import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { createTestServer } from '@/test/msw/server';
import {
  WORKBENCH_DOCUMENT_ID,
  WORKBENCH_OLD_REVISION_ID,
  WORKBENCH_REVISION_ID,
  revisionHandlers,
} from '@/test/msw/handlers/revisions';
import { currentSearchParams, replaceCalls, resetNavigation } from './testing/mockNavigation';
import { installResizeObserver } from './testing/resizeObserver';
import { Workbench } from './Workbench';

vi.mock('next/navigation', async () => (await import('./testing/mockNavigation')).navigationModule);

const server = createTestServer();
const requestedUrls: string[] = [];
const PATH = `/documents/${WORKBENCH_DOCUMENT_ID}`;

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
  server.events.on('request:start', ({ request }) => {
    requestedUrls.push(new URL(request.url).pathname);
  });
});
beforeEach(() => {
  server.use(...revisionHandlers);
  requestedUrls.length = 0;
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());

function viewers() {
  return {
    original: screen.queryByRole('group', { name: 'Original drawing' }),
    svg: screen.queryByRole('group', { name: 'SVG export' }),
  };
}

async function renderWorkbench(search = '', documentId = WORKBENCH_DOCUMENT_ID) {
  resetNavigation(`/documents/${documentId}`, search);
  const user = userEvent.setup();
  render(<Workbench documentId={documentId} />);
  return user;
}

describe('Workbench at wide width', () => {
  let restoreResize: () => void;
  beforeEach(() => {
    restoreResize = installResizeObserver({ width: 1280, height: 600 });
  });
  afterEach(() => restoreResize());

  it('shows the display image and the SVG export as images with a page-sized overlay', async () => {
    await renderWorkbench();
    await screen.findByRole('heading', { name: 'line-12 iso.jpg' });

    const { original, svg } = viewers();
    expect(original).toBeTruthy();
    expect(svg).toBeTruthy();

    const displayImg = within(original!).getByRole('img', { name: /Original drawing/ });
    expect(displayImg.getAttribute('src')).toBe(`/api/v1/documents/${WORKBENCH_DOCUMENT_ID}/display`);
    expect(displayImg.className).toContain('object-contain');

    const exportUrl = `/api/v1/documents/${WORKBENCH_DOCUMENT_ID}/revisions/${WORKBENCH_REVISION_ID}/exports/svg`;
    const exportImg = within(svg!).getByRole('img', { name: /SVG export/ });
    expect(exportImg.tagName).toBe('IMG');
    expect(exportImg.getAttribute('src')).toBe(exportUrl);
    expect(exportImg.className).toContain('object-contain');

    // Page 480x640 (EXIF orientation 6 of a 640x480 source); the overlay uses page units.
    expect(within(svg!).getByTestId('svg-overlay').getAttribute('viewBox')).toBe('0 0 480 640');
    expect(within(original!).getByTestId('source-overlay').getAttribute('viewBox')).toBe('0 0 480 640');
    expect(requestedUrls).not.toContain(exportUrl);

    const download = screen.getByRole('link', { name: 'Download SVG' });
    expect(download.getAttribute('href')).toBe(exportUrl);
    expect(download.getAttribute('download')).toBe('line-12 iso.svg');
  });

  it('keyboard selection in the objects list updates the URL and both viewers', async () => {
    const user = await renderWorkbench();
    const objects = await screen.findByRole('listbox', { name: 'Scene objects' });

    objects.focus();
    await user.keyboard('{ArrowDown}{Enter}');

    expect(currentSearchParams().get('object')).toBe('obj-j2');
    expect(replaceCalls.at(-1)).toBe(`${PATH}?object=obj-j2`);

    const { original, svg } = viewers();
    expect(original!.getAttribute('data-selected-object')).toBe('obj-j2');
    expect(svg!.getAttribute('data-selected-object')).toBe('obj-j2');
    expect(within(original!).getByTestId('source-highlight').getAttribute('data-highlight-object')).toBe('obj-j2');
    expect(within(svg!).getByTestId('svg-highlight').getAttribute('data-highlight-object')).toBe('obj-j2');

    // Enter centers both viewers on the junction at page (360, 160).
    expect(original!.getAttribute('data-center')).toBe('360.00,160.00');
    expect(svg!.getAttribute('data-center')).toBe('360.00,160.00');

    const selectedOption = within(objects).getByRole('option', { selected: true });
    expect(selectedOption.getAttribute('aria-label')).toMatch(/Junction · elbow/);
    expect(screen.getByText('artifact-j2')).toBeTruthy();
  });

  it('keyboard selection in the review items list selects the item object', async () => {
    const user = await renderWorkbench();
    const items = await screen.findByRole('listbox', { name: 'Review items' });

    items.focus();
    await user.keyboard('{End}{Enter}');

    expect(currentSearchParams().get('object')).toBe('obj-n1');
    expect(viewers().svg!.getAttribute('data-selected-object')).toBe('obj-n1');
    expect(within(items).getByRole('option', { selected: true }).getAttribute('aria-label')).toMatch(/high|medium|low/);
  });

  it('a tap on an SVG hit target selects the object in both viewers', async () => {
    await renderWorkbench();
    await screen.findByRole('listbox', { name: 'Scene objects' });
    const { svg } = viewers();
    const target = svg!.querySelector('[data-object-id="obj-p1"]')!;

    fireEvent.pointerDown(target, { pointerId: 1, button: 0, pointerType: 'touch' });
    fireEvent.pointerUp(target, { pointerId: 1, button: 0, pointerType: 'touch' });

    expect(currentSearchParams().get('object')).toBe('obj-p1');
    expect(viewers().original!.getAttribute('data-selected-object')).toBe('obj-p1');
  });

  it('shares zoom between viewers through keyboard shortcuts', async () => {
    const user = await renderWorkbench();
    await screen.findByRole('listbox', { name: 'Scene objects' });
    const { original, svg } = viewers();

    original!.focus();
    await user.keyboard('+');
    expect(original!.getAttribute('data-zoom')).toBe('1.250');
    expect(svg!.getAttribute('data-zoom')).toBe('1.250');
    expect(screen.getByLabelText('Zoom level relative to fit').textContent).toBe('125%');

    svg!.focus();
    await user.keyboard('{ArrowRight}');
    expect(original!.getAttribute('data-center')).toBe(svg!.getAttribute('data-center'));
    expect(svg!.getAttribute('data-center')).not.toBe('240.00,320.00');

    await user.keyboard('0');
    expect(original!.getAttribute('data-zoom')).toBe('1.000');
    expect(svg!.getAttribute('data-center')).toBe('240.00,320.00');
  });

  it('restores selection from the URL object param', async () => {
    await renderWorkbench('object=obj-j1');
    await screen.findByRole('listbox', { name: 'Scene objects' });
    expect(viewers().original!.getAttribute('data-selected-object')).toBe('obj-j1');
    expect(viewers().svg!.getAttribute('data-selected-object')).toBe('obj-j1');
  });

  it('uses the revision URL param instead of the current revision', async () => {
    await renderWorkbench(`revision=${WORKBENCH_OLD_REVISION_ID}`);
    await screen.findByRole('listbox', { name: 'Scene objects' });
    const exportImg = within(viewers().svg!).getByRole('img', { name: /SVG export/ });
    expect(exportImg.getAttribute('src')).toContain(`/revisions/${WORKBENCH_OLD_REVISION_ID}/exports/svg`);
    expect(screen.queryByText(/· current/)).toBeNull();
  });

  it('shows the request id when the document cannot be loaded', async () => {
    await renderWorkbench('', 'doc-missing');
    expect(await screen.findByText(/req-not-found/)).toBeTruthy();
  });
});

describe('Workbench below 900px', () => {
  let restoreResize: () => void;
  beforeEach(() => {
    restoreResize = installResizeObserver({ width: 600, height: 480 });
  });
  afterEach(() => restoreResize());

  it('shows one canvas at a time and keeps zoom and selection across the switch', async () => {
    const user = await renderWorkbench();
    const originalTab = await screen.findByRole('tab', { name: 'Original' });
    expect(originalTab.getAttribute('aria-selected')).toBe('true');
    expect(viewers().original).toBeTruthy();
    expect(viewers().svg).toBeNull();
    expect(screen.queryByRole('listbox', { name: 'Scene objects' })).toBeNull();

    const reviewButton = screen.getByRole('button', { name: /Review/ });
    await user.click(reviewButton);
    const drawer = screen.getByRole('dialog', { name: 'Review' });
    const objects = within(drawer).getByRole('listbox', { name: 'Scene objects' });
    objects.focus();
    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

    expect(currentSearchParams().get('object')).toBe('obj-p1');
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(reviewButton);

    const original = viewers().original!;
    expect(original.getAttribute('data-selected-object')).toBe('obj-p1');
    original.focus();
    await user.keyboard('++');
    const zoom = original.getAttribute('data-zoom');
    const center = original.getAttribute('data-center');
    expect(zoom).toBe('1.563');

    await user.click(screen.getByRole('tab', { name: 'SVG' }));
    expect(viewers().original).toBeNull();
    const svg = viewers().svg!;
    expect(svg.getAttribute('data-selected-object')).toBe('obj-p1');
    expect(svg.getAttribute('data-zoom')).toBe(zoom);
    expect(svg.getAttribute('data-center')).toBe(center);
    expect(within(svg).getByTestId('svg-highlight').getAttribute('data-highlight-object')).toBe('obj-p1');

    await user.click(screen.getByRole('tab', { name: 'Original' }));
    expect(viewers().original!.getAttribute('data-selected-object')).toBe('obj-p1');
    expect(currentSearchParams().get('object')).toBe('obj-p1');
  });

  it('gives the canvas switch 44px targets', async () => {
    await renderWorkbench();
    const tab = await screen.findByRole('tab', { name: 'SVG' });
    expect(tab.parentElement!.className).toContain('[&>button]:h-11');
  });
});

describe('Workbench loading', () => {
  it('waits for data before showing viewers', async () => {
    const restore = installResizeObserver({ width: 1280, height: 600 });
    await renderWorkbench();
    expect(screen.getByRole('progressbar', { name: 'Loading drawing' })).toBeTruthy();
    await waitFor(() => expect(viewers().svg).toBeTruthy());
    restore();
  });
});
