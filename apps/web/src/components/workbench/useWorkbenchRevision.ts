'use client';

import { useCallback, useState } from 'react';
import { ApiError } from '@/api/http';
import {
  postRevisionEdits,
  resolveReviewItem,
  type ResolveReviewItemRequest,
  type RevisionEditsRequest,
  type RevisionMutationResponse,
} from '@/api/revisions';

export type SaveState = 'idle' | 'pending' | 'saved' | 'error';

export function useWorkbenchRevision(documentId: string, revisionId: string, onRevisionChange: (nextId: string) => void) {
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);

  const applyMutation = useCallback(
    async (run: () => Promise<RevisionMutationResponse>) => {
      setSaveState('pending');
      setSaveError(null);
      setRequestId(null);
      try {
        const result = await run();
        setSaveState('saved');
        onRevisionChange(result.revision_id);
        return result;
      } catch (error) {
        setSaveState('error');
        if (error instanceof ApiError) {
          setSaveError(error.message);
          setRequestId(error.requestId);
        } else {
          setSaveError(error instanceof Error ? error.message : String(error));
        }
        throw error;
      }
    },
    [onRevisionChange],
  );

  const postEdits = useCallback(
    (body: RevisionEditsRequest) =>
      applyMutation(() => postRevisionEdits(documentId, revisionId, body)),
    [applyMutation, documentId, revisionId],
  );

  const resolveItem = useCallback(
    (itemId: string, body: ResolveReviewItemRequest) =>
      applyMutation(() => resolveReviewItem(documentId, revisionId, itemId, body)),
    [applyMutation, documentId, revisionId],
  );

  return { saveState, saveError, requestId, postEdits, resolveItem, resetSaveState: () => setSaveState('idle') };
}
