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

export function retryDrawingReading(documentId: string): Promise<{ document_id: string; job_id: string; status: string }> {
  return apiFetch(`${drawingReadingPath(documentId)}/retry`, { method: 'POST' });
}

export function isDrawingReadingPending(reading: DrawingReadingResponse | null): boolean {
  return reading?.status === 'pending';
}

export type DrawingReadingState = {
  reading: DrawingReadingResponse | null;
  loading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
  retry: () => Promise<void>;
};

function isTransientError(error: ApiError): boolean {
  return error.status === 0 || error.status === 408 || error.status === 429 || error.status >= 500;
}

export function useDrawingReading(documentId: string): DrawingReadingState {
  const [reading, setReading] = useState<DrawingReadingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [pollGeneration, setPollGeneration] = useState(0);
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

  const retry = useCallback(async () => {
    setLoading(true);
    setError(null);
    setReading({ status: 'pending' });
    try {
      await retryDrawingReading(documentId);
    } catch (err) {
      const apiError =
        err instanceof ApiError ? err : new ApiError(0, 'unknown_error', 'Could not retry drawing reading', null);
      setError(apiError);
      setLoading(false);
      return;
    }
    setPollGeneration((value) => value + 1);
  }, [documentId]);

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
  }, [fetchReading, pollGeneration]);

  return { reading, loading, error, refresh, retry };
}
