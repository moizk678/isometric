'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiFetch } from '@/api/http';
import type { components } from '@/api/schema.d';

export type DrawingReadingResponse = components['schemas']['DrawingReadingResponse'];
export type DrawingReadingGroup = components['schemas']['DrawingReadingGroup'];
export type DrawingReadingRow = components['schemas']['DrawingReadingRow'];

const POLL_MS = 750;

function drawingReadingPath(documentId: string): string {
  return `/api/v1/documents/${encodeURIComponent(documentId)}/drawing-reading`;
}

export function fetchDrawingReading(documentId: string): Promise<DrawingReadingResponse> {
  return apiFetch<DrawingReadingResponse>(drawingReadingPath(documentId));
}

export function isDrawingReadingPending(reading: DrawingReadingResponse | null): boolean {
  return reading?.status === 'pending';
}

export type DrawingReadingState = {
  reading: DrawingReadingResponse | null;
  loading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
};

function isTransientError(error: ApiError): boolean {
  return error.status === 0 || error.status === 408 || error.status === 429 || error.status >= 500;
}

export function useDrawingReading(documentId: string): DrawingReadingState {
  const [reading, setReading] = useState<DrawingReadingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const readingRef = useRef<DrawingReadingResponse | null>(null);

  const fetchReading = useCallback(async (): Promise<DrawingReadingResponse | ApiError> => {
    try {
      const next = await fetchDrawingReading(documentId);
      setError(null);
      readingRef.current = next;
      setReading(next);
      return next;
    } catch (err) {
      const apiError =
        err instanceof ApiError ? err : new ApiError(0, 'unknown_error', 'Could not load drawing reading', null);
      setError(apiError);
      return apiError;
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchReading();
  }, [fetchReading]);

  useEffect(() => {
    let cancelled = false;

    const schedule = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        void tick();
      }, POLL_MS);
    };

    const tick = async () => {
      if (cancelled) {
        return;
      }
      const next = await fetchReading();
      if (cancelled) {
        return;
      }
      if (next instanceof ApiError) {
        if (!isTransientError(next)) {
          return;
        }
        schedule();
        return;
      }
      if (next.status === 'pending') {
        schedule();
      }
    };

    setLoading(true);
    void tick();

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [fetchReading]);

  return { reading, loading, error, refresh };
}
