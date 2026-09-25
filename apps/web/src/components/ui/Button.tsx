import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'quiet' | 'danger';
export type ButtonSize = 'default' | 'compact' | 'large';

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leadingIcon?: ReactNode;
  loading?: boolean;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-ink-primary text-ink-on-dark hover:bg-[#242424] active:bg-[#242424] disabled:bg-surface-pressed disabled:text-ink-muted',
  secondary:
    'bg-surface-panel text-ink-primary border border-stroke-control hover:bg-surface-hover active:bg-surface-pressed disabled:text-ink-muted disabled:border-stroke-subtle',
  quiet:
    'bg-transparent text-ink-primary hover:bg-surface-hover active:bg-surface-pressed disabled:text-ink-muted',
  danger:
    'bg-state-danger text-ink-on-dark hover:bg-[#d94a32] active:bg-[#c9432d] disabled:bg-surface-pressed disabled:text-ink-muted',
};

const sizeClasses: Record<ButtonSize, string> = {
  default: 'h-[var(--control-default)] px-5 text-sm leading-5 rounded-[var(--radius-control)] min-w-[88px]',
  compact: 'h-[var(--control-compact)] px-3 text-[13px] leading-5 rounded-[18px] min-w-[72px]',
  large: 'h-[var(--control-large)] px-5 text-base leading-5 rounded-[var(--radius-control)] min-w-[96px]',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant = 'primary',
    size = 'default',
    leadingIcon,
    loading = false,
    disabled,
    children,
    type = 'button',
    ...props
  },
  ref,
) {
  const isDisabled = disabled || loading;

  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)]',
        'focus-visible:focus-ring disabled:cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {leadingIcon ? <span className="inline-flex shrink-0" aria-hidden>{leadingIcon}</span> : null}
      <span>{children}</span>
    </button>
  );
});
