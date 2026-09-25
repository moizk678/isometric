import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildUpstreamUrl, forwardToApi, resolveProxyEnv } from './api-proxy';

describe('resolveProxyEnv', () => {
  it('defaults API origin and owner id for local development', () => {
    expect(resolveProxyEnv({})).toEqual({
      apiOrigin: 'http://127.0.0.1:8000',
      ownerId: 'dev-owner',
    });
  });

  it('reads API_ORIGIN and DEV_OWNER_ID from the environment', () => {
    expect(
      resolveProxyEnv({
        API_ORIGIN: 'http://api.test/',
        DEV_OWNER_ID: 'owner-123',
      }),
    ).toEqual({
      apiOrigin: 'http://api.test',
      ownerId: 'owner-123',
    });
  });
});

describe('buildUpstreamUrl', () => {
  it('encodes path segments and preserves query strings', () => {
    expect(buildUpstreamUrl('http://127.0.0.1:8000', ['documents', 'abc'], '?limit=10')).toBe(
      'http://127.0.0.1:8000/api/v1/documents/abc?limit=10',
    );
  });
});

describe('forwardToApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('forwards method, query, body, and injects X-Owner-Id', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 201,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new Request('http://localhost:3000/api/v1/jobs?watch=1', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ document_id: 'doc-1' }),
    });

    const response = await forwardToApi(request, ['jobs'], {
      apiOrigin: 'http://127.0.0.1:8000',
      ownerId: 'dev-owner',
    });

    expect(response.status).toBe(201);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('http://127.0.0.1:8000/api/v1/jobs?watch=1');
    expect(init.method).toBe('POST');
    expect((init.headers as Headers).get('X-Owner-Id')).toBe('dev-owner');
    expect(init.body).toBe(request.body);
  });
});
