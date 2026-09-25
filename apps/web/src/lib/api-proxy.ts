export type ProxyEnv = {
  apiOrigin: string;
  ownerId: string;
};

// Node's fetch throws on several of these, and none of them may be forwarded by a proxy.
const HOP_BY_HOP_HEADERS = [
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'expect',
  'host',
];

export function resolveProxyEnv(env: Record<string, string | undefined> = process.env): ProxyEnv {
  const apiOrigin = (env.API_ORIGIN ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
  const ownerId = env.DEV_OWNER_ID ?? 'dev-owner';
  return { apiOrigin, ownerId };
}

export function buildUpstreamUrl(apiOrigin: string, pathSegments: string[], search: string): string {
  const path = pathSegments.map((segment) => encodeURIComponent(segment)).join('/');
  const suffix = search ? (search.startsWith('?') ? search : `?${search}`) : '';
  return `${apiOrigin}/api/v1/${path}${suffix}`;
}

function errorEnvelope(status: number, code: string, message: string): Response {
  return new Response(JSON.stringify({ code, message, request_id: null }), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

export async function forwardToApi(
  request: Request,
  pathSegments: string[],
  env: ProxyEnv,
): Promise<Response> {
  // URL parsing resolves "." and "..", which would let a request leave /api/v1 on the API.
  if (pathSegments.some((segment) => segment === '.' || segment === '..')) {
    return errorEnvelope(404, 'not_found', 'resource not found');
  }

  const upstreamUrl = buildUpstreamUrl(env.apiOrigin, pathSegments, new URL(request.url).search);
  const headers = new Headers(request.headers);
  for (const name of HOP_BY_HOP_HEADERS) {
    headers.delete(name);
  }
  headers.set('X-Owner-Id', env.ownerId);

  const method = request.method.toUpperCase();
  const hasBody = method !== 'GET' && method !== 'HEAD';

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method,
      headers,
      body: hasBody ? request.body : undefined,
      // @ts-expect-error duplex required for streaming bodies in Node 18+
      duplex: hasBody ? 'half' : undefined,
    });
  } catch {
    return errorEnvelope(502, 'upstream_unavailable', 'the API is unavailable');
  }

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');
  // fetch has already decoded the body, so the upstream encoding and length no longer apply.
  responseHeaders.delete('content-encoding');
  responseHeaders.delete('content-length');

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}
