export type ProxyEnv = {
  apiOrigin: string;
  ownerId: string;
};

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

export async function forwardToApi(
  request: Request,
  pathSegments: string[],
  env: ProxyEnv,
): Promise<Response> {
  const upstreamUrl = buildUpstreamUrl(env.apiOrigin, pathSegments, new URL(request.url).search);
  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('connection');
  headers.set('X-Owner-Id', env.ownerId);

  const method = request.method.toUpperCase();
  const hasBody = method !== 'GET' && method !== 'HEAD';

  const upstream = await fetch(upstreamUrl, {
    method,
    headers,
    body: hasBody ? request.body : undefined,
    // @ts-expect-error duplex required for streaming bodies in Node 18+
    duplex: hasBody ? 'half' : undefined,
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}
