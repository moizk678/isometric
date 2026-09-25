import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { makeWorkbenchReviewItems, makeWorkbenchScene } from '@/test/msw/handlers/revisions';
import { ReviewPane } from './ReviewPane';

afterEach(() => cleanup());

function renderPane(selectedObjectId: string | null = null) {
  const scene = makeWorkbenchScene();
  const reviewItems = makeWorkbenchReviewItems(scene).items;
  const onActivateObject = vi.fn();
  const utils = render(
    <ReviewPane
      scene={scene}
      reviewItems={[
        ...reviewItems,
        {
          id: 'item-orphan',
          issue_key: 'orphan',
          object_id: null,
          issue_type: 'unlinked_issue',
          severity: 'low',
          state: 'open',
        },
      ]}
      selectedObjectId={selectedObjectId}
      onActivateObject={onActivateObject}
    />,
  );
  return { ...utils, onActivateObject, user: userEvent.setup() };
}

describe('ReviewPane', () => {
  it('lists review item fields and scene objects', () => {
    renderPane();
    const items = screen.getByRole('listbox', { name: 'Review items' });
    expect(within(items).getAllByRole('option')).toHaveLength(5);
    expect(within(items).getByText('fixture_low_confidence:obj-p1')).toBeTruthy();
    expect(within(items).getAllByText('High').length).toBeGreaterThan(0);
    expect(within(items).getAllByText('State: open').length).toBe(5);

    const objects = screen.getByRole('listbox', { name: 'Scene objects' });
    expect(within(objects).getAllByRole('option')).toHaveLength(4);
    expect(within(objects).getByText('Annotation “2" CS”')).toBeTruthy();
  });

  it('moves the active option with arrows, Home, and End and activates on Enter', async () => {
    const { user, onActivateObject } = renderPane();
    const objects = screen.getByRole('listbox', { name: 'Scene objects' });
    objects.focus();

    await user.keyboard('{End}{ArrowUp}{Enter}');
    expect(onActivateObject).toHaveBeenLastCalledWith('obj-p1');
    const active = objects.getAttribute('aria-activedescendant');
    expect(document.getElementById(active!)?.getAttribute('aria-label')).toMatch(/Pipe segment/);

    await user.keyboard('{Home} ');
    expect(onActivateObject).toHaveBeenLastCalledWith('obj-j1');
  });

  it('marks the selected object in both lists and shows its evidence', () => {
    renderPane('obj-j2');
    const selectedObject = within(screen.getByRole('listbox', { name: 'Scene objects' })).getByRole('option', {
      selected: true,
    });
    expect(selectedObject.getAttribute('aria-label')).toMatch(/Junction · elbow, machine, score 0.70/);
    const selectedItem = within(screen.getByRole('listbox', { name: 'Review items' })).getByRole('option', {
      selected: true,
    });
    expect(selectedItem.getAttribute('aria-label')).toMatch(/medium severity/);

    expect(screen.getByText('vectorize')).toBeTruthy();
    expect(screen.getByText('artifact-j2')).toBeTruthy();
    expect(screen.getByText('Score').nextElementSibling?.textContent).toBe('0.70');
    expect(screen.getByText('Interpretation').nextElementSibling?.textContent).toBe('machine');
  });

  it('does not activate a review item without an object', async () => {
    const { user, onActivateObject } = renderPane();
    const items = screen.getByRole('listbox', { name: 'Review items' });
    items.focus();
    await user.keyboard('{End}{Enter}');
    expect(onActivateObject).not.toHaveBeenCalled();
  });
});
