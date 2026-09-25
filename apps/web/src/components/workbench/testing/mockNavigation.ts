import { useMemo, useSyncExternalStore } from 'react';

/** In-memory stand-in for next/navigation so tests can observe URL search params. */
let pathname = '/';
let search = '';
const listeners = new Set<() => void>();
export const replaceCalls: string[] = [];

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function navigate(href: string) {
  replaceCalls.push(href);
  const [path, query = ''] = href.split('?');
  pathname = path;
  search = query;
  listeners.forEach((listener) => listener());
}

export function resetNavigation(initialPathname: string, initialSearch = '') {
  pathname = initialPathname;
  search = initialSearch;
  replaceCalls.length = 0;
}

export function currentSearchParams(): URLSearchParams {
  return new URLSearchParams(search);
}

const router = {
  replace: (href: string) => navigate(href),
  push: (href: string) => navigate(href),
  back: () => undefined,
  forward: () => undefined,
  refresh: () => undefined,
  prefetch: () => undefined,
};

export const navigationModule = {
  useRouter: () => router,
  usePathname: () => useSyncExternalStore(subscribe, () => pathname, () => pathname),
  useSearchParams: () => {
    const value = useSyncExternalStore(subscribe, () => search, () => search);
    return useMemo(() => new URLSearchParams(value), [value]);
  },
};
