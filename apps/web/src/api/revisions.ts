import { apiFetch } from '@/api/http';
import type { components } from '@/api/schema.d';
import type { DrawingScene } from '../../../../packages/scene-schema/src/drawing-scene';

export type DocumentDetail = components['schemas']['DocumentDetailResponse'];
export type ReviewItem = components['schemas']['ReviewItem'];
export type ReviewItemListResponse = components['schemas']['ReviewItemListResponse'];
export type RevisionMutationResponse = components['schemas']['RevisionMutationResponse'];
export type RevisionEditsRequest = components['schemas']['RevisionEditsRequest'];
export type ResolveReviewItemRequest = components['schemas']['ResolveReviewItemRequest'];
export type AdoptCandidateResponse = components['schemas']['AdoptCandidateResponse'];
export type { DrawingScene };

function documentPath(documentId: string): string {
  return `/api/v1/documents/${encodeURIComponent(documentId)}`;
}

function revisionPath(documentId: string, revisionId: string): string {
  return `${documentPath(documentId)}/revisions/${encodeURIComponent(revisionId)}`;
}

export function getDocumentDetail(documentId: string): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>(documentPath(documentId));
}

export function getRevisionScene(documentId: string, revisionId: string): Promise<DrawingScene> {
  return apiFetch<DrawingScene>(`${revisionPath(documentId, revisionId)}/scene`);
}

export function getReviewItems(documentId: string, revisionId: string): Promise<ReviewItemListResponse> {
  return apiFetch<ReviewItemListResponse>(`${revisionPath(documentId, revisionId)}/review-items`);
}

/** EXIF-transposed source image; its pixel size is page.displayWidthPx x displayHeightPx. */
export function displayImageUrl(documentId: string): string {
  return `${documentPath(documentId)}/display`;
}

/** Rendered semantic SVG export. Show it with <img> only; never fetch it as markup. */
export function svgExportUrl(documentId: string, revisionId: string): string {
  return `${revisionPath(documentId, revisionId)}/exports/svg`;
}

/** Raster-faithful trace tied to a revision export when published. */
export function traceExportUrl(documentId: string, revisionId: string): string {
  return `${revisionPath(documentId, revisionId)}/exports/trace`;
}

/** Latest document-level trace (available before a revision exists). */
export function documentTraceUrl(documentId: string): string {
  return `${documentPath(documentId)}/trace`;
}

export function postRevisionEdits(
  documentId: string,
  revisionId: string,
  body: RevisionEditsRequest,
): Promise<RevisionMutationResponse> {
  return apiFetch<RevisionMutationResponse>(`${revisionPath(documentId, revisionId)}/edits`, {
    method: 'POST',
    headers: { 'If-Match': revisionId },
    body: JSON.stringify(body),
  });
}

export function resolveReviewItem(
  documentId: string,
  revisionId: string,
  itemId: string,
  body: ResolveReviewItemRequest,
): Promise<RevisionMutationResponse> {
  return apiFetch<RevisionMutationResponse>(
    `${revisionPath(documentId, revisionId)}/review-items/${encodeURIComponent(itemId)}/resolve`,
    {
      method: 'POST',
      headers: { 'If-Match': revisionId },
      body: JSON.stringify(body),
    },
  );
}

export function adoptCandidateRevision(
  documentId: string,
  currentRevisionId: string,
  candidateRevisionId: string,
): Promise<AdoptCandidateResponse> {
  return apiFetch<AdoptCandidateResponse>(`${revisionPath(documentId, currentRevisionId)}/adopt`, {
    method: 'POST',
    headers: { 'If-Match': currentRevisionId },
    body: JSON.stringify({ candidate_revision_id: candidateRevisionId }),
  });
}

export function svgDownloadName(originalFilename: string | null | undefined, documentId: string): string {
  const base = (originalFilename ?? '').trim().split(/[\\/]/).pop() ?? '';
  const stem = base.replace(/\.[^.]*$/, '').trim();
  const safe = (stem || documentId).replace(/[\u0000-\u001f<>:"|?*]/g, '_');
  return `${safe}.svg`;
}
