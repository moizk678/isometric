import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';
import { Button } from './Button';
import { Panel } from './Panel';

export type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
};

export function EmptyState({ title, description, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <Panel className="flex flex-col items-center py-12 text-center">
      <div
        className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-inset text-ink-secondary"
        aria-hidden
      >
        {icon ?? <Inbox size={24} strokeWidth={1.5} />}
      </div>
      <h3 className="m-0 text-base font-semibold leading-6">{title}</h3>
      <p className="mt-2 max-w-[360px] text-sm leading-5 text-ink-secondary">{description}</p>
      {actionLabel && onAction ? (
        <div className="mt-6">
          <Button onClick={onAction}>{actionLabel}</Button>
        </div>
      ) : null}
    </Panel>
  );
}
