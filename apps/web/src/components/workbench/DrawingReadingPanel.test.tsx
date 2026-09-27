import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/http';
import type { DrawingReadingResponse } from '@/api/drawingReading';
import { DrawingReadingPanel } from './DrawingReadingPanel';

afterEach(() => cleanup());

const readySample: DrawingReadingResponse = {
  status: 'ready',
  groups: [
    { id: 'dimensions', title: 'Dimensions', rows: [{ location: 'Run A', reading: '6"' }] },
    { id: 'connections', title: 'Connections', rows: [] },
    { id: 'components', title: 'Components', rows: [] },
    { id: 'handwriting', title: 'Other handwriting', rows: [] },
  ],
};

describe('DrawingReadingPanel', () => {
  it('shows progress while loading without data', () => {
    render(<DrawingReadingPanel reading={null} loading error={null} />);
    expect(screen.getByRole('progressbar', { name: 'Reading the drawing' })).toBeTruthy();
  });

  it('shows progress while pending', () => {
    render(<DrawingReadingPanel reading={{ status: 'pending' }} loading={false} error={null} />);
    expect(screen.getByRole('progressbar', { name: 'Reading the drawing' })).toBeTruthy();
  });

  it('renders ready groups with empty group copy', () => {
    render(<DrawingReadingPanel reading={readySample} loading={false} error={null} />);
    expect(screen.getByRole('region', { name: 'Drawing reading' })).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: 'Location' })).toBeTruthy();
    expect(screen.getByText('Run A')).toBeTruthy();
    expect(screen.getByText('6"')).toBeTruthy();
    expect(screen.getAllByText('None found.')).toHaveLength(3);
  });

  it('shows disabled copy', () => {
    render(<DrawingReadingPanel reading={{ status: 'disabled' }} loading={false} error={null} />);
    expect(screen.getByText('Drawing reading is turned off')).toBeTruthy();
  });

  it('shows absent copy', () => {
    render(<DrawingReadingPanel reading={{ status: 'absent' }} loading={false} error={null} />);
    expect(screen.getByText('No reading for this drawing')).toBeTruthy();
  });

  it('shows unavailable error with code', () => {
    render(
      <DrawingReadingPanel reading={{ status: 'unavailable', error_code: 'missing_page' }} loading={false} error={null} />,
    );
    expect(screen.getByText('Drawing reading unavailable')).toBeTruthy();
    expect(screen.getByText(/source page image/)).toBeTruthy();
  });

  it('shows fetch error with retry', async () => {
    const onRetry = vi.fn();
    render(
      <DrawingReadingPanel
        reading={null}
        loading={false}
        error={new ApiError(500, 'server_error', 'Server blew up', 'req-500')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Could not load drawing reading')).toBeTruthy();
    screen.getByRole('button', { name: 'Try again' }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
