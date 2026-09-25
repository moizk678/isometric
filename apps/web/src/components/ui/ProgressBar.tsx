import { cn } from '@/lib/cn';

export type ProgressBarProps = {
  label?: string;
  className?: string;
};

export function ProgressBar({ label = 'Loading', className }: ProgressBarProps) {
  return (
    <div className={cn('w-full', className)} role="progressbar" aria-label={label} aria-valuetext="Loading">
      {label ? <p className="mb-2 text-xs leading-4 text-ink-secondary">{label}</p> : null}
      <div className="h-2 overflow-hidden rounded-full bg-surface-inset">
        <div
          className="progress-indeterminate-bar h-full w-1/3 rounded-full bg-ink-primary motion-reduce:animate-none"
          style={{ transformOrigin: '0% 50%' }}
        />
      </div>
    </div>
  );
}
