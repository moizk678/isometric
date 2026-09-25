import { apiFetch } from '@/api/http';
import type { components } from '@/api/schema.d';

export type DocumentListResponse = components['schemas']['DocumentListResponse'];
export type DocumentListItem = components['schemas']['DocumentListItem'];
export type DocumentCreateResponse = components['schemas']['DocumentCreateResponse'];

export type ListDocumentsParams = {
  limit?: number;
  offset?: number;
};

export async function listDocuments(params: ListDocumentsParams = {}): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>('/documents', {
    searchParams: {
      limit: params.limit,
      offset: params.offset,
    },
  });
}

export type CreateDocumentOptions = {
  profileId?: string;
  idempotencyKey: string;
};

export async function createDocument(
  file: File,
  options: CreateDocumentOptions,
): Promise<DocumentCreateResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('profile_id', options.profileId ?? 'piping_isometric');
  formData.append('options_json', '{}');

  return apiFetch<DocumentCreateResponse>('/documents', {
    method: 'POST',
    body: formData,
    headers: {
      'Idempotency-Key': options.idempotencyKey,
    },
  });
}
