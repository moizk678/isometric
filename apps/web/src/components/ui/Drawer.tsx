'use client';

import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { getFocusableElements, trapFocus } from '@/lib/focus-trap';
import { cn } from '@/lib/cn';
import { IconButton } from './IconButton';

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: 'start' | 'end';
  className?: string;
};

export function Drawer({ open, onClose, title, children, side = 'start', className }: DrawerProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    restoreFocusRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (!panel) {
      return;
    }

    const focusable = getFocusableElements(panel);
    (focusable[0] ?? panel).focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (panelRef.current) {
        trapFocus(panelRef.current, event);
      }
    };

    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      restoreFocusRef.current?.focus();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[var(--z-dialog)] flex" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-[var(--overlay-scrim)]"
        aria-label="Close drawer"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'relative z-[calc(var(--z-dialog)+1)] flex h-full max-w-[90vw] flex-col bg-surface-panel shadow-[var(--shadow-dialog)]',
          side === 'start' ? 'rounded-e-[var(--radius-overlay)]' : 'ms-auto rounded-s-[var(--radius-overlay)]',
          'w-[min(440px,90vw)]',
          className,
        )}
      >
        <header className="flex min-h-[72px] shrink-0 items-center justify-between gap-3 border-b border-stroke-subtle px-6 py-4">
          <h2 id={titleId} className="m-0 text-lg font-semibold leading-6">{title}</h2>
          <IconButton label="Close drawer" onClick={onClose}>
            <X size={20} strokeWidth={1.5} aria-hidden />
          </IconButton>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}
