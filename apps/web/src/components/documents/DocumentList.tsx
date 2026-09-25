'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '@/api/http';
import { listDocuments, type DocumentListItem } from '@/api/documents';
import { DocumentListRow } from '@/components/documents/DocumentListRow';
import { Button, EmptyState, ErrorState, Panel } from '@/components/ui';

const PAGE_SIZE = 20;

export function DocumentList() {
  const router = useRouter();
  const [items, setItems] = useState<DocumentListItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async (nextOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await listDocuments({ limit: PAGE_SIZE, offset: nextOffset });
      setItems(response.items);
      setOffset(response.offset);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'unknown_error', 'Could not load documents', null));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(0);
  }, [load]);

  if (loading) {
    return (
      <Panel title="Documents" aria-busy="true" aria-live="polite">
        <p className="text-sm text-ink-secondary">Loading documents…</p>
        <ul className="mt-4 flex flex-col gap-2">
          {[0, 1, 2].map((key) => (
            <li key={key} className="h-[72px] animate-pulse rounded-[24px] bg-surface-inset motion-reduce:animate-none" />
          ))}
        </ul>
      </Panel>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load documents"
        message={error.message}
        requestId={error.requestId}
        onRetry={() => {
          void load(offset);
        }}
      />
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="No documents yet"
        description="Upload your first isometric drawing to start review."
        actionLabel="Upload drawing"
        onAction={() => {
          router.push('/upload');
        }}
      />
    );
  }

  const hasPrevious = offset > 0;
  const hasNext = items.length === PAGE_SIZE;

  return (
    <Panel
      title="Documents"
      actions={
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="compact"
            disabled={!hasPrevious}
            onClick={() => {
              void load(Math.max(0, offset - PAGE_SIZE));
            }}
          >
            Previous
          </Button>
          <Button
            variant="secondary"
            size="compact"
            disabled={!hasNext}
            onClick={() => {
              void load(offset + PAGE_SIZE);
            }}
          >
            Next
          </Button>
        </div>
      }
    >
      <ul className="m-0 flex min-w-0 list-none flex-col gap-2 p-0">
        {items.map((item) => (
          <DocumentListRow key={item.document_id} item={item} />
        ))}
      </ul>
    </Panel>
  );
}
