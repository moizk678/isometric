'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  getDocumentDetail,
  getReviewItems,
  getRevisionScene,
  type DocumentDetail,
  type DrawingScene,
  type ReviewItem,
} from '@/api/revisions';

export type WorkbenchData =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'no-revision'; document: DocumentDetail }
  | {
      status: 'ready';
      document: DocumentDetail;
      revisionId: string;
      scene: DrawingScene;
      reviewItems: ReviewItem[];
    };

export function useWorkbenchData(documentId: string, revisionParam: string | null) {
  const [data, setData] = useState<WorkbenchData>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setData({ status: 'loading' });

    (async () => {
      const document = await getDocumentDetail(documentId);
      const revisionId = revisionParam ?? document.current_revision_id;
      if (!revisionId) {
        return { status: 'no-revision', document } as const;
      }
      const [scene, review] = await Promise.all([
        getRevisionScene(documentId, revisionId),
        getReviewItems(documentId, revisionId),
      ]);
      return { status: 'ready', document, revisionId, scene, reviewItems: review.items } as const;
    })().then(
      (next) => {
        if (!cancelled) setData(next);
      },
      (error: unknown) => {
        if (!cancelled) {
          setData({ status: 'error', error: error instanceof Error ? error : new Error(String(error)) });
        }
      },
    );

    return () => {
      cancelled = true;
    };
  }, [documentId, revisionParam, attempt]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { data, retry };
}
