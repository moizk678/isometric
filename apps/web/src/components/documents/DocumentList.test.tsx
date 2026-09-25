import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { DocumentList } from '@/components/documents/DocumentList';
import { makeDocumentListResponse } from '@/test/msw/handlers/documents';
import { createTestServer } from '@/test/msw/server';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

const server = createTestServer();

beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
  push.mockReset();
});
afterAll(() => server.close());

describe('DocumentList', () => {
  it('shows loading then populated rows', async () => {
    render(<DocumentList />);
    expect(screen.getByText(/Loading documents/)).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText('line-a-isometric.png')).toBeTruthy();
    });
    expect(screen.getByText('Succeeded')).toBeTruthy();
    expect(screen.getByText('Review required')).toBeTruthy();
  });

  it('shows empty state when there are no documents', async () => {
    server.use(
      http.get('/api/v1/documents', () =>
        HttpResponse.json(makeDocumentListResponse([], 20, 0)),
      ),
    );
    render(<DocumentList />);
    await waitFor(() => {
      expect(screen.getByText('No documents yet')).toBeTruthy();
    });
  });

  it('shows error state with request id', async () => {
    server.use(
      http.get('/api/v1/documents', () =>
        HttpResponse.json(
          { code: 'internal_error', message: 'List failed', request_id: 'req-docs-list' },
          { status: 500 },
        ),
      ),
    );
    render(<DocumentList />);
    await waitFor(() => {
      expect(screen.getByText(/req-docs-list/)).toBeTruthy();
    });
  });

  it('navigates to upload from empty state action', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('/api/v1/documents', () =>
        HttpResponse.json(makeDocumentListResponse([], 20, 0)),
      ),
    );
    render(<DocumentList />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Upload drawing' })).toBeTruthy();
    });
    await user.click(screen.getAllByRole('button', { name: 'Upload drawing' })[0]);
    expect(push).toHaveBeenCalledWith('/upload');
  });
});
