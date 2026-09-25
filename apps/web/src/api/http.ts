export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

type ApiErrorBody = {
  code?: string;
  message?: string;
  request_id?: string;
};

function buildUrl(path: string, searchParams?: Record<string, string | number | boolean | undefined>): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(normalized, 'http://localhost');
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.pathname + url.search;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { searchParams?: Record<string, string | number | boolean | undefined> },
): Promise<T> {
  const apiPath = path.startsWith('/api/v1') ? path : `/api/v1${path.startsWith('/') ? path : `/${path}`}`;
  const url = buildUrl(apiPath, init?.searchParams);

  const { searchParams: _ignored, body, ...rest } = init ?? {};
  const headers = new Headers(rest.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (body && !headers.has('Content-Type') && !(body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...rest,
    body,
    headers,
  });

  if (!response.ok) {
    let parsed: ApiErrorBody = {};
    try {
      parsed = (await response.json()) as ApiErrorBody;
    } catch {
      parsed = {};
    }
    throw new ApiError(
      response.status,
      parsed.code ?? 'unknown_error',
      parsed.message ?? response.statusText,
      parsed.request_id ?? null,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  return (await response.text()) as T;
}
