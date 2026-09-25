import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { JobProgressView } from '@/components/job/JobProgressView';
import { makeJobResponse } from '@/test/msw/handlers/jobs';
import { createTestServer } from '@/test/msw/server';

const server = createTestServer();

beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.useRealTimers();
});
afterAll(() => server.close());

describe('JobProgressView', () => {
  it('shows stale state when updated_at stops changing', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const frozen = '2020-01-01T00:00:00.000Z';
    server.use(
      http.get('/api/v1/jobs/:jobId', () =>
        HttpResponse.json(
          makeJobResponse({
            job_id: 'job-stale',
            state: 'running',
            stage: 'extract',
            attempt: 1,
            updated_at: frozen,
          }),
        ),
      ),
    );

    render(<JobProgressView jobId="job-stale" />);
    await waitFor(() => {
      expect(screen.getByText(/Stage:/)).toBeTruthy();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(31_000);
    });

    expect(screen.getByTestId('job-stale-banner')).toBeTruthy();
  });

  it('shows failed job error message', async () => {
    server.use(
      http.get('/api/v1/jobs/:jobId', () =>
        HttpResponse.json(
          makeJobResponse({
            job_id: 'job-failed',
            state: 'failed',
            stage: 'process',
            error_code: 'processing_failed',
            document_id: 'doc-failed',
          }),
        ),
      ),
    );

    render(<JobProgressView jobId="job-failed" />);
    await waitFor(() => {
      expect(screen.getByTestId('job-failure-message')).toBeTruthy();
    });
    expect(screen.getByText(/Processing failed unexpectedly/)).toBeTruthy();
  });
});
