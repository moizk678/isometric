import { AlertCircle } from 'lucide-react';
import { Button } from './Button';
import { Panel } from './Panel';

export type ErrorStateProps = {
  title: string;
  message: string;
  requestId?: string | null;
  onRetry?: () => void;
};

export function ErrorState({ title, message, requestId, onRetry }: ErrorStateProps) {
  return (
    <Panel className="bg-surface-inset">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-state-danger text-ink-primary"
          aria-hidden
        >
          <AlertCircle size={18} strokeWidth={1.5} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-base font-semibold leading-6">{title}</h3>
          <p className="mt-1 text-sm leading-5 text-ink-secondary">{message}</p>
          {requestId ? (
            <p className="mt-2 font-mono text-xs leading-4 text-ink-muted">
              Request ID: <span>{requestId}</span>
            </p>
          ) : null}
          {onRetry ? (
            <div className="mt-4">
              <Button variant="secondary" onClick={onRetry}>Try again</Button>
            </div>
          ) : null}
        </div>
      </div>
    </Panel>
  );
}
