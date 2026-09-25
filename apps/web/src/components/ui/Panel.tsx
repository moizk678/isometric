import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type PanelProps = HTMLAttributes<HTMLElement> & {
  as?: 'section' | 'div' | 'article';
  density?: 'default' | 'compact';
  title?: string;
  description?: string;
  actions?: ReactNode;
};

export function Panel({
  as = 'section',
  density = 'default',
  title,
  description,
  actions,
  className,
  children,
  ...props
}: PanelProps) {
  const Component = as;

  return (
    <Component
      className={cn(
        'bg-surface-panel text-ink-primary',
        density === 'compact' ? 'rounded-[24px] p-4' : 'rounded-[var(--radius-panel)] p-6',
        className,
      )}
      {...props}
    >
      {(title || actions) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div className="min-w-0">
            {title ? <h2 className="m-0 text-lg font-semibold leading-6 tracking-tight">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm leading-5 text-ink-secondary">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </header>
      )}
      {children}
    </Component>
  );
}
