import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  size?: 'default' | 'large';
  tone?: 'inset' | 'panel';
  children: ReactNode;
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { className, label, size = 'default', tone = 'inset', children, type = 'button', ...props },
  ref,
) {
  const dimension = size === 'large' ? 'h-[var(--control-large)] w-[var(--control-large)]' : 'h-[var(--control-default)] w-[var(--control-default)]';

  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        'inline-flex items-center justify-center rounded-full transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)]',
        'focus-visible:focus-ring disabled:cursor-not-allowed disabled:text-ink-muted',
        tone === 'inset' ? 'bg-surface-inset hover:bg-surface-hover active:bg-surface-pressed' : 'bg-surface-panel hover:bg-surface-hover active:bg-surface-pressed',
        dimension,
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
});
