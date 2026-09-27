'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '@/api/http';
import { getJob, isTerminalJobState, type JobResponse } from '@/api/jobs';

const POLL_MS = 750;
const STALE_THRESHOLD_MS = 30_000;

export type JobPollingState = {
  job: JobResponse | null;
  loading: boolean;
  error: ApiError | null;
  stale: boolean;
  refresh: () => Promise<void>;
};

/** Network failures, timeouts, rate limits, and 5xx may clear up; 403/404 will not. */
function isTransientError(error: ApiError): boolean {
  return error.status === 0 || error.status === 408 || error.status === 429 || error.status >= 500;
}

function computeStale(job: JobResponse, unchangedSince: number | null): boolean {
  if (isTerminalJobState(job.state)) {
    return false;
  }
  if (unchangedSince === null) {
    return false;
  }
  return Date.now() - unchangedSince >= STALE_THRESHOLD_MS;
}

export function useJobPolling(jobId: string | null): JobPollingState {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [stale, setStale] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastUpdatedAtRef = useRef<string | null>(null);
  const unchangedSinceRef = useRef<number | null>(null);
  const jobRef = useRef<JobResponse | null>(null);

  const applyJob = useCallback((next: JobResponse) => {
    jobRef.current = next;
    if (isTerminalJobState(next.state)) {
      lastUpdatedAtRef.current = next.updated_at;
      unchangedSinceRef.current = null;
      setStale(false);
    } else if (lastUpdatedAtRef.current !== next.updated_at) {
      lastUpdatedAtRef.current = next.updated_at;
      unchangedSinceRef.current = Date.now();
      setStale(false);
    } else if (unchangedSinceRef.current === null) {
      unchangedSinceRef.current = Date.now();
      setStale(false);
    } else {
      setStale(computeStale(next, unchangedSinceRef.current));
    }
    setJob(next);
  }, []);

  const fetchJob = useCallback(async (): Promise<JobResponse | ApiError> => {
    if (!jobId) {
      setLoading(false);
      return new ApiError(0, 'no_job', 'No job id', null);
    }
    try {
      const next = await getJob(jobId);
      setError(null);
      applyJob(next);
      return next;
    } catch (err) {
      const apiError =
        err instanceof ApiError ? err : new ApiError(0, 'unknown_error', 'Could not load job', null);
      setError(apiError);
      return apiError;
    } finally {
      setLoading(false);
    }
  }, [applyJob, jobId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchJob();
  }, [fetchJob]);

  useEffect(() => {
    if (!jobId) {
      setLoading(false);
      return undefined;
    }

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
      const next = await fetchJob();
      if (cancelled) {
        return;
      }
      if (next instanceof ApiError ? !isTransientError(next) : isTerminalJobState(next.state)) {
        return;
      }
      schedule();
    };

    lastUpdatedAtRef.current = null;
    unchangedSinceRef.current = null;
    setLoading(true);
    void tick();

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [fetchJob, jobId]);

  useEffect(() => {
    const interval = setInterval(() => {
      const current = jobRef.current;
      if (!current || isTerminalJobState(current.state)) {
        return;
      }
      setStale(computeStale(current, unchangedSinceRef.current));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return { job, loading, error, stale, refresh };
}
