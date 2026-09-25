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

  it('overrides a client-supplied X-Owner-Id', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await forwardToApi(
      new Request('http://localhost:3000/api/v1/documents', { headers: { 'X-Owner-Id': 'someone-else' } }),
      ['documents'],
      { apiOrigin: 'http://127.0.0.1:8000', ownerId: 'dev-owner' },
    );

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init.headers as Headers).get('X-Owner-Id')).toBe('dev-owner');
  });

  it('drops hop-by-hop request headers that Node fetch rejects', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const request = new Request('http://localhost:3000/api/v1/documents', {
      method: 'POST',
      headers: { 'keep-alive': 'timeout=5', expect: '100-continue', upgrade: 'h2c', te: 'trailers' },
      body: 'x',
    });
    await forwardToApi(request, ['documents'], { apiOrigin: 'http://127.0.0.1:8000', ownerId: 'dev-owner' });

    const headers = fetchMock.mock.calls[0]![1].headers as Headers;
    for (const name of ['keep-alive', 'expect', 'upgrade', 'te', 'transfer-encoding', 'connection']) {
      expect(headers.has(name), name).toBe(false);
    }
  });

  it('refuses dot segments so requests cannot escape /api/v1', async () => {
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    for (const segments of [['..', 'health'], ['documents', '.', 'x'], ['documents', '..', '..', 'docs']]) {
      const response = await forwardToApi(new Request('http://localhost:3000/api/v1/x'), segments, {
        apiOrigin: 'http://127.0.0.1:8000',
        ownerId: 'dev-owner',
      });
      expect(response.status).toBe(404);
      expect(((await response.json()) as { code: string }).code).toBe('not_found');
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('drops content-encoding and content-length because fetch already decoded the body', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response('{"ok":true}', {
            status: 200,
            headers: { 'content-type': 'application/json', 'content-encoding': 'gzip', 'content-length': '31' },
          }),
      ),
    );

    const response = await forwardToApi(new Request('http://localhost:3000/api/v1/documents'), ['documents'], {
      apiOrigin: 'http://127.0.0.1:8000',
      ownerId: 'dev-owner',
    });

    expect(response.headers.has('content-encoding')).toBe(false);
    expect(response.headers.has('content-length')).toBe(false);
    expect(response.headers.get('content-type')).toBe('application/json');
    expect(await response.json()).toEqual({ ok: true });
  });

  it('returns a 502 error envelope when the API is unreachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('fetch failed');
      }),
    );

    const response = await forwardToApi(new Request('http://localhost:3000/api/v1/documents'), ['documents'], {
      apiOrigin: 'http://127.0.0.1:8000',
      ownerId: 'dev-owner',
    });

    expect(response.status).toBe(502);
    const body = (await response.json()) as { code: string; message: string; request_id: string | null };
    expect(body.code).toBe('upstream_unavailable');
    expect(body.message).not.toContain('127.0.0.1');
  });
});
