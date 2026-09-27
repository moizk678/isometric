import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ProcessingTimeline } from '@/components/job/ProcessingTimeline';

afterEach(() => {
  cleanup();
});

describe('ProcessingTimeline', () => {
  it('highlights the trace phase for extract_centerlines', () => {
    render(<ProcessingTimeline stage="extract_centerlines" attempt={1} />);

    expect(screen.getByTestId('processing-phase-trace').getAttribute('data-phase-state')).toBe('active');
    expect(screen.getByTestId('processing-phase-prepare').getAttribute('data-phase-state')).toBe('complete');
  });

  it('falls back to indeterminate progress for unknown stages', () => {
    render(<ProcessingTimeline stage="extract" attempt={2} />);

    expect(screen.getByRole('progressbar', { name: 'Processing' })).toBeTruthy();
    expect(screen.queryByTestId('processing-phase-trace')).toBeNull();
    expect(screen.getByText(/Attempt 2/)).toBeTruthy();
  });
});
