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
      expect(screen.getByTestId('processing-timeline')).toBeTruthy();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(31_000);
    });

    expect(screen.getByTestId('job-stale-banner')).toBeTruthy();
  });

  it('keeps polling after a transient server error', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let calls = 0;
    server.use(
      http.get('/api/v1/jobs/:jobId', () => {
        calls += 1;
        if (calls === 2) {
          return HttpResponse.json(
            { code: 'internal_error', message: 'boom', request_id: 'req-500' },
            { status: 500 },
          );
        }
        return HttpResponse.json(
          makeJobResponse({
            job_id: 'job-flaky',
            state: calls >= 3 ? 'succeeded' : 'running',
            document_id: 'doc-flaky',
          }),
        );
      }),
    );

    render(<JobProgressView jobId="job-flaky" />);
    await waitFor(() => {
      expect(screen.getByTestId('processing-timeline')).toBeTruthy();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(calls).toBeGreaterThanOrEqual(3);
    expect(screen.getByRole('link', { name: 'Open document' })).toBeTruthy();
  });

  it('stops polling when the job is not found', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let calls = 0;
    server.use(
      http.get('/api/v1/jobs/:jobId', () => {
        calls += 1;
        return HttpResponse.json(
          { code: 'not_found', message: 'Job not found', request_id: 'req-404' },
          { status: 404 },
        );
      }),
    );

    render(<JobProgressView jobId="job-gone" />);
    await waitFor(() => {
      expect(screen.getByText('Could not load job')).toBeTruthy();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(calls).toBe(1);
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
