'use client';

import { cn } from '@/lib/cn';

export type SegmentedOption<T extends string> = {
  value: T;
  label: string;
};

export type SegmentedControlProps<T extends string> = {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  className?: string;
};

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        'inline-flex h-[var(--control-default)] gap-1 rounded-[var(--radius-control)] bg-surface-inset p-1',
        className,
      )}
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            className={cn(
              'h-9 min-w-[4.5rem] rounded-[18px] px-4 text-sm font-medium leading-5 transition-colors duration-[var(--duration-standard)] ease-[var(--ease-standard)]',
              'focus-visible:focus-ring',
              selected
                ? 'bg-ink-primary text-ink-on-dark'
                : 'bg-transparent text-ink-secondary hover:bg-surface-hover',
            )}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
