'use client';

import { useEffect, useId, useState, type KeyboardEvent, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type ListboxOption = {
  value: string;
  /** Accessible name of the option. */
  label: string;
  selected: boolean;
  disabled?: boolean;
  children: ReactNode;
};

export type ListboxProps = {
  label: string;
  options: ListboxOption[];
  onActivate: (value: string) => void;
  emptyText: string;
};

/** Single tab stop; arrows move the active option, Enter or Space activates it. */
export function Listbox({ label, options, onActivate, emptyText }: ListboxProps) {
  const baseId = useId();
  const [focused, setFocused] = useState(false);
  const selectedIndex = options.findIndex((option) => option.selected);
  const [activeIndex, setActiveIndex] = useState(Math.max(0, selectedIndex));

  useEffect(() => {
    if (selectedIndex >= 0) {
      setActiveIndex(selectedIndex);
    }
  }, [selectedIndex]);

  const clampedActive = options.length === 0 ? -1 : Math.min(activeIndex, options.length - 1);
  const optionId = (index: number) => `${baseId}-option-${index}`;

  useEffect(() => {
    if (!focused || clampedActive < 0) {
      return;
    }
    document.getElementById(optionId(clampedActive))?.scrollIntoView?.({ block: 'nearest' });
  });

  const activate = (index: number) => {
    const option = options[index];
    if (option && !option.disabled) {
      onActivate(option.value);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (options.length === 0) {
      return;
    }
    const last = options.length - 1;
    const moves: Record<string, number> = {
      ArrowDown: Math.min(last, clampedActive + 1),
      ArrowUp: Math.max(0, clampedActive - 1),
      Home: 0,
      End: last,
    };
    if (event.key in moves) {
      event.preventDefault();
      setActiveIndex(moves[event.key]);
      return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate(clampedActive);
    }
  };

  if (options.length === 0) {
    return <p className="m-0 rounded-[var(--radius-inset)] bg-surface-inset p-4 text-sm text-ink-secondary">{emptyText}</p>;
  }

  return (
    <ul
      role="listbox"
      aria-label={label}
      aria-activedescendant={clampedActive >= 0 ? optionId(clampedActive) : undefined}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      className="m-0 flex list-none flex-col overflow-hidden rounded-[var(--radius-inset)] bg-surface-inset p-0 focus-visible:focus-ring"
    >
      {options.map((option, index) => (
        <li
          key={option.value}
          id={optionId(index)}
          role="option"
          aria-selected={option.selected}
          aria-disabled={option.disabled || undefined}
          aria-label={option.label}
          onClick={() => {
            setActiveIndex(index);
            activate(index);
          }}
          className={cn(
            'flex min-h-16 cursor-pointer items-center gap-3 border-b border-stroke-subtle px-4 py-3 last:border-b-0',
            'transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)]',
            option.selected
              ? 'bg-surface-selected shadow-[inset_0_0_0_1px_var(--ink-primary)]'
              : 'hover:bg-surface-hover',
            option.disabled && 'cursor-not-allowed text-ink-muted',
            focused && index === clampedActive && 'outline-2 -outline-offset-4 outline-[var(--focus-ring)] outline-solid',
          )}
        >
          {option.children}
        </li>
      ))}
    </ul>
  );
}
