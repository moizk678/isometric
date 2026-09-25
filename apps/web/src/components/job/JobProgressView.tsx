'use client';

import Link from 'next/link';
import { useState } from 'react';
import { cancelJob, isTerminalJobState, jobErrorMessage } from '@/api/jobs';
import { useJobPolling } from '@/components/job/useJobPolling';
import { parseJobState } from '@/components/documents/parseJobState';
import { parseReviewState } from '@/components/documents/parseReviewState';
import {
  Button,
  ErrorState,
  JobStateBadge,
  Panel,
  ProgressBar,
  ReviewStateBadge,
  StatusBadgeNeutral,
} from '@/components/ui';

export type JobProgressViewProps = {
  jobId: string;
};

export function JobProgressView({ jobId }: JobProgressViewProps) {
  const { job, loading, error, stale, refresh } = useJobPolling(jobId);
  const [canceling, setCanceling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  if (loading && !job) {
    return (
      <Panel title="Job progress" aria-busy="true">
        <ProgressBar label="Loading job status" />
      </Panel>
    );
  }

  if (error && !job) {
    return (
      <ErrorState
        title="Could not load job"
        message={error.message}
        requestId={error.requestId}
        onRetry={() => {
          void refresh();
        }}
      />
    );
  }

  if (!job) {
    return null;
  }

  const jobState = parseJobState(job.state);
  const reviewState = parseReviewState(job.review_state);
  const terminal = isTerminalJobState(job.state);
  const stageLabel = job.progress.stage ?? job.stage ?? 'unknown';
  const attempt = job.progress.attempt ?? job.attempt;
  const failureMessage = job.state === 'failed' ? jobErrorMessage(job.error_code) : null;

  const onCancel = async () => {
    setCanceling(true);
    setCancelError(null);
    try {
      await cancelJob(jobId);
      await refresh();
    } catch {
      setCancelError('Could not cancel this job. Try again.');
    } finally {
      setCanceling(false);
    }
  };

  return (
    <Panel
      title="Job progress"
      description={`Job ${jobId}`}
      actions={
        !terminal && !job.cancel_requested ? (
          <Button variant="secondary" loading={canceling} onClick={() => void onCancel()}>
            Cancel job
          </Button>
        ) : null
      }
    >
      <div className="min-w-0 space-y-4">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {jobState ? <JobStateBadge state={jobState} /> : <StatusBadgeNeutral label={job.state} />}
          {reviewState ? <ReviewStateBadge state={reviewState} /> : null}
        </div>

        {!terminal ? (
          <>
            <p className="m-0 text-sm leading-5 text-ink-primary">
              Stage: <span className="break-words">{stageLabel}</span> · Attempt {attempt}
            </p>
            <ProgressBar label="Processing" />
          </>
        ) : (
          <p className="m-0 text-sm leading-5 text-ink-secondary">
            Final stage: <span className="break-words text-ink-primary">{stageLabel}</span> · Attempt {attempt}
          </p>
        )}

        {stale && !terminal ? (
          <div
            className="rounded-[20px] bg-surface-inset p-4 text-sm leading-5 text-ink-primary"
            role="status"
            data-testid="job-stale-banner"
          >
            This job has not updated in over 30 seconds. It may still be processing, or it may be stuck.
          </div>
        ) : null}

        {job.cancel_requested && !terminal ? (
          <p className="text-sm text-ink-secondary">Cancellation requested…</p>
        ) : null}

        {cancelError ? <p className="text-sm text-ink-danger" role="alert">{cancelError}</p> : null}

        {failureMessage ? (
          <div className="rounded-[20px] bg-surface-inset p-4" data-testid="job-failure-message">
            <p className="m-0 text-sm leading-5 text-ink-primary">{failureMessage}</p>
            {job.error_code ? (
              <p className="mt-1 text-xs leading-4 text-ink-muted">Error code: {job.error_code}</p>
            ) : null}
          </div>
        ) : null}

        {job.state === 'succeeded' ? (
          <div>
            <Link
              href={`/documents/${job.document_id}`}
              className="inline-flex min-h-11 items-center text-sm font-medium text-ink-primary underline-offset-4 hover:underline focus-visible:focus-ring"
            >
              Open document
            </Link>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
