'use client';

import type { DrawingReadingGroup, DrawingReadingResponse } from '@/api/drawingReading';
import { ApiError } from '@/api/http';
import { EmptyState, ErrorState, Panel, ProgressBar } from '@/components/ui';

export type DrawingReadingPanelProps = {
  reading: DrawingReadingResponse | null;
  loading: boolean;
  error: ApiError | null;
  onRetry?: () => void;
  className?: string;
};

function unavailableMessage(errorCode: string | null | undefined): string {
  if (errorCode === 'missing_page') {
    return 'The source page image was not available for reading.';
  }
  if (errorCode) {
    return `Drawing reading failed (${errorCode}).`;
  }
  return 'Drawing reading could not be completed.';
}

function ReadingTable({ group }: { group: DrawingReadingGroup }) {
  return (
    <section aria-labelledby={`reading-group-${group.id}`} className="flex flex-col gap-3">
      <h3 id={`reading-group-${group.id}`} className="m-0 text-base font-semibold leading-6">
        {group.title}
      </h3>
      {group.rows.length === 0 ? (
        <p className="m-0 text-sm leading-5 text-ink-secondary">None found.</p>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-inset)] border border-stroke-subtle">
          <table className="w-full min-w-[280px] border-collapse text-left text-sm leading-5">
            <thead>
              <tr className="border-b border-stroke-subtle bg-surface-inset">
                <th scope="col" className="px-3 py-2 font-medium text-ink-secondary">
                  Location
                </th>
                <th scope="col" className="px-3 py-2 font-medium text-ink-secondary">
                  Reading
                </th>
              </tr>
            </thead>
            <tbody>
              {group.rows.map((row, index) => (
                <tr key={`${group.id}-${index}`} className="border-b border-stroke-subtle last:border-b-0">
                  <td className="px-3 py-2 align-top text-ink-primary">{row.location}</td>
                  <td className="px-3 py-2 align-top text-ink-primary">{row.reading}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function DrawingReadingPanel({ reading, loading, error, onRetry, className }: DrawingReadingPanelProps) {
  if (loading && !reading) {
    return (
      <Panel className={className}>
        <ProgressBar label="Reading the drawing" />
      </Panel>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load drawing reading"
        message={error.message}
        requestId={error.requestId}
        onRetry={onRetry}
      />
    );
  }

  if (!reading || reading.status === 'pending') {
    return (
      <Panel className={className}>
        <ProgressBar label="Reading the drawing" />
      </Panel>
    );
  }

  if (reading.status === 'disabled') {
    return (
      <Panel className={className}>
        <EmptyState title="Drawing reading is turned off" description="Vision reading is disabled for this environment." />
      </Panel>
    );
  }

  if (reading.status === 'absent') {
    return (
      <Panel className={className}>
        <EmptyState title="No reading for this drawing" description="This document has no drawing reading job yet." />
      </Panel>
    );
  }

  if (reading.status === 'unavailable') {
    return (
      <ErrorState
        title="Drawing reading unavailable"
        message={unavailableMessage(reading.error_code)}
        onRetry={onRetry}
      />
    );
  }

  const groups = reading.groups ?? [];

  return (
    <Panel as="section" aria-label="Drawing reading" className={`flex flex-col gap-6 ${className ?? ''}`}>
      {groups.map((group) => (
        <ReadingTable key={group.id} group={group} />
      ))}
    </Panel>
  );
}
