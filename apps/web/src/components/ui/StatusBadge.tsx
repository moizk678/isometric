import type { ReactNode } from 'react';
import {
  AlertCircle,
  Ban,
  CheckCircle2,
  CircleDashed,
  Clock3,
  Loader2,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/cn';

const ICON_STROKE = 1.5;

export type StatusBadgeProps = {
  label: string;
  icon: ReactNode;
  className?: string;
  tone?: 'neutral' | 'positive' | 'pending' | 'warning' | 'danger' | 'info';
};

export function StatusBadge({ label, icon, className, tone = 'neutral' }: StatusBadgeProps) {
  const toneClasses: Record<NonNullable<StatusBadgeProps['tone']>, string> = {
    neutral: 'bg-surface-inset text-ink-primary',
    positive: 'bg-state-positive text-ink-primary',
    pending: 'bg-state-pending text-ink-primary',
    warning: 'bg-state-warning text-ink-primary',
    danger: 'bg-state-danger text-ink-primary',
    info: 'bg-state-info text-ink-primary',
  };

  return (
    <span
      className={cn(
        'inline-flex h-7 items-center gap-1.5 rounded-full px-3 text-xs font-medium leading-4',
        toneClasses[tone],
        className,
      )}
    >
      <span className="inline-flex shrink-0" aria-hidden>{icon}</span>
      <span>{label}</span>
    </span>
  );
}

export type JobState = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled';

const jobStateConfig: Record<JobState, { label: string; tone: StatusBadgeProps['tone']; icon: ReactNode }> = {
  queued: { label: 'Queued', tone: 'info', icon: <Clock3 size={14} strokeWidth={ICON_STROKE} /> },
  running: { label: 'Running', tone: 'pending', icon: <Loader2 size={14} strokeWidth={ICON_STROKE} className="animate-spin" /> },
  succeeded: { label: 'Succeeded', tone: 'positive', icon: <CheckCircle2 size={14} strokeWidth={ICON_STROKE} /> },
  failed: { label: 'Failed', tone: 'danger', icon: <AlertCircle size={14} strokeWidth={ICON_STROKE} /> },
  canceled: { label: 'Canceled', tone: 'neutral', icon: <Ban size={14} strokeWidth={ICON_STROKE} /> },
};

export function JobStateBadge({ state }: { state: JobState }) {
  const config = jobStateConfig[state];
  return <StatusBadge label={config.label} tone={config.tone} icon={config.icon} />;
}

export type ReviewState = 'review_required' | 'ready';

const reviewStateConfig: Record<ReviewState, { label: string; tone: StatusBadgeProps['tone']; icon: ReactNode }> = {
  review_required: {
    label: 'Review required',
    tone: 'warning',
    icon: <ShieldAlert size={14} strokeWidth={ICON_STROKE} />,
  },
  ready: {
    label: 'Ready',
    tone: 'positive',
    icon: <Sparkles size={14} strokeWidth={ICON_STROKE} />,
  },
};

export function ReviewStateBadge({ state }: { state: ReviewState }) {
  const config = reviewStateConfig[state];
  return <StatusBadge label={config.label} tone={config.tone} icon={config.icon} />;
}

export function StatusBadgeNeutral({ label }: { label: string }) {
  return <StatusBadge label={label} tone="neutral" icon={<CircleDashed size={14} strokeWidth={ICON_STROKE} />} />;
}
