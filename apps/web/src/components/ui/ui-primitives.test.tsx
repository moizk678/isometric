import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Drawer } from './Drawer';
import { ErrorState } from './ErrorState';
import { JobStateBadge, ReviewStateBadge } from './StatusBadge';

describe('status badges', () => {
  it('renders job and review states with icon and text labels', () => {
    render(
      <div>
        <JobStateBadge state="running" />
        <ReviewStateBadge state="review_required" />
      </div>,
    );

    expect(screen.getByText('Running')).toBeTruthy();
    expect(screen.getByText('Review required')).toBeTruthy();
  });
});

describe('ErrorState', () => {
  it('shows request_id when provided', () => {
    render(<ErrorState title="Failed" message="Could not load" requestId="req-abc" />);
    expect(screen.getByText(/req-abc/)).toBeTruthy();
  });
});

describe('Drawer', () => {
  it('closes on Escape and restores focus to the trigger', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <div>
        <button type="button">Open menu</button>
        <Drawer open title="Navigation" onClose={onClose}>
          <button type="button">Inside</button>
        </Drawer>
      </div>,
    );

    const trigger = screen.getByRole('button', { name: 'Open menu' });
    trigger.focus();

    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
