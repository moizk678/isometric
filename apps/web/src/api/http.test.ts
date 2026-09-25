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

  it('sets Content-Type application/json for JSON bodies but not for FormData', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const formData = new FormData();
    formData.append('file', new Blob(['x'], { type: 'text/plain' }), 'x.txt');
    await apiFetch('/upload', { method: 'POST', body: formData });

    const formHeaders = (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers;
    expect(formHeaders.has('Content-Type')).toBe(false);

    fetchMock.mockClear();
    await apiFetch('/documents', {
      method: 'POST',
      body: JSON.stringify({ name: 'doc' }),
    });

    const jsonHeaders = (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers;
    expect(jsonHeaders.get('Content-Type')).toBe('application/json');
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
