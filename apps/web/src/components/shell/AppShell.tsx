'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileStack, Menu, PanelLeftClose, PanelLeftOpen, Upload } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Drawer } from '@/components/ui/Drawer';
import { IconButton } from '@/components/ui/IconButton';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/cn';

const NAV_ITEMS = [
  { href: '/documents', label: 'Documents', icon: FileStack },
  { href: '/upload', label: 'Upload', icon: Upload },
] as const;

function NavLink({
  href,
  label,
  icon: Icon,
  collapsed,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: typeof FileStack;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn(
        'flex h-[var(--control-default)] items-center gap-3 rounded-[var(--radius-control)] px-3 text-sm font-medium leading-5 transition-colors duration-[var(--duration-quick)]',
        'focus-visible:focus-ring',
        active ? 'bg-ink-primary text-ink-on-dark' : 'text-ink-secondary hover:bg-surface-hover',
        collapsed ? 'justify-center px-0' : '',
      )}
      aria-current={active ? 'page' : undefined}
      title={collapsed ? label : undefined}
    >
      <Icon size={20} strokeWidth={1.5} aria-hidden className="shrink-0" />
      {collapsed ? <span className="sr-only">{label}</span> : <span>{label}</span>}
    </Link>
  );
}

function SidebarNav({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {NAV_ITEMS.map((item) => (
        <NavLink key={item.href} {...item} collapsed={collapsed} onNavigate={onNavigate} />
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const sidebarWidth = collapsed ? 'var(--sidebar-rail)' : 'var(--sidebar-expanded)';

  return (
    <div className="flex min-h-screen bg-surface-page">
      {isDesktop ? (
        <aside
          className="sticky top-0 flex h-screen shrink-0 flex-col border-e border-stroke-subtle bg-surface-panel p-4 transition-[width] duration-[var(--duration-panel)] ease-[var(--ease-standard)]"
          style={{ width: sidebarWidth }}
        >
          <div className="mb-6 flex items-center justify-between gap-2">
            {!collapsed ? (
              <p className="m-0 text-base font-semibold leading-5 tracking-tight">Isometric</p>
            ) : (
              <span className="sr-only">Isometric</span>
            )}
            <IconButton
              label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              onClick={() => setCollapsed((value) => !value)}
            >
              {collapsed ? (
                <PanelLeftOpen size={20} strokeWidth={1.5} aria-hidden />
              ) : (
                <PanelLeftClose size={20} strokeWidth={1.5} aria-hidden />
              )}
            </IconButton>
          </div>
          <SidebarNav collapsed={collapsed} />
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        {!isDesktop ? (
          <header className="sticky top-0 z-[var(--z-sticky)] flex h-14 items-center gap-3 border-b border-stroke-subtle bg-surface-panel px-4">
            <IconButton label="Open navigation" onClick={() => setMobileNavOpen(true)}>
              <Menu size={20} strokeWidth={1.5} aria-hidden />
            </IconButton>
            <p className="m-0 text-base font-semibold leading-5">Isometric</p>
          </header>
        ) : null}

        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>

      {!isDesktop ? (
        <Drawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} title="Navigation">
          <SidebarNav collapsed={false} onNavigate={() => setMobileNavOpen(false)} />
        </Drawer>
      ) : null}
    </div>
  );
}
