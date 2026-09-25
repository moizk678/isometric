import { http, HttpResponse } from 'msw';
import type { components } from '@/api/schema.d';

type DocumentListItem = components['schemas']['DocumentListItem'];
type DocumentListResponse = components['schemas']['DocumentListResponse'];
type DocumentCreateResponse = components['schemas']['DocumentCreateResponse'];
type ErrorResponse = components['schemas']['ErrorResponse'];

export const defaultDocumentItems: DocumentListItem[] = [
  {
    document_id: 'doc-1',
    created_at: '2026-03-20T10:00:00.000Z',
    current_revision_id: 'rev-1',
    review_state: 'review_required',
    original_filename: 'line-a-isometric.png',
    profile_id: 'piping_isometric',
    latest_job: { id: 'job-1', state: 'succeeded', stage: 'publish' },
  },
];

export function makeDocumentListResponse(
  items: DocumentListItem[],
  limit = 20,
  offset = 0,
): DocumentListResponse {
  return { items, limit, offset };
}

export const documentHandlers = [
  http.get('/api/v1/documents', ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? '20');
    const offset = Number(url.searchParams.get('offset') ?? '0');
    const items = defaultDocumentItems.slice(offset, offset + limit);
    return HttpResponse.json(makeDocumentListResponse(items, limit, offset));
  }),

  http.post('/api/v1/documents', async ({ request }) => {
    const idempotencyKey = request.headers.get('Idempotency-Key');
    if (!idempotencyKey) {
      const body: ErrorResponse = {
        code: 'invalid_request',
        message: 'Idempotency-Key is required',
        request_id: 'req-missing-key',
      };
      return HttpResponse.json(body, { status: 400 });
    }

    const response: DocumentCreateResponse = {
      document_id: 'doc-new',
      job_id: 'job-new',
      status: 'queued',
    };
    return HttpResponse.json(response, { status: 202 });
  }),
];
