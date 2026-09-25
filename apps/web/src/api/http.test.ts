import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from './http';

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls same-origin /api/v1 paths and returns JSON', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const data = await apiFetch<{ items: unknown[] }>('/documents');
    expect(data).toEqual({ items: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/documents',
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
  });

  it('throws ApiError with code and request_id from the error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            code: 'invalid_request',
            message: 'Bad input',
            request_id: 'req-42',
          }),
          { status: 400, headers: { 'content-type': 'application/json' } },
        ),
      ),
    );

    await expect(apiFetch('/documents')).rejects.toEqual(
      expect.objectContaining<Partial<ApiError>>({
        status: 400,
        code: 'invalid_request',
        requestId: 'req-42',
        message: 'Bad input',
      }),
    );
  });
});
