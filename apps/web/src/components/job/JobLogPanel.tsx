'use client';

import { useEffect, useRef } from 'react';
import type { JobResponse } from '@/api/jobs';
import { stageLabel } from '@/components/job/stageLabels';

export type JobLogPanelProps = {
  logs: JobResponse['logs'];
  emptyLabel?: string;
};

function formatLogTime(createdAt: string): string {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) {
    return createdAt;
  }
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function logLineClass(level: string): string {
  if (level === 'warning') {
    return 'text-ink-warning';
  }
  if (level === 'error') {
    return 'text-ink-danger';
  }
  return 'text-ink-secondary';
}

export function JobLogPanel({ logs, emptyLabel = 'Waiting for processing logs…' }: JobLogPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'nearest' });
  }, [logs.length, logs[logs.length - 1]?.id]);

  return (
    <div
      className="max-h-56 min-h-24 overflow-y-auto rounded-2xl border border-stroke-subtle bg-surface-inset p-3 font-mono text-[11px] leading-5"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      data-testid="job-log-panel"
    >
      {logs.length === 0 ? (
        <p className="m-0 text-ink-muted">{emptyLabel}</p>
      ) : (
        <ul className="m-0 list-none space-y-1 p-0">
          {logs.map((entry) => (
            <li key={entry.id} className={logLineClass(entry.level)} data-testid="job-log-line">
              <span className="text-ink-muted">{formatLogTime(entry.created_at)}</span>
              {' · '}
              <span className="text-ink-primary">{stageLabel(entry.stage)}</span>
              {' · '}
              <span>{entry.message}</span>
            </li>
          ))}
        </ul>
      )}
      <div ref={endRef} />
    </div>
  );
}
