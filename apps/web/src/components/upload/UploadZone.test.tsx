import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { UploadZone } from '@/components/upload/UploadZone';
import { createTestServer } from '@/test/msw/server';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

const server = createTestServer();
let postAttempts = 0;
let capturedKey: string | null = null;

beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
  push.mockReset();
  postAttempts = 0;
  capturedKey = null;
});
afterAll(() => server.close());

function pngFile(name = 'drawing.png') {
  return new File(['pixels'], name, { type: 'image/png' });
}

describe('UploadZone', () => {
  it('retains file and idempotency key after failure and reuses key on retry', async () => {
    server.use(
      http.post('/api/v1/documents', async ({ request }) => {
        const key = request.headers.get('Idempotency-Key');
        postAttempts += 1;
        if (postAttempts === 1) {
          capturedKey = key;
          return HttpResponse.json(
            { code: 'internal_error', message: 'Upload failed', request_id: 'req-upload' },
            { status: 500 },
          );
        }
        expect(key).toBe(capturedKey);
        return HttpResponse.json(
          { document_id: 'doc-new', job_id: 'job-new', status: 'queued' },
          { status: 202 },
        );
      }),
      http.get('/api/v1/jobs/job-new', () =>
        HttpResponse.json({
          job_id: 'job-new',
          document_id: 'doc-new',
          state: 'succeeded',
          stage: 'complete',
          attempt: 1,
          progress: { stage: 'complete', attempt: 1 },
          warnings: [],
          logs: [
            {
              id: 'log-1',
              created_at: new Date().toISOString(),
              level: 'info',
              stage: 'fixture_process',
              message: 'SVG rendered',
              detail: { byte_size: 1200 },
            },
          ],
          review_state: 'review_required',
          error_code: null,
          result_revision_id: 'rev-new',
          cancel_requested: false,
          updated_at: new Date().toISOString(),
          review_item_count: 0,
        }),
      ),
    );

    const user = userEvent.setup();
    render(<UploadZone />);

    const input = screen.getByTestId('upload-file-input');
    await user.upload(input, pngFile());

    const keyBefore = screen.getByTestId('upload-idempotency-key').textContent;
    expect(keyBefore).toBeTruthy();

    await user.click(screen.getByTestId('upload-start-button'));
    await waitFor(() => {
      expect(screen.getByTestId('upload-retry-button')).toBeTruthy();
    });
    expect(screen.getByText('drawing.png')).toBeTruthy();
    expect(screen.getByTestId('upload-idempotency-key').textContent).toBe(keyBefore);

    await user.click(screen.getByTestId('upload-retry-button'));
    await waitFor(() => {
      expect(screen.getByTestId('upload-open-document')).toBeTruthy();
    });
    expect(screen.getByText('SVG rendered')).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
    expect(postAttempts).toBe(2);
  });
});
